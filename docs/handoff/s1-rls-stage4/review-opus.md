# 設計審査の記録 — S1 段階④（クラウド Opus・1 回目）

- 審査した版: release/s1-rls-stage4-design HEAD fdc521ba842bb74484e4e4d8fe2413a2c46105c6（審査役が `git rev-parse HEAD` で一致を確認）。比べた main: feae3a8。
- 実行: クラウドの一回実行（2026-11-06T12:55:39Z〜12:59:40Z、229 秒）。読むだけ。クラウドの見張りに止められた操作 2 件（試験用 PostgreSQL の起動、削除の語を含む grep）。
- 判定: **REVISE**。
- 記録の制約: 実行記録の取得は返事の本文を途中で切って返す。指摘 1〜2 と 3 の冒頭までは読めた。残り（約 3,700 字）は読めていない。読めなかった分は、直した版で 2 回目の審査を流して確かめる。

## 指摘と対応

| # | 重さ | 指摘（審査役の文） | Opus が自分で確かめたこと | 対応 |
|---|---|---|---|---|
| 1 | 重大 | ポリシーに `NULLIF` が無く、文脈を外した接続（`app.tenant_id=''`）で `22P02` になる。運営画面の保存が 500 になる | backend/app/auth/dependencies.py:379 `SET app.tenant_id = ''`。手本 migrations/20261016_180000_add_users_write_rls.sql は全ポリシーが `NULLIF(current_setting('app.tenant_id', true), '')::INTEGER` | design.md §2 の全ポリシーを NULLIF 付きに。試験に「`SET app.tenant_id=''` の後」を追加。K5-1 の数える語に `invalid input syntax for type integer` を追加。recon.md の誤った説明を直した |
| 2 | 重大 | `CREATE POLICY` が冪等でなく、2 回目のデプロイで止まる | scripts/run_all_migrations.sh:14「全マイグレーションは冪等設計」、:25 `ON_ERROR_STOP=1`。手本は各 CREATE の前に `DROP POLICY IF EXISTS` | 各 CREATE POLICY の前に DROP POLICY IF EXISTS。戻し SQL も IF EXISTS。試験に「2 回当ててもエラーなし」を追加 |
| 3 | 中 | 「1 つの移行で入れるので全拒否の間は無い」は保証されない。run_sql にトランザクションの指定が無い | 前例 migrations/20261106_120000_create_discord_server_snapshot_tables.sql:13 `BEGIN;`・:69 `COMMIT;` | 型A・型C とも `BEGIN;`〜`COMMIT;` で囲む。ADR-1067 What 7 も直した |
| 4〜 | 未読 | 記録が途中で切れて読めなかった | — | 2 回目の審査で確かめる |
