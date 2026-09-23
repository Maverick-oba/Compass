#!/usr/bin/env python3
"""Incrementally build C3 T-minus research CSVs from the local RTD archive.

The archive is read-only. Race conditions and post times are read from
PC-KEIBA public.nvd_ra through a read-only PostgreSQL session. RTD parsing is
delegated to decode_local_odds_archive.py.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from decode_local_odds_archive import DEFAULT_TARGETS, TRACK_NAMES_JA, Snapshot, read_snapshots


SUPPORTED_TRACKS = {"42", "43", "44", "45"}
SELECTION_RULE = "strict_prior_minute_latest_record"
TERMINAL_STATUSES = {"C3", "NON-C3"}

O1_OUTPUT_COLUMNS = [
    "race_date", "track_code", "track_name", "race_no", "race_id",
    "class_name", "post_time", "target_minutes_before", "target_datetime",
    "selected_snapshot_time", "lag_seconds", "horse_no", "win_odds", "raw_odds",
]
O2_OUTPUT_COLUMNS = [
    "race_date", "track_code", "track_name", "race_no", "race_id",
    "class_name", "post_time", "target_minutes_before", "target_datetime",
    "selected_snapshot_time", "lag_seconds", "horse_no_1", "horse_no_2",
    "quinella_odds", "raw_odds",
]
MANIFEST_COLUMNS = [
    "race_date", "track_code", "track_name", "race_no", "race_id",
    "class_name", "post_time", "dataspec", "target_minutes_before",
    "target_datetime", "selected_snapshot_time", "lag_seconds",
    "selection_status", "row_count", "same_minute_conflict_count",
    "selected_record_ordinal", "raw_snapshot_count_at_selected_minute",
    "selection_rule",
]
PROCESSED_COLUMNS = [
    "race_id", "race_date", "track_code", "race_no", "o1_latest_hash",
    "o2_latest_hash", "processed_at", "status",
]


@dataclass(frozen=True)
class ArchiveRace:
    race_id: str
    race_date: str
    track_code: str
    race_no: str
    race_dir: Path
    o1_paths: tuple[Path, ...]
    o2_paths: tuple[Path, ...]
    o1_hash: str
    o2_hash: str


@dataclass(frozen=True)
class RaceInfo:
    class_name: str
    post_time: str
    post_datetime: datetime


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rtd_set_hash(paths: Iterable[Path]) -> str:
    """Fingerprint every RTD so additions and any content change are detected."""
    path_list = sorted(paths, key=lambda item: item.name)
    digest = hashlib.sha256()
    for path in path_list:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(path.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest().upper() if path_list else ""


def discover_archive_races(archive_root: Path) -> list[ArchiveRace]:
    races: list[ArchiveRace] = []
    if not archive_root.is_dir():
        raise FileNotFoundError(f"archive directory not found: {archive_root}")
    for date_dir in sorted(path for path in archive_root.iterdir() if path.is_dir()):
        if not re.fullmatch(r"\d{8}", date_dir.name):
            continue
        for track_dir in sorted(path for path in date_dir.iterdir() if path.is_dir()):
            if track_dir.name not in SUPPORTED_TRACKS:
                continue
            for race_dir in sorted(path for path in track_dir.iterdir() if path.is_dir()):
                match = re.fullmatch(r"(\d{1,2})R", race_dir.name, re.IGNORECASE)
                if not match:
                    continue
                race_no = f"{int(match.group(1)):02d}"
                o1_paths = tuple(sorted((race_dir / "0B41").glob("*.rtd")))
                o2_paths = tuple(sorted((race_dir / "0B42").glob("*.rtd")))
                race_id = date_dir.name + track_dir.name + race_no
                races.append(
                    ArchiveRace(
                        race_id=race_id,
                        race_date=date_dir.name,
                        track_code=track_dir.name,
                        race_no=race_no,
                        race_dir=race_dir,
                        o1_paths=o1_paths,
                        o2_paths=o2_paths,
                        o1_hash=rtd_set_hash(o1_paths),
                        o2_hash=rtd_set_hash(o2_paths),
                    )
                )
    return races


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def atomic_write_csv(path: Path, rows: Iterable[dict[str, str]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", prefix=path.name + ".",
            suffix=".tmp", dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(list(rows))
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def query_race_info(races: list[ArchiveRace], psql_path: Path) -> dict[str, RaceInfo]:
    if not races:
        return {}
    pgpass = Path(os.environ.get("APPDATA", "")) / "postgresql" / "pgpass.conf"
    if not psql_path.is_file():
        raise FileNotFoundError(f"psql not found: {psql_path}")
    if not pgpass.is_file():
        raise FileNotFoundError(f"PostgreSQL password file not found: {pgpass}")

    first_date = min(race.race_date for race in races)
    last_date = max(race.race_date for race in races)
    track_sql = ",".join(f"'{code}'" for code in sorted(SUPPORTED_TRACKS))
    sql = f"""
SELECT DISTINCT ON (kaisai_nen,kaisai_tsukihi,keibajo_code,race_bango)
       kaisai_nen||kaisai_tsukihi,keibajo_code,race_bango,
       COALESCE(kyoso_joken_meisho,''),hasso_jikoku
FROM public.nvd_ra
WHERE (kaisai_nen||kaisai_tsukihi) BETWEEN '{first_date}' AND '{last_date}'
  AND keibajo_code IN ({track_sql})
ORDER BY kaisai_nen,kaisai_tsukihi,keibajo_code,race_bango,
         data_sakusei_nengappi DESC NULLS LAST;
""".strip()

    environment = os.environ.copy()
    environment["PGPASSFILE"] = str(pgpass)
    environment["PGOPTIONS"] = "-c default_transaction_read_only=on"
    environment["PGCLIENTENCODING"] = "UTF8"
    completed = subprocess.run(
        [str(psql_path), "-X", "-w", "-h", "localhost", "-p", "5432",
         "-U", "postgres", "-d", "pckeiba", "-At", "-F", "\t", "-c", sql],
        check=False, capture_output=True, text=True, encoding="utf-8",
        errors="strict", env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"psql exited with {completed.returncode}")

    wanted = {race.race_id for race in races}
    result: dict[str, RaceInfo] = {}
    for line in completed.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        race_date, track_code, race_raw, class_name, post_raw = parts
        try:
            race_no = f"{int(race_raw):02d}"
        except ValueError:
            continue
        race_id = race_date + track_code + race_no
        if race_id not in wanted or not re.fullmatch(r"\d{4}", post_raw):
            continue
        post_datetime = datetime.strptime(race_date + post_raw, "%Y%m%d%H%M")
        result[race_id] = RaceInfo(
            class_name=class_name,
            post_time=post_datetime.strftime("%H:%M"),
            post_datetime=post_datetime,
        )
    return result


def is_explicit_c3(class_name: str) -> bool:
    return "C3" in unicodedata.normalize("NFKC", class_name).upper()


def select_race_rows(
    race: ArchiveRace, info: RaceInfo
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    snapshots = read_snapshots([race.race_dir])
    groups: dict[str, list[Snapshot]] = {"0B41": [], "0B42": []}
    for snapshot in snapshots:
        if snapshot.race_id != race.race_id:
            raise ValueError(
                f"RTD race_id mismatch: expected {race.race_id}, got {snapshot.race_id}"
            )
        if snapshot.dataspec in groups:
            groups[snapshot.dataspec].append(snapshot)
    if not groups["0B41"] or not groups["0B42"]:
        raise ValueError("both 0B41 and 0B42 snapshots are required")

    o1_rows: list[dict[str, str]] = []
    o2_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []
    common = {
        "race_date": race.race_date,
        "track_code": race.track_code,
        "track_name": TRACK_NAMES_JA.get(race.track_code, ""),
        "race_no": race.race_no,
        "race_id": race.race_id,
        "class_name": info.class_name,
        "post_time": info.post_time,
    }

    for dataspec in ("0B41", "0B42"):
        group = groups[dataspec]
        for minutes in DEFAULT_TARGETS:
            target_dt = info.post_datetime - timedelta(minutes=minutes)
            eligible = [snap for snap in group if snap.snapshot_dt < target_dt]
            manifest = {
                **common,
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
                "selection_rule": SELECTION_RULE,
            }
            if not eligible:
                manifest_rows.append(manifest)
                continue
            selected_minute = max(snap.snapshot_dt for snap in eligible)
            same_minute = sorted(
                (snap for snap in eligible if snap.snapshot_dt == selected_minute),
                key=lambda snap: snap.source_ordinal,
            )
            selected = same_minute[-1]
            lag_seconds = int((target_dt - selected.snapshot_dt).total_seconds())
            selected_rows = [
                {
                    **row,
                    **common,
                    "target_minutes_before": str(minutes),
                    "target_datetime": target_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "selected_snapshot_time": selected.snapshot_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "lag_seconds": str(lag_seconds),
                }
                for row in selected.rows
            ]
            (o1_rows if dataspec == "0B41" else o2_rows).extend(selected_rows)
            manifest.update(
                {
                    "selected_snapshot_time": selected.snapshot_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "lag_seconds": str(lag_seconds),
                    "selection_status": "selected_strict_prior_minute",
                    "row_count": str(len(selected_rows)),
                    "same_minute_conflict_count": str(max(0, len(same_minute) - 1)),
                    "selected_record_ordinal": str(len(same_minute)),
                    "raw_snapshot_count_at_selected_minute": str(len(same_minute)),
                }
            )
            manifest_rows.append(manifest)
    return o1_rows, o2_rows, manifest_rows


def replace_race_rows(
    existing: list[dict[str, str]], race_id: str, replacement: list[dict[str, str]]
) -> list[dict[str, str]]:
    return [row for row in existing if row.get("race_id") != race_id] + replacement


def validate_unique(rows: list[dict[str, str]], kind: str) -> None:
    seen: set[tuple[str, ...]] = set()
    for row in rows:
        if kind == "o1":
            key = (row.get("race_id", ""), row.get("target_minutes_before", ""), row.get("horse_no", ""))
        else:
            key = (
                row.get("race_id", ""), row.get("target_minutes_before", ""),
                row.get("horse_no_1", ""), row.get("horse_no_2", ""),
            )
        if key in seen:
            raise ValueError(f"duplicate {kind.upper()} output key: {key}")
        seen.add(key)


def sort_rows(rows: list[dict[str, str]], kind: str) -> list[dict[str, str]]:
    target_order = {str(value): index for index, value in enumerate(DEFAULT_TARGETS)}
    if kind == "o1":
        return sorted(rows, key=lambda row: (
            row.get("race_id", ""), target_order.get(row.get("target_minutes_before", ""), 999),
            int(row.get("horse_no") or 0),
        ))
    return sorted(rows, key=lambda row: (
        row.get("race_id", ""), target_order.get(row.get("target_minutes_before", ""), 999),
        int(row.get("horse_no_1") or 0), int(row.get("horse_no_2") or 0),
    ))


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, default=root / "archive")
    parser.add_argument("--output-dir", type=Path, default=root / "analysis" / "c3_odds_research")
    parser.add_argument(
        "--psql-path", type=Path,
        default=Path(r"C:\Program Files\PostgreSQL\16\bin\psql.exe"),
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    paths = {
        "o1": output_dir / "c3_o1_tminus_all.csv",
        "o2": output_dir / "c3_o2_tminus_all.csv",
        "manifest": output_dir / "c3_snapshot_manifest.csv",
        "processed": output_dir / "processed_races.csv",
    }
    counts = {name: 0 for name in ("NEW", "UPDATED", "SKIPPED", "C3", "NON-C3", "ERROR")}
    errors: list[str] = []
    try:
        races = discover_archive_races(args.archive_root)
        race_info = query_race_info(races, args.psql_path)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1

    o1_rows = read_csv_rows(paths["o1"])
    o2_rows = read_csv_rows(paths["o2"])
    manifest_rows = read_csv_rows(paths["manifest"])
    processed_rows = read_csv_rows(paths["processed"])
    processed = {row.get("race_id", ""): row for row in processed_rows if row.get("race_id")}
    dataset_changed = False
    processed_changed = False

    for race in races:
        previous = processed.get(race.race_id)
        unchanged = (
            previous is not None
            and previous.get("o1_latest_hash") == race.o1_hash
            and previous.get("o2_latest_hash") == race.o2_hash
            and previous.get("status") in TERMINAL_STATUSES
        )
        if unchanged:
            counts["SKIPPED"] += 1
            print(f"SKIPPED {race.race_id}")
            continue

        change_label = "NEW" if previous is None else "UPDATED"
        counts[change_label] += 1
        print(f"{change_label} {race.race_id}")
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        status = "ERROR"
        info = race_info.get(race.race_id)
        try:
            if not race.o1_paths or not race.o2_paths:
                raise ValueError("both 0B41 and 0B42 RTD sets are required")
            if info is None:
                raise ValueError("race condition/post time not found in public.nvd_ra")
            if is_explicit_c3(info.class_name):
                new_o1, new_o2, new_manifest = select_race_rows(race, info)
                o1_rows = replace_race_rows(o1_rows, race.race_id, new_o1)
                o2_rows = replace_race_rows(o2_rows, race.race_id, new_o2)
                manifest_rows = replace_race_rows(manifest_rows, race.race_id, new_manifest)
                dataset_changed = True
                status = "C3"
                counts["C3"] += 1
                print(f"C3 {race.race_id} class={info.class_name.strip()}")
            else:
                before = (len(o1_rows), len(o2_rows), len(manifest_rows))
                o1_rows = replace_race_rows(o1_rows, race.race_id, [])
                o2_rows = replace_race_rows(o2_rows, race.race_id, [])
                manifest_rows = replace_race_rows(manifest_rows, race.race_id, [])
                dataset_changed = dataset_changed or before != (len(o1_rows), len(o2_rows), len(manifest_rows))
                status = "NON-C3"
                counts["NON-C3"] += 1
                print(f"NON-C3 {race.race_id} class={info.class_name.strip()}")
        except (OSError, ValueError) as exc:
            counts["ERROR"] += 1
            errors.append(f"{race.race_id}: {exc}")
            print(f"ERROR {race.race_id}: {exc}")

        processed[race.race_id] = {
            "race_id": race.race_id, "race_date": race.race_date,
            "track_code": race.track_code, "race_no": race.race_no,
            "o1_latest_hash": race.o1_hash, "o2_latest_hash": race.o2_hash,
            "processed_at": now, "status": status,
        }
        processed_changed = True

    try:
        validate_unique(o1_rows, "o1")
        validate_unique(o2_rows, "o2")
        o1_rows = sort_rows(o1_rows, "o1")
        o2_rows = sort_rows(o2_rows, "o2")
        target_order = {str(value): index for index, value in enumerate(DEFAULT_TARGETS)}
        manifest_rows = sorted(manifest_rows, key=lambda row: (
            row.get("race_id", ""), row.get("dataspec", ""),
            target_order.get(row.get("target_minutes_before", ""), 999),
        ))
        if dataset_changed or not all(paths[name].exists() for name in ("o1", "o2", "manifest")):
            atomic_write_csv(paths["o1"], o1_rows, O1_OUTPUT_COLUMNS)
            atomic_write_csv(paths["o2"], o2_rows, O2_OUTPUT_COLUMNS)
            atomic_write_csv(paths["manifest"], manifest_rows, MANIFEST_COLUMNS)
        if processed_changed or not paths["processed"].exists():
            atomic_write_csv(paths["processed"], [processed[key] for key in sorted(processed)], PROCESSED_COLUMNS)
    except (OSError, ValueError) as exc:
        print(f"FATAL: output validation/write failed: {exc}", file=sys.stderr)
        return 1

    print("\nC3 Odds Research Dataset\n")
    for label in ("NEW", "UPDATED", "SKIPPED", "C3", "NON-C3", "ERROR"):
        print(f"{label + ':':<11}{counts[label]}")
    print(f"\nO1 rows: {len(o1_rows)}")
    print(f"O2 rows: {len(o2_rows)}")
    if errors:
        print("\nErrors:")
        for message in errors:
            print(f"- {message}")
    return 0 if counts["ERROR"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
