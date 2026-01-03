import io
import struct
import unittest
from pathlib import Path

from zddoc.cfbf import DocFormatError
from zddoc.fib import (
    FC_CLX_OFFSET,
    FIB_MIN_SIZE,
    LCB_CLX_OFFSET,
    WordFIB,
)
from zddoc.piece_table import PieceTable
from zddoc.reader import DocReader


def _build_fib_bytes(*, which_tbl: bool = False, encrypted: bool = False) -> bytes:
    data = bytearray(FIB_MIN_SIZE)
    struct.pack_into("<H", data, 0x0002, 0x00C1)
    flags = (0x0200 if which_tbl else 0) | (0x0100 if encrypted else 0)
    struct.pack_into("<H", data, 0x000A, flags)
    struct.pack_into("<I", data, FC_CLX_OFFSET, 0x1234)
    struct.pack_into("<I", data, LCB_CLX_OFFSET, 0x56)
    return bytes(data)


class WordFIBTest(unittest.TestCase):
    def test_table_stream_selection(self) -> None:
        fib = WordFIB.from_bytes(_build_fib_bytes(which_tbl=True))
        self.assertEqual("1Table", fib.table_stream_name)
        fib = WordFIB.from_bytes(_build_fib_bytes(which_tbl=False))
        self.assertEqual("0Table", fib.table_stream_name)

    def test_encryption_flag(self) -> None:
        fib = WordFIB.from_bytes(_build_fib_bytes(encrypted=True))
        self.assertTrue(fib.is_encrypted)

    def test_invalid_slice(self) -> None:
        with self.assertRaises(ValueError):
            WordFIB.from_bytes(b"short")


class PieceTableTest(unittest.TestCase):
    def test_simple_segment(self) -> None:
        cp_values = (0, 3)
        pcd = struct.pack("<H I H", 0, 0x40, 0)
        plc = struct.pack("<2I", *cp_values) + pcd
        clx = b"\x02" + struct.pack("<I", len(plc)) + plc
        fc_clx = 128
        table = bytearray(fc_clx + len(clx) + 16)
        table[fc_clx:fc_clx + len(clx)] = clx
        piece_table = PieceTable(bytes(table), fc_clx, len(clx))
        segments = list(piece_table.segments())
        self.assertEqual(1, len(segments))
        segment = segments[0]
        self.assertEqual(0x40, segment.offset)
        self.assertEqual(3 * 2, segment.byte_length)

    def test_missing_clx(self) -> None:
        table = bytearray(b"\x00" * 16)
        with self.assertRaises(ValueError):
            PieceTable(bytes(table), 8, 4)


class DocReaderTest(unittest.TestCase):
    def test_non_cfbf_rejected(self) -> None:
        with self.assertRaises(DocFormatError):
            DocReader(b"invalid")


class DocReaderIntegrationTest(unittest.TestCase):
    def test_reads_sample_doc(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        doc_path = base_dir / "test_doc" / "hnw14-vdw79.doc"
        with DocReader(doc_path) as reader:
            text = reader.read_text()
        self.assertIn("my test file for python", text)


if __name__ == "__main__":
    unittest.main()
