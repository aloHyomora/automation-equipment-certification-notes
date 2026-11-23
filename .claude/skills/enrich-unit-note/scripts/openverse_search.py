"""Search Openverse (openly licensed images from Wikimedia, Flickr, museums, NASA, ...).

Use when Wikimedia Commons has nothing suitable or keeps answering 429.
No API key needed for light use.

Usage:
    python -I openverse_search.py "relay coil contact" "optocoupler"

Prints: openverse-id | title | license | creator | source | size
Only CC0 / public domain / CC BY / CC BY-SA results are requested.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "ObsidianStudyNotesImageFetcher/1.1 (personal study notes; python-urllib)"}
API = "https://api.openverse.org/v1/images/?"

args = sys.argv[1:]
# --no-wikimedia: skip Wikimedia-hosted files. Use it while Wikimedia is rate-limiting,
# because Openverse's proxy cannot fetch those either (it answers 424).
params = dict(license="cc0,pdm,by,by-sa", page_size=10)
if "--no-wikimedia" in args:
    args.remove("--no-wikimedia")
    params["excluded_source"] = "wikimedia"

for q in args:
    time.sleep(2)
    url = API + urllib.parse.urlencode(dict(params, q=q))
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
    except urllib.error.HTTPError as e:
        print("##", q, "ERR", e.code); continue
    print(f"## {q}  ({d.get('result_count', 0)} hits)", flush=True)
    for r in d.get("results", []):
        lic = f"{r['license']} {r.get('license_version') or ''}".strip()
        print(f"   {r['id']} | {r['title'][:60]} | {lic} | {(r.get('creator') or '')[:30]} | {r['source']} | {r.get('width')}x{r.get('height')}", flush=True)
