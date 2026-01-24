from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import numpy as np
import joblib

# ---------------- CONFIG ----------------
IF_MODEL_PATH = "models/adsb_iforest.pkl"
SCALER_PATH   = "models/adsb_if_scaler.pkl"

FEATURE_ORDER = ["velocity", "baro_altitude", "vertical_rate", "true_track"]

# ---------------- LOAD MODEL & SCALER ----------------
app = FastAPI(
    title="Aircraft ADS-B Anomaly API",
    description="Isolation Forest–based anomaly detection for ADS-B flight states",
    version="1.0.0",
)

try:
    if_model = joblib.load(IF_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Isolation Forest and scaler loaded.")
except Exception as e:
    print(f"❌ Error loading model or scaler: {e}")
    if_model = None
    scaler = None


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


# ---------------- HELPER FUNCTIONS ----------------
def build_feature_vector(payload: ADSBIFInput) -> np.ndarray:
    """
    Convert the incoming JSON into a numpy array with the same
    feature order used in training: [velocity, baro_altitude, vertical_rate, true_track].
    """
    values = [
        payload.velocity,
        payload.baro_altitude,
        payload.vertical_rate,
        payload.true_track,
    ]
    return np.array(values, dtype=float).reshape(1, -1)


def map_risk(if_label: int) -> str:
    """
    Simple mapping from Isolation Forest label to risk level.
    You can refine thresholds or wording later.
    """
    return "High" if if_label == 1 else "Low"


# ---------------- ROUTES ----------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "ADS-B Isolation Forest anomaly API running",
    }


@app.post("/predict_adsb_if", response_model=ADSBIFPrediction)
def predict_adsb_if(data: ADSBIFInput):
    """
    Take a single ADS-B state vector, run it through the scaler + Isolation Forest,
    and return anomaly flag, score, and a human-readable recommendation.
    """
    if if_model is None or scaler is None:
        raise HTTPException(status_code=500, detail="Model or scaler not loaded on server.")

    # 1) Build feature vector
    X = build_feature_vector(data)

    # 2) Apply same scaling as in training
    try:
        X_scaled = scaler.transform(X)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scaling error: {e}")

    # 3) Predict with Isolation Forest
    try:
        raw_label = int(if_model.predict(X_scaled)[0])     # 1 normal, -1 anomaly
        score = float(if_model.score_samples(X_scaled)[0]) # lower = more anomalous
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model prediction error: {e}")

    # Convert to 0/1 convention for easier use
    iforest_anomaly = 1 if raw_label == -1 else 0
    risk = map_risk(iforest_anomaly)

    # 4) Build message
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
