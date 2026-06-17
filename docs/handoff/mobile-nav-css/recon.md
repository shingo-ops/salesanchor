# recon — mobile-nav-css

**仕事名**: mobile-nav-css  
**日付**: 2026-06-17  
**対象ADR**: ADR-087  
**担当**: Hikky-dev（Claude Code）

---

## file:line 引用表

| 引用先 | 確認内容 |
|--------|---------|
| `frontend/src/mobile-shell.css:155` | .nav-item-list ルートが存在し、flex column レイアウト定義済み |
| `frontend/src/mobile-shell.css:163` | .nav-item-list__item が display:flex + text-decoration:none で定義済み |
| `frontend/src/mobile-shell.css:170` | text-decoration:none でブラウザデフォルト青リンク下線を抑制 |
| `frontend/src/mobile-shell.css:189` | .nav-item-list__item--active が active 状態トークン参照で定義済み |
| `frontend/src/mobile-shell.css:198` | .nav-item-list__icon アイコンラップが定義済み |
| `frontend/src/mobile-shell.css:206` | .nav-item-list__label ラベルが定義済み |
| `frontend/src/mobile-shell.css:213` | .nav-item-list__badge 未読バッジが定義済み |
| `frontend/src/mobile-shell.css:230` | .nav-item-list__group グループ親コンテナが定義済み |
| `frontend/src/mobile-shell.css:248` | .nav-item-list__children 子項目コンテナが定義済み |
| `frontend/src/mobile-shell.css:256` | .nav-item-list__child 子項目 NavLink が定義済み |
| `frontend/tests-e2e/mobile-shell.spec.ts:162` | CSS 検証テストブロック先頭（fix/morimoto/mobile-nav-css 追加分） |
| `frontend/tests-e2e/mobile-shell.spec.ts:179` | text-decorationLine が "none" であることを assert |
| `frontend/tests-e2e/mobile-shell.spec.ts:191` | display が "flex" であることを assert |
| `frontend/tests-e2e/mobile-shell.spec.ts:201` | タップターゲット高さ 44px 以上を assert（WCAG 2.5.5） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | nav-item-list__* クラスに対応する CSS が存在するか | `frontend/src/mobile-shell.css:155` で確認 | ✅ 解消済み |
| 2 | デザイントークン参照のみで ADR-067 に準拠しているか | `frontend/src/mobile-shell.css:189` の sidebar-item トークン使用を確認 | ✅ 解消済み |
| 3 | E2E テストでタップターゲット高さの検証が実施されているか | `frontend/tests-e2e/mobile-shell.spec.ts:201` で確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

NavItemList.tsx が出力する BEM クラス群（nav-item-list__*）に対応する CSS が
mobile-shell.css に存在しなかったことが根本原因。

ブラウザが a タグのデフォルトスタイル（青リンク・下線・block 表示）を適用し、
スマホ実機でメニュー項目が崩れる現象が発生していた。

本修正ですべてのカラー・余白・z-index をデザイントークン参照のみとした（ADR-067 準拠）。
