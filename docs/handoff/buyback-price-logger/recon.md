# recon: buyback-price-logger (ADR-157 Phase 1)

## 既存ADR検索結果

`git grep -i buyback docs/adr/` → ヒットなし（新規機能）

関連ADR:
- ADR-025: データ手動INSERT原則禁止（public スキーマテーブル設計に影響）
- ADR-027: i18n 強制（UI文字列は t("key") 経由）
- ADR-072: write エンドポイントの reset_tenant_context() 必須
- ADR-144: UIガバナンス遵守（DataTable/SelectControl/Drawer 金型使用）

## 実装対象ファイル

### Backend（新規）
- `backend/app/services/buyback_scraper/__init__.py` — パッケージ init
- `backend/app/services/buyback_scraper/base.py` — 基底スクレイパークラス
- `backend/app/services/buyback_scraper/shinsoku.py` — シンソク REST API スクレイパー
- `backend/app/services/buyback_scraper/homura.py` — 買取ホムラ HTML スクレイパー
- `backend/app/tasks/buyback_scraper.py` — Celery タスク（4時間ごと定期実行）
- `backend/app/routers/buyback_prices.py` — REST API エンドポイント

### Backend（変更）
- `backend/app/celery_app.py` — beat_schedule に buyback_scraper タスク追加
- `backend/app/main.py` — buyback_prices ルーター登録
- `backend/requirements.txt` — beautifulsoup4, lxml 追加

### Frontend（新規）
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx`
- `frontend/src/pages/buyback-prices/BuybackPricesPage.module.css`

### Frontend（変更）
- `frontend/src/App.tsx` — /buyback-prices ルート追加
- `frontend/src/components/DesktopShell.tsx` — サイドバーナビ追加
- `frontend/src/components/MobileShell.tsx` — モバイルナビ追加
- `frontend/src/locales/ja.json` — 28キー追加
- `frontend/src/locales/en.json` — 28キー追加

### Migrations（新規）
- `migrations/20260921_140000_create_buyback_tables.sql`
  - `public.buyback_shop_products` テーブル
  - `public.buyback_price_logs` テーブル

### Docs（新規）
- `docs/adr/ADR-157-buyback-price-logger.md`
- `docs/adr/README.md` — generate-adr-index.js により再生成

## スコープ外（触らない範囲）

- 既存スクレイパー・パイプライン（pipeline_*/抽出系）
- テナント別在庫テーブル
- 仕入れ・取引管理系ルーター
