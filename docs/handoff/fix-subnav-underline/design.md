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

## 外部事例

CSS 修正1行のため外部事例は不要。

## 守り手

SubMenu.css は stylelint + ADR-067 darkmode check で CI 監視中。
