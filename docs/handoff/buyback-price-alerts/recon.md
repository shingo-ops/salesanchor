# Recon: buyback-price-alerts

## 観測事実

- 買取価格データ蓄積中（457商品・JST 10:00/13:00/22:00 の3回取得）
- 価格変動をアプリ画面で検知・通知する仕組みが未実装
- 既存の通知パターン: `backend/app/services/discord_notifier.py` — Discord Webhook + de-bounce（既存・変更しない）
- 既存の通知チャンネル設定: `notification_channels` テーブル（テナントスキーマ）
- 買取データは `public` スキーマ → アラートルールも `public` に配置が自然
- フォーム用金型: `Modal`・`TextField`・`SelectControl`・`Button`・`Card`・`Badge` — 全て存在確認済み
- ADR: `docs/adr/ADR-157-buyback-price-logger.md`

## 影響ファイル

### 新規作成
- `migrations/20260924_000000_create_buyback_alert_rules.sql`
- `backend/app/routers/buyback_alerts.py`
- `backend/app/services/buyback_scraper/alert_checker.py`

### 変更
- `scripts/run_all_migrations.sh` — マイグレーション登録追加
- `backend/app/main.py` — ルーター登録追加
- `backend/app/tasks/buyback_scraper.py` — アラートチェック呼び出し追加
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx` — アラート設定UI追加
- `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` — i18nキー22件追加
