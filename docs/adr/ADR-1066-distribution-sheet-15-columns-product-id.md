# ADR-1066: 配信シートは PO が決めた15列の並びにし、最後に商品IDを載せる

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（K1〜K7 が ○ になったら採用に上げる） |
| 備考 | PO 2026-11-06「1、全配信データの構造を変更したい、並びは、投稿日時,Status,Mark,Japanese Title,English Title,Condition,Unit Price,Quantity,Ship_JA,Note_JA,提供者,Release Date,Series,Search Keywords,商品ID」。実装と反映: PO 2026-11-06「2」（問い「作ってよい。すぐ反映する」への答え） |
| 起案日 | 2026-11-06 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1014（在庫の行の定義は1か所）、ADR-1019（閲覧ページの列）、ADR-1023、ADR-099 |
| 設計・根拠 | [design.md](../handoff/dist-columns-product-id/design.md)、[recon.md](../handoff/dist-columns-product-id/recon.md)、[card.md](../handoff/dist-columns-product-id/card.md) |

---

## What（何を決めたか）

1. 配信先の「在庫集計」タブの見出しと並びは、`backend/app/services/tcg_distribution_svc.py` の `_SHEET_LAYOUT`（見出しと列名の組）が正本。並びは次の15列。
   投稿日時, Status, Mark, Japanese Title, English Title, Condition, Unit Price, Quantity, Ship_JA, Note_JA, 提供者, Release Date, Series, Search Keywords, 商品ID
2. 商品IDは `public.products.id` を文字で書く。
3. 商品の一覧表（マスタ）そのものはお客さんに送らない。
4. 閲覧ページ（アプリ）の写しと API は ADR-1019 のまま（14列＋offer_type）。商品IDは出さない。並びは `_GAS_COLUMNS` で別に持つ。
5. ADR-1014・ADR-1023 の「GAS 出力の14列は変えない」は当時の変更の範囲の決まりで、配信シートについてはこの ADR で15列に改める。

## Why（なぜ）

- お客さん側の GAS（例: 伊藤さんの見積シート）が、商品の名前の揺れに左右されずに商品を突き合わせるため。
- マスタを渡すと、商品の情報がまとめてお客さんの手に渡る。PO はそれを「最終手段」とした（2026-11-06）。
- 在庫一覧の GAS は見出しの名前で列を読むので、並び替えで壊れない（recon §5）。
- 閲覧ページまで変えると ADR-1019 と食い違い、位置で読む試験も約20か所動く。配信シートだけを変える（design §4-1 案A）。

## 戻し方

- 実装 PR を戻す PR をマージして反映する。配信は毎回タブ全体を書き直すので、次の配信で14列に戻る。DB の変更は無い。

## 受入条件

- design.md §7 の K1〜K7。
