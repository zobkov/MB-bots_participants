-- Добавляем колонки для полной информации о заявке, если их нет
ALTER TABLE applications 
ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS university VARCHAR(255),
ADD COLUMN IF NOT EXISTS course INTEGER,
ADD COLUMN IF NOT EXISTS phone VARCHAR(50),
ADD COLUMN IF NOT EXISTS email VARCHAR(255),
ADD COLUMN IF NOT EXISTS telegram_username VARCHAR(255),
ADD COLUMN IF NOT EXISTS how_found_kbk TEXT,
ADD COLUMN IF NOT EXISTS department VARCHAR(255),
ADD COLUMN IF NOT EXISTS position VARCHAR(255),
ADD COLUMN IF NOT EXISTS experience TEXT,
ADD COLUMN IF NOT EXISTS motivation TEXT,
ADD COLUMN IF NOT EXISTS resume_local_path TEXT,
ADD COLUMN IF NOT EXISTS resume_google_drive_url TEXT;

-- Создаем enum для статусов заявок если его нет
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'application_status') THEN
        CREATE TYPE application_status AS ENUM (
            'not_submitted',
            'submitted', 
            'canceled',
            'rejected',
            'accepted',
            'stage_1',
            'stage_2', 
            'stage_3',
            'approved'
        );
        
        -- Убираем default для колонки status
        ALTER TABLE applications ALTER COLUMN status DROP DEFAULT;
        
        -- Обновляем колонку status с VARCHAR на ENUM
        ALTER TABLE applications 
        ALTER COLUMN status TYPE application_status 
        USING status::application_status;
        
        -- Возвращаем default для колонки status
        ALTER TABLE applications ALTER COLUMN status SET DEFAULT 'not_submitted'::application_status;
    END IF;
END $$;
