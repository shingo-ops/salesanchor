# Design: SubMenu NavLink アンダーライン除去

## 目的

SubMenu コンポーネントの NavLink 項目からブラウザデフォルトのアンダーラインを除去する。

## recon 相互参照

- [recon.md](./recon.md) — 原因調査・影響範囲・ADR検索結果

## 対象と対象外

- **対象**: `frontend/src/components/SubMenu.css` の `.comp-subnav__item`
- **対象外**: 他のCSS・コンポーネント・JS/TS ファイル

## 変更内容

`SubMenu.css:84` の `color: var(--text-primary);` の直後に `text-decoration: none;` を追加。

### 変更前

```css
color: var(--text-primary);
background: none;
```

### 変更後

```css
color: var(--text-primary);
text-decoration: none;
background: none;
```

## 受入条件

| 基準 | 検証方法 |
|------|----------|
| 管理センターのサブメニューに下線がない | 目視確認 |
| CustomerHub のサブメニューに下線がない | 目視確認 |
| CI 全チェック通過 | GitHub Actions |
| stylelint エラーなし | `npx stylelint SubMenu.css` |

## 代替案と選択理由

| 案 | 内容 | 採否 |
|----|------|------|
| A. `.comp-subnav__item` に追加 | 金型クラスで一括制御 | **採用** — hub-shell.css:53 と同パターン |
| B. `index.css` で `a { text-decoration: none }` | グローバルリセット | 不採用 — 他の `<a>` タグへの影響が広すぎる |
| C. NavLink に inline style | 各使用箇所で個別指定 | 不採用 — DRY 違反・デザインシステム違反 |

## 外部・過去事例の参照と我々への応用

本リポジトリ内の既存パターンが直接の根拠であり、外部事例は不要。

- `frontend/src/hub-shell.css:53` — `.hub-subnav-item` に `text-decoration: none` を宣言（AnalysisRulesSidebar 用）
- `frontend/src/sidebar.css:138` — `.sidebar-item` に `text-decoration: none` を宣言
- `frontend/src/mobile-shell.css:144` — モバイルナビにも同様の宣言あり

いずれもナビゲーション用 `<a>` タグの下線除去として同一手法を採用。SubMenu も同じパターンに統一する。

## 維持の仕組み

- SubMenu.css は stylelint で CI 監視中（プロパティ順序・詳細度違反を自動検出）
- ADR-067 darkmode check で色トークンの `:root` / `force-dark` 両方宣言を検証
- `text-decoration: none` は非色プロパティのため darkmode check の対象外（追加作業不要）
