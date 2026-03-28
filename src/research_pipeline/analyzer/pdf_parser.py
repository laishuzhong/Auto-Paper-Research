from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from .scan import make_paper_id


def _marker_command_name(marker_cmd: str) -> str:
    parts = shlex.split(marker_cmd)
    if not parts:
        return ""
    return Path(parts[0]).name


def _build_marker_command(marker_cmd: str, pdf_path: Path, out_md_path: Path) -> list[str]:
    if "{input}" in marker_cmd or "{output}" in marker_cmd:
        rendered = marker_cmd.format(input=str(pdf_path), output=str(out_md_path))
        return shlex.split(rendered)
    command_name = _marker_command_name(marker_cmd)
    if command_name == "marker_single":
        return shlex.split(marker_cmd) + [
            str(pdf_path),
            "--output_dir",
            str(out_md_path.parent),
            "--output_format",
            "markdown",
        ]
    return shlex.split(marker_cmd) + ["--input", str(pdf_path), "--output", str(out_md_path)]


def _find_marker_single_output(pdf_path: Path, output_dir: Path) -> Path | None:
    direct_candidate = output_dir / f"{pdf_path.stem}.md"
    if direct_candidate.exists():
        return direct_candidate
    for candidate in sorted(output_dir.rglob("*.md")):
        if candidate.stem == pdf_path.stem:
            return candidate
    return None


def parse_pdf_to_md(pdf_path: Path, out_md_path: Path, marker_cmd: str) -> None:
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_marker_command(marker_cmd, pdf_path, out_md_path)
    subprocess.run(cmd, check=True)
    if out_md_path.exists():
        return
    if _marker_command_name(marker_cmd) != "marker_single":
        return
    produced_path = _find_marker_single_output(pdf_path, out_md_path.parent)
    if produced_path is None:
        raise FileNotFoundError(
            f"marker_single did not produce markdown output for: {pdf_path}"
        )
    produced_path.replace(out_md_path)


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
