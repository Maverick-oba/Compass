#!/usr/bin/env python3
"""Incrementally build confirmed C3 race results from PC-KEIBA PostgreSQL.

The C3 population is defined by c3_snapshot_manifest.csv. PostgreSQL is used
through a read-only session. Confirmed rows are skipped on later runs, while
PENDING and ERROR rows are checked again. No odds archive is modified.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable


TRACK_NAMES = {"42": "浦和", "43": "船橋", "44": "大井", "45": "川崎"}
FINAL_STATUSES = {"FINAL", "FINAL_SPECIAL"}

OUTPUT_COLUMNS = [
    "race_date", "venue_code", "venue_name", "race_no", "race_key",
    "race_name", "class_name", "field_size",
    "first_horse_no", "second_horse_no", "first_horse_nos", "second_horse_nos",
    "first_popularity", "second_popularity",
    "quinella_pair_1", "quinella_payout", "quinella_popularity_1",
    "quinella_pair_2", "quinella_payout_2", "quinella_popularity_2",
    "quinella_pair_3", "quinella_payout_3", "quinella_popularity_3",
    "quinella_payout_count", "dead_heat_flag",
    "fuseiritsu_flag_umaren", "tokubarai_flag_umaren", "henkan_flag_umaren",
    "refund_horse_info", "hr_data_kubun", "hr_data_created_date",
    "special_case_flag", "result_status", "result_retrieved_at",
]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def atomic_write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", prefix=path.name + ".",
            suffix=".tmp", dir=path.parent, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    return {column: row.get(column, "") for column in OUTPUT_COLUMNS}


def decode_hex(value: str) -> str:
    if not value:
        return ""
    return bytes.fromhex(value).decode("utf-8")


def clean_number(value: str) -> str:
    value = value.strip()
    if not value or not value.isdigit():
        return ""
    return str(int(value))


def clean_horse(value: str) -> str:
    return clean_number(value)


def split_pipe(value: str) -> list[str]:
    return [item for item in (part.strip() for part in value.split("|")) if item]


def manifest_race_keys(path: Path) -> list[str]:
    rows = read_csv_rows(path)
    keys = {row.get("race_id", "").strip() for row in rows}
    bad = sorted(key for key in keys if key and not re.fullmatch(r"\d{12}", key))
    if bad:
        raise ValueError(f"invalid race_id in manifest: {bad[0]}")
    result = sorted(key for key in keys if key)
    if not result:
        raise ValueError(f"no C3 race_id found in manifest: {path}")
    return result


def query_results(race_keys: list[str], psql_path: Path) -> dict[str, list[str]]:
    if not race_keys:
        return {}
    pgpass = Path(os.environ.get("APPDATA", "")) / "postgresql" / "pgpass.conf"
    if not psql_path.is_file():
        raise FileNotFoundError(f"psql not found: {psql_path}")
    if not pgpass.is_file():
        raise FileNotFoundError(f"PostgreSQL password file not found: {pgpass}")
    values_sql = ",".join(f"('{key}')" for key in race_keys)
    trim_finish = "btrim(s.kakutei_chakujun, chr(32)||chr(12288))"
    trim_horse = "btrim(s.umaban, chr(32)||chr(12288))"
    sql = f"""
WITH wanted(race_key) AS (VALUES {values_sql}),
se_agg AS (
  SELECT s.kaisai_nen||s.kaisai_tsukihi||s.keibajo_code||s.race_bango AS race_key,
         string_agg({trim_horse}, '|' ORDER BY ({trim_horse})::integer)
           FILTER (WHERE {trim_finish}='01') AS first_horses,
         string_agg({trim_horse}, '|' ORDER BY ({trim_horse})::integer)
           FILTER (WHERE {trim_finish}='02') AS second_horses,
         string_agg(COALESCE(btrim(s.tansho_ninkijun, chr(32)||chr(12288)),''), '|'
                    ORDER BY ({trim_horse})::integer)
           FILTER (WHERE {trim_finish}='01') AS first_popularities,
         string_agg(COALESCE(btrim(s.tansho_ninkijun, chr(32)||chr(12288)),''), '|'
                    ORDER BY ({trim_horse})::integer)
           FILTER (WHERE {trim_finish}='02') AS second_popularities,
         count(*) FILTER (WHERE {trim_finish}='01') AS first_count,
         count(*) FILTER (WHERE {trim_finish}='02') AS second_count,
         count(*) FILTER (
           WHERE COALESCE(btrim(s.dochaku_kubun, chr(32)||chr(12288)),'') NOT IN ('','0')
         ) AS dead_heat_marked_count
  FROM public.nvd_se s
  JOIN wanted w ON w.race_key=s.kaisai_nen||s.kaisai_tsukihi||s.keibajo_code||s.race_bango
  GROUP BY 1
)
SELECT w.race_key,
       CASE WHEN r.kaisai_nen IS NULL THEN '0' ELSE '1' END,
       COALESCE(encode(convert_to(COALESCE(r.kyosomei_hondai,''),'UTF8'),'hex'),''),
       COALESCE(encode(convert_to(COALESCE(r.kyoso_joken_meisho,''),'UTF8'),'hex'),''),
       COALESCE(btrim(r.shusso_tosu, chr(32)||chr(12288)),''),
       COALESCE(se.first_horses,''), COALESCE(se.second_horses,''),
       COALESCE(se.first_popularities,''), COALESCE(se.second_popularities,''),
       COALESCE(se.first_count,0), COALESCE(se.second_count,0),
       COALESCE(se.dead_heat_marked_count,0),
       COALESCE(btrim(h.data_kubun, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.data_sakusei_nengappi, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.fuseiritsu_flag_umaren, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.tokubarai_flag_umaren, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.henkan_flag_umaren, chr(32)||chr(12288)),''),
       COALESCE(encode(convert_to(COALESCE(h.henkan_umaban_joho,''),'UTF8'),'hex'),''),
       COALESCE(btrim(h.haraimodoshi_umaren_1a, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_1b, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_1c, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_2a, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_2b, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_2c, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_3a, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_3b, chr(32)||chr(12288)),''),
       COALESCE(btrim(h.haraimodoshi_umaren_3c, chr(32)||chr(12288)),'')
FROM wanted w
LEFT JOIN public.nvd_ra r
  ON w.race_key=r.kaisai_nen||r.kaisai_tsukihi||r.keibajo_code||r.race_bango
LEFT JOIN se_agg se ON se.race_key=w.race_key
LEFT JOIN public.nvd_hr h
  ON w.race_key=h.kaisai_nen||h.kaisai_tsukihi||h.keibajo_code||h.race_bango
ORDER BY w.race_key;
""".strip()
    environment = os.environ.copy()
    environment["PGPASSFILE"] = str(pgpass)
    environment["PGOPTIONS"] = "-c default_transaction_read_only=on"
    environment["PGCLIENTENCODING"] = "UTF8"
    completed = subprocess.run(
        [str(psql_path), "-X", "-w", "-h", "localhost", "-p", "5432",
         "-U", "postgres", "-d", "pckeiba", "-At", "-F", "\t", "-c", sql],
        check=False, capture_output=True, text=True, encoding="utf-8", errors="strict",
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"psql exited with {completed.returncode}")
    result: dict[str, list[str]] = {}
    for line in completed.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 27:
            raise RuntimeError(f"unexpected PostgreSQL column count: {len(parts)}")
        result[parts[0]] = parts
    return result


def build_row(parts: list[str], previous: dict[str, str] | None) -> dict[str, str]:
    race_key = parts[0]
    race_date, venue_code, race_no = race_key[:8], race_key[8:10], race_key[10:12]
    first_horses, second_horses = split_pipe(parts[5]), split_pipe(parts[6])
    first_pops, second_pops = split_pipe(parts[7]), split_pipe(parts[8])
    first_count, second_count, dead_heat_count = map(int, parts[9:12])
    hr_data_kubun = parts[12]
    payout_raw = [parts[18:21], parts[21:24], parts[24:27]]
    payouts: list[tuple[str, str, str]] = []
    for pair, payout, popularity in payout_raw:
        if pair.strip() or payout.strip() or popularity.strip():
            payouts.append((pair.strip(), clean_number(payout), clean_number(popularity)))

    special: list[str] = []
    if len(payouts) > 1:
        special.append("MULTIPLE_QUINELLA_PAYOUTS")
    if first_count > 1:
        special.append("MULTIPLE_FIRST_PLACE")
    if second_count > 1:
        special.append("MULTIPLE_SECOND_PLACE")
    if dead_heat_count:
        special.append("DEAD_HEAT_MARKER_PRESENT")
    for value, label in (
        (parts[14], "FUSEIRITSU_FLAG"),
        (parts[15], "TOKUBARAI_FLAG"),
        (parts[16], "HENKAN_FLAG"),
    ):
        if value not in ("", "0"):
            special.append(label)

    if parts[1] != "1":
        status = "ERROR"
        special.append("RACE_NOT_FOUND_IN_NVD_RA")
    elif hr_data_kubun != "2":
        status = "PENDING"
    else:
        if not payouts:
            special.append("NO_QUINELLA_PAYOUT")
        if first_count == 0:
            special.append("NO_FIRST_PLACE_RECORD")
        if second_count == 0:
            special.append("NO_SECOND_PLACE_RECORD")
        status = "FINAL_SPECIAL" if special else "FINAL"

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    row = {column: "" for column in OUTPUT_COLUMNS}
    row.update({
        "race_date": f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}",
        "venue_code": venue_code,
        "venue_name": TRACK_NAMES.get(venue_code, ""),
        "race_no": str(int(race_no)),
        "race_key": race_key,
        "race_name": decode_hex(parts[2]),
        "class_name": decode_hex(parts[3]),
        "field_size": clean_number(parts[4]),
        "first_horse_no": clean_horse(first_horses[0]) if len(first_horses) == 1 else "",
        "second_horse_no": clean_horse(second_horses[0]) if len(second_horses) == 1 else "",
        "first_horse_nos": "|".join(clean_horse(item) for item in first_horses),
        "second_horse_nos": "|".join(clean_horse(item) for item in second_horses),
        "first_popularity": clean_number(first_pops[0]) if len(first_pops) == 1 else "",
        "second_popularity": clean_number(second_pops[0]) if len(second_pops) == 1 else "",
        "quinella_payout_count": str(len(payouts)),
        "dead_heat_flag": "1" if dead_heat_count else "0",
        "fuseiritsu_flag_umaren": parts[14],
        "tokubarai_flag_umaren": parts[15],
        "henkan_flag_umaren": parts[16],
        "refund_horse_info": decode_hex(parts[17]),
        "hr_data_kubun": hr_data_kubun,
        "hr_data_created_date": parts[13],
        "special_case_flag": "|".join(special),
        "result_status": status,
        "result_retrieved_at": now,
    })
    for index in range(3):
        pair, payout, popularity = payout_raw[index]
        slot = index + 1
        row[f"quinella_pair_{slot}"] = pair.strip()
        row["quinella_payout" if slot == 1 else f"quinella_payout_{slot}"] = clean_number(payout)
        row[f"quinella_popularity_{slot}"] = clean_number(popularity)

    if previous is not None:
        prior = normalize_row(previous)
        comparison_columns = [column for column in OUTPUT_COLUMNS if column != "result_retrieved_at"]
        if all(prior[column] == row[column] for column in comparison_columns):
            row["result_retrieved_at"] = prior["result_retrieved_at"]
    return row


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=root / "analysis" / "c3_odds_research" / "c3_snapshot_manifest.csv",
    )
    parser.add_argument(
        "--output", type=Path,
        default=root / "analysis" / "c3_odds_research" / "c3_race_results.csv",
    )
    parser.add_argument(
        "--psql-path", type=Path,
        default=Path(r"C:\Program Files\PostgreSQL\16\bin\psql.exe"),
    )
    args = parser.parse_args()

    try:
        population = manifest_race_keys(args.manifest)
        existing_rows = read_csv_rows(args.output)
        existing: dict[str, dict[str, str]] = {}
        for row in existing_rows:
            key = row.get("race_key", "")
            if not re.fullmatch(r"\d{12}", key):
                raise ValueError(f"invalid race_key in existing results: {key!r}")
            if key in existing:
                raise ValueError(f"duplicate race_key in existing results: {key}")
            existing[key] = normalize_row(row)

        query_keys = [
            key for key in population
            if key not in existing or existing[key].get("result_status") not in FINAL_STATUSES
        ]
        queried = query_results(query_keys, args.psql_path)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1

    result = {key: normalize_row(row) for key, row in existing.items() if key in population}
    counts = {name: 0 for name in ("NEW", "UPDATED", "SKIPPED", "FINAL", "FINAL_SPECIAL", "PENDING", "ERROR")}
    errors: list[str] = []
    for key in population:
        previous = existing.get(key)
        if previous is not None and previous.get("result_status") in FINAL_STATUSES:
            counts["SKIPPED"] += 1
            print(f"SKIPPED {key} status={previous['result_status']}")
            continue
        parts = queried.get(key)
        if parts is None:
            counts["ERROR"] += 1
            errors.append(f"{key}: no row returned by PostgreSQL")
            print(f"ERROR {key}: no row returned by PostgreSQL")
            continue
        try:
            row = build_row(parts, previous)
            result[key] = row
            action = "NEW" if previous is None else (
                "SKIPPED" if normalize_row(previous) == row else "UPDATED"
            )
            counts[action] += 1
            counts[row["result_status"]] += 1
            print(f"{action} {key} status={row['result_status']}")
        except (UnicodeError, ValueError) as exc:
            counts["ERROR"] += 1
            errors.append(f"{key}: {exc}")
            print(f"ERROR {key}: {exc}")

    output_rows = [result[key] for key in sorted(result)]
    normalized_existing = [normalize_row(row) for row in sorted(existing_rows, key=lambda row: row.get("race_key", ""))]
    changed = output_rows != normalized_existing or not args.output.exists()
    try:
        if changed:
            atomic_write_csv(args.output, output_rows)
    except OSError as exc:
        print(f"FATAL: output write failed: {exc}", file=sys.stderr)
        return 1

    totals = {status: 0 for status in ("FINAL", "FINAL_SPECIAL", "PENDING", "ERROR")}
    for row in output_rows:
        status = row.get("result_status", "ERROR")
        totals[status if status in totals else "ERROR"] += 1

    print("\nC3 Race Results Dataset\n")
    print(f"Manifest races: {len(population)}")
    for label in ("NEW", "UPDATED", "SKIPPED"):
        print(f"{label + ':':<16}{counts[label]}")
    print(f"Confirmed:      {totals['FINAL'] + totals['FINAL_SPECIAL']}")
    print(f"  FINAL:        {totals['FINAL']}")
    print(f"  SPECIAL:      {totals['FINAL_SPECIAL']}")
    print(f"PENDING:        {totals['PENDING']}")
    print(f"ERROR:          {totals['ERROR'] + len(errors)}")
    print(f"CSV rows:       {len(output_rows)}")
    print(f"CSV changed:    {'YES' if changed else 'NO'}")
    print(f"Output:         {args.output}")
    if errors:
        print("\nErrors:")
        for message in errors:
            print(f"- {message}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
