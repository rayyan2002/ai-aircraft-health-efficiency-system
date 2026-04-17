"""
train_lstm.py  —  Aircraft Engine RUL Prediction (LSTM)
========================================================
Extracted from LSTM_TIMESERIES_i__1.ipynb

Place this file in the same folder as:
  - X_train_lstm.npy
  - y_train_lstm.npy
  - test_FD001.txt       (optional — only needed for NASA validation)
  - RUL_FD001.txt        (optional — only needed for NASA validation)

Outputs written to ./models/:
  - engine_model_v1.keras     ← what main.py loads
  - scaler_features.pkl       ← what main.py loads
  - scaler_target.pkl
  - api_config.json

Run:
  pip install tensorflow scikit-learn joblib matplotlib pandas numpy
  python train_lstm.py
"""

import os
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

import tensorflow as tf
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error

print("=" * 60)
print("  LSTM ENGINE RUL TRAINER")
print(f"  TensorFlow: {tf.__version__}")
print("=" * 60)

os.makedirs("models", exist_ok=True)

# ──────────────────────────────────────────────────────────────
# STEP 1 — LOAD PRE-GENERATED TRAINING ARRAYS
# (Generated from train_FD001.txt in the original notebook.
#  Skip if you already have the .npy files — which you do.)
# ──────────────────────────────────────────────────────────────
print("\n[1/5] Loading training data...")

X_train_full = np.load("X_train_lstm.npy")
y_train_full = np.load("y_train_lstm.npy")

print(f"  X shape : {X_train_full.shape}  →  (samples, timesteps, sensors)")
print(f"  y shape : {y_train_full.shape}  →  (RUL labels)")

assert X_train_full.ndim == 3, "X_train_lstm.npy must be 3D (samples, 30, 24)"
assert X_train_full.shape[1] == 30, "Expected 30 timesteps"
assert X_train_full.shape[2] == 24, "Expected 24 sensor features"

# ──────────────────────────────────────────────────────────────
# STEP 2 — TRAIN / VALIDATION SPLIT  (85 / 15)
# ──────────────────────────────────────────────────────────────
print("\n[2/5] Splitting data (85% train / 15% validation)...")

split_idx = int(0.85 * len(X_train_full))

X_train = X_train_full[:split_idx]
X_val   = X_train_full[split_idx:]
y_train = y_train_full[:split_idx]
y_val   = y_train_full[split_idx:]

print(f"  Train : {X_train.shape}")
print(f"  Val   : {X_val.shape}")

# ──────────────────────────────────────────────────────────────
# STEP 3 — BUILD LSTM MODEL
# Architecture is identical to the notebook (3 LSTM layers).
# EarlyStopping + ReduceLROnPlateau added to stop wasted epochs
# and help hit the MAE < 15 target.
# ──────────────────────────────────────────────────────────────
print("\n[3/5] Building model...")

model = Sequential([
    LSTM(128, return_sequences=True, input_shape=(30, 24)),
    Dropout(0.3),
    LSTM(64, return_sequences=True),
    Dropout(0.2),
    LSTM(32, return_sequences=False),
    Dropout(0.2),
    Dense(64, activation="relu"),
    Dropout(0.1),
    Dense(32, activation="relu"),
    Dense(1,  activation="linear"),
])

model.compile(
    optimizer=Adam(learning_rate=0.001),
    loss="mse",
    metrics=["mae"],
)

model.summary()

# ──────────────────────────────────────────────────────────────
# STEP 4 — TRAIN
# ──────────────────────────────────────────────────────────────
print("\n[4/5] Training...")

callbacks = [
    # Stop early if val_loss stops improving for 8 epochs
    EarlyStopping(
        monitor="val_loss",
        patience=8,
        restore_best_weights=True,
        verbose=1,
    ),
    # Halve LR if val_loss plateaus for 4 epochs
    ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=4,
        min_lr=1e-6,
        verbose=1,
    ),
]

history = model.fit(
    X_train, y_train,
    epochs=60,
    batch_size=128,
    validation_data=(X_val, y_val),
    callbacks=callbacks,
    verbose=1,
)

final_val_mae  = history.history["val_mae"][-1]
best_val_mae   = min(history.history["val_mae"])
epochs_run     = len(history.history["loss"])

print(f"\n  Epochs run    : {epochs_run}")
print(f"  Final val MAE : {final_val_mae:.2f} cycles")
print(f"  Best  val MAE : {best_val_mae:.2f} cycles")
print(f"  Benchmark     : {'✅ PASSED (<15)' if best_val_mae < 15 else '❌ FAILED — needs tuning'}")

# ── Validation scatter plot ──
val_pred = model.predict(X_val[:2000], verbose=0).flatten()

plt.figure(figsize=(14, 4))

plt.subplot(1, 3, 1)
plt.plot(history.history["loss"],     label="Train Loss", linewidth=2)
plt.plot(history.history["val_loss"], label="Val Loss",   linewidth=2)
plt.title("Loss Convergence")
plt.xlabel("Epoch"); plt.ylabel("MSE"); plt.legend(); plt.grid(alpha=0.3)

plt.subplot(1, 3, 2)
plt.plot(history.history["mae"],     label="Train MAE", linewidth=2)
plt.plot(history.history["val_mae"], label="Val MAE",   linewidth=2)
plt.title("MAE (Flight Cycles)")
plt.xlabel("Epoch"); plt.ylabel("MAE"); plt.legend(); plt.grid(alpha=0.3)

plt.subplot(1, 3, 3)
plt.scatter(y_val[:2000], val_pred, alpha=0.5, s=15)
plt.plot([y_val.min(), y_val.max()], [y_val.min(), y_val.max()], "r--", linewidth=2)
plt.title(f"Val RUL  —  MAE: {best_val_mae:.1f} cycles")
plt.xlabel("Actual RUL"); plt.ylabel("Predicted RUL"); plt.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("training_curves.png", dpi=150, bbox_inches="tight")
print("  Saved: training_curves.png")
plt.show()

# ──────────────────────────────────────────────────────────────
# STEP 5 — EXPORT  (everything main.py needs goes into models/)
# ──────────────────────────────────────────────────────────────
print("\n[5/5] Exporting production files...")

# 5a. LSTM model
model.save("models/engine_model_v1.keras")
model_mb = os.path.getsize("models/engine_model_v1.keras") / 1_048_576
print(f"  ✅ models/engine_model_v1.keras  ({model_mb:.1f} MB)")

# 5b. Feature scaler  ← main.py uses this as lstm_scaler
#     Fit on the last timestep of every training sequence (24 features)
scaler_features = StandardScaler()
scaler_features.fit(X_train[:, -1, :])
joblib.dump(scaler_features, "models/scaler_features.pkl")
sf_kb = os.path.getsize("models/scaler_features.pkl") / 1024
print(f"  ✅ models/scaler_features.pkl    ({sf_kb:.1f} KB)")

# 5c. Target scaler  (RUL normalisation — optional but saves for completeness)
scaler_target = StandardScaler()
scaler_target.fit(y_train.reshape(-1, 1))
joblib.dump(scaler_target, "models/scaler_target.pkl")
st_kb = os.path.getsize("models/scaler_target.pkl") / 1024
print(f"  ✅ models/scaler_target.pkl      ({st_kb:.1f} KB)")

# 5d. Training history
np.save("models/lstm_training_history.npy", history.history)
print(f"  ✅ models/lstm_training_history.npy")

# 5e. API config JSON
api_config = {
    "model_path":      "models/engine_model_v1.keras",
    "input_shape":     [1, 30, 24],
    "scaler_features": "models/scaler_features.pkl",
    "scaler_target":   "models/scaler_target.pkl",
    "version":         "v1.0",
    "epochs_run":      epochs_run,
    "best_val_mae":    round(float(best_val_mae), 2),
    "benchmark_pass":  bool(best_val_mae < 15),
}
with open("models/api_config.json", "w") as f:
    json.dump(api_config, f, indent=2)
print(f"  ✅ models/api_config.json")

# ──────────────────────────────────────────────────────────────
# OPTIONAL — NASA TEST SET VALIDATION (Day 2)
# Only runs if test_FD001.txt is present in the same folder.
# ──────────────────────────────────────────────────────────────
if os.path.exists("test_FD001.txt"):
    print("\n[OPTIONAL] NASA test set validation...")

    test_df = pd.read_csv("test_FD001.txt", sep=r"\s+", header=None)
    columns = (
        ["unit", "cycle", "op1", "op2", "op3"]
        + [f"sensor{i}" for i in range(1, 22)]
    )
    test_df.columns = columns[: len(test_df.columns)]

    # Load RUL ground truth
    if os.path.exists("RUL_FD001.txt"):
        rul_df = pd.read_csv("RUL_FD001.txt", header=None, names=["RUL"])
    else:
        print("  ⚠️ RUL_FD001.txt not found — using NASA FD001 standard fallback (125 cycles)")
        rul_df = pd.DataFrame({"RUL": [125] * 100})

    test_df["RUL"] = 0
    for unit_id in test_df["unit"].unique():
        idx     = min(int(unit_id) - 1, len(rul_df) - 1)
        unit_rul = rul_df.iloc[idx]["RUL"]
        last_idx = test_df[test_df["unit"] == unit_id]["cycle"].idxmax()
        test_df.loc[last_idx, "RUL"] = unit_rul

    feature_cols = [c for c in test_df.columns if c not in ("unit", "cycle", "RUL")]
    SEQ = 30
    X_seq, y_seq = [], []

    for unit in test_df["unit"].unique():
        unit_data = test_df[test_df["unit"] == unit][feature_cols].values
        unit_rul  = test_df[test_df["unit"] == unit]["RUL"].iloc[-1]
        if unit_rul == 0:
            unit_rul = 125
        if len(unit_data) >= SEQ:
            for i in range(len(unit_data) - SEQ + 1):
                X_seq.append(unit_data[i : i + SEQ])
                y_seq.append(unit_rul)

    X_test_seq = np.array(X_seq)
    y_test_seq = np.array(y_seq)

    test_pred = model.predict(X_test_seq, verbose=0).flatten()
    test_mae  = float(np.mean(np.abs(test_pred - y_test_seq)))
    test_rmse = float(np.sqrt(mean_squared_error(y_test_seq, test_pred)))

    print(f"  NASA Test MAE  : {test_mae:.1f} cycles")
    print(f"  NASA Test RMSE : {test_rmse:.1f} cycles")
    print(f"  Benchmark      : {'✅ PASSED (<15)' if test_mae < 15 else '❌ FAILED — needs tuning'}")

    api_config["nasa_test_mae"]  = round(test_mae,  2)
    api_config["nasa_test_rmse"] = round(test_rmse, 2)
    with open("models/api_config.json", "w") as f:
        json.dump(api_config, f, indent=2)
else:
    print("\n  ℹ️  test_FD001.txt not found — skipping NASA validation.")
    print("      Copy the file here and re-run to get test MAE.")

# ──────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ──────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  EXPORT COMPLETE — copy these to your project's models/ folder:")
print("=" * 60)
for f in ["engine_model_v1.keras", "scaler_features.pkl",
          "scaler_target.pkl", "api_config.json"]:
    path = f"models/{f}"
    if os.path.exists(path):
        kb = os.path.getsize(path) / 1024
        print(f"  ✅  {f:<35} {kb:>7.1f} KB")
    else:
        print(f"  ❌  {f}  — MISSING")

print(f"\n  Best val MAE : {best_val_mae:.2f} cycles")
print(f"  Target       : < 15 cycles")
print("=" * 60)
