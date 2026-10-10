"""Run the linkage audit for one book and print / save the result."""

from __future__ import annotations

import json
from collections import Counter

from lib.yearwise_all_catalogue import WORK, units_of
from lib.yearwise_linkage import as_json, run_unit, save_cache


def run_book(book: str, legacy_specs: set[str], verbose: bool = False,
             signal: str = "numbers", settled: dict | None = None) -> int:
    cand_file = WORK / "candidates" / f"{book}.json"
    if not cand_file.exists():
        raise SystemExit(f"{cand_file} missing -- run collect_yearwise_all_sources.py --book {book}")
    candidates = json.loads(cand_file.read_text(encoding="utf-8"))

    results, tally = [], Counter()
    for unit in units_of(book):
        sittings = run_unit(unit, candidates.get(unit.key, []), legacy_specs, signal, settled)
        save_cache()
        results.append(as_json(unit, sittings))
        print(f"\n== {unit.label} ({unit.key}) ==")
        for s in sittings:
            tally[s.verdict] += 1
            p = s.pairing
            pair_txt = (f"own {p['own']:.2f} / next {p['runner_up']:.2f}" if p else "-")
            print(f"  {s.label:13} {s.verdict:7} {s.spec or '-':6} "
                  f"{(s.qp.item_code if s.qp else '-') or '?':9} "
                  f"{(s.ms.pub_session if s.ms else '-') or '?':5} {pair_txt:22} {s.per_question}")
            for why in s.problems:
                print(f"      ! {why}")
            if verbose or s.verdict != "LINKED":
                for why in s.rejected:
                    print(f"      - rejected {why}")

    out = WORK / "linkage" / f"{book}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"\n{book}: {dict(tally)}  -> {out.relative_to(WORK.parent.parent)}")
    return 1 if tally["FAIL"] else 0
