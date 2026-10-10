"""
Check the finished Statistics S1 (WST01) yearwise workbook against its source papers.

The checks live in `lib/yearwise_workbook_audit.py`, shared with the other
units; read its module header for what each one proves and why the obvious
version of it does not work.

    python scripts/audit_s1_yearwise_workbook.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_workbook_audit import Volumes, audit  # noqa: E402

S1 = Volumes(slug="s1", token="S1", name="Statistics S1")


def main() -> int:
    return audit(S1)


if __name__ == "__main__":
    sys.exit(main())
