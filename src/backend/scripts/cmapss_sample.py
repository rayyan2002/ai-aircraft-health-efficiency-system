"""
cmapss_sample.py

Create a tiny CMAPSS health sample for one engine:
- load train_FD001.txt
- select a single engine_id
- compute a simple health index from cycle count
"""

import os
import pandas as pd

# Adjust this path to where you unzipped CMAPSSData.zip
CMAPSS_DIR = "src/data/raw"
TRAIN_FILE = os.path.join(CMAPSS_DIR, "train_FD001.txt")
OUTPUT_PATH = "src/data/processed/cmapss_health_sample.csv"


def load_fd001(train_path: str) -> pd.DataFrame:
    # FD001 has 26 columns: engine_id, cycle, and 24 settings/sensors
    col_names = (
        ["engine_id", "cycle"]
        + [f"setting_{i}" for i in range(1, 4)]
        + [f"sensor_{i}" for i in range(1, 22)]
    )

    df = pd.read_csv(
        train_path,
        sep=r"\s+",
        header=None,
        names=col_names,
    )
    return df


def build_health_sample():
    if not os.path.exists(TRAIN_FILE):
        raise FileNotFoundError(
            f"{TRAIN_FILE} not found. Update CMAPSS_DIR in cmapss_sample.py."
        )

    df = load_fd001(TRAIN_FILE)

    # Pick one engine (e.g., engine_id = 1)
    eng_id = 1
    df_eng = df[df["engine_id"] == eng_id].copy()

    # Max cycle for this engine (end-of-life)
    max_cycle = df_eng["cycle"].max()

    # Simple health index: remaining cycles / max_cycles (1 -> 0)
    df_eng["remaining_cycles"] = max_cycle - df_eng["cycle"]
    df_eng["health_index"] = df_eng["remaining_cycles"] / max_cycle

    # Keep only a few useful columns
    keep_cols = [
        "engine_id",
        "cycle",
        "health_index",
        "sensor_2",
        "sensor_3",
        "sensor_4",
    ]
    df_out = df_eng[keep_cols]

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df_out.to_csv(OUTPUT_PATH, index=False)
    print(
        f"Saved CMAPSS health sample for engine {eng_id} "
        f"({len(df_out)} cycles) to {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    build_health_sample()
