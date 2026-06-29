# recon: crm-hub-submenu

**対象:** PR — CustomerHubPage のサブナビを SubMenu 共通部品に置換
**正本commit:** develop 6f192ff9（2026-06-28 15:17 時点で確認）
**調査方法:** grep / cat による file:line 実引用。推測なし。

---

## 1. 置換対象の現状（CustomerHubPage.tsx）

| 事実 | file:line |
|---|---|
| import で NavLink を直接使用 | `frontend/src/pages/crm/CustomerHubPage.tsx:11` |
| items 定義（3項目: leads / companies / archive） | `frontend/src/pages/crm/CustomerHubPage.tsx:27-44` |
| 権限フィルタ: visibleItems | `frontend/src/pages/crm/CustomerHubPage.tsx:46` |
| NavLink でメニュー描画（グループなし・フラット） | `frontend/src/pages/crm/CustomerHubPage.tsx:52-64` |
| 翻訳: t() を labelKey に適用して描画 | `frontend/src/pages/crm/CustomerHubPage.tsx:61` |
| アクティブ判定: hub-subnav-item.active | `frontend/src/pages/crm/CustomerHubPage.tsx:57-59` |
| グループ見出し: 無（フラット構造） | `frontend/src/pages/crm/CustomerHubPage.tsx:48-73` |

## 2. キット（SubMenu）が受け取る形の確認

| 事実 | file:line |
|---|---|
| SubMenuItem: key / label(string) / to? | `frontend/src/components/SubMenu.tsx:13-22` |
| SubMenuGroup: title?(string) / items | `frontend/src/components/SubMenu.tsx:24-28` |
| SubMenuProps: groups / activeKey / onChange? / className? | `frontend/src/components/SubMenu.tsx:32-38` |
| NavLink 描画分岐（item.to あり） | `frontend/src/components/SubMenu.tsx:65-92` |

## 3. 型の橋渡し確認

| 事実 | file:line |
|---|---|
| 既存 SubNavItem.labelKey は i18n キー（string） | `frontend/src/pages/crm/CustomerHubPage.tsx:19` |
| SubMenuItem.label は翻訳済み文字列（string）— t() 適用が必要 | `frontend/src/components/SubMenu.tsx:14` |
| visibleItems[0].to で初期 activeKey を決定可能 | `frontend/src/pages/crm/CustomerHubPage.tsx:46` |
| useLocation で現在 URL を取得し activeKey を解決 | `frontend/src/pages/crm/CustomerHubPage.tsx:46` |

## 4. CSS クラスの差

| 現在 | キット |
|---|---|
| `.hub-subnav` (container) | → SubMenu の `className="hub-subnav"` prop で維持 |
| `.hub-subnav-item.active` | → `.comp-subnav__item--active` に変わる |
| `.hub-subnav-section` / `.hub-subnav-title` | → 今回はグループなし(title未指定)なので非表示 |

→ 見た目の差は置換後の画面確認で評価（本 recon のスコープ外）

## 5. 不明点リスト

- 未解決ゼロ。上記すべて file:line 実引用で確認済み。
