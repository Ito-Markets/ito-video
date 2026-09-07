#!/usr/bin/env python3
"""Ito draft defaults; reusable export implementation comes from installed ECC."""

import sys
from pathlib import Path

from tasteforge.media.capcut import main as export_main


def main():
    root = Path(__file__).resolve().parent
    export_main(
        [
            str(root / "concat.txt"),
            "--drafts",
            str(Path.home() / "Movies/CapCut/User Data/Projects/com.lveditor.draft"),
            "--name",
            "ito_brand_film",
            *sys.argv[1:],
        ]
    )


if __name__ == "__main__":
    main()
