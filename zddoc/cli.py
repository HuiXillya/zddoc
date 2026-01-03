"""Command-line helper to dump text from a Word 97-2003 document."""

import argparse
from pathlib import Path

from .cfbf import DocFormatError
from .reader import DocReader


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump text from a binary .doc file using pure Python")
    parser.add_argument("document", type=Path, help="path to the .doc file")
    parser.add_argument("--no-newline", action="store_true", help="do not append final newline")
    args = parser.parse_args()
    try:
        with DocReader(args.document) as reader:
            text = reader.read_text()
    except DocFormatError as exc:
        parser.error(str(exc))
    end = "" if args.no_newline else "\n"
    print(text, end=end)


if __name__ == "__main__":
    main()
