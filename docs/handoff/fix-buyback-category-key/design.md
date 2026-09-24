# design: fix-buyback-category-key

## KGI

買取 by-product ページのカテゴリタブが `bsp.card_game` の正規化キー（例: `pokemon` / `onepiece`）で表示され、
同一カードゲームの重複タブが消える。

## 変更内容（4箇所・buyback_prices.py のみ）

| Change | 場所 | 変更前 | 変更後 |
|--------|------|--------|--------|
| A | `buyback_prices.py:413,419` (swing CTE) | `UPPER(p.category)` SELECT/GROUP BY | `bsp.card_game` SELECT/GROUP BY |
| B | `buyback_prices.py:424,428` (non-swing) | `UPPER(p.category)` SELECT/GROUP BY | `bsp.card_game` SELECT/GROUP BY |
| C | `buyback_prices.py:439` (filter) | `UPPER(p.category) = UPPER(:category)` | `EXISTS (SELECT 1 FROM bsp_f WHERE bsp_f.product_id = p.id AND bsp_f.card_game = :category)` |
| D | `buyback_prices.py:479` (main SELECT) | `UPPER(p.category) AS category` | scalar subquery from `bsp_cg.card_game` |

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| カテゴリタブに重複なし | 買取 by-product ページを開き、タブ一覧を目視確認。同名タブが複数存在しないこと |
| タブクリックで対応商品のみ表示 | `pokemon` タブクリック後、一覧に pokemon 以外の商品が表示されないこと |
| タブカウント数が実態と一致 | 各タブの件数バッジが、実際の一覧件数と一致すること |
| swing フィルター併用時も正常 | swing_days / min_swing パラメータ付きリクエストでも重複タブが出ないこと |

## 触らない範囲

- `products.category` カラムのデータ（変更なし）
- フロントエンドコード（変更なし）
- `list_by_shop` エンドポイント（すでに `bsp.card_game` 使用・変更不要）
- マイグレーションファイル（スキーマ変更なし）

## 外部事例

N/A — 自由記述カラムから正規化済みカラムへの参照切り替えは内部SQL修正。

## 守り手

- 既存 CI テスト（`backend/tests/`）— buyback 専用テストは未作成だが回帰範囲外
- 本番反映後: 買取 by-product ページのタブ目視確認
