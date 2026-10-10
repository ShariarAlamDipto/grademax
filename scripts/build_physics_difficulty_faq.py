"""Build the difficulty-ranked, mark-scheme-sourced FAQ for Edexcel IGCSE Physics.

Reads every 4PH1/4PH0 question paper and mark scheme in the archive for the given
years, joins each question part to its mark scheme cell, verifies the parse against
the paper's own printed mark totals, scores each part for difficulty and groups the
questions that recur across sittings.

Usage:
    python scripts/build_physics_difficulty_faq.py [--from-year 2018] [--to-year 2025]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.physics_faq_cluster import (  # noqa: E402
    canonical_stem, cluster_parts, common_points, is_multiple_choice,
)
from lib.physics_faq_corpus2 import build_corpus  # noqa: E402
from lib.physics_topics import topic_of  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data" / "Ultimate Final IGCSE" / "Physics"
OUT_DIR = ROOT / "data" / "faq" / "physics_difficulty"

TIER_ORDER = ("banker", "routine", "discriminator", "top-grade")


def summarise_cluster(cluster) -> dict:
    """Reduce one group of repeated questions to a single FAQ entry."""
    members = cluster.members
    exemplar = max(members, key=lambda m: (len(m.points), m.tariff or 0))
    tiers = Counter(m.difficulty.tier for m in members)
    stem = canonical_stem(cluster)
    number, name = topic_of(f"{stem} {' '.join(exemplar.points)}")

    reasons: Counter = Counter()
    for member in members:
        reasons.update(member.difficulty.reasons)

    traps = [m.notes for m in members if m.notes and "reject" in m.notes.lower()]
    return {
        "stem": stem,
        "exemplar_stem": exemplar.stem,
        "topic_n": number,
        "topic": name,
        "tier": tiers.most_common(1)[0][0],
        "score": round(sum(m.difficulty.score for m in members) / len(members), 1),
        "command": Counter(m.difficulty.command for m in members).most_common(1)[0][0],
        "multiple_choice": is_multiple_choice(exemplar.stem),
        "tariff": exemplar.tariff,
        "papers": cluster.papers,
        "appearances": len(members),
        "years": cluster.years,
        "sittings": sorted({f"{m.sitting} {m.ref}" for m in members}),
        "points": exemplar.points,
        "menu": exemplar.menu,
        "recurring_points": common_points(cluster),
        "notes": exemplar.notes,
        "traps": traps[:3],
        "why_hard": [r for r, _ in reasons.most_common(4)],
        "specs": sorted({m.spec for m in members}),
    }


# A reject clause runs until the next examiner instruction, so the lookahead stops
# it before it swallows the following "allow ..." and becomes unreadable.
_REJECT_RE = re.compile(
    r"\b(?:reject|do not accept|do not credit)\b\s*[:\-]?\s*"
    r"(.{3,90}?)(?=\s*\b(?:allow|ignore|condone|accept|reject|ecf|award|mp\d)\b|[;.]|$)",
    re.I,
)


def hard_skill_groups(parts: list, tiers: tuple[str, ...]) -> list[dict]:
    """Group the hardest parts by what they demand, not by how they are worded.

    A banker question repeats verbatim -- "State the formula linking..." is the same
    sentence every session -- so grouping by wording finds it. The hard marks do not
    repeat that way: the context changes every time and only the demand recurs. So
    these are grouped by topic and command word, and the frequency reported is how
    many separate papers made that demand.
    """
    buckets: dict[tuple, list] = {}
    for part in parts:
        if part.difficulty.tier not in tiers:
            continue
        number, name = topic_of(f"{part.stem} {' '.join(part.points)}")
        buckets.setdefault((number, name, part.difficulty.command), []).append(part)

    groups = []
    for (number, name, command), members in buckets.items():
        papers = {m.paper_id for m in members}
        if len(papers) < 3:
            continue
        reasons: Counter = Counter()
        for member in members:
            reasons.update(member.difficulty.reasons)
        # Show questions that are typical of the group rather than its biggest one.
        # Ranking by tariff alone surfaced a six-mark practical write-up as the face
        # of "Forces and motion, calculate", which is the one thing in the group that
        # is not a calculation.
        top_reason = reasons.most_common(1)[0][0] if reasons else None
        examples = sorted(
            members,
            key=lambda m: (
                top_reason not in m.difficulty.reasons,
                abs((m.tariff or 0) - 3),
                -len(m.points),
            ),
        )[:3]
        groups.append({
            "topic_n": number,
            "topic": name,
            "command": command,
            "questions": len(members),
            "papers": len(papers),
            "marks": sum(m.tariff or 0 for m in members),
            "why_hard": [{"reason": r, "n": n} for r, n in reasons.most_common(5)],
            "examples": [{
                "stem": e.stem, "tariff": e.tariff, "points": e.points,
                "notes": e.notes, "sitting": f"{e.sitting} {e.ref}",
            } for e in examples],
        })
    groups.sort(key=lambda g: -g["marks"])
    return groups


def zero_scoring_answers(parts: list, min_papers: int = 1) -> list[dict]:
    """The answers the mark schemes explicitly refuse to credit.

    A "reject" note is written because enough candidates gave that exact answer to
    be worth telling examiners about, which makes it the closest thing in the
    archive to a record of what students actually get wrong.

    These are collected per ruling rather than per repeated phrase: examiners write
    them in free text, so across 2018-2025 only a handful recur word for word even
    though the same misconception is being refused. Gating on repetition would throw
    away almost all of them, so every distinct ruling is kept and the ones that do
    repeat are ranked first.
    """
    found: dict[str, dict] = {}
    for part in parts:
        for raw in _REJECT_RE.findall(part.notes or ""):
            # Examiners quote the rejected wording inconsistently, so the quote marks
            # are stripped before de-duplicating: without this, "half the time" and
            # "half the time" land as two separate rulings.
            phrase = re.sub(r"[‘’“”\"']", "", re.sub(r"\s+", " ", raw))
            phrase = phrase.strip(" .,()•·").lower()
            if len(phrase) < 4 or phrase.startswith(("if ", "any ", "the candidate")):
                continue
            if not re.search(r"[a-z]{3}", phrase):
                continue
            row = found.setdefault(phrase, {
                "phrase": phrase, "papers": set(), "topics": Counter(), "contexts": [],
            })
            row["papers"].add(part.paper_id)
            row["topics"][topic_of(part.stem + " " + " ".join(part.points))[1]] += 1
            if len(row["contexts"]) < 4:
                row["contexts"].append({
                    "stem": part.stem[:170],
                    "accepted": part.points[:3],
                    "sitting": f"{part.sitting} {part.ref}",
                })
    # Lead with the tersest example of each ruling. "reject scale" alongside
    # "balance" teaches the swap in one glance; alongside a four-mark method it
    # teaches nothing.
    for row in found.values():
        row["contexts"].sort(key=lambda c: len(" ".join(c["accepted"])))

    rows = [{
        "phrase": r["phrase"],
        "papers": len(r["papers"]),
        "topic": r["topics"].most_common(1)[0][0],
        "contexts": r["contexts"],
    } for r in found.values() if len(r["papers"]) >= min_papers]
    # Repeated rulings first, then the crisp ones -- a short ruling is one a student
    # can actually hold in their head walking into the exam.
    rows.sort(key=lambda r: (-r["papers"], len(r["phrase"])))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", default=str(ARCHIVE))
    ap.add_argument("--from-year", type=int, default=2018)
    ap.add_argument("--to-year", type=int, default=2025)
    ap.add_argument("--min-papers", type=int, default=2,
                    help="how many separate papers a question must appear in")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    print(f"[1/4] reading papers {args.from_year}-{args.to_year}", flush=True)
    parts, report, failures = build_corpus(Path(args.archive), args.from_year, args.to_year)
    for line in report:
        print(f"      {line}", flush=True)
    print(f"      {len(failures)} questions excluded by the reconciliation check", flush=True)

    print("[2/4] scoring difficulty", flush=True)
    tiers = Counter(p.difficulty.tier for p in parts)
    for tier in TIER_ORDER:
        print(f"      {tier:14} {tiers[tier]:5} parts", flush=True)

    print("[3/4] grouping questions that recur across sittings", flush=True)
    clusters = cluster_parts(parts)
    recurring = [c for c in clusters if c.papers >= args.min_papers]
    print(f"      {len(clusters)} groups, {len(recurring)} appear in "
          f"{args.min_papers}+ papers", flush=True)

    entries = [summarise_cluster(c) for c in recurring]
    entries.sort(key=lambda e: (TIER_ORDER.index(e["tier"]), -e["papers"]))

    hard = hard_skill_groups(parts, ("discriminator", "top-grade"))
    rejects = zero_scoring_answers(parts)
    print(f"      {len(hard)} recurring hard-skill groups, "
          f"{len(rejects)} repeated 'reject' rulings", flush=True)

    print(f"[4/4] writing {args.out}", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "entries.json").write_text(
        json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "corpus.json").write_text(json.dumps([{
        "paper_id": p.paper_id, "year": p.year, "spec": p.spec, "ref": p.ref,
        "stem": p.stem, "tariff": p.tariff, "points": p.points, "notes": p.notes,
        "tier": p.difficulty.tier, "score": p.difficulty.score,
        "command": p.difficulty.command, "why": list(p.difficulty.reasons),
        "topic": topic_of(p.stem + " " + " ".join(p.points))[1],
    } for p in parts], indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "hard_skills.json").write_text(
        json.dumps(hard, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "rejects.json").write_text(
        json.dumps(rejects, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "build_report.json").write_text(json.dumps({
        "report": report,
        "tier_counts": dict(tiers),
        "n_entries": len(entries),
        "n_hard_groups": len(hard),
        "n_rejects": len(rejects),
        "topic_marks": dict(Counter(
            topic_of(p.stem + " " + " ".join(p.points))[1] for p in parts)),
        "excluded": failures,
    }, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"      {len(entries)} FAQ entries, {len(parts)} corpus parts", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
