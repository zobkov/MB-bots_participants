# Интеграция с Google Sheets

## Описание

Функция синхронизации данных о регистрации на дебаты с Google Таблицами позволяет автоматически экспортировать всю информацию в таблицу для удобного просмотра и анализа.

## Настройка

### 1. Создание проекта в Google Cloud Console

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - Перейдите в "APIs & Services" → "Library"
   - Найдите "Google Sheets API" и включите его

### 2. Создание Service Account

1. Перейдите в "APIs & Services" → "Credentials"
2. Нажмите "Create Credentials" → "Service Account"
3. Заполните форму:
   - Service account name: `mb-bot-sheets`
   - Service account ID: (автогенерируется)
   - Description: `Service account for MB bot Google Sheets integration`
4. Нажмите "Create and Continue"
5. Выберите роль "Editor" или создайте custom роль с правами на Google Sheets
6. Нажмите "Continue" → "Done"

### 3. Создание ключа

1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на него, перейдите на вкладку "Keys"
3. Нажмите "Add Key" → "Create new key"
4. Выберите тип JSON и нажмите "Create"
5. Файл автоматически скачается

### 4. Настройка бота

1. Переместите скачанный JSON файл в папку `config/` с именем `google_credentials.json`
2. Создайте Google Таблицу для экспорта данных
3. Скопируйте ID таблицы из URL (часть между `/spreadsheets/d/` и `/edit`)
4. Добавьте email Service Account как редактора таблицы:
   - Откройте таблицу
   - Нажмите "Share" → "Share with others"
   - Добавьте email из файла `google_credentials.json` (поле `client_email`)
   - Дайте права "Editor"

### 5. Настройка .env файла

Добавьте/обновите следующие переменные в `.env`:

```env
# Google Services
GOOGLE_CREDENTIALS_PATH=config/google_credentials.json
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here
```

## Использование

### Команда синхронизации

Команда `/sync_debates_google` доступна только администраторам бота.

**Что делает команда:**

1. Получает всех пользователей из базы данных
2. Получает актуальную информацию о регистрации
3. Очищает лист "MAIN" в Google Таблице
4. Записывает новые данные в следующем формате:

| ID пользователя | Username | Видимое имя | Кейс регистрации | Название кейса | Дата обновления |
|-----------------|----------|-------------|------------------|----------------|-----------------|
| 123456789 | @username | Иван Иванов | 1 | ВТБ | — |

### Структура экспорта

**Основные данные:**
- Все пользователи бота (зарегистрированные и незарегистрированные на дебаты)
- Информация о регистрации на конкретные кейсы
- Username и видимые имена пользователей

## Безопасность

1. **Файл credentials:** Никогда не коммитьте `google_credentials.json` в репозиторий
2. **Права доступа:** Service Account имеет доступ только к таблицам, которые явно предоставлены ему
3. **Команда админов:** Синхронизация доступна только пользователям из `ADMIN_IDS`

## Устранение неполадок

### Ошибка "File not found"
- Убедитесь, что файл `config/google_credentials.json` существует
- Проверьте путь в переменной `GOOGLE_CREDENTIALS_PATH`

### Ошибка "Permission denied"
- Убедитесь, что Service Account добавлен как редактор таблицы
- Проверьте правильность ID таблицы в `GOOGLE_SPREADSHEET_ID`

### Ошибка "API not enabled"
- Включите Google Sheets API в Google Cloud Console
- Подождите несколько минут для активации API

### Ошибка "Quota exceeded"
- Google Sheets API имеет лимиты на количество запросов
- При больших объемах данных может потребоваться оптимизация

## Мониторинг

Все операции логируются:
- Успешная синхронизация: INFO уровень
- Ошибки подключения: ERROR уровень
- Детали операций: DEBUG уровень

Проверить логи можно в файле `logs/bot-YYYY-MM-DD.log` или через команды админа в боте.