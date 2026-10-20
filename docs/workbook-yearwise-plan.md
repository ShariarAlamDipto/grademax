# Yearwise workbooks — Mechanics M1, Statistics S1, Pure Mathematics P4

A second, separate product from the chapterwise workbooks in
[workbook-s1-p4-plan.md](./workbook-s1-p4-plan.md) and
[workbook-mathsa-plan.md](./workbook-mathsa-plan.md). Same two units in the S1/P4
case, entirely different book.

A **chapterwise** book takes a question out of its paper and gives it a measured
block of ruled space, organised by syllabus section. A **yearwise** book reprints
whole past papers in order, so the exam is the unit and the board's own layout is
the point: the frame, the sidebars, the ruled lines, the mark fence and the total
band all stay exactly as Edexcel set them.

Built and shipped 2026-09-22 (M1) and 2026-09-23 (S1, P4).

| Unit | Papers | Questions volume | Mark scheme volume |
|------|--------|------------------|--------------------|
| M1 (WME01) | 20 — Jan 2017 to Oct 2023 | 448pp | 336pp |
| S1 (WST01) | 14 — Jan 2019 to Oct 2023 | 285pp | 180pp |
| P4 (WMA14) | 10 — Oct 2020 to Oct 2023 | 265pp | 246pp |

Output: `data/workbook/{m1,s1,p4}_yearwise/final/`.

---

## 0. The contents

One row per sitting: year heading, session, paper reference, page. Nothing
finer.

An earlier edition also printed every question's page under each session
(`Q1 5  Q2 8  Q3 10 …`). It doubled the length of the contents and buried the
thing a reader comes to it for, which is where a given year and session begins;
on M1 it pushed the contents onto a second sheet. The per-question map is still
recorded in `print_index.json`, where the workbook audit checks it — it just is
not printed.

Because those rows are now the book's only navigation, the independent verifier
reads them **off the printed page** and opens each one: all 44 land on the sheet
that session starts on.

---

## 1. The one change made to the papers

Everything is reprinted 1:1 except the **answer space**. Edexcel gives a question
as many as five further sides of ruled paper, because one printed paper has to
suit the largest handwriting in the cohort. The book caps that at **two blank
sides per question** and drops the surplus.

Dropping, not shrinking. Nothing is rescaled, reflowed, or replaced with a
generic blank page: a kept page is the board's page at full size, and a dropped
page is simply not there, exactly as if the board had set a shorter paper.

| Unit | Source pages | Book pages | Dropped |
|------|-------------|-----------|---------|
| M1 | 568 | 444 | 124 (22%) |
| S1 | 340 | 281 | 59 (17%) |
| P4 | 316 | 261 | 55 (17%) |

### Which blank side gets dropped — not the last one

Edexcel prints `(Total for Question 4 is 12 marks)` at the foot of a question's
final page, which on most questions is a page that is otherwise blank. Taking
"the last two" would throw the mark tariff away on three questions in four.

**A page carrying the total band is always kept**, whatever the allowance, and
the allowance is then filled from the *earliest* blank sides — so the cut comes
out of the middle, where nothing is printed at all. `--allowance 0` therefore
means "no spare space", not "throw the tariffs away".

### The distribution is bimodal, which is why the cut differs by unit

Blank answer sides per question, measured:

| Unit | 0 | 1 | 2 | 3 | 4 | 5 |
|------|---|---|---|---|---|---|
| M1 | 1 | 41 | 2 | 88 | 12 | 2 |
| S1 | — | 18 | 8 | 32 | 3 | — |
| P4 | — | 34 | 2 | 48 | — | — |

Almost nothing sits between 1 and 3, so a cap at 2 only touches the three-side
questions. That is why M1 loses 22% and the other two 17%, and why the finished
books are not uniform — a question that had one blank side still has one.

Alternatives measured and not taken: allowance 1 cuts 34–35% and makes every
question identical (tight for a 15-mark S1 question, the top of that unit's
range); a mark-aware allowance (one side up to 8 marks, two above) is more
principled but was declined in favour of consistency across the series.

---

## 2. Scope — which sittings exist

A unit declares **the sittings that were actually sat**, not a year range. This
matters more than it sounds.

### P4 did not exist before October 2020

WMA14 is an A2 unit of the 2018 IAL Mathematics specification (first teaching
September 2018), so the units phased in and P4 came last. The 2020 summer series
was then cancelled, which makes **October 2020 the first P4 sitting ever**, using
the paper printed for June 2020 (`P65759A`).

Checked three ways, so nobody has to re-open it:

- **Pearson's own catalogue** holds 2,592 IAL Mathematics assets. The earliest
  WMA14 anything — question paper, mark scheme or examiner report — is October
  2020.
- **Paperlords**, listed session by session, shows the phase-in directly:
  October 2019 = C12, C34, M1, P1, P2, S1; January 2020 adds P3; **P4 first
  appears in May 2020**.
- **PMT** has no IAL P4 page at all.

The files sitting in the archive's 2019 "P4" folders are `WMA02` **Core
Mathematics C34** — a different qualification, 125 marks, 48–52 pages, carrying
trapezium rule and numerical iteration, which are P2/P3 content under this spec.
They are not listed as sittings and the audit never opens them.

Iterating a year range instead would report nine phantom holes for P4.

### The cancelled 2020 summer series

Every unit's archive files the paper printed for June 2020 under **both** 2020
slots, because it was sat in October. The book prints it once, as October, with
a contents note. The mark scheme is likewise one document filed twice.

---

## 3. What the source audit found

Four slots across the two new units held the wrong paper or nothing at all.
Every "wrong" case is a **duplicate of a neighbouring session**, which defeats
any filename or cover check — the copy's cover honestly names the session it
really is.

| Slot | Held | Now |
|------|------|-----|
| S1 2021 May/Jun | the **Oct 2021** paper (`P71284A` in both 2021 slots) | `P63150A` |
| S1 2023 May/Jun | the **Jan 2023** paper (`P72072A`) | `P72904A`, Thu 11 May 2023 |
| P4 2023 May/Jun | the **Jan 2023** paper (`P72871A`) | `P74329A`, Fri 9 Jun 2023 |
| S1 2019 Oct | not held | `P58493A`, Wed 16 Oct 2019 |
| S1 2020 Jan | not held | `P60578A`, Mon 20 Jan 2020 |

M1 had the same defect at 2023 May/June and a missing October 2019; both were
fixed in the earlier pass. Displaced papers are in
`data/quarantine/yearwise_wrong_session/`, never deleted.

### The five checks

1. **Genuine question paper**, not a worked-solutions document filed under a
   `_QP` name — the board's item code has to be on every page and the text layer
   cannot be near-empty.
2. **GradeMax stamped** on every page, no third-party branding.
3. **The mark scheme is the session it claims**, from its Pearson publication
   code.
4. **The question paper is the session it claims**, from the exam date on its
   cover.
5. **The pair belongs together**, by content.

### Check 3 — the publication code, and its two traps

`WME01_01_1806_MS` — unit, paper, YYMM, kind — printed on a mark scheme's last
page. It is the only session identifier in either document that cannot be wrong,
and it is what caught M1's June 2018 slot holding `6677_01_1806_MS`, the legacy
GCE unit's mark scheme rather than the international one.

- **Eight digits are a publication DATE, not a session.** `WME01_01_rms_20240118`
  is the October 2023 paper: summer publishes in August, January in March, and
  the autumn series in the January or February *after* it. Read literally, that
  code makes October 2023 look like January 2024. Order the regex alternation
  `\d{8}|\d{4}` or `\d{4}` swallows the year and calls `20240118` "2024".
- **Pearson makes typos.** January 2021 is coded `WME01_01_2021_MS` and
  `WMA14_01_2021_MS` — 2101 transposed — on two different units. The covers and
  the schemes both say January 2021. Recorded per unit in `Subject.pub_typos`.

### Check 5 — a score, not a verdict

Each question paper is scored against every mark scheme on the numbers they
share, **weighted by how rare each number is** across the mark schemes. Raw
overlap is useless: unweighted, `9.8`, `75` and the page numbers put every
session within 0.02 of every other.

Typical margins, which is what tells you whether to believe a flag:

| Unit | A correct pair | Its runner-up |
|------|---------------|---------------|
| S1 | 0.26 – 0.42 | ~0.10 (a 3–4× gap) |
| M1 | 0.23 – 0.46 | within 0.05 on three sessions |
| P4 | 0.28 – 0.45 | within 0.02 |

**P4 discriminates worst, and it produced a false alarm.** The check flagged P4
January 2021; the file is byte-identical to Pearson's own copy, cover reading
Thursday 7 January 2021. Both 2021 P4 papers open with a binomial expansion,
which is enough shared vocabulary to beat the margin. On P4 the cover date
outranks the pairing score.

`Subject.settled` records such a case **with the evidence that settled it**,
reported as a note, rather than suppressing the flag — so a later reader sees
what was checked instead of finding a silent exception.

---

## 4. Sourcing gaps

### Pearson files one unit under three folder spellings

Which one a paper lands in follows its publication date, not its unit. Guessing
returns a 152 KB HTML shell with a `200`, which is easy to mistake for a PDF.

```
…/International%20Advanced%20Level/Mathematics/2013/Exam%20materials/   up to 2020
…/International%20Advanced%20Level/Mathematics/2018/Exam-materials/     2021 on
…/International-Advanced-Level/Mathematics/2018/Exam-materials/         2023 on
```

**Always take the URL from the Algolia catalogue** (credentials and query in
`scripts/fill_ial_gaps_from_algolia.py`), never build it.

### What is gated

A handful of papers sit under `/content/dam/secure/...` and answer a 995-byte
login page — recognisable by an `ial-<unit>-01-oct19.pdf` style name. Both
October 2019 question papers (M1 and S1) are gated this way.

Those come from **Paperlords** via `scripts/harvest_paperlords_links.py`, whose
listing is public but entirely client-rendered, so the URL must be read off the
page and never generated. Its copies carry no watermark of their own.

A free cross-check fell out of this: S1's October 2019 mark scheme is public from
Pearson *and* present on Paperlords, and the two are byte-identical at 473,410
bytes.

### Verification is derived from the session, not from looked-up strings

Writing down the item code and exam date you expect only proves the file is the
one you looked up. If the lookup was wrong, the check agrees with it. So a
download is checked against properties of the **session**: item code on every
page, the unit's paper reference, no third-party branding, a cover date in the
right season, and a better match to that session's own mark scheme than to any
other.

**A mark scheme has no paper reference.** It writes `In Statistics S1 (WST01)
Paper 01`, which no `WST01\s*/?\s*0?1` pattern matches — this failed the S1
January 2020 mark scheme for a reason that was not a defect. A scheme is checked
against its publication code instead, which names the unit *and* the session and
is strictly stronger evidence.

---

## 5. Page geometry

Measured over all 44 papers of the three units (47 archive slots, three of which
are the duplicated 2020 paper), and **re-measured per unit rather than assumed to
carry over**:

| | Value |
|---|---|
| Page size | 595 × 842 (A4), no bleed, every page |
| Frame top edge | never above y = 36.5 |
| Frame bottom edge | never below y = 791.1 |
| Barcode top | never above y = 799.4 |

So a **34pt band at the head and 46pt at the foot** removes every piece of board
furniture — the item barcode, their page number, "Turn over", the scraper footer
on the 2017–2019 papers, and our own ingest stamp — without touching the frame,
let alone the question. The book writes its own running header and footer there
instead, so its page numbers cannot disagree with its contents.

**Mark schemes get no bands.** They are unframed, their content starts at x=14,
and real content runs to 97.75% of the page height, so there is no clean strip to
cut. They are scaled to fit whole; a landscape sheet is turned a quarter
clockwise rather than fitted to the width, which is the fix that took 355pt of
dead space off every page of the Maths B mark scheme volume.

---

## 6. How a page gets its owner

From the board's own furniture, which is more reliable than any layout analysis.
Two templates:

```
(Total 9 marks)                    + a `Q1` label in the margin     to 2022
(Total for Question 1 is 7 marks)                                   2023 on
Question 1 continued                                                both
```

The totals are load-bearing: exactly one per question, on that question's **last**
page, running in order, so they tile the paper end to end. `Question n continued`
then fixes where question 1 begins — one page before its first continuation —
which is the only boundary the totals leave open.

What is deliberately **not** used:

- The opening `4.` is missing from the 2023+ text layer altogether, and on every
  template a question opening with a figure extracts its number as a line of its
  own, so a pattern demanding text after the dot matches nothing.
- `(Total 9 marks)` alone does not name its question — the number is in a `Q4`
  label set separately in the margin, hundreds of characters away in extraction
  order. Pair them by **being on the same page**, never by adjacency.

Validation that this is right: every one of the 44 papers across the three units
parses to **exactly 75 marks**, with question counts matching the units'
published shapes (M1 7–8, S1 6–7, P4 8–11).

### Telling a blank side from a content page

Strip the furniture and measure what is left. Both obvious figure guards fire on
every page in the book:

- every page carries a **522 × 755pt frame rectangle** — 79% of the sheet, larger
  than any figure will ever be;
- every page places a **24 × 762pt image**, the rotated `DO NOT WRITE IN THIS
  AREA` ribbon.

A figure is judged instead by stroke count against the same paper's own empty
pages. Across the M1 corpus, of 370 pages empty of text once stripped, exactly
three carry extra drawings and all three are a paper's last page, where the extra
strokes are the `TOTAL FOR PAPER: 75 MARKS` box.

Also: an answer rule is **one non-alphanumeric character repeated**, matched by
repetition and not by character — the 2016–2019 papers have a broken CMap that
encodes `.` as U+0011, so a dot list matches nothing and every ruled page reads
as full of content.

---

## 7. Auditing the finished book

Counting pages cannot fail. A book that dropped a figure, clipped the mark fence
off every sheet, or numbered its contents one page short has exactly the page
count it was supposed to have. The audit reads the finished PDF and takes nothing
from the code that wrote it.

1. **Nothing but blank space was dropped** — every absent source page is checked
   against the source, not against the builder's decision.
2. **Every mark tariff survived.**
3. **Nothing was clipped or covered.**
4. **The contents is true** — each entry is read back and the page it names is
   opened.
5. **The mark schemes are complete.**

### Check 3 needs two passes, and the reason cost a failed audit

**A white rectangle hides text but leaves it in the text layer.** Painting one is
how the book removes the board's footer, so a band set 150pt too deep — straight
through the first four lines of a question — reads as a *perfect match* on every
text comparison there is. That was not a hypothesis: a deliberately broken build
passed the first version of this audit.

So every page is also compared as **rendered ink**, band by band. Not as pixels:
the book's sheets are 842.0pt tall and the papers 841.89, so every row of type
lands a fraction of a pixel off and a correct, dense cover page differs in 1% of
its pixels. What a covering destroys is not pixel equality but ink — the band
goes empty. A run of three 12pt bands is required before it counts, because one
sparse band of ruled lines can lose a quarter of its ink to that same fraction of
a pixel.

### Two more traps in the audit itself

- The comparison window must be stated **absolutely**, not measured from the page
  bottom. That 0.11pt difference puts `Pearson Education Ltd.` inside one window
  and outside the other, which failed all three 2023 covers.
- The text used to align book pages to source pages must **not** be
  furniture-stripped. A blank continuation sheet is nothing *but* furniture;
  strip it and every blank side in a paper reads identically, so the alignment
  cannot say which one was dropped. Three papers' last pages were reported
  missing when they were there all along.

### An independent re-check of the finished books

`scripts/verify_yearwise_books.py` is a second, deliberately standalone pass. It
imports nothing from `lib/yearwise_*`, reads no audit JSON and no archive: it
opens the finished watermarked PDFs and checks them against Edexcel's own
printing and a list of sittings typed from Pearson's catalogue. A check sharing
a library with the thing it checks can only confirm the library is
self-consistent.

It asks: every sitting present and nothing extra; chronological order; the
running header's claim matching the item code printed on every page and the exam
date on the cover; no paper lacking an item code (a worked-solutions scan); no
two papers the same exam; every paper summing to 75 marks by its own fences;
every printed contents row opening on the session it names; and the mark scheme
volume carrying the same sittings in the same order, each identified by the
Pearson publication code it prints.

Two things it needed, both of which would otherwise have produced a confident
wrong answer:

- The separator written as `·` (U+00B7) comes back out of the text layer as `•`
  (U+2022) — PyMuPDF's base-14 Helvetica remaps it, the same substitution class
  as the en dash. Matching only U+00B7 read 43 of 44 papers as absent from books
  that were correct.
- **Plain word overlap cannot detect a duplicate paper.** Two genuinely
  different M1 papers share 60–74% of their four-letter words, because every
  mechanics paper says *particle*, *velocity*, *horizontal*, *find*. A flat
  threshold flags the entire book. Weighting by word rarity separates the cases
  completely, and it is calibrated against ground truth: the three duplicate
  papers this project actually caught, kept in
  `data/quarantine/yearwise_wrong_session/`, score **1.000** against the paper
  each really was, while genuinely distinct pairs average 0.21 (S1) to 0.37
  (P4). The threshold sits at 0.95, in the empty space between.

Note that **18 of the 44 papers set their cover date in an image**, so no date
can be read from them — the 2021 June to 2023 January run on all three units.
For those the session evidence is the item code, the mark-scheme pairing and
distinctness, not a printed date.

### Always run it against a broken copy

The audit is exercised against three deliberate breakages — a deleted page, a
header band painted too deep, and a page moved out of order. All three must fail
it and the real book must pass. This is how the covered-text gap was found.

### One command for all of it

`scripts/test_yearwise_workbooks.py` runs the whole battery in seven stages,
cheapest first: compilation, the three source audits, the three workbook audits,
the independent verifier, a **determinism check** (rebuilding from the same
archive must reproduce all six interiors exactly — a build that drifts is a build
whose audit means nothing, because the audited file is not the one that ships),
the negative control, and press readiness. `--quick` skips the rebuild and the
negative control.

Run it before sending anything to a printer, and after touching anything under
`lib/yearwise_*`. Full pass takes about three minutes; 14 checks.

---

## 8. Script map

Per-unit entry points stay separate (see the standing rule about never adding a
subject to an existing shared script); the logic lives in `scripts/lib/`.

| Stage | Entry points | Library |
|-------|-------------|---------|
| Source audit | `audit_{m1,s1,p4}_yearwise_sources.py` | `lib/yearwise_sources.py` |
| Fill gaps | `repair_{s1,p4}_missing_qps.py`, `repair_m1_missing_qps.py` | `lib/yearwise_repair.py` |
| Build | `build_{m1,s1,p4}_yearwise_workbook.py` | `lib/yearwise_build.py`, `lib/yearwise_layout.py`, `lib/m1_paper_pages.py` |
| Audit the book | `audit_{m1,s1,p4}_yearwise_workbook.py` | `lib/yearwise_workbook_audit.py` |
| Covers + watermark | `finalize_{m1,s1,p4}_yearwise_workbook.py` | `lib/yearwise_finish.py`, `lib/workbook_finish.py` |
| Independent re-check | `verify_yearwise_books.py` (all three units) | none, by design |
| Everything at once | `test_yearwise_workbooks.py` | runs all of the above |

A `Subject` (source audit) declares its archives, the sittings that exist,
cancelled slots, reissued item codes, publication-code typos and settled
pairings. A `Plan` (build) declares the book's name and code, which slots to
skip, and what the contents should say about them.

**M1 is the regression test for the shared engine.** After touching anything
under `lib/yearwise_*`, rebuild M1: it must reproduce 447 and 334 interior pages
and audit clean.

### Adding a fourth unit

1. Write `audit_<unit>_yearwise_sources.py` with a `Subject` — confirm the
   sittings against Pearson's catalogue first, do not assume a year range.
2. Run it; fill whatever it reports with a `repair_<unit>_missing_qps.py`.
3. **Re-measure the page geometry** before trusting the 34/46pt bands.
4. Write the `Plan`, build, audit, finalize.

---

## 9. House details worth not re-deriving

- **PyMuPDF's base-14 fonts have no en or em dash** and silently substitute a
  middot, so a title page read `January 2017 · October/November 2023`. Use a
  hyphen. `·` itself is fine.
- `workbook_finish.verify` requires **exactly one image on each cover** — the
  artwork alone, so a watermark leaking onto the cover shows up as a second —
  and a printed page number on **every** sheet, including the title page. A
  purely typographic cover fails the first; the books put the GradeMax lockup on
  the cover, which satisfies it honestly.
- Watermark policy is unchanged from the other books: 55% of page width, centred,
  10% ink, drawn **under** the page. That only works because a reprinted exam
  sheet marks the paper where there is ink and nowhere else — if a future edition
  starts painting its own white ground the mark will vanish, and that is the
  first place to look.
- Save plain. `garbage=3` on books of this size costs hours for about 2%.

---

## 10. Open

- **Mark scheme boilerplate.** Each scheme opens with Edexcel front matter that
  is near-identical across sessions, before the first `Question / Scheme / Marks`
  page. Measured, median **3 pages** per scheme:

  | Unit | Front matter | Of total | If printed once |
  |------|-------------|----------|-----------------|
  | M1 | 73pp | 21% | ~60pp saved |
  | S1 | 48pp | 26% | ~42pp saved |
  | P4 | 32pp | 13% | ~27pp saved |

  Kept deliberately — the page-cutting brief was about the question papers. Note
  this is a third of what a first estimate of "~6 pages a scheme" suggested; the
  table above is measured, not estimated.
- **P4 has two papers that were never sat**: a specimen
  (`ial-pure-maths-4-specimen-paper-qp.pdf`) and an unused January 2022 reserve
  (`WMA14_01_Jan22_UNUSED.pdf`, with its mark scheme). Both are available as
  bonus papers if wanted.
- **No commissioned cover artwork** for any of the three; the books generate a
  typographic cover carrying the lockup.
- **Later sittings.** All three units continue past 2023 in Pearson's catalogue
  (to October 2024 and beyond). Extending is a one-line change to `sittings`
  plus whatever the source audit then reports.
