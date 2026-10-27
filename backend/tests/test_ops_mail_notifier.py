from __future__ import annotations

"""
ops_mail_notifier のユニットテスト（outage-recovery-watch 便3）。

テスト方針:
  - IMAP・Redis・httpx をすべてモックし、実際のネットワーク接続は発生しない。
  - 会員 ID・契約者名・メールアドレスは架空の値（XX000000・試験 太郎・support@sakura.ad.jp）だけを使う。
  - 本文の 2 行以外（会員 ID・契約者名）が Discord にもログにも出ないことをアサートする。
"""

import calendar
import email.header
import logging
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

import app.services.ops_mail_notifier as n

FIXED_NOW = float(calendar.timegm((2026, 10, 23, 0, 0, 0)))
WEBHOOK = "https://discord.example.com/webhook"
SUBJECT_OPS = "［緊急］さくらのVPS東京・大阪・石狩リージョンのソフトウェアメンテナンスについて"
SCHEDULE = "2026年10月21日15時00分 - 2026年10月22日18時00分"
SCOPE = "さくらのVPS 東京・大阪・石狩リージョン"
BODY_TEXT = (
    "会員ID : XX000000\n"
    "ご契約者名 : 試験 太郎\n"
    "対象会員ID : XX000000\n"
    f"■作業日程 : {SCHEDULE}\n"
    f"■影響範囲 :　{SCOPE}\n"
    "その他の行です。\n"
)


def _hdr(text: str) -> str:
    return email.header.Header(text, "utf-8").encode()


def _header_bytes(from_: str, subject: str, date: str = "Wed, 21 Oct 2026 16:05:00 +0900") -> bytes:
    return f"From: {from_}\r\nSubject: {_hdr(subject)}\r\nDate: {date}\r\n\r\n".encode()


def _full_bytes(from_: str, subject: str, body: str) -> bytes:
    m = MIMEText(body, "plain", "utf-8")
    m["From"] = from_
    m["Subject"] = _hdr(subject)
    return m.as_bytes()


def _make_imap(messages: dict[bytes, tuple[bytes, bytes]], search_status: str = "OK"):
    """messages: uid -> (ヘッダーの bytes, 本文取得で返す bytes)。"""
    conn = MagicMock()
    conn.response.return_value = ("UIDVALIDITY", [b"777"])
    calls: list[tuple] = []

    def uid(cmd, *args):
        calls.append((cmd, *args))
        if cmd == "search":
            return search_status, [b" ".join(messages.keys())]
        if cmd == "fetch":
            uid_b, what = args
            head, body = messages[uid_b]
            data = body if what == n._BODY_FETCH else head
            return "OK", [(b"1 (BODY[] {1}", data), b")"]
        raise AssertionError(cmd)

    conn.uid.side_effect = uid
    conn.calls = calls
    return conn


def _run(conn, redis_client=None, post_status: int = 204):
    redis_client = redis_client or MagicMock(exists=MagicMock(return_value=0))
    resp = MagicMock(status_code=post_status, text="x")
    with (
        patch.object(n, "_IMAP_HOST", "imap.example.com"),
        patch.object(n, "_IMAP_USER", "ops@example.com"),
        patch.object(n, "_IMAP_PASSWORD", "pw-secret"),
        patch.object(n, "_DISCORD_WEBHOOK", WEBHOOK),
        patch("imaplib.IMAP4_SSL", return_value=conn),
        patch.object(n, "_get_redis", return_value=redis_client),
        patch("httpx.post", return_value=resp) as post,
    ):
        result = n.check_and_notify()
    return result, redis_client, post


def _fetch_whats(conn) -> list[str]:
    return [c[2] for c in conn.calls if c[0] == "fetch"]


# 1
def test_is_sakura() -> None:
    assert n._is_sakura("さくら <support@sakura.ad.jp>")
    assert n._is_sakura("domain@SAKURA.AD.JP")
    for bad in ("x@xsakura.ad.jp", "x@sakura.ad.jp.example.com", "support@sakura.ad.jp.evil", "not-an-address"):
        assert not n._is_sakura(bad)
    raw = email.header.Header("さくらインターネット株式会社, サポート", "utf-8").encode() + " <support@sakura.ad.jp>"
    assert n._is_sakura(raw)


# 2
def test_is_ops_subject() -> None:
    assert n._is_ops_subject(SUBJECT_OPS)
    assert not n._is_ops_subject("クレジットカード決済のお知らせ")


# 3
def test_since_date() -> None:
    assert n._since_date(calendar.timegm((2026, 10, 23, 0, 0, 0))) == "16-Oct-2026"
    assert n._since_date(calendar.timegm((2026, 1, 3, 0, 0, 0))) == "27-Dec-2025"


# 4
def test_extract_lines_basic() -> None:
    assert n._extract_lines(BODY_TEXT) == (SCHEDULE, SCOPE)


# 5
def test_extract_lines_fullwidth_missing_and_truncate() -> None:
    assert n._extract_lines("■作業日時　：　A日時\n■影響範囲　：　B範囲\n") == ("A日時", "B範囲")
    assert n._extract_lines("関係ない行\n") == (None, None)
    s, _ = n._extract_lines("■作業日時 : " + "あ" * 300)
    assert s is not None and len(s) == 200


# 6b
def test_extract_lines_strips_and_empty_is_none() -> None:
    assert n._extract_lines("■作業日時 :    \n■影響範囲 :   \n") == (None, None)
    assert n._extract_lines("■作業日時 :\r\n■影響範囲 :\r\n会員ID : XX000000\r\n") == (None, None)
    assert n._extract_lines("■作業日時 :  A日時  \r\n") == ("A日時", None)


# 6
def test_extract_lines_does_not_pick_member_lines() -> None:
    text = "会員ID : XX000000\nご契約者名 : 試験 太郎\n対象会員ID : XX000000\n"
    assert n._extract_lines(text) == (None, None)
    # 値が空の行で次の行（会員 ID など）を拾わない
    assert n._extract_lines("■影響範囲 :\n会員ID : XX000000\n")[1] is None


# 7
def test_body_text_variants() -> None:
    jp = MIMEText("作業日程 : テスト", "plain", "iso-2022-jp").as_bytes()
    assert "テスト" in n._body_text(jp)

    from email.mime.multipart import MIMEMultipart

    mp = MIMEMultipart("alternative")
    mp.attach(MIMEText("プレーン本文", "plain", "utf-8"))
    mp.attach(MIMEText("<p>html</p>", "html", "utf-8"))
    assert "プレーン本文" in n._body_text(mp.as_bytes())

    assert "abc" in n._body_text(b"From: a@b\r\nSubject: s\r\n\r\nabc\r\n")

    full = _full_bytes("support@sakura.ad.jp", "s", "あ" * 40000)
    assert isinstance(n._body_text(full[:65536]), str)

    broken = n._body_text(b"\xff\xfe broken")
    assert "broken" in broken and "\ufffd" in broken
    with patch("email.message_from_bytes", side_effect=ValueError("boom")):
        assert n._body_text(b"x") == ""
    bad_charset = b"Content-Type: text/plain; charset=nosuch-cs\r\n\r\nxyz\r\n"
    assert "xyz" in n._body_text(bad_charset)


# 8
def test_build_content() -> None:
    expected = (
        "📢 さくらからの点検・障害のお知らせ\n"
        f"件名: {SUBJECT_OPS}\n"
        f"作業日時: {SCHEDULE}\n"
        f"影響範囲: {SCOPE}\n"
        "受信: Wed, 21 Oct 2026 16:05:00 +0900\n"
        "本文は業務用メールで確かめてください"
    )
    assert n._build_content(SUBJECT_OPS, SCHEDULE, SCOPE, "Wed, 21 Oct 2026 16:05:00 +0900") == expected
    no_sched = n._build_content("s", None, SCOPE, "d")
    assert "作業日時: 本文から読み取れませんでした（業務用メールで確かめてください）" in no_sched
    no_scope = n._build_content("s", SCHEDULE, None, "d")
    assert "影響範囲" not in no_scope
    assert "受信: 不明" in n._build_content("s", SCHEDULE, SCOPE, "")


# 9
def test_unconfigured_does_not_connect() -> None:
    with (
        patch.object(n, "_IMAP_HOST", "imap.example.com"),
        patch.object(n, "_IMAP_USER", "ops@example.com"),
        patch.object(n, "_IMAP_PASSWORD", "pw"),
        patch.object(n, "_DISCORD_WEBHOOK", ""),
        patch("imaplib.IMAP4_SSL") as imap,
    ):
        assert n.check_and_notify() == 0
    imap.assert_not_called()


# 10
def test_redis_none_does_not_connect_or_post() -> None:
    with (
        patch.object(n, "_IMAP_HOST", "imap.example.com"),
        patch.object(n, "_IMAP_USER", "ops@example.com"),
        patch.object(n, "_IMAP_PASSWORD", "pw"),
        patch.object(n, "_DISCORD_WEBHOOK", WEBHOOK),
        patch.object(n, "_get_redis", return_value=None),
        patch("imaplib.IMAP4_SSL") as imap,
        patch("httpx.post") as post,
    ):
        assert n.check_and_notify() == 0
    imap.assert_not_called()
    post.assert_not_called()


# 11
def test_sakura_ops_mail_is_posted_once() -> None:
    conn = _make_imap(
        {b"5": (_header_bytes("さくら <support@sakura.ad.jp>", SUBJECT_OPS),
                _full_bytes("support@sakura.ad.jp", SUBJECT_OPS, BODY_TEXT))}
    )
    result, r, post = _run(conn)
    assert result == 1
    post.assert_called_once()
    payload = post.call_args.kwargs["json"]
    assert payload["allowed_mentions"] == {"parse": []}
    content = payload["content"]
    assert SCHEDULE in content and SCOPE in content and SUBJECT_OPS in content
    assert "XX000000" not in content and "試験 太郎" not in content and "その他の行" not in content
    r.set.assert_any_call("ops_mail:notified:777:5", "1", ex=30 * 24 * 60 * 60)
    keys = [c.args[0] for c in r.set.call_args_list]
    assert n.LAST_SAKURA_MAIL_TS_KEY in keys and n.LAST_POLL_OK_TS_KEY in keys


# 12
def test_sakura_non_ops_mail_not_posted_nor_body_read() -> None:
    conn = _make_imap(
        {b"6": (_header_bytes("support@sakura.ad.jp", "クレジットカード決済のお知らせ"), b"")}
    )
    result, r, post = _run(conn)
    assert result == 0
    post.assert_not_called()
    assert n._BODY_FETCH not in _fetch_whats(conn)
    r.set.assert_any_call("ops_mail:notified:777:6", "1", ex=30 * 24 * 60 * 60)
    sakura_sets = [c for c in r.set.call_args_list if c.args[0] == n.LAST_SAKURA_MAIL_TS_KEY]
    assert any("nx" not in c.kwargs for c in sakura_sets)


# 13
def test_non_sakura_mail_not_posted_nor_body_read() -> None:
    conn = _make_imap({b"7": (_header_bytes("someone@example.com", SUBJECT_OPS), b"")})
    result, r, post = _run(conn)
    assert result == 0
    post.assert_not_called()
    assert n._BODY_FETCH not in _fetch_whats(conn)
    r.set.assert_any_call("ops_mail:notified:777:7", "1", ex=30 * 24 * 60 * 60)
    sakura_sets = [c for c in r.set.call_args_list if c.args[0] == n.LAST_SAKURA_MAIL_TS_KEY]
    assert len(sakura_sets) == 1 and sakura_sets[0].kwargs.get("nx") is True


# 14
def test_post_failure_does_not_mark() -> None:
    conn = _make_imap(
        {b"8": (_header_bytes("support@sakura.ad.jp", SUBJECT_OPS),
                _full_bytes("support@sakura.ad.jp", SUBJECT_OPS, BODY_TEXT))}
    )
    result, r, post = _run(conn, post_status=500)
    assert result == 0
    post.assert_called_once()
    assert all(c.args[0] != "ops_mail:notified:777:8" for c in r.set.call_args_list)
    # 次の回に同じ uid でもう一度送る
    result2, _, post2 = _run(_make_imap(
        {b"8": (_header_bytes("support@sakura.ad.jp", SUBJECT_OPS),
                _full_bytes("support@sakura.ad.jp", SUBJECT_OPS, BODY_TEXT))}
    ))
    assert result2 == 1
    post2.assert_called_once()


# 15
def test_notified_uid_not_fetched_and_search_uses_since() -> None:
    conn = _make_imap({b"9": (b"", b"")})
    redis_client = MagicMock(exists=MagicMock(return_value=1))
    with patch("app.services.ops_mail_notifier.time.time", return_value=FIXED_NOW):
        result, _, post = _run(conn, redis_client=redis_client)
    assert result == 0
    assert _fetch_whats(conn) == []
    post.assert_not_called()
    search = [c for c in conn.calls if c[0] == "search"][0]
    assert search[2] == "SINCE" and search[1] is None
    assert search[3] == n._since_date(FIXED_NOW) == "16-Oct-2026"


# 16
def test_logs_do_not_leak(caplog) -> None:
    conn = _make_imap(
        {
            b"1": (_header_bytes("support@sakura.ad.jp", SUBJECT_OPS),
                   _full_bytes("support@sakura.ad.jp", SUBJECT_OPS, BODY_TEXT)),
            b"2": (_header_bytes("someone@example.com", "別の件名"), b""),
        }
    )
    with caplog.at_level(logging.DEBUG):
        _run(conn)
    text = caplog.text
    assert "[ops_mail] notified uid=1" in text
    assert "[ops_mail] skipped uid=2 reason=not_sakura" in text
    assert "[ops_mail] done notified=1" in text
    for secret in (SUBJECT_OPS, "別の件名", "support@sakura.ad.jp", "someone@example.com", "XX000000", "試験 太郎", "pw-secret", WEBHOOK):
        assert secret not in text


# 17
def test_imap_connection_has_timeout() -> None:
    conn = _make_imap({b"3": (b"", b"")})
    redis_client = MagicMock(exists=MagicMock(return_value=1))
    with (
        patch.object(n, "_IMAP_HOST", "imap.example.com"),
        patch.object(n, "_IMAP_USER", "ops@example.com"),
        patch.object(n, "_IMAP_PASSWORD", "pw"),
        patch.object(n, "_DISCORD_WEBHOOK", WEBHOOK),
        patch("imaplib.IMAP4_SSL", return_value=conn) as imap,
        patch.object(n, "_get_redis", return_value=redis_client),
    ):
        n.check_and_notify()
    assert imap.call_args.kwargs.get("timeout") == 30


# 18
def test_header_fetch_unexpected_response_logs_uid_only(caplog) -> None:
    conn = _make_imap({b"4": (b"", b"")})
    orig = conn.uid.side_effect

    def uid(cmd, *args):
        if cmd == "fetch":
            return "OK", [b")"]
        return orig(cmd, *args)

    conn.uid.side_effect = uid
    with caplog.at_level(logging.DEBUG):
        result, _, post = _run(conn)
    assert result == 0
    post.assert_not_called()
    assert "[ops_mail] header fetch unexpected response uid=4" in caplog.text
