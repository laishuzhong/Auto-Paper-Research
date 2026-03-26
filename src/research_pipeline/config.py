from __future__ import annotations

from pathlib import Path
import yaml

from .models.schema import TopicConfig


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
