"""
AeroTwin — write all verified hex codes into the fleet table.

Hex codes verified individually on Flightradar24 (Mode S field).
They form a contiguous Pakistan CAA allocation block, which cross-validates
every value:

    AP-BPE  760A05   FlyJinnah
    AP-BPF  760A06   AirSial
    AP-BPG  760A07   AirSial     (seen live as SIF124)
    AP-BPH  760A08   AirSial
    AP-BPI  760A09   AirSial
    AP-BPJ  760A0A   AirSial     (seen live as SIF123)
    AP-BPK  760A0B   -- not in fleet
    AP-BPL  760A0C   FlyJinnah
    AP-BPM  760A0D   FlyJinnah   (seen live as FJL672)
    AP-BPN  760A0E   AirSial     (seen live as SIF722) -- not in fleet

Leased Air Arabia aircraft flying Fly Jinnah callsigns (correctly NOT fleet):
    A6-AQJ  89666A   (FJL870)
    A6-AQQ  8966B0   (FJL866)

Run from src/backend:
    python apply_hex.py
"""
import sqlite3

VERIFIED = [
    ("AP-BPE", "760A05", "FlyJinnah"),
    ("AP-BPF", "760A06", "AirSial"),
    ("AP-BPG", "760A07", "AirSial"),
    ("AP-BPH", "760A08", "AirSial"),
    ("AP-BPI", "760A09", "AirSial"),
    ("AP-BPJ", "760A0A", "AirSial"),
    ("AP-BPL", "760A0C", "FlyJinnah"),
    ("AP-BPM", "760A0D", "FlyJinnah"),
    ("AP-BPN", "760A0E", "AirSial"),   # likely not in fleet — handled gracefully
]

conn = sqlite3.connect("aviation_data.db")
conn.row_factory = sqlite3.Row

print("=" * 68)
print("Applying verified hex codes (source: Flightradar24 Mode S)")
print("=" * 68)

written, skipped, absent = 0, 0, []

for tail, hx, airline in VERIFIED:
    row = conn.execute(
        "SELECT tail_number, hex_code, airline FROM fleet WHERE tail_number = ?", (tail,)
    ).fetchone()

    if not row:
        absent.append((tail, hx, airline))
        continue

    if row["hex_code"] and row["hex_code"].strip():
        print(f"  --  {tail} already has hex {row['hex_code']} — left alone")
        skipped += 1
        continue

    conn.execute("UPDATE fleet SET hex_code = ? WHERE tail_number = ?", (hx, tail))
    print(f"  OK  {tail}  ({row['airline']:<10}) <- hex {hx}")
    written += 1

conn.commit()

print(f"\n  Wrote {written} new hex codes. ({skipped} already had one.)")

if absent:
    print()
    print("  Not in the fleet table (real aircraft, but not part of your 44):")
    for tail, hx, airline in absent:
        print(f"     {tail}  hex={hx}  {airline}")
    print("  Left out deliberately — adding an aircraft without real engine-cycle")
    print("  history would make its RUL prediction meaningless.")

print()
print("=" * 68)
print("FLEET HEX COVERAGE")
print("=" * 68)
total = conn.execute("SELECT COUNT(*) FROM fleet").fetchone()[0]
have = conn.execute(
    "SELECT COUNT(*) FROM fleet WHERE hex_code IS NOT NULL AND TRIM(hex_code) <> ''"
).fetchone()[0]
print(f"   {have} of {total} aircraft have a hex code   ({have*100//total}%)")

still = conn.execute("""
    SELECT tail_number, airline FROM fleet
    WHERE hex_code IS NULL OR TRIM(hex_code) = ''
    ORDER BY airline, tail_number
""").fetchall()

if still:
    print(f"\n   Still missing ({len(still)}):")
    for r in still:
        print(f"     {r['tail_number']:<9} {r['airline']}")
else:
    print("\n   ✅ Every fleet aircraft can now be matched to a live flight.")

# Sanity check: no duplicate hex codes
dupes = conn.execute("""
    SELECT hex_code, COUNT(*) n, GROUP_CONCAT(tail_number) tails
    FROM fleet
    WHERE hex_code IS NOT NULL AND TRIM(hex_code) <> ''
    GROUP BY UPPER(TRIM(hex_code)) HAVING n > 1
""").fetchall()
if dupes:
    print("\n   ⚠️  DUPLICATE hex codes found — two aircraft cannot share one:")
    for d in dupes:
        print(f"     {d['hex_code']}  ->  {d['tails']}")
else:
    print("   No duplicate hex codes. Every code maps to exactly one airframe.")

print("\n   Restart uvicorn to pick up the changes.")
conn.close()