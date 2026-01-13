"""
analyze_snapshot.py
 
Analysis of aircraft state vectors (Asia region):
- basic statistics for key kinematic variables
- anomaly detection using IsolationForest
"""
 
import os
import pandas as pd
from sklearn.ensemble import IsolationForest
 
 
def load_region_snapshot(
    path: str = "src/data/processed/asia_snapshot.csv",
) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run src.data.load_snapshot first."
        )
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows from {path}")
    return df
 
 
def basic_stats(df: pd.DataFrame) -> None:
    print("=== Basic stats (velocity & altitudes) ===")
    for col in ["velocity", "baro_altitude", "geo_altitude", "vertical_rate"]:
        if col in df.columns:
            print(f"\nColumn: {col}")
            print(df[col].describe(percentiles=[0.25, 0.5, 0.75]))
 
 
def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    # Choose numeric features commonly present in OpenSky state vectors
    features = []
    for col in ["velocity", "baro_altitude", "geo_altitude", "vertical_rate"]:
        if col in df.columns:
            features.append(col)
 
    if not features:
        raise ValueError("No numeric features found for anomaly detection")
 
    print(f"\nUsing features for IsolationForest: {features}")
 
    X = df[features].fillna(0.0)
 
    # IsolationForest for unsupervised anomaly detection
    # contamination ~ expected fraction of anomalies
    model = IsolationForest(
        n_estimators=100,
        contamination=0.02,  # 2% anomalies; adjust if needed
        random_state=42,
    )
 
    print("Fitting IsolationForest...")
    df["anomaly_score"] = model.fit_predict(X)  # -1 = anomaly, 1 = normal
 
    anomalies = df[df["anomaly_score"] == -1].copy()
    print(f"Detected {len(anomalies)} anomalies out of {len(df)} rows")
 
    return anomalies
 
 
if __name__ == "__main__":
    df_region = load_region_snapshot()
    basic_stats(df_region)
 
    anomalies = detect_anomalies(df_region)
    os.makedirs("src/data/processed", exist_ok=True)
    anomalies.to_csv("src/data/processed/asia_anomalies.csv", index=False)
    print("Saved anomalies to src/data/processed/asia_anomalies.csv")