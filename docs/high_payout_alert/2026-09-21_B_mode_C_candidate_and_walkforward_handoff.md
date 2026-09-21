# 2026-09-21 High Payout Research Handoff — B Mode / C Candidate

## Status

This note continues the frozen A10+B4 state without modifying it.

Existing frozen baseline:
- A10 + B4 remains the reference baseline.
- Do not overwrite `docs/high_payout_alert/2026-09-21_high_payout_A10_B4_frozen.md`.
- A10-R1 is a reconstruction/research branch, not the frozen original A10.

## A10-R1 audit reminder

A10-R1 reproduced the 2025 frozen A10 result very closely, but 2024 chronological validation showed it is not proven to be the original A10.

2024 chronological validation for pair-model C=0.3:
- Jul-Aug: 88 races, 3 x 100x hits, ROI 89.49%
- Sep-Oct: 114 races, 2 x 100x hits, ROI 77.65%
- Nov-Dec: 153 races, 2 x 100x hits, ROI 39.97%
- total: 355 races, 7 x 100x hits, ROI 64.34%

2024-only C-grid:
- C=0.03: 9 hits, ROI 88.12%
- C=0.10: 10 hits, ROI 95.20%
- C=0.30: 7 hits, ROI 64.34%
- C=1.00: 6 hits, ROI 63.80%
- C=3.00: 6 hits, ROI 63.80%

Conclusion: A10-R1 C=0.3 should not replace the frozen A10.

## AI score consistency check

The 2026 direct PCKEIBA prediction pipeline uses the same 30-feature contract/model definition as 2024/2025.
The reproduction gate confirmed:
- 30/30 feature match for 2024/2025
- predicted_probability numerical match within 1e-15
- AI rank exact match

Thus the 2026 behavior is not currently explained by a different score-generation formula.

## B type observations

B gate remains:
- field_size in (13,14)
- ai_top3_sum < 1.30

B4 fixed pairs:
- AI2-11
- AI3-12
- AI4-10
- AI1-12

Frozen B4:
- 2024 ROI 96.8%, 4 x 100x hits
- 2025 ROI 94.2%, 5 x 100x hits
- 2026 through 2026-09-20 ROI 211.1%, 7 x 100x hits

2026 B strength was concentrated in the first half.

B-gate 100x structure:
- 2024 AI11+ involved: ~24%
- 2025 AI11+ involved: ~50%
- 2026 AI11+ involved: ~61.8%

2026 H1 vs H2 (through Sep 20):
- Jan-Jun: 141 B-gate races, 24 x 100x, 17.0% 100x rate, B4 hit 7
- Jul-Sep20: 86 B-gate races, 10 x 100x, 11.6% 100x rate, B4 hit 0

2026 H1 actual 100x pair distribution included:
- AI1-5 x AI11+: 41.7%
- Q1 x Q4: 37.5%

2026 H2:
- AI1-5 x AI11+: 10.0%
- Q1 x Q4: 10.0%

Interpretation:
2026 H1 itself had a B4-friendly high-payout distribution. This was not only a consequence of looking at B4 winners.

## Weekly / meeting-mode experiment

2/4/6/8-week rolling windows were tested as a possible environment/mode detector.

Current conclusion:
- 2 weeks: too noisy
- 4 weeks: unstable
- 6 weeks: useful as an environment observation indicator
- 8 weeks: stable but slower
- not strong enough yet to automatically change betting logic

Use it as monitoring information only, not as an automatic betting-mode switch.

## C candidate

Search policy:
- 2024 full year = discovery
- 2025 full year = holdout validation
- 2026 through Sep 20 = reference only
- A/B are excluded first

Best simple C candidate found:

- outside A/B
- field_size 15-16
- ai_score_std <= 0.135

Results:
- 2024: 242 races, 44 x 100x, 18.18%
- 2025: 252 races, 44 x 100x, 17.46%
- 2026 through Sep20: 236 races, 30 x 100x, 12.71%

C candidate actual 100x pair structure:
- 2024 AI11+ involved: 68.2%
- 2025 AI11+ involved: 61.4%
- 2026: 43.3%

Broad pair distribution:
2024:
- AI1-5 x AI11+: 54.5%
- AI6-10 x AI11+: 13.6%
- AI1-5 x AI6-10: 20.5%
- AI6-10 x AI6-10: 11.4%

2025:
- AI1-5 x AI11+: 38.6%
- AI6-10 x AI11+: 22.7%
- AI1-5 x AI6-10: 22.7%
- AI6-10 x AI6-10: 13.6%

2026:
- AI1-5 x AI11+: 20.0%
- AI6-10 x AI11+: 40.0%
- AI1-5 x AI6-10: 23.3%
- AI6-10 x AI6-10: 16.7%

Median winning-pair rank gap:
- 2024: 8.0
- 2025: 6.5
- 2026: 6.0

## C fixed-pair / zone validation

C fixed pair tests were intentionally conservative.

2024 pairs appearing at least twice produced a 7-point set.

C7:
- 2024: 242 races, 17 x 100x hits, ROI 367.46%
- 2025: 252 races, 6 x 100x hits, ROI 109.60%
- 2026 reference: 236 races, 1 x 100x hit, ROI 31.23%

Zone: AI1-5 x AI11+
- 2024 ROI 138.98%
- 2025 ROI 100.04%
- 2026 ROI 39.21%

Zone: AI1-10 x AI11+
- 2024 ROI 88.70%
- 2025 ROI 79.39%
- 2026 ROI 35.03%

Conclusion:
C is interesting as a race-selection / "chaos warning" structure, but the winning-pair distribution is not stable enough to freeze a C4/C7 betting rule.
Do not promote C fixed bets to production.

## Next research direction

Generate walk-forward AI scores for earlier years to determine whether 2026-like distribution shifts have appeared before.

Correct no-leak plan:
- 2021 prediction model: train 2011-2020
- 2022 prediction model: train 2011-2021
- 2023 prediction model: train 2011-2022
- 2024+ current reference: 2011-2023 baseline

Start with 2023 only.
Use the existing PCKEIBA 30-feature SQL / feature-generation code and preserve strict-prior logic.

Required 2023 outputs:
- horse-level predicted_probability / ai_rank
- race-level field_size, ai1/ai2/ai5, gap12/gap15, top3_sum, score_std
- quinella result fields joined only after prediction for analysis
- future-leak audit
- field_size semantics audit
- comparison to 2024 score distributions

Do not modify existing 2024/2025/2026 canonical artifacts.
