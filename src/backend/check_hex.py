"""
AeroTwin diagnostic: why aren't live flights matching the fleet?

Run from src/backend:
    python check_hex.py
"""
import sqlite3

conn = sqlite3.connect("aviation_data.db")
conn.row_factory = sqlite3.Row

print("=" * 70)
print("1. LIVE FLIGHTS (last 30 minutes, from OpenSky)")
print("=" * 70)
live = conn.execute("""
    SELECT DISTINCT tail_number AS hex, callsign
    FROM flight_telemetry
    WHERE timestamp >= datetime('now', '-30 minutes')
""").fetchall()

if not live:
    print("  (none — no recent OpenSky rows)")
for r in live:
    print(f"  hex={r['hex']:<10} callsign={r['callsign']}")

print()
print("=" * 70)
print("2. FLEET HEX CODE HEALTH")
print("=" * 70)
total, missing = conn.execute("""
    SELECT COUNT(*),
           SUM(CASE WHEN hex_code IS NULL OR TRIM(hex_code) = '' THEN 1 ELSE 0 END)
    FROM fleet
""").fetchone()
print(f"  Total fleet aircraft : {total}")
print(f"  Missing hex_code     : {missing}")
if missing:
    print("  ^^ These can NEVER be matched to a live flight!")
    for r in conn.execute("SELECT tail_number, airline FROM fleet WHERE hex_code IS NULL OR TRIM(hex_code)=''"):
        print(f"       {r['tail_number']} ({r['airline']})")

print()
print("=" * 70)
print("3. THE REAL TEST — does each live hex match a fleet aircraft?")
print("=" * 70)
matched = 0
for r in live:
    hx = (r["hex"] or "").strip().upper()
    hit = conn.execute(
        "SELECT tail_number, airline FROM fleet WHERE UPPER(TRIM(hex_code)) = ?",
        (hx,)
    ).fetchone()
    if hit:
        matched += 1
        print(f"  ✅ {r['callsign']:<10} hex={hx:<8} -> {hit['tail_number']} ({hit['airline']})")
    else:
        print(f"  ❌ {r['callsign']:<10} hex={hx:<8} -> NOT IN FLEET TABLE")

print()
print(f"  Matched {matched} of {len(live)} live flights to fleet aircraft.")

print()
print("=" * 70)
print("4. VERDICT")
print("=" * 70)
if not live:
    print("  No live data. Nothing to diagnose right now.")
elif matched == len(live):
    print("  All live flights matched. Counts should agree across pages.")
elif matched == 0 and missing == 0:
    print("  Live flights exist and fleet has hex codes, but NONE match.")
    print("  => Likely a FORMAT problem (case, spacing, or wrong hex values).")
    print("  Compare the hex strings above against your fleet's hex_code column.")
else:
    print(f"  {len(live) - matched} live flight(s) are operated by aircraft that")
    print("  are NOT in your 44-aircraft fleet table.")
    print("  => This is EXPECTED if the real airline fleet is bigger than 44.")
    print("     Pakistani carriers operate more aircraft than are seeded here.")
    print("     The counts are then CORRECT, just confusingly presented.")

print()
print("  Sample of fleet hex codes for eyeball comparison:")
for r in conn.execute("SELECT tail_number, hex_code, airline FROM fleet WHERE hex_code IS NOT NULL LIMIT 8"):
    print(f"       {r['tail_number']:<8} hex={r['hex_code']:<8} {r['airline']}")

conn.close()