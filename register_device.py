import sqlite3
import sys

device_id = sys.argv[1] if len(sys.argv) > 1 else "ESP001"

try:
    with open(f"public_key_{device_id}.pem", "r") as f:
        public_key = f.read()
except FileNotFoundError:
    print(f"ERROR: public_key_{device_id}.pem not found!")
    print(f"Run first: python generate_keys.py {device_id}")
    exit(1)

conn = sqlite3.connect("database.db")
conn.execute(
    "INSERT OR REPLACE INTO devices (device_id, public_key) VALUES (?, ?)",
    (device_id, public_key)
)
conn.commit()

# Show all registered devices
devices = conn.execute("SELECT device_id FROM devices").fetchall()
conn.close()

print(f"{device_id} registered successfully!")
print("\nAll registered devices:")
for d in devices:
    print(f"  → {d[0]}")