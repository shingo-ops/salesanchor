"""閲覧者の Discord 受付の文面（SSOT・日本語。PO 決定 2026-10-17）。bot_texts.py（顧客用チケット・英語既定）とは別。

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
    "在庫一覧のお試しを始められます。"
    "下のボタンを押して、お申込みのあとに画面に出たコードを入れてください。"
)
OPEN_BUTTON_LABEL = "申込コードを入れる"
CODE_MODAL_TITLE = "申込コード"
CODE_INPUT_LABEL = "申込コード（例：ABCD-EFGH-JKMN-PQRS）"

WRONG_SERVER = "このボタンは、このサーバーでは使えません。"
CODE_INVALID = "コードが違うか、期限が切れています。確かめてから、もう一度入れてください。"
TOO_MANY_ATTEMPTS = "試した回数が多すぎます。1時間ほど待ってから、もう一度お試しください。"
TRY_LATER = "うまくいきませんでした。しばらく待ってから、もう一度お試しください。"
DISCORD_ALREADY_LINKED = "この Discord アカウントは、別のお申込みですでに使われています。"
YOUR_ROOM = "あなた専用の部屋：<#{channel_id}>"
ROOM_WELCOME = (
    "ようこそ。在庫一覧のお試しが始まりました。\n"
    "URL: https://app.salesanchor.jp/viewer/\n"
    "メールアドレス: {email}\n"
    "初期パスワード: {password}\n"
    "最初のログインのときに、パスワードを変えてください。"
)
ROOM_RECREATED = (
    "部屋を作り直しました。\n"
    "URL: https://app.salesanchor.jp/viewer/\n"
    "メールアドレス: {email}\n"
    "パスワードを忘れたときは、ログイン画面の「パスワードを忘れた」から再発行してください。"
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
