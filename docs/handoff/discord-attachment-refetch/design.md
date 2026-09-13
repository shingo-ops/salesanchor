# design: discord-attachment-refetch

## 目的

Discord プラットフォームで受信した画像の CDN URL が期限切れになった場合に、
Bot Token を用いて Discord REST API からメッセージを再取得し、有効な添付 URL を返す。

対象ADR: ADR-091

recon: docs/handoff/discord-attachment-refetch/recon.md

## 変更内容

`backend/app/routers/leads.py:1326` に Discord 専用分岐を追加。

- `platform == "discord"` のとき、Meta Graph API ではなく `discord_api_request` を呼ぶ。
- Bot Token は `DISCORD_BOT_TOKEN` 環境変数から取得（ADR-091 B方式と同パターン）。
- チャンネル ID は `leads.discord_guild_channel_id` から取得。
- Discord API の `GET /channels/{channel_id}/messages/{message_id}` で attachments を取得。
- 成功時: `attachment_url` を DB に UPDATE し `{"url": ...}` を返す。
- 失敗時: 404 `expired_or_unavailable`。

## 外部・過去事例の参照と我々への応用

Meta CDN URL の期限切れ対応として `fetch_attachment_url`（`backend/app/services/meta_graph.py:1197`）が実装済み。
Discord の CDN URL（`cdn.discordapp.com`）も同様に期限付きであることが Discord 公式ドキュメントで確認されている。
Meta 側の実装パターン（onError → 再取得API → DB更新 → 画面反映）をそのまま Discord にも適用する。
Bot Token の取得パターンは `backend/app/routers/discord_channel_invite.py:47` の `_get_bot_token()` と同一。

## 受入基準

| 基準 | 検証方法 |
|---|---|
| platform == "discord" のとき Discord API を呼ぶ | test_discord_inbox.py の全 PASS |
| Bot Token 未設定時は 409 を返す | pytest test_discord_inbox.py |
| channel_id 未設定時は 404 を返す | pytest test_discord_inbox.py |
| Discord API 失敗時は 404 `expired_or_unavailable` を返す | pytest test_discord_inbox.py |
| Meta 側の既存テストが壊れていない | test_message_image_send.py 全 PASS / test_messages.py 全 PASS |

## 弊害・トレードオフ

- **Discord の新 URL にも期限がある**: Discord CDN URL は再取得しても有効期限が存在する。
  本実装は「表示しようとした瞬間に取り直す」対症療法であり、根本解決ではない。
  根本解決（受信画像を自社ストレージに保存してパーマリンクを生成する）は別テーマとして扱う。
- Bot Token は環境変数から取得するため、テナントごとの差異を吸収できない。
  現状は単一 Bot 運用のため問題なし。マルチ Bot 対応は別 ADR で検討する。

## 維持の仕組み

- 守り手: 人手で守る（Discord CDN URL 期限切れ対応は E2E テストで自動検証困難なため）
- CI で `test_discord_inbox.py` を実行し、分岐追加によるリグレッションを検出する。
