# PARITY-03 商品マスタ登録 API — design.md

**対象ADR**: ADR-045, ADR-154  
**recon**: docs/handoff/parity03-product-master-drawer-be/recon.md  
**日付**: 2026-09-03  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- ADR-154（GAS→Python 段階移植方針）の延長実施。同方針の先行 PR（parity03-supplier-quality-be）がロールモデル。
- additive-only migration（ADR-045）: `mark` / `english_title` 列を #3246 で追加済み。本 PR は INSERT のみ（スキーマ変更なし）。
- 認証: `require_super_admin` — 商品マスタ登録は管理者専用操作。既存パターン踏襲（tcg_analysis_review と同一）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 認証なしで全エンドポイントが 401/403 を返す | `pytest backend/tests/test_tcg_product_master.py::test_registration_form_requires_auth` 他 5件 |
| B-1 登録フォームが item.mark / item.english_title を返す | `pytest backend/tests/test_tcg_product_master.py::test_registration_form_ok` |
| B-3 登録時に mark / english_title が DB に渡される | `pytest backend/tests/test_tcg_product_master.py::test_create_product_with_mark_english_title` |
| B-4 商品名検索が candidates を返す | `pytest backend/tests/test_tcg_product_master.py::test_search_ok` |
| B-2 重複チェックが candidates[] を返す | `pytest backend/tests/test_tcg_product_master.py::test_check_duplicates_ok` |
| B-5 キーワード追加が ok:true を返す | `pytest backend/tests/test_tcg_product_master.py::test_add_keyword_ok` |
| R-1 再解析が before/after を返す | `pytest backend/tests/test_tcg_product_master.py::test_reanalyze_ok` |
| CI pytest が全 16 tests PASS | CI `pytest-run-internal` ジョブ green |

---

## 技術 How・KPI

- KPI: 16 テスト全 PASS / lint clean / process-artifacts gate green
- 技術選択: FastAPI + AsyncSession（既存パターン踏襲）。サービス層とルーター層を分離。
- 依存: #3246（mark/english_title 列）が先にマージされること

---

## 弊害・トレードオフ

- `mark` / `english_title` を先に INSERT しようとすると列が存在せず 500 エラー → #3246 先行適用が必須
- R-1 再解析は GAS 値に戻せない（ベースラインテーブル `analysis_results_gas_baseline_20260903` で手動復元）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | #3246 migration マージ（mark/english_title 列作成） | PO |
| 2 | #3239 本 PR マージ（API コード） | PO |
| 3 | #3243 item_corrections マージ | PO |
| 4 | #3244 FE ドロワー実装マージ | PO |
