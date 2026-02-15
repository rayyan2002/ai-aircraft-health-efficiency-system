from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import numpy as np
import joblib

# ---------------- CONFIG ----------------
IF_MODEL_PATH = "models/adsb_iforest.pkl"
SCALER_PATH   = "models/adsb_if_scaler.pkl"

CMAPSS_MODEL_PATH = "models/cmapss_health_rf.pkl"

# Hardcoded demo registry: ICAO24 / registration -> aircraft type
AIRCRAFT_REGISTRY = {
    "800736": "Boeing 737-800",
    "A6-EAD": "Airbus A380-800",
    "ABC123": "Airbus A320",
}

# ---------------- APP ----------------
app = FastAPI(
    title="Aircraft Health & Efficiency API",
    description="ADS-B anomaly + CMAPSS engine health services",
    version="1.0.0",
)

# ---------------- LOAD MODELS ----------------
# ADS-B models
try:
    if_model = joblib.load(IF_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Isolation Forest and scaler loaded.")
except Exception as e:
    print(f"❌ Error loading ADS-B model or scaler: {e}")
    if_model = None
    scaler = None

# CMAPSS model
try:
    cmapss_model = joblib.load(CMAPSS_MODEL_PATH)
    print("✅ CMAPSS health model loaded.")
except Exception as e:
    print(f"❌ Error loading CMAPSS model: {e}")
    cmapss_model = None

# ---------------- Pydantic SCHEMAS ----------------
class ADSBIFInput(BaseModel):
    velocity: float
    baro_altitude: float
    vertical_rate: float
    true_track: float
    icao24: Optional[str] = None
    callsign: Optional[str] = None
    origin_country: Optional[str] = None


class ADSBIFPrediction(BaseModel):
    iforest_anomaly: int          # 0 = normal, 1 = anomaly
    iforest_score: float          # lower = more anomalous
    risk_level: str               # e.g. "Low" / "High"
    message: str


class CMAPSSInput(BaseModel):
    sensor_2: float
    sensor_3: float
    sensor_4: float
    cycle: float
    engine_id: Optional[int] = None


class CMAPSSPrediction(BaseModel):
    health_index_pred: float
    health_status: str
    message: str


# High‑level analysis request from frontend
class AnalysisRequest(BaseModel):
    aircraft: str
    departure_airport: str
    arrival_airport: str
    weather_conditions: str

    # NEW: extra context fields for FYP-1
    aircraft_id: Optional[str] = None          # ICAO24 or registration
    aircraft_age_years: Optional[float] = None
    flight_hours_input: Optional[float] = None
    last_maintenance_days: Optional[float] = None
    last_maintenance_type: Optional[str] = None

# ---------------- HELPER FUNCTIONS ----------------
def build_feature_vector(payload: ADSBIFInput) -> np.ndarray:
    values = [
        payload.velocity,
        payload.baro_altitude,
        payload.vertical_rate,
        payload.true_track,
    ]
    return np.array(values, dtype=float).reshape(1, -1)


def map_risk(if_label: int) -> str:
    return "High" if if_label == 1 else "Low"


def build_cmapss_vector(payload: CMAPSSInput) -> np.ndarray:
    values = [
        payload.sensor_2,
        payload.sensor_3,
        payload.sensor_4,
        payload.cycle,
    ]
    return np.array(values, dtype=float).reshape(1, -1)


def map_health_status(health_index: float) -> str:
    if health_index < 0.3:
        return "Low"
    elif health_index < 0.6:
        return "Medium"
    else:
        return "High"


def resolve_aircraft_type(aircraft_id: Optional[str], fallback_type: str) -> tuple[str, bool]:
    """
    Map a unique aircraft ID (ICAO24 / registration) to an aircraft type.
    Returns (aircraft_type, is_exact_mapping).
    """
    if aircraft_id and aircraft_id in AIRCRAFT_REGISTRY:
        return AIRCRAFT_REGISTRY[aircraft_id], True
    return fallback_type, False

# ---------------- BASE ROUTES (for direct model testing) ----------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "ADS-B Isolation Forest anomaly + CMAPSS engine health API running",
    }


@app.post("/predict_adsb_if", response_model=ADSBIFPrediction)
def predict_adsb_if(data: ADSBIFInput):
    if if_model is None or scaler is None:
        raise HTTPException(status_code=500, detail="Model or scaler not loaded on server.")

    X = build_feature_vector(data)

    try:
        X_scaled = scaler.transform(X)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scaling error: {e}")

    try:
        raw_label = int(if_model.predict(X_scaled)[0])     # 1 normal, -1 anomaly
        score = float(if_model.score_samples(X_scaled)[0]) # lower = more anomalous
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model prediction error: {e}")

    iforest_anomaly = 1 if raw_label == -1 else 0
    risk = map_risk(iforest_anomaly)

    if iforest_anomaly == 1:
        msg = (
            "Potential anomalous flight state detected. "
            "Recommend additional monitoring or manual review of this aircraft."
        )
    else:
        msg = "Flight state appears within normal range based on Isolation Forest model."

    return ADSBIFPrediction(
        iforest_anomaly=iforest_anomaly,
        iforest_score=score,
        risk_level=risk,
        message=msg,
    )


@app.post("/predict_cmapss_health", response_model=CMAPSSPrediction)
def predict_cmapss_health(data: CMAPSSInput):
    if cmapss_model is None:
        raise HTTPException(status_code=500, detail="CMAPSS model not loaded on server.")

    X = build_cmapss_vector(data)

    try:
        health_pred = float(cmapss_model.predict(X)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CMAPSS prediction error: {e}")

    status = map_health_status(health_pred)

    if status == "Low":
        msg = (
            "Engine health is low. Recommend detailed inspection and planning "
            "for maintenance in the near term."
        )
    elif status == "Medium":
        msg = (
            "Engine health is moderate. Continue monitoring and plan checks in "
            "upcoming maintenance cycles."
        )
    else:
        msg = "Engine health appears good. Continue normal monitoring."

    return CMAPSSPrediction(
        health_index_pred=health_pred,
        health_status=status,
        message=msg,
    )

# ---------------- SUPPORT ENDPOINTS FOR FRONTEND ----------------
@app.get("/api/aircraft")
def get_aircraft():
    return {
        "aircraft": [
            "Boeing 737-800",
            "Airbus A320",
            "Boeing 777-300ER",
            "Airbus A350-900",
        ]
    }


@app.get("/api/airports")
def get_airports():
    return {
        "airports": [
            "JFK - New York",
            "LAX - Los Angeles",
            "DXB - Dubai",
            "LHR - London Heathrow",
            "KHI - Karachi",
        ]
    }

# ---------------- HIGH‑LEVEL ANALYSIS ENDPOINT ----------------
@app.post("/api/analyze")
def analyze_route(req: AnalysisRequest):
    """
    High-level analysis used by the Streamlit dashboard.

    Inputs (from frontend):
      - aircraft
      - departure_airport
      - arrival_airport
      - weather_conditions
      - aircraft_id (optional)
      - aircraft_age_years, flight_hours_input
      - last_maintenance_days, last_maintenance_type
    """

    # -------- 0) Aircraft & maintenance context --------
    aircraft_type, aircraft_type_exact = resolve_aircraft_type(
        req.aircraft_id, fallback_type=req.aircraft
    )

    aircraft_age_years = req.aircraft_age_years if req.aircraft_age_years is not None else 8.0
    total_flight_hours = req.flight_hours_input if req.flight_hours_input is not None else 12000.0
    last_maintenance_days = req.last_maintenance_days if req.last_maintenance_days is not None else 45.0
    last_maintenance_type = req.last_maintenance_type or "A-check"

    # Placeholder cycles estimate (FYP-2: replace with better logic)
    total_cycles = int(total_flight_hours / 1.25)

    # -------- 1) Choose representative ADS-B + CMAPSS profiles --------
    # Default: generic cruise profile
    velocity = 210.0
    baro_altitude = 11500.0
    vertical_rate = -5.0
    true_track = 145.0

    sensor_2 = 642.0
    sensor_3 = 1585.0
    sensor_4 = 1402.0
    cycle = 50.0

    # Adjust by aircraft type (example)
    if "737" in aircraft_type or "A320" in aircraft_type:
        # narrow-body, short/medium haul
        velocity = 230.0
        baro_altitude = 11000.0
        sensor_2 = 630.0
        sensor_3 = 1550.0
    else:
        # wide-body, long haul
        velocity = 250.0
        baro_altitude = 12000.0
        sensor_2 = 660.0
        sensor_3 = 1600.0

    # Adjust by weather (roughly)
    if req.weather_conditions == "Stormy":
        vertical_rate = -10.0
        true_track = 150.0
        cycle = 90.0
    elif req.weather_conditions == "Moderate Wind":
        vertical_rate = -7.0
        cycle = 70.0

    # -------- 2) Run CMAPSS health model --------
    if cmapss_model is None:
        raise HTTPException(status_code=500, detail="CMAPSS model not loaded on server.")

    cmapss_input = CMAPSSInput(
        sensor_2=sensor_2,
        sensor_3=sensor_3,
        sensor_4=sensor_4,
        cycle=cycle,
        engine_id=1,
    )
    X_cmapss = build_cmapss_vector(cmapss_input)
    try:
        health_pred = float(cmapss_model.predict(X_cmapss)[0])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CMAPSS prediction error: {e}")

    health_status = map_health_status(health_pred)
    health_score = round(health_pred * 100)

    if health_status == "Low":
        maintenance_risk = "High"
    elif health_status == "Medium":
        maintenance_risk = "Medium"
    else:
        maintenance_risk = "Low"

    # Adjust maintenance risk slightly if long since last maintenance
    if last_maintenance_days > 180 and maintenance_risk == "Medium":
        maintenance_risk = "High"

    # -------- 3) Run ADS-B anomaly model --------
    adsb_if_risk = "Unknown"
    if if_model is not None and scaler is not None:
        adsb_input = ADSBIFInput(
            velocity=velocity,
            baro_altitude=baro_altitude,
            vertical_rate=vertical_rate,
            true_track=true_track,
            icao24="800736",
            callsign="AIC143",
            origin_country="India",
        )
        X_adsb = build_feature_vector(adsb_input)
        X_adsb_scaled = scaler.transform(X_adsb)
        raw_label = int(if_model.predict(X_adsb_scaled)[0])      # 1 normal, -1 anomaly
        iforest_anomaly = 1 if raw_label == -1 else 0
        adsb_if_risk = map_risk(iforest_anomaly)

    # -------- 4) Weather + ADS-B risk => stress level --------
    if req.weather_conditions == "Stormy":
        base_stress = "High"
    elif req.weather_conditions == "Moderate Wind":
        base_stress = "Medium"
    else:
        base_stress = "Low"

    if adsb_if_risk == "High" and base_stress == "Low":
        stress_level = "Medium"
    elif adsb_if_risk == "High" and base_stress == "Medium":
        stress_level = "High"
    else:
        stress_level = base_stress

    if adsb_if_risk == "High":
        if maintenance_risk == "Low":
            maintenance_risk = "Medium"
        elif maintenance_risk == "Medium":
            maintenance_risk = "High"

    # -------- 5) Route distance & fuel logic --------
    base_distance = 4000
    route_key = f"{req.departure_airport[:3]}-{req.arrival_airport[:3]}"
    if route_key == "JFK-LAX":
        base_distance = 2475
    elif route_key == "KHI-DXB":
        base_distance = 760
    elif route_key == "LHR-DXB":
        base_distance = 3400

    recommended_distance = base_distance
    alternative_distance = int(base_distance * 1.03)

    if "737" in aircraft_type:
        factor = 2.2
    elif "A320" in aircraft_type:
        factor = 2.0
    else:
        factor = 2.5

    recommended_fuel = int(recommended_distance * factor)
    alternative_fuel = int(alternative_distance * factor)

    if base_stress == "High":
        weather_factor = 1.15
        maintenance_advisory = "Check critical systems after arrival."
    elif base_stress == "Medium":
        weather_factor = 1.05
        maintenance_advisory = "Monitor systems; routine checks are sufficient."
    else:
        weather_factor = 1.0
        maintenance_advisory = "No additional maintenance actions needed."

    # append last maintenance info
    maintenance_advisory = (
        maintenance_advisory
        + f" Last maintenance: {int(last_maintenance_days)} days ago ({last_maintenance_type})."
    )

    fuel_consumption = int(recommended_fuel * weather_factor)
    co2_emissions = int(fuel_consumption * 2.5)

    flight_hours = int(total_flight_hours)
    cycles = int(total_cycles)
    fuel_efficiency = round(fuel_consumption / max(recommended_distance, 1), 2)

    return {
        "health_score": health_score,
        "flight_hours": flight_hours,
        "cycles": cycles,
        "fuel_efficiency": fuel_efficiency,
        "maintenance_risk": maintenance_risk,
        "recommended_route": {
            "distance": recommended_distance,
            "estimated_fuel": recommended_fuel,
        },
        "alternative_route": {
            "distance": alternative_distance,
            "estimated_fuel": alternative_fuel,
        },
        "turbulence_risk": adsb_if_risk,
        "fuel_consumption": fuel_consumption,
        "co2_emissions": co2_emissions,
        "maintenance_advisory": maintenance_advisory,
        "stress_level": stress_level,
        "aircraft_type": aircraft_type,
        "aircraft_type_exact": aircraft_type_exact,
        "aircraft_id": req.aircraft_id,
        "aircraft_age_years": aircraft_age_years,
        "last_maintenance_days": last_maintenance_days,
        "last_maintenance_type": last_maintenance_type,
    }
