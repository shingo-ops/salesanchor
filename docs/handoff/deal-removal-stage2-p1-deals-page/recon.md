# recon — deal-removal stage2-P1 deals page

**仕事名**: deal-removal stage2-P1 deals page  
**日付**: 2026-07-21  
**対象ADR**: ADR-121  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/App.tsx:22-23,222-223,342` | `/deals` の import とルート定義を除去対象として特定 |
| `frontend/src/config/routeTitles.ts:24` | `"/deals"` の route title マッピングを除去対象として特定 |
| `frontend/src/pages/management-center/ManagementCenterPage.tsx:45-49` | 管理センターの `/deals` 導線を除去対象として特定 |

---

## ページ本体の扱い

- frontend/src/pages/deals/DealsPage.tsx、frontend/src/pages/deals/DealEditPage.tsx、frontend/src/pages/deals/DealFormFields.tsx は削除対象。詳細な差分は PR 本体で追う。

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `/deals` 削除で frontend のビルドと型が壊れないか | `npm run build` | ✅ 解消済み |
| 2 | shell 系の既存 Playwright 赤が本 PR の阻害要因か | `mobile-shell.spec.ts` は main 時点で既存・非必須と ruleset 実測で確認 | ✅ 解消済み |
| 3 | backend 変更が必要か | 今回の /deals 廃止は frontend 導線の削除に限定して backend 無変更で成立 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
