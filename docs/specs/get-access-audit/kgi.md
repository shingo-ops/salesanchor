# KGI — get-access-audit

PO 承認: 2026-10-17 の一任（ideal-state.md）に基づき Opus が確定。PO 個別の y は未取得。

| ID | 基準（○×で判定） | 検証方法 | 結果 |
|---|---|---|---|
| K1 | 一覧の全件取得・ファイル出力の GET が成功したら、data_access_events に event_type=data_export の行が 1 行残る（利用者・パス・接続元つき） | CI の T1・T2 が緑（変更前は赤）。本番で行が現れるかは反映後の利用待ちで観測 | ○（CI: 変更前 35 failed→変更後 37 passed、PR #4411 の pytest 合格）。本番の data_export 行は 2026-10-17 01:41 JST 時点で未発生（利用待ち） |
| K2 | 1 人が 10 分に 500 回を超えて閲覧したら、bulk_read_alert の行がちょうど 1 行と警告ログが残る。500 回以下では 0 行 | CI の T3・T4 が緑（変更前は赤） | ○（同上） |
| K3 | 本番で閲覧の回数を数える処理が失敗していない | 反映後、backend 起動以後に GET /api/v1/ が 1 件以上通り、backend ログの「閲覧回数の追跡に失敗」が 0 件（反映前の基準: /tmp/CC報告ファイル/s6-get-audit/k/before.txt）。本番 Redis のキーを直接数える方法は、Redis のパスワードを扱うため安全装置に止められた（2026-10-17）。そのため Redis 未設定時の黙った素通りとは区別できない（その部分は未確認） | ○（2026-10-17 01:41 JST: 反映後 GET /api/v1/ 5 件・失敗ログ 0 件。Redis 未設定時の素通りとの区別は未確認） |
| K4 | 反映後もエラーが増えず、普段の使い方で誤検知が出ない | backend の Traceback・ERROR、nginx の 5xx が反映前の基準から増えない。観測時間内の bulk_read_alert が 0 行 | ○（反映 2026-10-16 16:24Z 後 17 分・nginx 248 行: Traceback・ERROR 0、5xx 0、大量閲覧の警告 0、bulk_read_alert 0。反映前も 0） |

生出力: /tmp/CC報告ファイル/s6-get-audit/k/（before.txt・after1.txt・after2.txt）、merge/（checks・deploy）。
