"""Extract content from Unit HSE manual to a folder to idendify content changes.

:author: Shay Hill
:created: 2025-04-01
"""

import itertools as it

import sys
import subprocess

from contextlib import suppress
import shutil
import os
from pathlib import Path
from collections.abc import Iterator
import datetime
from docx2python import docx2python
import filecmp

_MANUAL_DIR = Path(__file__).parents[1]
_CONTENT_DIR = Path(__file__).parent / "docx_content"
_CONTENT_HISTORY_DIR = Path(__file__).parent / "docx_content_history"
_CONTENT_CACHE_DIR = Path(__file__).parent / "docx_content_cache"
_CHANGELOG = Path(__file__).parent / "changelog.txt"

for dir in (_CONTENT_DIR, _CONTENT_HISTORY_DIR):
    dir.mkdir(exist_ok=True)

def _gvim_diff(text_file_a: Path, text_file_b: Path) -> None:
    """Open Vim in diff mode to compare two files.

    :param file1: Path to the first text file
    :param file2: Path to the second text file
    :raises FileNotFoundError: If either file does not exist
    """
    if not text_file_a.exists():
        raise FileNotFoundError(f"File not found: {text_file_a}")
    if not text_file_b.exists():
        raise FileNotFoundError(f"File not found: {text_file_b}")

    file1_path = str(text_file_a.resolve())
    file2_path = str(text_file_b.resolve())
    subprocess.run(["gvim", "-d", file1_path, file2_path], check=True)

def _iter_manual_files() -> Iterator[Path]:
    for manual_file in _MANUAL_DIR.glob("HSE*.docx"):
        yield manual_file


def _copy_content_dir() -> Path:
    """Copy the _CONTENT_DIR to a new folder with a timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    new_content_dir = _CONTENT_HISTORY_DIR / f"content_{timestamp}"
    new_content_dir.mkdir()
    for content_file in _CONTENT_DIR.glob("*"):
        content_file.rename(new_content_dir / content_file.name)
    return new_content_dir


def _move_content_to_cache():
    """Cache the _CONTENT_DIR to a new folder with a timestamp."""
    with suppress(FileNotFoundError):
        shutil.rmtree(_CONTENT_CACHE_DIR)
    _CONTENT_CACHE_DIR.mkdir()
    for content_file in _CONTENT_DIR.glob("*"):
        content_file.rename(_CONTENT_CACHE_DIR / content_file.name)


def _restore_cached_content():
    """Restore the _CONTENT_DIR from the cache."""
    _clear_content_dir()
    for content_file in _CONTENT_CACHE_DIR.glob("*"):
        content_file.rename(_CONTENT_DIR / content_file.name)
    with suppress(FileNotFoundError):
        shutil.rmtree(_CONTENT_CACHE_DIR)


def _clear_content_dir():
    """Clear the _CONTENT_DIR."""
    for content_file in _CONTENT_DIR.glob("*"):
        content_file.unlink()


def _extract_file_content(manual_file: Path) -> None:
    """Extract the content from a manual file."""
    with docx2python(manual_file) as doc:
        content = doc.text
    output_file = (_CONTENT_DIR / manual_file.name).with_suffix(".txt")
    with output_file.open("w") as output:
        output.write(content)


def _extract_hse_manual_content() -> None:
    """Extract the content from the manual files to the _CONTENT_DIR."""
    for manual_file in _iter_manual_files():
        _extract_file_content(manual_file)


def _add_a_blank_entry_to_the_change_log(filename: str, msg: str = "#TODO") -> None:
    """Add a blank entry to the change log.

    filename\ttimestamp\tcontent
    """
    timestamp = datetime.datetime.now().strftime("%y%m%d %H:%M:%S")
    entry = f"{filename}\t{timestamp}\t{msg}\n"
    sys.stdout.write(entry)
    with _CHANGELOG.open("a") as changelog:
        changelog.write(entry)

def _try_find_stem(dir_: Path, stem: str) -> Path | None:
    """Try to find a file with the given stem in the given directory."""
    candidates = list(dir_.glob(f'{stem}.*'))
    if not candidates:
        return None
    try:
        match, = candidates  # unpack singleton
    except ValueError:
        msg = "Ambiguous state: Multiple matches for {stem} in {dir_}"
        raise ValueError(msg)
    return match

# def collect_stems() -> set[str]:
#     stems: set[str] = set()
#     for dir_ in _CONTENT_HISTORY_DIR.glob("content_*"):
#         for file in dir_.glob("*"):
#             stems.add(file.stem)
#     return stems

# def strip_redundant_history():
#     stems = collect_stems()
#     dirs = sorted(_CONTENT_HISTORY_DIR.glob("content_*"), reverse=True)
#     for stem in stems:
#         matches = [_try_find_stem(dir_, stem) for dir_ in dirs]
#         for prv, nxt in it.pairwise(matches):
#             if prv is None:
#                 continue
#             if nxt is None:
#                 continue
#             if filecmp.cmp(prv, nxt):
#                 print(f'unlinking {prv}')
#                 os.unlink(prv)
def remove_empty():
    dirs = sorted(_CONTENT_HISTORY_DIR.glob("content_*"), reverse=True)
    for dir_ in dirs:
        if not list(dir_.glob('*')):
            print(f'removing empty dir {dir_}')
            dir_.rmdir()

remove_empty()

def _find_latest(name: str) -> Path | None:
    """Search backwards through history to find the latest file with the given name."""
    history_dirs = sorted(_CONTENT_HISTORY_DIR.glob("content_*"), reverse=True)
    stem = Path(name).stem
    for history_dir in history_dirs:
        match = _try_find_stem(history_dir, stem)
        if match is None:
            continue
        if match.suffix == '.deleted':
            return None
        return match



def _compare_content_files(old: Path, new: Path) -> None:
    """Compare the content files in two directories."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    changes = _CONTENT_HISTORY_DIR / f"content_{timestamp}"
    for new_file in new.glob('*'):
        old_file = _find_latest(new_file.name)
        if old_file is None:
            _add_a_blank_entry_to_the_change_log(new_file.stem, "file added")
            changes.mkdir(exist_ok=True)
            shutil.copy(new_file, changes / new_file.name)
        elif not filecmp.cmp(old_file, new_file):
            _add_a_blank_entry_to_the_change_log(old_file.stem)
            changes.mkdir(exist_ok=True)
            shutil.copy(new_file, changes / new_file.name)
            _gvim_diff(new_file, old_file)
    old_stems = {x.stem for x in _CONTENT_CACHE_DIR.glob('*')}
    new_stems = {x.stem for x in new.glob('*')}
    for name in old_stems - new_stems:
        _add_a_blank_entry_to_the_change_log(name, "file removed")
        changes.mkdir(exist_ok=True)
        (changes / name).with_suffix('.deleted').touch()


def main():
    cache = _move_content_to_cache()

    # If *anything* goes wrong, restore the old content. Most likely, a file was open
    # in Word and the extraction blew up due to a permission error.
    try:
        _extract_hse_manual_content()
    except Exception as e:
        sys.stdout.write(f"Error extracting content: {e}. Restoring state.\n")
        _restore_cached_content()

    _compare_content_files(_CONTENT_CACHE_DIR, _CONTENT_DIR)


if __name__ == "__main__":
    pass
    # _move_content_to_cache()
    # _restore_cached_content()
    main()
