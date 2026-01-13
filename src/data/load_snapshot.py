"""
load_snapshot.py

Load an OpenSky 'Aircraft States Snapshot' CSV,
filter to a broad Asia region,
and save a smaller CSV for analysis.
"""

import os
import pandas as pd

# Asia bounding box [min_lat, max_lat, min_lon, max_lon]
ASIA_BBOX = [-10.0, 60.0, 20.0, 150.0]


def filter_one_file(input_path: str) -> pd.DataFrame:
    print(f"Loading snapshot from {input_path}")
    df = pd.read_csv(input_path)

    lat_col = "latitude"
    lon_col = "longitude"

    min_lat, max_lat, min_lon, max_lon = ASIA_BBOX
    mask = (
        df[lat_col].between(min_lat, max_lat)
        & df[lon_col].between(min_lon, max_lon)
    )
    df_asia = df[mask].copy()

    print(f"Rows in Asia from this file: {len(df_asia)}")
    return df_asia


def load_and_filter_snapshot():
    # adjust 'src' here depending on where your CSV actually is
    input_path = os.path.join("src", "data", "raw", "opensky_states_snapshot.csv")
    output_path = os.path.join("src", "data", "processed", "asia_snapshot.csv")

    df_asia = filter_one_file(input_path)

    print(f"Saving filtered snapshot to {output_path}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_asia.to_csv(output_path, index=False)


if __name__ == "__main__":
    load_and_filter_snapshot()
