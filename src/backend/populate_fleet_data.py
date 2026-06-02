"""
populate_fleet_data.py
======================
Populates age_years, total_flight_hours, total_cycles, engine_type
for all 44 fleet aircraft based on real verified data.

Sources:
- Delivery dates from FlightRadar24 / planespotters.net (as seen in screenshots)
- Flight hours estimated from age × average annual utilization
  (PIA ~3000 hrs/yr, AirBlue ~3500 hrs/yr, AirSial/FlyJinnah ~3200 hrs/yr)

Run once from src/backend/:
    python populate_fleet_data.py
"""

import sqlite3, os
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "aviation_data.db")

# Real delivery/age data from planespotters.net screenshots
# Format: tail_number -> (age_years, engine_type, annual_hours)
FLEET_DATA = {
    # ── PIA A320 family ──
    "AP-BLB": (8.5,  "CFM56-5B4", 3000),
    "AP-BLC": (8.5,  "CFM56-5B4", 3000),
    "AP-BLS": (8.0,  "CFM56-5B4", 3000),
    "AP-BLZ": (7.5,  "CFM56-5B6", 3000),
    "AP-BMV": (6.0,  "CFM56-5B4", 3000),
    "AP-BMX": (6.0,  "CFM56-5B4", 3000),
    "AP-BMY": (6.0,  "CFM56-5B4", 3000),
    "AP-BOK": (4.5,  "CFM56-5B4", 3000),
    "AP-BOL": (4.5,  "CFM56-5B4", 3000),
    "AP-BOM": (4.0,  "CFM56-5B4", 3000),
    "AP-BON": (4.0,  "CFM56-5B4", 3000),
    # ── PIA B777 ──
    "AP-BGK": (18.0, "GE90-94B",  4500),
    "AP-BHX": (16.0, "GE90-94B",  4500),
    "AP-BMH": (11.0, "GE90-94B",  4500),
    "AP-BGY": (17.0, "GE90-110B", 4500),
    "AP-BGZ": (17.0, "GE90-110B", 4500),
    "AP-BHV": (13.0, "GE90-115B", 4500),
    "AP-BMS": (12.0, "GE90-115B", 4500),
    # ── AirBlue A320 ──
    "AP-BNU": (15.7, "CFM56-5B4", 3500),
    "AP-BNV": (15.8, "CFM56-5B4", 3500),
    "AP-EDG": (12.4, "CFM56-5B4", 3500),
    "AP-EDH": (12.3, "CFM56-5B4", 3500),
    # ── AirBlue A321 ──
    "AP-BMM": (12.2, "CFM56-5B3", 3500),
    "AP-BMN": (12.2, "CFM56-5B3", 3500),
    "AP-BMP": (12.0, "CFM56-5B3", 3500),
    "AP-BMW": (9.9,  "CFM56-5B3", 3500),
    "AP-BOD": (5.6,  "CFM56-5B3", 3500),
    # ── FlyJinnah A320 ──
    "AP-BOO": (6.9,  "CFM56-5B4", 3200),
    "AP-BOP": (7.2,  "CFM56-5B4", 3200),
    "AP-BOQ": (7.0,  "CFM56-5B4", 3200),
    "AP-BOV": (15.4, "CFM56-5B4", 3200),
    "AP-BOZ": (15.3, "CFM56-5B4", 3200),
    "AP-BPE": (12.6, "CFM56-5B4", 3200),
    "AP-BPL": (12.9, "CFM56-5B4", 3200),
    "AP-BPM": (12.8, "CFM56-5B4", 3200),
    # ── AirSial A320 ──
    "AP-BOA": (21.8, "CFM56-5B4", 3200),
    "AP-BOB": (17.9, "CFM56-5B4", 3200),
    "AP-BOR": (14.4, "CFM56-5B4", 3200),
    "AP-BOS": (13.3, "CFM56-5B4", 3200),
    "AP-BPF": (16.4, "CFM56-5B4", 3200),
    "AP-BPG": (16.3, "CFM56-5B4", 3200),
    "AP-BPH": (15.6, "CFM56-5B4", 3200),
    "AP-BPI": (15.5, "CFM56-5B4", 3200),
    "AP-BPJ": (14.0, "CFM56-5B4", 3200),
}

conn    = sqlite3.connect(DB_PATH)
updated = 0

for tail, (age, engine, annual_hrs) in FLEET_DATA.items():
    total_hours  = round(age * annual_hrs)
    total_cycles = round(total_hours / 1.8)  # avg ~1.8 hrs per cycle for domestic

    conn.execute("""
        UPDATE fleet SET
            age_years          = ?,
            engine_type        = ?,
            total_flight_hours = ?,
            total_cycles       = ?
        WHERE tail_number = ?
    """, (age, engine, total_hours, total_cycles, tail))
    updated += 1

conn.commit()

# Verify
print(f"✅ Updated {updated} aircraft\n")
rows = conn.execute("""
    SELECT tail_number, airline, age_years, engine_type,
           total_flight_hours, total_cycles
    FROM fleet ORDER BY airline, age_years DESC
""").fetchall()

print(f"{'Tail':<12} {'Airline':<12} {'Age':>5} {'Engine':<16} {'Hours':>7} {'Cycles':>7}")
print("-" * 65)
for r in rows:
    print(f"{r[0]:<12} {(r[1] or ''):<12} {(r[2] or 0):>5.1f} {(r[3] or ''):<16} {(r[4] or 0):>7} {(r[5] or 0):>7}")

conn.close()