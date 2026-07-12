#!/usr/bin/env python3
"""
Phase 3a — Blueprint prediction.

Turns patterns.json into a slot-by-slot blueprint for the target sitting, constrained
to the real paper shape (question count + total marks). Every slot carries predicted
topic, marks, command words, difficulty, a style reference (recurring template), a
confidence score, and cited historical evidence. Fully deterministic & explainable.

Output: data/predictions/{code}/{session}_{year}/blueprint.json

Usage: python scripts/predictor/04_predict.py --subject 4PM1
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.env import REPO_ROOT
from lib.config import load_config, PredictorConfig

OVERDUE_BOOST = 0.25      # marks-demand multiplier for an overdue topic
CONF_HIGH, CONF_MED = 0.55, 0.32


def load_patterns(code: str) -> dict:
    return json.loads((REPO_ROOT / "data" / "analysis" / code / "patterns.json").read_text(encoding="utf-8"))


def load_questions(code: str) -> list[dict]:
    p = REPO_ROOT / "data" / "analysis" / code / "questions.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def choose_question_count(paper_pat: dict, typical: list[int], rows_paper: list[dict]) -> int:
    counts = Counter()
    for r in rows_paper:
        if r["spec_era"] == "9-1":
            counts[(r["year"], r["session"], r["variant"])] += 1
    per_paper = list(counts.values())
    if per_paper:
        target = int(round(statistics.median(per_paper)))
    else:
        target = typical[1]
    return max(typical[0], min(typical[1], target))


def slot_affinity(paper_pat: dict) -> dict[int, dict[str, float]]:
    aff: dict[int, dict[str, float]] = {}
    for s in paper_pat["slot_patterns"]:
        total = sum(t["weight"] for t in s["top_topics"]) or 1.0
        aff[s["slot"]] = {t["topic"]: t["weight"] / total for t in s["top_topics"]}
    return aff


def build_blueprint(cfg: PredictorConfig, pid: str, paper_pat: dict, rows: list[dict]) -> dict:
    rows_paper = [r for r in rows if r["paper"] == pid]
    nine = [r for r in rows_paper if r["spec_era"] == "9-1"]
    total_marks = paper_pat["marks_target"]
    n_q = choose_question_count(paper_pat, paper_pat["typical_question_count"], rows_paper)

    freq = {t["topic"]: t for t in paper_pat["topic_frequency"]}
    cyc = {c["topic"]: c for c in paper_pat["cycles"]}
    tmpl_by_topic: dict[str, dict] = {}
    for t in paper_pat["templates"]:
        tmpl_by_topic.setdefault(t["topic"], t)
    aff = slot_affinity(paper_pat)
    avg_slot_marks = {s["slot"]: s["avg_marks"] for s in paper_pat["slot_patterns"]}
    diff_slot = {s["slot"]: s["difficulty_mode"] for s in paper_pat["slot_patterns"]}
    cmds_slot = {s["slot"]: s["common_commands"] for s in paper_pat["slot_patterns"]}

    # marks demand per topic = marks_share * total, boosted if overdue
    demand: dict[str, float] = {}
    for t, f in freq.items():
        boost = 1.0 + (OVERDUE_BOOST if cyc.get(t, {}).get("overdue_score", 0) >= 1.3 else 0.0)
        demand[t] = f["marks_share"] * total_marks * boost
    # normalize back to total
    dsum = sum(demand.values()) or 1.0
    demand = {t: v * total_marks / dsum for t, v in demand.items()}
    remaining = dict(demand)

    # Soft cap on how many slots one topic may occupy (from its marks demand).
    per_q = total_marks / n_q
    target_count = {t: max(0, round(demand.get(t, 0) / per_q)) for t in freq}
    picked = Counter()
    prev_topic = None

    slots = []
    for slot in range(1, n_q + 1):
        a = aff.get(slot, {})
        # score = position affinity blended with remaining demand, with soft cap + exhaustion penalty
        scored = []
        for t in freq:
            pos = a.get(t, 0.0)
            rem = remaining.get(t, 0.0)
            score = 0.5 * pos + 0.5 * (max(0.0, rem) / (total_marks or 1))
            cap = max(1, target_count.get(t, 1)) + 1
            if picked[t] >= cap:
                score *= 0.12          # already used as often as its demand warrants
            elif rem <= 0:
                score *= 0.45          # demand spent — allow only if nothing better
            if t == prev_topic:
                score *= 0.5           # avoid the same topic in adjacent slots
            scored.append((score, pos, t))
        scored.sort(reverse=True)
        _, pos_share, topic = scored[0]
        picked[topic] += 1
        prev_topic = topic

        marks = int(round(avg_slot_marks.get(slot, total_marks / n_q)))
        marks = max(3, min(total_marks // 3, marks))
        remaining[topic] = remaining.get(topic, 0) - marks

        f = freq.get(topic, {})
        c = cyc.get(topic, {})
        conf = round(min(0.95, 0.45 * f.get("freq_share", 0) * 4 + 0.35 * pos_share +
                         0.20 * (1.0 if c.get("cadence") == "annual" else 0.4)), 3)
        band = "high" if conf >= CONF_HIGH else ("medium" if conf >= CONF_MED else "low")

        tmpl = tmpl_by_topic.get(topic, {})
        rep = tmpl.get("representative", {})
        # evidence: recent 9-1 q_ids of this topic on this paper
        ev = sorted([r for r in nine if r["primary_topic"] == topic],
                    key=lambda r: r["year"], reverse=True)[:4]
        rationale = []
        rationale.append(f"{f.get('name', topic)} carries {int(f.get('marks_share',0)*100)}% of weighted marks on this paper")
        if c.get("cadence") == "annual":
            rationale.append("appears almost every year")
        if c.get("overdue_score", 0) >= 1.3:
            rationale.append(f"overdue (last seen {c.get('last_seen')}, mean gap {c.get('mean_gap')}y)")
        if pos_share >= 0.3:
            rationale.append(f"frequently sits at Q{slot}")

        slots.append({
            "slot": slot,
            "topic": topic,
            "topic_name": f.get("name", topic),
            "marks": marks,
            "command_words": (cmds_slot.get(slot) or [])[:3] or _topic_commands(nine, topic),
            "difficulty": diff_slot.get(slot, "medium"),
            "skills": (tmpl.get("common_skills") or _topic_skills(nine, topic))[:4],
            "style_reference": {
                "context_tag": rep.get("context_tag", ""),
                "example_marks": rep.get("marks"),
                "example_excerpt": rep.get("text_excerpt", "")[:280],
                "from_q_id": rep.get("q_id", ""),
            },
            "confidence": conf,
            "confidence_band": band,
            "rationale": "; ".join(rationale),
            "evidence": [{"q_id": r["q_id"], "year": r["year"], "marks": r.get("marks_total"),
                          "context": r.get("context_tag", "")} for r in ev],
        })

    # reconcile marks to exactly total_marks
    _reconcile_marks(slots, total_marks)
    # estimate subparts from topic norm
    for s in slots:
        s["est_subparts"] = _topic_subparts(nine, s["topic"])

    return {
        "paper": pid, "paper_name": paper_pat["name"],
        "target": cfg.target, "total_marks": total_marks,
        "question_count": n_q,
        "predicted_marks": sum(s["marks"] for s in slots),
        "topic_demand": {t: round(v, 1) for t, v in sorted(demand.items(), key=lambda x: -x[1])},
        "slots": slots,
    }


def _topic_commands(rows, topic):
    c = Counter(cw.lower() for r in rows if r["primary_topic"] == topic for cw in r.get("command_words", []))
    return [w for w, _ in c.most_common(3)] or ["find"]


def _topic_skills(rows, topic):
    c = Counter(s for r in rows if r["primary_topic"] == topic for s in r.get("skills", []))
    return [s for s, _ in c.most_common(4)]


def _topic_subparts(rows, topic):
    vals = [r.get("n_subparts", 0) for r in rows if r["primary_topic"] == topic]
    return int(round(statistics.median(vals))) if vals else 2


def _reconcile_marks(slots, total):
    cur = sum(s["marks"] for s in slots)
    if not slots:
        return
    i = 0
    guard = 0
    while cur != total and guard < 500:
        s = slots[i % len(slots)]
        if cur < total:
            s["marks"] += 1; cur += 1
        elif s["marks"] > 3:
            s["marks"] -= 1; cur -= 1
        i += 1
        guard += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    args = ap.parse_args()
    cfg = load_config(args.subject)
    patterns = load_patterns(cfg.code)
    rows = load_questions(cfg.code)

    out_dir = REPO_ROOT / "data" / "predictions" / cfg.code / f"{cfg.target['session']}_{cfg.target['year']}"
    out_dir.mkdir(parents=True, exist_ok=True)

    papers = {}
    for pid, paper_pat in patterns["papers"].items():
        papers[pid] = build_blueprint(cfg, pid, paper_pat, rows)

    blueprint = {
        "subject_code": cfg.code, "subject_name": cfg.name,
        "target": cfg.target, "papers": papers,
        "method": "recency/era/session-weighted topic demand + position priors + cycle overdue boost",
    }
    (out_dir / "blueprint.json").write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{cfg.code}] blueprint -> {out_dir/'blueprint.json'}")
    for pid, p in papers.items():
        print(f"  Paper {pid}: {p['question_count']} Q, {p['predicted_marks']}/{p['total_marks']} marks")
        for s in p["slots"]:
            print(f"    Q{s['slot']:>2} {s['marks']:>2}m  {s['topic_name']:<34} conf={s['confidence_band']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
