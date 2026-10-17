"""閲覧者の Discord 受付の文面（SSOT・英語）。bot_texts.py（顧客用チケット）とは別。

利用箇所:
  - discord_gateway/client.py（custom_id の接頭辞の判定）
  - discord_gateway/viewer_trial.py（ボタン・小窓・応答・部屋の投稿）
  - viewer_discord_cli.py（受付の部屋へのボタン投稿）
"""
from __future__ import annotations

VIEWER_CUSTOM_ID_PREFIX = "viewer_trial_"
OPEN_BUTTON_CUSTOM_ID = "viewer_trial_open"
CODE_MODAL_CUSTOM_ID = "viewer_trial_code"
CODE_INPUT_CUSTOM_ID = "viewer_trial_code_input"

RECEPTION_MESSAGE = (
    "Start your free trial of the inventory viewer. "
    "Press the button below and enter the signup code shown after you applied."
)
OPEN_BUTTON_LABEL = "Enter signup code"
CODE_MODAL_TITLE = "Signup code"
CODE_INPUT_LABEL = "Signup code (e.g. ABCD-EFGH-JKMN-PQRS)"

WRONG_SERVER = "This button can't be used on this server."
CODE_INVALID = "The code is wrong or has expired. Please check it and try again."
TOO_MANY_ATTEMPTS = "Too many attempts. Please wait an hour and try again."
TRY_LATER = "Something went wrong. Please wait a while and try again."
DISCORD_ALREADY_LINKED = "This Discord account is already linked to another signup."
YOUR_ROOM = "Your private channel: <#{channel_id}>"
ROOM_WELCOME = (
    "Welcome! Your trial of the inventory viewer has started.\n"
    "URL: https://app.salesanchor.jp/viewer/\n"
    "Email: {email}\n"
    "Initial password: {password}\n"
    "Please change your password at your first login."
)
ROOM_RECREATED = (
    "Your channel was recreated.\n"
    "URL: https://app.salesanchor.jp/viewer/\n"
    "Email: {email}\n"
    "If you have forgotten your password, use “Forgot password” on the login page."
)


def reception_message_payload() -> dict:
    """受付の部屋に置くボタン付きメッセージの Discord REST ペイロード（呼び出しごとに新しい dict）。"""
    return {
        "content": RECEPTION_MESSAGE,
        "components": [
            {
                "type": 1,  # ActionRow
                "components": [
                    {
                        "type": 2,  # Button
                        "style": 1,  # Primary
                        "label": OPEN_BUTTON_LABEL,
                        "custom_id": OPEN_BUTTON_CUSTOM_ID,
                    }
                ],
            }
        ],
    }
