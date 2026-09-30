"""Discord Bot の顧客向け文言（SSOT）。

顧客（Discord サーバーのメンバー）に見える文言はすべてここで定義する。
英語を既定とする（PO 決定 2026-09-30「お客様向けは全部英語」）。
管理画面の API エラーや内部通知（運用者向け）は対象外で、日本語のまま各所に置く。

利用箇所:
  - discord_gateway/client.py（ボタン押下への ephemeral 応答）
  - discord_gateway/ticket_channel_creator.py（ウェルカム既定文）
  - routers/discord_auto_setup.py・routers/discord_ticket_config.py（ボタン投稿・設定既定値）

DB 側の既定値（tenant_discord_ticket_config.welcome_template）は
migrations/20260930_130000_set_discord_welcome_template_english.sql が
DEFAULT_WELCOME_TEMPLATE と同じ文言に揃える。
"""
from __future__ import annotations

# ウェルカム既定文（PO 確定・docs/handoff/ticket-welcome-en/design.md）
DEFAULT_WELCOME_TEMPLATE = (
    "Thanks for reaching out! I've created a private channel just for you. "
    "I'll connect you with our sales team — please reply with your name to get started."
)

# チケット開始ボタン（custom_id / emoji は変更しない）
TICKET_BUTTON_MESSAGE = "Need help? Click the button below to open a private support ticket."
TICKET_BUTTON_LABEL = "Open a ticket"
TICKET_BUTTON_CUSTOM_ID = "ticket_open"
TICKET_BUTTON_EMOJI = "🎫"

# ボタン押下への ephemeral 応答
TICKET_READY_TEMPLATE = "Your private channel is ready → {mention}"
GUILD_ONLY = "This can only be used inside a server."
GUILD_NOT_REGISTERED = "This server is not registered. Please contact the administrator."
TICKET_NOT_CONFIGURED = "The ticket feature is not set up. Please contact the administrator."
TICKET_CREATE_FAILED = "Failed to create the channel. Please contact the administrator."


def ticket_button_payload() -> dict:
    """チケット開始ボタン付きメッセージの Discord REST ペイロードを返す（呼び出しごとに新しい dict）。"""
    return {
        "content": TICKET_BUTTON_MESSAGE,
        "components": [
            {
                "type": 1,  # ActionRow
                "components": [
                    {
                        "type": 2,  # Button
                        "style": 1,  # Primary（青）
                        "label": TICKET_BUTTON_LABEL,
                        "custom_id": TICKET_BUTTON_CUSTOM_ID,
                        "emoji": {"name": TICKET_BUTTON_EMOJI},
                    }
                ],
            }
        ],
    }
