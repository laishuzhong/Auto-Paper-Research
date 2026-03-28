from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from ..models.schema import Chunk, Evidence, Finding


class OpenAISummarizer:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        single_paper_prompt_template: str | None = None,
        final_topic_prompt_template: str | None = None,
    ) -> None:
        self.model = model
        self.single_paper_prompt_template = single_paper_prompt_template or ""
        self.final_topic_prompt_template = final_topic_prompt_template or ""
        client_kwargs: dict[str, Any] = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)

    def summarize_single_paper(
        self,
        topic: str,
        questions: list[str],
        paper_id: str,
        paper_title: str,
        chunks: list[Chunk],
    ) -> dict[str, Any]:
        context_lines = self._build_context_lines(chunks)
        prompt = _render_prompt_template(
            self.single_paper_prompt_template,
            {
                "topic": str(topic),
                "questions": str(questions),
                "paper_id": paper_id,
                "paper_title": paper_title,
                "context_chunks": "\n".join(context_lines),
            },
        )
        data = self._chat_json(prompt)
        paper_summary = data.get("paper_summary")
        if not isinstance(paper_summary, dict):
            raise ValueError("Single paper summary must include object field 'paper_summary'.")
        return self.normalize_single_paper_summary(
            paper_id=paper_id,
            chunks=chunks,
            paper_summary=paper_summary,
        )

    def normalize_single_paper_summary(
        self,
        *,
        paper_id: str,
        chunks: list[Chunk],
        paper_summary: dict[str, Any],
    ) -> dict[str, Any]:
        chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
        normalized_chunk_map = {_normalize_chunk_id(chunk.chunk_id): chunk for chunk in chunks}
        by_section_paragraph: dict[tuple[str, str], Chunk] = {}
        by_paragraph: dict[str, Chunk] = {}
        for chunk in chunks:
            section_key = chunk.section.strip("*# ").lower()
            paragraph_key = chunk.paragraph_id.strip().lower()
            by_section_paragraph[(section_key, paragraph_key)] = chunk
            by_paragraph.setdefault(paragraph_key, chunk)

        normalized = dict(paper_summary)
        normalized.setdefault("paper_id", paper_id)

        evidence_items = normalized.get("evidence", [])
        if not isinstance(evidence_items, list):
            normalized["evidence"] = []
            return normalized

        cleaned_evidence: list[dict[str, str]] = []
        seen: set[str] = set()
        for evidence in evidence_items:
            raw_chunk_id: str | None = None
            if isinstance(evidence, dict):
                maybe_chunk_id = evidence.get("chunk_id")
                if isinstance(maybe_chunk_id, str):
                    raw_chunk_id = maybe_chunk_id
            elif isinstance(evidence, str):
                raw_chunk_id = evidence
            if raw_chunk_id is None:
                continue

            canonical = _canonicalize_single_paper_chunk_id(
                raw_chunk_id=raw_chunk_id,
                paper_id=paper_id,
                chunk_map=chunk_map,
                normalized_chunk_map=normalized_chunk_map,
                by_section_paragraph=by_section_paragraph,
                by_paragraph=by_paragraph,
            )
            if canonical is None or canonical in seen:
                continue
            seen.add(canonical)
            cleaned_evidence.append({"chunk_id": canonical})

        normalized["evidence"] = cleaned_evidence
        return normalized

    def summarize(
        self,
        topic: str,
        questions: list[str],
        chunks: list[Chunk],
        min_findings: int,
        single_paper_summaries: list[dict[str, Any]] | None = None,
        validation_chunks: list[Chunk] | None = None,
    ) -> tuple[list[Finding], dict[str, list[str]]]:
        effective_validation_chunks = validation_chunks or chunks
        chunk_map = {chunk.chunk_id: chunk for chunk in effective_validation_chunks}
        normalized_chunk_map = {
            _normalize_chunk_id(chunk.chunk_id): chunk for chunk in effective_validation_chunks
        }
        normalized_by_paper_section: dict[tuple[str, str], list[Chunk]] = {}
        for chunk in effective_validation_chunks:
            key = (chunk.paper_id.lower(), chunk.section.strip("*# ").lower())
            normalized_by_paper_section.setdefault(key, []).append(chunk)
        context_lines = self._build_context_lines(chunks)
        retry_notes = ""
        last_findings: list[Finding] = []
        last_paper_map: dict[str, list[str]] = {}
        for attempt in range(1, 4):
            prompt = _render_prompt_template(
                self.final_topic_prompt_template,
                {
                    "topic": str(topic),
                    "questions": str(questions),
                    "min_findings": str(min_findings),
                    "context_chunks": "\n".join(context_lines),
                    "single_paper_summaries": json.dumps(
                        single_paper_summaries or [],
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "retry_notes": retry_notes,
                },
            )
            data = self._chat_json(prompt)

            findings_raw = data.get("findings", [])
            paper_map = data.get("paper_map", {}) or {}
            if not isinstance(findings_raw, list):
                retry_notes = "Previous output was invalid: findings was not a list."
                continue

            findings, invalid_count, missing_evidence_count = self._build_validated_findings(
                findings_raw=findings_raw,
                chunk_map=chunk_map,
                normalized_chunk_map=normalized_chunk_map,
                normalized_by_paper_section=normalized_by_paper_section,
            )

            last_findings = findings
            last_paper_map = paper_map
            enough_findings = len(findings) >= min_findings
            evidence_ok = missing_evidence_count == 0
            if enough_findings and evidence_ok:
                return findings, paper_map

            retry_notes = (
                "Previous output failed validation. "
                f"invalid_evidence={invalid_count}, findings_without_evidence={missing_evidence_count}, "
                f"findings_count={len(findings)}, required_min_findings={min_findings}. "
                "Regenerate and ensure each finding has at least one valid evidence quote in original English."
            )

        # After 3 attempts, keep claims but drop evidence as requested.
        stripped = [Finding(claim=f.claim, evidence=[]) for f in last_findings]
        if len(stripped) < min_findings:
            raise ValueError(
                f"Expected at least {min_findings} findings, got {len(stripped)} after retries."
            )
        return stripped, last_paper_map

    def _build_validated_findings(
        self,
        *,
        findings_raw: list[Any],
        chunk_map: dict[str, Chunk],
        normalized_chunk_map: dict[str, Chunk],
        normalized_by_paper_section: dict[tuple[str, str], list[Chunk]],
    ) -> tuple[list[Finding], int, int]:
        findings: list[Finding] = []
        invalid_evidence_count = 0
        findings_without_evidence = 0
        for item in findings_raw:
            claim = item.get("claim")
            evidence_items = item.get("evidence", [])
            if not claim or not isinstance(evidence_items, list):
                continue
            evidence_list: list[Evidence] = []
            for evidence in evidence_items:
                if isinstance(evidence, str):
                    evidence = {"chunk_id": evidence}
                if not isinstance(evidence, dict):
                    invalid_evidence_count += 1
                    continue
                chunk_id = evidence.get("chunk_id")
                if chunk_id:
                    chunk = chunk_map.get(str(chunk_id))
                    if chunk is None:
                        chunk = normalized_chunk_map.get(_normalize_chunk_id(str(chunk_id)))
                    if chunk is None:
                        chunk = _fallback_chunk_lookup(
                            str(chunk_id),
                            normalized_by_paper_section,
                        )
                    if chunk is None:
                        invalid_evidence_count += 1
                        continue
                    quote = _extract_english_quote_from_chunk(chunk.text)
                    if quote is None:
                        invalid_evidence_count += 1
                        continue
                    evidence_list.append(
                        Evidence(
                            paper_id=chunk.paper_id,
                            section=chunk.section,
                            paragraph_id=chunk.paragraph_id,
                            quote=quote,
                        )
                    )
                    continue
                paper_id = evidence.get("paper_id")
                section = evidence.get("section")
                paragraph_id = evidence.get("paragraph_id")
                if not (paper_id and section and paragraph_id):
                    invalid_evidence_count += 1
                    continue
                evidence_chunk_id = f"{paper_id}|{section}|{paragraph_id}"
                if evidence_chunk_id not in chunk_map and _normalize_chunk_id(evidence_chunk_id) not in normalized_chunk_map:
                    chunk = _fallback_chunk_lookup(evidence_chunk_id, normalized_by_paper_section)
                    if chunk is None:
                        invalid_evidence_count += 1
                        continue
                else:
                    chunk = chunk_map.get(evidence_chunk_id)
                    if chunk is None:
                        chunk = normalized_chunk_map[_normalize_chunk_id(evidence_chunk_id)]
                quote = _extract_english_quote_from_chunk(chunk.text)
                if quote is None:
                    invalid_evidence_count += 1
                    continue
                evidence_list.append(
                    Evidence(
                        paper_id=chunk.paper_id,
                        section=chunk.section,
                        paragraph_id=chunk.paragraph_id,
                        quote=quote,
                    )
                )
            if not evidence_list:
                findings_without_evidence += 1
            findings.append(Finding(claim=claim, evidence=evidence_list))
        return findings, invalid_evidence_count, findings_without_evidence

    def _build_context_lines(self, chunks: list[Chunk]) -> list[str]:
        context_lines: list[str] = []
        for chunk in chunks:
            text = chunk.text.strip()
            if len(text) > 800:
                text = text[:800] + "..."
            context_lines.append(f"[{chunk.chunk_id}] ({chunk.section}) {text}")
        return context_lines

    def _chat_json(self, prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a careful research assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return _parse_json(content)


def _parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Failed to parse JSON from summarizer response.") from exc


def _render_prompt_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered


def _normalize_chunk_id(chunk_id: str) -> str:
    parts = [part.strip().lower() for part in str(chunk_id).split("|")]
    if len(parts) != 3:
        return str(chunk_id).strip().lower()
    paper_id, section, paragraph_id = parts
    section = section.strip("*# ")
    return f"{paper_id}|{section}|{paragraph_id}"


def _canonicalize_single_paper_chunk_id(
    *,
    raw_chunk_id: str,
    paper_id: str,
    chunk_map: dict[str, Chunk],
    normalized_chunk_map: dict[str, Chunk],
    by_section_paragraph: dict[tuple[str, str], Chunk],
    by_paragraph: dict[str, Chunk],
) -> str | None:
    candidate = str(raw_chunk_id).strip().strip("[]")
    if not candidate:
        return None

    direct = chunk_map.get(candidate)
    if direct is not None:
        return direct.chunk_id

    normalized = normalized_chunk_map.get(_normalize_chunk_id(candidate))
    if normalized is not None:
        return normalized.chunk_id

    parts = [part.strip() for part in candidate.split("|") if part.strip()]
    if len(parts) == 3:
        prefixed = f"{paper_id}|{parts[1]}|{parts[2]}"
        normalized = normalized_chunk_map.get(_normalize_chunk_id(prefixed))
        if normalized is not None:
            return normalized.chunk_id

    if len(parts) == 2:
        section, paragraph_id = parts
        prefixed = f"{paper_id}|{section}|{paragraph_id}"
        normalized = normalized_chunk_map.get(_normalize_chunk_id(prefixed))
        if normalized is not None:
            return normalized.chunk_id
        section_key = section.strip("*# ").lower()
        paragraph_key = paragraph_id.strip().lower()
        guessed = by_section_paragraph.get((section_key, paragraph_key))
        if guessed is not None:
            return guessed.chunk_id

    if len(parts) == 1 and re.fullmatch(r"p\d+", parts[0], flags=re.IGNORECASE):
        guessed = by_paragraph.get(parts[0].lower())
        if guessed is not None:
            return guessed.chunk_id

    return None


def _fallback_chunk_lookup(
    chunk_id: str,
    normalized_by_paper_section: dict[tuple[str, str], list[Chunk]],
) -> Chunk | None:
    parts = [part.strip() for part in chunk_id.split("|")]
    if len(parts) != 3:
        return None
    paper_id, section, paragraph_id = parts
    key = (paper_id.lower(), section.strip("*# ").lower())
    candidates = normalized_by_paper_section.get(key, [])
    if not candidates:
        return None
    if paragraph_id.startswith("p") and paragraph_id[1:].isdigit():
        target = int(paragraph_id[1:])

        def distance(chunk: Chunk) -> int:
            if chunk.paragraph_id.startswith("p") and chunk.paragraph_id[1:].isdigit():
                return abs(int(chunk.paragraph_id[1:]) - target)
            return 10**9

        candidates = sorted(candidates, key=distance)
    return candidates[0]


def _normalize_quote_text(text: str) -> str:
    normalized = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    normalized = " ".join(normalized.split())
    return normalized.strip().lower()


def _is_valid_evidence_quote(quote: Any, chunk_text: str) -> bool:
    if not isinstance(quote, str):
        return False
    cleaned_quote = _normalize_quote_text(quote)
    if len(cleaned_quote) < 10:
        return False
    cleaned_chunk = _normalize_quote_text(chunk_text)
    return cleaned_quote in cleaned_chunk


def _extract_english_quote_from_chunk(chunk_text: str) -> str | None:
    # Deterministically extract a short English sentence from the source chunk.
    text = " ".join(chunk_text.split())
    if not text:
        return None
    sentence_candidates = re.split(r"(?<=[.!?。！？])\s+", text)
    valid_candidates: list[str] = []
    for sentence in sentence_candidates:
        sentence = sentence.strip().strip('"')
        if len(sentence) < 20:
            continue
        if not re.search(r"[A-Za-z]", sentence):
            continue
        if re.search(r"[\u4e00-\u9fff]", sentence):
            continue
        valid_candidates.append(sentence[:280])

    if valid_candidates:
        valid_candidates.sort(key=len, reverse=True)
        return valid_candidates[0]

    fallback = text[:280].strip().strip('"')
    if re.search(r"[A-Za-z]", fallback) and not re.search(r"[\u4e00-\u9fff]", fallback):
        return fallback
    return None
