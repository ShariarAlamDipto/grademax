"""
Put the two M1 question papers the archive was missing into the archive.

The yearwise audit (`audit_m1_yearwise_sources.py`) found two holes in
2017-2023, and neither announced itself as a hole:

  2023 May-Jun  the slot held a SECOND COPY of January 2023 -- same item code
                P72070A, same cover, same question 1 -- so the session looked
                complete while serving the wrong exam. The real paper is
                P72902A, sat Tuesday 16 May 2023.

  2019 Oct-Nov  no question paper at all, though we hold its mark scheme.
                The paper is P58496A, sat Wednesday 23 October 2019.

Each comes from the cleanest source that actually serves it. Pearson publishes
Summer 2023 themselves; October 2019 they keep behind an Edexcel Online login
(`/content/dam/secure/...` answers a 995-byte HTML page, not a PDF) and PMT
never hosted it, so that one comes from the Paperlords archive, whose copy
carries no watermark of its own -- the URL is read off the listing by
`harvest_paperlords_links.py`, since the upload-timestamp suffix makes it
unguessable.

Nothing is written until the download has been checked against what the paper
is supposed to be -- its item code on every page, its printed exam date, its
paper reference, and no third-party branding. A file that fails leaves the
archive untouched. Anything displaced goes to `data/quarantine/`, never the bin.

    python scripts/repair_m1_missing_qps.py            # check only
    python scripts/repair_m1_missing_qps.py --commit
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz
import httpx

ROOT = Path(__file__).resolve().parents[1]
IAL = ROOT / "data" / "Ultimate Final IAL" / "Mathematics"
QUARANTINE = ROOT / "data" / "quarantine" / "m1_wrong_session"

# The stamp every shelf-mate carries, measured off
# Mathematics_M1_2023_Oct-Nov_QP.pdf.
GM_TEXT = "GradeMax"
GM_FONT = "tiro"           # Times-Roman builtin
GM_SIZE = 11.0
GM_RIGHT_MARGIN = 8.0
GM_BASELINE_Y = 14.0
PROV_FONT = "helv"
PROV_SIZE = 9.0
PROV_X = 16.0
PROV_BASELINE_Y = 27.2

THIRD_PARTY = re.compile(
    r"physicsandmathstutor|pmt\.education|pmt\.physics|paperlords|automatepapers", re.I)


@dataclass(frozen=True)
class Missing:
    year: int
    season: str
    season_label: str          # as the provenance line writes it
    item_code: str
    exam_date: str             # as printed on the cover
    url: str
    source: str
    displaces: str | None      # what is in the slot now, and wrong

    @property
    def target(self) -> Path:
        return (IAL / str(self.year) / self.season /
                f"Mathematics_M1_{self.year}_{self.season}_QP.pdf")

    @property
    def provenance(self) -> str:
        return (f"Mathematics · {self.year} · {self.season_label} "
                f"· M1 · QP")


WANTED = (
    Missing(
        year=2023, season="May-Jun", season_label="May/Jun",
        item_code="P72902A", exam_date="Tuesday 16 May 2023",
        url=("https://qualifications.pearson.com/content/dam/pdf/"
             "International-Advanced-Level/Mathematics/2018/Exam-materials/"
             "wme01-01-que-20230517.pdf"),
        source="Pearson",
        displaces="Mathematics_M1_2023_May-Jun_QP__actually_January_2023.pdf"),
    Missing(
        year=2019, season="Oct-Nov", season_label="Oct/Nov",
        item_code="P58496A", exam_date="Wednesday 23 October 2019",
        url=("https://archive.paperlords.org/library/IAL/Maths/Oct%202019/"
             "IAL_MATHS_2019_Oct_M1_QP.pdf"),
        source="Paperlords",
        displaces=None),
)


def check(pdf: bytes, want: Missing) -> list[str]:
    doc = fitz.open(stream=pdf, filetype="pdf")
    texts = [doc[i].get_text() for i in range(doc.page_count)]
    doc.close()
    flat = re.sub(r"\s+", " ", "\n".join(texts))

    problems = []
    coded = sum(1 for t in texts if want.item_code in re.sub(r"\s+", "", t))
    if coded < len(texts):
        problems.append(f"{want.item_code} on only {coded}/{len(texts)} pages")
    if want.exam_date not in re.sub(r"\s+", " ", texts[0]):
        problems.append(f"cover does not read {want.exam_date}")
    if not re.search(r"WME01\s*/?\s*0?1", flat):
        problems.append("no WME01/01 paper reference")
    if THIRD_PARTY.search(flat):
        problems.append("third-party branding present")
    return problems


def stamp(pdf: bytes, want: Missing) -> bytes:
    doc = fitz.open(stream=pdf, filetype="pdf")
    width = fitz.get_text_length(GM_TEXT, fontname=GM_FONT, fontsize=GM_SIZE)
    for page in doc:
        page.insert_text((page.rect.width - GM_RIGHT_MARGIN - width, GM_BASELINE_Y),
                         GM_TEXT, fontname=GM_FONT, fontsize=GM_SIZE)
        page.insert_text((PROV_X, PROV_BASELINE_Y), want.provenance,
                         fontname=PROV_FONT, fontsize=PROV_SIZE)
    return doc.tobytes()


def repair(want: Missing, commit: bool) -> bool:
    print(f"\n{want.year} {want.season}  <- {want.source}")
    try:
        r = httpx.get(want.url, timeout=90, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
    except httpx.HTTPError as exc:
        print(f"  download failed: {exc}")
        return False
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        print(f"  download failed: {r.status_code} {r.headers.get('content-type')}")
        return False
    print(f"  {len(r.content):,} bytes")

    problems = check(r.content, want)
    for p in problems:
        print(f"  ! {p}")
    if problems:
        print("  verification failed -- archive untouched")
        return False

    doc = fitz.open(stream=r.content, filetype="pdf")
    pages = doc.page_count
    doc.close()
    print(f"  verified: {want.item_code}, {want.exam_date}, {pages} pages")

    out = stamp(r.content, want)
    if check(out, want):
        print("  stamping broke the paper -- archive untouched")
        return False
    doc = fitz.open(stream=out, filetype="pdf")
    stamped = sum(1 for p in doc if "GradeMax" in p.get_text())
    doc.close()
    print(f"  stamped GradeMax on {stamped}/{pages} pages")

    if not commit:
        print(f"  would write {want.target.relative_to(ROOT)}")
        return True

    want.target.parent.mkdir(parents=True, exist_ok=True)
    if want.target.exists():
        if not want.displaces:
            print(f"  {want.target.relative_to(ROOT)} already exists and nothing "
                  "is recorded as wrong with it -- skipped")
            return True
        QUARANTINE.mkdir(parents=True, exist_ok=True)
        kept = QUARANTINE / want.displaces
        if kept.exists():
            print(f"  already repaired ({kept.name} is in quarantine) -- rewriting")
            want.target.unlink()
        else:
            shutil.move(str(want.target), str(kept))
            print(f"  quarantined the wrong paper -> {kept.relative_to(ROOT)}")
    want.target.write_bytes(out)
    print(f"  wrote {want.target.relative_to(ROOT)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    args = ap.parse_args()

    ok = all([repair(w, args.commit) for w in WANTED])
    if not args.commit:
        print("\ndry run -- rerun with --commit to file them")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
