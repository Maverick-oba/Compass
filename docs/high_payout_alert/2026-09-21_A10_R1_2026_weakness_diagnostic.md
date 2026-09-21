# A10-R1 2026 weakness diagnostic

## Scope

A10-R1 is kept fixed. This note diagnoses why the same 2024-trained pair ranker works strongly in 2025 and collapses in 2026. No 2026-specific tuning is applied.

## Main finding

A10-R1 allocates about 92% of its top-10 tickets to same-quartile middle structures, mainly Q2xQ2 and Q3xQ3.

This matched a profitable subset of 2025 100x races, but that subset became rare in 2026.

### Actual Stage-1 100x races

2025:
- 148 actual 100x races inside the Stage-1 candidate set
- Q2xQ2: 17 races, A10-R1 hit 9
- Q3xQ3: 14 races, A10-R1 hit 12
- therefore 21 of the 23 A10-R1 100x hits came from Q2xQ2/Q3xQ3

2026:
- 83 actual 100x races with valid result/payout inside the Stage-1 candidate set
- Q2xQ2: 4 races, A10-R1 hit 2
- Q3xQ3: 1 race, A10-R1 hit 1
- Q2xQ2 + Q3xQ3 are only 5/83 = 6.0% of actual 100x races

Meanwhile 2026 actual 100x shifted toward cross-quartile structures:
- Q1xQ2: 18
- Q1xQ3: 14
- Q1xQ4: 18
- Q2xQ3: 10
- Q2xQ4: 8
- Q3xQ4: 9

## Actual winning-pair model rank

2025 actual 100x pair model rank:
- rank 1-10: 23
- 11-20: 19
- 21-30: 9
- 31-50: 20
- 51-100: 53
- 101+: 24
- median rank: 54

2026 actual 100x pair model rank:
- rank 1-10: 3
- 11-20: 4
- 21-30: 5
- 31-50: 14
- 51-100: 45
- 101+: 12
- median rank: 67

The failure is therefore primarily Stage-2 pair ordering, not Stage-1 race detection.

## Simple diversification probe

A transparent 10-point quota derived only from 2024 positive qpair frequencies was tested as a diagnostic.

Result:
- 2026 100x hits improved from 3 to 7
- but 2025 100x hits dropped from 23 to 9

Therefore a simple fixed diversification rule does not solve both years. The two years genuinely have different winning-pair structures.

## Interpretation

2025 rewarded same-quartile middle pairs unusually strongly for this ranker. 2026 shifted toward separated/cross-quartile pairs, especially Q1-involved combinations. The A10-R1 model is not simply “less accurate” in 2026; the distribution of profitable pair shapes moved away from the shapes receiving most of its top-10 ticket allocation.

## Research implication

Do not modify the frozen A10+B4 baseline from this result alone.

If an A2 research branch is built, it should explicitly address pair-shape regime change rather than simply reweight Q1 or force diversification. A robust approach would need to decide, pre-race and without odds, whether the race is a same-zone type or a cross-zone type before assigning the ten pair slots.
