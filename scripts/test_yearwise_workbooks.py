"""
One comprehensive pass over the three yearwise workbooks. Run it before
sending anything to a printer, and after touching anything under `lib/yearwise_*`.

Seven stages, ordered so the cheap ones fail first:

  1. Every module compiles.
  2. SOURCE AUDITS -- the archive holds the right papers for the right sessions,
     each paired with its own mark scheme.
  3. WORKBOOK AUDITS -- each book against the papers it was built from, page by
     page and as rendered ink.
  4. INDEPENDENT VERIFIER -- the finished PDFs, both volumes, checked by code
     that shares nothing with the builder.
  5. DETERMINISM -- rebuilding from the same archive reproduces all six
     interiors exactly. A build that drifts is a build whose audit means
     nothing, because the audited file is not the one that ships.
  6. NEGATIVE CONTROL -- three deliberate breakages, which the audit MUST
     catch. A check that has never failed has never been tested; this is how
     the covered-text gap was found, when a build with a white band painted
     through a question passed every text comparison.
  7. PRESS READINESS -- the six files a printer receives: page counts, A4 and
     upright, the watermark and footer on every interior sheet, one image on
     each cover.

Stage 6 mutates a copy of the P4 interior and restores it; stage 5 rewrites the
interiors from the archive. Neither touches `final/`.

    python scripts/test_yearwise_workbooks.py
    python scripts/test_yearwise_workbooks.py --quick    # skip 5 and 6
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
UNITS = (("m1", "M1"), ("s1", "S1"), ("p4", "P4"))

results: list[tuple[str, bool]] = []


def record(tag: str, ok: bool, seconds: float | None = None) -> bool:
    results.append((tag, ok))
    took = f"  ({seconds:.0f}s)" if seconds is not None else ""
    print(f"[{'PASS' if ok else 'FAIL'}] {tag}{took}", flush=True)
    return ok


def run(args: list[str], tag: str) -> subprocess.CompletedProcess:
    start = time.time()
    proc = subprocess.run([sys.executable, *args], capture_output=True, text=True,
                          env=ENV, cwd=ROOT)
    if not record(tag, proc.returncode == 0, time.time() - start):
        for line in proc.stdout.splitlines():
            if line.strip().startswith("!"):
                print(f"        {line.strip()}", flush=True)
    return proc


def interior(slug: str, token: str, kind: str) -> Path:
    return ROOT / "data" / "workbook" / f"{slug}_yearwise" / \
        f"{token}_Yearwise_{kind}_interior.pdf"


def final(slug: str, token: str, kind: str) -> Path:
    tail = "" if kind == "Questions" else "_MarkSchemes"
    return ROOT / "data" / "workbook" / f"{slug}_yearwise" / "final" / \
        f"GradeMax_{token}_Yearwise_Workbook{tail}.pdf"


def fingerprint(path: Path) -> tuple[int, str]:
    """Page count plus a hash of every page's text -- stable across re-saves."""
    doc = fitz.open(path)
    digest = hashlib.md5()
    for index in range(doc.page_count):
        digest.update(doc[index].get_text().encode("utf-8", "replace"))
    count = doc.page_count
    doc.close()
    return count, digest.hexdigest()


def stage_compile() -> None:
    print("\n1. EVERY MODULE COMPILES", flush=True)
    modules = [f"scripts/lib/yearwise_{name}.py" for name in
               ("sources", "repair", "layout", "build", "finish", "workbook_audit")]
    modules += ["scripts/lib/m1_paper_pages.py", "scripts/verify_yearwise_books.py"]
    modules += [f"scripts/{verb}_{slug}_yearwise_{noun}.py"
                for slug, _ in UNITS
                for verb, noun in (("audit", "sources"), ("audit", "workbook"),
                                   ("build", "workbook"), ("finalize", "workbook"))]
    run(["-m", "py_compile", *modules], f"compile {len(modules)} modules")


def stage_audits() -> None:
    print("\n2. SOURCE AUDITS  (archive: right papers, right sessions, clean pairs)",
          flush=True)
    for slug, _ in UNITS:
        run([f"scripts/audit_{slug}_yearwise_sources.py"], f"{slug} source audit")

    print("\n3. WORKBOOK AUDITS  (book vs its sources, page by page + rendered ink)",
          flush=True)
    for slug, _ in UNITS:
        run([f"scripts/audit_{slug}_yearwise_workbook.py"], f"{slug} workbook audit")

    print("\n4. INDEPENDENT VERIFIER  (finished PDFs, both volumes, no shared code)",
          flush=True)
    run(["scripts/verify_yearwise_books.py"], "verify all six volumes")


def stage_determinism() -> None:
    print("\n5. REBUILD IS DETERMINISTIC  (same archive must give the same book)",
          flush=True)
    before = {}
    for slug, token in UNITS:
        for kind in ("Questions", "MarkSchemes"):
            path = interior(slug, token, kind)
            before[path] = fingerprint(path)
    for slug, _ in UNITS:
        subprocess.run([sys.executable,
                        f"scripts/build_{slug}_yearwise_workbook.py", "--execute"],
                       capture_output=True, text=True, env=ENV, cwd=ROOT)
    same = True
    for path, was in before.items():
        now = fingerprint(path)
        if now != was:
            same = False
            print(f"        {path.name}: {was[0]}pp/{was[1][:8]} -> "
                  f"{now[0]}pp/{now[1][:8]}", flush=True)
    record("rebuild reproduces all six interiors exactly", same)


def stage_negative_control(scratch: Path) -> None:
    print("\n6. NEGATIVE CONTROL  (the audit must FAIL on a broken book)", flush=True)
    live = interior("p4", "P4", "Questions")
    good, broken_copy = scratch / "p4_good.pdf", scratch / "p4_broken.pdf"
    shutil.copy(live, good)

    def audit() -> int:
        return subprocess.run(
            [sys.executable, "scripts/audit_p4_yearwise_workbook.py"],
            capture_output=True, text=True, env=ENV, cwd=ROOT).returncode

    def attempt(tag, mutate) -> None:
        shutil.copy(good, live)
        doc = fitz.open(live)
        mutate(doc)
        doc.save(str(broken_copy))
        doc.close()
        shutil.copy(broken_copy, live)
        record(f"audit catches: {tag}", audit() != 0)

    try:
        attempt("a question page deleted", lambda d: d.delete_page(5))
        attempt("content covered by a white band",
                lambda d: d[5].draw_rect(fitz.Rect(0, 0, 595, 150),
                                         color=None, fill=(1, 1, 1)))
        attempt("two papers swapped", lambda d: d.move_page(40, 5))
    finally:
        shutil.copy(good, live)
    record("restored book audits clean again", audit() == 0)


def stage_press() -> None:
    print("\n7. PRESS READINESS  (the six files that go to the printer)", flush=True)
    every = True
    for slug, token in UNITS:
        for kind in ("Questions", "MarkSchemes"):
            book, source = final(slug, token, kind), interior(slug, token, kind)
            doc, inner = fitz.open(book), fitz.open(source)
            sizes = {f"{p.rect.width:.0f}x{p.rect.height:.0f}" for p in doc}
            rotated = sum(1 for p in doc if p.rotation)
            body = doc.page_count - 2
            marked = sum(1 for n in range(1, doc.page_count - 1)
                         if doc[n].get_images(full=True))
            footed = sum(1 for n in range(1, doc.page_count - 1)
                         if "GradeMax" in doc[n].get_text())
            # One image per cover: the artwork alone, so a watermark that leaked
            # onto a cover shows up as a second.
            covers = (len(doc[0].get_images(full=True)) == 1
                      and len(doc[doc.page_count - 1].get_images(full=True)) == 1)
            ok = (doc.page_count == inner.page_count + 2 and sizes == {"595x842"}
                  and rotated == 0 and marked == body and footed == body and covers)
            every &= ok
            print(f"[{'PASS' if ok else 'FAIL'}] {book.name:48} {doc.page_count:4}pp  "
                  f"sizes={sorted(sizes)} rotated={rotated} watermark={marked}/{body} "
                  f"footer={footed}/{body} "
                  f"covers={'1 image each' if covers else 'WRONG'}", flush=True)
            doc.close()
            inner.close()
    record("press readiness of all six volumes", every)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true",
                        help="skip the rebuild and the negative control")
    args = parser.parse_args()

    print("=" * 72)
    print("  Yearwise workbooks -- comprehensive test")
    print("=" * 72)
    stage_compile()
    stage_audits()
    if not args.quick:
        stage_determinism()
        with tempfile.TemporaryDirectory() as scratch:
            stage_negative_control(Path(scratch))
    stage_press()

    failed = [tag for tag, ok in results if not ok]
    print("\n" + "=" * 72)
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    for tag in failed:
        print(f"  FAILED: {tag}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
