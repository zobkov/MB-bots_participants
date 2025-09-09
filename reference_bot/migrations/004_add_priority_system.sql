-- Добавление системы приоритетов для выбора вакансий
-- Заменяем одиночные department/position на три приоритета

-- Добавляем новые колонки для системы приоритетов
ALTER TABLE applications 
ADD COLUMN IF NOT EXISTS department_1 VARCHAR(255),
ADD COLUMN IF NOT EXISTS position_1 VARCHAR(255),
ADD COLUMN IF NOT EXISTS department_2 VARCHAR(255),
ADD COLUMN IF NOT EXISTS position_2 VARCHAR(255),
ADD COLUMN IF NOT EXISTS department_3 VARCHAR(255),
ADD COLUMN IF NOT EXISTS position_3 VARCHAR(255);

-- Мигрируем существующие данные из старых полей в первый приоритет
UPDATE applications 
SET department_1 = department, position_1 = position 
WHERE department IS NOT NULL OR position IS NOT NULL;

-- Удаляем старые колонки (закомментировано для безопасности)
ALTER TABLE applications DROP COLUMN IF EXISTS department;
ALTER TABLE applications DROP COLUMN IF EXISTS position;

-- Создаем индексы для новых полей
CREATE INDEX IF NOT EXISTS idx_applications_department_1 ON applications(department_1);
CREATE INDEX IF NOT EXISTS idx_applications_department_2 ON applications(department_2);
CREATE INDEX IF NOT EXISTS idx_applications_department_3 ON applications(department_3);
