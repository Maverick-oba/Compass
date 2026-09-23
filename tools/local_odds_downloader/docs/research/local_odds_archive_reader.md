# Local odds archive Reader

`scripts/research/decode_local_odds_archive.py` is an independent research reader for previously saved UmaConn RTD files. It does not instantiate NVDTLab, download data, or integrate with the production downloader.

## Input and outputs

Pass one or more `.rtd` files or directories with `--input`. Directory inputs are searched recursively. Identical record bodies repeated in cumulative RTD snapshots are deduplicated; conflicting records with the same dataspec, race, and snapshot time stop with an error instead of selecting arbitrarily.

For each race and dataspec, the reader writes one all-snapshots CSV:

- `YYYYMMDD_JJ_RR_o1_all.csv`
- `YYYYMMDD_JJ_RR_o2_all.csv`

Selected snapshots include the dataspec in the name to keep simultaneous O1/O2 exports distinct, for example `YYYYMMDD_JJ_RR_o1_T120.csv` and `YYYYMMDD_JJ_RR_o2_T120.csv`.

O1 columns are `race_date, track_code, track_name, race_no, race_id, snapshot_time, horse_no, win_odds`. O2 replaces the final fields with `horse_no_1, horse_no_2, quinella_odds`.

The 0B41/0B42 raw odds values `0000` / `00000` are emitted as an empty CSV cell. The reader does not interpret them as zero odds or infer a scratch/withdrawal reason. Empty fixed slots are omitted. Track names in CSV are Japanese; the configured display aliases remain `Urawa`, `Funabashi`, `Oi`, and `Kawasaki`.

## T-minus snapshots

Give the race post times using `--schedule-csv` or repeated `--post-time RACE_ID=HH:MM`. The schedule CSV accepts the `race_key`/`race_id` and `post_time` columns produced by the RACE schedule reader. T-minus choices default to 120, 90, 60, 45, 30, 15, and 5 minutes; use `--target` to choose one or more.

For each target, the reader selects the latest snapshot satisfying:

```text
snapshot_time <= post_time - target_minutes
```

It never selects a future snapshot. If no prior snapshot exists, it writes a `no_snapshot_at_or_before_target` row to `snapshot_selection_manifest.csv` and does not create an empty target file. Each selected-snapshot row carries `target_minutes_before`, `target_datetime`, `selected_snapshot_time`, and `lag_seconds`.

Output names are created exclusively. If a requested filename already exists, the reader appends `_001`, `_002`, and so on. It never opens an existing CSV for writing.

## Example

```powershell
python scripts\research\decode_local_odds_archive.py `
  --input archive\20260923\42\01R `
  --output-dir research\decoded `
  --post-time 202609234201=13:30
```

Repeat `--input` and `--post-time` to analyze multiple races. A schedule CSV can be passed instead:

```powershell
python scripts\research\decode_local_odds_archive.py `
  --input archive\20260923\42 `
  --output-dir research\decoded `
  --schedule-csv schedule_20260923.csv
```

`track_code=42` is Urawa / 浦和, `43` Funabashi / 船橋, `44` Oi / 大井, and `45` Kawasaki / 川崎. Race-key assembly is unchanged: `YYYYMMDD + JJ + RR`.

## Confirmed layout and boundaries

- O1本文960 bytes; horse blocks start at byte 43 and repeat every 8 bytes. Horse number is 2 bytes; win odds is 4 ASCII digits divided by 10.
- O2本文2040 bytes; pair slots start at byte 40 and repeat every 13 bytes. The observed first 66 slots for 12 runners are ascending horse pairs; quinella odds is 5 ASCII digits at block offset +5, divided by 10.
- O1末尾2 bytes、O2 marker and final 3 bytes, O2 combinations involving runner numbers 13–18, and scratch/withdrawal encodings remain unidentified.
- Validation used the 2026-09-23 Urawa 1R–3R RTDs and the available TAN/UMA CSV rows. The two requested `(1).CSV` 30-minute files were absent from the searched local paths, so direct validation of those file copies is still outstanding.

The research probes `decode_local_o1_probe.py` and `decode_local_o2_probe.py` display candidate raw fields for an individual RTD. These remain separate from this CSV reader and from the production downloader.

## Validation: 2026-09-23 Urawa 1R–3R

RACE post times came from the existing schedule reader's read-only `public.nvd_ra` fallback: 1R 13:30, 2R 14:00, and 3R 14:30. All RTD files under each race directory were read and exact duplicate records across cumulative archives were removed.

| Race | race_id | O1 snapshots / CSV rows | O2 snapshots / CSV rows |
|---|---|---:|---:|
| 浦和1R | `202609234201` | 33 / 396 | 33 / 2,178 |
| 浦和2R | `202609234202` | 39 / 468 | 39 / 2,574 |
| 浦和3R | `202609234203` | 43 / 516 | 46 / 3,036 |

Earliest snapshot across these files was 11:19. All 42 T-minus selections (3 races × 2 dataspecs × 7 targets) found a snapshot at or before the target; zero selections used a future snapshot. Times below are the chosen snapshot times; each generated row also carries the lag in seconds.

| Race / dataspec | T-120 | T-90 | T-60 | T-45 | T-30 | T-15 | T-5 |
|---|---|---|---|---|---|---|---|
| 浦和1R O1/O2 | 11:28 | 11:57 | 12:28 | 12:41 | 13:00 | 13:13 | 13:21 |
| 浦和2R O1/O2 | 11:57 | 12:28 | 13:00 | 13:13 | 13:29 | 13:43 | 13:51 |
| 浦和3R O1 | 12:28 | 13:00 | 13:29 | 13:43 | 13:59 | 14:10 | 14:10 |
| 浦和3R O2 | 12:28 | 13:00 | 13:29 | 13:43 | 13:59 | 14:15 | 14:22 |

No target lacked a prior snapshot. The sparsest area was O1 for 3R: T-15 and T-5 both selected 14:10, which was 300 and 900 seconds before their respective targets. O2 had a newer 14:22 record for T-5.

The generated CSVs had the requested race IDs and `track_name=浦和`. The all-snapshot rows at the available TAN/UMA CSV timestamps matched all 12 single-horse values and all 66 quinella pairs for each of the three races. The 30-minute `(1).CSV` copies were not present locally, so that filename set could not be independently read during this run.
