import requests

url = "https://opensky-network.org/api/states/all"
params = {"lamin": 23.0, "lomin": 61.0, "lamax": 37.5, "lomax": 78.0}

resp   = requests.get(url, params=params, timeout=15)
states = resp.json().get("states", [])

print(f"Found {len(states)} flights:")
for s in states:
    icao24   = str(s[0]).strip().upper() if s[0] else "?"
    callsign = str(s[1]).strip()         if s[1] else "NO_CALL"
    lat      = s[6]
    lon      = s[5]
    alt      = s[7]
    print(f"  icao24={icao24:<12} callsign='{callsign:<10}' lat={lat} lon={lon} alt={alt}")