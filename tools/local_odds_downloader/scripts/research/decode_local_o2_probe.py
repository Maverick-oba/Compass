#!/usr/bin/env python3
"""Inspect O2 (quinella) records in a local NVDTLab RTD file.

Research-only probe. Offsets are zero-based byte offsets in the 2040-byte O2
record body. It does not modify the RTD or any downloader data.
"""

from __future__ import annotations

import argparse
import itertools
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


LOCAL_FILE_SIGNATURE = 0x04034B50
STORED = 0
DEFLATED = 8
O2_BODY_LENGTH = 2040
PAIR_START = 40
PAIR_BLOCK_LENGTH = 13
HORSE_COUNT = 18
PAIR_COUNT = HORSE_COUNT * (HORSE_COUNT - 1) // 2
TRAILER_START = PAIR_START + PAIR_COUNT * PAIR_BLOCK_LENGTH


@dataclass(frozen=True)
class LocalEntry:
    name: str
    data: bytes


def read_local_entries(path: Path) -> list[LocalEntry]:
    blob = path.read_bytes()
    entries: list[LocalEntry] = []
    pos = 0
    while pos + 30 <= len(blob):
        if struct.unpack_from("<I", blob, pos)[0] != LOCAL_FILE_SIGNATURE:
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
            raise ValueError("ZIP data-descriptor entries are not supported by this probe")
        name_encoding = "utf-8" if flags & 0x0800 else "cp932"
        name = blob[name_start : name_start + name_length].decode(
            name_encoding, errors="replace"
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


def field(body: bytes, start: int, length: int) -> str:
    return body[start : start + length].decode("ascii", errors="replace")


def race_key(body: bytes) -> str:
    return field(body, 11, 8) + field(body, 19, 2) + field(body, 25, 2)


def timestamp_arg(value: str) -> str:
    value = value.strip().replace(":", "")
    if (len(value) == 4 or len(value) == 8) and value.isdigit():
        return value
    raise argparse.ArgumentTypeError("timestamp must be HHmm, HH:mm, or MMDDHHmm")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rtd", type=Path, help="0B42 RTD file to inspect")
    parser.add_argument("--timestamp", type=timestamp_arg)
    parser.add_argument("--index", type=int, help="zero-based O2 candidate index")
    parser.add_argument("--pair", help="show only one pair, such as 1-2")
    parser.add_argument(
        "--include-blank", action="store_true", help="also print unused pair slots"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        candidates = [
            (entry, body_from_entry(entry))
            for entry in read_local_entries(args.rtd)
            if body_from_entry(entry).startswith(b"O2")
        ]
        if not candidates:
            raise ValueError("no O2 records found")

        print("O2 candidates")
        print("index  entry                              body_bytes race_key      timestamp")
        for index, (entry, body) in enumerate(candidates):
            print(
                f"{index:5d}  {entry.name:<33.33} {len(body):9d} "
                f"{race_key(body):<12} {field(body, 27, 8)}"
            )

        if args.index is not None:
            selected = args.index
        elif args.timestamp is not None:
            matches = [
                i
                for i, (_, body) in enumerate(candidates)
                if field(body, 27, 8) == args.timestamp
                or field(body, 27, 8).endswith(args.timestamp)
            ]
            if len(matches) != 1:
                raise ValueError(f"timestamp matched {len(matches)} records; expected one")
            selected = matches[0]
        else:
            selected = len(candidates) - 1
        if selected < 0 or selected >= len(candidates):
            raise IndexError(f"candidate index out of range: {selected}")

        entry, body = candidates[selected]
        if len(body) != O2_BODY_LENGTH:
            print(f"WARNING: observed body size is {len(body)}, expected {O2_BODY_LENGTH}")
        print(f"\nSelected index={selected}, entry={entry.name}")
        print(f"body_length={len(body)}, race_key={race_key(body)}")
        print("header candidates (zero-based, end-exclusive)")
        for start, length, label in [
            (0, 2, "record_id"),
            (2, 1, "subtype_unknown"),
            (3, 8, "date_1_unknown"),
            (11, 8, "race_date_candidate"),
            (19, 2, "track_code"),
            (21, 2, "meeting_number_candidate"),
            (23, 2, "meeting_day_candidate"),
            (25, 2, "race_number"),
            (27, 8, "announcement_MMDDHHmm"),
            (35, 5, "header_tail_unknown"),
        ]:
            print(f"[{start:03d}:{start + length:03d}] {label:<28} raw={field(body, start, length)!r}")

        chosen_pair = None
        if args.pair:
            try:
                left, right = (int(x) for x in args.pair.split("-", 1))
            except (ValueError, TypeError) as exc:
                raise ValueError("--pair must look like 1-2") from exc
            chosen_pair = tuple(sorted((left, right)))
            if left == right or not (1 <= left <= HORSE_COUNT and 1 <= right <= HORSE_COUNT):
                raise ValueError("pair numbers must be different integers from 1 to 18")

        print("\npair_index block_offset pair_raw marker_raw odds_raw decoded_odds tail_raw")
        shown = 0
        for pair_index, pair in enumerate(itertools.combinations(range(1, 19), 2)):
            start = PAIR_START + pair_index * PAIR_BLOCK_LENGTH
            block = body[start : start + PAIR_BLOCK_LENGTH]
            if len(block) < PAIR_BLOCK_LENGTH:
                raise ValueError(f"truncated pair block {pair_index} at byte {start}")
            if chosen_pair is not None and pair != chosen_pair:
                continue
            if not args.include_blank and block == b" " * PAIR_BLOCK_LENGTH:
                continue
            pair_raw = field(block, 0, 4)
            marker_raw = field(block, 4, 1)
            odds_raw = field(block, 5, 5)
            tail_raw = field(block, 10, 3)
            if odds_raw.isdigit() and odds_raw != "00000":
                decoded = f"{int(odds_raw) / 10:.1f}"
            elif odds_raw == "00000":
                decoded = "<zero/no displayed odds>"
            else:
                decoded = "<blank/unparsed>"
            print(
                f"{pair_index:9d} {start:12d} {pair_raw!r:>8} "
                f"{marker_raw!r:>10} {odds_raw!r:>10} {decoded:>22} {tail_raw!r:>9}"
            )
            shown += 1
        print(f"\nprinted_pair_slots={shown}/{PAIR_COUNT}")
        print(f"pair_array_end={TRAILER_START}; trailing_raw={body[TRAILER_START:]!r}")
        print("marker_raw and tail_raw meanings remain unidentified by this probe.")
        return 0
    except (OSError, ValueError, IndexError, zlib.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
