# 実装カード 便④-2 — public.discord_server_snapshots・public.discord_server_apply_runs に RLS（型A）

- 状態: 草案（クラウド設計審査 1 回目 REVISE〔T1 会社番号 978 が使用中・T2 代わりの確かめの前提〕を直した版。2 回目の審査の前）。PO の実装承認は design.md 冒頭（2026-11-06「1」: KGI-4〜6 と 5 便の順番）。完走の指示は PO 2026-11-07 チャット「PRマージ、デプロイまで完走させてくれ」。
- 根拠の版: origin/main a03e222c2（2026-11-07 02:30 JST に fetch。便④-1 #5221 の合流後）。行番号はすべてこの版。
- 設計: [design.md](design.md) §2-1（型A）・§3（④-2 行と「前提の表」）・§4（試験）・§5（K4-1・K4-2・K5-1・K5-2）・§7（戻し方）。現状: [recon.md](recon.md) R§4-2。手本: 便④-1 [card-4-1.md](card-4-1.md) と、合流済みの backend/tests/test_inventory_movements_rls.py。
- 実装ブランチ: `release/s1-rls-stage4-bin2`（origin/main から作る）。1 便 1 PR。PR は Draft で起票する。

## 1. 触るファイル（これ以外は触らない）

| # | ファイル | 変更 |
|---|---|---|
| 1 | `migrations/20261107_110000_add_discord_server_records_rls.sql` | 新規。§2 の SQL を一字一句この内容で作る |
| 2 | `scripts/run_all_migrations.sh` | 末尾（今の最終行 :1239 `run_sql migrations/20261107_100000_add_inventory_movements_rls.sql` の次の行）に §3 の 2 行を足す |
| 3 | `.github/workflows/migration-test.yml` | 「変更 SQL の前提の移行を先に実行（ログイン許可の依頼の表）」step（:1328-1335）の直後、「変更 SQL を 1回目実行」step（:1337）の直前に、§4 の step を 1 つ足す |
| 4 | `backend/tests/test_discord_server_records_rls.py` | 新規。§5 |
| 5 | `docs/handoff/s1-rls-stage4/card-4-2.md` | このカード（Opus が置く。実装役は触らない） |
| 6 | `.claude-pipeline/active-work.d/release-s1-rls-stage4-bin2.md` | 台帳（Opus が本店の写しに置く。実装役は触らない） |

- 実装の直前に `git ls-tree --name-only origin/main migrations/ | tail -3` を流し、`20261107_110000` より後の名前の移行が main に入っていたら止まって Opus に戻す（名前を自分で変えない）。
- 触らない: `backend/app/routers/discord_own_server.py`（書込の入口 2 か所はどちらも会社の文脈がある。§6）、`backend/tests/conftest.py`（§5 末尾）、`backend/tests/rls_bootstrap.py`、frontend、他の 6 表。

## 2. 移行 SQL（design §2-1 の型A を 2 表の名で埋め、1 つの取引にまとめたもの）

```sql
-- ADR-1067 段階④ 便④-2: public.discord_server_snapshots と public.discord_server_apply_runs に会社ごとの RLS（型A）を付ける。
-- 読む: 自社の会社文脈か運営文脈。書く: 自社の会社文脈だけ。文脈が空なら 0 行（エラーにしない）。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-1。
BEGIN;
ALTER TABLE public.discord_server_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discord_server_snapshots FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS discord_server_snapshots_select ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_select ON public.discord_server_snapshots FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS discord_server_snapshots_insert ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_insert ON public.discord_server_snapshots FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_snapshots_update ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_update ON public.discord_server_snapshots FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_snapshots_delete ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_delete ON public.discord_server_snapshots FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
ALTER TABLE public.discord_server_apply_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discord_server_apply_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS discord_server_apply_runs_select ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_select ON public.discord_server_apply_runs FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS discord_server_apply_runs_insert ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_insert ON public.discord_server_apply_runs FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_apply_runs_update ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_update ON public.discord_server_apply_runs FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_apply_runs_delete ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_delete ON public.discord_server_apply_runs FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
COMMIT;
```

## 3. run_all_migrations.sh に足す 2 行

```bash
# ADR-1067 段階④ 便④-2: discord_server_snapshots・discord_server_apply_runs に会社ごとの RLS（型A）。冪等・1 取引
run_sql migrations/20261107_110000_add_discord_server_records_rls.sql
```

- 本番の順: 2 表を作る 20261106_120000 は run_all:1229。本 SQL（末尾 :1241 になる）より先に流れる。

## 4. migration-test.yml に足す step（design §3「前提の表」）

- 理由: 変更 SQL のジョブ（migration-test.yml の Step 5）には 2 表の定義が無い（`grep -n discord_server .github/workflows/migration-test.yml` が 0 件。a03e222c2 で確かめた）。前提の移行を先に流さないと、本 SQL が「relation does not exist」で落ちる。全件ドライランは run_all（:1229）で 2 表を作るので足すものは無い。
- 20261106_120000 が指すのは `public.tenants` だけ（同ファイル :17・:37）。tenants は同じジョブの `PUBLIC_SQL` で作られる（design §3。実装役は `grep -n "CREATE TABLE IF NOT EXISTS tenants\|CREATE TABLE IF NOT EXISTS public.tenants" .github/workflows/migration-test.yml` で、足す step より前の行にあることを確かめ、無ければ止まって Opus に戻す）。
- 前例 :1328-1335 と同じ形で、次の step を足す（字下げは前例に合わせて 6 つ）:

```yaml
      - name: 変更 SQL の前提の移行を先に実行（Discord サーバーの記録の表）
        if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261107_110000_add_discord_server_records_rls.sql')
        run: |
          # 20261107_110000 は discord_server_snapshots と discord_server_apply_runs（20261106_120000）が先にある前提（本番と同じ順）
          for sqlfile in migrations/20261106_120000_create_discord_server_snapshot_tables.sql; do
            echo "▶ $sqlfile を前提として実行中..."
            psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
            echo "✅ $sqlfile 成功"
          done
```

- `.github/workflows/workflow-lint.yml` は触らない（PO 確認が要るファイル）。migration-test.yml は対象外。

## 5. 試験 backend/tests/test_discord_server_records_rls.py（新規）

手本: 合流済みの backend/tests/test_inventory_movements_rls.py（便④-1。:20-33 の skipif・:59-97 の `_fresh()`・:99 `_admin_exec`・:107 `_ctx_conn`・:120 `_sqlstate`）。同じ形で書く。

- 会社番号: 972（自社）・973（他社）。backend/tests で未使用（`git grep -n -w 972 origin/main -- backend/tests` と `git grep -n -w 973 origin/main -- backend/tests` がどちらも 0 件。a03e222c2 で確かめた（初版の 978 は test_calendar_sync_tenant_reset_pg.py:38 で使用中だったため替えた。macOS の git grep -E は \b を解さないので -w を使う）。実装の前にもう一度流し、1 件でもあれば止まって Opus に戻す）。
- `_fresh()` の中身（使い捨て DB `dsr_rls_<hex12>`、app_engine は `pool_size=1, max_overflow=0`）:
  1. admin の接続で `_ensure_public_users(conn)`（rls_bootstrap.py:213。public.tenants と public.users を作り、tenant 999 を入れる）。続けて admin で `INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) VALUES (972, 'tenant_972', 'T972', 'T972', TRUE), (973, 'tenant_973', 'T973', 'T973', TRUE)`。2 表は tenants を外部キーで指す（20261106_120000:17・:37）。
  2. `_apply_migration(admin_engine, "20261106_120000_create_discord_server_snapshot_tables.sql")`（2 表を本物の移行で作る。表の定義を試験に書き写さない）。
  3. admin で `_GRANT_DDL`（便④-1 の試験 :43-46 と同じ 2 行）。
  4. admin で各社 1 行ずつ両方の表に INSERT（972 と 973）。snapshots: `purpose='own'`・`body='{"version":1,"roles":[],"channels":[]}'::jsonb`・`taken_by=1`。apply_runs: `purpose='own'`・`plan_digest='d'`・`applied_by=1`・`result='{"rows":[]}'::jsonb`。
  5. `_apply_migration(admin_engine, "20261107_110000_add_discord_server_records_rls.sql")`。
  - 1〜2 のどれかが使い捨て DB で通らないときは、通らない理由を記録して止まり、Opus に戻す（design §4。推測で定義を書き足さない）。
- 試験（design §4 型A ①〜⑧ を 2 表それぞれに。`@pytest.mark.parametrize` で表名を回してよい）。すべて app_engine（アプリの接続役 salesanchor_app・NOBYPASSRLS）で行う:
  - ① 972 の文脈で INSERT でき、SELECT で 972 の行だけが 2 行（土台の 1 行＋今の 1 行）見える。
  - ② 973 の文脈で SELECT すると 972 の行が 0 行。
  - ③ 972 の文脈で tenant_id=973 の INSERT が 42501。
  - ④ 972 の文脈で 973 の行への UPDATE（snapshots は taken_by、apply_runs は plan_digest だけ変える）・DELETE が 0 行。後で admin で 973 の行が元のまま 1 行あることを確かめる。
  - ⑤ 運営の文脈（`app.is_operator='true'`・会社の文脈なし）で SELECT が 972・973 の両方の行を返す。
  - ⑥ 文脈なしの SELECT が 0 行。新しい接続の場合と、同じ接続で `SET app.tenant_id = ''` の後の場合の両方。後者でエラー（22P02）にならない。
  - ⑦ 同じ移行をもう一度当ててもエラーにならず、`pg_policies` の本数が 2 表とも 4 のまま。
  - ⑧ 972 の文脈で自社の行の tenant_id を 973 へ付け替える UPDATE が 42501。
  - ⑨ 書込の入口と同じ文脈の張り方で書ける: app_engine の接続で `SET app.tenant_id = '972'` と `SET app.is_operator = ''`（backend/app/auth/dependencies.py:251-256 の get_current_tenant と同じ 2 文。set_config でなく SET）を流し、backend/app/routers/discord_own_server.py の `_insert_sql` と同じ文（`INSERT INTO public.discord_server_snapshots (tenant_id, purpose, body, taken_by) VALUES (:tid, 'own', CAST(:body AS JSONB), :uid) RETURNING id`）が id を 1 つ返す。apply_runs も `_apply_insert_sql`（:377-386）と同じ文（`INSERT INTO public.discord_server_apply_runs (tenant_id, purpose, plan_digest, started_at, finished_at, applied_by, result) VALUES (:tid, 'own', :digest, :started, :finished, :uid, CAST(:result AS JSONB)) RETURNING id`）で id を 1 つ返す。RETURNING が SELECT のポリシーにも通ることの確かめ。
- 既にある試験への影響（`git grep -l -E "discord_server_snapshots|discord_server_apply_runs" origin/main -- backend/tests` = 6 本: conftest.py・test_discord_notice_rooms.py・test_discord_own_server_app_roles.py・test_discord_own_server_apply.py・test_discord_own_server_plan.py・test_discord_own_server_snapshot.py）:
  - conftest.py は 2 表を SQLite に作り（:1275-1296。`AUTOINCREMENT`）、`public.` を外す書き換え（:323-326）と後片付けの DELETE（:1794-1795）も SQLite の上で行う。RLS は SQLite に無いので、design §4 の「後片付けの後に行が残っていないこと」の心配は起きない。触らない。
  - 残りの 5 本は conftest.py の SQLite の DB を使う。本 PR の移行は流れないので影響なし。触らない。
  - rls_bootstrap.py の共有の PG の DB に 2 表は作られない（`git grep -n 20261106_120000 origin/main -- backend/tests` が 0 件）。触らない。

## 6. 書込の入口（触らないが、文脈があることの根拠）

- 記録を取る: backend/app/routers/discord_own_server.py:113-178 `take_own_server_snapshot`。`tenant_id = Depends(get_current_tenant)`（:120）が同じ session に `SET app.tenant_id = '<会社>'`（dependencies.py:253）を流してから、:161-164 で INSERT … RETURNING id。commit の後に `reset_tenant_context`（:178）。
- 反映する: 同ファイル :421-483 `apply_own_server_plan`。`Depends(get_current_tenant)`（:429）→ :460-471 で INSERT … RETURNING id → :482 commit → :483 `reset_tenant_context`。
- 読む箇所: 本番コードで 2 表を読む箇所は無い（`git grep -n -E "discord_server_snapshots|discord_server_apply_runs" origin/main -- backend/app` は discord_own_server.py の INSERT 2 文と監査の表名 2 つだけ）。

## 7. 合格の条件（実装役が自分で確かめて生出力をファイルに残す）

| 基準 | 確かめ方 |
|---|---|
| §1 の 1〜4 以外に差分が無い（5・6 は Opus） | `git diff origin/main...HEAD --name-only` |
| 移行 SQL が §2 と一字一句同じ | `diff` で 0 行 |
| step が §4 と同じ | `git diff origin/main...HEAD -- .github/workflows/migration-test.yml` が §4 の 9 行の追加だけ |
| CI の Backend Tests・migration-test・ADR index ほか必須チェックが全部緑 | `gh pr checks <PR>` |
| 新しい試験が CI で実行されて通っている（skip でない） | CI の PostgreSQL のログに `violates row-level security policy for table "discord_server_snapshots"` と `"discord_server_apply_runs"` が出る（便④-1 で使った確かめ方。pytest は `-q` で個別の PASSED を出さない） |
| i18n・UI は触らない | 差分に frontend が無い |

## 8. 本番の確かめ（Opus が反映の後に行う。実装役は行わない）

基準値: 反映の直前に Opus が 2 表の会社ごとの行数と RLS の状態（False/False・0 本の見込み）を読み、PR のコメントに残す。

- K4-1: `SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid IN ('public.discord_server_snapshots'::regclass, 'public.discord_server_apply_runs'::regclass)` と `SELECT tablename, count(*) FROM pg_policies WHERE schemaname='public' AND tablename IN ('discord_server_snapshots','discord_server_apply_runs') GROUP BY tablename` → 2 表とも t/t・4。
- K4-2: 2 表の会社ごとの行数（`SELECT tenant_id, count(*) … GROUP BY tenant_id` を表の持ち主の役で）が反映の前と同じ。
- K5-1: 反映時刻以降の backend・celery-worker・celery-beat・discord-gateway の `docker logs --since <反映時刻>` で `42501`・`row-level security`・`invalid input syntax for type integer` が 0 件。
- K5-2（書込の入口）: design §5 の「自社の Discord サーバーの記録を画面から 1 回取り、応答 200 で行が 1 増える」は、ログインした人の操作が要る。PO が席に戻ったら頼む（待ちの間も次の便は進めてよい。ただし④-2 の K5-2 が済むまで KPI の「確かめ済み」には数えない）。
  - その前の代わりの確かめ（Opus が反映の直後に行う・本番に何も残さない）: backend の入れ物の Python で、アプリと同じ接続（環境変数 DATABASE_URL＝アプリの接続役）を開き、1 つの取引の中で ① `SET LOCAL app.tenant_id = '1'`・`SET LOCAL app.is_operator = ''` ② §5 ⑨ と同じ INSERT … RETURNING id を 2 表に 1 回ずつ（id が返る）③ SAVEPOINT の中で tenant_id=3 の INSERT が 42501 ④ 最後に ROLLBACK。流した後、2 表の行数が反映前と同じであること（K4-2 の読み方）を確かめる。会社 1（test-corp）と 3 だけを使う。会社 4（highlife-jpn）は使わない。
  - 流す前に、会社 1 と 3 が public.tenants にあることを読んで確かめる（`SELECT id FROM public.tenants WHERE id IN (1,3)` が 2 行）。2 表は tenants を外部キーで指す（20261106_120000:17・:37）ので、無いと ② が外部キーの誤りで落ち、42501 の確かめにならない。2 行でなければ流さずに止まる。
  - ROLLBACK しても採番の値（id の続き番号）は戻らない。2 表の id に 1 つずつ欠番が出る。行の数と中身は変わらない。
  - 道: 無制限鍵。本カードが審査役の APPROVE を受けた手順として、ADR-1003 追記 2026-11-02 に従い Opus が流す。反映前の自動控え（deploy.yml の Pre-deploy DB backup）の名前を先に確かめる。

## 9. 戻し方（design §7 を表名で埋めたもの）

```sql
BEGIN;
DROP POLICY IF EXISTS discord_server_snapshots_select ON public.discord_server_snapshots;
DROP POLICY IF EXISTS discord_server_snapshots_insert ON public.discord_server_snapshots;
DROP POLICY IF EXISTS discord_server_snapshots_update ON public.discord_server_snapshots;
DROP POLICY IF EXISTS discord_server_snapshots_delete ON public.discord_server_snapshots;
ALTER TABLE public.discord_server_snapshots NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.discord_server_snapshots DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS discord_server_apply_runs_select ON public.discord_server_apply_runs;
DROP POLICY IF EXISTS discord_server_apply_runs_insert ON public.discord_server_apply_runs;
DROP POLICY IF EXISTS discord_server_apply_runs_update ON public.discord_server_apply_runs;
DROP POLICY IF EXISTS discord_server_apply_runs_delete ON public.discord_server_apply_runs;
ALTER TABLE public.discord_server_apply_runs NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.discord_server_apply_runs DISABLE ROW LEVEL SECURITY;
COMMIT;
```
- 順番・道・流す人は design §7 のとおり（便④-1 card-4-1.md §8 と同じ）。戻しの PR では移行ファイル・run_all の 2 行・migration-test.yml の step を消す。

## 10. 想定される分岐（実装役が出会ったら止まって Opus に戻す）

- `_ensure_public_users` か 20261106_120000 が使い捨て DB で失敗する。
- 972・973 が既に使われている。
- migration-test の変更 SQL のジョブで、足した step の前に tenants が無い。
- 既にある Discord の試験 5 本のどれかが落ちる。
- 上の以外でも、カードに書いていない変更が要ると分かったとき。

## 11. 危険パスと GO

- `migrations/`・`scripts/`・`.github/workflows/` を含む＝危険 PR（ADR-135・ADR-136）。マージの前に、審査役（reviewer・opus）の APPROVE、CI 全緑、直前のバックアップの確認を揃え、PR 本文に `### GO記録`（POの委任に基づくClaude Opus発行・委任 ADR-1003・PR 番号・HEAD・日時・相乗りの PR が無いこと）を書く。
