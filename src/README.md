# ✈️ AI-Powered Aircraft Health & Efficiency System
### Live Digital Twin — FYP-2 | GIKI AI Bootcamp 2025

> *Predicting engine failure before it happens — by analyzing how a plane is flying right now.*

---

## 📌 Table of Contents
- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Team & Responsibilities](#-team--responsibilities)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [ML Models](#-ml-models)
- [Sprint Progress](#-sprint-progress)
- [Known Issues](#-known-issues)

---

## 🧠 Project Overview

Aviation maintenance today is either reactive (wait for a warning) or rigidly scheduled (replace parts on a calendar). Both approaches waste money and risk safety.

This project builds a **Live Digital Twin** for a commercial airline fleet. It answers one question in real time:

> *How many flights does this engine have left before it fails?*

The system continuously tracks live Pakistani aircraft via the OpenSky Network, feeds their real-time telemetry into a Deep Learning LSTM model, and predicts the **Remaining Useful Life (RUL)** of each engine in flight cycles. A Streamlit dashboard visualizes everything — live maps, SHAP explainability, mission logs, and health scores.

### What Makes This Different
- **Not a static calculator** — data flows live from real aircraft in Pakistani airspace every 5 minutes
- **Not a black box** — SHAP-style feature attribution tells mechanics *why* an engine is flagged
- **Not a demo** — the full pipeline runs autonomously: fetch → store → infer → visualize → auto-log

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                    │
│         Live Map │ SHAP Chart │ Mission Logs             │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP REST
┌────────────────────────▼────────────────────────────────┐
│                    FASTAPI BACKEND                       │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  IForest    │  │  CMAPSS RF   │  │  LSTM (Kamal) │  │
│  │  Anomaly    │  │  Health      │  │  RUL Predict  │  │
│  │  Detection  │  │  Index       │  │  engine_v1    │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         BACKGROUND WORKER (every 5 min)          │   │
│  │   OpenSky API → flight_telemetry → auto-land     │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │ SQLAlchemy ORM
┌────────────────────────▼────────────────────────────────┐
│                    SQLITE DATABASE                       │
│   fleet │ flight_telemetry │ flight_history │            │
│   maintenance_records │ health_predictions               │
└─────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai-aircraft-health-efficiency-system/
│
├── README.md
├── .gitignore
├── setup.py                     ← Run this first after cloning
│
└── src/
    ├── backend/
    │   ├── main.py              ← FastAPI server (all endpoints)
    │   ├── database.py          ← SQLAlchemy connection
    │   ├── models_db.py         ← ORM table schemas
    │   └── aviation_data.db     ← SQLite DB (gitignored)
    │
    ├── frontend/
    │   └── app.py               ← Streamlit dashboard
    │
    ├── models/                  ← ML model files (gitignored)
    │   ├── adsb_iforest.pkl     ← FYP-1: Anomaly detection
    │   ├── adsb_if_scaler.pkl   ← FYP-1: IForest scaler
    │   ├── cmapss_health_rf.pkl ← FYP-1: Engine health RF
    │   ├── engine_model_v1.keras← FYP-2: LSTM RUL model
    │   ├── scaler_features.pkl  ← FYP-2: LSTM feature scaler
    │   └── scaler_target.pkl    ← FYP-2: LSTM target scaler
    │
    ├── notebooks/
    │   ├── ADS_B_Modeling.ipynb     ← IForest training
    │   ├── CMAPSS_Modeling.ipynb    ← RF health training
    │   ├── LSTM_TIMESERIES.ipynb    ← LSTM RUL training
    │   └── train_lstm.py            ← Standalone LSTM trainer
    │
    ├── scripts/
    │   ├── fetch_opensky.py     ← Manual OpenSky fetcher
    │   └── fetch_weather.py     ← Weather data fetcher
    │
    ├── data/
    │   └── raw/
    │       └── CMAPSS_DIR/      ← NASA CMAPSS dataset
    │
    ├── requirements.txt         ← Windows dependencies
    ├── requirements_mac.txt     ← macOS dependencies
    └── setup.py                 ← First-time DB + data setup
```

---

## 👥 Team & Responsibilities

| Member | Role | Sprint 3 Task |
|--------|------|---------------|
| **Rayyan** | Tech Lead / Backend | API architecture, endpoint routing, ghost bug fix, OpenSky integration |
| **Maiz** | Backend / ML Ops | LSTM training pipeline, loss curve documentation |
| **Kamal** | Machine Learning | LSTM hyperparameter tuning — target MAE < 15 cycles |
| **Ruhab** | Data Engineering | Fleet table seeding, Pakistan airspace lock, flight history |
| **Areeba** | Frontend | Streamlit dashboard, live map, mission logs UI |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit, Plotly, Folium |
| Backend | FastAPI, Uvicorn, SQLAlchemy |
| Database | SQLite |
| ML — Anomaly | Isolation Forest (scikit-learn) |
| ML — Health | Random Forest Regressor (scikit-learn) |
| ML — RUL | LSTM Neural Network (TensorFlow/Keras) |
| Data Source | OpenSky Network API (live ADS-B) |
| Language | Python 3.11 |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11
- Git

### 1. Clone the repo
```bash
git clone https://github.com/rayyan2002/ai-aircraft-health-efficiency-system.git
cd ai-aircraft-health-efficiency-system
```

### 2. Create virtual environment

**macOS:**
```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r src/requirements_mac.txt --only-binary=:all:
```

**Windows:**
```bash
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r src/requirements.txt --only-binary=:all:
```

### 3. Get model files
Models are not stored in git due to file size. Get them from the team shared Google Drive folder and place them in `src/models/`.

Required files:
```
src/models/adsb_iforest.pkl
src/models/adsb_if_scaler.pkl
src/models/cmapss_health_rf.pkl
src/models/engine_model_v1.keras
src/models/scaler_features.pkl
src/models/scaler_target.pkl
```

### 4. First-time setup (creates DB + seeds data)
```bash
cd src
python setup.py
```

### 5. Start the backend
```bash
cd src/backend
uvicorn main:app --reload
```

You should see:
```
✅ SUCCESS: FYP-1 Models Loaded
✅ SUCCESS: FYP-2 Kamal's LSTM & Scaler Loaded
INFO: Application startup complete.
```

### 6. Start the frontend (new terminal)
```bash
cd src
source venv/bin/activate   # Mac
# venv\Scripts\activate    # Windows
streamlit run frontend/app.py
```

Open **http://localhost:8501**

---

## 📡 API Reference

Base URL: `http://localhost:8000`

Interactive docs: **http://localhost:8000/docs**

### Fleet & Telemetry

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/fleet` | List all aircraft (tail number + active flight) |
| `GET` | `/api/telemetry/{tail}` | Latest lat/lon/alt/speed for one aircraft |
| `GET` | `/api/route/{tail}` | Full flight path (all historical points) |

### ML Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analyze/{tail}` | Full ML inference — RUL, SHAP, risk, emissions |

### Flight History

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/history/{tail}` | Past flight logs for Mission Logs tab |
| `POST` | `/api/complete_flight/{tail}` | Log a completed flight manually |

### Admin (Ruhab)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/admin/seed_pakistan_fleet` | One-time fleet table seed |

### Sprint 4 Shells (ready for implementation)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/log_maintenance` | Mechanic portal — log maintenance + reset health |
| `POST` | `/api/simulate` | Predictive simulator — hypothetical flight inputs |

### Legacy FYP-1

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predict_adsb_if` | Direct IForest anomaly prediction |

---

## 🤖 ML Models

### FYP-1 Models

| Model | Algorithm | Input | Output |
|-------|-----------|-------|--------|
| `adsb_iforest.pkl` | Isolation Forest | velocity, altitude, vertical_rate, true_track | anomaly flag + score |
| `cmapss_health_rf.pkl` | Random Forest | sensor_2, sensor_3, sensor_4, cycle | health index (0–1) |

### FYP-2 Model

| Model | Algorithm | Input | Output |
|-------|-----------|-------|--------|
| `engine_model_v1.keras` | 3-layer LSTM | 30 timesteps × 24 sensors | RUL (cycles) |

**LSTM Architecture:**
```
Input  → (30 timesteps, 24 sensors)
LSTM   → 128 units → Dropout 0.3
LSTM   → 64 units  → Dropout 0.2
LSTM   → 32 units  → Dropout 0.2
Dense  → 64 → Dense 32 → Dense 1
Output → Predicted RUL (cycles)
```

**Current Performance:**
- V1 MAE: ~57 cycles (Sprint 3 target: < 15 cycles)
- Training data: NASA CMAPSS FD001 (17,631 sequences)

### To retrain the LSTM
```bash
# Place X_train_lstm.npy and y_train_lstm.npy in src/notebooks/
cd src/notebooks
python train_lstm.py
# Outputs saved to src/notebooks/models/
# Copy to src/models/ when done
```

---

## 📊 Sprint Progress

| Sprint | Status | Key Deliverables |
|--------|--------|-----------------|
| FYP-1 | ✅ Complete | IForest anomaly detection, CMAPSS health RF, static dashboard |
| Sprint 1 | ✅ Complete | FastAPI backend, SQLite DB, OpenSky integration |
| Sprint 2 | ✅ Complete | LSTM integration, live telemetry, Streamlit dashboard |
| Sprint 3 | 🔄 In Progress | Dynamic ML inference, Pakistan fleet lock, ghost bug fix |
| Sprint 4 | 📋 Planned | Mechanic portal, predictive simulator, Docker deployment |

---

## ⚠️ Known Issues

| Issue | Status | Owner |
|-------|--------|-------|
| LSTM MAE = 57 cycles (target < 15) | 🔄 Kamal tuning | Kamal |
| Flight path needs multiple DB records to render | ⏳ Resolves with live data | Auto |
| Models not in git — manual transfer required | 📋 Google Drive workaround | Rayyan |

---

## 📝 Notes for Teammates

### After every `git pull`
```bash
# Re-save model files if sklearn version changed
python - <<'EOF'
import joblib
for p in ['src/models/adsb_iforest.pkl','src/models/adsb_if_scaler.pkl','src/models/cmapss_health_rf.pkl']:
    obj = joblib.load(p); joblib.dump(obj, p); print(f'OK {p}')
EOF
```

### Database location
- **Backend reads from:** `src/backend/aviation_data.db`
- **setup.py creates it at:** `src/backend/aviation_data.db`
- **fetch_opensky.py writes to:** `src/backend/aviation_data.db`

### OpenSky rate limit
The background worker fetches every 5 minutes. OpenSky free tier allows ~400 requests/day. Do not reduce the interval below 3 minutes or you will hit 429 errors.

---

*Built at GIKI AI Bootcamp 2025 — Sprint 3 of 4*
