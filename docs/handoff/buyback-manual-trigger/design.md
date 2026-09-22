# design: buyback-manual-trigger

## KGI
スーパー管理者が買取相場ページの「今すぐ取得」ボタンをクリックすると、Celery タスクが開始され「取得タスクを開始しました」メッセージが画面に表示される。非スーパー管理者にはボタンが表示されない。

## 設計方針

| 項目 | 決定内容 |
|------|---------|
| 認証 | `require_super_admin`（`is_super_admin=True` ユーザーのみ） |
| レスポンス | HTTP 202 + `TriggerResponse{task_id, message}` |
| タスク実行 | `fetch_all_buyback_prices.delay()`（既存 Celery タスク） |
| UI制御 | `useSuperAdmin` フックで `isSuperAdmin` を取得、false 時は非表示 |
| ボタン | `Button variant="secondary" size="sm"`（金型遵守） |
| フィードバック | 成功/失敗メッセージを `fetchMsg` state で表示 |

## 外部・過去事例の参照と我々への応用

既存の `backend/app/routers/reports.py` に `export_csv.delay()` + HTTP 202 + `TriggerResponse` の実装パターンがあり、そのまま踏襲した。新たな外部ライブラリ・サービスの導入なし。我々への応用: 同じ delay + 202 パターンを buyback_prices.py に適用し、タスク起動の一貫性を維持する。

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| スーパー管理者でボタン表示 | is_super_admin=true ユーザーで /buyback-prices を開き「今すぐ取得」ボタンが表示される |
| 非スーパー管理者でボタン非表示 | is_super_admin=false ユーザーでボタンが表示されない |
| クリック → 202 返却 | ボタンクリック後「取得タスクを開始しました」メッセージが表示される |
| 非認証リクエスト拒否 | Bearer なしの POST /buyback-prices/trigger が 403 返却 |

## ADR参照
- ADR-157: 買取相場ログ（本機能の親ADR）

## recon参照
- docs/handoff/buyback-manual-trigger/recon.md

## 弊害
- なし（既存 GET エンドポイントへの影響なし・ルーター登録順は POST を GET の前に配置）

## 維持の仕組み

- `require_super_admin` dependency により非スーパー管理者からのアクセスは 403 で自動拒否
- フロントエンドの `useSuperAdmin` フックがボタン表示を制御するため UI レベルでも非表示

守り手: backend/app/auth/dependencies.py（require_super_admin）
