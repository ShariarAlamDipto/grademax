#!/usr/bin/env python3
"""
Re-cut the IGCSE Economics (4EC1) mark schemes by page range, then point the
live questions at them. See lib/commerce_ms_fix.py for the rule and checks.

    python -X utf8 scripts/fix_economics_markschemes.py recut            # dry run
    python -X utf8 scripts/fix_economics_markschemes.py recut --write
    python -X utf8 scripts/fix_economics_markschemes.py publish          # dry run
    python -X utf8 scripts/fix_economics_markschemes.py publish --execute
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.commerce_ms_fix import publish, recut  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["recut", "publish"])
    ap.add_argument("--write", action="store_true", help="recut: write the cuts")
    ap.add_argument("--execute", action="store_true", help="publish: write to R2 and the database")
    args = ap.parse_args()
    sys.exit(recut("4EC1", write=args.write) if args.step == "recut" else publish("4EC1", execute=args.execute))
