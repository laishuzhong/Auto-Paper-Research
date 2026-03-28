from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .models.schema import TopicConfig


@dataclass
class ArxivFetchRequest:
    query: str
    categories: list[str] = field(default_factory=list)
    max_results: int = 20
    sort: str = "submittedDate"
    date_from: str | None = None
    date_to: str | None = None


@dataclass
class ArxivTopicConfig:
    topic: str
    query: str
    categories: list[str] = field(default_factory=list)
    max_results: int = 20
    sort: str = "submittedDate"
    date_from: str | None = None
    date_to: str | None = None


def build_query_from_terms(terms: list[str]) -> str:
    cleaned_terms = [term.strip() for term in terms if term and term.strip()]
    if not cleaned_terms:
        return ""
    parts: list[str] = []
    for term in cleaned_terms:
        if " " in term:
            parts.append(f'"{term}"')
        else:
            parts.append(term)
    return " OR ".join(parts)


def build_arxiv_query_from_keyword_groups(
    and_groups: list[list[str]],
    query_fields: list[str] | None = None,
) -> str:
    fields = [item.strip() for item in (query_fields or ["all"]) if item.strip()]
    if not fields:
        fields = ["all"]

    normalized_groups: list[list[str]] = []
    for group in and_groups:
        cleaned_group = [term.strip() for term in group if term and term.strip()]
        if cleaned_group:
            normalized_groups.append(cleaned_group)

    if not normalized_groups:
        return ""

    clauses: list[str] = []
    for group in normalized_groups:
        group_parts: list[str] = []
        for term in group:
            text = f'"{term}"' if " " in term else term
            for field in fields:
                if field == "all":
                    group_parts.append(text)
                else:
                    group_parts.append(f"{field}:{text}")
        clauses.append("(" + " OR ".join(group_parts) + ")")

    return " AND ".join(clauses)


def load_topic_config(path: Path, topic: str) -> TopicConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    topics = data.get("topics", {})
    if topic not in topics:
        raise KeyError(f"Topic not found in config: {topic}")
    topic_data = topics[topic] or {}
    return TopicConfig(
        topic=topic,
        synonyms=topic_data.get("synonyms", []),
        questions=topic_data.get("questions", []),
    )


def load_arxiv_topic_config(path: Path, topic: str) -> ArxivTopicConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    defaults = data.get("defaults", {}) or {}
    topics = data.get("topics", {}) or {}
    if topic not in topics:
        raise KeyError(f"Topic not found in arXiv config: {topic}")

    topic_data = topics.get(topic, {}) or {}
    query = str(topic_data.get("query", "")).strip()
    if not query:
        query = build_query_from_terms(topic_data.get("query_terms", []))
    if not query:
        raise ValueError(f"No query or query_terms configured for topic: {topic}")

    default_categories = defaults.get("categories", []) or []
    categories = topic_data.get("categories", default_categories) or []

    return ArxivTopicConfig(
        topic=topic,
        query=query,
        categories=[str(item).strip() for item in categories if str(item).strip()],
        max_results=int(topic_data.get("max_results", defaults.get("max_results", 20))),
        sort=str(topic_data.get("sort", defaults.get("sort", "submittedDate"))),
        date_from=topic_data.get("date_from", defaults.get("date_from")),
        date_to=topic_data.get("date_to", defaults.get("date_to")),
    )


def build_arxiv_fetch_request(
    query: str,
    categories: list[str] | None,
    max_results: int | None,
    sort: str | None,
    date_from: str | None,
    date_to: str | None,
) -> ArxivFetchRequest:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query cannot be empty")
    normalized_categories = [item.strip() for item in (categories or []) if item.strip()]
    normalized_sort = (sort or "submittedDate").strip() or "submittedDate"
    normalized_max_results = max_results if max_results is not None else 20
    if normalized_max_results <= 0:
        raise ValueError("max_results must be > 0")

    return ArxivFetchRequest(
        query=normalized_query,
        categories=normalized_categories,
        max_results=normalized_max_results,
        sort=normalized_sort,
        date_from=date_from,
        date_to=date_to,
    )
