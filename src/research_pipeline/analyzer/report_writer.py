from __future__ import annotations

from pathlib import Path

from ..models.schema import Evidence, Finding, PaperMeta, TopicReport


def generate_topic_report(
    topic: str,
    papers: list[PaperMeta],
    findings: list[Finding],
    paper_map: dict[str, list[str]],
    out_path: Path,
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
    out_path.write_text(render_report(report), encoding="utf-8")
    return report


def render_report(report: TopicReport) -> str:
    lines: list[str] = []
    lines.append(f"# Topic Report: {report.topic}")
    lines.append("")
    lines.append("## Paper Map")
    for category, papers in report.paper_map.items():
        lines.append(f"- {category}: {', '.join(papers)}")
    lines.append("")
    lines.append("## Comparison Table (Simplified)")
    lines.append("| Paper ID | Title | Year | Source |")
    lines.append("| --- | --- | --- | --- |")
    for row in report.table_rows:
        lines.append(
            f"| {row['paper_id']} | {row['title']} | {row['year']} | {row['source']} |"
        )
    lines.append("")
    lines.append("## Key Findings")
    for index, finding in enumerate(report.findings, start=1):
        lines.append(f"{index}. {finding.claim}")
        for evidence in finding.evidence:
            lines.append(_format_evidence(evidence))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _format_evidence(evidence: Evidence) -> str:
    line = (
        f"- Evidence: {evidence.paper_id}, "
        f"{evidence.section}/{evidence.paragraph_id}"
    )
    if evidence.quote:
        line += f' ("{evidence.quote}")'
    return line
