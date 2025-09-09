-- Добавление полей для под-отделов в систему приоритетов
-- Поддержка новой структуры отделов с под-отделами

-- Добавляем новые колонки для под-отделов
ALTER TABLE applications 
ADD COLUMN IF NOT EXISTS subdepartment_1 VARCHAR(255),
ADD COLUMN IF NOT EXISTS subdepartment_2 VARCHAR(255),
ADD COLUMN IF NOT EXISTS subdepartment_3 VARCHAR(255);

-- Создаем индексы для новых полей
CREATE INDEX IF NOT EXISTS idx_applications_subdepartment_1 ON applications(subdepartment_1);
CREATE INDEX IF NOT EXISTS idx_applications_subdepartment_2 ON applications(subdepartment_2);
CREATE INDEX IF NOT EXISTS idx_applications_subdepartment_3 ON applications(subdepartment_3);

-- Добавляем комментарии к новым колонкам
COMMENT ON COLUMN applications.subdepartment_1 IS 'Под-отдел для первого приоритета (если применимо)';
COMMENT ON COLUMN applications.subdepartment_2 IS 'Под-отдел для второго приоритета (если применимо)';
COMMENT ON COLUMN applications.subdepartment_3 IS 'Под-отдел для третьего приоритета (если применимо)';
