# LINE自動書き出し（ADB方式）の現状と実測

対象ADR: 対象外（DB操作・解析ロジックの変更を伴わない。端末側の運用スクリプトの登録）。

## 根拠

- 端末（Galaxy / Android 16）で稼働中の自動書き出しは、Termuxのジョブスケジューラ（job 4203）が
  約15分ごとに `~/bin/line-auto-export` を起動し、proot内の `/root/line-auto-export/auto-export.sh` が
  ADBで端末自身を操作して LINE のトーク履歴を書き出す構成。
- 取り込み側（Termuxへ共有されたファイルを salesanchor へ送る部分）は既存の `tools/termux-line-import`。
  本件はその手前の「書き出しを自動化する部分」で、これまで**端末上にしか存在しなかった**。
- 代替案（ADB不要の自作アプリ）は `tools/line-auto-export-app` で検証中。2026-09-19 時点でロック画面への
  タップが届かず未達（別ブランチ release/line-auto-export-app、evidence-20260919-unlock.md）。

## 実データと検証範囲

2026-09-19 に周期を1時間から15分へ変更し、約11時間・48回を実測した。

| 項目 | 実測 |
| --- | --- |
| 成功 | 44回（92%） |
| 見送り（スマホ使用中） | 2回 |
| 失敗 | 2回（`FAIL export: ...（shortcut）`、`（open_menu）`。いずれも次の回で成功） |
| 発火間隔 | 最小5分 / 最大25分 / 平均15.6分 |
| 1回の所要 | 最小36秒 / 最大67秒 / 平均40秒 |

変更前（1時間周期）の 2026-09-18 は、深夜にワイヤレスデバッグの接続が切れ、01:33〜07:33 の7回が
`ADBに接続できない` で連続失敗した。15分周期では単発の失敗が次の回で埋まる。

## ジョブスケジューラの制約（実測）

- `termux-job-scheduler --period-ms` の下限は 900000（15分）。ツールのヘルプに
  「since Android N, the minimum period is 900,000ms」と明記。
- 実測: `--period-ms 600000`（10分）で登録すると、端末側は `PERIODIC: interval=+15m0s0ms flex=+10m0s0ms`
  として登録する（10分は15分に切り上げられる）。
- 時刻の指定はできない。登録した瞬間が周期の起点になり、1回あたり約0.6分ずつ後ろにずれる。

## 再開・導入

端末が初期化された場合の復旧手順は `tools/line-auto-export/README.md`（配置・ジョブ登録・暗証番号の置き場）。

## 静的検査

シェルスクリプトのため `bash -n` で文法確認済み。ユニットテストは持たない（端末のGUI状態に依存し、
CIから検証できない）。取り込み側の回帰は既存の `tools/termux-line-import/test_android_import.py`。

## 参照（file:line）

実装の所在。いずれもこのブランチの実ファイルで、行番号は 2026-10-09 時点のもの。

- `tools/line-auto-export/auto-export.sh:12` — `MODE=${LINE_AUTO_EXPORT_MODE:-app}`。既定はアプリへの合図。`MODE=adb` で従来のADB方式へ切り戻せる。
- `tools/line-auto-export/auto-export.sh:22` — `flock -n` による多重起動防止。周期実行が重なっても二重に走らない。
- `tools/line-auto-export/README.md:50` — 切替と切り戻しの手順（ADBへ戻す場合は再ペアリングが必要なことを含む）。

設計は [design-app-trigger.md](design-app-trigger.md)（このrecon.mdを参照している）。

### 受信後の既存処理（この設計が前提にしている実装）

- `tools/termux-line-import/client.py:196` — 同じ内容を再共有したときに `stage='send' result='duplicate'` を記録する。書き出しが同じ内容を繰り返しても二重取り込みにならない根拠。
- `tools/termux-line-import/client.py:23` — 1回に送るファイルの上限（`MAX_BYTES`）。
- `tools/termux-line-import/android_parser.py:3-4` — 「本文のバイト完全復元は保証しない」旨の明記。書き出した原本をそのまま渡す根拠。
- `docs/handoff/line-android-import/design.md:1` — 受信後の送信・通知・履歴の設計。本件はその手前の「書き出しの起動方法」だけを変える。
