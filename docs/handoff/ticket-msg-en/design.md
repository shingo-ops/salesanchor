# design: チケット案内文2種の英語化

- 日付: 2026-06-29
- 担当: Hikky-dev
- 関連: ADR-091
- recon: `docs/handoff/ticket-msg-en/recon.md`

## KGI

| 基準 | 検証方法 |
|---|---|
| ①ticket-startのボタン案内文が英語になる | Discord上でticket-startを確認（デプロイ後・再投稿要） |
| ②チケット発行時の専用チャンネル案内が英語になる | テストサーバーでボタン押下し確認（次回発行から自動） |

## 確定文言（PO確定）

| # | 日本語（変更前） | 英語（変更後） |
|---|---|---|
| ① | `サポートが必要な場合は下のボタンを押してください。` | `Whether it's a new order or a follow-up, we're here to help — just tap below to get started.` |
| ② | `f"専用チャンネルを用意しました → {channel.mention}"` | `f"We've set up a private channel just for you → {channel.mention}"` |

## 変更内容

### ①ボタン案内文（2か所・同一文）

- `backend/app/routers/discord_auto_setup.py:591` — `_post_ticket_button_step()` payload["content"]
- `backend/app/routers/discord_ticket_config.py:257` — `deploy_ticket_button()` payload["content"]

### ②専用チャンネル案内（1か所）

- `backend/app/discord_gateway/client.py:193` — `interaction.followup.send()`
- `{channel.mention}` はそのまま維持。`ephemeral=True` も維持。

### テスト追従（必須）

- `backend/tests/test_discord_auto_setup.py:227, 874` — アサーション文字列を新英語文言に更新

## 触らない範囲

- `welcome_template`（歓迎メッセージ・既に英語化済み）
- ボタンの `custom_id`（ticket_open）・ボタンラベル（チケットを開く）
- チケット作成ロジック・受信振り分け・`_hide_ticket_start`
- `en.json`/`ja.json`（①②はi18n管理外）
- migration / deploy.yml（DB変更なし）

## DB変更

なし。

## 外部事例

Discord bot の案内文英語化は文字列置換のみ。ロジック変更なし。

## デプロイ後の実機確認手順

### ②（自動反映・再投稿不要）
1. テストサーバーで任意ユーザーがチケットを開く
2. エフェメラルメッセージが `"We've set up a private channel just for you → #ticket-xxx"` と表示されること ○

### ①（既存ボタン再投稿が必要）
1. ticket-start チャンネルの既存ボタンメッセージを Discord 上で手動削除
2. 管理画面 → `POST /admin/discord-ticket-config/deploy-button` 実行（または auto-setup 再実行）
3. ticket-start に `"Whether it's a new order or a follow-up, we're here to help — just tap below to get started."` ＋ ボタンが表示されること ○
