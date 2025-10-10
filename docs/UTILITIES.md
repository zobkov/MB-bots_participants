# Утилиты для управления системой регистрации

Этот документ описывает все доступные утилиты для управления системой регистрации на дебаты.

## 📊 Статистика и мониторинг

### `tools/debate_manager.py`
Основная утилита для управления системой дебатов.

```bash
# Просмотр статистики
python3 tools/debate_manager.py stats

# Синхронизация Redis с БД  
python3 tools/debate_manager.py sync

# Сброс всех регистраций (ОСТОРОЖНО!)
python3 tools/debate_manager.py reset
```

### `tools/user_manager.py`
Управление пользователями и их данными.

```bash
# Список всех пользователей
python3 tools/user_manager.py list

# Только зарегистрированные на дебаты
python3 tools/user_manager.py registered

# Поиск пользователя по ID, username или имени
python3 tools/user_manager.py search "Артём"
python3 tools/user_manager.py search "@username"
python3 tools/user_manager.py search 123456789

# Общая статистика базы данных
python3 tools/user_manager.py stats
```

## 📋 Экспорт данных

### `tools/export_participants.py`
Экспорт всех участников в CSV файл.

```bash
python3 tools/export_participants.py
```

Создает файл вида `participants_YYYYMMDD_HHMMSS.csv` с колонками:
- User ID
- Username  
- Visible Name
- Debate Case
- Case Name

### `tools/test_google_sheets.py`
Тестирование интеграции с Google Таблицами.

```bash
python3 tools/test_google_sheets.py
```

Проверяет:
- Подключение к Google Sheets API
- Права доступа к таблице
- Синхронизацию данных с листом MAIN

## 🤖 Административные команды бота

Команды, доступные администраторам через Telegram бота:

### Статистика
- `/debate_stats` - Краткая статистика регистраций
- `/detailed_stats` - Подробная статистика с именами участников

### Управление
- `/reset_user_registration <user_id>` - Сброс регистрации пользователя
- `/sync_debate_cache` - Синхронизация кеша Redis с базой данных
- `/sync_debates_google` - Синхронизация данных с Google Таблицами

### Тестирование системы
- `/test_error` - Генерация тестовой ошибки
- `/test_warning` - Генерация тестовых предупреждений  
- `/test_critical` - Генерация критической ошибки
- `/test_exception` - Генерация исключения

## 🔧 Миграции базы данных

### Создание миграции
```bash
alembic revision --autogenerate -m "Описание изменений"
```

### Применение миграций
```bash
alembic upgrade head
```

### Откат миграции
```bash
alembic downgrade -1
```

## 📈 Примеры использования

### Ежедневный мониторинг
```bash
# Проверка статистики
python3 tools/debate_manager.py stats

# Просмотр новых регистраций
python3 tools/user_manager.py registered
```

### Подготовка к мероприятию
```bash
# Экспорт списка участников
python3 tools/export_participants.py

# Детальная статистика
python3 tools/user_manager.py stats
```

### Устранение проблем
```bash
# Синхронизация при расхождениях
python3 tools/debate_manager.py sync

# Поиск конкретного пользователя
python3 tools/user_manager.py search "проблемный_user"
```

## ⚠️ Важные замечания

1. **Резервное копирование**: Всегда делайте резервную копию БД перед использованием команды reset
2. **Права доступа**: Административные команды бота доступны только пользователям из `ADMIN_IDS` в .env
3. **Логирование**: Все операции логируются и доступны в папке `logs/`
4. **Мониторинг**: Система автоматически уведомляет админов о новых регистрациях и ошибках

## 🚨 В случае проблем

1. Проверьте логи в папке `logs/`
2. Убедитесь, что Redis и PostgreSQL доступны
3. Используйте команду синхронизации кеша
4. Проверьте права доступа к базе данных

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи бота
2. Используйте команды диагностики
3. Обратитесь к документации в `docs/DEBATE_REGISTRATION.md`