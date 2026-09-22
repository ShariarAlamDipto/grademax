# Chapterwise workbook — Statistics 1 (WST01) and Pure Mathematics 4 (WMA14)

Third and fourth subjects for the chapterwise workbook, after 4PM1 (Further Pure
Maths) and 4MB1 (Maths B). Same phases, **separate scripts per subject** —
`*_s1_*` and `*_p4_*`, never added to the FPM or Maths B ones.

Phase 0 (specification study + taxonomy) and the question-paper half of Phase 1
are **done**; mark-scheme attachment is the remaining part of Phase 1.

Sections 2 and 3 were written before the papers were fully measured. Where a
later measurement overturned them, the section carries a pointer to §5 rather
than being deleted — the reasoning is why the method ended up where it did.

---

## 1. What the specification actually says

Source: *Pearson Edexcel International Advanced Subsidiary/Advanced Level in
Mathematics, Further Mathematics and Pure Mathematics — Specification, Issue 3,
April 2019*. Content tables read directly from the PDF, not from memory.

### S1 (WST01) — six topics, section S1.3, pp. 55–56

| # | Heading | Statements |
|---|---------|-----------|
| 1 | Mathematical models in probability and statistics | 1.1 |
| 2 | Representation and summary of data | 2.1 histograms / stem and leaf / box plots · 2.2 measures of location + coding · 2.3 measures of dispersion + interpolation · 2.4 skewness and outliers |
| 3 | Probability | 3.1 elementary · 3.2 sample space, exclusive/complementary, conditional · 3.3 independence · 3.4 sum and product laws, tree and Venn diagrams, sampling with/without replacement |
| 4 | Correlation and regression | 4.1 scatter diagrams, least squares regression · 4.2 explanatory/response variables, prediction, extrapolation, linear change of variable · 4.3 PMCC |
| 5 | Discrete random variables | 5.1 concept · 5.2 probability function and CDF · 5.3 mean and variance, E(aX+b), Var(aX+b) · 5.4 discrete uniform distribution |
| 6 | The Normal distribution | 6.1 mean, variance, use of tables of the CDF |

Two things worth not re-deriving:

- The **unit description** (p. 53) lists "discrete distributions" as though it
  were a seventh area. The **content table** folds it into topic 5 as statement
  5.4. The content table is what the assessment is written against, so the
  workbook follows it.
- The specification has a **typo**: the single statement under heading
  "6. The Normal distribution" is numbered *5.1*, not 6.1.

### P4 (WMA14) — seven topics, section P4.3, pp. 27–29

| # | Heading | Statements |
|---|---------|-----------|
| 1 | Proof | 1.1 proof by contradiction |
| 2 | Algebra and functions | 2.1 partial fractions (denominators no worse than repeated linear terms; numerator degree may equal or exceed denominator; quadratic factors not required) |
| 3 | Coordinate geometry in the (x, y) plane | 3.1 parametric equations and cartesian ↔ parametric conversion |
| 4 | Binomial expansion | 4.1 binomial series for any rational n, \|x\| < b/a |
| 5 | Differentiation | 5.1 implicit and parametric, tangents and normals · 5.2 forming simple differential equations, connected rates of change |
| 6 | Integration | 6.1 volume of revolution (∫πy²dx only) · 6.2 substitution and by parts · 6.3 partial fractions · 6.4 separable first-order differential equations · 6.5 area under a parametrically-defined curve |
| 7 | Vectors | 7.1 2D and 3D · 7.2 magnitude and unit vectors · 7.3 addition and scalar multiplication · 7.4 position vectors · 7.5 distance between two points · 7.6 vector equations of lines, parallel/intersecting/skew · 7.7 scalar product and the angle between two lines |

P4's prerequisites explicitly include P1, P2 and P3 "and may be tested".

---

## 2. What the source archive actually holds

Measured over `data/Ultimate Final IAL/Mathematics`, not assumed.

### The P4 folder is mostly not P4

Only the 2018 specimen and **June 2020 onwards** are genuine WMA14. WMA14's
first assessment was June 2020; everything filed as "P4" before that is a
different qualification:

| Cover says | Code | Marks | Files |
|---|---|---|---|
| Pure Mathematics P4 | WMA14 | 75 | 2018 specimen + 2020 Jun → 2025 Jan |
| Core Mathematics C34 | WMA02 | **125** | 2014 Jan, 2015 Jan, 2016 Jan, 2016 Jun, 2017 Jan, 2017 Nov, 2018 Jan, 2018 Nov, 2019 Jan, 2019 Jun |
| Core Mathematics C4 | legacy | 75 | 2014 Jun, 2015 Jun, 2017 Jun, 2018 Jun |

The papers confirm the split independently of their covers:

| Probe | legacy C34/C4 | genuine WMA14 |
|---|---|---|
| trapezium rule | 10 / 14 | **0 / 14** |
| numerical iteration / Newton–Raphson | 9 / 14 | **0 / 14** |

Both are P2/P3 content under the 2018 specification. **The workbook window is
therefore the 2018 specimen plus June 2020 onwards.** Mining the legacy C4/C34
papers is a possible later expansion (see §5), but it needs a per-question
specification filter and must not be folded in blind.

S1 is clean by contrast: all 31 files are genuine WST01, 2014 → 2025.

### Duplicate papers — the same paper filed under two sessions

Five pairs, found by comparing extracted text after stripping our own
watermark's session token. Every pair scores a similarity ratio of **exactly
1.0000** — the only differences in the raw text are the watermark reading
"MayJun" vs "OctNov" (or "Jan" vs "May").

| Subject | Pair |
|---|---|
| S1 | 2020 May-Jun ≡ 2020 Oct-Nov |
| S1 | 2021 May-Jun ≡ 2021 Oct-Nov |
| S1 | 2023 Jan ≡ 2023 May-Jun |
| P4 | 2020 May-Jun ≡ 2020 Oct-Nov |
| P4 | 2023 Jan ≡ 2023 May-Jun |

This is the COVID paper-reuse pattern already recorded for the Edexcel gap-fill
work, and it is invisible to a filename check. **Deduplicate before segmenting**
or ~12% of the S1 book and ~13% of the P4 book is the same question twice.

P4 2021 May-Jun vs Oct-Nov scores 0.920 with different mark vectors — genuinely
different papers, keep both.

### Corpus after deduplication

| | files | unique papers | questions |
|---|---|---|---|
| S1 (WST01) | 31 | **28** | **179** segmented from 27 (the specimen is held out — §5) |
| P4 (WMA14) | 16 | **14** | **130** (14/14 papers clean) |

These are the measured Phase 1 results, not estimates. See §5.

Both papers are 75 marks, and every parsed paper's fences sum to exactly 75 —
the same per-paper invariant FPM and Maths B rely on as an audit gate.

Mark tariffs (from the parsed fences):

- **S1: mean 11.2, median 11, range 4–17** — 6–8 long questions per paper.
- **P4: mean 8.2, median 8, range 3–15** — 8–11 questions per paper.

Difficulty bands must be derived from these, **not copied**. FPM's bands
(≤6 easy / ≤10 medium) would call almost nothing in S1 easy, and Maths B's
(≤3 / ≤6) would call almost everything in both hard.

---

## 3. Segmentation: what is different from FPM and Maths B

### Two fence eras, and the old one carries no question number

| Era | Printed fence | Carries |
|---|---|---|
| ≤ 2022 Jan | `(Total 9 marks)` | marks only |
| ≥ 2022 May-Jun | `Total for Question 3 is 9 marks` | number **and** marks |

The FPM segmenter's whole design is that the label comes from the paper rather
than from our inference — the end fence states its own number. **For IAL papers
before 2022 that is not available**, and 26 of the 42 papers are in that era.

> **Superseded by measurement — see §5.** The fix is not the left-margin marker
> this section originally proposed. Every IAL page names its own owner in the
> top-left corner (`2.` or `Question 2 continued`), so boundaries come from the
> page headers and the question number is printed on every page. The fence is
> demoted to a marks-only signal, cross-checked against the per-part tallies.

### The +29 CMap breakage must be repaired *before* fence matching

In FPM and Maths B the broken-CMap repair was an enricher concern — the stems
were classifier input only. Here it changes segmentation itself: several papers
lose most or all of their fences to it. Repairing spans first recovers them.

| Paper | fences raw | fences after +29 repair |
|---|---|---|
| S1 2015 Jan | 7 | 7 (sums to 75) |
| P4 2016 Jan | 1 | — legacy C34, out of window |
| S1 2014 Jan | 8 | 8 (sums to 75) |

Apply **per span, never per page** — the same rule as FPM. One page mixes broken
and intact spans.

### Five S1 papers yield no fence, and one cannot be parsed at all

> **Resolved — see §5.** The five are recovered from the bold per-part tallies
> (each still summing to exactly 75). The sixth, the 2018 specimen, uses an
> arbitrary font-subset encoding and is held out. The original diagnosis below
> stands as the reason the two cases are different.

### Original diagnosis

`2014 May-Jun`, `2015 May-Jun`, `2016 Jan`, `2016 May-Jun`, `2017 Jan`,
`2018 Specimen`. These are **not** image-only — body text extracts fine (e.g.
2016 May-Jun yields "the total area under the histogram is 94.5 cm²"). The
`(Total N marks)` lines specifically are missing or partial from the text layer,
which points at a different font subset rather than the +29 breakage.

Handle them the way Maths B handled its held-back papers, in this order:

1. `recover_missing_fence` — a single gap has exactly one possible mark value
   given the 75-mark total, and the boundary comes from the next question's
   printed marker.
2. `MANUAL_QUESTION_MARKS` read off a **rendered** page when two or more fences
   are missing. Render it and look; do not infer from the mark scheme's mark
   column, which holds per-part marks.

Together these are ~40 of S1's ~184 questions, so they are worth recovering
rather than dropping.

### Does either subject share pages between questions?

**Measured: no.** 0 of 130 P4 fence pages and 1 of 148 S1 fence pages also
carry a question start, and that one is a false positive. Page ranges are safe
for both subjects and no cropping is used — see §5. Background:
FPM never shares a page (page-range splitting is safe);
Maths B Paper 1 shares 33% of its pages (y-crop bands required). S1 and P4 are
long-question papers like FPM, so page ranges are *likely* safe — but measure it
before choosing, and if cropping is needed use `show_pdf_page(..., clip=...)`,
never `set_cropbox`. The cropbox/mediabox offset bug cost the Maths B build 137
silent audit defects.

---

## 4. The taxonomy (Phase 0 — DONE and applied)

- `supabase/migrations/18_workbook_s1_taxonomy.sql` — **6 chapters / 19 sections**
- `supabase/migrations/19_workbook_p4_taxonomy.sql` — **7 chapters / 15 sections**
- `scripts/apply_s1_p4_workbook_taxonomy.py` — reads the rows out of the
  migrations and inserts them over PostgREST (pure DML, tables exist from
  migration 12 — the route migration 15 took). Idempotent; never updates or
  deletes, so it cannot disturb a taxonomy questions are already classified
  against.

Applied 2026-09-10. Verified live: WST01 6/19, WMA14 7/15, and 4PM1 (10/41/423)
and 4MB1 (11/53/1046) untouched.

### S1 — 19 sections

```
1. Mathematical models in probability and statistics
   1.1 Modelling in probability and statistics
2. Representation and summary of data
   2.1 Measures of location and dispersion
   2.2 Coding
   2.3 Quartiles, percentiles and linear interpolation
   2.4 Histograms and frequency density
   2.5 Stem and leaf diagrams and box plots
   2.6 Skewness, outliers and comparing distributions
3. Probability
   3.1 Sample space, elementary probability and the addition law
   3.2 Venn diagrams
   3.3 Conditional probability and independence
   3.4 Tree diagrams and sampling with and without replacement
4. Correlation and regression
   4.1 Scatter diagrams and the summary statistics Sxx, Syy and Sxy
   4.2 The product moment correlation coefficient
   4.3 The least squares regression line, prediction and coding
5. Discrete random variables
   5.1 Probability distributions and the cumulative distribution function
   5.2 Expectation and variance
   5.3 The discrete uniform distribution
6. The Normal distribution
   6.1 Standardising, z-values and the Normal tables
   6.2 Finding an unknown mean or standard deviation
```

~184 questions / 19 sections ≈ **10 per section** — comparable to FPM's 431/41.

### P4 — 15 sections

```
1. Proof
   1.1 Proof by contradiction
2. Algebra and functions
   2.1 Partial fractions
3. Coordinate geometry in the (x, y) plane
   3.1 Parametric equations and conversion to cartesian form
4. Binomial expansion
   4.1 Binomial series for any rational n and its range of validity
5. Differentiation
   5.1 Implicit differentiation, tangents and normals
   5.2 Parametric differentiation, tangents and normals
   5.3 Connected rates of change and forming differential equations
6. Integration
   6.1 Integration by substitution and by parts
   6.2 Integration using partial fractions
   6.3 First order differential equations with separable variables
   6.4 Volumes of revolution
   6.5 Area under a curve given parametrically
7. Vectors
   7.1 Vector algebra, magnitude, unit vectors and position vectors
   7.2 Vector equations of lines: parallel, intersecting and skew
   7.3 The scalar product and the angle between two lines
```

130 questions / 15 sections ≈ **9 per section**.

### Why the sections are sized the way they are

Measured over the deduplicated corpora (28 S1 papers, 14 P4 papers), counting
papers that mention each idea:

| P4 | papers | Consequence |
|---|---|---|
| proof by contradiction | **14 / 14** | Earns its own chapter despite being one spec statement |
| parametric | 14 / 14 | See the disambiguation rule below — must **not** all land in chapter 3 |
| binomial | 14 / 14 | One section, ~14 questions |
| integration by substitution | 13 / 14 | |
| differential equations | 13 / 14 | |
| volume of revolution / parametric area | 12 / 14 | Split into 6.4 and 6.5 per the spec's separate statements |
| vectors | 11 / 14 | Three sections, not seven — one long question usually spans all of them |
| partial fractions | 8 / 14 | |
| integration **by parts** | **1 / 14** | Merged with substitution (spec pairs them in 6.2); a separate heading would look empty |
| "implicit" | **0 / 14** | The word is never printed — see below |

| S1 | papers | Consequence |
|---|---|---|
| mean / standard deviation | 27 / 28 | 2.1 will legitimately be the largest section |
| PMCC · regression | 27 / 28 each | |
| probability distribution / CDF | 26 / 28 | |
| skewness / outliers | 25 / 28 | |
| conditional probability / independence | 24 / 28 | |
| E(X) / Var(X) | 22 / 28 | |
| quartiles, percentiles, interpolation | 20 / 28 | |
| Venn diagrams | 20 / 28 | |
| Sxx / Sxy summary statistics | 18 / 28 | |
| Normal distribution | 16 / 28 | Two sections |
| histograms · stem-and-leaf/box plots · tree diagrams | 14–16 / 28 | |
| coding | 9 / 28 | |
| addition law alone | **3 / 28** | Merged into 3.1 with sample space |
| discrete uniform distribution | **2 / 28** | Kept anyway — explicit spec statement 5.4 |

**Two sections are expected to stay thin and are kept deliberately:** S1 1.1
(topic 1 is never a standalone question — it is the "comment on this model" tail
of a question about something else, so it will mostly appear as a *secondary*
label) and S1 5.3. Keeping a thin section costs a heading the book generator can
skip; deleting one costs a renumbering migration. Keep is reversible.

### Two classifier rules this taxonomy depends on

These are the P4 equivalent of FPM's "kinematics must be scoped to a particle in
motion" rule, and the tree does not work without them:

1. **Parametric questions do not all belong to chapter 3.** Chapter 3 is for
   questions whose *own subject* is the parametric or cartesian form of a curve.
   A parametric curve that is then differentiated is **5.2**; one that is then
   integrated is **6.3/6.4/6.5**. Parametric equations appear in 14 of 14 papers,
   so without this rule chapter 3 absorbs most of the book — the same skew that
   put 111 of 431 FPM questions into one chapter before multi-labelling fixed it.
2. **"Implicit" is never printed.** The paper gives an equation relating x and y
   and asks for dy/dx. Section 5.1 must be detected from that *shape*, not from
   the word. A keyword probe will return zero and mean nothing.

And carry over the probe discipline that has now bitten this project twice: use
word boundaries, and read a sample of the actual hits before concluding the
classifier is wrong. (`solve.{0,25}(sin|cos|tan)` matching "solve the
simul**tan**eous equations" is the canonical example.)

---

## 5. Phase 1 — QP segmentation DONE

Decision taken: **P4 stays on the new specification only.** The legacy C4/C34
papers are not mined; `is_in_scope()` gates on the paper's own cover.

| | papers in | out of scope | duplicates | excluded | **segmented** | questions |
|---|---|---|---|---|---|---|
| S1 (WST01) | 31 | — | 3 | 1 | **27** | **179** |
| P4 (WMA14) | 30 | 14 | 2 | 0 | **14** | **130** |

Every paper's marks sum to exactly 75. **Audit gate PASS for both**: 0
mislabelled / 0 bundled / 0 unverifiable across 309 segments.

Independent coverage check (not part of the gate): **0 page overlaps**, and
exactly one unassigned page per paper — the cover. Every other page of every
paper belongs to exactly one question.

### Files

- `scripts/lib/ial_qp_parse.py` — the shared IAL *page-format* parser. Subject-
  neutral; read its module header before touching either script.
- `scripts/build_s1_workbook_segments.py` → `data/workbook/s1/` (gitignored)
- `scripts/build_p4_workbook_segments.py` → `data/workbook/p4/` (gitignored)
- `data/workbook/{s1,p4}_segmentation_report.json`

Each `--execute` writes `<paper_key>/questions/qN.pdf` plus a `manifest.json`
carrying page ranges, marks and **mark provenance**. Re-run `--audit` any time.

### The method changed, and it is better than the IGCSE one

The plan above assumed IAL would need FPM's fence-derived boundaries with
marker recovery for the pre-2022 papers. Measuring the papers showed something
better: **every IAL page announces its own owner in the top-left corner.**

```
page 1   '1.	 (a) Find the first 4 terms ...'   <- question 1 starts here
page 2   'Question 1 continued'                  <- question 1 owns this page
page 3   '2.'                                    <- question 2 starts here
```

So boundaries come from the printed page headers, and the question number is
**stated explicitly on every page** rather than inferred from position. All 42
papers yield starts numbering exactly 1..N with no gaps. This removes the
pre-2022 "fence carries no question number" problem entirely rather than
working around it.

Marks then come from two independent signals — the fence, and the **bold
per-part tallies** in the right margin. Measured provenance:

| | fence + tally agree | tally only |
|---|---|---|
| S1 | 148 | 31 |
| P4 | 130 | 0 |

**The two signals never disagreed once** across all 278 questions that print
both. That is a real cross-check, unlike aligning mark schemes by LCS on the
mark values, which guarantees the agreement it then reports. The 31 tally-only
questions are the five WST01 papers whose `(Total N marks)` lines are absent
from the text layer; each of those papers still sums to exactly 75.

### Two things the measurement corrected

- **No y-cropping is needed.** Both subjects are long-question papers: 0 of 130
  P4 fence pages and 1 of 148 S1 fence pages also carry a question start, and
  that one is a false positive (a data value `30` on a "Question 2 continued"
  page). Page-range splitting is safe, so the whole `set_cropbox` /
  mediabox-offset bug class that cost Maths B 137 silent defects cannot arise.
- **My first marker probe reported 0/42 papers usable, and was wrong.** It ran
  `fullmatch(r"\d{1,2}")` against the whole assembled line, so
  `'1.	 (a) Find the first 4 terms...'` never matched. This is the same
  failure Maths B already recorded ("marker spans are not always bare numbers")
  and it nearly led to a needless OCR detour. Match a prefix, and look at a
  real page before believing a probe that says a signal is absent.

### One paper held out

`S1 2018 Specimen` — arbitrary per-font subset encoding; its text layer decodes
`'!"#$"%'` for "Leave". Not the +29 CMap shift, so no arithmetic repair recovers
it (same class as Maths B's `2016_jan_2R`). Worth ~7 questions. The
`MANUAL_QP_RANGES` hook is in place so it can be added from a rendered contact
sheet without touching any logic.

### Mark schemes — DONE

`scripts/lib/ial_ms_parse.py`, wired into both segmenters; audited by
`scripts/audit_s1_p4_markschemes.py`.

| | attached | dropped | ruled | unruled |
|---|---|---|---|---|
| S1 | **127/179 (70%)** | 52 | 98 | 29 |
| P4 | **89/130 (68%)** | 23 | 69 | 20 |

A block is attached **only when its marks reconcile with the question's marks**,
derived independently from the question paper. Anything else is dropped.
Coverage below 100% is the intended outcome — a blank slot is something a
student can act on; another question's scheme is not.

Audit: 0 wrong-question, 0 unreadable, 0 page overlaps across all 216 attached.
Two P4 papers (2018 specimen, 2020 May-Jun) have no mark scheme file at all in
the archive.

**Two extractors, because there are two layouts.** Ruled (~2015–2022) is a real
bordered table that `find_tables()` reads cleanly; unruled (~2023–2025) has no
borders at all, so `find_tables()` returns nothing and every block sums to zero.
Both run and whatever reconciles is kept, which is safe precisely because
acceptance rests on the QP's marks rather than on which extractor won.

**The earlier "rotated or unmapped" diagnosis was wrong.** Every mark-scheme
line reports `dir=(1.0, 0.0)`. Every failure was in the reader. What actually
mattered:

- Every mark scheme opens with a **numbered guidance list** ("1. The total
  number of marks for the paper is 75") that reads exactly like a question cell
  and anchored question 1 several pages before the table began.
- The mark-code regex **had been matching nothing at all** — `` was written
  into the file as a literal backspace byte, so the `M1`/`A1`/`B1` signal was
  dead. It also needs a `(?!\d)` tail rather than ``, or `A1ft` and `B1cso`
  are missed.
- The two extractors need **different cell patterns**: a ruled cell is already
  isolated by its table so a prefix match is right, while an unruled "cell" is
  just a line in the left column and must match in full, or `5 marks` and
  `12 cm` register as question starts.
- The column is located **per page from the printed header**, not by a fixed x —
  the left margin moves between papers (x=26 on WST01 2024 Jan, x=61 on WMA14
  2021 Jan). A page with no header cannot start a question. Requiring the same
  of the ruled extractor was measured and reverted: it cost 12 correct blocks
  and fixed nothing.

**Four hand-written audit probes produced false alarms before one worked**, and
every case they flagged that was checked by hand turned out to be a parser
success and a probe failure. A mark-scheme page's left column is dense with data
values and formula digits, so "question 25", "question 32" and "question 70"
were all reported on papers with at most eleven questions. The working audit
re-reads the written artifact with the parser's own primitives, and its
docstring is explicit that the independent check is the marks reconciliation,
not the probe.

---

## 6. Phase 2 — enrichment DONE

`scripts/enrich_s1_workbook_questions.py` and
`scripts/enrich_p4_workbook_questions.py` →
`data/workbook/{s1,p4}_questions.json`.

| | questions | difficulty (e/m/h) | text status | sub-parts reconciled | usable for Phase 3 |
|---|---|---|---|---|---|
| S1 | 179 | 64 / 48 / 67 | 111 ok, 68 repaired | 129/176 (73%) | **179/179 (100%)** |
| P4 | 130 | 36 / 40 / 54 | 47 ok, 83 repaired | 75/98 (76%) | **130/130 (100%)** |

No question in either subject needs vision — a better starting point than 4PM1,
which had 13 vision-only questions and spent days blocked on a 20-request daily
model quota.

### Difficulty bands are per subject and were computed, not chosen

Difficulty comes from the **mark tariff, not from a model**: the 4PM1 build
measured an LLM returning 2 easy / 317 medium / 116 hard at a mean self-reported
confidence of 0.93, which is a model agreeing with itself.

The cut points are the most even three-way split of each subject's own measured
distribution:

| | mean | median | range | bands | split |
|---|---|---|---|---|---|
| S1 | 11.3 | 12 | 3–17 | easy ≤10 · medium 11–12 · hard ≥13 | 64/48/67 |
| P4 | 8.1 | 8 | 2–15 | easy ≤6 · medium 7–8 · hard ≥9 | 36/40/54 |

They must not be shared. P4 questions run at about two thirds of an S1 tariff,
so S1's cut points would call 55 of 130 P4 questions easy and only 26 hard.
The 4PM1 bands (easy ≤6) would call 12 of 179 S1 questions easy; the 4MB1 bands
(easy ≤3) would call one.

S1's medium band is narrow (11–12) because its distribution is tightly peaked
around the median — that is the distribution's shape, not a tuning choice.

### Sub-parts are verified or dropped

Each bold right-margin tally closes the most recently opened `(a)`/`(b)` label,
which is how a candidate reads the page. The breakdown is kept **only when its
marks sum to the question total** — same discipline as the marks themselves,
because a wrong breakdown is worse than none.

### Two bugs this phase surfaced

- **`Leave` and `blank` were in 125 of 179 S1 stems.** They sit stacked in the
  right-hand margin box, so the text layer emits them as two independent lines
  and a filter matching only the phrase `Leave\s*blank` never fired. They were
  the first thing a classifier would have read. Now 1 of 179, and 0 of 130 for P4.
- `text_status` uses **exactly** the three values the DB CHECK constraint allows
  (`ok` / `repaired` / `needs_vision`). The Maths B loader grew a fourth and
  aborted 295 rows into a real load, minutes after a dry run reported success —
  a dry run never attempts an insert, so it never meets a constraint.

"repaired" means real, measured residue — private-use codepoints (unmapped
Symbol/maths glyphs) or the `) =word` artefact the +29 repair deliberately
leaves. Median density in a repaired stem is 1.8% of characters, so these are
readable stems with a few glyphs, not broken text.

---

## 7. Phase 3 — classification and archetypes DONE

`classify_{s1,p4}_workbook_sections.py` + `cluster_{s1,p4}_archetypes.py`,
on `lib/ial_classify.py` and `lib/ial_archetypes.py`.

| | questions | sections used | with a secondary | agreed | same chapter | disputed |
|---|---|---|---|---|---|---|
| S1 | 179 | 18/19 | **80%** | 141 | 30 | 8 |
| P4 | 130 | 15/15 | 36% | 121 | 3 | 6 |

**No section is dead in either subject** once secondary labels are counted —
better than 4PM1's first pass (6 empty) and 4MB1's (3 empty). The thin primaries
are exactly where the rules send them: S1's 2.6 skewness/outliers is 1 primary
but **31 secondary** (matching the 25-of-28-papers corpus probe), and P4's
vectors 7.1/7.3 are 12 and 11 secondary behind 7.2. S1's 1.1 is 0 primary /
3 secondary, which is what the rule asks for.

### Model routing had to change

**`llama-3.3-70b-versatile` no longer exists** — Groq 404s the model both
previous subjects used. Current routing:

| role | model | why |
|---|---|---|
| primary | `openai/gpt-oss-120b` | clean JSON, reasoning kept out of `content` |
| second opinion | `qwen/qwen3.8-27b` | a genuinely different family — same-family agreement is not evidence |

Avoid `qwen/qwen3.6-27b`: it spends its budget on a `<think>` block and never
reaches the JSON. `groq/compound*` caps `max_tokens` at 8192. Groq sits behind
Cloudflare, which rejects **urllib**'s default User-Agent with a bare
`403 error code: 1010` — call it with `requests`.

Self-reported confidence is not used to triage anything; 4PM1 measured its
spread at 0.03 across the full range of correctness. The queue is ordered by
two-model disagreement.

### Both P4 disambiguation rules confirmed working

- Parametric equations appear in **14 of 14 papers**, yet chapter 3 holds only
  **6** questions — the rule routes parametric-then-differentiate to 5.2 and
  parametric-then-integrate to 6.3/6.4/6.5, so chapter 3 did not absorb the book.
- Section 5.1 collected **14** questions from the *shape* of an equation in x
  and y, with the word "implicit" never printed anywhere in the corpus.

### Archetypes: threshold 0.32, and why S1 clusters weakly on purpose

0.45 (the 4PM1 value) split P4 section 4.1 into four clusters that were all
plainly the same binomial expansion. 0.32 merges them while keeping sections
apart; 0.26 begins to blob (11 of section 7.2's 12 questions in one cluster is
the section, not a shape). Verified by reading the three largest clusters — all
genuine single shapes. **P4: 76 archetypes, 57% of questions in a repeated shape.**

**S1 reaches only 28%, and that is structural, not a tuning failure.** Statistics
questions are contextual: all fifteen section 4.2 questions set the same task —
compute and interpret the PMCC — dressed as a price comparison website, blood
volume, milk and bread, foetal scans, caffeine, sea-level temperature, petrol,
GDP, film takings, dissolving sugar, bears and rabbits. They share almost no
content words, so TF-IDF cannot see the shape and no threshold recovers it;
lowering it merges unlike questions on filler instead.

So **for S1 the section is the archetype**, and ~70% of its questions are
singletons. A book generator must not present those singletons as recurring
shapes — for S1 the section heading carries the pattern, for P4 the archetype
does.

---

## 8. Phase 4 — loaded to Postgres and R2

`load_{s1,p4}_workbook_to_db.py` on `lib/ial_workbook_load.py`.

| | rows | PDFs | R2 prefix | agreed | same chapter | disputed | verified |
|---|---|---|---|---|---|---|---|
| S1 | 179 | 306 | `workbook/s1/` | 141 | 30 | 8 | 0 |
| P4 | 130 | 219 | `workbook/p4/` | 121 | 3 | 6 | 0 |

`verified_at` is NULL on every row, so RLS keeps all of it out of student view
until a human signs it off. 4PM1 (423) and 4MB1 (1046) untouched.

**Verified against the database and R2, not the scripts' summaries:** counts
match the local files exactly, slugs unique, every row carries a section and an
archetype, `ms_pdf_url` count matches `has_markscheme` exactly (127 / 89),
ordinals contiguous within every section, sampled R2 URLs return
200 `application/pdf`.

### Two fixes the real load forced

- **Supabase drops a pooled connection mid-load**, surfacing as a bare
  `httpx.WriteError`. The first S1 run died after 150 of 179 rows. Writes are
  now retried — transport errors only, never a constraint violation, which is a
  real answer and must surface immediately. The load was already idempotent
  (matched on `(source_paper_key, source_question_number)`), so the resume
  updated the 150 and created the remaining 29.
- **A dry run reported "147 archetypes created" where the real run creates 36**,
  because it never inserted and so never updated its own dedup map. It now
  simulates the insert and the two modes agree. The gap between them was the
  in-run dedup guard doing its job: 147 S1 clusters collapse to 36 distinct
  `(section, label)` keys.

### Review UI

The verify picker listed all ~98 site subjects, of which only five have a
workbook — the rest 404 from the queue endpoint. New
`/api/admin/workbook/subjects` returns only subjects with a taxonomy, plus each
one's unverified count, using the same condition the queue requires.

Current workbook subjects:

| subject | chapters | questions | verified |
|---|---|---|---|
| 4PM1 | 10 | 423 | **423** |
| 4MB1 | 11 | 1046 | **1046** |
| 4MA1 | 6 | 0 | — taxonomy only |
| WST01 | 6 | 179 | 0 |
| WMA14 | 7 | 130 | 0 |

4PM1 and 4MB1 were fully verified in a later session than the project memory
recorded.

---

## 9. Mark-scheme matching re-checked, and the test-builder bridge

### Matching: 216/216, zero wrong

`scripts/check_s1_p4_markscheme_matching.py` reads the question number each
scheme **prints**, from flat text — independent of both the marks signal used to
attach and the parser's geometric cell reader. S1 127/127, P4 89/89, **0
disagreements, 0 unreadable**.

A content-overlap check was tried first and was worthless: it reported 66
suspects and every one hand-checked was correct. Maths mark schemes are almost
pure notation (~1,400 chars against a ~9,000-char question), so there is no
prose to match on — P4's median margin was **+0.008**, i.e. none. That is the
fifth probe in this project to produce false alarms; the rule stands that a
flagged case gets hand-checked before it is believed.

### Bridge to the test builder and worksheet generator

Those tools read `topics` + `pages`, not `workbook_questions`.

**Done:** topics created — **19 for WST01, 15 for WMA14**, one per workbook
section, code = section code. `normalizeTopicCodes` already passes dotted codes
through, so no UI change was needed.

**Deliberately not done: no `pages` rows written.** `pages` has **no RLS gate on
verification** — anything there is instantly live in the test builder, unlike
`workbook_questions`. The publisher defaults to verified-only and currently
writes nothing, because all 309 questions are still awaiting review.

### Live in both tools (2026-09-15)

Three separate blockers, all of which apply to any future subject:

1. **Public access had silently lapsed** — `publicToolsTrial.ts` had a hardcoded
   end date of 2026-08-14 that passed a month ago, quietly putting both tools
   back behind `/login`. Now driven by `PUBLIC_TOOLS_ACCESS_UNTIL`; an
   unparseable value fails **open**, since failing closed is what caused this.
2. **Both pages carry a hardcoded subject allowlist** — a subject does not
   appear however much data it has until it is in both lists.
3. The questions must be in `pages`.

**Published 262 of 309 with `--agreed-only`** (S1 141, P4 121) — only questions
where both classifier families agreed; the 47 disputed/same-chapter are held
back. Nothing is human-verified yet and the script reports that rather than
calling them verified.

Verified by replaying the test builder's own query path: 19 and 15 distinct
topics tagged, topic filters return expected counts, PDFs return 200.

To publish the remaining 47: verify at `/admin/workbook/verify`, then
`python scripts/publish_{s1,p4}_to_pages.py --execute`.

---

## 9. Closed decision: the legacy C4/C34 papers


P4 at 130 questions is the smallest corpus of the four workbook subjects. The 14
legacy papers in the same folder (4 × C4 at 75 marks, 10 × C34 at 125) could
roughly double it, and legacy C4 content overlaps WMA14 heavily — partial
fractions, parametric equations, implicit differentiation, integration by
substitution and parts, differential equations, volumes of revolution, vectors.

But they are a different specification. C4 and C34 both examine the trapezium
rule and numerical iteration, which are P2/P3 under the 2018 spec, and the C34
papers additionally carry a whole C3 half (functions, trig identities, numerical
methods) that is not P4 at all.

**Decided 2026-09-12: P4 stays on the new specification only.** The 14 legacy
papers are out of scope and the cover gate enforces it. Retained here as the
rationale, and because the option remains open later.

Original recommendation: ship the pure WMA14 window first. Get segmentation,
classification and verification working on 130 clean on-specification questions,
then mine the legacy papers as a Phase 1b with a per-question specification
filter and a distinct provenance flag so a student can see which are legacy. That
keeps the first release correct and the expansion reversible. Adding them up
front means every off-spec question has to be caught by a human in the verify UI.

---

## 10. Remaining phases

Port the FPM/Maths B scripts, one dedicated pair per subject.

| Phase | S1 | P4 |
|---|---|---|
| 0 taxonomy | **DONE** | **DONE** |
| 1 segment (QP) | **DONE** — 179 q, gate PASS | **DONE** — 130 q, gate PASS |
| 1 segment (MS) | **DONE** — 127 attached | **DONE** — 89 attached |
| 2 enrich | **DONE** — 179 records | **DONE** — 130 records |
| 3 classify + cluster | **DONE** — 18/19 sections | **DONE** — 15/15 sections |
| 4 load | **DONE** — 179 rows | **DONE** — 130 rows |
| 2 enrich | `enrich_s1_workbook_questions.py` | `enrich_p4_workbook_questions.py` |
| 3 classify + cluster | `classify_s1_workbook_sections.py`, `cluster_s1_archetypes.py` | `classify_p4_…`, `cluster_p4_…` |
| 4 load | `load_s1_workbook_to_db.py` | `load_p4_workbook_to_db.py` |

Non-negotiables carried over from the first two subjects:

- **Dedupe the reused papers first** (§2) — before segmentation, not after.
- **The loader must treat a row with `verified_at` set as authoritative**,
  refreshing only mechanical fields and routing the classifier's newer opinion to
  `proposed_section_id`. This is the rule that lets verification run while the
  pipeline is still being re-run.
- **Pre-flight every row against the schema in dry-run mode too.** A dry run
  never attempts an insert, so it never meets a CHECK constraint — that is how
  1046 Maths B rows got 295 in before aborting.
- **Page PostgREST reads explicitly.** It silently caps at 1000 rows.
- **Write caches atomically** (temp file + `os.replace`).
- **Record which model answered** in the classification cache and print the
  breakdown; a silent fallback classified 180 FPM questions before anyone noticed.
- **Never use a model's self-reported confidence to triage.** Measured spread
  across the full range of correctness was 0.03. Two model families plus
  disagreement is the signal that works.
- R2 prefix `workbook/s1/…` and `workbook/p4/…`, separate from `subjects/…`.
- Slugs `S1.CH04.S02.Q017` / `P4.CH06.S01.Q009`, issued once, matched on
  `(source_paper_key, source_question_number)`, never renumbered.
- The unique key on `workbook_questions` is per-subject as of migration 17, so a
  third and fourth subject will not collide on a shared paper key.
- The verify UI at `/admin/workbook/verify` is already subject-generic — no UI
  work needed.
