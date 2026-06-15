from __future__ import annotations

"""
review_mail_notifier のユニットテスト。

テスト方針:
  - IMAP・Redis・httpx をすべてモックし、実際のネットワーク接続は発生しない。
  - セキュリティ要件（本文・oobCode・再設定リンクを Discord に投稿しない）を明示的にアサート。
  - Redis 不能時は Discord POST を呼ばないことをアサート（重複通知防止）。
"""

import email
import email.header
from unittest.mock import MagicMock, patch

import app.services.review_mail_notifier as notifier

# ---------------------------------------------------------------------------
# ヘルパー: RFC 2047 エンコード済みヘッダ値の生成
# ---------------------------------------------------------------------------

def _encode_header(text: str, charset: str = "utf-8") -> str:
    h = email.header.Header(text, charset)
    return str(h)


def _make_raw_header(
    from_: str = "sender@example.com",
    subject: str = "Test Subject",
    date: str = "Sat, 14 Jun 2026 10:00:00 +0900",
) -> bytes:
    return (
        f"From: {from_}\r\n"
        f"Subject: {subject}\r\n"
        f"Date: {date}\r\n\r\n"
    ).encode()


# ---------------------------------------------------------------------------
# _decode_mime_header
# ---------------------------------------------------------------------------

class TestDecodeMimeHeader:
    def test_plain_ascii(self) -> None:
        assert notifier._decode_mime_header("Hello") == "Hello"

    def test_utf8_encoded(self) -> None:
        encoded = _encode_header("テスト件名", "utf-8")
        result = notifier._decode_mime_header(encoded)
        assert result == "テスト件名"

    def test_iso2022jp_encoded(self) -> None:
        encoded = _encode_header("テスト", "iso-2022-jp")
        result = notifier._decode_mime_header(encoded)
        assert result == "テスト"

    def test_empty_string(self) -> None:
        assert notifier._decode_mime_header("") == ""


# ---------------------------------------------------------------------------
# _build_discord_content: セキュリティ要件
# ---------------------------------------------------------------------------

class TestBuildDiscordContent:
    def test_contains_from_subject_date(self) -> None:
        content = notifier._build_discord_content(
            from_addr="sender@example.com",
            subject="テスト件名",
            date_str="Sat, 14 Jun 2026 10:00:00 +0900",
        )
        assert "sender@example.com" in content
        assert "テスト件名" in content
        assert "Sat, 14 Jun 2026 10:00:00 +0900" in content

    def test_contains_webmail_url(self) -> None:
        with patch.object(notifier, "_WEBMAIL_URL", "https://webmail.example.com/"):
            content = notifier._build_discord_content("f@e.com", "sub", "date")
        assert "https://webmail.example.com/" in content

    def test_no_body_in_content(self) -> None:
        """メール本文は絶対に含まれてはならない。"""
        mail_body = "This is the email body with sensitive content"
        content = notifier._build_discord_content("f@e.com", "sub", "date")
        assert mail_body not in content

    def test_no_firebase_reset_link(self) -> None:
        """Firebase パスワード再設定リンクは含まれてはならない。"""
        reset_link = "https://accounts.google.com/signin/action?oobCode=abc123xyz"
        content = notifier._build_discord_content("f@e.com", "sub", "date")
        assert reset_link not in content
        assert "oobCode=abc123" not in content

    def test_no_oobcode_value_from_body(self) -> None:
        """件名ではなくメール本文の oobCode 値は出てこない（本文を読まない設計）。
        件名に "oobCode" という文字が含まれる場合は件名の一部として表示されるが、
        実際のコード値（乱数）はメール本文にのみ存在するため取得しない。"""
        # 本文にのみ存在するはずの実際のコード値（件名には入らない長い乱数）
        actual_oob_code_value = "xK9mP2rT5uW8nQ1vB4cD7eF0gH3iJ6kL"
        content = notifier._build_discord_content(
            "noreply@firebase.com",
            "パスワードのリセット",  # 件名にoobCodeは含まない
            "date",
        )
        assert actual_oob_code_value not in content

    def test_subject_truncated_at_200_chars(self) -> None:
        long_subject = "A" * 300
        content = notifier._build_discord_content("f@e.com", long_subject, "date")
        assert "A" * 200 in content
        assert "A" * 201 not in content

    def test_from_truncated_at_300_chars(self) -> None:
        long_from = "B" * 400
        content = notifier._build_discord_content(long_from, "sub", "date")
        assert "B" * 300 in content
        assert "B" * 301 not in content

    def test_imap_fetch_uses_peek_header_only(self) -> None:
        """IMAP fetch コマンドが BODY.PEEK[HEADER.FIELDS] のみを要求することを確認する。
        BODY[] や BODY[TEXT] が使われると本文が取得され、セキュリティ違反となる。"""
        raw_header = _make_raw_header()
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"1"]),
            (None, [(b"1 ...", raw_header)]),
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/wh"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post", return_value=mock_resp),
        ):
            notifier.check_and_notify()

        # fetch 呼び出しの引数を確認
        fetch_calls = [c for c in mock_imap.uid.call_args_list if c[0][0] == "fetch"]
        assert len(fetch_calls) == 1
        fetch_arg = fetch_calls[0][0][2]
        assert "BODY.PEEK[HEADER.FIELDS" in fetch_arg
        assert "BODY[]" not in fetch_arg
        assert "BODY[TEXT]" not in fetch_arg


# ---------------------------------------------------------------------------
# _post_discord: webhook 挙動
# ---------------------------------------------------------------------------

class TestPostDiscord:
    def test_no_op_when_webhook_unset(self) -> None:
        """webhook 未設定時は Discord POST を呼ばず False を返す。"""
        with (
            patch.object(notifier, "_DISCORD_WEBHOOK", ""),
            patch("httpx.post") as mock_post,
        ):
            result = notifier._post_discord("test message")
        assert result is False
        mock_post.assert_not_called()

    def test_returns_true_on_success(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        with (
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("httpx.post", return_value=mock_resp),
        ):
            result = notifier._post_discord("test")
        assert result is True

    def test_returns_false_on_http_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"
        with (
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("httpx.post", return_value=mock_resp),
        ):
            result = notifier._post_discord("test")
        assert result is False

    def test_returns_false_on_network_error(self) -> None:
        with (
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("httpx.post", side_effect=Exception("connection refused")),
        ):
            result = notifier._post_discord("test")
        assert result is False


# ---------------------------------------------------------------------------
# check_and_notify: 統合ケース（IMAP・Redis をモック）
# ---------------------------------------------------------------------------

class TestCheckAndNotify:
    def test_unconfigured_returns_zero(self) -> None:
        with (
            patch.object(notifier, "_IMAP_HOST", ""),
            patch.object(notifier, "_IMAP_USER", ""),
            patch.object(notifier, "_IMAP_PASSWORD", ""),
        ):
            assert notifier.check_and_notify() == 0

    def test_imap_connection_failure_returns_zero(self) -> None:
        mock_redis = MagicMock()
        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch("imaplib.IMAP4_SSL", side_effect=Exception("connection refused")),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
        ):
            result = notifier.check_and_notify()
        assert result == 0

    def test_redis_unavailable_skips_discord(self) -> None:
        """Redis 不能時は Discord POST を呼ばず 0 を返す（重複通知防止）。"""
        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_get_redis", return_value=None),
            patch("httpx.post") as mock_post,
        ):
            result = notifier.check_and_notify()

        assert result == 0
        mock_post.assert_not_called()

    def test_already_notified_uid_is_skipped(self) -> None:
        """通知済み UID は Discord POST を呼ばない（重複通知防止）。"""
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"1"]),  # search ALL → UID 1
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # 通知済み

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post") as mock_post,
        ):
            result = notifier.check_and_notify()

        assert result == 0
        mock_post.assert_not_called()

    def test_new_mail_triggers_discord_and_marks_redis(self) -> None:
        """新着メールは Discord に通知し、UID を Redis に記録する。"""
        raw_header = _make_raw_header()
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"42"]),
            (None, [(b"42 ...", raw_header)]),
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0  # 未通知
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post", return_value=mock_resp),
        ):
            result = notifier.check_and_notify()

        assert result == 1
        mock_redis.set.assert_called_once()
        set_key = mock_redis.set.call_args[0][0]
        assert set_key == "review_mail:notified:42"

    def test_duplicate_uid_not_notified_twice(self) -> None:
        """同一 UID が複数回 check_and_notify() されても Discord POST は 1 回のみ。"""
        raw_header = _make_raw_header()
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        # 1回目: 未通知 → 通知後に Redis に記録
        mock_redis = MagicMock()
        mock_redis.exists.side_effect = [0, 1]  # 1回目=未通知, 2回目=通知済み

        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"10"]),
            (None, [(b"10 ...", raw_header)]),
            (None, [b"10"]),  # 2回目の search
        ]

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post", return_value=mock_resp) as mock_post,
        ):
            first = notifier.check_and_notify()
            second = notifier.check_and_notify()

        assert first == 1
        assert second == 0
        assert mock_post.call_count == 1

    def test_discord_payload_has_no_body_or_sensitive_data(self) -> None:
        """Discord への POST payload にメール本文・oobCode・再設定リンクが含まれない。

        Firebase パスワード再設定メールを受信した場合でも、IMAP から取得するのは
        BODY.PEEK[HEADER.FIELDS] のみ（件名・差出人・日時）。
        メール本文に含まれる oobCode 値や再設定リンクは Discord に出ない。
        """
        raw_header = _make_raw_header(
            from_="noreply@firebase.com",
            subject="Password Reset for your account",
        )
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"99"]),
            (None, [(b"99 ...", raw_header)]),
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        captured_payload: list[dict] = []

        def capture_post(url: str, json: dict, timeout: float) -> MagicMock:
            captured_payload.append(json)
            return mock_resp

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post", side_effect=capture_post),
        ):
            notifier.check_and_notify()

        assert len(captured_payload) == 1
        content = captured_payload[0]["content"]

        # メール本文テキストは含まない（BODY は取得しないため）
        assert "email body" not in content.lower()
        # oobCode パラメータは含まない（本文から取得しないため）
        assert "oobCode=" not in content
        # Firebase 再設定リンク全体は含まない
        assert "https://accounts.google.com/signin" not in content
        # 通知の必要情報（差出人・件名）は含む
        assert "noreply@firebase.com" in content
        assert "Password Reset for your account" in content


# ---------------------------------------------------------------------------
# _parse_mention: メンション解析
# ---------------------------------------------------------------------------

class TestParseMention:
    def test_empty_string_returns_none(self) -> None:
        mention, am = notifier._parse_mention("")
        assert mention is None
        assert am == {"parse": []}

    def test_whitespace_only_returns_none(self) -> None:
        mention, am = notifier._parse_mention("   ")
        assert mention is None
        assert am == {"parse": []}

    def test_user_mention_valid(self) -> None:
        mention, am = notifier._parse_mention("<@1255555836776939692>")
        assert mention == "<@1255555836776939692>"
        assert am == {"parse": [], "users": ["1255555836776939692"]}

    def test_user_mention_with_exclamation(self) -> None:
        mention, am = notifier._parse_mention("<@!1255555836776939692>")
        assert mention == "<@!1255555836776939692>"
        assert am == {"parse": [], "users": ["1255555836776939692"]}

    def test_role_mention_valid(self) -> None:
        mention, am = notifier._parse_mention("<@&123456789012345678>")
        assert mention == "<@&123456789012345678>"
        assert am == {"parse": [], "roles": ["123456789012345678"]}

    def test_invalid_format_returns_none_with_warning(self, caplog) -> None:
        import logging
        with caplog.at_level(logging.WARNING):
            mention, am = notifier._parse_mention("@everyone")
        assert mention is None
        assert am == {"parse": []}
        assert "不正" in caplog.text

    def test_invalid_too_short_id(self) -> None:
        mention, am = notifier._parse_mention("<@12345>")
        assert mention is None

    def test_invalid_plain_text(self) -> None:
        mention, am = notifier._parse_mention("SomeText")
        assert mention is None

    def test_leading_trailing_whitespace_stripped(self) -> None:
        mention, am = notifier._parse_mention("  <@1255555836776939692>  ")
        assert mention == "<@1255555836776939692>"
        assert am["users"] == ["1255555836776939692"]


# ---------------------------------------------------------------------------
# _build_discord_content: メンション付きメッセージ
# ---------------------------------------------------------------------------

class TestBuildDiscordContentMention:
    def test_mention_prepended_to_content(self) -> None:
        content = notifier._build_discord_content(
            "f@e.com", "sub", "date", mention="<@1255555836776939692>"
        )
        assert content.startswith("<@1255555836776939692>\n")

    def test_no_mention_when_none(self) -> None:
        content = notifier._build_discord_content("f@e.com", "sub", "date", mention=None)
        assert not content.startswith("<@")
        assert content.startswith("📩")

    def test_subject_in_mention_does_not_fire(self) -> None:
        """件名に @everyone や <@999> が含まれても allowed_mentions で制御する。
        content 文字列に @everyone が含まれること自体は許容（Discord 側で制御）。"""
        content = notifier._build_discord_content(
            "f@e.com", "@everyone big sale", "date", mention=None
        )
        assert "@everyone big sale" in content  # 件名は表示される


# ---------------------------------------------------------------------------
# _post_discord: allowed_mentions ペイロード
# ---------------------------------------------------------------------------

class TestPostDiscordAllowedMentions:
    def test_allowed_mentions_in_payload(self) -> None:
        """allowed_mentions が Discord POST payload に含まれる。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        captured: list[dict] = []

        def capture(url, json, timeout):
            captured.append(json)
            return mock_resp

        with (
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/wh"),
            patch("httpx.post", side_effect=capture),
        ):
            notifier._post_discord("test", allowed_mentions={"parse": [], "users": ["123"]})

        assert len(captured) == 1
        assert captured[0]["allowed_mentions"] == {"parse": [], "users": ["123"]}

    def test_default_allowed_mentions_parse_empty(self) -> None:
        """allowed_mentions 未指定時は parse:[] がデフォルト。"""
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        captured: list[dict] = []

        def capture(url, json, timeout):
            captured.append(json)
            return mock_resp

        with (
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/wh"),
            patch("httpx.post", side_effect=capture),
        ):
            notifier._post_discord("test")

        assert captured[0]["allowed_mentions"] == {"parse": []}


# ---------------------------------------------------------------------------
# check_and_notify: メンション統合ケース
# ---------------------------------------------------------------------------

class TestCheckAndNotifyMention:
    def test_mention_prepended_in_discord_payload(self) -> None:
        """REVIEW_MAIL_DISCORD_MENTION 設定時、Discord payload 先頭にメンションが付く。"""
        raw_header = _make_raw_header()
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"55"]),
            (None, [(b"55 ...", raw_header)]),
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        captured: list[dict] = []

        def capture(url, json, timeout):
            captured.append(json)
            return mock_resp

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/wh"),
            patch.object(notifier, "_DISCORD_MENTION", "<@1255555836776939692>"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post", side_effect=capture),
        ):
            result = notifier.check_and_notify()

        assert result == 1
        assert len(captured) == 1
        assert captured[0]["content"].startswith("<@1255555836776939692>\n")
        assert captured[0]["allowed_mentions"] == {"parse": [], "users": ["1255555836776939692"]}

    def test_invalid_mention_env_skips_mention(self) -> None:
        """REVIEW_MAIL_DISCORD_MENTION が不正形式のとき、メンションなしで通知する。"""
        raw_header = _make_raw_header()
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"56"]),
            (None, [(b"56 ...", raw_header)]),
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        captured: list[dict] = []

        def capture(url, json, timeout):
            captured.append(json)
            return mock_resp

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/wh"),
            patch.object(notifier, "_DISCORD_MENTION", "bad-mention-format"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
            patch("httpx.post", side_effect=capture),
        ):
            result = notifier.check_and_notify()

        assert result == 1
        assert not captured[0]["content"].startswith("<@")
        assert captured[0]["allowed_mentions"] == {"parse": []}
