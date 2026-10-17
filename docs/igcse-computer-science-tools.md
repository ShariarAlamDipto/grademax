# Chapterwise IGCSE Computer Science tools

Computer Science is wired into `/generate` and `/test-builder`, using the
six chapters in the [Pearson Edexcel 4CP0 specification](https://qualifications.pearson.com/content/dam/pdf/International%20GCSE/computer-science/2017/specification-and-sample-assessments/international-gcse-in-Computer-Science-Specification.pdf).
The existing archive subject ID is `8c628af9-d6b2-41a4-a0a3-d7575e82a731`,
internally coded `4CP1`. The selectors display Pearson's official `4CP0` code.

The published database bank contains **48 complete written questions and 48
matching mark schemes** from eight 80-mark papers: June 2019, November 2020,
June/November 2021, June 2022, June 2023, June 2024 and June 2026.
No 2025 paper is present in the current live archive.

| Code | Chapter | Questions |
| --- | --- | ---: |
| 1 | Problem solving | 8 |
| 2 | Programming | 10 |
| 3 | Data | 18 |
| 4 | Computers | 23 |
| 5 | Communication and the internet | 19 |
| 6 | The bigger picture | 10 |

Questions retain every subpart, diagram and answer area. A complete question
can assess several chapters, so these counts overlap. Chapter decisions list
the primary assessed chapter first. A 16 October 2026 audit added chapter 4
(4.2.6 cloud storage) to 2022 Q3, 2023 Q6 and 2026 Q4, whose cloud-benefit
parts had no Computers tag; the live rows were updated in place. Difficulty is a reviewed estimate: two
easy, 19 medium and 27 hard questions. PDF totals use the verified marks.

Paper 2 is held: practical tasks depend on external code/data files, and four
source pairs also fail the source-code identity check. Those tasks are not
standalone PDF questions. Their status is recorded per paper in `verdicts.json`.

## Protocols and evidence

- Question boundaries use the existing total-line segmenter and preserve original PDF content.
- The existing pairing gate proves 21 pairs by number/marks and 27 by question
  labels plus the current whole-paper pairing audit. No gate was weakened.
- A direct QP/MS reading records the assessed chapters, difficulty and reason
  for every question. SHA-256 fingerprints bind each decision to both PDFs.
- The artifact audit checks coverage, unique PDFs, question fences, source
  barcodes, matching subject/paper identity and complete 80-mark papers.
  It requires the prior pairing audit to match the current source URLs.
- The 2020 deferred paper retains its original May cover date; its November
  scheme and current whole-paper pairing evidence qualify the autumn sitting.
- All 96 PDFs (295 pages) were rendered. Review sheets were visually inspected;
  the automated overlay check found no red-grid overlays.
- Publication backs up database metadata and uploads content-hashed objects
  before inserting URLs. Existing rows are preserved and saved-download
  `questions` mirrors retain the same IDs, URLs and difficulty.
- The publisher refuses missing/invalid chapter reads, changed PDFs and stale
  artifact-audit input fingerprints. A repeated dry run proposes zero changes.

The subject-specific PDF writer disables optional resource deduplication,
which stalled on a shared-resource mark scheme. It retains vector content,
uses the same cut boundaries and preserves hidden-layer settings. The default
behaviour for other subjects is unchanged. OCR caches are written atomically.

## Rebuild and verify

From the repository root:

```powershell
node --env-file=.env.local scripts/cache-commerce-sources.mjs --subject 4CP1
.venv/Scripts/python -X utf8 scripts/onboard_igcse_computer_science.py stage
.venv/Scripts/python -X utf8 scripts/onboard_igcse_computer_science.py dump
```

Read each complete QP/MS pair and update `topic_reads.json` with its chapter
codes, difficulty, reason and both PDF hashes. Regenerating PDFs can invalidate
their old byte fingerprints; changed files require another review.

```powershell
.venv/Scripts/python -X utf8 scripts/onboard_igcse_computer_science.py audit
.venv/Scripts/python -X utf8 scripts/render_computer_science_pdfs.py
node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4CP1
node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4CP1 --execute
npx tsx --env-file=.env.local scripts/verify_computer_science_tools.ts
```

The publisher also updates `src/lib/computerScienceQuestionMarks.json`; deploy
that file with the UI changes. Staging, reads, audit reports and smoke PDFs are
under `data/analysis/live_rebuild/4CP1/`. The database backup is under
`data/backups/commerce_onboarding_2026-10-16T14-20-27-087Z/4CP1/`.

## Validation and release state

On 16 October 2026, all 48 database rows and their mirrors matched the reviewed
metadata, and all 96 public PDF downloads matched their local SHA-256 hashes.
Anonymous chapter and difficulty queries returned the expected counts. The
application assembler produced a six-question, 22-page worksheet and matching
19-page scheme with zero placeholders; the rendered output was inspected.

Both local tool routes returned HTTP 200 and included Computer Science. The
topics endpoint returned all six chapters. The 58 application tests, six
Python checks, TypeScript and targeted frontend lint checks passed.

**Database publication is complete. The UI and marks-map changes are in the
local workspace and have not been deployed to the hosted website.**

The tool pages list subjects from `TOOL_SUBJECT_SLOTS` in
`src/lib/toolSubjects.ts` (cached, with the login gate). An earlier rewrite of
`src/app/generate/page.tsx` and `src/app/test-builder/page.tsx` that read a
shorter IGCSE-only list was reverted because it dropped Mathematics A, Human
Biology and every IAL unit; its patch is kept under
`data/backups/codex_tool_pages_2026-10-16/`.
