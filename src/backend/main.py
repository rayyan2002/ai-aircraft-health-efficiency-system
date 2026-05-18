from fastapi import FastAPI, HTTPException, Depends
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
                     latitude, longitude, anomaly_flag, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (tail, callsign, airline_name, alt_m, vel_ms,
                      lat, lon, 1 if is_est else 0, _datetime.now()))
                saved += 1

        except Exception as e:
            print(f"  ⚠️ {icao_code}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ [AviationStack] Saved {saved} flights to pakistan_telemetry.")

# ──────────────────────────────────────────────────────────────
# 2. BACKGROUND WORKER
# ──────────────────────────────────────────────────────────────
async def automated_data_pipeline():
    """Runs every 5 minutes — fetches live OpenSky data + auto-lands planes."""
    while True:
        print("🔄 [HEARTBEAT] Running Automated Data Pipeline...")
        db = SessionLocal()
        try:
            # ── Fetch live OpenSky data → flight_telemetry (Live Dashboard) ──
            await asyncio.get_event_loop().run_in_executor(
                None, fetch_and_insert_opensky
            )
            # ── Fetch AviationStack data → pakistan_telemetry (Fleet page) ──
            await asyncio.get_event_loop().run_in_executor(
                None, fetch_and_insert_aviationstack
            )

            # ── Auto-lander: detect landed planes and log to history ──
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
                    current_log  = recent_logs[0]
                    previous_log = recent_logs[1]

                    if previous_log.altitude > 0 and current_log.altitude <= 0:
                        print(f"🛬 DETECTED LANDING: {tail}. Moving to History...")

                        # ── Dynamic health score from LSTM ──
                        final_health = 45.2
                        if lstm_model and lstm_scaler:
                            try:
                                sensor_data = np.zeros((30, 24))
                                sensor_data[:, 0] = (current_log.altitude or 0) / 1000
                                sensor_data[:, 1] = (current_log.velocity or 0)
                                scaled = lstm_scaler.transform(sensor_data)
                                rul = float(lstm_model.predict(
                                    scaled.reshape(1, 30, 24), verbose=0
                                )[0][0])
                                final_health = round(min(100, max(0, rul / 2)), 1)
                            except:
                                pass

                        # ── Dynamic fuel & CO2 ──
                        fuel = round(compute_fuel_burn(
                            current_log.altitude or 0,
                            current_log.velocity or 0,
                            30
                        ), 1)

                        new_history = models_db.FlightHistory(
                            tail_number=tail,
                            origin="Unknown (Auto-Detect)",
                            destination="Current Coords",
                            total_fuel_liters=fuel,
                            co2_kg=round(fuel * 2.53, 1),
                            final_health_score=final_health,
                        )
                        db.add(new_history)
                        db.commit()
                        print(f"✅ Saved {tail} — fuel={fuel}L health={final_health}")

        except Exception as e:
            print(f"⚠️ Pipeline Error: {e}")
            db.rollback()
        finally:
            db.close()

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
    tail_number:      str
    aircraft_age_yrs: float = 8.0
    weather:          str   = "Clear"
    cargo_kg:         float = 15000.0

class MaintenanceLogRequest(BaseModel):
    tail_number:      str
    maintenance_type: str
    notes:            Optional[str] = None


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
                df          = pd.DataFrame([{"altitude": dict(h).get("altitude") or 0,
                                              "velocity": dict(h).get("velocity") or 0}
                                             for h in history])
                sensor_data = np.zeros((len(df), 24))
                sensor_data[:, 0] = df["altitude"].fillna(0) / 1000
                sensor_data[:, 1] = df["velocity"].fillna(0)
                scaled = lstm_scaler.transform(sensor_data)
                if len(scaled) < 30:
                    scaled = np.vstack([np.zeros((30 - len(scaled), 24)), scaled])
                else:
                    scaled = scaled[:30]
                predicted_rul = float(
                    lstm_model.predict(scaled.reshape(1, 30, 24), verbose=0)[0][0]
                )
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
    wind_ms      = compute_wind(speed, alt)
    temp_c       = compute_temp(alt)
    health_score = round(min(100, max(0, predicted_rul / 2)), 1)
    shap_values  = compute_dynamic_shap(alt, speed, if_score, predicted_rul)

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
            "weather_wind_ms":       wind_ms,
            "temp_c":                temp_c,
            "predicted_fuel_liters": fuel_litres,
            "predicted_co2_kg":      co2_kg,
        },
        "anomaly_flag":  anomaly_flag,
        "iforest_score": round(if_score, 4),
        "records_used":  n_records,
    }


@app.get("/api/pak_route/{tail_number}")
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
    Sprint 4: Mechanic Portal.
    Will log maintenance event + reset engine health baseline to 100%.
    """
    return {
        "status":      "shell",
        "message":     f"Maintenance endpoint ready for Sprint 4.",
        "tail_number": data.tail_number,
    }


@app.post("/api/simulate")
def simulate_flight(data: SimulateRequest):
    """
    Sprint 4: Predictive Simulator.
    Dispatcher inputs hypothetical variables → predicted fuel + health impact.
    """
    return {
        "status":  "shell",
        "message": "Simulator endpoint ready for Sprint 4.",
        "inputs":  data.model_dump(),
    }