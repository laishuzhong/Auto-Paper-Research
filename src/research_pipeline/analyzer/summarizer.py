from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from ..models.schema import Chunk, Evidence, Finding


class OpenAISummarizer:
    def __init__(self, model: str) -> None:
        self.model = model
        self.client = OpenAI()

    def summarize(
        self,
        topic: str,
        questions: list[str],
        chunks: list[Chunk],
        min_findings: int,
    ) -> tuple[list[Finding], dict[str, list[str]]]:
        chunk_map = {chunk.chunk_id: chunk for chunk in chunks}
        context_lines = []
        for chunk in chunks:
            text = chunk.text.strip()
            if len(text) > 800:
                text = text[:800] + "..."
            context_lines.append(
                f"[{chunk.chunk_id}] ({chunk.section}) {text}"
            )

        prompt = (
            "You are summarizing research papers for a topic.\n"
            "Return ONLY valid JSON with this schema:\n"
            '{ "findings": [ { "claim": "...", "evidence": [ { "chunk_id": "...", "quote": "..." } ] } ],'
            ' "paper_map": { "category": ["paper_id", "..."] } }\n'
            "Rules:\n"
            "- Use only the provided context.\n"
            "- Provide at least "
            f"{min_findings} findings.\n"
            "- Evidence must reference a provided chunk_id exactly.\n"
            "- Quotes should be short (1-2 sentences).\n\n"
            f"Topic: {topic}\n"
            f"Questions: {questions}\n\n"
            "Context chunks:\n"
            + "\n".join(context_lines)
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a careful research assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        data = _parse_json(content)

        findings_raw = data.get("findings", [])
        paper_map = data.get("paper_map", {}) or {}
        if not isinstance(findings_raw, list):
            raise ValueError("Summarizer output 'findings' must be a list.")
        findings: list[Finding] = []
        for item in findings_raw:
            claim = item.get("claim")
            evidence_items = item.get("evidence", [])
            if not claim or not isinstance(evidence_items, list):
                raise ValueError("Each finding must include claim and evidence list.")
            evidence_list: list[Evidence] = []
            for evidence in evidence_items:
                chunk_id = evidence.get("chunk_id")
                if chunk_id:
                    if chunk_id not in chunk_map:
                        raise ValueError(f"Evidence does not match any chunk: {chunk_id}")
                    chunk = chunk_map[chunk_id]
                    evidence_list.append(
                        Evidence(
                            paper_id=chunk.paper_id,
                            section=chunk.section,
                            paragraph_id=chunk.paragraph_id,
                            quote=evidence.get("quote"),
                        )
                    )
                    continue
                paper_id = evidence.get("paper_id")
                section = evidence.get("section")
                paragraph_id = evidence.get("paragraph_id")
                if not (paper_id and section and paragraph_id):
                    raise ValueError("Evidence must include chunk_id or paper_id/section/paragraph_id.")
                if f"{paper_id}|{section}|{paragraph_id}" not in chunk_map:
                    raise ValueError(
                        f"Evidence does not match any chunk: {paper_id}|{section}|{paragraph_id}"
                    )
                evidence_list.append(
                    Evidence(
                        paper_id=paper_id,
                        section=section,
                        paragraph_id=paragraph_id,
                        quote=evidence.get("quote"),
                    )
                )
            findings.append(Finding(claim=claim, evidence=evidence_list))

        if len(findings) < min_findings:
            raise ValueError(
                f"Expected at least {min_findings} findings, got {len(findings)}."
            )

        return findings, paper_map


def _parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Failed to parse JSON from summarizer response.") from exc
