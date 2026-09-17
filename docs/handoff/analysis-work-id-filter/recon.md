# recon.md — analysis-work-id-filter

## 問題

解析レビュー画面（仕入元品質詳細）で、解析結果に作品情報（work_id / 作品名）が表示されない。
作品ごとの絞り込みもできない。
Gemini は work_id を出力し extraction_items.resolved_work_id に保存されているが、
analysis_results → フロント表示の経路で作品情報が欠落している。

## 根本原因

| 要因 | 詳細 |
|------|------|
| SELECT に work_id なし | `backend/app/services/tcg_analysis_review_svc.py:200-201` で p.product_code, p.name のみ取得。p.work_id 未取得 |
| tcg_series JOIN なし | `backend/app/services/tcg_analysis_review_svc.py:40` で LEFT JOIN public.products p はあるが、tcg_series への JOIN がない |
| API レスポンスに work_id なし | `backend/app/services/tcg_analysis_review_svc.py:256-268` の system dict に work_id/work_name フィールドなし |
| Pydantic スキーマに work_id なし | `backend/app/routers/tcg_analysis_review.py:47-58` の SystemFields に work_id/work_name なし |
| エンドポイントに work_id フィルタなし | `backend/app/routers/tcg_analysis_review.py:105-116` のクエリパラメータに work_id なし |
| フロント表示に作品名なし | `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:31` に作品名の ComparisonMetadataRow なし |
| フロントにフィルタ UI なし | `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx` に作品フィルタなし |

根拠:
- `backend/app/services/tcg_analysis_review_svc.py:33-42`（_BASE_FROM: LEFT JOIN public.products p のみ）
- `backend/app/services/tcg_analysis_review_svc.py:190-225`（SELECT カラム一覧に work_id なし）
- `backend/app/services/tcg_analysis_review_svc.py:256-268`（system dict に work_id なし）
- `backend/app/services/tcg_analysis_review_svc.py:49-102`（_build_where: work_id 条件なし）
- `backend/app/routers/tcg_analysis_review.py:47-58`（SystemFields に work_id なし）
- `backend/app/routers/tcg_analysis_review.py:105-116`（エンドポイントパラメータに work_id なし）
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:31`（作品名行なし）
- `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:47,68`（API呼び出しに work_id パラメータなし）

## データ経路（事実）

```
public.products.work_id (UUID NOT NULL)
  ↑ migrations/20260909_000000:13 で追加
  ↑ migrations/20260916_130000:11 で NOT NULL 化
  ↓
{TCG_SCHEMA}.tcg_series.id (UUID PK)
  → display_name (TEXT NOT NULL): 英語作品名
  → alt_name (TEXT): 日本語作品名
  ↑ migrations/20260902_110000:38-47 で定義
  ↑ FK制約なし（データ整合性はアプリ層で担保）
```

## 既存の作品フィルタ実装（先例）

| 画面 | 実装方法 | 根拠 |
|------|---------|------|
| 商品マスタ一覧 | Tabs 金型 + works 配列 + URLパラメータ work_id | TcgProductMasterPage.tsx:84 |
| works 一覧 API | `/tcg/products/list` レスポンスに works フィールド | tcg_product_import.py:134-142 |
| works 型定義 | ProductWork(id, code, display_name, alt_name) | tcg_product_import.py:71-74 |

## 影響範囲

| ファイル | 役割 | 影響 |
|---------|------|------|
| `backend/app/services/tcg_analysis_review_svc.py` | 解析結果取得サービス | JOIN追加・SELECT追加・dict追加・WHERE追加 |
| `backend/app/routers/tcg_analysis_review.py` | 解析結果API | スキーマ追加・パラメータ追加・works一覧追加 |
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx` | 解析結果比較表示 | 作品名行追加 |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx` | 仕入元詳細画面 | works取得・Tabsフィルタ追加 |
| `frontend/src/locales/en.json` / `frontend/src/locales/ja.json` | i18n | キー追加 |

## ADR 参照

- ADR-027: UI文字列はt()経由（i18n強制）
- ADR-144: UI部品は金型優先（生select/生input禁止）
