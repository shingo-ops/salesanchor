# PARITY-03 解析レビュー画面 FE — recon.md

作成日: 2026-09-02  
ブランチ: release/parity03-analysis-review-fe

---

## 既存 ADR 検索結果

`git grep -i "parity" docs/adr/` → ADR-154-tcg-parity02-gas-python-migration  
PARITY-03 固有 ADR は未起案。ADR-154 方針（GAS→Python 段階移植）の延長として実施。  
ADR-027 (i18n 強制): `t("key")` 経由。ADR-067 (CSS デザイントークン): component-scoped vars。

---

## GAS ソース対応表

| GAS 実装 | FE 移植先 |
|---|---|
| `google.script.run.getAnalysisReviewPage(params)` | `api.get('/api/v1/tcg/analysis-results?...')` |
| `google.script.run.previewAnalysisReviewStatusTabs(params)` | `api.get('/api/v1/tcg/analysis-results/status-counts?...')` |
| `google.script.run.saveAnalysisReviewNote(...)` | disabled ボタン（Phase 2）|
| `google.script.run.saveAnalysisReviewCorrections(...)` | disabled ボタン（Phase 2）|

---

## 変更ファイル一覧（file:line）

| ファイル | 変更種別 | 主要行 |
|---|---|---|
| `frontend/src/App.tsx` | 修正 | L89 (import 追加), L310-311 (route 追加) |
| `frontend/src/pages/super-admin/TcgAnalysisReviewPage.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/AnalysisReviewWorkspace.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/ReviewListPanel.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/ItemComparison.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/SourceRawPane.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/analysis-review.css` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/source-raw-pane.css` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/components/DataList.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/components/StatusBadge.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/components/StatusTabBar.tsx` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/components/data-list.css` | 新規作成 | 全行 |
| `frontend/src/features/tcg-analysis-review/components/status-tab-bar.css` | 新規作成 | 全行 |
| `frontend/src/locales/ja.json` | 修正 | `superAdminTcgAnalysisReview` キー追加 |
| `frontend/src/locales/en.json` | 修正 | 同上 |

### App.tsx route 追加

```
L310-311:
  path="/super-admin/tcg-analysis-review"
  element={<TcgAnalysisReviewPage />}
```

---

## 触らない範囲

- `frontend/src/pages/super-admin/` 配下の既存ページ（新規ファイル追加のみ、既存ファイル不変）
- `backend/` 一切（BE は PR #3225 で対応済み）
- `frontend/src/features/` 配下の他フィーチャ（変更なし）

---

## 既存 ADR との整合

- ADR-027: 全 UI 文字列 `t("key")` 経由。`ja.json`/`en.json` に `superAdminTcgAnalysisReview` 追加
- ADR-067: CSS は component-scoped vars + project token (`--border`, `--bg-surface`, `--accent` 等)
- ADR-120: `StatusBadge.tsx` の `badge-${tone}` は `// status-ssot-exempt: review issue tone` 免除
- ADR-154: GAS 解析レビュー UI → React 段階移植（第1段階: 読み取り専用）
