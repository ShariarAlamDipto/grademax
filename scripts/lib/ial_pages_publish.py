"""
Publishing workbook questions into the `topics` + `pages` layer that the test
builder and worksheet generator read.

Subject-neutral; each subject has its own entry-point script.

TWO LAYERS, ON PURPOSE
----------------------
`workbook_questions` is the CURATED layer: stable slugs, human verification,
student progress pointing at it forever. `pages` is the DISPOSABLE ingest layer
the test builder and worksheet generator query, and it is regenerated whenever
segmentation improves.

This script is the bridge. It never moves data the other way, and it never
writes anything `workbook_questions` depends on.

THE GATE THAT MATTERS: `pages` HAS NO RLS ON VERIFICATION
----------------------------------------------------------
`workbook_questions` is hidden from students until `verified_at` is set. **The
`pages` table has no such protection** -- anything written here is immediately
live to every user of the test builder.

So by default this publishes ONLY questions a human has verified. Publishing an
unverified classification would put a machine's guess in front of a student as
though it were checked, in a surface that gives no sign it was never reviewed.
`--include-unverified` exists for a deliberate call, not as a convenience, and
it reports exactly how many unreviewed rows it would expose.

TOPIC CODES ARE SECTION CODES
-----------------------------
`normalizeTopicCodes` in `src/lib/topicCodes.ts` already passes dotted codes
through unchanged ("Chemistry/Bio granular codes ... stored as-is"), so the
workbook's own section codes -- `2.4`, `6.1` -- become the topic vocabulary.
One vocabulary across both systems means a worksheet filtered to "Venn
diagrams" is filtered to exactly the questions a human verified as Venn
diagrams, and the multi-label secondaries come along as extra topic tags.
"""

from __future__ import annotations

from dataclasses import dataclass

PAGE_SIZE = 1000


@dataclass(frozen=True)
class PublishPlan:
    topics: list[dict]
    pages: list[dict]
    skipped_unverified: int
    missing_papers: list[str]


def fetch_all(query_builder, page_size: int = PAGE_SIZE) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        chunk = query_builder(offset, page_size).execute().data or []
        rows.extend(chunk)
        if len(chunk) < page_size:
            return rows
        offset += page_size


def build_topics(taxonomy: dict[str, str], subject_id: str) -> list[dict]:
    """One topic per workbook section, keyed by the section code."""
    return [
        {"subject_id": subject_id, "code": code, "name": title}
        for code, title in sorted(
            taxonomy.items(), key=lambda kv: [int(p) for p in kv[0].split(".")]
        )
    ]


def build_pages(
    questions: list[dict],
    section_code_of: dict[str, str],
    secondary_codes_of: dict[str, list[str]],
    verified_slugs: set[str],
    paper_id_of: dict[str, str],
    include_unverified: bool,
) -> PublishPlan:
    """
    One `pages` row per workbook question.

    `question_number` is TEXT here, matching the column and the existing rows.
    Topics carry the primary section first, then the verified secondaries, so a
    worksheet filtered to a section finds questions that merely touch it too.
    """
    pages: list[dict] = []
    skipped = 0
    missing: list[str] = []

    for question in questions:
        slug = question["slug"]
        if slug not in verified_slugs and not include_unverified:
            skipped += 1
            continue

        paper_key = question["source_paper_key"]
        paper_id = paper_id_of.get(paper_key)
        if paper_id is None:
            if paper_key not in missing:
                missing.append(paper_key)
            continue

        primary = section_code_of.get(slug)
        if primary is None:
            continue
        topics = [primary] + [c for c in secondary_codes_of.get(slug, []) if c != primary]

        pages.append(
            {
                "paper_id": paper_id,
                "question_number": str(question["source_question_number"]),
                "topics": topics,
                "difficulty": question["difficulty"],
                "qp_page_url": question["_qp_url"],
                "ms_page_url": question["_ms_url"],
                "is_question": True,
                "page_count": question["qp_pages"][1] - question["qp_pages"][0] + 1,
                "page_number": question["qp_pages"][0],
                "text_excerpt": (question["stem"] or "")[:500],
            }
        )

    return PublishPlan(topics=[], pages=pages, skipped_unverified=skipped, missing_papers=missing)
