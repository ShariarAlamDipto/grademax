#!/usr/bin/env python3
"""Collect paper PDF links from a Paperlords listing page, as a visitor would.

The listing is a client-rendered accordion: subjects contain sessions, sessions
contain units, and each unit has QP / MS buttons. The buttons carry no href —
the file URL lives in the page's own JavaScript state — so the only way to read
a link is to press the button and see where the browser is sent.

That is what this does, and no more: it opens the published page, expands the
accordions, presses the buttons for the sessions asked for, and records the URL
each press produces. The PDF transfer itself is **aborted** the moment the URL
is known, so nothing is downloaded here and the site is spared the bandwidth;
the files are fetched once, later, by `ingest_2026_papers.py ingest-urls`.

Output is a plain URL list (plus a JSON sidecar with the subject/session/paper
each link came from) ready to hand to that script.

Usage:
    python -X utf8 scripts/harvest_paperlords_links.py --level igcse --session 2026
    python -X utf8 scripts/harvest_paperlords_links.py --level ial --session 2026
    python -X utf8 scripts/harvest_paperlords_links.py --level igcse --session "Nov 2025" --out links.txt
"""
import argparse
import io
import json
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://www.paperlords.org"
ARCHIVE_GLOB = "**archive.paperlords.org**"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

EXPAND_ALL = """() => {
    let n = 0;
    for (const d of document.querySelectorAll('details:not([open])')) {
        d.open = true;
        d.dispatchEvent(new Event('toggle'));
        n++;
    }
    return n;
}"""


def expand_everything(page, rounds: int = 4) -> None:
    for _ in range(rounds):
        opened = page.evaluate(EXPAND_ALL)
        page.wait_for_timeout(1800)
        if not opened:
            return


def enumerate_targets(page, session_filter: str) -> list[dict]:
    """List every (subject, session, button) the filter selects, without clicking."""
    return page.evaluate(
        """(filter) => {
            const want = new RegExp(filter, 'i');
            const out = [];
            const subjects = [...document.querySelectorAll('details')].filter(d => {
                const s = d.querySelector('summary');
                return s && d.parentElement.closest('details') === null;
            });
            subjects.forEach((subj, si) => {
                const sname = (subj.querySelector('summary')?.innerText || '').trim().split('\\n')[0];
                [...subj.querySelectorAll('details')].forEach((sess, ei) => {
                    const ename = (sess.querySelector('summary')?.innerText || '').trim().split('\\n')[0];
                    if (!want.test(ename)) return;
                    [...sess.querySelectorAll('button[title]')].forEach((b, bi) => {
                        out.push({subject: sname, session: ename,
                                  title: b.getAttribute('title'),
                                  si: si, ei: ei, bi: bi});
                    });
                });
            });
            return out;
        }""", session_filter)


# Pressing a button opens a full-screen modal (an iframe PDF preview) which
# covers every other button, so it has to be dismissed between presses. Ad
# overlays appear the same way.
DISMISS = """() => {
    let n = 0;
    for (const b of document.querySelectorAll('button')) {
        const t = (b.getAttribute('aria-label') || b.innerText || '').trim();
        if (/^close\\s*(modal|ad|advertisement)$/i.test(t)) { b.click(); n++; }
    }
    return n;
}"""

BLOCKED = """() => {
    for (const el of document.querySelectorAll('div')) {
        const cs = getComputedStyle(el);
        if (cs.position === 'fixed' && parseInt(cs.zIndex || '0', 10) >= 50 &&
            cs.display !== 'none' && el.getBoundingClientRect().height > 300) return true;
    }
    return false;
}"""


def dismiss_overlays(page, tries: int = 4) -> bool:
    """Close any modal/ad covering the listing. True if the page is clear."""
    for _ in range(tries):
        if not page.evaluate(BLOCKED):
            return True
        page.evaluate(DISMISS)
        page.wait_for_timeout(350)
        if page.evaluate(BLOCKED):
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            page.wait_for_timeout(350)
    return not page.evaluate(BLOCKED)


def press(page, t: dict) -> bool:
    """Press one button by its position in the tree."""
    handle = page.evaluate_handle(
        """([si, ei, bi]) => {
            const subjects = [...document.querySelectorAll('details')].filter(
                d => d.parentElement.closest('details') === null);
            const sess = [...subjects[si].querySelectorAll('details')][ei];
            return [...sess.querySelectorAll('button[title]')][bi];
        }""", [t["si"], t["ei"], t["bi"]])
    el = handle.as_element()
    if not el:
        return False
    try:
        el.scroll_into_view_if_needed(timeout=5000)
        el.click(timeout=8000)
        return True
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--level", choices=("igcse", "ial"), default="igcse")
    ap.add_argument("--session", default="2026", help="regex matched against the session label")
    ap.add_argument("--subject", default=None, help="only this subject")
    ap.add_argument("--out", default=None, help="output .txt (default data/manifest/paperlords_<level>_links.txt)")
    ap.add_argument("--delay", type=float, default=0.35, help="seconds between presses")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    out_txt = Path(args.out) if args.out else ROOT / "data" / "manifest" / f"paperlords_{args.level}_links.txt"
    out_json = out_txt.with_suffix(".json")
    url = f"{BASE}/{args.level}"

    captured: list[str] = []
    records: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(user_agent=UA, viewport={"width": 1440, "height": 1200},
                                  locale="en-US", accept_downloads=True)

        # Record the URL, then abort: we want the address, not the file.
        def on_route(route):
            captured.append(route.request.url)
            try:
                route.abort()
            except Exception:
                pass

        ctx.route(ARCHIVE_GLOB, on_route)
        page = ctx.new_page()
        page.on("download", lambda d: captured.append(d.url))

        print(f"opening {url} ...")
        page.goto(url, wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2500)
        expand_everything(page)

        targets = enumerate_targets(page, args.session)
        if args.subject:
            targets = [t for t in targets if t["subject"].lower().startswith(args.subject.lower())]
        if args.limit:
            targets = targets[: args.limit]

        subjects = sorted({t["subject"] for t in targets})
        print(f"{len(targets)} buttons match session /{args.session}/ across {len(subjects)} subjects")
        print(f"subjects: {', '.join(subjects)}\n")

        for i, t in enumerate(targets, 1):
            if not dismiss_overlays(page):
                print("  !! an overlay will not close; stopping")
                break
            before = len(captured)
            ok = press(page, t)
            deadline = time.time() + 6
            while len(captured) == before and time.time() < deadline:
                page.wait_for_timeout(120)
            got = captured[-1] if len(captured) > before else None
            if got:
                records.append({**t, "url": got})
            dismiss_overlays(page)
            status = "ok " if got else ("no-url" if ok else "click-failed")
            print(f"  [{i:>4}/{len(targets)}] {t['subject'][:22]:22} {t['session'][:11]:11} "
                  f"{t['title'][:9]:9} {status}")
            time.sleep(args.delay)

        browser.close()

    # De-duplicate, preserving order.
    seen, urls = set(), []
    for r in records:
        u = r["url"].split("#")[0]
        if u not in seen:
            seen.add(u)
            urls.append(u)

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    header = [f"# harvested from {url} (session filter: {args.session})",
              f"# {len(urls)} unique paper links"]
    out_txt.write_text("\n".join(header + urls) + "\n", encoding="utf-8")
    out_json.write_text(json.dumps(records, indent=1), encoding="utf-8")

    print(f"\ncaptured {len(urls)} unique links from {len(records)} presses")
    try:
        print(f"written: {out_txt.relative_to(ROOT)}")
    except ValueError:
        print(f"written: {out_txt}")
    missed = len(targets) - len(records)
    if missed > 0:
        print(f"note: {missed} buttons produced no URL — re-run to pick them up")


if __name__ == "__main__":
    main()
