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
    output = render_report(report)
    assert "- Evidence: paper-1, Intro/p1" in output
