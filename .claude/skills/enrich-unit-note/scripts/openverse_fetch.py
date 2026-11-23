"""Download Openverse images by id, save as WebP, and record credits.

Usage (vault root):
    python -I .claude/skills/enrich-unit-note/scripts/openverse_fetch.py --prefix 자동제어 \
        "0eff3e5c-77ce-46c2-9a26-702fa2ab9373=릴레이_원리"

Each argument is "<openverse id>=<short name>" (ids come from openverse_search.py).
Images come through Openverse's own thumbnail proxy, so this still works while
Wikimedia Commons is rate-limiting. Credits go into the same
attachments/.commons_credits.json used by commons_fetch.py, so credits_section.py
builds one table for both sources.
"""
import argparse
import io
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageSequence

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "ObsidianStudyNotesImageFetcher/1.1 (personal study notes; python-urllib)"}
API = "https://api.openverse.org/v1/images/"
MAX_SIDE = 960
OK = {"cc0", "pdm", "by", "by-sa"}


def get(url):
    for wait in (0, 15, 40):
        time.sleep(wait + 2)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                print(f"  ({e.code}, backing off)", flush=True)
                continue
            # 424 = Openverse could not reach the upstream file; 404 etc. = gone.
            # Return None so the caller tries the next download route.
            print(f"  ({e.code} from {url.split('?')[0][-60:]}, trying next route)", flush=True)
            return None
        except urllib.error.URLError as e:
            print(f"  (network error {e.reason}, trying next route)", flush=True)
            return None
    return None


def to_webp(data, out):
    im = Image.open(io.BytesIO(data))
    if getattr(im, "is_animated", False):
        frames = [f.convert("RGBA") for f in ImageSequence.Iterator(im)]
        frames[0].save(out, save_all=True, append_images=frames[1:],
                       duration=im.info.get("duration", 100), loop=0, quality=85)
    else:
        im = im.convert("RGBA") if im.mode in ("P", "LA", "RGBA") else im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE))
        im.save(out, quality=85, method=6)


def license_name(r):
    lic, ver = r["license"], r.get("license_version") or ""
    if lic == "cc0":
        return "CC0"
    if lic == "pdm":
        return "Public domain"
    return f"CC {lic.upper()} {ver}".strip()


def save_credit(cache, name, entry):
    # re-read right before writing so a parallel run's entries are not lost
    cur = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    cur[name] = entry
    cache.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--dest", default="attachments")
    ap.add_argument("items", nargs="+", help='"<openverse id>=short_name"')
    a = ap.parse_args()
    dest = pathlib.Path(a.dest)
    cache = dest / ".commons_credits.json"

    for item in a.items:
        oid, name = item.rsplit("=", 1)
        out = dest / f"{a.prefix}_{name}.webp"
        raw = get(API + oid + "/")
        if raw is None:
            print("SKIPPED (throttled):", out.name); continue
        r = json.loads(raw)
        if r["license"] not in OK:
            print("REFUSED license", r["license"], out.name); continue
        # routes: Openverse proxy (full) -> Openverse proxy (small, often cached) -> original file
        data = (get(API + oid + "/thumb/?full_size=true")
                or get(API + oid + "/thumb/")
                or get(r["url"]))
        if data is None:
            print("SKIPPED (throttled):", out.name); continue
        to_webp(data, out)
        save_credit(cache, out.name, dict(
            title=r["title"], page=r.get("foreign_landing_url") or r["url"],
            license=license_name(r), licurl=r.get("license_url"),
            artist=(r.get("creator") or "").strip(), source=f"Openverse ({r['source']})"))
        print(f"saved {out}  {out.stat().st_size // 1024} KB  [{license_name(r)}, {r['source']}]", flush=True)


if __name__ == "__main__":
    main()
