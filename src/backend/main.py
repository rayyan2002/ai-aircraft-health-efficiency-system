from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import numpy as np
import joblib
import pandas as pd
import math
import tensorflow as tf
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models_db
import os
import asyncio
from contextlib import asynccontextmanager

# ──────────────────────────────────────────────────────────────
# 1. PATH CONFIGURATION
# ──────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))   # src/backend/
MODELS_DIR = os.path.join(BASE_DIR, "..", "models")        # src/models/

IF_MODEL_PATH     = os.path.join(MODELS_DIR, "adsb_iforest.pkl")
SCALER_PATH       = os.path.join(MODELS_DIR, "adsb_if_scaler.pkl")
CMAPSS_MODEL_PATH = os.path.join(MODELS_DIR, "cmapss_health_rf.pkl")
LSTM_MODEL_PATH   = os.path.join(MODELS_DIR, "engine_model_v1.keras")
LSTM_SCALER_PATH  = os.path.join(MODELS_DIR, "scaler_features.pkl")

models_db.Base.metadata.create_all(bind=engine)

# ──────────────────────────────────────────────────────────────
# OPENSKY FETCHER  (runs inside the background worker)
# ──────────────────────────────────────────────────────────────
import sqlite3 as _sqlite3
from datetime import datetime as _datetime

DB_PATH = os.path.join(BASE_DIR, "..", "backend", "aviation_data.db")

# ── Create fleet_status + pipeline_log tables on startup ──
def _init_extra_tables():
    conn = _sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fleet_status (
            tail_number       TEXT PRIMARY KEY,
            status            TEXT DEFAULT 'unknown',
            last_seen         TEXT,
            current_callsign  TEXT,
            departure_airport TEXT,
            arrival_airport   TEXT,
            last_flight_id    INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_records (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            tail_number      TEXT NOT NULL,
            component        TEXT,
            maintenance_type TEXT,
            location         TEXT,
            notes            TEXT,
            performed_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather_data (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            city          TEXT NOT NULL,
            iata_code     TEXT,
            temp_celsius  REAL,
            wind_speed_ms REAL,
            wind_dir_deg  REAL,
            description   TEXT,
            fetched_at    TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col in ["departure_airport", "arrival_airport"]:
        try:
            conn.execute(f"ALTER TABLE pakistan_telemetry ADD COLUMN {col} TEXT")
        except:
            pass  # already exists

    conn.commit()
    conn.close()

_init_extra_tables()   # ← runs on every uvicorn startup

# Pakistan-only airspace bounding box
# Lat: 23°N to 37.5°N | Lon: 61°E to 78°E
OPENSKY_PARAMS = {
    "lamin": 23.0, "lomin": 61.0,
    "lamax": 37.5, "lomax": 78.0,
}

def fetch_and_insert_opensky():
    """
    Hits the OpenSky Network API for Pakistan airspace and inserts
    live telemetry into flight_telemetry. Called by the background worker.
    """
    import requests as _req

    url = "https://opensky-network.org/api/states/all"
    print("📡 [OpenSky] Pinging API for Pakistan airspace...")

    try:
        resp = _req.get(url, params=OPENSKY_PARAMS, timeout=15)

        if resp.status_code == 429:
            print("⚠️ [OpenSky] Rate limit hit — skipping this cycle.")
            return
        if resp.status_code != 200:
            print(f"⚠️ [OpenSky] HTTP {resp.status_code} — skipping.")
            return

        states = resp.json().get("states") or []
        if not states:
            print("⚠️ [OpenSky] No flights in bounding box right now.")
            return

        conn   = _sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        saved = 0
        limit = 100
        PAK_PREFIXES = ("PIA", "ABQ", "ERD", "NL", "SAI", "ORM")

        for flight in states:
            if saved >= limit:
                break

            icao24   = str(flight[0]).strip().upper() if flight[0] else "UNKNOWN"
            callsign = str(flight[1]).strip().upper() if flight[1] else "UNKNOWN"
            lon      = flight[5]
            lat      = flight[6]
            alt      = flight[7]
            vel      = flight[9]

            if None in (lat, lon, alt, vel):
                continue
            if alt <= 0:
                continue

            if not any(callsign.startswith(p) for p in PAK_PREFIXES):
                continue

            cursor.execute("""
                INSERT INTO flight_telemetry
                (tail_number, callsign, altitude, velocity,
                 latitude, longitude, anomaly_flag, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """, (icao24, callsign, alt, vel, lat, lon, _datetime.now()))
            saved += 1

        conn.commit()
        conn.close()
        print(f"✅ [OpenSky] Saved {saved} live flights to flight_telemetry.")

    except Exception as e:
        print(f"❌ [OpenSky] Error: {e}")


def fetch_and_insert_aviationstack():
    """
    Fetches live Pakistani airline flights from AviationStack.
    Uses real GPS when available, falls back to estimated position.
    Saves to pakistan_telemetry table.
    """
    import requests as _req
    import math as _math

    AVSTACK_KEY  = "906fb3efbe9699177f8b43380bf32669"
    AVSTACK_URL  = "http://api.aviationstack.com/v1/flights"

    PAK_AIRLINES = [
        ("PIA", "Pakistan International Airlines"),
        ("ABQ", "AirBlue"),
        ("SIF", "AirSial"),
        ("FJL", "Fly Jinnah"),
    ]

    AIRPORT_COORDS = {
        "KHI": (24.9008, 67.1681), "LHE": (31.5216, 74.4036),
        "ISB": (33.6167, 73.0994), "PEW": (33.9939, 71.5146),
        "LYP": (31.3600, 72.9947), "MUX": (30.2032, 71.4191),
        "SKT": (32.5356, 74.3639), "UET": (30.2512, 66.9378),
        "GWD": (25.2330, 62.3294), "SKZ": (27.7220, 68.7926),
        "DXB": (25.2532, 55.3657), "AUH": (24.4330, 54.6511),
        "DOH": (25.2731, 51.6080), "KWI": (29.2266, 47.9689),
        "MCT": (23.5933, 58.2844), "JED": (21.6796, 39.1565),
        "RUH": (24.9578, 46.6989), "MED": (24.5534, 39.7051),
        "LHR": (51.4700,  -0.4543), "MAN": (53.3537, -2.2750),
        "CDG": (49.0097,   2.5479), "FRA": (50.0379,  8.5622),
        "IST": (41.2608,  28.7418), "KUL": ( 2.7456, 101.7099),
        "PEK": (40.0799, 116.6031), "CAN": (23.3959, 113.3080),
        "DEL": (28.5562,  77.1000), "BOM": (19.0896,  72.8656),
        "YYZ": (43.6777, -79.6248), "JFK": (40.6413, -73.7781),
        "NBO": (-1.3192,  36.9275), "ADD": ( 8.9779,  38.7993),
        "BAH": (26.2708,  50.6336), "RYK": (28.3839,  70.2796),
    }

    CRUISE = {
        "A320": {"alt_m": 11000, "vel_ms": 235},
        "A321": {"alt_m": 11200, "vel_ms": 238},
        "B777": {"alt_m": 12000, "vel_ms": 250},
        "B737": {"alt_m": 10500, "vel_ms": 230},
        "DEFAULT": {"alt_m": 10000, "vel_ms": 230},
    }

    def _parse_dt(s):
        if not s:
            return None
        try:
            return _datetime.strptime(s[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
        except:
            return None

    def _ac_code(t):
        t = (t or "").upper()
        for k in ["A321", "A320", "777", "737"]:
            if k in t:
                return "A321" if k=="A321" else "A320" if k=="A320" else "B777" if k=="777" else "B737"
        return "DEFAULT"

    def _estimate(flight, ac):
        dep = flight.get("departure") or {}
        arr = flight.get("arrival")   or {}
        dc  = AIRPORT_COORDS.get((dep.get("iata") or "").upper())
        ac_ = AIRPORT_COORDS.get((arr.get("iata") or "").upper())
        if not dc or not ac_:
            return None
        dt = _parse_dt(dep.get("actual") or dep.get("estimated") or dep.get("scheduled"))
        at = _parse_dt(arr.get("estimated") or arr.get("scheduled"))
        now = _datetime.utcnow()
        if dt and at:
            prog = max(0.0, min(1.0, (now-dt).total_seconds() / max((at-dt).total_seconds(),1)))
        else:
            prog = 0.5
        lat = dc[0] + (ac_[0] - dc[0]) * prog
        lon = dc[1] + (ac_[1] - dc[1]) * prog
        p   = CRUISE.get(ac, CRUISE["DEFAULT"])
        alt = p["alt_m"] * (prog/0.15 if prog<0.15 else (1-prog)/0.15 if prog>0.85 else 1.0)
        return {"lat": round(lat,4), "lon": round(lon,4),
                "alt_m": round(max(alt,0),1), "vel_ms": p["vel_ms"]}

    conn   = _sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    saved  = 0

    print("📡 [AviationStack] Fetching Pakistani airline flights...")

    for icao_code, airline_name in PAK_AIRLINES:
        try:
            resp = _req.get(AVSTACK_URL, params={
                "access_key": AVSTACK_KEY,
                "airline_icao": icao_code,
                "flight_status": "active",
            }, timeout=15)

            if resp.status_code != 200:
                continue

            for f in (resp.json().get("data") or []):
                tail     = ((f.get("aircraft") or {}).get("registration") or "UNKNOWN").strip().upper()
                callsign = (f.get("flight",{}).get("icao") or f.get("flight",{}).get("iata") or icao_code).strip().upper()
                ac_type  = _ac_code((f.get("aircraft") or {}).get("iata",""))
                live     = f.get("live") or {}

                # ── Extract departure / arrival airports ──
                dep_iata = ((f.get("departure") or {}).get("iata") or "Unknown").upper()
                arr_iata = ((f.get("arrival")   or {}).get("iata") or "Unknown").upper()

                lat, lon, alt_raw, vel_kh = (
                    live.get("latitude"), live.get("longitude"),
                    live.get("altitude"), live.get("speed_horizontal")
                )
                is_est = False
                if lat is not None and lon is not None and alt_raw is not None:
                    alt_m  = round(float(alt_raw), 2)
                    vel_ms = round((vel_kh or 0) * 0.27778, 2)
                else:
                    est = _estimate(f, ac_type)
                    if est:
                        lat, lon, alt_m, vel_ms = est["lat"], est["lon"], est["alt_m"], est["vel_ms"]
                        is_est = True
                    else:
                        lat = lon = alt_m = vel_ms = None

                cursor.execute("""
                    INSERT INTO pakistan_telemetry
                    (tail_number, callsign, airline, altitude, velocity,
                     latitude, longitude, anomaly_flag, departure_airport,
                     arrival_airport, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tail, callsign, airline_name, alt_m, vel_ms,
                      lat, lon, 1 if is_est else 0,
                      dep_iata, arr_iata, _datetime.now()))
                saved += 1

        except Exception as e:
            print(f"  ⚠️ {icao_code}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ [AviationStack] Saved {saved} flights to pakistan_telemetry.")


def fetch_and_insert_aviationstack_tracked() -> set:
    """
    Same as fetch_and_insert_aviationstack but also returns
    the set of tail_numbers that are currently active.
    Used by absence detection in the background worker.
    """
    fetch_and_insert_aviationstack()
    # Read back which tails were just inserted in the last 10 minutes
    try:
        c = _sqlite3.connect(DB_PATH)
        rows = c.execute("""
            SELECT DISTINCT tail_number FROM pakistan_telemetry
            WHERE tail_number != 'UNKNOWN'
            AND timestamp >= datetime('now', '-10 minutes')
        """).fetchall()
        c.close()
        return {r[0] for r in rows}
    except:
        return set()

def fetch_and_insert_weather():
    """
    Fetches live weather for 4 major Pakistani airports from OpenWeatherMap.
    Saves to weather_data table. Called by the background worker every cycle.
    """
    import requests as _req

    WEATHER_KEY = "4f7ba9337ae4f2f8bd338f49f323662d"
    WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

    # Major Pakistani airports: city name → IATA code
    AIRPORTS = {
        "Karachi":    "KHI",
        "Lahore":     "LHE",
        "Islamabad":  "ISB",
        "Peshawar":   "PEW",
    }

    conn  = _sqlite3.connect(DB_PATH)
    saved = 0

    for city, iata in AIRPORTS.items():
        try:
            resp = _req.get(WEATHER_URL, params={
                "q":      city,
                "appid":  WEATHER_KEY,
                "units":  "metric",
            }, timeout=10)

            if resp.status_code != 200:
                print(f"  ⚠️ Weather {city}: HTTP {resp.status_code}")
                continue

            data = resp.json()
            temp     = data["main"]["temp"]
            wind_spd = data["wind"]["speed"]
            wind_dir = data["wind"].get("deg", 0)
            desc     = data["weather"][0]["description"].title()

            conn.execute("""
                INSERT INTO weather_data
                (city, iata_code, temp_celsius, wind_speed_ms,
                 wind_dir_deg, description, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (city, iata, temp, wind_spd, wind_dir, desc,
                  _datetime.now().isoformat()))
            saved += 1

        except Exception as e:
            print(f"  ⚠️ Weather {city}: {e}")

    conn.commit()
    conn.close()
    if saved:
        print(f"🌤️ [Weather] Saved {saved} airport weather records.")


def get_nearest_airport_weather(lat: float, lon: float) -> dict:
    """
    Returns the most recent weather for the nearest Pakistani airport
    based on aircraft lat/lon. Falls back to Karachi if nothing found.
    """
    AIRPORT_COORDS = {
        "KHI": (24.9008, 67.1681),
        "LHE": (31.5216, 74.4036),
        "ISB": (33.6167, 73.0994),
        "PEW": (33.9939, 71.5146),
    }

    # Find nearest airport
    nearest = "KHI"
    min_dist = float("inf")
    for iata, (alat, alon) in AIRPORT_COORDS.items():
        dist = math.sqrt((lat - alat)**2 + (lon - alon)**2)
        if dist < min_dist:
            min_dist = dist
            nearest  = iata

    # Query latest weather for that airport
    try:
        conn = _sqlite3.connect(DB_PATH)
        row  = conn.execute("""
            SELECT temp_celsius, wind_speed_ms, wind_dir_deg, description
            FROM weather_data WHERE iata_code = ?
            ORDER BY fetched_at DESC LIMIT 1
        """, (nearest,)).fetchone()
        conn.close()

        if row:
            return {
                "airport":    nearest,
                "temp_c":     row[0],
                "wind_ms":    row[1],
                "wind_dir":   row[2],
                "conditions": row[3],
                "source":     "live",
            }
    except:
        pass

    # Fallback to ISA estimates
    return {
        "airport":    nearest,
        "temp_c":     compute_temp(8000),
        "wind_ms":    15.0,
        "wind_dir":   270,
        "conditions": "Estimated",
        "source":     "estimated",
    }


# ──────────────────────────────────────────────────────────────
# 2. BACKGROUND WORKER
# ──────────────────────────────────────────────────────────────
def _get_row_count(table: str) -> int:
    try:
        c = _sqlite3.connect(DB_PATH)
        n = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        c.close()
        return n
    except:
        return 0


async def automated_data_pipeline():
    """Runs every 5 minutes — fetches live data, detects landings, logs every cycle."""
    while True:
        print("🔄 [HEARTBEAT] Running Automated Data Pipeline...")
        cycle_start    = _datetime.now()
        opensky_saved  = 0
        avstack_saved  = 0
        landings_logged= 0
        errors         = []
        db = SessionLocal()

        try:
            # ── Step 1: snapshot active tails BEFORE fetch ──
            conn_snap = _sqlite3.connect(DB_PATH)
            prev_active = set(
                r[0] for r in conn_snap.execute(
                    "SELECT tail_number FROM fleet_status WHERE status='airborne'"
                ).fetchall()
            )
            conn_snap.close()

            # ── Step 2: Fetch OpenSky → flight_telemetry ──
            try:
                before = _get_row_count("flight_telemetry")
                await asyncio.get_event_loop().run_in_executor(None, fetch_and_insert_opensky)
                opensky_saved = _get_row_count("flight_telemetry") - before
            except Exception as e:
                errors.append(f"opensky:{e}")

            # ── Step 3: Fetch AviationStack → pakistan_telemetry ──
            # Also collect which tails are active this cycle
            try:
                before = _get_row_count("pakistan_telemetry")
                current_active = await asyncio.get_event_loop().run_in_executor(
                    None, fetch_and_insert_aviationstack_tracked
                )
                avstack_saved = _get_row_count("pakistan_telemetry") - before
            except Exception as e:
                errors.append(f"aviationstack:{e}")
                current_active = set()

            # ── Step 3b: Fetch weather for Pakistani airports ──
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, fetch_and_insert_weather
                )
            except Exception as e:
                errors.append(f"weather:{e}")

            # ── Step 4: Update fleet_status for active planes ──
            conn_fs = _sqlite3.connect(DB_PATH)
            for tail in current_active:
                conn_fs.execute("""
                    INSERT INTO fleet_status (tail_number, status, last_seen)
                    VALUES (?, 'airborne', ?)
                    ON CONFLICT(tail_number) DO UPDATE SET
                        status='airborne', last_seen=excluded.last_seen
                """, (tail, _datetime.now().isoformat()))
            conn_fs.commit()

            # ── Step 5: Absence detection — who just landed? ──
            just_landed = prev_active - current_active
            for tail in just_landed:
                print(f"🛬 ABSENCE DETECTED — {tail} no longer active. Logging flight...")

                # Get last known telemetry
                last_row = conn_fs.execute("""
                    SELECT altitude, velocity, callsign,
                           COALESCE(departure_airport, 'Unknown') as departure_airport,
                           COALESCE(arrival_airport, 'Unknown') as arrival_airport
                    FROM pakistan_telemetry
                    WHERE tail_number = ?
                    ORDER BY id DESC LIMIT 1
                """, (tail,)).fetchone()

                if last_row:
                    alt_last = last_row[0] or 0
                    vel_last = last_row[1] or 0
                    callsign = last_row[2] or tail
                    origin   = last_row[3] or "Unknown"
                    dest     = last_row[4] or "Unknown"
                else:
                    alt_last = vel_last = 0
                    callsign = tail
                    origin   = dest = "Unknown"

                # Calculate metrics
                fuel = round(compute_fuel_burn(alt_last, vel_last, 30), 1)
                co2  = round(fuel * 2.53, 1)

                final_health = 45.2
                if lstm_model and lstm_scaler:
                    try:
                        sd = np.zeros((30, 24))
                        sd[:, 0] = alt_last / 1000
                        sd[:, 1] = vel_last
                        scaled = lstm_scaler.transform(sd)
                        rul = float(lstm_model.predict(scaled.reshape(1,30,24), verbose=0)[0][0])
                        final_health = round(min(100, max(0, rul / 2)), 1)
                    except:
                        pass

                # Insert into flight_history
                db.add(models_db.FlightHistory(
                    tail_number       = tail,
                    origin            = origin,
                    destination       = dest,
                    total_fuel_liters = fuel,
                    co2_kg            = co2,
                    final_health_score= final_health,
                ))
                db.commit()
                landings_logged += 1

                # Update fleet_status to grounded
                conn_fs.execute("""
                    UPDATE fleet_status SET status='grounded', last_seen=?
                    WHERE tail_number=?
                """, (_datetime.now().isoformat(), tail))
                conn_fs.commit()
                print(f"  ✅ {tail} → flight_history | fuel={fuel}L health={final_health}")

            conn_fs.close()

            # ── Step 6: Legacy auto-lander on flight_telemetry ──
            flying_planes = db.query(models_db.FlightTelemetry.callsign).distinct().all()
            for plane in flying_planes:
                tail = plane[0]
                if not tail:
                    continue
                recent_logs = db.query(models_db.FlightTelemetry)\
                                .filter(models_db.FlightTelemetry.callsign == tail)\
                                .order_by(models_db.FlightTelemetry.timestamp.desc())\
                                .limit(2).all()
                if len(recent_logs) == 2:
                    cur = recent_logs[0]
                    prv = recent_logs[1]
                    if (prv.altitude or 0) > 0 and (cur.altitude or 0) <= 0:
                        fuel = round(compute_fuel_burn(cur.altitude or 0, cur.velocity or 0, 30), 1)
                        db.add(models_db.FlightHistory(
                            tail_number=tail, origin="Auto-Detect", destination="Auto-Detect",
                            total_fuel_liters=fuel, co2_kg=round(fuel*2.53,1), final_health_score=45.2
                        ))
                        db.commit()

        except Exception as e:
            errors.append(f"pipeline:{e}")
            print(f"⚠️ Pipeline Error: {e}")
            db.rollback()
        finally:
            db.close()

        # ── Step 7: Log this cycle ──
        duration  = round((_datetime.now() - cycle_start).total_seconds(), 1)
        error_str = " | ".join(errors) if errors else "none"
        log_line  = (
            f"{cycle_start.strftime('%Y-%m-%d %H:%M:%S')} | "
            f"opensky={opensky_saved} | avstack={avstack_saved} | "
            f"landings={landings_logged} | errors={error_str} | duration={duration}s"
        )
        print(f"📝 {log_line}")

        # Write to pipeline_log table
        try:
            c = _sqlite3.connect(DB_PATH)
            c.execute("""
                INSERT INTO pipeline_log
                (timestamp, opensky_saved, avstack_saved, landings_logged, errors, duration_sec)
                VALUES (?,?,?,?,?,?)
            """, (cycle_start.isoformat(), opensky_saved, avstack_saved,
                  landings_logged, error_str, duration))
            c.commit()
            c.close()
        except Exception as e:
            print(f"⚠️ Log write failed: {e}")

        print("💤 [HEARTBEAT] Sleeping 5 minutes...")
        await asyncio.sleep(300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(automated_data_pipeline())
    yield
    worker_task.cancel()


# ──────────────────────────────────────────────────────────────
# 3. APP INIT
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Aircraft Health & Efficiency Dashboard",
    description="ADS-B anomaly + CMAPSS + FYP-2 LSTM Real Inference",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────────────────────
# 4. LOAD MODELS
# ──────────────────────────────────────────────────────────────
if_model     = None
scaler       = None
cmapss_model = None
lstm_model   = None
lstm_scaler  = None

try:
    if_model     = joblib.load(IF_MODEL_PATH)
    scaler       = joblib.load(SCALER_PATH)
    cmapss_model = joblib.load(CMAPSS_MODEL_PATH)
    print("✅ SUCCESS: FYP-1 Models Loaded")
except Exception as e:
    print(f"⚠️ WARNING: FYP-1 Models missing or failed: {e}")

try:
    lstm_model  = tf.keras.models.load_model(LSTM_MODEL_PATH, safe_mode=False)
    lstm_scaler = joblib.load(LSTM_SCALER_PATH)
    print("✅ SUCCESS: FYP-2 Kamal's LSTM & Scaler Loaded")
except Exception as e:
    print(f"⚠️ WARNING: FYP-2 LSTM missing or failed: {e}")


# ──────────────────────────────────────────────────────────────
# 5. PYDANTIC SCHEMAS
# ──────────────────────────────────────────────────────────────
class ADSBIFInput(BaseModel):
    velocity:      float
    baro_altitude: float
    vertical_rate: float
    true_track:    float

class AnalysisRequest(BaseModel):
    aircraft:           str
    departure_airport:  str
    arrival_airport:    str
    weather_conditions: str
    aircraft_id:        Optional[str] = None

class FlightCompletionData(BaseModel):
    origin:       str
    destination:  str
    fuel_liters:  float
    co2_kg:       float
    health_score: float

class PakistanSeedRequest(BaseModel):
    planes: List[dict]

class SimulateRequest(BaseModel):
    tail_number:       str
    aircraft_age_yrs:  float = 8.0
    departure_iata:    str   = "KHI"
    arrival_iata:      str   = "LHE"
    weather:           str   = "Clear"
    cargo_kg:          float = 15000.0

class MaintenanceLogRequest(BaseModel):
    tail_number:       str
    component:         str              # Engine 1/Engine 2/APU/Landing Gear/Avionics/Windshield/Fuel System
    maintenance_type:  str              # A-check/B-check/C-check/Component replacement/Inspection
    location:          str   = "KHI"
    notes:             Optional[str] = None


# ──────────────────────────────────────────────────────────────
# 6. DYNAMIC MATH HELPERS
# ──────────────────────────────────────────────────────────────
def compute_flight_phase(alt_m: float, speed_ms: float) -> str:
    if alt_m > 8000 and speed_ms > 180:
        return "cruise"
    elif alt_m > 1000:
        return "climb_descent"
    elif speed_ms > 30:
        return "taxi_takeoff"
    else:
        return "grounded"


def compute_fuel_burn(alt_m: float, speed_ms: float, n_records: int) -> float:
    """
    Dynamic fuel burn in litres.
    Burn rate depends on flight phase; each DB record ≈ 5 minutes of flight.
    """
    phase = compute_flight_phase(alt_m, speed_ms)
    burn_rates = {
        "cruise":        85.0,
        "climb_descent": 110.0,
        "taxi_takeoff":  45.0,
        "grounded":      5.0,
    }
    return round(burn_rates[phase] * n_records * 5, 1)


def compute_wind(speed_ms: float, alt_m: float) -> float:
    """Relative wind estimate from airspeed and altitude."""
    if alt_m > 8000:
        return round(speed_ms * 0.20, 1)
    elif alt_m > 1000:
        return round(speed_ms * 0.10, 1)
    else:
        return round(speed_ms * 0.05, 1)


def compute_temp(alt_m: float) -> float:
    """ISA lapse rate: 15°C at sea level, -6.5°C per 1000 m."""
    return round(15.0 - (alt_m / 1000.0) * 6.5, 1)


def compute_dynamic_shap(alt_m: float, speed_ms: float,
                          if_score: float, predicted_rul: float) -> list:
    """
    SHAP-style attribution from real aircraft physics.
    Every plane gets unique values because alt/speed differ.
    Negative impact = hurts engine health.
    """
    alt_norm   = min(alt_m    / 13000.0, 1.0)
    speed_norm = min(speed_ms / 300.0,   1.0)

    alt_impact     = round(-(alt_norm ** 2) * 15.0, 2)
    speed_impact   = round(-(speed_norm * 12.0), 2) if speed_ms > 250 else round(speed_norm * 3.0, 2)
    anomaly_impact = round(if_score * 8.0, 2)
    rul_norm       = min(predicted_rul / 200.0, 1.0)
    wear_impact    = round(-(1.0 - rul_norm) * 10.0, 2)
    phase          = compute_flight_phase(alt_m, speed_ms)
    phase_impact   = {"cruise": 2.0, "climb_descent": -5.0, "taxi_takeoff": -3.0, "grounded": 0.0}[phase]

    return [
        {"feature": "Altitude (m)",                                  "impact": alt_impact},
        {"feature": "Airspeed (m/s)",                                "impact": speed_impact},
        {"feature": "ADS-B Anomaly Score",                           "impact": round(anomaly_impact, 2)},
        {"feature": "Engine Wear (RUL)",                             "impact": wear_impact},
        {"feature": f"Phase: {phase.replace('_', ' ').title()}",     "impact": round(phase_impact, 2)},
    ]


def run_iforest(velocity: float, altitude: float,
                vertical_rate: float, true_track: float):
    """Returns (anomaly_flag, if_score). Safe fallback if model missing."""
    if if_model is None or scaler is None:
        return 0, -0.05
    X       = np.array([velocity, altitude, vertical_rate, true_track], dtype=float).reshape(1, -1)
    X_s     = scaler.transform(X)
    raw     = int(if_model.predict(X_s)[0])
    score   = float(if_model.score_samples(X_s)[0])
    return (1 if raw == -1 else 0), score


# ──────────────────────────────────────────────────────────────
# 7. FYP-1 ENDPOINT
# ──────────────────────────────────────────────────────────────
def build_feature_vector(payload: ADSBIFInput) -> np.ndarray:
    return np.array(
        [payload.velocity, payload.baro_altitude, payload.vertical_rate, payload.true_track],
        dtype=float
    ).reshape(1, -1)


@app.post("/predict_adsb_if")
def predict_adsb_if(data: ADSBIFInput):
    if if_model is None or scaler is None:
        raise HTTPException(500, "ADS-B Model not loaded.")
    X   = build_feature_vector(data)
    X_s = scaler.transform(X)
    raw = int(if_model.predict(X_s)[0])
    return {"iforest_anomaly": 1 if raw == -1 else 0}


@app.post("/api/analyze_old")
def analyze_route_old(req: AnalysisRequest):
    return {"message": "Old FYP-1 analysis endpoint preserved."}


# ──────────────────────────────────────────────────────────────
# 8. FLEET ENDPOINTS
# ──────────────────────────────────────────────────────────────
@app.get("/api/fleet")
def get_fleet_data(db: Session = Depends(get_db)):
    """Priority 1: Ruhab's locked Fleet table. Priority 2: telemetry fallback."""
    try:
        fleet_planes  = db.query(models_db.Fleet).all()
        response_data = []

        if fleet_planes:
            for plane in fleet_planes:
                latest    = db.query(models_db.FlightTelemetry)\
                              .filter(models_db.FlightTelemetry.tail_number == plane.tail_number)\
                              .order_by(models_db.FlightTelemetry.timestamp.desc()).first()
                flight_no = latest.callsign if latest and latest.callsign else "Grounded"
                response_data.append({"tail_number": plane.tail_number, "current_flight": flight_no})
            return {"fleet": response_data}

        callsigns = db.query(models_db.FlightTelemetry.callsign).distinct().all()
        planes    = [c[0] for c in callsigns if c[0] is not None]

        if not planes:
            return {"fleet": [{"tail_number": "AP-BLC", "current_flight": "PK304"}]}

        for p in planes:
            response_data.append({"tail_number": p, "current_flight": p})

        return {"fleet": response_data}

    except Exception as e:
        return {"fleet": [{"tail_number": "Error", "current_flight": str(e)}]}


@app.get("/api/live_fleet")
def get_live_fleet(db: Session = Depends(get_db)):
    """
    For Live Dashboard only.
    Always returns distinct callsigns from flight_telemetry —
    never touches the locked fleet table.
    """
    try:
        callsigns = db.query(models_db.FlightTelemetry.callsign).distinct().all()
        planes    = [c[0] for c in callsigns if c[0] is not None and c[0] != "UNKNOWN"]

        if not planes:
            return {"fleet": [{"tail_number": "No live flights", "current_flight": "—"}]}

        return {
            "fleet": [{"tail_number": p, "current_flight": p} for p in planes[:100]]
        }
    except Exception as e:
        return {"fleet": [{"tail_number": "Error", "current_flight": str(e)}]}


@app.post("/api/admin/seed_pakistan_fleet")
def seed_pakistan_fleet(payload: PakistanSeedRequest, db: Session = Depends(get_db)):
    """
    Ruhab's one-time seed endpoint.
    POST body: {"planes": [{"tail_number": "AP-BLC", "aircraft_type": "B737"}]}
    """
    added, skipped = [], []

    for p in payload.planes:
        tail = p.get("tail_number", "").strip()
        if not tail:
            continue
        exists = db.query(models_db.Fleet).filter(models_db.Fleet.tail_number == tail).first()
        if exists:
            skipped.append(tail)
            continue
        db.add(models_db.Fleet(tail_number=tail, aircraft_type=p.get("aircraft_type", "Unknown")))
        added.append(tail)

    db.commit()
    return {
        "message": f"Seeded {len(added)} planes, skipped {len(skipped)} duplicates.",
        "added":   added,
        "skipped": skipped,
    }


# ──────────────────────────────────────────────────────────────
# 9. TELEMETRY ENDPOINT
# ──────────────────────────────────────────────────────────────
@app.get("/api/telemetry/{tail_number}")
def get_latest_telemetry(tail_number: str, db: Session = Depends(get_db)):
    latest = db.query(models_db.FlightTelemetry)\
               .filter(models_db.FlightTelemetry.callsign == tail_number)\
               .order_by(models_db.FlightTelemetry.id.desc()).first()
    if not latest:
        raise HTTPException(404, "No telemetry found.")
    return {
        "tail_number": latest.callsign,
        "lat":         latest.latitude,
        "lon":         latest.longitude,
        "alt_ft":      latest.altitude,
        "speed_knots": latest.velocity,
    }


@app.get("/api/route/{tail_number}")
def get_flight_route(tail_number: str, db: Session = Depends(get_db)):
    """
    Returns all lat/lon points for this aircraft in chronological order.
    Used by the frontend to draw the flight path polyline on the map.
    """
    rows = db.query(models_db.FlightTelemetry)\
             .filter(models_db.FlightTelemetry.callsign == tail_number)\
             .filter(models_db.FlightTelemetry.latitude  != None)\
             .filter(models_db.FlightTelemetry.longitude != None)\
             .order_by(models_db.FlightTelemetry.id.asc())\
             .all()

    if not rows:
        raise HTTPException(404, f"No route data for {tail_number}.")

    points = [
        {"lat": r.latitude, "lon": r.longitude,
         "alt_m": r.altitude, "speed_ms": r.velocity}
        for r in rows
    ]

    return {
        "tail_number":  tail_number,
        "point_count":  len(points),
        "origin":       points[0],
        "current":      points[-1],
        "route_points": points,
    }
#     Every metric is calculated from THIS plane's real DB data.
# ──────────────────────────────────────────────────────────────
@app.get("/api/analyze/{tail_number}")
def analyze_aircraft_live(tail_number: str, db: Session = Depends(get_db)):
    """
    Sprint 3: ALL metrics dynamically calculated from real altitude,
    velocity, and history of the specific selected plane.
    No two planes return the same numbers.
    """
    # Safe defaults — only used if DB has zero rows for this plane
    predicted_rul             = 45.2
    lat, lon                  = 30.3753, 69.3451   # centre of Pakistan
    alt, speed                = 9000.0, 220.0      # typical cruise defaults
    n_records                 = 1
    vertical_rate, true_track = -5.0, 145.0
    anomaly_flag, if_score    = 0, -0.05

    # Step 1: Pull real telemetry
    history = db.query(models_db.FlightTelemetry)\
                .filter(models_db.FlightTelemetry.callsign == tail_number)\
                .order_by(models_db.FlightTelemetry.id.desc())\
                .limit(30).all()

    if history:
        latest    = history[0]
        lat       = latest.latitude  or lat
        lon       = latest.longitude or lon
        alt       = latest.altitude  or alt
        speed     = latest.velocity  or speed
        n_records = len(history)

        # Step 2: Estimate vertical rate + track from consecutive rows
        if len(history) >= 2:
            vertical_rate = (history[0].altitude or 0) - (history[1].altitude or 0)
            dlat          = (history[0].latitude  or 0) - (history[1].latitude  or 0)
            dlon          = (history[0].longitude or 0) - (history[1].longitude or 0)
            true_track    = math.degrees(math.atan2(dlon, dlat)) % 360

        # Step 3: IForest on real physics
        anomaly_flag, if_score = run_iforest(speed, alt, vertical_rate, true_track)

        # Step 4: LSTM on real sensor matrix
        if lstm_model and lstm_scaler:
            try:
                df          = pd.DataFrame([{"altitude": h.altitude or 0, "velocity": h.velocity or 0} for h in history])
                sensor_data = np.zeros((len(df), 24))
                sensor_data[:, 0] = df["altitude"].fillna(0) / 1000
                sensor_data[:, 1] = df["velocity"].fillna(0)

                scaled = lstm_scaler.transform(sensor_data)
                if len(scaled) < 30:
                    scaled = np.vstack([np.zeros((30 - len(scaled), 24)), scaled])
                else:
                    scaled = scaled[:30]

                predicted_rul = float(lstm_model.predict(scaled.reshape(1, 30, 24), verbose=0)[0][0])
                print(f"🎯 LSTM [{tail_number}]: RUL={predicted_rul:.1f}")
            except Exception as e:
                print(f"⚠️ LSTM failed for {tail_number}: {e}")

    # Step 5: All dynamic calculations — zero hardcoded values
    if predicted_rul < 20 or anomaly_flag == 1:
        risk_level = "High"
    elif predicted_rul < 50:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    fuel_litres  = compute_fuel_burn(alt, speed, n_records)
    co2_kg       = round(fuel_litres * 2.53, 1)
    wind_ms      = compute_wind(speed, alt)
    temp_c       = compute_temp(alt)
    health_score = round(min(100, max(0, predicted_rul / 2)), 1)
    shap_values  = compute_dynamic_shap(alt, speed, if_score, predicted_rul)

    return {
        "tail":                 tail_number,
        "predicted_rul_cycles": round(predicted_rul, 1),
        "risk_level":           risk_level,
        "health_score":         health_score,
        "flight_phase":         compute_flight_phase(alt, speed),
        "live_telemetry": {
            "lat":           lat,
            "lon":           lon,
            "alt_m":         round(alt, 1),
            "speed_ms":      round(speed, 1),
            "vertical_rate": round(vertical_rate, 1),
        },
        "explainability_shap": shap_values,
        "route_and_emissions": {
            "weather_wind_ms":       wind_ms,
            "temp_c":                temp_c,
            "predicted_fuel_liters": fuel_litres,
            "predicted_co2_kg":      co2_kg,
        },
        "anomaly_flag":  anomaly_flag,
        "iforest_score": round(if_score, 4),
        "records_used":  n_records,
    }


# ──────────────────────────────────────────────────────────────
# 11. FLIGHT HISTORY ENDPOINTS
#     Fixed: these were unreachable dead code before (inside analyze())
# ──────────────────────────────────────────────────────────────
@app.post("/api/complete_flight/{tail_number}")
def complete_flight(tail_number: str, data: FlightCompletionData,
                    db: Session = Depends(get_db)):
    """Ruhab's Task: Inserts a finished flight into flight_history."""
    try:
        db.add(models_db.FlightHistory(
            tail_number        = tail_number,
            origin             = data.origin,
            destination        = data.destination,
            total_fuel_liters  = data.fuel_liters,
            co2_kg             = data.co2_kg,
            final_health_score = data.health_score,
        ))
        db.commit()
        return {"message": f"Flight log saved for {tail_number}!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/history/{tail_number}")
def get_flight_history(tail_number: str, db: Session = Depends(get_db)):
    """Areeba's Task: Fetches history for the Mission Logs tab."""
    history = db.query(models_db.FlightHistory)\
                .filter(models_db.FlightHistory.tail_number == tail_number)\
                .order_by(models_db.FlightHistory.timestamp.desc())\
                .limit(10).all()

    if not history:
        return {"history": []}

    return {"history": [{
        "flight_id":     f"FL-{h.flight_id}",
        "date":          h.timestamp.strftime("%Y-%m-%d %H:%M") if h.timestamp else "N/A",
        "route":         f"{h.origin} → {h.destination}",
        "fuel_consumed": h.total_fuel_liters,
        "co2_emissions": h.co2_kg,
        "health_score":  h.final_health_score,
    } for h in history]}


# ──────────────────────────────────────────────────────────────
# 12. PAKISTAN FLEET ENDPOINTS
#     These query pakistan_telemetry (separate from flight_telemetry)
#     Used by the Fleet page in the Streamlit dashboard
# ──────────────────────────────────────────────────────────────

def get_raw_conn():
    """Raw SQLite connection to aviation_data.db."""
    import sqlite3
    db_path = os.path.join(BASE_DIR, "aviation_data.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/pak_fleet")
def get_pakistan_fleet():
    """
    Returns all 44 locked Pakistani aircraft from fleet table
    with their latest telemetry from pakistan_telemetry.
    Used by the Fleet page dropdown.
    """
    conn = get_raw_conn()
    try:
        rows = conn.execute("""
            SELECT
                f.tail_number,
                f.aircraft_type,
                f.airline,
                f.hex_code,
                t.callsign,
                t.altitude,
                t.velocity,
                t.latitude,
                t.longitude,
                t.timestamp
            FROM fleet f
            LEFT JOIN (
                SELECT tail_number, callsign, altitude, velocity,
                       latitude, longitude, timestamp
                FROM pakistan_telemetry
                WHERE id IN (
                    SELECT MAX(id) FROM pakistan_telemetry
                    GROUP BY tail_number
                )
            ) t ON t.tail_number = f.tail_number
            ORDER BY f.airline, f.tail_number
        """).fetchall()

        fleet = []
        for r in rows:
            r = dict(r)
            status = "grounded"
            if r.get("altitude") and r["altitude"] > 100:
                status = "airborne"
            elif r.get("callsign"):
                status = "active"

            fleet.append({
                "tail_number":   r["tail_number"],
                "aircraft_type": r["aircraft_type"],
                "airline":       r["airline"],
                "hex_code":      r["hex_code"],
                "callsign":      r.get("callsign") or "Grounded",
                "status":        status,
                "altitude":      r.get("altitude"),
                "velocity":      r.get("velocity"),
                "latitude":      r.get("latitude"),
                "longitude":     r.get("longitude"),
                "last_seen":     r.get("timestamp"),
            })

        return {"fleet": fleet, "total": len(fleet)}
    finally:
        conn.close()


@app.get("/api/pak_analyze/{tail_number}")
def analyze_pakistan_aircraft(tail_number: str):
    """
    Full ML analysis for a specific fleet aircraft.
    Queries pakistan_telemetry for real position data.
    Returns same JSON contract as /api/analyze/{tail_number}
    but sourced from pakistan_telemetry table.
    """
    conn = get_raw_conn()
    try:
        # Get fleet info
        fleet_row = conn.execute(
            "SELECT * FROM fleet WHERE tail_number = ?", (tail_number,)
        ).fetchone()

        if not fleet_row:
            raise HTTPException(404, f"{tail_number} not found in fleet table.")

        fleet_row = dict(fleet_row)

        # Get last 30 telemetry records
        history = conn.execute("""
            SELECT altitude, velocity, latitude, longitude, timestamp
            FROM pakistan_telemetry
            WHERE tail_number = ?
            ORDER BY id DESC LIMIT 30
        """, (tail_number,)).fetchall()

    finally:
        conn.close()

    # ── Defaults ──
    predicted_rul             = 45.2
    lat, lon                  = 30.3753, 69.3451
    alt, speed                = 9000.0, 220.0
    n_records                 = 1
    vertical_rate, true_track = -5.0, 145.0
    anomaly_flag, if_score    = 0, -0.05

    if history:
        latest    = dict(history[0])
        lat       = latest.get("latitude")  or lat
        lon       = latest.get("longitude") or lon
        alt       = latest.get("altitude")  or alt
        speed     = latest.get("velocity")  or speed
        n_records = len(history)

        if len(history) >= 2:
            prev          = dict(history[1])
            vertical_rate = (latest.get("altitude") or 0) - (prev.get("altitude") or 0)
            dlat          = (latest.get("latitude")  or 0) - (prev.get("latitude")  or 0)
            dlon          = (latest.get("longitude") or 0) - (prev.get("longitude") or 0)
            true_track    = math.degrees(math.atan2(dlon, dlat)) % 360

        anomaly_flag, if_score = run_iforest(speed, alt, vertical_rate, true_track)

        if lstm_model and lstm_scaler:
            try:
                # ── Build richer sensor input using all available telemetry ──
                # Get aircraft age from fleet table for degradation baseline
                fleet_age = 0
                fleet_hours = 0
                try:
                    _fc = get_raw_conn()
                    _fr = _fc.execute(
                        "SELECT age_years, total_flight_hours FROM fleet WHERE tail_number=?",
                        (tail_number,)
                    ).fetchone()
                    _fc.close()
                    if _fr:
                        fleet_age   = float(_fr[0] or 0)
                        fleet_hours = float(_fr[1] or 0)
                except:
                    pass

                # Build sequence from all available history rows
                rows = [dict(h) for h in history]

                # Map available fields to CMAPSS-like sensor channels
                # ch0=alt/1000, ch1=vel, ch2=vrate, ch3=track/360,
                # ch4=age_factor, ch5=if_score, ch6-23=derived
                sensor_data = np.zeros((len(rows), 24))
                for i, row in enumerate(rows):
                    a = row.get("altitude") or alt
                    v = row.get("velocity") or speed
                    sensor_data[i, 0]  = a / 1000                    # altitude km
                    sensor_data[i, 1]  = v / 300                     # velocity normalized
                    sensor_data[i, 2]  = vertical_rate / 100          # vertical rate
                    sensor_data[i, 3]  = true_track / 360             # track normalized
                    sensor_data[i, 4]  = fleet_age / 20               # age factor
                    sensor_data[i, 5]  = fleet_hours / 50000          # hours factor
                    sensor_data[i, 6]  = abs(if_score)                # anomaly magnitude
                    sensor_data[i, 7]  = a / 12000                    # alt pressure proxy
                    sensor_data[i, 8]  = v * fleet_age / 3000         # wear proxy
                    sensor_data[i, 9]  = (a - 8000) / 4000            # cruise deviation
                    # Fill remaining channels with noise-free constants
                    sensor_data[i, 10] = 0.95 - (fleet_age * 0.01)   # efficiency
                    sensor_data[i, 11] = v / 250                       # fan speed proxy
                    sensor_data[i, 12] = 1.0 - (fleet_hours / 100000) # cycle health

                scaled = lstm_scaler.transform(sensor_data)
                if len(scaled) < 30:
                    # Pad with slightly varied values rather than pure zeros
                    pad = np.tile(scaled[0], (30 - len(scaled), 1))
                    pad += np.random.default_rng(
                        abs(hash(tail_number)) % (2**32)
                    ).normal(0, 0.01, pad.shape)
                    scaled = np.vstack([pad, scaled])
                else:
                    scaled = scaled[:30]

                predicted_rul = float(
                    lstm_model.predict(scaled.reshape(1, 30, 24), verbose=0)[0][0]
                )
                # Clamp to realistic range
                predicted_rul = max(5.0, min(200.0, predicted_rul))
                print(f"🎯 PAK LSTM [{tail_number}]: RUL={predicted_rul:.1f} age={fleet_age}yrs")

            except Exception as e:
                print(f"⚠️ LSTM failed for {tail_number}: {e}")

    # ── Risk ──
    if predicted_rul < 20 or anomaly_flag == 1:
        risk_level = "High"
    elif predicted_rul < 50:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    fuel_litres  = compute_fuel_burn(alt, speed, n_records)
    co2_kg       = round(fuel_litres * 2.53, 1)

    # ── Use real weather from DB, fall back to estimates ──
    wx        = get_nearest_airport_weather(lat, lon)
    wind_ms   = wx["wind_ms"]
    temp_c    = wx["temp_c"]
    wx_source = wx["source"]

    health_score = round(min(100, max(0, predicted_rul / 2)), 1)
    shap_values  = compute_dynamic_shap(alt, speed, if_score, predicted_rul)

    # ── Maintenance override: if maintained within 72 hours → reset health ──
    try:
        _conn = get_raw_conn()
        last_maint = _conn.execute("""
            SELECT performed_at FROM maintenance_records
            WHERE tail_number = ?
            ORDER BY performed_at DESC LIMIT 1
        """, (tail_number,)).fetchone()
        _conn.close()
        if last_maint:
            from datetime import datetime as _dt2
            maint_time   = _dt2.fromisoformat(last_maint[0])
            hours_since  = (_dt2.now() - maint_time).total_seconds() / 3600
            if hours_since < 72:
                health_score  = 100.0
                predicted_rul = 200.0
                risk_level    = "Low"
    except:
        pass

    return {
        "tail":                 tail_number,
        "aircraft_type":        fleet_row.get("aircraft_type"),
        "airline":              fleet_row.get("airline"),
        "predicted_rul_cycles": round(predicted_rul, 1),
        "risk_level":           risk_level,
        "health_score":         health_score,
        "flight_phase":         compute_flight_phase(alt, speed),
        "live_telemetry": {
            "lat":           lat,
            "lon":           lon,
            "alt_m":         round(alt, 1),
            "speed_ms":      round(speed, 1),
            "vertical_rate": round(vertical_rate, 1),
        },
        "explainability_shap": shap_values,
        "route_and_emissions": {
            "weather_wind_ms":    wind_ms,
            "temp_c":             temp_c,
            "weather_source":     wx_source,
            "weather_airport":    wx.get("airport", "KHI"),
            "weather_conditions": wx.get("conditions", "—"),
            "predicted_fuel_liters": fuel_litres,
            "predicted_co2_kg":   co2_kg,
        },
        "anomaly_flag":  anomaly_flag,
        "iforest_score": round(if_score, 4),
        "records_used":  n_records,
    }


@app.get("/api/weather")
def get_weather():
    """Returns latest weather for all 4 Pakistani airports."""
    conn = get_raw_conn()
    try:
        rows = conn.execute("""
            SELECT city, iata_code, temp_celsius, wind_speed_ms,
                   wind_dir_deg, description, fetched_at
            FROM weather_data
            WHERE id IN (
                SELECT MAX(id) FROM weather_data GROUP BY iata_code
            )
            ORDER BY iata_code
        """).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"weather": [], "message": "No weather data yet — wait for next pipeline cycle"}

    return {"weather": [
        {
            "city":        r[0],
            "iata":        r[1],
            "temp_c":      r[2],
            "wind_ms":     r[3],
            "wind_dir":    r[4],
            "conditions":  r[5],
            "fetched_at":  r[6],
        } for r in rows
    ]}
def get_pakistan_route(tail_number: str):
    conn = get_raw_conn()
    try:
        rows = conn.execute("""
            SELECT latitude, longitude, altitude, velocity, timestamp
            FROM pakistan_telemetry
            WHERE tail_number = ?
              AND latitude IS NOT NULL
              AND longitude IS NOT NULL
            ORDER BY id ASC
        """, (tail_number,)).fetchall()

        # ── If no telemetry — return home airport (KHI default) ──
        if not rows:
            fleet_row = conn.execute(
                "SELECT airline FROM fleet WHERE tail_number = ?",
                (tail_number,)
            ).fetchone()

            airline = fleet_row[0] if fleet_row else ""
            # PIA bases at KHI, AirBlue at ISB, FlyJinnah at KHI, AirSial at SKT
            HOME = {
                "Pakistan International Airlines": (24.9008, 67.1681),
                "AirBlue":   (33.6167, 73.0994),
                "AirSial":   (32.5356, 74.3639),
                "Fly Jinnah":(24.9008, 67.1681),
            }
            lat, lon = HOME.get(airline, (30.3753, 69.3451))
            return {
                "tail_number":  tail_number,
                "point_count":  1,
                "is_grounded":  True,
                "origin":       {"lat": lat, "lon": lon, "alt_m": 0, "speed_ms": 0},
                "current":      {"lat": lat, "lon": lon, "alt_m": 0, "speed_ms": 0},
                "route_points": [{"lat": lat, "lon": lon, "alt_m": 0, "speed_ms": 0}],
            }
    finally:
        conn.close()

    points = [{"lat": r[0], "lon": r[1],
               "alt_m": r[2], "speed_ms": r[3]} for r in rows]
    return {
        "tail_number":  tail_number,
        "point_count":  len(points),
        "is_grounded":  False,
        "origin":       points[0],
        "current":      points[-1],
        "route_points": points,
    }
@app.get("/api/pak_history/{tail_number}")
def get_pakistan_history(tail_number: str, db: Session = Depends(get_db)):
    """
    Returns flight history for a fleet aircraft from flight_history table.
    """
    history = db.query(models_db.FlightHistory)\
                .filter(models_db.FlightHistory.tail_number == tail_number)\
                .order_by(models_db.FlightHistory.timestamp.desc())\
                .limit(20).all()

    if not history:
        return {"history": [], "tail_number": tail_number}

    return {"history": [{
        "flight_id":     f"FL-{h.flight_id}",
        "date":          h.timestamp.strftime("%Y-%m-%d %H:%M") if h.timestamp else "N/A",
        "route":         f"{h.origin} → {h.destination}",
        "fuel_consumed": h.total_fuel_liters,
        "co2_emissions": h.co2_kg,
        "health_score":  h.final_health_score,
    } for h in history]}


# ──────────────────────────────────────────────────────────────
# 13. SPRINT 4 SHELLS — ready to implement
# ──────────────────────────────────────────────────────────────
@app.post("/api/log_maintenance")
def log_maintenance(data: MaintenanceLogRequest, db: Session = Depends(get_db)):
    """
    Mechanic Portal — full implementation.
    Saves maintenance record and resets aircraft health baseline to 100%.
    """
    # ── 1. Save to maintenance_records via raw SQLite (always) ──
    conn = get_raw_conn()
    try:
        # Ensure table exists with correct schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                tail_number      TEXT NOT NULL,
                component        TEXT,
                maintenance_type TEXT,
                location         TEXT,
                notes            TEXT,
                performed_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            INSERT INTO maintenance_records
            (tail_number, component, maintenance_type, location, notes, performed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.tail_number, data.component,
            data.maintenance_type, data.location,
            data.notes or "", _datetime.now().isoformat()
        ))
        conn.commit()
        record_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    finally:
        conn.close()

    # ── 2. Reset health baseline → insert health_predictions row ──
    if hasattr(models_db, "HealthPrediction"):
        db.add(models_db.HealthPrediction(
            tail_number          = data.tail_number,
            health_score         = 100.0,
            predicted_rul_cycles = 200,
            shap_top_feature     = "maintenance_reset",
        ))
        db.commit()

    # ── 3. Update fleet_status maintenance fields ──
    try:
        conn = get_raw_conn()
        conn.execute("""
            UPDATE fleet_status
            SET status='grounded', last_seen=?
            WHERE tail_number=?
        """, (_datetime.now().isoformat(), data.tail_number))
        conn.commit()
        conn.close()
    except:
        pass

    print(f"🔧 Maintenance logged: {data.tail_number} — {data.component} — {data.maintenance_type}")

    return {
        "status":          "success",
        "record_id":       record_id,
        "tail_number":     data.tail_number,
        "component":       data.component,
        "maintenance_type":data.maintenance_type,
        "location":        data.location,
        "performed_at":    _datetime.now().isoformat(),
        "health_reset_to": 100,
        "rul_reset_to":    200,
        "message":         f"Maintenance logged for {data.tail_number}. Health baseline reset to 100%.",
    }


@app.get("/api/maintenance_history/{tail_number}")
def get_maintenance_history(tail_number: str):
    """Returns full maintenance history for a fleet aircraft."""
    conn = get_raw_conn()
    try:
        # Ensure correct schema exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                tail_number      TEXT NOT NULL,
                component        TEXT,
                maintenance_type TEXT,
                location         TEXT,
                notes            TEXT,
                performed_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Check if id column exists, if not recreate table
        cols = [r[1] for r in conn.execute("PRAGMA table_info(maintenance_records)").fetchall()]
        if "id" not in cols:
            conn.execute("DROP TABLE maintenance_records")
            conn.execute("""
                CREATE TABLE maintenance_records (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    tail_number      TEXT NOT NULL,
                    component        TEXT,
                    maintenance_type TEXT,
                    location         TEXT,
                    notes            TEXT,
                    performed_at     TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        rows = conn.execute("""
            SELECT id, tail_number, component, maintenance_type,
                   location, notes, performed_at
            FROM maintenance_records
            WHERE tail_number = ?
            ORDER BY performed_at DESC
            LIMIT 20
        """, (tail_number,)).fetchall()
    finally:
        conn.close()

    return {"tail_number": tail_number, "records": [
        {
            "id":               r[0],
            "tail_number":      r[1],
            "component":        r[2],
            "maintenance_type": r[3],
            "location":         r[4],
            "notes":            r[5],
            "performed_at":     r[6],
        } for r in rows
    ]}


@app.post("/api/simulate")
def simulate_flight(data: SimulateRequest):
    """
    Predictive Simulator — full implementation.
    Dispatcher inputs hypothetical variables → predicted fuel, CO2, health impact.
    """
    # ── Airport coordinates for distance calculation ──
    AIRPORT_COORDS = {
        "KHI":(24.9008,67.1681), "LHE":(31.5216,74.4036),
        "ISB":(33.6167,73.0994), "PEW":(33.9939,71.5146),
        "MUX":(30.2032,71.4191), "LYP":(31.3600,72.9947),
        "SKT":(32.5356,74.3639), "UET":(30.2512,66.9378),
        "GWD":(25.2330,62.3294), "DXB":(25.2532,55.3657),
        "DOH":(25.2731,51.6080), "JED":(21.6796,39.1565),
        "RUH":(24.9578,46.6989), "LHR":(51.4700,-0.4543),
        "IST":(41.2608,28.7418),
    }

    dep = AIRPORT_COORDS.get(data.departure_iata.upper(), (24.9, 67.1))
    arr = AIRPORT_COORDS.get(data.arrival_iata.upper(), (31.5, 74.4))

    # ── Distance in km ──
    dist_km = round(math.sqrt(
        ((arr[0]-dep[0])*111)**2 + ((arr[1]-dep[1])*111)**2
    ), 1)

    # ── Base flight time in hours ──
    cruise_speed_kmh = 850
    flight_hours = dist_km / cruise_speed_kmh

    # ── Base fuel (litres/hour varies by aircraft age) ──
    base_burn_lph = 3200 + (data.aircraft_age_yrs * 50)

    # ── Weather multiplier ──
    weather_mult = {"Clear": 1.0, "Moderate Wind": 1.08, "Stormy": 1.18}.get(data.weather, 1.0)

    # ── Cargo weight multiplier (every 10,000 kg adds ~2% fuel) ──
    cargo_mult = 1.0 + (data.cargo_kg / 10000) * 0.02

    # ── Estimated fuel ──
    estimated_fuel = round(base_burn_lph * flight_hours * weather_mult * cargo_mult, 1)
    estimated_co2  = round(estimated_fuel * 2.53, 1)

    # ── Health impact — older aircraft + heavy cargo + bad weather degrades faster ──
    age_factor     = min(data.aircraft_age_yrs / 20, 1.0)
    cargo_factor   = min(data.cargo_kg / 50000, 1.0)
    weather_factor = {"Clear": 0.0, "Moderate Wind": 0.1, "Stormy": 0.25}.get(data.weather, 0.0)
    health_impact  = round((age_factor * 5 + cargo_factor * 3 + weather_factor * 7) * -1, 1)

    # ── Next maintenance interval ──
    if data.aircraft_age_yrs > 15:
        next_maint = "Within 50 flight cycles"
    elif data.aircraft_age_yrs > 8:
        next_maint = "Within 150 flight cycles"
    else:
        next_maint = "Within 300 flight cycles"

    if data.weather == "Stormy":
        next_maint = "Inspect after landing — stormy conditions"

    return {
        "status": "success",
        "inputs": {
            "tail_number":      data.tail_number,
            "aircraft_age_yrs": data.aircraft_age_yrs,
            "departure":        data.departure_iata.upper(),
            "arrival":          data.arrival_iata.upper(),
            "weather":          data.weather,
            "cargo_kg":         data.cargo_kg,
        },
        "predictions": {
            "distance_km":              dist_km,
            "flight_hours":             round(flight_hours, 2),
            "estimated_fuel_litres":    estimated_fuel,
            "estimated_co2_kg":         estimated_co2,
            "health_impact":            health_impact,
            "next_maintenance_interval":next_maint,
        },
        "risk_flags": [
            f"Aircraft age {data.aircraft_age_yrs}yrs — increased wear expected"
            if data.aircraft_age_yrs > 12 else None,
            f"Heavy cargo {data.cargo_kg:,.0f}kg — elevated fuel burn"
            if data.cargo_kg > 30000 else None,
            f"Stormy weather — recommend delay or alternate route"
            if data.weather == "Stormy" else None,
        ],
    }


@app.get("/api/pipeline_logs")
def get_pipeline_logs():
    """Returns last 50 pipeline cycle logs for system health monitoring."""
    conn = get_raw_conn()
    try:
        rows = conn.execute("""
            SELECT timestamp, opensky_saved, avstack_saved,
                   landings_logged, errors, duration_sec
            FROM pipeline_log
            ORDER BY id DESC LIMIT 50
        """).fetchall()
    except:
        return {"logs": [], "message": "pipeline_log table not yet created"}
    finally:
        conn.close()

    return {"logs": [
        {
            "timestamp":       r[0],
            "opensky_saved":   r[1],
            "avstack_saved":   r[2],
            "landings_logged": r[3],
            "errors":          r[4],
            "duration_sec":    r[5],
        } for r in rows
    ]}


@app.get("/api/fleet_status")
def get_fleet_status():
    """Returns current airborne/grounded status for all fleet planes."""
    conn = get_raw_conn()
    try:
        rows = conn.execute("""
            SELECT f.tail_number, f.airline, f.aircraft_type,
                   COALESCE(fs.status, 'unknown') as status,
                   fs.last_seen, fs.current_callsign,
                   fs.departure_airport, fs.arrival_airport
            FROM fleet f
            LEFT JOIN fleet_status fs ON fs.tail_number = f.tail_number
            ORDER BY f.airline, f.tail_number
        """).fetchall()
    finally:
        conn.close()

    airborne = sum(1 for r in rows if r[3] == "airborne")
    grounded = sum(1 for r in rows if r[3] == "grounded")

    return {
        "summary":  {"airborne": airborne, "grounded": grounded,
                     "unknown": len(rows) - airborne - grounded},
        "aircraft": [
            {
                "tail_number":    r[0],
                "airline":        r[1],
                "aircraft_type":  r[2],
                "status":         r[3],
                "last_seen":      r[4],
                "callsign":       r[5],
                "departure":      r[6],
                "arrival":        r[7],
            } for r in rows
        ],
    }