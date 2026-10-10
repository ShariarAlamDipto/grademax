"""Render the difficulty-ranked Physics FAQ as a self-contained study page.

Takes the JSON produced by build_physics_difficulty_faq.py and writes one HTML
file with everything embedded, so the page works offline and can be published as
an artifact without a data fetch.

The page has three parts, because the archive supports three different claims:
  1. the questions that repeat verbatim, which can be answered from memory;
  2. where the hard marks sit, which repeat as a demand rather than as wording;
  3. the answers mark schemes explicitly refuse to credit.

Usage:
    python scripts/render_physics_difficulty_faq.py [--limit 120] [--out PATH]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "faq" / "physics_difficulty"

TIERS = {
    "banker": ("Banker", "Marks you should never drop. Learn the wording, not the idea."),
    "routine": ("Routine", "The bulk of every paper. Method matters more than recall."),
    "discriminator": ("Discriminator", "Where grades separate. Practise these deliberately."),
    "top-grade": ("Top grade", "The hardest marks on the paper. Leave time, then attack."),
}
TIER_ORDER = ("banker", "routine", "discriminator", "top-grade")

COMMAND_LABEL = {
    "recall": "state / give / name",
    "describe": "describe",
    "calculate": "calculate / determine",
    "explain": "explain / suggest",
    "apply": "draw / use",
    "other": "mixed",
}


def esc(text) -> str:
    return html.escape(str(text or ""), quote=True)


# A question paper's cover furniture occasionally survives into a stem. Cutting the
# stem at the marker keeps the published page clean without re-reading every PDF.
_COVER = re.compile(
    r"\s*(Paper reference|Centre Number|Candidate Number|Total Marks"
    r"|Turn over|Pearson Edexcel|You must have)\b.*$",
    re.I | re.S,
)

_PUA = re.compile("[\uf000-\uf0ff]")


_TRAILING_PAGENO = re.compile(r"\s+\d{1,2}\s*$")
# Edexcel's page-code barcode text, e.g. *P67160RA02932*, set inline in the margin.
_PAGECODE = re.compile(r"\*?P\d{5,6}[A-Z]{0,2}\d*\*?")


def clean(text: str) -> str:
    """Trim cover-page furniture and drop any unmapped Symbol-font leftovers."""
    out = _PAGECODE.sub("", _PUA.sub("", _COVER.sub("", text or "")))
    return _TRAILING_PAGENO.sub("", re.sub(r"\s{2,}", " ", out).strip()).strip()


# --------------------------------------------------------------------------- #
# section 1: questions that repeat verbatim
# --------------------------------------------------------------------------- #

def entry_html(entry: dict, index: int) -> str:
    points = entry.get("points") or []
    tariff = entry.get("tariff")
    tier = entry.get("tier", "routine")

    menu = entry.get("menu")
    credits = "".join(
        f'<li><button class="dot{" alt" if menu else ""}" aria-pressed="false" '
        f'aria-label="Mark point {n} learned">{"&bull;" if menu else n}</button>'
        f'<span class="pt">{esc(point)}</span></li>'
        for n, point in enumerate(points, 1)
    )
    if menu:
        credits = (
            f'<li class="menuhead">The scheme lists these as alternatives &mdash; '
            f'you need {tariff or "some"} of them, not all</li>' + credits
        )
    traps = "".join(f'<p class="trap">{esc(t)}</p>' for t in (entry.get("traps") or [])[:2])
    notes = entry.get("notes")
    note_html = f'<p class="note">{esc(notes)}</p>' if notes and not traps else ""
    why = "".join(f"<li>{esc(w)}</li>" for w in (entry.get("why_hard") or []))
    sittings = entry.get("sittings") or []
    seen = ", ".join(esc(s) for s in sittings[:6])
    more = f" +{len(sittings) - 6} more" if len(sittings) > 6 else ""
    search = esc(clean(entry["stem"] + " " + " ".join(points)).lower())

    return (
        f'<article class="q" data-tier="{esc(tier)}" data-topic="{entry["topic_n"]}"'
        f' data-text="{search}">'
        f'<header class="qh"><span class="pill t-{esc(tier)}">{esc(TIERS[tier][0])}</span>'
        f'<span class="topic">{esc(entry["topic"])}</span><span class="grow"></span>'
        f'<span class="freq">{entry["papers"]} papers</span>'
        + (f'<span class="tariff">({tariff})</span>' if tariff else "")
        + f'</header><h3 class="stem"><span class="n">{index}</span>{esc(clean(entry["stem"]))}</h3>'
        f'<ol class="credits">{credits}</ol>{traps}{note_html}'
        f'<details class="meta"><summary>Where it came up</summary>'
        f'<p class="sit">{seen}{more}</p>'
        + (f'<ul class="why">{why}</ul>' if why else "")
        + "</details></article>"
    )


# --------------------------------------------------------------------------- #
# section 2: where the hard marks are
# --------------------------------------------------------------------------- #

def hard_html(group: dict, widest: int) -> str:
    reasons = "".join(
        f'<li><span class="rn">{esc(r["n"])}</span>{esc(r["reason"])}</li>'
        for r in group.get("why_hard", [])[:4]
    )
    examples = ""
    for ex in group.get("examples", []):
        pts = "".join(f"<li>{esc(p)}</li>" for p in (ex.get("points") or [])[:6])
        note = f'<p class="note">{esc(ex["notes"])}</p>' if ex.get("notes") else ""
        examples += (
            f'<div class="ex"><p class="exs">{esc(clean(ex["stem"])[:400])}'
            + (f' <span class="tariff">({ex["tariff"]})</span>' if ex.get("tariff") else "")
            + f'</p><ol class="credits tight">{pts}</ol>{note}'
            f'<p class="sit">{esc(ex["sitting"])}</p></div>'
        )
    width = max(4, round(100 * group["marks"] / widest))
    return (
        f'<article class="hg"><header class="hgh">'
        f'<h3>{esc(group["topic"])}</h3>'
        f'<span class="cmd">{esc(COMMAND_LABEL.get(group["command"], group["command"]))}</span>'
        f'<span class="grow"></span>'
        f'<span class="freq">{group["questions"]} questions &middot; {group["papers"]} papers</span>'
        f'</header>'
        f'<div class="bar"><span style="width:{width}%"></span>'
        f'<b>{group["marks"]} marks</b></div>'
        f'<ul class="why big">{reasons}</ul>'
        f'<details class="meta"><summary>See {len(group.get("examples", []))} of these questions,'
        f' with the mark scheme</summary>{examples}</details></article>'
    )


# --------------------------------------------------------------------------- #
# section 3: answers that score zero
# --------------------------------------------------------------------------- #

def reject_html(row: dict) -> str:
    ctx = row.get("contexts", [{}])[0]
    accepted = " &middot; ".join(esc(a) for a in (ctx.get("accepted") or [])[:2])
    # The question it was asked in, rather than a derived topic label: topic
    # inference on a bare phrase like "scale" is unreliable, and the stem tells the
    # student when the ruling applies, which is what they actually need.
    stem = esc(clean(ctx.get("stem") or "")[:110])
    return (
        f'<article class="rj"><p class="bad">{esc(row["phrase"])}</p>'
        f'<p class="good">{accepted or "&mdash;"}</p>'
        f'<p class="rjm"><span class="ctx">{stem}</span>'
        f'<span class="freq">{row["papers"]} paper{"s" if row["papers"] != 1 else ""}</span>'
        f"</p></article>"
    )


# --------------------------------------------------------------------------- #

def build(entries: list[dict], hard: list[dict], rejects: list[dict],
          report: dict, limit: int, hard_limit: int, reject_limit: int,
          for_print: bool = False) -> str:
    entries = entries[:limit]
    hard = hard[:hard_limit]
    rejects = rejects[:reject_limit]

    tier_counts = Counter(e["tier"] for e in entries)
    topics = sorted({(e["topic_n"], e["topic"]) for e in entries})
    stats = report.get("report", [])
    n_papers = stats[0].split()[0] if stats else "?"
    verified = stats[1] if len(stats) > 1 else ""
    n_parts = report.get("tier_counts", {})
    total_parts = sum(n_parts.values())

    chips = "".join(
        f'<button class="chip c-{t}" data-tier="{t}" aria-pressed="false">'
        f'{TIERS[t][0]} <b>{tier_counts.get(t, 0)}</b></button>' for t in TIER_ORDER
    )
    options = "".join(f'<option value="{n}">{esc(name)}</option>' for n, name in topics)

    sections = ""
    for tier in TIER_ORDER:
        rows = [e for e in entries if e["tier"] == tier]
        if not rows:
            continue
        body = "".join(entry_html(e, i) for i, e in enumerate(rows, 1))
        sections += (
            f'<section class="tier" data-tier="{tier}">'
            f'<h3 class="th t-{tier}"><span>{esc(TIERS[tier][0])}</span>'
            f'<em>{esc(TIERS[tier][1])}</em><b>{len(rows)}</b></h3>{body}</section>'
        )

    widest = max((g["marks"] for g in hard), default=1)
    hard_body = "".join(hard_html(g, widest) for g in hard)
    reject_body = "".join(reject_html(r) for r in rejects)

    tier_bar = "".join(
        f'<span class="seg s-{t}" style="width:{100 * n_parts.get(t, 0) / max(total_parts, 1):.1f}%"'
        f' title="{esc(TIERS[t][0])}: {n_parts.get(t, 0)} parts"></span>'
        for t in TIER_ORDER
    )
    tier_key = "".join(
        f'<span class="k"><i class="s-{t}"></i>{esc(TIERS[t][0])} '
        f'<b>{100 * n_parts.get(t, 0) / max(total_parts, 1):.0f}%</b></span>'
        for t in TIER_ORDER
    )

    page = "".join([
        HEAD, CSS, PRINT_CSS if for_print else "",
        '<div class="wrap"><header class="top">',
        "<h1>Every mark point worth memorising</h1>",
        '<p class="lede">Edexcel International GCSE Physics (4PH1). Every question paper '
        "and mark scheme from 2018 to 2025, read end to end, reduced to the questions that "
        "keep coming back &mdash; answered in the examiner&rsquo;s own words, ranked by how "
        "hard the marks are to get.</p>",
        '<div class="stats">',
        f'<div class="stat"><b>{esc(n_papers)}</b><span>papers read</span></div>',
        f'<div class="stat"><b>{total_parts}</b><span>mark scheme cells</span></div>',
        f'<div class="stat"><b>{len(entries)}</b><span>repeat questions</span></div>',
        f'<div class="stat"><b>{len(rejects)}</b><span>zero-score answers</span></div>',
        "</div>",
        '<div class="ramp"><p class="ramplab">Every mark in the corpus, by tier</p>',
        f'<div class="bars">{tier_bar}</div><div class="keys">{tier_key}</div></div>',
        '<div class="howto"><h2>How to read an answer line</h2>',
        "<p>An Edexcel mark scheme separates its creditable points with a semicolon "
        "&mdash; one semicolon, one mark. Each numbered line below is one of those "
        "points, copied from the scheme. Write the lines, not an essay: a beautiful "
        "paragraph that misses a line scores nothing for it.</p>",
        '<p>Lines in <span class="inred">red</span> are the examiner&rsquo;s '
        "<code>reject</code> notes. They exist because enough candidates wrote that "
        "exact wrong thing to be worth warning markers about &mdash; which makes them "
        "the most valuable sentences on this page.</p></div>",
        '<nav class="nav"><a href="#repeats">1 &middot; Questions that repeat</a>'
        '<a href="#hard">2 &middot; Where the hard marks are</a>'
        '<a href="#zero">3 &middot; Answers that score zero</a></nav>',
        "</header>",

        '<section id="repeats" class="major"><h2>Questions that repeat</h2>',
        '<p class="intro">Every question here has been set in at least two separate '
        "papers since 2018, in wording close enough to answer the same way. The "
        "answer lines are the mark scheme&rsquo;s, not a paraphrase. "
        + ("Tick each box with a pen as you learn the line.</p>" if for_print
           else "Tap a number to tick a line off.</p>"),
        "" if for_print else
        f'<div class="controls">{chips}'
        f'<select id="topic" aria-label="Filter by topic"><option value="">All topics</option>'
        f'{options}</select>'
        '<input type="search" id="q" placeholder="Search: half-life, moment, refraction&hellip;"'
        ' aria-label="Search questions">'
        '<span class="count" id="count"></span></div>',
        sections,
        "" if for_print else '<p class="empty" id="empty" hidden>No question matches that filter.</p>',
        "</section>",

        '<section id="hard" class="major"><h2>Where the hard marks are</h2>',
        '<p class="intro">The hard marks do not repeat as wording &mdash; the context '
        "changes every session and only the demand comes back. So these are grouped by "
        "topic and command word, and ranked by how many marks the group is worth across "
        "the whole 2018&ndash;2025 window. If revision time is short, this is the "
        "order to spend it in.</p>",
        f'<div class="hgs">{hard_body}</div></section>',

        '<section id="zero" class="major"><h2>Answers that score zero</h2>',
        '<p class="intro">Each line is something a mark scheme explicitly refuses to '
        "credit. Examiners are only told to reject an answer when enough candidates "
        "give it, so this is the closest thing in the archive to a list of what "
        "students actually get wrong. The middle column is what the scheme accepts "
        "instead. Most of these rulings were written once; the count on the right "
        "shows the few that came back across several sittings.</p>",
        '<div class="rjh"><span>Do not write</span><span>Write this instead</span>'
        "<span>Where it was ruled</span></div>",
        f'<div class="rjs">{reject_body}</div></section>',

        "<footer><p><b>How this was built.</b> Every question paper and mark scheme in "
        f"the archive for 2018&ndash;2025 was parsed straight from the original PDFs. {esc(verified)} "
        "A question is used here only if its parsed marks add up to the total the paper "
        "itself prints for it; the rest were withheld rather than guessed at. Questions "
        "are grouped when their wording matches, and only groups appearing in two or "
        "more separate papers are shown.</p>",
        "<p><b>What difficulty means here.</b> Edexcel does not publish how well "
        "candidates actually scored on each question, so the tiers are modelled from "
        "what the mark scheme reveals: the tariff, the command word, whether the scheme "
        "spells out a rearrangement step, whether it warns about a unit conversion, "
        "whether it carries an error forward, and whether it names a common wrong "
        "answer. It is an informed estimate of where marks get lost, not a measurement "
        "of it.</p>",
        "<p><b>Two specifications.</b> 4PH1 was first sat in June 2019. The January 2019 "
        "and 2018 papers here are the legacy 4PH0, kept because the physics overlaps "
        "almost completely &mdash; but the paper structure differed, so treat them as "
        "extra practice rather than as a model of the paper you will sit.</p></footer>",
        "</div>", "" if for_print else SCRIPT,
    ])
    if for_print:
        # On paper there is nothing to expand, so every collapsed section is opened
        # and the disclosure triangle is hidden by the print stylesheet.
        page = page.replace('<details class="meta">', '<details class="meta" open>')
    return page


PRINT_CSS = """<style>
/* The print edition. A student revising from paper cannot filter or search, so the
   controls are gone and everything collapsible is open; the tick boxes stay because
   on paper they are ticked with a pen. Colour is kept -- the tier stripe and the red
   reject line are load-bearing, not decoration -- but the ground goes white so it
   does not drink a cartridge. */
:root{
 --paper:#FFFFFF; --card:#FFFFFF; --ink:#111820; --ink2:#454F59; --ink3:#6B7580;
 --rule:#C8D0D8; --shadow:none;
}
@page{size:A4;margin:13mm 12mm 14mm}
html,body{background:#fff}
body{font-size:9.6pt;line-height:1.42}
.wrap{max-width:none;padding:0}
h1{font-size:24pt;margin-bottom:6pt}
.lede{font-size:11pt;max-width:none;margin-bottom:12pt}
header.top{padding-top:0}
.nav,.controls,.empty{display:none}
.stats{break-inside:avoid}
.stat b{font-size:15pt}
.howto{break-inside:avoid;box-shadow:none;border:1px solid var(--rule);
 border-left:3pt solid var(--pen)}
.howto p{font-size:10pt}

.major{margin-top:16pt;break-before:page}
#repeats{break-before:auto}
.major>h2{font-size:16pt;margin-bottom:4pt}
.intro{font-size:10pt;margin-bottom:10pt;max-width:none}

.tier{margin-top:14pt;break-inside:auto}
.th{break-after:avoid;font-size:13pt;margin-bottom:8pt}
.q,.hg,.rj{break-inside:avoid;box-shadow:none;page-break-inside:avoid}
.q{padding:8pt 10pt;margin-bottom:6pt;border-color:var(--rule)}
.stem{font-size:11pt;margin-bottom:7pt}
.credits li{font-size:9.2pt;line-height:1.45}
.credits{padding-top:6pt;gap:3pt}
.dot{width:11pt;height:11pt;font-size:7pt;margin-top:1pt;
 -webkit-print-color-adjust:exact;print-color-adjust:exact}
.trap,.note{font-size:8.6pt;margin-top:6pt}
.meta{margin-top:6pt;padding-top:5pt}
.meta summary{display:none}
.meta .sit,.meta .why{font-size:8pt;margin-top:0}

.hg{padding:9pt 10pt;border-color:var(--rule)}
.hgh h3{font-size:12pt}
.exs{font-size:10pt}
.ex .credits li{font-size:8.8pt}

.rjh{font-size:7.6pt}
.rj{padding:5pt 8pt}
.bad,.good{font-size:9pt}
.ctx{font-size:9pt}
.rj:nth-child(odd){background:#F4F6F8;-webkit-print-color-adjust:exact;
 print-color-adjust:exact}

footer{margin-top:16pt;font-size:8.4pt;break-inside:avoid}
footer p{max-width:none}
.pill,.seg,.k i,.bar span{-webkit-print-color-adjust:exact;print-color-adjust:exact}
a{color:inherit;text-decoration:none}
</style>
"""

HEAD = (
    "<title>Physics Mark Point Drill</title>\n"
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&"
    'family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">\n'
)

CSS = """<style>
:root{
 --paper:#EDF0F3; --card:#FFFFFF; --ink:#16202B; --ink2:#57646F; --ink3:#87949F;
 --rule:#D4DBE2; --pen:#1D4E89; --credit:#176B4F; --reject:#A32B22;
 --t-banker:#2F7A5C; --t-routine:#1D4E89; --t-discriminator:#A8630B; --t-top-grade:#8A2F45;
 --shadow:0 1px 2px rgba(22,32,43,.05),0 6px 18px -12px rgba(22,32,43,.26);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#0F151A; --card:#171F26; --ink:#E4ECF2; --ink2:#9AA8B4; --ink3:#6C7B88;
 --rule:#27313A; --pen:#82B4E2; --credit:#4FBB90; --reject:#E5847C;
 --t-banker:#55B98D; --t-routine:#82B4E2; --t-discriminator:#DBA24A; --t-top-grade:#DE8296;
 --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px -14px rgba(0,0,0,.75);
}}
:root[data-theme="dark"]{
 --paper:#0F151A; --card:#171F26; --ink:#E4ECF2; --ink2:#9AA8B4; --ink3:#6C7B88;
 --rule:#27313A; --pen:#82B4E2; --credit:#4FBB90; --reject:#E5847C;
 --t-banker:#55B98D; --t-routine:#82B4E2; --t-discriminator:#DBA24A; --t-top-grade:#DE8296;
 --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 22px -14px rgba(0,0,0,.75);
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
 font-family:"Archivo",system-ui,-apple-system,"Segoe UI",sans-serif;
 font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1060px;margin:0 auto;padding:0 20px 80px}
:focus-visible{outline:2px solid var(--pen);outline-offset:2px}

header.top{padding:44px 0 0}
h1{font-size:clamp(29px,4.3vw,45px);line-height:1.05;margin:0 0 12px;
 letter-spacing:-.024em;font-weight:700;text-wrap:balance}
.lede{font-family:"Source Serif 4",Georgia,serif;font-size:17px;color:var(--ink2);
 max-width:64ch;margin:0 0 24px;line-height:1.55}
.stats{display:flex;flex-wrap:wrap;border:1px solid var(--rule);background:var(--card);
 border-radius:3px;overflow:hidden}
.stat{flex:1 1 160px;padding:11px 14px;border-right:1px solid var(--rule)}
.stat:last-child{border-right:0}
.stat b{display:block;font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:21px;
 font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.03em}
.stat span{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;
 color:var(--ink3);margin-top:4px}

.ramp{margin-top:14px}
.ramplab{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--ink3);
 margin:0 0 6px}
.bars{display:flex;height:9px;border-radius:2px;overflow:hidden;background:var(--rule)}
.seg{display:block;height:100%}
.s-banker{background:var(--t-banker)} .s-routine{background:var(--t-routine)}
.s-discriminator{background:var(--t-discriminator)} .s-top-grade{background:var(--t-top-grade)}
.keys{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px}
.k{font-size:11.5px;color:var(--ink2);display:inline-flex;align-items:center;gap:6px}
.k i{width:9px;height:9px;border-radius:2px;display:inline-block}
.k b{font-family:"IBM Plex Mono",monospace;font-weight:500;color:var(--ink3);
 font-variant-numeric:tabular-nums}

.howto{margin:26px 0 0;padding:16px 18px;border-left:3px solid var(--pen);
 background:var(--card);border-radius:0 3px 3px 0;box-shadow:var(--shadow)}
.howto h2{font-size:11px;text-transform:uppercase;letter-spacing:.11em;margin:0 0 9px;
 color:var(--pen);font-weight:700}
.howto p{margin:0 0 9px;font-family:"Source Serif 4",Georgia,serif;font-size:15.5px;
 color:var(--ink2);max-width:72ch;line-height:1.55}
.howto p:last-child{margin-bottom:0}
.howto code{font-family:"IBM Plex Mono",monospace;font-size:12.5px;background:var(--paper);
 padding:1px 5px;border-radius:2px;color:var(--ink)}
.inred{color:var(--reject);font-weight:600}

.nav{display:flex;flex-wrap:wrap;gap:0;margin:26px 0 0;border-top:1px solid var(--rule);
 border-bottom:2px solid var(--ink)}
.nav a{flex:1 1 200px;padding:12px 4px;color:var(--ink2);text-decoration:none;
 font-size:12.5px;font-weight:600;letter-spacing:.01em;border-right:1px solid var(--rule)}
.nav a:last-child{border-right:0}
.nav a:hover{color:var(--pen)}

.major{margin-top:46px}
.major>h2{font-size:24px;font-weight:700;letter-spacing:-.02em;margin:0 0 8px}
.intro{font-family:"Source Serif 4",Georgia,serif;font-size:15.5px;color:var(--ink2);
 max-width:70ch;margin:0 0 18px;line-height:1.55}

.controls{position:sticky;top:0;z-index:5;background:var(--paper);padding:12px 0;
 border-bottom:1px solid var(--rule);display:flex;flex-wrap:wrap;gap:7px;align-items:center}
.chip{font:inherit;font-size:12.5px;font-weight:600;cursor:pointer;padding:6px 11px;
 border-radius:2px;border:1px solid var(--rule);background:var(--card);color:var(--ink2);
 display:inline-flex;gap:6px;align-items:center}
.chip b{font-family:"IBM Plex Mono",monospace;font-weight:500;color:var(--ink3);
 font-variant-numeric:tabular-nums}
.chip[aria-pressed="true"]{color:#fff;border-color:transparent}
.c-banker[aria-pressed="true"]{background:var(--t-banker)}
.c-routine[aria-pressed="true"]{background:var(--t-routine)}
.c-discriminator[aria-pressed="true"]{background:var(--t-discriminator)}
.c-top-grade[aria-pressed="true"]{background:var(--t-top-grade)}
.chip[aria-pressed="true"] b{color:rgba(255,255,255,.72)}
select,input[type=search]{font:inherit;font-size:13px;padding:6px 9px;border-radius:2px;
 border:1px solid var(--rule);background:var(--card);color:var(--ink)}
input[type=search]{flex:1 1 200px;min-width:150px}
.count{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--ink3);
 font-variant-numeric:tabular-nums}
.empty{color:var(--ink3);font-size:14px;padding:22px 0}

.tier{margin-top:30px}
.th{display:flex;align-items:baseline;gap:12px;margin:0 0 13px;padding-bottom:8px;
 border-bottom:1px solid var(--rule);font-size:17px;font-weight:700;letter-spacing:-.012em}
.th em{font-style:normal;font-family:"Source Serif 4",Georgia,serif;font-size:13.5px;
 color:var(--ink2);font-weight:400;flex:1}
.th b{font-family:"IBM Plex Mono",monospace;font-size:12.5px;font-weight:500;color:var(--ink3)}
.t-banker span{color:var(--t-banker)} .t-routine span{color:var(--t-routine)}
.t-discriminator span{color:var(--t-discriminator)} .t-top-grade span{color:var(--t-top-grade)}

.q{background:var(--card);border:1px solid var(--rule);border-left-width:3px;
 border-radius:0 3px 3px 0;padding:14px 16px 12px;margin-bottom:9px;box-shadow:var(--shadow)}
.q[data-tier=banker]{border-left-color:var(--t-banker)}
.q[data-tier=routine]{border-left-color:var(--t-routine)}
.q[data-tier=discriminator]{border-left-color:var(--t-discriminator)}
.q[data-tier=top-grade]{border-left-color:var(--t-top-grade)}
.qh{display:flex;align-items:center;gap:8px;margin-bottom:9px;flex-wrap:wrap}
.pill{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
 padding:2px 7px;border-radius:2px;color:#fff}
.pill.t-banker{background:var(--t-banker)} .pill.t-routine{background:var(--t-routine)}
.pill.t-discriminator{background:var(--t-discriminator)}
.pill.t-top-grade{background:var(--t-top-grade)}
.topic{font-size:11.5px;color:var(--ink3)}
.grow{flex:1}
.freq,.tariff{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--ink3);
 font-variant-numeric:tabular-nums}
.tariff{color:var(--ink2);font-weight:600;border:1px solid var(--rule);padding:1px 6px;
 border-radius:2px}
.stem{font-family:"Source Serif 4",Georgia,serif;font-size:16.5px;font-weight:600;
 line-height:1.4;margin:0 0 11px;letter-spacing:-.004em;text-wrap:pretty}
.stem .n{font-family:"IBM Plex Mono",monospace;font-size:11.5px;font-weight:500;
 color:var(--ink3);margin-right:9px;vertical-align:1px}
.credits{list-style:none;margin:0;padding:10px 0 0;display:flex;flex-direction:column;
 gap:5px;border-top:1px dashed var(--rule)}
.credits li{display:flex;gap:9px;align-items:flex-start;font-family:"IBM Plex Mono",monospace;
 font-size:12.5px;line-height:1.55;color:var(--ink)}
.credits.tight{border-top:0;padding-top:6px;list-style:none;counter-reset:c}
.credits.tight li{padding-left:16px;position:relative;display:list-item}
.credits.tight li::before{content:"";position:absolute;left:2px;top:8px;width:5px;height:5px;
 border-radius:1px;background:var(--credit)}
.dot{flex:0 0 auto;width:18px;height:18px;border:1px solid var(--credit);border-radius:2px;
 background:transparent;color:var(--credit);font-family:"IBM Plex Mono",monospace;
 font-size:10px;font-weight:600;display:grid;place-items:center;margin-top:2px;
 cursor:pointer;padding:0;line-height:1}
.dot.alt{border-radius:50%;border-style:dashed}
.menuhead{font-family:"Archivo",sans-serif!important;font-size:11px!important;
 color:var(--ink3)!important;letter-spacing:.02em;display:block!important}
.dot[aria-pressed="true"]{background:var(--credit);color:var(--card)}
.dot[aria-pressed="true"]+.pt{color:var(--ink3);text-decoration:line-through;
 text-decoration-color:var(--rule)}
.pt{flex:1;min-width:0;overflow-wrap:anywhere}
.trap,.note{margin:10px 0 0;font-size:12px;font-family:"IBM Plex Mono",monospace;
 line-height:1.55;color:var(--ink2);padding-left:11px;border-left:2px solid var(--rule)}
.trap{border-left-color:var(--reject);color:var(--reject)}
.meta{margin-top:10px;border-top:1px dashed var(--rule);padding-top:8px}
.meta summary{font-size:11.5px;color:var(--ink3);cursor:pointer}
.meta .sit,.meta .why{font-family:"IBM Plex Mono",monospace;font-size:11px;
 color:var(--ink3);margin:8px 0 0;line-height:1.65}
.meta .why{padding-left:15px}
.q.hide,.tier.hide{display:none}

.hgs{display:grid;gap:10px}
.hg{background:var(--card);border:1px solid var(--rule);border-radius:3px;
 padding:15px 16px;box-shadow:var(--shadow)}
.hgh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.hgh h3{margin:0;font-size:16px;font-weight:700;letter-spacing:-.012em}
.cmd{font-family:"IBM Plex Mono",monospace;font-size:11.5px;color:var(--pen);
 border:1px solid var(--rule);padding:1px 7px;border-radius:2px}
.bar{display:flex;align-items:center;gap:10px;margin-bottom:11px}
.bar span{height:7px;background:var(--t-discriminator);border-radius:2px;display:block}
.bar b{font-family:"IBM Plex Mono",monospace;font-size:11.5px;font-weight:500;
 color:var(--ink3);font-variant-numeric:tabular-nums;white-space:nowrap}
.why{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}
.why.big li{display:flex;gap:9px;align-items:baseline;font-size:12.5px;color:var(--ink2)}
.rn{font-family:"IBM Plex Mono",monospace;font-size:11px;color:var(--ink3);
 min-width:26px;text-align:right;font-variant-numeric:tabular-nums}
.ex{border-top:1px dashed var(--rule);padding-top:11px;margin-top:11px}
.exs{font-family:"Source Serif 4",Georgia,serif;font-size:15px;font-weight:600;
 margin:0;line-height:1.42}
.ex .credits{border-top:0;padding-top:7px}
.ex .credits li{font-size:12px;color:var(--ink2)}
.ex .sit{margin-top:7px}

.rjh{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1.15fr);
 gap:16px;padding:0 14px 7px;font-size:10.5px;text-transform:uppercase;
 letter-spacing:.09em;color:var(--ink3);border-bottom:1px solid var(--rule)}
.rjs{display:flex;flex-direction:column}
.rj{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1.15fr);
 gap:16px;padding:10px 14px;border-bottom:1px solid var(--rule);align-items:baseline}
.rj:nth-child(odd){background:var(--card)}
.bad,.good{margin:0;font-family:"IBM Plex Mono",monospace;font-size:12.5px;line-height:1.5;
 overflow-wrap:anywhere}
.bad{color:var(--reject);text-decoration:line-through;text-decoration-thickness:1px}
.good{color:var(--credit)}
.rjm{margin:0;display:flex;flex-direction:column;gap:3px;min-width:0}
.ctx{font-family:"Source Serif 4",Georgia,serif;font-size:12.5px;color:var(--ink2);
 line-height:1.4;overflow-wrap:anywhere}

footer{margin-top:52px;padding-top:20px;border-top:1px solid var(--rule);
 font-size:12.5px;color:var(--ink3);line-height:1.65}
footer b{color:var(--ink2);font-weight:600}
footer p{max-width:76ch;margin:0 0 10px}
@media (max-width:680px){
 .stat{flex:1 1 50%;border-bottom:1px solid var(--rule)}
 .controls{position:static}
 .rjh{display:none}
 .rj{grid-template-columns:1fr;gap:4px}
 .rjm{flex-direction:row;gap:10px;text-align:left}
 .bad::before{content:"Not: ";text-decoration:none;display:inline-block}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
"""

SCRIPT = """<script>
(function(){
 var tiers=new Set(), topic="", term="";
 var count=document.getElementById("count"), empty=document.getElementById("empty");
 var KEY="4ph1-drill-v1", done={};
 try{ done=JSON.parse(localStorage.getItem(KEY)||"{}")||{}; }catch(e){ done={}; }
 function save(){ try{ localStorage.setItem(KEY,JSON.stringify(done)); }catch(e){} }

 function apply(){
  var shown=0;
  document.querySelectorAll(".q").forEach(function(q){
   var ok=(!tiers.size||tiers.has(q.dataset.tier))
        &&(!topic||q.dataset.topic===topic)
        &&(!term||q.dataset.text.indexOf(term)>=0);
   q.classList.toggle("hide",!ok); if(ok)shown++;
  });
  document.querySelectorAll(".tier").forEach(function(s){
   s.classList.toggle("hide",!s.querySelector(".q:not(.hide)"));
  });
  count.textContent=shown+" showing";
  empty.hidden=shown>0;
 }
 document.querySelectorAll(".chip").forEach(function(c){
  c.addEventListener("click",function(){
   var t=c.dataset.tier, on=c.getAttribute("aria-pressed")==="true";
   c.setAttribute("aria-pressed",on?"false":"true");
   if(on){tiers.delete(t);}else{tiers.add(t);}
   apply();
  });
 });
 document.getElementById("topic").addEventListener("change",function(e){
  topic=e.target.value; apply();
 });
 document.getElementById("q").addEventListener("input",function(e){
  term=e.target.value.trim().toLowerCase(); apply();
 });
 document.querySelectorAll("#repeats .q").forEach(function(q,qi){
  q.querySelectorAll(".dot").forEach(function(d,di){
   var id=qi+":"+di;
   if(done[id]){ d.setAttribute("aria-pressed","true"); }
   d.addEventListener("click",function(){
    var on=d.getAttribute("aria-pressed")==="true";
    d.setAttribute("aria-pressed",on?"false":"true");
    if(on){delete done[id];}else{done[id]=1;}
    save();
   });
  });
 });
 apply();
})();
</script>"""


CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def find_chrome() -> str | None:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    return shutil.which("chrome") or shutil.which("msedge") or shutil.which("chromium")


def print_pdf(html_path: Path, pdf_path: Path) -> None:
    """Drive headless Chrome to lay the print edition out on A4.

    Chrome is used rather than a Python PDF library because the page's layout is the
    deliverable -- the tier stripes, the tick boxes, the three-column reject table --
    and re-implementing it against a second rendering engine would be a second thing
    to keep correct.
    """
    browser = find_chrome()
    if not browser:
        raise SystemExit("no Chrome or Edge found to print with")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-first-run",
             f"--user-data-dir={profile}",
             "--no-pdf-header-footer",
             "--virtual-time-budget=20000",
             f"--print-to-pdf={pdf_path}", html_path.resolve().as_uri()],
            check=True, capture_output=True, timeout=300,
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--hard-limit", type=int, default=14)
    ap.add_argument("--reject-limit", type=int, default=40)
    ap.add_argument("--out", default=str(DATA / "physics_faq.html"))
    ap.add_argument("--pdf", nargs="?", const=str(DATA / "physics_faq.pdf"),
                    help="also write a print edition and render it to PDF")
    args = ap.parse_args()

    data = Path(args.data)
    load = lambda name: json.loads((data / name).read_text(encoding="utf-8"))  # noqa: E731
    payload = (load("entries.json"), load("hard_skills.json"), load("rejects.json"),
               load("build_report.json"))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        build(*payload, args.limit, args.hard_limit, args.reject_limit), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")

    if args.pdf:
        pdf = Path(args.pdf)
        print_html = pdf.with_suffix(".print.html")
        print_html.write_text(
            build(*payload, args.limit, args.hard_limit, args.reject_limit,
                  for_print=True), encoding="utf-8")
        print_pdf(print_html, pdf)
        import fitz
        with fitz.open(pdf) as doc:
            pages = doc.page_count
        print(f"wrote {pdf} ({pdf.stat().st_size / 1024:.0f} KB, {pages} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
