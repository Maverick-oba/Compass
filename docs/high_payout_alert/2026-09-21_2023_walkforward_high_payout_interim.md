# 2023 walk-forward high-payout validation — interim analysis

Source:
- `race_level_2023.csv`
- 3,329 races
- Walk-forward model: train 2011-2022, predict 2023
- Descriptive validation only. This does not change frozen A10/B4 or define a production mode switch.

## B gate

Frozen B entrance:
- `field_size in (13,14)`
- `ai_top3_sum < 1.30`

2023:
- 13-14 runner races: 599
- B gate: 283 races / 30 x 100x / 10.60%
- 13-14 non-B: 316 races / 20 x 100x / 6.33%
- B 30x+: 122/283 = 43.11%
- B 50x+: 69/283 = 24.38%

Fisher exact comparison for B vs non-B inside 13-14 runners:
- odds ratio ~= 1.75
- p ~= 0.075

### Time variation

H1:
- 117 B races / 14 x 100x / 11.97%

H2:
- 166 B races / 16 x 100x / 9.64%

Quarterly B 100x rates:
- Q1: 4/52 = 7.69%
- Q2: 10/65 = 15.38%
- Q3: 12/100 = 12.00%
- Q4: 4/66 = 6.06%

Quarter heterogeneity chi-square p ~= 0.299.

Overlapping 6-week observation windows showed substantial variation:
- weak windows around late Jan to mid Mar: 0/21 to 0/26
- stronger windows around Mar-Apr: up to 4/19 = 21.05%
- stronger windows around late Jun-Jul: up to 8/41 = 19.51%
- weak windows in autumn: roughly 3-5%

Because these windows overlap, they are monitoring evidence only, not independent proof of a switchable B mode.

## C raw candidate

Raw entrance:
- `field_size in (15,16)`
- `ai_score_std <= 0.135`

Important:
The formal C definition excludes A/B first. The 2023 race-level file does not contain the frozen A-gate flag, so this is C raw, not final C.

2023:
- 15-16 runner races: 1,451
- C raw: 713 races / 144 x 100x / 20.20%
- 15-16 non-C: 738 races / 74 x 100x / 10.03%
- C raw 30x+: 347/713 = 48.67%
- C raw 50x+: 247/713 = 34.64%

Fisher exact comparison for C raw vs non-C:
- odds ratio ~= 2.27
- p ~= 6.46e-08

Quarterly C raw 100x rates:
- Q1: 41/184 = 22.28%
- Q2: 27/170 = 15.88%
- Q3: 29/141 = 20.57%
- Q4: 47/218 = 21.56%

Quarter heterogeneity chi-square p ~= 0.436.

## Threshold stability audit

This is not threshold optimization. Neighboring thresholds were checked only for an isolated-spike failure.

B, 13-14 runners:
- top3_sum < 1.25: 242 / 26 / 10.74%
- < 1.275: 260 / 29 / 11.15%
- < 1.30: 283 / 30 / 10.60%
- < 1.325: 305 / 31 / 10.16%
- < 1.35: 325 / 32 / 9.85%

C, 15-16 runners:
- std <= 0.125: 555 / 114 / 20.54%
- <= 0.130: 633 / 129 / 20.38%
- <= 0.135: 713 / 144 / 20.20%
- <= 0.140: 787 / 152 / 19.31%
- <= 0.145: 857 / 160 / 18.67%

Both change smoothly around the frozen cutoffs; C in particular is not supported by a single threshold spike.

## Interim conclusion

1. The B entrance existed in 2023 and was not unique to 2026.
2. B showed calendar-time variation, but 2023 alone does not justify an automatic mode switch.
3. The raw C entrance reproduced strongly in 2023 and is the cleaner structural finding so far.
4. Formal 2023 C comparison still requires frozen A exclusion if an exact A flag becomes available.
5. Next priority: append walk-forward 2022 and 2021 with identical definitions, then compare 2021-2026 without retuning thresholds.
