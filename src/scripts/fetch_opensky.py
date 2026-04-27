import requests
import sqlite3
from datetime import datetime
import os

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR    = os.path.dirname(SCRIPT_DIR)
DB_PATH    = os.path.join(SRC_DIR, "backend", "aviation_data.db")

# ── AviationStack Config ──
API_KEY  = "906fb3efbe9699177f8b43380bf32669"
BASE_URL = "http://api.aviationstack.com/v1/flights"

# Pakistani airlines ICAO codes
PAK_AIRLINES = [
    ("PIA",  "Pakistan International Airlines"),
    ("ABQ",  "AirBlue"),
    ("ERD",  "AirSial"),
    ("SAI",  "SereneAir"),
    ("ORM",  "Fly Jinnah"),
]

print(f"🔗 Connecting to database at: {DB_PATH}")


def fetch_pakistan_flights():
    """
    Fetches live Pakistani airline flights from AviationStack
    and saves them to the flight_telemetry table.
    """
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_saved   = 0
    total_skipped = 0

    for icao_code, airline_name in PAK_AIRLINES:
        print(f"\n📡 Fetching {airline_name} ({icao_code}) flights...")

        try:
            params = {
                "access_key":    API_KEY,
                "airline_icao":  icao_code,
                "flight_status": "active",
            }

            resp = requests.get(BASE_URL, params=params, timeout=15)

            if resp.status_code == 429:
                print(f"  ⚠️ Rate limit hit — skipping {icao_code}")
                continue
            if resp.status_code == 401:
                print(f"  ❌ Invalid API key")
                break
            if resp.status_code != 200:
                print(f"  ❌ HTTP {resp.status_code}")
                continue

            data    = resp.json()
            flights = data.get("data", [])

            if not flights:
                print(f"  ⚠️ No active {icao_code} flights right now")
                continue

            print(f"  ✅ Found {len(flights)} active flights")

            for flight in flights:
                try:
                    # Callsign
                    callsign = (
                        flight.get("flight", {}).get("icao") or
                        flight.get("flight", {}).get("iata") or
                        "UNKNOWN"
                    ).strip().upper()

                    # Tail number
                    tail = (flight.get("aircraft") or {}).get("registration", "UNKNOWN")
                    if tail:
                        tail = tail.strip().upper()

                    # Live position
                    live = flight.get("live") or {}
                    lat  = live.get("latitude")
                    lon  = live.get("longitude")
                    alt  = live.get("altitude")          # feet
                    vel  = live.get("speed_horizontal")  # km/h

                    if None in (lat, lon, alt, vel):
                        total_skipped += 1
                        continue

                    # Convert: feet → metres, km/h → m/s
                    alt_m  = round(alt * 0.3048,  2)
                    vel_ms = round(vel * 0.27778, 2)

                    if alt_m <= 0:
                        total_skipped += 1
                        continue

                    cursor.execute("""
                        INSERT INTO flight_telemetry
                        (tail_number, callsign, altitude, velocity,
                         latitude, longitude, anomaly_flag, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                    """, (tail, callsign, alt_m, vel_ms,
                          lat, lon, datetime.now()))

                    total_saved += 1
                    print(f"  ✈️  {callsign:<10} | {tail:<10} | "
                          f"alt={alt_m:.0f}m | lat={lat:.3f} lon={lon:.3f}")

                except Exception as e:
                    print(f"  ⚠️ Error processing flight: {e}")
                    continue

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Connection error for {icao_code}: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"\n💾 Done — Saved {total_saved} Pakistani flights | "
          f"Skipped {total_skipped} (no live data)")


if __name__ == "__main__":
    fetch_pakistan_flights()