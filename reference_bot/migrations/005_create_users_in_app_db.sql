-- Create users table in applications database to consolidate user service info
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    created TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    language VARCHAR(5) NOT NULL DEFAULT 'ru',
    is_alive BOOLEAN NOT NULL DEFAULT TRUE,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    submission_status VARCHAR(20) NOT NULL DEFAULT 'not_submitted'
);

CREATE INDEX IF NOT EXISTS idx_users_submission_status ON users(submission_status);
CREATE INDEX IF NOT EXISTS idx_users_is_alive ON users(is_alive);
