import requests

url = "https://opensky-network.org/api/states/all"
params = {"lamin": 23.0, "lomin": 61.0, "lamax": 37.5, "lomax": 78.0}

resp   = requests.get(url, params=params, timeout=15)
states = resp.json().get("states", [])

PAK_PREFIXES = ("PIA", "ABQ", "ERD", "NL", "SAI", "ORM")

print(f"Total flights: {len(states)}\n")
print("ALL CALLSIGNS:")
for s in states:
    callsign = str(s[1]).strip() if s[1] else "NO_CALL"
    icao24   = str(s[0]).strip().upper() if s[0] else "?"
    is_pak   = any(callsign.upper().startswith(p) for p in PAK_PREFIXES)
    flag     = "🇵🇰" if is_pak else "  "
    print(f"  {flag} icao24={icao24:<12} callsign='{callsign}'")