# Chapterwise workbook — Mathematics A (4MA1), Higher Tier papers 1H and 2H

Fifth subject for the chapterwise workbook, after 4PM1 (Further Pure Maths),
4MB1 (Maths B) and the two IAL units WST01/WMA14. Same phases, **separate
scripts per subject** — `*_mathsa_*`, never added to the FPM or Maths B ones.

Maths A is an IGCSE, so the method it ports is the **IGCSE one** (end-fence
labelling + y-crop segmentation) from 4PM1/4MB1 — *not* the IAL page-header
method built for S1/P4. IAL prints `Question 1 continued` in every page header;
Edexcel IGCSE does not.

Subject `4MA1` = `8b7b0cb0-e95c-480d-ac0a-c710f1e59213`.
Source archive: `data/Ultimate Final IGCSE/Mathematics_A/<year>/<session>/`.
Output tree `data/workbook/mathsa/`, gitignored like the others.

Everything below is measured over the archive, not assumed.

---

## 1. Scope: which files are actually 4MA1 Higher

### THE BIG FINDING: every "1H"/"2H" before June 2018 is really 4MA0 3H/4H

The archive holds 648 Maths A PDFs and the filenames are **not** evidence. Read
off each paper's own cover:

| Filename says | Cover says | Sessions |
|---|---|---|
| `Paper_1H` | **4MA0/3H** | 2011 May-Jun → 2018 Jan |
| `Paper_2H` | **4MA0/4H** | 2011 May-Jun → 2018 Jan |
| `Paper_1HR` | **4MA0/3HR** | 2013 May-Jun → 2018 Jan |
| `Paper_2HR` | **4MA0/4HR** | 2013 May-Jun → 2018 Jan |
| `Paper_1H`/`2H`/`1HR`/`2HR` | **4MA1/1H, 2H, 1HR, 2HR** | 2018 May-Jun onwards |

**38 of 123 Higher-tier filenames disagree with their own cover**, and every one
of those files is a duplicate of the correctly-named `3H`/`4H` file sitting
beside it in the same folder. The old 4MA0 specification had no papers 1H or 2H
at all — its Higher tier *was* 3H and 4H — so a "2016 Paper 1H" cannot exist.

This is the same class of defect as the P4 folder (see
`docs/workbook-s1-p4-plan.md` §2) and it is invisible to any filename or
paper-code audit.

**4MA1's first assessment was June 2018.** Scope is therefore
**2018 May-Jun onwards**, which is also exactly the set the user asked for.

### Two traps that produce false cover evidence

1. **The untiered `Paper_1` / `Paper_2` / `Paper_1R` / `Paper_2R` files are all
   Foundation** (`4MA0/1F`, `4MA1/2FR`, …), 100 of them. They look like they
   might hide an untiered Higher paper. They do not — every one reads
   Foundation.
2. **Some covers extract only a PMT watermark**, e.g. `2015 May-Jun Paper 1H`
   yields `4MA1 | 2015 | May/June | Paper 1H |`. That string is
   PhysicsAndMathsTutor's own label, not the Pearson cover, and it is wrong
   here (there was no 4MA1 in 2015). `scripts/audit_igcse_edexcel_labels.py`
   already documents this trap. **Strip the watermark before reading a cover.**
   The 2019 Jan papers are the benign version of the same thing — their covers
   carry no extractable `4MA1/1H`, but the page-2 barcodes (`P59017A`,
   `P59019A`, `P59022A`, `P59024A`) and the "International GCSE Mathematics
   Formulae sheet – Higher Tier" line confirm them as genuine 4MA1 Higher.

### The corpus: 43 papers

| Session | Papers present |
|---|---|
| 2018 May-Jun | 1H 1HR 2H 2HR |
| 2019 Jan | 1H 1HR 2H 2HR |
| 2019 May-Jun | 1H 1HR 2H 2HR |
| 2021 Oct-Nov | 1H 2H |
| 2022 Jan | 1H 1HR 2H 2HR |
| 2022 May-Jun | 1H 1HR 2H 2HR |
| 2023 Jan | 1H 1HR 2H 2HR |
| 2023 May-Jun | 1H 1HR 2H 2HR |
| 2023 Oct-Nov | 1H 2H |
| 2024 May-Jun | 1H 1HR 2H 2HR |
| 2024 Oct-Nov | **2H only** |
| 2025 May-Jun | 1H 1HR 2H 2HR |
| 2025 Oct-Nov | 1H 2H |

**Archive gaps, all confirmed absent rather than misfiled:**

- **2020 Jan, 2020 Oct-Nov, 2021 Jan, 2021 May-Jun carry no Higher-tier paper
  at all** — Foundation only. Roughly 12–14 papers.
- **2024 Oct-Nov 1H** is missing (its 2H is present).

These are gap-fill candidates for `scripts/fill_edexcel_gaps_from_pearson.py`.
The book can ship without them; widening later is a re-run, not a redesign.

**No duplicate papers.** A shingle-Jaccard comparison of watermark-stripped text
across all 43 found no pair above 0.90. The COVID reuse that produced five
duplicate S1/P4 papers does not appear here — largely because the 2020/2021
sessions that would carry it are the ones missing from the archive.

---

## 2. Scale and shape (measured)

- **43 papers, 1,042 questions.** 1,036 parse from a printed fence; 6 more are
  recoverable (§4).
- **~24 questions per paper**, both papers alike — unlike Maths B, where
  Paper 1 (28 short) and Paper 2 (11 long) differ sharply. 1H and 2H are the
  same shape here, so one set of rules covers both.
- **Every paper totals exactly 100 marks** — the same audit-gate invariant FPM,
  Maths B, S1 and P4 all use. 39 of 43 hit it on fences alone.
- Fence wording is the IGCSE one, `Total for Question N is X marks`, so
  `FENCE_RE` ports from Maths B unchanged.

### Mark tariffs and difficulty bands

n=1,036 · mean **4.13** · median **4** · range **2–9**

| marks | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|
| count | 81 | 320 | 262 | 216 | 99 | 36 | 17 | 5 |

Maths A questions are **short** — 90% are 3–6 marks, and nothing exceeds 9.
Neither predecessor's bands transfer: FPM's (≤6 easy / ≤10 medium) would call
94% of the book easy, and Maths B's (≤3 / ≤6) leaves only 6% hard.

**Bands for Maths A: ≤3 easy · 4–5 medium · ≥6 hard** → 39% / 46% / 15%.

---

## 3. Segmentation: y-crop required, and the `set_cropbox` trap is live

**13% of fence pages also start a later question** (130 of 1,036). Page-range
splitting would staple those questions together — the exact defect the rebuild
exists to remove. So Maths A needs **Maths B's y-crop segmenter**, not FPM's
page ranges.

**34 of the 43 papers have `CropBox != MediaBox`.** This is precisely the
condition that cost the Maths B build 137 audit defects: `get_text` reports
coordinates against the **CropBox** (`page.rect`), but `set_cropbox` takes
**MediaBox** coordinates, so every band lands ~28pt off and each question's PDF
silently captures its *predecessor's* fence.

**Use `show_pdf_page(..., clip=...)` onto a fresh page.** Its `clip` is in the
source page's own coordinate space — the same space `get_text` reports — so no
conversion is involved. Whole uncropped pages still go through `insert_pdf`.
This is a port, not a rediscovery: `scripts/build_mathsb_workbook_segments.py`
already does it correctly.

Band coordinates are read, not guessed: top = the printed left-margin question
number (`x0 < 80`, excluding the bottom 60pt so page-number footers cannot
match); bottom = the fence line's bottom. Adjacent bands share a single midpoint
so neighbouring crops cannot overlap.

---

## 4. The four 2019 Jan papers

All four lose fences — the text `Total for Question N` is **entirely absent**
for specific questions, not garbled, so this is a missing-text-layer problem
rather than the +29 CMap shift seen elsewhere.

| Paper | N | missing fences | shortfall | resolution |
|---|---|---|---|---|
| 2019 Jan 1H | 21 | Q2, Q3 | 10 | ambiguous — two gaps |
| 2019 Jan 1HR | 23 | Q7, Q10 | 6 | ambiguous — two gaps |
| 2019 Jan 2H | 23 | Q10 | 3 | **automatic** — single gap, Q10 = 3 |
| 2019 Jan 2HR | 23 | Q18 | 4 | **automatic** — single gap, Q18 = 4 |

Maths B's `recover_missing_fence` handles a single gap from the 100-mark total
with no ambiguity, so 2H and 2HR recover in code. 1H and 1HR need four values in
`MANUAL_QUESTION_MARKS`, **read off rendered pages** (`get_pixmap(dpi=100)`),
never inferred — the Maths B note on this is explicit that the mark-scheme
column can mislead because it holds per-part marks. Entries must still sum to
the shortfall or the paper fails.

Recovered questions carry no fence, so the audit counts them on a separate
`boundary-inferred` line rather than as defects.

---

## 5. Mark schemes — the best starting position of any subject so far

**All 43 mark schemes are present** (0 missing, unlike P4's two absent files),
and none is image-only (14k–32k characters each).

- **38 of 43 print a per-question `Total N marks` tally** — Maths B's Format A,
  the layout that reached 93% (FPM) and 89% (Maths B) coverage.
- **5 print no per-question total at all**: `2018_may-jun_1H` and all four
  `2019_jan_*`. These are Maths B's Format B — one continuous table where the
  question number is a standalone integer in the leftmost column and its mark
  is the standalone integer in the far-right column at the same y.

Both layouts are already implemented in
`scripts/build_mathsb_workbook_segments.py` (`ms_totals_in_order`,
`ms_question_rows`, `align_sequences`, `locate_ms_blocks`). Port them.

**Carry over the two hard-won rules:**

1. Align by **longest common subsequence** on mark values, not exact match — a
   single stray tally must not throw away a whole paper's scheme.
2. LCS *aligns on* marks, so "the marks agree" is circular and is **not**
   evidence. The real constraint is the skip pattern: accept when `skipQ == 0`
   or `skipMS == 0`; when **both** sides skip, the mapping is ambiguous and the
   paper gets no mark schemes. A wrong mark scheme is worse than a missing one.

MS pages mix portrait and landscape, so blocks are emitted as **whole pages**,
never geometrically cropped. The accepted consequence is that a page shared by
three questions attaches to all three.

---

## 6. Taxonomy — the specification's own structure, 1:1

Source: *Pearson Edexcel International GCSE in Mathematics (Specification A)
(9–1), Specification, Issue 2, November 2017*, **Higher Tier** content tables
(spec pp. 29–41). Read out of the PDF, not from memory.

Unlike Maths B — where the `topics` table had ten rows and Calculus had to be
added as an eleventh chapter — 4MA1's spec structure is clean and complete, and
the `topics` table holds **no** 4MA1 rows at all. So the workbook tree follows
the specification exactly: **6 chapters / 39 sections**, numbered as printed.

| # | Chapter | Sections |
|---|---|---|
| 1 | Numbers and the number system | 11 (1.1–1.11) |
| 2 | Equations, formulae and identities | 8 (2.1–2.8) |
| 3 | Sequences, functions and graphs | 4 (3.1–3.4) |
| 4 | Geometry and trigonometry | 11 (4.1–4.11) |
| 5 | Vectors and transformation geometry | 2 (5.1–5.2) |
| 6 | Statistics and probability | 3 (6.1–6.3) |

39 sections over 1,042 questions ≈ 27 per section — a practice set, in line with
4PM1 and 4MB1.

### Keeping the spec numbering costs three thin sections, deliberately

**1.11 Electronic calculators**, **1.10 Applying number** and **4.4 Measures**
are process statements: they are exercised *inside* other questions and are
never a question's own subject. Two options were weighed — drop them (36
sections, numbering no longer matching the spec) or keep them and let the book
generator skip empties. **Keep**, for the reason recorded on Maths B and S1:
keeping a thin section is reversible, deleting one needs a renumbering
migration.

**Classifier rule that follows from this:** 1.10, 1.11 and 4.4 are
**SECONDARY-only** labels and must never be assigned as a primary section.
Without that rule a catch-all named "Applying number" will absorb the book — the
same skew that put 111 of 431 FPM questions in one chapter, and the reason P4
needed its parametric rule.

### The evidence probe under-fires — do not size sections from it

A keyword probe over the 1,036 stems gives a usable ranking at the top
(4.9 Mensuration 136 · 4.10 3D shapes 107 · 1.8 Degree of accuracy 103 ·
4.1 Angles 95 · 2.2 Algebraic manipulation 83 · 6.3 Probability 78) but is
**wrong at the bottom**, and predictably so:

- **2.7 Quadratic equations: 7 hits.** Quadratics are routine in 1H/2H. The
  probe only ever matched the *formula sheet* ("The quadratic equation …"),
  because a real question says "Solve x² + 5x + 6 = 0" and never prints the word
  "quadratic".
- **1.4 Powers and roots: 2 hits**, for the same reason — indices questions show
  an expression, not a keyword.

This is the fourth time a probe has lied on this project (FPM keywords, Maths B
trig, S1/P4 markers). Treat these counts as directional only; **section sizing
comes from the specification, and the real distribution comes from the Phase 3
classifier**. Also note the formulae sheet sits before the first fence and
contaminates chunk 0 of every paper — strip it before any stem-level work.

---

## 7. Phases

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Spec study + taxonomy migration + apply | **this document + migration 20** |
| 1 | `scripts/build_mathsa_workbook_segments.py` → `data/workbook/mathsa/` | next |
| 2 | `scripts/enrich_mathsa_workbook_questions.py` | |
| 3 | `scripts/classify_mathsa_workbook_sections.py` | |
| 4 | `scripts/cluster_mathsa_archetypes.py` | |
| 5 | `scripts/load_mathsa_workbook_to_db.py` | |
| 6 | print build / covers / watermark | |

### Non-negotiables carried over from the first four subjects

- Loader treats `verified_at` rows as authoritative — new classifier opinion
  goes to `proposed_section_id`, never over a verified row.
- **Pre-flight every row against the schema in dry-run too.** A dry run never
  attempts an insert, so it cannot meet a CHECK constraint; that is how Maths B
  aborted 295 rows in.
- **Page every PostgREST read** — it silently caps at 1000 rows, and this corpus
  is 1,042.
- Archetype dedup must consult rows created *during* the run, not only those
  existing before it.
- Migration 17 already made `workbook_questions`' unique key per-subject, so
  4MA1 will not collide with 4PM1/4MB1 on a shared paper key.
- Slugs `MA.CH04.S09.Q017`, issued once. R2 prefix `workbook/mathsa/`.
- The verify UI `/admin/workbook/verify` is subject-generic — no UI work needed.
- **Verify against the artifact, not the script's own summary.** All four
  Maths B load bugs reported success while something was wrong.
