from research_pipeline.analyzer.report_writer import render_report
from research_pipeline.models.schema import Evidence, Finding, TopicReport


def test_render_report_includes_evidence_line() -> None:
    report = TopicReport(
        topic="autism large language model",
        findings=[
            Finding(
                claim="Test claim",
                evidence=[Evidence(paper_id="paper-1", section="Intro", paragraph_id="p1")],
            )
        ],
        paper_map={"All papers": ["paper-1"]},
        table_rows=[],
    )
    output = render_report(report, paper_title_map={"paper-1": "示例论文"})
    assert "- 证据：示例论文 (paper-1), Intro/p1" in output


def test_render_report_marks_missing_evidence() -> None:
    report = TopicReport(
        topic="autism large language model",
        findings=[Finding(claim="Test claim without evidence", evidence=[])],
        paper_map={"All papers": ["paper-1"]},
        table_rows=[],
    )
    output = render_report(report, paper_title_map={"paper-1": "示例论文"})
    assert "无有效证据（重试3次后仍未通过校验）" in output
