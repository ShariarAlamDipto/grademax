#!/usr/bin/env python3
"""
Phase 3c — Render Markdown artifacts to self-contained HTML (perfect math via MathJax,
printable to PDF from any browser). Optionally also writes real PDFs if Playwright +
Chromium are available.

Renders:
  data/predictions/{code}/{session}_{year}/paper_p*.md, markscheme_p*.md
  data/analysis/{code}/report.md

Usage: python scripts/predictor/06_render_pdf.py --subject 4PM1 [--pdf]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.env import REPO_ROOT
from lib.config import load_config
from lib.render_html import render_page


def try_pdf(html_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            page = b.new_page()
            page.goto(html_path.resolve().as_uri())
            page.wait_for_timeout(2500)  # let MathJax typeset
            page.pdf(path=str(html_path.with_suffix(".pdf")), format="A4",
                     margin={"top": "12mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
            b.close()
        return True
    except Exception as e:
        print(f"    (pdf skipped: {str(e)[:80]})")
        return False


def render_file(md_path: Path, title: str, want_pdf: bool) -> Path:
    html = render_page(title, md_path.read_text(encoding="utf-8"))
    out = md_path.with_suffix(".html")
    out.write_text(html, encoding="utf-8")
    if want_pdf:
        try_pdf(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--pdf", action="store_true", help="also render PDF via Playwright if available")
    args = ap.parse_args()
    cfg = load_config(args.subject)
    pred_dir = REPO_ROOT / "data" / "predictions" / cfg.code / f"{cfg.target['session']}_{cfg.target['year']}"
    ana_dir = REPO_ROOT / "data" / "analysis" / cfg.code

    rendered = []
    for md in sorted(pred_dir.glob("*.md")):
        title = f"{cfg.code} {md.stem}"
        rendered.append(render_file(md, title, args.pdf))
    report = ana_dir / "report.md"
    if report.exists():
        rendered.append(render_file(report, f"{cfg.code} pattern report", args.pdf))

    for r in rendered:
        print(f"  rendered {r.relative_to(REPO_ROOT)}")
    print(f"[{cfg.code}] {len(rendered)} HTML file(s) written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
