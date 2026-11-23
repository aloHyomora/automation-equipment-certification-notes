"""Download Commons images, shrink them, save as WebP, and print a credits table.

Usage (run from the vault root):
    python -I .claude/skills/enrich-unit-note/scripts/commons_fetch.py \
        --prefix 공유압 \
        "File:Working principle of a hydraulic jack.svg=파스칼_유압잭" \
        "File:Venturi-tube.svg=벤투리관"

Each argument is "<Commons title>=<short name>". The image is saved to
attachments/<prefix>_<short name>.webp (animated GIFs stay animated).
SVGs are fetched as Commons' PNG rendering, so nothing executable lands in the vault.

At the end it prints a markdown table for the note's "### 그림 출처" section.
A small cache (credits JSON next to this script's work dir) lets you rerun after a
429 without downloading the finished files again.
"""
import argparse
import io
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageSequence

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "study-notes-client/1.0 (educational notes)"}
API = "https://commons.wikimedia.org/w/api.php?"
MAX_SIDE = 960


def get(url):
    for wait in (0, 30, 60, 120, 240):
        time.sleep(wait + 4)
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            print("  (429 rate limited, backing off)", flush=True)
    raise SystemExit("Commons kept refusing; rerun later — finished files are kept.")


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True, help="subject prefix, e.g. 공유압")
    ap.add_argument("--dest", default="attachments")
    ap.add_argument("items", nargs="+", help='"File:Title.ext=short_name"')
    a = ap.parse_args()

    dest = pathlib.Path(a.dest)
    cache = dest / ".commons_credits.json"
    credits = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}

    for item in a.items:
        title, name = item.rsplit("=", 1)
        out = dest / f"{a.prefix}_{name}.webp"
        if out.exists() and out.name in credits:
            print("skip (done)", out.name)
            continue
        params = dict(action="query", format="json", titles=title, prop="imageinfo",
                      iiprop="url|extmetadata", iiurlwidth=MAX_SIDE,
                      iiextmetadatafilter="LicenseShortName|LicenseUrl|Artist")
        d = json.loads(get(API + urllib.parse.urlencode(params)))
        page = next(iter(d["query"]["pages"].values()))
        if "imageinfo" not in page:
            print("NOT FOUND:", title)
            continue
        ii = page["imageinfo"][0]
        m = ii["extmetadata"]
        to_webp(get(ii.get("thumburl") or ii["url"]), out)
        credits[out.name] = dict(
            title=title.removeprefix("File:"), page=ii["descriptionurl"],
            license=m.get("LicenseShortName", {}).get("value", "?"),
            licurl=m.get("LicenseUrl", {}).get("value"),
            artist=re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip().replace("\n", " "))
        cache.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"saved {out}  {out.stat().st_size // 1024} KB  [{credits[out.name]['license']}]", flush=True)

    print("\n| 그림 | 작성자 | 라이선스 |\n| --- | --- | --- |")
    for item in a.items:
        name = f"{a.prefix}_{item.rsplit('=', 1)[1]}.webp"
        c = credits.get(name)
        if not c:
            continue
        lic = f"[{c['license']}]({c['licurl']})" if c.get("licurl") and "BY" in c["license"] else c["license"]
        lic = lic.replace("Public domain", "퍼블릭 도메인")
        print(f"| [{c['title'].rsplit('.', 1)[0]}]({c['page']}) | {c['artist']} | {lic} |")


if __name__ == "__main__":
    main()
