# 2026-09-21 A10 exact reproduction audit

## Goal

Reproduce the frozen A-type 10-point direct quinella pair ranker that was previously recorded as:

- 2025: 767 races, 10 points/race, 100x+ hits 23, ROI 171.6%, payout 1,315,990 yen
- 2026 (2026-01-04 to 2026-09-20): 485 races, 10 points/race, 100x+ hits 4, ROI 41.9%

This audit does **not** replace the frozen A10. It is a reconstruction attempt only.

## Source data used

- `quinella_100x_structure_phase_m3/race_level_rows_for_m4.csv`
- `pace_feature_probe_phase3b/horse_pace_features.csv`
- `forward_input_20260104_20260920.csv`

## Stage-1 reconstruction

Rebuilt a 2024-trained no-odds logistic race selector using:

Numeric:
- field_size
- kyori
- ai1_score
- ai2_score
- ai5_score
- ai_gap12
- ai_gap15
- ai_top3_sum
- ai_score_std

Categorical:
- surface
- grade_code
- track_code

The 2025 AUC reproduced the previously observed range (~0.647).

A threshold around 0.1563 gives:
- 2024 100x capture: 117 races at race-level
- 2025 100x capture: 160 races at race-level
- selected races: about 667 (2024), 779 (2025)

A threshold chosen to force exactly 767 selected 2025 races gives:
- 2025 capture: 159, not the frozen 160

Therefore the old frozen 767 count was likely produced by a slightly different selector encoding/threshold or by downstream eligibility filtering. Exact Stage-1 race membership is not yet reproduced.

## Stage-2 reconstruction attempts

Generated all unordered horse pairs inside candidate races and trained only on 2024. Positive label was the actual 100x+ winning quinella pair; all other pairs were negative.

Tested:
- raw AI probability/rank pair features
- probability sum/difference
- rank sum/gap
- prior3 pace-position features
- CK style/rate features
- position_index
- exact AI-rank-pair categorical feature
- AI rank-band pair categorical feature
- relative quartile pair categorical feature
- logistic regression with several C values and class-weight settings

Representative 2025 results:
- basic numeric pair LR: about 19-20 100x hits, payout about 0.53-0.58M yen
- rank-band categorical structural model: about 20 hits, payout about 1.06M yen
- numeric + rank-band model: up to about 24 hits, payout about 0.79M yen

None reproduced the frozen target:
- 23 hits
- payout 1,315,990 yen
- ROI 171.6%

## Status

**NOT REPRODUCED.**

The frozen A10 remains the canonical result. Do not replace it with any model from this audit.

The missing artifact is the original per-race A10 ticket output or the exact original pair-feature/model specification.

Until that is found, any A10 pruning/Q1 reweighting is diagnostic research only and must be kept separate from the frozen A10+B4 baseline.
