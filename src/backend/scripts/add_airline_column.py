import sqlite3, os

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(SRC_DIR, "backend", "aviation_data.db")

conn = sqlite3.connect(DB_PATH)

# Add airline column
try:
    conn.execute("ALTER TABLE fleet ADD COLUMN airline VARCHAR")
    print("✅ Added airline column")
except:
    print("ℹ️  airline column already exists")

# Airline mapping
AIRLINE_MAP = {
    "AP-BLB": "PIA", "AP-BLC": "PIA", "AP-BLS": "PIA", "AP-BLZ": "PIA",
    "AP-BMV": "PIA", "AP-BMX": "PIA", "AP-BMY": "PIA", "AP-BOK": "PIA",
    "AP-BOL": "PIA", "AP-BOM": "PIA", "AP-BON": "PIA", "AP-BGK": "PIA",
    "AP-BHX": "PIA", "AP-BMH": "PIA", "AP-BGY": "PIA", "AP-BGZ": "PIA",
    "AP-BHV": "PIA", "AP-BMS": "PIA",
    "AP-BNU": "AirBlue", "AP-BNV": "AirBlue", "AP-EDG": "AirBlue",
    "AP-EDH": "AirBlue", "AP-BMM": "AirBlue", "AP-BMN": "AirBlue",
    "AP-BMP": "AirBlue", "AP-BMW": "AirBlue", "AP-BOD": "AirBlue",
    "AP-BOO": "FlyJinnah", "AP-BOP": "FlyJinnah", "AP-BOQ": "FlyJinnah",
    "AP-BOV": "FlyJinnah", "AP-BOZ": "FlyJinnah", "AP-BPE": "FlyJinnah",
    "AP-BPL": "FlyJinnah", "AP-BPM": "FlyJinnah",
    "AP-BOA": "AirSial", "AP-BOB": "AirSial", "AP-BOR": "AirSial",
    "AP-BOS": "AirSial", "AP-BPF": "AirSial", "AP-BPG": "AirSial",
    "AP-BPH": "AirSial", "AP-BPI": "AirSial", "AP-BPJ": "AirSial",
}

for tail, airline in AIRLINE_MAP.items():
    conn.execute("UPDATE fleet SET airline=? WHERE tail_number=?", (airline, tail))

conn.commit()

# Verify
print("\n=== UPDATED FLEET TABLE ===")
rows = conn.execute("SELECT tail_number, aircraft_type, airline FROM fleet ORDER BY airline, tail_number").fetchall()
for r in rows:
    print(f"  {r[0]:<12} {r[1]:<22} {r[2]}")
print(f"\n  Total: {len(rows)} aircraft")

conn.close()