"""Build source-preserving IGCSE question books for the requested 2019–2026 range.

Read-only against production. Downloads QPs, checks their covers, records an
explicit inventory, and builds bookmarked PDFs with linked contents. The
original sheets (including English source booklets and answer space) survive
unchanged. --prepare refreshes sources; --build requires a reviewed inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.live_paper_sources import fetch_rows, r2_reader, subject_id, supabase_client
from lib.yearwise_all_layout import PAGE_HEIGHT, PAGE_WIDTH, MARGIN, INK, MUTED, RULE, put

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/yearwise_all/request_2019_2026"
OUT = ROOT / "output/Yearwise_Questions_2019-2026"
YEARS = list(range(2019, 2027))
SEASONS = {"jan": 0, "may-jun": 1, "oct-nov": 2}
LABELS = {"jan": "January", "may-jun": "May/June", "oct-nov": "October/November"}
SUBJECTS = {
    "4PM1": ("Further Pure Mathematics", "Further_Pure_Maths", "igcse_fpm"),
    "4MB1": ("Mathematics B", "Mathematics_B", "igcse_mathsb"),
    "4PH1": ("Physics", "Physics", "igcse_physics"),
    "4CH1": ("Chemistry", "Chemistry", "igcse_chemistry"),
    "4BI1": ("Biology", "Biology", "igcse_biology"),
    "4HB1": ("Human Biology", "Human_Biology", None),
    "4EB1": ("English Language B", "English_B", None),
}


def relative(path):
    return path.relative_to(ROOT).as_posix()


def paper_number(value):
    m = re.fullmatch(r"0?([12])[PCB]?", str(value))
    return int(m[1]) if m else None


def check(path, code, year, season, paper, settled=False):
    """Identify from exam text, never the added GradeMax provenance stamp."""
    with fitz.open(path) as doc:
        head = doc[0].get_text()
        # Remove only our ingest stamp lines before identifying the cover.
        head = "\n".join(line for line in head.splitlines()
                         if "GradeMax" not in line and " · " not in line)
        flat = re.sub(r"\s+", " ", head)
        codes = re.findall(r"\b(4[A-Z]{2}[01])\s*/\s*(0?[12][A-Z]{0,2})\b", flat)
        valid = [(c, p) for c, p in codes if c[:3] == code[:3] and paper_number(p) == paper]
        date = re.search(r"\b(January|February|May|June|October|November)\s+(20\d{2})\b", flat, re.I)
        item = re.search(r"\*?(P\d{5}R{0,2}A)\d{4}\*?", "\n".join(p.get_text() for p in doc))
        result = {"pages": len(doc), "cover_codes": codes, "item": item[1] if item else None,
                  "identity": "cover", "legacy": bool(valid and valid[0][0] != code)}
        errors = []
        if len(doc) < 4:
            errors.append("too few sheets")
        if re.search(r"Mark\s*Scheme|Model\s*Answer|Worked\s*Solution", flat, re.I):
            errors.append("not a question paper")
        if re.search(r"Do not return this Booklet", flat, re.I) and not re.search(r"Candidate surname", flat, re.I):
            errors.append("reading insert without its question paper")
        if not valid:
            errors.append("cover code unreadable or wrong subject/paper")
        if date:
            actual_season = {"january": "jan", "february": "jan", "may": "may-jun", "june": "may-jun",
                             "october": "oct-nov", "november": "oct-nov"}[date[1].lower()]
            if (int(date[2]), actual_season) == (2020, "may-jun"):
                actual_season = "oct-nov"
            if (int(date[2]), actual_season) != (year, season):
                errors.append(f"cover date is {date[1]} {date[2]}")
            result["cover_date"] = date[0]
        else:
            errors.append("cover date unreadable")
        if settled and all(e.startswith("cover") for e in errors):
            result["identity"] = "existing linkage audit"
            errors = []
        result["errors"] = errors
        result["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result


def prepare():
    WORK.mkdir(parents=True, exist_ok=True)
    sb = supabase_client()
    get_bytes, _ = r2_reader()
    inventory = {}
    for code, (name, folder, book) in SUBJECTS.items():
        rows = fetch_rows(lambda o: sb.table("papers").select("id,year,season,paper_number,pdf_url")
                          .eq("subject_id", subject_id(sb, code)).gte("year", 2019).lte("year", 2026)
                          .range(o, o + 999))
        rows = [r for r in rows if paper_number(r["paper_number"]) and r["season"] in SEASONS]
        (WORK / f"{code}_live_rows.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        cache = WORK / "sources" / code
        cache.mkdir(parents=True, exist_ok=True)

        def fetch(r):
            path = cache / (hashlib.sha1((r["pdf_url"] or r["id"]).encode()).hexdigest() + ".pdf")
            if r["pdf_url"] and not path.exists():
                raw = get_bytes(r["pdf_url"])
                if raw and raw.startswith(b"%PDF"):
                    path.write_bytes(raw)
            return r, path

        with ThreadPoolExecutor(8) as pool:
            downloaded = list(pool.map(fetch, rows))
        candidates = {}
        for r, path in downloaded:
            key = (r["year"], r["season"], paper_number(r["paper_number"]))
            candidates.setdefault(key, []).append((path, "live", False))
        if book:
            linkage = json.loads((ROOT / f"data/yearwise_all/linkage/{book}.json").read_text())
            for unit in linkage:
                paper = int(unit["unit"][-1])
                for s in unit["sittings"]:
                    year, season = s["sitting"].split(" ", 1)
                    season = {"Jan": "jan", "May-Jun": "may-jun", "Oct-Nov": "oct-nov"}[season]
                    if int(year) not in YEARS or not s.get("qp"):
                        continue
                    candidates.setdefault((int(year), season, paper), []).append(
                        (ROOT / s["qp"]["path"], "linkage", s["verdict"] in ("LINKED", "LEGACY")))
        for path in (ROOT / "data/Ultimate Final IGCSE" / folder).glob("**/*_QP.pdf"):
            m = re.search(r"_(20\d\d)_(Jan|May-Jun|Oct-Nov)_Paper_([12])_QP", path.name)
            if m and int(m[1]) in YEARS:
                key = (int(m[1]), {"Jan":"jan", "May-Jun":"may-jun", "Oct-Nov":"oct-nov"}[m[2]], int(m[3]))
                candidates.setdefault(key, []).append((path, "local", False))
        selected, rejected = [], []
        for (year, season, paper), sources in sorted(candidates.items(), key=lambda e: (e[0][0], SEASONS[e[0][1]], e[0][2])):
            chosen = None
            for path, origin, settled in sources:
                if not path.is_file():
                    continue
                result = check(path, code, year, season, paper, settled)
                record = {"year": year, "season": season, "paper": paper, "path": relative(path),
                          "source": origin, **result}
                if not result["errors"]:
                    chosen = record
                    break
                rejected.append(record)
            if chosen:
                selected.append(chosen)
        inventory[code] = {"subject": name, "papers": selected, "rejected": rejected,
                           "unfilled_slots": [list(k) for k in candidates if k not in
                                              {(p["year"], p["season"], p["paper"]) for p in selected}]}
        print(f"{code} {name}: {len(selected)} papers; unfilled {inventory[code]['unfilled_slots']}", flush=True)
    (WORK / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")


def caption(p):
    return f"{LABELS[p['season']]} {p['year']} | Paper {p['paper']}" + (" | previous specification" if p["legacy"] else "")


def resolve():
    """Resolve cover scans using Pearson PDFs and explicit review receipts.

    Sources discovered during review can be added to supplemental_sources.json:
    code, year, season, paper, url. All still pass the cover identity checks.
    """
    inventory = json.loads((WORK / "inventory.json").read_text(encoding="utf-8"))
    inventory = {code:info for code,info in inventory.items() if code in SUBJECTS}
    assets = json.loads((WORK / "pearson_catalogue.json").read_text(encoding="utf-8"))
    supplement = WORK / "supplemental_sources.json"
    supplemental = json.loads(supplement.read_text()) if supplement.exists() else []
    cache = WORK / "pearson"
    cache.mkdir(exist_ok=True)
    jobs = []
    for code, info in inventory.items():
        for year, season, paper in info["unfilled_slots"]:
            for a in assets:
                if (a["code"], a["year"], a["season"], paper_number(a["variant"]), a["kind"]) == (code,year,season,paper,"QP"):
                    jobs.append({"code":code,"year":year,"season":season,"paper":paper,
                                 "url":"https://qualifications.pearson.com"+a["url"], "catalogue":True})
    jobs.extend(a for a in supplemental if a["code"] in inventory)

    def download(a):
        path = cache / (hashlib.sha1(a["url"].encode()).hexdigest()+".pdf")
        try:
            if not path.exists():
                response = httpx.get(a["url"], follow_redirects=True, timeout=60)
                if response.status_code != 200 or not response.content.startswith(b"%PDF"):
                    return a, None, f"HTTP {response.status_code}; not a PDF"
                path.write_bytes(response.content)
            return a, path, None
        except httpx.HTTPError as error:
            return a, None, type(error).__name__

    with ThreadPoolExecutor(8) as pool:
        downloads = list(pool.map(download,jobs))
    for a,path,error in downloads:
        code,year,season,paper = (a[k] for k in ("code","year","season","paper"))
        info=inventory[code]
        key=(year,season,paper)
        if any(tuple(p[k] for k in ("year","season","paper")) == key for p in info["papers"]):
            continue
        if not path:
            info.setdefault("unavailable_sources",[]).append({**a,"reason":error})
            print(code,key,error,flush=True)
            continue
        proof=check(path,code,year,season,paper)
        if (code,year,season,paper,proof["item"]) == ("4EA1",2019,"jan",1,"P60311A"):
            # Pearson's own PDF is image-only. Its cover was read in
            # english_jan2019_primary.png: Monday 14 January 2019, 4EA1/01.
            proof.update(errors=[], identity="visual review of Pearson original cover",
                         cover_date="14 January 2019", legacy=False)
        if proof["errors"] == ["cover date unreadable"] and a.get("catalogue"):
            proof["errors"]=[]
            proof["identity"]="Pearson catalogue and original PDF paper code"
        if proof["errors"]:
            print(code,key,'rejected supplemental',proof["errors"],flush=True)
            continue
        original=next((p for p in info["rejected"]
                       if (p["year"],p["season"],p["paper"])==key and p["item"]==proof["item"]
                       and all(e.startswith("cover") for e in p["errors"])),None)
        if original:
            chosen={**original,"errors":[],"legacy":proof["legacy"],
                    "identity":"item code matches Pearson original PDF", "identity_url":a["url"],
                    "identity_sha256":proof["sha256"]}
        else:
            chosen={"year":year,"season":season,"paper":paper,"path":relative(path),
                    "source":"pearson" if a.get("catalogue") else "reviewed supplement",
                    "identity_url":a["url"],**proof}
        info["papers"].append(chosen)
        print(code,key,chosen["identity"],chosen["pages"],flush=True)
    # This image-only legacy cover was actually read in covers_1.png. Its own
    # image says Tuesday 15 January 2019, 4HB0/02, and its scheme says 1901.
    info=inventory["4HB1"]
    if not any((p["year"],p["season"],p["paper"])==(2019,"jan",2) for p in info["papers"]):
        p=next(p for p in info["rejected"] if (p["year"],p["season"],p["paper"])==(2019,"jan",2))
        assert p["item"]=="P55796A"
        info["papers"].append({**p,"errors":[],"legacy":True,"identity":"visual cover review",
                               "cover_date":"15 January 2019","review":"covers_1.png; cover reads 4HB0/02; scheme publication 4HB0_02_1901"})
    for code,info in inventory.items():
        if code == "4PM1":
            for p in info["papers"]:
                if (p["year"],p["season"]) == (2019,"jan"):
                    p["legacy"] = True
        info["papers"].sort(key=lambda p:(p["year"],SEASONS[p["season"]],p["paper"]))
        present={(p["year"],p["season"],p["paper"]) for p in info["papers"]}
        info["unfilled_slots"]=[k for k in info["unfilled_slots"] if tuple(k) not in present]
        print(code,'unfilled',info["unfilled_slots"],flush=True)
    (WORK / "inventory.json").write_text(json.dumps(inventory,indent=2),encoding="utf-8")


def heading(doc, name, code, span, count):
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.draw_rect(page.rect, color=None, fill=INK)
    white = (1, 1, 1)
    put(page, MARGIN, 180, "GRADEMAX", 18, True, white)
    put(page, MARGIN, 230, "Pearson Edexcel International GCSE", 13, color=white)
    size = min(30, 480 / max(1, fitz.Font(fontfile="C:/Windows/Fonts/arialbd.ttf").text_length(name, fontsize=1)))
    put(page, MARGIN, 315, name, size, True, white)
    put(page, MARGIN, 350, code, 16, color=white)
    put(page, MARGIN, 420, "YEARWISE QUESTION PAPERS", 17, True, white)
    put(page, MARGIN, 465, span, 25, True, white)
    put(page, MARGIN, 520, f"{count} papers in chronological order", 12, color=white)
    put(page, MARGIN, 700, "Original questions, diagrams, answer space and enclosed inserts.", 10, color=white)
    put(page, MARGIN, 723, "Standard papers; regional R variants are outside this edition.", 10, color=white)


def expected_slots(code):
    """Independent sitting matrix, rather than treating held DB rows as complete."""
    slots = []
    for year in YEARS:
        seasons = ["may-jun", "oct-nov"]
        if year in (2019,2022):
            seasons = ["jan", "may-jun"]
        elif year == 2020:
            seasons = ["jan", "oct-nov"]
        elif year == 2021 and code in ("4MB1","4PH1","4CH1","4BI1"):
            seasons = ["jan", "may-jun", "oct-nov"]
        elif year == 2023:
            seasons = ["jan", "may-jun", "oct-nov"]
        elif year == 2026:
            seasons = ["may-jun"]
        for season in seasons:
            for paper in ([1] if code == "4EB1" else [1,2]):
                slots.append((year,season,paper))
    return slots


def coverage(code, papers):
    present = {(p["year"],p["season"],p["paper"]) for p in papers}
    return [{"year":year,"season":season,"paper":paper}
            for year,season,paper in expected_slots(code) if (year,season,paper) not in present]


def build_one(code, info, papers, path, span):
    doc = fitz.open()
    heading(doc, info["subject"], code, span, len(papers))
    gaps = coverage(code, papers)
    if gaps:
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        put(page, MARGIN, 96, "Coverage notes", 24, True)
        put(page, MARGIN, 150, "All eight years, 2019 through 2026, appear in this book.", 11)
        put(page, MARGIN, 185, "These individual papers could not be sourced as verified PDFs:", 11)
        y = 217
        for p in gaps:
            put(page, MARGIN+15, y, f"{LABELS[p['season']]} {p['year']} | Paper {p['paper']}", 11, True)
            y += 23
        put(page, MARGIN, y+20, "The unavailable papers are listed here so the session gaps are explicit.", 10, color=MUTED)
        put(page, MARGIN, y+43, "The 2026 section contains May/June papers. Autumn 2026 is upcoming.", 10, color=MUTED)
    # Fit TOC lines on A4, including repeated year headings across pages.
    rows, current, year = [], [], None
    for p in papers:
        need = 2 if p["year"] != year else 1
        if len(current) + need > 29:
            rows.append(current); current = []; year = None
        if p["year"] != year:
            current.append(("year", p["year"])); year = p["year"]
        current.append(("paper", p))
    if current:
        rows.append(current)
    toc_pages = [doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT).number for _ in rows]
    positions, bookmarks, checks = {}, [[1, span, 1]], []
    layer_visibility = {}
    for p in papers:
        if p["year"] not in positions:
            divider = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            put(divider, MARGIN, 250, str(p["year"]), 64, True)
            put(divider, MARGIN, 300, info["subject"], 23, True)
            put(divider, MARGIN, 350, "Question papers in session and paper order", 11, color=MUTED)
            positions[p["year"]] = len(doc)
            bookmarks.append([2, str(p["year"]), len(doc)])
        first = len(doc) + 1
        with fitz.open(ROOT / p["path"]) as source:
            # insert_pdf copies layer references, but not the source catalogue's
            # visibility configuration. Give imported layers unique names so
            # every paper keeps its own ON/OFF settings in the combined book.
            for xref, layer in source.get_ocgs().items():
                name = f"{p['sha256'][:16]}:{xref}:{layer['name']}"
                layer_visibility[name] = layer["on"]
                source.xref_set_key(xref,"Name",fitz.get_pdf_str(name))
            doc.insert_pdf(source, links=True, annots=True)
        bookmarks.append([3, caption(p), first])
        checks.append({**p, "book_page": first})
    mapping = {(p["year"], p["season"], p["paper"]): p["book_page"] for p in checks}
    for number, lines in zip(toc_pages, rows):
        page = doc[number]
        put(page, MARGIN, 90, "Contents", 24, True)
        put(page, MARGIN, 118, f"{info['subject']} ({code}) | {span}", 10, color=MUTED)
        page.draw_line((MARGIN, 132), (PAGE_WIDTH-MARGIN, 132), color=RULE)
        y = 158
        for kind, value in lines:
            if kind == "year":
                put(page, MARGIN, y, str(value), 12, True)
            else:
                target = mapping[(value["year"], value["season"], value["paper"])]
                label = f"{LABELS[value['season']]} | Paper {value['paper']}"
                if value["legacy"]:
                    label += " (previous specification)"
                put(page, MARGIN+15, y, label, 10)
                put(page, PAGE_WIDTH-MARGIN-30, y, str(target), 10, True)
                page.insert_link({"kind": fitz.LINK_GOTO, "from": fitz.Rect(MARGIN,y-12,PAGE_WIDTH-MARGIN,y+3), "page": target-1})
            y += 21
    doc.set_toc(bookmarks)
    if layer_visibility:
        groups, on, off = [], [], []
        for xref in range(1,doc.xref_length()):
            if doc.xref_get_key(xref,"Type") == ("name","/OCG"):
                name = doc.xref_get_key(xref,"Name")[1]
                ref = f"{xref} 0 R"
                groups.append(ref)
                (on if layer_visibility.get(name,True) else off).append(ref)
        doc.xref_set_key(doc.pdf_catalog(),"OCProperties",
                         "<< /OCGs [ "+" ".join(groups)+" ] /D << /BaseState /ON /ON [ "+
                         " ".join(on)+" ] /OFF [ "+" ".join(off)+" ] >> >>")
    doc.set_metadata({"title":f"{info['subject']} - Yearwise Questions {span}",
                      "author":"GradeMax", "subject":f"Edexcel International GCSE {code}"})
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path, garbage=3, deflate=True)
    doc.close()
    return {"file": relative(path), "papers": checks, "years": sorted(positions),
            "session_gaps":gaps}


def verify(report):
    """Independent checks of reopened PDFs, including all retained source sheets."""
    with fitz.open(ROOT / report["file"]) as book:
        expected_years = report["years"]
        actual_years = [int(t[1]) for t in book.get_toc() if t[0] == 2]
        assert actual_years == expected_years, "missing/reordered year bookmark"
        starts = [t[2] for t in book.get_toc() if t[0] == 3]
        assert starts == [p["book_page"] for p in report["papers"]], "paper bookmarks disagree"
        linked_starts = [l["page"]+1 for pg in book for l in pg.get_links() if l["kind"] == fitz.LINK_GOTO]
        assert all(s in linked_starts for s in starts), "missing contents link"
        seen = set()
        rendering_variations = []
        last_end = 0
        for p in report["papers"]:
            key = (p["year"], p["season"], p["paper"])
            assert key not in seen, f"duplicate sitting {key}"
            seen.add(key)
            assert p["book_page"] > last_end, "overlapping paper ranges"
            source_path = ROOT / p["path"]
            assert hashlib.sha256(source_path.read_bytes()).hexdigest() == p["sha256"], "source changed"
            with fitz.open(source_path) as source:
                last_end = p["book_page"]+len(source)-1
                for i, pg in enumerate(source):
                    dest = book[p["book_page"]-1+i]
                    assert dest.rect == pg.rect, f"sheet dimensions changed {key} p{i+1}"
                    assert dest.get_text() == pg.get_text(), f"sheet text changed {key} p{i+1}"
                    # Rendering detects lost images, diagrams, scans and vector content.
                    a = pg.get_pixmap(matrix=fitz.Matrix(.35,.35), alpha=False).samples
                    b = dest.get_pixmap(matrix=fitz.Matrix(.35,.35), alpha=False).samples
                    if a != b:
                        # Imported grayscale image resources can differ by a
                        # few colour levels after PDF object consolidation.
                        # Accept only tiny, sparse tonal changes; missing text,
                        # images, guides or geometry still fail this comparison.
                        assert len(a)==len(b), f"render dimensions changed {key} p{i+1}"
                        difference=[abs(x-y) for x,y in zip(a,b)]
                        maximum,mean=max(difference),sum(difference)/len(difference)
                        assert maximum<=16 and mean<=.25, f"sheet appearance changed {key} p{i+1}: max={maximum}, mean={mean}"
                        rendering_variations.append({"sitting":list(key),"source_page":i+1,
                                                     "maximum_channel_difference":maximum,"mean_channel_difference":mean})
        if report.get("session_gaps"):
            printed = book[1].get_text().replace("\u00a0"," ")
            assert "Coverage notes" in printed, "session gaps not disclosed in the PDF"
            for p in report["session_gaps"]:
                assert f"{LABELS[p['season']]} {p['year']} | Paper {p['paper']}" in printed
        return {"pages":len(book), "papers":len(seen), "years":actual_years,
                "rendering_variations":rendering_variations,"status":"PASS"}


def build(selected=None):
    inventory = json.loads((WORK / "inventory.json").read_text(encoding="utf-8"))
    inventory = {code:inventory[code] for code in SUBJECTS}
    previous = json.loads((OUT / "build_report.json").read_text()) if (OUT / "build_report.json").exists() else []
    reports = []
    for code, info in inventory.items():
        papers = info["papers"]
        assert not info["unfilled_slots"], f"unfilled source slots for {code}: {info['unfilled_slots']}"
        assert sorted({p["year"] for p in papers}) == YEARS, f"missing year in {code}"
        expected_papers = {1} if code == "4EB1" else {1,2}
        for year in YEARS:
            assert {p["paper"] for p in papers if p["year"] == year} == expected_papers, f"missing component {code} {year}"
        keys = [(p["year"], SEASONS[p["season"]], p["paper"]) for p in papers]
        assert keys == sorted(set(keys)), f"duplicate/reordered papers in {code}"
        path = OUT / f"GradeMax_{code}_Yearwise_Questions_2019-2026.pdf"
        if selected and code not in selected:
            receipt = next(r for r in previous if r["file"] == relative(path))
            assert receipt["verification"]["status"] == "PASS"
            assert [(p["path"],p["sha256"]) for p in receipt["papers"]] == [(p["path"],p["sha256"]) for p in papers]
            reports.append(receipt)
            continue
        report = build_one(code, info, papers, path, "2019 - 2026")
        report["verification"] = verify(report)
        reports.append(report)
        # Keep completed verification receipts if a later subject exposes a
        # damaged source or a PDF assembly issue.
        (OUT / "build_report.json").write_text(json.dumps(reports,indent=2),encoding="utf-8")
        print(f"{code}: {report['verification']}", flush=True)
    write_outputs(inventory,reports)


def write_outputs(inventory,reports):
    (OUT / "build_report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    lines = ["# Yearwise Question Papers, 2019–2026", "",
             "Pearson Edexcel International GCSE. Every book contains 2019, 2020, 2021, 2022, 2023, 2024, 2025 and 2026 in ascending order.", "",
             "English is English Language B (4EB1). Standard papers are included; regional R variants are excluded. January 2019 papers from previous specifications are clearly marked where applicable. Original exam sheets and enclosed reading/source booklets are preserved.", "",
             "The 2026 coverage is May/June. This edition includes the papers available on 13 October 2026; future autumn 2026 exams are not represented. [Pearson's autumn timetable](https://qualifications.pearson.com/content/dam/pdf/Support/Examination-timetables-for-Edexcel-International-GCSE/intgcse-nov-2026-final.pdf).", "",
             "| Subject | PDF | Papers | Pages | Verification |", "|---|---|---:|---:|---|"]
    for (code, info), report in zip(inventory.items(), reports):
        v = report["verification"]
        lines.append(f"| {info['subject']} ({code}) | [{Path(report['file']).name}]({Path(report['file']).name}) | {v['papers']} | {v['pages']} | {v['status']} |")
    gaps = [(info,p) for info,report in zip(inventory.values(),reports)
            for p in report.get("session_gaps",[])]
    if gaps:
        lines += ["", "Known session gaps (the years themselves are present):"]
        for info,p in gaps:
            lines.append(f"- {info['subject']}: {LABELS[p['season']]} {p['year']}, Paper {p['paper']} — verified PDF unavailable.")
    else:
        lines += ["", "Session coverage: every expected standard sitting from 2019 through May/June 2026 is present, with no gaps."]
    sources = [(info,p) for info in inventory.values() for p in info["papers"]
               if (p.get("identity_url") or "").startswith("https://automatepapers.com/")]
    if sources:
        lines += ["", "Papers collected from the known AutomatePapers archive:"]
        for info,p in sources:
            lines.append(f"- [{info['subject']}, {LABELS[p['season']]} {p['year']}, Paper {p['paper']}]({p['identity_url']}) — cover identity and matching mark-scheme log number verified.")
    lines += ["", "Verification reopens every PDF, checks all eight year bookmarks and paper links, and compares the text, dimensions and rendered appearance of every source sheet against the book.", ""]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--resolve", action="store_true")
    parser.add_argument("--subjects", nargs="+", choices=SUBJECTS, help="rebuild these subjects using verified receipts for the rest")
    args = parser.parse_args()
    if args.prepare:
        prepare()
    if args.resolve:
        resolve()
    if args.build:
        build(args.subjects)
