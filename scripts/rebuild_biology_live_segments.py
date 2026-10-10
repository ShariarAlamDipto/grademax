#!/usr/bin/env python3
"""
Rebuild every live 4BI1 question + mark-scheme segment from the whole papers
and prove each pair. Staging only -- publish with publish_biology_live_segments.py.
See lib/igcse_science_rebuild.py.

    python scripts/rebuild_biology_live_segments.py
    python scripts/rebuild_biology_live_segments.py --paper 2019_jan_P2
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.igcse_science_rebuild import run  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", help="only papers whose key contains this")
    sys.exit(run("4BI1", only=parser.parse_args().paper))
