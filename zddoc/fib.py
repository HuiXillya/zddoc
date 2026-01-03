"""Parses the File Information Block (FIB) from a WordDocument stream."""

import struct
from dataclasses import dataclass
from typing import Final

FC_CLX_OFFSET: Final[int] = 0x01A2
LCB_CLX_OFFSET: Final[int] = 0x01A6
FIB_MIN_SIZE: Final[int] = 0x01AA


@dataclass
class WordFIB:
    """Minimal view of the Fib needed to locate the Piece Table."""

    fWhichTblStm: bool
    table_stream_name: str
    fcClx: int
    lcbClx: int
    is_encrypted: bool
    nFib: int

    @classmethod
    def from_bytes(cls, data: bytes) -> "WordFIB":
        if len(data) < FIB_MIN_SIZE:
            raise ValueError("WordDocument stream is too short to contain a FIB")
        nFib = struct.unpack_from("<H", data, 0x0002)[0]
        flags = struct.unpack_from("<H", data, 0x000A)[0]
        fWhichTblStm = bool(flags & 0x0200)
        is_encrypted = bool(flags & 0x0100)
        fcClx = struct.unpack_from("<I", data, FC_CLX_OFFSET)[0]
        lcbClx = struct.unpack_from("<I", data, LCB_CLX_OFFSET)[0]
        table_stream_name = "1Table" if fWhichTblStm else "0Table"
        return cls(fWhichTblStm, table_stream_name, fcClx, lcbClx, is_encrypted, nFib)
