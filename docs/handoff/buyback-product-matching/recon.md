# Recon: buyback-product-matching

## ADR参照
- ADR-157: 買取価格スクレイパー（Phase 3: 商品マスタ紐付け）

## 既存実装の確認

### マッチングロジック（横展開元）
- `backend/app/services/tcg_analyzer_svc.py:299` — `match_keyword()`: 検索KW/除外KWによる商品マッチング
- `backend/app/services/tcg_analyzer_svc.py:243` — `normalize_en()`: 商品名正規化（半角統一・スペース正規化）
- `backend/app/services/tcg_analyzer_svc.py:175` — `load_product_keywords()`: 商品マスタからKW辞書を構築

### 買取テーブル元定義
- `migrations/20260921_140000_create_buyback_tables.sql` — `buyback_shop_products` 定義
  - `product_id UUID NULL` — 今回 INTEGER に変更（全件NULL、データ影響なし）

### 買取ルーター既存実装
- `backend/app/routers/buyback_prices.py` — `GET /buyback-prices` 既存エンドポイント

### 買取スクレイパー既存実装
- `backend/app/tasks/buyback_scraper.py` — Celery タスク本体

### フロントエンド既存実装
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx` — 一覧ページ
- `frontend/src/pages/buyback-prices/buybackTypes.ts` — 型定義

## マッチング精度（本番460件実測）
| 区分 | 件数 | 率 |
|------|------|-----|
| auto | 318 | 69% |
| pending_review | 3 | 1% |
| unmatched | 139 | 30% |

| 店舗 | マッチ率 |
|------|---------|
| ホムラ | 85.1% |
| シンソク | 57.1% |

| カードゲーム | マッチ率 |
|-------------|---------|
| ワンピース | 100% |
| 遊戯王 | 80% |
| ポケモン | 66.6% |
