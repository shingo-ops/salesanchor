# ADR-157: 買取相場ログ（外部買取店の価格定期取得）

## Status

proposed

## Date

2026-09-21

## Context

運営者・テナントが TCG（トレーディングカードゲーム）商品の買取相場を把握するため、
外部買取店の価格情報を定期的に取得してログ化する仕組みが必要になった。

主な要求:
- 複数の外部買取店の買取価格を定期収集する
- 商品ごとの価格推移（時系列）を参照できるようにする
- 将来的に運営者・テナントが「今いくらで買い取られているか」をアプリ内から閲覧できる API を提供する

対象外部ソース:
1. **シンソク（shinsoku-tcg.com）**: REST API 経由で BOX/CARTON/PACK/UNOPENED_PROMO を取得
2. **買取ホムラ（kaitori-homura.com）**: HTML スクレイピングで各カテゴリの価格を取得

## Decision

シンソク（REST API）と買取ホムラ（HTML スクレイピング）から 4 時間ごとに価格を取得し、
`public` スキーマの 2 テーブルに蓄積する（テナント横断の共用データ）。

### テーブル設計

- `public.buyback_shop_products`: 買取店ごとの商品マスタ（UPSERT で管理）
- `public.buyback_price_logs`: 時系列価格ログ（前回と価格変化があった場合のみ追記）

### 取得方式

- **シンソク**: `GET /api/brands?context=yuso` → ブランド一覧 → 各ブランド × type(BOX/CARTON/PACK/UNOPENED_PROMO) × 全ページを巡回
- **買取ホムラ**: 対象サブカテゴリ ID × 全ページを HTTP リクエスト → BeautifulSoup でパース

### レート制限

リクエスト間に 1.5 秒の sleep を挟み、外部サーバーへの負荷を抑制する。
User-Agent: `SalesAnchor-PriceLogger/1.0 (+https://salesanchor.jp)`

### Celery スケジュール

`beat_schedule` に `"fetch-buyback-prices"` を追加し、4 時間ごと（`crontab(minute=0, hour="*/4")`）に実行。

## Consequences

### 追加されるもの

- `public.buyback_shop_products` テーブル
- `public.buyback_price_logs` テーブル
- `backend/app/services/buyback_scraper/` パッケージ（base / shinsoku / homura）
- `backend/app/tasks/buyback_scraper.py` Celery タスク
- `backend/app/routers/buyback_prices.py` API エンドポイント
- `backend/requirements.txt` に `beautifulsoup4>=4.12.0` / `lxml>=5.0.0` を追加

### 注意事項

- 外部サイトの HTML 構造変更によりスクレイピングが壊れる可能性がある。  
  件数 0 件を異常とみなしてログ警告する。
- 商品マスタ（`public.buyback_shop_products`）の `product_id` は将来の自社商品マスタとのリンク用で、当初は NULL。
- public スキーマを使用するため RLS の `app.is_operator = 'true'` が必要。

## References

- `migrations/20260921_140000_create_buyback_tables.sql`
- `backend/app/services/buyback_scraper/`
- `backend/app/tasks/buyback_scraper.py`
- `backend/app/routers/buyback_prices.py`
