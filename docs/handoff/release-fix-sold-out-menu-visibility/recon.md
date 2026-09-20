# recon — fix-sold-out-menu-visibility

## 調査日
2026-09-20

## 根本原因（事実）

### DesktopShell.tsx:191 — リンク先の不一致
`frontend/src/components/DesktopShell.tsx:191`

```ts
// 修正前（誤）
{ to: "/super-admin/tcg-line-import",  labelKey: "nav.superAdminAnalysisRules" },
// 修正後（正）
{ to: "/super-admin/analysis-rules",   labelKey: "nav.superAdminAnalysisRules" },
```

ラベルは「解析管理」（`nav.superAdminAnalysisRules`）なのに、リンク先がインポートページ（`/super-admin/tcg-line-import`）になっていた。

### MobileShell.tsx — isSuperAdmin メニュー定義なし
`frontend/src/components/MobileShell.tsx`

`useSuperAdmin` hook の呼び出しなし・`/super-admin/analysis-rules` のエントリなし（全行確認済み）。

### routeTitles.ts — /super-admin/analysis-rules 未登録
`frontend/src/config/routeTitles.ts`

`/super-admin/tcg-sold-out` は登録済みだが `/super-admin/analysis-rules` は未登録。
ページタイトルが空になる原因。

## 関連ファイル（フルパス:行番号）

| ファイル | 行 | 内容 |
|--------|-----|------|
| `frontend/src/components/DesktopShell.tsx:191` | 191 | 誤リンク先（修正対象） |
| `frontend/src/components/MobileShell.tsx` | — | isSuperAdmin メニュー未定義（追加対象） |
| `frontend/src/config/routeTitles.ts:14` | 14 | `/super-admin/analysis-rules` 未登録（追加対象） |
| `frontend/src/hooks/useSuperAdmin.ts` | — | `isSuperAdmin` を返す hook（既存・変更なし） |
| `frontend/src/constants/icons.tsx:263` | 263 | `NAV_ICONS.saasAdmin = CommandLine`（既存・流用） |
| `frontend/src/locales/ja.json` | — | `nav.superAdminAnalysisRules: "解析管理"` 登録済み |
| `frontend/src/locales/en.json` | — | `nav.superAdminAnalysisRules: "Analysis Management"` 登録済み |
| `frontend/src/App.tsx` | — | `path="/super-admin/analysis-rules"` ルート定義済み |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` | — | 完売ルール管理ページ実装済み |
