"""
Render a formula sheet as real mathematical typesetting.

matplotlib's mathtext implements a LaTeX subset and needs no TeX installation,
which is the only reason this is possible on a machine with none. It gives the
things a formula sheet is judged on -- fraction bars, a radical with a proper
vinculum, integrals and sums with limits above and below, italic variables
against upright function names.

Everything is measured before it is placed. mathtext will happily typeset a line
wider than the page and let it run off the edge, so each line's rendered width is
checked and the line is set smaller if it must be; anything that still does not
fit is reported by name rather than silently cropped at the margin.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("pdf")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_agg import RendererAgg  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

PAGE_WIDTH, PAGE_HEIGHT = 595.0, 842.0
MARGIN = 34.0
TOP = 118.0
BOTTOM = 786.0

CHAPTER_SIZE = 11.5
HEADING_SIZE = 8.4
LINE_SIZE = 9.8
MIN_LINE_SIZE = 7.4
# Prose explaining a concept, as against the results themselves. Set a shade
# smaller and greyer so a reader scanning for a formula is not slowed by it.
NOTE_SIZE = 9.0

CHAPTER_LEAD = 7.0
HEADING_LEAD = 3.0
LINE_LEAD = 3.4
NOTE_LEAD = 2.8
NOTE_GAP = 3.0
GROUP_GAP = 6.0
CHAPTER_GAP = 13.0

INK = "#16191f"
MUTED = "#6b7280"
NOTE = "#3d434e"


def _tokens(text: str) -> list[str]:
    """
    Split a line into wrappable units, keeping every `$...$` span whole.

    Splitting on spaces alone would break a formula in half and leave both
    halves with an odd number of `$`, which mathtext rejects outright.
    """
    out: list[str] = []
    buffer = ""
    in_math = False
    for char in text:
        if char == "$":
            in_math = not in_math
            buffer += char
        elif char == " " and not in_math:
            if buffer:
                out.append(buffer)
                buffer = ""
        else:
            buffer += char
    if buffer:
        out.append(buffer)
    return out


def _configure() -> None:
    plt.rcParams.update({
        "mathtext.fontset": "stix",
        "font.family": "STIXGeneral",
        "pdf.fonttype": 42,
    })


class _Sheet:
    """A4 pages that text is flowed onto, in points from the top-left."""

    def __init__(self, pdf: PdfPages, title: str = "Formula Sheet") -> None:
        self.pdf = pdf
        self.title = title
        self.figure = None
        # The PDF canvas cannot measure text -- it has no renderer until it
        # draws. An Agg renderer of the same geometry measures identically and
        # never touches the output.
        self.renderer = RendererAgg(PAGE_WIDTH, PAGE_HEIGHT, 72.0)
        self.cursor = TOP
        self.first_page = True
        self.overflow: list[str] = []

    def _new_page(self) -> None:
        self._close()
        self.figure = plt.figure(figsize=(PAGE_WIDTH / 72, PAGE_HEIGHT / 72))
        self.cursor = TOP
        if self.first_page:
            self._raw(MARGIN, 74.0, self.title, 19.0, INK, weight="bold")
            self.figure.add_artist(
                plt.Line2D([MARGIN / PAGE_WIDTH, (PAGE_WIDTH - MARGIN) / PAGE_WIDTH],
                           [1 - 106.0 / PAGE_HEIGHT] * 2,
                           color="#cbd0d8", linewidth=0.8))
            self.first_page = False

    def _close(self) -> None:
        if self.figure is not None:
            self.pdf.savefig(self.figure)
            plt.close(self.figure)
            self.figure = None

    def _raw(self, x: float, y: float, text: str, size: float, colour: str,
             weight: str = "normal"):
        return self.figure.text(x / PAGE_WIDTH, 1 - y / PAGE_HEIGHT, text,
                                fontsize=size, color=colour, va="top", ha="left",
                                fontweight=weight)

    def _measure(self, artist) -> tuple[float, float]:
        """(width, height) of a placed artist, in points."""
        box = artist.get_window_extent(self.renderer)
        scale = 72.0 / self.renderer.dpi
        return box.width * scale, box.height * scale

    def place(self, text: str, size: float, colour: str, lead: float,
              weight: str = "normal", label: str = "") -> None:
        """Put one line down, shrinking it if it is too wide, paging if it must."""
        if self.figure is None:
            self._new_page()

        artist = self._raw(MARGIN, self.cursor, text, size, colour, weight)
        width, height = self._measure(artist)

        limit = PAGE_WIDTH - 2 * MARGIN
        while width > limit and size > MIN_LINE_SIZE:
            artist.remove()
            size -= 0.3
            artist = self._raw(MARGIN, self.cursor, text, size, colour, weight)
            width, height = self._measure(artist)
        if width > limit:
            self.overflow.append(label or text[:60])

        if self.cursor + height > BOTTOM:
            artist.remove()
            self._new_page()
            artist = self._raw(MARGIN, self.cursor, text, size, colour, weight)
            _, height = self._measure(artist)

        self.cursor += height + lead

    def measure_width(self, text: str, size: float) -> float:
        """How wide this line would be, without committing it to the page."""
        if self.figure is None:
            self._new_page()
        artist = self._raw(MARGIN, self.cursor, text, size, INK)
        width, _height = self._measure(artist)
        artist.remove()
        return width

    def place_wrapped(self, text: str, size: float, colour: str,
                      lead: float) -> None:
        """
        Put a paragraph down, broken at word boundaries to fit the column.

        Prose has to WRAP where a formula only has to shrink. The existing
        shrink-to-fit is right for a line of results -- setting it smaller keeps
        it on one line, which is how a formula wants to be read -- but applied to
        a sentence it either ran off the page or reduced it to unreadable type.
        Nine of the summary lines did exactly that.

        A `$...$` span is atomic: breaking inside one would split a formula
        across two lines and, worse, leave each half with unbalanced delimiters,
        which mathtext then refuses to parse at all.
        """
        limit = PAGE_WIDTH - 2 * MARGIN
        line = ""
        for token in _tokens(text):
            trial = f"{line} {token}".strip()
            if line and self.measure_width(trial, size) > limit:
                self.place(line, size, colour, lead)
                line = token
            else:
                line = trial
        if line:
            self.place(line, size, colour, lead)

    def gap(self, amount: float) -> None:
        if self.figure is not None:
            self.cursor += amount

    def room_for(self, points: float) -> bool:
        return self.figure is not None and self.cursor + points <= BOTTOM

    def finish(self) -> list[str]:
        self._close()
        return self.overflow


def render(blocks: list[dict], path, title: str = "Formula Sheet") -> list[str]:
    """
    Write the sheet to `path`. Returns any lines that would not fit the column.

    A group is kept whole: if its heading and first line cannot both fit the
    remaining space, the group starts the next page instead, so no heading is
    left stranded at the foot of a sheet.

    A block may carry `notes` -- prose explaining the concept, set before the
    results and in a quieter style. Blocks without them are unaffected, which is
    what keeps the Further Pure sheet identical.
    """
    _configure()
    with PdfPages(path) as pdf:
        sheet = _Sheet(pdf, title)
        for block in blocks:
            notes = block.get("notes") or ()
            if block["chapter"]:
                sheet.gap(CHAPTER_GAP)
                if not sheet.room_for(60.0):
                    sheet._new_page()
                sheet.place(block["chapter"], CHAPTER_SIZE, INK, CHAPTER_LEAD,
                            weight="bold", label=block["chapter"])
            elif not sheet.room_for(46.0):
                sheet._new_page()
            else:
                sheet.gap(GROUP_GAP)

            sheet.place(block["heading"], HEADING_SIZE, MUTED, HEADING_LEAD,
                        label=block["heading"])
            for line in notes:
                sheet.place_wrapped(line, NOTE_SIZE, NOTE, NOTE_LEAD)
            if notes and block["lines"]:
                sheet.gap(NOTE_GAP)
            for line in block["lines"]:
                sheet.place(line, LINE_SIZE, INK, LINE_LEAD, label=line[:60])
        return sheet.finish()
