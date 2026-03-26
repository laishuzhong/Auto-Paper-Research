from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import json
import re

from ..models.schema import PaperMeta


def make_paper_id(pdf_path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "-", pdf_path.stem).strip("-").lower()
    hasher = sha1()
    with pdf_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()[:8]
    if not stem:
        stem = "paper"
    return f"{stem}-{digest}"


def scan_pdf_dir(pdf_dir: Path, parsed_dir: Path) -> list[PaperMeta]:
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    papers: list[PaperMeta] = []
    for pdf in pdfs:
        paper_id = make_paper_id(pdf)
        parsed_md_path = parsed_dir / f"{paper_id}.md"
        papers.append(
            PaperMeta(
                paper_id=paper_id,
                title=pdf.stem,
                source="local",
                pdf_path=pdf,
                parsed_md_path=parsed_md_path,
            )
        )
    return papers


def write_meta_jsonl(papers: list[PaperMeta], meta_path: Path) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as handle:
        for paper in papers:
            row = paper.model_dump()
            row["pdf_path"] = str(paper.pdf_path)
            row["parsed_md_path"] = str(paper.parsed_md_path) if paper.parsed_md_path else None
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
