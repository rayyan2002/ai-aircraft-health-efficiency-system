"""
fetch_fr24_summaries.py
=======================
Pulls Flightradar24 flight summaries (takeoff, landing, route) for every
fleet registration over a date range into the fr24_flight_summary table.
This is the reference flight list the OpenSky capture rate is measured
against, and the source of observed flight cycles per tail.

The API allows at most 15 registrations and 14 days per request, so the
range is split into 7-day windows and groups of 15. Summary data starts
2024-04-07; how far back your plan reaches depends on its tier.

Run from src/backend (dates are UTC, both inclusive):
    python scripts/fetch_fr24_summaries.py --from 2026-10-20 --to 2026-11-02 --count-only
    python scripts/fetch_fr24_summaries.py --from 2026-10-20 --to 2026-11-02
    python scripts/fetch_fr24_summaries.py --from 2026-10-20 --to 2026-11-02 --full
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BACKEND, "aviation_data.db")
BASE = "https://fr24api.flightradar24.com/api"
GROUP = 15
WINDOW_DAYS = 7
PAUSE_S = 7


def api_key():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BACKEND, ".env"))
    except ImportError:
        pass
    key = os.getenv("FR24_API_KEY", "").strip()
    if not key:
        sys.exit("FR24_API_KEY is not set (src/backend/.env or the shell).")
    return key


def headers(key):
    return {
        "Accept": "application/json",
        "Accept-Version": "v1",
        "User-Agent": "AeroTwin-FYP/1.0",
        "Authorization": f"Bearer {key}",
    }


def credits_used(key):
    try:
        r = requests.get(f"{BASE}/usage", headers=headers(key), timeout=(10, 25))
        if r.status_code != 200:
            return None
        return sum(int(d.get("credits", 0)) for d in (r.json() or {}).get("data", []))
    except Exception:
        return None


def windows(start, end):
    t = start
    while t < end:
        u = min(t + timedelta(days=WINDOW_DAYS), end)
        yield t, u
        t = u


def get(url, key, params):
    for attempt in range(2):
        r = requests.get(url, headers=headers(key), params=params, timeout=(10, 60))
        if r.status_code == 429 and attempt == 0:
            print("  rate limited, waiting 60 s")
            time.sleep(60)
            continue
        return r
    return r


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fr24_flight_summary (
            fr24_id          TEXT PRIMARY KEY,
            reg              TEXT,
            hex              TEXT,
            callsign         TEXT,
            flight           TEXT,
            type             TEXT,
            orig_icao        TEXT,
            dest_icao        TEXT,
            dest_icao_actual TEXT,
            datetime_takeoff TEXT,
            datetime_landed  TEXT,
            first_seen       TEXT,
            last_seen        TEXT,
            flight_ended     INTEGER,
            detail           TEXT,
            raw              TEXT,
            fetched_at       TEXT
        )
    """)


def store(conn, rows, detail):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for f in rows:
        ended = f.get("flight_ended")
        conn.execute("""
            INSERT OR REPLACE INTO fr24_flight_summary VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f.get("fr24_id"), f.get("reg"), f.get("hex"), f.get("callsign"),
            f.get("flight"), f.get("type"), f.get("orig_icao"), f.get("dest_icao"),
            f.get("dest_icao_actual"), f.get("datetime_takeoff"), f.get("datetime_landed"),
            f.get("first_seen"), f.get("last_seen"),
            None if ended is None else int(bool(ended)),
            detail, json.dumps(f), now,
        ))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (UTC)")
    ap.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD (UTC), inclusive")
    ap.add_argument("--full", action="store_true", help="full summaries (runways, distance, flight time)")
    ap.add_argument("--count-only", action="store_true", help="only count matching flights")
    args = ap.parse_args()

    start = datetime.strptime(args.date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(args.date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    if end <= start:
        sys.exit("--to must not be before --from.")

    key = api_key()
    conn = sqlite3.connect(DB_PATH)
    regs = [r[0] for r in conn.execute(
        "SELECT tail_number FROM fleet WHERE tail_number IS NOT NULL ORDER BY tail_number")]
    groups = [regs[i:i + GROUP] for i in range(0, len(regs), GROUP)]
    detail = "full" if args.full else "light"
    endpoint = "count" if args.count_only else detail
    ensure_table(conn)

    before = credits_used(key)
    total, failures, first = 0, [], True
    for t0, t1 in windows(start, end):
        for group in groups:
            if not first:
                time.sleep(PAUSE_S)
            first = False
            params = {
                "flight_datetime_from": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "flight_datetime_to": t1.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "registrations": ",".join(group),
            }
            if not args.count_only:
                params["limit"] = 20000
            label = f"{t0:%Y-%m-%d}..{t1:%Y-%m-%d} {group[0]}..{group[-1]}"
            try:
                r = get(f"{BASE}/flight-summary/{endpoint}", key, params)
            except Exception as e:
                failures.append(f"{label}: {type(e).__name__}")
                print(f"  {label}: request failed ({type(e).__name__})")
                continue
            if r.status_code != 200:
                failures.append(f"{label}: HTTP {r.status_code}")
                print(f"  {label}: HTTP {r.status_code} {r.text[:160]}")
                continue
            body = r.json() or {}
            if args.count_only:
                n = int(body.get("record_count", 0))
            else:
                rows = body.get("data") or []
                store(conn, rows, detail)
                conn.commit()
                n = len(rows)
            total += n
            print(f"  {label}: {n}")

    conn.close()
    after = credits_used(key)
    print(f"\n{'Counted' if args.count_only else 'Stored'} {total} flight summaries "
          f"for {len(regs)} registrations, {args.date_from} to {args.date_to}.")
    if before is not None and after is not None:
        print(f"Credits used by this run: {after - before}")
    if failures:
        print(f"{len(failures)} request(s) failed — the reference list is INCOMPLETE:")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
