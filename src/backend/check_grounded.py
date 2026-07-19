"""
Why is a grounded aircraft still showing altitude / speed / fuel?

Run from src/backend WHILE uvicorn is running:
    python check_grounded.py

Answers three questions in order:
  1. Is the running main.py actually the fixed version?
  2. What does the database say about this aircraft?
  3. What do the two API endpoints actually return?
"""
import sqlite3, json, sys

try:
    import requests
except ImportError:
    print("pip install requests"); sys.exit(1)

API = "http://localhost:8000"

# ── 1. Is the running code the fixed version? ──
print("=" * 68)
print("1. IS THE RUNNING CODE THE FIXED VERSION?")
print("=" * 68)
try:
    src = open("main.py", encoding="utf-8").read()
except Exception as e:
    print(f"   Cannot read main.py: {e}"); sys.exit(1)

checks = [
    ("live_telemetry gated",  'if _is_airborne else None'),
    ("fuel gated",            'fuel_litres = None'),
    ("pak_fleet uses flight_telemetry", 'FROM flight_telemetry ft'),
    ("dynamic airborne timeout", 'def _airborne_timeout_min'),
]
all_ok = True
for name, needle in checks:
    ok = needle in src
    all_ok &= ok
    print(f"   [{'OK ' if ok else 'MISSING'}] {name}")

if not all_ok:
    print("\n   >>> main.py on disk is NOT the fixed version.")
    print("       Copy the latest main.py into src/backend, then restart uvicorn.")
    sys.exit(1)
print("\n   main.py on disk is correct. If the API still misbehaves,")
print("   uvicorn is running OLD code in memory -> restart it.\n")

# ── 2. Pick a grounded aircraft from the DB ──
print("=" * 68)
print("2. WHAT DOES THE DATABASE SAY?")
print("=" * 68)
conn = sqlite3.connect("aviation_data.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT f.tail_number, fs.status, fs.last_seen
    FROM fleet f LEFT JOIN fleet_status fs ON fs.tail_number = f.tail_number
    ORDER BY f.tail_number
""").fetchall()

grounded = [r for r in rows if (r["status"] or "grounded") != "airborne"]
airborne = [r for r in rows if (r["status"] or "") == "airborne"]
print(f"   fleet_status: {len(airborne)} airborne, {len(grounded)} grounded")

if not grounded:
    print("   No grounded aircraft to test. Try again later.")
    sys.exit(0)

target = grounded[0]["tail_number"]
print(f"   Testing grounded aircraft: {target}")
print(f"     status={grounded[0]['status']}  last_seen={grounded[0]['last_seen']}")

tel = conn.execute("""
    SELECT altitude, velocity, timestamp FROM flight_telemetry
    WHERE UPPER(TRIM(tail_number)) = (
        SELECT UPPER(TRIM(hex_code)) FROM fleet WHERE tail_number = ?)
    ORDER BY timestamp DESC LIMIT 1
""", (target,)).fetchone()
if tel:
    print(f"     last stored telemetry: alt={tel['altitude']} vel={tel['velocity']} at {tel['timestamp']}")
conn.close()

# ── 3. What do the endpoints return? ──
print()
print("=" * 68)
print("3. WHAT DO THE APIs ACTUALLY RETURN?")
print("=" * 68)

try:
    pf = requests.get(f"{API}/api/pak_fleet", timeout=20).json()
    me = next((p for p in pf["fleet"] if p["tail_number"] == target), None)
    print(f"\n   /api/pak_fleet  ->  {target}")
    if me:
        for k in ("status", "altitude", "velocity", "latitude", "longitude"):
            v = me.get(k)
            flag = ""
            if k != "status" and v is not None:
                flag = "   <-- SHOULD BE null FOR A GROUNDED AIRCRAFT"
            print(f"      {k:<10} = {v}{flag}")
    else:
        print("      aircraft not found in response")
except Exception as e:
    print(f"   pak_fleet failed: {e}")

try:
    an = requests.get(f"{API}/api/pak_analyze/{target}", timeout=60).json()
    print(f"\n   /api/pak_analyze/{target}")
    print(f"      is_airborne = {an.get('is_airborne')}")
    lt = an.get("live_telemetry") or {}
    for k in ("alt_m", "speed_ms", "vertical_rate"):
        v = lt.get(k)
        flag = "   <-- SHOULD BE null" if v is not None else ""
        print(f"      live_telemetry.{k:<14} = {v}{flag}")
    em = an.get("route_and_emissions") or {}
    for k in ("predicted_fuel_liters", "predicted_co2_kg"):
        v = em.get(k)
        flag = "   <-- SHOULD BE null" if v is not None else ""
        print(f"      {k:<26} = {v}{flag}")
    print(f"      basis = {em.get('basis')}")
except Exception as e:
    print(f"   pak_analyze failed: {e}")

print()
print("=" * 68)
print("VERDICT")
print("=" * 68)
print("""
  All values null, but browser still shows numbers
      -> frontend cache. Hard-refresh with Ctrl+Shift+R.

  API still returns numbers
      -> uvicorn is running old code in memory. Stop it fully (Ctrl+C)
         and start again. --reload does not always pick up every change.

  is_airborne = true for an aircraft you believe is parked
      -> it is inside the airborne timeout window and the system still
         considers it flying. That is a timing question, not a display bug.
""")