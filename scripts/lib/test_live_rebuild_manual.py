"""
Checks for the hand-cut / recovery helpers added for the withheld Maths B
schemes (2026-10-09). No pytest in the venv: run this file directly.

    python scripts/lib/test_live_rebuild_manual.py

They read real staged sources, so they also guard the measured facts the
helpers were built on.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # noqa: E402

from lib import live_rebuild_common as common  # noqa: E402
from lib.ms_hand_cut import holds_only_header, label_cuts, regions  # noqa: E402

SOURCES = Path(__file__).resolve().parents[2] / "data/analysis/live_rebuild/4MB1/sources"


def _region(**kw):
    return SimpleNamespace(**kw)


def test_decoded_copy_reads_every_fence() -> None:
    copy = common.decoded_copy(SOURCES / "2015_jan_P1R_qp.pdf", 29)
    with fitz.open(copy) as doc:
        text = " ".join(" ".join(p.get_text().split()) for p in doc)
    fences = re.findall(r"Total for Question (\d+) is (\d+)", text)
    assert [int(q) for q, _ in fences] == list(range(1, 30))
    assert sum(int(m) for _, m in fences) == 100


def test_decoded_words_keep_shifted_digits_and_stamps() -> None:
    with fitz.open(SOURCES / "2015_jan_P1R_qp.pdf") as doc:
        words = [w for _, w in common._decoded_words(doc[2], 29)]
    assert "Question" in words and "4" in words      # digits were control codes
    assert "GradeMax" in words and "2015" in words   # our stamp line left alone


def test_display_regions_follow_rotation() -> None:
    # 2020 Jan P1 scheme pages are stored portrait with /Rotate 90: a displayed
    # horizontal band must come back as a full-height vertical strip.
    seg = SimpleNamespace(Region=_region)
    ms = SOURCES / "2020_jan_P1_ms.pdf"
    (band,) = common.display_regions(seg, ms, [[6, 82, 193.5]])
    with fitz.open(ms) as doc:
        page = doc[6]
        assert page.rotation in (90, 270)
        assert abs((band.bottom - band.top) - page.cropbox.height) < 1.0
        assert abs((band.right - band.left) - (193.5 - 82)) < 1.0


def test_display_regions_identity_when_upright() -> None:
    seg = SimpleNamespace(Region=_region)
    (band,) = common.display_regions(seg, SOURCES / "2019_may-jun_P1_ms.pdf", [[10, 484.5, 500]])
    assert (round(band.top, 1), round(band.bottom, 1)) == (484.5, 500.0)


def test_header_only_strip_is_detected() -> None:
    with fitz.open(SOURCES / "2025_may-jun_P1_ms.pdf") as doc:
        assert holds_only_header(doc[5], 30.0, 92.3)       # bare "Question | Working ..." row
        assert not holds_only_header(doc[4], 220.7, 318.3)  # question 2's own rows


def test_regions_stop_at_next_question_rule() -> None:
    cut = regions(SOURCES / "2025_may-jun_P1_ms.pdf", (4, 221.7), (4, 319.3))
    assert cut == [[4, 220.7, 318.3]]


def test_label_cuts_take_the_row_line_above_a_centred_label() -> None:
    # 2019 Jan P1 centres "4" in a two-line row; the cut must start at the
    # row's top rule, above the label, so its first working line is kept.
    cuts = label_cuts(SOURCES / "2019_jan_P1_ms.pdf",
                      [(3, 5, 180.4), (4, 5, 244.8), (5, 5, 305.2)])
    start_4 = cuts[4][0][1]
    assert start_4 < 244.8 - 8.0
    assert cuts[3][0][2] == start_4


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS {test.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc!r}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
