# Question Pattern Analyzer & Predictor

Analyzes every past Paper 1 / Paper 2 for a subject, finds recurring patterns and
cycles, and produces a **predicted paper** for an upcoming sitting as both a
data-driven **blueprint** (topic/marks/structure/confidence + evidence) and a
**written mock paper + mark scheme**.

First subjects: **Edexcel IGCSE Further Pure Maths (4PM1)** and **Physics (4PH1)**,
targeting the **October/November 2026** series.

## How it works

Heavy compute runs offline as Python; the Next.js admin UI (`/admin/predictor`)
consumes committed artifacts. Everything is driven by one config per subject so any
subject can be onboarded.

```
config/predictor/{CODE}.yaml          subject config (paper shape, spec eras, weights, target, LLMs)
scripts/predictor/
  02_extract_questions.py             per-question PDF -> structured record (PyMuPDF text + LLM classify)
  03_analyze_patterns.py              frequency / position / cycle / template / spec-shift analysis
  04_predict.py                       blueprint: slot-by-slot prediction (deterministic, evidence-cited)
  05_generate_paper.py                written mock paper + mark scheme (LLM, template-guided)
  06_render_pdf.py                    Markdown -> self-contained HTML (MathJax); optional PDF via Playwright
  07_publish.py                       copy artifacts into public/predictor/ + refresh index.json
  run_all.py                          chain the whole pipeline
  lib/                                env, folders, config, llm, extract_text, fingerprint, render_html
data/analysis/{CODE}/questions.jsonl  one record per historical question (the dataset)
data/analysis/{CODE}/patterns.json    computed patterns
data/analysis/{CODE}/report.md/html   human-readable pattern report
data/predictions/{CODE}/{session}_{year}/  blueprint.json, paper_p*.md/html, markscheme_p*.md/html, paper.json
public/predictor/                     published artifacts the admin UI serves
```

## Run

```bash
# Full pipeline for a subject (extract is the slow part: ~10-12 min, resumable)
python scripts/predictor/run_all.py --subject 4PM1
python scripts/predictor/run_all.py --subject 4PH1

# Re-run only the prediction tail after extraction (cheap):
python scripts/predictor/run_all.py --subject 4PM1 --skip-extract

# Start mid-pipeline:
python scripts/predictor/run_all.py --subject 4PH1 --from analyze
python scripts/predictor/run_all.py --subject 4PM1 --from generate

# Smoke test extraction on a few questions:
python scripts/predictor/02_extract_questions.py --subject 4PM1 --folder 2024_Jun_1P --limit 3 --out data/analysis/_smoke.jsonl
```

Extraction writes incrementally and skips already-done `q_id`s, so it is safe to
re-run / resume.

## LLMs

Set in `config/predictor/{CODE}.yaml` under `llm:`. Keys read from `.env.local`.

- **extract**: `groq` `llama-3.3-70b-versatile` (free, fast, structuring only — text already
  extracted locally with PyMuPDF; no vision needed).
- **generate**: `openrouter` `anthropic/claude-sonnet-4` (quality writing of new questions +
  mark schemes). Fallbacks: `anthropic/claude-3.5-haiku`, `openai/gpt-4o-mini`.

## What the analysis models

- **Spec eras**: pre-2019 papers are the legacy 4×0 spec (down-weighted ×0.2); 2019+ are 9–1 (×1.0).
- **Session weighting**: autumn (Oct/Nov) analogues up-weighted ×1.3 because the target is autumn.
- **Recency**: half-life 3 years toward the target year.
- **Cycles**: per-topic appearance cadence + an "overdue" score (years-since-seen / mean-gap).
- **Templates**: questions sharing a topic+command+marks signature across ≥2 years — recurring
  question types, used as style references for the generator.

## Onboarding a new subject

1. `cp config/predictor/4PM1.yaml config/predictor/{CODE}.yaml` and edit (code, processed_dir,
   topics_source, paper shape, target).
2. Ensure per-question PDFs exist under `data/processed/{processed_dir}/{Year}_{Session}_{Paper}/pages/`.
3. `python scripts/predictor/run_all.py --subject {CODE}`.

## Caveats

- Generated papers are **AI-predicted practice material**, watermarked as such — not official
  Pearson/Edexcel papers and not leaked content. The blueprint is the fully-grounded artifact;
  the written paper is a best-effort emulation (each question is marks-validated; mismatches are
  flagged `needs_review`).
- Predictions for the Oct/Nov 2026 series assume the **linear 4PH1/4PM1** format (the modular
  IGCSE Physics route is out of scope).
