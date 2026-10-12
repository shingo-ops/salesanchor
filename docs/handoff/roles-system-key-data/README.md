# roles.system_key の値の設定（一度きり・本 PR では実行しない）

gen_sql.py が、仕様表（5 テナント × オーナー / システム管理者）から precheck.sql / dryrun.sql / apply.sql / rollback.sql / postcheck.sql を生成する。手で直さず、仕様表を直して再生成する。

- 実行の条件: roles.system_key の列を足す PR がデプロイされていること。PO の psql write チケット（都度）。
- 手順: precheck（読み取り）→ dryrun（最後に ROLLBACK）→ apply（1 トランザクション、COMMIT）→ postcheck（読み取り）。戻しは rollback.sql（新たな PO の判断が必要）。
- 件数は書かれた値ではなく、実行時に読み直して照合する。2026-10-05 07:53Z の読み取りでは、各テナントに roles 7 行、オーナー 1、システム管理者 1（どちらも is_system 真）。
- 実行記録（実行時刻・ファイルの sha256・件数）は、実行した時にこの README の末尾へ追記する。未実行。

## 実行記録

- 実行者: claude-opus（PO 承認 2026-10-05、本番データ変更の委任 autoMode.allow による）。
- 許可: 各実行前に PO が `bash scripts/permit-danger.sh "psql write"` を発行した（2 回）。
  - 2026-10-09T21:38:25Z 発行（dryrun 用）
  - 2026-10-09T22:08:09Z 発行（apply 用）
- dryrun.sql
  - sha256: `927b5702b7b80672e2dd852da3e8456cf379ce93c65ee47ffabf1d51de37895a`
  - 実行: 2026-10-09T21:38:43Z 頃
  - 出力: 5 社とも roles total = 7、`DONE: 10 roles updated, 5 audit_log rows`、ROLLBACK。
  - 直後の読み取り確認: system_key 非 NULL 0 件、audit_log 0 行。
- apply.sql
  - sha256: `c1fa1fc140a4844bda14b4a2d7369ca2a651ead444b546260af72ea25b4cf592`
  - 実行: 2026-10-09T22:08:29Z 〜 22:08:30Z
  - 出力: dryrun と同じ（5 社とも roles total = 7、`DONE: 10 roles updated, 5 audit_log rows`）+ COMMIT。
- postcheck（読み取りのみ）
  - tenant_001 / tenant_003: オーナー id1 = owner、システム管理者 id4 = admin
  - tenant_004 / tenant_005 / tenant_006: オーナー id1 = owner、システム管理者 id2 = admin
  - 全て is_system = t、計 10 行。audit_log の該当行は 5。
- 生出力の保存先（ローカル）: `/tmp/CC報告ファイル/next-4012/{dryrun_out.txt,apply_out.txt,postcheck_out.txt}`
