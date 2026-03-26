from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from .scan import make_paper_id


def _build_marker_command(marker_cmd: str, pdf_path: Path, out_md_path: Path) -> list[str]:
    if "{input}" in marker_cmd or "{output}" in marker_cmd:
        rendered = marker_cmd.format(input=str(pdf_path), output=str(out_md_path))
        return shlex.split(rendered)
    return shlex.split(marker_cmd) + ["--input", str(pdf_path), "--output", str(out_md_path)]


def parse_pdf_to_md(pdf_path: Path, out_md_path: Path, marker_cmd: str) -> None:
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_marker_command(marker_cmd, pdf_path, out_md_path)
    subprocess.run(cmd, check=True)


def parse_batch(
    pdf_paths: list[Path],
    out_dir: Path,
    marker_cmd: str,
    skip_existing: bool = True,
) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    parsed_paths: list[Path] = []
    for pdf in pdf_paths:
        out_path = out_dir / f"{make_paper_id(pdf)}.md"
        if skip_existing and out_path.exists():
            parsed_paths.append(out_path)
            continue
        parse_pdf_to_md(pdf, out_path, marker_cmd)
        parsed_paths.append(out_path)
    return parsed_paths
