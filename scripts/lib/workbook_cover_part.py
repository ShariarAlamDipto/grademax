"""
Turn the one-volume cover artwork into a Part 1 / Part 2 cover.

The book is split for binding, not redesigned, so the cover is not redrawn --
the supplied artwork is copied through untouched and ONE string is added to the
front: the part label, running on from the line that already reads CHAPTERWISE
WORKBOOK, in that line's own face, size, colour and rhythm.

WHY THIS IS NOT `insert_text`
-----------------------------
Three things about that line are not what a naive redraw would produce, and all
three were measured off the artwork rather than guessed:

1. IT IS DRAWN TWICE, AND ONLY ONE COPY IS INK. A black copy sits 2.8pt below
   the white one and never reaches the page: the design tool draws it as the
   luminosity source of a soft-masked drop shadow, so it appears in the text
   layer but not in the render. Copying BOTH -- the obvious reading of what
   `get_text` returns -- paints a hard black ghost under the label that the
   words in front of it do not have. Checked by rendering the artwork at 420dpi
   before trusting it, and checked again on the finished cover by `verify`,
   which compares the label's darkest pixel against the title's.

2. IT IS LETTER-SPACED, AND NOT EVENLY. The design tool quantised every advance
   onto a grid: each step is `grid * (floor(natural/grid + tracking) + phase)`,
   so two characters of different natural width can take the SAME step. Setting
   the label at the font's natural advances makes it visibly tighter than the
   words in front of it; setting it at a flat average makes it drift. The three
   constants are recovered from the artwork itself by `_Rhythm.fit`, which then
   refuses to run unless the model reproduces every observed step exactly.

3. THE FONT IS SUBSET TO THE GLYPHS THE ARTWORK USES. Saira Condensed SemiBold
   is embedded twice on the front cover and neither copy carries a digit or a
   hyphen -- so "PART 1" cannot be set from the file's own resources at all.
   The full face is vendored beside this module (SIL Open Font License, see
   fonts/OFL.txt); its advance widths were checked against both embedded subsets
   and agree to twelve digits, so it is the same cut, not a lookalike.

USAGE
-----
    covers = part_cover(COVER, 1, out_dir)   # -> Path to a 2-page cover PDF

The result is the same shape as the input -- page 0 front, page 1 back -- so it
drops straight into workbook_finish.assemble in place of the original.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import fitz
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_FILE = FONT_DIR / "SairaCondensed-SemiBold.ttf"

# The words the part label runs on from. Matched on the front cover only.
TITLE_TEXT = "CHAPTERWISE WORKBOOK"

# What gets appended. The separator is a hyphen rather than the cover's usual
# middle dot because that is how the label reads on the spine label and in the
# print order: "Chapterwise Workbook - Part 1".
LABEL = " - PART {part}"

# How far the model's reproduction of an observed advance may drift before the
# calibration is rejected. The steps in the artwork are exact to 4 decimals.
FIT_TOLERANCE = 0.002

# Two advances this close apart are the same advance. Characters set at the same
# step read back from the PDF a hundredth of a point apart -- the positions are
# accumulated from single-precision offsets in the content stream -- and without
# clustering, that noise is picked up as the grid and the fit collapses.
SAME_STEP = 0.02


@dataclass(frozen=True)
class _Rhythm:
    """The quantised letter-spacing the artwork was set with."""

    grid: float
    phase: float
    tracking: float

    def step(self, natural: float) -> float:
        """The advance the design tool would have used for this character."""
        return self.grid * (math.floor(natural / self.grid + self.tracking) + self.phase)

    @classmethod
    def fit(cls, steps: list[float], naturals: list[float]) -> "_Rhythm":
        """
        Recover grid, phase and tracking from one line of the artwork.

        `grid` is the smallest gap between two distinct observed advances --
        every step is a whole number of grid units plus a constant. `phase` is
        that constant. `tracking` is then bounded by each character
        independently (the floor must land on the observed unit count), and the
        intersection of those bounds is taken at its midpoint so the model is as
        far as possible from the next character that would tip it.
        """
        levels: list[list[float]] = []
        for step in sorted(steps):
            if levels and step - levels[-1][0] <= SAME_STEP:
                levels[-1].append(step)
            else:
                levels.append([step])
        unique = [sum(level) / len(level) for level in levels]
        gaps = [b - a for a, b in zip(unique, unique[1:])]
        if not gaps:
            raise ValueError("cover title has a single advance; cannot fit its rhythm")
        grid = min(gaps)

        # Phases are read against the first step so a value sitting either side
        # of the wrap does not average to the middle of the grid cell.
        base = (steps[0] / grid) % 1.0
        phases = [base + (((s / grid) - base + 0.5) % 1.0) - 0.5 for s in steps]
        phase = sum(phases) / len(phases)
        if max(abs(p - phase) for p in phases) > SAME_STEP / grid:
            raise ValueError("cover title advances do not sit on one grid; "
                             "the artwork was set differently from what this expects")

        low, high = -math.inf, math.inf
        for step, natural in zip(steps, naturals):
            units = round(step / grid - phase)
            low = max(low, units - natural / grid)
            high = min(high, units + 1 - natural / grid)
        if low >= high:
            raise ValueError("no single tracking value explains the cover title")
        rhythm = cls(grid=grid, phase=phase, tracking=(low + high) / 2)

        for step, natural in zip(steps, naturals):
            if abs(rhythm.step(natural) - step) > FIT_TOLERANCE:
                raise ValueError(f"fitted rhythm reproduces {step:.4f} as "
                                 f"{rhythm.step(natural):.4f}; refusing to guess")
        return rhythm


@dataclass(frozen=True)
class _TitleRun:
    """One drawn copy of the title line: where it sits and what colour it is."""

    origin_x: float
    baseline: float
    size: float
    colour: tuple[float, float, float]
    end_x: float


class _Face:
    """Advance widths from the vendored font, in points at a given size."""

    def __init__(self, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"missing cover font: {path}")
        self.path = path
        font = TTFont(path)
        self._upm = font["head"].unitsPerEm
        self._cmap = font.getBestCmap()
        self._hmtx = font["hmtx"]
        font.close()

    def advance(self, char: str, size: float) -> float:
        glyph = self._cmap.get(ord(char))
        if glyph is None:
            raise ValueError(f"{self.path.name} has no glyph for {char!r}")
        return self._hmtx[glyph][0] / self._upm * size


def _rgb(colour: int) -> tuple[float, float, float]:
    return ((colour >> 16 & 0xFF) / 255, (colour >> 8 & 0xFF) / 255, (colour & 0xFF) / 255)


def _title_runs(page: fitz.Page) -> list[_TitleRun]:
    """
    Every drawn copy of the title line, in the order the page draws them.

    The last one is the visible face; anything before it is the shadow's mask
    source. See the module docstring for how that was established.
    """
    runs: list[_TitleRun] = []
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                chars = span["chars"]
                if "".join(c["c"] for c in chars) != TITLE_TEXT:
                    continue
                runs.append(_TitleRun(origin_x=chars[0]["origin"][0],
                                      baseline=chars[0]["origin"][1],
                                      size=span["size"],
                                      colour=_rgb(span["color"]),
                                      end_x=span["bbox"][2]))
    if not runs:
        raise ValueError(f"front cover has no {TITLE_TEXT!r} line to run on from")
    return runs


def _observed(page: fitz.Page) -> tuple[list[float], list[float], float]:
    """The title's per-character advances, its natural ones, and its size."""
    face = _Face(FONT_FILE)
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                chars = span["chars"]
                if "".join(c["c"] for c in chars) != TITLE_TEXT:
                    continue
                steps = [chars[i + 1]["origin"][0] - chars[i]["origin"][0]
                         for i in range(len(chars) - 1)]
                naturals = [face.advance(c["c"], span["size"]) for c in chars[:-1]]
                return steps, naturals, span["size"]
    raise ValueError(f"front cover has no {TITLE_TEXT!r} line to measure")


def part_cover(cover_path: Path, part: int, out_dir: Path,
               label: str | None = None) -> Path:
    """
    Write a copy of the cover artwork whose front carries the part label.

    Nothing else on either page is touched: the file is copied object for
    object, and the label is drawn on top of the front page in the visible
    title's own face, size, colour, baseline and letter-spacing.
    """
    label = label or LABEL.format(part=part)
    face = _Face(FONT_FILE)

    doc = fitz.open(cover_path)
    if doc.page_count != 2:
        raise ValueError(f"cover must be 2 pages (front, back), got {doc.page_count}")
    front = doc[0]

    steps, naturals, size = _observed(front)
    rhythm = _Rhythm.fit(steps, naturals)

    # The title's own last character has no observed step -- it is the end of
    # the line -- so the label starts one modelled advance past it.
    run = _title_runs(front)[-1]
    tail = TITLE_TEXT[-1]
    start = run.end_x - face.advance(tail, size) + rhythm.step(face.advance(tail, size))

    x = start
    for char in label:
        front.insert_text((x, run.baseline), char, fontname="sairasb",
                          fontfile=str(FONT_FILE), fontsize=run.size,
                          color=run.colour)
        x += rhythm.step(face.advance(char, run.size))

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{cover_path.stem}_Part{part}.pdf"
    doc.save(out, deflate=True)
    doc.close()
    return out


# How much darker than the title's own darkest pixel the label's band may be
# before it is reported. A hard black ghost is 30-plus levels darker; the
# background gradient across 90pt of cover is worth two or three.
GHOST_TOLERANCE = 10
PROOF_DPI = 200


def _row_chars(page: fitz.Page, baseline: float, from_x: float) -> list[dict]:
    """
    Characters sitting on one baseline at or past `from_x`, in reading order.

    Selected by position rather than by content: matching on the label's own
    characters instead would pick up every 'A', 'R' and 'T' on the cover, and
    matching on the span would miss it entirely -- a run drawn character by
    character does not come back as one span. The 0.5pt window is well inside
    the 2.8pt that separates the visible face from its shadow.
    """
    found: list[dict] = []
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                for char in span["chars"]:
                    if abs(char["origin"][1] - baseline) <= 0.5 and \
                            char["origin"][0] >= from_x - 0.5:
                        found.append({"c": char["c"], "bbox": char["bbox"],
                                      "origin": char["origin"],
                                      "font": span["font"], "size": span["size"]})
    return sorted(found, key=lambda c: c["origin"][0])


def _darkest(page: fitz.Page, box: fitz.Rect) -> int:
    """The darkest pixel in a region of the rendered page, 0-255."""
    pixmap = page.get_pixmap(clip=box, dpi=PROOF_DPI, colorspace=fitz.csGRAY)
    return min(pixmap.samples)


def verify(cover_path: Path, part: int, label: str | None = None) -> list[str]:
    """
    Read a finished part cover back. Returns problems; empty means it is right.

    Checks what actually matters on the press: the label is on the front and
    nowhere else, it is set in the title's face at the title's size, it sits on
    the title's baseline, and -- rendered, not merely parsed -- it carries no
    ink the title does not carry. The last one is the check that would have
    caught the black ghost described in the module docstring.
    """
    label = label or LABEL.format(part=part)
    problems: list[str] = []
    doc = fitz.open(cover_path)
    front = doc[0]

    visible = _title_runs(front)[-1]

    # The whole line, read off the page a character at a time. A run drawn
    # character by character does not come back as one span, so `get_text()`
    # alone can report the title and the label as separate lines even when they
    # are set on the same baseline.
    line = "".join(c["c"] for c in _row_chars(front, visible.baseline, visible.origin_x))
    if line != TITLE_TEXT + label:
        problems.append(f"front cover title line reads {line!r}, "
                        f"expected {TITLE_TEXT + label!r}")

    chars = _row_chars(front, visible.baseline, visible.end_x)
    for char in chars:
        if "SairaCondensed" not in char["font"]:
            problems.append(f"label character {char['c']!r} is set in "
                            f"{char['font']}, not the title's face")
            break
        if abs(char["size"] - visible.size) > 0.05:
            problems.append(f"label is set at {char['size']:.2f}pt, "
                            f"the title at {visible.size:.2f}pt")
            break

    if chars:
        top = min(c["bbox"][1] for c in chars)
        bottom = max(c["bbox"][3] for c in chars)
        left = min(c["bbox"][0] for c in chars)
        right = max(c["bbox"][2] for c in chars)
        title_box = fitz.Rect(visible.origin_x, top, visible.end_x, bottom)
        label_box = fitz.Rect(left, top, right, bottom)
        title_dark, label_dark = _darkest(front, title_box), _darkest(front, label_box)
        if label_dark < title_dark - GHOST_TOLERANCE:
            problems.append(f"label band renders down to {label_dark}/255 against "
                            f"the title's {title_dark}/255 -- something is painting "
                            f"ink the title does not have (a shadow copy?)")

    if label.strip() in " ".join(doc[1].get_text().split()).replace("  ", " "):
        problems.append("part label leaked onto the back cover")

    doc.close()
    return problems
