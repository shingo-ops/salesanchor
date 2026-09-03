# DEPLOY LOG — SalesAnchor FE/BE

CC_TASK_AUTO-01 自律実装の記録。各デプロイの根拠・検証・戻し方を記録する。

---

## PARITY-03 Phase 3 — tcg_products mark/english_title 追加 (2026-09-03)

### PR #3246: migration 20260903_180000_tcg_products_mark_en_t004.sql

**マージ前バックアップ必須（PO実施）:**
```sql
CREATE TABLE tenant_004.tcg_products_bak_20260903
AS SELECT * FROM tenant_004.tcg_products;

-- 件数確認（268件以上あること）
SELECT COUNT(*) FROM tenant_004.tcg_products_bak_20260903;
```

**復元 SQL（rollback 時）:**
```sql
-- 1. 列を削除
ALTER TABLE tenant_004.tcg_products DROP COLUMN IF EXISTS mark;
ALTER TABLE tenant_004.tcg_products DROP COLUMN IF EXISTS english_title;

-- 2. または backup から全件 COPY 復元:
-- TRUNCATE tenant_004.tcg_products CASCADE;
-- INSERT INTO tenant_004.tcg_products SELECT * FROM tenant_004.tcg_products_bak_20260903;
```

**充填率（2026-09-03 シート直読み）:**
- mark: 239/268 filled, NULL 29件 (89.2%)
- english_title: 251/268 filled, NULL 17件 (93.7%)

**GO記録:** GO発行者: Shingo / 日時: 2026-09-03 / GO原文: "GO を3本発行しました"

---

## Phase 0 — GAS レイアウト根拠の確立 (2026-09-03)

参照元: `sqr07_work/analysis-review-ui/src/` (最終更新 2026-08-30、sqr06より新)

### 0-1: SupplierQualityPage.tsx (一覧)

`sqr07_work/analysis-review-ui/src/SupplierQualityPage.tsx:29-56`

```tsx
<main>
  <DataList columns={SUPPLIER_QUALITY_COLUMNS} rows={summaries} ... />
</main>
```

特別なグリッドなし。DataList コンポーネントが一覧表示を担う。

### 0-2: SupplierDetailPage.tsx (詳細) の JSX 構造

`sqr07_work/analysis-review-ui/src/SupplierDetailPage.tsx:46-74`

```tsx
<main className="supplier-detail">
  <div className="supplier-detail-header"> ... </div>
  <div className="supplier-detail-body">
    <SourceRawPane ... />
    <section className="supplier-detail-items">
      {items.map((item) => (
        <div className="item-with-action">
          <ItemComparison item={item} readOnly={true} onJumpToSourceLine={jumpToLine} />
          <div className="item-actions">
            <button>修正する →</button>
          </div>
        </div>
      ))}
    </section>
  </div>
</main>
```

**重要**: `readOnly={true}` — Manual修正カラムは JSX 自体が非表示。

### 0-3: CSS grid-template-columns の実値 → カラム数断定

**ページボディ** `sqr07_work/analysis-review-ui/src/supplier-detail.css:1`:
```
.supplier-detail-body { grid-template-columns: clamp(320px,28vw,480px) minmax(0,1fr) }
```
→ **2カラム: [source-raw pane | items section]**

**ItemComparison 通常モード** `sqr07_work/analysis-review-ui/src/style.css:1`:
```
.item-head-grid, .aligned-fields, .item-extra-grid {
  grid-template-columns: minmax(300px,1fr) minmax(320px,1.05fr) minmax(330px,1.1fr)
}
```
→ 3カラム（Gemini | System | Manual）。**ただし詳細ページには適用されない**。

**ItemComparison readOnly モード** `sqr07_work/analysis-review-ui/src/item-comparison-readonly.css:1`:
```
.item-comparison--readonly .item-head-grid, .aligned-fields, .item-extra-grid {
  grid-template-columns: minmax(300px,1fr) minmax(320px,1.05fr)
}
```
→ **2カラム: Gemini | System のみ**

**5カラム定義** `style.css:1` `.sheet-header`:
```
grid-template-columns: 110px 360px minmax(300px,1fr) minmax(320px,1.05fr) minmax(330px,1.1fr)
```
→ 旧 TcgAnalysisReviewPage（`.comparison-sheet` コンテキスト）のシートヘッダー。**仕入元詳細と無関係**。

**断定: 仕入元詳細では `readOnly={true}` → ItemComparison は2カラム（Gemini | System）が正しい。**

### 0-4: 背景・カード・余白・sticky

`sqr07_work/analysis-review-ui/src/supplier-detail.css:1` より:

| 要素 | GAS 仕様 |
|------|---------|
| `.supplier-detail` | `padding: var(--space-5)` (24px) |
| `.source-raw` | `position: sticky; top: var(--space-3); height: calc(100vh - 140px); min-height: 420px; background: var(--color-surface); border-right: 1px solid var(--color-border)` |
| `.item-with-action` | `border-bottom: 1px solid var(--color-border)` (**カード背景なし**) |
| `.item-actions` | `display: flex; justify-content: flex-end; padding: var(--space-2) var(--space-3) var(--space-3)` |

GAS にはアイテムごとの `background: var(--color-surface)` はない。ユーザー要求（「各パネルをカードに入れ、背景を白」）はGASにない追加仕様。

### 0-5: analysis-review.css の定義が詳細画面に必要か

GAS では `style.css` がスコープなしで `.item-head-grid`・`.comparison-field` 等を定義。
FE の `analysis-review.css` は `.tcg-analysis-review` スコープのため、仕入元詳細（`.tcg-analysis-review` なし）では**適用されない**。

→ `display: grid`・`comparison-field` スタイルを詳細専用に追加が必要。PR #3235 で対応済み。

### 0-6: PR #3235 との差分照合

| 差分 | GAS 仕様 | PR #3235 実装 | 判定 |
|------|---------|--------------|------|
| ページ grid-template-columns | `clamp(320px,28vw,480px) minmax(0,1fr)` | 同値 | ✅ |
| source-raw sticky | あり | あり | ✅ |
| source-raw background | `var(--color-surface)` | `var(--bg-surface)` (ADR-067) | ✅ |
| ItemComparison カラム数 | 2カラム (readOnly) | 2カラム | ✅ |
| display:grid on item grids | スコープなし (style.css) | item-comparison-readonly.css に追加 | ✅ |
| アイテム背景 | なし (border-bottomのみ) | `var(--bg-surface)` + border | ⚠️ GAS外・ユーザー追加要求 |
| ページネーション | なし (limit:500全件) | 初期20件 + さらに読み込む | ✅ タスクC |
| overflow:hidden | なし | 削除済み | ✅ |

**結論: PR #3235 のカラム数（2カラム）はGAS準拠で正しい。**

---

## AUTO-01-01: 仕入元詳細 UI修正 + ページネーション (2026-09-03)

- PR: #3235
- ブランチ: release/parity03-supplier-quality-ui
- 変更ファイル:
  - frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx
  - frontend/src/features/tcg-analysis-review/supplier-detail-view.css
  - frontend/src/features/tcg-analysis-review/item-comparison-readonly.css
  - frontend/src/locales/ja.json
  - frontend/src/locales/en.json
- GAS の根拠:
  - sqr07_work/analysis-review-ui/src/supplier-detail.css:1 (ページグリッド・sticky・背景)
  - sqr07_work/analysis-review-ui/src/SupplierDetailPage.tsx:62 (readOnly=true)
  - sqr07_work/analysis-review-ui/src/item-comparison-readonly.css:1 (2カラム override)
  - sqr07_work/analysis-review-ui/src/style.css:1 (comparison-field・item-comparison 基本スタイル)

### 変更前

- ページ grid: `1fr 2fr`（GAS 仕様と不一致）
- source-raw: sticky/background なし（`.comparison-sheet .source-raw` スコープ外）
- ItemComparison: display:grid 未適用（`.tcg-analysis-review` スコープ外）→ フィールドが縦積み
- ページネーション: なし（全500件一括描画）

### 変更後

- ページ grid: `clamp(320px,28vw,480px) minmax(0,1fr)` (GAS準拠)
- source-raw: sticky + `var(--bg-surface)` 白背景
- ItemComparison: display:grid 適用 → 2カラム表示
- ページネーション: 初期20件 + さらに読み込む

- マージコミット: `17192936e090404c23ac8bba054a46d958bfbf31`

### 検証結果

| 確認項目 | 結果 | 生出力 |
|---------|------|-------|
| デプロイ全ステップ | ✅ success | run 33682346379: `{"status":"completed","conclusion":"success"}` |
| `GET /api/health` | ✅ ok | `{"status":"ok","database":"connected","redis":"connected","celery":"connected"}` |
| `https://app.salesanchor.jp/` | ✅ 200 | HTTP 200 |
| 他の画面（/leads） | ✅ 200 | HTTP 200 |
| 仕入元サマリー API | ⚠️ 401 | 認証なし → 401（エンドポイント存在確認のみ。件数確認はJWT必須のため測定不能） |

### 戻し方

git revert 17192936e090404c23ac8bba054a46d958bfbf31
→ PR を作成 → CI green → マージ でデプロイ前の状態に戻る

---

## AUTO-02-BE: PARITY-03 Phase 3 BE — 商品マスタ登録・再解析 API (2026-09-03)

- PR: #3239 (Draft)
- ブランチ: release/parity03-product-master-drawer-be
- コミット: 44185e42
- 変更ファイル:
  - backend/app/services/tcg_product_master_svc.py (新規)
  - backend/app/routers/tcg_product_master.py (新規)
  - backend/app/main.py (ルーター登録)
  - backend/tests/test_tcg_product_master.py (新規, 16 tests PASS)

### R-1 再解析 recon 結果

| 調査項目 | 結果 |
|---------|------|
| analyze_extraction_job の存在 | tcg_analyzer_svc.py:851 に存在（sync Session） |
| HTTP エンドポイントの有無 | なし（backend/app/routers/ 全件 grep で確認） |
| GAS 相当機能 | ShadowReviewV2.gs:87 refreshShadowReviewV2（全件対象） |
| 本実装の対象 | 1ジョブ限定 / UPSERT |

### R-1 安全装置の確認

| 確認項目 | 結果 |
|---------|------|
| 行単位の事前保存 | ❌ なし（集計値 before のみ）。行単位復元はベースラインテーブルで対応 |
| 一括実行（45ジョブ）防止 | ✅ URL パスに extraction_job_id 必須。一括実行不可 |

### GAS ベースラインスナップショット（実行済み・2026-09-03）

```sql
-- 実行済み（本番 DB: jarvis_db）
CREATE TABLE tenant_004.analysis_results_gas_baseline_20260903
AS SELECT * FROM tenant_004.analysis_results;
-- → SELECT 1626（件数確認済み）
```

**復元用テーブル**: `tenant_004.analysis_results_gas_baseline_20260903`（1626行・変更不可・削除禁止）

**復元 SQL**（対象ジョブを GAS 時点に戻す場合）:

```sql
INSERT INTO tenant_004.analysis_results
  SELECT * FROM tenant_004.analysis_results_gas_baseline_20260903
  WHERE extraction_item_id IN (
    SELECT id FROM tenant_004.extraction_items
    WHERE extraction_job_id = '<対象ジョブID>'
  )
ON CONFLICT (extraction_item_id) DO UPDATE
  SET pid_resolved   = EXCLUDED.pid_resolved,
      unit_resolved  = EXCLUDED.unit_resolved,
      needs_review   = EXCLUDED.needs_review,
      product_id     = EXCLUDED.product_id,
      pid_basis      = EXCLUDED.pid_basis,
      unit           = EXCLUDED.unit,
      condition      = EXCLUDED.condition,
      status         = EXCLUDED.status,
      note           = EXCLUDED.note,
      exclusion      = EXCLUDED.exclusion;
```

### ロールバック手順（訂正済み）

- 再解析（R-1）は Python エンジンで上書きする
- **GAS が計算した値には戻らない**（「再度呼べば復元可能」という記述は誤り・docstring 修正済み）
- 復元は上記 SQL でベースラインテーブルから差し戻す

