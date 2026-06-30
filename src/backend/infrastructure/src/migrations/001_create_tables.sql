-- 001_create_tables.sql – create todos and settings tables
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'Medium',
    status TEXT NOT NULL DEFAULT 'Pending'
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
