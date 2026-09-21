# 2021-2023 B/C robustness checks — anti-overinterpretation pass

This note deliberately tries to break the current hypotheses. No thresholds were tuned.

## 1. B: simple composition shift does not explain 2022

Within the frozen B gate (13-14 runners and ai_top3_sum < 1.30), the pre-race distributions were broadly similar across 2021-2023.

Mean values:
- ai1_score: 2021 0.4566 / 2022 0.4544 / 2023 0.4559
- ai2_score: 0.3534 / 0.3537 / 0.3551
- ai5_score: 0.2221 / 0.2322 / 0.2305
- ai_gap12: 0.1031 / 0.1007 / 0.1007
- ai_gap15: 0.2345 / 0.2222 / 0.2254
- ai_top3_sum: 1.1018 / 1.1044 / 1.1101
- ai_score_std: 0.1159 / 0.1162 / 0.1171
- field_size: 13.636 / 13.553 / 13.597

Pairwise standardized differences were small. The largest 2021-vs-2022 effect among these broad numeric descriptors was ai5_score at about |SMD|=0.19. Surface, grade and track-code mixes were also not decisively different.

Keibajo mix differed across years, but this is partly expected from calendar/venue changes and should not be treated as a causal B-mode explanation without stronger evidence.

A logistic model among all 13-14 runner races, using B-gate status plus broad pre-race descriptors, still showed a negative 2022 B interaction relative to 2021 (interaction p about 0.084). This is suggestive, not proof.

Conclusion:
- 2022 B weakness is not obviously explained by a simple shift in the broad AI score distribution, surface, distance or field-size mix.
- Do not invent a new filter to explain it yet.

## 2. B: the effect is not unique to 100x in the stronger years

B vs same-field-size non-B payout rates:

2021:
- 30x+: 45.00% vs 32.68%
- 50x+: 30.36% vs 19.61%
- 100x+: 18.21% vs 10.78%

2022:
- 30x+: 37.73% vs 34.62%
- 50x+: 24.54% vs 24.85%
- 100x+: 11.72% vs 11.54%

2023:
- 30x+: 43.11% vs 29.43%
- 50x+: 24.38% vs 15.82%
- 100x+: 10.60% vs 6.33%

This strengthens the observation that 2022 is genuinely different from 2021/2023, but does not yet identify why.

## 3. C raw: separation survives multiple payout thresholds

C raw vs same-field-size non-C:

2021:
- 30x+: 48.76% vs 36.94%
- 50x+: 32.86% vs 25.00%
- 100x+: 17.99% vs 11.81%

2022:
- 30x+: 48.10% vs 35.12%
- 50x+: 32.07% vs 21.92%
- 100x+: 16.74% vs 11.32%

2023:
- 30x+: 48.67% vs 32.25%
- 50x+: 34.64% vs 21.95%
- 100x+: 20.20% vs 10.03%

This is useful anti-overfitting evidence because the effect is not limited to the selected 100x cutoff.

## 4. Scratches / field-size semantics robustness

Because field_size is the declared-entry count while prediction_row_count may be smaller after scratches, results were rechecked on races where prediction_row_count == field_size only.

B, matched rows only:
- 2021: 17.04% vs 11.46%
- 2022: 11.79% vs 11.85%
- 2023: 10.78% vs 6.31%

C raw, matched rows only:
- 2021: 18.05% vs 11.64%
- 2022: 16.52% vs 11.36%
- 2023: 20.00% vs 9.63%

The main patterns remain after excluding races with a field-size/prediction-row mismatch. Therefore the current B/C observations are not artifacts of the field_size semantics or scratch races.

## 5. Current stance

Do not promote:
- B as an automatic mode switch
- C raw as a finalized production rule
- any new threshold or venue-specific rule

Current evidence only supports:
- B effectiveness varies materially across years/periods; 2022 is a real counterexample to constant-strength B.
- C raw separation is reproducible across 2021-2023 and across 30x/50x/100x payout thresholds.
- Both findings survive the field_size vs prediction-row-count robustness check.

Next:
- obtain full 2024/2025/2026 race-level data and apply the same raw B/C definitions without A/B exclusion or threshold changes;
- then compare 2021-2026 before making any structural interpretation.
