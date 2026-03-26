from research_pipeline.analyzer.library import extract_sections, chunk_sections


def test_chunk_sections_paragraph_ids() -> None:
    md_text = """# Intro

First paragraph.

Second paragraph.

## Methods

Method paragraph.
"""
    sections = extract_sections(md_text)
    chunks = chunk_sections("paper-1234", sections)

    assert len(chunks) == 3
    assert chunks[0].section == "Intro"
    assert chunks[0].paragraph_id == "p1"
    assert chunks[1].paragraph_id == "p2"
    assert chunks[2].section == "Methods"
