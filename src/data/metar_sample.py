"""
metar_sample.py

Parse a few manually downloaded raw METAR text files (OMDB, OTHH, OEJN)
from aviationweather.gov and save a simple CSV with key tokens.
"""

import os
import pandas as pd

RAW_DIR = "src/data/raw"
OUTPUT_PATH = "src/data/processed/metar_sample.csv"


def parse_raw_metar(line: str):
    """
    Very simple METAR parser for lines like:
    METAR OMDB 131200Z 33010KT 300V360 CAVOK 24/13 Q1019 NOSIG
    """
    parts = line.strip().split()
    if len(parts) < 5:
        return None

    # Basic tokens
    metar_type = parts[0]           # METAR
    icao = parts[1]                 # OMDB
    time_token = parts[2]           # 131200Z
    wind_token = parts[3]           # 33010KT
    # Remaining tokens vary; we just store the raw string
    rest = " ".join(parts[4:])

    return {
        "metar_type": metar_type,
        "icao": icao,
        "time_token": time_token,
        "wind_token": wind_token,
        "raw_text": line.strip(),
        "rest_tokens": rest,
    }


def build_metar_sample():
    files = [
        os.path.join(RAW_DIR, "metar_OMDB.txt"),
        os.path.join(RAW_DIR, "metar_OTHH.txt"),
        os.path.join(RAW_DIR, "metar_OEJN.txt"),
    ]

    records = []

    for path in files:
        if not os.path.exists(path):
            print(f"Warning: {path} not found, skipping.")
            continue

        print(f"Loading METAR from {path}")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = parse_raw_metar(line)
                    if rec is not None:
                        records.append(rec)

    if not records:
        print("No METAR records loaded.")
        return

    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(df)} METAR rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_metar_sample()
