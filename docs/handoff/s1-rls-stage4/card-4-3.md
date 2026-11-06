# 実装カード 便④-3 — public.tenant_discord_config・public.tenant_discord_ticket_config に RLS（型C）

- 状態: 草案（クラウド設計審査の前）。PO の実装承認は design.md 冒頭（2026-11-06「1」: KGI-4〜6 と 5 便の順番）。完走の指示は PO 2026-11-07 チャット「PRマージ、デプロイまで完走させてくれ」。便④-3 へ進むことは PO 2026-11-07 04:2x JST チャット「1」（便④-2 の報告の選択肢 1「このまま次の 3 つの表へ進む」）。
- 根拠の版: origin/main 468a224c5（2026-11-07 04:20 JST に fetch。便④-2 #5224 の合流後）。行番号はすべてこの版。
- 設計: [design.md](design.md) §2（表ごとの型: 2 表とも型C）・§2-2（型C のポリシー）・§3（④-3 行と「前提の表」）・§4（試験 型C ①〜⑥）・§5（K4-1・K4-2・K5-1・K5-2）・§7（戻し方）。現状: [recon.md](recon.md) R§4-3・R§4-4。手本: 便④-2 [card-4-2.md](card-4-2.md) と、合流済みの backend/tests/test_discord_server_records_rls.py。
- 実装ブランチ: `release/s1-rls-stage4-bin3`（origin/main から作った。カードはこのブランチに Opus が置く）。1 便 1 PR。PR は Draft で起票する。

## 1. 触るファイル（これ以外は触らない）

| # | ファイル | 変更 |
|---|---|---|
| 1 | `migrations/20261107_130000_add_discord_config_rls.sql` | 新規。§2 の SQL を一字一句この内容で作る |
| 2 | `scripts/run_all_migrations.sh` | 末尾（今の最終行 :1243 `run_sql migrations/20261107_120000_create_staff_join_invites.sql` の次の行）に §3 の 2 行を足す |
| 3 | `backend/tests/test_discord_config_rls.py` | 新規。§5 |
| 4 | `docs/handoff/s1-rls-stage4/card-4-3.md` | このカード（Opus が置く。実装役は触らない） |
| 5 | `.claude-pipeline/active-work.d/release-s1-rls-stage4-bin3.md` | 台帳（Opus が本店の写しに置く。実装役は触らない） |

- 実装の直前に `git ls-tree --name-only origin/main migrations/ | tail -3` を流し、`20261107_130000` より後の名前の移行、または同じ名前の移行が main に入っていたら止まって Opus に戻す（名前を自分で変えない）。
- `.github/workflows/migration-test.yml` は触らない（§4。前提の表は変更 SQL のジョブに定義済み）。
- 触らない: プログラム（backend/app 配下すべて。書込の入口はどれも会社の文脈がある。§6）、`backend/tests/conftest.py`、`backend/tests/rls_bootstrap.py`、frontend、他の表。

## 2. 移行 SQL（design §2-2 の型C を 2 表の名で埋め、1 つの取引にまとめたもの）

```sql
-- ADR-1067 段階④ 便④-3: public.tenant_discord_config と public.tenant_discord_ticket_config に会社ごとの RLS（型C）を付ける。
-- 読む: 全行（Discord の受け口が会社を決める前に guild_id から会社を引くため。design.md §2）。書く: 自社の会社文脈か運営文脈だけ。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-2。
BEGIN;
ALTER TABLE public.tenant_discord_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_discord_config FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_discord_config_select ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_select ON public.tenant_discord_config FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_discord_config_insert ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_insert ON public.tenant_discord_config FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_config_update ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_update ON public.tenant_discord_config FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_config_delete ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_delete ON public.tenant_discord_config FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
ALTER TABLE public.tenant_discord_ticket_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_discord_ticket_config FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_discord_ticket_config_select ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_select ON public.tenant_discord_ticket_config FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_discord_ticket_config_insert ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_insert ON public.tenant_discord_ticket_config FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_ticket_config_update ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_update ON public.tenant_discord_ticket_config FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_ticket_config_delete ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_delete ON public.tenant_discord_ticket_config FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
```

## 3. run_all_migrations.sh に足す 2 行

```bash
# ADR-1067 段階④ 便④-3: tenant_discord_config・tenant_discord_ticket_config に会社ごとの RLS（型C: 読取は全行・書込は自社か運営）。冪等・1 取引
run_sql migrations/20261107_130000_add_discord_config_rls.sql
```

- 本番の順: 2 表を作る・形を変える移行（099 :413、20260602_120000 :425、150000 :428、160000 :431、20260602_200000 :443、20260626_120000 :676、20261105_100000 :1221、20261106_100000 :1225）はすべて本 SQL（末尾 :1245 になる）より先に流れる。
- 移行を流す役は jarvis（本番で rolsuper=t・rolbypassrls=t。2026-11-07 04:21 JST に読んだ）。後の移行が 2 表を UPDATE しても RLS に止められない。

## 4. CI の前提の表（足す step は無い）

- 変更 SQL のジョブ: `.github/workflows/migration-test.yml` の `PUBLIC_SQL`（:478 から）で、tenant_discord_config は :480-486、tenant_discord_ticket_config は :491-495 に定義済み。どちらも tenant_id 列を持つ。ポリシーが参照する列は tenant_id だけなので、この最小の定義の上で本 SQL が通る。
- 全件ドライラン: run_all の順で 2 表が先に作られる（§3）。
- このため便④-2 のような「前提の移行を先に実行」の step は足さない。

## 5. 試験 backend/tests/test_discord_config_rls.py（新規）

手本: 合流済みの backend/tests/test_discord_server_records_rls.py（便④-2。:24 の skipif、:38 `_GRANT_DDL`、:80-121 の `_fresh()`、:122 `_admin_exec`、:130 `_ctx_conn`、:143 `_sqlstate`）。同じ形で書く。

- 会社番号: 974（自社）・975（他社）。backend/tests で未使用（`git grep -n -w 974 origin/main -- backend/tests` と `git grep -n -w 975 origin/main -- backend/tests` がどちらも 0 件。468a224c5 で確かめた）。実装の前にもう一度流し、1 件でもあれば止まって Opus に戻す。
- `_fresh()` の中身（使い捨て DB `dcf_rls_<hex12>`、app_engine は `pool_size=1, max_overflow=0`）:
  1. admin の接続で `_ensure_public_users(conn)`（rls_bootstrap.py:213）。続けて admin で `INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) VALUES (974, 'tenant_974', 'T974', 'T974', TRUE), (975, 'tenant_975', 'T975', 'T975', TRUE)`。
  2. 本物の移行を本番と同じ順で `_apply_migration(admin_engine, <名>)` で当てる（表の定義を試験に書き写さない）: `099_add_discord_guild_config.sql` → `20260602_120000_add_discord_ticket_config.sql` → `20260602_150000_add_discord_scale_channels.sql` → `20260602_160000_add_discord_role_names.sql` → `20260602_200000_add_discord_config_connected_by_staff.sql` → `20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql` → `20261105_100000_tenant_discord_config_purpose.sql` → `20261106_100000_tenant_discord_config_purpose_pk.sql`。
     - 099 と 20260602_120000 は `tenant_[0-9]+` の置き場を回す部分を持つが、使い捨て DB にはその置き場が無いので 0 回まわるだけ（rls_bootstrap.py:35-38 の `_TENANT_BOOTSTRAP_MIGRATIONS` に 2 本とも無いので、`_apply_migration` は置き場の指定なしで流せる）。
     - 20260930_130000 は行の値と既定値を変えるだけで形を変えないので当てない（design §4）。
  3. admin で `_GRANT_DDL`（便④-2 の試験と同じ 2 行）。
  4. admin で各社 1 行ずつ両方の表に INSERT（974 と 975）。tenant_discord_config: `(tenant_id, purpose, guild_id)` = `(974, 'customer', 'g974')`・`(975, 'customer', 'g975')`。tenant_discord_ticket_config: `(tenant_id, ticket_category_id, ticket_button_channel_id)` = `(974, 'c974', 'b974')`・`(975, 'c975', 'b975')`。
  5. `_apply_migration(admin_engine, "20261107_130000_add_discord_config_rls.sql")`。
  - 1〜2 のどれかが使い捨て DB で通らないときは、通らない理由を記録して止まり、Opus に戻す（推測で定義を書き足さない）。
- 試験（design §4 型C ①〜⑥ を 2 表それぞれに。`@pytest.mark.parametrize` で表名を回してよい）。すべて app_engine（アプリの接続役 salesanchor_app・NOBYPASSRLS）で行う:
  - ① 文脈なし（新しい接続）で SELECT すると 974・975 の両方の行が見える（2 行）。975 の文脈でも 974 の行が見える。同じ接続で `SET app.tenant_id = ''` の後の SELECT もエラー（22P02）にならず 2 行。
  - ② 974 の文脈で tenant_id=975 の INSERT が 42501（tenant_discord_config は purpose='own'・guild_id='x975' で入れる。主キー (tenant_id, purpose) の重複で落ちないように）。
  - ③ 974 の文脈で 975 の行への UPDATE（tenant_discord_config は guild_id、ticket は ticket_category_id だけ変える）・DELETE が 0 行。後で admin で 975 の行が元のまま 1 行あることを確かめる。
  - ④ 運営の文脈（`app.is_operator='true'`・`app.tenant_id=''`）で 975 の行の UPDATE が 1 行（取引は最後に ROLLBACK してよい）。
  - ⑤ 同じ移行をもう一度当ててもエラーにならず、`pg_policies` の本数が 2 表とも 4 のまま。
  - ⑥ 974 の文脈で自社の行の tenant_id を 975 へ付け替える UPDATE が 42501。
  - ⑦ 書込の入口と同じ文脈の張り方で、自社の行の upsert が通る: app_engine の接続で `SET app.tenant_id = '974'` と `SET app.is_operator = ''`（backend/app/auth/dependencies.py:252・:256 の get_current_tenant と同じ 2 文。set_config でなく SET）を流し、backend/app/routers/discord_oauth.py:220-228 と同じ `INSERT … ON CONFLICT (tenant_id, purpose) DO UPDATE SET guild_id = EXCLUDED.guild_id, connected_by_staff_id = EXCLUDED.connected_by_staff_id, updated_at = NOW()`（既にある 974/customer の行に当たり UPDATE 側を通る）と、backend/app/routers/discord_ticket_config.py:146-167 と同じ `INSERT … ON CONFLICT (tenant_id) DO UPDATE SET …` が、どちらもエラー無く通り、admin で値が変わったことを確かめる。最後に同じ接続で `SET app.tenant_id = ''` に戻す。
    - 入れる値: tenant_discord_config は `(tid, purpose, guild_id, staff_id)` = `(974, 'customer', 'g974x', NULL)`（'g975' と重ならない新しい値。uq_tenant_discord_config_guild_id に当たらない）。tenant_discord_ticket_config は `(tid, category_id, button_channel_id, staff_role_id, welcome_template, small_channel_id, large_channel_id, small_role_name, large_role_name)` = `(974, 'c974x', 'b974x', NULL, 'w974', NULL, NULL, 'Member', 'Partner')`（NOT NULL の welcome_template・small_role_name・large_role_name に値を入れる。20260602_120000:10、20260602_160000:14-15）。
    - 確かめ: admin で 974/customer の guild_id が 'g974x'、974 の ticket_category_id が 'c974x' になっている。
- 既にある試験への影響（`git grep -l -E "tenant_discord_(ticket_)?config" origin/main -- backend/tests` = 14 本: conftest.py と test_discord_*.py 13 本）:
  - conftest.py は 2 表を SQLite に作り、`public.` を外す書き換え（:321-322）と後片付けの DELETE（:1796）も SQLite の上で行う。RLS は SQLite に無い。触らない。
  - test_discord_oauth_rls.py は実 PostgreSQL を使うが、作る表は public.tenants と会社の置き場の audit_logs だけ（:46・:69）。2 表は作らず、本 PR の移行も当てない。影響なし。
  - 残りの 12 本は conftest.py の SQLite の DB を使う（実 PostgreSQL の接続先を持たない。test_discord_own_server.py:290 の "postgresql://unused" は接続しない文字列）。影響なし。触らない。

## 6. 書込の入口（触らないが、文脈があることの根拠。origin/main 468a224c5）

| 表 | 書込 | 文脈 |
|---|---|---|
| tenant_discord_config | backend/app/routers/discord_oauth.py:221 INSERT … ON CONFLICT DO UPDATE | :215 `set_tenant_context`（SET。取引をまたいで残る） |
| tenant_discord_config | backend/app/routers/discord_guild_config.py:104・:167 DELETE | :99・:162 `Depends(get_current_tenant)` |
| tenant_discord_ticket_config | backend/app/routers/discord_auto_setup.py:391 INSERT … ON CONFLICT DO UPDATE | :91 `Depends(get_current_tenant)`。書込の後 :436 commit・:437 `reset_tenant_context` |
| tenant_discord_ticket_config | backend/app/routers/discord_ticket_config.py:147 INSERT … ON CONFLICT DO UPDATE | :141 `Depends(get_current_tenant)` |

- `git grep -n -E "tenant_discord_(ticket_)?config" origin/main -- backend/app scripts` の 52 行で、INSERT・UPDATE・DELETE は上の 5 か所だけ（残りは SELECT と説明文と run_all の登録）。
- 文脈なしで読む箇所（型C で読取を全行にした理由）: backend/app/discord_gateway/client.py:101-126 `_resolve_tenant_id`、:308 `get_ticket_config`（:294 の直後に新しい接続）、backend/app/services/discord_role_sync.py:59-66、backend/app/tasks/discord_own_staff_sync.py:22-24。

## 7. 合格の条件（実装役が自分で確かめて生出力をファイルに残す）

| 基準 | 確かめ方 |
|---|---|
| §1 の 1〜3 以外に差分が無い（4・5 は Opus） | `git diff origin/main...HEAD --name-only` |
| 移行 SQL が §2 と一字一句同じ | `diff` で 0 行 |
| run_all の差分が §3 の 2 行の追加だけ | `git diff origin/main...HEAD -- scripts/run_all_migrations.sh` |
| CI の Backend Tests・migration-test・ADR index ほか必須チェックが全部緑 | `gh pr checks <PR>` |
| 新しい試験が CI で実行されて通っている（skip でない） | CI の PostgreSQL のログに `violates row-level security policy for table "tenant_discord_config"` と `"tenant_discord_ticket_config"` が出る（便④-1・④-2 で使った確かめ方） |
| i18n・UI は触らない | 差分に frontend が無い |

## 8. 本番の確かめ（Opus が反映の後に行う。実装役は行わない）

基準値（2026-11-07 04:21 JST、反映前に Opus が読んだ）: 2 表とも RLS f/f・ポリシー 0 本・持ち主 jarvis。tenant_discord_config: 会社 1 customer 1・会社 1 own 1・会社 4 customer 1・会社 6 customer 1（計 4）。tenant_discord_ticket_config: 会社 1・4・6 が各 1（計 3）。

- 読む道: 基準値・K4-1・K4-2 は design §5 のとおり reader 鍵の道（docs/handoff/ai-readonly-db-path/usage.md）で読む。無制限鍵で本番 DB を読むことはしない。reader 鍵の道で読めない項目があったら、そこで止まって PO に戻す。
- K4-1: 2 表とも relrowsecurity / relforcerowsecurity が t/t、ポリシー各 4 本。
- K4-2: 2 表の会社ごとの行数が上の基準値と同じ。
- K5-1: 反映時刻以降の backend・celery-worker・celery-beat・discord-gateway のログで `42501`・`row-level security`・`invalid input syntax for type integer` が 0 件。加えて discord-gateway のログで `tenant_id 逆引き失敗`（client.py:124）が 0 件。
- K5-2（design §5 ④-3 のとおり）: 反映時刻以降の discord-gateway のログで `tenant_id 逆引き失敗`（client.py:124）が 0 件（K5-1 と同じ数え方。`tenant 未登録` は数えない）。会社の文脈なしの読取が通ることは、CI の試験①（アプリの接続役で 2 行とも読める）で確かめる。本番で役を替えて読む確かめは行わない。
- 画面での確かめ（PO 戻り後）: 自社の Discord サーバーでチケットを 1 件出して作られる（design §5 K5-2）。待ちの間も次の便は進めてよい。

## 9. 戻し方（design §7 を表名で埋めたもの）

```sql
BEGIN;
DROP POLICY IF EXISTS tenant_discord_config_select ON public.tenant_discord_config;
DROP POLICY IF EXISTS tenant_discord_config_insert ON public.tenant_discord_config;
DROP POLICY IF EXISTS tenant_discord_config_update ON public.tenant_discord_config;
DROP POLICY IF EXISTS tenant_discord_config_delete ON public.tenant_discord_config;
ALTER TABLE public.tenant_discord_config NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_discord_config DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_discord_ticket_config_select ON public.tenant_discord_ticket_config;
DROP POLICY IF EXISTS tenant_discord_ticket_config_insert ON public.tenant_discord_ticket_config;
DROP POLICY IF EXISTS tenant_discord_ticket_config_update ON public.tenant_discord_ticket_config;
DROP POLICY IF EXISTS tenant_discord_ticket_config_delete ON public.tenant_discord_ticket_config;
ALTER TABLE public.tenant_discord_ticket_config NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_discord_ticket_config DISABLE ROW LEVEL SECURITY;
COMMIT;
```
- 順番・道・流す人は design §7 のとおり（便④-1 card-4-1.md §8 と同じ）。戻しの PR では移行ファイルと run_all の 2 行を消す。

## 10. 想定される分岐（実装役が出会ったら止まって Opus に戻す）

- §5 の 2 の移行のどれかが使い捨て DB で失敗する。
- 974・975 が既に使われている。
- 既にある Discord の試験 13 本のどれかが落ちる。
- main に `20261107_130000` 以降の移行が先に入った。
- 上の以外でも、カードに書いていない変更が要ると分かったとき。

## 11. 危険パスと GO

- `migrations/`・`scripts/` を含む＝危険 PR（ADR-135・ADR-136）。マージの前に、審査役（reviewer・opus）の APPROVE、CI 全緑、直前のバックアップの確認を揃え、PR 本文に `### GO記録`（POの委任に基づくClaude Opus発行・委任 ADR-1003・PR 番号・HEAD・日時・相乗りの PR が無いこと）を書く。
