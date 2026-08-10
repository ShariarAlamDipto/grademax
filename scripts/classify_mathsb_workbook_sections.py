"""
Phase 3: classify FPM workbook questions into chapter sections.

Assigns every question a PRIMARY section (which chapter of the book it is
printed in) plus any SECONDARY sections it also draws on (which make it findable
from those chapters). Multi-label is the point: the single-tag classification in
`pages.topics` is why Coordinates ended up with 111 questions and Graphs with 12
-- a question that finds where a curve meets a line and then integrates between
the intersections is Coordinates *and* Calculus, and forcing a choice skews
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

So text classification runs on Groq `llama-3.3-70b-versatile`, whose free tier
is per-minute and comfortably covers 70 batches. The ~13 questions with no
extractable text (a scanned paper) go to `gemini-flash-latest`, which carries
its own quota -- a handful of vision calls is all that budget can cover, and it
beats classifying an empty string.

The second opinion (`--second-pass`) deliberately uses a DIFFERENT family,
gpt-oss, because two runs of one model agree with themselves and would make the
agreement signal meaningless.

Every cached result records which model answered, and the run prints the
breakdown. That is not decoration: an earlier version fell back silently from a
dead primary model and classified 180 questions before anyone noticed.

Results are cached per question, so re-runs cost nothing and an interrupted run
resumes where it stopped.

USAGE
-----
    python scripts/classify_mathsb_workbook_sections.py --limit 20   # sample first
    python scripts/classify_mathsb_workbook_sections.py              # full run
    python scripts/classify_mathsb_workbook_sections.py --report     # from cache
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
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "mathsb_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "mathsb_classification_cache.json"
SECOND_CACHE_PATH = REPO_ROOT / "data" / "workbook" / "mathsb_classification_second.json"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "mathsb_classifications.json"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# `gemini-2.5-flash` is capped at 20 requests PER DAY on this project's free
# tier (quota GenerateRequestsPerDayPerProjectPerModel), which a single sample
# run exhausts. That is a daily cap, not a rate limit, so retrying never clears
# it. `gemini-flash-latest` carries its own quota and is used for the handful of
# vision calls, which is all the budget can cover.
GEMINI_VISION_MODEL = "gemini-flash-latest"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
# Second opinion. A different family from GROQ_MODEL on purpose -- two runs of
# the same model agree with themselves and would make the agreement signal
# meaningless. gpt-oss keeps its reasoning out of the content field, unlike
# Qwen, which emits a <think> block that ate the whole token budget before
# reaching the JSON.
GROQ_SECOND_MODEL = "openai/gpt-oss-120b"

# Reasoning models spend output tokens thinking before they answer, so the
# allowance has to cover both or the JSON is truncated away.
GROQ_MAX_TOKENS = 9000

BATCH_SIZE = 6
STEM_LIMIT = 900
REQUEST_DELAY_S = 0.4
MAX_RETRIES = 4
RENDER_DPI = 110

# The 47 sections, mirroring supabase/migrations/12_workbook_schema.sql.
# `--check-taxonomy` diffs the two: drift here would map questions onto section
# codes that do not exist in the database, and nothing downstream would notice.
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


def latest_section_migration(subject_code: str = "4MB1") -> Path | None:
    """
    The highest-numbered migration that seeds `workbook_sections` FOR THIS
    SUBJECT.

    Resolved by glob rather than pinned to a filename: sections have already
    been reshaped once (12 seeded 47, 13 merged them to 41) and a pinned path
    silently checks a stale taxonomy the moment another migration lands.

    The subject filter is not optional. Migration 15 seeds 50 sections for Maths
    B, so an unfiltered glob returns that file and diffs FPM's taxonomy against
    another subject's -- reporting every FPM section as missing and every Maths B
    section as unexpected, for a taxonomy that had not changed at all.
    """
    candidates = [
        path
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if "INSERT INTO workbook_sections" in (text := path.read_text(encoding="utf-8"))
        and f"'{subject_code}'" in text
    ]
    return candidates[-1] if candidates else None
TAXONOMY: dict[str, str] = {
    "1.1": 'Fractions, decimals and percentages',
    "1.2": 'Ratio, proportion and rates of change',
    "1.3": 'Indices, surds and standard form',
    "1.4": 'Accuracy, bounds and estimation',
    "2.1": 'Set notation and Venn diagrams',
    "2.2": 'Two-set problems',
    "2.3": 'Three-set problems',
    "3.1": 'Expanding, factorising and simplifying',
    "3.2": 'Linear equations and inequalities',
    "3.3": 'Simultaneous equations',
    "3.4": 'Quadratic equations',
    "3.5": 'Algebraic fractions',
    "3.6": 'Rearranging formulae and changing the subject',
    "3.7": 'Sequences and the nth term',
    "4.1": 'Function notation, domain and range',
    "4.2": 'Composite functions',
    "4.3": 'Inverse functions',
    "4.4": 'Graphs of functions and graphical solutions',
    "5.1": 'Matrix arithmetic',
    "5.2": 'Determinants and inverse matrices',
    "5.3": 'Solving simultaneous equations with matrices',
    "5.4": 'Matrix transformations',
    "6.1": 'Angles, parallel lines and polygons',
    "6.2": 'Triangles, congruence and similarity',
    "6.3": 'Circle theorems',
    "6.4": "Pythagoras' theorem",
    "6.5": 'Constructions and loci',
    "7.1": 'Perimeter and area of plane shapes',
    "7.2": 'Circles, arcs and sectors',
    "7.3": 'Volume and surface area of solids',
    "7.4": 'Similar shapes: length, area and volume',
    "8.1": 'Vector arithmetic and magnitude',
    "8.2": 'Position vectors and geometric proof',
    "8.3": 'Single transformations',
    "8.4": 'Combined and inverse transformations',
    "9.1": 'Right-angled triangle trigonometry',
    "9.2": 'The sine rule',
    "9.3": 'The cosine rule and the area of a triangle',
    "9.4": 'Bearings and three-dimensional problems',
    "9.5": 'Trigonometric graphs and equations',
    "10.1": 'Presenting and interpreting data',
    "10.2": 'Averages and measures of spread',
    "10.3": 'Cumulative frequency and box plots',
    "10.4": 'Histograms and frequency density',
    "10.5": 'Probability of single and combined events',
    "10.6": 'Tree diagrams and conditional probability',
    "11.1": 'Differentiating polynomials',
    "11.2": 'Gradients, tangents and normals',
    "11.3": 'Turning points and their nature',
    "11.4": 'Kinematics: displacement, velocity and acceleration',
}

CHAPTER_NAMES = {
    "1": 'Number',
    "2": 'Sets',
    "3": 'Algebra',
    "4": 'Functions',
    "5": 'Matrices',
    "6": 'Geometry',
    "7": 'Mensuration',
    "8": 'Vectors and transformation geometry',
    "9": 'Trigonometry',
    "10": 'Statistics and probability',
    "11": 'Calculus',
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


SYSTEM_PROMPT = f"""You classify Edexcel International GCSE Mathematics B (4MB1) exam questions into a fixed syllabus taxonomy.

{taxonomy_block()}

For each question return:
  primary   - the ONE section code for the dominant skill being examined. This decides which chapter of the workbook the question is printed in. Choose the skill that carries the most marks, not the first topic mentioned.
  secondary - 0 to 3 further section codes the question genuinely also requires. Omit anything incidental (basic algebra, arithmetic). Leave empty if the question is single-topic.
  archetype - a short lowercase phrase naming the recurring question shape, 3-6 words, e.g. "tangent to curve at point", "sum to infinity of gp", "r-formula max then solve". Use the SAME phrase for questions of the same shape so repeats cluster.
  confidence - 0.0 to 1.0, your genuine certainty in `primary`.

Rules:
- Use ONLY codes from the list above. Never invent a code.
- A question spanning several topics still gets exactly one primary.
- Reply with a JSON array and nothing else. No prose, no markdown fences.

Disambiguation - these pairs are confused most often:
- 5.4 Matrix transformations applies ONLY when a MATRIX represents the transformation, or one is asked for. A reflection, rotation, translation or enlargement described geometrically is 8.3, and a composition of them is 8.4.
- A Venn diagram asking for a PROBABILITY is 10.5, or 10.6 if it is conditional. Chapter 2 is for set notation, regions, shading and counting elements.
- 6.4 Pythagoras is for right-angled triangles where only SIDES are involved. Bring in 9.1 as soon as an angle is used or asked for.
- 9.2 is the sine rule, 9.3 the cosine rule and the (1/2)ab sin C area formula. Use 9.4 when the question is set in bearings or in three dimensions, even though a rule is applied.
- 7.4 Similar shapes is for AREA or VOLUME scale factors between similar figures. Simple similar-triangle side lengths are 6.2.
- 7.2 covers anything where an arc, sector, circumference or circle area is central; 7.1 is straight-edged plane shapes.
- 11.4 Kinematics means a PARTICLE OR BODY IN MOTION described by displacement, velocity or acceleration - use it even though the work is differentiating. A growing or shrinking volume, radius or area is 11.1 or 11.2.
- 11.3 is for finding turning points and determining their nature; 11.2 is for gradients, tangents and normals at a given point.
- 10.4 Histograms applies whenever frequency density or unequal class widths appear.
- 1.4 covers upper and lower bounds and "to the nearest"; ordinary rounding of a final answer is incidental and should not drive the classification.
- 3.4 Quadratic equations is for solving algebraically. Use 4.4 only when the demand is to draw, complete or read values from a graph.
- 4.2 is fg(x) style composition; 4.3 is finding an inverse. Evaluating f(3) alone is 4.1.

Format: [{{"id":"<id>","primary":"9.4","secondary":["8.2"],"archetype":"tangent to curve at point","confidence":0.9}}]"""


def check_taxonomy() -> int:
    """Diff TAXONOMY against the section seed in migration 12. 0 if identical."""
    migration_path = latest_section_migration()
    if migration_path is None:
        print(f"No migration seeding workbook_sections found in {MIGRATIONS_DIR}")
        return 1

    print(f"checking against {migration_path.name}")
    sql = migration_path.read_text(encoding="utf-8")
    try:
        block = sql.split("INSERT INTO workbook_sections")[1].split(") AS v(chapter_number")[0]
    except IndexError:
        print("Could not locate the workbook_sections seed block in the migration.")
        return 1

    seeded = {
        f"{chapter}.{section}": title
        # `''` is SQL's escape for a literal apostrophe, so a section titled
        # "Pythagoras'' theorem" in the migration must be read as one value and
        # unescaped -- a naive [^']+ stops at the first quote and drops it.
        for chapter, section, title in (
            (c, s, t.replace("''", "'"))
            for c, s, t in re.findall(r"\((\d+),\s*(\d+),\s*'((?:[^']|'')+)'\)", block)
        )
    }

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
            time.sleep(6 * (attempt + 1))  # free tier is per-minute; wait it out
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

    secondary = [
        str(code).strip()
        for code in (entry.get("secondary") or [])
        if str(code).strip() in TAXONOMY and str(code).strip() != primary
    ]

    try:
        confidence = float(entry.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    archetype = str(entry.get("archetype", "")).strip().lower()[:80]

    return {
        "primary": primary,
        "secondary": secondary[:3],
        "archetype": archetype,
        "confidence": max(0.0, min(1.0, confidence)),
    }


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


def classify_vision(question: dict) -> dict | None:
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
    print(f"FPM SECTION CLASSIFICATION")
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
            failed += 1
            print(f"  ! vision failed for {key}")
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
