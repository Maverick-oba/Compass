# 2021-2023 walk-forward high-payout comparison

## Scope

No thresholds were tuned in this comparison.

Walk-forward inputs:
- 2021: train 2011-2020, predict 2021
- 2022: train 2011-2021, predict 2022
- 2023: train 2011-2022, predict 2023

Frozen/previously selected entrance conditions:
- B: field_size in (13,14) AND ai_top3_sum < 1.30
- C raw: field_size in (15,16) AND ai_score_std <= 0.135

C is called "raw" here because the formal C candidate excludes frozen A/B first, and the race-level walk-forward files do not contain an exact frozen A flag.

## B result

2021:
- B 280 races / 51 x 100x = 18.21%
- same field-size non-B 306 / 33 = 10.78%
- odds ratio 1.84, Fisher p=0.0129

2022:
- B 273 / 32 = 11.72%
- non-B 338 / 39 = 11.54%
- odds ratio 1.02, Fisher p=1.00

2023:
- B 283 / 30 = 10.60%
- non-B 316 / 20 = 6.33%
- odds ratio 1.75, Fisher p=0.0751

Pooled 2021-2023:
- B 836 / 113 = 13.52%
- non-B 960 / 92 = 9.58%
- odds ratio 1.47, Fisher p=0.00926

Interpretation:
- B is not a constant-strength structure.
- It separated clearly in 2021, disappeared in 2022, and separated again directionally in 2023.
- A year-interaction logistic model is consistent with 2022 being the exceptional weak-B year; the 2022 interaction term is negative (p about 0.09).
- This supports treating B as environment-sensitive rather than as a permanently strong gate.

### B quarterly 100x rates

2021:
- Q1 14.04%
- Q2 18.52%
- Q3 21.74%
- Q4 16.88%

2022:
- Q1 7.55%
- Q2 10.91%
- Q3 13.98%
- Q4 12.50%

2023:
- Q1 7.69%
- Q2 15.38%
- Q3 12.00%
- Q4 6.06%

Across all three years, pooled quarter rates are:
- Q1 9.88%
- Q2 14.94%
- Q3 15.79%
- Q4 12.09%

Quarter heterogeneity is not statistically decisive, so calendar season itself should not yet be used as a switch. The important finding is the large year/time variation in B effectiveness.

## C raw result

2021:
- C raw 767 / 138 = 17.99%
- same field-size non-C 720 / 85 = 11.81%
- odds ratio 1.64, Fisher p=0.000827

2022:
- C raw 711 / 119 = 16.74%
- non-C 689 / 78 = 11.32%
- odds ratio 1.57, Fisher p=0.00436

2023:
- C raw 713 / 144 = 20.20%
- non-C 738 / 74 = 10.03%
- odds ratio 2.27, Fisher p=6.46e-08

Pooled 2021-2023:
- C raw 2,191 / 401 = 18.30%
- non-C 2,147 / 237 = 11.04%
- odds ratio 1.81, Fisher p=1.39e-11

Interpretation:
- C raw separated from its comparison group in every walk-forward year.
- The effect direction is stable in 2021, 2022, and 2023.
- A year-interaction logistic model found no meaningful evidence that the C effect changes by year (2022 interaction p about 0.85; 2023 about 0.13).
- This is substantially cleaner cross-year evidence than B.

### C raw quarterly 100x rates

2021:
- Q1 17.54%
- Q2 18.92%
- Q3 21.58%
- Q4 15.52%

2022:
- Q1 16.58%
- Q2 21.59%
- Q3 18.10%
- Q4 12.39%

2023:
- Q1 22.28%
- Q2 15.88%
- Q3 20.57%
- Q4 21.56%

There is no single quarter driving the result. Pooled quarter heterogeneity is not significant (p about 0.44).

## Neighbor-threshold stability

No optimization was performed; neighboring values were checked only to detect a brittle single-cutoff spike.

C raw 100x rates remain smooth around 0.135:
- 2021: 0.125 19.41% -> 0.135 17.99% -> 0.145 16.85%
- 2022: 0.125 17.84% -> 0.135 16.74% -> 0.145 15.75%
- 2023: 0.125 20.54% -> 0.135 20.20% -> 0.145 18.67%

B also changes gradually around top3_sum 1.30, but its year dependence is much stronger.

## Current research interpretation

The walk-forward extension changes the picture:

1. C raw is now the strongest structural finding. It reproduced in three independently trained prediction years without threshold retuning.
2. B is real in aggregate, but its strength is regime-dependent. 2022 is the clearest counterexample to assuming B is always active.
3. The prior "B mode" idea should therefore be researched as an environment detector, not promoted to an automatic betting switch.
4. The next useful step is to join these walk-forward years to the existing 2024-2026 reference while keeping C-raw and formal C (A/B excluded) explicitly separate.
5. Do not optimize fixed C betting pairs from these results. The evidence currently supports race-selection/chaos-warning structure much more strongly than stable fixed-pair selection.
