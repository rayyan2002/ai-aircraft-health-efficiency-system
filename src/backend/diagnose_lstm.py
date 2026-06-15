"""
diagnose_lstm.py — figure out what input range makes the LSTM
output high vs low RUL. Run from src/backend/:
    python diagnose_lstm.py
"""
import numpy as np, joblib, os, tensorflow as tf

BASE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(BASE, "..", "models")

lstm   = tf.keras.models.load_model(os.path.join(MODELS, "engine_model_v1.keras"), safe_mode=False)
scaler = joblib.load(os.path.join(MODELS, "scaler_features.pkl"))

print("Scaler expects", scaler.n_features_in_, "features")
print("Scaler mean (first 5):", scaler.mean_[:5])
print("Scaler scale (first 5):", scaler.scale_[:5])
print()

# Try feeding RAW values at different magnitudes to see what the model does
for label, raw_val in [("all zeros", 0.0), ("all 0.5", 0.5), ("all 1.0", 1.0),
                        ("scaler mean", None), ("low", -1.0), ("high", 2.0)]:
    if raw_val is None:
        # feed the scaler's own mean (should = "average training sample")
        seq = np.tile(scaler.mean_, (30, 1))
    else:
        seq = np.full((30, 24), raw_val)
    scaled = scaler.transform(seq)
    rul = float(lstm.predict(scaled.reshape(1,30,24), verbose=0)[0][0])
    print(f"{label:15s} -> RUL = {rul:.2f}")

# Now simulate a healthy-to-failure sweep using SCALED space directly
print("\n--- Sweep in scaled space (what model actually sees) ---")
for z in [-2, -1, 0, 1, 2]:
    seq = np.full((30, 24), float(z))   # z-score input directly
    rul = float(lstm.predict(seq.reshape(1,30,24), verbose=0)[0][0])
    print(f"z-score {z:+d} -> RUL = {rul:.2f}")