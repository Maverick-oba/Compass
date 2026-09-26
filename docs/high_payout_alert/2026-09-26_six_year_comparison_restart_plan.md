# 2026-09-26 High Payout 6-Year Comparison Restart Plan

## Purpose

Continue the central JRA high-payout quinella research without modifying any frozen baseline artifacts.

The immediate goal is to compare the high-payout structure across 2021-2026 using no-leak AI scores, with special focus on whether 2026-like distribution shifts appeared in earlier years.

## Frozen references — do not modify

- `docs/high_payout_alert/2026-09-21_high_payout_A10_B4_frozen.md`
- historical formal A10:
  - 2025 selected 767 races
  - 23 hits at 100x+
  - payout 1,315,990 yen
  - ROI 171.6%
  - exact Stage-2 artifact is missing and must not be reconstructed by tuning to 2025
- A10-R1:
  - research/reconstruction branch only
  - do not promote to formal A10
- B4:
  - reproducible fixed baseline
  - gate: field_size in (13,14) and ai_top3_sum < 1.30
  - fixed pairs: AI2-AI11, AI3-AI12, AI4-AI10, AI1-AI12

## Existing C candidate

Outside A/B:
- field_size 15-16
- ai_score_std <= 0.135

Use C as a race-structure / chaos-warning candidate only.
Do not create a production fixed C ticket rule from 2026.

## Walk-forward AI contract

Use strictly prior training years:
- 2021 prediction: train 2011-2020
- 2022 prediction: train 2011-2021
- 2023 prediction: train 2011-2022
- 2024+ reference: current 2011-2023 baseline

Expected completed prediction race counts previously reported:
- 2021: 3,329 races
- 2022: 3,331 races
- 2023: 3,329 races

Before rebuilding anything, search the existing research directories and Git history for those completed outputs and audits. If matching outputs exist, reuse them. Do not retrain merely because the current session cannot immediately find the files.

## Next execution order

1. Locate existing 2021/2022/2023 walk-forward outputs, models, audit files, and scripts.
2. Confirm for each year:
   - prediction race count
   - train period
   - no future-year rows in training
   - 30-feature contract
   - one prediction row per active horse
   - unique race/horse keys
   - AI rank generated only from that year's out-of-sample predictions
3. Build a common race-level analysis dataset for 2021-2026.
4. Join official quinella results only after prediction/ranking is complete.
5. Apply the existing A/B/C race-structure definitions without tuning them to 2021-2023.
6. Produce year-by-year and half-year/meeting-period summaries.
7. Save every new script, threshold definition, output CSV, and result note to Git before trying any new rule.

## Required common race-level fields

At minimum:
- race_id
- race_date
- year
- field_size
- ai1_score
- ai2_score
- ai5_score
- ai_gap12
- ai_gap15
- ai_top3_sum
- ai_score_std
- winning quinella payout
- winning pair AI rank 1
- winning pair AI rank 2
- winning rank gap
- Q1-Q4 zone for each winning horse
- broad bands:
  - AI1-5
  - AI6-10
  - AI11+

Score absolute levels across separately trained walk-forward models must not be compared naively. Prefer AI-rank structure, rank bands, relative quartiles, and within-year score position.

## Six-year outputs

Create one canonical summary CSV with one row per year and at least:

- all races
- 100x+ quinella count
- A race count
- A 100x+ count
- B race count
- B 100x+ count
- B4 hits and ROI where reproducible
- C candidate race count
- C 100x+ count
- winning-pair band distribution
- AI11+ involvement rate
- Q1-Q4 pair distribution
- median winning-pair AI-rank gap

Also create separate half-year or meeting-period summaries to check whether mode shifts occur by calendar period rather than by arbitrary race counts.

## Main research questions

1. Was 2026 genuinely unusual, or did similar pair-distribution regimes occur in 2021-2023?
2. Did B-type strength appear in earlier periods and then fade in a similar way?
3. Is C candidate frequency stable even when its winning-pair distribution changes?
4. Are A/B/C useful as race-structure labels even when fixed ticket rules are not stable?
5. Is there any repeated calendar/meeting-level regime transition that can be observed without using results leakage?

Do not force a C-type betting rule. If no stable new pattern exists, record that as the result.

## Git rule

Every checkpoint must preserve:
- logic / feature definitions
- coefficients or model metadata when applicable
- thresholds
- ticket rules
- race-level output CSV
- yearly summary CSV
- audit results

Do not leave a result only in chat.
