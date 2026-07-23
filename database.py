import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE devices ADD COLUMN challenge TEXT")
conn.commit()
conn.close()

print("Updated database")