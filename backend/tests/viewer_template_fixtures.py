"""閲覧者向け文面テンプレート 9 件の「初期の本文」（テスト専用。送る側のコードにはもう持たない）。

本番の初期値は便1 の seed で DB に入った。ここはテストが DB 読みをモックする／PG に入れるための写し。
"""
from __future__ import annotations

DEFAULT_BODIES: dict[str, str] = {
    "signup_request": (
        "在庫集計ツールのお試しのご案内です😊\n"
        "下記のページから、メールアドレスと LINE の表示名を入力してお申し込みください。\n"
        "申込ページ：{signup_url}\n"
        "お申し込みのあと画面に出る「申込コード」と「Discord に参加する」ボタンで、"
        "Discord の受付にお進みください。"
    ),
    "reissue_notice": (
        "{line_name}さん、申込コードを作り直しました。\n"
        "申込コード：{code}（{expires}まで有効）\n"
        "Discord への招待：{invite_url}\n"
        "Discord の受付の部屋で「申込コードを入れる」ボタンを押し、このコードを入れてください。"
    ),
    "reissue_notice_no_invite": (
        "{line_name}さん、申込コードを作り直しました。\n"
        "申込コード：{code}（{expires}まで有効）\n"
        "Discord の受付の部屋で「申込コードを入れる」ボタンを押し、このコードを入れてください。"
    ),
    "room_welcome": (
        "在庫集計ツールのお試しありがとうございます😊\n"
        "下記のURLにログイン情報を入力してご利用ください。\n"
        "URL: https://app.salesanchor.jp/viewer/\n"
        "メールアドレス: {email}\n"
        "初期パスワード: `{password}`"
    ),
    "room_recreated": (
        "部屋を作り直しました。\n"
        "URL: https://app.salesanchor.jp/viewer/\n"
        "メールアドレス: {email}\n"
        "パスワードを忘れたときは、ログイン画面の「パスワードを忘れた」から再発行してください。"
    ),
    "notice_extended": "お試し期間を {until_date} まで延長しました😊",
    "notice_activated": "本登録が完了しました。引き続きご利用ください😊",
    "notice_suspended": "ご利用を停止しました。ご不明な点は、この部屋でお知らせください。",
    "interview_request": (
        "お試し期間は {expires_date} で終わります。\n"
        "ご利用の感想やこれからのご利用についてお話しするため、短い面談をお願いできますでしょうか😊\n"
        "ご都合のよい日時を、この部屋に3つほどお送りください。"
    ),
}


def make_load_body(bodies: dict[str, str | None] | None = None):
    """vmt.load_body の代わり（AsyncMock の side_effect 用）。bodies に無い鍵は DEFAULT_BODIES、None 指定は行なし。"""
    merged: dict[str, str | None] = {**DEFAULT_BODIES, **(bodies or {})}

    async def _load(db, key):  # noqa: ARG001
        return merged.get(key)

    return _load
