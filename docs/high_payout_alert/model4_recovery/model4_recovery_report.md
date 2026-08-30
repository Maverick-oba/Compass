# M8-C 固定Model 4 推論式復元

## 判定

**固定Model4推論式復元成功・M8-B再開可能**

## 方法

2024 M3の7生特徴量と、保存済み`M4_all`の`risk`だけを`race_id`で1対1結合した。結果ラベル`y`、`max_payout`、2025データは係数推定に一切使用していない。

保存済みriskを `logit(risk) = ln(risk / (1-risk))` へ変換し、次の生特徴量線形式を最小二乗で逆算した。

`z = intercept_raw + Σ beta_raw_i * x_i`  
`risk_reproduced = 1 / (1 + exp(-z))`

2024の結合件数は3,327件、設計行列rankは8（8列）である。従って7特徴と切片の式は一意に決定できる。

## 2024再現誤差

| 指標 | 値 |
|---|---:|
| max absolute error | 5.607e-15 |
| mean absolute error | 1.765e-15 |
| RMSE | 2.058e-15 |
| float64完全一致 | 0 / 3,327 |
| 誤差≤1e-12 | 3,327 / 3,327 |

## 2025固定式照合（係数調整なし）

2024で逆算した式をそのまま2025のM3特徴量へ適用し、保存済み2025 `M4_all risk` と照合した。2025は式の係数、切片、境界の決定には使用していない。

| 指標 | 値 |
|---|---:|
| 件数 | 3,335 |
| max absolute error | 5.662e-15 |
| mean absolute error | 1.853e-15 |
| RMSE | 2.145e-15 |
| 誤差≤1e-12 | 3,335 / 3,335 |

## 5段階境界

保存済み2024 M4 riskから元スクリプトと同じ`np.quantile(..., [0,.2,.4,.6,.8,1])`を再計算し、`searchsorted(..., side='right')`で割り当てた。再計算件数は `{'LOW': 666, 'NORMAL': 665, 'WATCH': 665, 'HIGH': 665, 'EXTREME': 666}`、M5保存値は `{'LOW': 666, 'NORMAL': 665, 'WATCH': 665, 'HIGH': 665, 'EXTREME': 666}`、一致判定は **True**。

数値境界は `model4_level_boundaries.json` に固定保存した。2025にはこの2024固定境界だけを適用する。

## 標準化係数との整合

`model_coefficients.csv` の係数はStandardScaler後の係数である。復元した生特徴量係数との関係は、各特徴で `coefficient_standardized = beta_raw × implied_scale` として検算し、全特徴で数値誤差を記録した。これは当時のscaler尺度を別経路からfitしたものではなく、保存済み係数と復元済み生係数の代数的対応である。

## 成果物

- `model4_recovered_formula.json`: feature順序、切片、生係数、既存標準化係数、再現誤差。
- `model4_reproduction_2024.csv`: 保存riskと復元riskの全件照合。
- `model4_reproduction_2025.csv`: 2024固定式だけによる2025照合。
- `model4_level_boundaries.json`: 2024固定5段階境界と件数照合。

既存M3/M4/M5成果物、V2、JV-Link downloader、PCKEIBA、公開Webには変更を加えていない。

