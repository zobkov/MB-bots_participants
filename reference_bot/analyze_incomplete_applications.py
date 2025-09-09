#!/usr/bin/env python3
"""
Скрипт для анализа контекста из Redis и составления таблицы незаполненных анкет в CSV формате.
Анализирует FSM состояния пользователей в Redis и данные из PostgreSQL.
"""

import asyncio
import csv
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import asyncpg
import redis.asyncio as redis
from environs import Env

# Добавляем путь к проекту для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import load_config
from app.infrastructure.database.models.applications import ApplicationsModel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedisConfig:
    """Конфигурация для подключения к Redis"""
    def __init__(self, host: str = "localhost", port: int = 6379, password: str = None, db: int = 0):
        self.host = host
        self.port = port
        self.password = password
        self.db = db


class IncompleteApplicationsAnalyzer:
    """Анализатор незаполненных анкет"""
    
    def __init__(self, redis_config: RedisConfig, postgres_config: Dict[str, Any]):
        self.redis_config = redis_config
        self.postgres_config = postgres_config
        
        # Определяем поля анкеты и их важность
        self.application_fields = {
            'full_name': 'ФИО',
            'university': 'Университет',
            'course': 'Курс',
            'phone': 'Телефон',
            'email': 'Email',
            'how_found_kbk': 'Как узнал о КБК',
            'experience': 'Опыт',
            'motivation': 'Мотивация',
            'resume_local_path': 'Резюме',
            'previous_department': 'Предыдущий отдел',
            'department_1': 'Отдел 1 приоритет',
            'position_1': 'Позиция 1 приоритет',
            'subdepartment_1': 'Подотдел 1 приоритет',
            'department_2': 'Отдел 2 приоритет',
            'position_2': 'Позиция 2 приоритет',
            'subdepartment_2': 'Подотдел 2 приоритет',
            'department_3': 'Отдел 3 приоритет',
            'position_3': 'Позиция 3 приоритет',
            'subdepartment_3': 'Подотдел 3 приоритет',
        }
        
        # Обязательные поля для завершенной анкеты
        self.required_fields = {
            'full_name', 'university', 'course', 'phone', 'email', 
            'how_found_kbk', 'experience', 'motivation', 'resume_local_path',
            'department_1', 'position_1'
        }

    async def connect_to_redis(self) -> redis.Redis:
        """Подключение к Redis"""
        try:
            redis_client = redis.Redis(
                host=self.redis_config.host,
                port=self.redis_config.port,
                password=self.redis_config.password,
                db=self.redis_config.db,
                decode_responses=True
            )
            
            # Тестируем подключение
            await redis_client.ping()
            logger.info(f"Успешно подключен к Redis: {self.redis_config.host}:{self.redis_config.port}")
            return redis_client
            
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            raise

    async def connect_to_postgres(self) -> asyncpg.Connection:
        """Подключение к PostgreSQL"""
        try:
            conn = await asyncpg.connect(
                user=self.postgres_config['user'],
                password=self.postgres_config['password'],
                database=self.postgres_config['database'],
                host=self.postgres_config['host'],
                port=self.postgres_config['port']
            )
            logger.info(f"Успешно подключен к PostgreSQL: {self.postgres_config['host']}:{self.postgres_config['port']}")
            return conn
            
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            raise

    async def get_fsm_data(self, redis_client: redis.Redis) -> Dict[str, Dict]:
        """Получение данных FSM из Redis"""
        fsm_data = {}
        
        try:
            # Получаем все ключи FSM состояний
            # Формат ключей: fsm:{bot_id}:{user_id}:state или fsm:{bot_id}:{user_id}:data
            fsm_keys = await redis_client.keys("fsm:*")
            
            user_states = {}
            user_data = {}
            
            for key in fsm_keys:
                parts = key.split(':')
                if len(parts) >= 4:
                    user_id = parts[2]
                    key_type = parts[3]
                    
                    if key_type == 'state':
                        state_value = await redis_client.get(key)
                        if state_value:
                            user_states[user_id] = state_value
                    elif key_type == 'data':
                        data_value = await redis_client.get(key)
                        if data_value:
                            try:
                                user_data[user_id] = json.loads(data_value)
                            except json.JSONDecodeError:
                                logger.warning(f"Не удалось разобрать JSON для ключа {key}")
            
            # Объединяем состояния и данные
            for user_id in set(list(user_states.keys()) + list(user_data.keys())):
                fsm_data[user_id] = {
                    'state': user_states.get(user_id),
                    'data': user_data.get(user_id, {})
                }
            
            logger.info(f"Получено FSM данных для {len(fsm_data)} пользователей")
            return fsm_data
            
        except Exception as e:
            logger.error(f"Ошибка получения FSM данных: {e}")
            return {}

    async def get_applications_from_db(self, postgres_conn: asyncpg.Connection) -> Dict[int, ApplicationsModel]:
        """Получение заявок из базы данных"""
        try:
            query = """
            SELECT id, user_id, created, updated, full_name, university, course, phone, email, 
                   telegram_username, how_found_kbk, department_1, position_1, subdepartment_1,
                   department_2, position_2, subdepartment_2, department_3, position_3, subdepartment_3,
                   experience, motivation, resume_local_path, resume_google_drive_url, previous_department
            FROM applications
            ORDER BY created DESC;
            """
            
            rows = await postgres_conn.fetch(query)
            applications = {}
            
            for row in rows:
                app = ApplicationsModel(
                    id=row['id'],
                    user_id=row['user_id'],
                    created=row['created'],
                    updated=row['updated'],
                    full_name=row['full_name'],
                    university=row['university'],
                    course=row['course'],
                    phone=row['phone'],
                    email=row['email'],
                    telegram_username=row['telegram_username'],
                    how_found_kbk=row['how_found_kbk'],
                    department_1=row['department_1'],
                    position_1=row['position_1'],
                    subdepartment_1=row['subdepartment_1'],
                    department_2=row['department_2'],
                    position_2=row['position_2'],
                    subdepartment_2=row['subdepartment_2'],
                    department_3=row['department_3'],
                    position_3=row['position_3'],
                    subdepartment_3=row['subdepartment_3'],
                    experience=row['experience'],
                    motivation=row['motivation'],
                    resume_local_path=row['resume_local_path'],
                    resume_google_drive_url=row['resume_google_drive_url'],
                    previous_department=row['previous_department']
                )
                applications[app.user_id] = app
            
            logger.info(f"Получено {len(applications)} заявок из базы данных")
            return applications
            
        except Exception as e:
            logger.error(f"Ошибка получения заявок из БД: {e}")
            return {}

    def analyze_completion_status(self, application: ApplicationsModel) -> Tuple[bool, List[str], float]:
        """Анализ статуса заполнения анкеты"""
        missing_fields = []
        filled_fields = 0
        total_fields = len(self.application_fields)
        
        for field_name in self.application_fields:
            value = getattr(application, field_name, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_fields.append(self.application_fields[field_name])
            else:
                filled_fields += 1
        
        # Проверяем обязательные поля
        missing_required = []
        for field in self.required_fields:
            value = getattr(application, field, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                missing_required.append(self.application_fields[field])
        
        is_complete = len(missing_required) == 0
        completion_percentage = (filled_fields / total_fields) * 100
        
        return is_complete, missing_fields, completion_percentage

    def get_state_description(self, state: str) -> str:
        """Получение описания состояния FSM"""
        state_descriptions = {
            # FirstStageSG состояния
            "FirstStageSG:stage_info": "Просмотр информации о первом этапе",
            "FirstStageSG:full_name": "Ввод ФИО",
            "FirstStageSG:university": "Ввод университета",
            "FirstStageSG:course": "Ввод курса",
            "FirstStageSG:phone": "Ввод телефона",
            "FirstStageSG:email": "Ввод email",
            "FirstStageSG:how_found_kbk": "Выбор как узнал о КБК",
            "FirstStageSG:previous_department": "Выбор предыдущего отдела",
            "FirstStageSG:experience": "Ввод опыта",
            "FirstStageSG:motivation": "Ввод мотивации",
            "FirstStageSG:resume_upload": "Загрузка резюме",
            "FirstStageSG:confirmation": "Подтверждение анкеты",
            "FirstStageSG:edit_menu": "Меню редактирования",
            "FirstStageSG:success": "Анкета успешно отправлена",
            
            # JobSelectionSG состояния
            "JobSelectionSG:select_department": "Выбор отдела (1 приоритет)",
            "JobSelectionSG:select_subdepartment": "Выбор подотдела (1 приоритет)",
            "JobSelectionSG:select_position": "Выбор позиции (1 приоритет)",
            "JobSelectionSG:select_department_2": "Выбор отдела (2 приоритет)",
            "JobSelectionSG:select_subdepartment_2": "Выбор подотдела (2 приоритет)",
            "JobSelectionSG:select_position_2": "Выбор позиции (2 приоритет)",
            "JobSelectionSG:select_department_3": "Выбор отдела (3 приоритет)",
            "JobSelectionSG:select_subdepartment_3": "Выбор подотдела (3 приоритет)",
            "JobSelectionSG:select_position_3": "Выбор позиции (3 приоритет)",
            "JobSelectionSG:priorities_overview": "Обзор всех приоритетов",
            "JobSelectionSG:complete_selection": "Завершение выбора",
        }
        
        return state_descriptions.get(state, f"Неизвестное состояние: {state}")

    async def generate_csv_report(self, analysis_data: List[Dict], filename: str = None):
        """Генерация CSV отчета"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"incomplete_applications_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'user_id', 'telegram_username', 'full_name', 'email', 'phone',
                    'current_state', 'state_description', 'in_database', 'is_complete',
                    'completion_percentage', 'missing_fields', 'last_updated', 'created'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for data in analysis_data:
                    writer.writerow(data)
            
            logger.info(f"CSV отчет сохранен: {filename}")
            print(f"✅ Отчет сохранен в файл: {filename}")
            
        except Exception as e:
            logger.error(f"Ошибка создания CSV отчета: {e}")
            raise

    async def analyze_applications(self, redis_config: RedisConfig = None) -> List[Dict]:
        """Основной метод анализа заявок"""
        # Используем переданную конфигурацию Redis или текущую
        if redis_config:
            self.redis_config = redis_config
            
        redis_client = None
        postgres_conn = None
        
        try:
            # Подключаемся к Redis и PostgreSQL
            redis_client = await self.connect_to_redis()
            postgres_conn = await self.connect_to_postgres()
            
            # Получаем данные
            fsm_data = await self.get_fsm_data(redis_client)
            applications = await self.get_applications_from_db(postgres_conn)
            
            analysis_results = []
            
            # Анализируем каждого пользователя из FSM
            for user_id_str, fsm_info in fsm_data.items():
                try:
                    user_id = int(user_id_str)
                except ValueError:
                    logger.warning(f"Некорректный user_id: {user_id_str}")
                    continue
                
                application = applications.get(user_id)
                current_state = fsm_info.get('state')
                fsm_user_data = fsm_info.get('data', {})
                
                # Определяем статус заполнения
                if application:
                    is_complete, missing_fields, completion_percentage = self.analyze_completion_status(application)
                    in_database = True
                    last_updated = application.updated.isoformat() if application.updated else None
                    created = application.created.isoformat() if application.created else None
                    full_name = application.full_name
                    email = application.email
                    phone = application.phone
                    telegram_username = application.telegram_username
                else:
                    is_complete = False
                    missing_fields = list(self.application_fields.values())
                    completion_percentage = 0.0
                    in_database = False
                    last_updated = None
                    created = None
                    full_name = fsm_user_data.get('full_name')
                    email = fsm_user_data.get('email')
                    phone = fsm_user_data.get('phone')
                    telegram_username = fsm_user_data.get('telegram_username')
                
                analysis_results.append({
                    'user_id': user_id,
                    'telegram_username': telegram_username or 'Не указан',
                    'full_name': full_name or 'Не указано',
                    'email': email or 'Не указан',
                    'phone': phone or 'Не указан',
                    'current_state': current_state or 'Нет состояния',
                    'state_description': self.get_state_description(current_state) if current_state else 'Нет активного состояния',
                    'in_database': 'Да' if in_database else 'Нет',
                    'is_complete': 'Да' if is_complete else 'Нет',
                    'completion_percentage': f"{completion_percentage:.1f}%",
                    'missing_fields': '; '.join(missing_fields) if missing_fields else 'Все поля заполнены',
                    'last_updated': last_updated or 'Не обновлялось',
                    'created': created or 'Не создано'
                })
            
            # Также проверяем пользователей, которые есть в БД, но нет в FSM (завершили процесс)
            for user_id, application in applications.items():
                if str(user_id) not in fsm_data:
                    is_complete, missing_fields, completion_percentage = self.analyze_completion_status(application)
                    
                    analysis_results.append({
                        'user_id': user_id,
                        'telegram_username': application.telegram_username or 'Не указан',
                        'full_name': application.full_name or 'Не указано',
                        'email': application.email or 'Не указан',
                        'phone': application.phone or 'Не указан',
                        'current_state': 'Завершен',
                        'state_description': 'Процесс подачи заявки завершен',
                        'in_database': 'Да',
                        'is_complete': 'Да' if is_complete else 'Нет',
                        'completion_percentage': f"{completion_percentage:.1f}%",
                        'missing_fields': '; '.join(missing_fields) if missing_fields else 'Все поля заполнены',
                        'last_updated': application.updated.isoformat() if application.updated else 'Не обновлялось',
                        'created': application.created.isoformat() if application.created else 'Не создано'
                    })
            
            # Сортируем результаты по проценту заполнения (незаполненные сначала)
            analysis_results.sort(key=lambda x: (
                x['is_complete'] == 'Да',  # Незаполненные сначала
                -float(x['completion_percentage'].rstrip('%'))  # По убыванию процента заполнения
            ))
            
            return analysis_results
            
        finally:
            # Закрываем соединения
            if redis_client:
                await redis_client.aclose()
            if postgres_conn:
                await postgres_conn.close()

    def print_summary(self, analysis_data: List[Dict]):
        """Вывод краткой сводки"""
        total_users = len(analysis_data)
        incomplete_users = len([d for d in analysis_data if d['is_complete'] == 'Нет'])
        users_in_db = len([d for d in analysis_data if d['in_database'] == 'Да'])
        users_in_fsm = len([d for d in analysis_data if d['current_state'] != 'Завершен'])
        
        print("\n" + "="*60)
        print("📊 СВОДКА АНАЛИЗА НЕЗАПОЛНЕННЫХ АНКЕТ")
        print("="*60)
        print(f"👥 Всего пользователей: {total_users}")
        print(f"❌ Незаполненных анкет: {incomplete_users}")
        print(f"✅ Полностью заполненных: {total_users - incomplete_users}")
        print(f"💾 Записей в базе данных: {users_in_db}")
        print(f"🔄 Активных в FSM: {users_in_fsm}")
        print("="*60)
        
        if incomplete_users > 0:
            print(f"\n🔍 ТОП-5 НЕЗАПОЛНЕННЫХ АНКЕТ:")
            incomplete_only = [d for d in analysis_data if d['is_complete'] == 'Нет'][:5]
            for i, data in enumerate(incomplete_only, 1):
                print(f"{i}. User ID: {data['user_id']} | {data['full_name']} | {data['completion_percentage']} | {data['state_description']}")


async def main():
    """Главная функция"""
    print("🔍 Анализатор незаполненных анкет КБК")
    print("="*50)
    
    # Загружаем конфигурацию
    try:
        config = load_config()
        
        # Конфигурация PostgreSQL из настроек приложения
        postgres_config = {
            'user': config.db_applications.user,
            'password': config.db_applications.password,
            'database': config.db_applications.database,
            'host': config.db_applications.host,
            'port': config.db_applications.port
        }
        
        # Локальная конфигурация Redis для тестирования
        local_redis_config = RedisConfig(
            host="localhost",
            port=6379,
            password=None,  # Для локального Redis обычно нет пароля
            db=0
        )
        
        # Удаленная конфигурация Redis (закомментирована для безопасности)
        remote_redis_config = RedisConfig(
            host="45.90.217.194",
            port=6380,
            password=config.redis.password,  # Используем пароль из конфигурации
            db=0
        )
        
        analyzer = IncompleteApplicationsAnalyzer(local_redis_config, postgres_config)
        
        print("🔄 Подключение к локальному Redis и анализ данных...")
        
        # Анализируем локальный Redis
        try:
            analysis_results = await analyzer.analyze_applications(local_redis_config)
            
            # Генерируем отчет
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_filename = f"incomplete_applications_local_{timestamp}.csv"
            await analyzer.generate_csv_report(analysis_results, local_filename)
            
            # Выводим сводку
            analyzer.print_summary(analysis_results)
            
        except Exception as e:
            print(f"❌ Ошибка анализа локального Redis: {e}")
            logger.error(f"Ошибка анализа локального Redis: {e}")
        
        # Опционально анализируем удаленный Redis
        print(f"\n{'='*50}")
        choice = input("🌐 Хотите проанализировать удаленный Redis (45.90.217.194:6380)? (y/N): ").lower()
        
        if choice in ['y', 'yes', 'да']:
            print("🔄 Подключение к удаленному Redis и анализ данных...")
            try:
                analysis_results_remote = await analyzer.analyze_applications(remote_redis_config)
                
                # Генерируем отчет для удаленного Redis
                remote_filename = f"incomplete_applications_remote_{timestamp}.csv"
                await analyzer.generate_csv_report(analysis_results_remote, remote_filename)
                
                # Выводим сводку
                print("\n" + "="*60)
                print("📊 СВОДКА ДЛЯ УДАЛЕННОГО REDIS")
                analyzer.print_summary(analysis_results_remote)
                
            except Exception as e:
                print(f"❌ Ошибка анализа удаленного Redis: {e}")
                logger.error(f"Ошибка анализа удаленного Redis: {e}")
        
        print(f"\n✅ Анализ завершен!")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
