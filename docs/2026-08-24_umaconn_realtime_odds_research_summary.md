# UmaConn / NVDTLab 速報オッズ直取得 調査まとめ

日付: 2026-08-24

## 目的

PC-KEIBAの速報系有料機能に依存せず、UmaConn / NVDTLab.dll を直接利用して地方競馬の速報オッズを取得できるか検証する。

最終的な用途は、UmaConn直取得 → 自前Odds Reader → 地方競馬分析 / Local Compass周辺機能への活用を想定する。

## 既知の環境

- NVDTLab.dll: `C:\Windows\SysWOW64\NVDTLab.dll`
- Version: 3.5.4.0
- COM ProgID: `NVDTLabLib.NVLink`
- 32bit COM
- UmaConn本番データ保存先: `C:\UmaConn\chiho.k-ba\data\`
- テスト用隔離保存先: `C:\UmaConn_test\direct\`
- servicekey等の認証情報は本資料に記載しない

## 直接COMアクセスの確認

32bit PowerShellから以下を確認済み。

```text
New-Object -ComObject NVDTLabLib.NVLink
NVInit("UNKNOWN") = 0
NVClose() = 0
NVSetSavePath(test) = 0
```

通常蓄積系では以下が成功した。

```text
NVOpen("RACE", "20260818000000", 1, ...)
```

結果:

- return = 0
- readcount = 14
- downloadcount = 14
- 14本の `.nvd` を隔離保存先へ直接取得

取得確認済み:

- RA
- SE
- HR
- O1～O6
- OA
- H1
- H6
- HA
- WF

PC-KEIBAを介さずにUmaConn / NVDTLabから直接データ取得できること自体は確認済み。

## `.nvd` / O1構造

UmaConnの `.nvd` はZIP形式で、内部に固定長TXTを保持する。

確認済み:

- RA: 1270 bytes + CRLF
- SE: 553 bytes + CRLF
- O1: 960 bytes + CRLF

O1には少なくとも単勝・複勝・枠連が含まれる。

## NVRTOpen / recordspec 静的調査

実在確認済みのrecordspecificコード:

```text
0B30～0B36
0B3A
0B41
0B42
0B51
```

確認結果:

- `0B41` = O1時系列
- `0B42` = O2時系列
- `0B43～0B46` は見つからず
- `0B51` はO1別フェーズではなくWF系（速報重勝式）
- `0B50`, `0B52～0B5F`, `0B6x～0B9x` は見つからず
- `0B3A` = OA（枠単）速報の可能性が高い

オッズ系は `/OddsData/` 配下の配信系統に分類されることを静的確認。

ローカルRealtime cacheは概ね:

```text
cache\yyyy\<dataspec><key>.rtd
```

## 船橋5R 0B31 実取得

対象:

- 2026-08-24 船橋5R
- key: `202608244305`

実行:

```text
NVRTOpen("0B31", "202608244305") = 0
NVStatus() = 0
NVRead() = 962
```

生成:

```text
0B31202608244305.rtd
```

内部:

```text
O1202608244305.txt
```

解凍後962 bytes = O1固定長960 + CRLF。

取得O1の発表時刻は13:41。

南関東公式16:06時点のオッズと比較すると値は変動していたが、同一レースの単勝・複勝として自然な変化であり、O1デコードは正常と判断。

同一0B31を16時台に再取得しても、ファイル・SHA-256・発表時刻13:41は不変だった。

## 0B41 静的調査

既存0B41を42レース、合計11,176件確認。

- 1レースあたり126～332件のO1
- 同一レースの複数発表時点を保持
- 発表時刻は数分刻みで進行

したがって `0B41` は1レース分のO1時系列データと判断。

最新値候補は、全O1の `happyo_tsukihi_jifun` 最大レコード。

## 船橋7R 0B41 実取得

対象:

- 2026-08-24 船橋7R
- key: `202608244307`
- 実行時刻: 16:51頃

結果:

```text
NVRTOpen("0B41", "202608244307") = 0
NVStatus() = 0
```

NVRead:

- 962 bytes × 40件
- -1 × 1回
- 0 (EOF) × 1回

生成:

```text
0B41202608244307.rtd
```

内容:

- ZIP entry数: 40
- 全件record_id = O1
- 最初の発表時刻: 11:31
- 最後/最大発表時刻: 13:41
- 発表時刻は単調非減少
- 重複なし

16:51に新規取得したにもかかわらず、末尾は13:41だった。

### 南関東公式との比較

16:45公式画面と比較すると、人気構造は一致。

特に8番が1番人気、4番が2番人気で、時間経過による投票増加として自然な変動だったため、データ内容自体は正常と判断。

## PCKEIBA起動・通常取得との関係

### 起動のみ

PCKEIBAを通常起動し約2分、何も操作せず終了。

その後同じ船橋7R 0B41を再取得。

結果:

- LastWriteTime不変
- SHA-256不変
- entry数40のまま
- 最大発表時刻13:41のまま

→ PCKEIBA起動だけでは0B41は更新されない。

### 通常取得後

PCKEIBAで通常取得を実施後、終了。

同じ0B41を再取得。

結果は同じく13:41のまま。

→ PCKEIBA通常取得でも速報0B41は更新されない。

## recordspec探索結果

0B51が存在したため別フェーズ候補として調査したが、WF（速報重勝式）でありO1最新値用途ではなかった。

現時点で、0B41以降の「最新O1専用」未発見コード候補は確認できていない。

## NVRTOpen 13:41停止原因の静的追跡

NVDTLab.dll 3.5.4.0の静的調査で以下を確認。

### 配信経路

オッズ系:

```text
0B30～0B36
0B3A
0B41
0B42
    ↓
/OddsData/
```

URL構成要素として:

```text
/OddsData/
yyyy
mm
dd
yyyymmdd
.zip
```

を確認。

サーバー設定には主系・副系が存在:

- `supercombi.jp`
- `nar-van.com`
- path: `/NAR-VAN`
- port: 80

主系/副系の具体的切替条件は未確定。

### ライセンス/SID

NVDTLabにはライセンス確認処理が存在。

PC-KEIBA Realtimeは自前テストの `UNKNOWN` とは異なる専用SIDを `NVInit` に渡している。

重要な差:

```text
自前: NVInit("UNKNOWN")
PC-KEIBA Realtime: 専用SIDでNVInit
```

`UNKNOWN`でもNVInit=0、0B31/0B41の有効データ取得には成功しているため、単純な認証失敗とは判断できない。

### payflag

TypeLibに `m_payflag` / `NVSetPayFlag` は存在するが、PC-KEIBA Realtime側で呼び出している証拠は確認できず、現時点で速報有料会員フラグとは判断しない。

### `.rtd`更新判定

静的調査で以下を確認。

- 60秒以内のローカル再利用判定
- HTTP GetFileInfo / Header確認
- redirect処理
- 403 / 404処理
- 404の負キャッシュ

推定される流れ:

```text
.rtdが60秒以内
  → ローカル再利用

60秒超
  → リモートメタデータ確認
  → リモート更新ありなら取得
  → 同一なら既存.rtd再利用
```

船橋7R 0B41はローカルに存在しない状態から16:51に新規取得して13:41までだったため、ローカル60秒キャッシュだけでは説明できない。

## PC-KEIBA Realtime経路

静的調査上、地方Realtime処理は概ね:

```text
PC-KEIBA専用SIDでNVInit
  ↓
レースkeyなら0B30を追加
  ↓
0B20を追加
  ↓
各dataspecでNVRTOpen
  ↓
NVRead
  ↓
NVClose
```

PC-KEIBA Realtimeは主に `0B30 / 0B20` を使い、0B41を要求する経路は確認できなかった。

## 船橋7R 0B30 実取得テスト

対象:

- dataspec: `0B30`
- key: `202608244307`
- NVInit: `UNKNOWN`
- 実行時刻: 17:45頃

結果:

- NVRTOpenを1回のみ実行
- 32bit COMプロセスが終了せず約2分待ち
- 当該プロセスのみ停止
- NVRTOpen戻り値を回収できず
- NVStatus/NVRead結果も未確認
- `.rtd`生成なし
- 新規・更新ファイルなし

したがって0B30の配信内容は判定不能。

ただし `UNKNOWN` SIDでの0B30呼び出しは、0B31/0B41とは明らかに異なる挙動を示した。

## 現時点の整理

### 確認済み

1. UmaConn/NVDTLabはPC-KEIBAなしで直接操作可能。
2. 通常RACEデータはNVOpenで直接取得可能。
3. 0B31からO1を1レース単位で取得可能。
4. 0B41はO1時系列であり、複数時点の単勝・複勝等を保持する。
5. O1固定長デコードは正常。
6. 2026-08-24船橋では0B31/0B41とも13:41で止まった。
7. PCKEIBA起動のみ・通常取得後でも0B41は13:41のまま。
8. ローカルキャッシュだけでは13:41停止を説明できない。
9. 0B51はO1別フェーズではなくWF系。
10. PC-KEIBA Realtimeは0B30/0B20を使用する。
11. `UNKNOWN` SIDでの0B30はハングし、内容未確認。

### 否定/優先度低下した仮説

- PCKEIBA起動だけで更新トリガーが入る
- PCKEIBA通常取得で0B41が最新化される
- 0B51がO1の後半フェーズ
- 0B43～0B46がO3～O6時系列
- ローカル60秒キャッシュだけが13:41停止原因
- m_payflagを単純に速報有料会員フラグとみなす

## 未解決の本命

1. PC-KEIBA Realtime専用SIDの性質
2. `UNKNOWN`と専用SIDで配信先/提供範囲が異なるか
3. 0B30がSID依存か
4. 0B20の正式用途
5. 主系/副系サーバー選択条件
6. リモート側ZIPが13:41で止まっていた理由
7. 配信側ZIP生成停止/同期ずれ/契約区分の可能性
8. 0B30がUNKNOWNで戻らない条件

## 次回の推奨調査順

いきなり実取得を増やさず、まず静的に以下を確認する。

1. PC-KEIBA Realtime専用SIDがどのようなアプリ識別子か
2. SIDの利用条件
3. 0B20の役割
4. 0B30呼び出し時の前提条件
5. PC-KEIBA Realtimeと自前呼び出しの差分
6. 必要なら、許可された正規SIDで1レース限定比較テスト

PC-KEIBA専用SIDを自前クライアントへ無断流用する前提では進めない。

## 運用上の注意

- PC-KEIBA / UmaConn本番設定を変更しない
- テストは隔離保存先を使用
- servicekey等の秘密情報をログ・GitHubへ保存しない
- 投票系APIには触れない
- 未知dataspec総当たりは行わない
- COMハング時は再試行せず対象プロセスのみ停止
- テスト後はsavepathを本番値へ復帰確認

## 現時点の結論

UmaConn直取得そのものは成立しており、O1速報・O1時系列も取得・解析できた。

一方、「開催中の最新オッズ」を安定して取得する経路は未確定。

現時点では、0B31/0B41の13:41停止はローカルキャッシュではなく、配信リソース・SID・配信先選択など上流側の条件が関与している可能性が高い。

次回はPC-KEIBA Realtime専用SIDと0B30/0B20の関係を中心に、静的調査から再開する。
