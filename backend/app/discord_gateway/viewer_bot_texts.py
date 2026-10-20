"""閲覧者の Discord 受付の文面（SSOT・日本語。PO 決定 2026-10-17）。bot_texts.py（顧客用チケット・英語既定）とは別。

利用箇所:
  - discord_gateway/client.py（custom_id の接頭辞の判定）
  - discord_gateway/viewer_trial.py（ボタン・小窓・応答・部屋の投稿）
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
ROOM_WELCOME = (
    "在庫集計ツールのお試しありがとうございます😊\n"
    "下記のURLにログイン情報を入力してご利用ください。\n"
    "URL: https://app.salesanchor.jp/viewer/\n"
    "メールアドレス: {email}\n"
    "初期パスワード: `{password}`"
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

ROOM_TOPIC = "在庫集計ツールのお試し（番号 {viewer_id}）"


# ── 手で送る案内文（ADR-1019 段10 便1。管理画面のコピーボタンが API 経由で受け取る） ──
SIGNUP_URL = "https://app.salesanchor.jp/viewer/?openExternalBrowser=1#signup"
SIGNUP_REQUEST = (
    "在庫集計ツールのお試しのご案内です😊\n"
    "下記のページから、メールアドレスと LINE の表示名を入力してお申し込みください。\n"
    "申込ページ：{signup_url}\n"
    "お申し込みのあと画面に出る「申込コード」と「Discord に参加する」ボタンで、"
    "Discord の受付にお進みください。"
)
REISSUE_NOTICE = (
    "{line_name}さん、申込コードを作り直しました。\n"
    "申込コード：{code}（{expires}まで有効）\n"
    "Discord への招待：{invite_url}\n"
    "Discord の受付の部屋で「申込コードを入れる」ボタンを押し、このコードを入れてください。"
)
REISSUE_NOTICE_NO_INVITE = (
    "{line_name}さん、申込コードを作り直しました。\n"
    "申込コード：{code}（{expires}まで有効）\n"
    "Discord の受付の部屋で「申込コードを入れる」ボタンを押し、このコードを入れてください。"
)

# ── 操作の直後に部屋へ自動で送るお知らせ（段10 便2。停止の解除は文面なし） ──
NOTICE_EXTENDED = "お試し期間を {until_date} まで延長しました😊"
NOTICE_ACTIVATED = "本登録が完了しました。引き続きご利用ください😊"
NOTICE_SUSPENDED = "ご利用を停止しました。ご不明な点は、この部屋でお知らせください。"

# ── 期限の前日に部屋へ自動で送る面談のお願い（段10 便3） ──
INTERVIEW_REQUEST = (
    "お試し期間は {expires_date} で終わります。\n"
    "ご利用の感想やこれからのご利用についてお話しするため、短い面談をお願いできますでしょうか😊\n"
    "ご都合のよい日時を、この部屋に3つほどお送りください。"
)

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


def signup_request_text() -> str:
    """① 申込のお願い（手で送る）。"""
    return SIGNUP_REQUEST.format(signup_url=SIGNUP_URL)


def reissue_notice_text(
    line_name: str | None,
    code: str,
    expires_at: datetime,
    invite_url: str | None,
) -> str:
    """② 申込コード作り直しの案内（手で送る）。LINE名が無ければ「〇〇さん、」を付けない。"""
    template = REISSUE_NOTICE if invite_url else REISSUE_NOTICE_NO_INVITE
    text = template.format(
        line_name=(line_name or "").strip(),
        code=code,
        expires=format_jst_datetime(expires_at),
        invite_url=external_browser_url(invite_url) if invite_url else "",
    )
    if not (line_name or "").strip():
        text = text.removeprefix("さん、")
    return text


def interview_request_text(expires_at: datetime) -> str:
    """③ 期限の前日に部屋へ送る面談のお願い。"""
    return INTERVIEW_REQUEST.format(expires_date=format_jst_date(expires_at))
