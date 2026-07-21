"""
What score does the Isolation Forest actually flag at?

Run from src/backend:
    python check_threshold.py
"""
import os, joblib, sqlite3

MODELS = os.path.join("..", "models")
m = joblib.load(os.path.join(MODELS, "adsb_iforest.pkl"))

print("=" * 62)
print("ISOLATION FOREST DECISION BOUNDARY")
print("=" * 62)
print(f"  contamination setting : {m.contamination}")
print(f"  offset_ (the boundary): {m.offset_:.6f}")
print(f"  n_estimators          : {m.n_estimators}")
print()
print("  sklearn flags a point when:   score_samples < offset_")
print(f"  So anything below {m.offset_:.4f} is flagged as an anomaly.")
print()

# Show where our real fleet scores actually fall
try:
    conn = sqlite3.connect("aviation_data.db")
    rows = conn.execute("""
        SELECT anomaly_flag, COUNT(*) FROM flight_telemetry
        GROUP BY anomaly_flag
    """).fetchall()
    conn.close()
    total = sum(r[1] for r in rows)
    print("=" * 62)
    print("HOW OFTEN THIS FIRES ON OUR DATA")
    print("=" * 62)
    for flag, n in rows:
        label = "flagged anomalous" if flag == 1 else "normal"
        print(f"  {label:<20} {n:>7}  ({n/total*100:.1f}%)")
except Exception as e:
    print(f"  (could not read database: {e})")

print()
print("=" * 62)
print("WHAT TO SAY")
print("=" * 62)
print(f"""
  "The flag comes from the model's own decision function. sklearn sets
   the boundary at {m.offset_:.4f} based on the contamination rate we
   trained with. A flight scoring below that is flagged; above it is
   treated as normal. We display the continuous score as well, so you
   can see how close to that boundary a given flight sits."
""")