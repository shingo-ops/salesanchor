# roles.system_key の値の設定（一度きり・本 PR では実行しない）

gen_sql.py が、仕様表（5 テナント × オーナー / システム管理者）から precheck.sql / dryrun.sql / apply.sql / rollback.sql / postcheck.sql を生成する。手で直さず、仕様表を直して再生成する。

- 実行の条件: roles.system_key の列を足す PR がデプロイされていること。PO の psql write チケット（都度）。
- 手順: precheck（読み取り）→ dryrun（最後に ROLLBACK）→ apply（1 トランザクション、COMMIT）→ postcheck（読み取り）。戻しは rollback.sql（新たな PO の判断が必要）。
- 件数は書かれた値ではなく、実行時に読み直して照合する。2026-10-05 07:53Z の読み取りでは、各テナントに roles 7 行、オーナー 1、システム管理者 1（どちらも is_system 真）。
- 実行記録（実行時刻・ファイルの sha256・件数）は、実行した時にこの README の末尾へ追記する。未実行。
