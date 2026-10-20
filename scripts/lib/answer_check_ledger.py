"""
Ledger for the question <-> mark-scheme ANSWER read-through
(scripts/build_answer_check_sheets.py makes the sheets; Claude reads them).

data/analysis/answer_check/ledger.json:
  {code: {paper: {"read": true, "pairs": n, "suspects": {question: reason}}}}

`record(code, paper, pairs, suspects)` marks one paper read; a paper with no
suspects means every pair in it was read and the scheme answers its question.
"""

from __future__ import annotations

import json
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[2] / "data" / "analysis" / "answer_check" / "ledger.json"


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.is_file() else {}


def record(code: str, paper: str, pairs: int, suspects: dict | None = None) -> None:
    data = load()
    data.setdefault(code, {})[paper] = {"read": True, "pairs": pairs,
                                        "suspects": {str(k): v for k, v in (suspects or {}).items()}}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")


def progress() -> str:
    data = load()
    papers = sum(len(v) for v in data.values())
    pairs = sum(p["pairs"] for v in data.values() for p in v.values())
    suspects = sum(len(p["suspects"]) for v in data.values() for p in v.values())
    return f"papers read {papers}, pairs read {pairs}, suspects {suspects}"
