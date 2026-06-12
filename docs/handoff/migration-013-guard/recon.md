# recon — migration 013 が部分テナントで deploy パイプラインを止める

## KGI（定量・PO承認待ち）

- **本番 deploy パイプラインのブロック解消**: release #2081 のデプロイは `Run database migrations` ステップが [2/145] で abort し、以降の全 migration が未実行。**次回以降の全デプロイが同地点で失敗する**状態を 0 にする。
- **再発防止**: 過去 migration 未遡及の部分テナント（新規テナント onboarding で発生）が **1 件でも存在すると deploy 全体が止まる**脆弱性を解消し、「部分テナント存在 → loud-warn してデプロイ継続、整合性は schema-check が検出」に変える。

## 事実（推測禁止・file:line / ログ直接証拠）

### 1. 失敗の直接証拠（deploy run 27432430556 / commit 8016a5a5）

`Run database migrations` ステップ [2/145]（`psql < migrations/013_add_meta_webhook_idempotency.sql`）でログ:

```
NOTICE:  Processing schema: tenant_001
NOTICE:  meta_messages: message_id column and unique index applied for tenant_001
ERROR:  column "source" does not exist
QUERY:  SELECT source FROM tenant_001.leads WHERE source LIKE 'messenger:%' ...
CONTEXT: PL/pgSQL function inline_code_block line 39 at EXECUTE
```

= **`tenant_001.leads` に `source` 列が存在しない**。`psql -v ON_ERROR_STOP=1`（`scripts/run_all_migrations.sh:25`）のため migration 全体が abort。

### 2. 該当コード

- `migrations/013_add_meta_webhook_idempotency.sql:53` — `leads.source` を**列存在チェックなしで参照**する `EXECUTE format('SELECT COUNT(*) ... SELECT source FROM %I.leads ...')`。全 `tenant_%` schema をループ（`migrations/013_add_meta_webhook_idempotency.sql:20`）。
- `scripts/run_all_migrations.sh:74` — `run_sql migrations/013_add_meta_webhook_idempotency.sql`（実行2番目・leads 系 migration より前）。
- `scripts/run_all_migrations.sh:25` — `PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"`（1件のエラーで全体停止）。

### 3. `leads.source` の出所と順序の矛盾

- `migrations/003_add_phase1_tenant_tables.sql:83` — `source VARCHAR(50),`（leads.source を作る初期プロビジョニング migration）。
- **`003` は `scripts/run_all_migrations.sh` に登録されていない**（`grep 003_add_phase1` → 0 件）。初期テナント作成時のみ適用される。
- したがって `003` 未適用の部分テナントでは leads.source が無く、`013`（`scripts/run_all_migrations.sh:74`）が先に参照して落ちる。

### 4. release #2081 は migration/script を一切変更していない

- `git log 57df8f1e..8016a5a5 -- migrations/ scripts/` → 0 件。直前の成功デプロイ（57df8f1e・16:44）と migration コードは同一。
- → 変わったのは **tenant_001 の DB スキーマ状態**（16:44〜17:41 の間に部分スキーマで作成/リセット）。PO が同時間帯にアカウント（テナント）操作をしていた、と Hitoshi さん確認済み。

### 5. 既存 ADR（着手前検索・FEATURE-INDEX 経由）

- `docs/adr/ADR-036-tenant-schema-integrity.md:1` — 「新規テナントを作成しても同じ問題が2度と発生しない」を 4 レベルで保証。**全操作 idempotent・マージ判断は Shingo（自動マージ禁止）**。Level 1 = `scripts/db/sync_tenant_schema.py`（tenant_004 基準で全テナント差分を同期）。Level 3 = `schema-check.yml`（差分で PR ブロック）。
- `docs/adr/ADR-034-tenant-migration-automation.md:1` — 新規テナント migration 自動化＋既存テナント整合化（Proposed）。同一原因（過去 migration 未遡及）を扱う。
- `scripts/db/sync_tenant_schema.py:382` — `async def main(dry_run)`。`docker compose exec -e DATABASE_URL=... backend python /app/scripts/db/sync_tenant_schema.py [--dry-run]`。冪等。
- **ADR-036/034 のツール群は実装済みだが `deploy.yml` には未配線**（`grep sync_tenant_schema .github/workflows/deploy.yml` → 0 件。deploy は `.github/workflows/deploy.yml:457` の `bash scripts/run_all_migrations.sh` のみ）。

## 制約

- 私（Hikky-dev）の本番 VPS SSH は **読み取り専用 forced-command** に制限済み（PR #2078「SSH鍵隔離」）。**DB 直接クエリ・schema 修正・sync スクリプト実行は不可** → 本筋の tenant_001 整合は PO（DB アクセス保有）が実施。
- 本変更は `migrations/` を含む＝危険パス。ADR-135 / ADR-036 により **develop マージ・本番デプロイは PO 明示 GO 待ち**。
