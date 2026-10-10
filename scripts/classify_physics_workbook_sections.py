"""
Phase 3: classify Physics (4PH0/4PH1) workbook questions into chapter sections.

Port of classify_mathsa_workbook_sections.py. Assigns every question a PRIMARY
section (which chapter of the book it is printed in) plus SECONDARY sections it
also draws on. Physics makes multi-label matter more than any maths subject: a
typical 9-mark question opens on a v-t graph, moves to F = ma and closes on
kinetic energy, so it is 1.1 AND 1.2 AND 4.3. The primary is the topic carrying
the most marks.

CANDIDATES ONLY. The two-model agreement decides how closely each one is
reviewed before it reaches the book.

MODELS
------
Groq `openai/gpt-oss-120b` first, `qwen/qwen3.8-27b` as the independent second
opinion (a different family, so agreement means something). Every cached
result records which model answered.

THE 12 SCANNED QUESTIONS ARE CLASSIFIED FROM THEIR MARK SCHEMES
---------------------------------------------------------------
2019 May-Jun Paper 1 is an image-only scan, so its stems are empty. Maths A
rejected a mark-scheme fallback because its blocks were whole pages carrying
two or three questions with offset numbers. That reason does not hold here:
every Physics mark scheme block is cut to its own band and pinned by the
question number the scheme PRINTS ("Total for question 7 = 14 marks"), and the
Phase 1 audit read every one back. So for those 12 the classifier reads the
verified mark-scheme text, labelled as such in the prompt, and the result is
marked `route: "markscheme"` so the review step can see where it came from.

USAGE
-----
    python scripts/classify_physics_workbook_sections.py --limit 12   # sample
    python scripts/classify_physics_workbook_sections.py              # pass 1
    python scripts/classify_physics_workbook_sections.py --second-pass
    python scripts/classify_physics_workbook_sections.py --report --write
    python scripts/classify_physics_workbook_sections.py --check-taxonomy
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
QUESTIONS_PATH = REPO_ROOT / "data" / "workbook" / "physics_questions.json"
CACHE_PATH = REPO_ROOT / "data" / "workbook" / "physics_classification_cache.json"
SECOND_CACHE_PATH = REPO_ROOT / "data" / "workbook" / "physics_classification_second.json"
OUTPUT_PATH = REPO_ROOT / "data" / "workbook" / "physics_classifications.json"

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
# Physics stems are long and multi-part (mean 846 characters); the later parts
# often carry the most marks, so the limit has to reach them.
STEM_LIMIT = 1800
REQUEST_DELAY_S = 0.4
MAX_RETRIES = 4
RENDER_DPI = 110

# The 30 sections, mirroring supabase/migrations/33_workbook_physics_taxonomy.sql.
# `--check-taxonomy` diffs the two: drift here would map questions onto section
# codes that do not exist in the database, and nothing downstream would notice.
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"


def latest_section_migration(subject_code: str = "4PH1") -> Path | None:
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
    "1.1": "Movement and position",
    "1.2": "Forces and their effects",
    "1.3": "Stopping distance and terminal velocity",
    "1.4": "Hooke's law and elastic behaviour",
    "1.5": "Momentum",
    "1.6": "Moments and centre of gravity",
    "2.1": "Mains electricity and electrical power",
    "2.2": "Current, voltage and resistance in circuits",
    "2.3": "Charge, current and energy transfer",
    "2.4": "Electric charge",
    "3.1": "Properties of waves",
    "3.2": "The electromagnetic spectrum",
    "3.3": "Light: reflection, refraction and total internal reflection",
    "3.4": "Sound",
    "4.1": "Energy stores, transfers and efficiency",
    "4.2": "Thermal energy transfer",
    "4.3": "Work and power",
    "4.4": "Energy resources and electricity generation",
    "5.1": "Density and pressure",
    "5.2": "Change of state and specific heat capacity",
    "5.3": "Ideal gas molecules",
    "6.1": "Magnetism",
    "6.2": "Electromagnetism",
    "6.3": "Electromagnetic induction",
    "7.1": "Atoms and radioactive emissions",
    "7.2": "Half-life, uses and dangers of radioactivity",
    "7.3": "Fission and fusion",
    "8.1": "Motion in the universe",
    "8.2": "Stellar evolution",
    "8.3": "Cosmology",
}

CHAPTER_NAMES = {
    "1": "Forces and motion",
    "2": "Electricity",
    "3": "Waves",
    "4": "Energy resources and energy transfers",
    "5": "Solids, liquids and gases",
    "6": "Magnetism and electromagnetism",
    "7": "Radioactivity and particles",
    "8": "Astrophysics",
}

# Physics has no process-only sections: the spec's "Units" sub-topics, the only
# candidates, are not in the taxonomy at all (see migration 33).
SECONDARY_ONLY: set[str] = set()
SECONDARY_ONLY_FALLBACK: dict[str, str] = {}


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


SYSTEM_PROMPT = f"""You classify Edexcel International GCSE Physics (4PH1) exam questions into a fixed syllabus taxonomy.

{taxonomy_block()}

For each question return:
  primary   - the ONE section code for the physics that carries the MOST MARKS in the question. This decides which chapter of the workbook it is printed in. Physics questions are multi-part: weigh every part by its (n) mark tally, do not just take the topic of part (a).
  secondary - 0 to 3 further section codes that other parts of the question genuinely examine. Leave empty if single-topic.
  archetype - a short lowercase phrase naming the recurring question shape, 3-6 words, e.g. "velocity time graph distance", "specific heat capacity experiment", "half-life graph activity". Use the SAME phrase for questions of the same shape so repeats cluster.
  confidence - 0.0 to 1.0, your genuine certainty in `primary`.

Rules:
- Use ONLY codes from the list above. Never invent a code.
- A practical / experiment question is classified by the PHYSICS being investigated (a specific heat capacity experiment is 5.2, a refractive index experiment is 3.3), not as a generic skills question.
- Some inputs are a MARK SCHEME instead of the question, because the question page is a scan. Classify the question that mark scheme answers.
- Reply with a JSON array and nothing else. No prose, no markdown fences.

Section boundaries, written from the specification statements each section holds:
- 1.1 distance-time and velocity-time graphs, average speed, acceleration = change in velocity / time, gradient and area of a v-t graph, v^2 = u^2 + 2as.
- 1.2 types of force, vectors and scalars, resultant force, friction, F = m x a, W = m x g, free-body force diagrams.
- 1.3 stopping, thinking and braking distance and the factors affecting them; forces on falling objects, parachutes and terminal velocity.
- 1.4 force-extension of springs, wires and rubber bands, Hooke's law, limit of proportionality, elastic behaviour.
- 1.5 momentum p = m x v, conservation of momentum in collisions and explosions, force = change in momentum / time, car safety features (crumple zones, airbags, seat belts), Newton's third law.
- 1.6 moment = force x perpendicular distance, centre of gravity, principle of moments, beams on two supports, stability.
- 2.1 mains safety (fuses, earthing, double insulation, circuit breakers, plug wiring), heating effect of current, P = I x V, E = I x V x t, choosing a fuse, a.c. versus d.c.
- 2.2 series and parallel circuits, current-voltage characteristics of resistor, filament lamp and diode, LDRs and thermistors, V = I x R, current at a junction, combining resistances.
- 2.3 current as rate of flow of charge, Q = I x t, electrons in metals, voltage as energy per unit charge, E = Q x V.
- 2.4 electrostatics: charging insulators by friction, transfer of electrons, attraction and repulsion, dangers and uses of static charge.
- 3.1 transverse and longitudinal waves, amplitude, frequency, wavelength, period, v = f x lambda, f = 1/T (including for sound and light), the DOPPLER EFFECT for a moving source, reflection and refraction of waves in general (ripple tanks).
- 3.2 order of the electromagnetic spectrum, uses and dangers of each region.
- 3.3 law of reflection, ray diagrams, refraction of light, refractive index n = sin i / sin r, critical angle, sin c = 1/n, total internal reflection, optical fibres.
- 3.4 sound: hearing range 20-20 000 Hz, measuring the speed of sound, echoes, oscilloscope traces, pitch and frequency, loudness and amplitude.
- 4.1 energy stores and transfers, conservation of energy, efficiency, Sankey diagrams.
- 4.2 conduction, convection, radiation, insulation, emission and absorption by surfaces.
- 4.3 work done = force x distance, GPE = m x g x h, KE = 1/2 m v^2, conversions between them, power = work done / time.
- 4.4 generating electricity from fossil fuels, nuclear, wind, water, geothermal and solar sources, and their advantages and disadvantages.
- 5.1 density = mass / volume and measuring it, pressure = force / area, pressure acts equally in all directions, pressure difference = height x density x g.
- 5.2 heating and changes of state, particle arrangements of solids, liquids and gases, temperature-time heating and cooling curves, specific heat capacity and its measurement.
- 5.3 random motion of gas molecules, gas pressure, absolute zero, the Kelvin scale, kinetic energy and temperature, p/T and pV relationships for a fixed mass of gas.
- 6.1 magnets, magnetic materials, hard and soft magnetic materials, field lines and field patterns of magnets, induced magnetism.
- 6.2 magnetic field of a current, electromagnets, fields of wires/coils/solenoids, force on a moving charge, the MOTOR EFFECT, left-hand rule, electric motors, loudspeakers.
- 6.3 electromagnetic induction, generators and dynamos, transformers, Vp/Vs = Np/Ns, Vp x Ip = Vs x Is, high-voltage transmission of electricity.
- 7.1 atomic structure, atomic and mass number, isotopes, nature and penetration of alpha, beta and gamma, nuclear decay equations, detectors, background radiation.
- 7.2 activity and its decrease, half-life calculations and graphs, uses of radioactivity in medicine and industry, contamination versus irradiation, dangers and safety.
- 7.3 nuclear fission of U-235, chain reactions, control rods, moderator, shielding, nuclear fusion and the conditions it needs.
- 8.1 the solar system, gravitational force and g on different bodies, orbits of planets, moons, comets and satellites, orbital speed = 2 x pi x r / T.
- 8.2 colour and surface temperature of stars, life cycle of stars, absolute magnitude, Hertzsprung-Russell diagram.
- 8.3 Big Bang theory, cosmic microwave background, red-shift of galaxies, change in wavelength / wavelength = velocity / speed of light, expansion of the universe.

Overlaps most likely to go wrong:
- Doppler effect of a moving sound or wave source is 3.1; red-shift of GALAXIES is 8.3.
- Fusion powering stars inside a stellar LIFE CYCLE question is 8.2; fusion versus fission or reactor physics is 7.3.
- A nuclear power station question about control rods, moderators or chain reactions is 7.3; one comparing it with other ENERGY RESOURCES is 4.4.
- W = m x g on Earth is 1.2; g on other planets or in orbit is 8.1.
- A falling object reaching TERMINAL VELOCITY is 1.3 even though it involves resultant force.
- KE and GPE calculations are 4.3 even when the object is a car or a falling ball.
- The heating effect of a current or a fuse rating is 2.1; a circuit with resistors and meters is 2.2.
- Electrical energy E = Q x V or Q = I x t is 2.3; E = I x V x t and P = I x V in appliances is 2.1.
- Transformers and generators are 6.3; motors and the left-hand rule are 6.2.
- v = f x lambda for sound or water waves is 3.1; pitch, loudness, oscilloscope traces and measuring the speed of sound are 3.4.

Format: [{{"id":"<id>","primary":"3.3","secondary":["3.1"],"archetype":"refractive index glass block","confidence":0.9}}]"""


def section_migrations(subject_code: str = "4PH1") -> list[Path]:
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
            f"{QUESTIONS_PATH} not found. Run enrich_physics_workbook_questions.py --execute first."
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


def markscheme_text(question: dict) -> str:
    """The verified mark-scheme block's text, for a question with no stem."""
    if not question.get("ms_pdf"):
        return ""
    with fitz.open(REPO_ROOT / question["ms_pdf"]) as doc:
        text = " ".join(page.get_text() for page in doc)
    text = re.sub(r"GradeMax|Physics\s*·[^\n]*|4PH\d\s*\|[^\n]*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem_for(question: dict) -> tuple[str, str]:
    """(text to classify, route). Scanned questions read their mark scheme."""
    if question["text_status"] == "needs_vision":
        scheme = markscheme_text(question)
        if scheme:
            return f"[MARK SCHEME for this question] {scheme}", "markscheme"
    return question["stem"], "text"


def classify_text_batch(batch: list[dict], provider: str = "gemini") -> dict[str, dict]:
    routes = {question_id(q): stem_for(q) for q in batch}
    payload = "\n\n".join(
        f'--- id: {question_id(q)} | {q["marks"]} marks ---\n'
        f"{routes[question_id(q)][0][:STEM_LIMIT]}"
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
            results[entry_id] = {**cleaned, "model": model, "route": routes[entry_id][1]}

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
    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ_API_KEY is not set in .env.local")
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

    # Every question goes by text; scanned ones carry their mark scheme text
    # (see the module docstring), so nothing needs the vision route.
    text_pending = pending
    vision_pending: list[dict] = []

    print(f"{'=' * 74}")
    print("PHYSICS (4PH1) SECTION CLASSIFICATION")
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
