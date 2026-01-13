"""
synthetic_maintenance.py

Create a simple synthetic maintenance log for aircraft in the Asia snapshot:
- one row per aircraft (icao24)
- random last maintenance date and type
- needs_attention = 1 if aircraft appears in anomaly list, else 0
"""

import os
import random
from datetime import datetime, timedelta

import pandas as pd


def load_asia_snapshot(
    path: str = "src/data/processed/asia_snapshot.csv",
) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run src.data.load_snapshot first."
        )
    return pd.read_csv(path)


def load_anomalies(
    path: str = "src/data/processed/asia_anomalies.csv",
) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run src.analysis.analyze_snapshot first."
        )
    return pd.read_csv(path)


def random_date_within_days(days_back: int = 180) -> str:
    """Return a random date string within last `days_back` days."""
    today = datetime.utcnow().date()
    delta = timedelta(days=random.randint(0, days_back))
    d = today - delta
    return d.isoformat()


def build_synthetic_maintenance():
    df_asia = load_asia_snapshot()
    df_anom = load_anomalies()

    # Unique aircraft in Asia snapshot
    aircraft = df_asia["icao24"].dropna().unique()

    # Aircraft that had at least one anomalous state
    anomalous_aircraft = set(df_anom["icao24"].dropna().unique())

    records = []
    maintenance_types = ["A-check", "B-check", "Unscheduled"]

    for icao in aircraft:
        needs_attention = 1 if icao in anomalous_aircraft else 0

        rec = {
            "icao24": icao,
            "last_maintenance_date": random_date_within_days(180),
            "maintenance_type": random.choice(maintenance_types),
            "needs_attention": needs_attention,
        }
        records.append(rec)

    df_maint = pd.DataFrame(records)

    os.makedirs("src/data/processed", exist_ok=True)
    output_path = "src/data/processed/synthetic_maintenance.csv"
    df_maint.to_csv(output_path, index=False)

    print(f"Saved synthetic maintenance log for {len(df_maint)} aircraft to {output_path}")


if __name__ == "__main__":
    random.seed(42)
    build_synthetic_maintenance()
