# recon: submenu-link-mode

**対象:** PR #2650 — SubMenu にリンク型（ドア型）対応を追加
**正本commit:** develop adf7eba（2026-06-28 06:24 時点で確認）
**調査方法:** grep / cat による file:line 実引用。推測なし。

---

## 1. 共通部品 SubMenu の現状（リンク型未対応の確認）

| 事実 | file:line |
|---|---|
| props 定義 interface SubMenuProps の範囲 | `frontend/src/components/SubMenu.tsx:29-35` |
| アイテムを描画する要素が `<button>` である | `frontend/src/components/SubMenu.tsx:64` |
| クリック時に onChange(item.key) を呼ぶ | `frontend/src/components/SubMenu.tsx:74` |
| アイテム1個の描画範囲（map の中身） | `frontend/src/components/SubMenu.tsx:63-86` |
| NavLink / useNavigate / to= / href= の記述が全行に存在しない（＝リンク型未対応） | `frontend/src/components/SubMenu.tsx:1` |
| CSS: アイテムの見た目を決める基本クラス | `frontend/src/components/SubMenu.css:1` |

## 2. アプリ内サイドメニューの全数調査（7個・4系統）

| ファイル(file:line) | 型 | 付属機能(file:line) |
|---|---|---|
| `frontend/src/pages/management-center/ManagementCenterPage.tsx:89` | 遷移（NavLink to=:96） | なし |
| `frontend/src/pages/crm/CustomerHubPage.tsx:52` | 遷移（NavLink to=:56） | なし |
| `frontend/src/pages/orders/OrdersPage.tsx:66` | 切替（onClick setStatusFilter:70,81） | btn-primary:48 |
| `frontend/src/components/DesktopShell.tsx:204` | 遷移（NavLink 多数:223-366） | nav-unread-badge:255 ※スコープ外 |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx:444` | 切替（onChange:557） | color付きinput:516,524,547,555 ※スコープ外 |
| `frontend/src/pages/roles/RolesPage.tsx:324` | 切替（onClick selectRole:345） | 階層indent:341, 色borderLeft:344, btn:328/354, badge:369 |
| `frontend/src/pages/design-preview/DesignPreviewPage.tsx:58` | 切替（onChange:63、SubMenu使用済み） | dp-band-btn:73 |

※ Drawer.tsx / InboxConversationList.tsx / GoalSettingPage.tsx の aside はナビではない表示パネルのため除外。

## 3. SubMenu の本番採用状況

| 事実 | file:line |
|---|---|
| SubMenu の本番機能ページでの使用はゼロ | （grep結果: design-preview のみ） |
| デザイン見本での使用 | `frontend/src/pages/design-preview/sections/SubMenuSection.tsx:55` |

## 4. リンク型の土台（実装方式の確認）

| 事実 | file:line |
|---|---|
| 既存の遷移型は NavLink(react-router-dom)で実装 | `frontend/src/pages/management-center/ManagementCenterPage.tsx:14` |
| react-router-dom バージョン | `frontend/package.json:81` |
| ルーティング検査テストの前例（MemoryRouter） | `frontend/src/components/NavItemList.test.tsx:47` |

## 5. 不明点リスト

- 未解決ゼロ。上記すべて file:line 実引用で確認済み。
