"""Read the Unit HSE Manual changelog and create a report of changes.

:author: Shay Hill
:created: 2025-08-18
"""

from pathlib import Path
import re

_LOG = Path(__file__).parent / "changelog.txt"



def map_changes_to_filenames() -> dict[str, list[str]]:
    """Map changes to filenames from the changelog.

    :return: {filename: [list of changes]}
    """
    filename2changes: dict[str, list[str]] = {}
    with _LOG.open("r", encoding = 'utf-8') as log_file:
        log_entries = log_file.readlines()
    for entry in log_entries[1:]:
        filename, _, content = (x.strip() for x in entry.split("\t"))
        filename2changes.setdefault(filename, []).append(content)
    return filename2changes

def print_changes_report(changes: dict[str, list[str]]) -> None:
    """Print a report of changes.

    :param changes: {filename: [list of changes]}
    """
    blocks: list[str] = []
    for k, v in changes.items():
        block = f"{k}:\n" + "\n".join(f"  - {change}" for change in v)
        blocks.append(block)
    report = "\n\n".join(sorted(blocks))
    print(report)


if __name__ == "__main__":
    filename2changes = map_changes_to_filenames()
    print_changes_report(filename2changes)
