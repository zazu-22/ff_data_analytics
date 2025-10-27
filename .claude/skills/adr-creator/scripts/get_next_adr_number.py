#!/usr/bin/env python3
"""Get next ADR number by reading existing ADR files."""

import re
from pathlib import Path


def get_next_adr_number(adr_dir: Path = Path("docs/adr")) -> int:
    """Find the highest ADR number and return next."""
    adr_files = list(adr_dir.glob("ADR-*.md"))

    if not adr_files:
        return 1

    numbers = []
    for file in adr_files:
        match = re.search(r"ADR-(\d+)", file.name)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1


if __name__ == "__main__":
    next_num = get_next_adr_number()
    print(f"Next ADR number: {next_num:03d}")
    print(f"Filename: ADR-{next_num:03d}-your-title.md")
