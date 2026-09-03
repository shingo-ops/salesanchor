# PARITY-03 商品割り当て変更ドロワー — recon.md

作成日: 2026-09-03
ブランチ: release/parity03-product-assign-drawer

---

## 既存 ADR 検索結果

ADR-154（GAS→Python 段階移植）: `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`
本 PR は migration なし（ロジック変更のみ）。

---

## 問題の実態

1. 解決済みの行を「修正する」で開いてもドロワーに何も表示されない  
   (`MasterMaintenanceSection` が `return null` を返す)

2. 「修正する」ボタンが `MASTER_ISSUE_IDS` のある行にしか表示されない  
   (解決済み行にはボタンが出ない)

3. 商品割り当てを確認・変更しても記録がなく、180件作業で同じ行を重複確認する

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:91` | `MASTER_ISSUE_IDS` 条件付きボタン表示（削除対象） |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:382` | `MasterMaintenanceSection` — resolved 行は null 返却 |
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:387` | `return null`（新 `ProductAssignSection` に差し替え） |
| `frontend/src/features/tcg-analysis-review/reviewIssues.ts:1` | `AtomicReviewIssueId` 型定義（PRODUCT_CONFIRMED 追加） |
| `frontend/src/features/tcg-analysis-review/reviewIssues.ts:2` | tone 型: `'warning' | 'danger'`（'success' 追加） |
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:6` | `AnalysisReviewItem` 型（system は Record<string,string> で変更不要） |
| `backend/app/services/tcg_analysis_review_svc.py:106` | `_compute_issues` — `PRODUCT_CONFIRMED` 引数追加 |
| `backend/app/services/tcg_analysis_review_svc.py:189` | SELECT `p.code AS product_code` — `product_title` / `product_uuid` 追加 |
| `backend/app/services/tcg_product_master_svc.py:127` | `p.code AS product_id` — `p.id::text AS product_uuid` 追加 |
| `backend/app/routers/tcg_product_master.py:61` | `SearchCandidate` モデル — `product_uuid` フィールド追加 |
| `backend/app/services/item_corrections_svc.py:15` | `save_corrections` — product_id 変更時に analysis_results UPDATE 追加 |
| `backend/app/routers/item_corrections.py:40` | `SaveCorrectionsRequest` — 変更なし（既存エンドポイント利用） |

---

## 触らない範囲

- `analysis_results` テーブル定義 — migration 不要
- `item_corrections` テーブル定義 — migration 不要
- R-1 エンドポイント本体 (`reanalyze`) — 変更なし
- `RegistrationSection` / `SearchKeywordSection` / `ExcludedSection` — 変更なし
- `SearchKeywordSection` が使う `selected.product_id`（コード）は変更しない（search 結果の product_id は既存通り code のまま、product_uuid を追加）

---

## 確認済みバッジ実装方針

GAS `reviewIssues.ts` に "confirmed" の概念なし → 新設。

- `PRODUCT_CONFIRMED` を `AtomicReviewIssueId` に追加（`tone: 'success'`, `label: '確認済み'`）
- `needsReviewIssueIds` には含めない（問題バッジではない）
- PR #3247 で追加した `badge-success` CSS を自動利用
- Backend: `item_corrections` に `field_name='product_id' AND system_value=human_value` 行があれば追加
