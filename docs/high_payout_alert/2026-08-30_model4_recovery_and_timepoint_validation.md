# 高配当警戒度 Model 4 復元・2026時点別検証まとめ — 2026-08-30

## 1. 目的

高配当警戒度 Model 4 について、固定推論artifact不足で止まっていた2026年時点別検証を再開するため、既存M3/M4/M5成果物から推論式を復元し、V2の時系列0B30を使って朝・昼・直前の安定性を検証した。

## 2. M8-C 固定Model 4 推論式復元

対象Modelは `M4_all`。

使用特徴量は以下の7項目。

1. `field_size`
2. `fav_odds`
3. `market_entropy`
4. `ai_gap15`
5. `ai_top3_sum`
6. `top5_overlap`
7. `rank_spearman`

既存成果物から、2024年のM3入力特徴量3,327RとM4保存済みrisk3,327Rがrace_idで全件一致し、7特徴の欠損は0件だった。

保存済みriskを教師ラベルとして再学習するのではなく、`logit(risk)` を生特徴量から決定論的に再現する式を逆算した。

復元結果:

- 2024: 3,327R
- 最大絶対誤差: `5.61e-15`
- 全3,327Rが誤差 `1e-12` 以下
- 2025: 3,335Rを係数調整なしで照合
- 2025最大絶対誤差: `5.66e-15`
- 全3,335Rが誤差 `1e-12` 以下
- 復元切片: `-3.487315220201205`
- 既存標準化係数との数学的整合: 全7特徴で確認

2024固定5段階境界も復元し、M5の件数

`666 / 665 / 665 / 665 / 666`

と完全一致した。

判定:

**固定Model4推論式復元成功・M8-B再開可能**

ローカル正本:

`C:\KEIBA_AI\central_pckeiba_ai_lab\output\analysis\quinella_100x_structure_phase_m8\model4_recovery\`

主な成果物:

- `model4_recovered_formula.json`
- `model4_reproduction_2024.csv`
- `model4_reproduction_2025.csv`
- `model4_level_boundaries.json`
- `model4_recovery_report.md`

## 3. V2 0B30履歴の探索誤り

初回M8-Bでは `0B30*.rtd` のみを探索していたため、V2の正式な時点付き保存本体である `ODDS_RT_0B30_*` を除外していた。

正しい保存先:

`C:\KEIBA_AI\v2\data\raw\odds`

確認結果:

- `ODDS_RT_0B30_*` 総数: 75,606件
- `.txt`: 37,749件
- `.csv`: 37,857件
- 正式命名パターン: 75,498件
- 時点付きsnapshot: 37,749件
- race数: 1,248
- 開催日数: 36日
- 期間: 2026-05-02 ～ 2026-08-30

V2は0B30を上書きしておらず、通常は

`ODDS_RT_0B30_{race_key}_{yyyyMMdd_HHmmss}`

で時刻別保存している。

10分main / 発走10分前 / 発走5分前はいずれも同じ保存系統を通る。`before_minutes` はファイル名には含まれず、milestoneログとの照合で識別する。

## 4. M8-B 再評価

正しい `ODDS_RT_0B30_*` を使用し、固定Model 4・2024固定境界を変更せず、朝・昼・60/50/40/30/20/10/5分前を非未来選択で評価した。

主要結果:

### 朝時点

- coverage: 824R / 100%
- final level完全一致: 78.28%
- ±1 level以内: 99.64%
- HIGH+EXTREME recall: 96.52%
- HIGH+EXTREME precision: 84.45%
- HIGH+EXTREME高配当lift: 約1.43

### 昼時点

- coverage: 824R / 100%
- final level完全一致: 87.38%
- ±1 level以内: 99.64%
- HIGH+EXTREME recall: 98.61%
- HIGH+EXTREME precision: 90.13%
- HIGH+EXTREME高配当lift: 約1.53

### 5分前

- final level完全一致: 93.32%
- HIGH+EXTREME precision: 94.63%
- HIGH+EXTREME高配当lift: 約1.49

60分前・30分前なども評価したが、昼時点から直前までの改善幅は限定的で、2026外部評価では昼時点のliftも十分高かった。

## 5. 運用方針候補

既存ランチャーは現在、

- 09:30頃: morning
- 12:15頃: live

の2回処理がある。

高配当警戒度については既存ローカルHTML処理には接続せず、独立した新規パイプラインとして09:30版と12:15版を生成する方針が有力。

想定:

- 09:30: 朝版を生成
- 12:15: 昼版へ更新
- Web公開用には専用JSON等で疎結合
- 高配当警戒度生成失敗時は既存Compass本体へ影響させない

直前10分/5分の64bit 0B30は、当面は研究・検証用途として蓄積を継続する。

## 6. 次回再開点

次回は、既存ローカルHTMLとは独立した高配当警戒度専用パイプラインを設計する。

重点:

1. 09:30 morning相当入力
2. 12:15 live相当入力
3. 固定Model 4推論
4. 2024固定level境界
5. 専用JSON生成
6. 既存Compass本体と疎結合
7. 失敗時は警戒度だけ非表示

Model 4の再学習・係数変更・level境界変更は行わない。
