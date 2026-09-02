# PARITY-03 解析レビュー画面 FE — design.md

作成日: 2026-09-02  
ブランチ: release/parity03-analysis-review-fe  
参照: docs/handoff/parity03-analysis-review-fe/recon.md  
対象ADR: ADR-154（GAS→Python マイグレーション方針）

---

## 目的

GAS ベースの解析レビュー画面（analysis-review-ui）を React（salesanchor アプリ）に移植する。  
第1段階: 読み取り専用（一覧・タブ・フィルタ・ページング・ソース原文表示）。  
手動修正フォームは表示のみ（保存ボタン disabled）。BE PR #3225 に依存。

---

## URL / 権限

| 項目 | 値 |
|---|---|
| URL | `/super-admin/tcg-analysis-review` |
| 権限 | `is_super_admin` 限定（App.tsx の SuperAdminRoute でガード） |
| API | GET `/api/v1/tcg/analysis-results` / `/api/v1/tcg/analysis-results/status-counts`（BE PR #3225）|

---

## コンポーネント構成

```
TcgAnalysisReviewPage          (pages/super-admin/)
  └── AnalysisReviewWorkspace  (features/tcg-analysis-review/)
        ├── ReviewListPanel    — 一覧・タブ・フィルタ・ページング
        ├── ItemComparison     — 比較カード・手動修正フォーム（disabled）
        └── SourceRawPane      — ソース原文表示・行ハイライト
```

---

## 受け入れ基準と検証方法

| 基準 | 検証方法 | 守り手: |
|---|---|---|
| `/super-admin/tcg-analysis-review` が 404 にならない | App.tsx の route が追加されていること | コードレビュー |
| is_super_admin 以外がアクセスすると弾かれる | SuperAdminRoute が既存他ページと同様に動作 | コードレビュー |
| 解析結果一覧が表示される（API 結合） | BE PR #3225 マージ後の本番 smoke | 人手（smoke） |
| タブ・フィルタ・ページングが動く | 同上 | 人手（smoke） |
| 手動修正ボタンが disabled | `disabled` 属性確認（コードレビュー） | コードレビュー |
| ADR-027 i18n: UI 文字列が `t("key")` 経由 | ESLint i18n ルール + CI | CI |
| ADR-067 CSS: project token のみ使用 | `check-css-hardcoded-values.js` CI | CI |
| ADR-120 status-direct-writes: badge-${tone} に免除コメント | StatusBadge.tsx コードレビュー | CI |

---

## 外部・過去事例の参照と我々への応用

PARITY-01（TCG平行レポート）で確立した GAS→React 移植パターンを踏襲。  
`google.script.run.*` コールバック → `fetch()` + React state、GAS HTML ガジェット → JSX コンポーネント。  
ADR-154 方針（読み取り専用を先行移植し、書き込みは Phase 2 で追加）に基づく分割。

---

## 弊害・リスク

| リスク | 対策 |
|---|---|
| BE PR #3225 未マージ時は API 404 | PR 本文に「BE 依存」明記。同時マージ推奨 |
| CSS トークン不正によるビジュアル崩れ | CI `check-css-hardcoded-values.js` でブロック |
| i18n キー漏れ | CI i18n-missing-key-guard でブロック |

---

## 維持の仕組み

守り手: .github/workflows/process-artifacts-gate.yml（SOP プロセス継続）、CI の ADR-067 CSS チェック・ADR-027 i18n チェックが恒久的に守る。
