"""Decodes the Piece Table (PlcPcd) to enumerate document segments."""

import io
import struct
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class PieceSegment:
    cp_start: int
    cp_end: int
    offset: int
    encoding: str
    byte_length: int


class PieceTable:
    """Translates the CLX/Pcdt into text segments."""

    def __init__(self, table_stream: bytes, fc_clx: int, lcb_clx: int):
        self._table = table_stream
        self._clx = self._extract_clx(self._table, fc_clx, lcb_clx)
        self._segments = self._parse()

    @staticmethod
    def _extract_clx(table_stream: bytes, fc_clx: int, lcb_clx: int) -> bytes:
        end = fc_clx + lcb_clx
        if fc_clx < 0 or end > len(table_stream):
            raise ValueError("Table stream is too short for CLX")
        return table_stream[fc_clx:end]

    def _parse(self) -> List[PieceSegment]:
        marker = b"\x02"
        idx = self._clx.find(marker)
        if idx == -1 or idx + 5 > len(self._clx):
            raise ValueError("Pcdt header missing in CLX")
        length = struct.unpack_from("<I", self._clx, idx + 1)[0]
        start = idx + 5
        plc = self._clx[start : start + length]
        if len(plc) < 4 or (len(plc) - 4) % 12 != 0:
            raise ValueError("PlcPcd is malformed")
        count = (len(plc) - 4) // 12
        cp_values = struct.unpack_from(f"<{count + 1}I", plc, 0)
        pcds = plc[4 * (count + 1) :]
        if len(pcds) != count * 8:
            raise ValueError("Pcd array size mismatch")
        segments: List[PieceSegment] = []
        for i in range(count):
            cp_start = cp_values[i]
            cp_end = cp_values[i + 1]
            if cp_end <= cp_start:
                continue
            pcd_offset = i * 8
            fc_raw = struct.unpack_from("<H I H", pcds, pcd_offset)[1]
            is_compressed = bool(fc_raw & 0x40000000)
            fc_value = fc_raw & 0x3FFFFFFF
            file_offset = fc_value // 2 if is_compressed else fc_value
            char_count = cp_end - cp_start
            byte_length = char_count if is_compressed else char_count * 2
            encoding = "cp1252" if is_compressed else "utf-16le"
            segments.append(
                PieceSegment(cp_start, cp_end, file_offset, encoding, byte_length)
            )
        return segments

    def segments(self) -> Iterable[PieceSegment]:
        return iter(self._segments)
