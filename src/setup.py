"""
setup.py  —  First-time setup for Aircraft Digital Twin
=======================================================
Run this ONCE after cloning the repo:
    cd src
    python setup.py

What it does:
    1. Creates a fresh aviation_data.db with all tables
    2. Seeds sample Pakistan flight data so the UI works immediately
    3. Checks for missing model files and tells you exactly what to do
"""

import os
import sqlite3
from datetime import datetime, timedelta

# ── Paths ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(SCRIPT_DIR, "backend", "aviation_data.db")

print("=" * 60)
print("  AIRCRAFT DIGITAL TWIN — FIRST TIME SETUP")
print("=" * 60)


# ──────────────────────────────────────────────────────────────
# STEP 1 — CREATE DATABASE TABLES
# ──────────────────────────────────────────────────────────────
print("\n[1/3] Setting up database...")

try:
    import sys
    sys.path.insert(0, os.path.join(SCRIPT_DIR, "backend"))
    from database import engine
    import models_db
    models_db.Base.metadata.create_all(bind=engine)
    print(f"  ✅ Database created at: {DB_PATH}")
except Exception as e:
    print(f"  ❌ DB creation failed: {e}")
    print("     Make sure you are running from the src/ folder")
    exit(1)

# ── Verify tables ──
conn   = sqlite3.connect(DB_PATH)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    count = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
    print(f"     {t[0]}: {count} rows")


# ──────────────────────────────────────────────────────────────
# STEP 2 — SEED SAMPLE PAKISTAN FLIGHT DATA
# ──────────────────────────────────────────────────────────────
print("\n[2/3] Seeding sample Pakistan flight data...")

# 15 real Pakistan/regional callsigns with approximate positions
SAMPLE_FLIGHTS = [
    ("PIA201",  "AP-BHO", 10500, 245, 33.60, 73.10),   # Islamabad
    ("PIA305",  "AP-BLC", 11000, 252, 31.52, 74.40),   # Lahore
    ("PIA101",  "AP-BGJ", 9800,  238, 24.90, 67.15),   # Karachi
    ("FLY101",  "AP-BIG", 8500,  220, 30.18, 66.97),   # Quetta
    ("PIA411",  "AP-BJA", 11200, 255, 34.20, 71.51),   # Peshawar
    ("ASL201",  "AP-BHH", 10000, 240, 26.22, 68.42),   # Sukkur
    ("PIA501",  "AP-BLD", 9500,  235, 32.08, 72.68),   # Faisalabad
    ("PIA601",  "AP-BLE", 10800, 248, 29.37, 71.68),   # Multan
    ("AIRB01",  "AP-BLF", 7500,  210, 35.22, 75.33),   # Gilgit
    ("PIA701",  "AP-BLG", 11100, 250, 25.39, 68.87),   # Hyderabad
]

now     = datetime.now()
inserted = 0

for flight in SAMPLE_FLIGHTS:
    callsign, tail, alt, vel, lat, lon = flight

    # Insert 10 historical points per aircraft (simulates 50 min of flight)
    for i in range(10):
        t        = now - timedelta(minutes=i * 5)
        fake_lat = round(lat + (i * 0.03), 4)
        fake_lon = round(lon - (i * 0.02), 4)
        fake_alt = max(1000, alt - (i * 80))

        conn.execute("""
            INSERT INTO flight_telemetry
            (tail_number, callsign, altitude, velocity,
             latitude, longitude, anomaly_flag, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (tail, callsign, fake_alt, vel, fake_lat, fake_lon, t))
        inserted += 1

conn.commit()
print(f"  ✅ Inserted {inserted} telemetry points for {len(SAMPLE_FLIGHTS)} aircraft")
print(f"     Each aircraft has 10 historical points → flight paths visible immediately")


# ──────────────────────────────────────────────────────────────
# STEP 3 — CHECK FOR MODEL FILES
# ──────────────────────────────────────────────────────────────
print("\n[3/3] Checking model files...")

MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
REQUIRED_MODELS = [
    "adsb_iforest.pkl",
    "adsb_if_scaler.pkl",
    "cmapss_health_rf.pkl",
    "engine_model_v1.keras",
    "scaler_features.pkl",
    "scaler_target.pkl",
]

missing = []
for model in REQUIRED_MODELS:
    path = os.path.join(MODELS_DIR, model)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"  ✅ {model:<35} ({size_kb:.1f} KB)")
    else:
        print(f"  ❌ {model:<35} MISSING")
        missing.append(model)

if missing:
    print(f"""
  ⚠️  {len(missing)} model file(s) missing.
  Models are not stored in git (too large).
  
  Get them from your team lead (Rayyan) via:
    • Google Drive shared folder
    • USB transfer
  
  Place them in:
    src/models/
  
  OR retrain the LSTM yourself:
    cd src/notebooks
    python train_lstm.py
  
  Note: FYP-1 models (adsb_iforest, cmapss) must be
  copied from the team — they cannot be retrained without
  the original training data.
""")
else:
    print("  ✅ All model files present!")


# ──────────────────────────────────────────────────────────────
# DONE
# ──────────────────────────────────────────────────────────────
conn.close()

print("=" * 60)
print("  SETUP COMPLETE")
print("=" * 60)
print("""
Next steps:
  1. Activate your virtual environment
  2. pip install -r requirements_mac.txt   (Mac)
     pip install -r requirements.txt       (Windows)
  3. Start FastAPI:
       cd src/backend && uvicorn main:app --reload
  4. Start Streamlit (new terminal):
       cd src && streamlit run frontend/app.py
  5. Open http://localhost:8501
""")
