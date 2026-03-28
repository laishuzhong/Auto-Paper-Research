# Auto Paper Research

A local paper pipeline for researchers:

1. Crawl papers from arXiv by keywords and download PDFs.
2. Parse PDFs locally and extract key evidence and findings.
3. Generate topic-level markdown reports for reading and follow-up writing.

The recommended workflow is two-stage: fetch first, then analyze.

## What You Can Do With It

1. Enter topic keywords (supports AND/OR groups) and auto-build arXiv queries.
2. Filter papers by date range (for example, only January 2026).
3. Download papers to a local directory (for example, `pdf/tmp`).
4. Generate reports automatically under `reports/topics/*.md`.

## 0. Prerequisites

1. Python >= 3.10
2. Marker command available (recommended: `marker_single`)
3. An OpenAI-compatible API endpoint (used in stage 2 summarization)

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create a `.env` file in the repository root:

```env
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_MODEL=gpt-4.1-mini
```

Notes:

1. `OPENAI_API_KEY` is required (stage 2 depends on it).
2. `OPENAI_BASE_URL` is optional; if omitted, the default OpenAI endpoint is used.
3. `OPENAI_MODEL` is optional; default is `gpt-4.1-mini`.

## 2. Quick Start (Recommended Commands)

### Stage 1: Fetch arXiv Papers by Keywords and Download

Example goal: fetch papers from January 2026 that satisfy:

1. Keyword group A: `autism OR autistic`
2. Keyword group B: `llm OR "large language model"`
3. A and B are combined with AND

```bash
research fetch-arxiv \
  --and-group autism,autistic \
  --and-group llm,"large language model" \
  --query-fields ti,abs \
  --date-from 2026-01-01 \
  --date-to 2026-01-31 \
  --pdf-dir pdf/tmp \
  --manifest data/arxiv/fetch_manifest.jsonl \
  --max-results 100
```

If you want to preview matches without downloading PDFs:

```bash
research fetch-arxiv \
  --and-group autism,autistic \
  --and-group llm,"large language model" \
  --query-fields ti,abs \
  --date-from 2026-01-01 \
  --date-to 2026-01-31 \
  --max-results 100 \
  --dry-run
```

### Stage 2: Analyze Locally and Generate a Report

```bash
research analyze \
  --topic "autism large language model" \
  --pdf-dir pdf/tmp \
  --out reports/topics/autism_llm_2026_01_tmp.md \
  --config configs/topics.yaml \
  --prompt-config configs/prompts.yaml \
  --work-dir data/tmp_2026_01 \
  --single-summary-dir data/tmp_2026_01/summaries \
  --reuse-single-summary
```

After running, you will get:

1. Downloaded papers: `pdf/tmp/*.pdf`
2. Fetch manifest: `data/arxiv/fetch_manifest.jsonl`
3. Intermediate artifacts: `data/tmp_2026_01/*`
4. Final report: `reports/topics/autism_llm_2026_01_tmp.md`

## 3. Two Fetch Modes

### Mode A (Recommended): Keyword Group Composition

Best for most users; no need to hand-write complex arXiv queries.

```bash
research fetch-arxiv \
  --and-group autism,autistic \
  --and-group llm,"large language model" \
  --query-fields ti,abs
```

Semantics:

1. Each `--and-group` is OR within the group.
2. Multiple `--and-group` options are ANDed together.
3. `--query-fields ti,abs` maps each keyword to title and abstract fields.

### Mode B: Raw arXiv Query

Useful if you are already familiar with arXiv query syntax.

```bash
research fetch-arxiv \
  --query '((ti:autism OR ti:autistic OR abs:autism OR abs:autistic) AND (ti:llm OR ti:"large language model" OR abs:llm OR abs:"large language model"))'
```

## 4. Fetch With Topic Presets (Config-Driven)

You can also define queries in config and fetch by topic only:

```bash
research fetch-arxiv --topic autism_llm --arxiv-config configs/arxiv_topics.yaml --pdf-dir pdf
```

See `configs/arxiv_topics.yaml` for the current preset examples.

## 5. Most Common Options (Cheat Sheet)

### research fetch-arxiv

1. Query input: `--query` or `--and-group` or `--topic`
2. Date range: `--date-from` `--date-to`
3. Download directory: `--pdf-dir`
4. Manifest path: `--manifest`
5. Volume and sorting: `--max-results` `--sort`
6. Category filter: `--categories` (for example `cs.CL,cs.AI`)
7. Other: `--dry-run` `--force` `--as-json`

### research analyze

1. Input directory: `--pdf-dir`
2. Output report: `--out`
3. Topic config: `--config`
4. Prompt config: `--prompt-config`
5. Cache directories: `--work-dir` `--single-summary-dir`

## 6. Configuration Files

1. `configs/arxiv_topics.yaml`: fetch presets (query, query_terms, categories, date, max_results, etc.)
2. `configs/topics.yaml`: analysis topics (synonyms, questions)
3. `configs/prompts.yaml`: prompts for single-paper and final-topic summaries

## 7. Output Paths

1. Fetch manifest: `data/arxiv/fetch_manifest.jsonl`
2. Parsed markdown: `data/parsed/*.md` (or custom `--work-dir`)
3. Paper metadata: `data/meta/papers.jsonl`
4. Single-paper summaries: `data/summaries/*.json` (or custom `--single-summary-dir`)
5. Final reports: `reports/topics/*.md`

## 8. FAQ

1. Error: `Topic not found in config`
Check whether topic names match in `configs/topics.yaml` or `configs/arxiv_topics.yaml`.

2. Error: Marker command not found
Install `marker_single`, or specify command via `--marker-cmd`.

3. Stage 2 did not generate a report
Ensure `OPENAI_API_KEY` is set and `--pdf-dir` actually contains PDFs.

4. Want to force re-run summarization
Delete summary caches, or switch `--work-dir` / `--single-summary-dir`.

## 9. Development & Testing

```bash
pytest -q
```
