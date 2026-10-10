"""
Re-typeset the IGCSE Accounting "Chapterwise Formats" booklet.

WHY
---
The draft booklet is 18 separate topic documents printed by three or four
different generators and then stapled together in one PDF. That leaves three
faults the teacher asked to have fixed:

  1. every topic heading is a different typeface, case and alignment, several
     of them hand-patched with a white box and a pasted "Topic N" in a font
     that matches nothing else on the page;
  2. worked examples split across the page break -- the caption "Katrina --
     Equipment Account" sits at the foot of one page and the T-account it
     names starts at the top of the next;
  3. there is no logo on the pages.

Fault 2 is the one that dictates the approach. You cannot un-split a table by
drawing on top of a finished PDF: the content has to be re-flowed. So this
module slices each source page into content bands, groups the bands that must
travel together (a shaded worked-example box, a table and its caption, a
heading and the block beneath it), and re-flows those groups onto fresh pages.

Bands are re-placed with show_pdf_page + clip, never re-typeset, so the vector
text, the table rules and the fills come through byte-identical to the draft.
Nothing is retyped and nothing can be silently dropped.

The diagonal "Azwad Hossain Tahmid" watermark has to come out before slicing:
it is a rotated text object lying across the whole page, so any band that
crosses it inherits a meaningless diagonal fragment. It is stripped from the
content stream -- rotated text is the watermark and nothing else in this
corpus. It ran on two topics out of eighteen; the badge now stamped on every
page carries the same attribution consistently.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import fitz

A4 = (595.2756, 841.8898)

# Output page furniture. The logo sits in the top margin, so the content area
# has to start below it rather than at the source's y=51. Each topic's content
# is centred on the sheet rather than set to a fixed left margin: the four
# generators used four different measures, and centring makes them agree.
HEADER_H = 52.0          # logo band
FOOTER_H = 34.0          # page number / topic name
CONTENT_TOP = HEADER_H
CONTENT_BOT = A4[1] - FOOTER_H
CONTENT_H = CONTENT_BOT - CONTENT_TOP

# House colours, sampled from the draft itself.
NAVY = (0.102, 0.212, 0.365)     # #1A365D  topic headings
BLUE = (0.169, 0.424, 0.690)     # #2B6CB0  section headings, table headers
GREY = (0.45, 0.45, 0.45)

# Band detection. Two elements belong to the same row if their vertical
# extents are closer than ROW_GAP; two rows belong to the same atom if they
# are closer than ATOM_GAP. Measured against the draft: body leading is 12-17pt
# with ~6pt paragraph spacing, so 5.0 separates paragraphs without chopping
# a wrapped sentence in half.
ROW_GAP = 1.0
ATOM_GAP = 5.0

# A filled rectangle this wide and tall is a container (a "Worked Example" or
# "Contents" panel), not a rule or a table cell.
CONTAINER_MIN_W = 280.0
CONTAINER_MIN_H = 26.0

# Two of the generators wrap the whole text frame of every page in a thin
# ruled card. It is page decoration, but geometrically it is a panel running
# from the first line to the last, so it welds every block on the page into one
# unsplittable lump and the topic comes through the re-flow untouched. Measured
# across the draft, real panels top out at 0.81 of the page height and these
# frames start at 0.87, so the cut is unambiguous.
PAGE_FRAME_H = 0.84
PAGE_FRAME_W = 0.70

# Content that reaches this close to the source page edge is assumed to be
# a block the generator cut in half at the page break.
EDGE_TOL = 12.0

# Ink at or above this level on every channel is invisible on paper. Two of the
# generators lay a #FDFDFD tint over the whole page, and the hand-patched topic
# headings are white boxes painted over the old title; neither is content.
WHITE_FLOOR = 0.95

# The strip at the foot of a source page that holds the running foot. Real
# content never reaches below y = H - 44 in this corpus (lowest measured: 797.3
# against a page height of 841.9), while every generator's footer starts below
# it. Some footers extract as broken glyph runs the text rules cannot match, so
# the geometric cut is the one that has to be reliable.
FOOTER_BAND = 44.0

# One page is a hand-designed full-bleed card (a navy banner over two formula
# panels on a tinted ground) rather than a run of flowing blocks. Re-flowing it
# would take the design apart, so it is passed through whole.
PASSTHROUGH_PAGES = {28}


# --------------------------------------------------------------------------
# 1. content-stream cleaning: drop rotated text (the watermark)
# --------------------------------------------------------------------------

_TOKEN = re.compile(
    rb"""
      (?P<str>\((?:\\.|[^()\\])*\))        # literal string (no nested parens in this corpus)
    | (?P<hex><[0-9A-Fa-f\s]*>)            # hex string
    | (?P<dict_open><<) | (?P<dict_close>>>)
    | (?P<name>/[^\s/\[\]<>(){}%]*)
    | (?P<num>[+-]?(?:\d+\.\d*|\.\d+|\d+))
    | (?P<delim>[\[\]{}])
    | (?P<op>[A-Za-z'"*][A-Za-z0-9'"*]*)
    | (?P<comment>%[^\r\n]*)
    """,
    re.VERBOSE,
)


def _mat_mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + b * C, a * B + b * D,
            c * A + d * C, c * B + d * D,
            e * A + f * C + E, e * B + f * D + F)


def strip_rotated_text(data: bytes) -> bytes:
    """Remove every BT..ET block drawn under a rotated matrix.

    In this booklet the only rotated text is the diagonal watermark; all body
    text, table text and footers are axis-aligned. Everything else in the
    stream -- fills, rules, XObjects -- is passed through untouched.
    """
    out = bytearray()
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    stack: list[tuple] = []

    in_text = False
    buf = bytearray()
    text_rotated = False
    operands: list[bytes] = []

    pos = 0
    for m in _TOKEN.finditer(data):
        if m.start() > pos:
            gap = data[pos:m.start()]
            (buf if in_text else out).extend(gap)
        pos = m.end()
        tok = m.group(0)
        kind = m.lastgroup

        if kind != "op":
            operands.append(tok)
            (buf if in_text else out).extend(tok)
            continue

        op = tok
        if in_text:
            buf.extend(tok)
            if op == b"Tm" and len(operands) >= 6:
                try:
                    tm = tuple(float(x) for x in operands[-6:])
                except ValueError:
                    tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                comb = _mat_mul(tm, ctm)
                if abs(comb[1]) > 0.01 or abs(comb[2]) > 0.01:
                    text_rotated = True
            if op == b"ET":
                if not text_rotated:
                    out.extend(buf)
                buf = bytearray()
                in_text = False
                text_rotated = False
            operands = []
            continue

        if op == b"BT":
            # decide from the CTM alone first; a Tm inside may refine it
            in_text = True
            text_rotated = abs(ctm[1]) > 0.01 or abs(ctm[2]) > 0.01
            buf = bytearray(tok)
            operands = []
            continue

        out.extend(tok)
        if op == b"q":
            stack.append(ctm)
        elif op == b"Q":
            ctm = stack.pop() if stack else (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        elif op == b"cm" and len(operands) >= 6:
            try:
                ctm = _mat_mul(tuple(float(x) for x in operands[-6:]), ctm)
            except ValueError:
                pass
        operands = []

    if pos < len(data):
        (buf if in_text else out).extend(data[pos:])
    if in_text and not text_rotated:
        out.extend(buf)
    return bytes(out)


def erase_text(page: fitz.Page, band: fitz.Rect) -> None:
    """Delete the text inside a band for real, not merely hide it.

    show_pdf_page's ``clip`` sets a bounding box on the form it creates: the
    band outside it stops being drawn, but the text objects are still in the
    stream and still come back from get_text and from a reader's search and
    copy. The old topic headings and the four generators' running feet are
    dropped from this book, so they have to be genuinely removed -- otherwise
    every re-flowed page carries an invisible copy of the furniture it
    replaced. Line art and images are left alone; only glyphs go.
    """
    annot = page.add_redact_annot(band)
    annot.set_colors(stroke=None, fill=None)
    annot.update()
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                          text=fitz.PDF_REDACT_TEXT_REMOVE)


# A hand-applied white-out: a small form XObject dropped over something the
# teacher wanted gone, drawn from its own tiny content stream. Most sit in the
# heading or footer bands this rebuild discards anyway, so they are left where
# they are; the one on the full-bleed formula page is not, and shows up as a
# white smear across the banner.
_PATCH_STREAM = re.compile(
    rb"^[\sQq]*1 0 0 1 [\d.]+ [\d.]+ cm\s*/\w+ Do\s*[\sQq]*$")


def drop_patch_streams(doc: fitz.Document, pages: set[int]) -> int:
    """Undo the hand-applied white-outs on the given pages."""
    dropped = 0
    for pno in pages:
        page = doc[pno]
        keep = [x for x in page.get_contents()
                if not _PATCH_STREAM.match(doc.xref_stream(x))]
        if len(keep) == len(page.get_contents()):
            continue
        dropped += len(page.get_contents()) - len(keep)
        doc.xref_set_key(page.xref, "Contents",
                         "[" + " ".join(f"{x} 0 R" for x in keep) + "]")
    return dropped


def clean_source(src_path: str, first_pages: set[int] | None = None) -> fitz.Document:
    """Open the draft and return a copy ready to slice.

    Removes the diagonal watermark, the running feet, and -- on the first page
    of each topic -- the old heading that the uniform one replaces.
    """
    doc = fitz.open(src_path)
    for page in doc:
        data = page.read_contents()
        cleaned = strip_rotated_text(data)
        if cleaned == data:
            continue
        xref = doc.get_new_xref()
        doc.update_object(xref, "<<>>")
        doc.update_stream(xref, cleaned, compress=True)
        doc.xref_set_key(page.xref, "Contents", f"{xref} 0 R")

    # Measured before the text goes, and kept on the document: once the old
    # title has been redacted heading_cut has nothing left to recognise, but
    # the banner and rule it was set in are line art and still there, so the
    # slicer still needs to know where the heading ended.
    drop_patch_streams(doc, PASSTHROUGH_PAGES)

    first_pages = first_pages or set()
    cuts = {n: heading_cut(doc[n]) for n in first_pages}
    doc.heading_cuts = cuts

    for page in doc:
        W, H = page.rect.width, page.rect.height
        bands = [fitz.Rect(0, furniture_cut(page) + 0.5, W, H)]
        cut = cuts.get(page.number, 0.0)
        if cut > 0:
            bands.append(fitz.Rect(0, 0, W, cut))
        for band in bands:
            if band.height > 0.5:
                erase_text(page, band)
    return doc


# --------------------------------------------------------------------------
# 2. band extraction
# --------------------------------------------------------------------------

@dataclass
class Elem:
    """One drawn thing on a source page."""
    x0: float
    y0: float
    x1: float
    y1: float
    kind: str        # 'text' | 'fill' | 'stroke' | 'image'
    container: bool = False
    size: float = 0.0
    bold: bool = False


@dataclass
class Row:
    """Elements that share a horizontal line of the page."""
    y0: float
    y1: float
    x0: float
    x1: float
    kinds: set = field(default_factory=set)
    size: float = 0.0
    bold: bool = False


@dataclass
class Slice:
    """A vertical band of one source page."""
    page: int
    y0: float
    y1: float


@dataclass
class Group:
    """Atoms that must be printed on one page, with their internal spacing.

    ``slices`` holds (atom, offset-from-group-top) pairs, so a group assembled
    from two halves of a split panel reproduces the panel with the page break
    taken out of the middle of it.
    """
    slices: list = field(default_factory=list)
    lead_gap: float = 0.0     # whitespace to preserve above the group
    total: float = 0.0        # laid-out height
    tag: str = ""
    passthrough: bool = False


def _expand_even_odd(path: dict) -> list:
    """Turn an even-odd pair of nested rectangles into the bands it paints.

    Every generator in this booklet draws a border, a rule and a panel's accent
    bar the same way: an outer rectangle, an inner rectangle, and an even-odd
    fill, so what is actually inked is the ring between them. Read as two solid
    rectangles it becomes a block of colour reaching from the top of the page to
    the bottom of a panel -- which then drags a hundred points of nothing into
    the re-flow. All 208 multi-rectangle paths in the draft are this shape.
    """
    if not path.get("even_odd"):
        return path["items"]
    rects = [it[1] for it in path["items"] if it[0] == "re"]
    if len(rects) != 2 or len(path["items"]) != 2:
        return path["items"]
    outer, inner = sorted(rects, key=lambda r: -r.get_area())
    if not outer.contains(inner):
        return path["items"]
    bands = [
        fitz.Rect(outer.x0, outer.y0, outer.x1, inner.y0),   # top
        fitz.Rect(outer.x0, inner.y1, outer.x1, outer.y1),   # bottom
        fitz.Rect(outer.x0, inner.y0, inner.x0, inner.y1),   # left
        fitz.Rect(inner.x1, inner.y0, outer.x1, inner.y1),   # right
    ]
    return [("re", b, 1) for b in bands if b.width > 0.05 and b.height > 0.05]


def page_elements(page: fitz.Page, body_top: float, body_bot: float) -> list[Elem]:
    """Every visible element of the page body, as flat rectangles.

    Drawing *paths* are exploded into their items: a single path often holds
    every row rule of a table, and its union rectangle would swallow the whole
    table into one unsplittable blob.
    """
    W, H = page.rect.width, page.rect.height
    out: list[Elem] = []

    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                x0, y0, x1, y1 = span["bbox"]
                if not span["text"].strip():
                    continue
                if y1 <= body_top or y0 >= body_bot:
                    continue
                bold = bool(span["flags"] & 2 ** 4) or "bold" in span["font"].lower()
                out.append(Elem(x0, y0, x1, y1, "text",
                                size=span["size"], bold=bold))

    for g in page.get_drawings():
        fill = g.get("fill")
        paint = fill if fill else g.get("color")
        if paint and min(paint) >= WHITE_FLOOR:
            continue        # page tint, white backdrop, or a white-out patch
        kind = "fill" if fill else "stroke"
        items = _expand_even_odd(g)
        for it in items:
            if it[0] == "re":
                ir = it[1]
                boxes = [(ir.x0, ir.y0, ir.x1, ir.y1)]
            elif it[0] == "l":
                p, q = it[1], it[2]
                boxes = [(min(p.x, q.x), min(p.y, q.y), max(p.x, q.x), max(p.y, q.y))]
            elif it[0] in ("c", "qu"):
                pts = [p for p in it[1:] if isinstance(p, fitz.Point)]
                if not pts:
                    continue
                boxes = [(min(p.x for p in pts), min(p.y for p in pts),
                          max(p.x for p in pts), max(p.y for p in pts))]
            else:
                continue
            for x0, y0, x1, y1 in boxes:
                if y1 <= body_top or y0 >= body_bot:
                    continue
                if x1 - x0 >= W * PAGE_FRAME_W and y1 - y0 >= H * PAGE_FRAME_H:
                    continue                 # page frame, not content
                cont = (kind == "fill" and x1 - x0 >= CONTAINER_MIN_W
                        and y1 - y0 >= CONTAINER_MIN_H)
                out.append(Elem(x0, y0, x1, y1, kind, container=cont))

    for info in page.get_image_info():
        x0, y0, x1, y1 = info["bbox"]
        if y1 <= body_top or y0 >= body_bot:
            continue
        out.append(Elem(x0, y0, x1, y1, "image"))

    return out


def rows_from_elements(elems: list[Elem]) -> list[Row]:
    """Collapse elements into horizontal rows, merging on vertical overlap."""
    if not elems:
        return []
    rows: list[Row] = []
    for e in sorted(elems, key=lambda e: (e.y0, e.x0)):
        placed = False
        for r in rows:
            if e.y0 <= r.y1 + ROW_GAP and e.y1 >= r.y0 - ROW_GAP:
                r.y0 = min(r.y0, e.y0)
                r.y1 = max(r.y1, e.y1)
                r.x0 = min(r.x0, e.x0)
                r.x1 = max(r.x1, e.x1)
                r.kinds.add(e.kind)
                r.size = max(r.size, e.size)
                r.bold = r.bold or e.bold
                placed = True
                break
        if not placed:
            rows.append(Row(e.y0, e.y1, e.x0, e.x1, {e.kind}, e.size, e.bold))
    # merging is order-dependent; settle it
    changed = True
    while changed:
        changed = False
        rows.sort(key=lambda r: r.y0)
        merged: list[Row] = []
        for r in rows:
            if merged and r.y0 <= merged[-1].y1 + ROW_GAP:
                m = merged[-1]
                m.y1 = max(m.y1, r.y1)
                m.x0 = min(m.x0, r.x0)
                m.x1 = max(m.x1, r.x1)
                m.kinds |= r.kinds
                m.size = max(m.size, r.size)
                m.bold = m.bold or r.bold
                changed = True
            else:
                merged.append(r)
        rows = merged
    return rows


# --------------------------------------------------------------------------
# 3. section assembly: rows -> atoms -> keep-together groups
# --------------------------------------------------------------------------

# Running heads and feet the generators print on every page. These are dropped
# and replaced with the booklet's own footer, so they must be recognised by
# text rather than by position alone -- the four generators put them at four
# different heights.
FURNITURE = re.compile(
    r"""^(
        \s*\d{1,3}\s*
      | \s*Page\s+\d+\s+of\s+\d+\s*
      | \s*\d+\s*/\s*\d+\s*
      | \s*Azwad\s+Hossain\s+Tahmid\s*
      | \s*Edexcel\s+IGCSE\s+Accounting\s*[-—–].*
      | \s*Topic\s+\d+\s*:?.*
      | \s*O\s+Level\s+Accounting\s+Notes\s*
    )$""",
    re.VERBOSE | re.IGNORECASE,
)


def furniture_cut(page: fitz.Page) -> float:
    """Lowest y that still holds real content, i.e. the top of the footer."""
    H = page.rect.height
    cut = H - FOOTER_BAND
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            txt = "".join(s["text"] for s in line["spans"])
            if not txt.strip():
                continue
            y0, y1 = line["bbox"][1], line["bbox"][3]
            if y0 < H - 70:
                continue
            if FURNITURE.match(txt):
                cut = min(cut, y0 - 1.0)
    return cut


# The strapline some of the generators print under the topic title. It names
# the same topic a second time, in a fourth typeface, and is replaced along
# with the title -- but it has body-text size, so it can only be told from the
# first real heading by what it says.
KICKER = re.compile(
    r"(Edexcel\s+IGCSE\s+Accounting"
    r"|Introduction\s+to\s+Bookkeeping"
    r"|Complete\s+Revision\s+Guide"
    r"|O\s+Level\s+Accounting\s+Notes)",
    re.IGNORECASE,
)

# A topic title is set at 16pt or more in every one of the source documents;
# the largest body heading is 15pt. Title lines that belong to the same title
# sit within this much of each other -- in several topics the pasted "Topic N"
# patch and the title it covers are separate lines a few points apart.
TITLE_MIN_SIZE = 15.5
TITLE_RUN_GAP = 30.0
KICKER_REACH = 40.0


def heading_cut(page: fitz.Page) -> float:
    """Bottom of the old topic heading on a section's first page.

    Everything above it is dropped and replaced by the booklet's own uniform
    heading -- which is what finally makes the eighteen topic titles agree.
    The cut has to be tight: the line under the heading is often a "Contents"
    panel or the topic's first real section heading, and taking those with it
    would lose content.
    """
    H = page.rect.height
    lines = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            txt = "".join(s["text"] for s in line["spans"]).strip()
            if not txt or line["bbox"][1] > H * 0.32:
                continue
            lines.append((line["bbox"][1], line["bbox"][3],
                          max(s["size"] for s in line["spans"]), txt))
    lines.sort()
    if not lines:
        return 0.0

    # the run of title-sized lines at the top of the page
    bottom = None
    for y0, y1, size, _ in lines:
        if size < TITLE_MIN_SIZE:
            continue
        if bottom is not None and y0 > bottom + TITLE_RUN_GAP:
            break
        bottom = y1 if bottom is None else max(bottom, y1)
    if bottom is None:
        return 0.0
    top = min(y0 for y0, _, size, _ in lines if size >= TITLE_MIN_SIZE)

    # then any strapline hanging off it
    changed = True
    while changed:
        changed = False
        for y0, y1, _, txt in lines:
            if bottom < y0 <= bottom + KICKER_REACH and KICKER.search(txt):
                bottom = max(bottom, y1)
                changed = True

    # the banner the title sits in, or the rule drawn under it
    for g in page.get_drawings():
        r = g["rect"]
        if r.width < 200 or r.y1 > H * 0.32:
            continue
        if r.y0 <= top + 2 and bottom - 2 <= r.y1 <= bottom + 30:
            bottom = max(bottom, r.y1)          # full banner behind the title
        elif r.height <= 8 and bottom <= r.y0 <= bottom + 26:
            bottom = max(bottom, r.y1)          # rule under the title
    return bottom + 2.0


def _atoms_from_rows(rows: list[Row], page: int) -> list[list[Row]]:
    """Split a page's rows into atoms wherever the whitespace opens up."""
    atoms: list[list[Row]] = []
    for r in rows:
        if atoms and r.y0 - atoms[-1][-1].y1 < ATOM_GAP:
            atoms[-1].append(r)
        else:
            atoms.append([r])
    return atoms


@dataclass
class Atom:
    page: int
    rows: list
    touches_top: bool = False
    touches_bottom: bool = False
    joined: bool = False     # continues the atom before it, across a page break
    text_cache: str = ""
    trim_top: float | None = None
    trim_bottom: float | None = None

    @property
    def y0(self) -> float:
        raw = min(r.y0 for r in self.rows)
        return raw if self.trim_top is None else max(raw, self.trim_top)

    @property
    def y1(self) -> float:
        raw = max(r.y1 for r in self.rows)
        return raw if self.trim_bottom is None else min(raw, self.trim_bottom)

    @property
    def ink_rows(self) -> list:
        return [r for r in self.rows if r.kinds & {"text", "image"}]

    @property
    def x0(self) -> float:
        return min(r.x0 for r in self.rows)

    @property
    def x1(self) -> float:
        return max(r.x1 for r in self.rows)

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def text(self, doc) -> str:
        return doc[self.page].get_text(
            "text", clip=fitz.Rect(0, self.y0 - 1, doc[self.page].rect.width, self.y1 + 1)
        ).strip()

    @property
    def is_blank(self) -> bool:
        """Fill and rules only -- the empty foot of a panel the generator split.

        When a shaded worked-example box overruns a page, the padding below its
        last line lands on the next page as a band of tinted nothing. Carrying
        it into the re-flow would reopen the very split this rebuild closes, so
        it is dropped; anything holding text or a figure is kept.
        """
        kinds = set()
        for r in self.rows:
            kinds |= r.kinds
        return not (kinds & {"text", "image"})

    @property
    def is_heading(self) -> bool:
        """A short, large or emphasised line that introduces what follows."""
        text_rows = [r for r in self.rows if "text" in r.kinds]
        if len(text_rows) != 1 or self.height > CAPTION_MAX_H:
            return False
        r = text_rows[0]
        return r.size >= 13.0 or (r.bold and r.size >= 11.0)


def section_atoms(doc: fitz.Document, first: int, last: int) -> list[Atom]:
    """Every content atom of one topic, in reading order, page joins healed.

    A block the generator cut at a page break (a worked-example panel whose
    caption is stranded on the previous page) is marked ``joined`` so the flow
    stage keeps the two halves together.
    """
    per_page: dict[int, list[Atom]] = {}
    bounds: dict[int, tuple[float, float]] = {}

    for pno in range(first, last + 1):
        page = doc[pno]
        top = getattr(doc, "heading_cuts", {}).get(pno, 0.0)
        bot = furniture_cut(page)
        rows = rows_from_elements(page_elements(page, top, bot))
        rows = [r for r in rows if r.y1 > top and r.y0 < bot]
        if not rows:
            continue
        page_atoms = [a for a in (Atom(pno, grp) for grp in _atoms_from_rows(rows, pno))
                      if not a.is_blank]
        if not page_atoms:
            continue
        per_page[pno] = page_atoms
        bounds[pno] = (min(a.y0 for a in page_atoms), max(a.y1 for a in page_atoms))

    if not per_page:
        return []

    # Where the generator's own text frame starts and ends. Taken across the
    # section rather than per page, because a page that simply ran out of
    # content must not be read as one that was cut off.
    body_pages = [n for n in per_page if n != first and n not in PASSTHROUGH_PAGES]
    frame_top = min(bounds[n][0] for n in body_pages) if body_pages else bounds[first][0]
    frame_bot = max(bounds[n][1] for n in bounds if n not in PASSTHROUGH_PAGES)

    atoms: list[Atom] = []
    for pno in sorted(per_page):
        page_atoms = per_page[pno]
        for a in page_atoms:
            a.touches_top = a.y0 <= frame_top + EDGE_TOL
            a.touches_bottom = a.y1 >= frame_bot - EDGE_TOL
        if pno in PASSTHROUGH_PAGES:
            atoms.extend(page_atoms)
            continue
        if atoms and atoms[-1].page not in PASSTHROUGH_PAGES                 and atoms[-1].touches_bottom and page_atoms[0].touches_top                 and _panel_continues(atoms[-1], page_atoms[0]):
            page_atoms[0].joined = True
            _trim_seam(doc, atoms[-1], page_atoms[0])
        atoms.extend(page_atoms)
    return atoms


# When a panel is cut by a page break, the half above ends with the panel's
# tint running on to the foot of the page and the half below starts with the
# same tint at the head of the next. Re-joining the halves without trimming
# that padding reopens a 90pt hole between a caption and the account it names
# -- the exact defect this rebuild exists to remove.
SEAM_PAD = 10.0


def _panel_continues(upper: Atom, lower: Atom) -> bool:
    """Is this page break cutting through a panel or a table?

    Reaching the foot of the text frame is not enough on its own: a topic whose
    pages all run full would otherwise read as one block a dozen pages long.
    What marks a real split is the tint or the rules carrying over -- the shaded
    box, or the account's grid, ending at the foot of one page and starting
    again at the head of the next over the same columns.
    """
    bottom = max(upper.rows, key=lambda r: r.y1)
    top = min(lower.rows, key=lambda r: r.y0)
    ink = {"fill", "stroke"}
    if not (bottom.kinds & ink and top.kinds & ink):
        return False
    overlap = min(bottom.x1, top.x1) - max(bottom.x0, top.x0)
    return overlap > 0.5 * min(bottom.x1 - bottom.x0, top.x1 - top.x0)


def _ink_extent(page: fitz.Page, y0: float, y1: float) -> tuple[float, float] | None:
    """Top and bottom of the real ink inside a band.

    Read from the page rather than from the atom's rows: a shaded panel merges
    into a single row spanning its whole tint, so the rows cannot say where the
    last line of text actually sits.
    """
    top, bot = None, None
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for span in line["spans"]:
                if not span["text"].strip():
                    continue
                sy0, sy1 = span["bbox"][1], span["bbox"][3]
                if sy1 <= y0 or sy0 >= y1:
                    continue
                top = sy0 if top is None else min(top, sy0)
                bot = sy1 if bot is None else max(bot, sy1)
    for info in page.get_image_info():
        iy0, iy1 = info["bbox"][1], info["bbox"][3]
        if iy1 <= y0 or iy0 >= y1:
            continue
        top = iy0 if top is None else min(top, iy0)
        bot = iy1 if bot is None else max(bot, iy1)
    return None if top is None else (top, bot)


def _trim_seam(doc: fitz.Document, upper: Atom, lower: Atom) -> None:
    up = _ink_extent(doc[upper.page], upper.y0, upper.y1)
    lo = _ink_extent(doc[lower.page], lower.y0, lower.y1)
    if up:
        upper.trim_bottom = up[1] + SEAM_PAD
    if lo:
        lower.trim_top = lo[0] - SEAM_PAD


# --------------------------------------------------------------------------
# 4. keep-together grouping
# --------------------------------------------------------------------------

# A block at least this tall is a table or a panel: the thing a caption above
# it is naming, and therefore the thing it must not be separated from.
BLOCK_MIN_H = 55.0

# A caption sits this close to the block it names. Measured on the draft, a
# caption-to-table gap runs 10-17pt while a paragraph-to-table gap runs 20pt+.
CAPTION_GAP = 19.0

# A caption is short. Anything taller is a paragraph that merely happens to sit
# above a table, and breaking after it costs nothing.
CAPTION_MAX_H = 34.0


def _keep_with_next(atoms: list[Atom], i: int, gaps: list[float]) -> bool:
    """Would a page break after atom *i* strand something?

    Three cases, all of them visible in the draft:
      * a section heading left alone at the foot of a page;
      * a caption -- "Katrina -- Equipment Account" -- parted from its account;
      * a lead-in line ending in a colon, parted from the block it introduces.
    """
    if i + 1 >= len(atoms):
        return False
    a, nxt = atoms[i], atoms[i + 1]
    if nxt.joined:
        return True
    if a.height > CAPTION_MAX_H:
        return False
    gap = gaps[i + 1]
    if gap > CAPTION_GAP:
        return False
    if a.is_heading:
        return True
    if nxt.height >= BLOCK_MIN_H:
        return True
    return a.text_cache.rstrip().endswith(":")


def build_groups(doc: fitz.Document, atoms: list[Atom],
                 median_gap: float) -> list[Group]:
    """Chain atoms into groups that must be printed on one page."""
    for a in atoms:
        a.text_cache = a.text(doc)

    gaps = [0.0]
    for prev, cur in zip(atoms, atoms[1:]):
        if cur.joined:
            gaps.append(0.0)
        elif cur.page == prev.page:
            gaps.append(max(0.0, cur.y0 - prev.y1))
        else:
            gaps.append(median_gap)

    keep = [_keep_with_next(atoms, i, gaps) for i in range(len(atoms))]

    groups: list[Group] = []
    i = 0
    while i < len(atoms):
        j = i
        while j < len(atoms) - 1 and (keep[j] or atoms[j + 1].joined):
            j += 1
        members = atoms[i:j + 1]
        g = Group(tag=members[0].text_cache.split("\n")[0][:60])
        offset = 0.0
        for k, a in enumerate(members):
            if k:
                offset += gaps[i + k]
            g.slices.append((a, offset))
            offset += a.height
        g.total = offset
        g.lead_gap = gaps[i] if i else 0.0
        g.passthrough = members[0].page in PASSTHROUGH_PAGES
        groups.append(g)
        i = j + 1
    return groups
