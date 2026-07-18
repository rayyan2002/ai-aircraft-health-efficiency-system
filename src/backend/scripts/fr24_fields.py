"""
FR24 — get the exact field names, cheaply and reliably.

Queries ONLY your fleet registrations (not a bounding box), so it costs a
fraction of the credits. Retries on transient network failures.

Usage (from src/backend):
    python fr24_fields.py YOUR_API_KEY
"""
import sys, json, time, sqlite3

try:
    import requests
except ImportError:
    print("Needs the 'requests' package:  pip install requests")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python fr24_fields.py YOUR_API_KEY")
    sys.exit(1)

KEY = sys.argv[1].strip()
BASE = "https://fr24api.flightradar24.com/api"

# Headers that WORK. Do NOT add X-API-Key — Cloudflare blocks that combination
# and returns an HTML page. A default Python user-agent also gets blocked.
HEADERS = {
    "Accept": "application/json",
    "Accept-Version": "v1",
    "User-Agent": "AeroTwin-FYP/1.0",
    "Authorization": f"Bearer {KEY}",
}

session = requests.Session()
session.headers.update(HEADERS)


def get(url, tries=4):
    """GET with retries — transient timeouts are common and not fatal."""
    for attempt in range(1, tries + 1):
        try:
            r = session.get(url, timeout=(10, 40))
            if r.status_code == 200:
                return r.json()
            print(f"  HTTP {r.status_code}: {r.text[:300]}")
            return None
        except requests.exceptions.RequestException as e:
            kind = type(e).__name__
            if attempt < tries:
                wait = attempt * 4
                print(f"  {kind} (attempt {attempt}/{tries}) — retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"  Network failed after {tries} attempts: {kind}")
                print("  Check your internet connection, then re-run.")
                return None
    return None


# ── credits before ──
print("Checking credit usage...")
u0 = get(f"{BASE}/usage")
if u0 is None:
    sys.exit(1)
before = sum(int(d.get("credits", 0)) for d in u0.get("data", []))
print(f"Credits used so far: {before}\n")

# ── fleet registrations ──
try:
    conn = sqlite3.connect("aviation_data.db")
    regs = [r[0] for r in conn.execute(
        "SELECT tail_number FROM fleet WHERE tail_number IS NOT NULL").fetchall()]
    conn.close()
except Exception as e:
    print(f"Could not read fleet: {e}")
    sys.exit(1)

print(f"Querying {len(regs)} fleet registrations (cheap — only our aircraft)")
data = get(f"{BASE}/live/flight-positions/full",)
# build with params so requests handles encoding
data = None
for attempt in range(1, 4):
    try:
        r = session.get(f"{BASE}/live/flight-positions/full",
                        params={"registrations": ",".join(regs)},
                        timeout=(10, 40))
        if r.status_code == 200:
            data = r.json()
            break
        print(f"  HTTP {r.status_code}: {r.text[:300]}")
        break
    except requests.exceptions.RequestException as e:
        if attempt < 3:
            print(f"  {type(e).__name__} — retrying...")
            time.sleep(attempt * 4)
        else:
            print("  Network failed. Re-run when the connection is stable.")

if data is None:
    sys.exit(1)

flights = data.get("data", [])
print("\n" + "=" * 66)
print(f"FLEET AIRCRAFT AIRBORNE RIGHT NOW: {len(flights)}")
print("=" * 66)

if flights:
    print("\n--- FULL RECORD (all field names) ---")
    print(json.dumps(flights[0], indent=2))
    print("\n--- ALL FLEET FLIGHTS ---")
    for f in flights:
        orig = f.get("orig_iata") or f.get("orig") or "?"
        dest = f.get("dest_iata") or f.get("dest") or "?"
        print(f"  {str(f.get('reg')):<9} {str(f.get('callsign')):<9} "
              f"hex={str(f.get('hex')):<8} {orig} -> {dest}  "
              f"alt={f.get('alt')}ft spd={f.get('gspeed')}kt")
else:
    print("\nNone of your 44 aircraft are airborne at this moment.")
    print("Re-run in 20 minutes.")

# ── credits after ──
u1 = get(f"{BASE}/usage")
if u1:
    after = sum(int(d.get("credits", 0)) for d in u1.get("data", []))
    print("\n" + "=" * 66)
    print(f"CREDIT COST OF THIS QUERY: {after - before}")
    print(f"Total used: {after}")
    print("=" * 66)
    print("\n  For comparison: one Pakistan BOUNDING BOX query cost 160 credits.")
    print("  This is why the integration queries registrations, never a bbox.")