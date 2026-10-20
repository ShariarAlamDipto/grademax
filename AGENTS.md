# AGENTS.md — read this before changing GradeMax

GradeMax (Next.js 16 + Supabase + Cloudflare R2, deployed on Vercel) serves Edexcel and
Cambridge past papers. It also offers two question tools: the **Worksheet Generator**
(`/generate`) and the **Test Builder** (`/test-builder`). Two agents work in this repository:
Claude Code and Codex. This file records the rules that keep their work from colliding, and
the state of the most recent work.

> The repository is **public**. Never write keys, passwords, service-role tokens or
> `.env.local` values into this file, a script, a doc or a commit.

---

## 1. Ground rules (do not break these)

1. **Do not rewrite shared files to add one subject.** Change only what the new subject
   needs. If a working-tree file already holds someone else's uncommitted change, leave it
   alone. Never "simplify" a file whose existing behaviour you have not read.
2. **The tool subject list has one source of truth:** `TOOL_SUBJECT_SLOTS` in
   `src/lib/toolSubjects.ts`. Add a subject there and nowhere else. Both tool pages call
   `getToolSubjects()`, which provides the list.
3. **Keep the tool pages as they are.** Do not rewrite `src/app/generate/page.tsx` or
   `src/app/test-builder/page.tsx`. Each one does three things that must be kept:
   - `await connection()`: the page renders per request, because the access gate depends
     on the date.
   - The login gate: `/generate` redirects to `/login?next=/generate`, and `/test-builder`
     shows `TestBuilderLanding` to logged-out visitors. Both gates are skipped while
     `isPublicToolsTrialActive()` is true.
   - `getToolSubjects()`: an `unstable_cache` lookup that refreshes after 1 hour, which
     keeps Supabase round trips per visit low. The site has already run over its Vercel
     Hobby limits once.
   The same applies to `src/app/api/worksheets/generate-v2/route.ts`. It must keep
   using `auth.supabase` (the user-scoped client, not `auth.db`). Its `worksheet_items`
   insert stays non-fatal (it logs the error): a failed history save must never block
   the user's PDF. Add features to the current file; never paste an older copy over it.
   The test-builder route keeps `toAbsolutePdfUrl()` on both PDF URLs.
4. **One dedicated script per subject.** Do not add a new subject to an existing
   multi-subject script. Shared helpers in `scripts/lib/` may be imported and reused.
5. **The question ↔ mark-scheme pairing gate is never weakened.** A question is
   published only when its pairing is `PROVEN`, `SEQUENCE_PROVEN`, `LABEL_PROVEN` or
   `REVIEWED_PROVEN` (`PUBLISHABLE` in `scripts/lib/igcse_science_rebuild.py`). If a
   paper fails, hold it and write down why. Never loosen the check to make it pass.
6. **Chapter or topic tags come from reading each question, never from keywords.** Every
   read records its chapters, difficulty and reason, plus the SHA-256 of both the QP and
   the MS PDF. If a PDF is regenerated, its read is stale and the question must be read
   again.
7. **Live database writes:** dry run first. Back up the affected rows into
   `data/backups/<task>_<date>/`. Guard every update by requiring the old value to still
   be there. Re-read after writing. Use `--execute` only after the dry run shows exactly
   the intended change.
8. **Git:** production serves `main`. Work is committed on `V1`, and `main` receives it by
   a merge or fast-forward. Check `git rev-list --left-right --count main...V1` first.
   Commit or push only when the user asks. Use conventional commits
   (`feat:`, `fix:`, `docs:` …). Never commit or push large "everything in the working
   tree" changes; the tree always holds unrelated in-progress work.
   **What may be committed** is set by `.gitignore` (17 Oct 2026). Never commit
   `data/supabase-export` (every user's email), `data/backups`, raw paper archives,
   built books or segment PDFs (R2 serves them), predictions, `output/` or `tmp/`. Do
   commit code, tests, docs, the JSON work product in `data/workbook`, and each
   subject's chapter decisions in `data/analysis/live_rebuild/<code>/`
   (`topic_reads.json`, `topics_new.json`, `manual_review.json`). Never use
   `git add -f` on an ignored path, and never restore a file from an old commit over
   newer work: on 17 Oct the April copy of `generate-v2/route.ts`, which lacks the
   30-question limit, reappeared in the working tree and had to be reverted.
9. **Print books** (chapterwise and yearwise) always ship as two editions that differ
   only in their watermark: a GradeMax store edition and the user's students edition.

---

## 2. How the tools read data

| Piece | Where |
| --- | --- |
| Subject list and initial topics | `src/lib/toolSubjects.ts` → `getToolSubjects()` |
| Per-subject filter behaviour | `src/lib/igcseToolSubjects.ts`: `usesExamPaperFilters` (Business 4BS1, Economics 4EC1: filter by whole paper), `usesChapterFilters` (Computer Science), `toolSubjectDisplayCode` (shows `4CP1` as `4CP0`) |
| Question search (Test Builder) | `src/app/api/test-builder/questions/route.ts`, which filters `pages.topics` with `.overlaps()` |
| Worksheet generation | `src/app/api/worksheets/generate-v2/route.ts`, which also filters `pages.topics` |
| PDF assembly | `src/lib/questionPdfAssembly.ts` |
| Marks printed on PDFs | `src/lib/questionMarks.ts`, which merges `commerceQuestionMarks.json` and `computerScienceQuestionMarks.json` (key `paperId|questionNumber`). Questions with no known marks count as 4. |
| Question limit | `src/lib/toolLimits.ts` (30 questions for normal students; admins, teachers and Pro users unlimited) |

Each question is a row in **`pages`** (`is_question = true`, `topics text[]`,
`difficulty`, `qp_page_url`, `ms_page_url`). It also has a row with the **same id** in the
**`questions`** table, kept for saved downloads. The tools filter only on
`pages.topics`. Topic rows (`topics` table, `code` + `name` per subject) give the chapter
names.

---

## 3. IGCSE Computer Science: current state (audited 16 Oct 2026)

Full write-up: `docs/igcse-computer-science-tools.md`. Staging and evidence:
`data/analysis/live_rebuild/4CP1/`.

### Identity
- The database subject has code **`4CP1`** (id `8c628af9-d6b2-41a4-a0a3-d7575e82a731`)
  and holds Pearson's **4CP0** specification papers. The UI shows `4CP0`. Do not create
  a second subject.

### Chapters = the six specification topics
`1` Problem solving · `2` Programming · `3` Data · `4` Computers ·
`5` Communication and the internet · `6` The bigger picture.

Questions are **whole questions with every subpart**. One question usually spans several
chapters, so `topics` has several codes with the main chapter **first**.

Topic mapping decisions confirmed against the spec text (follow these):
- Boolean logic and truth tables → **4** (4.3). Encryption and ciphers → **3** (3.4).
- Anti-malware and utility software → **4** (4.4.2). Simulation and modelling → **4** (4.4.3).
- Cloud storage concept and benefits → **4** (4.2.6). Cloud security → **5** (5.2.2).
- Audit trails, code reviews, penetration testing, phishing and authentication → **5** (5.2).
- AI, quantum, DNA, nanotechnology, intellectual property, licensing, environment and
  ethics → **6**.
- Algorithm tracing, flowcharts and pseudocode → **1**, plus **2** when the question
  writes, corrects or explains code constructs.

### What is live (verified 16 Oct 2026)
- **48 questions** = Paper 1 Q1–Q6 for 2019 Jun, 2020 Nov, 2021 Jun, 2021 Nov, 2022 Jun,
  2023 Jun, 2024 Jun and 2026 Jun. Each paper's questions total 80 marks. The archive has
  no 2025 paper.
- Chapter counts: 1 = 8, 2 = 10, 3 = 18, **4 = 23**, 5 = 19, 6 = 10. Difficulty:
  2 easy, 19 medium, 27 hard.
- All 96 R2 PDFs match their local SHA-256. Every MS segment was checked independently:
  each holds only its own question number, and its part letters match the QP.
- **Paper 2 is deliberately held.** It is an on-screen practical that needs external
  code and data files. Four pairs also fail the source-identity check: 2020 Nov, 2021 Jun,
  2021 Nov and 2022 Jun. Do not publish Paper 2 as PDF questions.

### Changes Claude made on 16 Oct 2026 (do not undo)
1. **Tag fix:** chapter `4` was added to `2022_may-jun_P1|3`, `2023_may-jun_P1|6` and
   `2026_may-jun_P1|4`, because each has a cloud-storage benefit part (spec 4.2.6). The
   change is in `topic_reads.json` and in live `pages.topics`. Old values and live
   rows are in `data/backups/codex_tool_pages_2026-10-16/`.
2. **Reverted Codex's rewrite of `src/app/generate/page.tsx` and
   `src/app/test-builder/page.tsx`.** It read a shorter IGCSE-only list, which dropped
   Maths A (4MA1), Human Biology (4HB1) and every IAL unit (P1–P4, M1, S1). It also dropped
   the login gate and the cache. The rejected patch is
   `data/backups/codex_tool_pages_2026-10-16/tool_pages.patch`; do not reapply it.
   `IGCSE_TOOL_SUBJECT_SLOTS` was deleted from `igcseToolSubjects.ts` for the same reason.
3. SEO text: Computer Science added to the `/generate` and `/test-builder` metadata
   keywords and to `TestBuilderLanding`. The test-builder description again names
   Physics, Maths, Chemistry and Biology.

### Pipeline (run from the repo root)
```powershell
node --env-file=.env.local scripts/cache-commerce-sources.mjs --subject 4CP1
.venv/Scripts/python -X utf8 scripts/onboard_igcse_computer_science.py stage   # segment + pairing proof -> verdicts.json
.venv/Scripts/python -X utf8 scripts/onboard_igcse_computer_science.py dump    # review.txt for reading
#   -> read every new QP+MS pair, add it to topic_reads.json (topics, difficulty, reason, qp_sha256, ms_sha256)
.venv/Scripts/python -X utf8 scripts/onboard_igcse_computer_science.py audit   # writes artifact_audit.json (pins hashes)
.venv/Scripts/python -X utf8 scripts/render_computer_science_pdfs.py           # review sheets in review/, then LOOK at them
node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4CP1            # dry run
node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4CP1 --execute  # inserts NEW questions only
npx tsx --env-file=.env.local scripts/verify_computer_science_tools.ts                      # read-only live check
.venv/Scripts/python -X utf8 -m unittest tests/test_igcse_computer_science.py
```

Things the pipeline enforces (keep them):
- `audit` fails unless every publishable question has a read, each paper has Q1–Q6
  totalling 80 marks, there are no duplicate PDFs, every barcode and subject/paper
  identity matches, and the paper has current whole-paper pairing evidence.
- `publish-commerce-questions.mjs` **only inserts.** It refuses to run when
  `artifact_audit.json` is stale against `verdicts.json` or `topic_reads.json`. It also
  **throws** when a live row's topics or difficulty differ from the reads.
  ⇒ **To change tags on questions already published:** edit `topic_reads.json`, rerun
  `audit`, then apply a small guarded update to `pages.topics` (rule 7). Do not delete
  and re-insert rows: that changes ids, and saved downloads in `questions` depend on them.
- `onboard_igcse_computer_science.py` disables `garbage=3` when saving PDFs; Pearson CS
  mark schemes stall on it. That setting affects this subject only.

### Not done yet
- **Nothing is committed or deployed.** The CS UI files (`toolSubjects.ts` slot,
  `igcseToolSubjects.ts`, `questionMarks.ts`, `computerScienceQuestionMarks.json`,
  `TestBuilderPage.tsx` / `FilterBar.tsx` / `SubjectSelector.tsx` / `WorksheetGenerator.tsx`
  edits) are uncommitted in a working tree full of other work. Stage files by name and
  deploy them together; the marks JSON must ship with the UI.
- **Possibly mislabelled files:** the Paper 2 files for 2020 Nov, 2021 Jun, 2021 Nov and
  2022 Jun failed the identity check, so the files on the past-papers pages may carry the
  wrong labels. Not yet investigated.
- **Possible improvement:** splitting whole questions into parts would make chapter
  filters exact, but it would change ids and needs the user's approval first.

### Review of all Codex work, 17 Oct 2026
Verified as correct and kept: commerce/CS tool UI (marks, filters), the Maths A wiring,
the root-layout SEO cleanup (the site-wide homepage canonical was removed and pages now
use `publicPageMetadata()` from `src/lib/metadata.ts`), the single homepage `<h1>`, the
`/books/bangladesh` page, the store copy (checked against `src/lib/store/pricing.ts`),
the past-papers year page reading `getPapersIndex()`, and the yearwise store prices
(M1 ৳550, S1 ৳350, P4 ৳350). All live tool subjects have zero orphan or untagged
questions.

Fixed:
- generate-v2 route: Codex's version was an older copy of the file. It was restored and
  the marks feature re-added.
- The test-builder route's `toAbsolutePdfUrl()` was restored.
- `/edexcel-worksheets` FAQ: the subject list is complete again.
- The sitemap lists `/generate` only while `isPublicToolsTrialActive()` is true.
- `/books/bangladesh` showed the currency twice ("৳550 BDT").
- The publisher no longer recreates Accounting's `1`/`2` topics.

The promo banner is no longer rendered (the user asked for its removal on 13 Oct), so
`PromoBanner.tsx`, `PromoBannerClose.tsx` and the `.gm-promo*` CSS are now unused.

---

## 4. Related subjects onboarded the same way (16 Oct 2026)
- **Accounting 4AC1:** 20 spec chapters, 276 questions read, live. Taxonomy is in
  `scripts/lib/accounting_topics.py`, reads are in
  `data/analysis/live_rebuild/4AC1/topic_reads.json`, and changes are applied with
  `scripts/apply_accounting_tool_topics.py` (refuses to run while any live question is
  unread).
  New Accounting papers: `publish-commerce-questions.mjs --subject 4AC1` inserts them
  with a temporary paper tag (it no longer recreates the `1`/`2` topic rows). Then read
  them and run the apply script, which re-tags them.
- **Business 4BS1 and Economics 4EC1:** still filtered by whole exam paper (`1`/`2`), as
  set in `usesExamPaperFilters`. Difficulty is disabled for them in the UI.
