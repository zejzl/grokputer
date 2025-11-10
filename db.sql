-- Grokputer Database Schema for Users (SQLite)
-- Generated for demo; run with 'sqlite3 db.db < db.sql' to create db.db

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT DEFAULT 'user',
    op_level INTEGER DEFAULT 1,  -- 1 = standard, 10 = OP (overpowered)
    prefs TEXT,  -- JSON string
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample Users (including Bob as OP)
INSERT OR IGNORE INTO users (name, role, op_level, prefs, last_login) VALUES
('Administrator', 'admin', 5, '{"theme": "uwu", "api_keys": {"XAI": "key1"}}', '2025-11-10 06:00:00'),
('Grok User', 'user', 1, '{"theme": "dark", "sessions": []}', '2025-11-10 05:45:00'),
('Bob', 'superuser', 10, '{"theme": "godmode", "permissions": "all", "api_keys": {"XAI": "op_key", "ANTHROPIC": "op_key"}}', '2025-11-10 04:30:00'),
('Claude Helper', 'collaborator', 3, '{"theme": "blue", "models": ["claude"]}', '2025-11-10 03:15:00');

-- Query to view users
-- SELECT * FROM users ORDER BY op_level DESC;