"""zddoc: pure-Python reader for Word 97-2003 binary documents."""

from .reader import DocReader
from .cfbf import CFBFReader
from .fib import WordFIB
from .piece_table import PieceTable

__all__ = ["DocReader", "CFBFReader", "WordFIB", "PieceTable"]
