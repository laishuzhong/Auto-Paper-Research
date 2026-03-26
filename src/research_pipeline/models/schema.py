from __future__ import annotations

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class PaperMeta(BaseModel):
    paper_id: str
    title: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    pdf_path: Path
    parsed_md_path: Optional[Path] = None


class Evidence(BaseModel):
    paper_id: str
    section: str
    paragraph_id: str
    quote: Optional[str] = None


class Finding(BaseModel):
    claim: str
    evidence: list[Evidence] = Field(default_factory=list)


class Section(BaseModel):
    title: str
    text: str


class Chunk(BaseModel):
    paper_id: str
    section: str
    paragraph_id: str
    text: str

    @computed_field
    @property
    def chunk_id(self) -> str:
        return f"{self.paper_id}|{self.section}|{self.paragraph_id}"


class TopicReport(BaseModel):
    topic: str
    findings: list[Finding]
    paper_map: dict[str, list[str]]
    table_rows: list[dict[str, str]] = Field(default_factory=list)


class TopicConfig(BaseModel):
    topic: str
    synonyms: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
