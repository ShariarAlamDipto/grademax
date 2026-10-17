"""One-off: find worked-solution strings containing raw control characters,
which mean json.loads silently ate a LaTeX backslash (e.g. \\frac -> \\x0c+rac,
\\times -> \\x09+imes). These need re-solving or backslash restoration."""
import json, sys, unicodedata
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/workbook/mathsb_worked_solutions_part2.json")
c = json.loads(path.read_text(encoding="utf-8"))

def texts(sol):
    yield "final_answer", sol.get("final_answer", "") or ""
    for i, st in enumerate(sol.get("steps") or []):
        yield f"step{i}", (st or {}).get("step", "") or ""

hits = {}
for slug, rec in c.items():
    sol = rec.get("solution") or {}
    for where, t in texts(sol):
        bad = [(j, ord(ch)) for j, ch in enumerate(t) if ord(ch) < 32]
        if bad:
            hits.setdefault(slug, [])
            for j, o in bad:
                hits[slug].append((where, hex(o), repr(t[max(0, j-6):j+6])))

print(f"solutions with raw control chars: {len(hits)}")
for slug, lst in hits.items():
    print(" ", slug)
    for where, o, ctx in lst:
        print("      ", where, o, ctx)
