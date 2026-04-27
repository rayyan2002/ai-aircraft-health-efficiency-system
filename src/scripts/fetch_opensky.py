"""
fetch_opensky.py
================
Fetches live Pakistani airline flights from AviationStack.
When live GPS is unavailable (free tier), estimates position
from departure/arrival airports and scheduled flight time.

Saves to pakistan_telemetry table.
anomaly_flag = 0 → real GPS
anomaly_flag = 1 → estimated position
"""

import requests
import sqlite3
from datetime import datetime
import os
import math

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR    = os.path.dirname(SCRIPT_DIR)
DB_PATH    = os.path.join(SRC_DIR, "backend", "aviation_data.db")

# ── AviationStack Config ──
API_KEY  = "906fb3efbe9699177f8b43380bf32669"
BASE_URL = "http://api.aviationstack.com/v1/flights"

# ── Pakistani Airlines ──
PAK_AIRLINES = [
    ("PIA", "Pakistan International Airlines"),
    ("ABQ", "AirBlue"),
    ("SIF", "AirSial"),
    ("FJL", "Fly Jinnah"),
]

# ── Airport Coordinates (lat, lon) ──
AIRPORT_COORDS = {
    "KHI": (24.9008,  67.1681),
    "LHE": (31.5216,  74.4036),
    "ISB": (33.6167,  73.0994),
    "PEW": (33.9939,  71.5146),
    "LYP": (31.3600,  72.9947),
    "MUX": (30.2032,  71.4191),
    "SKT": (32.5356,  74.3639),
    "UET": (30.2512,  66.9378),
    "GWD": (25.2330,  62.3294),
    "SKZ": (27.7220,  68.7926),
    "BHV": (29.9481,  71.7181),
    "RYK": (28.3839,  70.2796),
    "TUK": (25.9864,  63.0322),
    "GIL": (35.9188,  74.3336),
    "DXB": (25.2532,  55.3657),
    "AUH": (24.4330,  54.6511),
    "DOH": (25.2731,  51.6080),
    "KWI": (29.2266,  47.9689),
    "BAH": (26.2708,  50.6336),
    "MCT": (23.5933,  58.2844),
    "JED": (21.6796,  39.1565),
    "RUH": (24.9578,  46.6989),
    "MED": (24.5534,  39.7051),
    "LHR": (51.4700,  -0.4543),
    "MAN": (53.3537,  -2.2750),
    "CDG": (49.0097,   2.5479),
    "FRA": (50.0379,   8.5622),
    "IST": (41.2608,  28.7418),
    "KUL": ( 2.7456, 101.7099),
    "PEK": (40.0799, 116.6031),
    "CAN": (23.3959, 113.3080),
    "DEL": (28.5562,  77.1000),
    "BOM": (19.0896,  72.8656),
    "YYZ": (43.6777,  -79.6248),
    "JFK": (40.6413,  -73.7781),
    "NBO": (-1.3192,   36.9275),
    "ADD": ( 8.9779,   38.7993),
}

CRUISE_PROFILE = {
    "A320":    {"alt_m": 11000, "vel_ms": 235},
    "A321":    {"alt_m": 11200, "vel_ms": 238},
    "B777":    {"alt_m": 12000, "vel_ms": 250},
    "B737":    {"alt_m": 10500, "vel_ms": 230},
    "DEFAULT": {"alt_m": 10000, "vel_ms": 230},
}

print(f"🔗 Database: {DB_PATH}")


def get_aircraft_type_code(type_str: str) -> str:
    if not type_str:
        return "DEFAULT"
    t = type_str.upper()
    if "A321" in t: return "A321"
    if "A320" in t: return "A320"
    if "777"  in t: return "B777"
    if "737"  in t: return "B737"
    return "DEFAULT"


def parse_dt(s):
    if not s:
        return None
    # AviationStack format: "2026-04-27T10:32:00+00:00"
    # Strip timezone offset and parse
    try:
        clean = s[:19].replace("T", " ")
        return datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def estimate_position(flight: dict, ac_type: str = "DEFAULT") -> dict:
    """
    Estimate current lat/lon from departure/arrival airports
    and scheduled flight times.
    """
    dep = flight.get("departure") or {}
    arr = flight.get("arrival")   or {}

    dep_iata = (dep.get("iata") or "").upper()
    arr_iata = (arr.get("iata") or "").upper()

    dep_coords = AIRPORT_COORDS.get(dep_iata)
    arr_coords = AIRPORT_COORDS.get(arr_iata)

    if not dep_coords or not arr_coords:
        return None

    dep_lat, dep_lon = dep_coords
    arr_lat, arr_lon = arr_coords

    dep_time = parse_dt(dep.get("actual") or dep.get("estimated") or dep.get("scheduled"))
    arr_time = parse_dt(arr.get("estimated") or arr.get("scheduled"))

    now = datetime.utcnow()

    if dep_time and arr_time:
        total_secs   = max((arr_time - dep_time).total_seconds(), 1)
        elapsed_secs = (now - dep_time).total_seconds()
        progress     = max(0.0, min(1.0, elapsed_secs / total_secs))
    else:
        progress = 0.5

    lat = dep_lat + (arr_lat - dep_lat) * progress
    lon = dep_lon + (arr_lon - dep_lon) * progress

    profile = CRUISE_PROFILE.get(ac_type, CRUISE_PROFILE["DEFAULT"])
    if progress < 0.15:
        alt_m = profile["alt_m"] * (progress / 0.15)
    elif progress > 0.85:
        alt_m = profile["alt_m"] * ((1.0 - progress) / 0.15)
    else:
        alt_m = profile["alt_m"]

    return {
        "lat":          round(lat, 4),
        "lon":          round(lon, 4),
        "alt_m":        round(max(alt_m, 0), 1),
        "vel_ms":       profile["vel_ms"],
        "dep_iata":     dep_iata,
        "arr_iata":     arr_iata,
        "progress_pct": round(progress * 100, 1),
    }


def fetch_pakistan_flights():
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_saved     = 0
    total_live_gps  = 0
    total_estimated = 0
    total_no_data   = 0

    for icao_code, airline_name in PAK_AIRLINES:
        print(f"\n📡 {airline_name} ({icao_code})...")

        try:
            params = {
                "access_key":    API_KEY,
                "airline_icao":  icao_code,
                "flight_status": "active",
            }
            resp = requests.get(BASE_URL, params=params, timeout=15)

            if resp.status_code == 429:
                print(f"  ⚠️ Rate limit — skipping")
                continue
            if resp.status_code != 200:
                print(f"  ❌ HTTP {resp.status_code}")
                continue

            flights = resp.json().get("data", [])
            if not flights:
                print(f"  ⚠️ No active flights")
                continue

            print(f"  Found {len(flights)} active flights")

            for flight in flights:
                tail = (flight.get("aircraft") or {}).get("registration", "UNKNOWN")
                tail = tail.strip().upper() if tail else "UNKNOWN"

                ac_type = get_aircraft_type_code(
                    (flight.get("aircraft") or {}).get("iata", "")
                )

                callsign = (
                    flight.get("flight", {}).get("icao") or
                    flight.get("flight", {}).get("iata") or
                    icao_code
                ).strip().upper()

                dep_iata = (flight.get("departure") or {}).get("iata", "—")
                arr_iata = (flight.get("arrival")   or {}).get("iata", "—")

                # ── Try live GPS ──
                live   = flight.get("live") or {}
                lat    = live.get("latitude")
                lon    = live.get("longitude")
                alt_ft = live.get("altitude")
                vel_kh = live.get("speed_horizontal")

                # anomaly_flag: 0=real GPS, 1=estimated
                is_estimated = False

                if lat is not None and lon is not None and alt_ft is not None:
                    # AviationStack returns altitude in METRES (not feet)
                    alt_m        = round(float(alt_ft), 2)
                    vel_ms       = round((vel_kh or 0) * 0.27778, 2)
                    is_estimated = False
                    total_live_gps += 1
                    tag = "🛰️  GPS"
                else:
                    est = estimate_position(flight, ac_type)
                    if est:
                        lat          = est["lat"]
                        lon          = est["lon"]
                        alt_m        = est["alt_m"]
                        vel_ms       = est["vel_ms"]
                        is_estimated = True
                        total_estimated += 1
                        tag = f"📐 EST {est['dep_iata']}→{est['arr_iata']} {est['progress_pct']}%"
                    else:
                        lat = lon = alt_m = vel_ms = None
                        is_estimated = False
                        total_no_data += 1
                        tag = "❓ NO DATA"

                cursor.execute("""
                    INSERT INTO pakistan_telemetry
                    (tail_number, callsign, airline, altitude, velocity,
                     latitude, longitude, anomaly_flag, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tail, callsign, airline_name,
                    alt_m, vel_ms, lat, lon,
                    1 if is_estimated else 0,
                    datetime.now()
                ))
                total_saved += 1
                print(f"  ✈️  {callsign:<10} {tail:<12} {tag}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    conn.commit()
    conn.close()

    print(f"\n{'='*55}")
    print(f"  🛰️  Live GPS   : {total_live_gps}")
    print(f"  📐 Estimated  : {total_estimated}")
    print(f"  ❓ No data    : {total_no_data}")
    print(f"  💾 Total saved: {total_saved}")
    print(f"{'='*55}")


if __name__ == "__main__":
    fetch_pakistan_flights()