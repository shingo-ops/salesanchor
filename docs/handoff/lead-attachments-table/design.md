# 設計 — lead_attachments テーブル作成マイグレーション（便2）

> この文書は何か（専門用語なしの1行）:
> 顧客から届いた添付ファイルの情報（誰のどのファイルか）を記録するDB台帳を
> 全テナントのDBに作るための設計。

対象ADR: ADR-091
recon: docs/handoff/lead-attachments-table/recon.md
親テーマ: docs/specs/attachment-storage/README.md

## 1. あるべき姿

顧客が送った添付ファイルをサーバーに保存したとき、どのリードに紐づく
どのファイルを保存したかをDBで管理できる。
添付ファイルはリード削除と連動して台帳からも消える（CASCADE）。
テナント分離は既存の `current_tenant_id()` で担保される。

## 2. recon（実測）

docs/handoff/lead-attachments-table/recon.md を参照。
要点は次の3つ。
- `scripts/run_all_migrations.sh:530` が最終 `run_sql` 行であり、その直後に挿入する。
- 参照実装は `migrations/026_create_customer_contact_channels.sql`（同じ pg_namespace walk 方式）。
- `message_id` の UNIQUE INDEX により、同一添付の二重保存を防ぐ。

## 3. design（技術How）

### 作成するテーブル（全 tenant_NNN スキーマ）

```sql
tenant_NNN.lead_attachments (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL,
    lead_id         INTEGER NOT NULL REFERENCES tenant_NNN.leads(id) ON DELETE CASCADE,
    message_id      VARCHAR(64) NOT NULL,
    platform        VARCHAR(32) NOT NULL,
    file_path       TEXT NOT NULL,
    file_size       BIGINT NOT NULL,
    content_type    VARCHAR(128),
    original_filename TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

### インデックス（3件）

| インデックス名 | カラム | 用途 |
|---|---|---|
| `idx_la_lead_id` | `lead_id` | リード削除時の対象特定（高速化） |
| `idx_la_tenant_created` | `(tenant_id, created_at)` | 容量集計と古い順削除（便5） |
| `idx_la_message_id` | `message_id` | 同一添付の二重保存防止（UNIQUE） |

### トリガ

`trg_la_updated_at`: UPDATE 前に `updated_at = NOW()` をセット。
既存の `trg_set_updated_at()` 関数を利用（未定義スキーマ向けに冪等作成）。

### RLS

- `ALTER TABLE lead_attachments ENABLE ROW LEVEL SECURITY`
- ポリシー `tenant_isolation_lead_attachments`:
  leads を経由して `current_tenant_id()` とテナントを照合。

### 冪等性の保証

| 処理 | 冪等手段 |
|---|---|
| テーブル作成 | `CREATE TABLE IF NOT EXISTS` |
| インデックス作成 | `CREATE INDEX IF NOT EXISTS` |
| UNIQUE インデックス | `CREATE UNIQUE INDEX IF NOT EXISTS` |
| トリガ作成 | `pg_trigger` 存在確認 → IF NOT EXISTS ブロック |
| RLS ポリシー | `pg_policies` 存在確認 → IF NOT EXISTS ブロック |
| RLS 有効化 | `ALTER TABLE ENABLE ROW LEVEL SECURITY`（再実行は無害） |
| trg_set_updated_at() 関数 | `CREATE OR REPLACE FUNCTION` |

### 触らない範囲

- `migrations/` 以外のファイル（backend/frontend/docs/specs/）
- `docker-compose.yml`
- 既存マイグレーションファイル

## 4. 外部・過去事例の参照と我々への応用

### 外部事例

PostgreSQL の公式ドキュメント（Row Security Policies）では、
RLS ポリシーを `USING (tenant_id = current_setting('app.tenant_id')::int)` の形で
設計する例が示されている。多くの SaaS マルチテナント実装でこの方式が採用されている。

### 過去事例（社内）

`migrations/026_create_customer_contact_channels.sql` が同じ
pg_namespace walk + EXECUTE format + RLS の組み合わせで実装されており、
本番稼働中である。本便はその型をそのまま踏襲する。

### 我々への応用

新しいパターンを持ち込まず、026 の型をコピーすることで
レビュー・運用の学習コストをゼロにする。

## 5. 弊害・トレードオフ

- 弊害: pg_namespace walk は全スキーマを順次処理するため、
  テナント数が多いとマイグレーション実行時間が延びる。
  現状のテナント数（数件〜数十件）では許容範囲内。
- 弊害: `CREATE OR REPLACE FUNCTION trg_set_updated_at()` は
  既存の同名関数を上書きする。シグネチャ変更はないため影響なし。
- トレードオフ: `message_id` の UNIQUE INDEX により、
  Discord 以外のプラットフォームで message_id が空・重複する場合に INSERT が失敗する。
  保存処理（便3）で platform ごとの一意 ID を必ず付与する設計とする。

## 6. 受入基準

| 基準 | 検証方法 |
|---|---|
| マイグレーションSQLが構文エラーなし | psql --set ON_ERROR_STOP=1 で実行して exit 0 |
| テーブルが tenant_NNN スキーマに作成される | pg_tables に lead_attachments が存在する |
| 3インデックスが作成される | pg_indexes に idx_la_lead_id / idx_la_tenant_created / idx_la_message_id が存在する |
| RLS が有効になっている | pg_class.relrowsecurity = true |
| tenant_isolation_lead_attachments ポリシーが存在する | pg_policies にポリシー名が存在する |
| run_all_migrations.sh に登録されている | grep で run_sql migrations/20260902_100000_create_lead_attachments.sql が1件ヒット |
| 既存行を変更していない | git diff の削除行が0行である |
| DROP TABLE が存在しない | grep -c で0件 |

## 7. 維持の仕組み

- 守り手: Process Artifacts Gate（CI）が recon.md・design.md の存在・完成度を確認
- 守り手: run_all_migrations.sh への登録により、次回以降のマイグレーション実行で自動適用される
- 人手で守る部分: 便3（受信・保存）実装時に lead_attachments への INSERT が正しく動くか
  実測による動作確認が必要（マイグレーションだけでは INSERT 経路はカバーしない）
