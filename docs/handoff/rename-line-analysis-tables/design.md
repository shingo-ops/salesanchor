# design: LINE解析テーブルリネーム

作成日: 2026-09-22  
ブランチ: release/rename-line-analysis-tables  
関連 ADR: ADR-090（LINE解析パイプライン）, ADR-156（商品マスタ整備）

---

## 背景・動機

public.units / public.conditions は LINE解析パイプライン専用テーブルだが、
ADR-156 で新設された正式マスタ quantity_units / condition_definitions と
名前の意味が重複し混乱を招く。line_ 接頭辞を付与して区別を明確にする。

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
| 旧名で SELECT 可能 | SELECT count(*) FROM public.units が整数を返す | ○: エラーなし |
| 新名で SELECT 可能 | SELECT count(*) FROM public.line_units が旧名と同じ件数を返す | ○: 件数一致 |
| 既存 API 正常動作 | LINE解析画面でエラーなし | ○: 502/500 なし |

---

## Phase 2（将来PR）: コード更新

Phase 1 の VIEW が安定稼働確認後（1週間程度）に実施。

### 対象ファイル（予定・Phase 2 以降で変更）

- backend/app/routers/tcg_line_import.py: units → line_units, conditions → line_conditions
- backend/app/services/tcg_line_import_svc.py: 同上
- backend/app/services/tcg_line_android_parser.py: 同上
- backend/tests/test_tcg_line_import.py: フィクスチャ更新

Phase 2 完了後に VIEW を DROP する Phase 3 も予定。

---

## 弊害・リスク

| リスク | 対策 |
|--------|------|
| FK 参照テーブルが VIEW に INSERT 不可 | units/conditions は参照先FK なし（親テーブル側）。子から親へのFKは RENAME で自動更新済み |
| 単純 VIEW では INSERT が通らないケース | CREATE VIEW AS TABLE は全列投影の単純VIEW → PostgreSQL でINSERT/UPDATE/DELETE 透過 |
| 冪等性失敗（二重実行） | IF EXISTS / IF NOT EXISTS で保護済み |

---

## 外部・過去事例の参照と我々への応用

守り手: Shingo（PO）・Hikky-dev（実装）

- PostgreSQL 公式 ALTER TABLE RENAME: FK・INDEX は自動追従するため、既存の参照整合性が失われない。本実装で FK 付きテーブルが存在してもリネーム後も有効。参照: https://www.postgresql.org/docs/current/sql-altertable.html
- PostgreSQL 公式 CREATE VIEW (updatable views): 全列投影の単純 VIEW は INSERT/UPDATE/DELETE が透過的に動作する。本実装の後方互換 VIEW は WHERE 句・集計なしの TABLE public.line_units 形式であり updatable view 条件を満たす。参照: https://www.postgresql.org/docs/current/sql-createview.html
- 過去事例: ADR-090 パイプライン tables を tenant_004 から public に移行したとき（PR #3500系）と同じパターン（DDL のみ・後方互換維持）。

---

## 維持の仕組み

守り手: Phase 2 PR 作成担当者

Phase 2 でコード更新後、grep -r で units/conditions への SQL 参照が 0件 になったことを確認してから VIEW を DROP する。DROP 前にこのチェックを CI gate として追加するかは Phase 2 PR で検討。

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
