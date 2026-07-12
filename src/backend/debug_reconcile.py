"""
AeroTwin — why isn't reconciliation marking aircraft airborne?

check_hex.py says 14 fleet aircraft are flying.
The Home page says 1 is airborne.
This script replicates the reconcile logic EXACTLY and shows where it diverges.

Run from src/backend:
    python debug_reconcile.py
"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("aviation_data.db")
conn.row_factory = sqlite3.Row

print("=" * 72)
print("A. TIME SANITY CHECK  (timezone bugs hide here)")
print("=" * 72)
py_now = datetime.now()
sq_now = conn.execute("SELECT datetime('now')").fetchone()[0]
sq_local = conn.execute("SELECT datetime('now','localtime')").fetchone()[0]
print(f"  Python datetime.now()        : {py_now.strftime('%Y-%m-%d %H:%M:%S')}   (local)")
print(f"  SQLite  datetime('now')      : {sq_now}   (UTC)")
print(f"  SQLite  datetime('now','local'): {sq_local}")
newest = conn.execute("SELECT MAX(timestamp) FROM flight_telemetry").fetchone()[0]
print(f"  Newest flight_telemetry row  : {newest}")
print()
print("  ^ If the newest row is close to the PYTHON time, timestamps are LOCAL.")
print("    If it's close to the SQLite UTC time, they are UTC.")

print()
print("=" * 72)
print("B. WHAT RECONCILE SEES  (exact same query as main.py)")
print("=" * 72)
cutoff = (datetime.now() - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
print(f"  cutoff = {cutoff}")

live_rows = conn.execute("""
    SELECT tail_number AS hex, callsign, MAX(timestamp) AS last_seen
    FROM flight_telemetry
    WHERE timestamp >= ?
    GROUP BY tail_number
""", (cutoff,)).fetchall()
print(f"  Rows in window: {len(live_rows)}")

fleet_rows = conn.execute(
    "SELECT tail_number, hex_code FROM fleet WHERE hex_code IS NOT NULL"
).fetchall()
hex_to_fleet = {(r["hex_code"] or "").strip().upper(): r["tail_number"] for r in fleet_rows}
print(f"  Fleet hex codes loaded: {len(hex_to_fleet)}")

live_fleet = {}
for r in live_rows:
    hx = (r["hex"] or "").strip().upper()
    if hx in hex_to_fleet:
        live_fleet[hex_to_fleet[hx]] = (r["callsign"], r["last_seen"])

print(f"\n  >>> RECONCILE WOULD MARK {len(live_fleet)} AIRCRAFT AIRBORNE:")
for tail, (cs, seen) in sorted(live_fleet.items()):
    print(f"        {tail:<9} {cs:<9} last_seen={seen}")
if not live_fleet:
    print("        (none)")

print()
print("=" * 72)
print("C. WHAT fleet_status ACTUALLY SAYS RIGHT NOW")
print("=" * 72)
fs = conn.execute("""
    SELECT tail_number, status, current_callsign, last_seen
    FROM fleet_status
    WHERE status = 'airborne'
    ORDER BY tail_number
""").fetchall()
print(f"  Rows marked 'airborne': {len(fs)}")
for r in fs:
    print(f"        {r['tail_number']:<9} {str(r['current_callsign']):<9} last_seen={r['last_seen']}")
if not fs:
    print("        (none)")

print()
print("=" * 72)
print("D. THE FRESHNESS FILTER  (pak_fleet / fleet_status endpoints)")
print("=" * 72)
print(f"  fresh cutoff = {cutoff}")
print("  An 'airborne' row is only shown if last_seen >= that cutoff.\n")
for r in fs:
    ls = r["last_seen"]
    ok = bool(ls) and str(ls) >= cutoff
    verdict = "PASSES -> shown airborne" if ok else "STALE  -> reported grounded"
    print(f"        {r['tail_number']:<9} last_seen={str(ls):<28} {verdict}")

print()
print("=" * 72)
print("E. DIAGNOSIS")
print("=" * 72)
would = len(live_fleet)
marked = len(fs)
fresh_ok = sum(1 for r in fs if r["last_seen"] and str(r["last_seen"]) >= cutoff)

print(f"  Reconcile SHOULD mark airborne : {would}")
print(f"  fleet_status rows marked       : {marked}")
print(f"  ...of which pass freshness      : {fresh_ok}   <-- what the UI shows")
print()

if would > 0 and marked == 0:
    print("  => fleet_status is EMPTY of airborne rows even though aircraft are")
    print("     flying. The reconcile function is not running, or is erroring.")
    print("     Check the uvicorn log for 'reconcile:' errors, and confirm the")
    print("     pipeline has completed a cycle since you restarted.")
elif would > marked:
    print(f"  => Reconcile should mark {would} but only {marked} are marked.")
    print("     The pipeline likely has not run since the hex codes were added.")
    print("     Restart uvicorn and WAIT for one full pipeline cycle.")
elif marked > fresh_ok:
    print(f"  => {marked - fresh_ok} airborne row(s) are being hidden as STALE.")
    print("     Their last_seen is older than the 30-minute window.")
    print("     This points at a TIMESTAMP FORMAT or TIMEZONE mismatch —")
    print("     compare section A: are stored timestamps local or UTC?")
elif would == fresh_ok and would > 0:
    print("  => Everything agrees. The UI should be showing", fresh_ok, "airborne.")
    print("     If it shows fewer, the frontend is caching — hard-refresh (Ctrl+F5).")
else:
    print("  => No fleet aircraft are currently airborne. Counts are correct.")
