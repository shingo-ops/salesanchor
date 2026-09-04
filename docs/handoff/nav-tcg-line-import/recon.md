# recon — nav-tcg-line-import（サイドメニューへのインポート追加）

**仕事名**: SaaS管理者サイドメニューに「インポート」項目を追加  
**日付**: 2026-09-05  
**対象ADR**: ADR-027, ADR-144  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/DesktopShell.tsx:190` | `saasAdminItems` 配列定義（変更前: 2項目 tcg-supplier-quality / fx-rate） |
| `frontend/src/locales/ja.json:150` | `superAdminTcgSupplierQuality` キー（挿入直前行。新キーはここの上に追加） |
| `frontend/src/locales/en.json:150` | 同上（英語版） |
| `frontend/src/config/routeTitles.ts` | super-admin の tcg-supplier-quality / fx-rate に対応するエントリなし — `check-nav-title-sync.js` は `EXCLUDE_DIRS: super-admin` のため対象外 |
| `frontend/scripts/check-nav-title-sync.js:32` | `EXCLUDE_DIRS` に `super-admin` が含まれる（routeTitles.ts 登録不要の根拠） |

---

## 1. サイドメニュー定義箇所の現在の状態

`frontend/src/components/DesktopShell.tsx:190` の `saasAdminItems`:

```ts
const saasAdminItems: NavItem[] = isSuperAdmin ? [
  { to: "/super-admin/tcg-supplier-quality", labelKey: "nav.superAdminTcgSupplierQuality" },
  { to: "/super-admin/fx-rate",              labelKey: "nav.superAdminFxRate" },
] : [];
```

`/super-admin/tcg-line-import` ルートは **App.tsx に追加済み（#3285）** — 本カードでは触らない。

## 2. routeTitles.ts 登録要否

`frontend/scripts/check-nav-title-sync.js:32` の `EXCLUDE_DIRS` に `super-admin` が含まれる:

```js
const EXCLUDE_DIRS = new Set([
  'super-admin', // 管理者専用サブナビ体系、main sidebar 対象外
  ...
]);
```

→ `check-nav-title-sync` の検査対象外。`routeTitles.ts` 登録は**不要**。

## 3. 翻訳キーの既存状況

`frontend/src/locales/ja.json:148-151` 時点（変更前）:

```json
"superAdminFxRate": "為替レート管理",
"superAdminTcgParallelReport": "並行運用比較レポート",
"superAdminTcgSupplierQuality": "解析精度管理",
"superAdminTcgDistribution": "配信先管理"
```

`nav.superAdminTcgLineImport` キーは存在しない → 追加対象。

## 4. 既存ルートの確認（App.tsx #3285 追加済み）

`frontend/src/App.tsx` に `/super-admin/tcg-line-import` ルートが #3285 で追加済みであることを確認した（本カードで触らない根拠）。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `check-nav-title-sync.js` が `super-admin` ルートに対して `routeTitles.ts` 登録を要求するか | `frontend/scripts/check-nav-title-sync.js:32` の `EXCLUDE_DIRS` を確認 | ✅ 解消済み（不要） |
| 2 | `nav.superAdminTcgLineImport` キーが既存か | `grep -n "superAdminTcgLineImport" frontend/src/locales/*.json` → 0件 | ✅ 解消済み（存在しない） |

**未解決ゼロ確認**: 全て解消済み
