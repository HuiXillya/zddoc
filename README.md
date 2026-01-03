# zddoc

Pure-Python reader for legacy Microsoft Word 97-2003 (`.doc`) documents. The project parses the underlying OLE2 container, the Word File Information Block, and the Piece Table entirely with Python’s standard library (mostly `struct`, `io`, and dataclasses) so it can be embedded in lightweight services or CLI utilities without third-party dependencies.

## Installation

Build/install locally before publishing, or let pip pull directly from GitHub later:

```bash
# From this repo
pip install .

# From GitHub once the repository is public and tagged
pip install git+https://github.com/HuiXillya/zddoc.git@v0.1.0
```

## Usage

The package exposes a CLI helper:

```bash
python -m zddoc.cli path/to/example.doc
```

And you can programmatically read a document as well:

```python
from zddoc.reader import DocReader

with DocReader("path/to/example.doc") as reader:
    text = reader.read_text()
```

## Testing

Run the regression suite with:

```bash
python -m unittest discover tests
```

The tests include a fixture document in `test_doc/hnw14-vdw79.doc`.

## Project layout

- `zddoc/cfbf.py` – Minimal Compound File Binary Format reader.
- `zddoc/fib.py` – Parses Word’s File Information Block and chooses the correct table stream.
- `zddoc/piece_table.py` – Traverses the CLX/Pcdt tables to decode compressed vs. Unicode segments.
- `zddoc/reader.py` – Facade that drives the extraction loop and normalizes control characters.
- `zddoc/cli.py` – Entry point for CLI usage.
- `tests/` – Unit tests (including an integration check against the sample `.doc`).
- `test_doc/` – Contains the sample document used by the integration test.

## Packaging notes

`pyproject.toml` selects setuptools/wheel as the build backend, and `setup.cfg` provides metadata plus a console script entry point (`zddoc`). When you push to GitHub, add a tag (`v0.1.0`) so pip can install a specific release.

