# design: ボタン案内・ウェルカムをサーバー名義で投稿

> 作成: 2026-10-02 | recon: `docs/handoff/discord-guild-identity-posts/recon.md` | 対象ADR: ADR-159, ADR-091

## 外部・過去事例の参照と我々への応用
| 事例 | 応用 |
|---|---|
| Discord 公式 docs: application-owned webhook は components 送信可 | Bot 作成の既存 webhook 基盤（ADR-159）をそのまま流用 |
| ギルドアイコン CDN 仕様（a_ = アニメーション） | gif/png を拡張子で切替。DB へ複製せず送信時に取得 |

## 変更（触らない範囲: send_as_staff の挙動、ephemeral 返信、DB スキーマ）
1. `backend/app/services/discord_webhook_sender.py`: 送信本体を `_send_via_webhook` に共通化。`send_as_identity`（components 対応）と `try_send_as_identity`（失敗時 None）を追加。`send_as_staff` は components なしで同一挙動。
2. `backend/app/services/discord_guild_identity.py`（新規）: `GuildIdentity`・`guild_icon_url`・`build_guild_identity`・`fetch_guild_identity`（GET /guilds/{id}）。
3. `backend/app/routers/discord_auto_setup.py` / `backend/app/routers/discord_ticket_config.py`: ボタンをサーバー名義で投稿。None なら従来の Bot 投稿へ戻す。
4. `backend/app/discord_gateway/ticket_channel_creator.py`: ウェルカムを `guild.name` / `guild.icon.key` からサーバー名義で送信。失敗時は `channel.send`。

方針: サーバー名義の案内は欠落させない（名前が discord/clyde を含む・80 超・webhook 権限なし・API 失敗はすべて Bot 投稿へ戻し warning ログ）。担当者返信はフォールバックなしのまま。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| ボタン投稿が username=サーバー名・avatar=サーバーアイコン・components 付きの webhook 実行になる | tests/test_discord_webhook_sender.py::test_send_as_identity_includes_components_username_and_avatar |
| アニメーションアイコンは gif、静止は png、未設定は avatar なし | test_guild_icon_url_handles_static_animated_and_missing / test_try_send_as_identity_returns_id_on_success |
| 名前不正・webhook エラーで Bot 投稿に戻る | test_try_send_as_identity_*、tests/test_discord_guild_identity_posts.py、tests/test_discord_ticket_channel.py::test_welcome_falls_back_* |
| 担当者返信は components なし・挙動不変 | test_send_as_staff_payload_has_no_components と既存 sender テスト |
| 実機: tenant_001 で「ボタンを投稿する」→ メッセージにサーバー名/アイコン表示 → 「Open a ticket」押下でチケットチャンネル作成 → ウェルカムにサーバー名/アイコン表示 | PO が実機確認（デプロイ後） |

## リスク・戻し方
- リスク: webhook 投稿のボタン押下が Bot に届かない可能性（docs に明記なし）。届かなければ本 PR を revert（DB 変更なし・revert のみで元に戻る）。
- 戻し方: `git revert` のみ。測り方: 上記実機確認。

## 維持の仕組み
守り手: 人手で守る（受入条件表のテストが CI で毎回実行される。Bot 投稿への戻り経路もテストで固定）
- 担当者返信のフォールバック禁止（ADR-159）は send_as_staff の既存テストで維持。
