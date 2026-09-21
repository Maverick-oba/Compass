# 2026-09-21 A10-R1 reconstruction checkpoint

## Status

The A-type 10-ticket ranker was rebuilt from the surviving source datasets instead of continuing to chase the missing historical artifact.

This reconstruction is close enough to the frozen historical A10 to treat it as a strong reproduction candidate, but it does **not** automatically replace the previously frozen A10+B4 baseline.

## Stage 1: no-odds high-payout race selector

Training year: 2024 only.

Model:
- StandardScaler
- LogisticRegression
- C = 1.0

Features:
- field_size
- ai1_score
- ai2_score
- ai5_score
- ai_gap12
- ai_gap15
- ai_top3_sum
- ai_score_std

Target:
- quinella payout >= 10,000 yen

Selection rule:
- fixed threshold = 2024 predicted-risk 80th percentile
- threshold = 0.15373081991763984

Reproduction:
- 2025 selected races = 767
- This exactly reproduces the previously logged "AI structure + field size" 767-race front gate.

## Stage 2: direct pair ranker

Training year: 2024 only.

Universe:
- all unordered quinella pairs inside Stage-1 selected races

Target:
- the actual winning quinella pair, only when official payout >= 10,000 yen

Model:
- numeric StandardScaler
- qpair OneHotEncoder
- LogisticRegression
- C = 0.3

Numeric pair features:
- r1
- r2
- s1
- s2
- rank_sum
- rank_gap
- score_sum
- score_gap

Definitions:
- r1/r2 = AI ranks in ascending rank order
- s1/s2 = corresponding AI scores
- qpair uses relative quartiles:
  - Qi = min(4, ceil(4 * ai_rank / field_size))
  - qpair = Q(first)xQ(second)

Ticket rule:
- rank every pair in each selected race by predicted probability
- buy Top 10

## 2025 holdout

Reconstructed A10-R1:
- selected races: 767
- investment: 767,000 yen
- all quinella hits: 65
- 50x+: 39
- 100x+: 23
- 200x+: 13
- payout: 1,314,670 yen
- ROI: 171.4%
- maximum payout: 280,380 yen

Previously frozen A10:
- selected races: 767
- 100x+: 23
- payout: 1,315,990 yen
- ROI: 171.6%

Difference in total payout is only 1,320 yen.

This is a very close reproduction of the historical A10.

## 2026 application

For 2026-01-04 through 2026-09-20, using the same Stage-1 and pair model without refitting:

Consistent field-size reconstruction using final_shusso_tosu:
- selected races: 489
- all quinella hits: 21
- 50x+: 10
- 100x+: 3
- 200x+: 1
- payout: 167,050 yen
- ROI: 34.2%
- max payout: 56,950 yen

Previously frozen historical audit:
- selected races: 485
- 100x+: 4
- ROI: 41.9%

The exact counts differ slightly, but the important result is reproduced: the 2025-strong A10 structure collapses sharply in 2026.

## Interpretation

The reconstructed model confirms that the old A10 was not an accidental one-off result.

2025 is reproduced almost exactly, while the same fixed structure weakens heavily in 2026. Therefore the next investigation should focus on structural drift in the winning-pair distribution, not on rebuilding the Stage-1 gate.

Do not tune this reconstruction on 2026. Use it as the reproducible A-type diagnostic model.

## Files

- research_data/2026-09-21_A10_R1_summary.csv
- research_data/2026-09-21_A10_R1_pair_coefficients.csv
- research_data/2026-09-21_A10_R1_stage1_coefficients.csv

The frozen A10+B4 checkpoint remains unchanged.
