# design: mc-hub-submenu

**対象:** PR — ManagementCenterPage のサブナビを SubMenu 共通部品に置換
**対象ADR:** ADR-148
**recon:** docs/handoff/mc-hub-submenu/recon.md

---

## 外部・過去事例の参照と我々への応用

- ADR-148 段階移行 Step 3。Step 2（CustomerHubPage / PR #2662）で確立した `groups + activeKey + useLocation` パターンを、グループ付き（4グループ）に拡張する。
- `sections.flatMap` で全項目を平坦化して activeKey を算出する点が顧客ハブとの唯一の差異。同リポジトリ内の確立済みパターンの範囲内。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| ManagementCenterPage のサブナビが SubMenu に置換されている | `git diff --name-only origin/develop...HEAD` が `ManagementCenterPage.tsx` 1件のみ |
| 4グループが描画される（チーム・データ・API連携・ビジネス） | ブラウザで `/management-center/staff` を開き 4グループが表示されることを目視確認 |
| クリックで対応ページに遷移する | 各項目をクリックして URL と右コンテンツが切り替わることを確認 |
| グループ見出しが翻訳されて表示される | 日英切り替えで見出しが変わることを確認 |
| 型チェック通過 | `tsc --noEmit` EXIT=0 |
| lint 通過 | `eslint src/pages/management-center/ManagementCenterPage.tsx --max-warnings=0` EXIT=0 |

---

## 技術 How・KPI

- `sections.map` で `SubMenuGroup[]` に変換: `title: t(section.titleKey)`、`label: t(item.labelKey)` で翻訳済み文字列を渡す
- `sections.flatMap(s => s.items)` で全項目を平坦化し `useLocation` + `pathname.endsWith` で activeKey を解決
- `variant="grouped"` / `className="hub-subnav"` で既存レイアウトを維持

---

## 弊害・トレードオフ

- アクティブクラスが `.hub-subnav-item.active` → `.comp-subnav__item--active` に変わる（顧客ハブと同様）。画面確認で評価し、必要なら後続 PR で CSS 調整。
- `integrations/google-drive` 等のネストパスは `pathname.endsWith("/integrations/google-drive")` で正しく判定される。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | ManagementCenterPage.tsx の import・groups・activeKey・SubMenu 呼び出しに変更 | Generator |
| 2 | tsc / eslint で型・lint 確認 | Generator |
| 3 | PR 作成 → CI 通過確認 | Generator |
| 4 | 画面確認（4グループ・アクティブスタイルの差を目視評価） | PO |

---

## 継続

顧客ハブ・管理センターの置換完了後、アクティブスタイルの差異（`hub-subnav-item.active` vs `comp-subnav__item--active`）を画面確認の結果に応じて CSS 調整する。
