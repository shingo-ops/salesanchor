"""Discord Bot の顧客向け文言（SSOT）。

顧客（Discord サーバーのメンバー）に見える文言はすべてここで定義する。
英語を既定とする（PO 決定 2026-09-30「お客様向けは全部英語」）。
管理画面の API エラーや内部通知（運用者向け）は対象外で、日本語のまま各所に置く。

利用箇所:
  - discord_gateway/client.py（ボタン押下への ephemeral 応答）
  - discord_gateway/ticket_channel_creator.py（ウェルカム既定文）
  - routers/discord_auto_setup.py・routers/discord_ticket_config.py（ボタン投稿・設定既定値）
  - routers/discord_channel_invite.py（規模別チャンネル案内）

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

# 自動セットアップが作る Discord カテゴリ名（PO 指定 2026-10-02・全角縦線 U+FF5C）
# DM: チケット開始チャンネル＋新規チケット / Stock: 小口（メンバー）・大口向け在庫アナウンス
CATEGORY_DM = "\U0001F4E9\uff5cDM"
CATEGORY_STOCK_MEMBER = "\U0001F340\uff5cStock Information"
CATEGORY_STOCK_LARGE = "\U0001F352\uff5cStock Information"
# 旧セットアップが作っていた DM カテゴリの名前（再実行時に CATEGORY_DM へ名前変更する）
CATEGORY_DM_LEGACY = "Sales Anchor"

# ボタン押下への ephemeral 応答
TICKET_READY_TEMPLATE = "Your private channel is ready → {mention}"
GUILD_ONLY = "This can only be used inside a server."
GUILD_NOT_REGISTERED = "This server is not registered. Please contact the administrator."
TICKET_NOT_CONFIGURED = "The ticket feature is not set up. Please contact the administrator."
TICKET_CREATE_FAILED = "Failed to create the channel. Please contact the administrator."

# 規模別の専用チャンネル案内（discord_channel_invite）。顧客向けのため英語（規模ラベルも英語）
CHANNEL_INVITE_TEMPLATE = (
    "[Notice] Here is the dedicated channel for our {scale_label} customers.\n"
    "Check the channel below for the latest news and special offers \U0001F447\n"
    "<#{channel_id}>"
)
# estimated_scale → 顧客に見せる英語ラベル（小口 / 一般 / 大口）
CHANNEL_INVITE_SCALE_LABELS = {
    "Small": "small-volume",
    "Medium": "regular",
    "Large": "large-volume",
}


def channel_invite_message(estimated_scale: str, channel_id: str) -> str:
    """規模別チャンネル案内の本文を返す。未知の規模は値をそのままラベルにする。"""
    scale_label = CHANNEL_INVITE_SCALE_LABELS.get(estimated_scale, estimated_scale)
    return CHANNEL_INVITE_TEMPLATE.format(scale_label=scale_label, channel_id=channel_id)


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
