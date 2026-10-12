# Recon: SubMenu NavLink アンダーライン除去

## 現象

管理センター（ManagementCenterPage）のサブメニュー項目にアンダーライン（下線）が表示される。

## 原因

- `frontend/src/components/SubMenu.tsx:65-91` — `item.to` がある場合 `<NavLink>` を使用
- `<NavLink>` は HTML `<a>` タグとしてレンダリングされる
- ブラウザデフォルト: `a { text-decoration: underline; }`
- `frontend/src/components/SubMenu.css:75-91` — `.comp-subnav__item` に `text-decoration: none` が**ない**
- `frontend/src/index.css:419-423` — グローバルリセットに `text-decoration` リセットは**ない**

## 比較: 他のサイドバー

| コンポーネント | 要素 | text-decoration: none | 下線 |
|---|---|---|---|
| AnalysisRulesSidebar (`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:37`) | `<button>` | hub-shell.css:53 で宣言 | なし |
| SubMenu (NavLink mode) | `<a>` (NavLink) | **なし** | **あり** ← 問題 |
| sidebar.css:138 `.sidebar-item` | `<a>` | 宣言あり | なし |

## 影響範囲

SubMenu を `item.to` 付きで使用しているページ:

1. `frontend/src/pages/management-center/ManagementCenterPage.tsx:92-96`
2. `frontend/src/pages/crm/CustomerHubPage.tsx:53-57`

## ADR検索

- `git grep -i 'text-decoration' docs/adr/` — 該当 ADR なし
- ADR-067（デザイントークン）: `text-decoration` はトークン対象外（色・サイズ系のみ）
- ADR-144（UIガバナンス）: コンポーネント金型の修正であり新設ではない
