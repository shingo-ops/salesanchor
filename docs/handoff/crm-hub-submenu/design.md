# design: crm-hub-submenu

**対象:** PR — CustomerHubPage のサブナビを SubMenu 共通部品に置換
**対象ADR:** ADR-148
**recon:** docs/handoff/crm-hub-submenu/recon.md

---

## 外部・過去事例の参照と我々への応用

- 同リポジトリ内 ADR-148（`docs/adr/ADR-148-submenu-ssot-link-mode.md`）が定める段階移行の Step 2 に該当。1本目（PR #2650）で SubMenu にリンク型を追加済み。本 PR はそれを初めて本番ページに適用する。
- react-router-dom v7 の `useLocation` による現在パス取得は、同リポジトリの NavItemList.tsx 等で確立されたパターンに沿う。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| CustomerHubPage のサブナビが SubMenu に置換されている | `git diff --name-only origin/develop...HEAD` が `CustomerHubPage.tsx` 1件のみ |
| リード・会社・アーカイブの3項目が描画される | ブラウザで `/crm/leads` を開き 3項目が表示されることを目視確認 |
| クリックで対応ページに遷移する | 各項目をクリックして URL と右コンテンツが切り替わることを確認 |
| アクティブ項目に `comp-subnav__item--active` クラスが付く | DevTools で確認（`hub-subnav-item.active` から変わる） |
| 型チェック通過 | `tsc --noEmit` EXIT=0 |
| lint 通過 | `eslint src/pages/crm/CustomerHubPage.tsx --max-warnings=0` EXIT=0 |

---

## 技術 How・KPI

- `visibleItems` を `SubMenuGroup[]` に変換: `label: t(i.labelKey)` で翻訳済み文字列を渡す（SubMenu は labelKey ではなく string を受け取るため）
- `useLocation` で現在パスを取得し `location.pathname.endsWith(/${i.to})` で activeKey を解決
- `variant="grouped"` / `className="hub-subnav"` により既存の `.hub-shell` レイアウトを維持
- グループ見出しは今回なし（`title` 未指定）— 顧客ハブは元々フラット構造

---

## 弊害・トレードオフ

- アクティブクラスが `.hub-subnav-item.active` → `.comp-subnav__item--active` に変わる。`hub-shell.css` は `.hub-subnav-item.active` を参照しているため、アクティブスタイルが変わる可能性がある。置換後の画面確認で評価し、必要なら後続 PR で CSS 調整。
- NavLink のアクティブ判定（isActive）とuseLocation による activeKey の両方が効く。NavLink 側が主で activeKey は SubMenu の button 分岐用（今回は全項目 to あり = NavLink 分岐のみ = 実質 activeKey は無効化）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | CustomerHubPage.tsx の import・groups・activeKey・SubMenu 呼び出しに変更 | Generator |
| 2 | tsc / eslint で型・lint 確認 | Generator |
| 3 | PR 作成 → CI 通過確認 | Generator |
| 4 | 画面確認（アクティブスタイルの差を目視評価） | PO |

---

## 継続

管理センター（ManagementCenterPage.tsx）は次の 3本目 PR で同様に置換する（グループあり・4グループ構造）。アクティブスタイルの差異は管理センター置換後に一括で CSS 調整を判断する。
