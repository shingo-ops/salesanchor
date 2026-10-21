"""閲覧者の Discord 受付の部品の文言（日本語。PO 決定 2026-10-17）。bot_texts.py（顧客用チケット・英語既定）とは別。

お客様へ送る案内文 9件（申込のお願い・申込コードの作り直し2件・部屋のはじめの案内・部屋の作り直しの案内・
延長/本登録/停止のお知らせ・面談のお願い）はここに持たない。正本は DB（public.viewer_message_templates。
鍵と差し込み項目は services/viewer_message_templates.py の台帳。ADR-1019 段11 便2 で移した）。

ここに残すもの（段11 の対象外）:
  - 受付のボタン付きメッセージ RECEPTION_MESSAGE、ボタン名・小窓の題・エラーの返事、YOUR_ROOM、ROOM_TOPIC
  - SIGNUP_URL、external_browser_url、format_jst_date、format_jst_datetime（台帳側・画面側が差し込みに使う）

利用箇所:
  - discord_gateway/client.py（custom_id の接頭辞の判定）
  - discord_gateway/viewer_trial.py（ボタン・小窓・応答）
  - viewer_discord_cli.py（受付の部屋へのボタン投稿）
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

VIEWER_CUSTOM_ID_PREFIX = "viewer_trial_"
OPEN_BUTTON_CUSTOM_ID = "viewer_trial_open"
CODE_MODAL_CUSTOM_ID = "viewer_trial_code"
CODE_INPUT_CUSTOM_ID = "viewer_trial_code_input"

RECEPTION_MESSAGE = (
    "在庫集計ツールのお試しを開始する場合は、下のボタンを押してください。"
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

ROOM_TOPIC = "在庫集計ツールのお試し（番号 {viewer_id}）"


# ── 申込ページの URL（申込のお願いの {signup_url} に API が入れる。文面そのものは DB） ──
SIGNUP_URL = "https://app.salesanchor.jp/viewer/?openExternalBrowser=1#signup"

_JST = timezone(timedelta(hours=9))


def external_browser_url(url: str) -> str:
    """LINE アプリ内ブラウザでなく外部ブラウザで開かせる目印 openExternalBrowser=1 を付ける。

    クエリが無ければ ?、あれば & で付ける。既に付いていれば何もしない。# があれば # の前に入れる。
    """
    base, sep, fragment = url.partition("#")
    if "openExternalBrowser=" in base:
        return url
    base += ("&" if "?" in base else "?") + "openExternalBrowser=1"
    return base + sep + fragment


def _to_jst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # naive は UTC とみなす
    return dt.astimezone(_JST)


def format_jst_date(dt: datetime) -> str:
    """JST の「M月D日」（ゼロ埋めなし）。"""
    j = _to_jst(dt)
    return f"{j.month}月{j.day}日"


def format_jst_datetime(dt: datetime) -> str:
    """JST の「M月D日 HH:MM」（月日はゼロ埋めなし、時分は2桁）。"""
    j = _to_jst(dt)
    return f"{j.month}月{j.day}日 {j.hour:02d}:{j.minute:02d}"
