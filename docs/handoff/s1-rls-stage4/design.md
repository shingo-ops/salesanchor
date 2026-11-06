# 設計 — S1 段階④（public の会社ごとの 8 表の RLS）

> この文書は何か：会社ごとの設定・記録の 8 表に、データベース自身が「他社の行を書かせない（表によっては見せない）」守りを付ける計画です。表ごとに型を選び、5 便に分けて 1 便ずつ本番に出します。

- 状態: **設計案（PO の KGI 承認待ち）**。PO の方向の指示: 2026-11-06 チャット「1」（問い「8 件すべてに守りを足す設計をする【おすすめ】：在庫の動きから順に、入口を1件ずつ調べて設計します。」への答え）。
- 根拠: [docs/handoff/s1-rls-stage4/recon.md](recon.md)（以下 R と書く。R§4 は recon の 4 章）。決定の記録: [ADR-1067](../../adr/ADR-1067-public-tenant-config-tables-rls.md)。前例: ADR-1018・ADR-145。
- 自己審査: 同じ AI（Claude Opus）が Planner と Architect を順に担った。独立した第二者の審査ではない。各便のカードの前にクラウドの設計審査を通す。審査の記録: [review-opus.md](review-opus.md)（1 回目 REVISE、指摘 1〜3 を反映済み）。

## 1. 目的と利用者に見える変化

- 目的: アプリのどこかで会社の絞り込み（`WHERE tenant_id`）を書き忘れても、他社の設定を書き換えたり、他社の記録を読んだりできないようにする。今は SQL の 1 行だけが守りで、DB 側の守りが無い（R§5）。
- 利用者に見える変化: 無い。画面・Discord・Google 予定の動きは変わらない。変わるのは、絞り込みを書き忘れた不具合が起きたときに、DB がその読み書きを止める点。
- 対象外: 全社共用の一覧 6 表・運営の記録 4 表（ADR-1063 便5 の許可一覧に理由付きで載せる）。認証トークンの 3 表（ADR-1018 Decision 6 のまま）。

## 2. 表ごとの型（R§4 の入口から決めた）

| 表 | 型 | 選んだ理由（R の根拠） |
|---|---|---|
| inventory_movements | 型A: 読み書きとも自社だけ（運営は読める） | 本番 0 行（R§3）。本番コードの書込なし。読むのは試験用の道具と手で流す書き出しだけ（R§4-1） |
| discord_server_snapshots | 型A | 書くのは会社の画面だけ（discord_own_server.py:107、:119 で会社の文脈）。読む箇所なし（R§4-2） |
| discord_server_apply_runs | 型A | 同上（:375、:389） |
| tenant_discord_config | 型C: 書込・削除は自社か運営だけ。読取は全行可 | 会社が決まる前に読む: Discord の受け口 client.py:108-126、全社の点検 backend/app/tasks/discord_own_staff_sync.py:24、文脈なしの新しい接続 backend/app/services/discord_role_sync.py:59-60（R§4-3） |
| tenant_discord_ticket_config | 型C | 文脈を張らない接続で読む: client.py:308（_resolve_tenant_id の直後に新しい接続で get_ticket_config）、discord_role_sync.py:67（R§4-4） |
| google_webhook_subscriptions | 型C | 会社が決まる前に読む: verify_channel google_webhook.py:212。全社の期限点検 :395（R§4-5） |
| tenant_llm_budgets | 型C ＋運営画面に運営の文脈を足す | 運営画面が全社を読む（super_admin_llm_budget.py:102・121、tcg_analysis_dashboard.py:526）。運営の保存 :154 は文脈なし（R§4-6） |
| tenant_settings | 型C ＋運営画面に運営の文脈を足す | 段階の切替 super_admin_phase_switch.py:126-129 → phase_gate.py:147 が文脈なしで書く（R§4-7） |

### 2-1. 型A のポリシー（ADR-145 の型から、共用行の道を外したもの）
```sql
BEGIN;
ALTER TABLE public.<表> ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.<表> FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS <表>_select ON public.<表>;
CREATE POLICY <表>_select ON public.<表> FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS <表>_insert ON public.<表>;
CREATE POLICY <表>_insert ON public.<表> FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS <表>_update ON public.<表>;
CREATE POLICY <表>_update ON public.<表> FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS <表>_delete ON public.<表>;
CREATE POLICY <表>_delete ON public.<表> FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
COMMIT;
```
- 3 点の決まり（クラウド審査 2026-11-06 の指摘 1〜3。型A・型C とも）:
  - `NULLIF(…, '')` を必ず付ける。文脈を外した接続は `app.tenant_id=''` を持つ（backend/app/auth/dependencies.py:379）。`''::INTEGER` は NULL にならず `invalid input syntax for type integer`（22P02）で失敗する。同じ穴は migrations/20260605_020000_fix_translation_glossary_rls_cast.sql で一度直した。手本 migrations/20261016_180000_add_users_write_rls.sql も NULLIF 付き。
  - 各 `CREATE POLICY` の前に `DROP POLICY IF EXISTS`。scripts/run_all_migrations.sh は毎回すべての移行を流し（:14）、`ON_ERROR_STOP=1`（:25）なので、2 回目のデプロイで `policy already exists` になると止まる。
  - `BEGIN;`〜`COMMIT;` で 1 つのトランザクションにまとめる。run_sql は `psql < file` で流すだけで、まとめる指定が無い。まとめないと ENABLE の後・ポリシーの前に全拒否の間ができる。前例 migrations/20261106_120000_create_discord_server_snapshot_tables.sql:13・:69。
- tenant_id が空の行は本番に 0 行（R§3）。空の行はどの文脈からも書けない。

### 2-2. 型C のポリシー（ADR-1018 段階③便C users と同じ考え方）
```sql
BEGIN;
ALTER TABLE public.<表> ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.<表> FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS <表>_select ON public.<表>;
CREATE POLICY <表>_select ON public.<表> FOR SELECT USING (true);
DROP POLICY IF EXISTS <表>_insert ON public.<表>;
CREATE POLICY <表>_insert ON public.<表> FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS <表>_update ON public.<表>;
CREATE POLICY <表>_update ON public.<表> FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS <表>_delete ON public.<表>;
CREATE POLICY <表>_delete ON public.<表> FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
```
- 型C は「読めてしまう」守りの穴を残す。8 表に秘密の値の列は無い（R§5-5）。読取まで絞ると、会社が決まる前の入口（R§5-2）が止まる。読取の絞り込みは、入口を「会社を引くだけの関数」に置き換えてから別の段階で考える（本段階の対象外。§8）。

## 3. 便の分け方（1 便ずつ: 出す → 本番で確かめる → 次）

| 便 | 表 | migration 以外の変更 |
|---|---|---|
| ④-1 | inventory_movements | scripts/export_inventory_for_sheet.py:108（origin/main 6caae154f の `engine.connect()`）の接続で、読む前に会社の文脈（`set_config('app.tenant_id', <会社>, false)`）を張る。張らないと型A で 0 行になる（R§6 U4: `DATABASE_URL`＝アプリの接続役） |
| ④-2 | discord_server_snapshots・discord_server_apply_runs | なし |
| ④-3 | tenant_discord_config・tenant_discord_ticket_config | なし（書込の入口はすべて会社の文脈あり。R§4-3・4-4） |
| ④-4 | google_webhook_subscriptions | なし（書込の入口 register・stop・sync は会社の文脈あり。R§4-5、backend/app/routers/calendar.py の呼び出し） |
| ④-5 | tenant_llm_budgets・tenant_settings | 運営画面の書込 2 か所（super_admin_llm_budget.py の upsert、super_admin_phase_switch.py の切替）で、書く直前に `set_operator_context`、`finally` で `reset_operator_context`。段階②b の型（会社の文脈の後に運営の文脈、finally で戻す）。加えて翻訳の見張りの書込 backend/app/services/translation_monitor.py:206 の前に `set_tenant_context`、終わりに `clear_tenant_context`（R§7） |

- 順番の理由: 行と入口が少ない順。④-1 は PO の指示「在庫の動きから」。
- 各便は migration を含むので危険パス。GO は ADR-136 の手順、委任 GO は ADR-1003 の範囲で Opus が出す（段階②b・③と同じ）。
- 移行の置き場所と登録（各便のカードに書く）:
  - ファイル: `migrations/<YYYYMMDD_HHMMSS>_add_<表>_rls.sql`（1 便 1 ファイル。④-2〜④-5 の 2 表の便も 1 ファイルに 2 表）。
  - 登録: scripts/run_all_migrations.sh の末尾に `run_sql migrations/<ファイル>` を 1 行足す（:15「新マイグレーションは末尾の『ここから追加』セクションに追加すること」）。
  - 前提の表（CI の 2 つのジョブ。origin/main 6caae154f で確かめた。表の定義は書き写さない）:
    - inventory_movements・tenant_llm_budgets: migrations/062_create_inventory_movements_and_budget.sql（:88・:151 で作る）は scripts/migrate_inventory_sprint1.py:56 の一覧にあり、本番は run_all_migrations.sh:361 の `run_py`、CI は変更 SQL のジョブ migration-test.yml:1046-1047・全件ドライラン :1906-1907 で流れる。どちらも変更 SQL より前。足すものは無い。
    - tenant_discord_config・tenant_settings: 変更 SQL のジョブの `PUBLIC_SQL` :480・:498、全件ドライラン :1824・:1831 に定義済み。tenant_discord_ticket_config: 変更 SQL のジョブ :491 に定義済み、全件ドライランは run_all:425 で作られる。足すものは無い。
    - google_webhook_subscriptions（④-4）・discord_server_snapshots と discord_server_apply_runs（④-2）: 全件ドライランは run_all（:376・:1217・:1229）で作られる。変更 SQL のジョブには無い（migration-test.yml を表の名で grep して 0 件）。このため ④-2・④-4 のカードで、変更 SQL を流す前に前提の移行を先に流す step を 1 つ足す。前例は migration-test.yml:1299-1338 の「変更 SQL の前提の移行を先に実行」（`contains(steps.detect.outputs.changed_sql, '<その便のファイル>')` で絞る）。④-2 は 20261106_120000_create_discord_server_snapshot_tables.sql（tenants だけを指す。tenants は :187 に定義済み）。④-4 は 077_calendar_sync_mode_and_webhook_subscriptions.sql → 20261103_200000_add_google_calendar_import_sync.sql の順（077 が ALTER する tenant_google_calendar_config は :957 に定義済み）。
- ADR-1063 便5 の許可一覧には、8 表を「段階④で RLS を付ける予定（ADR-1067 便④-N）」の理由で載せておき、各便で 1 行ずつ消す。これで便5 の CI 確かめを先に「落とす形」へ切り替えられる。

## 4. 試験（実 PostgreSQL・アプリの接続役。前例: backend/tests/test_users_rls.py）

- 本物の migration を当てて試す（表の定義を試験に書き写さない。test-schema-dup の見張り）。使い捨て DB に backend/tests/rls_bootstrap.py の `_apply_migration` で、前提の表を作る移行と、その後に形を変える移行を本番と同じ順（run_all_migrations.sh の順。sprint1 は :361）に当ててから、その便の移行を当てる。表ごとの一覧（origin/main 6caae154f で `git grep -l <表> -- migrations` と run_all の行番号から作った。カードを書くときに同じ方法で流し直す）:
  - ④-1 inventory_movements: 062。
  - ④-2 discord_server_snapshots・discord_server_apply_runs: 20261106_120000（run_all:1229）。
  - ④-3 tenant_discord_config: 099_add_discord_guild_config.sql（:413）→ 20260602_200000（:443）→ 20260626_120000（:676）→ 20261105_100000（:1221）→ 20261106_100000（:1225）。tenant_discord_ticket_config: 20260602_120000（:425）→ 20260602_150000（:428）→ 20260602_160000（:431）。20260930_130000（:1056）は行の値を変えるだけで形を変えないので当てない。
  - ④-4 google_webhook_subscriptions: 077（:376）→ 20261103_200000（:1217）。077 は tenant_google_calendar_config を ALTER するので、その前に 076（:375）を当てる。
  - ④-5 tenant_llm_budgets: 062 → 20260604_220000_create_translation_glossary.sql（run_all:518、:142 で ALTER）。066（:33 で ALTER）は run_all に無い（grep 0 件）ので当てない。本番に 066 の列が在るかは reader 鍵で読めず（information_schema が 0 行、AUDIT sha=ddf04b4a4dd4）未確認。RLS の試験は列に依らないので止めない。tenant_settings: 070_add_spreadsheet_phase.sql（:47 で作る。run_all に無い＝grep 0 件。本番の表は在る）→ 080_phase_b_migration.sql（run_all:379、:33 で既定値を変える）→ 20260604_050000_add_tenant_policy_columns.sql（:459、:24 で列を足す）。20260604_160000 は注記で名を出すだけで形を変えない。
  - 一覧の各ファイルが試験の DB で通らないときは、通らない理由（足りない前提の表）を記録して止まり、Opus に戻す（推測で定義を書き足さない）。
- 会社番号は他の試験と重ならない番号（例 984・985）を使う。
- 型A: ①自社文脈で INSERT・SELECT できる ②他社文脈で SELECT が 0 行 ③他社の tenant_id で INSERT が 42501 ④他社行の UPDATE・DELETE が 0 行 ⑤運営文脈で全社の SELECT ができる ⑥文脈なしで SELECT 0 行（新しい接続の場合と、`SET app.tenant_id=''` の後の場合の両方。後者でエラーにならず 0 行）⑦同じ移行を 2 回当ててもエラーにならない ⑧自社文脈で自社の行の tenant_id を他社へ付け替える UPDATE が 42501（前例 backend/tests/test_users_rls.py:293-296）。
- 型C: ①文脈なし・他社文脈で SELECT が全行 ②他社の tenant_id で INSERT が 42501 ③他社行の UPDATE・DELETE が 0 行 ④運営文脈（`app.is_operator='true'`・`app.tenant_id=''`）で他社行の UPDATE が 1 行 ⑤同じ移行を 2 回当ててもエラーにならない ⑥自社文脈で自社の行の tenant_id を他社へ付け替える UPDATE が 42501。
- ④-5 は運営画面 2 本の API 試験（`SET app.tenant_id=''` の済んだ接続で保存が通る・終わった後に `app.is_operator` が空に戻る）。翻訳の見張りの通知の試験 1 本（通知の後に tenant_llm_budgets の時刻が入る）。

## 5. 受入条件（KGI 案は kgi.md の KGI-4〜6）

| 基準 | 検証方法 |
|---|---|
| K4-1 8 表すべてが本番で RLS 有効（ENABLE と FORCE）でポリシー 4 本 | 各便の反映後、reader 鍵の道で `pg_class.relrowsecurity / relforcerowsecurity` と `pg_policies` の件数を読む（読めることを確かめ済み: R§6 U6。反映前の基準値は 8 表とも False/False・0 本） |
| K4-2 反映の前後で 8 表の行数が変わらない | reader 鍵の道で R§3 と同じ集計を反映の前後に流し、表ごとに一致 |
| K5-1 各便の反映後、backend・worker・beat・discord-gateway のログに 42501 と `row-level security` と `invalid input syntax for type integer` が 0 件 | 反映時刻以降の `docker logs` を数える（前例 KGI-2 と同じ数え方） |
| K5-2 各便で触る入口が本番で動く | ④-1: 書き出し台本を 1 社分流し、出た行数が反映前に同じ会社で流した行数と一致し、エラー 0。④-2: 自社の Discord サーバーの記録を画面から 1 回取り、応答 200 で discord_server_snapshots の行が 1 増える（reader 鍵の道で数える）。④-3: 反映時刻以降の discord-gateway のログで `tenant_id 逆引き失敗`（backend/app/discord_gateway/client.py:123）が 0 件、かつ自社サーバーでチケットを 1 件出して作られる（`tenant 未登録`（:297）は登録の無いサーバーからでも正当に出るので数えない）。④-4: 期限の点検を反映後に 1 回手で起こし（カードに起こし方を書く）、そのログにエラー 0、かつ Google の通知の受け口が反映後に 1 回以上 200 を返す（backend のログで数える）。④-5: 運営画面で予算を同じ値で保存して 200、段階の切替の画面を開いて 200 |
| K6-1 アプリの接続役で、許されない読み書きを DB が拒否する | CI の Backend Tests が緑で、PostgreSQL のログに 8 表それぞれ `violates row-level security policy` が 1 件以上 |
| K6-2 便5 の CI 確かめで「RLS の無い会社ごとの表」が 0 | 便④-5 の後、便5 の許可一覧から 8 表がすべて消え、CI が緑 |

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 書込の入口に会社の文脈が無いと、INSERT は 42501 で失敗、UPDATE は静かに 0 行になる（段階②b の教訓） | R§4 と R§7（外の仕組みからの入口）で全入口の文脈を行番号で確かめた。文脈が無い書込は運営画面の 2 か所と翻訳の見張りの 1 か所で、④-5 で足す。各便の反映後に K5-1 で数える |
| 型C で読めてしまう | 秘密の列は無い（R§5-5）。読取の絞り込みは §8 の後続で扱う |
| 会社を作る処理 backend/app/services/tenant.py:1803 が初期行を書けなくなる | :1780 で新しい会社の文脈を張ってから書く。型C の INSERT の条件を満たす。④-5 の試験に「会社を作る」を 1 本入れる |
| 運営の文脈がつなぎの使い回しで残る | finally で reset_operator_context。`get_db` の終わりの clear_tenant_context（database.py:57-61）が二重の守り |
| デプロイ中の約 70 秒、reader 鍵の道が使えない | 数分おいて流し直す（ADR-1024 の運用） |

## 7. 戻し方

- 各便の migration と対の戻し SQL をカードに書く: `BEGIN; DROP POLICY IF EXISTS <表>_select ON public.<表>;`（insert・update・delete も同じ）`ALTER TABLE public.<表> NO FORCE ROW LEVEL SECURITY; ALTER TABLE public.<表> DISABLE ROW LEVEL SECURITY; COMMIT;`。データは変えないので、戻しても行は失われない。
- 戻しの SQL だけを流しても、次のデプロイで scripts/run_all_migrations.sh がすべての移行を流し直すため（:14）、RLS がまた付く。だから戻すときは、戻しの SQL を流すことと、その便の PR を戻す（run_sql の 1 行と移行のファイルが消える）ことを同じ便で行う。
- 順番は「戻しの SQL を流す → K4-1 と同じ読み方で RLS なし・ポリシー 0 本を確かめる → 戻しの PR を main に入れる → デプロイ → もう一度 RLS なし・ポリシー 0 本を確かめる」。理由: デプロイは先にコードを入れ替えて動かし、その後で移行を流す（.github/workflows/deploy.yml の手順「1. Deploy to VPS (code + env + docker compose)」→「2. Run database migrations」）。戻しの PR を先に入れると、古いコードが RLS 付きの表で動く時間ができる。先に RLS を外せば、各便の新しいコード（会社・運営の文脈を張るだけ）は RLS が無くても動くので、止まる時間が無い。
- 戻しの SQL を流してから戻しの PR のデプロイまでの間に別のデプロイが走ると、RLS がまた付く。このため戻しの SQL を流す前に `gh run list --workflow deploy.yml` で走っている・待っているデプロイが 0 件であることを確かめ、戻しの PR はすぐに入れる。デプロイ後の確かめで RLS が付いていたら、戻しの SQL をもう一度流す。
- ④-5 は RLS とコードの両方を含む。コードと RLS を 1 つの戻しの PR で戻し、上と同じ順で流す（コードだけを戻す PR は作らない。コードだけを先に戻すと、RLS が残ったまま運営画面の保存が止まる）。

## 8. 触らない範囲・後続

- 触らない: 全社共用の一覧 6 表・運営の記録 4 表、会社スキーマの表、認証トークン 3 表、画面（frontend）。
- 後続（本段階の対象外。必要になったら PO に聞く）: 型C の 5 表の読取の絞り込み。会社が決まる前の入口を「guild_id や channel から会社だけを返す関数」に置き換える必要がある。

## 9. 外部・過去事例の参照と我々への応用

- 社内の前例（直接の根拠）: ADR-1018 段階①〜③。11 表のうち 8 表に RLS を付け、各段階の反映後に 42501・row-level security が 0 件（docs/specs/tenant-rls/kgi.md KGI-2、2026-10-16 17:30）。段階②b で「書込の入口に運営の文脈が無いと UPDATE が静かに 0 行」を見つけ、入口を全部数えてから出す手順にした。本設計 R§4 はその手順に従った。
- 外部の仕様: PostgreSQL の RLS は `FORCE` を付けると表の持ち主にも効き、superuser と BYPASSRLS の役割には効かない。根拠: PostgreSQL 16 公式文書「5.8. Row Security Policies」（https://www.postgresql.org/docs/16/ddl-rowsecurity.html、2026-11-06 取得）の原文「Superusers and roles with the BYPASSRLS attribute always bypass the row security system when accessing a table. Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with ALTER TABLE ... FORCE ROW LEVEL SECURITY.」と「If no policy exists for the table, a default-deny policy is used」。Context7 は月の上限に達して使えなかったため、起動指示の許可に従い公式文書を直接読んだ。適用: 両方の型で FORCE を付ける。ポリシーを付ける前に ENABLE だけを先に流すと、その間は全拒否になるため、ENABLE・FORCE・ポリシー 4 本を 1 つの移行の中で、`BEGIN;`〜`COMMIT;` で囲んで入れる（§2 の決まり）。
- 外部の導入事例の数値は使わない。理由: 本段階は社内の前例と同じ型の繰り返しで、判断の根拠は社内の実測で足りる。

## 10. PO に決めてもらうこと

- KGI-4〜6（docs/specs/tenant-rls/kgi.md の追記）と、5 便の順番の承認。A 区分（migration を含む）のため PO の承認が要る（docs/STANDARD-WORKFLOW.md §1）。

## 維持の仕組み

- 新しく会社ごとの表を public に作って RLS を付け忘れると、ADR-1063 便5 の CI 確かめが落とす（許可一覧に理由を書かない限り）。
- 型の選び方（型A／型C／付けない）は ADR-1067 に残し、次の表もこの表で判断する。
