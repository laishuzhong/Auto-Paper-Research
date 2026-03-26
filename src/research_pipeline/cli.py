from __future__ import annotations

from pathlib import Path
import os
import typer

from .config import load_topic_config
from .analyzer.pipeline import analyze_topic

app = typer.Typer(help="Local PDF research pipeline.")


@app.command()
def analyze(
    topic: str = typer.Option(..., help="Topic to analyze"),
    pdf_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True),
    out: Path = typer.Option(
        Path("reports/topics/autism_llm.md"),
        help="Output markdown report path",
    ),
    config: Path = typer.Option(
        Path("configs/topics.yaml"),
        help="YAML configuration with topic questions/synonyms",
    ),
    work_dir: Path = typer.Option(Path("data"), help="Working directory for cache"),
    marker_cmd: str = typer.Option(
        os.environ.get("MARKER_CMD", "marker"),
        help="Marker CLI command (optionally with {input}/{output} placeholders)",
    ),
    model: str = typer.Option(
        os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
        help="OpenAI model name",
    ),
    max_chunks: int = typer.Option(40, help="Maximum chunks passed to summarizer"),
    min_findings: int = typer.Option(10, help="Minimum number of findings"),
):
    topic_config = load_topic_config(config, topic)
    analyze_topic(
        topic=topic,
        topic_config=topic_config,
        pdf_dir=pdf_dir,
        out_path=out,
        work_dir=work_dir,
        marker_cmd=marker_cmd,
        model=model,
        max_chunks=max_chunks,
        min_findings=min_findings,
    )
