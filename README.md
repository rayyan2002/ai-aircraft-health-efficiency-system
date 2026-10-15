# AeroTwin — AI-Powered Aircraft Health & Efficiency Digital Twin

AeroTwin is a web-based decision-support system that monitors the health,
efficiency, and live status of a curated fleet of 44 Pakistani commercial
aircraft (PIA, AirBlue, AirSial, Fly Jinnah). It links live ADS-B flight
surveillance to physical airframes and applies two machine-learning models to
estimate engine health and detect anomalous flight behaviour in real time.

> **Scope note.** AeroTwin is a decision-support tool, not an airworthiness
> authority. Its predictions assist maintenance and operations decisions; a
> certified engineer makes the final call. The engine model is calibrated on
> NASA's benchmark dataset, not validated on real airline maintenance records.

---

## What it does

- **Live fleet tracking** — pulls live flight positions and routes, matching each
  flight to a physical aircraft by its ICAO 24-bit transponder hex code.
- **Engine health / RUL** — an LSTM (trained on NASA C-MAPSS) estimates Remaining
  Useful Life per airframe from its accumulated engine cycles.
- **Anomaly detection** — an Isolation Forest flags abnormal flight behaviour from
  live telemetry (altitude, speed, vertical rate, heading), scored at ingest.
- **Fleet dashboards** — health overview, predictive maintenance calendar,
  anomaly feed, CO₂ / ESG estimates, route efficiency, and a digital-twin
  comparison view.
- **Flight lifecycle** — detects when a fleet aircraft is airborne, attaches its
  flight number, and logs completed flights to history on landing.

---

## Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, SQLite |
| Machine learning | TensorFlow/Keras (LSTM), scikit-learn (Isolation Forest) |
| Frontend | React, Vite, Recharts, Leaflet |
| Data sources | Flightradar24 API (live positions + routes), OpenSky Network (ADS-B fallback), NASA C-MAPSS (engine data) |

---

## Repository structure

```
ai-aircraft-health-efficiency-system/
├── src/
│   ├── backend/
│   │   ├── main.py              # FastAPI app: endpoints + data pipeline
│   │   ├── database.py          # SQLAlchemy session/engine
│   │   ├── models_db.py         # ORM models
│   │   ├── requirements.txt
│   │   ├── aviation_data.db     # SQLite database (sample data included)
│   │   └── scripts/             # diagnostic & setup utilities (see below)
│   ├── models/                  # trained model files (.keras, .pkl)
│   └── notebooks/               # LSTM training & SHAP explainability
└── frontend-react/
    └── src/
        ├── api/                 # centralised API calls
        ├── components/          # shared UI + LiveMap
        └── pages/               # one file per screen
```

---

## Getting started

### Prerequisites

- Python 3.11
- Node.js and npm
- ~8 GB RAM recommended

### 1. Backend

```bash
cd src/backend

# create and activate a virtual environment
python -m venv venv311
# Windows:
venv311\Scripts\activate
# macOS/Linux:
source venv311/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload
# backend runs on http://localhost:8000
```

On startup you should see the models load:

```
✅ SUCCESS: FYP-1 Models Loaded
✅ SUCCESS: FYP-2 LSTM & Scaler Loaded
📡 DATA SOURCE: OpenSky ADS-B
```

A background pipeline then fetches live flight and weather data every few
minutes and prints a status line per cycle.

### 2. Frontend

In a second terminal:

```bash
cd frontend-react
npm install
npm run dev
# open http://localhost:5173
```

---

## Configuration

The system runs without any API key, using the free OpenSky Network feed. To
enable route data (origin/destination), set a Flightradar24 API key:

```bash
# Windows PowerShell
$env:FR24_API_KEY="your_key_here"

# macOS / Linux
export FR24_API_KEY="your_key_here"
```

| Variable | Default | Purpose |
|---|---|---|
| `FR24_API_KEY` | *(unset)* | Enables Flightradar24, polled alongside OpenSky. |
| `FR24_INTERVAL_MIN` | 30 | Minutes between Flightradar24 polls (billed per aircraft returned). |
| `PIPELINE_INTERVAL_MIN` | 5 | Minutes between cycles; OpenSky is polled every cycle. |
| `OPENSKY_CLIENT_ID` / `OPENSKY_CLIENT_SECRET` | *(unset)* | OAuth2 client credentials for a registered OpenSky account. Anonymous access (400 credits/day) runs out after ~11 hours at a 5-minute poll over the Pakistan box. |
| `OPENWEATHER_API_KEY` | *(unset)* | Airport weather. Skipped if unset. |

Every `flight_telemetry` row records its feed in `source` (`FR24` / `OpenSky`)
and how that feed obtained the position in `pos_source` (`ADSB`, `MLAT`,
`ESTIMATED`, ...). `pipeline_log` records each feed's outcome per cycle
(`opensky_status`, `fr24_status`), so a failed poll is never read as an empty sky.

```bash
# Windows PowerShell
$env:FR24_API_KEY="..."
$env:OPENWEATHER_API_KEY="..."

# macOS / Linux
export FR24_API_KEY="..."
export OPENWEATHER_API_KEY="..."
```

**Never commit an API key.** The application reads it from the environment only;
no key is stored in source. `GET /api/data_source` reports which feed is active.

> **On Flightradar24 credits.** The API bills per aircraft returned, so the
> system queries only the 44 fleet registrations rather than a bounding box.
> A single poll costs roughly 160 credits, which is why the default interval is
> 30 minutes when FR24 is enabled.

---

## Utility scripts

Standalone helpers live in `src/backend/scripts/`. **Run them from
`src/backend/`** (not from inside `scripts/`), so the database path resolves:

```bash
cd src/backend
python scripts/check_hex.py
```

| Script | Purpose |
|---|---|
| `Migrate_db.py` | Create/upgrade the database schema |
| `populate_fleet_data.py` | Seed the 44-aircraft fleet registry |
| `check_hex.py` | Verify hex-code coverage and live-flight matching |
| `backfill_hex.py` / `apply_hex.py` | Populate missing transponder hex codes |
| `debug_reconcile.py` | Diagnose airborne/grounded status discrepancies |
| `Verify_predictions.py` | Sanity-check model outputs |
| `test_fr24.py` / `diag_fr24.py` / `fr24_fields.py` | Flightradar24 API checks |
| `fetch_fr24_summaries.py` | Flightradar24 flight summaries (takeoff, landing, route) per fleet registration over a date range; `--count-only` first to see the size |

The database is included in the repository with sample data, so the utility
scripts are not required for a first run.

---

## How the models work

**Engine health (LSTM).** The model is a sequence regressor trained on NASA
C-MAPSS: 30 timesteps x 24 channels (21 sensors + 3 operational settings),
predicting Remaining Useful Life in cycles. Test MAE is approximately 6.3 cycles.

For a live aircraft we have **no engine sensor data** — ADS-B does not carry it.
So the system constructs a representative degradation profile from that
airframe's known accumulated cycles, expressed in the same 30x24 form the model
was trained on, and the LSTM maps it to an RUL. That output is then blended with
a direct physical wear model:

```
wear_fraction = accumulated_cycles / design_life
wear_rul      = 123 - wear_fraction * (123 - 5)
final_rul     = 0.30 * lstm_output + 0.70 * wear_rul
health_score  = (final_rul - 5) / (123 - 5) * 100
```

The wear model carries the larger weight because accumulated cycles are a **real
measured quantity** for our fleet, whereas the LSTM was trained on simulated
engines. This is precisely why the project describes live-fleet RUL as
*calibrated*, not *validated*.

**Anomaly detection (Isolation Forest).** Unsupervised, trained on four ADS-B
channels: **ground velocity, barometric altitude, vertical rate, and true
track**. Every telemetry record is scored at ingest. `score_samples` returns a
negative value — closer to zero is more normal, more negative is more anomalous.

It is unsupervised because no labelled set of "abnormal flights" exists to train
against. It detects abnormal *flight behaviour*, not engine condition, since
those four channels contain no engine information.

**The hex link.** ADS-B gives a callsign, but a callsign is a schedule slot, not
an airframe. AeroTwin matches the broadcast ICAO 24-bit hex code against the
fleet registry to identify the specific physical aircraft — and therefore its
cycle history. All 44 hex codes were verified against Flightradar24.

---

**Fuel and CO2.** Fuel is estimated, not measured:

```
phase      = f(altitude, airspeed)          # cruise / climb-descent / taxi
burn_rate  = {cruise: 85, climb_descent: 110, taxi: 45}  # litres/minute
fuel       = burn_rate * observed_duration
co2        = fuel * 2.53                    # kg CO2 per litre Jet A-1
```

The CO2 factor is a published standard: Jet A-1 density ~0.80 kg/L times the
ICAO emission factor ~3.16 kg CO2 per kg fuel. The **fuel** figure is coarse —
burn rates are generic rather than per aircraft type, and duration covers only
the window over which the aircraft was observed.

---

## Known limitations (by design)

These are stated openly rather than hidden:

1. **RUL is calibrated, not validated** on real Pakistani engines — it is
   trained on NASA C-MAPSS. Validating it requires airline maintenance logs.
2. **ADS-B carries no engine sensors**, so anomaly detection covers flight
   behaviour, not engine condition.
3. **ADS-B does not broadcast route.** Origin and destination therefore come
   from a commercial feed (Flightradar24). Without an API key the system falls
   back to OpenSky and the interface states that route data is unavailable
   rather than fabricating it.
4. **Some positions are interpolated.** Flightradar24 marks records as `ADSB` or
   `ESTIMATED`; the system counts and reports estimated positions separately so
   an interpolation is never presented as a measurement.
5. **On the OpenSky fallback, coverage over parts of Pakistan is sparse**, so an
   aircraft may briefly appear grounded while genuinely flying.

---

## Data sources & licensing

- **OpenSky Network** — open ADS-B data, used for research/academic purposes.
- **NASA C-MAPSS** — public turbofan degradation benchmark dataset.
- Fleet registry curated and verified against publicly available records.

This project is academic (Final Year Project) and non-commercial.

---

## Note on the models directory

`cmapss_health_rf.pkl` (a Random Forest baseline) is **not** included — it is a
122 MB early experiment that is not used by the running system. The backend
loads it optionally and runs correctly without it. The models the system
actually uses (`engine_model_v1.keras`, `adsb_iforest.pkl` and the scalers) are
included in the repository.