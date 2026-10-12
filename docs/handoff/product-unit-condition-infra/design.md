# Phase 3 設計 — 販売単位・状態マスタ連鎖プルダウン基盤

**対象ADR**: ADR-025
**recon**: docs/handoff/product-unit-condition-infra/recon.md
**日付**: 2026-09-22
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本マイグレーションはDDLのみの構造整備であり、外部事例参照は不要と判断。既存の quantity_units / condition_definitions テーブルの設計を踏襲する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| マイグレーションSQL構文が正しい | CI postgres lint / psql 実行 |
| 既存テーブルのデータに影響がない | CI diff（DMLなし確認） |
| 3テーブルが正常に作成される | DB接続後 \dt で確認 |

---

## 技術 How・KPI

- KPI: マイグレーション実行後にエラーゼロ、既存テーブルのデータ件数変化ゼロ
- 技術選択: PostgreSQL DDL（CREATE TABLE IF NOT EXISTS / COMMENT ON / ALTER TABLE）
  - CREATE TABLE IF NOT EXISTS で冪等性を確保
  - REFERENCES FK でデータ整合性を保証
  - UNIQUE 制約で重複登録を防止

---

## 弊害・トレードオフ

- quantity_units.value の NOT NULL → NULL 変更は後方互換性あり（既存データは変更なし）
- product_line_available_units / unit_condition_links / product_quantity_units は空テーブルとして作成（値はアプリ/CSV投入）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | マイグレーションファイル作成 | Generator |
| 2 | CI確認 | Generator |
| 3 | 本番適用（PO GO後） | しんごさん |

---

## 継続

- 完了後の監視: 本番適用後、3テーブルの存在確認（\dt）
- 次フェーズへの引き継ぎ: アプリ/CSVからのデータ投入（quantity_units / condition_definitions / product_line_available_units / unit_condition_links / product_quantity_units）
