# recon: hotfix-css-mediaq-safari

## 問題

本番（app.salesanchor.jp）で iPhone Safari / mobile 375px の responsive ルールが完全に無視された。

- .sidebar-panel が transform: translate(-100%) で隠れない → collapsed sidebar 常時表示
- .mobile-menu-btn が display: flex にならない → hamburger button 非表示
- .app-body の margin-left: 0 が効かない → sidebar 分の余白が残る

## 原因

Vite 8 は CSS minification のデフォルト target として "baseline-widely-available" を使用する。
この target に Safari 16.4+ が含まれるため、lightningcss が CSS Level 4 メディアクエリ range 構文に変換する。

| 変換前（ソース） | 変換後（本番 dist） |
|---|---|
| @media (max-width: 767px) | @media (width<=767px) |
| @media (min-width: 768px) | @media (width>=768px) |

Safari 16.4 未満（iOS 16.3 以前）は Level 4 range 構文に非対応のため、@media ブロック全体が無視される。

## 調査ファイル

| ファイル | 内容 |
|---|---|
| `frontend/vite.config.ts` | build.cssTarget 未設定 → Vite 8 デフォルト target 使用 |

## ADR 検索結果

- git grep -i "vite cssTarget lightningcss browserslist" docs/adr/ → 0件
- git grep -i "responsive" docs/adr/ → 0件
- git grep -i "safari browser" docs/adr/ → ADR-067 のみ（デザイントークン）

## 影響範囲

本番 CSS 全体で 27 箇所の @media (width<=...) / @media (width>=...) が非対応 Safari で無視される。
PR-R1 (#2156) の responsive ルールのみでなく、inbox、hub-shell、comp-btn 等の既存 responsive ルールも含む。
