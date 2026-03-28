from __future__ import annotations

from pathlib import Path
import os
import shutil
import typer
from dotenv import load_dotenv

from .arxiv.fetcher import fetch_and_download, paper_to_console_row, result_to_json
from .config import (
    build_arxiv_fetch_request,
    build_arxiv_query_from_keyword_groups,
    load_arxiv_topic_config,
    load_topic_config,
)
from .analyzer.pipeline import analyze_topic

load_dotenv()


def _default_marker_cmd() -> str:
    env_cmd = os.environ.get("MARKER_CMD")
    if env_cmd:
        return env_cmd
    if shutil.which("marker_single"):
        return "marker_single"
    return "marker"

app = typer.Typer(help="Local PDF research pipeline.")


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _split_keyword_group(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@app.command()
def analyze(
    topic: str = typer.Option(..., help="Topic to analyze"),
    pdf_dir: Path = typer.Option(
        Path("pdf"),
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Directory containing input PDF files",
    ),
    out: Path = typer.Option(
        Path("reports/topics/autism_llm.md"),
        help="Output markdown report path",
    ),
    config: Path = typer.Option(
        Path("configs/topics.yaml"),
        help="YAML configuration with topic questions/synonyms",
    ),
    prompt_config: Path = typer.Option(
        Path("configs/prompts.yaml"),
        help="YAML prompt templates for single-paper and final-topic summaries",
    ),
    work_dir: Path = typer.Option(Path("data"), help="Working directory for cache"),
    single_summary_dir: Path = typer.Option(
        Path("data/summaries"),
        help="Directory to store per-paper JSON summaries",
    ),
    reuse_single_summary: bool = typer.Option(
        True,
        help="Reuse existing per-paper JSON summaries if present",
    ),
    marker_cmd: str = typer.Option(
        _default_marker_cmd(),
        help="Marker CLI command (optionally with {input}/{output} placeholders)",
    ),
    model: str = typer.Option(
        os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        help="OpenAI model name",
    ),
    openai_api_key: str | None = typer.Option(
        os.environ.get("OPENAI_API_KEY"),
        help="OpenAI API key (defaults to OPENAI_API_KEY from .env/environment)",
        show_default=False,
    ),
    openai_base_url: str | None = typer.Option(
        os.environ.get("OPENAI_BASE_URL"),
        help="OpenAI-compatible base URL (defaults to OPENAI_BASE_URL from .env/environment)",
    ),
    max_chunks: int = typer.Option(40, help="Maximum chunks passed to summarizer"),
    min_findings: int = typer.Option(10, help="Minimum number of findings"),
    enable_single_paper_summary: bool = typer.Option(
        True,
        help="Whether to generate per-paper summaries before final topic summarization",
    ),
):
    topic_config = load_topic_config(config, topic)
    analyze_topic(
        topic=topic,
        topic_config=topic_config,
        pdf_dir=pdf_dir,
        out_path=out,
        work_dir=work_dir,
        single_summary_dir=single_summary_dir,
        reuse_single_summary=reuse_single_summary,
        prompt_config_path=prompt_config,
        marker_cmd=marker_cmd,
        model=model,
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        max_chunks=max_chunks,
        min_findings=min_findings,
        enable_single_paper_summary=enable_single_paper_summary,
    )


@app.command("fetch-arxiv")
def fetch_arxiv(
    query: str | None = typer.Option(
        None,
        help="Raw arXiv query string. If omitted, can be built from --and-group or loaded from --topic.",
    ),
    and_group: list[str] = typer.Option(
        [],
        help=(
            "Comma-separated OR-keywords for one group; pass this option multiple times "
            "to create AND groups. Example: --and-group autism,autistic --and-group llm,\"large language model\""
        ),
    ),
    query_fields: str = typer.Option(
        "ti,abs",
        help="Comma-separated query fields for keyword groups: ti,abs,all.",
    ),
    topic: str | None = typer.Option(
        None,
        help="Topic key in arXiv YAML config.",
    ),
    arxiv_config: Path = typer.Option(
        Path("configs/arxiv_topics.yaml"),
        help="YAML configuration for arXiv query presets.",
    ),
    pdf_dir: Path = typer.Option(
        Path("pdf"),
        file_okay=False,
        dir_okay=True,
        help="Directory to save downloaded PDFs.",
    ),
    manifest: Path = typer.Option(
        Path("data/arxiv/fetch_manifest.jsonl"),
        help="JSONL manifest path for fetch/download records.",
    ),
    categories: str | None = typer.Option(
        None,
        help="Comma-separated arXiv categories, e.g. cs.CL,cs.AI.",
    ),
    max_results: int | None = typer.Option(
        None,
        min=1,
        help="Maximum number of papers to request.",
    ),
    sort: str | None = typer.Option(
        None,
        help="Sort criterion: submittedDate, lastUpdatedDate, relevance.",
    ),
    date_from: str | None = typer.Option(
        None,
        help="Inclusive lower bound of publication date (YYYY-MM-DD).",
    ),
    date_to: str | None = typer.Option(
        None,
        help="Inclusive upper bound of publication date (YYYY-MM-DD).",
    ),
    dry_run: bool = typer.Option(
        False,
        help="Only search/filter without downloading PDFs.",
    ),
    force: bool = typer.Option(
        False,
        help="Re-download even if target file already exists.",
    ),
    as_json: bool = typer.Option(
        False,
        help="Print result summary in JSON format.",
    ),
):
    if not query and not topic and not and_group:
        raise typer.BadParameter("Provide one of --query, --and-group, or --topic.")

    base_query = query
    if not base_query and and_group:
        groups = [_split_keyword_group(item) for item in and_group]
        fields = _split_csv(query_fields) or ["ti", "abs"]
        base_query = build_arxiv_query_from_keyword_groups(groups, fields)
        if not base_query:
            raise typer.BadParameter("--and-group did not produce a valid query.")

    base_categories = _split_csv(categories)
    base_max_results = max_results
    base_sort = sort
    base_date_from = date_from
    base_date_to = date_to

    if topic:
        topic_config = load_arxiv_topic_config(arxiv_config, topic)
        if not base_query:
            base_query = topic_config.query
        if not base_categories:
            base_categories = topic_config.categories
        if base_max_results is None:
            base_max_results = topic_config.max_results
        if base_sort is None:
            base_sort = topic_config.sort
        if base_date_from is None:
            base_date_from = topic_config.date_from
        if base_date_to is None:
            base_date_to = topic_config.date_to

    request = build_arxiv_fetch_request(
        query=base_query or "",
        categories=base_categories,
        max_results=base_max_results,
        sort=base_sort,
        date_from=base_date_from,
        date_to=base_date_to,
    )

    result = fetch_and_download(
        request=request,
        pdf_dir=pdf_dir,
        manifest_path=manifest,
        dry_run=dry_run,
        force=force,
    )

    if as_json:
        typer.echo(result_to_json(result))
        return

    typer.echo(
        f"query={result.query} requested={result.requested} matched={result.matched} "
        f"downloaded={result.downloaded} skipped_existing={result.skipped_existing}"
    )
    for paper in result.papers:
        row = paper_to_console_row(paper)
        typer.echo(
            f"[{row['arxiv_id']}] {row['published']} {row['title']} ({row['categories']})"
        )
