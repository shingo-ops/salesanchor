# Phase 3 設計 — mobile-nav-css

**対象ADR**: ADR-087  
**recon**: docs/handoff/mobile-nav-css/recon.md  
**日付**: 2026-06-17  
**担当**: Hikky-dev（Claude Code）

---

## 外部・過去事例の参照と我々への応用

- 事例1: BEM 規約によるモバイルナビ CSS — nav__item に text-decoration:none と display:flex を付与するのは一般的慣習（MDN Web Docs のリンクリセット推奨に準拠） → 我々への応用: a タグのデフォルトスタイルを BEM ルート nav-item-list__item でリセットし、上位コンポーネントへの依存をゼロにする
- 事例2: WCAG 2.5.5 タッチターゲットサイズ（44×44 CSS px 以上）→ 我々への応用: nav-item-list__item に min-height: var(--size-icon-btn-lg) を設定し、モバイル実機のタップ精度を保証

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| nav-item-list__item に text-decoration:none が適用される | `frontend/tests-e2e/mobile-shell.spec.ts:179`（E2E assert） |
| nav-item-list__item が display:flex で横並びになる | `frontend/tests-e2e/mobile-shell.spec.ts:191`（E2E assert） |
| タップターゲット高さ 44px 以上（WCAG 2.5.5） | `frontend/tests-e2e/mobile-shell.spec.ts:201`（E2E assert） |
| すべての nav-item 項目が viewport 幅内に収まる（横スクロールなし） | `frontend/tests-e2e/mobile-shell.spec.ts:217`（E2E assert） |
| ADR-067 デザイントークン準拠（ハードコードカラーなし） | `frontend/src/mobile-shell.css:189`（lint チェック） |

---

## 技術 How・KPI

- KPI: スマホ実機（375×812）で nav-item-list__item の青リンク・下線が消え、flex 横並びになること（E2E 4件 PASS）
- 技術選択: BEM クラス名を維持したまま mobile-shell.css に nav-item-list__* ルールを追加（NavItemList.tsx の変更なし）。CSS のみの修正で最小変更リスク。

---

## 弊害・トレードオフ

- nav-item-list__* CSS が今後 NavItemList.tsx の BEM クラスと乖離するリスク → 対策: E2E テストがクラス名ベースで乖離を即時検知する仕組みをこの PR で追加済み

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | mobile-shell.css に nav-item-list__* スタイル追加 | Generator |
| 2 | mobile-shell.spec.ts に CSS 検証 assert 4件追加 | Generator |
| 3 | check:all + build + Playwright 26件 PASS 確認 | Generator |

---

## 継続

- 完了後の監視: E2E mobile-shell.spec.ts が毎 PR で自動実行されるため監視不要
- 次フェーズへの引き継ぎ: 該当なし（CSS bugfix 完結）
