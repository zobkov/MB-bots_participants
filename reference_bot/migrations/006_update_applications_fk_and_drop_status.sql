-- Update applications to reference users and drop service status
-- Backfill users from applications before adding FK
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = 'users'
    ) THEN
        RAISE EXCEPTION 'Table users must exist before applying this migration';
    END IF;

    -- Insert missing users (idempotent)
    INSERT INTO users (user_id)
    SELECT DISTINCT a.user_id
    FROM applications a
    LEFT JOIN users u ON u.user_id = a.user_id
    WHERE u.user_id IS NULL;
END $$;

-- Add FK (NOT VALID so it won't fail on existing data), guarded
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE c.conname = 'applications_user_id_fkey'
          AND t.relname = 'applications'
    ) THEN
        ALTER TABLE applications
            ADD CONSTRAINT applications_user_id_fkey
            FOREIGN KEY (user_id)
            REFERENCES users(user_id)
            ON DELETE CASCADE
            NOT VALID;
    END IF;
END $$;

-- Validate FK if present and not yet validated
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE c.conname = 'applications_user_id_fkey'
          AND t.relname = 'applications'
          AND NOT c.convalidated
    ) THEN
        ALTER TABLE applications VALIDATE CONSTRAINT applications_user_id_fkey;
    END IF;
END $$;

-- Remove status column from applications if present; status is tracked in users.submission_status
ALTER TABLE applications
    DROP COLUMN IF EXISTS status;

-- Add trigger to auto-create users row on application insert (optional safety)
CREATE OR REPLACE FUNCTION ensure_user_exists() RETURNS trigger AS $$
BEGIN
    INSERT INTO users (user_id)
    VALUES (NEW.user_id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'applications_ensure_user_exists'
    ) THEN
        CREATE TRIGGER applications_ensure_user_exists
        BEFORE INSERT ON applications
        FOR EACH ROW
        EXECUTE FUNCTION ensure_user_exists();
    END IF;
END $$;
