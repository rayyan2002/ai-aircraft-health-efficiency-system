"""
AeroTwin — test the AirLabs key BEFORE trusting it in a demo.

Usage (from src/backend):
    python test_airlabs.py YOUR_API_KEY

Checks the three things that actually matter:
    1. Does it return flights over Pakistan?
    2. Does it give origin/destination (the thing OpenSky cannot)?
    3. Do the hex codes match OUR 44 fleet aircraft?
"""
import sys
import sqlite3
import json
import urllib.request
import urllib.parse

if len(sys.argv) < 2:
    print("Usage: python test_airlabs.py YOUR_API_KEY")
    sys.exit(1)

KEY = sys.argv[1].strip()
BBOX = "23.0,60.0,37.5,78.0"          # lat_min,lng_min,lat_max,lng_max — Pakistan

url = "https://airlabs.co/api/v9/flights?" + urllib.parse.urlencode({
    "api_key": KEY,
    "bbox": BBOX,
})

print("=" * 68)
print("AirLabs test — Pakistan airspace")
print("=" * 68)

try:
    with urllib.request.urlopen(url, timeout=25) as r:
        data = json.loads(r.read().decode())
except Exception as e:
    print(f"\n❌ Request failed: {e}")
    sys.exit(1)

if data.get("error"):
    print(f"\n❌ API error: {data['error']}")
    sys.exit(1)

flights = data.get("response") or []
print(f"\n1. FLIGHTS RETURNED: {len(flights)}")
if not flights:
    print("   ❌ No flights. Check the key and your plan's coverage.")
    sys.exit(1)

with_route = [f for f in flights if f.get("dep_iata") or f.get("arr_iata")]
with_reg   = [f for f in flights if f.get("reg_number")]
with_hex   = [f for f in flights if f.get("hex")]

print(f"\n2. DATA QUALITY")
print(f"   with origin/destination : {len(with_route)} / {len(flights)}   <-- the thing OpenSky CANNOT give")
print(f"   with registration       : {len(with_reg)} / {len(flights)}")
print(f"   with hex code           : {len(with_hex)} / {len(flights)}")

print("\n   Sample flights:")
for f in flights[:6]:
    dep = f.get("dep_iata") or "?"
    arr = f.get("arr_iata") or "?"
    print(f"     {str(f.get('flight_iata') or f.get('flight_icao')):<9} "
          f"{str(f.get('reg_number')):<9} hex={str(f.get('hex')):<8} "
          f"{dep} -> {arr}   alt={f.get('alt')}m  spd={f.get('speed')}km/h")

# 3. Do these match OUR fleet?
print(f"\n3. MATCH AGAINST YOUR 44 FLEET AIRCRAFT")
try:
    conn = sqlite3.connect("aviation_data.db")
    fleet = {
        (h or "").strip().upper(): t
        for t, h in conn.execute(
            "SELECT tail_number, hex_code FROM fleet WHERE hex_code IS NOT NULL"
        )
    }
    conn.close()
except Exception as e:
    print(f"   (could not open aviation_data.db: {e})")
    sys.exit(0)

matched = []
for f in flights:
    hx = (f.get("hex") or "").strip().upper()
    if hx in fleet:
        matched.append((fleet[hx], f))

print(f"   Fleet aircraft currently airborne: {len(matched)}")
for tail, f in matched:
    dep = f.get("dep_iata") or "?"
    arr = f.get("arr_iata") or "?"
    print(f"     ✅ {tail:<9} {str(f.get('flight_iata')):<8} {dep} -> {arr}")

print()
print("=" * 68)
print("VERDICT")
print("=" * 68)
if len(with_route) > len(flights) * 0.5 and matched:
    print("  ✅ AirLabs works AND gives routes AND matches your fleet.")
    print("     Set the key and restart:")
    print('        $env:AIRLABS_API_KEY="' + KEY[:6] + '..."     (PowerShell)')
    print("        uvicorn main:app")
elif not matched:
    print("  ⚠️  Flights returned, but none match your 44 aircraft right now.")
    print("     That may just mean none of your fleet is flying at this moment.")
    print("     Re-run in 20 minutes before concluding anything.")
else:
    print("  ⚠️  Flights returned but route coverage is thin on this plan.")