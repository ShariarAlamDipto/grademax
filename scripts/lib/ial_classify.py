"""
Shared plumbing for classifying IAL workbook questions into taxonomy sections.

Subject-neutral: the taxonomy, the disambiguation rules and the question file
all come from the caller. Each subject keeps its own entry-point script.

WHY TWO MODELS, AND WHY NOT CONFIDENCE
--------------------------------------
The 4PM1 build measured this rather than assuming it. Self-reported confidence
has **no discriminative power**: mean confidence was 0.858 where two models
agreed, 0.850 where they agreed only on the chapter, and 0.827 where they
flatly disagreed -- a 0.03 spread across the entire range of correctness. Asking
a model how sure it is tells you nothing about whether it is right.

What does work is **two different model families plus their disagreement**. The
review queue is then ordered disputed -> same-chapter -> unconfirmed -> agreed,
so a human looks first at the questions where the evidence is actually weak.

MODEL ROUTING, AS OF SEPTEMBER 2026
-----------------------------------
`llama-3.3-70b-versatile`, which the 4PM1 and 4MB1 runs used, **no longer
exists** -- Groq now 404s it. The account's usable text models are:

  * `openai/gpt-oss-120b`  -- primary. Clean JSON, keeps its reasoning out of
    `content`, fast.
  * `qwen/qwen3.8-27b`     -- second opinion. A genuinely different family,
    which is the whole point; same-family agreement is not evidence.

Avoid `qwen/qwen3.6-27b`: it spends its budget on a `<think>` block and never
reaches the JSON (measured: 682 completion tokens, no array). `groq/compound*`
caps `max_tokens` at 8192.

OpenRouter 402s on this account (no credits were ever purchased) and the Gemini
free tier is 20 requests per day per model -- a daily cap, not a rate limit, so
no amount of backoff clears it. Neither is a viable second opinion here.

OPERATIONAL RULES THAT COST TIME TO LEARN
-----------------------------------------
* **No `response_format`.** Groq's JSON mode requires a top-level object, and
  the reply here is an array; several models 400 on it. The array is extracted
  from free text instead.
* **Record which model answered, in the cache.** A silent fallback classified
  180 4PM1 questions before anyone noticed.
* **Write the cache atomically.** It is rewritten in full after every batch, so
  a plain write interrupted mid-flight destroys the whole run, not one batch.
* **Call with `requests`, not `urllib`.** Groq sits behind Cloudflare, which
  rejects urllib's default User-Agent with a bare `403 error code: 1010`.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

PRIMARY_MODEL = "openai/gpt-oss-120b"
SECOND_MODEL = "qwen/qwen3.8-27b"

MAX_TOKENS = 8000
MAX_RETRIES = 4
BATCH_SIZE = 8

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


# ─────────────────────────────────────────────────────────────────────────────
# Taxonomy
# ─────────────────────────────────────────────────────────────────────────────


def latest_section_migration(subject_code: str) -> Path | None:
    """
    The highest-numbered migration that seeds `workbook_sections` FOR THIS
    SUBJECT.

    The subject filter is not optional. Several migrations seed sections for
    different subjects, and an unfiltered glob returns whichever landed last --
    which once had 4PM1 being diffed against Maths B's taxonomy and reporting
    every section as both missing and unexpected, for a tree that had not
    changed at all.
    """
    candidates = [
        path
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if "INSERT INTO workbook_sections" in (text := path.read_text(encoding="utf-8"))
        and f"'{subject_code}'" in text
    ]
    return candidates[-1] if candidates else None


def sections_from_migration(path: Path) -> dict[str, str]:
    """
    Parse `(chapter, section, 'title')` rows into `{'4.2': 'title'}`.

    Titles are read with `(?:[^']|'')+` rather than `[^']+`: the shorter form
    stops at SQL's doubled-quote escape and silently truncated
    "Pythagoras'' theorem" on a previous subject.
    """
    text = path.read_text(encoding="utf-8")
    body = text.split("INSERT INTO workbook_sections", 1)[1]
    out: dict[str, str] = {}
    for chapter, section, title in re.findall(
        r"^\s*\((\d+),\s*(\d+),\s*'((?:[^']|'')+)'\)", body, re.M
    ):
        out[f"{chapter}.{section}"] = title.replace("''", "'")
    return out


def taxonomy_block(taxonomy: dict[str, str]) -> str:
    return "\n".join(f"{code}  {title}" for code, title in sorted(
        taxonomy.items(), key=lambda kv: [int(p) for p in kv[0].split(".")]
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Cache
# ─────────────────────────────────────────────────────────────────────────────


def write_json_atomically(path: Path, payload: object) -> None:
    """Temp file plus replace. The cache is rewritten in full every batch."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# Model calls
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Reply:
    entries: list[dict]
    model: str


def call_groq(system_prompt: str, payload: str, model: str) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise SystemExit("GROQ_API_KEY missing from .env.local")

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload},
        ],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {key}"},
                json=body,
                timeout=120,
            )
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
            continue

        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        if response.status_code != 200:
            return None

        try:
            return response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            return None

    return None


def parse_reply(raw: str) -> list[dict]:
    """
    Pull the JSON array out of whatever the model wrapped it in.

    Models fence it, preface it, or emit a `<think>` block first, so the array
    is located by bracket matching rather than by parsing the whole reply.
    """
    if not raw:
        return []
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        parsed = json.loads(raw[start : end + 1])
    except ValueError:
        return []
    return [item for item in parsed if isinstance(item, dict)]


def clean_entry(entry: dict, taxonomy: dict[str, str]) -> dict | None:
    """
    Keep only what the taxonomy actually contains.

    A hallucinated section code is worse than a missing one: it would load as a
    real assignment and nothing downstream would question it.
    """
    qid = entry.get("id")
    primary = str(entry.get("primary", "")).strip()
    if not qid or primary not in taxonomy:
        return None

    secondary_raw = entry.get("secondary") or []
    if isinstance(secondary_raw, str):
        secondary_raw = [secondary_raw]
    secondary = [
        str(code).strip()
        for code in secondary_raw
        if str(code).strip() in taxonomy and str(code).strip() != primary
    ]

    return {
        "id": str(qid),
        "primary": primary,
        "secondary": sorted(dict.fromkeys(secondary)),
    }


def classify_batch(
    batch: list[dict], system_prompt: str, taxonomy: dict[str, str], model: str
) -> dict[str, dict]:
    payload = json.dumps(
        [{"id": q["slug"], "marks": q["marks"], "stem": q["stem"][:1400]} for q in batch],
        ensure_ascii=False,
    )
    raw = call_groq(system_prompt, payload, model)
    if raw is None:
        return {}

    out: dict[str, dict] = {}
    for entry in parse_reply(raw):
        cleaned = clean_entry(entry, taxonomy)
        if cleaned is not None:
            # The model that answered is recorded on every row, so a silent
            # fallback shows up in the report instead of hiding in the data.
            cleaned["model"] = model
            out[cleaned["id"]] = cleaned
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Agreement
# ─────────────────────────────────────────────────────────────────────────────


def review_priority(primary: dict | None, second: dict | None) -> str:
    """
    How urgently a human should look at this question.

    Ordered by how weak the evidence is, NOT by any model's confidence.
    """
    if primary is None:
        return "unclassified"
    if second is None:
        return "unconfirmed"
    if primary["primary"] == second["primary"]:
        return "agreed"
    if primary["primary"].split(".")[0] == second["primary"].split(".")[0]:
        return "same_chapter"
    return "disputed"
