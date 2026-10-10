#!/usr/bin/env python3
"""
Audit every live IAL Pure Mathematics 1 (WMA11) question <-> mark-scheme link by content.

    python scripts/audit_physics_live_ms_linkage.py

Read-only. Report: data/analysis/live_ms_linkage/WMA11.{json,csv}.
See lib/live_ms_linkage.py for what counts as proof.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.live_ms_linkage_run import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run("WMA11"))
