#!/usr/bin/env python3
"""Inspect O1 records stored in a local NVDTLab 0B41 RTD file.

This is a research probe, not a production parser.  All offsets printed by this
script are zero-based byte offsets in the 960-byte O1 record body.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


LOCAL_FILE_SIGNATURE = 0x04034B50
STORED = 0
DEFLATED = 8
O1_BODY_LENGTH = 960
HORSE_BLOCK_OFFSET = 43
HORSE_BLOCK_LENGTH = 8
HORSE_SLOT_COUNT = 18


@dataclass(frozen=True)
class LocalEntry:
    name: str
    data: bytes


def _decode_name(raw: bytes, utf8: bool) -> str:
    encoding = "utf-8" if utf8 else "cp932"
    return raw.decode(encoding, errors="replace")


def read_local_entries(path: Path) -> list[LocalEntry]:
    """Read the concatenated ZIP local-file entries used by the observed RTDs."""
    blob = path.read_bytes()
    entries: list[LocalEntry] = []
    pos = 0

    while pos + 30 <= len(blob):
        signature = struct.unpack_from("<I", blob, pos)[0]
        if signature != LOCAL_FILE_SIGNATURE:
            break

        flags, method = struct.unpack_from("<HH", blob, pos + 6)
        compressed_size = struct.unpack_from("<I", blob, pos + 18)[0]
        name_length, extra_length = struct.unpack_from("<HH", blob, pos + 26)
        name_start = pos + 30
        data_start = name_start + name_length + extra_length
        data_end = data_start + compressed_size
        if data_end > len(blob):
            raise ValueError(f"truncated local entry at byte {pos}")
        if flags & 0x0008:
            raise ValueError(
                "ZIP data-descriptor entries are outside this probe's observed format"
            )

        name = _decode_name(
            blob[name_start : name_start + name_length], bool(flags & 0x0800)
        )
        compressed = blob[data_start:data_end]
        if method == STORED:
            data = compressed
        elif method == DEFLATED:
            data = zlib.decompress(compressed, -zlib.MAX_WBITS)
        else:
            raise ValueError(f"unsupported ZIP compression method {method}")

        entries.append(LocalEntry(name=name, data=data))
        pos = data_end

    if not entries:
        raise ValueError("no ZIP local-file entries found")
    return entries


def body_from_entry(entry: LocalEntry) -> bytes:
    return entry.data.removesuffix(b"\r\n")


def ascii_field(body: bytes, start: int, length: int) -> str:
    return body[start : start + length].decode("ascii", errors="replace")


def composed_race_key(body: bytes) -> str:
    # The YYYYMMDDJJRR key is not contiguous in the observed record.
    return (
        ascii_field(body, 11, 8)
        + ascii_field(body, 19, 2)
        + ascii_field(body, 25, 2)
    )


def print_candidates(records: list[tuple[LocalEntry, bytes]]) -> None:
    print("O1 candidates")
    print("index  entry                              bytes  race_key      timestamp")
    for index, (entry, body) in enumerate(records):
        timestamp = ascii_field(body, 27, 8) if len(body) >= 35 else "<short>"
        race_key = composed_race_key(body) if len(body) >= 27 else "<short>"
        print(f"{index:5d}  {entry.name:<33.33}  {len(body):5d}  {race_key:<12}  {timestamp}")


def print_record(index: int, entry: LocalEntry, body: bytes) -> None:
    print()
    print(f"Selected record: index={index}, entry={entry.name}")
    print(f"body_length={len(body)} (expected observed O1 length={O1_BODY_LENGTH})")
    print("Offsets are zero-based byte offsets; end is exclusive.")
    print()
    print("Header candidates")
    fields = [
        (0, 2, "record_id"),
        (2, 1, "record_subtype_unknown"),
        (3, 8, "date_1_semantics_unconfirmed"),
        (11, 8, "race_date"),
        (19, 2, "track_code"),
        (21, 2, "meeting_number_candidate"),
        (23, 2, "meeting_day_candidate"),
        (25, 2, "race_number"),
        (27, 8, "announcement_MMDDHHmm"),
        (35, 8, "header_unknown"),
    ]
    for start, length, label in fields:
        raw = ascii_field(body, start, length)
        print(f"[{start:03d}:{start + length:03d}] {label:<30} raw={raw!r}")
    print(f"composed YYYYMMDDJJRR race_key={composed_race_key(body)!r}")

    print()
    print("Win-odds slot candidates")
    print("slot block     horse_raw odds_raw decoded_odds tail_raw")
    for slot in range(1, HORSE_SLOT_COUNT + 1):
        start = HORSE_BLOCK_OFFSET + (slot - 1) * HORSE_BLOCK_LENGTH
        block = body[start : start + HORSE_BLOCK_LENGTH]
        horse_raw = ascii_field(body, start, 2)
        odds_raw = ascii_field(body, start + 2, 4)
        tail_raw = ascii_field(body, start + 6, 2)
        if block == b" " * HORSE_BLOCK_LENGTH:
            decoded = "<unused-slot>"
        elif odds_raw.isdigit() and odds_raw != "0000":
            decoded = f"{int(odds_raw) / 10:.1f}"
        elif odds_raw == "0000":
            decoded = "<no-displayed-odds>"
        else:
            decoded = "<unparsed>"
        print(
            f"{slot:4d} [{start:03d}:{start + 8:03d}] "
            f"{horse_raw!r:>9} {odds_raw!r:>8} {decoded:>18} {tail_raw!r:>8}"
        )
    print("Note: tail_raw is deliberately not named; it is not formally identified.")


def normalize_timestamp(value: str) -> str:
    value = value.strip().replace(":", "")
    if len(value) == 4 and value.isdigit():
        return value
    if len(value) == 8 and value.isdigit():
        return value
    raise argparse.ArgumentTypeError("timestamp must be HHmm, HH:mm, or MMDDHHmm")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rtd", type=Path, help="0B41 RTD file to inspect")
    parser.add_argument(
        "--timestamp",
        type=normalize_timestamp,
        help="select HHmm/HH:mm or MMDDHHmm; default is the last O1 record",
    )
    parser.add_argument(
        "--index", type=int, help="select a zero-based O1 candidate index"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        entries = read_local_entries(args.rtd)
        records = [
            (entry, body_from_entry(entry))
            for entry in entries
            if body_from_entry(entry).startswith(b"O1")
        ]
        if not records:
            raise ValueError("no O1 records found")
        print_candidates(records)

        if args.index is not None:
            selected_index = args.index
        elif args.timestamp is not None:
            matches = []
            for index, (_, body) in enumerate(records):
                raw = ascii_field(body, 27, 8)
                if raw == args.timestamp or raw.endswith(args.timestamp):
                    matches.append(index)
            if len(matches) != 1:
                raise ValueError(
                    f"timestamp matched {len(matches)} records (expected exactly one)"
                )
            selected_index = matches[0]
        else:
            selected_index = len(records) - 1

        if selected_index < 0 or selected_index >= len(records):
            raise IndexError(f"record index out of range: {selected_index}")
        entry, body = records[selected_index]
        print_record(selected_index, entry, body)
        return 0
    except (OSError, ValueError, IndexError, zlib.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
