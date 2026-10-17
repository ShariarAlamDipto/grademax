# Maths A classification and segmentation — 13 October 2026

The tool rebuild publishes **2,067 Higher-tier questions from 88 papers**. This
includes the older 4MA0 3H/4H papers and the newer 4MA1 1H/2H papers, including
regional variants. The workbook plan's original 43-paper scope is a separate,
earlier corpus.

Every staged question now has section tags. The interrupted review's remaining
141 questions have been read; all 208 disputed questions have recorded decisions.
Eight earlier decisions were revised for consistency with the taxonomy and the
dominant assessed skill. Empty or scrambled text was checked against rendered
question pages where needed.

| Classification evidence | Questions |
|---|---:|
| Previously matched workbook question text | 1,036 |
| Agreement between two model families | 823 |
| Direct question review | 208 |
| Unresolved | 0 |

Direct reads include reasons and SHA-256 fingerprints of their question PDFs.
Regeneration refuses a changed reviewed PDF, invalid section codes, process-only
tags, duplicate tags, stale question keys, and inconsistent notes. It returns a
failure status when model disagreement still needs a direct read.

Artifacts are in `data/analysis/live_rebuild/4MA1/`:

- `topics_new.json`: primary section first, followed by secondary tags.
- `topic_sources.json`: classification provenance for every question.
- `topic_reads.json` and `topic_read_notes.json`: direct decisions and evidence.
- `classification_review.csv`: all 2,067 questions, tags, reasons and PDF paths.
- `artifact_audit.json`: the latest PDF audit results and any failures.
- `live_publication_audit.json`: live rows, storage checksums and public downloads.
- `metadata_apply.json`: applied worksheet tags and metadata backup location.
- `production_activation.json`: selector deployment status and published commit.
- `mathsa_smoke_worksheet.pdf` and `mathsa_smoke_markscheme.pdf`: PDFs assembled
  from three live questions using the application's PDF assembly function.
- `segments/`: question and mark-scheme PDFs.

The artifact audit reopens all PDFs, checks question fences, question-number
coverage, 100 marks per paper, duplicate files, and question/mark-scheme evidence.
For schemes whose totals cannot be read, it uses the existing whole-paper identity
audit only when that audit's source URLs still match current paper records. The
seven questions without a readable fence include image-only questions; their
existing segmentation review remains part of the evidence.

The completed audit **passes with zero failures**: all 4,134 PDFs are present,
all 88 papers have contiguous question numbering and total 100 marks, and every
question/mark-scheme pair qualifies. Fresh verdicts are 1,928 `PROVEN`, 46
`SEQUENCE_PROVEN`, 29 `REVIEWED_PROVEN` and 64 `LABEL_PROVEN`. The independent
whole-paper identity audit matches current source URLs for all 88 papers.

Validation commands:

```powershell
python -X utf8 scripts/classify_mathsa_tool_topics.py --review-only
python -X utf8 scripts/audit_mathsa_staged_artifacts.py
python -X utf8 -m unittest discover -s tests -p test_mathsa_tool_topics.py -v
python -X utf8 scripts/apply_mathsa_rebuild_topics.py
python -X utf8 scripts/publish_mathsa_live_segments.py
```

Publication and metadata application completed on 13 October 2026. The live
audit passes with zero failures: 2,067 question rows and matching question
mirrors, 36 topic definitions, 2,575 worksheet tag assignments, and all 4,134
storage object checksums. Sixteen public PDF downloads match their local files
exactly. Public difficulty filters return 773 easy, 904 medium and 390 hard.

Four classification regression tests, three upload regression tests and all 55
application tests pass. Publication inserts tags and difficulty with each row;
the metadata script verifies complete coverage before reconciling worksheet tags.
Uploads complete before any database URLs are written.

Backups are in `data/backups/live_ms_linkage_20261013_105431/` and
`data/backups/mathsa_metadata_20261013_110014/`. The subject-selector change adds
`4MA1` to the shared tool catalogue and changes the cache key to refresh the list.
TypeScript checking passes. The smoke worksheet merges all three live question
PDFs into three pages; the matching scheme has four pages. Both carry all three
question labels and contain no placeholders. The public topics endpoint returns
all 36 Maths A sections.

The selector change is committed as `cea957c81630eeb3350345dce181e096be0a236e`
and pushed to both `main` and `V1`. Vercel CLI authentication succeeded and the
clean deployment worktree is linked to team `grademax2`, project `grademax_`.

The first direct production deployment (`dpl_GG2uSREZNpJ6m8qbk7sQHytbsi4R`)
compiled and passed TypeScript, but failed after three prerender timeouts on
`/past-papers/english-language-b/2014`. Commit `f26b256d` replaces the year
page's extra database queries with the paper snapshot already used for its
navigation and the session pages. TypeScript and all 55 application tests pass.
Both branches include this fix. Replacement deployment
`dpl_BquwAV9QpAZ9CJzfhZkf9fSNzU5S` reached `READY` and was aliased to
`https://www.grademax.me`.

Live verification at 2026-10-13 06:47 UTC confirms that `/generate` and
`/test-builder` each return HTTP 200 and include Maths A (`4MA1`, subject ID
`8b7b0cb0-e95c-480d-ac0a-c710f1e59213`) in their actual tool subject lists.
The public topics endpoint returns all 36 topics. The previously failing
English Language B 2014 page returns HTTP 200. `live_release_check.json`
records these checks; `check_release.py` repeats them. Maths A is released.
