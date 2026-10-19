"""Minimal, dependency-free Markdown -> self-contained HTML with MathJax.

Deliberately tiny: handles the subset our generators emit (#/##/### headings,
**bold**, _italic_, > blockquote, --- rule, tables, paragraphs) while leaving
LaTeX math spans ($...$ and $$...$$) untouched so MathJax can render them.
"""
from __future__ import annotations
import html
import re

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script>
  window.MathJax = {{ tex: {{ inlineMath: [['$','$'], ['\\\\(','\\\\)']],
      displayMath: [['$$','$$'], ['\\\\[','\\\\]']] }},
    options: {{ skipHtmlTags: ['script','noscript','style','textarea','pre'] }} }};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
<style>
  :root {{ --ink:#1a1a2e; --muted:#5b6472; --line:#d8dde6; --accent:#2b59ff; --warn:#b91c1c; }}
  body {{ font-family: Georgia,'Times New Roman',serif; color:var(--ink); max-width:820px;
         margin:0 auto; padding:42px 32px 80px; line-height:1.55; background:#fff; }}
  h1 {{ font-size:1.55rem; margin:0 0 .2rem; }}
  h2 {{ font-size:1.15rem; color:var(--muted); font-weight:600; margin:.1rem 0 1rem; }}
  h3 {{ font-size:1.05rem; margin:1.4rem 0 .4rem; }}
  hr {{ border:0; border-top:1px solid var(--line); margin:1.2rem 0; }}
  blockquote {{ background:#fff7f6; border-left:3px solid var(--warn); color:#7a1f1f;
               margin:1rem 0; padding:.6rem .9rem; font-family:system-ui,sans-serif; font-size:.85rem; }}
  table {{ border-collapse:collapse; width:100%; margin:1rem 0; font-family:system-ui,sans-serif; font-size:.85rem; }}
  th,td {{ border:1px solid var(--line); padding:5px 9px; text-align:left; }}
  th {{ background:#f3f5f9; }}
  .marks {{ float:right; color:var(--muted); font-style:italic; }}
  p {{ margin:.5rem 0; }}
  code {{ background:#f3f5f9; padding:0 .25rem; border-radius:3px; font-size:.9em; }}
  @media print {{ a {{ color:inherit; text-decoration:none; }} body {{ padding:8mm; }} }}
</style></head><body>
{body}
</body></html>"""

_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<!\w)_(.+?)_(?!\w)"), r"<em>\1</em>"),
    (re.compile(r"`([^`]+?)`"), r"<code>\1</code>"),
]


def _protect_math(text: str) -> tuple[str, list[str]]:
    spans: list[str] = []

    def repl(m):
        spans.append(m.group(0))
        return f"\x00MATH{len(spans)-1}\x00"

    text = re.sub(r"\$\$.+?\$\$", repl, text, flags=re.S)
    text = re.sub(r"\$[^$\n]+?\$", repl, text)
    return text, spans


def _restore_math(text: str, spans: list[str]) -> str:
    for i, s in enumerate(spans):
        text = text.replace(f"\x00MATH{i}\x00", s)
    return text


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    for pat, rep in _INLINE:
        text = pat.sub(rep, text)
    return text


def md_to_html_body(md: str) -> str:
    md, spans = _protect_math(md)
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1; continue
        if ln.startswith("### "):
            out.append(f"<h3>{_inline(ln[4:])}</h3>")
        elif ln.startswith("## "):
            out.append(f"<h2>{_inline(ln[3:])}</h2>")
        elif ln.startswith("# "):
            out.append(f"<h1>{_inline(ln[2:])}</h1>")
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.startswith("> "):
            out.append(f"<blockquote>{_inline(ln[2:])}</blockquote>")
        elif ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: "):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            out.append(_table(rows)); continue
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{_inline(lines[i][2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        else:
            out.append(f"<p>{_inline(ln)}</p>")
        i += 1
    return _restore_math("\n".join(out), spans)


def _table(rows: list[str]) -> str:
    def cells(r):
        return [c.strip() for c in r.strip().strip("|").split("|")]
    header = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    h = "".join(f"<th>{_inline(c)}</th>" for c in header)
    b = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def render_page(title: str, md: str) -> str:
    return _PAGE.format(title=html.escape(title), body=md_to_html_body(md))
