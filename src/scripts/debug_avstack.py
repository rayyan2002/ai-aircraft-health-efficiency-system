import requests, json

API_KEY  = "906fb3efbe9699177f8b43380bf32669"
BASE_URL = "http://api.aviationstack.com/v1/flights"

resp = requests.get(BASE_URL, params={
    "access_key":    API_KEY,
    "airline_icao":  "ABQ",
    "flight_status": "active",
}, timeout=15)

data = resp.json().get("data", [])
if data:
    f = data[0]
    print("=== FULL FLIGHT OBJECT ===")
    print(json.dumps(f, indent=2))
else:
    print("No flights found")