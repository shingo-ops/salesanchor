# recon — 販売単位・状態マスタ連鎖プルダウン基盤

**仕事名**: product-unit-condition-infra
**日付**: 2026-09-22
**対象ADR**: ADR-025
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20260922_060000_product_unit_condition_infra.sql:1` | マイグレーションファイル（本PR唯一の変更） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | quantity_units.value の NOT NULL 制約が既存データに影響するか | DDL変更のみ（DROP NOT NULL）、既存データへの影響なし | ✅ 解消済み |
| 2 | LINE解析用テーブル（units/conditions）との区別が不明瞭 | COMMENT ON TABLE でラベル明記 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 本マイグレーションはDDLのみ（CREATE TABLE IF NOT EXISTS / COMMENT ON / ALTER TABLE）
- DMLなし（INSERT/UPDATE/DELETE一切なし）
- ADR-025（手動INSERT原則禁止）遵守
- 既存テーブル（units/unit_aliases/conditions/condition_aliases）の構造・データへの変更なし
