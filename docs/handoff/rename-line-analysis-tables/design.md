# design: LINE解析テーブルリネーム

作成日: 2026-09-22  
ブランチ: release/rename-line-analysis-tables  
関連 ADR: ADR-090（LINE解析パイプライン）, ADR-156（商品マスタ整備）

---

## 背景・動機

`public.units` / `public.conditions` は LINE解析パイプライン専用テーブルだが、
ADR-156 で新設された正式マスタ `quantity_units` / `condition_definitions` と
名前の意味が重複し混乱を招く。`line_` 接頭辞を付与して区別を明確にする。

---

## Phase 1（本PR）: RENAME + 後方互換VIEW

### 変更内容

| 旧テーブル名 | 新テーブル名 | 後方互換VIEW |
|------------|------------|------------|
| public.units | public.line_units | public.units (VIEW) |
| public.unit_aliases | public.line_unit_aliases | public.unit_aliases (VIEW) |
| public.conditions | public.line_conditions | public.conditions (VIEW) |
| public.condition_aliases | public.line_condition_aliases | public.condition_aliases (VIEW) |

### 検証方法（KGI/KPI）

| 基準 | 検証方法 | 合否判定 |
|------|---------|---------|
| マイグレーション完走 | デプロイログに NOTICE 4件（RENAME成功） + NOTICE 4件（VIEW作成成功）が出力される | ○: 8件の NOTICE が全部出る |
| 旧名で SELECT 可能 | `SELECT count(*) FROM public.units;` が整数を返す | ○: エラーなし |
| 新名で SELECT 可能 | `SELECT count(*) FROM public.line_units;` が旧名と同じ件数を返す | ○: 件数一致 |
| 既存 API 正常動作 | LINE解析画面でエラーなし | ○: 502/500 なし |

---

## Phase 2（将来PR）: コード更新

Phase 1 の VIEW が安定稼働確認後（1週間程度）に実施。

### 対象ファイル（予定）

- `backend/app/routers/line_analysis.py`: `units` → `line_units`, `conditions` → `line_conditions`
- `backend/app/services/line_parser.py`: 同上
- `backend/app/models/line_units.py`: モデル定義のテーブル名変更
- `frontend/src/api/lineAnalysis.ts`: API エンドポイント名変更（BE と合わせて）
- `backend/tests/test_line_parser.py`: フィクスチャ更新

Phase 2 完了後に VIEW を DROP する Phase 3 も予定。

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| FK 参照テーブルが VIEW に INSERT → 不可 | units/conditions は参照先FK なし（親テーブル側）。子から親へのFKは RENAME で自動更新済み |
| 単純 VIEW では INSERT が通らないケース | `CREATE VIEW ... AS TABLE ...` は全列投影の単純VIEW → PostgreSQL でINSERT/UPDATE/DELETE 透過 |
| 冪等性失敗（二重実行） | IF EXISTS / IF NOT EXISTS で保護済み |

---

## 外部事例

- [PostgreSQL 公式: ALTER TABLE RENAME](https://www.postgresql.org/docs/current/sql-altertable.html) — FK / INDEX は自動追従
- [PostgreSQL 公式: CREATE VIEW updatable](https://www.postgresql.org/docs/current/sql-createview.html) — "A simple view is automatically updatable"

---

## 戻し方

```sql
-- VIEW を DROP して元のテーブル名に戻す（本番未適用ならマイグレーション削除のみ）
DROP VIEW IF EXISTS public.units CASCADE;
DROP VIEW IF EXISTS public.unit_aliases CASCADE;
DROP VIEW IF EXISTS public.conditions CASCADE;
DROP VIEW IF EXISTS public.condition_aliases CASCADE;
ALTER TABLE public.line_units RENAME TO units;
ALTER TABLE public.line_unit_aliases RENAME TO unit_aliases;
ALTER TABLE public.line_conditions RENAME TO conditions;
ALTER TABLE public.line_condition_aliases RENAME TO condition_aliases;
```
