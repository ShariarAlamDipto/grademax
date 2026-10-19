"""
Fetch the papers a yearwise workbook's archive is missing, or holds wrongly.

Shared by the per-unit repair scripts. Two kinds of hole get filled, and the
second is the dangerous one because it does not look like a hole:

  MISSING   the slot is empty.
  WRONG     the slot holds another session's paper. Every such case found so
            far is a DUPLICATE of a neighbouring session -- M1's June 2023 held
            January's, S1's June 2021 held October's -- and a duplicate defeats
            any cover check, because the copy's cover honestly names the session
            it really is.

WHAT IS VERIFIED, AND WHY IT IS NOT A LIST OF MAGIC STRINGS

The obvious way to verify a download is to write down the item code and exam
date you expect and compare. That only proves the file is the one you looked up
-- if the lookup was wrong, the check agrees with it. So the expectations here
are derived from the SESSION instead:

  * the board's item code is on every page      (it is a question paper at all)
  * a question paper prints the unit's paper reference; a MARK SCHEME prints
    no such reference -- it writes `In Statistics S1 (WST01) Paper 01`, which
    no `WST01/01` pattern matches -- so a scheme is checked against its Pearson
    publication code instead, which names the unit AND the session and is
    therefore the stronger evidence anyway
  * no third-party branding                     (it is clean enough to publish)
  * the exam date on the cover, WHEN THERE IS ONE, falls in the right season
    and year -- from 2021 many covers set the date in an image, so its absence
    proves nothing either way
  * it matches the target session's own mark scheme better than any other

The last is the one that catches a wrong paper, and it is the same rarity-
weighted comparison the source audit uses. Its verdict is reported with the
margin, because on a unit where consecutive papers open with the same kind of
question the margin can be thin -- see the P4 note in `audit_p4_yearwise_sources`.

Nothing is written until every check passes, so a failed download leaves the
archive as it was. Anything displaced goes to `data/quarantine/`, never the bin.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import fitz
import httpx

from .yearwise_sources import (
    ITEM_CODE, PUB_CODE, SEASON_MM, SEASON_MONTHS, THIRD_PARTY, Subject,
    affinity, rarity, read, session_of)

ROOT = Path(__file__).resolve().parents[2]
QUARANTINE = ROOT / "data" / "quarantine" / "yearwise_wrong_session"

# The stamp every shelf-mate carries, measured off the archive's own files.
GM_TEXT = "GradeMax"
GM_FONT = "tiro"           # Times-Roman builtin
GM_SIZE = 11.0
GM_RIGHT_MARGIN = 8.0
GM_BASELINE_Y = 14.0
PROV_FONT = "helv"
PROV_SIZE = 9.0
PROV_X = 16.0
PROV_BASELINE_Y = 27.2

PROV_SEASON = {"Jan": "Jan", "May-Jun": "May/Jun", "Oct-Nov": "Oct/Nov"}
NUMERIC = re.compile(r"\d+\.\d+|\b\d{1,4}\b")
# How much better the target session's mark scheme must score than the runner-up
# before the download is accepted as that session's paper.
PAIR_MARGIN = 0.05


@dataclass(frozen=True)
class Wanted:
    """One hole to fill."""
    year: int
    season: str
    kind: str               # QP | MS
    url: str
    source: str             # who serves it
    why: str                # missing | holds another session's paper


def target(subject: Subject, w: Wanted) -> Path:
    archive = subject.archives[0]
    return archive.locate(w.year, w.season, w.kind)


def provenance(unit_token: str, w: Wanted) -> str:
    return (f"Mathematics · {w.year} · {PROV_SEASON[w.season]} "
            f"· {unit_token} · {w.kind}")


def mark_schemes(subject: Subject) -> dict[tuple[int, str], object]:
    """Every mark scheme the unit holds, for the pairing check."""
    out = {}
    for year, season in subject.sittings:
        for archive in subject.archives:
            path = archive.locate(year, season, "MS")
            if path.exists():
                out[(year, season)] = read(subject, year, season, "MS",
                                           archive.label, path)
                break
    return out


def check(pdf: bytes, subject: Subject, w: Wanted,
          schemes: dict) -> tuple[list[str], list[str]]:
    """Returns (problems, observations). Empty problems means it may be filed."""
    doc = fitz.open(stream=pdf, filetype="pdf")
    texts = [doc[i].get_text() for i in range(doc.page_count)]
    doc.close()
    blob = "\n".join(texts)
    flat = re.sub(r"\s+", " ", blob)

    problems: list[str] = []
    notes: list[str] = []

    codes = {m.group(1) for m in ITEM_CODE.finditer(blob)}
    coded = sum(1 for t in texts if ITEM_CODE.search(t))
    if w.kind == "QP":
        if coded < len(texts):
            problems.append(f"board item code on only {coded}/{len(texts)} pages")
        notes.append(f"item code {sorted(codes)[0] if codes else '-'}, "
                     f"{len(texts)} pages")
        if not subject.paper_code.search(flat):
            problems.append(f"no {subject.unit} paper code printed")
    else:
        # A mark scheme carries no paper reference -- it writes the unit as
        # `In Statistics S1 (WST01) Paper 01`, which no `WST01/01` pattern
        # matches. What it does carry is the publication code, which names the
        # unit AND the session, so it is both the stronger check and the only
        # one available.
        pub = PUB_CODE.search(flat)
        if not pub:
            problems.append("no Pearson publication code printed")
        else:
            code = f"{pub.group(1)}_{pub.group(2)}_{pub.group(3)}"
            said = subject.pub_typos.get(code, session_of(pub.group(3)))
            notes.append(f"publication code {code}")
            want = f"{w.year % 100:02d}{SEASON_MM[w.season]}"
            if not pub.group(1).upper().startswith(subject.unit):
                problems.append(f"publication code names {pub.group(1)}, "
                                f"not {subject.unit}")
            elif said != want:
                problems.append(f"publication code says session {said}, "
                                f"wanted {want}")
    if THIRD_PARTY.search(flat):
        problems.append("third-party branding present")

    date = re.search(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
        r"\d{1,2}\s+(\w+)\s+(20\d\d)\b", re.sub(r"\s+", " ", texts[0]))
    if date:
        month, year = date.group(1), int(date.group(2))
        notes.append(f"cover reads {date.group(0)}")
        if month not in SEASON_MONTHS[w.season] or year != w.year:
            problems.append(f"cover reads {month} {year}, wanted {w.year} {w.season}")
    else:
        notes.append("cover carries no exam date (it is set in an image)")

    # Does it pair with the session we are filling?
    body = "\n".join(texts[4:]) if w.kind == "MS" else blob
    numbers = set(NUMERIC.findall(body))
    if w.kind == "QP" and schemes:
        idf = rarity(list(schemes.values()))
        probe = type("P", (), {"numbers": numbers})()
        scored = sorted((( affinity(probe, ms, idf), key)
                         for key, ms in schemes.items()), reverse=True)
        own = next((s for s, k in scored if k == (w.year, w.season)), None)
        best, best_key = scored[0]
        if own is None:
            notes.append("no mark scheme held for this session to pair against")
        else:
            ranked = ", ".join(f"{k[0]} {k[1]} {s:.3f}" for s, k in scored[:3])
            notes.append(f"pairs with {w.year} {w.season}'s own mark scheme at "
                         f"{own:.3f}; best three: {ranked}")
            if best_key != (w.year, w.season) and best > own + PAIR_MARGIN:
                problems.append(
                    f"matches the {best_key[0]} {best_key[1]} mark scheme "
                    f"({best:.3f}) better than {w.year} {w.season}'s ({own:.3f})")
    return problems, notes


def stamp(pdf: bytes, unit_token: str, w: Wanted) -> bytes:
    doc = fitz.open(stream=pdf, filetype="pdf")
    line = provenance(unit_token, w)
    width = fitz.get_text_length(GM_TEXT, fontname=GM_FONT, fontsize=GM_SIZE)
    for page in doc:
        page.insert_text((page.rect.width - GM_RIGHT_MARGIN - width, GM_BASELINE_Y),
                         GM_TEXT, fontname=GM_FONT, fontsize=GM_SIZE)
        page.insert_text((PROV_X, PROV_BASELINE_Y), line,
                         fontname=PROV_FONT, fontsize=PROV_SIZE)
    return doc.tobytes()


def repair(subject: Subject, unit_token: str, w: Wanted,
           schemes: dict, commit: bool) -> bool:
    print(f"\n{w.year} {w.season} {w.kind}  ({w.why})  <- {w.source}")
    try:
        r = httpx.get(w.url, timeout=120, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
    except httpx.HTTPError as exc:
        print(f"  download failed: {exc}")
        return False
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        print(f"  download failed: {r.status_code} "
              f"{r.headers.get('content-type')} ({len(r.content)} bytes)")
        return False
    print(f"  {len(r.content):,} bytes")

    problems, notes = check(r.content, subject, w, schemes)
    for n in notes:
        print(f"  . {n}")
    for p in problems:
        print(f"  ! {p}")
    if problems:
        print("  verification failed -- archive untouched")
        return False

    out = stamp(r.content, unit_token, w)
    again, _ = check(out, subject, w, schemes)
    if again:
        print("  stamping broke it: " + "; ".join(again))
        return False
    doc = fitz.open(stream=out, filetype="pdf")
    stamped = sum(1 for p in doc if GM_TEXT in p.get_text())
    pages = doc.page_count
    doc.close()
    if stamped < pages:
        print(f"  stamp landed on only {stamped}/{pages} pages")
        return False
    print(f"  verified, stamped GradeMax on {stamped}/{pages} pages")

    path = target(subject, w)
    if not commit:
        print(f"  would write {path.relative_to(ROOT)}")
        return True

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        kept = QUARANTINE / f"{path.stem}__wrong_session{path.suffix}"
        if kept.exists():
            print(f"  already repaired once ({kept.name} held) -- rewriting")
            path.unlink()
        else:
            shutil.move(str(path), str(kept))
            print(f"  displaced copy -> {kept.relative_to(ROOT)}")
    path.write_bytes(out)
    print(f"  wrote {path.relative_to(ROOT)}")
    return True


def run(subject: Subject, unit_token: str, wanted: tuple[Wanted, ...],
        commit: bool) -> int:
    schemes = mark_schemes(subject)
    print(f"{subject.name} ({subject.unit}): {len(wanted)} to fetch, "
          f"{len(schemes)} mark schemes to pair against")
    ok = all([repair(subject, unit_token, w, schemes, commit) for w in wanted])
    if not commit:
        print("\ndry run -- rerun with --commit to file them")
    return 0 if ok else 1
