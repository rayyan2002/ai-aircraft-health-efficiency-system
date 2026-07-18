import sqlite3, os
conn = sqlite3.connect("../backend/aviation_data.db")

print("=== FLEET TABLE (44 planes) ===")
fleet = conn.execute("SELECT tail_number, aircraft_type, airline FROM fleet ORDER BY airline").fetchall()
for r in fleet:
    print(f"  {r[0]:<12} {r[1]:<22} {r[2]}")

print(f"\n=== TELEMETRY for fleet planes ===")
rows = conn.execute("""
    SELECT f.tail_number, f.airline, t.callsign, t.altitude, t.latitude, t.longitude
    FROM fleet f
    LEFT JOIN flight_telemetry t ON t.tail_number = f.tail_number
    WHERE t.id IS NOT NULL
    ORDER BY f.airline, f.tail_number
""").fetchall()

if rows:
    for r in rows:
        print(f"  {r[0]:<12} {r[1]:<12} callsign={r[2]:<10} alt={r[3]} lat={r[4]} lon={r[5]}")
else:
    print("  No telemetry yet for fleet planes — run fetch_opensky.py during peak hours")

conn.close()