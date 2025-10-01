"""Find every reference to qualified personnel in the HSE manuals.

I used this script to find all the qualified personnel references on 250904. This is
:robably no longer needed.

:author: Shay Hill
:created: 2025-09-04
"""

from re import L
import sys

import os
from pathlib import Path
from collections.abc import Iterator
import datetime
from docx2python import docx2python
import filecmp
from docx2python.iterators import iter_paragraphs

_MANUAL_DIR = Path(__file__).parents[1]
_CONTENT_DIR = Path(__file__).parent / "docx_content"
_CONTENT_HISTORY_DIR = Path(__file__).parent / "docx_content_history"
_CHANGELOG = Path(__file__).parent / "changelog.txt"

for dir in (_CONTENT_DIR, _CONTENT_HISTORY_DIR):
    dir.mkdir(exist_ok=True)

def _iter_manual_files() -> Iterator[Path]:
    for manual_file in _MANUAL_DIR.glob('HSE*.docx'):
        yield manual_file

def _extract_file_content(manual_file: Path) -> Iterator[str]:
    """Extract the content from a manual file."""
    title_yielded = False
    with docx2python(manual_file) as doc:
        content = doc.body_pars
    pars = iter_paragraphs(content)
    pars = (p for p in pars if any("qualif" in s for s in p.run_strings))
    for par in pars:
        if not title_yielded:
            yield f"# {manual_file.name}"
            title_yielded = True
        yield "".join(par.run_strings).strip()

def _extract_hse_manual_content() -> Iterator[str]:
    """Extract the content from the manual files to the _CONTENT_DIR."""
    for manual_file in _iter_manual_files():
        yield from _extract_file_content(manual_file)

def main():
    lines = _extract_hse_manual_content()
    breakpoint()
     

if __name__ == "__main__":
    main()




