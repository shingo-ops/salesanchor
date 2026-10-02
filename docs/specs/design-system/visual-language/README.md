# アプリ視覚デザイン言語（visual-language）— 表紙

> この文書は何か（専門用語なしの1行）:
> アプリの画面部品（金型）を美しく・PCでもスマホでも使いやすくするための「組み合わせ方の決まり」の入口。

- 親テーマ: [design-system](../README.md)（トークン・共通部品・SSOT）。兄弟: component-ssot（page-title / page-header-v2 / field-size）
- 日付: 2026-10-02 / PO: しんご
- 状態: PO原文は記録済み。KGIはPO承認済み（2026-10-02）。設計は草案（自己審査済み）。製品の実装には着手していない。
- 子文書:
  - [ideal-state.md](./ideal-state.md) — PO原文（書き換え禁止）
  - [kgi.md](./kgi.md) — 合格条件の候補（基準値は実測済み、目標値は未承認）
  - [design.md](./design.md) — 設計草案
  - [recon](../../../handoff/app-visual-language/recon.md) — 現状の実測（基準コミット 946e6dbcd）

## 境界
- 対象: 見た目の質と使いやすさ。具体的には、文字の強弱・余白のリズム・密度・画面幅ごとの並び方・メッセージ画面の操作の型。親テーマ README の境界13行目で「対象外（別途行う）」とされた範囲を、このテーマで扱う。
- 対象外: DB・API・配線（他セッションの管轄）、データの持ち方。
- 値の正本は変えない: 色・寸法などの値は `frontend/src/tokens.css` と `frontend/src/index.css`、部品は `frontend/src/components/` が正本のまま。この文書は値を持たず、トークン名と金型名で参照する。
- 受信箱カルテ（右パネル）の見た目の正本は ADR-108 の `docs/adr/karte_reference.html`。この部分を変える場合は ADR-108 側で扱う。

## 維持の仕組み
- 守り手: frontend/package.json（`check:all`。色・値の直書き、ブレークポイント同期、モバイル構造などを検査する既存の関所）
- 対象: 金型登録のない直書き、トークン外の値
- このテーマで新しく必要になる関所（3幅の画面検査）は、まだ無い。design.md の段階1で設計する。それまでは人手で守る（理由: 関所が未実装のため）。
