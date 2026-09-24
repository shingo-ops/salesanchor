# design: buyback by-product view improvements

## 参照ADR

- ADR-157: 買取相場ログ

## 変更方針

既存の `list_by_product` エンドポイントを後方互換を保ちながら拡張する。

| 項目 | 変更前 | 変更後 |
|---|---|---|
| mark | なし | `p.mark` をSELECT追加 |
| 最高価格 | homura_price_s / shinsoku_price_s 個別 | `best_price` = GREATEST(両店舗) |
| 最高価格店舗 | なし | `best_shop` = どちらの店舗か |
| 前日比 | なし | `yesterday_diff` = 今日best - 前日best（前日なしはNULL） |
| カテゴリ | `p.category`（混在） | `UPPER(p.category)`（正規化） |

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| mark列が表示される | ブラウザで/buyback-prices の商品別タブを開き、Mark列が見えること |
| best_price列に最高価格と店舗名が表示される | homura/shinsoku いずれか高い方の価格と店舗バッジが表示されること |
| yesterday_diffが前日比を正しく表示 | 前日データあり → 差分が+/-色付きで表示。なし → 「—」 |
| カテゴリタブが正規化される | 大文字/小文字混在カテゴリが同一タブに集約される |

## 外部事例

GREATEST() / LATERAL JOIN は PostgreSQL 標準。yesterday_diff の NULL判定は両prev NULLの場合のみNULLとする。

## 守り手

既存フィールド（homura_*/shinsoku_*）はAPIレスポンスに残し、BuybackProductHistoryDrawerが引き続き利用できる。
