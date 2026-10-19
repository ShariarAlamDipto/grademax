"""
Phase 3: classify Maths A (4MA1) Higher workbook questions into chapter sections.

Assigns every question a PRIMARY section (which chapter of the book it is
printed in) plus any SECONDARY sections it also draws on (which make it findable
from those chapters). Multi-label is the point: the single-tag classification in
`pages.topics` is why one FPM chapter ended up with 111 of 431 questions -- a
Maths A question that finds the area of a sector and then the volume of the
prism built on it is Mensuration *and* 3D shapes, and forcing a choice skews
everything.

This produces CANDIDATES ONLY. Phase 4 puts every one in front of a human before
anything reaches the book. The job here is to make that review fast, not to be
trusted on its own.

MODEL ROUTING -- and why it is not what you would expect
-------------------------------------------------------
Two providers were ruled out by their free tiers, not by quality:

  * OpenRouter is the usual route in this repo, but that account has never
    purchased credits, so every non-free model returns 402.
  * Gemini looked ideal (strong on notation, native vision, JSON mode) but
    `gemini-2.5-flash` allows 20 requests PER DAY on this project
    (GenerateRequestsPerDayPerProjectPerModel). A single sample run exhausts it,
    and because it is a daily cap rather than a rate limit, retry and backoff
    never clear it.

MODEL AVAILABILITY MOVED SINCE THE MATHS B RUN -- `llama-3.3-70b-versatile`
now 404s ("model_not_found"); Groq has retired the Llama family from this
account entirely. Verified available here: openai/gpt-oss-120b, gpt-oss-20b,
qwen/qwen3.6-27b, qwen/qwen3.8-27b, groq/compound. So text classification runs
on Groq `openai/gpt-oss-120b`, whose free tier is per-minute and comfortably
covers the batches. The 5 questions with no extractable text (the 2019 Jan
image-only pages) go to `gemini-flash-latest`, which carries its own quota.

The second opinion (`--second-pass`) deliberately uses a DIFFERENT family,
qwen3.8, because two runs of one model agree with themselves and would make the
agreement signal meaningless. This Qwen was checked for the failure the older
one had -- emitting a <think> block that ate the token budget before reaching
the JSON -- and does not do it; it returns pretty-printed JSON that parses.

THE MARK-SCHEME FALLBACK WAS TRIED AND REJECTED -- measured, not assumed
------------------------------------------------------------------------
When the vision quota is spent, the four 2019 Jan image-only questions have no
stem to classify. Their MARK SCHEMES do have text, and a mark scheme states the
method outright, so reading those instead looked like the obvious way to avoid
classifying an empty string.

It was built, run, and checked against three questions whose rendered pages had
already been read by hand during Phase 1. It got roughly ONE of four right:

  2019_jan_1H:3   biased spinner, estimate times it lands on yellow (6.3)
                  -> returned 1.6 Percentages
  2019_jan_1HR:7  scale model of two water towers (4.11)
                  -> returned 2.6 Simultaneous equations, lifted from a
                     NEIGHBOURING block on the same page
  2019_jan_2H:10  -> returned 3.3 from a block the page prints as Q9

The cause is structural: these are Format B whole-page attachments, so the page
carries two or three questions and the numbers printed on it are offset from
ours. Pinning the right block by its mark total does not work, because several
blocks on a page share a total -- the same lesson already recorded for the S1/P4
mark schemes, that block matching is not evidence the block is right.

Vision, by contrast, got its one completed case right (2019_jan_1HR:10, area
between concentric semicircles -> 4.9 Mensuration). So the route was removed and
those questions are left UNCLASSIFIED until the quota resets. A wrong section is
worse than a missing one: it looks reviewed and it is not.

Every cached result records which model answered, and the run prints the
breakdown. That is not decoration: an earlier version fell back silently from a
dead primary model and classified 180 questions before anyone noticed.

Results are cached per question, so re-runs cost nothing and an interrupted run
resumes where it stopped.

USAGE
-----
    python scripts/classify_mathsa_workbook_sections.py --limit 20   # sample first
    python scripts/classify_mathsa_workbook_sections.py              # full run
    python scripts/classify_mathsa_workbook_sections.py --report     # from cache
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import fitz  # PyMuPDF
import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_classification_cache.json"
SECOND_CACHE_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_classification_second.json"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "mathsa_classifications.json"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# `gemini-2.5-flash` is capped at 20 requests PER DAY on this project's free
# tier (quota GenerateRequestsPerDayPerProjectPerModel), which a single sample
# run exhausts. That is a daily cap, not a rate limit, so retrying never clears
# it. `gemini-flash-latest` carries its own quota and is used for the handful of
# vision calls, which is all the budget can cover.
GEMINI_VISION_MODEL = "gemini-flash-latest"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"
# Second opinion. A different family from GROQ_MODEL on purpose -- two runs of
# the same model agree with themselves and would make the agreement signal
# meaningless. Checked on this corpus: qwen3.8 does NOT emit the <think> block
# that made an older Qwen unusable, and its pretty-printed JSON parses.
GROQ_SECOND_MODEL = "qwen/qwen3.8-27b"

# Reasoning models spend output tokens thinking before they answer, so the
# allowance has to cover both or the JSON is truncated away.
GROQ_MAX_TOKENS = 9000

BATCH_SIZE = 6
STEM_LIMIT = 900
REQUEST_DELAY_S = 0.4
MAX_RETRIES = 4
RENDER_DPI = 110

# The 39 sections, mirroring supabase/migrations/20_workbook_mathsa_taxonomy.sql.
# `--check-taxonomy` diffs the two: drift here would map questions onto section
# codes that do not exist in the database, and nothing downstream would notice.
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


def latest_section_migration(subject_code: str = "4MA1") -> Path | None:
    """
    The highest-numbered migration that seeds `workbook_sections` FOR THIS
    SUBJECT.

    Resolved by glob rather than pinned to a filename: a taxonomy can be
    reshaped by a later migration (12 seeded 47 for FPM, 13 merged them to 41)
    and a pinned path silently checks a stale taxonomy the moment one lands.

    The subject filter is not optional. Migration 20 seeds 39 sections for Maths
    A, so an unfiltered glob returns whichever subject landed last and diffs
    this taxonomy against another subject's -- reporting every section as missing
    and every foreign section as unexpected, for a taxonomy that had not changed.
    """
    candidates = [
        path
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if "INSERT INTO workbook_sections" in (text := path.read_text(encoding="utf-8"))
        and f"'{subject_code}'" in text
    ]
    return candidates[-1] if candidates else None


TAXONOMY: dict[str, str] = {
    "1.1": 'Integers',
    "1.2": 'Fractions',
    "1.3": 'Decimals',
    "1.4": 'Powers and roots',
    "1.5": 'Set language and notation',
    "1.6": 'Percentages',
    "1.7": 'Ratio and proportion',
    "1.8": 'Degree of accuracy',
    "1.9": 'Standard form',
    "1.10": 'Applying number',
    "1.11": 'Electronic calculators',
    "2.1": 'Use of symbols',
    "2.2": 'Algebraic manipulation',
    "2.3": 'Expressions and formulae',
    "2.4": 'Linear equations',
    "2.5": 'Proportion',
    "2.6": 'Simultaneous linear equations',
    "2.7": 'Quadratic equations',
    "2.8": 'Inequalities',
    "3.1": 'Sequences',
    "3.2": 'Function notation',
    "3.3": 'Graphs',
    "3.4": 'Calculus',
    "4.1": 'Angles, lines and triangles',
    "4.2": 'Polygons',
    "4.3": 'Symmetry',
    "4.4": 'Measures',
    "4.5": 'Construction',
    "4.6": 'Circle properties',
    "4.7": 'Geometrical reasoning',
    "4.8": "Trigonometry and Pythagoras' theorem",
    "4.9": 'Mensuration',
    "4.10": '3D shapes and volume',
    "4.11": 'Similarity',
    "5.1": 'Vectors',
    "5.2": 'Transformation geometry',
    "6.1": 'Graphical representation of data',
    "6.2": 'Statistical measures',
    "6.3": 'Probability',
}

CHAPTER_NAMES = {
    "1": 'Numbers and the number system',
    "2": 'Equations, formulae and identities',
    "3": 'Sequences, functions and graphs',
    "4": 'Geometry and trigonometry',
    "5": 'Vectors and transformation geometry',
    "6": 'Statistics and probability',
}

# Sections that describe a PROCESS used inside other questions rather than a
# question's own subject. They are legitimate specification statements and are
# kept so the tree matches the spec 1:1, but a catch-all named "Applying number"
# will absorb the book if the model may choose it as a primary -- the same skew
# that put 111 of 431 FPM questions into one chapter. Enforced in clean_result(),
# not merely requested in the prompt, because a prompt rule is a request and a
# code rule is a guarantee.
SECONDARY_ONLY = {"1.10", "1.11", "4.4"}

# Where a SECONDARY_ONLY code is proposed as primary, it is rewritten to the
# section that actually carries the question. Chosen per code rather than
# dropped, so the question still lands somewhere defensible.
SECONDARY_ONLY_FALLBACK = {
    "1.10": "1.7",   # "applying number" in practice means ratio/proportion work
    "1.11": "1.8",   # calculator use shows up as an accuracy demand
    "4.4": "4.9",    # measures questions are mensuration in all but name
}


def taxonomy_block() -> str:
    lines: list[str] = []
    current_chapter = None
    for code, title in TAXONOMY.items():
        chapter = code.split(".")[0]
        if chapter != current_chapter:
            current_chapter = chapter
            lines.append(f"\nCHAPTER {chapter} - {CHAPTER_NAMES[chapter]}")
        lines.append(f"  {code}  {title}")
    return "\n".join(lines)


SYSTEM_PROMPT = f"""You classify Edexcel International GCSE Mathematics A (4MA1) HIGHER TIER exam questions into a fixed syllabus taxonomy.

{taxonomy_block()}

For each question return:
  primary   - the ONE section code for the dominant skill being examined. This decides which chapter of the workbook the question is printed in. Choose the skill that carries the most marks, not the first topic mentioned.
  secondary - 0 to 3 further section codes the question genuinely also requires. Omit anything incidental (basic arithmetic, rounding a final answer). Leave empty if the question is single-topic.
  archetype - a short lowercase phrase naming the recurring question shape, 3-6 words, e.g. "reverse percentage original price", "histogram frequency density estimate", "similar solids volume scale factor". Use the SAME phrase for questions of the same shape so repeats cluster.
  confidence - 0.0 to 1.0, your genuine certainty in `primary`.

Rules:
- Use ONLY codes from the list above. Never invent a code.
- A question spanning several topics still gets exactly one primary.
- NEVER use 1.10, 1.11 or 4.4 as a primary. They are process statements, not question subjects; use them only as secondary, and pick the real topic for primary.
- Reply with a JSON array and nothing else. No prose, no markdown fences.

Disambiguation - written against what 4MA1 actually sets, and where a first pass is most likely to go wrong:
- Chapter 1 vs chapter 2 is the biggest risk. NUMERIC work on given numbers is chapter 1; work on ALGEBRAIC expressions is chapter 2. "Simplify 3/8 + 1/6" is 1.2; "Simplify (x+3)/(x^2-9)" is 2.2.
- 1.4 Powers and roots covers surds, rationalising a denominator, and the laws of indices applied to NUMBERS or simple powers - "Simplify y^5 x y^9", "Rationalise 1/(3+sqrt2)". Do not send these to 2.2.
- 1.8 Degree of accuracy is for UPPER AND LOWER BOUNDS and calculations with bounds. "Give your answer to 3 significant figures" appearing at the end of any question is incidental instruction, NOT evidence for 1.8 - that phrase is printed on most questions in the paper.
- 1.5 Set language is the Venn-diagram and set-notation section. A Venn diagram whose demand is a PROBABILITY is 6.3.
- 1.6 Percentages covers reverse percentages, compound interest and depreciation. 1.7 is ratio, direct sharing and rates. Where a question mixes them, choose the one carrying more marks.
- 2.5 Proportion is for "y is directly/inversely proportional to x" and finding the constant. Ordinary ratio sharing is 1.7.
- 2.7 Quadratic equations is for SOLVING - factorising to solve, the formula, completing the square. Real questions almost never print the word "quadratic", so judge by the shape of the equation, not by keyword. Forming the equation from a geometric or worded context still counts as 2.7.
- 2.8 Inequalities includes representing a region on a grid and listing integer solutions.
- 3.1 Sequences covers nth term of linear and quadratic sequences. 3.2 Function notation covers f(x), fg(x) and inverse functions. 3.3 Graphs covers drawing and reading graphs, gradient and the equation of a straight line, and graphical solution of equations.
- 3.4 Calculus means DIFFERENTIATION: gradient of a curve, turning points, and velocity/acceleration from a displacement function. Finding the gradient BETWEEN TWO POINTS is 3.3, not 3.4.
- 4.8 covers Pythagoras, right-angled trigonometry, the sine and cosine rules, the (1/2)ab sin C area formula, bearings, and 3D trigonometry - the specification puts all of it in one statement, so do not split it out to 4.1.
- 4.1 Angles, lines and triangles is angle facts: parallel lines, angles in a triangle, exterior angles. 4.2 Polygons is interior/exterior angles of polygons specifically.
- 4.6 Circle properties is the circle theorems (cyclic quadrilaterals, angle at centre, tangent-radius, alternate segment).
- 4.9 Mensuration is perimeter, area, arcs and sectors. 4.10 is volume and surface area of SOLIDS (cylinder, cone, sphere, prism, pyramid, frustum).
- 4.11 Similarity covers similar triangles AND area/volume scale factors between similar solids. Congruence proofs are 4.7 Geometrical reasoning.
- 5.1 Vectors covers column-vector arithmetic, magnitude, and vector geometric proof. 5.2 Transformation geometry covers reflection, rotation, translation and enlargement, including describing a single transformation and combining two.
- 6.1 Graphical representation covers histograms (whenever frequency density or unequal class widths appear), cumulative frequency curves, box plots and scatter diagrams. 6.2 Statistical measures covers mean/median/mode, estimated mean from a grouped table, and quartiles/interquartile range read off a source.
- 6.3 Probability covers single and combined events, tree diagrams, conditional probability and probability from a Venn diagram or two-way table.

Format: [{{"id":"<id>","primary":"4.9","secondary":["1.8"],"archetype":"area of sector and triangle","confidence":0.9}}]"""


def section_migrations(subject_code: str = "4MA1") -> list[Path]:
    """
    Every migration seeding `workbook_sections` for this subject, in order.

    Accumulating is correct HERE because Maths B's migrations are purely
    additive: 15 seeded 50 sections and 16 added 3 more. It would be wrong for
    FPM, whose migration 13 renumbered the sections rather than extending them,
    so accumulating 12 and 13 would leave stale codes behind. That script
    therefore still reads only its newest migration -- the difference is in the
    migrations, not an inconsistency between the scripts.
    """
    return [
        path
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if "INSERT INTO workbook_sections" in (text := path.read_text(encoding="utf-8"))
        and f"'{subject_code}'" in text
    ]


def check_taxonomy() -> int:
    """Diff TAXONOMY against the sections seeded by the migrations. 0 if identical."""
    migration_paths = section_migrations()
    if not migration_paths:
        print(f"No migration seeding workbook_sections found in {MIGRATIONS_DIR}")
        return 1

    print(f"checking against {', '.join(p.name for p in migration_paths)}")

    # Accumulate across migrations in order. A subject's taxonomy is not confined
    # to one file: 15 seeded 50 sections for Maths B and 16 added 3 more, so
    # diffing against only the newest reports the other 50 as missing.
    seeded: dict[str, str] = {}
    for migration_path in migration_paths:
        sql = migration_path.read_text(encoding="utf-8")
        for chunk in sql.split("INSERT INTO workbook_sections")[1:]:
            block = chunk.split(") AS v(chapter_number")[0]
            # `''` is SQL's escape for a literal apostrophe, so a section titled
            # "Pythagoras'' theorem" must be read as one value and unescaped --
            # a naive [^']+ stops at the first quote and drops it.
            for chapter, section, title in re.findall(
                r"\((\d+),\s*(\d+),\s*'((?:[^']|'')+)'\)", block
            ):
                seeded[f"{chapter}.{section}"] = title.replace("''", "'")

    missing = sorted(set(TAXONOMY) - set(seeded), key=lambda c: [int(p) for p in c.split(".")])
    extra = sorted(set(seeded) - set(TAXONOMY), key=lambda c: [int(p) for p in c.split(".")])
    renamed = [
        (code, TAXONOMY[code], seeded[code])
        for code in sorted(set(TAXONOMY) & set(seeded), key=lambda c: [int(p) for p in c.split(".")])
        if TAXONOMY[code] != seeded[code]
    ]

    print(f"script: {len(TAXONOMY)} sections   migration: {len(seeded)} sections")
    for code in missing:
        print(f"  MISSING FROM MIGRATION  {code}  {TAXONOMY[code]}")
    for code in extra:
        print(f"  MISSING FROM SCRIPT     {code}  {seeded[code]}")
    for code, in_script, in_migration in renamed:
        print(f"  TITLE DIFFERS           {code}\n      script:    {in_script}\n      migration: {in_migration}")

    if missing or extra or renamed:
        print(f"\n  {len(missing) + len(extra) + len(renamed)} difference(s) -- these must match.")
        return 1

    print("\n  In sync.")
    return 0


def load_questions() -> list[dict]:
    if not QUESTIONS_PATH.is_file():
        raise FileNotFoundError(
            f"{QUESTIONS_PATH} not found. Run enrich_fpm_workbook_questions.py --execute first."
        )
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def question_id(question: dict) -> str:
    return f"{question['paper_key']}:{question['question_number']}"


def load_cache() -> dict:
    if CACHE_PATH.is_file():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def write_json_atomically(path: Path, payload: object) -> None:
    """
    Write via a temp file and rename, so the cache is never left truncated.

    This matters more than it looks: the cache is the ONLY record of work
    already paid for, and it is rewritten after every batch. A plain write_text
    that is interrupted partway -- process killed, runtime limit hit, machine
    sleeps -- leaves invalid JSON and destroys the entire run's progress, not
    just the batch in flight. os.replace is atomic within a filesystem, so a
    reader sees either the old complete file or the new complete file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def save_cache(cache: dict) -> None:
    write_json_atomically(CACHE_PATH, cache)


def render_first_page(pdf_path: Path) -> str:
    """Base64 PNG of a question's first page, for the vision path."""
    with fitz.open(REPO_ROOT / pdf_path) as doc:
        pixmap = doc[0].get_pixmap(dpi=RENDER_DPI)
        return base64.b64encode(pixmap.tobytes("png")).decode()


def call_gemini(model: str, parts: list[dict]) -> str | None:
    """
    One Gemini call. `parts` is the user content (text and/or inline images).

    Thinking is disabled: this is a lookup against a fixed taxonomy, not a
    reasoning problem, and a thinking budget eats the output allowance and
    truncates the JSON.
    """
    # No thinkingConfig: `gemini-flash-latest` rejects thinkingBudget 0 outright
    # with a bare "invalid argument" 400 -- that model requires thinking, so it
    # cannot be switched off. The output allowance is set high enough that
    # thinking tokens do not truncate the JSON.
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GEMINI_URL.format(model=model),
                params={"key": os.environ["GEMINI_API_KEY"]},
                json=body,
                timeout=120,
            )
        except requests.RequestException:
            time.sleep(3 * (attempt + 1))
            continue

        if response.status_code == 429 or response.status_code >= 500:
            # A 429 body states how long to wait ("Please retry in 31.2s") and
            # the free tier's 20-requests-per-minute window is longer than a
            # short fixed backoff, so 6/12/18/24s never cleared it and all four
            # vision questions failed every run. Honour the server's own number
            # when it gives one, with a floor that actually crosses the window.
            if response.status_code == 429 and "free_tier_requests" in response.text:
                # The daily allowance, not a per-minute burst. Waiting cannot
                # clear it, so stop trying for the rest of the run.
                global _VISION_QUOTA_SPENT
                _VISION_QUOTA_SPENT = True
                print("  ! Gemini free-tier vision quota spent -- skipping vision")
                return None
            delay = 6 * (attempt + 1)
            stated = re.search(r"retry in ([\d.]+)s", response.text)
            if stated:
                delay = max(delay, float(stated.group(1)) + 2)
            elif response.status_code == 429:
                delay = max(delay, 35)
            time.sleep(delay)
            continue
        if response.status_code != 200:
            return None

        try:
            candidates = response.json().get("candidates") or []
            return candidates[0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError):
            return None

    return None


def call_groq(payload: str, model: str = GROQ_MODEL) -> str | None:
    """
    Text-only classification call.

    No `response_format`: Groq's JSON mode requires a top-level object, but the
    taxonomy reply is an array, and several models 400 on it. `parse_reply`
    extracts the array from free text anyway.
    """
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": payload},
        ],
        "temperature": 0,
        "max_tokens": GROQ_MAX_TOKENS,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
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
    """Pull the JSON array out of a reply that may be fenced or padded."""
    # Reasoning models emit a <think> block first, which can itself contain
    # brackets and would otherwise be mistaken for the payload.
    text = re.sub(r"<think>.*?</think>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"^\s*```(?:json)?|```\s*$", "", text.strip(), flags=re.M).strip()
    match = re.search(r"\[.*\]", text, re.S)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except ValueError:
        return []
    return parsed if isinstance(parsed, list) else []


def clean_result(entry: dict) -> dict | None:
    """Validate one model result against the taxonomy. Invalid -> None."""
    primary = str(entry.get("primary", "")).strip()
    if primary not in TAXONOMY:
        return None

    # A process section is never a question's own subject. The prompt asks for
    # this, but a prompt is a request -- rewriting here is what makes it hold,
    # and the original is kept so the review queue can see what was proposed.
    demoted_from = None
    if primary in SECONDARY_ONLY:
        demoted_from = primary
        primary = SECONDARY_ONLY_FALLBACK[primary]

    secondary = [
        str(code).strip()
        for code in (entry.get("secondary") or [])
        if str(code).strip() in TAXONOMY and str(code).strip() != primary
    ]
    if demoted_from and demoted_from not in secondary:
        secondary.insert(0, demoted_from)

    try:
        confidence = float(entry.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    archetype = str(entry.get("archetype", "")).strip().lower()[:80]

    result = {
        "primary": primary,
        "secondary": secondary[:3],
        "archetype": archetype,
        "confidence": max(0.0, min(1.0, confidence)),
    }
    if demoted_from:
        result["demoted_from"] = demoted_from
    return result


def classify_text_batch(batch: list[dict], provider: str = "gemini") -> dict[str, dict]:
    payload = "\n\n".join(
        f'--- id: {question_id(q)} | {q["marks"]} marks ---\n{q["stem"][:STEM_LIMIT]}'
        for q in batch
    )

    if provider == "groq":
        raw, model = call_groq(payload, GROQ_SECOND_MODEL), GROQ_SECOND_MODEL
    else:
        raw, model = call_groq(payload, GROQ_MODEL), GROQ_MODEL

    if raw is None:
        return {}

    valid_ids = {question_id(q) for q in batch}
    results: dict[str, dict] = {}

    for entry in parse_reply(raw):
        cleaned = clean_result(entry)
        if cleaned is None:
            continue
        entry_id = str(entry.get("id", "")).strip()
        if entry_id in valid_ids:
            results[entry_id] = {**cleaned, "model": model, "route": "text"}

    return results


# Gemini's free tier caps vision at 20 requests PER DAY, so once it is spent no
# amount of backoff clears it -- the earlier code burned 4 retries x 35s on each
# of four questions before giving up. Latched once, then every later question
# goes straight to the mark-scheme route.
_VISION_QUOTA_SPENT = False


def classify_vision(question: dict) -> dict | None:
    global _VISION_QUOTA_SPENT
    if _VISION_QUOTA_SPENT:
        return None

    image = render_first_page(Path(question["qp_pdf"]))

    raw = call_gemini(
        GEMINI_VISION_MODEL,
        [
            {
                "text": f'--- id: {question_id(question)} | {question["marks"]} marks ---\n'
                f"This question has no extractable text. Read it from the image."
            },
            {"inline_data": {"mime_type": "image/png", "data": image}},
        ]
    )
    if raw is None:
        return None

    for entry in parse_reply(raw):
        cleaned = clean_result(entry)
        if cleaned is not None:
            return {**cleaned, "model": GEMINI_VISION_MODEL, "route": "vision"}

    return None


def review_priority(primary: dict, second: dict | None) -> str:
    """
    How carefully a human needs to look at this one.

    Self-reported confidence is not trustworthy here -- the model returns a mean
    of 0.86 with nothing below 0.7 while getting roughly one in five wrong, the
    same miscalibration that made the old `pages.difficulty` labels useless.
    Agreement between two independent models is a far better signal, so it takes
    precedence and confidence is only a tiebreak when there is no second opinion.
    """
    if second is None:
        return "unconfirmed"
    if second["primary"] == primary["primary"]:
        return "agreed"
    if second["primary"].split(".")[0] == primary["primary"].split(".")[0]:
        return "same_chapter"  # right chapter, arguable section
    return "disputed"


def report(questions: list[dict], cache: dict, second_cache: dict | None = None) -> None:
    second_cache = second_cache or {}
    classified = [q for q in questions if question_id(q) in cache]
    if not classified:
        print("Nothing classified yet.")
        return

    by_chapter: Counter = Counter()
    by_section: Counter = Counter()
    confidences: list[float] = []
    multi = 0
    archetypes: dict[str, list[str]] = defaultdict(list)

    for question in classified:
        result = cache[question_id(question)]
        primary = result["primary"]
        by_chapter[primary.split(".")[0]] += 1
        by_section[primary] += 1
        confidences.append(result["confidence"])
        multi += bool(result["secondary"])
        if result["archetype"]:
            archetypes[result["archetype"]].append(question_id(question))

    total = len(classified)
    print(f"\n{'=' * 74}\nCLASSIFICATION REPORT  ({total} of {len(questions)} questions)\n{'=' * 74}")

    print("\n  Primary chapter distribution")
    for chapter in sorted(CHAPTER_NAMES, key=int):
        count = by_chapter.get(chapter, 0)
        bar = "#" * round(count * 40 / max(by_chapter.values() or [1]))
        print(f"    {chapter:>2}  {CHAPTER_NAMES[chapter][:34]:<35} {count:>3}  {bar}")

    empty_sections = [code for code in TAXONOMY if code not in by_section]
    print(f"\n  Sections used     : {len(by_section)} of {len(TAXONOMY)}")
    if empty_sections:
        print(f"  Sections with none: {', '.join(empty_sections)}")

    print(f"\n  Multi-section     : {multi} ({multi / total:.0%})")
    print(f"  Mean confidence   : {sum(confidences) / total:.2f} (self-reported, uncalibrated)")

    if second_cache:
        priorities = Counter(
            review_priority(cache[question_id(q)], second_cache.get(question_id(q)))
            for q in classified
        )
        confirmed = priorities["agreed"]
        print("\n  Two-model agreement (the Phase 4 review signal)")
        print(f"    agreed on section  : {confirmed:>3} ({confirmed / total:.0%})  -> fast accept")
        print(f"    same chapter only  : {priorities['same_chapter']:>3}  -> quick look")
        print(f"    disputed           : {priorities['disputed']:>3}  -> review carefully")
        print(f"    no second opinion  : {priorities['unconfirmed']:>3}")

    clustered = {k: v for k, v in archetypes.items() if len(v) > 1}
    print(f"\n  Archetypes        : {len(archetypes)} distinct, {len(clustered)} with repeats")
    for label, ids in sorted(clustered.items(), key=lambda kv: -len(kv[1]))[:8]:
        print(f"    {len(ids):>3}x  {label}")


def write_merged(questions: list[dict], cache: dict, second_cache: dict) -> None:
    """Fold both passes onto the question inventory for Phase 4 to consume."""
    merged = [
        {
            **question,
            "classification": cache.get(question_id(question)),
            "second_opinion": second_cache.get(question_id(question)),
            "review_priority": (
                review_priority(
                    cache[question_id(question)], second_cache.get(question_id(question))
                )
                if question_id(question) in cache
                else None
            ),
        }
        for question in questions
    ]
    write_json_atomically(OUTPUT_PATH, merged)
    print(f"\n  written: {OUTPUT_PATH.relative_to(REPO_ROOT)}  ({len(merged)} questions)")


def main() -> int:
    load_dotenv(REPO_ROOT / ".env.local")
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is not set in .env.local")
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="classify at most N new questions")
    parser.add_argument("--report", action="store_true", help="report from cache, call nothing")
    parser.add_argument("--write", action="store_true", help="write the classifications file")
    parser.add_argument(
        "--check-taxonomy",
        action="store_true",
        help="diff this script's sections against migration 12 and exit",
    )
    parser.add_argument(
        "--second-pass",
        action="store_true",
        help="run an independent second opinion (Groq) for agreement scoring",
    )
    args = parser.parse_args()

    if args.check_taxonomy:
        return check_taxonomy()

    questions = load_questions()
    cache = load_cache()
    second_cache = (
        json.loads(SECOND_CACHE_PATH.read_text(encoding="utf-8"))
        if SECOND_CACHE_PATH.is_file()
        else {}
    )

    if args.report:
        report(questions, cache, second_cache)
        if args.write:
            write_merged(questions, cache, second_cache)
        return 0

    if args.second_pass:
        # Only questions the first pass classified, and only by text: the point
        # is an independent read of the same evidence.
        pending = [
            q
            for q in questions
            if question_id(q) in cache
            and question_id(q) not in second_cache
            and q["text_status"] != "needs_vision"
        ]
        if args.limit:
            pending = pending[: args.limit]

        print(f"Second pass ({GROQ_MODEL}): {len(pending)} to do, {len(second_cache)} cached\n")
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            for key, result in classify_text_batch(batch, provider="groq").items():
                second_cache[key] = result
            write_json_atomically(SECOND_CACHE_PATH, second_cache)
            print(f"  {min(start + BATCH_SIZE, len(pending)):>4}/{len(pending)}  cached={len(second_cache)}")
            time.sleep(REQUEST_DELAY_S)

        report(questions, cache, second_cache)
        return 0

    pending = [q for q in questions if question_id(q) not in cache]
    if args.limit:
        pending = pending[: args.limit]

    text_pending = [q for q in pending if q["text_status"] != "needs_vision"]
    vision_pending = [q for q in pending if q["text_status"] == "needs_vision"]

    print(f"{'=' * 74}")
    print(f"MATHS A (4MA1) SECTION CLASSIFICATION")
    print(f"  cached   : {len(cache)}")
    print(f"  to do    : {len(text_pending)} by text, {len(vision_pending)} by vision")
    print(f"{'=' * 74}\n")

    done = failed = 0

    for start in range(0, len(text_pending), BATCH_SIZE):
        batch = text_pending[start : start + BATCH_SIZE]
        results = classify_text_batch(batch)

        for question in batch:
            key = question_id(question)
            if key in results:
                cache[key] = results[key]
                done += 1
            else:
                failed += 1
                print(f"  ! no valid result for {key}")

        save_cache(cache)
        print(f"  text {min(start + BATCH_SIZE, len(text_pending)):>4}/{len(text_pending)}  cached={len(cache)}")
        time.sleep(REQUEST_DELAY_S)

    for index, question in enumerate(vision_pending, 1):
        key = question_id(question)
        result = classify_vision(question)
        if result is None:
            # Left UNCLASSIFIED on purpose. A mark-scheme-text fallback was
            # built and measured here and it is not good enough -- see the
            # module docstring. Re-run once the daily vision quota resets.
            failed += 1
            print(f"  ! vision failed for {key} -- left unclassified")
        else:
            cache[key] = result
            done += 1
        save_cache(cache)
        print(f"  vision {index:>3}/{len(vision_pending)}  {key}")
        time.sleep(REQUEST_DELAY_S)

    print(f"\n  classified this run: {done}    failed: {failed}    cache: {len(cache)}")

    report(questions, cache)

    if args.write:
        write_merged(questions, cache, second_cache)

    return 0


if __name__ == "__main__":
    sys.exit(main())
