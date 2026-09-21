# 2026-09-21 C raw bet-count research — fixed-pair stress test

## Scope

This test is limited to C raw races:
- field_size in (15,16)
- ai_score_std <= 0.135

Available winner-AI-rank data:
- 2024 full year
- 2025 full year
- 2026 through 2026-09-13

2021-2023 walk-forward race-level files do not contain winner_ai_rank_low/high, so the C betting-point conclusion is not finalized across all six years.

No threshold change was made.

## 1. How concentrated are 100x winner pairs?

If each year is allowed to rank its own winning AI-rank pairs after seeing the result, the minimum number of distinct fixed pairs needed to cover portions of that year's 100x races is:

| Year | 25% coverage | 33% | 50% | 67% | 80% |
|---|---:|---:|---:|---:|---:|
| 2024 | 9 | 14 | 23 | 33 | 48 |
| 2025 | 9 | 13 | 23 | 36 | 55 |
| 2026* | 7 | 10 | 16 | 27 | 36 |

*through Sep 13

Even in-sample, C is not highly concentrated into 4-7 fixed rank pairs.

## 2. Cross-year stability of top pairs

The top fixed AI-rank pairs change substantially year to year.

Top-k overlap:
- top 4: no common pair between any year pair
- top 7: almost no overlap
- top 10: only 1 pair appears in all three top-10 sets
- top 20: only 3 pairs appear in all three top-20 sets

This is materially less stable than would be desirable for a frozen C4/C7 style rule.

## 3. 2024 discovery -> 2025/2026 holdout

Pairs were ranked using 2024 100x hit count only (payout used only as tie-break).
The selected list was then frozen and applied to 2025 and 2026 without adjustment.

### 4 points
- 2024: 15 x 100x hits, ROI 190.8%
- 2025: 4 hits, ROI 54.1%
- 2026*: 6 hits, ROI 75.0%

### 7 points
- 2024: 24 hits, ROI 165.4%
- 2025: 11 hits, ROI 62.5%
- 2026*: 8 hits, ROI 64.6%

### 10 points
- 2024: 31 hits, ROI 182.7%
- 2025: 19 hits, ROI 91.7%
- 2026*: 9 hits, ROI 59.3%

### 15 points
- 2024: 41 hits, ROI 181.3%
- 2025: 24 hits, ROI 80.1%
- 2026*: 12 hits, ROI 54.2%

### 20 points
- 2024: 51 hits, ROI 165.5%
- 2025: 30 hits, ROI 74.9%
- 2026*: 18 hits, ROI 59.5%

The 2024-trained fixed lists do not generalize well enough to justify a frozen C point count from these years.

## 4. Broad rank-zone distribution

100x winning pairs in C raw are spread mainly across three cross-band structures:

2024:
- AI1-5 x AI11+: 33.3%
- AI1-5 x AI6-10: 27.2%
- AI6-10 x AI11+: 21.1%

2025:
- 31.5%
- 24.0%
- 26.0%

2026*:
- 25.3%
- 33.3%
- 24.0%

Together these three broad cross-band families account for roughly 81-83% each year, but betting all pairs in those zones would require too many combinations to be a practical fixed-point rule.

## Current conclusion

Do not set C to 4, 7, 10, 15 or 20 fixed AI-rank pairs yet.

The evidence so far says:
- C race selection is much more stable than C exact winning-pair selection.
- A/B-style small frozen pair lists are a poor fit for C.
- C may require an adaptive pair-selection rule inside the selected race rather than a frozen rank-pair list.
- The exact point count remains open.

Before designing a new adaptive selector, first extend winner-rank output to the 2021-2023 walk-forward race-level data. This is a data-generation task, not an analysis task.
