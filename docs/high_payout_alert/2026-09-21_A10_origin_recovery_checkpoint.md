# 2026-09-21 A10 origin recovery checkpoint

## Purpose

Recover what the original high-payout A10 actually was, based on the exported ChatGPT research log and surviving Git artifacts.

This checkpoint does **not** redefine or replace the frozen historical A10.
It records only what can now be established and what is still missing.

---

## What was recovered from the old chat log

The original research path contained two distinct 10-ticket models.

### 1. Initial 10-ticket version

Earlier version:
- 2024 training
- 2025 untouched holdout
- around 779 selected races
- 10 tickets per selected race
- 17 hits at 100x+
- payout 763,550 yen
- ROI 98.02%

Method:
- score all unordered quinella pairs inside the selected high-payout candidate races
- buy Top 10
- mainly AI-rank-pair based

This was the first simple logistic-style pair ranker.

---

### 2. Formal A10

The formal A10 was then rebuilt from 2024 only.

Key design:
- positive label = the actual winning quinella pair when official payout >= 10,000 yen
- training year = 2024 only
- regularization strength determined inside 2024 using time split
- 2025 was not used for tuning
- every unordered quinella pair in each selected race was scored
- Top 10 pairs were bought

2025 holdout result:
- selected races: 767
- 100x+ hits: 23
- payout: 1,315,990 yen
- ROI: 171.6%

2026 historical audit:
- selected races: 485
- 100x+ hits: 4
- ROI: 41.9%

Important:
The improvement from the initial 17-hit / 98.02% version to the formal 23-hit / 171.6% A10 was not a small parameter tweak.
It was a rebuild into a pair ranker trained directly on actual 100x+ winning quinella pairs.

---

## What is still missing from the formal A10

The old chat confirms that the formal A10 was created and that its coefficients were said to have been fixed.

However, the actual original artifact has not been recovered.

Still missing:
- exact Stage-2 pair feature list used by the formal A10
- exact preprocessing
- exact regularization value
- exact fitted coefficients / intercept
- exact per-race Top10 historical output

Therefore the historical formal A10 cannot currently be reproduced exactly.

---

## A10-R1 reconstruction

A later reconstruction was created from surviving datasets.

Stage 1:
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

Threshold:
- 2024 predicted-risk 80th percentile
- 0.15373081991763984

Stage 2:
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

Relative quartile feature:
- qpair
- Qi = min(4, ceil(4 * ai_rank / field_size))

Ticket rule:
- score all unordered pairs
- buy Top 10

2025:
- selected races: 767
- 100x+ hits: 23
- payout: 1,314,670 yen
- ROI: 171.4%

This is numerically very close to the frozen historical A10 but must not be treated as identical.

---

## Important interpretation

The current evidence supports:

1. The formal A10 was a 2024-only, time-split-validated, 100x+ winning-pair classifier.
2. The original A10 was not a fixed set of 10 rank pairs.
3. The initial 17-hit version and the formal 23-hit version were different rankers.
4. A10-R1 is a strong reconstruction candidate, not the original artifact.
5. Similar 2025 aggregate results do not prove identical race-level/ticket-level behavior.
6. The formal A10 artifact itself remains missing.

---

## Next restart point

Next session should start from here.

Priority:
1. Search only for the original formal A10 Stage-2 artifacts around the point where the chat first reported:
   - 767 races
   - 23 hits
   - payout 1,315,990 yen
   - ROI 171.6%
2. Look for:
   - pair features
   - LogisticRegression C
   - coefficient/intercept dumps
   - scaler parameters
   - per-race Top10 output
3. Compare any recovered artifact against A10-R1 at race/ticket level.
4. Do not tune A10-R1 to force agreement with the frozen historical aggregate.

---

## Status

Research paused here on 2026-09-21.

The origin and training concept of the formal A10 have now been recovered.
Only the exact original Stage-2 artifact remains unresolved.
