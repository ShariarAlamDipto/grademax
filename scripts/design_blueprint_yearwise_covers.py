"""Blueprint front + back covers for the 13 yearwise question books (2019-2026).

Same house style as the M1/S1/P4 covers (data/workbook/M1 S1 P4 cover/): the
editable P4 HTML is the template, its fonts and logo live in
data/workbook/yearwise_blueprint_covers/assets/. Paper lists come from the
audited catalog Codex wrote for the books, never typed by hand.

  .venv/Scripts/python.exe -X utf8 scripts/design_blueprint_yearwise_covers.py            # covers
  .venv/Scripts/python.exe -X utf8 scripts/design_blueprint_yearwise_covers.py --books    # + books
  ... --only 4PH1 WMA14                                                                    # subset

Outputs go to output/pdf/GradeMax_Yearwise_2026_Blueprint/. Inputs are never modified.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts' / 'lib'))

from blueprint_cover_themes import COPY, SEASON, SEASON_SHORT, THEMES, Theme  # noqa: E402
from blueprint_plates_maths import PLATES as MATHS_PLATES  # noqa: E402
from blueprint_plates_science import PLATES as SCIENCE_PLATES  # noqa: E402

ASSETS = ROOT / 'data/workbook/yearwise_blueprint_covers/assets'
CATALOG = ROOT / 'output/book-cover-redesign-2026-10-16/catalog.json'
SOURCE_BOOKS = ROOT / 'output/pdf/GradeMax_Yearwise_2026_Vibrant/Books'
OUT = ROOT / 'output/pdf/GradeMax_Yearwise_2026_Blueprint'
PLATES = {**MATHS_PLATES, **SCIENCE_PLATES}
INSTRUCTOR = 'Shariar Alam Dipto'


def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip('#')
    return f'rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})'


def mix(a: str, b: str, t: float) -> str:
    pa = [int(a.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    pb = [int(b.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02X}' for x, y in zip(pa, pb))


def sittings(book: dict) -> list[str]:
    names = SEASON[book['level']]
    return [f"{names[s['season']]} {s['year']}" for s in book['sessions']]


def css(t: Theme, columns: int) -> str:
    shadow = 'text-shadow:0 0 12mm rgba(0,0,0,.6);' if t.dark else ''
    hair = rgba(t.ink, .26 if t.dark else .30)
    hair2 = rgba(t.ink, .14 if t.dark else .16)
    soft = mix(t.ink, t.muted, .45) if t.dark else t.muted
    return f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{background:#59636a;font-family:'Body',sans-serif}}
@page{{size:210mm 297mm;margin:0}}
.page{{position:relative;width:210mm;height:297mm;overflow:hidden;page-break-after:always}}
@media screen{{.page{{margin:12mm auto;box-shadow:0 6mm 22mm rgba(0,0,0,.45)}}}}
.reg{{position:absolute;width:9mm;height:9mm;opacity:.6;z-index:4}}
.reg.tl{{top:8mm;left:8mm;border-top:.5mm solid;border-left:.5mm solid}}
.reg.tr{{top:8mm;right:8mm;border-top:.5mm solid;border-right:.5mm solid}}
.reg.bl{{bottom:8mm;left:8mm;border-bottom:.5mm solid;border-left:.5mm solid}}
.reg.br{{bottom:8mm;right:8mm;border-bottom:.5mm solid;border-right:.5mm solid}}
.logo{{position:absolute;background:#fff;padding:2.2mm;line-height:0;z-index:5;box-shadow:0 1mm 4mm rgba(0,0,0,.3)}}
.logo img{{width:100%;display:block}}
.front{{background:radial-gradient(120% 88% at 50% 44%, {t.bg[0]} 0%, {t.bg[1]} 60%, {t.bg[2]} 100%);color:{t.ink};
  --pm:{t.ink};--ps:{soft};--pa:{t.accent};--pg:{t.ink};--pt:{t.ink};--pglow:{t.glow}}}
.front .reg{{color:{rgba(t.ink, .55)}}}
.front .hair{{position:absolute;inset:11mm;border:.35mm solid {hair};z-index:4}}
.front .hair2{{position:absolute;inset:12.6mm;border:.2mm solid {hair2};z-index:4}}
.front .logo{{top:16.5mm;right:16.5mm;width:26mm}}
.plate-wrap{{position:absolute;left:50%;top:172mm;transform:translate(-50%,-50%);width:180mm;height:180mm;z-index:1}}
.plate{{width:100%;height:100%;display:block}}
.title{{position:absolute;left:17mm;right:48mm;top:28mm;z-index:3}}
.title .kick{{font-family:'Mono',monospace;font-size:3mm;letter-spacing:.48em;text-transform:uppercase;color:{t.muted};margin-bottom:3.4mm}}
.title h1{{font-family:'Display',sans-serif;font-weight:700;font-size:21mm;line-height:.88;letter-spacing:-.01em;text-transform:uppercase;color:{t.ink};{shadow}white-space:nowrap}}
.title h1 .thin{{font-weight:400;color:{t.muted}}}
.title .rule{{width:104mm;height:.7mm;margin:4.4mm 0 3mm;background:linear-gradient(90deg,{t.accent} 0 30%,{t.muted} 30% 55%,{t.ink} 55% 78%,{rgba(t.ink, .3)} 78% 100%)}}
.title .board{{font-family:'Mono',monospace;font-size:3.4mm;letter-spacing:.4em;color:{t.ink};text-transform:uppercase;opacity:.9}}
.foot .row{{display:flex;justify-content:space-between;align-items:flex-end;gap:6mm}}
.foot .range{{font-family:'Mono',monospace;font-size:2.6mm;line-height:1.9;letter-spacing:.24em;color:{rgba(t.ink, .72)};text-transform:uppercase;text-align:right;padding-bottom:.6mm}}
.foot .range b{{font-family:'Display',sans-serif;font-weight:600;font-size:4.6mm;letter-spacing:.08em;color:{t.ink}}}
.foot{{position:absolute;left:17mm;right:17mm;bottom:17mm;z-index:3;display:flex;flex-direction:column;gap:4mm}}
.foot .cw{{font-family:'Display',sans-serif;font-weight:700;font-size:8mm;text-transform:uppercase;letter-spacing:.04em;color:{t.ink};{shadow}}}
.foot .by{{font-size:4mm;letter-spacing:.08em;color:{rgba(t.ink, .85)};margin-top:-1mm}}
.foot .by b{{font-weight:500;color:{t.ink}}}
.foot .rule2{{border-top:.45mm solid {rgba(t.ink, .55)};padding-top:3mm;display:flex;justify-content:space-between;align-items:flex-end;gap:6mm}}
.foot .k{{font-family:'Mono',monospace;font-size:2.5mm;letter-spacing:.22em;text-transform:uppercase;color:{t.accent};margin-bottom:1.4mm}}
.foot .v{{font-family:'Display',sans-serif;font-weight:600;font-size:6mm;letter-spacing:.05em;text-transform:uppercase;line-height:1;color:{t.ink}}}
.foot .v small{{font-family:'Mono',monospace;font-weight:400;font-size:2.8mm;letter-spacing:.1em;color:{t.muted};text-transform:none}}
.foot .right{{text-align:right}}
.swatch{{position:absolute;left:17mm;bottom:12mm;display:flex;gap:1mm;z-index:3}}
.swatch i{{display:block;width:9mm;height:1.4mm}}
.back{{background:#FFFFFF;color:{t.back_ink}}}
.back .grid{{position:absolute;inset:0;background-size:6mm 6mm;background-image:linear-gradient({t.back_grid} .2mm,transparent .2mm),linear-gradient(90deg,{t.back_grid} .2mm,transparent .2mm)}}
.back .hair{{position:absolute;inset:11mm;border:.35mm solid {t.back_line}}}
.back .corner{{position:absolute;right:-52mm;bottom:8mm;width:150mm;height:150mm;opacity:.4;z-index:0;
  --pm:{t.back_plate};--ps:{t.back_plate};--pa:{t.back_plate};--pg:{t.back_plate};--pt:{t.back_plate};--pglow:transparent}}
.back .corner svg{{width:100%;height:100%}}
.back .inner{{position:absolute;inset:17mm;display:flex;flex-direction:column;z-index:2}}
.back .reg{{color:{t.back_ink};opacity:.35}}
.bhead{{display:flex;justify-content:space-between;align-items:flex-start;gap:8mm}}
.bhead .eyebrow{{font-family:'Mono',monospace;font-size:2.7mm;letter-spacing:.3em;text-transform:uppercase;color:{t.back_mid}}}
.bhead h2{{font-family:'Display',sans-serif;font-weight:700;font-size:12.5mm;line-height:.9;text-transform:uppercase;letter-spacing:-.01em;margin-top:3mm}}
.bhead .logo{{position:static;box-shadow:none;padding:0;width:22mm;flex:0 0 22mm}}
.blurb{{margin-top:6mm;max-width:124mm;font-size:3.5mm;line-height:1.6;color:{t.back_ink};opacity:.86}}
.blurb + .blurb{{margin-top:2.6mm}}
.idx{{margin-top:6.5mm;border-top:.4mm solid {t.back_line};padding-top:3.6mm}}
.idx .lab{{font-family:'Mono',monospace;font-size:2.7mm;letter-spacing:.3em;text-transform:uppercase;color:{t.back_ink};opacity:.6;margin-bottom:3.4mm}}
.idx .lab b{{color:{t.back_mid};font-weight:500;opacity:1}}
.idx ol{{list-style:none;columns:{columns};column-gap:9mm}}
.idx li{{break-inside:avoid;display:flex;align-items:baseline;gap:3mm;padding:1.8mm 0;border-bottom:.2mm dotted {t.back_line}}}
.idx li .n{{font-family:'Mono',monospace;font-size:3mm;color:{t.back_mid};letter-spacing:.06em}}
.idx li .t{{font-family:'Display',sans-serif;font-weight:600;font-size:4.4mm;text-transform:uppercase;letter-spacing:.02em;line-height:1.1}}
.tags{{margin-top:5mm;display:flex;gap:2.2mm;flex-wrap:wrap}}
.tags span{{font-family:'Mono',monospace;font-size:2.6mm;letter-spacing:.16em;text-transform:uppercase;padding:1.6mm 3mm;border:.3mm solid {t.back_line};color:{t.back_ink};background:rgba(255,255,255,.7)}}
.instr{{margin-top:6mm;display:flex;align-items:center;gap:3mm}}
.instr .band{{width:6mm;height:6mm;background:{t.back_mid};flex:0 0 6mm}}
.instr .k{{font-family:'Mono',monospace;font-size:2.6mm;letter-spacing:.26em;text-transform:uppercase;color:{t.back_ink};opacity:.6}}
.instr .v{{font-family:'Display',sans-serif;font-weight:700;font-size:5.2mm;letter-spacing:.03em;text-transform:uppercase;color:{t.back_ink}}}
.bfoot{{margin-top:auto;border-top:.45mm solid {t.back_ink};padding-top:3.4mm;display:flex;justify-content:space-between;align-items:flex-end;gap:6mm}}
.bfoot .k{{font-family:'Mono',monospace;font-size:2.5mm;letter-spacing:.22em;text-transform:uppercase;margin-bottom:1.5mm;color:{t.back_mid}}}
.bfoot .v{{font-family:'Display',sans-serif;font-weight:600;font-size:6mm;letter-spacing:.05em;text-transform:uppercase;line-height:1}}
.bfoot .v small{{font-family:'Mono',monospace;font-weight:400;font-size:3mm;letter-spacing:.1em;color:{t.back_ink};opacity:.7;text-transform:none}}
.bfoot .right{{text-align:right}}
"""


def page_html(book: dict, fonts: str, logo_b64: str) -> str:
    code = book['code']
    t, c = THEMES[code], COPY[code]
    plate = PLATES[code]()
    names = sittings(book)
    level = 'IGCSE' if book['level'] == 'IGCSE' else 'IAL'
    board = f'{level} &nbsp;Edexcel &nbsp;&middot;&nbsp; {code}'
    first, last = names[0].split(), names[-1].split()
    span = f'{SEASON_SHORT[first[0]]} {first[1]} &mdash; {SEASON_SHORT[last[0]]} {last[1]}'
    count = f"{book['sessions_count']} sittings &middot; {book['papers']} papers"
    brk = ' ' if c.inline else '<br>'
    thin = f'{brk}<span class="thin">{html.escape(c.thin)}</span>' if c.thin else ''
    logo = f'<div class="logo"><img src="data:image/jpeg;base64,{logo_b64}"></div>'
    items = ''.join(f'<li><span class="n">{i:02d}</span><span class="t">{html.escape(n)}</span></li>'
                    for i, n in enumerate(names, 1))
    columns = 2 if len(names) <= 12 else 3
    swatch = ''.join(f'<i style="background:{x}"></i>' for x in (t.ink, t.muted, t.accent, rgba(t.ink, .55)))
    regs = '<div class="reg tl"></div><div class="reg tr"></div><div class="reg bl"></div><div class="reg br"></div>'
    foot_brand = ('<div><div class="k">Published by</div><div class="v">Tri Axis Education</div></div>'
                  '<div class="right"><div class="k">Powered by</div>'
                  '<div class="v">GradeMax<br><small>grademax.me</small></div></div>')
    full = f'{c.title} {c.thin}'.strip()
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(full)} &middot; {code} &middot; Year-Wise</title>
<style>{fonts}
{css(t, columns)}</style></head><body>
<section class="page front">
  <div class="hair"></div><div class="hair2"></div>{regs}
  <div class="plate-wrap">{plate}</div>
  {logo}
  <div class="title">
    <div class="kick">Year-Wise Question Paper</div>
    <h1>{html.escape(c.title)}{thin}</h1>
    <div class="rule"></div>
    <div class="board">{board}</div>
  </div>
  <div class="foot">
    <div class="row"><div><div class="cw">Year-Wise Question Paper</div>
      <div class="by">by <b>{INSTRUCTOR}</b></div></div>
      <div class="range"><b>{span}</b><br>{count}</div></div>
    <div class="rule2">{foot_brand}</div>
  </div>
  <div class="swatch">{swatch}</div>
</section>
<section class="page back">
  <div class="grid"></div>
  <div class="corner">{plate}</div>
  <div class="hair"></div>{regs}
  <div class="inner">
    <div class="bhead">
      <div><div class="eyebrow">{html.escape(full)} &nbsp;&middot;&nbsp; {level} Edexcel {code}</div>
        <h2>Every paper,<br>year by year.</h2></div>
      {logo}
    </div>
    <p class="blurb">A year-wise question paper collection for {html.escape(c.subject)} &mdash; every
      paper from {names[0]} to {names[-1]}, arranged by session, so you work through the exam exactly
      as it was sat.</p>
    <p class="blurb">Sit each paper to time, then mark it against the official mark scheme on
      grademax.me. {html.escape(c.topics)} &mdash; the real questions in the real order.</p>
    <div class="idx"><div class="lab">Sittings included &nbsp;&middot;&nbsp; <b>{count}</b></div>
      <ol>{items}</ol></div>
    <div class="tags"><span>Full past papers</span><span>Original layout</span>
      <span>Year-by-year order</span><span>Timed practice</span></div>
    <div class="instr"><span class="band"></span><span class="k">Course Instructor</span>
      <span class="v">{INSTRUCTOR}</span></div>
    <div class="bfoot">{foot_brand}</div>
  </div>
</section></body></html>"""


def render(books: list[dict]) -> list[Path]:
    from playwright.sync_api import sync_playwright

    fonts = (ASSETS / 'fonts.css').read_text(encoding='utf-8')
    logo_b64 = base64.b64encode((ASSETS / 'tri_axis_logo.jpg').read_bytes()).decode()
    (OUT / 'Covers').mkdir(parents=True, exist_ok=True)
    (OUT / 'Editable_HTML').mkdir(parents=True, exist_ok=True)
    made = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        for book in books:
            doc = page_html(book, fonts, logo_b64)
            src = OUT / 'Editable_HTML' / f"{book['code']}_YearWise_QP_Cover_editable.html"
            src.write_text(doc, encoding='utf-8')
            page.goto(src.as_uri())
            page.evaluate('document.fonts.ready')
            pdf = OUT / 'Covers' / f"{book['code']}_YearWise_QP_Blueprint_Cover.pdf"
            page.pdf(path=str(pdf), width='210mm', height='297mm', print_background=True,
                     margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
            made.append(pdf)
            print(f"  cover {book['code']:6s} -> {pdf.relative_to(ROOT)}")
        browser.close()
    return made


def previews(books: list[dict]) -> None:
    import fitz
    from PIL import Image, ImageDraw

    (OUT / 'Previews').mkdir(parents=True, exist_ok=True)
    sheets: dict[int, list[Image.Image]] = {0: [], 1: []}
    for book in books:
        pdf = OUT / 'Covers' / f"{book['code']}_YearWise_QP_Blueprint_Cover.pdf"
        with fitz.open(pdf) as d:
            assert len(d) == 2, f'{pdf.name}: expected 2 pages, got {len(d)}'
            for i, side in enumerate(('Front', 'Back')):
                pix = d[i].get_pixmap(dpi=110)
                img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                img.save(OUT / 'Previews' / f"{book['code']}_{side}.png")
                sheets[i].append(img.resize((300, 424)))
    for i, side in ((0, 'Fronts'), (1, 'Backs')):
        tiles = sheets[i]
        cols = 5
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 316 + 16, rows * 456 + 16), '#2B3036')
        draw = ImageDraw.Draw(sheet)
        for k, (img, book) in enumerate(zip(tiles, books)):
            x, y = 16 + (k % cols) * 316, 16 + (k // cols) * 456
            sheet.paste(img, (x, y))
            draw.text((x, y + 428), f"{book['code']}  {THEMES[book['code']].name}", fill='#D8DDE2')
        sheet.save(OUT / f'Overview_{side}.png')


def apply_to_books(books: list[dict]) -> list[dict]:
    """Swap page 0 and the last page of each finished book for the new covers.

    The two cover pages are replaced; every interior page object, its links,
    the page labels and the bookmarks are kept and then checked.
    """
    import fitz

    (OUT / 'Books').mkdir(parents=True, exist_ok=True)
    report = []
    for book in books:
        src_pdf = SOURCE_BOOKS / Path(book['source_pdf']).name
        cover = OUT / 'Covers' / f"{book['code']}_YearWise_QP_Blueprint_Cover.pdf"
        out = OUT / 'Books' / src_pdf.name
        with fitz.open(src_pdf) as src, fitz.open(cover) as art:
            before = {'pages': len(src), 'toc': src.get_toc(simple=True),
                      'links': interior_links(src)}
            labels = src.get_page_labels()
            meta = src.metadata
            last = len(src) - 1
            # Build a fresh document: front cover, every interior page in ONE
            # insert (so their internal links survive), back cover. Editing the
            # covers in place corrupted objects: deleting page 0 rewrote the
            # outline (its root bookmark points at the cover) and later saves
            # reused numbers the grafted cover still referenced.
            book_doc = fitz.open()
            book_doc.insert_pdf(art, from_page=0, to_page=0)
            book_doc.insert_pdf(src, from_page=1, to_page=last - 1)
            book_doc.insert_pdf(art, from_page=1, to_page=1)
        with book_doc:
            book_doc.set_toc(before['toc'])
            if labels:
                book_doc.set_page_labels(labels)
            title = f"{COPY[book['code']].subject} - Year-Wise Questions {names_span(book)}"
            book_doc.set_metadata({**meta, 'title': f'GradeMax {title}',
                                   'author': 'GradeMax / Tri Axis Education'})
            book_doc.save(out, garbage=3, deflate=True)
        report.append(verify_book(book, out, before))
        print(f"  book  {book['code']:6s} {report[-1]['pages']}pp  errors={report[-1]['errors']}")
    return report


def interior_links(doc) -> list[list[tuple]]:
    return [[(l.get('kind'), l.get('page'), l.get('uri')) for l in doc[i].get_links()]
            for i in range(1, len(doc) - 1)]


def names_span(book: dict) -> str:
    return f"{book['first_session']['year']}-{book['last_session']['year']}"


def verify_book(book: dict, out: Path, before: dict) -> dict:
    import fitz

    errors = []
    with fitz.open(out) as d:
        if len(d) != before['pages']:
            errors.append(f"page count {len(d)} != {before['pages']}")
        if d.get_toc(simple=True) != before['toc']:
            errors.append('bookmarks changed')
        links = interior_links(d)
        if links != before['links']:
            errors.append(f"interior links changed ({sum(map(len, links))} vs "
                          f"{sum(map(len, before['links']))})")
        front = d[0].get_text().upper()
        back = d[-1].get_text().upper()
        c = COPY[book['code']]
        if c.title.upper() not in front or 'YEAR-WISE QUESTION PAPER' not in front:
            errors.append('front cover text missing')
        if 'EVERY PAPER' not in back or INSTRUCTOR.upper() not in back:
            errors.append('back cover text missing')
        for name in sittings(book):
            if name.upper() not in back:
                errors.append(f'back cover missing sitting {name}')
        for i in (0, len(d) - 1):
            fitz.TOOLS.reset_mupdf_warnings()
            d[i].get_pixmap(dpi=20)
            if 'syntax' in fitz.TOOLS.mupdf_warnings():
                errors.append(f'cover page {i} renders with syntax errors')
        pages = len(d)
    return {'code': book['code'], 'book': str(out.relative_to(ROOT)), 'pages': pages, 'errors': errors}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--books', action='store_true', help='also put the covers on the 13 books')
    ap.add_argument('--only', nargs='*', help='subject codes to build')
    args = ap.parse_args()
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    books = [b for b in catalog if not args.only or b['code'] in args.only]
    missing = [b['code'] for b in books if b['code'] not in PLATES or b['code'] not in THEMES]
    if missing:
        raise SystemExit(f'no plate/theme for {missing}')
    OUT.mkdir(parents=True, exist_ok=True)
    render(books)
    previews(books)
    if args.books:
        report = apply_to_books(books)
        (OUT / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        bad = [r for r in report if r['errors']]
        if bad:
            raise SystemExit(f'{len(bad)} book(s) failed verification; see verification.json')
        print(f'all {len(report)} books verified')


if __name__ == '__main__':
    main()
