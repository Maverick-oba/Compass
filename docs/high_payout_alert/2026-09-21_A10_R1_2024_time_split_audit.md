# 2026-09-21 A10-R1 2024 time-split audit

## Purpose

Check whether reconstructed A10-R1 shows the same strength inside 2024 without using 2025.

The test is strictly chronological:
- train only on past 2024 months
- select Stage-1 threshold from the training window
- train Stage-2 pair ranker on training-window selected races
- apply unchanged to later 2024 months

## A10-R1 specification tested

Stage 1:
- LogisticRegression C=1.0
- StandardScaler
- features:
  - field_size
  - ai1_score
  - ai2_score
  - ai5_score
  - ai_gap12
  - ai_gap15
  - ai_top3_sum
  - ai_score_std
- threshold = training-window predicted-risk 80th percentile

Stage 2:
- LogisticRegression
- numeric:
  - r1, r2
  - s1, s2
  - rank_sum, rank_gap
  - score_sum, score_gap
- categorical:
  - relative qpair Q1xQ1 ... Q4xQ4
- Top10 tickets per selected race

## C=0.3 chronological result

| Split | Selected races | Stage1 100x | 100x hits | Return | ROI |
|---|---:|---:|---:|---:|---:|
| Jan-Jun -> Jul-Aug | 88 | 13 | 3 | 78,750 | 89.49% |
| Jan-Aug -> Sep-Oct | 114 | 17 | 2 | 88,520 | 77.65% |
| Jan-Oct -> Nov-Dec | 153 | 30 | 2 | 61,150 | 39.97% |
| Total | 355 | 60 | 7 | 228,420 | 64.34% |

Therefore A10-R1 with C=0.3 is **not** shown to have 2025-like strength inside 2024.

## Regularization grid using only 2024 chronological folds

| C | 100x hits | Return | ROI |
|---:|---:|---:|---:|
| 0.03 | 9 | 312,810 | 88.12% |
| 0.10 | 10 | 337,950 | **95.20%** |
| 0.30 | 7 | 228,420 | 64.34% |
| 1.00 | 6 | 226,500 | 63.80% |
| 3.00 | 6 | 226,500 | 63.80% |

C=0.10 is best in this 2024-only rolling audit.

However, when a full-2024 model with C=0.10 is applied to 2025:
- selected races: 767
- 100x hits: 13
- return: 483,320
- ROI: 63.0%

By contrast C=0.30 gives the previously observed near-match to the old A10:
- selected races: 767
- 100x hits: 23
- return: 1,314,670
- ROI: 171.4%

This means choosing C=0.30 because it matches the old 2025 A10 result is effectively using 2025 information. It should not be described as independently validated by 2024.

## Conclusion

- Stage-1 reconstruction remains strong and reproducible.
- The Stage-2 C=0.30 solution is not stable enough inside 2024 to call it an independently reproduced canonical A10.
- The near-perfect 2025 match (23 hits / 171.4%) is real, but it may be a coincidental or alternate solution rather than proof that the old A10 specification has been recovered.
- The frozen historical A10+B4 baseline should remain untouched.
- Any new A ranker should be treated as a fresh research branch and selected using 2024-only rules before looking at 2025/2026.
