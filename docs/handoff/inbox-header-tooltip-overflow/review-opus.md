# 設計審査: 受信箱のページが縦にはみ出す件（Architect）

> この文書は何か: design.md が実装役に渡せる出来かを審査した記録。

- 審査日: 2026-11-23
- 審査者: Claude Opus（設計担当が Architect を兼ねた自己審査。独立した第二者の審査ではない。独立の確認はマージ前の審査役 reviewer が行う）
- 対象: [design.md](./design.md)・[recon.md](./recon.md)・[impl-card.md](./impl-card.md)

## 判定: APPROVE（設計合格）

設計合格は、PO の実装承認・実装開始・マージ・本番反映の承認を兼ねない。

## 確かめたこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| 原因が実物で確かめられているか | ○ | 本番で吹き出しを消すとはみ出し 0（1426→1392）。3つのボタンの `::after` の top が 1400px（docs/handoff/inbox-header-tooltip-overflow/recon.md §3） |
| 直し方が実物で効くか | ○ | 本番の画面に手元だけで指定を差し込み、はみ出し 0・吹き出し top 42px・横のはみ出しなし・マウスを乗せた吹き出しが見える（docs/handoff/inbox-header-tooltip-overflow/recon.md §3-1） |
| 既存の決めごととの整合 | ○ | `frontend/src/components.css:437-441` のコメント「要素は position が必要」に沿う。共通の箱（`components.css:501`。ADR-144 の共通 CSS）1か所に書く＝SSOT。ADR-067: 数字を足さない |
| 影響の範囲 | ○ | `.page-header-actions` の使い手6画面のうち `data-tooltip` を渡すのは受信箱だけ（docs/handoff/inbox-header-tooltip-overflow/recon.md §2-3 の `git grep`） |
| 見張り（同じ失敗を二度と通さない） | ○ | 新しい試験は CI で今も走る `visual-language/` に置く（`.github/workflows/e2e.yml:170-175`・全体の E2E は `:294` で停止）。直す前に落ちることを GitHub の CI で示す（impl-card.md §4 の 5） |
| スマホを壊さない | ○ | スマホ幅はヘッダーのボタンを出さない（`frontend/src/pages/inbox/InboxPage.tsx:83`）。試験も skip |
| 受け入れ基準の測り方 | ○ | K1〜K5 の全行に測り方と担当がある（design.md §6） |
| 実装範囲の明確さ | ○ | 前後のコードと触らない範囲・想定分岐がある（design.md §3-3・§3-4、impl-card.md §3） |

## 審査で直したこと

- 試験の置き場所を、止まっている全体の E2E（`frontend/tests-e2e/` 直下）から、CI で走る `visual-language/` に変えた。
- 案D（`HeaderButton` に付ける）が受信箱に効かない理由（受信箱は `Button` と `icon-btn` を直接使う。`InboxPage.tsx:87-113`）を書き足した。

## 1回目の依頼の後の直し（2026-11-23）

- クラウドで試験用のブラウザが取れず BLOCKED になった（Download failure, code=1）。赤と緑の確かめを GitHub の CI（画面検査）へ移し、依頼を「試験だけ」と「CSS だけ」の2回に分けた（impl-card.md §4）。確かめる中身（768・1280 で直す前に落ち、直した後に通る）は変えていない。判定は APPROVE のまま。

## 未解決事項

- なし。
- 未確認（設計合格を妨げない）: タブレット幅（768〜1279px）での本番実測。CI の 768px の試験で確かめる。
