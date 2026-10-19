#!/usr/bin/env python3
"""
Phase 1 — Question extraction.

For every per-question PDF in the analysis window, build one structured record:
deterministic fields (marks, subparts, diagram signals) from the PDF text, plus
LLM-classified fields (topics, command words, skills, difficulty, style).

Output: data/analysis/{code}/questions.jsonl  (one JSON object per line, resumable).

Usage:
  python scripts/predictor/02_extract_questions.py --subject 4PM1
  python scripts/predictor/02_extract_questions.py --subject 4PH1 --folder 2024_May-Jun_P1
  python scripts/predictor/02_extract_questions.py --subject 4PM1 --limit 5      # smoke test
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.env import REPO_ROOT
from lib.config import load_config, PredictorConfig
from lib.folders import parse_folder, PaperFolder
from lib.extract_text import extract_question, read_markscheme_text, QuestionText
from lib.llm import chat_json, LLMError
from lib.fingerprint import signature

COMMAND_VOCAB = [
    "state", "define", "describe", "explain", "calculate", "find", "show that",
    "prove", "sketch", "draw", "plot", "determine", "solve", "estimate",
    "give a reason", "suggest", "complete", "deduce", "express", "differentiate",
    "integrate", "expand",
]


def _qnum(p: Path) -> int:
    m = re.search(r"q(\d+)", p.stem)
    return int(m.group(1)) if m else 0


def build_prompt(cfg: PredictorConfig, qt: QuestionText, ms_text: str, multi: bool) -> list[dict]:
    topic_block = cfg.topics_prompt_block()
    multi_rule = ("Choose ALL relevant topic ids (a question may span several)."
                  if multi else "Choose the SINGLE best topic id.")
    subpart_hint = (f"Sub-part labels detected: {qt.subpart_labels}. "
                    if qt.subpart_labels else "No lettered sub-parts detected. ")
    total_hint = (f"The official total is {qt.total_marks} marks; make subpart marks sum to it. "
                  if qt.total_marks else "")
    sys_msg = (
        f"You are an expert {cfg.name} (Edexcel IGCSE {cfg.code}) examiner. "
        "You classify a single exam question into structured metadata. "
        "Return ONLY a JSON object. Use ONLY topic ids from the provided list."
    )
    user_msg = f"""TOPICS (id = name):
{topic_block}

COMMAND-WORD VOCABULARY (pick those that actually appear as instructions):
{", ".join(COMMAND_VOCAB)}

{subpart_hint}{total_hint}{multi_rule}

QUESTION TEXT:
\"\"\"
{qt.text[:3200]}
\"\"\"

MARK SCHEME (excerpt, may be empty):
\"\"\"
{ms_text[:1400]}
\"\"\"

Return JSON with EXACTLY these keys:
{{
  "topics": ["<id>", ...],
  "primary_topic": "<id>",
  "command_words": ["<from vocab>", ...],
  "skills": ["<short skill phrase>", ...],          // 1-4 concrete skills tested
  "formulae": ["<formula/identity used>", ...],     // may be empty
  "context_tag": "<=6 words naming the real-world/abstract context",
  "difficulty": "easy" | "medium" | "hard",
  "answer_type": "calculation" | "explanation" | "proof" | "graph" | "mixed",
  "subparts": [{{"label": "a", "marks": <int>, "skill": "<short>"}}]
}}"""
    return [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}]


def classify(cfg: PredictorConfig, qt: QuestionText, ms_text: str, multi: bool) -> dict:
    prov = cfg.llm["extract"]["provider"]
    model = cfg.llm["extract"]["model"]
    messages = build_prompt(cfg, qt, ms_text, multi)
    data = chat_json(prov, model, messages, temperature=0.1, max_tokens=900)

    valid_ids = set(cfg.topic_by_id.keys())
    topics = [str(t) for t in data.get("topics", []) if str(t) in valid_ids]
    primary = str(data.get("primary_topic", "")).strip()
    if primary not in valid_ids:
        primary = topics[0] if topics else "1"
    if primary not in topics:
        topics = [primary] + topics
    if not multi:
        topics = [primary]
    return {
        "topics": topics,
        "primary_topic": primary,
        "primary_topic_name": cfg.topic_by_id[primary].name,
        "command_words": [c for c in data.get("command_words", []) if isinstance(c, str)][:8],
        "skills": [s for s in data.get("skills", []) if isinstance(s, str)][:5],
        "formulae": [s for s in data.get("formulae", []) if isinstance(s, str)][:5],
        "context_tag": str(data.get("context_tag", ""))[:80],
        "difficulty": data.get("difficulty") if data.get("difficulty") in ("easy", "medium", "hard") else "medium",
        "answer_type": data.get("answer_type", "mixed"),
        "subparts": [s for s in data.get("subparts", []) if isinstance(s, dict)][:12],
    }


def iter_folders(cfg: PredictorConfig) -> list[PaperFolder]:
    base = REPO_ROOT / "data" / "processed" / cfg.processed_dir
    out: list[PaperFolder] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        pf = parse_folder(child.name)
        if not pf or not cfg.in_window(pf.year):
            continue
        if pf.is_retake and not cfg.include_retakes:
            continue
        out.append(pf)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True, help="config code, e.g. 4PM1 or 4PH1")
    ap.add_argument("--folder", help="restrict to a single processed folder")
    ap.add_argument("--limit", type=int, help="cap number of questions (smoke test)")
    ap.add_argument("--sleep", type=float, default=0.6, help="seconds between LLM calls")
    ap.add_argument("--out", help="override output jsonl path")
    args = ap.parse_args()

    cfg = load_config(args.subject)
    base = REPO_ROOT / "data" / "processed" / cfg.processed_dir
    out_path = Path(args.out) if args.out else REPO_ROOT / "data" / "analysis" / cfg.code / "questions.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["q_id"])
            except Exception:
                pass
    print(f"[{cfg.code}] resume: {len(done)} questions already extracted -> {out_path}")

    folders = iter_folders(cfg)
    if args.folder:
        folders = [f for f in folders if f.folder == args.folder]
    multi = cfg.code == "4PH1"

    written = 0
    fout = out_path.open("a", encoding="utf-8")
    try:
        for pf in folders:
            pages_dir = base / pf.folder / "pages"
            ms_dir = base / pf.folder / "markschemes"
            if not pages_dir.is_dir():
                continue
            for qp in sorted(pages_dir.glob("q*.pdf"), key=_qnum):
                qn = _qnum(qp)
                q_id = f"{cfg.code}:{pf.year}:{pf.session}:{pf.paper}{pf.variant}:q{qn}"
                if q_id in done:
                    continue
                if args.limit and written >= args.limit:
                    print(f"[{cfg.code}] limit {args.limit} reached"); return 0
                try:
                    qt = extract_question(str(qp))
                except Exception as e:
                    print(f"  ! extract failed {q_id}: {e}"); continue
                if len(qt.text) < 15:
                    continue  # blank / continuation page
                ms_path = ms_dir / qp.name
                ms_text = read_markscheme_text(str(ms_path)) if ms_path.exists() else ""
                try:
                    cls = classify(cfg, qt, ms_text, multi)
                except (LLMError, Exception) as e:
                    print(f"  ! classify failed {q_id}: {str(e)[:120]} (will retry on re-run)")
                    time.sleep(args.sleep)
                    continue

                era = cfg.spec_era_for(pf.year)
                record = {
                    "q_id": q_id,
                    "subject_code": cfg.code,
                    "year": pf.year,
                    "session": pf.session,
                    "session_raw": pf.session_raw,
                    "paper": pf.paper,
                    "variant": pf.variant,
                    "q_number": qn,
                    "spec_era": era["name"],
                    "spec_code": era["code"],
                    "marks_total": qt.total_marks,
                    "n_subparts": qt.n_subparts,
                    "subpart_labels": qt.subpart_labels,
                    "has_diagram": qt.has_diagram,
                    "has_graph": qt.has_graph,
                    "has_data_table": qt.has_data_table,
                    "pages": qt.pages,
                    **cls,
                    "weight": round(cfg.combined_weight(pf.year, pf.session), 4),
                    "text_excerpt": qt.text[:600],
                    "source_qp": str(qp.relative_to(REPO_ROOT)).replace("\\", "/"),
                }
                record["signature"] = signature(record)
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                fout.flush()
                written += 1
                if written % 10 == 0:
                    print(f"  … {written} written (last {q_id} -> T{record['primary_topic']} {record['marks_total']}m)")
                time.sleep(args.sleep)
    finally:
        fout.close()
    print(f"[{cfg.code}] done: +{written} new (total {len(done)+written}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
