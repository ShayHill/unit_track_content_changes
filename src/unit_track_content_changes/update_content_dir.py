"""Extract content from Unit HSE manual to a folder to idendify content changes.

:author: Shay Hill
:created: 2025-04-01
"""

import datetime
import filecmp
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

from docx2python import docx2python

_PROJECT_DIR = Path(__file__).parents[2]
_MANUAL_DIR = (
    Path.home()
    / "OneDrive"
    / "Foundation Safety"
    / "clients"
    / "Unit Drilling"
    / "HSE Manual"
)

_HISTORY = _PROJECT_DIR / "history" / "docx_content_history"
_CHANGELOG = _PROJECT_DIR / "output" / "changelog.txt"


def _gvim_diff(text_file_a: Path, text_file_b: Path) -> None:
    """Open Vim in diff mode to compare two files.

    :param file1: Path to the first text file
    :param file2: Path to the second text file
    :raises FileNotFoundError: If either file does not exist
    """
    if not text_file_a.exists():
        msg = f"file not found: {text_file_a}"
        raise FileNotFoundError(msg)
    if not text_file_b.exists():
        msg = f"file not found: {text_file_b}"
        raise FileNotFoundError(msg)

    file1_path = str(text_file_a.resolve())
    file2_path = str(text_file_b.resolve())
    _ = subprocess.run(["gvim", "-d", file1_path, file2_path], check=True)


def _iter_manual_files() -> Iterator[Path]:
    yield from _MANUAL_DIR.glob("HSE*.docx")


def _extract_file_content(temp_dir: str, manual_file: Path) -> None:
    """Extract the content from a manual file."""
    with docx2python(manual_file) as doc:
        content = doc.text
    output_file = (Path(temp_dir) / manual_file.name).with_suffix(".txt")
    with output_file.open("w") as output:
        _ = output.write(content)


def _extract_hse_manual_content(temp_dir: str) -> None:
    """Extract the content from the manual files to a temporary dir."""
    for manual_file in _iter_manual_files():
        _extract_file_content(temp_dir, manual_file)


def _add_a_blank_entry_to_the_change_log(filename: str, msg: str = "#TODO") -> None:
    r"""Add a blank entry to the change log.

    filename\ttimestamp\tcontent
    """
    utc = datetime.timezone.utc
    timestamp = datetime.datetime.now(tz=utc).strftime("%Y-%m-%d_%H-%M-%S")
    entry = f"{filename}\t{timestamp}\t{msg}\n"
    _ = sys.stdout.write(entry)
    with _CHANGELOG.open("a") as changelog:
        _ = changelog.write(entry)


def _try_find_stem(dir_: Path, stem: str) -> Path | None:
    """Try to find a file with the given stem in the given directory."""
    candidates = list(dir_.glob(f"{stem}.*"))
    if not candidates:
        return None
    try:
        (match,) = candidates  # unpack singleton
    except ValueError as e:
        msg = "Ambiguous state: Multiple matches for {stem} in {dir_}"
        raise ValueError(msg) from e
    return match


def _find_latest(stem: str) -> Path | None:
    """Search backwards through history to find the latest file with the given stem."""
    history_dirs = sorted(_HISTORY.glob("content_*"), reverse=True)
    for history_dir in history_dirs:
        match = _try_find_stem(history_dir, stem)
        if match is None:
            continue
        if match.suffix == ".deleted":
            return None
        return match
    return None


def _collect_stems() -> set[str]:
    """Collect the stems of all files in the history."""
    stems: set[str] = set()
    for dir_ in _HISTORY.glob("content_*"):
        for file in dir_.glob("*"):
            stems.add(file.stem)
    return stems


def _collect_existing_stems() -> set[str]:
    """List all files that SHOULD BE present in the HSE manual.

    If a file is missing, mark the change that it was deleted.
    """
    stems = _collect_stems()
    for stem in tuple(stems):
        latest = _find_latest(stem)
        if latest is None:
            msg = "Stem {stem} is present in history but not found. This is a bug."
            raise RuntimeError(msg)
        if latest.suffix == ".deleted":
            stems.remove(stem)
    return stems


def _compare_with_state(content_files: str) -> None:
    """Compare content files with latest state in history."""
    new = Path(content_files)
    utc = datetime.timezone.utc
    timestamp = datetime.datetime.now(tz=utc).strftime("%Y-%m-%d_%H-%M-%S")
    changes = _HISTORY / f"content_{timestamp}"
    for new_file in new.glob("*"):
        old_file = _find_latest(new_file.stem)
        if old_file is None:
            _add_a_blank_entry_to_the_change_log(new_file.stem, "file added")
            changes.mkdir(exist_ok=True)
            _ = shutil.copy(new_file, changes / new_file.name)
        elif not filecmp.cmp(old_file, new_file):
            _add_a_blank_entry_to_the_change_log(old_file.stem)
            changes.mkdir(exist_ok=True)
            _ = shutil.copy(new_file, changes / new_file.name)
            _gvim_diff(new_file, old_file)

    old_stems = _collect_existing_stems()
    new_stems = {x.stem for x in new.glob("*")}
    for name in old_stems - new_stems:
        _add_a_blank_entry_to_the_change_log(name, "file removed")
        changes.mkdir(exist_ok=True)
        (changes / name).with_suffix(".deleted").touch()


def main() -> None:
    """Identify and record changes to the HSE manual content."""
    with tempfile.TemporaryDirectory() as temp_dir:
        _extract_hse_manual_content(temp_dir)
        _compare_with_state(temp_dir)


if __name__ == "__main__":
    main()
