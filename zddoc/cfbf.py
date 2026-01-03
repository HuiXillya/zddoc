"""Minimal OLE2 CFBF reader implemented with the standard library."""

import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, Sequence, Union

OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD


class DocFormatError(Exception):
    """Raised when the container is not a valid OLE2 file."""


class MissingStreamError(Exception):
    """Raised when a required stream cannot be found."""


@dataclass
class DirectoryEntry:
    name: str
    object_type: int
    start_sector: int
    stream_size: int


class CFBFReader:
    """Provide transparent access to streams stored in a Compound File."""

    def __init__(self, source: Union[str, Path, BinaryIO, bytes]):
        self._stream = self._open_source(source)
        self._owns_stream = isinstance(source, (str, Path))
        self._header = self._read_exact(512)
        self._validate_header()
        self._fat_sectors = []
        self._fat: Sequence[int] = ()
        self._entries: Dict[str, DirectoryEntry] = {}
        self._mini_stream_data = b""
        self._mini_fat: Sequence[int] = []
        self._build_fat()
        self._read_directory()
        self._load_mini_stream()

    def _open_source(self, source: Union[str, Path, BinaryIO, bytes]) -> BinaryIO:
        if isinstance(source, bytes):
            return io.BytesIO(source)
        if isinstance(source, (str, Path)):
            return open(source, "rb")
        if hasattr(source, "read") and hasattr(source, "seek"):
            return source
        raise TypeError("source must be path, bytes, or file-like")

    def _read_exact(self, size: int) -> bytes:
        data = self._stream.read(size)
        if len(data) != size:
            raise DocFormatError("container header is truncated")
        return data

    def _validate_header(self) -> None:
        if self._header[:8] != OLE_SIGNATURE:
            raise DocFormatError("not an OLE2 container")
        sector_shift = struct.unpack_from("<H", self._header, 0x1E)[0]
        mini_sector_shift = struct.unpack_from("<H", self._header, 0x20)[0]
        self.sector_size = 1 << sector_shift
        self.mini_sector_size = 1 << mini_sector_shift
        self._dir_start_sector = struct.unpack_from("<I", self._header, 0x30)[0]
        self.mini_stream_cutoff = struct.unpack_from("<I", self._header, 0x38)[0]
        self._mini_fat_start = struct.unpack_from("<I", self._header, 0x3C)[0]
        self._mini_fat_sectors = struct.unpack_from("<I", self._header, 0x40)[0]
        self._difat_start = struct.unpack_from("<I", self._header, 0x44)[0]
        self._difat_sectors = struct.unpack_from("<I", self._header, 0x48)[0]
        self._difat_entries = struct.unpack_from("<109I", self._header, 0x4C)

    def _sector_offset(self, sector_index: int) -> int:
        return self.sector_size * (sector_index + 1)

    def _read_sector(self, sector_index: int) -> bytes:
        try:
            self._stream.seek(self._sector_offset(sector_index))
        except OSError as exc:
            raise DocFormatError("failed to seek sector %d" % sector_index) from exc
        sector = self._stream.read(self.sector_size)
        if len(sector) != self.sector_size:
            raise DocFormatError("sector %d is truncated" % sector_index)
        return sector

    def _build_fat(self) -> None:
        self._fat_sectors = [idx for idx in self._difat_entries if idx not in (FREESECT, ENDOFCHAIN)]
        next_sector = self._difat_start
        entries_per_sector = (self.sector_size - 4) // 4
        fmt = f"<{entries_per_sector}I"
        while next_sector not in (FREESECT, ENDOFCHAIN):
            block = self._read_sector(next_sector)
            self._fat_sectors.extend(
                idx for idx in struct.unpack_from(fmt, block, 0) if idx not in (FREESECT, ENDOFCHAIN)
            )
            next_sector = struct.unpack_from("<I", block, entries_per_sector * 4)[0]
        fat_data = bytearray()
        for sector in self._fat_sectors:
            fat_data.extend(self._read_sector(sector))
        self._fat = struct.unpack(f"<{len(fat_data) // 4}I", fat_data) if fat_data else ()

    def _iter_chain(self, start_sector: int) -> Iterable[int]:
        sector = start_sector
        while sector not in (FREESECT, ENDOFCHAIN):
            yield sector
            try:
                sector = self._fat[sector]
            except IndexError as exc:
                raise DocFormatError("FAT chain is corrupt") from exc

    def _read_chain(self, start_sector: int) -> bytes:
        if start_sector in (FREESECT, ENDOFCHAIN):
            return b""
        data = bytearray()
        for sector in self._iter_chain(start_sector):
            data.extend(self._read_sector(sector))
        return bytes(data)

    def _read_directory(self) -> None:
        raw = self._read_chain(self._dir_start_sector)
        for offset in range(0, len(raw), 128):
            entry = raw[offset : offset + 128]
            if len(entry) < 128:
                break
            name_len = struct.unpack_from("<H", entry, 0x40)[0]
            if name_len < 2:
                continue
            name = entry[: name_len - 2].decode("utf-16le", errors="ignore").rstrip("\x00")
            object_type = entry[0x42]
            start_sector = struct.unpack_from("<I", entry, 0x74)[0]
            stream_size = struct.unpack_from("<Q", entry, 0x78)[0]
            self._entries[name] = DirectoryEntry(name, object_type, start_sector, stream_size)

    def _load_mini_stream(self) -> None:
        root = self._entries.get("Root Entry")
        if not root or root.stream_size == 0:
            return
        self._mini_stream_data = self._read_chain(root.start_sector)[: root.stream_size]
        if self._mini_fat_start in (FREESECT, ENDOFCHAIN):
            return
        mini_fat_bytes = bytearray()
        for sector in self._iter_chain(self._mini_fat_start):
            mini_fat_bytes.extend(self._read_sector(sector))
        if mini_fat_bytes:
            self._mini_fat = struct.unpack(f"<{len(mini_fat_bytes) // 4}I", mini_fat_bytes)

    def open_stream(self, name: str) -> io.BytesIO:
        entry = self._entries.get(name)
        if not entry:
            raise MissingStreamError(f"stream {name!r} not found")
        if entry.stream_size == 0:
            return io.BytesIO(b"")
        use_mini = (
            entry.stream_size < self.mini_stream_cutoff
            and entry.start_sector not in (FREESECT, ENDOFCHAIN)
            and self._mini_stream_data
            and self._mini_fat
        )
        if use_mini:
            data = self._read_mini_chain(entry.start_sector)
        else:
            data = self._read_chain(entry.start_sector)
        return io.BytesIO(data[: entry.stream_size])

    def _read_mini_chain(self, start_sector: int) -> bytes:
        if not self._mini_stream_data or not self._mini_fat:
            raise DocFormatError("mini stream data is unavailable")
        data = bytearray()
        sector = start_sector
        while sector not in (FREESECT, ENDOFCHAIN):
            offset = sector * self.mini_sector_size
            data.extend(self._mini_stream_data[offset : offset + self.mini_sector_size])
            if sector >= len(self._mini_fat):
                raise DocFormatError("mini FAT is corrupt")
            sector = self._mini_fat[sector]
        return bytes(data)

    def close(self) -> None:
        if self._owns_stream:
            self._stream.close()

    def __enter__(self) -> "CFBFReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
