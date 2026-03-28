from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
import json
import re
from typing import Any

from ..config import ArxivFetchRequest


ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?$")


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    categories: list[str]
    published: date | None
    updated: date | None
    summary: str
    pdf_url: str
    entry_id: str


@dataclass
class FetchResult:
    query: str
    requested: int
    matched: int
    downloaded: int
    skipped_existing: int
    papers: list[ArxivPaper]


def _normalize_arxiv_id(entry_id: str) -> str:
    raw = entry_id.rstrip("/").split("/")[-1]
    match = ARXIV_ID_RE.search(raw)
    if not match:
        return raw.replace("/", "_")
    return match.group(1)


def _matches_categories(paper_categories: list[str], required_categories: list[str]) -> bool:
    if not required_categories:
        return True
    paper_set = set(paper_categories)
    return any(cat in paper_set for cat in required_categories)


def _in_date_range(day: date | None, date_from: date | None, date_to: date | None) -> bool:
    if day is None:
        return False
    if date_from and day < date_from:
        return False
    if date_to and day > date_to:
        return False
    return True


def _parse_optional_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


def _sort_criterion(sort: str) -> str:
    normalized = sort.strip().lower()
    if normalized == "relevance":
        return "relevance"
    if normalized in {"lastupdateddate", "updated", "last_updated"}:
        return "lastUpdatedDate"
    return "submittedDate"


def _to_arxiv_paper(result: Any) -> ArxivPaper:
    return ArxivPaper(
        arxiv_id=_normalize_arxiv_id(result.entry_id),
        title=result.title.strip(),
        authors=[author.name for author in result.authors],
        categories=list(result.categories),
        published=result.published.date() if result.published else None,
        updated=result.updated.date() if result.updated else None,
        summary=(result.summary or "").strip(),
        pdf_url=result.pdf_url,
        entry_id=result.entry_id,
    )


def _append_manifest(manifest_path: Path, payload: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def fetch_and_download(
    request: ArxivFetchRequest,
    pdf_dir: Path,
    manifest_path: Path,
    dry_run: bool = False,
    force: bool = False,
) -> FetchResult:
    import arxiv

    pdf_dir.mkdir(parents=True, exist_ok=True)

    date_from = _parse_optional_date(request.date_from)
    date_to = _parse_optional_date(request.date_to)

    query = request.query
    if request.categories:
        category_filter = " OR ".join(f"cat:{cat}" for cat in request.categories)
        query = f"({query}) AND ({category_filter})"

    client = arxiv.Client(page_size=min(request.max_results, 200), delay_seconds=3.0, num_retries=3)
    sort_name = _sort_criterion(request.sort)
    sort_by = getattr(arxiv.SortCriterion, sort_name[0].upper() + sort_name[1:])
    search = arxiv.Search(
        query=query,
        max_results=request.max_results,
        sort_by=sort_by,
        sort_order=arxiv.SortOrder.Descending,
    )

    papers: list[ArxivPaper] = []
    downloaded = 0
    skipped_existing = 0

    for result in client.results(search):
        paper = _to_arxiv_paper(result)
        if not _matches_categories(paper.categories, request.categories):
            continue
        if date_from or date_to:
            published = paper.published
            if not _in_date_range(published, date_from, date_to):
                continue

        papers.append(paper)
        target = pdf_dir / f"{paper.arxiv_id}.pdf"
        existed = target.exists()

        action = "skip-existing"
        if not existed or force:
            action = "dry-run" if dry_run else "download"

        if not dry_run and (not existed or force):
            result.download_pdf(dirpath=str(pdf_dir), filename=target.name)
            downloaded += 1
        elif existed and not force:
            skipped_existing += 1

        _append_manifest(
            manifest_path,
            {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "query": request.query,
                "categories": request.categories,
                "published": paper.published.isoformat() if paper.published else None,
                "updated": paper.updated.isoformat() if paper.updated else None,
                "pdf_path": str(target),
                "action": action,
                "dry_run": dry_run,
            },
        )

    return FetchResult(
        query=request.query,
        requested=request.max_results,
        matched=len(papers),
        downloaded=downloaded,
        skipped_existing=skipped_existing,
        papers=papers,
    )


def paper_to_console_row(paper: ArxivPaper) -> dict:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "published": paper.published.isoformat() if paper.published else "",
        "categories": ",".join(paper.categories),
        "authors": ", ".join(paper.authors),
    }


def result_to_json(result: FetchResult) -> str:
    payload = {
        "query": result.query,
        "requested": result.requested,
        "matched": result.matched,
        "downloaded": result.downloaded,
        "skipped_existing": result.skipped_existing,
        "papers": [asdict(item) for item in result.papers],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)