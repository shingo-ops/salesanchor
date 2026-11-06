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

# 2 回目（クラウド Opus）

- 審査した版: HEAD 2c983ebfcc189c05c8b098d1a7d7f683af8e57e1（審査役が一致を確認）。比べた main: feae3a8。
- 実行: 2026-11-06T13:07:34Z〜13:11:16Z（212 秒・27 手）。読むだけ。クラウドの見張りに止められた操作 2 件（削除の語を含む grep、psql の語を含む grep）。語を外して同じ点を調べ直した。
- 判定: **REVISE**（中 2・軽 4）。1 回目の指摘 1〜3 の直しは正しいと確認された。会社の文脈なしで書く入口の漏れは 0 件（8 表で約 60 か所を照合）。PostgreSQL 16 の仕様との食い違いは 0 件。
- 今回は返事が切れずに全部読めた。

| # | 重さ | 指摘 | Opus が自分で確かめたこと（origin/main 6caae154f） | 対応 |
|---|---|---|---|---|
| 4 | 中 | 戻しの SQL を手で流しても、次のデプロイで RLS がまた付く。④-5 でコードだけ戻すと運営画面の保存が止まる | scripts/run_all_migrations.sh:14「全マイグレーションは冪等設計」で毎回全部流す | design §7・ADR-1067「戻し方」に、PR を戻す → デプロイ → 戻しの SQL の順と、④-5 は 1 つの PR で両方戻すことを書いた |
| 5 | 中 | 移行のファイル名・登録手順が無い。062 が run_all にも migration-test.yml にも無く、全件ドライランで表が無いと落ちる | `grep 062_` が run_all_migrations.sh・migration-test.yml とも 0 件。tenant_discord_config・tenant_settings は migration-test.yml :480・:498・:1824・:1831 に定義あり | design §3 に置き場所・登録・前提の表の足し方を書いた。§4 に試験で前提の移行を当てる順を書いた |
| 6 | 軽 | 自社の行の tenant_id を他社へ付け替える試験が無い | backend/tests/test_users_rls.py:294 の UPDATE と :296 の 42501 | 型A ⑧・型C ⑥ を足した |
| 7 | 軽 | K5-2 が○×で判定できない（④-2 が無い、`tenant 未登録` は正当にも出る、④-4 の点検が動く保証が無い） | client.py:123 `tenant_id 逆引き失敗`、:297 `tenant 未登録のため ticket 発行スキップ` | K5-2 を便ごとの数で判定できる形に書き直した |
| 8 | 軽 | KGI-5 に `invalid input syntax for type integer` が無い | kgi.md の KGI-5 行 | 足した |
| 9 | 軽 | 行番号のずれ | export_inventory_for_sheet.py:108 が接続。discord_guild_config.py の手で入れる INSERT は ea0142e71 で消えた。discord_oauth.py は :215 で文脈 → :221 INSERT（recon の旧記載 :99・:105 は誤り） | recon・design の行番号を origin/main 6caae154f に合わせた |

- 審査役の未確認: 試験用 PostgreSQL では SQL を流していない（クラウドの見張りが止める）。これは各便の CI（Backend Tests・migration-test）で確かめる。
