<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。 -->
# Phase 3 設計 — 商品マスタの新規追加が 500 になる（便 F1）

**対象ADR**: ADR-1020
**recon**: docs/handoff/fix-product-create-category-id/recon.md
**日付**: 2026-11-10
**担当**: Planner（Opus）・実装はクラウドの Sonnet
**上位の設計**: release/estimate-sheet-auto ブランチの docs/handoff/estimate-sheet-auto/design.md §7-9「実装カード: 商品の新規登録の 500 を直す（便 F1）」（PO 決定とカードの全文）

## 目的
- 商品マスタ画面の「新規追加」で、商品を登録できるようにする（今はどの商品でも 500）。
- PO の言葉（2026-11-10）: 「不具合なおして進めて」。

## 外部・過去事例の参照と我々への応用
- 該当なし：原因はこのリポジトリの1コミット（90367c1a3）で入った型の食い違いで、外部の事例で判断する点がない。過去の形（`::text` で文字どうしを比べる）は同じ SQL の work_id・manufacturer_id で今も使っており、その形に戻す。

## 変更
- 重複の確かめは文字どうしで比べる（9-20 より前の形）。書く側だけ数に直す。数にできない値は ValueError → 入口で 422。
- 触るファイル: サービス1つ・試験4つ。画面・入口・CSV の道・他の SQL は触らない。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 文字の "1" で登録でき、DB には数で入る | CI の PostgreSQL で `backend/tests/test_tcg_completion_safety.py` の test_new_product_registration_accepts_category_id_as_text |
| INSERT に渡る値が数 | `backend/tests/test_product_required_fields.py` の test_create_product_converts_text_category_id_to_int |
| 数にできない値は止まり、何も書かれない | `backend/tests/test_product_required_fields.py` の test_create_product_rejects_non_numeric_category_id |
| 既存の試験が通る | CI の pytest が緑 |
| 本番で直った | 反映後、商品マスタ画面から EB-06 を登録して成功し、本番 DB で EB-06 が1件 |

## 弊害・トレードオフ
- 重複の確かめは文字で比べるので、商品区分の索引は使わない → 同じ SQL の他の比べも同じ形で、件数は共用マスタの範囲。
- 戻し方: マージの1コミットを revert。DB の変更なし。

## 維持の仕組み
守り手: backend/tests/test_tcg_completion_safety.py
- 文字の道の実 DB 試験が CI の必須 pytest で毎回流れる。比べ方を数に戻すと、この試験が落ちる。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | カードどおりの実装と試験 | クラウドの Sonnet（済み） |
| 2 | 審査・CI・GO・マージ・反映 | Opus |
| 3 | 本番で5商品を登録して確かめる | Opus |
