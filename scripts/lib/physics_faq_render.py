"""Render the Physics FAQ content to a print-ready A4 PDF using PyMuPDF's Story engine.

Note on styling: PyMuPDF's Story re-paints every CSS background-color it has drawn so far
at the top of each continuation page, which strikes through the text there. Backgrounds are
therefore avoided entirely - borders render correctly, and the chapter banners are drawn
directly onto the page after layout, into space reserved by insetting the first frame.
"""
from __future__ import annotations

import html
from pathlib import Path

import fitz

INK = "#16202b"
MUTED = "#5b6b7c"
ACCENT = "#0b5cab"
RULE = "#d3dce5"
HOT = "#b3300f"

ACCENT_RGB = (0x0b / 255, 0x5c / 255, 0xab / 255)
MUTED_RGB = (0.42, 0.47, 0.53)

BANNER_H = 54.0

CSS = f"""
* {{ font-family: sans-serif; }}
body {{ color: {INK}; }}
p {{ font-size: 9.6pt; line-height: 1.45; margin: 0 0 4pt 0; }}

.cover-kicker {{ font-size: 10pt; color: {ACCENT}; font-weight: bold; margin-bottom: 6pt; }}
.cover-title {{ font-size: 30pt; font-weight: bold; line-height: 1.12; margin-bottom: 4pt; }}
.cover-sub {{ font-size: 15pt; color: {MUTED}; margin-bottom: 14pt; }}
.cover-rule {{ border-top: 2.5pt solid {ACCENT}; font-size: 1pt; margin: 0 0 14pt 0; }}
.cover-note {{ font-size: 9.5pt; color: {MUTED}; line-height: 1.5; margin-bottom: 14pt; }}
.cover-h {{ font-size: 11pt; font-weight: bold; margin: 14pt 0 6pt 0; }}
.cover-li {{ font-size: 9.8pt; line-height: 1.5; margin: 0 0 7pt 0; padding-left: 10pt; }}

.stat-row {{ font-size: 9.4pt; margin: 0 0 3pt 0; }}
.stat-k {{ font-weight: bold; }}

.ch-blurb {{ font-size: 9.6pt; color: {MUTED}; line-height: 1.45; margin: 0 0 8pt 0; }}
.sec-h {{ font-size: 10.5pt; font-weight: bold; color: {ACCENT};
          border-bottom: 0.8pt solid {RULE}; padding-bottom: 2pt; margin: 13pt 0 6pt 0; }}

th {{ font-size: 8.2pt; text-align: left; padding: 3pt 5pt; color: {MUTED};
      font-weight: bold; border-bottom: 0.8pt solid {ACCENT}; }}
td {{ font-size: 9pt; padding: 3.5pt 5pt; border-bottom: 0.4pt solid {RULE};
      vertical-align: top; }}
td.q {{ font-weight: bold; }}
td.f {{ font-family: serif; }}
td.u {{ color: {MUTED}; font-size: 8.4pt; }}
td.n {{ text-align: right; }}

.item {{ margin: 0 0 11pt 0; }}
.badge {{ font-size: 7.6pt; font-weight: bold; color: {ACCENT}; margin: 0 0 2pt 0; }}
.badge-hot {{ font-size: 7.6pt; font-weight: bold; color: {HOT}; margin: 0 0 2pt 0; }}
.q {{ font-size: 10.2pt; font-weight: bold; line-height: 1.35; margin: 0 0 4pt 0; }}
.a-h {{ font-size: 7.8pt; font-weight: bold; color: {MUTED}; margin: 0 0 2pt 0; }}
.a {{ font-size: 9.5pt; line-height: 1.42; margin: 0 0 2pt 0; padding-left: 9pt; }}
.tip {{ font-size: 8.9pt; line-height: 1.4; color: {MUTED};
        border-left: 2pt solid {RULE}; padding-left: 7pt; margin: 5pt 0 0 3pt; }}
.years {{ font-size: 7.6pt; color: {MUTED}; margin: 2pt 0 0 0; }}
"""


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def _badge(item: dict) -> str:
    freq = item.get("freq")
    marks = item.get("marks", "")
    if not freq or not freq["papers"]:
        return f'<p class="badge">{esc(marks)}</p>' if marks else ""
    n, total = freq["papers"], freq["total_papers"]
    label = f"ASKED IN {n} OF {total} PAPERS"
    if marks:
        label += f"  ·  {marks}"
    if n >= 5:
        return f'<p class="badge-hot">HIGH FREQUENCY  ·  {esc(label)}</p>'
    return f'<p class="badge">{esc(label)}</p>'


def _years(item: dict) -> str:
    freq = item.get("freq")
    if not freq or not freq["years"]:
        return ""
    return f'<p class="years">Seen in: {esc(", ".join(str(y) for y in freq["years"]))}</p>'


def _formula_table(formulas: list) -> str:
    rows = "".join(
        f"<tr><td class='q' style='width:31%'>{esc(q)}</td>"
        f"<td class='f' style='width:53%'>{esc(f)}</td>"
        f"<td class='u' style='width:16%'>{esc(u)}</td></tr>"
        for q, f, u in formulas)
    return f"<table style='width:100%'>{rows}</table>"


def _items_html(section: dict, prefix: str) -> str:
    out = []
    for i, item in enumerate(section["items"], 1):
        answers = "".join(f'<p class="a">•&#160;&#160;{esc(a)}</p>' for a in item["a"])
        tip = (f'<p class="tip"><b>Examiner tip.</b> {esc(item["tip"])}</p>'
               if item.get("tip") else "")
        out.append(
            f'<div class="item">{_badge(item)}'
            f'<p class="q">{prefix}{i}&#160;&#160;{esc(item["q"])}</p>'
            f'<p class="a-h">MARK SCHEME ANSWER</p>{answers}{_years(item)}{tip}</div>')
    return "".join(out)


def _cover(meta: dict) -> str:
    lis = "".join(f'<p class="cover-li">•&#160;&#160;{esc(x)}</p>' for x in meta["how_to_use"])
    return f"""
<div>
  <p class="cover-kicker">{esc(meta['board'])} &#183; {esc(meta['code'])}</p>
  <p class="cover-title">{esc(meta['subject'])}<br/>{esc(meta['title'])}</p>
  <p class="cover-sub">Past papers {esc(meta['window'])}</p>
  <p class="cover-rule">&#160;</p>
  <p class="cover-note">{esc(meta['corpus_note'])}</p>
  <p class="stat-row"><span class="stat-k">{meta['n_papers']}</span> distinct papers analysed
     &#160;&#160;·&#160;&#160;
     <span class="stat-k">{meta['n_questions']}</span> distinct exam questions read
     &#160;&#160;·&#160;&#160;<span class="stat-k">8</span> chapters</p>
  <p class="cover-h">How to use this sheet</p>
  {lis}
</div>
"""


def _weighting(chapters: list[dict]) -> str:
    rows = "".join(
        f"<tr><td class='n'>{c['n']}</td><td class='q'>{esc(c['title'])}</td>"
        f"<td class='n'>{c['n_questions']}</td>"
        f"<td class='n'>{c['q_share'] * 100:.0f}%</td>"
        f"<td class='n'>{c['m_share'] * 100:.0f}%</td>"
        f"<td class='n'>{len(c['items'])}</td></tr>"
        for c in chapters)
    return f"""
<div>
  <p class="sec-h">WHERE THE MARKS ACTUALLY ARE</p>
  <p class="ch-blurb">Measured across every 2018&#8211;2025 paper in the archive. Use it to
     decide what to revise first if you are short of time.</p>
  <table style="width:100%">
    <tr><th>#</th><th>Chapter</th><th>Questions</th><th>Share of questions</th>
        <th>Share of marks</th><th>FAQs here</th></tr>
    {rows}
  </table>
</div>
"""


def _formula_page(chapters: list[dict]) -> str:
    blocks = []
    for c in chapters:
        if c.get("formulas"):
            blocks.append(f"<p class='sec-h'>{c['n']}. {esc(c['title']).upper()}</p>"
                          + _formula_table(c["formulas"]))
    return f"""
<div>
  <p class="sec-h">EVERY FORMULA YOU MAY BE ASKED TO STATE</p>
  <p class="ch-blurb">&#8220;State the formula linking &#8230;&#8221; is the single most common
     question type in this subject &#8211; it is worth one mark, it needs no working, and some
     form of it appears in nearly every paper. Learn this page and you collect those marks
     before you have done any physics.</p>
  {''.join(blocks)}
</div>
"""


def _skills_body(skills: dict) -> str:
    return ('<div>'
            f'<p class="ch-blurb">{esc(skills["blurb"])}</p>'
            '<p class="sec-h">MOST-ASKED QUESTIONS</p>'
            + _items_html(skills, "S.") + '</div>')


def _chapter_body(ch: dict) -> str:
    parts = ['<div>', f'<p class="ch-blurb">{esc(ch["blurb"])}</p>',
             f'<p class="stat-row">{ch["n_questions"]} questions in the 2018&#8211;2025 archive '
             f'&#160;·&#160; {ch["q_share"] * 100:.0f}% of all questions '
             f'&#160;·&#160; {ch["m_share"] * 100:.0f}% of all marks</p>']
    if ch.get("formulas"):
        parts.append('<p class="sec-h">FORMULAS FOR THIS CHAPTER</p>'
                     + _formula_table(ch["formulas"]))
    parts.append('<p class="sec-h">MOST-ASKED QUESTIONS</p>')
    parts.append(_items_html(ch, f'{ch["n"]}.'))
    parts.append('</div>')
    return "".join(parts)


def _decorate(path: Path, meta: dict, banners: list[tuple[int, str, str]],
              frame: fitz.Rect) -> None:
    """Draw chapter banners and page footers onto the finished document."""
    doc = fitz.open(path)
    by_page = {p: (k, t) for p, k, t in banners}
    for i, page in enumerate(doc):
        if i in by_page:
            kicker, title = by_page[i]
            rect = fitz.Rect(frame.x0, frame.y0, frame.x1, frame.y0 + BANNER_H - 10)
            page.draw_rect(rect, color=None, fill=ACCENT_RGB)
            page.insert_text(fitz.Point(rect.x0 + 12, rect.y0 + 16), kicker,
                             fontname="hebo", fontsize=8, color=(0.81, 0.89, 0.96))
            page.insert_text(fitz.Point(rect.x0 + 12, rect.y0 + 36), title,
                             fontname="hebo", fontsize=17, color=(1, 1, 1))
        if i == 0:
            continue
        y = page.rect.height - 30
        page.draw_line(fitz.Point(frame.x0, y - 10), fitz.Point(frame.x1, y - 10),
                       color=(0.83, 0.86, 0.90), width=0.4)
        page.insert_text(
            fitz.Point(frame.x0, y),
            f"{meta['board']} {meta['code']} · {meta['title']} · {meta['window']}",
            fontname="helv", fontsize=7.2, color=MUTED_RGB)
        page.insert_text(fitz.Point(frame.x1 - 28, y), f"page {i + 1}",
                         fontname="helv", fontsize=7.2, color=MUTED_RGB)
    doc.saveIncr()
    doc.close()


def render_pdf(meta: dict, chapters: list[dict], out_path: Path,
               skills: dict | None = None) -> None:
    sections: list[dict] = [
        {"html": _cover(meta)},
        {"html": _weighting(chapters)},
        {"html": _formula_page(chapters)},
    ]
    if skills:
        sections.append({"html": _skills_body(skills),
                         "banner": ("BEFORE YOU START", skills["title"])})
    for ch in chapters:
        sections.append({"html": _chapter_body(ch),
                         "banner": (f"CHAPTER {ch['n']}", ch["title"])})

    writer = fitz.DocumentWriter(str(out_path))
    mediabox = fitz.paper_rect("a4")
    frame = mediabox + (42, 46, -42, -46)
    inset = frame + (0, BANNER_H, 0, 0)

    banners: list[tuple[int, str, str]] = []
    page_index = 0
    for section in sections:
        story = fitz.Story(html=section["html"], user_css=CSS)
        banner = section.get("banner")
        first, more = True, 1
        while more:
            device = writer.begin_page(mediabox)
            more, _ = story.place(inset if (first and banner) else frame)
            story.draw(device)
            writer.end_page()
            if first and banner:
                banners.append((page_index, banner[0], banner[1]))
            first = False
            page_index += 1
    writer.close()
    _decorate(out_path, meta, banners, frame)
