"""Download one image from any open-licence page, save as WebP, record credits.

Use for sources that have no dedicated fetcher (Library of Congress, NASA, Smithsonian,
museum open-access pages, ...). The licence MUST be verifiable on the --page URL.
Only CC0 / public domain / CC BY / CC BY-SA are accepted.

Usage (vault root):
    python -I .claude/skills/enrich-unit-note/scripts/web_fetch.py --prefix 기계요소설계 \
        --url "https://example.org/img.jpg" --name 롤러체인 \
        --license "Public domain" --author "U.S. Navy" \
        --page "https://example.org/item/123" [--title "Roller chain"] [--source "Library of Congress"]

Credits go into attachments/.commons_credits.json (same keys as the other fetchers:
title, page, license, licurl, artist, source), re-read right before writing.
"""
import argparse
import io
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "ObsidianStudyNotesImageFetcher/1.1 (personal study notes; python-urllib)"}
MAX_SIDE = 960
LICURL = {"CC0": "https://creativecommons.org/publicdomain/zero/1.0/"}


def licurl(lic):
    if lic in LICURL:
        return LICURL[lic]
    parts = lic.upper().split()  # e.g. "CC BY-SA 2.0"
    if len(parts) == 3 and parts[0] == "CC":
        return f"https://creativecommons.org/licenses/{parts[1].lower()}/{parts[2]}/"
    return None


def download(url):
    for wait in (0, 20, 60):
        time.sleep(wait + 1)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After")
                w = min(int(ra), 300) if ra and ra.isdigit() else 30
                print(f"  ({e.code}, Retry-After {ra}; waiting {w}s)", flush=True)
                time.sleep(w)
                continue
            sys.exit(f"HTTP {e.code} for {url}")
    sys.exit("still throttled; try later")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--url", required=True, help="direct image URL")
    ap.add_argument("--name", required=True, help="short name -> <prefix>_<name>.webp")
    ap.add_argument("--license", required=True, help='e.g. "CC0", "Public domain", "CC BY 2.0", "CC BY-SA 4.0"')
    ap.add_argument("--author", default="")
    ap.add_argument("--page", required=True, help="source page where the licence can be verified")
    ap.add_argument("--title", default=None)
    ap.add_argument("--source", default=None, help="source label shown in the credits table")
    ap.add_argument("--dest", default="attachments")
    a = ap.parse_args()

    lic = a.license.strip()
    ok = lic in ("CC0", "Public domain") or lic.upper().startswith(("CC BY ", "CC BY-SA "))
    if not ok or "NC" in lic.upper() or "ND" in lic.upper():
        sys.exit(f"REFUSED licence: {lic}")

    dest = pathlib.Path(a.dest)
    out = dest / f"{a.prefix}_{a.name}.webp"
    im = Image.open(io.BytesIO(download(a.url)))
    im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    q = 85
    while True:
        im.save(out, quality=q, method=6)
        if out.stat().st_size <= 1_000_000 or q <= 40:
            break
        q -= 10

    cache = dest / ".commons_credits.json"
    cur = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    from urllib.parse import urlparse
    cur[out.name] = dict(title=a.title or a.name, page=a.page, license=lic,
                         licurl=licurl(lic), artist=a.author.strip(),
                         source=a.source or urlparse(a.page).netloc)
    cache.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {out}  {out.stat().st_size // 1024} KB  [{lic}]")


if __name__ == "__main__":
    main()
