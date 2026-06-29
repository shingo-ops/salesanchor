# recon: mc-hub-submenu

**対象:** PR — ManagementCenterPage のサブナビを SubMenu 共通部品に置換
**正本commit:** develop 322c95e3（2026-06-28 21:28 時点で確認）
**調査方法:** grep / cat による file:line 実引用。推測なし。

---

## 1. 置換対象の現状（ManagementCenterPage.tsx）

| 事実 | file:line |
|---|---|
| import で NavLink を直接使用 | `frontend/src/pages/management-center/ManagementCenterPage.tsx:14` |
| rawSections 定義（4グループ・権限付き） | `frontend/src/pages/management-center/ManagementCenterPage.tsx:30-78` |
| 権限フィルタ: sections（rawSections → NavSection[]） | `frontend/src/pages/management-center/ManagementCenterPage.tsx:81-83` |
| グループ見出し 4つ（titleKey） | `frontend/src/pages/management-center/ManagementCenterPage.tsx:33,45,56,69` |
| NavLink でメニュー描画（グループあり） | `frontend/src/pages/management-center/ManagementCenterPage.tsx:89-106` |
| 翻訳: t() を titleKey/labelKey に適用して描画 | `frontend/src/pages/management-center/ManagementCenterPage.tsx:92,101` |
| アクティブ判定: hub-subnav-item.active | `frontend/src/pages/management-center/ManagementCenterPage.tsx:97-99` |

## 2. キット（SubMenu）が受け取る形の確認

| 事実 | file:line |
|---|---|
| SubMenuGroup: title?(string) / items | `frontend/src/components/SubMenu.tsx:24-28` |
| grouped 時の title 描画条件 | `frontend/src/components/SubMenu.tsx:47` |
| item.to → NavLink 分岐 | `frontend/src/components/SubMenu.tsx:65` |

## 3. 顧客ハブとの差分（踏襲する点・異なる点）

| 項目 | 顧客ハブ（お手本） | 管理センター（今回） |
|---|---|---|
| グループ数 | 1（title なし） | 4（title あり） |
| groups 構築 | visibleItems.map（フラット） | sections.map（グループ構造維持） |
| activeKey 算出用リスト | visibleItems | sections.flatMap(s => s.items) |
| title 翻訳 | 不要 | t(section.titleKey) が必要 |

## 4. 不明点リスト

- 未解決ゼロ。上記すべて file:line 実引用で確認済み。
