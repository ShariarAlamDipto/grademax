"""Stack a paper's scheme cuts into one image, each labelled with the question
it is assigned to and that question's marks on the paper, for reading."""

from __future__ import annotations

from pathlib import Path

import fitz


def stack(seg_dir: Path, questions: list[int], marks: dict[int, int], out: Path, dpi: int = 40) -> Path:
    tiles = []
    for q in questions:
        f = seg_dir / "markschemes" / f"q{q}.pdf"
        if not f.exists():
            continue
        with fitz.open(f) as d:
            for i, page in enumerate(d):
                tmp = fitz.open()
                tmp.insert_pdf(d, from_page=i, to_page=i)
                pg = tmp[0]
                pg.insert_text((4, 12), f"ASSIGNED Q{q}  (paper: {marks.get(q,'?')} marks)",
                               fontsize=9, color=(1, 0, 0))
                tiles.append(pg.get_pixmap(dpi=dpi))
                tmp.close()
    width = max(t.width for t in tiles)
    height = sum(t.height + 8 for t in tiles)
    canvas = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, width, height), False)
    canvas.clear_with(255)
    y = 0
    for t in tiles:
        t = fitz.Pixmap(fitz.csRGB, t) if t.colorspace != fitz.csRGB else t
        if t.alpha:
            t = fitz.Pixmap(t, 0)
        t.set_origin(0, y)
        canvas.copy(t, t.irect)
        y += t.height + 8
    canvas.save(out)
    return out


def annotate_groups(pdf: Path, groups: list, out: Path, dpi: int = 30, cols: int = 5) -> Path:
    """Contact sheet of the pages the groups cover, with each group's number and
    start line drawn in red -- to decide which groups belong together."""
    pages = sorted({r[0] for g in groups for r in g})
    tiles = []
    with fitz.open(pdf) as doc:
        for p in pages:
            tmp = fitz.open()
            tmp.insert_pdf(doc, from_page=p, to_page=p)
            pg = tmp[0]
            for n, g in enumerate(groups, start=1):
                for k, (gp, top, _bottom) in enumerate(g):
                    if gp == p:
                        pg.draw_line((0, top), (pg.rect.width, top), color=(1, 0, 0), width=1.5)
                        pg.insert_text((pg.rect.width - 70, top + 14), f"G{n}" + ("" if k == 0 else "+"),
                                       fontsize=14, color=(1, 0, 0))
            pg.insert_text((10, 30), f"page {p}", fontsize=14, color=(0, 0, 1))
            tiles.append(pg.get_pixmap(dpi=dpi))
            tmp.close()
    w = max(t.width for t in tiles); h = max(t.height for t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    canvas = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, cols * (w + 6), rows * (h + 6)), False)
    canvas.clear_with(200)
    for i, t in enumerate(tiles):
        t = fitz.Pixmap(fitz.csRGB, t) if t.colorspace != fitz.csRGB else t
        if t.alpha:
            t = fitz.Pixmap(t, 0)
        t.set_origin((i % cols) * (w + 6), (i // cols) * (h + 6))
        canvas.copy(t, t.irect)
    canvas.save(out)
    return out
