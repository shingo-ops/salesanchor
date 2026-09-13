# recon — lead_attachments テーブル作成マイグレーション

> この文書は何か（専門用語なしの1行）:
> 顧客から届いた添付ファイルの台帳となるDBテーブルを作る前に、
> 既存のDB・マイグレーション構成を実測して記録したもの。

対象ADR: ADR-091
親テーマ: docs/specs/attachment-storage/README.md

## 実測（2026-09-01）

### migrations/ の最新状態

- 直近3件（`ls -t migrations/ | head -3` 実測）:
  - `20260902_100000_create_lead_attachments.sql`（本便で追加）
  - `20260901_090000_add_condition_resolution_columns.sql`
  - `20260831_110000_create_tcg_analysis_tables_t004.sql`
- 実行済みの最終ファイルは `20260831_110000_create_tcg_analysis_tables_t004.sql`（本便着手時点）

### run_all_migrations.sh の構造

- ファイル行数: 534行（本便着手時点）
- `run_sql` 関数定義: `scripts/run_all_migrations.sh:61`
  ```sh
  run_sql() {
      local file="$1"
      docker exec -i "${POSTGRES}" ${PSQL} < "${REPO_DIR}/${file}"
  }
  ```
- 最終 `run_sql` 行: `scripts/run_all_migrations.sh:530`
  - 内容: `run_sql migrations/20260831_110000_create_tcg_analysis_tables_t004.sql`
- 新規 `run_sql` 行の挿入位置: 行530の直後（`echo ""` ブロックの前）

### 参照実装（同型の実装）

- `migrations/026_create_customer_contact_channels.sql`:
  - pg_namespace walk で `tenant_NNN` スキーマを列挙する DO ブロック方式
  - `EXECUTE format(...)` による動的SQL（スキーマ名埋め込み）
  - `IF NOT EXISTS` による冪等性
  - `trg_set_updated_at()` 関数（スキーマ別作成）
  - RLS + ポリシーの pg_policies 存在確認

### current_tenant_id() 存在確認

- `public.current_tenant_id()` は `public` スキーマの関数として既存（026実装と同じ参照方法）

### leads テーブル存在確認

- `pg_tables WHERE schemaname = schema_rec.nspname AND tablename = 'leads'` で存在チェック済み
- leads テーブルが存在しないスキーマには `lead_attachments` を作成しない（CONTINUE で skip）

### message_id の一意性

- 同一の添付ファイルが複数回 webhook で届いても二重保存しないために
  `message_id` に UNIQUE INDEX を付ける（Discord の message_id は全プラットフォームで一意）

## 本便で変更する箇所

- `migrations/20260902_100000_create_lead_attachments.sql`: 新規作成（134行）
- `scripts/run_all_migrations.sh`: 3行追加（空行1・コメント1・run_sql 1）

いずれも既存行を変更しない追加のみ。
