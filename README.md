# Auto Paper Research

This repository provides a local PDF research pipeline:

1. Parse PDFs into markdown.
2. Build section/paragraph chunks.
3. Retrieve topic-relevant chunks.
4. Generate single-paper summaries and a final topic report.
5. Attach evidence lines that map back to source chunks.

## Requirements

1. Python `>=3.10`
2. A Marker CLI command (`marker_single` recommended, or `marker`)
3. OpenAI-compatible API access

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create or edit `.env` in repo root:

```env
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_MODEL=gpt-4.1-mini
```

Notes:

1. `OPENAI_API_KEY` is required.
2. `OPENAI_BASE_URL` is optional for official OpenAI.
3. `OPENAI_MODEL` defaults to `gpt-4.1-mini` if not set.

## Quick Start

Put PDFs under `pdf/`, then run:

```bash
research --topic "autism large language model" --out reports/topics/autism_llm.md
```

Equivalent explicit form:

```bash
research analyze --topic "autism large language model" --out reports/topics/autism_llm.md
```

## Full Example

```bash
CUDA_VISIBLE_DEVICES=2 research \
  --topic "autism large language model" \
  --pdf-dir pdf \
  --out reports/topics/autism_llm.md \
  --config configs/topics.yaml \
  --prompt-config configs/prompts.yaml \
  --marker-cmd "marker_single --disable_multiprocessing" \
  --single-summary-dir data/summaries \
  --reuse-single-summary \
  --max-chunks 40 \
  --min-findings 10
```

## CLI Options

Core options:

1. `--topic`: topic key from `configs/topics.yaml`.
2. `--pdf-dir`: input PDF directory.
3. `--out`: output markdown report path.

Config options:

1. `--config`: topic config path (default `configs/topics.yaml`).
2. `--prompt-config`: prompt config path (default `configs/prompts.yaml`).
3. `--work-dir`: cache/work directory (default `data`).

Single-paper summary options:

1. `--enable-single-paper-summary / --no-enable-single-paper-summary`
2. `--single-summary-dir` (default `data/summaries`)
3. `--reuse-single-summary / --no-reuse-single-summary`

Model and parsing options:

1. `--model`
2. `--openai-api-key`
3. `--openai-base-url`
4. `--marker-cmd`
5. `--max-chunks`
6. `--min-findings`

## What You Can Customize

### 1) Topic Retrieval and Analysis Scope

File: `configs/topics.yaml`

You can customize for each topic:

1. `synonyms`: retrieval expansion terms.
2. `questions`: analysis dimensions (these affect both retrieval and summarization focus).

Example dimensions currently used include:

1. problem statement
2. contributions
3. methodology
4. innovation
5. experiments
6. datasets
7. open-source links
8. limitations

### 2) Prompt Templates and Output Schema

File: `configs/prompts.yaml`

You can customize:

1. `single_paper_summary_prompt`
2. `final_topic_summary_prompt`

Current single-paper schema expected by prompt:

```json
{
  "paper_summary": {
    "paper_id": "...",
    "title": "...",
    "tasks": ["..."],
    "github_links": ["..."],
    "contributions": ["..."],
    "data_sources": ["..."],
    "methods": ["..."],
    "experiments": ["..."],
    "results": ["..."],
    "limitations": ["..."],
    "evidence": [{"chunk_id": "..."}]
  }
}
```

### 3) PDF Parsing Backend

You can switch parsing command with:

1. `MARKER_CMD` environment variable, or
2. `--marker-cmd` CLI option

Behavior:

1. If command contains `{input}` and `{output}`, placeholders are substituted directly.
2. Otherwise command is invoked as `marker_single` style or `marker` style depending on binary name.

## Output and Cache Files

1. Parsed markdown: `data/parsed/*.md`
2. Paper metadata: `data/meta/papers.jsonl`
3. Single-paper summaries: `data/summaries/*.json`
4. Audit log: `data/summaries/_audit.jsonl`
5. Final report: `reports/topics/*.md`

## Important Behavior (Recent Changes)

### 1) Summary cache invalidation is prompt-aware

Single summary JSON now includes `prompt_config_fingerprint`.

1. If `configs/prompts.yaml` content changes, old cached summaries are treated as stale.
2. With `--reuse-single-summary`, stale files are automatically regenerated.

### 2) Single summary schema normalization

Before use/save, summary objects are normalized to the canonical schema.

1. Required list fields are guaranteed to exist (empty list if missing).
2. Legacy aliases are mapped:
   1. `evaluation` -> `experiments`
   2. `deployment` -> `results`
3. Non-schema fields are dropped.
4. Evidence `chunk_id` values are canonicalized and validated against source chunks.

### 3) Evidence validation fallback

Final summarization still builds model context from selected retrieved chunks, but evidence validation can fall back to all chunks.

This prevents "subset mismatch" from dropping valid evidence that exists in full parsed content but was not in the top-k retrieval subset.

## Troubleshooting

1. `Topic not found in config`: check the exact key under `topics:` in `configs/topics.yaml`.
2. Marker command not found: install `marker_single`/`marker` or set `--marker-cmd`.
3. Summaries do not reflect new prompt: rerun once (prompt fingerprint will invalidate stale cache automatically).
4. You can force fresh run by deleting `data/summaries/*.json`.

## Development

Run tests:

```bash
pytest -q
```
