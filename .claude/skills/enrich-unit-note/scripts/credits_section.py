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
        "모두 위키미디어 공용(Wikimedia Commons) 자료이고, 노트에 맞게 크기를 줄이고 WebP로 변환했다.", "",
        "| 그림 | 작성자 | 라이선스 |", "| --- | --- | --- |"]
for f in used:
    c = cred[f]
    lic = f"[{c['license']}]({c['licurl']})" if c.get("licurl") and "BY" in c["license"] else c["license"]
    lic = lic.replace("Public domain", "퍼블릭 도메인")
    rows.append(f"| [{c['title'].rsplit('.', 1)[0]}]({c['page']}) | {c['artist']} | {lic} |")
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
