from __future__ import annotations

from pathlib import Path

from ..models.schema import Chunk, TopicConfig
from .library import extract_sections, chunk_sections, load_markdown
from .pdf_parser import parse_pdf_to_md
from .report_writer import generate_topic_report
from .retriever import KeywordRetriever
from .scan import scan_pdf_dir, write_meta_jsonl
from .summarizer import OpenAISummarizer


def analyze_topic(
    topic: str,
    topic_config: TopicConfig,
    pdf_dir: Path,
    out_path: Path,
    work_dir: Path,
    marker_cmd: str,
    model: str,
    max_chunks: int,
    min_findings: int,
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
    for paper in papers:
        if not paper.parsed_md_path or not paper.parsed_md_path.exists():
            continue
        md_text = load_markdown(paper.parsed_md_path)
        sections = extract_sections(md_text)
        chunks.extend(chunk_sections(paper.paper_id, sections))

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

    summarizer = OpenAISummarizer(model=model)
    findings, paper_map = summarizer.summarize(
        topic=topic,
        questions=topic_config.questions,
        chunks=selected_chunks,
        min_findings=min_findings,
    )
    generate_topic_report(
        topic=topic,
        papers=papers,
        findings=findings,
        paper_map=paper_map,
        out_path=out_path,
    )
