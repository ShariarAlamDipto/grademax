"""
Put the covers and the "Acing Mathematics with Shariar Alam Dipto" watermark on
the IGCSE Mathematics B (4MB1) 2018-2026 yearwise books, then verify every
interior sheet carries it and neither cover does.

    python -X utf8 scripts/finalize_mathsb_yearwise_all.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.yearwise_all_finish import finish  # noqa: E402

if __name__ == "__main__":
    sys.exit(finish("igcse_mathsb", "4MB1", "Mathematics B"))
