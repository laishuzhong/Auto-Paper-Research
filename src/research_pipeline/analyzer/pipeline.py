from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.schema import Chunk, TopicConfig
from ..prompts import load_prompt_templates
from .library import extract_sections, chunk_sections, load_markdown
from .pdf_parser import parse_pdf_to_md
from .report_writer import generate_topic_report
from .retriever import KeywordRetriever
from .scan import scan_pdf_dir, write_meta_jsonl
from .single_summary_store import (
    append_summary_audit,
    load_single_paper_summary,
    save_single_paper_summary,
)
from .summarizer import OpenAISummarizer
from .title_resolver import resolve_paper_title


def analyze_topic(
    topic: str,
    topic_config: TopicConfig,
    pdf_dir: Path,
    out_path: Path,
    work_dir: Path,
    single_summary_dir: Path,
    reuse_single_summary: bool,
    prompt_config_path: Path,
    marker_cmd: str,
    model: str,
    openai_api_key: str | None,
    openai_base_url: str | None,
    max_chunks: int,
    min_findings: int,
    enable_single_paper_summary: bool,
) -> None:
    parsed_dir = work_dir / "parsed"
    meta_path = work_dir / "meta" / "papers.jsonl"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    papers = scan_pdf_dir(pdf_dir, parsed_dir)
    write_meta_jsonl(papers, meta_path)

    for paper in papers:
        if paper.parsed_md_path is None:
            continue
        if paper.parsed_md_path.exists():
            continue
        parse_pdf_to_md(paper.pdf_path, paper.parsed_md_path, marker_cmd)

    chunks: list[Chunk] = []
    chunks_by_paper: dict[str, list[Chunk]] = {}
    for paper in papers:
        if not paper.parsed_md_path or not paper.parsed_md_path.exists():
            continue
        paper.title = resolve_paper_title(
            pdf_stem_title=paper.pdf_path.stem,
            parsed_md_path=paper.parsed_md_path,
        )
        md_text = load_markdown(paper.parsed_md_path)
        sections = extract_sections(md_text)
        paper_chunks = chunk_sections(paper.paper_id, sections)
        chunks_by_paper[paper.paper_id] = paper_chunks
        chunks.extend(paper_chunks)

    write_meta_jsonl(papers, meta_path)

    retriever = KeywordRetriever(topic_config.synonyms)
    selected_chunks: list[Chunk] = []
    if topic_config.questions:
        per_question = max(1, max_chunks // len(topic_config.questions))
        for question in topic_config.questions:
            selected_chunks.extend(
                retriever.retrieve(f"{topic} {question}", chunks, per_question)
            )
    else:
        selected_chunks = retriever.retrieve(topic, chunks, max_chunks)

    unique_map = {chunk.chunk_id: chunk for chunk in selected_chunks}
    selected_chunks = list(unique_map.values())
    selected_chunks.sort(key=lambda c: c.chunk_id)

    single_paper_prompt, final_topic_prompt = load_prompt_templates(prompt_config_path)
    summarizer = OpenAISummarizer(
        model=model,
        api_key=openai_api_key,
        base_url=openai_base_url,
        single_paper_prompt_template=single_paper_prompt,
        final_topic_prompt_template=final_topic_prompt,
    )

    paper_title_map = {paper.paper_id: (paper.title or paper.paper_id) for paper in papers}
    single_paper_summaries: list[dict[str, Any]] = []
    if enable_single_paper_summary:
        for paper_id, paper_chunks in chunks_by_paper.items():
            if not paper_chunks:
                continue
            summary_path = single_summary_dir / f"{paper_id}.json"
            summary = None
            if reuse_single_summary:
                summary = load_single_paper_summary(
                    summary_path,
                    prompt_config_path=prompt_config_path,
                )
            if summary is None:
                summary = summarizer.summarize_single_paper(
                    topic=topic,
                    questions=topic_config.questions,
                    paper_id=paper_id,
                    paper_title=paper_title_map.get(paper_id, paper_id),
                    chunks=paper_chunks[: max(1, min(len(paper_chunks), max_chunks))],
                )
                summary = summarizer.normalize_single_paper_summary(
                    paper_id=paper_id,
                    chunks=paper_chunks,
                    paper_summary=summary,
                )
                save_single_paper_summary(
                    summary_dir=single_summary_dir,
                    paper_id=paper_id,
                    paper_title=paper_title_map.get(paper_id, paper_id),
                    prompt_config_path=prompt_config_path,
                    summary=summary,
                )
            else:
                summary = summarizer.normalize_single_paper_summary(
                    paper_id=paper_id,
                    chunks=paper_chunks,
                    paper_summary=summary,
                )
            append_summary_audit(
                summary_dir=single_summary_dir,
                record={
                    "paper_id": paper_id,
                    "used_cached_summary": bool(reuse_single_summary and summary_path.exists()),
                    "summary_path": str(summary_path),
                },
            )
            single_paper_summaries.append(summary)

    findings, paper_map = summarizer.summarize(
        topic=topic,
        questions=topic_config.questions,
        chunks=selected_chunks,
        min_findings=min_findings,
        single_paper_summaries=single_paper_summaries,
        validation_chunks=chunks,
    )
    generate_topic_report(
        topic=topic,
        papers=papers,
        findings=findings,
        paper_map=paper_map,
        out_path=out_path,
        paper_title_map=paper_title_map,
    )
