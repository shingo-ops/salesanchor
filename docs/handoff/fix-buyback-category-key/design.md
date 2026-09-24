# design: fix-buyback-category-key

recon: docs/handoff/fix-buyback-category-key/recon.md

ADR: ADR-155

## KGI

買取 by-product ページのカテゴリタブが bsp.card_game の正規化キー（例: pokemon / onepiece）で表示され、
同一カードゲームの重複タブが消える。

## 変更内容（4箇所）

対象ファイル: backend/app/routers/buyback_prices.py

| Change | 行 | 変更前 | 変更後 |
|--------|---|--------|--------|
| A | 413,419 (swing CTE) | UPPER(p.category) SELECT/GROUP BY | bsp.card_game SELECT/GROUP BY |
| B | 424,428 (non-swing) | UPPER(p.category) SELECT/GROUP BY | bsp.card_game SELECT/GROUP BY |
| C | 439 (filter) | UPPER(p.category) = UPPER(:category) | EXISTS (SELECT 1 FROM bsp_f WHERE bsp_f.product_id = p.id AND bsp_f.card_game = :category) |
| D | 479 (main SELECT) | UPPER(p.category) AS category | scalar subquery from bsp_cg.card_game |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| カテゴリタブに重複なし | 買取 by-product ページを開き、タブ一覧を目視確認。同名タブが複数存在しないこと |
| タブクリックで対応商品のみ表示 | pokemon タブクリック後、一覧に pokemon 以外の商品が表示されないこと |
| タブカウント数が実態と一致 | 各タブの件数バッジが、実際の一覧件数と一致すること |
| swing フィルター併用時も正常 | swing_days / min_swing パラメータ付きリクエストでも重複タブが出ないこと |

## 触らない範囲

- products.category カラムのデータ（変更なし）
- フロントエンドコード（変更なし）
- list_by_shop エンドポイント（すでに bsp.card_game 使用・変更不要）
- マイグレーションファイル（スキーマ変更なし）

## 外部・過去事例の参照と我々への応用

該当なし。自由記述カラムから正規化済みカラムへの参照切り替えは内部SQL修正のみ。
list_by_shop エンドポイントが既に bsp.card_game を使用している実績を参考に、
list_by_product も同じカラムに統一する。

## 維持の仕組み

守り手: 既存 CI テスト（backend/tests/）、本番反映後の買取 by-product ページ目視確認
