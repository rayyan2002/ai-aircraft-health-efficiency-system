"""
Verify that fuel / CO2 figures actually vary between flights.

Run from src/backend:
    python check_fuel.py
"""
import sqlite3

conn = sqlite3.connect("aviation_data.db")
conn.row_factory = sqlite3.Row

# Read the real schema rather than assuming column names.
cols = [r["name"] for r in conn.execute("PRAGMA table_info(flight_history)")]
print("flight_history columns:", ", ".join(cols))
print()


def pick(*candidates):
    """Return the first column that actually exists."""
    for c in candidates:
        if c in cols:
            return c
    return None


c_tail = pick("tail_number", "aircraft", "registration")
c_call = pick("callsign", "flight_number", "current_callsign", "flight")
c_fuel = pick("total_fuel_liters", "fuel_liters", "fuel_consumed", "fuel")
c_co2  = pick("co2_kg", "co2_emissions", "co2")
c_time = pick("landing_time", "arrival_time", "timestamp", "landed_at", "created_at")

print("=" * 72)
print("RECENT LANDINGS — fuel and CO2 per flight")
print("=" * 72)

if not c_fuel:
    print("  No fuel column found in flight_history.")
else:
    sel = ", ".join(x for x in [c_tail, c_call, c_fuel, c_co2, c_time] if x)
    order = "id DESC" if "id" in cols else f"{c_time} DESC"
    rows = conn.execute(f"SELECT {sel} FROM flight_history ORDER BY {order} LIMIT 20").fetchall()

    if not rows:
        print("  No landings logged yet. Wait for a cycle where an aircraft lands.")
    else:
        hdr = f"  {'Tail':<9} {'Callsign':<10} {'Fuel (L)':>11} {'CO2 (kg)':>11}  When"
        print(hdr)
        print("  " + "-" * 68)
        fuels = []
        for r in rows:
            f = r[c_fuel] or 0
            fuels.append(float(f))
            tail = r[c_tail] if c_tail else "?"
            call = r[c_call] if c_call else "?"
            co2  = r[c_co2] if c_co2 else 0
            when = str(r[c_time])[:19] if c_time else ""
            print(f"  {str(tail):<9} {str(call):<10} {float(f):>11,.1f} "
                  f"{float(co2 or 0):>11,.1f}  {when}")

        uniq = len(set(round(x, 1) for x in fuels))
        print()
        print(f"  Distinct fuel values: {uniq} out of {len(fuels)} flights")
        if uniq == 1:
            print("  >>> ALL IDENTICAL — the duration fix is NOT working.")
        elif uniq < max(2, len(fuels) // 2):
            print("  >>> Many repeats — aircraft seen only once use a default duration.")
        else:
            print("  >>> Values vary per flight. Working as intended.")

# Telemetry depth drives the duration calculation.
print()
print("=" * 72)
print("TELEMETRY DEPTH PER AIRBORNE FLIGHT (drives duration -> fuel)")
print("=" * 72)
try:
    rows2 = conn.execute("""
        SELECT fs.tail_number, fs.current_callsign AS cs,
               COUNT(ft.id) AS n,
               MIN(ft.timestamp) AS t0, MAX(ft.timestamp) AS t1
        FROM fleet_status fs
        JOIN fleet f ON f.tail_number = fs.tail_number
        LEFT JOIN flight_telemetry ft
               ON UPPER(TRIM(ft.tail_number)) = UPPER(TRIM(f.hex_code))
              AND ft.callsign = fs.current_callsign
        WHERE fs.status = 'airborne'
        GROUP BY fs.tail_number
        ORDER BY n DESC
    """).fetchall()

    if rows2:
        print(f"  {'Tail':<9} {'Callsign':<10} {'Points':>7}   First -> last seen")
        print("  " + "-" * 68)
        for r in rows2:
            print(f"  {r['tail_number']:<9} {str(r['cs']):<10} {r['n']:>7}   "
                  f"{str(r['t0'])[:19]} -> {str(r['t1'])[:19]}")
        print()
        print("  More points = longer observed flight = higher fuel estimate.")
        print("  An aircraft seen only ONCE has no measurable duration and")
        print("  falls back to a single polling interval.")
    else:
        print("  No airborne aircraft right now.")
except Exception as e:
    print(f"  (could not compute: {e})")

conn.close()