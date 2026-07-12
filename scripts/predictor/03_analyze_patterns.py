#!/usr/bin/env python3
"""
Phase 2 — Pattern analysis.

Reads data/analysis/{code}/questions.jsonl and computes, per paper:
  - weighted topic frequency + by-year matrix (spec-era aware)
  - marks-per-topic, difficulty + command-word distributions
  - per-slot (question position) topic/marks/command patterns
  - recurrence/cycle detection with an "overdue" score for the target year
  - recurring question templates (signature clusters spanning years)
  - legacy-vs-9-1 spec shift

Outputs: data/analysis/{code}/patterns.json  and  data/analysis/{code}/report.md

Usage: python scripts/predictor/03_analyze_patterns.py --subject 4PM1
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.env import REPO_ROOT
from lib.config import load_config, PredictorConfig


def load_questions(code: str) -> list[dict]:
    p = REPO_ROOT / "data" / "analysis" / code / "questions.jsonl"
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _wsum(rows: list[dict]) -> float:
    return round(sum(r.get("weight", 1.0) for r in rows), 2)


def topic_frequency(cfg: PredictorConfig, rows: list[dict]) -> list[dict]:
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_topic[r["primary_topic"]].append(r)
    total_w = sum(r.get("weight", 1.0) for r in rows) or 1.0
    total_marks_w = sum((r.get("marks_total") or 0) * r.get("weight", 1.0) for r in rows) or 1.0
    out = []
    for tid, qs in by_topic.items():
        marks = [q.get("marks_total") or 0 for q in qs]
        w = sum(q.get("weight", 1.0) for q in qs)
        marks_w = sum((q.get("marks_total") or 0) * q.get("weight", 1.0) for q in qs)
        era = Counter(q["spec_era"] for q in qs)
        out.append({
            "topic": tid,
            "name": cfg.topic_by_id[tid].name if tid in cfg.topic_by_id else tid,
            "raw_count": len(qs),
            "weighted": round(w, 2),
            "freq_share": round(w / total_w, 4),
            "avg_marks": round(statistics.mean(marks), 1) if marks else 0,
            "marks_share": round(marks_w / total_marks_w, 4),
            "years": sorted({q["year"] for q in qs}),
            "era_counts": dict(era),
        })
    out.sort(key=lambda x: x["weighted"], reverse=True)
    return out


def topic_by_year(rows: list[dict]) -> dict[str, dict[str, int]]:
    m: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        m[r["primary_topic"]][str(r["year"])] += 1
    return {t: dict(c) for t, c in m.items()}


def slot_patterns(cfg: PredictorConfig, rows: list[dict]) -> list[dict]:
    by_slot: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        by_slot[r["q_number"]].append(r)
    out = []
    for slot in sorted(by_slot):
        qs = by_slot[slot]
        topics = Counter()
        cmds = Counter()
        marks = [q.get("marks_total") or 0 for q in qs]
        diff = Counter(q.get("difficulty", "medium") for q in qs)
        for q in qs:
            topics[q["primary_topic"]] += q.get("weight", 1.0)
            for c in q.get("command_words", []):
                cmds[c.lower()] += 1
        top = [{"topic": t, "name": cfg.topic_by_id[t].name if t in cfg.topic_by_id else t,
                "weight": round(w, 2)} for t, w in topics.most_common(3)]
        out.append({
            "slot": slot,
            "n": len(qs),
            "avg_marks": round(statistics.mean(marks), 1) if marks else 0,
            "marks_range": [min(marks), max(marks)] if marks else [0, 0],
            "top_topics": top,
            "common_commands": [c for c, _ in cmds.most_common(4)],
            "difficulty_mode": diff.most_common(1)[0][0] if diff else "medium",
        })
    return out


def cycles(cfg: PredictorConfig, rows: list[dict]) -> list[dict]:
    """Recurrence analysis on the 9-1 era only (predictive era)."""
    target_year = int(cfg.target["year"])
    nine = [r for r in rows if r["spec_era"] == "9-1"]
    years_all = sorted({r["year"] for r in nine})
    n_years = len(years_all) or 1
    by_topic: dict[str, list[int]] = defaultdict(list)
    for r in nine:
        by_topic[r["primary_topic"]].append(r["year"])
    out = []
    for tid, yrs in by_topic.items():
        uniq = sorted(set(yrs))
        gaps = [b - a for a, b in zip(uniq, uniq[1:])] if len(uniq) > 1 else []
        mean_gap = round(statistics.mean(gaps), 2) if gaps else float(n_years)
        last_seen = max(uniq)
        years_since = target_year - last_seen
        coverage = len(uniq) / n_years
        overdue = round(years_since / mean_gap, 2) if mean_gap else 0.0
        cadence = "annual" if coverage >= 0.8 else ("alternating" if 1.5 <= mean_gap <= 2.5 else "sparse")
        # appearances per year (count) to gauge volume
        per_year = Counter(yrs)
        out.append({
            "topic": tid,
            "name": cfg.topic_by_id[tid].name if tid in cfg.topic_by_id else tid,
            "appearance_years": uniq,
            "total_appearances": len(yrs),
            "per_year_counts": {str(y): per_year[y] for y in uniq},
            "coverage": round(coverage, 2),
            "mean_gap": mean_gap,
            "last_seen": last_seen,
            "years_since": years_since,
            "overdue_score": overdue,
            "cadence": cadence,
        })
    out.sort(key=lambda x: (-x["coverage"], -x["overdue_score"]))
    return out


def templates(cfg: PredictorConfig, rows: list[dict], min_size: int = 3) -> list[dict]:
    by_sig: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_sig[r.get("signature", "?")].append(r)
    out = []
    for sig, qs in by_sig.items():
        years = sorted({q["year"] for q in qs})
        if len(qs) < min_size or len(years) < 2:
            continue
        rep = max(qs, key=lambda q: (q.get("weight", 0), q["year"]))
        skills = Counter()
        for q in qs:
            for s in q.get("skills", []):
                skills[s] += 1
        out.append({
            "signature": sig,
            "topic": rep["primary_topic"],
            "name": cfg.topic_by_id.get(rep["primary_topic"]).name if rep["primary_topic"] in cfg.topic_by_id else rep["primary_topic"],
            "size": len(qs),
            "years": years,
            "weighted": _wsum(qs),
            "common_skills": [s for s, _ in skills.most_common(5)],
            "representative": {
                "q_id": rep["q_id"], "context_tag": rep.get("context_tag", ""),
                "marks": rep.get("marks_total"), "command_words": rep.get("command_words", []),
                "skills": rep.get("skills", []), "text_excerpt": rep.get("text_excerpt", "")[:300],
            },
        })
    out.sort(key=lambda x: x["weighted"], reverse=True)
    return out


def spec_shift(cfg: PredictorConfig, rows: list[dict]) -> dict:
    def share(era):
        sub = [r for r in rows if r["spec_era"] == era]
        tot = len(sub) or 1
        c = Counter(r["primary_topic"] for r in sub)
        return {t: round(n / tot, 3) for t, n in c.items()}, len(sub)
    legacy, n_legacy = share("legacy")
    nine, n_nine = share("9-1")
    grew, shrank = [], []
    for t in set(legacy) | set(nine):
        d = nine.get(t, 0) - legacy.get(t, 0)
        name = cfg.topic_by_id[t].name if t in cfg.topic_by_id else t
        if d >= 0.03:
            grew.append({"topic": t, "name": name, "delta": round(d, 3)})
        elif d <= -0.03:
            shrank.append({"topic": t, "name": name, "delta": round(d, 3)})
    grew.sort(key=lambda x: -x["delta"])
    shrank.sort(key=lambda x: x["delta"])
    return {"n_legacy": n_legacy, "n_nine_one": n_nine,
            "legacy_share": legacy, "nine_one_share": nine,
            "grew_under_9_1": grew, "shrank_under_9_1": shrank}


def analyze(cfg: PredictorConfig, rows: list[dict]) -> dict:
    papers = {}
    for p in cfg.papers:
        pid = p["id"]
        pr = [r for r in rows if r["paper"] == pid]
        nine = [r for r in pr if r["spec_era"] == "9-1"]
        papers[pid] = {
            "name": p["name"],
            "marks_target": p["total_marks"],
            "typical_question_count": p["typical_questions"],
            "n_questions": len(pr),
            "n_questions_9_1": len(nine),
            "topic_frequency": topic_frequency(cfg, nine or pr),
            "topic_by_year": topic_by_year(pr),
            "slot_patterns": slot_patterns(cfg, nine or pr),
            "command_words": [{"word": w, "count": c} for w, c in
                              Counter(cw.lower() for r in (nine or pr) for cw in r.get("command_words", [])).most_common(15)],
            "difficulty_dist": dict(Counter(r.get("difficulty", "medium") for r in (nine or pr))),
            "cycles": cycles(cfg, pr),
            "templates": templates(cfg, nine or pr),
        }
    return {
        "subject_code": cfg.code,
        "subject_name": cfg.name,
        "target": cfg.target,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_questions": len(rows),
        "years": sorted({r["year"] for r in rows}),
        "papers": papers,
        "spec_shift": spec_shift(cfg, rows),
    }


# ---------------- report.md ----------------
def render_report(cfg: PredictorConfig, a: dict) -> str:
    L = []
    L.append(f"# {cfg.name} ({cfg.code}) — Question Pattern Analysis")
    L.append(f"_Target sitting: **{cfg.target.get('label')}** · {a['n_questions']} questions analysed · years {a['years'][0]}–{a['years'][-1]} · generated {a['generated_at'][:10]}_\n")
    L.append("> Weighting: 9–1 era ×1.0 (legacy ×0.2), autumn-session ×1.3, recency half-life "
             f"{cfg.recency_half_life}y. Recurrence/cycle stats use the 9–1 era only.\n")

    ss = a["spec_shift"]
    L.append("## Specification shift (legacy 4×0 → 9–1)")
    L.append(f"- Legacy questions: {ss['n_legacy']} · 9–1 questions: {ss['n_nine_one']}")
    if ss["grew_under_9_1"]:
        L.append("- **More emphasis under 9–1:** " + ", ".join(f"{g['name']} (+{int(g['delta']*100)}%)" for g in ss["grew_under_9_1"][:6]))
    if ss["shrank_under_9_1"]:
        L.append("- **Less emphasis under 9–1:** " + ", ".join(f"{g['name']} ({int(g['delta']*100)}%)" for g in ss["shrank_under_9_1"][:6]))
    L.append("")

    for pid, p in a["papers"].items():
        L.append(f"## {p['name']} (target {p['marks_target']} marks, ~{p['typical_question_count'][0]}–{p['typical_question_count'][1]} questions)")
        L.append(f"_{p['n_questions']} historical questions ({p['n_questions_9_1']} in 9–1 era)._\n")

        L.append("### Topic priority (recency/era/session-weighted)")
        L.append("| Rank | Topic | Weighted | Freq share | Avg marks | Marks share | Years seen |")
        L.append("|---|---|---:|---:|---:|---:|---|")
        for i, t in enumerate(p["topic_frequency"], 1):
            yrs = f"{min(t['years'])}–{max(t['years'])}" if t["years"] else "—"
            L.append(f"| {i} | {t['name']} | {t['weighted']} | {int(t['freq_share']*100)}% | {t['avg_marks']} | {int(t['marks_share']*100)}% | {yrs} |")
        L.append("")

        L.append("### Recurrence & cycles (9–1 era)")
        L.append("| Topic | Cadence | Appears (yrs) | Mean gap | Last seen | Overdue score |")
        L.append("|---|---|---|---:|---:|---:|")
        for c in p["cycles"]:
            flag = " ⚠️" if c["overdue_score"] >= 1.3 else ""
            L.append(f"| {c['name']} | {c['cadence']} | {','.join(map(str,c['appearance_years']))} | {c['mean_gap']} | {c['last_seen']} | {c['overdue_score']}{flag} |")
        L.append("")

        L.append("### Position (slot) patterns")
        L.append("| Q# | Avg marks | Usual topics | Common commands | Difficulty |")
        L.append("|---:|---:|---|---|---|")
        for s in p["slot_patterns"]:
            tt = ", ".join(f"{x['name']}" for x in s["top_topics"][:2])
            L.append(f"| {s['slot']} | {s['avg_marks']} | {tt} | {', '.join(s['common_commands'][:3])} | {s['difficulty_mode']} |")
        L.append("")

        if p["templates"]:
            L.append("### Recurring question templates (recur across ≥2 years)")
            for t in p["templates"][:8]:
                L.append(f"- **{t['name']}** ({t['size']}× over {min(t['years'])}–{max(t['years'])}): "
                         f"{', '.join(t['common_skills'][:3])} — e.g. _{t['representative']['context_tag']}_ ({t['representative']['marks']}m)")
            L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()
    cfg = load_config(args.subject)
    rows = load_questions(cfg.code)
    out_dir = REPO_ROOT / "data" / "analysis" / cfg.code
    a = analyze(cfg, rows)
    (out_dir / "patterns.json").write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render_report(cfg, a), encoding="utf-8")
    print(f"[{cfg.code}] analysis written: patterns.json + report.md ({len(rows)} questions)")
    for pid, p in a["papers"].items():
        top = p["topic_frequency"][0] if p["topic_frequency"] else {}
        print(f"  Paper {pid}: {p['n_questions']} q, top topic = {top.get('name')} ({top.get('weighted')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
