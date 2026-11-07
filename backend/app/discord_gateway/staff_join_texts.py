"""スタッフ自己登録の Discord 受付の文言（日本語。ADR-1068・設計 docs/handoff/staff-self-registration/design.md §4-3）。

viewer_bot_texts.py（閲覧者の受付）と同じ型。自社サーバーのスタッフ用で、閲覧者・顧客用チケットとは別。

利用箇所:
  - discord_gateway/client.py（custom_id の前置きの判定）
  - discord_gateway/staff_join.py（ボタン・小窓・応答）
  - staff_join_discord_cli.py（受付の部屋へのボタン投稿）
"""
from __future__ import annotations

import os

CUSTOM_ID_PREFIX = "staff_join_"
OPEN_BUTTON_CUSTOM_ID = "staff_join_open"
CODE_MODAL_CUSTOM_ID = "staff_join_code"
CODE_INPUT_CUSTOM_ID = "staff_join_code_input"

RECEPTION_MESSAGE = (
    "スタッフとして登録する場合は、下のボタンを押して、登録番号を入れてください。"
)
OPEN_BUTTON_LABEL = "登録番号を入れる"
CODE_MODAL_TITLE = "登録番号"
CODE_INPUT_LABEL = "登録番号（例：ABCD-EFGH-JKMN-PQRS）"

WRONG_SERVER = "このボタンは、このサーバーでは使えません。"
ALREADY_REGISTERED = "すでに登録済みです。"
NOT_READY = "受付の準備ができていません。管理者に連絡してください。"
CODE_INVALID = "番号が違うか、期限が切れています。確かめてから、もう一度入れてください。"
TOO_MANY_ATTEMPTS = "試した回数が多すぎます。1時間ほど待ってから、もう一度お試しください。"
TRY_LATER = "うまくいきませんでした。しばらく待ってから、もう一度お試しください。"
ROOM_CREATED = "あなた専用の個室を作りました：<#{channel_id}>"
ROOM_FAILED = "個室を作れませんでした。管理者に連絡してください。"

# 部屋の説明（片付けが持ち主を探す目印）と名前
ROOM_TOPIC = "スタッフ登録（招待 {invite_id}）"
ROOM_NAME = "staff-join-{invite_id}"

_DEFAULT_FRONTEND_BASE_URL = "https://app.salesanchor.jp"

# 個室に出す文面。仮パスワードだけをバッククォートで囲む（スマホで長押しコピーするため）
ROOM_WELCOME = (
    "スタッフ登録が終わりました。最初のログインに使う情報です。\n"
    "メールアドレス: {email}\n"
    "仮パスワード: `{password}`\n"
    "ログインURL: {login_url}\n"
    "最初のログインで変更してください。"
)


def login_url() -> str:
    """staff_join.join_url と同じ環境変数の読み方（FRONTEND_BASE_URL。無ければ既定）。"""
    base = (os.getenv("FRONTEND_BASE_URL") or _DEFAULT_FRONTEND_BASE_URL).rstrip("/")
    return f"{base}/login"


def room_welcome(email: str, password: str) -> str:
    return ROOM_WELCOME.format(email=email, password=password, login_url=login_url())


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
