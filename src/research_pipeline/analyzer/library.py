from __future__ import annotations

from pathlib import Path
import re

from ..models.schema import Section, Chunk


def load_markdown(md_path: Path) -> str:
    return md_path.read_text(encoding="utf-8")


def extract_sections(md_text: str) -> list[Section]:
    sections: list[Section] = []
    current_title = "Main"
    current_lines: list[str] = []

    def flush() -> None:
        if not current_lines:
            return
        text = "\n".join(current_lines).strip()
        if text:
            sections.append(Section(title=current_title, text=text))

    for line in md_text.splitlines():
        if re.match(r"^\s*#{1,6}\s+", line):
            flush()
            current_title = re.sub(r"^\s*#{1,6}\s+", "", line).strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return sections


def _split_paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if buffer:
                paragraphs.append("\n".join(buffer).strip())
                buffer = []
            continue
        buffer.append(line)
    if buffer:
        paragraphs.append("\n".join(buffer).strip())
    return [p for p in paragraphs if p]


def chunk_sections(paper_id: str, sections: list[Section]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in sections:
        paragraphs = _split_paragraphs(section.text)
        for index, paragraph in enumerate(paragraphs, start=1):
            paragraph_id = f"p{index}"
            chunks.append(
                Chunk(
                    paper_id=paper_id,
                    section=section.title,
                    paragraph_id=paragraph_id,
                    text=paragraph,
                )
            )
    return chunks
