# Auto Paper Research

This repository provides a modular pipeline to analyze local PDFs for a topic and generate a markdown report with evidence lines.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run (MVP)

```bash
research analyze --topic "autism large language model" --pdf_dir /path/to/pdfs --out reports/topics/autism_llm.md
```

Required environment variables:

- `OPENAI_API_KEY`: API key for OpenAI.

Optional configuration:

- `OPENAI_MODEL`: overrides the default model (`gpt-4.1-mini`).
- `MARKER_CMD`: command template for the Marker CLI. If it contains `{input}` and `{output}`, they will be substituted. Otherwise the command is invoked as `marker --input <pdf> --output <md>`.

## Notes

This pipeline is offline for PDF parsing and chunking. Summarization uses the OpenAI API by default.
