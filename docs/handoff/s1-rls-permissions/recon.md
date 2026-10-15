---
mode: handoff
---
# recon — S1 段階①（public.permissions に RLS）

> この文書は何か：権限の一覧表（permissions）を、アプリから書き換えられないようにする前に、今どうなっているかを実物で確かめた記録です。

親: [docs/specs/tenant-rls/README.md](../../specs/tenant-rls/README.md)
**日付**: 2026-10-15　**基準**: origin/main e1351e663（fetch 後）

## 1. 既存 ADR の検索結果

| 検索 | 結果 |
|---|---|
| `git grep -i "permissions" docs/adr/` ＋ `docs/adr/FEATURE-INDEX.md` | permissions 表に RLS を定める ADR は無い。ADR-1007:50,73 は「権限一覧の正本」の話で、RLS は範囲外 |
| `git grep -i "row level security\|FORCE ROW" docs/adr/` | ADR-145（public.products の FORCE RLS）が手本。ADR-072（テナントスキーマ分離）、ADR-131（接続ごとの文脈リセット） |
| ADR-1013 | 認証系の表に RLS を付けない判断（`migrations/20261013_160000_add_self_hosted_auth_tables.sql:3`）。段階①の対象外 |

→ 新規 ADR-1018 を起案する。

## 2. 本番 DB の事実（2026-10-15 読取・SELECT のみ）

| 項目 | 値 | 根拠 |
|---|---|---|
| 接続役の属性 | jarvis = rolsuper t / rolbypassrls t、salesanchor_app = f / f | scratchpad `s1-perm-prod-read.txt` |
| permissions の RLS | relrowsecurity f / relforcerowsecurity f、所有者 jarvis、ポリシー 0 本、123 行 | 同上 |
| salesanchor_app の権限 | permissions に SELECT, INSERT, UPDATE, DELETE あり（＝アプリ接続で権限マスタを書き換えられる） | 同上 |
| 列 | id, key, resource, action, description, category, permission_group, display_name_jp, display_name_en, display_order | 同上 |
| アプリ・Celery の接続役 | 全て salesanchor_app（backend 6 本・celery 等）。jarvis は照会用 psql 1 本のみ | scratchpad `s1-prod-conn-read.txt` |
| `.env` の役名 | ADMIN_DATABASE_URL = jarvis、DATABASE_URL = salesanchor_app、`SA18_PHASE2_ENABLED=1` が 1 行 | 2026-10-15 ssh 読取（パスワード非表示） |

→ アプリは RLS が効く役で接続している。migration 実行役（jarvis）は superuser のため RLS を素通りする。

## 3. PostgreSQL 公式文書（docs/16/ddl-rowsecurity）

Context7 が月間上限超過で使えず、公式ページを直接確認（本起動指示で許可された代替）。

- "Superusers and roles with the BYPASSRLS attribute always bypass the row security system when accessing a table."
- "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with ALTER TABLE ... FORCE ROW LEVEL SECURITY."
- "If no policy exists for the table, a default-deny policy is used."
- 複数の permissive ポリシーは OR で結合される。

→ jarvis は FORCE でも素通り＝ migration は止まらない。`.github/workflows/test.yml:218-219` のコメントが公式と一致。ADR-145 の「bypassrls=t でも強制」という記述は公式と食い違う（ADR-1018 で注記）。

## 4. アプリから permissions への読み書き（全走査）

書込 0 件。読取のみ:

- `backend/app/routers/roles.py:122`, `:393`, `:434`
- `backend/app/auth/dependencies.py:595`, `:606`
- `backend/app/routers/tenant_admin_inventory_visibility.py:70`, `:151`, `:160`, `:175`
- `backend/app/services/tenant.py:1532`, `:1540`, `:1549`

書込は jarvis（ADMIN）経路のみ:

- 番号式 migration 002/004/006/008/010（INSERT）、067_down/069_down/079（DELETE）
- `scripts/migrate_inventory_sprint8.py` / `sprint9.py`（run_py・ADMIN 接続）
- テスト `backend/tests/test_permission_resolution_pg.py`（admin 接続）

## 5. 権限の再付与（表単位 REVOKE が効かない理由）

- `scripts/run_all_migrations.sh` は毎デプロイ全件を再実行（939 行、最終行 939 `run_sql migrations/20261013_180000_drop_extraction_shadow_tables.sql`）。
- `migrations/20260605_030000_create_salesanchor_app_role.sql:16-17` が全表に SELECT/INSERT/UPDATE/DELETE を毎回再付与（`scripts/run_all_migrations.sh:326`）。

→ 表単位の REVOKE は次のデプロイで戻る。RLS（ポリシー）は再付与の影響を受けない。

## 6. 手本

`migrations/20260628_170000_add_app_fx_rates.sql`
- :46-47 ENABLE / FORCE ROW LEVEL SECURITY
- :51-54 `FOR SELECT USING (true)`
- :59-63 `FOR ALL` を `current_setting('app.is_operator', true) = 'true'` に限定

## 7. テスト・CI

- `backend/tests/test_rls_invariants.py` はダミー表。`backend/tests/rls_bootstrap.py` が実 migration を適用（002 は :15）。
- 実表を salesanchor_app で読む手本: `backend/tests/test_countries_master.py:113-171`。
- CI: `.github/workflows/test.yml`（:222, :224 env、:241 pytest、:250-251）、`migration-test.yml`、`migration-guard.yml`。

## 8. 障害：migration-guard チェック 8

- `scripts/check-migration-value-writes.py`（呼出 `.github/workflows/migration-guard.yml:405-408`, `:422-425`）。保護表 `protected-tables.txt:16` permissions、`:22` suppliers。
- 許可パターン（同スクリプト :35-42 付近）に `ALTER TABLE` はあるが `POLICY` が無い。`CREATE POLICY ... ON public.permissions` と `DROP POLICY IF EXISTS ... ON public.permissions` の行がブロックされることを、関数にサンプル行を当てて確認（scratchpad `guard-sample-run.txt`）。
- 先例 products（2026-06-26 作成）はガード強化（2026-10-07 commit 11093c72a）より前のため通過していた。

## 9. 未確認

- なし（段階①の設計に必要な前提は全て確認済み）。
