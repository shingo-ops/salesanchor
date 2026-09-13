# 添付ファイル配信API 設計書（attachment-storage 便4）

- 対象ADR: docs/adr/ADR-091-discord-bot-scope-definition.md
- recon: docs/handoff/attachment-serve-api/recon.md

## 目的

Discord CDN の署名付き URL はブラウザから 503 を返す（サーバー側からは 200）。
便3で自社ディスクに保存した実体を、自社 API 経由でブラウザに配信する。
画面（frontend）は `msg.attachment_url` を `<img src>` に使うだけなので、
`attachment_url` を自社 URL に書き換えれば画面変更ゼロで表示が機能する。

## 変更対象

| ファイル | 変更内容 |
|---|---|
| `backend/app/routers/leads.py` | `GET /leads/{lead_id}/attachments/{attachment_id}` 新設 |
| `backend/app/discord_gateway/ticket_channel_writer.py` | INSERT に `RETURNING id` 追加・`meta_messages.attachment_url` を自社 URL に UPDATE |
| `backend/tests/test_attachment_serve.py` | 新設 API のユニットテスト（SQLite + tmp_path） |

## 外部・過去事例の参照と我々への応用

**Django / Rails の send_file パターン（一般的な Web フレームワーク）**
- 署名付き CDN URL を使わず、アプリサーバーがディスクから読み込み `Content-Disposition` で返す。
- キャッシュヘッダ `Cache-Control: private, max-age=3600` を付けることでブラウザが
  1 時間キャッシュし、同じ画像を繰り返し取得しない。
- 我々への応用: FastAPI の `FileResponse` が同等のパターンを提供する。
  `media_type` と `filename` を DB から取得して設定することで
  ブラウザの保存ダイアログ対応と MIME 判定を両立する。

**既存 SSE 前例（`backend/app/routers/meta_inbox.py:1105`）**
- `StreamingResponse` の使い方を参照し、`FileResponse` との違いを把握した。
- `FileResponse` は `starlette.responses` から import し、遅延 import でルーター冒頭を汚さない。

## 受入基準

| 基準 | 検証方法 |
|---|---|
| 存在しない `attachment_id` に対して 404 が返る | `test_serve_not_found_attachment_id` |
| 他テナントの行に対して 404 が返る（RLS 相当） | `test_serve_other_tenant_returns_404` |
| DB 行があっても実体ファイルが無い場合に 404 が返る | `test_serve_missing_file_returns_404` |
| 正常時に 200 と正しい `content-type` が返る | `test_serve_success_returns_file` |
| 受信時に `meta_messages.attachment_url` が自社 URL になる | `ticket_channel_writer.py` の UPDATE 確認（ログで検証） |
| 既存テスト（attachment_save / ticket_channel / inbox）が壊れない | CI 全 passed |

## 実装方針

### 配信 URL の形式
```
/api/v1/leads/{lead_id}/attachments/{attachment_id}
```
`attachment_id` は `lead_attachments.id`（自社採番・integer）を使う。
`message_id`（Discord 側 ID）を使わない理由: プラットフォーム依存を避けるため。
将来 LINE 等を追加しても形式が変わらない。

### ファイルパス解決
`ATTACHMENT_ROOT`（デフォルト `/data/attachments`）+ `file_path`（DB の相対パス）。
`Path.is_file()` で存在確認し、不在なら 404。

### 権限
`require_permission("messaging.view")` — 既存 attachment-url API と同じ。

## 弊害・トレードオフ

1. **`attachment_url` の混在**
   `meta_messages.attachment_url` に Discord CDN URL（旧受信分）と
   自社 URL（本便以降の新受信分）が混在する。
   Discord 分は今後すべて自社 URL になるため時間とともに解消する。
   Meta 分は既存方式を維持するため CDN URL のまま残る。
   画面（`InboxMessageThread.tsx`）は URL の形式を問わず `<img src>` に渡すため、
   混在しても動作上の問題はない。

2. **画面を変更しない設計判断**
   `msg.attachment_url` をそのまま `<img src>` に使う既存ロジックを変更しない。
   `attachment_url` 列の値を自社 URL に変えることで、画面変更ゼロで機能させる。
   この判断により frontend の変更・テスト・デプロイのリスクをゼロにする。

3. **テストの `load_user_permissions` モック衝突**
   テストファイル内で自前 `patch("app.auth.dependencies.load_user_permissions", ...)` を
   行うと、`conftest.py:1477` の `bypass_permissions`（`autouse=True`）と二重になり、
   実際の呼び出し引数 `(db, tenant_id, user_id)` に対して
   自前モックの旧シグネチャ `(user_id, db)` が不一致を起こし `TypeError` になる。
   解決策: 自前 `patch` を完全に除去し、`conftest` の `autouse` に委ねる。

## 維持の仕組み

守り手: `backend/tests/test_attachment_serve.py` の 4 テストが CI で毎 PR 実行される。
- `test_serve_not_found_attachment_id` — 404 境界
- `test_serve_other_tenant_returns_404` — テナント分離
- `test_serve_missing_file_returns_404` — 実体不在の 404
- `test_serve_success_returns_file` — 正常系 200 + media_type

`ATTACHMENT_ROOT` 環境変数を変えれば、将来 S3 Presigned URL などへの移行も可能。
