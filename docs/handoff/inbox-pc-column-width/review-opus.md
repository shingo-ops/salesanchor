# 設計審査: PC受信箱の3列の幅（Architect）

> この文書は何か: design.md が実装役に渡せる出来かを審査した記録。

- 審査日: 2026-11-23
- 審査者: Claude Opus（設計担当が Architect を兼ねた自己審査。独立した第二者の審査ではない。独立の確認はマージ前の審査役 reviewer が行う）
- 対象: [design.md](./design.md)・[recon.md](./recon.md)・[ADR-1086](../../adr/ADR-1086-inbox-pc-column-width.md)

## 判定: APPROVE（設計合格）

設計合格は、PO の実装承認・実装開始・マージ・本番反映の承認を兼ねない。

## 確かめたこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR との整合 | ○ | ADR-064 は幅の記述を根拠にしないと明記（`docs/adr/ADR-064-inbox-meta-exact-replica.md:117`）。ADR-108 の 396px はタブレットの引き出しで残す。ADR-067 に沿い値は全部トークン |
| 箱の入れ子と `%` の基準 | ○ | `frontend/src/pages/inbox/InboxPage.tsx:161-273` を読み、カルテ＝`.inbox-wrapper`、一覧＝`.inbox-columns` が基準と確認。本番実測（recon.md §3-2）の式と5幅で一致 |
| 数字の再計算 | ○ | 1280〜2560px を 1px 刻みで計算。最大を超える幅 0 件・会話欄の最小 449.8px（1280px）。K1〜K5 は表と ±1px 以内 |
| カルテを隠したとき | ○（審査で追加） | `frontend/src/pages/inbox/InboxKartePanel.tsx:130-133` で隠せる。一覧は 330px。K6b を足した |
| タブレット・スマホを壊さない | ○ | `frontend/src/pages/inbox/InboxPage.css:904`・`:922`（`!important`）・`:1042`・`:1249` が PC の指定を上書きする |
| 書き出し先で使えるか | ○ | `min()` は Chrome 87・Safari 14 で使える（MDN・Context7）。`cqw` は使わない |
| 検査に止められないか | ○ | `frontend/scripts/check-css-hardcoded-values.js` は `var()` を含む値を検査しない。生の px は書かない |
| 受け入れ基準の測り方 | ○ | 全行に測り方と担当がある（design.md §6） |
| 実装範囲の明確さ | ○ | 4か所の前後のコードと、触らない範囲が書かれている（design.md §3-3・§3-4） |

## 審査で直したこと

- 一覧とカルテが最大の幅に達する窓の幅を、約1300px・約1468px から 約1316px・約1469px に直した（1px 刻みの計算に合わせた）。
- カルテを隠したときの幅（K6b）と、その測り方を足した。
- recon.md に箱の入れ子の行番号を足した。

## 未解決事項

- なし。
- 別件（本件の対象外）: ページが縦に 31px はみ出してスクロールバーが出る（recon.md §3-1）。
