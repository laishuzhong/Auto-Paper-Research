from pathlib import Path

from research_pipeline.analyzer.scan import make_paper_id


def test_make_paper_id_stable(tmp_path: Path) -> None:
    pdf_path = tmp_path / "Sample.pdf"
    pdf_path.write_bytes(b"sample content")

    first = make_paper_id(pdf_path)
    second = make_paper_id(pdf_path)

    assert first == second


def test_make_paper_id_changes_with_content(tmp_path: Path) -> None:
    pdf_path = tmp_path / "Sample.pdf"
    pdf_path.write_bytes(b"sample content")
    first = make_paper_id(pdf_path)

    pdf_path.write_bytes(b"updated content")
    second = make_paper_id(pdf_path)

    assert first != second
