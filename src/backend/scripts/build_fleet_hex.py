"""
build_fleet_hex.py
==================
1. Looks up ICAO24 hex codes for all 44 fleet planes via hexdb.io (free API)
2. Saves hex codes to fleet table
3. Creates pakistan_telemetry table (separate from flight_telemetry)

Run once from src/scripts/:
    python build_fleet_hex.py
"""

import requests
import sqlite3
import os
import time

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR    = os.path.dirname(SCRIPT_DIR)
DB_PATH    = os.path.join(SRC_DIR, "backend", "aviation_data.db")

conn = sqlite3.connect(DB_PATH)

# ──────────────────────────────────────────────────────────────
# STEP 1 — Add hex_code column to fleet table if missing
# ──────────────────────────────────────────────────────────────
print("[1/3] Adding hex_code column to fleet table...")
try:
    conn.execute("ALTER TABLE fleet ADD COLUMN hex_code VARCHAR")
    print("  ✅ hex_code column added")
except:
    print("  ℹ️  hex_code column already exists")

# ──────────────────────────────────────────────────────────────
# STEP 2 — Create pakistan_telemetry table (separate from flight_telemetry)
# ──────────────────────────────────────────────────────────────
print("\n[2/3] Creating pakistan_telemetry table...")
conn.execute("""
    CREATE TABLE IF NOT EXISTS pakistan_telemetry (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        tail_number  VARCHAR NOT NULL,
        callsign     VARCHAR,
        airline      VARCHAR,
        altitude     FLOAT,
        velocity     FLOAT,
        latitude     FLOAT,
        longitude    FLOAT,
        anomaly_flag INTEGER DEFAULT 0,
        timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()
print("  ✅ pakistan_telemetry table ready")

# ──────────────────────────────────────────────────────────────
# STEP 3 — Lookup hex codes for all fleet planes via hexdb.io
# ──────────────────────────────────────────────────────────────
print("\n[3/3] Looking up ICAO24 hex codes via hexdb.io...")

fleet = conn.execute(
    "SELECT tail_number, aircraft_type, airline FROM fleet ORDER BY airline, tail_number"
).fetchall()

found    = 0
missing  = 0

for tail, aircraft_type, airline in fleet:
    # hexdb.io accepts registration directly
    url = f"https://hexdb.io/reg-hex?reg={tail.replace('-', '')}"

    try:
        resp = requests.get(url, timeout=10)

        if resp.status_code == 200 and resp.text.strip():
            hex_code = resp.text.strip().upper()
            conn.execute(
                "UPDATE fleet SET hex_code=? WHERE tail_number=?",
                (hex_code, tail)
            )
            print(f"  ✅ {tail:<12} {airline:<12} → {hex_code}")
            found += 1
        else:
            # Try alternative format with dash
            url2 = f"https://hexdb.io/reg-hex?reg={tail}"
            resp2 = requests.get(url2, timeout=10)
            if resp2.status_code == 200 and resp2.text.strip():
                hex_code = resp2.text.strip().upper()
                conn.execute(
                    "UPDATE fleet SET hex_code=? WHERE tail_number=?",
                    (hex_code, tail)
                )
                print(f"  ✅ {tail:<12} {airline:<12} → {hex_code}")
                found += 1
            else:
                print(f"  ❌ {tail:<12} {airline:<12} → not found")
                missing += 1

    except Exception as e:
        print(f"  ⚠️ {tail:<12} error: {e}")
        missing += 1

    # Be polite to the free API — small delay
    time.sleep(0.3)

conn.commit()
conn.close()

print(f"\n{'='*50}")
print(f"  Hex codes found  : {found}")
print(f"  Not found        : {missing}")
print(f"  pakistan_telemetry table: ready")
print(f"{'='*50}")
print("\nNext: update fetch_opensky.py to use pakistan_telemetry table")