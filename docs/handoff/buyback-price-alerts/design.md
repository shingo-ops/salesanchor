# Design: buyback-price-alerts

recon: docs/handoff/buyback-price-alerts/recon.md

## 方針

買取価格の変動を検知し Discord 通知するアラートルールを、アプリ画面で CRUD 管理できるようにする。

### データモデル

`public.buyback_alert_rules` テーブル新設（buyback_shop_products と同じ public スキーマ）。
ルールごとに方向（下落/上昇/両方）・閾値（%）・監視グレード・対象フィルタ・クールダウンを設定。

### アラート発火フロー

1. スクレイパータスク `fetch_all_prices` 完了後に `check_alerts()` 実行
2. アクティブルールごとに直近2回の price_log を比較
3. 閾値超過の商品を集約し Discord Webhook で通知
4. `last_notified_at` を更新しクールダウン期間中の再通知を抑止

### フロントエンド

買取相場ページの ContentToolbar に「アラート設定」ボタン（super admin 限定）。
Modal(size="lg") でルール一覧表示 + 作成フォーム。全コンポーネントはデザインシステム金型使用。

## 変更前後

| 基準 | 検証方法 |
|---|---|
| アラートルール CRUD が動作する | アプリ画面でルール作成・有効/無効切替・削除 |
| 閾値超過時に Discord 通知が送られる | テストルールを作成し手動トリガーで発火確認 |
| スクレイパー本体に影響しない | アラートチェック例外時もスクレイパーは正常完了 |

**対象ADR**: ADR-157

守り手: `backend/app/routers/buyback_alerts.py`（CRUD API）/ `backend/app/services/buyback_scraper/alert_checker.py`（発火ロジック）

## 触るファイル
- `migrations/20260924_000000_create_buyback_alert_rules.sql`（新規）
- `scripts/run_all_migrations.sh`（登録追加）
- `backend/app/routers/buyback_alerts.py`（新規）
- `backend/app/services/buyback_scraper/alert_checker.py`（新規）
- `backend/app/main.py`（ルーター登録）
- `backend/app/tasks/buyback_scraper.py`（アラートチェック呼び出し）
- `frontend/src/pages/buyback-prices/BuybackPricesPage.tsx`（アラート設定UI）
- `frontend/src/locales/ja.json`（22キー追加）
- `frontend/src/locales/en.json`（22キー追加）

## 触らないファイル
- `backend/app/services/buyback_scraper/base.py`（スクレイパー本体は変更なし）
- `backend/app/services/discord_notifier.py`（既存通知は変更なし、パターンのみ参考）

## 外部・過去事例の参照と我々への応用
- 既存の `discord_notifier.py` の de-bounce パターン（`last_hard_stop_notified_at` + UPDATE RETURNING）を `last_notified_at` + `cooldown_minutes` で踏襲

## 維持の仕組み
- アラートチェックはスクレイパータスクに組み込み（別タスク不要）
- 例外発生時はログ出力のみでスクレイパー本体に影響しない（BLE001）
- ルール管理はアプリ画面からスーパー管理者が操作
