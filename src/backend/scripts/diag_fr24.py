"""
FR24 — find out what is ACTUALLY happening.

The previous script only searched the HTML for the word "maintenance", which
was a guess, not a diagnosis. This one reports the real evidence: status code,
final URL after redirects, server/CDN headers, and the response body.

Usage (from src/backend):
    python diag_fr24.py YOUR_API_KEY
"""
import sys
import json
import urllib.request
import urllib.error

if len(sys.argv) < 2:
    print("Usage: python diag_fr24.py YOUR_API_KEY")
    sys.exit(1)

KEY = sys.argv[1].strip()

# Several candidate endpoints. If only SOME fail, it is not "maintenance".
TARGETS = [
    ("API host root",       "https://fr24api.flightradar24.com/"),
    ("API live positions",  "https://fr24api.flightradar24.com/api/live/flight-positions/full?bounds=37.0,23.5,60.5,77.5"),
    ("API usage endpoint",  "https://fr24api.flightradar24.com/api/usage"),
    ("Main website",        "https://www.flightradar24.com/"),
    ("Unrelated control",   "https://api.github.com/"),
]

INTERESTING_HEADERS = [
    "server", "cf-ray", "cf-cache-status", "x-cache", "via",
    "content-type", "location", "retry-after", "x-ratelimit-remaining",
]


def probe(name, url, with_key=True):
    print("=" * 70)
    print(f"{name}")
    print(f"  {url[:90]}")
    print("=" * 70)

    headers = {
        "Accept": "application/json",
        "Accept-Version": "v1",
        "User-Agent": "AeroTwin-FYP/1.0",
    }
    if with_key and "fr24api" in url:
        headers["Authorization"] = f"Bearer {KEY}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode(errors="replace")
            print(f"  STATUS      : {r.status}")
            print(f"  FINAL URL   : {r.url}")
            for h in INTERESTING_HEADERS:
                v = r.headers.get(h)
                if v:
                    print(f"  {h:<12}: {v}")
            is_html = "<html" in body[:400].lower()
            print(f"  BODY TYPE   : {'HTML page' if is_html else 'data/JSON'}")
            print(f"  BODY (300)  : {body[:300].strip()[:300]}")
            return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  STATUS      : {e.code}  {e.reason}")
        print(f"  FINAL URL   : {e.url}")
        for h in INTERESTING_HEADERS:
            v = e.headers.get(h)
            if v:
                print(f"  {h:<12}: {v}")
        is_html = "<html" in body[:400].lower()
        print(f"  BODY TYPE   : {'HTML page' if is_html else 'data/JSON'}")
        print(f"  BODY (300)  : {body[:300].strip()[:300]}")
        return e.code, body, dict(e.headers)
    except Exception as e:
        print(f"  FAILED      : {type(e).__name__}: {e}")
        return None, "", {}
    finally:
        print()


results = {}
for name, url in TARGETS:
    results[name] = probe(name, url)

# Also try the API WITHOUT the key — if the response is identical, the block
# happens before authentication is ever checked (i.e. it is not your key).
print("=" * 70)
print("SAME ENDPOINT, NO API KEY  (does the key even reach them?)")
print("=" * 70)
nokey = probe("no-key control",
              "https://fr24api.flightradar24.com/api/live/flight-positions/full?bounds=37.0,23.5,60.5,77.5",
              with_key=False)

print("=" * 70)
print("HOW TO READ THIS")
print("=" * 70)
print("""
  * Control (api.github.com) fails too
        -> your network/proxy is the problem, not FR24.

  * Main website loads but API host returns HTML
        -> the API host is blocked or misrouted for you, NOT global maintenance.

  * 'server' or 'cf-ray' header present with an HTML body
        -> a CDN/WAF is blocking the request. Often geographic or bot filtering.
           A VPN or a different network would confirm this in one minute.

  * Identical response with and without the API key
        -> you are being blocked BEFORE authentication. The key is irrelevant,
           so no amount of key regeneration will fix it.

  * JSON error mentioning subscription/credits
        -> genuine account issue. Contact FR24 support with that message.
""")