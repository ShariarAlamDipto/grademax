#!/usr/bin/env python3
"""
Run the full predictor pipeline for a subject.

Stages: extract -> analyze -> predict -> generate -> render -> publish.

Usage:
  python scripts/predictor/run_all.py --subject 4PM1
  python scripts/predictor/run_all.py --subject 4PH1 --skip-extract   # reuse questions.jsonl
  python scripts/predictor/run_all.py --subject 4PM1 --from analyze    # start mid-pipeline
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

STAGES = [
    ("extract",  "02_extract_questions.py"),
    ("analyze",  "03_analyze_patterns.py"),
    ("predict",  "04_predict.py"),
    ("generate", "05_generate_paper.py"),
    ("render",   "06_render_pdf.py"),
    ("publish",  "07_publish.py"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--skip-extract", action="store_true")
    ap.add_argument("--from", dest="start", choices=[s[0] for s in STAGES])
    ap.add_argument("--pdf", action="store_true")
    args = ap.parse_args()

    started = args.start is None
    for name, script in STAGES:
        if args.start and name == args.start:
            started = True
        if not started:
            continue
        if name == "extract" and args.skip_extract:
            print(f"== skip {name} =="); continue
        cmd = [PY, str(HERE / script), "--subject", args.subject]
        if name == "render" and args.pdf:
            cmd.append("--pdf")
        print(f"\n===== {name}: {' '.join(cmd[1:])} =====")
        r = subprocess.run(cmd)
        if r.returncode != 0:
            print(f"!! stage '{name}' failed (exit {r.returncode})"); return r.returncode
    print(f"\n✅ pipeline complete for {args.subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
