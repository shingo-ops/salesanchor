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

## 外部事例
既存パターン踏襲のため該当なし。`backend/app/routers/reports.py` が直接の参考実装。

## 検証方法

| 基準 | 検証方法 |
|------|---------|
| スーパー管理者でボタン表示 | is_super_admin=true ユーザーで /buyback-prices を開き「今すぐ取得」ボタンが表示される |
| 非スーパー管理者でボタン非表示 | is_super_admin=false ユーザーでボタンが表示されない |
| クリック → 202 返却 | ボタンクリック後「取得タスクを開始しました」メッセージが表示される |
| 非認証リクエスト拒否 | Bearer なしの POST /buyback-prices/trigger が 403 返却 |

## ADR参照
- ADR-157: 買取相場ログ（本機能の親ADR）

## 弊害
- なし（既存 GET エンドポイントへの影響なし・ルーター登録順は POST を GET の前に配置）
