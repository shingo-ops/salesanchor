# design.md — analysis-work-id-filter

参照: [recon.md](docs/handoff/analysis-work-id-filter/recon.md) / ADR-027（i18n強制） / ADR-144（UIガバナンス）

---

## 目的

解析レビュー画面（仕入元品質詳細）で作品名を表示し、作品ごとに解析結果を絞り込めるようにする。
商品マスタの既存 work_id を JOIN で参照し、データ重複なし（SSOT遵守）。

---

## 対象と対象外

| 区分 | 内容 | 理由 |
|------|------|------|
| **対象** | 解析結果に作品名を表示 | PO要件 |
| **対象** | 作品ごとの絞り込みフィルタ | PO要件 |
| **対象外** | analysis_results テーブルへの work_id カラム追加 | SSOT: products.work_id を JOIN で参照（方法A採用） |
| **対象外** | Gemini判定 work_id の保持改善 | 別テーマ |
| **対象外** | ParseReviewPage への作品表示 | 別画面・別テーマ |

---

## 変更箇所

触るファイル:
- `backend/app/services/tcg_analysis_review_svc.py`
- `backend/app/routers/tcg_analysis_review.py`
- `backend/tests/test_tcg_analysis_review.py`
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx`
- `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx`
- `frontend/src/locales/en.json`
- `frontend/src/locales/ja.json`
- `docs/handoff/analysis-work-id-filter/recon.md`
- `docs/handoff/analysis-work-id-filter/design.md`

削除するファイル:
- `backend/app/services/tcg_analysis_review_svc.py`（既存行の変更）
- `backend/app/routers/tcg_analysis_review.py`（既存行の変更）
- `backend/tests/test_tcg_analysis_review.py`（既存行の変更）
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx`（既存行の変更）
- `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx`（既存行の変更）
- `frontend/src/locales/en.json`（既存行の変更）
- `frontend/src/locales/ja.json`（既存行の変更）

### バックエンド

| ファイル | 変更内容 |
|---------|---------|
| `backend/app/services/tcg_analysis_review_svc.py:40` | `LEFT JOIN {TCG_SCHEMA}.tcg_series ws ON ws.id = p.work_id` 追加 |
| `backend/app/services/tcg_analysis_review_svc.py:200-201付近` | SELECT に `p.work_id::text AS work_id`, `ws.display_name AS work_name`, `ws.alt_name AS work_alt_name` 追加 |
| `backend/app/services/tcg_analysis_review_svc.py:256-268` | system dict に `"work_id": row.work_id or ""`, `"work_name": row.work_name or ""` 追加 |
| `backend/app/services/tcg_analysis_review_svc.py:49-102` | _build_where に work_id フィルタ条件追加 |
| `backend/app/routers/tcg_analysis_review.py:47-58` | SystemFields に `work_id: str = ""`, `work_name: str = ""` 追加 |
| `backend/app/routers/tcg_analysis_review.py:105-116` | エンドポイントに `work_id: str \| None = None` パラメータ追加 |
| `backend/app/routers/tcg_analysis_review.py:81-87` | AnalysisResultsResponse に `works: list` 追加 |
| `backend/app/routers/tcg_analysis_review.py` | works 一覧取得SQL追加（`tcg_product_import.py:134-142` と同一クエリ） |

### フロントエンド

| ファイル | 変更内容 |
|---------|---------|
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:31` | `<ComparisonMetadataRow label={t("superAdmin.supplierQuality.workName")} value={item.system.work_name \|\| t("common.unresolved")} />` 追加 |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx` | works 一覧を API レスポンスから取得、Tabs 金型（`components/Tabs.tsx`）で作品フィルタ追加、work_id パラメータを API 呼び出しに追加 |
| `frontend/src/locales/en.json` | キー追加: `superAdmin.supplierQuality.workName`, `superAdmin.supplierQuality.allWorks` |
| `frontend/src/locales/ja.json` | キー追加: `superAdmin.supplierQuality.workName` → "作品", `superAdmin.supplierQuality.allWorks` → "すべての作品" |

---

## 変更前後

### バックエンド: _BASE_FROM

**変更前:**
```python
LEFT JOIN public.products p ON p.id = ar.product_id
```

**変更後:**
```python
LEFT JOIN public.products p ON p.id = ar.product_id
LEFT JOIN {TCG_SCHEMA}.tcg_series ws ON ws.id = p.work_id
```

### バックエンド: SELECT（追加分）

```sql
p.work_id::text AS work_id,
ws.display_name AS work_name,
ws.alt_name     AS work_alt_name,
```

### バックエンド: system dict（追加分）

```python
"work_id": row.work_id or "",
"work_name": row.work_name or "",
```

### フロントエンド: ItemComparison（追加分）

```tsx
<ComparisonMetadataRow
  label={t("superAdmin.supplierQuality.workName")}
  value={item.system.work_name || t("common.unresolved")}
/>
```

### フロントエンド: SupplierDetailView（フィルタ追加）

Tabs 金型（`components/Tabs.tsx`）を使用。TcgProductMasterPage.tsx:84 と同一パターン。

---

## 検証基準

| 基準 | 検証方法 | 合格条件 |
|------|---------|---------|
| 作品名表示 | 仕入元詳細で解析結果を表示 | 各行に作品名（日本語alt_nameまたは英語display_name）が表示される |
| 作品フィルタ | Tabs で作品を選択 | 該当作品の解析結果のみ表示される |
| 全件表示 | フィルタ未選択（デフォルト） | 全解析結果が表示される（既存動作と同一） |
| 既存機能無影響 | 仕入元品質一覧→詳細→修正→ConditionReview | 変更前と同じ挙動 |
| i18n | 英語・日本語で画面表示 | 全テキストが翻訳済み |
| テスト | CI の Frontend lint & custom checks | pass |

---

## リスクと対処

| リスク | 発生条件 | 対処 |
|--------|---------|------|
| tcg_series に該当 ID なし | FK制約なしのため理論上可能 | LEFT JOIN で NULL → 空文字表示 |
| パフォーマンス劣化 | tcg_series は11行のみ | 影響なし（小テーブル） |

---

## 外部・過去事例の参照と我々への応用

自プロジェクト内の既存設計のみ参照。
- `TcgProductMasterPage.tsx:84`: Tabs 金型による works フィルタの実装先例
- `tcg_product_import.py:134-142`: works 一覧取得 SQL の先例
- `components/Tabs.tsx`: 金型コンポーネント（variant: underline/pill、size: sm/md）

---

## 守り手（維持の仕組み）

守り手:
- ADR-027 i18n チェックが UI 文字列のハードコードを CI でブロック（関所パス: `frontend/CLAUDE.md`）
- ADR-144 UIガバナンスチェックが金型外コンポーネント使用を CI でブロック（関所パス: `docs/CC_UI_GOVERNANCE.md`）
- `require_super_admin` 認証で解析結果 API を管理者のみに制限（関所パス: `backend/app/routers/tcg_analysis_review.py:116`）
