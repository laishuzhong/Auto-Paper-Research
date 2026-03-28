from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
from hashlib import sha256
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _prompt_fingerprint(prompt_config_path: Path) -> str:
    try:
        content = prompt_config_path.read_bytes()
    except OSError:
        return "missing"
    return sha256(content).hexdigest()


def save_single_paper_summary(
    *,
    summary_dir: Path,
    paper_id: str,
    paper_title: str,
    prompt_config_path: Path,
    summary: dict[str, Any],
) -> Path:
    summary_dir.mkdir(parents=True, exist_ok=True)
    out_path = summary_dir / f"{paper_id}.json"
    payload = {
        "paper_id": paper_id,
        "resolved_title": paper_title,
        "prompt_config_path": str(prompt_config_path),
        "prompt_config_fingerprint": _prompt_fingerprint(prompt_config_path),
        "generated_at": _now_iso(),
        "single_paper_summary": summary,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def load_single_paper_summary(
    summary_path: Path,
    *,
    prompt_config_path: Path | None = None,
) -> dict[str, Any] | None:
    if not summary_path.exists():
        return None
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if prompt_config_path is not None:
        expected_fingerprint = _prompt_fingerprint(prompt_config_path)
        stored_fingerprint = data.get("prompt_config_fingerprint")
        # Old cache files without fingerprint are considered stale.
        if not isinstance(stored_fingerprint, str):
            return None
        if stored_fingerprint != expected_fingerprint:
            return None
    summary = data.get("single_paper_summary")
    if not isinstance(summary, dict):
        return None
    return summary


def append_summary_audit(
    *,
    summary_dir: Path,
    record: dict[str, Any],
) -> None:
    summary_dir.mkdir(parents=True, exist_ok=True)
    audit_path = summary_dir / "_audit.jsonl"
    line = json.dumps(record, ensure_ascii=False)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
