"""
migrate_db.py — fixes three schema issues:
1. maintenance_records missing columns (component, location, performed_at)
2. fleet_status missing columns (departure_airport, arrival_airport)
3. pakistan_telemetry missing departure_airport/arrival_airport columns

Run once from src/backend/:
    python migrate_db.py
"""
import sqlite3, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "aviation_data.db")

conn = sqlite3.connect(DB_PATH)

print("🔧 Running DB migration...\n")

# ── Helper ──
def add_column(table, col, col_type, default=None):
    try:
        if default is not None:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT '{default}'")
        else:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"  ✅ Added {table}.{col}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"  ℹ️  {table}.{col} already exists")
        else:
            print(f"  ❌ {table}.{col} — {e}")

# ── 1. Drop and recreate maintenance_records with correct schema ──
print("[1/3] Fixing maintenance_records table...")
conn.execute("DROP TABLE IF EXISTS maintenance_records")
conn.execute("""
    CREATE TABLE maintenance_records (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        tail_number      TEXT NOT NULL,
        component        TEXT,
        maintenance_type TEXT,
        location         TEXT,
        notes            TEXT,
        performed_at     TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")
print("  ✅ maintenance_records recreated with correct schema")

# ── 2. Fix fleet_status columns ──
print("\n[2/3] Fixing fleet_status table...")
add_column("fleet_status", "departure_airport", "TEXT")
add_column("fleet_status", "arrival_airport",   "TEXT")
add_column("fleet_status", "current_callsign",  "TEXT")
add_column("fleet_status", "last_flight_id",    "INTEGER")

# ── 3. Fix pakistan_telemetry columns ──
print("\n[3/3] Fixing pakistan_telemetry table...")
add_column("pakistan_telemetry", "departure_airport", "TEXT")
add_column("pakistan_telemetry", "arrival_airport",   "TEXT")

conn.commit()
conn.close()

print("\n✅ Migration complete. Restart uvicorn.")