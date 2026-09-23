# design: fix-buyback-chart-stocklike

recon: docs/handoff/fix-buyback-chart-stocklike/recon.md

## KGI
買取価格チャートが株チャートと同様に動作する。

| 基準 | 検証方法 |
|------|---------|
| 価格変化がなくても毎スクレイプで price_logs に1件追加される | スクレイプ2回実行後 SELECT COUNT(*) が +2 になること |
| history エンドポイントが fetched_at ASC で返却する | レスポンス JSON の history[0].fetched_at が最古であること |
| チャートに S/A/AM/B/C 5本の Line が表示される | ブラウザで Drawer を開き5本確認 |

## 変更方針

### Fix 1: 毎回 INSERT（base.py）
前回ログ取得クエリと diff-only 条件分岐を削除し、UPSERT 直後に無条件で INSERT する。

### Fix 2: ASC 順（buyback_prices.py）
history クエリの `ORDER BY fetched_at DESC` を `ORDER BY fetched_at ASC` に変更。

### Fix 3: AM・C 追加（BuybackPricesPage.tsx）
- `BuybackProduct` に `price_am`/`price_c` フィールドを追加
- `chartData` マッピングに AM/C キーを追加
- `<Line dataKey="AM">` と `<Line dataKey="C">` を追加（既存トークン `--info`/`--color-error` 使用）

## 影響範囲
- フロントエンド: BuybackPricesPage のみ
- バックエンド: buyback_scraper/base.py（INSERT 頻度増加）、buyback_prices.py（ORDER BY 変更）
- DB: スキーマ変更なし。ログ行数がスクレイプ頻度×商品数で増加する

## 弊害・リスク
- ログテーブルのデータ量が増加する（スクレイプ頻度×商品数/日）
- 過去の diff-only データとの混在は問題なし（時系列は連続する）

## 戻し方
git revert でコミットを差し戻す（migrations なし）

## 外部・過去事例の参照と我々への応用
- 株価チャートの標準設計: 価格変化の有無にかかわらず定時でレコードを記録し時系列グラフを描画する
- recharts の `connectNulls` prop: データ欠損点をスキップして線を繋げる（既に実装済み）

## 維持の仕組み
今後のスクレイパー追加時も `save_product_and_price` を使えば自動的に毎回記録される。

守り手: docs/adr/ADR-157-buyback-price-logger.md（ADR-157 オーナー: shingo-ops）
