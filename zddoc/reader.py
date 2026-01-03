"""Facade that exposes the steps needed to read text from binary .doc files."""

import io
from typing import Iterable

from .cfbf import CFBFReader, DocFormatError
from .fib import WordFIB
from .piece_table import PieceSegment, PieceTable


class DocReader:
    """High-level API to load text from a pure Python CFBF reader."""

    def __init__(self, source):
        self._cfbf = CFBFReader(source)

    def read_text(self) -> str:
        word_stream = self._cfbf.open_stream("WordDocument")
        word_bytes = word_stream.getvalue()
        fib = WordFIB.from_bytes(word_bytes)
        if fib.is_encrypted:
            raise DocFormatError("encrypted documents are not supported")
        table_bytes = self._cfbf.open_stream(fib.table_stream_name).read()
        piece_table = PieceTable(table_bytes, fib.fcClx, fib.lcbClx)
        segments = tuple(piece_table.segments())
        consolidator = io.BytesIO(word_bytes)
        parts = []
        for segment in segments:
            parts.append(self._decode_segment(segment, consolidator))
        return self._normalize("".join(parts))

    @staticmethod
    def _decode_segment(segment: PieceSegment, stream: io.BytesIO) -> str:
        stream.seek(segment.offset)
        raw = stream.read(segment.byte_length)
        return raw.decode(segment.encoding, errors="ignore")

    @staticmethod
    def _normalize(content: str) -> str:
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        content = content.replace("\x0c", "\n").replace("\x07", "\t")
        for control in ("\x13", "\x14", "\x15"):
            content = content.replace(control, "")
        return content

    def close(self) -> None:
        self._cfbf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
