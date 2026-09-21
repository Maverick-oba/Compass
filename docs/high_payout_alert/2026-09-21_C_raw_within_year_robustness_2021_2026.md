# 2021-2026 C raw within-year robustness analysis

## Scope

Definition is fixed:
- C raw = field_size in (15,16) AND ai_score_std <= 0.135

No threshold optimization and no new production filter were introduced.

Important:
- 2026 uploaded comparison data ends at 2026-09-13.
- 2026 results below are therefore through Sep 13.

## 1. Within-year calendar stability

Monthly comparisons were made only inside 15-16 runner races:
- compare C raw with same-field-size non-C

Number of months where C raw 100x rate exceeded non-C:
- 2021: 10 / 12
- 2022: 9 / 12
- 2023: 11 / 12
- 2024: 10 / 12
- 2025: 10 / 12
- 2026*: 8 / 9

Total:
- 58 / 69 observed months had positive C-raw lift.

Because single-month samples can be small, independent-ish two-month blocks were also checked:
- 2021: 6 / 6 positive
- 2022: 5 / 6 positive
- 2023: 6 / 6 positive
- 2024: 5 / 6 positive
- 2025: 5 / 6 positive
- 2026*: 5 / 5 positive
- total: 32 / 35 positive

This argues against the annual C-raw result being produced by only one short seasonal burst.
It does not mean every month is positive; counterexamples exist.

## 2. Surface robustness

C raw vs non-C 100x lift remained positive in both dirt and turf in every observed year:

2021:
- dirt +6.83 pp
- turf +4.43 pp

2022:
- dirt +3.03 pp
- turf +10.33 pp

2023:
- dirt +10.68 pp
- turf +9.94 pp

2024:
- dirt +2.43 pp
- turf +8.81 pp

2025:
- dirt +5.44 pp
- turf +7.15 pp

2026*:
- dirt +2.11 pp
- turf +9.73 pp

Thus the six-year aggregate is not explained solely by one surface.

## 3. 15-runner vs 16-runner robustness

The effect is generally present in both field sizes, but not perfectly uniform.

15 runners:
- 2021 +4.36 pp
- 2022 -1.07 pp
- 2023 +7.15 pp
- 2024 +6.90 pp
- 2025 +4.94 pp
- 2026* +1.50 pp

16 runners:
- 2021 +6.92 pp
- 2022 +7.86 pp
- 2023 +11.49 pp
- 2024 +3.54 pp
- 2025 +6.69 pp
- 2026* +6.41 pp

The 2022 15-runner segment is a real counterexample and should be retained rather than explained away.

## 4. Is 0.135 a brittle cutoff?

Within all 15-16 runner races from 2021-2026*, ai_score_std was grouped into fixed descriptive bands.

100x rates:
- <= 0.115: 459 / 2,453 = 18.71%
- 0.115-0.125: 142 / 807 = 17.60%
- 0.125-0.135: 135 / 861 = 15.68%
- 0.135-0.145: 103 / 836 = 12.32%
- 0.145-0.155: 93 / 784 = 11.86%
- > 0.155: 275 / 2,480 = 11.09%

This is a broad monotonic-looking gradient rather than an isolated spike at 0.135.

A simple logistic regression controlling for prediction year also found a negative association between ai_score_std and 100x outcome:
- coefficient for ai_score_std < 0
- p approximately 6.5e-15
- each +0.01 in score std corresponded to an odds multiplier of about 0.933 in this descriptive model.

This is not causal evidence and should not be used to tune a new cutoff.

## 5. Current interpretation

The strongest robustness result so far is not "0.135 is the magic number".
Rather:
- among 15-16 runner races, flatter AI score distributions tend to have a higher 100x rate;
- this relationship is visible across years, calendar blocks and both surfaces;
- but there are counterexamples, especially in some months and the 2022 15-runner segment.

Therefore:
- keep C raw as a research structure;
- do not freeze it as a production type yet;
- do not optimize the threshold further;
- next inspect whether the relationship survives broad distance/grade strata and whether the 2026 Sep-20 completion changes any conclusion.
