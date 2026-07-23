import sqlite3

conn   = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS devices (
    device_id  TEXT PRIMARY KEY,
    public_key TEXT,
    challenge  TEXT,
    challenge_time INTEGER,
    last_seen  INTEGER,
    blocked    INTEGER DEFAULT 0,
    nickname   TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    device_id TEXT,
    token     TEXT,
    expiry    INTEGER,
    created   INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    event     TEXT,
    ip        TEXT,
    timestamp INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sensor_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT,
    temperature REAL,
    humidity    REAL,
    timestamp   INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS rate_limit (
    device_id TEXT,
    ip        TEXT,
    timestamp INTEGER
)
""")

# Upgrade existing DB safely
for col in [
    ("devices","blocked","INTEGER DEFAULT 0"),
    ("devices","nickname","TEXT"),
    ("devices","last_seen","INTEGER"),
    ("devices","challenge_time","INTEGER"),
    ("sessions","created","INTEGER"),
]:
    try: cursor.execute(f"ALTER TABLE {col[0]} ADD COLUMN {col[1]} {col[2]}")
    except: pass

# Default admin account (change password after first run!)
cursor.execute("INSERT OR IGNORE INTO admin VALUES ('admin','admin123')")

conn.commit()
conn.close()
print("Database ready!")
print("Tables: devices, sessions, logs, sensor_data, admin, rate_limit")
print("Default login => username: admin  password: admin123")