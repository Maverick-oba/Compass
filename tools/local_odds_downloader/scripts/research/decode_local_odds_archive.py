#!/usr/bin/env python3
"""Export O1/O2 snapshots from UmaConn RTD files to vertical CSVs.

Research reader only: it reads RTD files and writes new CSV output files. It
does not call NVDTLab or modify the source RTD/archive.
"""

from __future__ import annotations

import argparse
import csv
import re
import struct
import sys
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


LOCAL_FILE_SIGNATURE = 0x04034B50
STORED = 0
DEFLATED = 8
O1_LENGTH = 960
O1_BLOCK_START = 43
O1_BLOCK_LENGTH = 8
O1_SLOTS = 18
O2_LENGTH = 2040
O2_BLOCK_START = 40
O2_BLOCK_LENGTH = 13
HORSES = 18
DEFAULT_TARGETS = (120, 90, 60, 45, 30, 15, 5)

TRACK_NAMES_JA = {
    "42": "浦和",
    "43": "船橋",
    "44": "大井",
    "45": "川崎",
}

O1_COLUMNS = [
    "race_date",
    "track_code",
    "track_name",
    "race_no",
    "race_id",
    "snapshot_time",
    "horse_no",
    "win_odds",
    "raw_odds",
]
O2_COLUMNS = [
    "race_date",
    "track_code",
    "track_name",
    "race_no",
    "race_id",
    "snapshot_time",
    "horse_no_1",
    "horse_no_2",
    "quinella_odds",
    "raw_odds",
]
TARGET_COLUMNS = [
    "target_minutes_before",
    "target_datetime",
    "selected_snapshot_time",
    "lag_seconds",
]


@dataclass(frozen=True)
class ZipEntry:
    name: str
    payload: bytes


@dataclass(frozen=True)
class Snapshot:
    dataspec: str
    race_date: str
    track_code: str
    race_no: str
    race_id: str
    snapshot_dt: datetime
    source_ordinal: int
    rows: tuple[dict[str, str], ...]
    body: bytes


def read_local_zip_entries(path: Path) -> list[ZipEntry]:
    """Read the concatenated ZIP local entries used in observed RTD files."""
    blob = path.read_bytes()
    entries: list[ZipEntry] = []
    position = 0

    while position + 30 <= len(blob):
        if struct.unpack_from("<I", blob, position)[0] != LOCAL_FILE_SIGNATURE:
            break
        flags, method = struct.unpack_from("<HH", blob, position + 6)
        compressed_size = struct.unpack_from("<I", blob, position + 18)[0]
        name_length, extra_length = struct.unpack_from("<HH", blob, position + 26)
        name_start = position + 30
        data_start = name_start + name_length + extra_length
        data_end = data_start + compressed_size
        if data_end > len(blob):
            raise ValueError(f"{path}: truncated ZIP entry at byte {position}")
        if flags & 0x0008:
            raise ValueError(f"{path}: ZIP data descriptor is unsupported")

        name_encoding = "utf-8" if flags & 0x0800 else "cp932"
        name = blob[name_start : name_start + name_length].decode(
            name_encoding, errors="replace"
        )
        compressed = blob[data_start:data_end]
        if method == STORED:
            payload = compressed
        elif method == DEFLATED:
            payload = zlib.decompress(compressed, -zlib.MAX_WBITS)
        else:
            raise ValueError(f"{path}: unsupported ZIP compression method {method}")
        entries.append(ZipEntry(name=name, payload=payload))
        position = data_end

    if not entries:
        raise ValueError(f"{path}: no ZIP local entries found")
    return entries


def body_from_entry(entry: ZipEntry) -> bytes:
    return entry.payload.removesuffix(b"\r\n")


def ascii_field(body: bytes, start: int, length: int, label: str) -> str:
    value = body[start : start + length]
    try:
        return value.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(f"non-ASCII {label} at offset {start}") from exc


def make_snapshot_time(race_date: str, raw_timestamp: str) -> datetime:
    if not re.fullmatch(r"\d{8}", race_date):
        raise ValueError(f"invalid race date {race_date!r}")
    if not re.fullmatch(r"\d{8}", raw_timestamp):
        raise ValueError(f"invalid snapshot timestamp {raw_timestamp!r}")
    # RTD announcement field is MMDDHHmm; the race date supplies the year.
    value = race_date[:4] + raw_timestamp
    try:
        return datetime.strptime(value, "%Y%m%d%H%M")
    except ValueError as exc:
        raise ValueError(f"invalid RTD timestamp {raw_timestamp!r}") from exc


def decimal_odds(raw: str, width: int, label: str) -> str:
    if raw == "-" * width:
        # The formal meaning of this marker is not confirmed. Preserve it in
        # raw_odds and expose no numeric odds instead of guessing its meaning.
        return ""
    if not re.fullmatch(rf"\d{{{width}}}", raw):
        raise ValueError(f"invalid {label} raw field {raw!r}")
    integer = int(raw)
    if integer == 0:
        return ""  # zero raw values are missing/no displayed odds, not 0.0 odds
    return f"{integer // 10}.{integer % 10}"


def base_metadata(body: bytes) -> dict[str, str | datetime]:
    if len(body) < 35:
        raise ValueError(f"record too short: {len(body)} bytes")
    record_id = ascii_field(body, 0, 2, "record_id")
    if record_id not in {"O1", "O2"}:
        raise ValueError(f"unsupported record_id {record_id!r}")
    race_date = ascii_field(body, 11, 8, "race_date")
    track_code = ascii_field(body, 19, 2, "track_code")
    race_no = ascii_field(body, 25, 2, "race_no")
    raw_timestamp = ascii_field(body, 27, 8, "snapshot_time")
    if not re.fullmatch(r"\d{2}", track_code) or not re.fullmatch(r"\d{2}", race_no):
        raise ValueError("invalid track/race code")
    race_id = race_date + track_code + race_no
    snapshot_dt = make_snapshot_time(race_date, raw_timestamp)
    return {
        "record_id": record_id,
        "race_date": race_date,
        "track_code": track_code,
        "track_name": TRACK_NAMES_JA.get(track_code, ""),
        "race_no": race_no,
        "race_id": race_id,
        "snapshot_dt": snapshot_dt,
        "snapshot_time": snapshot_dt.strftime("%Y-%m-%d %H:%M:%S"),
    }


def parse_o1(body: bytes, source_ordinal: int) -> Snapshot:
    if len(body) != O1_LENGTH:
        raise ValueError(f"O1 body length {len(body)} != {O1_LENGTH}")
    metadata = base_metadata(body)
    rows: list[dict[str, str]] = []
    for slot in range(O1_SLOTS):
        start = O1_BLOCK_START + slot * O1_BLOCK_LENGTH
        block = body[start : start + O1_BLOCK_LENGTH]
        if block == b" " * O1_BLOCK_LENGTH:
            continue
        horse_raw = ascii_field(body, start, 2, "O1 horse number")
        if not re.fullmatch(r"\d{2}", horse_raw):
            raise ValueError(f"unexpected O1 horse number {horse_raw!r} at {start}")
        odds_raw = ascii_field(body, start + 2, 4, "O1 odds")
        odds = decimal_odds(odds_raw, 4, "O1 odds")
        rows.append(
            {
                "race_date": str(metadata["race_date"]),
                "track_code": str(metadata["track_code"]),
                "track_name": str(metadata["track_name"]),
                "race_no": str(metadata["race_no"]),
                "race_id": str(metadata["race_id"]),
                "snapshot_time": str(metadata["snapshot_time"]),
                "horse_no": str(int(horse_raw)),
                "win_odds": odds,
                "raw_odds": odds_raw,
            }
        )
    return Snapshot(
        dataspec="0B41",
        race_date=str(metadata["race_date"]),
        track_code=str(metadata["track_code"]),
        race_no=str(metadata["race_no"]),
        race_id=str(metadata["race_id"]),
        snapshot_dt=metadata["snapshot_dt"],  # type: ignore[arg-type]
        source_ordinal=source_ordinal,
        rows=tuple(rows),
        body=body,
    )


def parse_o2(body: bytes, source_ordinal: int) -> Snapshot:
    if len(body) != O2_LENGTH:
        raise ValueError(f"O2 body length {len(body)} != {O2_LENGTH}")
    metadata = base_metadata(body)
    rows: list[dict[str, str]] = []
    for pair_index in range(HORSES * (HORSES - 1) // 2):
        start = O2_BLOCK_START + pair_index * O2_BLOCK_LENGTH
        block = body[start : start + O2_BLOCK_LENGTH]
        if len(block) != O2_BLOCK_LENGTH:
            raise ValueError(f"truncated O2 pair block at offset {start}")
        if block == b" " * O2_BLOCK_LENGTH:
            continue
        pair_raw = ascii_field(body, start, 4, "O2 pair numbers")
        if not re.fullmatch(r"\d{4}", pair_raw):
            raise ValueError(f"invalid O2 pair number field {pair_raw!r} at {start}")
        horse_1, horse_2 = int(pair_raw[:2]), int(pair_raw[2:])
        if not (1 <= horse_1 <= HORSES and 1 <= horse_2 <= HORSES) or horse_1 == horse_2:
            raise ValueError(f"invalid O2 horse pair {pair_raw!r} at offset {start}")
        odds_raw = ascii_field(body, start + 5, 5, "O2 odds")
        odds = decimal_odds(odds_raw, 5, "O2 odds")
        rows.append(
            {
                "race_date": str(metadata["race_date"]),
                "track_code": str(metadata["track_code"]),
                "track_name": str(metadata["track_name"]),
                "race_no": str(metadata["race_no"]),
                "race_id": str(metadata["race_id"]),
                "snapshot_time": str(metadata["snapshot_time"]),
                "horse_no_1": str(horse_1),
                "horse_no_2": str(horse_2),
                "quinella_odds": odds,
                "raw_odds": odds_raw,
            }
        )
    return Snapshot(
        dataspec="0B42",
        race_date=str(metadata["race_date"]),
        track_code=str(metadata["track_code"]),
        race_no=str(metadata["race_no"]),
        race_id=str(metadata["race_id"]),
        snapshot_dt=metadata["snapshot_dt"],  # type: ignore[arg-type]
        source_ordinal=source_ordinal,
        rows=tuple(rows),
        body=body,
    )


def discover_rtds(inputs: Iterable[Path]) -> list[Path]:
    paths: set[Path] = set()
    for source in inputs:
        if source.is_file():
            if source.suffix.lower() != ".rtd":
                raise ValueError(f"input file is not an RTD: {source}")
            paths.add(source.resolve())
        elif source.is_dir():
            paths.update(p.resolve() for p in source.rglob("*.rtd") if p.is_file())
        else:
            raise FileNotFoundError(f"input path not found: {source}")
    if not paths:
        raise ValueError("no RTD files found in input")
    return sorted(paths)


def read_snapshots(inputs: Iterable[Path]) -> list[Snapshot]:
    unique: dict[tuple[str, bytes], Snapshot] = {}
    source_ordinal = 0
    for path in discover_rtds(inputs):
        for entry in read_local_zip_entries(path):
            body = body_from_entry(entry)
            if body.startswith(b"O1"):
                source_ordinal += 1
                snapshot = parse_o1(body, source_ordinal)
            elif body.startswith(b"O2"):
                source_ordinal += 1
                snapshot = parse_o2(body, source_ordinal)
            else:
                continue
            # RTDs are cumulative. Collapse byte-identical copies while
            # retaining the last observed position for deterministic ordering.
            unique[(snapshot.dataspec, body)] = snapshot

    snapshots = sorted(
        unique.values(),
        key=lambda item: (
            item.race_date,
            item.track_code,
            item.race_no,
            item.dataspec,
            item.snapshot_dt,
            item.source_ordinal,
        ),
    )
    return snapshots


def unique_output_path(output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = Path(filename)
    candidate = output_dir / base.name
    if not candidate.exists():
        return candidate
    for suffix in range(1, 10000):
        candidate = output_dir / f"{base.stem}_{suffix:03d}{base.suffix}"
        if not candidate.exists():
            return candidate
    raise FileExistsError(f"could not allocate a new output name for {filename}")


def write_csv_new(
    output_dir: Path, filename: str, rows: Iterable[dict[str, str]], columns: list[str]
) -> Path:
    materialized = list(rows)
    for suffix in range(0, 10000):
        if suffix == 0:
            name = filename
        else:
            base = Path(filename)
            name = f"{base.stem}_{suffix:03d}{base.suffix}"
        target = output_dir / name
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("x", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(materialized)
            return target
        except FileExistsError:
            continue
    raise FileExistsError(f"could not allocate a new output name for {filename}")


def parse_post_time(value: str) -> tuple[str, datetime.time]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("post time must be RACE_ID=HH:MM")
    race_id, time_raw = value.split("=", 1)
    if not re.fullmatch(r"\d{12}", race_id):
        raise argparse.ArgumentTypeError("race id must be YYYYMMDDJJRR")
    try:
        parsed = datetime.strptime(time_raw, "%H:%M").time()
    except ValueError as exc:
        raise argparse.ArgumentTypeError("post time must be HH:MM") from exc
    return race_id, parsed


def load_schedule(path: Path | None, post_times: list[tuple[str, datetime.time]]) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
    if path is not None:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                race_id = (row.get("race_id") or row.get("race_key") or "").strip()
                post_time = (row.get("post_time") or "").strip()
                post_datetime = (row.get("post_datetime") or "").strip()
                if not race_id:
                    date = (row.get("race_date") or "").strip()
                    code = (row.get("track_code") or "").strip()
                    race = (row.get("race_no") or row.get("race") or "").strip()
                    if date and code and race:
                        race_id = date + code + f"{int(race):02d}"
                if not race_id:
                    continue
                if post_time:
                    if len(race_id) != 12:
                        raise ValueError(f"invalid race_id in schedule CSV: {race_id}")
                    value = datetime.strptime(race_id[:8] + post_time, "%Y%m%d%H:%M")
                elif post_datetime:
                    try:
                        value = datetime.fromisoformat(post_datetime)
                    except ValueError:
                        value = None
                        for date_format in (
                            "%m/%d/%Y %H:%M:%S",
                            "%m/%d/%Y %I:%M:%S %p",
                            "%Y-%m-%d %H:%M:%S",
                        ):
                            try:
                                value = datetime.strptime(post_datetime, date_format)
                                break
                            except ValueError:
                                pass
                        if value is None:
                            raise ValueError(f"unrecognized post_datetime {post_datetime!r}")
                else:
                    continue
                result[race_id] = value
    for race_id, post_clock in post_times:
        result[race_id] = datetime.combine(
            datetime.strptime(race_id[:8], "%Y%m%d").date(), post_clock
        )
    return result


def snapshot_row_count(snapshot: Snapshot) -> int:
    return len(snapshot.rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True, help="RTD file or directory; repeatable")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--schedule-csv", type=Path, help="CSV from get_race_schedule.ps1")
    parser.add_argument("--post-time", type=parse_post_time, action="append", default=[], metavar="RACE_ID=HH:MM")
    parser.add_argument("--target", type=int, choices=DEFAULT_TARGETS, action="append", help="T-minus minutes; repeatable; default: all supported targets")
    args = parser.parse_args()

    try:
        snapshots = read_snapshots(args.input)
        schedule = load_schedule(args.schedule_csv, args.post_time)
        targets = args.target if args.target else list(DEFAULT_TARGETS)
        groups: dict[tuple[str, str, str, str], list[Snapshot]] = {}
        for snap in snapshots:
            groups.setdefault(
                (snap.race_date, snap.track_code, snap.race_no, snap.dataspec), []
            ).append(snap)

        for (race_date, track_code, race_no, dataspec), group in sorted(groups.items()):
            all_rows = [row for snap in group for row in snap.rows]
            columns = O1_COLUMNS if dataspec == "0B41" else O2_COLUMNS
            suffix = "o1" if dataspec == "0B41" else "o2"
            race_id = group[0].race_id
            all_name = f"{race_date}_{track_code}_{race_no}R_{suffix}_all.csv"
            all_path = write_csv_new(args.output_dir, all_name, all_rows, columns)
            print(
                f"ALL {dataspec} race_id={race_id} snapshots={len(group)} "
                f"rows={len(all_rows)} file={all_path}"
            )

        if not schedule:
            print("T-minus extraction skipped: provide --schedule-csv or --post-time.")
            return 0

        manifest: list[dict[str, str]] = []
        selection_rule = "strict_prior_minute_latest_record"
        for (race_date, track_code, race_no, dataspec), group in sorted(groups.items()):
            race_id = group[0].race_id
            suffix = "o1" if dataspec == "0B41" else "o2"
            post_dt = schedule.get(race_id)
            if post_dt is None:
                for minutes in targets:
                    manifest.append(
                        {
                            "race_id": race_id,
                            "dataspec": dataspec,
                            "target_minutes_before": str(minutes),
                            "target_datetime": "",
                            "selected_snapshot_time": "",
                            "lag_seconds": "",
                            "selection_status": "missing_post_time",
                            "row_count": "0",
                            "same_minute_conflict_count": "0",
                            "selected_record_ordinal": "",
                            "raw_snapshot_count_at_selected_minute": "0",
                            "selection_rule": selection_rule,
                        }
                    )
                continue
            if post_dt.date() != datetime.strptime(race_date, "%Y%m%d").date():
                raise ValueError(f"schedule date mismatch for {race_id}: {post_dt}")
            for minutes in targets:
                target_dt = post_dt - timedelta(minutes=minutes)
                # Announcement timestamps have minute precision. Exclude the
                # target minute itself so a record published up to 59 seconds
                # after the true target instant can never leak into selection.
                eligible = [snap for snap in group if snap.snapshot_dt < target_dt]
                if not eligible:
                    manifest.append(
                        {
                            "race_id": race_id,
                            "dataspec": dataspec,
                            "target_minutes_before": str(minutes),
                            "target_datetime": target_dt.strftime("%Y-%m-%d %H:%M:%S"),
                            "selected_snapshot_time": "",
                            "lag_seconds": "",
                            "selection_status": "no_snapshot_strictly_before_target",
                            "row_count": "0",
                            "same_minute_conflict_count": "0",
                            "selected_record_ordinal": "",
                            "raw_snapshot_count_at_selected_minute": "0",
                            "selection_rule": selection_rule,
                        }
                    )
                    continue
                selected_minute = max(snap.snapshot_dt for snap in eligible)
                same_minute = sorted(
                    (snap for snap in eligible if snap.snapshot_dt == selected_minute),
                    key=lambda snap: snap.source_ordinal,
                )
                selected = same_minute[-1]
                selected_record_ordinal = len(same_minute)
                raw_snapshot_count = len(same_minute)
                same_minute_conflict_count = max(0, raw_snapshot_count - 1)
                lag_seconds = int((target_dt - selected.snapshot_dt).total_seconds())
                target_rows = [
                    {
                        **row,
                        "target_minutes_before": str(minutes),
                        "target_datetime": target_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "selected_snapshot_time": selected.snapshot_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "lag_seconds": str(lag_seconds),
                    }
                    for row in selected.rows
                ]
                columns = O1_COLUMNS if dataspec == "0B41" else O2_COLUMNS
                snapshot_columns = columns + TARGET_COLUMNS
                target_name = f"{race_date}_{track_code}_{race_no}R_{suffix}_T{minutes:03d}.csv"
                target_path = write_csv_new(args.output_dir, target_name, target_rows, snapshot_columns)
                manifest.append(
                    {
                        "race_id": race_id,
                        "dataspec": dataspec,
                        "target_minutes_before": str(minutes),
                        "target_datetime": target_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "selected_snapshot_time": selected.snapshot_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "lag_seconds": str(lag_seconds),
                        "selection_status": "selected_strict_prior_minute",
                        "row_count": str(len(target_rows)),
                        "same_minute_conflict_count": str(same_minute_conflict_count),
                        "selected_record_ordinal": str(selected_record_ordinal),
                        "raw_snapshot_count_at_selected_minute": str(raw_snapshot_count),
                        "selection_rule": selection_rule,
                    }
                )
                print(
                    f"SELECT {dataspec} race_id={race_id} T-{minutes} "
                    f"target={target_dt:%H:%M:%S} selected={selected.snapshot_dt:%H:%M:%S} "
                    f"lag_seconds={lag_seconds} ordinal={selected_record_ordinal}/"
                    f"{raw_snapshot_count} rows={len(target_rows)} file={target_path}"
                )

        manifest_columns = [
            "race_id",
            "dataspec",
            "target_minutes_before",
            "target_datetime",
            "selected_snapshot_time",
            "lag_seconds",
            "selection_status",
            "row_count",
            "same_minute_conflict_count",
            "selected_record_ordinal",
            "raw_snapshot_count_at_selected_minute",
            "selection_rule",
        ]
        manifest_path = write_csv_new(
            args.output_dir,
            "snapshot_selection_manifest.csv",
            manifest,
            manifest_columns,
        )
        print(f"MANIFEST rows={len(manifest)} file={manifest_path}")
        return 0
    except (OSError, ValueError, zlib.error, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
