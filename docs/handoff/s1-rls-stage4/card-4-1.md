# 実装カード 便④-1 — public.inventory_movements に RLS（型A）

- 状態: 草案（クラウド設計審査の前）。PO の実装承認は design.md 冒頭（2026-11-06「1」: KGI-4〜6 と 5 便の順番、「最初の在庫の動きの分から作り始め、本番に出して確かめるところまで進めます。」）。
- 根拠の版: origin/main 5574bf327（2026-11-06 23:58 JST に fetch）。行番号はすべてこの版。
- 設計: [design.md](design.md) §2-1（型A）・§3（④-1 行）・§4（試験）・§5（K4-1・K4-2・K5-1・K5-2）・§7（戻し方）。現状: [recon.md](recon.md)。
- 実装ブランチ: `release/s1-rls-stage4-bin1`（origin/main から作る）。1 便 1 PR。PR は Draft で起票する。

## 1. 触るファイル（これ以外は触らない）

| # | ファイル | 変更 |
|---|---|---|
| 1 | `migrations/20261107_100000_add_inventory_movements_rls.sql` | 新規。§2 の SQL を一字一句この内容で作る |
| 2 | `scripts/run_all_migrations.sh` | 末尾（今の最終行 :1237 `run_sql migrations/20261106_210000_add_notification_channels_blueprint_key.sql` の後）に §3 の 2 行を足す |
| 3 | `scripts/export_inventory_for_sheet.py` | :108-109 の 1 か所だけ。§4 |
| 4 | `backend/tests/test_inventory_movements_rls.py` | 新規。§5 |
| 5 | `.claude-pipeline/active-work.d/release-s1-rls-stage4-bin1.md` | 台帳（Opus が本店の写しに置く。実装役は触らない） |

- 実装の直前に `git ls-tree --name-only origin/main migrations/ | tail -3` を流し、`20261107_100000` より後の名前の移行が main に入っていたら止まって Opus に戻す（名前を自分で変えない）。
- 触らない: `backend/tests/rls_bootstrap.py`（`_PG_BOOTSTRAP_MIGRATIONS` に新しい移行を足さない。共有の試験 DB の inventory_movements は RLS 無しのままにし、既にある試験 test_inventory_sprint1_migrations.py:304-340 の文脈なし INSERT を壊さない）、`backend/app/ops/tenant_rls_allowlist.py`（ADR-1063 便5 の許可一覧。#5194 の版でも中身は空 `{}`。本便では触らない）、frontend、他の 7 表。

## 2. 移行 SQL（design §2-1 の型A を表名で埋めたもの）

```sql
-- ADR-1067 段階④ 便④-1: public.inventory_movements に会社ごとの RLS（型A）を付ける。
-- 読む: 自社の会社文脈か運営文脈。書く: 自社の会社文脈だけ。文脈が空なら 0 行（エラーにしない）。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-1。
BEGIN;
ALTER TABLE public.inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_movements FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inventory_movements_select ON public.inventory_movements;
CREATE POLICY inventory_movements_select ON public.inventory_movements FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS inventory_movements_insert ON public.inventory_movements;
CREATE POLICY inventory_movements_insert ON public.inventory_movements FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS inventory_movements_update ON public.inventory_movements;
CREATE POLICY inventory_movements_update ON public.inventory_movements FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS inventory_movements_delete ON public.inventory_movements;
CREATE POLICY inventory_movements_delete ON public.inventory_movements FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
COMMIT;
```

## 3. run_all_migrations.sh に足す 2 行

```bash
# ADR-1067 段階④ 便④-1: inventory_movements に会社ごとの RLS（型A）。冪等・1 取引
run_sql migrations/20261107_100000_add_inventory_movements_rls.sql
```

- CI の前提（design §3、origin/main 5574bf327 で確かめ直した）: 表を作る 062 は scripts/migrate_inventory_sprint1.py の一覧にあり、run_all の `run_py`（:361）で流れる。変更 SQL のジョブと全件ドライランでも本 SQL より先に流れる。足す step は無い。

## 4. scripts/export_inventory_for_sheet.py（:108-109）

変更前:
```python
    async with engine.connect() as conn:
        rows = (await conn.execute(text(sql), params)).mappings().all()
```
変更後:
```python
    async with engine.connect() as conn:
        # ADR-1067 便④-1: inventory_movements は RLS（型A）。読む前に同じ取引で会社の文脈を張る。
        # engine.connect() は最初の execute で取引が自動で始まり、抜けるときに戻される（SQLAlchemy 2.0
        # 「Commit As You Go」）。is_local=true なので文脈は取引の終わりで消え、接続の使い回しに残らない。
        await conn.execute(
            text("SELECT set_config('app.tenant_id', :tid_ctx, true)"),
            {"tid_ctx": str(tenant_id)},
        )
        rows = (await conn.execute(text(sql), params)).mappings().all()
```
- design §3 の `false`（接続の間ずっと）からの変更点: `true`（取引の間だけ）にする。理由: fetch_movements は試験から共有の engine を渡されて呼ばれる（backend/tests/test_export_inventory_for_sheet.py）。`false` だと接続を池に戻した後も会社の文脈が残り、次の使い手に他社の文脈が付く。`true` でも同じ取引の中の SELECT には効く（根拠: SQLAlchemy 2.0 公式 docs.sqlalchemy.org/en/20/core/connections.html「Commit As You Go」— The first time the Connection.execute() method is called … this transaction is begun automatically … The transaction remains in place … until … commit() or rollback()」。2026-11-06 に取得。Context7 は月の上限で使えなかった）。要件のバージョン backend/requirements.txt `sqlalchemy==2.0.38`。
- 他の行（SQL の文・WHERE tenant_id=:tid・並び順・CSV の列）は変えない。

## 5. 試験 backend/tests/test_inventory_movements_rls.py（新規）

手本: backend/tests/test_users_rls.py（:24-36 の skipif・:81-131 の `_fresh()`・:134 `_admin_exec`・:142-152 `_ctx_conn`・:161 `_sqlstate`）。同じ形で書く。

- 会社番号: 976（自社）・977（他社）。backend/tests で未使用（`git grep -n -E "\b(976|977)\b" origin/main -- backend/tests` が 0 件であることを実装の前に確かめる。1 件でもあれば止まって Opus に戻す）。
- `_fresh()` の中身（使い捨て DB `imv_rls_<hex12>`、app_engine は `pool_size=1, max_overflow=0`）:
  1. admin で `_ensure_public_users(conn)`（tenants・users の最小の土台）→ tenants に 976・977 を INSERT。
  2. `await bootstrap_public_products(admin_engine)`（rls_bootstrap.py:327。002・056・062 ほかを本番の順で当て、inventory_movements と products・suppliers を本物の移行で作る。表の定義を試験に書き写さない）。
  3. admin で products に 1 行（`INSERT INTO public.products (name, stock_quantity) VALUES ('imv rls', 100) RETURNING id`。前例 test_inventory_sprint1_migrations.py:313-316）。
  4. admin で `_GRANT_DDL`（test_users_rls.py:57-60 と同じ 2 行）。
  5. admin で各社 1 行ずつ inventory_movements を INSERT（976 と 977。before 100・delta -1・after 99・source_type 'manual_adjust'・operator_id 1。算術トリガ 062:126-140 に合わせる）。
  6. `_apply_migration(admin_engine, "20261107_100000_add_inventory_movements_rls.sql")`。
  - 1〜2 のどれかが使い捨て DB で通らないときは、通らない理由（足りない前提の表）を記録して止まり、Opus に戻す（design §4。推測で定義を書き足さない）。
- 試験（design §4 型A ①〜⑧ と、書き出しの入口 1 本）。すべて app_engine（アプリの接続役 salesanchor_app・NOBYPASSRLS）で行う:
  - ① 976 の文脈で INSERT でき、SELECT で 976 の行だけが 2 行（土台の 1 行＋今の 1 行）見える。
  - ② 977 の文脈で SELECT すると 976 の行が 0 行。
  - ③ 976 の文脈で tenant_id=977 の INSERT が 42501。
  - ④ 976 の文脈で 977 の行への UPDATE（notes だけ変える）・DELETE が 0 行。後で admin で 977 の行が元のまま 1 行あることを確かめる。
  - ⑤ 運営の文脈（`app.is_operator='true'`・会社の文脈なし）で SELECT が 976・977 の両方の行を返す。
  - ⑥ 文脈なしの SELECT が 0 行。新しい接続の場合と、同じ接続で `SET app.tenant_id = ''` の後の場合の両方。後者でエラー（22P02）にならない。
  - ⑦ 同じ移行をもう一度当ててもエラーにならず、`pg_policies` の本数が 4 のまま。
  - ⑧ 976 の文脈で自社の行の tenant_id を 977 へ付け替える UPDATE が 42501。
  - ⑨ 書き出しの入口: `scripts/export_inventory_for_sheet.py` の `fetch_movements(app_engine, tenant_id=976, since=date(2000,1,1), until=None)` が 976 の行だけを返す（977 の行が混ざらない・0 行でない）。続けて同じ app_engine（接続 1 本）で文脈なしの SELECT が 0 行（set_config が取引の外に残っていない）。読み込みは test_export_inventory_for_sheet.py と同じ方法で scripts/ から import する（その試験ファイルの import の行を見て同じ形にする）。
- 既にある試験への影響（`git grep -l inventory_movements origin/main -- backend/tests` = 3 本）:
  - rls_bootstrap.py: 触らない（§1）。
  - test_inventory_sprint1_migrations.py: 共有 DB に新しい移行を当てないので影響なし。
  - test_export_inventory_for_sheet.py: TEST_PG_URL の試験（CI では skip）。§4 の変更で文の結果は変わらない。触らない。

## 6. 合格の条件（実装役が自分で確かめて生出力をファイルに残す）

| 基準 | 確かめ方 |
|---|---|
| §1 の 4 ファイル以外に差分が無い | `git diff origin/main...HEAD --name-only` |
| 移行 SQL が §2 と一字一句同じ | `diff` で 0 行 |
| CI の Backend Tests・migration-test・ADR index ほか必須チェックが全部緑 | `gh pr checks <PR>` |
| 新しい試験 ①〜⑨ が CI で実行されて通っている（skip でない） | CI の pytest ログで `test_inventory_movements_rls.py` の各試験が PASSED |
| i18n・UI は触らない | 差分に frontend が無い |

## 7. 本番の確かめ（Opus が反映の後に行う。実装役は行わない）

基準値（2026-11-06 23:55 JST、reader 鍵の道で取得）: inventory_movements は全社 0 行（tenants 1・3・4・5・6 とも 0）。生出力 /tmp/CC報告ファイル/c41/tenants.txt。RLS は False/False・ポリシー 0 本（recon R§3・design §5 の基準値）。

- K4-1: reader 鍵の道で `SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid='public.inventory_movements'::regclass` と `SELECT count(*) FROM pg_policies WHERE schemaname='public' AND tablename='inventory_movements'` → t/t・4。
- K4-2: reader 鍵の道で `SELECT count(*) FROM ai_ro.public__inventory_movements`（ビューの持ち主は jarvis で security_invoker なし＝RLS の後も全行を数える。migrations/20261017_130100_create_ai_ro_views.sql:2）→ 反映前と同じ 0。
- K5-1: 反映時刻以降の backend・celery-worker・celery-beat・discord-gateway の `docker logs --since <反映時刻>` で `42501`・`row-level security`・`invalid input syntax for type integer` が 0 件。
- K5-2（書き出しの入口）: 書き出し台本は backend の入れ物に入っていない（backend/Dockerfile:24 `COPY . .` の土台は build: ./backend＝docker-compose.yml:64。scripts/ は入らない）。サーバーの写し /home/ubuntu/salesanchor は deploy.yml:258-259 で origin/main に揃う。このため、写しの台本を標準入力で入れ物の Python に渡して流す（ファイルを作らない・出力は /dev/null・読むだけ）:
  - 入れ物の名前を先に読む: `docker ps --format '{{.Names}}' | grep backend`（blue-green の後は astro-webapp-backend-1。scripts/blue-green-cutover.sh:27・Step 6）。
  - 流す: `cd /home/ubuntu/salesanchor && docker exec -i astro-webapp-backend-1 python - --tenant 1 --since 2000-01-01 --output /dev/null < scripts/export_inventory_for_sheet.py`。
  - 会社 1（test-corp）を使う。tenant 4（highlife-jpn）は使わない。
  - 反映の前に 1 回（古い台本・RLS なし）、反映の後に 1 回（新しい台本・RLS あり）流し、両方で終了コード 0・ログに `OK: 0 rows written to /dev/null`・`export 失敗` が 0 件。行数が前後で一致（0 = 0）。
  - 本番が 0 行なので、行数の一致は弱い確かめになる。「自社の行が見え、他社の行が見えない」ことの強い確かめは §5 ⑨（CI・アプリの接続役）で行う。
  - 道: 無制限鍵（読むだけの調査。AGENTS.md の恒常許可の範囲外の DB 読み取りを含むので、本カードが審査役の APPROVE を受けた手順として ADR-1003 追記 2026-11-02 に従い Opus が控えを取って流す）。

## 8. 戻し方（design §7 を表名で埋めたもの）

```sql
BEGIN;
DROP POLICY IF EXISTS inventory_movements_select ON public.inventory_movements;
DROP POLICY IF EXISTS inventory_movements_insert ON public.inventory_movements;
DROP POLICY IF EXISTS inventory_movements_update ON public.inventory_movements;
DROP POLICY IF EXISTS inventory_movements_delete ON public.inventory_movements;
ALTER TABLE public.inventory_movements NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_movements DISABLE ROW LEVEL SECURITY;
COMMIT;
```
- 順番・道・流す人は design §7 のとおり（戻しの PR の CI 緑と GO → デプロイ 0 件の確認 → `docker exec -e PGOPTIONS="-c lock_timeout=1s" -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 <` で流す → K4-1 の読み方で RLS なし・0 本 → 戻しの PR をマージ → もう一度確かめる）。
- 台本の §4 の変更は RLS が無くても正しく動く（文脈を張るだけ）ので、戻しの PR で一緒に戻してよいし、残してもよい。戻しの PR では移行ファイルと run_all の 2 行を消す。

## 9. 想定される分岐（実装役が出会ったら止まって Opus に戻す）

- `bootstrap_public_products` が使い捨て DB で失敗する（足りない前提がある）。
- 976・977 が既に使われている。
- §4 の変更で test_export_inventory_for_sheet.py が CI で skip でなく走って落ちる。
- CI の migration-test で本 SQL が前提の表の無さで落ちる。
- 上の以外でも、カードに書いていない変更が要ると分かったとき。

## 10. 危険パスと GO

- `migrations/` と `scripts/` を含む＝危険 PR（ADR-135・ADR-136）。マージの前に、審査役（reviewer・opus）の APPROVE、CI 全緑、直前のバックアップの確認（デプロイの Pre-deploy DB backup）を揃え、PR 本文に `### GO記録`（POの委任に基づくClaude Opus発行・委任の根拠 ADR-1003・PR 番号・HEAD・日時・相乗りの PR が無いこと）を書く。
