# recon — fix-supplier-channels-created-at

**仕事名**: fix-supplier-channels-created-at  
**日付**: 2026-09-06  
**対象ADR**: ADR-154  
**担当**: Hikky-dev (FIX-05)

---

## 障害事実（2026-09-05 深夜）

PR #3311 デプロイ後に「新規登録」（action='create'）で 500 エラー。

```
Database error: POST /api/v1/tcg/line-import/{job_id}/resolve
(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError)
<class 'asyncpg.exceptions.UndefinedColumnError'>:
column "created_at" of relation "supplier_channels" does not exist

[SQL:
    INSERT INTO tenant_004.supplier_channels
      (id, supplier_id, channel, is_active, created_at)
    VALUES
      ($1, $2, 'line', TRUE, now())
]
```

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/routers/tcg_line_import.py:512` | `created_at` を含む INSERT 文（本 PR で修正） |
| `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:189` | `supplier_channels` CREATE TABLE 定義 |

---

## supplier_channels の実在列（DDL から確定）

```sql
-- migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:189
CREATE TABLE IF NOT EXISTS %I.supplier_channels (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id UUID        NOT NULL
                                REFERENCES %I.tcg_suppliers (id) ON DELETE CASCADE,
    channel     VARCHAR(50) NOT NULL,
    external_id TEXT,
    is_active   BOOLEAN     NOT NULL,
    CONSTRAINT uq_supplier_channels_channel_external UNIQUE (channel, external_id)
)
```

**5列: id / supplier_id / channel / external_id / is_active**  
`created_at` は存在しない。

---

## 全 INSERT/UPDATE 確認（supplier_channels）

`grep -rn "supplier_channels" backend/app/ --include="*.py"` 結果:

- `backend/app/routers/tcg_line_import.py:512` — INSERT（本 PR で修正）
- backend/app/tasks/tcg_mirror.py:175,195 — LEFT JOIN（SELECT のみ・変更不要）
- backend/app/services/tcg_diagnostics_svc.py:51 — JOIN（SELECT のみ・変更不要）
- backend/app/services/tcg_parallel_report_svc.py:186 — JOIN（SELECT のみ・変更不要）
- backend/app/services/tcg_analysis_review_svc.py:36 — JOIN（SELECT のみ・変更不要）
- backend/app/services/tcg_line_import_svc.py:398 — FROM（SELECT のみ・変更不要）
- backend/app/services/tcg_supplier_quality_svc.py:42,80 — JOIN（SELECT のみ・変更不要）
- backend/app/services/tcg_distribution_svc.py:230 — JOIN（SELECT のみ・変更不要）

**INSERT/UPDATE は 1 箇所のみ。**

---

## 原因分析

本日6件目の「テスト緑・本番で落ちる」パターン。  
テストがDB接続なしのモック方式のため、存在しない列への INSERT が検出されない。  
今回追加したテスト（`test_supplier_channels_insert_columns_match_ddl`）は  
DDL と INSERT を静的照合するため DB 不要で検出可能。

---

## 未解決ゼロ確認

全て解消済み
