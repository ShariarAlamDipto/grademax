# IGCSE commerce worksheet and test tools

Accounting (4AC1), Business Studies (4BS1) and Economics (4EC1) are available
in the shared subject list used by `/generate` and `/test-builder`.

The question bank contains 591 verified question/mark-scheme pairs:

| Subject | Paper 1 | Paper 2 | Total |
| --- | ---: | ---: | ---: |
| Accounting | 236 | 40 | 276 |
| Business Studies | 72 | 68 | 140 |
| Economics | 83 | 92 | 175 |

These are complete numbered questions, including their subparts. Filters
describe exam-paper scope rather than individual chapters. Business questions
retain the supplied formula sheet and shared case study. Difficulty ratings
are unavailable; the controls keep the difficulty filter empty for these subjects.
PDF cover totals use the marks read from each verified question.

Only current-specification papers are included. Legacy papers, missing source
files and pairs that fail the existing proof gate remain in the staging report
and are not served by the tools.

Paper names follow the Pearson specifications and paper covers:
[Accounting](https://qualifications.pearson.com/en/qualifications/edexcel-international-gcses/international-gcse-accounting-2017.html),
[Business](https://qualifications.pearson.com/content/dam/pdf/International%20GCSE/Business%20Studies/2017/specification-and-sample-assessment/9781446942765-international-gcse-business-specification.pdf),
and [Economics](https://qualifications.pearson.com/en/news-policy/subject-updates/economics/international-gcse-economics-assessmentsupport.html).

## Updating the bank

```powershell
node --env-file=.env.local scripts/cache-commerce-sources.mjs
.venv/Scripts/python -X utf8 scripts/onboard_igcse_commerce.py --subject 4AC1 --cached-sources
node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4AC1
node --env-file=.env.local scripts/publish-commerce-questions.mjs --subject 4AC1 --execute
```

Repeat staging and publishing for `4BS1` and `4EC1`. Run publications sequentially.
The publisher adds missing questions and topics, saves a timestamped backup,
uploads all PDFs before inserting their URLs, and mirrors new rows to `questions`.
It also updates `src/lib/commerceQuestionMarks.json`; deploy that file with the
website so new questions have accurate PDF totals. Existing rows are preserved.

Staging reports and PDFs are under `data/analysis/live_rebuild/<code>/`.
Publication backups are under `data/backups/commerce_onboarding_<timestamp>/`.

## Verification

TypeScript and lint checks passed, together with 58 Node tests and four Python
tests covering question boundaries, complete coverage, shared references and
paper variants. Both local routes returned HTTP 200 and listed all three codes.
Live PDF smoke checks build a question paper and mark scheme from both paper
filters for each subject; artifacts are in
`data/analysis/live_rebuild/commerce-smoke/`.
