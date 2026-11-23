"""Rebuild a note's '## 참고 / ### 그림 출처' credits table from attachments/.commons_credits.json.

Usage (vault root):  python -I .claude/skills/enrich-unit-note/scripts/credits_section.py <note.md>

Lists every Commons image the note embeds (in order of appearance) that exists on disk,
writes the table right before '## 수신 기록' if present, else at the end of the note,
and reports embedded images that are not downloaded yet.
"""
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
EMBED = re.compile(r"\.\./attachments/([^)|]+?\.webp)")

note = pathlib.Path(sys.argv[1])
t = note.read_text(encoding="utf-8")
cred = json.loads(pathlib.Path("attachments/.commons_credits.json").read_text(encoding="utf-8"))

used = []
for f in EMBED.findall(t):
    f = f.rstrip("\\")
    if f not in used and f in cred and pathlib.Path("attachments", f).exists():
        used.append(f)

rows = ["### 그림 출처", "",
        "위키미디어 공용(Wikimedia Commons)과 Openverse에서 가져온 공개 라이선스 자료이고, 노트에 맞게 크기를 줄이고 WebP로 변환했다.", "",
        "| 그림 | 작성자 | 라이선스 | 출처 |", "| --- | --- | --- | --- |"]
for f in used:
    c = cred[f]
    lic = f"[{c['license']}]({c['licurl']})" if c.get("licurl") and "BY" in c["license"] else c["license"]
    lic = lic.replace("Public domain", "퍼블릭 도메인")
    title = re.sub(r"\.(svg|png|jpe?g|gif|tiff?|webp)$", "", c["title"], flags=re.I)
    src = c.get("source", "Wikimedia Commons")
    rows.append(f"| [{title}]({c['page']}) | {c['artist']} | {lic} | {src} |")
own = []
for f in re.findall(r"\.\./attachments/([^)|]+?\.svg)", t):
    name = f.rstrip("\\").rsplit(".", 1)[0].split("_", 1)[-1].replace("_", " ")
    if name not in own:
        own.append(name)
if own:
    rows += ["", "직접 그린 그림(SVG, 이 볼트용으로 새로 작성): " + ", ".join(own) + "."]
block = "## 참고\n\n" + "\n".join(rows) + "\n\n"

anchor = "## 수신 기록"
t = re.sub(r"## 참고\n.*?(?=" + anchor + r"|\Z)", "", t, flags=re.S) if anchor in t else t
if anchor in t:
    t = t.replace(anchor, block + anchor, 1)
else:
    t = t.rstrip("\n") + "\n\n" + block
note.write_text(t, encoding="utf-8", newline="")

missing = sorted({f.rstrip("\\") for f in EMBED.findall(t) if not pathlib.Path("attachments", f.rstrip("\\")).exists()})
print(f"credited {len(used)}; not yet downloaded ({len(missing)}): {', '.join(missing)}")
