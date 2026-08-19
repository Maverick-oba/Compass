# UmaConn / NVDTLab 直接アクセス調査メモ

更新日: 2026-08-19

## 1. 調査目的

地方競馬DATAの取得について、PC-KEIBAへの依存を将来的に減らし、以下を実現できるか調査した。

- タイマーで `RACE` データを自動受信する
- 受信後に Local Compass のデータ生成・サーバーアップロードへつなげる
- PC-KEIBA有料会員機能に依存せず、オッズデータを自前取得・利用する
- 既存のPCKEIBA PostgreSQL依存は一気に外さず、段階的に移行する

現時点の結論として、**PC-KEIBAを介さず、32bitクライアントから `NVDTLabLib.NVLink` COMを直接操作し、地方競馬DATAの `.nvd` ファイルを取得できることを実機確認済み**。

---

## 2. UmaConn保存領域の確認

レジストリから以下の設定を確認した。

```text
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\NAR-VAN Data Lab
```

主な設定:

```text
server_info
  dataport
  dataport2
  datahost
  datahost2
  datapath
  datapath2

uid_pass
  saveflag
  savepath
  servicekey
  ukey
  installdate
  installpath
```

実機の保存先:

```text
C:\UmaConn\chiho.k-ba\data\
```

認証情報（servicekey等）は本資料には記載しない。

---

## 3. `.nvd` キャッシュ構造

UmaConnのキャッシュ領域:

```text
C:\UmaConn\chiho.k-ba\data\cache\2026\
```

ここには以下のような日次ファイルが存在する。

```text
RANV...
SENV...
HRNV...
O1NV...
O2NV...
O3NV...
O4NV...
O5NV...
O6NV...
H1NV...
H6NV...
HANV...
OANV...
WFNV...
```

`.nvd` の先頭シグネチャは `PK 03 04` であり、実体はZIP形式だった。

例:

```text
RANV2026081820260818231018.nvd
  -> ZIP
     -> 18.txt
```

つまり、少なくとも確認したRA/SE/O1については、独自暗号バイナリではなく、**ZIP内の固定長テキストレコード**で構成されている。

---

## 4. RA（レース情報）の確認

対象:

```text
RANV2026081820260818231018.nvd
```

ZIP内:

```text
18.txt
展開後サイズ: 118,296 bytes
```

実測:

```text
行数               = 93
1行の文字数        = 1131文字
Shift-JIS実バイト数 = 1270 bytes
```

計算:

```text
1270 bytes x 93行 = 118,110
CRLF 2 bytes x 93 = 186
合計               = 118,296 bytes
```

よってRAは、

```text
1レコード = 1270 bytes + CRLF
```

の固定長テキストであることを確認した。

### PCKEIBA nvd_raとの対応

`public.nvd_ra` の主キー:

```text
kaisai_nen
kaisai_tsukihi
keibajo_code
race_bango
```

raw先頭部は、DB列順と素直に対応している。

```text
record_id
 data_kubun
 data_sakusei_nengappi
 kaisai_nen
 kaisai_tsukihi
 keibajo_code
 kaisai_kai
 kaisai_nichime
 race_bango
 ...
```

### 差分配信の確認

2026-08-18作成のRA rawは93行だったが、当日のPCKEIBA `nvd_ra` は58件。

rawの `data_kubun` 内訳:

```text
data_kubun=7 : 58件
data_kubun=2 : 35件
```

内容を見ると、

```text
data_kubun=7 -> 2026-08-18開催分
data_kubun=2 -> 2026-08-20 / 08-21など将来開催分
```

が含まれていた。

さらに複数日の `RANV*.nvd` を累積し、

```text
開催年 + 開催月日 + 場 + R
```

でユニーク化すると、

```text
0820 = 48
0821 = 36
```

となり、PCKEIBA側の

```text
0818 | data_kubun=7 | 58
0820 | data_kubun=2 | 48
0821 | data_kubun=2 | 36
```

と一致した。

したがってRA `.nvd` は、完全スナップショットではなく、**作成日ごとの追加・更新差分を蓄積する形式**と考えるのが妥当。

---

## 5. SE（出走馬情報）の確認

対象:

```text
SENV2026081820260818231019.nvd
```

ZIP内:

```text
18.txt
展開後サイズ: 538,350 bytes
```

実測:

```text
行数        = 970
1行文字数   = 377
1行bytes    = 553
```

計算:

```text
553 x 970 = 536,410
CRLF       =   1,940
合計       = 538,350
```

よってSEは、

```text
1レコード = 553 bytes + CRLF
```

の固定長テキスト。

### nvd_seとの照合

raw先頭3頭とPCKEIBA `nvd_se` を照合し、以下が一致した。

- record_id
- data_kubun
- data_sakusei_nengappi
- 開催年/月日
- 競馬場
- 開催回/日目
- R番号
- 枠番
- 馬番
- 血統登録番号
- 馬名
- 性別/馬齢
- 調教師
- 馬主
- 負担重量
- 騎手
- 馬体重/増減
- 着順
- 単勝オッズ
- 人気
- 後3F

つまりSEについても、UmaConn rawからPCKEIBA `nvd_se` へ固定位置展開されていることを確認できた。

---

## 6. O1（単勝・複勝・枠連系）の確認

対象:

```text
O1NV2026081820260818231019.nvd
```

ZIP内:

```text
18.txt
展開後サイズ: 55,796 bytes
```

実測:

```text
行数      = 58
1行文字数 = 960
1行bytes  = 960
```

計算:

```text
960 x 58 = 55,680
CRLF     =    116
合計     = 55,796
```

よってO1は、

```text
1レコード = 960 bytes + CRLF
```

の固定長ASCII系データ。

### nvd_o1列構造

PCKEIBA `nvd_o1`:

```text
record_id
 data_kubun
 data_sakusei_nengappi
 kaisai_nen
 kaisai_tsukihi
 keibajo_code
 kaisai_kai
 kaisai_nichime
 race_bango
 happyo_tsukihi_jifun
 toroku_tosu
 shusso_tosu
 hatsubai_flag_tansho
 hatsubai_flag_fukusho
 hatsubai_flag_wakuren
 fukusho_chakubarai_key
 odds_tansho      varchar(224)
 odds_fukusho     varchar(336)
 odds_wakuren     varchar(324)
 hyosu_gokei_tansho varchar(11)
 hyosu_gokei_fukusho varchar(11)
 hyosu_gokei_wakuren varchar(11)
```

列幅合計が960 bytesとなり、raw実測値と一致。

したがって、PC-KEIBA有料会員機能を使わず、**UmaConn直取得したO1 rawを自前Parserで読むことが可能**と判断できる。

O2〜O6も同じ方法で調査可能。

---

## 7. PC-KEIBAが利用しているDLLの特定

Process MonitorでPC-KEIBAのデータベースプロセスを確認。

```text
Process: Com.Pckeiba.Database.exe
Version: 5.0.8.7
Architecture: 32-bit
```

ロードモジュールとして以下を確認した。

```text
C:\Windows\SysWOW64\NVDTLab.dll
Product : NVDTLab Module
Company : RateBuster Co.,Ltd
Version : 3.5.4.0
```

また中央用として、

```text
C:\Windows\SysWOW64\JVDTLAB\JVDTLab.dll
```

もロードされていた。

構造は概ね、

```text
Com.Pckeiba.Database.exe
  ├─ JVDTLab.dll -> JRA-VAN
  └─ NVDTLab.dll -> 地方競馬DATA / UmaConn
```

と考えられる。

---

## 8. NVDTLab COM登録

レジストリから以下を確認。

```text
ProgID:
NVDTLabLib.NVLink

CLSID:
{F726BBA6-5784-4529-8C67-26E152D49D73}

TypeLib:
{6B4C2ED0-BB26-483E-A264-1CA2820A6F3A}

TypeLib name:
NVDTLabLib

DLL:
C:\Windows\SysWOW64\NVDTLab.dll

ThreadingModel:
Both
```

COMは32bit側に登録されている。

---

## 9. COMオブジェクト直接生成

32bit PowerShellを起動。

```powershell
& "$env:WINDIR\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
```

確認:

```powershell
[Environment]::Is64BitProcess
```

結果:

```text
False
```

COM生成:

```powershell
$nv = New-Object -ComObject NVDTLabLib.NVLink
```

正常生成を確認。

表示された主なプロパティ:

```text
m_NVLinkVersion       = 0354
m_saveflag            = 1
m_savepath            = C:\UmaConn\chiho.k-ba\data\
m_TotalReadFilesize   = 0
m_CurrentReadFilesize = 0
```

認証キーは記載しない。

---

## 10. TypeLibから確認した公開API

TypeLib内の型:

```text
0 : INVLink
1 : INVLinkEvents
2 : NVLink
```

`INVLink` から取得した主なメソッド:

```text
NVSetSavePath(savepath)
NVInit(sid)
NVClose()
NVSetUIProperties()
NVOpen(dataspec, fromdate, option, readcount, downloadcount, lastfiletimestamp)
NVStatus()
NVRead(buff, size, filename)
NVRTOpen(dataspec, key)
NVCancel()
NVFiledelete(filename)
NVSetServiceKey(servicekey)
NVSetSaveFlag(saveflag)
NVSkip()
NVGets(buff, size, filename)
NVStarts(recordspec, code, fromdate, todate, count, bstr)
NVWatchEvent()
NVWatchEventClose()
```

その他、動画・コースファイル・投票連携系APIも存在する。

今回の調査対象はデータ取得系のみ。

---

## 11. NVInit / NVClose 直接実行確認

32bit PowerShellから直接実行。

```powershell
$rc = $nv.NVInit("UNKNOWN")
```

結果:

```text
NVInit rc = 0
```

終了:

```powershell
$rc2 = $nv.NVClose()
```

結果:

```text
NVClose rc = 0
```

PC-KEIBAを介さず、COMの初期化・終了が正常動作した。

---

## 12. テスト保存先分離

既存UmaConn領域を触らないよう、以下をテスト保存先として設定。

```text
C:\UmaConn_test\direct\
```

```powershell
$nv.NVSetSavePath("C:\UmaConn_test\direct\")
```

結果:

```text
NVSetSavePath rc = 0
m_savepath = C:\UmaConn_test\direct\
```

PC-KEIBAはこの直接取得テスト中は終了して実施した。

---

## 13. NVOpenによるRACE直接取得成功

実施:

```powershell
$nv.NVInit("UNKNOWN")

$readcount = 0
$downloadcount = 0
$lastfiletimestamp = ""

$result = $nv.NVOpen(
    "RACE",
    "20260818000000",
    1,
    [ref]$readcount,
    [ref]$downloadcount,
    [ref]$lastfiletimestamp
)
```

結果:

```text
NVOpen rc        = 0
readcount        = 14
downloadcount    = 14
lastfiletimestamp = 20260818231021
```

`NVStatus()`:

```text
14
```

テスト保存先に14ファイルが実際に生成された。

```text
WFNV...
SENV...
RANV...
OANV...
O6NV...
O5NV...
O4NV...
O3NV...
O2NV...
O1NV...
HRNV...
HANV...
H6NV...
H1NV...
```

最後に、

```powershell
$nv.NVClose()
```

結果:

```text
0
```

これにより、**PC-KEIBAを介さず、NVDTLab COMからRACEデータ一式を直接ダウンロードできることを実証した**。

---

## 14. 現在の到達点

### 確認済み

- `NVDTLabLib.NVLink` COMは実在する
- 32bitプロセスから直接生成可能
- `NVInit` / `NVClose` 正常動作
- `NVSetSavePath` で保存先を分離可能
- `NVOpen("RACE", ...)` により指定日のRACEデータ取得成功
- RA / SE / O1〜O6など14ファイルを直接取得可能
- RAは1270 bytes固定長
- SEは553 bytes固定長
- O1は960 bytes固定長
- `.nvd` はZIPで、内部は日付 `.txt`
- RA/SE/O1はPCKEIBA `nvd_ra` / `nvd_se` / `nvd_o1` と対応する
- RAは差分配信方式であり、複数日のrawを累積するとDB件数と一致する

### 未確認

- `NVOpen option` 各値の正式仕様
- `dataspec` の全種類
- `NVRTOpen` の正式用途と引数仕様
- `NVRead` / `NVGets` の運用要否
- O2〜O6の詳細Parser
- PCKEIBAがrawをDBへUPSERTする際の全更新ルール
- タイマー運用時の最適取得頻度
- Local Compass既存生成処理の依存テーブル全棚卸し

---

## 15. 今後の開発方針

目的は2系統に分ける。

### A. Local Compass自動更新

最終イメージ:

```text
Windowsタイマー / 自前ランチャー
  ↓
NVDTLabLib.NVLink
  ↓
RACE受信
  ↓
Local Compass用データ生成
  ↓
JSON生成
  ↓
サーバーアップロード
```

ただし現行Local CompassはPCKEIBA PostgreSQLへの依存が大きいため、一気に置き換えない。

当面は、

```text
UmaConn直取得
  ↓
既存PCKEIBA / 既存Local Compass処理を可能な限り維持
```

し、依存箇所を棚卸ししながら段階的に自前化する。

### B. オッズ自前化

オッズは元々PC-KEIBA有料会員機能を使っていないため、既存処理との結合が弱い。

そのため先に、

```text
UmaConn直取得
  ↓
O1〜O6 .nvd
  ↓
自前Parser
  ↓
オッズ利用ロジック / JSON
```

を独立系として構築するのが安全。

O1については固定長960 bytesとDB列対応まで確認済みなので、自前化の入口はすでに成立している。

---

## 16. 推奨する次の作業順

1. Local Compass現行生成処理が参照している `nvd_*` テーブルを棚卸しする
2. UmaConn直Downloaderを小さな32bitプログラムとして固定化する
3. 取得ログ・戻り値・ファイル数・最終timestampを保存する
4. Windowsタイマーから安全に定時実行できる形にする
5. O1〜O6のParserを別系統で作る
6. オッズ利用を先に自前化する
7. RACE側はPCKEIBA依存を保ちながら段階的に差し替える
8. 最終的に `raw -> 自前Parser -> PostgreSQL/JSON` へ移行可能か判断する

---

## 17. 運用上の注意

- NVDTLabは32bit COMのため、呼び出し側も32bit前提で設計する
- PC-KEIBAとの同時アクセスは避けて検証する
- 本番UmaConn保存先を直接使わず、開発中はテスト保存先を使う
- 認証キー・利用キーはログやGitHubへ保存しない
- `data_kubun` や `option` の意味は推測で決め打ちせず、実測・仕様確認を優先する
- Local Compass本番系は、直取得基盤が安定するまで既存経路を維持する

---

## 18. 現時点の結論

今回の調査により、UmaConn/NVDTLabはPC-KEIBA専用のブラックボックスではなく、Windows上に登録された32bit COM APIとして直接操作できることが確認できた。

さらに、`NVOpen("RACE", ...)` から実際にRA/SE/O1〜O6等の `.nvd` を取得できたため、以下は技術的に実現可能と判断する。

```text
自前タイマー
  ↓
UmaConn / NVDTLab直接取得
  ↓
地方競馬raw
  ↓
自前オッズ処理
  ↓
将来的なLocal Compass自動生成・アップロード
```

今後は「PCKEIBAをすぐ外す」のではなく、まずオッズを独立自前化し、RACE側は既存PCKEIBA依存を保ちながら段階的に移行する方針とする。
