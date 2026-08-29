# 高配当警戒度 JSON案 v0.1

## 目的

Phase M7以降でWeb/アプリへ高配当警戒度を渡す場合の、最小JSON項目案。

M6時点では仕様案のみであり、既存JSONは変更しない。

## 最小案

```json
{
  "high_payout_alert_level": "HIGH",
  "high_payout_alert_score": 0.0,
  "high_payout_alert_version": "high_payout_alert_v0_1"
}
```

## 項目

### `high_payout_alert_level`

UI表示用の5段階。

許容値:

- `LOW`
- `NORMAL`
- `WATCH`
- `HIGH`
- `EXTREME`

### `high_payout_alert_score`

固定Model 4の内部score。

用途:

- 内部診断
- 将来の監査
- 5段階判定の再現確認

原則としてユーザーUIへ直接表示しない。

### `high_payout_alert_version`

判定ロジック・モデル・境界を識別する内部version。

初期案:

`high_payout_alert_v0_1`

## 実装時の注意

- M4で固定したModel 4を変更しない
- M5で固定した5段階境界を変更しない
- UI都合でscoreを確率表示へ変換しない
- scoreを「万馬券発生確率」と表現しない
- 既存Compass分類とは別項目として保持する
- 欠損時のfallback仕様はM7で決定する
- 過去日アーカイブへの保持方法もM7で決定する

## 役割分離

- Compass: 市場構造・参加判断
- AI順位: 馬の相対評価
- 高配当警戒度: レース全体の高配当化しやすさ

既存フィールドへ意味を流用せず、独立フィールドとする。
