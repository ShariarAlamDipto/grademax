#!/usr/bin/env python3
"""Replace the wrong document in every QP/MS pair that
`audit_qp_ms_content_pairing.py` condemned, with a replacement proven by BOTH
identity and content.

For a row whose MARK SCHEME is wrong (MS_WRONG, or MISMATCH with a known-good QP):
  candidates = Pearson catalogue MSs + local-archive MSs + other live rows' MSs.
  A candidate is accepted only if
    * its own identity (cover session / publications code) names the ROW's
      session, and its unit does not contradict the QP's unit, and
    * against the row's QP it out-scores every live MS of the subject by
      ACCEPT_RATIO (so it is the best content fit, not just a plausible one).
For a row whose QUESTION PAPER is wrong (QP_WRONG) the roles swap: the
candidate QP must carry a barcode not already filed under another session, a
date/copyright year consistent with the row, and fit the row's MS best.

Nothing is guessed. A row with no accepted candidate is reported UNRESOLVED.

--commit: download the current R2 object to data/quarantine/qp_ms_pairing/,
clean + stamp the replacement (ingest_cambridge_papers.clean_and_stamp), and
overwrite the SAME R2 key (read from the row's URL), so no DB change is needed.

Usage:
    python -X utf8 scripts/fix_qp_ms_content_pairing.py                 # dry run
    python -X utf8 scripts/fix_qp_ms_content_pairing.py --subject WME01
    python -X utf8 scripts/fix_qp_ms_content_pairing.py --commit
"""

from __future__ import annotations

import argparse
import io
import json
import os
import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_qp_ms_content_pairing import (  # noqa: E402
    R2_BUCKET, R2_PUBLIC_BASE, _cache_path, _r2, ident_vs_row, ms_vs_row, session_eq,
)
from lib.paper_candidates import (  # noqa: E402
    fetch_pearson, local_candidates, parse_file, pearson_hits, pearson_kind, pearson_series,
)
from lib.paper_fingerprint import RarityScorer, option_letters, unit_family  # noqa: E402

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON = REPO_ROOT / "data" / "analysis" / "qp_ms_content_pairing.json"
OUT_JSON = REPO_ROOT / "data" / "analysis" / "qp_ms_content_fix_plan.json"
QUARANTINE = REPO_ROOT / "data" / "quarantine" / "qp_ms_pairing"
ACCEPT_RATIO = 1.35
PEARSON_PREFERENCE = 0.9
PEARSON_NOT_CONTRADICTED = 0.8
MS_SIDE = {"MS_WRONG", "MISMATCH"}
QP_SIDE = {"QP_WRONG"}
# Extra candidate folders (e.g. files fetched from Paperlords via
# harvest_paperlords_links.py). Their labels are never trusted: every file
# must pass the same cover-identity and content checks as any other candidate.
EXTRA_DIRS: list[str] = []
# Hand-verified replacements: (code, year, season, paper, side) -> file. Only for
# rows whose candidate was checked page-by-page by a person (e.g. a scanned
# third-party copy whose OCR text is too noisy for the content score).
MANUAL: dict[tuple, str] = {}


def live(url: str) -> dict | None:
    pkl = _cache_path(url, ".v5.pkl")
    return pickle.loads(pkl.read_bytes()) if pkl.is_file() else None


def candidate_pool(level: str, subject: str, kind: str, year: int, season: str,
                   live_docs: dict[str, dict]) -> list[dict]:
    """Pearson assets for the row's own series + all local archive files of the
    kind + every live document of the kind in the subject."""
    pool = []
    for hit in pearson_hits(level, subject):
        if pearson_kind(hit) != kind:
            continue
        y, s = pearson_series(hit)
        if not session_eq(y, s, year, season):
            continue
        info = fetch_pearson(hit["url"])
        if info:
            pool.append({**info, "origin": "pearson"})
    for path in local_candidates(level, subject, kind):
        info = parse_file(path)
        if info:
            pool.append({**info, "origin": "archive"})
    for path in EXTRA_DIRS:
        for f in sorted(Path(path).resolve().rglob("*.pdf")):
            info = parse_file(f, ocr_if_empty=True)
            if info:
                pool.append({**info, "origin": "third-party", "source": str(f)})
    for url, info in live_docs.items():
        pool.append({**info, "origin": "live", "source": url})
    return pool


def pick(row: dict, target: str, fixed_doc: dict, pool: list[dict],
         rivals: list[dict], scorer: RarityScorer, barcode_owner: dict,
         live_is_other_exam: bool = False) -> tuple[dict | None, str]:
    """Best candidate for the `target` side of `row`, or (None, reason)."""
    fixed_norm = scorer.vec_norm(fixed_doc["tokens"])
    rival_best = max((scorer.score(fixed_doc["tokens"], d["tokens"], fixed_norm,
                                   scorer.vec_norm(d["tokens"])) for d in rivals), default=0.0)
    fi = fixed_doc["ident"]
    fixed_units = {unit_family(u) for u in (fi.get("cover_unit"), fi.get("unit"))} - {None}
    fixed_option = option_letters(fi.get("paper"))
    best, best_score, reasons = None, 0.0, defaultdict(int)
    seen = set()
    scored = []
    for c in pool:
        ci = c["ident"]
        if ci.get("kind") != target:
            reasons["wrong kind"] += 1
            continue
        if target == "MS":
            if ms_vs_row(ci, row) is not True:
                reasons["session"] += 1
                continue
        else:
            if ident_vs_row(ci, row) is False:
                reasons["session"] += 1
                continue
            cy = ci.get("copy_year")
            if ci.get("year") is None and not (cy and row["year"] - 1 <= cy <= row["year"]):
                reasons["year unproven"] += 1
                continue
            owner = barcode_owner.get(ci.get("barcode"))
            if owner and not session_eq(owner[0], owner[1], row["year"], row["season"]):
                reasons["barcode filed elsewhere"] += 1
                continue
        cus = {unit_family(u) for u in (ci.get("cover_unit"), ci.get("unit"))} - {None}
        if fixed_units and cus and not (fixed_units & cus):
            reasons["unit"] += 1
            continue
        # The row's own unit ("Unit_2") must match the candidate's unit digit
        # (WCH12): otherwise a self-consistent pair of the WRONG unit would pass.
        row_unit = re.fullmatch(r"Unit_(\d)", str(row["paper_number"]))
        c_digit = next((m.group(1) for u in cus if u and (m := re.fullmatch(r"W[A-Z]{2}\d(\d)", u))), None)
        if row_unit and c_digit and c_digit != row_unit.group(1):
            reasons["row unit"] += 1
            continue
        # A single-unit IAL subject (code WST02) must get a WST02 document,
        # never a legacy GCE one (6684) that merely matches a wrong partner.
        if re.fullmatch(r"W[A-Z]{2}\d\d", row["code"]) and cus and row["code"] not in cus:
            reasons["subject unit"] += 1
            continue
        # An archive/live file filed under another year is another sitting,
        # whatever its content resembles (FPM "2017 Oct-Nov" = 2016 specimen).
        if c["origin"] in ("archive", "live") and str(row["year"]) not in str(c.get("source", "")):
            reasons["other year folder"] += 1
            continue
        c_option = option_letters(ci.get("paper"))
        if fixed_option and c_option and c_option != fixed_option:
            reasons["option"] += 1
            continue
        fp = frozenset(c["tokens"])
        if fp in seen:
            continue
        seen.add(fp)
        sc = scorer.score(fixed_doc["tokens"], c["tokens"], fixed_norm, scorer.vec_norm(c["tokens"]))
        scored.append((sc, c))
    for sc, c in scored:
        if sc > best_score:
            best, best_score = c, sc
    # Prefer Pearson's clean original over an archive/live copy that already
    # carries an old (possibly wrong) label trailer, when it fits as well.
    pearson = [(sc, c) for sc, c in scored if c["origin"] == "pearson"]
    if best is not None and pearson:
        p_sc, p_c = max(pearson, key=lambda t: t[0])
        if p_sc >= best_score * PEARSON_PREFERENCE:
            best, best_score = p_c, p_sc
    if best is None:
        return None, "no candidate passes identity: " + ", ".join(f"{k}={v}" for k, v in reasons.items())
    # A Pearson asset carries two independent authoritative identities (the
    # catalogue's Exam-Series tag, already required to match, and its own
    # cover, checked above); content then only has to not contradict it.
    # Anything else must win on content outright.
    need = PEARSON_NOT_CONTRADICTED if best["origin"] == "pearson" else ACCEPT_RATIO
    # The live MS is provably another exam (its unit code contradicts the QP's,
    # e.g. legacy GCE 6667 next to IAL WFM01). A Pearson asset whose catalogue
    # tag AND own cover name this unit and session is then strictly better,
    # even when a garbled QP text layer leaves content unable to vouch for it.
    if live_is_other_exam and best["origin"] == "pearson":
        need = 0.0
    if best_score < rival_best * need:
        return None, (f"best candidate {best['source']} scores {best_score:.4f}, not clearly "
                      f"above the best other-session doc {rival_best:.4f}")
    best = {**best, "score": round(best_score, 4), "rival_best": round(rival_best, 4)}
    return best, "ok"


def r2_key(url: str) -> str:
    if not url.startswith(R2_PUBLIC_BASE):
        raise ValueError(f"not an R2 public URL: {url}")
    return unquote(url[len(R2_PUBLIC_BASE):])


def install(url: str, replacement_path: str) -> str:
    """Quarantine the live object, stamp the replacement, overwrite the key."""
    sys.argv = [sys.argv[0]]  # ingest_cambridge_papers parses argv on import
    from ingest_cambridge_papers import clean_and_stamp
    key = r2_key(url)
    client = _r2()
    old = client.get_object(Bucket=R2_BUCKET, Key=key)["Body"].read()
    backup = QUARANTINE / key
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_bytes(old)
    cleaned = clean_and_stamp(Path(replacement_path).read_bytes())[0]
    if not cleaned.startswith(b"%PDF"):
        raise RuntimeError("stamped output is not a PDF")
    client.put_object(Bucket=R2_BUCKET, Key=key, Body=cleaned, ContentType="application/pdf")
    _cache_path(url, ".pdf").unlink(missing_ok=True)
    _cache_path(url, ".v5.pkl").unlink(missing_ok=True)
    return key


def resolve(r: dict, side: str, rows: list[dict], live_qp: dict, live_ms: dict,
            barcode_owner: dict, commit: bool) -> dict:
    code = r["code"]
    tag = f"{r['level']} {code} {r['year']} {r['season']:<7} P{r['paper_number']:<6} {r['verdict']:<9}"
    fixed = live_ms.get(r["markscheme_pdf_url"]) if side == "QP" else live_qp.get(r["pdf_url"])
    if fixed is None:
        print(f"{tag} {side} UNRESOLVED: the side we would match against is unreadable")
        return {**r, "fix": None, "reason": "fixed side unreadable"}
    docs_same_kind = live_qp if side == "QP" else live_ms
    pool = candidate_pool(r["level"], r["subject"], side, r["year"], r["season"], docs_same_kind)
    scorer = RarityScorer([d["tokens"] for d in (*live_qp.values(), *live_ms.values())]
                          + [c["tokens"] for c in pool if c["origin"] != "live"])
    col = "pdf_url" if side == "QP" else "markscheme_pdf_url"
    wrong_url = r[col]
    # rivals: other sessions' live docs of this kind (never this row's wrong one)
    rivals = [d for u, d in docs_same_kind.items() if u != wrong_url
              and not any(o.get(col) == u and o["paper_number"] == r["paper_number"]
                          and session_eq(o["year"], o["season"], r["year"], r["season"])
                          for o in rows)]
    other_exam = side == "MS" and r.get("unit_agree") is False
    wrong_doc = docs_same_kind.get(wrong_url)
    wrong_toks = wrong_doc["tokens"] if wrong_doc else set()

    def same_as_wrong(c: dict) -> bool:
        t = c["tokens"]
        return bool(wrong_toks) and len(t & wrong_toks) / (len(t | wrong_toks) or 1) >= 0.95

    pool = [c for c in pool if c.get("source") != wrong_url and not same_as_wrong(c)]
    manual = MANUAL.get((r["code"], r["year"], r["season"], str(r["paper_number"]), side))
    if manual:
        info = parse_file(Path(manual).resolve(), ocr_if_empty=True)
        if info and info["ident"].get("kind") == side:
            best = {**info, "origin": "hand-verified", "source": manual, "path": str(Path(manual).resolve()),
                    "score": None, "rival_best": None}
            return _accept(r, side, wrong_url, best, tag, commit)
    best, why = pick(r, side, fixed, pool,
                     rivals, scorer, barcode_owner, live_is_other_exam=other_exam)
    if best is None:
        print(f"{tag} {side} UNRESOLVED: {why}")
        return {**r, "fix": None, "reason": f"{side}: {why}"}
    return _accept(r, side, wrong_url, best, tag, commit)


def _accept(r: dict, side: str, wrong_url: str, best: dict, tag: str, commit: bool) -> dict:
    entry = {**r, "fix": {"side": side, "replace_url": wrong_url, "source": best["source"],
                          "origin": best["origin"], "score": best["score"],
                          "rival_best": best["rival_best"],
                          "ident": {k: best["ident"].get(k) for k in
                                    ("year", "season", "evidence", "pubcode", "barcode",
                                     "unit", "cover_unit", "paper")}}}
    local_path = best.get("path") or (str(_cache_path(best["source"], ".pdf"))
                                      if best["origin"] == "live" else None)
    entry["fix"]["local_path"] = local_path
    print(f"{tag} {side} <- [{best['origin']}] {best['source']} "
          f"(score {best['score']} vs other-session best {best['rival_best']}; "
          f"{best['ident'].get('evidence')})")
    if commit:
        try:
            entry["installed_key"] = install(wrong_url, local_path)
            print(f"{' ' * len(tag)} installed -> {entry['installed_key']}")
        except Exception as exc:  # noqa: BLE001
            entry["install_error"] = str(exc)
            print(f"{' ' * len(tag)} INSTALL FAILED: {exc}")
    return entry


def warm_archive(targets: list[dict]) -> None:
    """Parse every local candidate for the targeted subjects in parallel once;
    later lookups hit the pickle cache."""
    from concurrent.futures import ProcessPoolExecutor
    paths = sorted({p for r in targets for kind in ("QP", "MS")
                    for p in local_candidates(r["level"], r["subject"], kind)})
    print(f"warming {len(paths)} archive candidates ...", flush=True)
    with ProcessPoolExecutor(max_workers=10) as ex:
        list(ex.map(parse_file, paths, chunksize=8))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", help="subject code prefix")
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--accept", action="append", default=[],
                    help="hand-verified: CODE:YEAR:SEASON:PAPER:SIDE=path/to.pdf")
    ap.add_argument("--candidates-dir", action="append", default=[],
                    help="extra folder of candidate PDFs (third-party downloads)")
    args = ap.parse_args()
    load_dotenv(REPO_ROOT / ".env.local")
    EXTRA_DIRS.extend(args.candidates_dir)
    for spec in args.accept:
        key, path = spec.split("=", 1)
        code, year, season, paper, side = key.split(":")
        MANUAL[(code, int(year), season, paper, side)] = path

    results = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    by_subject = defaultdict(list)
    for r in results:
        if not args.subject or r["code"].startswith(args.subject):
            by_subject[r["code"]].append(r)

    warm_archive([r for rows in by_subject.values() for r in rows
                  if r["verdict"] in MS_SIDE | QP_SIDE])
    plan = []
    for code, rows in sorted(by_subject.items()):
        targets = [r for r in rows if r["verdict"] in MS_SIDE | QP_SIDE]
        if not targets:
            continue
        live_qp = {r["pdf_url"]: d for r in rows if r.get("pdf_url") and (d := live(r["pdf_url"]))}
        live_ms = {r["markscheme_pdf_url"]: d for r in rows
                   if r.get("markscheme_pdf_url") and (d := live(r["markscheme_pdf_url"]))}
        barcode_owner = {}
        for r in rows:
            d = live_qp.get(r.get("pdf_url"))
            bc = d and d["ident"].get("barcode")
            if bc and r["verdict"] not in QP_SIDE:
                barcode_owner[bc] = (r["year"], r["season"])

        for r in targets:
            # A unit contradiction does not say which file is the stranger
            # (2026 Jan Chemistry U2: the QP was the adapted Unit 1 paper).
            # Either side may be the stranger whatever the audit's label (the
            # 2018 FP specimen rows serve the M1 specimen QP). A QP candidate
            # must still fit the live MS strongly, so a wrong MS cannot pull
            # in a matching wrong QP.
            sides = ["QP"] if r["verdict"] in QP_SIDE else ["MS", "QP"]
            entry = None
            for side in sides:
                entry = resolve(r, side, rows, live_qp, live_ms, barcode_owner, args.commit)
                if entry.get("fix"):
                    break
            plan.append(entry)

    OUT_JSON.write_text(json.dumps(plan, indent=1, default=str), encoding="utf-8")
    fixed = sum(1 for p in plan if p.get("fix"))
    print(f"\n{'COMMITTED' if args.commit else 'DRY-RUN'}: {fixed} resolvable, "
          f"{len(plan) - fixed} unresolved -> {OUT_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
