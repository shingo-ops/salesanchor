# ADR-SA-19: DB セキュリティ検証ゲート

**Status**: Accepted（Phase1 実装済み）  
**Date**: 2026-06-05  
**Author**: Hikky-dev  
**PO**: shingo-ops

---

## What（何を）

RLS 不変条件を CI とデプロイ後スモークの2段階で機械検証するゲートを設ける。

| ゲート | タイミング | 内容 |
|--------|-----------|------|
| CI（RLS invariants） | PR → CI | `salesanchor_app` で 4 不変条件テスト |
| デプロイ後スモーク | Phase2 から | 7 チェック（RLS/role/接続/クロステナント/フェイルクローズ/app 接続ユーザー） |

---

## Why（なぜ）

ADR-SA-18 で `salesanchor_app` を作成しても、  
「RLS が実際に機能するか」は自動検証がないと将来のマイグレーションで壊れるリスクがある。  
ゲートを設けることで:
- RLS 破壊を PR 段階で検出
- デプロイ後も `jarvis`（BYPASSRLS）がアプリ接続に残っていないことを確認

---

## Scope（対象）

### Phase 1（本 ADR・additive only）

- CI: `salesanchor_app` ロール作成（DML のみ、CREATE なし）
- CI: `RLS_TEST_DATABASE_URL`（salesanchor_app）、`RLS_ADMIN_DATABASE_URL`（jarvis）環境変数設定
- `backend/tests/test_rls_invariants.py` — 4 不変条件テスト（新規）
- 既存 RLS テストの DDL を admin 接続に移行（CI role = DML only の不変条件）
- `scripts/smoke_test_post_deploy.sh` — 7チェックスモークスクリプト（先行作成・Phase2 からフック）

### Phase 2（別 PR）

- `deploy.yml` から `smoke_test_post_deploy.sh` 呼出
- スモーク [7] 精緻化（`application_name` タグ）
- スモーク [5] 種 tenant_id → 999999

---

## CI ゲート詳細

### `salesanchor_app` ロール（test.yml）

```yaml
DO $$ BEGIN
  CREATE ROLE salesanchor_app
    WITH LOGIN PASSWORD 'apppass'
    NOSUPERUSER NOCREATEDB NOBYPASSRLS;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'salesanchor_app already exists, skipping';
END $$;
-- DML のみ（CREATE は付与しない。CI role = 本番 role の契約）
GRANT USAGE ON SCHEMA public TO salesanchor_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO salesanchor_app;
```

**契約: CI role = 本番 role（DML 限定）**  
salesanchor_app には CREATE 権限を付与しない。テスト用テーブルの DDL は admin（jarvis）が担当。

### 環境変数

```yaml
RLS_TEST_DATABASE_URL: postgresql+asyncpg://salesanchor_app:apppass@localhost:5432/jarvis_test_db
RLS_ADMIN_DATABASE_URL: postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db
```

---

## 4 不変条件テスト（`test_rls_invariants.py`）

| # | テスト | 内容 |
|---|--------|------|
| 1 | `test_cross_tenant_blocking` | tenant=A が tenant=B 行を SELECT できない |
| 2 | `test_shared_rows_operator_only` | is_operator 未設定で共有行 INSERT → 42501 |
| 3 | `test_failclose_unset_is_operator` | `RESET app.is_operator` 後 → 拒否 |
| 4 | `test_pool_pollution_prevention` | operator リセット後 → tenant が共有行を書けない |

---

## スモークテスト 7 チェック（`scripts/smoke_test_post_deploy.sh`）

| # | チェック内容 |
|---|------------|
| 1 | `public.translation_glossary` の RLS 有効確認 |
| 2 | ポリシー 4 本確認 |
| 3 | `salesanchor_app` が NOSUPERUSER NOBYPASSRLS であることを確認 |
| 4 | `salesanchor_app` 実接続テスト |
| 5 | クロステナント遮断カナリア（admin が種行挿入 → app で見えないことを確認） |
| 6 | フェイルクローズ（`is_operator` 未設定 → 42501） |
| 7 | `pg_stat_activity` で app backend が `jarvis`（BYPASSRLS）で接続していないことを確認 |

Phase1 ではスクリプトを先行作成。Phase2 で `deploy.yml` からフックする。

---

## 関連 ADR

- `ADR-SA-18-app-db-least-privilege.md` — `salesanchor_app` ロールの詳細
