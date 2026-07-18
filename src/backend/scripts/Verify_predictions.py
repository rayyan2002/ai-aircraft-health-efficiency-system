"""
verify_predictions.py  —  AeroTwin prediction sanity harness
Run with the backend live (uvicorn on :8000).  python verify_predictions.py

It does NOT validate RUL against ground truth (none exists for the live fleet).
It verifies the three properties that define a trustworthy *calibrated* system:
  1. No ghost fallbacks  — no aircraft returns the hardcoded 45.2 default
  2. Monotonicity        — more cycles => lower RUL (correct degradation direction)
  3. Real spread         — RUL is distributed, not clustered at one value
"""
import requests

BASE = "http://localhost:8000/api"

def get_fleet():
    r = requests.get(f"{BASE}/pak_fleet", timeout=15)
    r.raise_for_status()
    data = r.json()
    # be defensive about response shape
    fleet = data if isinstance(data, list) else data.get("fleet") or data.get("aircraft") or []
    out = []
    for a in fleet:
        tail = a.get("tail_number") or a.get("tail")
        cyc  = a.get("total_cycles") or a.get("cycles") or 0
        if tail:
            out.append((tail, float(cyc)))
    return out

def analyze(tail):
    r = requests.get(f"{BASE}/pak_analyze/{tail}", timeout=30)
    r.raise_for_status()
    d = r.json()
    return (
        float(d.get("predicted_rul_cycles", -1)),
        float(d.get("health_score", -1)),
        d.get("risk_level", "?"),
    )

def main():
    fleet = sorted(get_fleet(), key=lambda x: x[1])  # ascending cycles
    rows, ghosts = [], []
    for tail, cyc in fleet:
        try:
            rul, health, risk = analyze(tail)
        except Exception as e:
            print(f"  !! {tail}: {e}")
            continue
        rows.append((tail, cyc, rul, health, risk))
        if abs(rul - 45.2) < 0.05:
            ghosts.append(tail)

    print(f"\n{'tail':10}{'cycles':>9}{'RUL':>8}{'health':>8}  risk")
    print("-" * 45)
    for tail, cyc, rul, health, risk in rows:
        print(f"{tail:10}{cyc:>9.0f}{rul:>8.1f}{health:>8.1f}  {risk}")

    # ---- Property checks ----
    print("\n=== TRUST CHECKS ===")
    print(f"[1] Ghost 45.2 fallbacks: {len(ghosts)}  {'PASS' if not ghosts else 'FAIL -> '+str(ghosts)}")

    ruls = [r[2] for r in rows]
    spread = (max(ruls) - min(ruls)) if ruls else 0
    print(f"[2] RUL spread: {min(ruls):.1f}..{max(ruls):.1f} (range {spread:.1f})  "
          f"{'PASS' if spread > 30 else 'FAIL (too clustered)'}")

    # monotonicity: count how often RUL drops as cycles rise (already sorted by cycles)
    drops = sum(1 for a, b in zip(ruls, ruls[1:]) if b <= a)
    pairs = max(1, len(ruls) - 1)
    pct = 100 * drops / pairs
    print(f"[3] Monotonic (RUL falls as cycles rise): {pct:.0f}% of steps  "
          f"{'PASS' if pct > 80 else 'CHECK'}")

    # determinism spot-check
    if rows:
        t = rows[0][0]
        a1 = analyze(t); a2 = analyze(t)
        print(f"[4] Determinism ({t}): {'PASS' if a1 == a2 else 'FAIL'}  {a1} vs {a2}")

if __name__ == "__main__":
    main()
    