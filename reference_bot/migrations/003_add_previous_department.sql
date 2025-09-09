-- Добавление поля previous_department в таблицу applications
ALTER TABLE applications 
ADD COLUMN IF NOT EXISTS previous_department VARCHAR(255);

-- Добавляем комментарий к колонке
COMMENT ON COLUMN applications.previous_department IS 'Отдел, в котором пользователь участвовал в КБК ранее';
