"""
AeroTwin — retry the 5 hex codes that failed to resolve.

The first pass resolved 3 of 8 but failed on the SIF/FJL hexes, most likely
because of rate limiting. This retries them slowly, tries both sources, and
prints the raw error so we can see what's actually happening.

Run from src/backend:
    python retry_hex.py
"""
import json
import time
import urllib.request

HEXES = {
    "760A07": "SIF124",
    "760A0A": "SIF123",
    "760A0E": "SIF722",
    "760A0D": "FJL672",
    "8966B0": "FJL866",
}

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def try_adsbdb(hx):
    d = get_json(f"https://api.adsbdb.com/v0/aircraft/{hx}")
    ac = (d.get("response") or {}).get("aircraft") or {}
    if ac.get("registration"):
        return ac["registration"], ac.get("registered_owner", ""), ac.get("type", "")
    return None


def try_hexdb(hx):
    d = get_json(f"https://hexdb.io/api/v1/aircraft/{hx}")
    if d.get("Registration"):
        return d["Registration"], d.get("RegisteredOwners", ""), d.get("Type", "")
    return None


print("=" * 70)
print("Retrying the 5 unresolved hex codes (slowly, both sources)")
print("=" * 70)
print()

results = {}

for hx, callsign in HEXES.items():
    print(f"{hx}  (seen as {callsign})")
    got = None

    for name, fn in [("adsbdb", try_adsbdb), ("hexdb", try_hexdb)]:
        try:
            got = fn(hx)
            if got:
                reg, owner, model = got
                print(f"   ✅ {name}: {reg}   ({owner} {model})")
                results[hx] = (reg, owner, model, callsign)
                break
            else:
                print(f"   -- {name}: responded but no registration")
        except Exception as e:
            print(f"   xx {name}: {e}")
        time.sleep(2)      # be gentle — this is what likely broke last time

    if not got:
        print(f"   ❌ could not resolve {hx}")
    print()
    time.sleep(3)          # generous pause between aircraft

print("=" * 70)
print("RESULT — SQL to run if these look right")
print("=" * 70)
if not results:
    print("\n  Nothing resolved. Look these up by hand on planespotters.net:\n")
    for hx, cs in HEXES.items():
        print(f"    {hx}   seen as {cs}")
else:
    print()
    for hx, (reg, owner, model, cs) in results.items():
        print(f"  -- {cs}: hex {hx} is {reg}  ({owner} {model})")
        print(f"  UPDATE fleet SET hex_code='{hx}' WHERE tail_number='{reg}';")
        print()
    print("  Run the UPDATEs above ONLY for registrations that actually exist")
    print("  in your fleet table. Verify first with:")
    print("     python -c \"import sqlite3;c=sqlite3.connect('aviation_data.db');print(c.execute('SELECT tail_number,airline FROM fleet WHERE hex_code IS NULL OR hex_code=\\\"\\\"').fetchall())\"")