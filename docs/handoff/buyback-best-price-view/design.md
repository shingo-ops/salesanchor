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

## 外部・過去事例の参照と我々への応用

- PostgreSQL GREATEST() 関数: NULL値はスキップ（COALESCEで0補完して扱う）
- LATERAL JOIN パターン: 既に同エンドポイントで homura/shinsoku の最新価格取得に使用済み（buyback_prices.py:496-523）
- yesterday_diff の NULL判定: 両店舗前日データなしのみNULL（片方あれば差分計算）

## 維持の仕組み

- 既存フィールド（homura_*/shinsoku_*）はAPIレスポンスに残し、BuybackProductHistoryDrawerが引き続き利用できる
- カテゴリ正規化はUPPER()のみ。DBのデータは変更しない
- 行インデックスマッピング（r[0]..r[20]）はコメントなしで追跡が難しいため、将来的にmappings()切り替えを検討

## 弊害・リスク

- 前日比計算: `l.fetched_at < CURRENT_DATE` は日本時間ではなくサーバーUTC基準。UTC 0時前後で「前日」の定義がずれる可能性あり（許容範囲）
- yesterday_diffのゼロ表示: 両日同額の場合も0（—ではなく+¥0）が表示される（仕様）
