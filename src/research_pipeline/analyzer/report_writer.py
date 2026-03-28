from __future__ import annotations

from pathlib import Path

from ..models.schema import Evidence, Finding, PaperMeta, TopicReport


def generate_topic_report(
    topic: str,
    papers: list[PaperMeta],
    findings: list[Finding],
    paper_map: dict[str, list[str]],
    out_path: Path,
    paper_title_map: dict[str, str] | None = None,
) -> TopicReport:
    if not paper_map:
        paper_map = {"All papers": [paper.paper_id for paper in papers]}
    table_rows = [
        {
            "paper_id": paper.paper_id,
            "title": paper.title or "",
            "year": str(paper.year) if paper.year else "",
            "source": paper.source or "",
        }
        for paper in papers
    ]

    report = TopicReport(
        topic=topic, findings=findings, paper_map=paper_map, table_rows=table_rows
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        render_report(report, paper_title_map=paper_title_map or {}),
        encoding="utf-8",
    )
    return report


def render_report(report: TopicReport, paper_title_map: dict[str, str] | None = None) -> str:
    paper_title_map = paper_title_map or {}
    lines: list[str] = []
    lines.append(f"# 主题报告：{report.topic}")
    lines.append("")
    lines.append("## 论文映射")
    for category, papers in report.paper_map.items():
        readable = [_render_paper_ref(paper, paper_title_map) for paper in papers]
        lines.append(f"- {category}: {', '.join(readable)}")
    lines.append("")
    lines.append("## 论文对照表（简化）")
    lines.append("| 论文ID | 标题 | 年份 | 来源 |")
    lines.append("| --- | --- | --- | --- |")
    for row in report.table_rows:
        lines.append(
            f"| {row['paper_id']} | {row['title']} | {row['year']} | {row['source']} |"
        )
    lines.append("")
    lines.append("## 核心结论")
    for index, finding in enumerate(report.findings, start=1):
        lines.append(f"{index}. {finding.claim}")
        if finding.evidence:
            for evidence in finding.evidence:
                lines.append(_format_evidence(evidence, paper_title_map))
        else:
            lines.append("- 证据：无有效证据（重试3次后仍未通过校验）")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_paper_ref(raw: str, paper_title_map: dict[str, str]) -> str:
    if "|" in raw:
        paper_id, remainder = raw.split("|", 1)
        title = paper_title_map.get(paper_id, paper_id)
        return f"{title} ({paper_id})|{remainder}"
    title = paper_title_map.get(raw, raw)
    return f"{title} ({raw})"


def _format_evidence(evidence: Evidence, paper_title_map: dict[str, str]) -> str:
    title = paper_title_map.get(evidence.paper_id, evidence.paper_id)
    line = (
        f"- 证据：{title} ({evidence.paper_id}), "
        f"{evidence.section}/{evidence.paragraph_id}"
    )
    if evidence.quote:
        line += f' ("{evidence.quote}")'
    return line
