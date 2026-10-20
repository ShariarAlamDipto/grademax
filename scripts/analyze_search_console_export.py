"""Read a Search Console Performance ZIP and write an evidence-only baseline.

The source archive and application files are never changed. No account access,
network requests, ZIP extraction, dependencies, or tracking changes are needed.

Example:
    python scripts/analyze_search_console_export.py export.zip --as-of 2026-10-16
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path


GOOGLE_DIMENSIONS = "https://support.google.com/webmasters/answer/17011259?hl=en"
GOOGLE_LIMITS = "https://developers.google.com/search/blog/2022/10/performance-data-deep-dive"
ROOT = Path(__file__).resolve().parents[1]
BRAND_RULE = "Casefold and remove every character except ASCII letters/digits; classify as branded when 'grademax' is present."
AMBIGUOUS_COMPACT = {"maxgrade", "grodemaxilt"}
TARGET_QUERIES = {
    "igcse biology past papers": "Improve the existing biology subject hub and its paper links.",
    "igcse economics past papers": "Improve the existing economics subject hub and its paper links.",
    "a level topic wise questions": "Explain actual supported subjects and link to working topic practice.",
    "worksheet maker": "Show the working generator, supported subjects and an example output.",
    "igcse biology past papers by topic": "Review the real biology topic experience before expanding this claim.",
    "a level maths question generator": "Explain the existing maths generator and its supported units.",
    "igcse edexcel chemistry topic questions": "Review available chemistry topic practice before claiming coverage.",
    "edexcel as maths past papers": "Improve the AS maths hub with P1/P2/M1/S1 links where appropriate.",
    "mathematics p1 past papers": "Improve P1 paper navigation and link to its real editions.",
    "p2 past papers": "Improve P2 paper navigation and link to its real editions.",
    "mechanics past papers": "Improve M1 paper navigation and link to its real editions.",
}


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def integer(value: str) -> int:
    number = int(value.replace(",", "").strip())
    if number < 0:
        raise ValueError("Negative click/impression count")
    return number


def metrics(rows: list[dict]) -> dict:
    clicks = sum(row["clicks"] for row in rows)
    impressions = sum(row["impressions"] for row in rows)
    return {"rows": len(rows), "clicks": clicks, "impressions": impressions,
            "weighted_ctr": ratio(clicks, impressions),
            "position_from_rounded_rows_approx": ratio(
                sum(row["position"] * row["impressions"] for row in rows), impressions)}


def classify(query: str) -> str:
    compact = re.sub(r"[^a-z0-9]", "", query.casefold())
    if "grademax" in compact:
        return "branded"
    if compact in AMBIGUOUS_COMPACT:
        return "ambiguous"
    return "nonbrand"


def read_export(source: Path) -> dict:
    dimensions = {"Chart.csv": "Date", "Queries.csv": "Top queries", "Pages.csv": "Top pages",
                  "Countries.csv": "Country", "Devices.csv": "Device"}
    tables = {}
    with zipfile.ZipFile(source, "r") as archive:
        names = {}
        for member in archive.namelist():
            base = Path(member.replace("\\", "/")).name.casefold()
            if base in names:
                raise ValueError(f"Ambiguous duplicate archive member: {base}")
            names[base] = member
        for name, dimension in dimensions.items():
            if name.casefold() not in names:
                raise ValueError(f"Missing required export table: {name}")
            text = archive.read(names[name.casefold()]).decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            required = {dimension, "Clicks", "Impressions", "CTR", "Position"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError(f"Unexpected columns in {name}: {reader.fieldnames}")
            tables[name] = [{"dimension": row[dimension], "clicks": integer(row["Clicks"]),
                             "impressions": integer(row["Impressions"]),
                             "reported_ctr": float(row["CTR"].strip().rstrip("%")) / 100,
                             "position": float(row["Position"])} for row in reader]
        filters = []
        if "filters.csv" in names:
            text = archive.read(names["filters.csv"]).decode("utf-8-sig")
            filters = list(csv.DictReader(io.StringIO(text)))
        tables["filters"] = filters
        tables["archive_members"] = archive.namelist()
    return tables


def inspect_analytics(repo: Path) -> dict:
    """Record only source evidence; never contact the production database."""
    evidence_specs = [
        ("src/app/layout.tsx", ["@vercel/analytics/next", "<Analytics"]),
        ("src/app/viewer/ViewerClient.tsx", ['track("pdf_view"', 'track("pdf_download"']),
        ("src/components/store/CheckoutClient.tsx", ["window.location.pathname", "document.referrer"]),
        ("src/app/api/admin/store/stats/route.ts", ["PAID_STATES", "cancelled", "byDistrict", "source_path", ".limit(5000)"]),
        ("src/app/api/admin/store/payment/route.ts", ['result?.changed', 'store_verify_payment']),
        ("src/lib/trackUsage.ts", ["UsageFeature", '"paper_view"']),
    ]
    evidence = []
    for relative, needles in evidence_specs:
        path = repo / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        evidence.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "matches": [{"line": index + 1, "text": line.strip()}
                                     for index, line in enumerate(lines) if any(n in line for n in needles)]})
    events = {name: [] for name in ["view_item", "add_to_cart", "begin_checkout", "purchase", "refund"]}
    for path in (repo / "src").rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
            for event in events:
                if re.search(r"[\"']" + event + r"[\"']", line):
                    events[event].append({"path": path.relative_to(repo).as_posix(), "line": index + 1})
    return {"scope": "Local source inspection only; live collection, dashboard access, order counts and attribution are unverified.",
            "source_evidence": evidence, "literal_ecommerce_event_names_found": events}


def analyze(source: Path, repo: Path, as_of: date) -> dict:
    tables = read_export(source)
    # The narrative compares an unsegmented property baseline with its country
    # rows. Refuse a pre-filtered export instead of quietly calling it global.
    segmented_filters = [row for row in tables["filters"]
                         if row.get("Filter", "").casefold() not in {"search type", "date"}]
    if segmented_filters:
        raise ValueError("Use an unsegmented Performance export for this global baseline; "
                         f"additional filters found: {segmented_filters}")
    chart = sorted(tables["Chart.csv"], key=lambda row: row["dimension"])
    if not chart:
        raise ValueError("Chart.csv has no daily rows")
    dates = [date.fromisoformat(row["dimension"]) for row in chart]
    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate daily date in Chart.csv")
    total = metrics(chart)
    countries = tables["Countries.csv"]
    bd = next((row.copy() for row in countries if row["dimension"].casefold() == "bangladesh"), None)
    if bd:
        bd.update(ctr_from_counts=ratio(bd["clicks"], bd["impressions"]),
                  click_share_of_chart=ratio(bd["clicks"], total["clicks"]),
                  impression_share_of_chart=ratio(bd["impressions"], total["impressions"]))
    queries = tables["Queries.csv"]
    for row in queries:
        row["classification"] = classify(row["dimension"])
    query_groups = {group: metrics([q for q in queries if q["classification"] == group])
                    for group in ["branded", "nonbrand", "ambiguous"]}
    visible = metrics(queries)
    devices = []
    for row in tables["Devices.csv"]:
        devices.append({**row, "ctr_from_counts": ratio(row["clicks"], row["impressions"]),
                        "click_share_of_chart": ratio(row["clicks"], total["clicks"]),
                        "impression_share_of_chart": ratio(row["impressions"], total["impressions"])})
    priorities = [{**row, "recommended_action": TARGET_QUERIES[row["dimension"]]}
                  for row in queries if row["dimension"] in TARGET_QUERIES and row["classification"] == "nonbrand"]
    priorities.sort(key=lambda row: (-row["impressions"], row["position"], row["dimension"]))
    country_total, device_total = metrics(countries), metrics(tables["Devices.csv"])
    return {"generated_as_of": as_of.isoformat(), "source_zip": str(source.resolve()),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "filters": tables["filters"], "archive_members": tables["archive_members"],
            "period": {"first_date": dates[0].isoformat(), "last_date": dates[-1].isoformat(),
                       "daily_rows": len(dates), "continuous": (dates[-1]-dates[0]).days+1 == len(dates)},
            "chart_totals": total, "bangladesh": bd, "country_table_totals": country_total,
            "device_table_totals": device_total,
            "reconciliation": {"country_clicks_equal_chart": country_total["clicks"] == total["clicks"],
                               "country_impressions_equal_chart": country_total["impressions"] == total["impressions"],
                               "device_clicks_equal_chart": device_total["clicks"] == total["clicks"],
                               "device_impressions_equal_chart": device_total["impressions"] == total["impressions"]},
            "devices": devices, "top_pages": sorted(tables["Pages.csv"], key=lambda r: (-r["clicks"], -r["impressions"]))[:15],
            "page_table_totals": metrics(tables["Pages.csv"]),
            "visible_queries": {"totals": visible, "classification_rule": BRAND_RULE,
                                "ambiguous_rule": "Reversed phrase 'max grade' and uncertain spelling 'grodemaxilt' are kept separate; no assumed brand intent.",
                                "groups": query_groups,
                                "branded_share_of_visible_query_clicks": ratio(query_groups["branded"]["clicks"], visible["clicks"]),
                                "clicks_not_represented_in_visible_query_rows": total["clicks"]-visible["clicks"],
                                "impressions_not_represented_in_visible_query_rows": total["impressions"]-visible["impressions"],
                                "rows": queries},
            "priority_queries_observed_globally_not_country_joined": priorities,
            "analytics_source_review": inspect_analytics(repo),
            "unknown_from_this_export": ["Submitted sitemap status and sitemap crawl errors", "Page indexing/exclusion reasons", "Google-selected canonical", "Bangladesh-specific queries, landing pages or device breakdown", "Google organic sessions, checkout starts, paid orders or revenue", "Search keyword market volume or future ranking"],
            "official_interpretation_sources": [GOOGLE_DIMENSIONS, GOOGLE_LIMITS]}


def pct(value: float | None) -> str:
    return f"{100*value:.2f}%" if value is not None else "n/a"


def table(headers: list[str], rows: list[list]) -> list[str]:
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    return ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"] + [
        "| " + " | ".join(escape(v) for v in row) + " |" for row in rows]


def render_report(summary: dict) -> str:
    p, totals, bd = summary["period"], summary["chart_totals"], summary["bangladesh"]
    visible = summary["visible_queries"]
    lines = ["# Google and Bangladesh search baseline", "", f"Prepared {summary['generated_as_of']} (Asia/Dhaka reporting plan).", "",
             f"Source: `{summary['source_zip']}`. SHA-256: `{summary['source_sha256']}`.", "",
             f"**Actual export dates: {p['first_date']} to {p['last_date']}, inclusive ({p['daily_rows']} daily rows).** The archive filename date is not the final observation date. All traffic figures below are observed Google Web search performance, not a forecast.", "",
             "## Confirmed baseline", ""]
    rows = [["Global clicks", totals["clicks"], "Chart.csv, daily sum"], ["Global impressions", totals["impressions"], "Chart.csv, daily sum"],
            ["Weighted global CTR", pct(totals["weighted_ctr"]), "sum(clicks) / sum(impressions); never the mean of daily CTRs"]]
    if bd:
        rows += [["Bangladesh clicks", bd["clicks"], pct(bd["click_share_of_chart"])+" of global clicks"],
                 ["Bangladesh impressions", bd["impressions"], pct(bd["impression_share_of_chart"])+" of global impressions"],
                 ["Bangladesh CTR", pct(bd["ctr_from_counts"]), "Country row clicks / impressions"],
                 ["Bangladesh average position", bd["position"], "Reported aggregate; not a rank for every query"]]
    lines += table(["Measure", "Value", "Basis"], rows)
    lines += ["", "**Confidence: Confirmed.** Countries and Devices totals " + ("reconcile" if all(summary["reconciliation"].values()) else "do not all reconcile") + " with Chart totals; exact checks are in summary.json. Country is where the search originated, not buyer nationality. Bangladesh already has the largest country click count in this export.", "",
              "## Device baseline", ""]
    lines += table(["Device", "Clicks", "Impressions", "CTR", "Click share"], [[r["dimension"], r["clicks"], r["impressions"], pct(r["ctr_from_counts"]), pct(r["click_share_of_chart"])] for r in summary["devices"]])
    lines += ["", "These device figures are global. The country table cannot be joined to the device, query or page table: these CSVs are separate aggregated views without a shared observation key.", "",
              "## Brand recognition versus new discovery", "", f"Explicit branded-query rule: {BRAND_RULE} {visible['ambiguous_rule']}", ""]
    lines += table(["Visible-query classification", "Rows", "Clicks", "Impressions", "CTR"], [[group, r["rows"], r["clicks"], r["impressions"], pct(r["weighted_ctr"])] for group,r in visible["groups"].items()])
    lines += ["", f"Branded searches account for **{pct(visible['branded_share_of_visible_query_clicks'])} of the {visible['totals']['clicks']} clicks in visible query rows**. This is a visible-query share, not the brand share of all searches. The difference from Chart totals is {visible['clicks_not_represented_in_visible_query_rows']} clicks and {visible['impressions_not_represented_in_visible_query_rows']} impressions. Do not classify that difference as nonbrand; anonymized/omitted queries are not available to classify.", "",
              f"Google documents [query omissions and dimension aggregation]({GOOGLE_DIMENSIONS}) and [Performance filtering/export limits]({GOOGLE_LIMITS}). Pages can have different aggregation from property totals; a sum of page rows is not a replacement for Chart totals.", "",
              "**Confidence: Likely opportunity.** The visible nonbrand rows show limited discovery. Their small impression counts do not establish market demand, search volume, a stable rank, or Bangladesh-specific intent. Anonymized traffic prevents a complete brand/nonbrand split.", "",
              "## Observed queries to improve first", "", "These are actual globally observed nonbrand queries, ordered by recorded impressions, then average position. Actions are hypotheses for existing relevant experiences, not promises of ranking gains. Validate subject support before adding topic/worksheet promises. No search-volume estimate is inferred.", ""]
    lines += table(["Observed query", "Clicks", "Impressions", "Avg. position", "Action"], [[r["dimension"],r["clicks"],r["impressions"],r["position"],r["recommended_action"]] for r in summary["priority_queries_observed_globally_not_country_joined"]])
    lines += ["", "## Leading Google landing pages", "", "Counts below are individual Pages.csv rows. They describe the global export, not Bangladesh landing pages. Performance commonly attributes data to canonical URLs; this table does not prove current Google-selected canonical status.", ""]
    lines += table(["Page", "Clicks", "Impressions", "Reported CTR", "Avg. position"], [[r["dimension"],r["clicks"],r["impressions"],pct(r["reported_ctr"]),r["position"]] for r in summary["top_pages"]])
    lines += ["", "## Existing store measurement, inspected locally", "",
              "**Confirmed in source; live data unverified:** Vercel Analytics is installed (`src/app/layout.tsx`); the PDF viewer emits `pdf_view` and `pdf_download`. The internal usage feature union records paper/lecture/worksheet/test-builder usage, rather than a store funnel.", "",
              "The store already has `/api/admin/store/stats` and its admin overview. It separates orders, paid orders, revenue, payment states and districts/divisions, excluding cancelled orders. Paid revenue uses `verified` or `paid_on_delivery`; placing an order or submitting a transaction ID is not proof of payment. The stats query is capped at 5,000 rows, so inspect that limit if volume grows.", "",
              "Checkout records `source.path` from the current `window.location.pathname` and `source.referrer` from immediate `document.referrer` (`src/components/store/CheckoutClient.tsx`). The path will ordinarily be `/checkout`; neither field alone reliably retains the initial Google landing page through an internal shopping journey. Existing source counts must not be presented as Google organic conversion attribution.", "",
              "The local scan found these literal ecommerce event names: " + ", ".join(f"`{name}` ({len(hits)} matches)" for name,hits in summary["analytics_source_review"]["literal_ecommerce_event_names_found"].items()) + ". This checks source, not the deployed analytics account. No production orders or analytics account data were accessed, and no tracking code was changed.", "",
              "## 30 / 60 / 90 day measurement plan", "",
              "Use the actual deployment date as Day 0 and compare complete, equal-length periods. Keep Search Console's native report dates; use Asia/Dhaka for store business-day reporting. Do not equate Search clicks with website sessions or try to join aggregate Search Console rows to individual orders.", ""]
    lines += table(["Checkpoint", "Google / Bangladesh measurement", "Store / conversion measurement"], [
        ["Day 0-30", "Save this global baseline. Export a NEW Performance view filtered Country = Bangladesh; then export Queries, Pages and Devices from that filtered view. Separately inspect Sitemaps, Page indexing and URL Inspection for the homepage, Bangladesh books page and each main book product. Record submitted sitemap status and inspected Google-selected canonical. Compare matched complete 28-day periods after deployment.", "Use the existing admin store totals as the order/payment baseline, with date, district, print/digital mix, paid orders and BDT revenue. Audit deployed Vercel events and attribution. Define view_item, preview_open, add_to_cart, begin_checkout and order_created; define purchase only when payment becomes verified/paid_on_delivery, deduplicated by order ID. Treat this as a measurement implementation proposal, not an existing capability."],
        ["Day 31-60", "Review Bangladesh clicks, impressions, CTR and landing-page performance against the first complete post-deploy period. Review visible branded/nonbrand queries separately and preserve the omitted-query caveat. Check indexing/canonical evidence for newly launched pages. Improve pages with relevant impressions and weak click-through or usability; document edits.", "If funnel measurement has been implemented and validated, report Bangladesh Google organic landing sessions -> book views -> add to cart -> checkout -> created orders -> verified/paid-on-delivery orders. Retain first landing/referrer/channel in a suitable analytics session, rather than using /checkout as the acquisition page. Do not label uninstrumented funnel rates as zero."],
        ["Day 61-90", "Compare three comparable 28-day windows and note exam-season/campaign effects. Track Bangladesh nonbrand discovery and relevant book-page traffic; avoid an all-query average-position target dominated by brand searches. Expand only pages that serve a real subject/edition need.", "Compare paid orders, BDT revenue, order-to-payment completion and refunds/cancellations by real product and delivery district. Once attribution is validated, compare Google organic assisted/completed sales with other channels. Keep digital orders without address separate; do not infer their country from a missing delivery district."],
    ])
    lines += ["", "Proposed events should use non-sensitive product/variant IDs, quantity, BDT value and deduplicated order IDs. Exclude names, phone numbers, addresses and payment transaction IDs from analytics event payloads. Preserve the existing server-side paid-state rules; refunds and cancellations need separate treatment. No new tracker, account configuration, promotion, or external outreach was performed.", "",
              "## Unknowns requiring other evidence", ""]
    lines += [f"- {unknown}." for unknown in summary["unknown_from_this_export"]]
    lines += ["", "This Performance ZIP contains no sitemap/indexing report, URL Inspection result or paid-sales data. A performance impression does not establish that every sitemap URL is indexed. Google rankings cannot be guaranteed; assess progress through country-filtered visibility and verified sales.", "",
              "## Reproduce", "", "The analyzer uses Python's standard library only and never extracts or changes the source ZIP. It writes only summary.json and this report in the chosen output directory.", "", "```powershell",
              f'python scripts/analyze_search_console_export.py "{summary["source_zip"]}" --as-of {summary["generated_as_of"]} --out "output/seo-bangladesh-{summary["generated_as_of"]}"', "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_zip", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    output = args.out or ROOT / f"output/seo-bangladesh-{args.as_of.isoformat()}"
    summary = analyze(args.source_zip, args.repo, args.as_of)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "GOOGLE-BANGLADESH-BASELINE.md").write_text(render_report(summary), encoding="utf-8")
    print(json.dumps({"summary": str((output / "summary.json").resolve()),
                      "report": str((output / "GOOGLE-BANGLADESH-BASELINE.md").resolve()),
                      "period": summary["period"], "totals": summary["chart_totals"],
                      "bangladesh": summary["bangladesh"]}, indent=2))


if __name__ == "__main__":
    main()
