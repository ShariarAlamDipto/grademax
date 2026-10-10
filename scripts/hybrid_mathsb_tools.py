"""
Hybrid helpers for the Maths B workbook solver: render a question's QP+MS into a
single image for a human/Opus to read, and write a hand-produced solution back
into the part cache. Used to finish the questions the free Gemini tier could not
solve, and to correct the few it got wrong.

USAGE
  # render given slugs (or all still-failed / flagged) to data/workbook/_hybrid/
  python scripts/hybrid_mathsb_tools.py render --part 1 --failed
  python scripts/hybrid_mathsb_tools.py render --part 1 --slugs MB.CH03.S01.Q057

  # apply a solution from a JSON file: {slug: {solution...}} or a single record
  python scripts/hybrid_mathsb_tools.py apply --part 1 --file sol.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
MATHSB_ROOT = REPO_ROOT / "data" / "workbook" / "mathsb"
HYBRID_DIR = REPO_ROOT / "data" / "workbook" / "_hybrid"


def cache_path(part: int) -> Path:
    return REPO_ROOT / "data" / "workbook" / f"mathsb_worked_solutions_part{part}.json"


def render_combined(qp_pdf: Path, ms_pdf: Path | None, out: Path, dpi: int = 120) -> None:
    """Stack all QP pages then all MS pages vertically into one PNG."""
    pixes = []
    for pdf in [qp_pdf, ms_pdf]:
        if pdf and pdf.exists():
            with fitz.open(pdf) as doc:
                for pg in doc:
                    pixes.append(pg.get_pixmap(dpi=dpi))
    if not pixes:
        return
    width = max(p.width for p in pixes)
    gap = 12
    height = sum(p.height for p in pixes) + gap * (len(pixes) + 1)
    canvas = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), False)
    canvas.clear_with(255)
    y = gap
    for p in pixes:
        if p.n - p.alpha < 3:  # normalise to RGB
            p = fitz.Pixmap(fitz.csRGB, p)
        p.set_origin(0, y)
        canvas.copy(p, fitz.IRect(0, y, p.width, y + p.height))
        y += p.height + gap
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def cmd_render(args) -> None:
    cache = json.loads(cache_path(args.part).read_text(encoding="utf-8"))
    slugs: list[str] = list(args.slugs or [])
    if args.failed:
        slugs += [s for s, r in cache.items() if not (r.get("solution") or {})]
    if args.flagged:
        for s, r in cache.items():
            sol = r.get("solution") or {}
            if sol and (not sol.get("ms_math_correct", True) or not sol.get("answer_agrees_with_ms", True)):
                slugs.append(s)
    slugs = sorted(set(slugs))
    HYBRID_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for s in slugs:
        rec = cache[s]
        qp = REPO_ROOT / rec["qp_pdf"]
        ms = REPO_ROOT / rec["ms_pdf"] if rec.get("ms_pdf") else None
        out = HYBRID_DIR / f"{s}.png"
        render_combined(qp, ms, out)
        manifest[s] = {
            "source": rec["source"], "marks": rec["marks"],
            "chapter": rec["chapter"], "section": rec["section"],
            "image": str(out.relative_to(REPO_ROOT)).replace("\\", "/"),
        }
        print(f"  {s}  {rec['source']} ({rec['marks']}m) -> {out.name}")
    (HYBRID_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(slugs)} rendered -> {HYBRID_DIR.relative_to(REPO_ROOT)}")


def cmd_apply(args) -> None:
    path = cache_path(args.part)
    cache = json.loads(path.read_text(encoding="utf-8"))
    incoming = json.loads(Path(args.file).read_text(encoding="utf-8"))
    n = 0
    for slug, sol in incoming.items():
        if slug not in cache:
            print(f"  SKIP unknown slug {slug}")
            continue
        # accept either a bare solution dict or {solution:{...}}
        solution = sol.get("solution", sol)
        cache[slug]["solution"] = solution
        cache[slug]["model"] = "opus-hybrid"
        n += 1
        print(f"  applied {slug}: {str(solution.get('final_answer'))[:50]}")
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{n} solutions applied to {path.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--part", type=int, default=1)
    r.add_argument("--slugs", nargs="*")
    r.add_argument("--failed", action="store_true")
    r.add_argument("--flagged", action="store_true")
    r.set_defaults(func=cmd_render)
    a = sub.add_parser("apply")
    a.add_argument("--part", type=int, default=1)
    a.add_argument("--file", required=True)
    a.set_defaults(func=cmd_apply)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
