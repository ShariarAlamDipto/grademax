#!/usr/bin/env python3
"""
Audit every live IGCSE Human Biology (4HB1) question <-> mark-scheme link by content.

    python scripts/audit_humanbio_live_ms_linkage.py

Read-only. Report: data/analysis/live_ms_linkage/4HB1.{json,csv}.
See lib/live_ms_linkage.py for what counts as proof.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_ms_linkage_run import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run("4HB1"))
