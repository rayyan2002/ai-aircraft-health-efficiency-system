# AI‑Powered Aircraft Health & Efficiency Analytics System

## Overview

This project is a research‑grade prototype that uses open aviation data and synthetic maintenance data to build an **Aircraft Health & Efficiency Analytics System**. The system computes aircraft health scores, maintenance‑risk indicators, and fuel/CO₂ efficiency metrics, and presents them in an interactive dashboard for engineering and operations teams.[file:256]

The final deliverable is a working pipeline:

1. Data ingestion (OpenSky/ADS‑B, METAR weather, NASA CMAPSS, synthetic maintenance).
2. Feature engineering (utilisation, weather stress, degradation indices, eco metrics).
3. Machine‑learning models (anomaly detection, maintenance‑risk prediction, eco‑efficiency estimation).
4. Web dashboard (Streamlit) for fleet overview, aircraft detail views, route analytics, and alerts.[file:256][web:308]

---

## Data Sources (planned)

- **OpenSky / ADS‑B** – public flight tracking data for routes, times, and aircraft usage.[file:256][web:308]  
- **METAR / TAF** – airport weather observations for departure and arrival conditions.[file:256]  
- **NASA CMAPSS** – simulated turbofan engine degradation dataset used to derive generic health/RUL indices.[web:7][web:304]  
- **Synthetic maintenance logs** – rule‑based events generated from utilisation and degradation to act as labels for predictive models.[file:256]

---

## Main Components

- `src/data/` – scripts for downloading/loading flight, weather, CMAPSS and synthetic maintenance data.  
- `src/features/` – feature engineering (hours, cycles, stress scores, degradation indices, eco metrics).  
- `src/models/` – training and inference code for anomaly detection, risk prediction, and eco‑efficiency models.  
- `src/dashboard/` – Streamlit app for visualising scores, trends and alerts.  
- `notebooks/` – Jupyter notebooks for EDA and experimentation.  
- `data/` – local data storage (raw, processed, external; not committed to Git).

---

## Team

- **Muhammad Rayyan Ayub** – Team Lead; problem definition, model design, scoring framework, partial implementation.[file:256]  
- **Kamal Akhtar** – Data Engineering; OpenSky/METAR ingestion, cleaning, unified dataset creation.[file:256]  
- **Ruhab** – Evaluation & Documentation; experiment design, metrics, limitations & future work, report writing.[file:256]  
- **Muhammad Maiz** – Technical Lead; project structure, integration of modules, training pipelines, scheduling.[file:256]  
- **Areeba Khan** – Dashboard & Tools; Streamlit UI, visualisations, connecting backend models to the front‑end.[file:256]

---

## Status

- Project structure and Git repository: **initialized**.  
- Next steps:
  1. Implement OpenSky + METAR data ingestion.
  2. Download CMAPSS dataset and explore engine health features.
  3. Design synthetic maintenance generator and initial feature set.

---

## Disclaimer

This system is a **decision‑support prototype only**.  
It is not certified for safety‑critical use and must be retrained and validated on real airline data before any operational deployment.[file:256][web:303]
