"""Check every local link in a note: images/notes must exist, '#heading' anchors must match a heading.

Usage (vault root):  python -I .claude/skills/enrich-unit-note/scripts/link_check.py <note.md> [<note2.md> ...]
Prints broken links per note; "broken 0" for each note means safe.
"""
import pathlib
import re
import sys
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
total = 0
for arg in sys.argv[1:]:
    p = pathlib.Path(arg)
    t = p.read_text(encoding="utf-8")
    heads = {re.sub(r"^#+\s*", "", l).strip() for l in t.split("\n") if l.startswith("#")}
    bad = []
    for target in re.findall(r"\]\(([^)\s]+)\)", t):
        target = target.rstrip("\\")
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        path, _, frag = target.partition("#")
        if not path:
            if urllib.parse.unquote(frag) not in heads:
                bad.append(target)
        elif not (p.parent / urllib.parse.unquote(path)).exists():
            bad.append(target)
    total += len(bad)
    print(f"{p}: broken {len(bad)}")
    for b in bad:
        print("   ", b)
sys.exit(1 if total else 0)
