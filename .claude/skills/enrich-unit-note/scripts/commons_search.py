"""Search Wikimedia Commons for freely licensed images.

Usage:
    python -I commons_search.py "pneumatic cylinder" "venturi tube" ...

Prints one line per hit: title, pixel size, license, author.
Commons rate-limits aggressively (HTTP 429), so queries are spaced out and
retried with backoff. Run several queries in one call rather than many calls.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "study-notes-client/1.0 (educational notes)"}
API = "https://commons.wikimedia.org/w/api.php?"
OK_LICENSES = ("CC0", "Public domain", "CC BY", "CC BY-SA", "PD")


def get_json(params):
    url = API + urllib.parse.urlencode(params)
    for wait in (0, 20, 45, 90):
        time.sleep(wait + 3)
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            print("  (429 rate limited, backing off)", flush=True)
    raise SystemExit("Commons kept refusing; try again in a few minutes.")


for q in sys.argv[1:]:
    d = get_json(dict(action="query", format="json", generator="search", gsrnamespace=6, gsrlimit=10,
                      gsrsearch=q + " -filetype:pdf", prop="imageinfo", iiprop="size|extmetadata",
                      iiextmetadatafilter="LicenseShortName|Artist"))
    print("##", q, flush=True)
    for p in d.get("query", {}).get("pages", {}).values():
        ii = p["imageinfo"][0]
        m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "?")
        if not lic.startswith(OK_LICENSES):
            continue  # skip fair-use / unclear licenses
        artist = re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value", ""))[:40].replace("\n", " ")
        print(f"   {p['title']}  {ii['width']}x{ii['height']} | {lic} | {artist}", flush=True)
