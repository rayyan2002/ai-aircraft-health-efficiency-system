"""
AeroTwin — test the Flightradar24 API key BEFORE building the integration.

Usage (from src/backend):
    python test_fr24.py YOUR_API_KEY

It runs TWO cheap tests:
  1. A tiny bounding-box query (verifies the key works at all)
  2. A registration-filtered query for YOUR fleet (the credit-efficient way
     we will actually use — only your aircraft, not all 90 in the box)

It reports whether you get origin/destination and how many of your 44
aircraft are airborne right now.
"""
import sys
import json
import sqlite3
import urllib.request
import urllib.error

if len(sys.argv) < 2:
    print("Usage: python test_fr24.py YOUR_API_KEY")
    sys.exit(1)

KEY = sys.argv[1].strip()
BASE = "https://fr24api.flightradar24.com/api/live/flight-positions/full"

# FR24 expects the header this way. If it 401s we also try Bearer.
def call(url, use_bearer=False):
    headers = {
        "Accept": "application/json",
        "Accept-Version": "v1",
    }
    if use_bearer:
        headers["Authorization"] = f"Bearer {KEY}"
    else:
        headers["Authorization"] = f"Bearer {KEY}"
        headers["X-API-Key"] = KEY
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())


def try_call(url):
    try:
        return call(url, use_bearer=False), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # Is this an HTML page (maintenance / gateway) rather than a JSON API error?
        if "<html" in body.lower() or "planned maintenance" in body.lower():
            if "maintenance" in body.lower():
                return None, "FR24_MAINTENANCE"
            return None, "FR24_HTML_ERROR"
        # retry with bearer-only if auth failed
        if e.code in (401, 403):
            try:
                return call(url, use_bearer=True), None
            except urllib.error.HTTPError as e2:
                b2 = e2.read().decode()
                if "maintenance" in b2.lower():
                    return None, "FR24_MAINTENANCE"
                return None, f"HTTP {e2.code}: {b2[:300]}"
        return None, f"HTTP {e.code}: {body[:300]}"
    except Exception as e:
        return None, str(e)


print("=" * 66)
print("Flightradar24 API test")
print("=" * 66)

# ── Test 1: small bounding box (Pakistan core) ──
# bounds format: north,south,west,east
print("\n1. BOUNDING BOX (Pakistan) — verifies the key works")
url1 = f"{BASE}?bounds=37.0,23.5,60.5,77.5"
data, err = try_call(url1)
if err == "FR24_MAINTENANCE":
    print("   \u26a0\ufe0f  FR24 API is under PLANNED MAINTENANCE right now.")
    print("      This is NOT a problem with your key or your code.")
    print("      Wait 30\u201360 minutes and run this exact command again.")
    sys.exit(0)
elif err:
    print(f"   \u274c {err}")
    print("\n   401/403 (with a JSON error): key wrong or not activated.")
    print("   402: plan has no credits / not subscribed.")
    sys.exit(1)

flights = data.get("data") or data.get("flights") or []
print(f"   ✅ {len(flights)} flights returned")
if flights:
    f = flights[0]
    print("   Sample record fields:", ", ".join(list(f.keys())[:14]))

# ── Test 2: registration-filtered (the way we'll actually use it) ──
print("\n2. FLEET REGISTRATIONS — the credit-efficient query we will use")
try:
    conn = sqlite3.connect("aviation_data.db")
    regs = [r[0] for r in conn.execute(
        "SELECT tail_number FROM fleet WHERE tail_number IS NOT NULL"
    ).fetchall()]
    conn.close()
except Exception as e:
    print(f"   (couldn't read fleet from db: {e})")
    regs = []

if regs:
    # FR24 accepts a comma-separated registrations filter
    reg_param = ",".join(regs)
    url2 = f"{BASE}?registrations={urllib.parse.quote(reg_param)}"
    import urllib.parse
    url2 = f"{BASE}?registrations={urllib.parse.quote(reg_param)}"
    data2, err2 = try_call(url2)
    if err2:
        print(f"   ❌ {err2}")
        print("   (registration filter may not be on your plan — bbox still works)")
    else:
        fl2 = data2.get("data") or data2.get("flights") or []
        print(f"   ✅ {len(fl2)} of your 44 fleet aircraft are airborne right now")
        with_route = 0
        for f in fl2:
            reg = f.get("reg") or f.get("registration") or "?"
            orig = f.get("orig_iata") or f.get("origin") or f.get("orig") or "?"
            dest = f.get("dest_iata") or f.get("destination") or f.get("dest") or "?"
            cs   = f.get("callsign") or "?"
            if orig != "?" or dest != "?":
                with_route += 1
            print(f"      {reg:<9} {cs:<9} {orig} -> {dest}  "
                  f"alt={f.get('alt')}ft spd={f.get('gspeed') or f.get('speed')}")
        print(f"\n   {with_route}/{len(fl2)} have origin/destination "
              f"(the thing OpenSky CANNOT give)")

print()
print("=" * 66)
print("VERDICT")
print("=" * 66)
print("""
  If Test 1 worked -> key is valid, integration will work.
  If Test 2 showed origin/destination -> we get ROUTE data. This is the win.
  If Test 2 failed but Test 1 worked -> we'll query by bounding box and
     filter to your fleet in code (costs a little more credit, still fine).

  Tell me which of these happened and I'll wire the fetcher accordingly.
""")