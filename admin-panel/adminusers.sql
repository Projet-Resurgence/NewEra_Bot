CREATE TABLE IF NOT EXISTS AdminUsers (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(200) NOT NULL,
    is_admin BOOLEAN DEFAULT 0 NOT NULL,
    can_manage_users BOOLEAN DEFAULT 0 NOT NULL,
    created_at TEXT,
    last_login TEXT,
    is_active BOOLEAN DEFAULT 1 NOT NULL
)