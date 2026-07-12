#!/usr/bin/env python3
"""
Phase 4 — Publish prediction artifacts into public/predictor/ so the admin UI
(and CDN) can serve them, and refresh public/predictor/index.json.

Usage: python scripts/predictor/07_publish.py --subject 4PM1
"""
from __future__ import annotations
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.env import REPO_ROOT
from lib.config import load_config

PUB = REPO_ROOT / "public" / "predictor"


def publish_subject(code: str) -> dict | None:
    cfg = load_config(code)
    tag = f"{cfg.target['session']}_{cfg.target['year']}"
    pred = REPO_ROOT / "data" / "predictions" / cfg.code / tag
    ana = REPO_ROOT / "data" / "analysis" / cfg.code
    if not (pred / "blueprint.json").exists():
        print(f"[{code}] no blueprint — skip"); return None

    dest = PUB / cfg.code / tag
    dest.mkdir(parents=True, exist_ok=True)

    # copy artifacts that exist
    def cp(src: Path):
        if src.exists():
            shutil.copy2(src, dest / src.name); return True
        return False

    cp(pred / "blueprint.json")
    cp(ana / "report.html")
    cp(ana / "patterns.json")
    blueprint = json.loads((pred / "blueprint.json").read_text(encoding="utf-8"))
    paper_ids = list(blueprint["papers"].keys())

    artifacts: dict = {"blueprint": f"{cfg.code}/{tag}/blueprint.json"}
    if (dest / "report.html").exists():
        artifacts["report"] = f"{cfg.code}/{tag}/report.html"
    artifacts["paper"], artifacts["markscheme"] = {}, {}
    for pid in paper_ids:
        if cp(pred / f"paper_p{pid}.html"):
            artifacts["paper"][pid] = f"{cfg.code}/{tag}/paper_p{pid}.html"
        if cp(pred / f"markscheme_p{pid}.html"):
            artifacts["markscheme"][pid] = f"{cfg.code}/{tag}/markscheme_p{pid}.html"
        for ext in ("pdf",):  # include PDFs if rendered
            cp(pred / f"paper_p{pid}.{ext}")
            cp(pred / f"markscheme_p{pid}.{ext}")

    summary = []
    for pid, p in blueprint["papers"].items():
        top = sorted({s["topic_name"]: 0 for s in p["slots"]}.keys())
        summary.append({
            "paper": pid, "name": p["paper_name"],
            "question_count": p["question_count"],
            "predicted_marks": p["predicted_marks"], "total_marks": p["total_marks"],
            "high_conf": sum(1 for s in p["slots"] if s["confidence_band"] == "high"),
        })

    return {
        "code": cfg.code, "name": cfg.name, "target": cfg.target,
        "dir": f"{cfg.code}/{tag}", "papers": paper_ids,
        "artifacts": artifacts, "summary": summary,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()
    PUB.mkdir(parents=True, exist_ok=True)
    idx_path = PUB / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"subjects": []}

    entry = publish_subject(args.subject)
    if entry:
        index["subjects"] = [s for s in index.get("subjects", []) if s.get("code") != entry["code"]]
        index["subjects"].append(entry)
        index["subjects"].sort(key=lambda s: s["code"])
        index["generated_at"] = datetime.now(timezone.utc).isoformat()
        idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{args.subject}] published -> public/predictor/{entry['dir']} (index has {len(index['subjects'])} subjects)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
