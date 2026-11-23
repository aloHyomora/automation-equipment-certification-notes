"""Check that a restructured note lost no content versus the last commit.

Usage (vault root):  python -I .claude/skills/enrich-unit-note/scripts/loss_check.py <note.md> [<git-rev>]
Prints missing original lines; "missing: 0" means safe to commit.
"""
import sys
import re, subprocess, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8")
f = sys.argv[1]
old = subprocess.run(["git", "show", f"{sys.argv[2] if len(sys.argv) > 2 else 'HEAD'}:{f}"], capture_output=True).stdout.decode("utf-8")
new = pathlib.Path(f).read_text(encoding="utf-8")
def core(s):
    s = re.sub(r"^\s*(#+|[-*>]|\d+\.)\s*", "", s)
    s = re.sub(r"[*|`_]", "", s)
    s = re.sub(r"\]\([^)]*\)", "]", s)
    return re.sub(r"\s+", " ", s).strip()
newcore = core(new.replace("\n", " ")) if False else " ".join(core(l) for l in new.split("\n"))
miss = []
for l in old.split("\n"):
    c = core(l)
    if not c or set(c) <= set("-: "): continue
    if c not in newcore:
        # section list lines: check number+title+page all present on one table row
        m = re.match(r"(?:핵심이론 )?(\d\d) (.+) \((p\.[^)]*)\)$", c)
        if m and any(m.group(1) in r and m.group(2) in r and m.group(3) in r for r in new.split("\n") if r.startswith("|")):
            continue
        miss.append(l)
print("missing:", len(miss)); [print("  ", x[:120]) for x in miss]
