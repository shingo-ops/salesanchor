# ADR-SA-18: アプリ DB 最小権限ロール（salesanchor_app）

**Status**: Accepted（Phase1 実装済み）  
**Date**: 2026-06-05  
**Author**: Hikky-dev  
**PO**: shingo-ops

---

## What（何を）

DB 接続ロールを2段階で分離する:

| ロール | 用途 | 権限 |
|--------|------|------|
| `jarvis` | マイグレーション・管理操作 | SUPERUSER + BYPASSRLS |
| `salesanchor_app` | アプリ実行時 | NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE、DML のみ |

---

## Why（なぜ）

**ADR-SA-17 監査で判明**: `jarvis` は SUPERUSER かつ BYPASSRLS のため、  
`FORCE ROW LEVEL SECURITY` を設定しても全 RLS ポリシーが完全に無効化される。  
アプリが `jarvis` で接続している限り、マルチテナント RLS は機能していない。

`salesanchor_app`（NOSUPERUSER NOBYPASSRLS）で接続することで:
- RLS ポリシーが実際に適用される
- SQL インジェクションや誤クエリが他テナントのデータに触れない
- 最小権限の原則を実施

---

## Scope（対象）

### Phase 1（本 ADR・additive only）

- `salesanchor_app` ロール作成（migration で冪等）
- public スキーマおよび既存 tenant_NNN スキーマ全件への DML 付与
- CI ゲート強化（SA-19）
- **アプリの接続先は変更しない**（依然 `jarvis`）

### Phase 2（別 PR・§5 監査後）

- `tenant.py` の `create_tenant_schema`: 管理者接続に切替
- Celery `process_data_deletion`: 管理者接続または per-tenant context 設定
- `deploy.yml`: DATABASE_URL を `salesanchor_app` に切替
- スモークテスト呼出 + `SALESANCHOR_APP_PASSWORD` Secrets 登録

---

## Migration（Phase 1）

### `20260605_030000_create_salesanchor_app_role.sql`

```sql
-- salesanchor_app 作成 + public スキーマ付与（冪等）
-- パスワードは deploy bootstrap ステップで ALTER ROLE ... PASSWORD で注入（SQL に書かない）
DO $$ BEGIN
  CREATE ROLE salesanchor_app
    LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'salesanchor_app already exists, skipping CREATE';
END $$;

GRANT CONNECT ON DATABASE jarvis_db TO salesanchor_app;
GRANT USAGE ON SCHEMA public TO salesanchor_app;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO salesanchor_app;
```

### `20260605_040000_grant_salesanchor_app_tenant_schemas.sql`

既存 `tenant_NNN` スキーマ全件への GRANT（pg_namespace ループ・冪等）。

---

## Phase 2 準備リスト（このPRでは未実装）

- [ ] §5 監査: `tenant.py:1453` CREATE SCHEMA → admin 接続
- [ ] §5 監査: Celery `process_data_deletion` → admin 接続 or テナント context 設定
- [ ] `deploy.yml`: DATABASE_URL 切替（salesanchor_app）
- [ ] `deploy.yml`: bootstrap ステップ（DB 起動 → ロール作成 + PW 設定 → app 起動 → migration → smoke）
- [ ] `SALESANCHOR_APP_PASSWORD` GitHub Secrets 登録（URL 安全文字のみ: alphanumeric + `-._~`。`@:/'"` 禁止）
- [ ] スモーク [7] 精緻化: `application_name` タグで app/admin 接続を識別

---

## 関連 ADR

- `ADR-SA-17-translation-bidirectional-glossary-two-layer.md` — RLS 監査の起点
- `ADR-SA-19-verification-gates.md` — CI ゲートの実装詳細
