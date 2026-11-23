"""Render SVG drawings to PNG with headless Edge so you can look at them with the Read tool.

Usage (vault root):
    python -I .claude/skills/enrich-unit-note/scripts/render_check.py <out_dir> attachments/자동제어_근궤적.svg [more.svg ...]

Writes <out_dir>/render_gallery.html, screenshots it, and splits the result into
<out_dir>/render_0.png, render_1.png, ... (about 3 drawings per image). Open each PNG
with Read and check: overlapping text, text cut off at the right edge, and whether
the drawing is physically/mathematically right. Use a scratch directory for out_dir.
"""
import pathlib
import subprocess
import sys
import time

from PIL import Image

out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
svgs = [pathlib.Path(s) for s in sys.argv[2:]]
parts = []
for s in svgs:
    svg = s.read_text(encoding="utf-8").replace("<svg ", '<svg width="600" ', 1)
    parts.append(f'<div style="margin:8px 0"><div style="font:12px sans-serif;background:#eee">{s.name}</div>{svg}</div>')
html = out / "render_gallery.html"
html.write_text('<html><body style="margin:0;background:#888">' + "".join(parts) + "</body></html>", encoding="utf-8")

edge = next((p for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if pathlib.Path(p).exists()), None)
if not edge:
    sys.exit("Edge not found; open the SVGs in the browser pane instead.")
height = 420 * max(1, len(svgs)) + 100
png = out / "render_full.png"
subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--screenshot={png}",
                f"--window-size=620,{height}", html.as_uri()], capture_output=True, timeout=60)
for _ in range(20):
    if png.exists():
        break
    time.sleep(0.5)
im = Image.open(png)
step = 1200
for i in range(0, im.size[1], step):
    part = out / f"render_{i // step}.png"
    im.crop((0, i, 620, min(im.size[1], i + step))).save(part)
    print(part)
