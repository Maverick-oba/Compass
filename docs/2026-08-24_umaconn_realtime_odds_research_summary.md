# UmaConn / NVDTLab 速報オッズ直取得 調査まとめ

日付: 2026-08-24

## 目的

PC-KEIBAの速報系有料機能に依存せず、UmaConn / NVDTLab.dll を直接利用して地方競馬の速報オッズを取得できるか検証する。

最終用途は、UmaConn直取得 → 自前Odds Reader → 地方競馬分析 / Local Compass周辺機能への活用を想定する。

> 注意: servicekey / ukey / password / token 等の認証情報は本資料に記載しない。

---

## 1. 既知の環境

- NVDTLab.dll: `C:\Windows\SysWOW64\NVDTLab.dll`
- Version: `3.5.4.0`
- Company: `RateBuster Co.,Ltd`
- COM ProgID: `NVDTLabLib.NVLink`
- CLSID: `{F726BBA6-5784-4529-8C67-26E152D49D73}`
- TypeLib: `{6B4C2ED0-BB26-483E-A264-1CA2820A6F3A}` v1.0
- 32bit COM / PE x86
- ThreadingModel: `Both`
- UmaConn本番保存先: `C:\UmaConn\chiho.k-ba\data\`
- テスト用隔離保存先: `C:\UmaConn_test\direct\`

32bit PowerShellの確認:

```powershell
[Environment]::Is64BitProcess
# False なら32bit
```

32bit PowerShell実体:

```text
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe
```

64bit PowerShellからCOM生成すると `REGDB_E_CLASSNOTREG (0x80040154)` になるため、必ず32bit PowerShellを使う。

---

## 2. 通常RACEデータの直接取得は確認済み

32bit PowerShellから:

```text
New-Object -ComObject NVDTLabLib.NVLink
NVInit("UNKNOWN") = 0
NVClose() = 0
NVSetSavePath(test) = 0
```

通常蓄積系:

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

PC-KEIBAを介さずにUmaConn / NVDTLabから直接データ取得できること自体は確定。

---

## 3. `.nvd` / O1 / O2 構造

UmaConnの `.nvd` はZIP形式で、内部に固定長TXTを保持する。

確認済み:

- RA: 1270 bytes + CRLF
- SE: 553 bytes + CRLF
- O1: 960 bytes + CRLF = 962 bytes
- O2: 2040 bytes + CRLF = 2042 bytes

O1には少なくとも単勝・複勝・枠連が含まれる。

OddsView2NV生成物 `.nvO1/.nvO2` は独自ヘッダを持たず、raw O1/O2固定長レコードの連結。

---

## 4. NVRTOpen / recordspec 静的調査

実在確認済みコード:

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
- `0B51` = WF系（速報重勝式 / WIN5系）
- `0B3A` = OA（枠単）速報の可能性が高い
- `0B12` = 払戻系
- `0B13` = タイムDM系
- `0B17` = 対戦DM系

`0B12/13/17/51` が最新O1/O2補完用である証拠はない。

オッズ系は `/OddsData/` 配下の配信系統に分類される。

ローカルRealtime cacheは概ね:

```text
cache\yyyy\<dataspec><key>.rtd
```

実際のOddsView2NV / UmaConn本番cacheでは開催回・日次を含む長いkey形式も確認している。

---

## 5. 初期の自前速報テスト

### 5.1 船橋5R 0B31

対象:

- 2026-08-24 船橋5R
- key: `202608244305`

```text
NVRTOpen("0B31", "202608244305") = 0
NVStatus() = 0
NVRead() = 962
```

取得O1発表時刻は13:41。

16時台に再取得しても、ファイル・SHA-256・発表時刻13:41は不変だった。

### 5.2 船橋7R 0B41（16:51頃）

対象:

- key: `202608244307`

```text
NVRTOpen("0B41", "202608244307") = 0
NVStatus() = 0
```

取得内容:

- O1 40件
- 最初 11:31
- 最後 13:41
- 全件O1
- 時刻は単調増加

この時点では16:51に取得しても13:41までだった。

PCKEIBA起動のみ、PCKEIBA通常取得後でも同じ0B41は13:41のままだった。

当初はSID差・配信先差・リモートZIP更新停止等を疑ったが、後述の2026-08-24夜の検証により、この解釈は大きく修正された。

---

## 6. OddsView2NVを比較対象として導入

導入ソフト:

```text
時系列オッズ Viewer２ for 地方競馬 Version 1.15
C:\keibasoftcom\OddsView2NV\OddsView2NV.exe
```

静的調査:

- x86 / 32bit
- ネイティブWindows EXE
- Delphi/VCL系の可能性が高い
- `NVDTLablib.NVLink` を利用
- `NVInit / NVRTOpen / NVStatus / NVRead / NVClose` を参照
- `0B41 → .nvO1`
- `0B42 → .nvO2`
- 固定専用SIDらしき定数あり（値は記録・利用しない）
- `0B20 / 0B30 / 0B31` は平文定数として見つからない
- 別速報dataspecでO1/O2を補完する静的証拠なし

マニュアル上も、開催日に対象レースを選択して「オッズ取得」を押すと、その時点以前の時系列オッズを取得する仕様。

OddsView2NVはUmaConn / 地方競馬DATA利用権を前提としており、独自HTTPスクレイピングが本線という証拠はない。

---

## 7. OddsView2NV生成データの全体観察（2026-08-24）

5場・57レース、O1/O2計114ファイルを読み取り専用集計。

場コード:

- 35 盛岡
- 43 船橋
- 46 金沢
- 48 名古屋
- 83 帯広

初期集計:

- 13:41～13:43で停止: 13R
- 13:43より後の系列あり: 44R
- 当時の44Rは13:43後がちょうど1件
- O1/O2時刻系列一致: 52R
- 不一致: 5R

その後ユーザー操作・再取得により、名古屋8～9R、帯広9Rなどにも後続系列が追加された。

重要な観察:

- 複数の連続レースが同じ最終発表時刻を持つブロックが存在
- ファイルLastWriteTimeと内部O1/O2発表時刻は独立
- 20:02台に一括再保存されても、内部発表時刻は各レース固有の時刻を保持
- 「常に最新1件だけ追加」という仮説は、後の11R/12R検証で否定された

---

## 8. 船橋11R / 12Rで複数の速報系列を確認

正規Viewerで一度は11R/12Rとも13:41/13:42止まりだったが、後で再取得すると複数の時系列が追加された。

### 11R

前回:

- 40件
- 最終13:41

後:

- 42件
- 20:06
- 20:14

### 12R

前回:

- 39件
- 最終13:42

後:

- 45件
- 20:04
- 20:06
- 20:14
- 20:19
- 20:25
- 20:32

重要:

- `.nvO1/.nvO2` と `.rtd` の件数・時刻系列は一致
- 最新系列はViewerが別データから合成したものではなく、`0B41/0B42.rtd` 自体に入っている
- 「履歴 + 取得時点最新1件だけ」仮説は否定

したがって現在の理解は:

> `0B41/0B42` は、その時点で配信側に公開済みのO1/O2時系列をまとめて返す。

配信側への反映は即時ではなく、レース時刻や公開タイミングに応じて後続系列が増える可能性が高い。

---

## 9. SID差仮説の再評価

当初:

```text
自前: NVInit("UNKNOWN")
OddsView2NV / PC-KEIBA系: 固定専用SID
```

という差から、UNKNOWNでは古い履歴だけ、専用SIDでは最新速報まで取れる可能性を疑った。

しかし後述の自前テストで、`NVInit("UNKNOWN") + 0B41` でも発走直前・発走後を含む最新系列まで取得できた。

したがって:

- 「専用SIDでなければ速報時系列が取れない」仮説は大幅に後退
- 初期の13:41停止は、SID差より配信側の公開タイミングだった可能性が高い

専用SIDの正式な性質は未確認のため、他製品のSID値を自前クライアントへ流用しない。

---

## 10. COM生成ハング騒動の切り分け

調査途中、Codex子プロセスから32bit COM生成が30秒/90秒で戻らない現象が発生。

Windows再起動後もCodex通常コンテキストでは再現したため、一時はCOM/NVDTLab破損を疑った。

静的確認:

- ProgID / CLSID 正常
- InprocServer32 = `C:\Windows\SysWOW64\NVDTLab.dll`
- DLL Version 3.5.4.0
- DLL LastWriteTime 2026-03-16
- OddsView2NV導入時にDLL差替え・COM再登録の痕跡なし

ProcMon観察では、制限外コンテキストでCOM生成が約1.16秒で正常終了。

- NVDTLab.dll Load Image SUCCESS
- NAR-VAN関連レジストリ読取成功
- savepath読取成功
- Networkアクセスなし
- 長時間待機なし

暫定結論:

> Codex通常子プロセス側のサンドボックス / 実行コンテキスト差によるハングだった可能性が高い。

さらにユーザーが最初に通常PowerShellで実行した際は64bit PowerShellだったため `REGDB_E_CLASSNOTREG` が発生。

32bit PowerShellへ切り替えると:

```text
COM生成成功
NVInit("UNKNOWN") = 0
```

となり、NVDTLab/COMが壊れていないことを確認した。

今後:

- COM実行はユーザー側の通常32bit PowerShellで行う
- Codexはスクリプト作成・静的解析・結果解析を担当

---

## 11. 決定的テスト: 自前 UNKNOWN + 0B41 で船橋12R取得

実行環境:

- ユーザー側の通常32bit PowerShell
- PC-KEIBA停止
- OddsView2NV停止
- `NVInit("UNKNOWN") = 0`

対象:

- 2026-08-24 船橋12R
- key: `202608244312`
- dataspec: `0B41`

結果:

```text
NVRTOpen("0B41", "202608244312") = 0
NVStatus() = 0
```

単発NVRead:

```text
ret = 962
filename = 0B41202608244312.rtd
buff length = 962
```

その後同一セッションでループ読取:

```text
record count = 48
```

注意:

- ループ前に単発NVReadを1件消費している
- よって今回の取得系列は実質49件相当

ループ末尾5件のO1先頭部から発表時刻を確認:

```text
Index 44 -> 20:32
Index 45 -> 20:44
Index 46 -> 20:47
Index 47 -> 20:49
Index 48 -> 21:12
```

船橋12R発走は20:50。

したがって自前 `UNKNOWN + 0B41` で少なくとも:

- 20:44 = 発走6分前
- 20:47 = 発走3分前
- 20:49 = 発走1分前
- 21:12 = 発走後

まで取得できた。

これは「UNKNOWNでは13:41までしか取れない」という初期仮説を反証する強い結果。

### 重要な結論

> UmaConn / NVDTLab を自前で直接使用し、`NVInit("UNKNOWN") + NVRTOpen("0B41", race_key)` から発走直前を含むO1時系列を取得できることを確認した。

現時点では、PC-KEIBAの速報系有料機能に依存せず、自前で速報O1時系列を取得する技術的経路が成立したと判断する。

### 未確認

- 自前 `0B42` の同条件最終確認はまだ未実施
- 21:12レコード先頭は `O142...` と見えるため、O1内部状態/区分の正式解釈は仕様確認が必要
- 0B41の公開更新間隔・公開タイミングの正式仕様は未確定

---

## 12. 現在の理解: 0B41/0B42の配信モデル

現在最も整合的なモデル:

```text
配信側でO1/O2時系列を蓄積
        ↓
レース進行に応じて系列が追加・公開
        ↓
NVRTOpen(0B41 / 0B42)
        ↓
その時点で公開済みの時系列をまとめて取得
```

初期に13:41付近で止まっていたレースでも、発走が近づくと20時台の複数系列が後から取得可能になった。

12Rでは:

```text
20:04
20:06
20:14
20:19
20:25
20:32
20:44
20:47
20:49
21:12
```

まで確認されている。

特に発走直前は更新間隔が短くなっている。

「常時ストリーミング」ではなく、要求時にサーバー側で公開済みの系列群を取得するオンデマンド型と考えるのが自然。

---

## 13. 0B30 / PC-KEIBA Realtimeについて

PC-KEIBA Realtime静的調査では概ね:

```text
専用SIDでNVInit
  ↓
0B30
  ↓
0B20
  ↓
NVRTOpen / NVRead
```

を確認。

一方、自前 `UNKNOWN + 0B30` は過去テストで処理が戻らず内容未確認。

ただし、今回 `UNKNOWN + 0B41` で発走直前O1時系列まで取得できたため、Local Compass等で単勝・複勝・枠連系速報を使う目的では、0B30を無理に追う優先度は大きく低下した。

0B20/0B30の正式用途は別課題として残す。

---

## 14. 現時点の確定事項

1. UmaConn/NVDTLabはPC-KEIBAなしで直接操作可能。
2. 通常RACEデータはNVOpenで直接取得可能。
3. `0B41` はO1時系列。
4. `0B42` はO2時系列。
5. `.rtd` 自体に複数の時系列レコードが格納される。
6. OddsView2NVは0B41/0B42を主経路として利用している。
7. Viewer独自の別速報dataspecからO1/O2を合成する証拠はない。
8. 13:41～13:43停止は恒久的な制限ではない。
9. 発走が近づくと後続系列が複数追加・公開される。
10. 自前 `NVInit("UNKNOWN") + 0B41` で発走直前O1まで取得成功。
11. 専用SID必須説は大幅に後退。
12. Codex通常子プロセスのCOMハングはNVDTLab破損ではなく実行コンテキスト差の可能性が高い。
13. COM直接実行は32bit PowerShell必須。

---

## 15. 優先度が下がった / 否定された仮説

- PCKEIBA起動だけで0B41更新トリガーが入る
- PCKEIBA通常取得で0B41が最新化される
- 0B51がO1後半フェーズ
- 0B43～0B46がO3～O6時系列
- ローカル60秒キャッシュだけが13:41停止原因
- m_payflagが単純な速報有料会員フラグ
- 別dataspecが最新O1/O2をViewerへ追記している
- 0B41/0B42は常に「履歴 + 最新1件」だけを返す
- UNKNOWN SIDでは速報最新値を取得できない
- OddsView2NV導入でNVDTLab.dll / COM登録が壊れた
- STA/MTA不一致がCOMハング原因

---

## 16. 未解決事項

1. 自前 `0B42` でO2時系列を同様に取得できることの最終確認
2. 0B41/0B42の正式な公開更新タイミング
3. 発走何分前から速報系列が増え始めるか
4. 発走直前の更新頻度ルール
5. 発走後レコードの区分・確定状態（例: 21:12 O1の先頭区分）
6. `0B20 / 0B30` の正式用途
7. PC-KEIBA専用SIDの正式な意味（利用はしない）
8. 自前運用時の安全な取得間隔・cache運用
9. Local Compassへ組み込む場合の必要券種・更新頻度

---

## 17. 次回の推奨順序

### Phase 1: 0B42確認

同じ自前32bit PowerShell経路で、1レースだけ:

```text
NVInit("UNKNOWN")
NVRTOpen("0B42", race_key)
NVRead
```

を確認し、O2の件数・最終時刻がO1と一致するかを見る。

### Phase 2: 自前Reader最小実装

目的を「最新オッズ取得」に限定し、最初は:

- 0B41
- 0B42
- race key指定
- 最新レコード抽出
- CSV/JSON出力

だけの小さなReaderを作る。

### Phase 3: 配信タイミング観測

別開催日に1レースだけ、発走90～60分前から一定間隔で観測し:

- 最初に後続系列が現れる時刻
- 発走までの更新間隔
- 発走後の最終系列

を記録する。

無駄な高頻度ポーリングは避ける。

### Phase 4: Local Compass連携検討

既存PCKEIBA本線はすぐに置き換えず、UmaConn直取得を独立ラインとして成立させてから段階的に依存を減らす。

---

## 最終結論（2026-08-24 21:42時点）

本日の調査で、当初最大の疑問だった「PC-KEIBA等の専用SIDがないと地方競馬の速報オッズを取得できないのではないか」という懸念は大きく後退した。

ユーザー側の通常32bit PowerShellから:

```text
NVInit("UNKNOWN") = 0
NVRTOpen("0B41", "202608244312") = 0
NVStatus() = 0
NVRead() = 962
```

が正常に動作し、船橋12Rについて発走6分前・3分前・1分前を含むO1時系列まで直接取得できた。

したがって、少なくともO1時系列については:

> **UmaConn / NVDTLabを直接利用した自前速報オッズ取得は技術的に成立する。**

初期の13:41停止はアクセス権不足よりも、配信側の時系列公開タイミングによる可能性が高い。

次の焦点は「取れるかどうか」ではなく、`0B42`確認、配信更新タイミングの把握、自前Readerへの安全な実装へ移る。
