"""
Loading IAL workbook questions into Postgres and R2.

Subject-neutral; each subject keeps its own entry-point script that supplies
paths, codes and prefixes.

THE RULE THAT PROTECTS HUMAN WORK
---------------------------------
**A row with `verified_at` set is authoritative.** Re-running a loader refreshes
only mechanical fields -- marks, sub-parts, PDF urls, stem, difficulty -- and
routes the classifier's newer opinion to `proposed_section_id`. It never
rewrites `section_id`, `secondary_section_ids` or `archetype_id` on a verified
row.

Without that split, a re-run silently reverts every manual reassignment while
leaving `verified_at` set, so the question looks signed off while carrying the
section a human already rejected. That is worse than losing the work outright,
because nothing about it looks wrong. It is the reason a verification pass can
safely run while the pipeline is still being re-run.

FOUR FAILURES THE 4MB1 LOAD HIT, ALL GUARDED HERE
--------------------------------------------------
1. **A CHECK constraint a dry run structurally cannot see.** `text_status`
   permits only three values; the enricher had grown a fourth. 295 rows went in
   and then the load aborted -- minutes after a dry run reported success,
   because *a dry run never attempts an insert, so it never meets a
   constraint*. Every row is therefore pre-flighted against the schema in BOTH
   modes here, before anything is written.
2. **PostgREST silently caps responses at 1000 rows.** A read that looks
   complete simply stops. Every read here pages explicitly.
3. **Archetype dedup that only consulted pre-existing rows.** Clustering emits
   several clusters sharing a (section, label), so each duplicate inserted
   again; the giveaway was an impossible "409 created, -26 reused". The map is
   updated as rows are created.
4. **A global unique key.** `(source_paper_key, source_question_number)` carries
   no subject, and every Edexcel subject sits the same sessions, so the second
   subject collided with the first on row one. Migration 17 re-scoped it to
   include `subject_id`.

SLUGS ARE ISSUED ONCE
---------------------
Matching is on `(subject_id, source_paper_key, source_question_number)`, never
on position. Attempts reference slugs forever, so a re-cut that renumbered them
would silently detach every student's history.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import boto3

# Mirrors the schema's CHECK constraints exactly. Kept here so a row can be
# rejected before it reaches the database rather than halfway through a load.
VALID_DIFFICULTY = frozenset({"easy", "medium", "hard"})
VALID_TEXT_STATUS = frozenset({"ok", "repaired", "needs_vision"})
VALID_REVIEW_PRIORITY = frozenset({"disputed", "same_chapter", "unconfirmed", "agreed"})

PAGE_SIZE = 1000

#: Supabase closes an idle or over-used pooled connection without warning, and
#: httpx surfaces it as a bare WriteError/ReadError. A load of several hundred
#: rows hits this reliably, so every write is retried rather than losing the run
#: partway. The load itself is idempotent -- it matches on
#: (source_paper_key, source_question_number) -- so a retry can never double-write.
WRITE_RETRIES = 4


# ─────────────────────────────────────────────────────────────────────────────
# Paged reads
# ─────────────────────────────────────────────────────────────────────────────


def with_retry(operation, what: str):
    """
    Run a PostgREST call, retrying a dropped connection.

    Only transport failures are retried. A constraint violation or a 4xx is a
    real answer and is raised immediately -- retrying it would just produce the
    same error four times and bury the message.
    """
    import time

    last: Exception | None = None
    for attempt in range(WRITE_RETRIES):
        try:
            return operation()
        except Exception as error:  # noqa: BLE001 - narrowed by inspection below
            name = type(error).__name__
            transport = any(
                token in name for token in ("WriteError", "ReadError", "ConnectError",
                                            "RemoteProtocolError", "ConnectTimeout",
                                            "ReadTimeout", "PoolTimeout")
            )
            if not transport:
                raise
            last = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{what}: transport failed after {WRITE_RETRIES} attempts") from last


def fetch_all(query_builder, page_size: int = PAGE_SIZE) -> list[dict]:
    """
    Read every row, not the first 1000.

    `query_builder` is a callable taking (offset, limit) and returning the
    PostgREST builder, so the range can be applied per page.
    """
    rows: list[dict] = []
    offset = 0
    while True:
        chunk = query_builder(offset, page_size).execute().data or []
        rows.extend(chunk)
        if len(chunk) < page_size:
            return rows
        offset += page_size


# ─────────────────────────────────────────────────────────────────────────────
# Pre-flight
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PreflightResult:
    ok: list[dict] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.problems


def preflight(rows: list[dict]) -> PreflightResult:
    """
    Check every row against the schema BEFORE any write, in every mode.

    This runs identically in a dry run and a real load. That is the whole point:
    the 4MB1 load died on a constraint its dry run could not have met.
    """
    result = PreflightResult()

    for row in rows:
        slug = row.get("slug", "<no slug>")
        errors: list[str] = []

        if not row.get("slug"):
            errors.append("slug is empty")
        if not row.get("section_id"):
            errors.append("section_id is unset (NOT NULL)")
        if not row.get("subject_id"):
            errors.append("subject_id is unset (NOT NULL)")
        if row.get("ordinal_in_chapter") is None:
            errors.append("ordinal_in_chapter is unset (NOT NULL)")

        marks = row.get("marks")
        if not isinstance(marks, int) or marks <= 0:
            errors.append(f"marks must be a positive integer, got {marks!r}")

        difficulty = row.get("difficulty")
        if difficulty is not None and difficulty not in VALID_DIFFICULTY:
            errors.append(f"difficulty {difficulty!r} not in {sorted(VALID_DIFFICULTY)}")

        text_status = row.get("text_status")
        if text_status is not None and text_status not in VALID_TEXT_STATUS:
            errors.append(f"text_status {text_status!r} not in {sorted(VALID_TEXT_STATUS)}")

        priority = row.get("review_priority")
        if priority is not None and priority not in VALID_REVIEW_PRIORITY:
            errors.append(
                f"review_priority {priority!r} not in {sorted(VALID_REVIEW_PRIORITY)}"
            )

        confidence = row.get("classifier_confidence")
        if confidence is not None and not (0.0 <= confidence <= 1.0):
            errors.append(f"classifier_confidence {confidence!r} outside [0, 1]")

        if errors:
            result.problems.extend(f"{slug}: {error}" for error in errors)
        else:
            result.ok.append(row)

    slugs = [row.get("slug") for row in rows]
    duplicates = {slug for slug in slugs if slugs.count(slug) > 1 and slug}
    for slug in sorted(duplicates):
        result.problems.append(f"{slug}: slug appears more than once in this batch")

    keys = [(r.get("source_paper_key"), r.get("source_question_number")) for r in rows]
    dup_keys = {key for key in keys if keys.count(key) > 1}
    for key in sorted(dup_keys, key=str):
        result.problems.append(f"{key}: (paper, question) appears more than once")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# R2
# ─────────────────────────────────────────────────────────────────────────────


def r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def upload_pdf(client, bucket: str, local_path: Path, key: str) -> str:
    client.upload_file(
        str(local_path), bucket, key, ExtraArgs={"ContentType": "application/pdf"}
    )
    return f"{os.environ['NEXT_PUBLIC_R2_PUBLIC_URL'].rstrip('/')}/{key}"


def public_url(key: str) -> str:
    return f"{os.environ['NEXT_PUBLIC_R2_PUBLIC_URL'].rstrip('/')}/{key}"


# ─────────────────────────────────────────────────────────────────────────────
# Archetypes
# ─────────────────────────────────────────────────────────────────────────────


def sync_archetypes(
    supabase,
    archetypes: list[dict],
    section_id_of: dict[str, str],
    execute: bool,
) -> tuple[dict[tuple[str, str], str], dict[str, int]]:
    """
    Ensure an archetype row exists per (section, label), and return the map.

    There is no unique constraint on `(section_id, label)`, and clustering emits
    several clusters sharing one -- so the map MUST be updated as rows are
    created, or every duplicate inserts again. The 4MB1 run reported an
    impossible "409 created, -26 reused" before this was fixed.
    """
    existing = fetch_all(
        lambda offset, limit: supabase.table("workbook_archetypes")
        .select("id,section_id,label")
        .range(offset, offset + limit - 1)
    )
    by_key: dict[tuple[str, str], str] = {
        (row["section_id"], row["label"]): row["id"] for row in existing
    }

    stats = {"created": 0, "reused": 0}
    for archetype in archetypes:
        section_id = section_id_of.get(archetype["section"])
        if section_id is None:
            continue
        key = (section_id, archetype["label"])
        if key in by_key:
            stats["reused"] += 1
            continue
        stats["created"] += 1
        if execute:
            created = (
                supabase.table("workbook_archetypes")
                .insert(
                    {
                        "section_id": section_id,
                        "label": archetype["label"],
                        "description": f"{archetype['size']} question(s) sharing this shape",
                    }
                )
                .execute()
                .data
            )
            if created:
                by_key[key] = created[0]["id"]
        else:
            # A dry run must simulate the insert in the map too, or it counts
            # every repeat of a (section, label) as another creation and reports
            # a number the real run will never match. Clustering emits many
            # clusters sharing a label, so this is the common case, not an edge.
            by_key[key] = f"dry-run-{len(by_key)}"

    return by_key, stats
