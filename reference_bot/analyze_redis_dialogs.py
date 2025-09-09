#!/usr/bin/env python3
"""
Скрипт для анализа диалогов пользователей из Redis и составления таблицы незаполненных анкет
Анализирует состояния FSM и данные диалогов в процессе заполнения
"""

import asyncio
import json
import csv
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from redis.asyncio import Redis
import argparse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RedisConfig:
    """Конфигурация Redis"""
    host: str
    port: int
    password: Optional[str] = None
    db: int = 0

@dataclass
class UserDialogState:
    """Состояние диалога пользователя"""
    user_id: int
    username: Optional[str]
    state: Optional[str]
    dialog_data: Dict[str, Any]
    last_activity: Optional[datetime]
    completion_percentage: float
    missing_fields: List[str]

class RedisDialogAnalyzer:
    """Анализатор диалогов из Redis"""
    
    def __init__(self, redis_config: RedisConfig):
        self.redis_config = redis_config
        self.redis_client: Optional[Redis] = None
        
        # Определяем обязательные поля для анкеты
        self.required_fields = {
            'personal_info': ['full_name', 'university', 'course', 'phone', 'email'],
            'preferences': ['how_found_selections', 'priority_1_department', 'priority_1_position'],
            'content': ['experience', 'motivation'],
            'files': ['resume_file']
        }
        
        # Состояния первого этапа анкеты
        self.first_stage_states = {
            'FirstStageSG:full_name',
            'FirstStageSG:university', 
            'FirstStageSG:course',
            'FirstStageSG:phone',
            'FirstStageSG:email',
            'FirstStageSG:how_found',
            'FirstStageSG:previous_department',
            'FirstStageSG:experience',
            'FirstStageSG:motivation',
            'FirstStageSG:resume_upload',
            'FirstStageSG:confirmation',
            'FirstStageSG:success',
            'JobSelectionSG:departments',
            'JobSelectionSG:subdepartments',
            'JobSelectionSG:positions',
            'JobSelectionSG:priority_overview'
        }

    async def connect(self):
        """Подключение к Redis"""
        try:
            if self.redis_config.password:
                redis_url = f"redis://:{self.redis_config.password}@{self.redis_config.host}:{self.redis_config.port}/{self.redis_config.db}"
            else:
                redis_url = f"redis://{self.redis_config.host}:{self.redis_config.port}/{self.redis_config.db}"
                
            self.redis_client = Redis.from_url(redis_url, decode_responses=True)
            
            # Проверяем подключение
            await self.redis_client.ping()
            logger.info(f"Успешно подключились к Redis {self.redis_config.host}:{self.redis_config.port}")
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise

    async def disconnect(self):
        """Отключение от Redis"""
        if self.redis_client:
            await self.redis_client.aclose()

    async def get_all_user_keys(self) -> List[str]:
        """Получение всех ключей пользователей из Redis"""
        try:
            # Ищем ключи aiogram-dialog (fsm:bot_id:user_id:chat_id:aiogd:context:*:data)
            aiogd_keys = await self.redis_client.keys("fsm:*:*:*:aiogd:*:data")
            # Ищем классические ключи FSM 
            state_keys = await self.redis_client.keys("*:*:*:state")
            data_keys = await self.redis_client.keys("*:*:*:data")
            
            logger.info(f"Найдено {len(aiogd_keys)} ключей aiogram-dialog, {len(state_keys)} ключей состояний и {len(data_keys)} ключей данных")
            
            return aiogd_keys + state_keys + data_keys
            
        except Exception as e:
            logger.error(f"Ошибка получения ключей: {e}")
            return []

    def parse_key(self, key: str) -> Optional[Tuple[str, str, str, str]]:
        """Парсинг ключа Redis для извлечения bot_id, user_id, chat_id и типа"""
        try:
            if key.startswith('fsm:') and ':aiogd:' in key:
                # Структура: fsm:bot_id:user_id:chat_id:aiogd:context:dialog_id:data
                parts = key.split(':')
                if len(parts) >= 7:
                    bot_id = parts[1]
                    user_id = parts[2]
                    chat_id = parts[3]
                    key_type = 'aiogd_data'
                    return bot_id, user_id, chat_id, key_type
            else:
                # Классическая структура: bot_id:user_id:chat_id:state/data
                parts = key.split(':')
                if len(parts) >= 4:
                    bot_id = parts[0]
                    user_id = parts[1] 
                    chat_id = parts[2]
                    key_type = parts[3]
                    return bot_id, user_id, chat_id, key_type
        except Exception as e:
            logger.debug(f"Не удалось распарсить ключ {key}: {e}")
        return None

    async def get_user_dialog_state(self, user_id: str, chat_id: str) -> Optional[UserDialogState]:
        """Получение состояния диалога пользователя"""
        try:
            # Ищем ключи для конкретного пользователя
            user_keys = await self.redis_client.keys(f"*:{user_id}:{chat_id}:*")
            
            state = None
            dialog_data = {}
            
            for key in user_keys:
                key_parts = self.parse_key(key)
                if not key_parts:
                    continue
                    
                _, _, _, key_type = key_parts
                
                if key_type == 'state':
                    state_data = await self.redis_client.get(key)
                    if state_data:
                        try:
                            state_obj = json.loads(state_data)
                            state = state_obj.get('state')
                        except json.JSONDecodeError:
                            state = state_data
                            
                elif key_type == 'data':
                    data_str = await self.redis_client.get(key)
                    if data_str:
                        try:
                            dialog_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            logger.warning(f"Не удалось декодировать JSON для ключа {key}")
                            
                elif key_type == 'aiogd_data':
                    # Обработка данных aiogram-dialog
                    data_str = await self.redis_client.get(key)
                    if data_str:
                        try:
                            aiogd_data = json.loads(data_str)
                            # В aiogram-dialog данные находятся в поле dialog_data
                            if isinstance(aiogd_data, dict):
                                # Получаем состояние
                                if 'state' in aiogd_data and not state:
                                    state = aiogd_data['state']
                                
                                # Получаем данные диалога
                                if 'dialog_data' in aiogd_data and isinstance(aiogd_data['dialog_data'], dict):
                                    dialog_data.update(aiogd_data['dialog_data'])
                                    
                        except json.JSONDecodeError:
                            logger.warning(f"Не удалось декодировать JSON для aiogd ключа {key}")
            
            # Если нет данных, пропускаем
            if not dialog_data:
                return None
            
            # Проверяем наличие данных анкеты
            has_form_data = any(field in dialog_data for field in ['full_name', 'university', 'phone', 'email', 'experience', 'motivation'])
            
            if not has_form_data:
                return None
                
            # Получаем username из данных диалога или используем user_id
            username = dialog_data.get('username') or f"user_{user_id}"
            
            # Анализируем заполненность
            completion_percentage, missing_fields = self.analyze_completion(dialog_data)
            
            return UserDialogState(
                user_id=int(user_id),
                username=username,
                state=state or 'В процессе заполнения',
                dialog_data=dialog_data,
                last_activity=datetime.now(),  # В реальности можно получить из TTL
                completion_percentage=completion_percentage,
                missing_fields=missing_fields
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения состояния для пользователя {user_id}: {e}")
            return None

    def analyze_completion(self, dialog_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Анализ заполненности анкеты"""
        total_fields = 0
        filled_fields = 0
        missing_fields = []
        
        for category, fields in self.required_fields.items():
            for field in fields:
                total_fields += 1
                
                if field in dialog_data and dialog_data[field]:
                    # Проверяем, что поле не пустое
                    value = dialog_data[field]
                    if isinstance(value, str) and value.strip():
                        filled_fields += 1
                    elif isinstance(value, (list, dict)) and value:
                        filled_fields += 1
                    elif isinstance(value, (int, float)):
                        filled_fields += 1
                    else:
                        missing_fields.append(field)
                else:
                    missing_fields.append(field)
        
        completion_percentage = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        return completion_percentage, missing_fields

    async def analyze_all_dialogs(self) -> List[UserDialogState]:
        """Анализ всех диалогов в Redis"""
        logger.info("Начинаем анализ всех диалогов в Redis...")
        
        all_keys = await self.get_all_user_keys()
        processed_users = set()
        user_states = []
        
        for key in all_keys:
            key_parts = self.parse_key(key)
            if not key_parts:
                continue
                
            bot_id, user_id, chat_id, key_type = key_parts
            user_key = f"{user_id}:{chat_id}"
            
            if user_key in processed_users:
                continue
                
            processed_users.add(user_key)
            
            user_state = await self.get_user_dialog_state(user_id, chat_id)
            if user_state:
                user_states.append(user_state)
        
        logger.info(f"Найдено {len(user_states)} пользователей в процессе заполнения анкет")
        return user_states

    def clean_text_field(self, text: str) -> str:
        """Очистка текстового поля для CSV"""
        if not text:
            return ''
        
        # Убираем переносы строк и лишние пробелы
        cleaned = ' '.join(text.strip().split())
        
        # Ограничиваем длину для удобства чтения
        if len(cleaned) > 200:
            cleaned = cleaned[:197] + '...'
            
        return cleaned

    def prepare_csv_data(self, user_states: List[UserDialogState]) -> List[Dict[str, Any]]:
        """Подготовка данных для CSV"""
        csv_data = []
        
        for user_state in user_states:
            data = user_state.dialog_data
            
            # Извлекаем приоритеты
            priorities = []
            for i in range(1, 4):
                dept = data.get(f'priority_{i}_department', '')
                subdept = data.get(f'priority_{i}_subdepartment', '')
                position = data.get(f'priority_{i}_position', '')
                
                if dept or position:
                    dept_name = dept if dept else 'Не выбрано'
                    pos_name = position if position else 'Не выбрано'
                    priority_text = f"{dept_name} - {pos_name}"
                    if subdept:
                        priority_text = f"{dept_name} ({subdept}) - {pos_name}"
                    priorities.append(priority_text)
                else:
                    priorities.append('Не заполнено')
            
            # Обработка множественного выбора "Откуда узнали"
            how_found_selections = data.get('how_found_selections', [])
            if isinstance(how_found_selections, list):
                how_found_text = ', '.join(how_found_selections) if how_found_selections else 'Не заполнено'
            else:
                how_found_text = str(how_found_selections) if how_found_selections else 'Не заполнено'
            
            csv_row = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_state.user_id,
                'username': user_state.username or '',
                'current_state': user_state.state or 'Неизвестно',
                'completion_percentage': f"{user_state.completion_percentage:.1f}%",
                'missing_fields': ', '.join(user_state.missing_fields),
                'full_name': self.clean_text_field(data.get('full_name', '')),
                'university': self.clean_text_field(data.get('university', '')),
                'course': data.get('course', ''),
                'phone': self.clean_text_field(data.get('phone', '')),
                'email': self.clean_text_field(data.get('email', '')),
                'how_found_kbk': how_found_text,
                'previous_department': self.clean_text_field(data.get('previous_department', '')),
                'department_1': priorities[0] if len(priorities) > 0 else 'Не заполнено',
                'department_2': priorities[1] if len(priorities) > 1 else 'Не заполнено', 
                'department_3': priorities[2] if len(priorities) > 2 else 'Не заполнено',
                'experience': self.clean_text_field(data.get('experience', '')),
                'motivation': self.clean_text_field(data.get('motivation', '')),
                'resume_file': data.get('resume_file', ''),
                'resume_google_url': data.get('resume_google_url', ''),
                'raw_dialog_data': json.dumps(data, ensure_ascii=False, separators=(',', ':')) if data else '{}'
            }
            
            csv_data.append(csv_row)
        
        return csv_data

    async def export_to_csv(self, redis_label: str = "local") -> str:
        """Экспорт анализа в CSV"""
        user_states = await self.analyze_all_dialogs()
        csv_data = self.prepare_csv_data(user_states)
        
        # Создаем имя файла с меткой времени
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"redis_dialogs_analysis_{redis_label}_{timestamp}.csv"
        
        # Записываем CSV
        if csv_data:
            fieldnames = [
                'timestamp', 'user_id', 'username', 'current_state', 'completion_percentage', 
                'missing_fields', 'full_name', 'university', 'course', 'phone', 'email',
                'how_found_kbk', 'previous_department', 'department_1', 'department_2', 
                'department_3', 'experience', 'motivation', 'resume_file', 
                'resume_google_url', 'raw_dialog_data'
            ]
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, escapechar='\\')
                writer.writeheader()
                writer.writerows(csv_data)
            
            logger.info(f"Экспортировано {len(csv_data)} записей в файл {filename}")
        else:
            logger.info("Нет данных для экспорта")
            # Создаем пустой файл с заголовками
            fieldnames = ['timestamp', 'user_id', 'username', 'current_state', 'completion_percentage', 'missing_fields']
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, escapechar='\\')
                writer.writeheader()
        
        return filename

    async def print_summary(self):
        """Вывод сводки по анализу"""
        user_states = await self.analyze_all_dialogs()
        
        if not user_states:
            logger.info("Пользователи в процессе заполнения анкет не найдены")
            return
        
        logger.info(f"\n=== СВОДКА ПО АНАЛИЗУ REDIS ДИАЛОГОВ ===")
        logger.info(f"Всего пользователей в процессе заполнения: {len(user_states)}")
        
        # Статистика по состояниям
        state_stats = {}
        completion_stats = {'0-25%': 0, '25-50%': 0, '50-75%': 0, '75-100%': 0}
        
        for user_state in user_states:
            # Подсчет по состояниям
            state = user_state.state or 'Неизвестно'
            state_stats[state] = state_stats.get(state, 0) + 1
            
            # Подсчет по заполненности
            completion = user_state.completion_percentage
            if completion <= 25:
                completion_stats['0-25%'] += 1
            elif completion <= 50:
                completion_stats['25-50%'] += 1
            elif completion <= 75:
                completion_stats['50-75%'] += 1
            else:
                completion_stats['75-100%'] += 1
        
        logger.info(f"\nРаспределение по состояниям:")
        for state, count in sorted(state_stats.items()):
            logger.info(f"  {state}: {count}")
        
        logger.info(f"\nРаспределение по заполненности:")
        for range_name, count in completion_stats.items():
            logger.info(f"  {range_name}: {count}")

async def main():
    parser = argparse.ArgumentParser(description='Анализ диалогов из Redis')
    parser.add_argument('--host', default='localhost', help='Хост Redis (по умолчанию: localhost)')
    parser.add_argument('--port', type=int, default=6379, help='Порт Redis (по умолчанию: 6379)')
    parser.add_argument('--password', help='Пароль Redis (опционально)')
    parser.add_argument('--db', type=int, default=0, help='Номер базы данных Redis (по умолчанию: 0)')
    parser.add_argument('--label', default='local', help='Метка для имени файла (по умолчанию: local)')
    
    args = parser.parse_args()
    
    redis_config = RedisConfig(
        host=args.host,
        port=args.port,
        password=args.password,
        db=args.db
    )
    
    analyzer = RedisDialogAnalyzer(redis_config)
    
    try:
        await analyzer.connect()
        
        # Выводим сводку
        await analyzer.print_summary()
        
        # Экспортируем в CSV
        filename = await analyzer.export_to_csv(args.label)
        
        logger.info(f"\nАнализ завершен. Результаты сохранены в файл: {filename}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения анализа: {e}")
    finally:
        await analyzer.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
