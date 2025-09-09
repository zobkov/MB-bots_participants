-- Создание таблицы applications
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'not_submitted',
    created TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Форма первого этапа
    full_name VARCHAR(255),
    university VARCHAR(255),
    course INTEGER CHECK (course >= 1 AND course <= 6),
    phone VARCHAR(50),
    email VARCHAR(255),
    telegram_username VARCHAR(255),
    how_found_kbk TEXT,
    department VARCHAR(255),
    position VARCHAR(255),
    experience TEXT,
    motivation TEXT,
    resume_local_path VARCHAR(500),
    resume_google_drive_url VARCHAR(500)
);

-- Создание индексов
CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created);
