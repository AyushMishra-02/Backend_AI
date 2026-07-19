CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Optional stretch goal: Index creation moved to seed_and_explain.py for EXPLAIN ANALYZE demonstration
-- CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

