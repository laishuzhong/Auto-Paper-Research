from __future__ import annotations

from pathlib import Path
import os
import shutil
import typer
from dotenv import load_dotenv

from .config import load_topic_config
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
