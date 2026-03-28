from __future__ import annotations

from pathlib import Path
import json
import re


def _normalize_title(text: str) -> str:
    # Collapse extra spaces and line breaks produced by OCR/parsers.
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("**", " ").replace("__", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" \t\r\n-_")


def _is_bad_title_candidate(title: str) -> bool:
    if not title:
        return True
    lowered = title.lower()
    blacklist = {
        "abstract",
        "article info",
        "keywords",
        "references",
        "introduction",
        "main",
        "table of contents",
        "contents",
        "journal name",
        "conference name",
    }
    if lowered in blacklist:
        return True
    if lowered.startswith("http"):
        return True
    bad_prefixes = (
        "journal homepage",
        "contents lists available",
        "available at",
        "www.",
        "elsevier",
    )
    if lowered.startswith(bad_prefixes):
        return True
    if len(title) < 12:
        return True
    return False


def _title_from_markdown(md_text: str) -> str | None:
    for line in md_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = _normalize_title(re.sub(r"^#{1,6}\s+", "", stripped))
        if _is_bad_title_candidate(title):
            continue
        return title
    return None


def _title_from_marker_meta(meta_path: Path) -> str | None:
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    toc = data.get("table_of_contents", [])
    candidates: list[str] = []
    for item in toc:
        if not isinstance(item, dict):
            continue
        title = _normalize_title(str(item.get("title", "")))
        if _is_bad_title_candidate(title):
            continue
        # First-page headings have much higher chance to be the paper title.
        if item.get("page_id") == 0:
            candidates.insert(0, title)
        else:
            candidates.append(title)

    return candidates[0] if candidates else None


def resolve_paper_title(
    *,
    pdf_stem_title: str,
    parsed_md_path: Path | None,
) -> str:
    if parsed_md_path and parsed_md_path.exists():
        try:
            md_text = parsed_md_path.read_text(encoding="utf-8")
        except OSError:
            md_text = ""
        title_from_md = _title_from_markdown(md_text)
        if title_from_md:
            return title_from_md

        marker_dir = parsed_md_path.parent / parsed_md_path.stem
        marker_meta = marker_dir / f"{parsed_md_path.stem}_meta.json"
        title_from_meta = _title_from_marker_meta(marker_meta)
        if title_from_meta:
            return title_from_meta

    return _normalize_title(pdf_stem_title) or pdf_stem_title
