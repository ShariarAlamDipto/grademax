"""
Check the finished Pure Mathematics P4 (WMA14) yearwise workbook against its source papers.

The checks live in `lib/yearwise_workbook_audit.py`, shared with the other
units; read its module header for what each one proves and why the obvious
version of it does not work.

    python scripts/audit_p4_yearwise_workbook.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_workbook_audit import Volumes, audit  # noqa: E402

P4 = Volumes(slug="p4", token="P4", name="Pure Mathematics P4")


def main() -> int:
    return audit(P4)


if __name__ == "__main__":
    sys.exit(main())
