# Local Odds Downloader

UmaConn / NVDTLabから地方競馬のO1・O2時系列速報を1レース単位で取得し、UmaConn通常キャッシュに生成された`.rtd`を自前の`archive`へコピーするダウンローダーです。

このディレクトリは実働版の再現・保守用コピーです。認証情報、取得済み`.rtd`、ログ、archive内容は含みません。

## 前提

- NVDTLabは32bit COMです。
- 必ず32bit PowerShellを使用します。
- COM ProgIDは`NVDTLabLib.NVLink`です。
- 初期化は`NVInit("UNKNOWN")`です。
- `0B41`はO1時系列、`0B42`はO2時系列です。
- 1取得ごとに新しい32bit PowerShellプロセスとCOMインスタンスを使用します。
- `NVSetSavePath`は使用しません。
- `m_savepath`が通常保存先と一致しない場合は取得を停止します。

UmaConn通常保存先:

```text
C:\UmaConn\chiho.k-ba\data\
```

## 対応競馬場

| 場コード | 競馬場 |
|---:|---|
| 42 | 川崎 |
| 43 | 船橋 |
| 44 | 大井 |
| 45 | 浦和 |

静的に確認済みの上記4場だけを許可しています。

## 配置と実行

現行BATは実働版と同じ次の配置を前提とします。

```text
C:\KEIBA_AI\local_odds_downloader\
```

実行例:

```bat
C:\KEIBA_AI\local_odds_downloader\01_download_test.bat 20260825 43 12
```

PowerShellを直接呼ぶ場合:

```powershell
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe `
  -NoProfile -STA -ExecutionPolicy Bypass `
  -File C:\KEIBA_AI\local_odds_downloader\scripts\download_local_odds.ps1 `
  -Date 20260825 -TrackCode 43 -Race 12
```

## 取得と保存

各dataspecは次の単位で処理します。

```text
新規32bit PowerShell
  → 新規COMインスタンス
  → NVInit("UNKNOWN")
  → m_savepath確認
  → NVRTOpen
  → NVStatus
  → NVRead（EOFまで）
  → NVClose
```

UmaConn通常キャッシュの原本は削除・移動しません。取得された`.rtd`を、このツール配下の`archive`へコピーし、コピー元とコピー先のサイズおよびSHA-256一致を確認します。

## RACEスケジュール

```powershell
powershell.exe -NoProfile -File C:\KEIBA_AI\local_odds_downloader\scripts\get_race_schedule.ps1 -Date 20260825
```

取得優先順位は次のとおりです。

1. UmaConn通常キャッシュの`RA*.nvd`
2. PC-KEIBA PostgreSQL `public.nvd_ra`のread-only SELECT

出力には`post_datetime`と`race_key`が含まれ、30分前・15分前・5分前の取得スケジュール計算に利用します。

地方RAでは、外側の`.nvd`ファイル名の日付と内部レコードの開催日が一致しない場合があります。開催日の判定では、固定長RAレコード内部の開催日を正としてください。

現行実働ロジックをそのまま保存しているため、`get_race_schedule.ps1`の候補ファイル探索は最初に`RANV<指定日>*.nvd`を使用します。将来日レースがそれ以前の日付名のRAファイルに収録されている場合、現行版はPostgreSQL fallbackを使用します。RA探索を拡張する際も、最終判定は必ず内部RAレコードの開催日で行ってください。

PostgreSQL fallbackは`default_transaction_read_only=on`でSELECTのみ実行します。接続資格情報はローカルの`pgpass.conf`を使用し、このリポジトリには含めません。

## 日次スケジューラ

当日のRACEスケジュールから、各レースの30分前・15分前・5分前に既存ダウンローダーを自動実行します。

- 起動時点より過去の予定は`SKIPPED`とし、遡及取得しません。
- 取得中はコンソールとタイトルに`ODDS DOWNLOADING`を表示します。
- 対象開催の最終レース発走10分後に自動終了します。

通常起動:

```bat
02_run_daily_scheduler.bat
```

dry-run:

```bat
02_run_daily_scheduler.bat -DryRun
```

## 安全設計

- COM生成と`NVRTOpen`は30秒、取得プロセス全体は180秒で監視します。
- `NVRead`は最大1000回です。
- `NVRTOpen`失敗時は後続の読取処理へ進みません。
- `finally`から`NVClose`を試行します。
- `NVFiledelete`、投票系API、`NVSetSavePath`は使用しません。
- servicekey、ukey、password、token等はコード・設定へ保存しません。

## Git管理対象外

このディレクトリの`.gitignore`で、次を除外します。

- `logs/**`
- `archive/**`
- `*.rtd`、`*.nvO1`、`*.nvO2`
- 実行時一時ファイル
- `.env`、`pgpass.conf`等の認証情報候補
