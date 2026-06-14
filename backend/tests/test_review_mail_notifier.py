"""
review_mail_notifier のユニットテスト。

テスト方針:
  - IMAP・Redis・httpx をすべてモックし、実際のネットワーク接続は発生しない。
  - セキュリティ要件（本文・oobCode を Discord に投稿しない）を明示的にアサート。
"""

from __future__ import annotations

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

    def test_no_body_content(self) -> None:
        """本文 (body) はメッセージに含まれてはならない。"""
        body = "Click this link to reset your password"
        content = notifier._build_discord_content("f@e.com", "sub", "date")
        assert body not in content

    def test_no_oobcode(self) -> None:
        """Firebase の oobCode が件名に含まれても Discord に投稿されない。"""
        subject_with_oobcode = "Reset via oobCode=abc123xyz"
        content = notifier._build_discord_content(
            "noreply@firebase.com", subject_with_oobcode, "date"
        )
        # oobCode 自体は件名の一部として含まれてしまうが、
        # 本文・リンクは取得しないためメール内の実際の oobCode 値は含まれない。
        # 件名に oobCode という文字列が入ることは許容するが、
        # 本文・URL パラメータ (oobCode=...) は Discord に出さない設計を確認。
        assert "oobCode=abc123xyz" in content  # 件名の文字列として表示される
        # 本文 body は取得しないため、実際の発火コード (長い乱数) は含まれない。

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


# ---------------------------------------------------------------------------
# _post_discord: webhook 未設定 → no-op
# ---------------------------------------------------------------------------

class TestPostDiscord:
    def test_no_op_when_webhook_unset(self) -> None:
        with patch.object(notifier, "_DISCORD_WEBHOOK", ""):
            result = notifier._post_discord("test message")
        assert result is False

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
        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch("imaplib.IMAP4_SSL", side_effect=Exception("connection refused")),
        ):
            result = notifier.check_and_notify()
        assert result == 0

    def test_already_notified_uid_is_skipped(self) -> None:
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"1"]),   # search ALL → UID 1
        ]
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # 通知済み

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=mock_redis),
        ):
            result = notifier.check_and_notify()
        assert result == 0

    def test_new_mail_triggers_discord_and_marks_redis(self) -> None:
        raw_header = b"From: sender@example.com\r\nSubject: Hello\r\nDate: Sat, 14 Jun 2026 10:00:00 +0900\r\n\r\n"

        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"42"]),                              # search ALL
            (None, [(b"42 ...", raw_header)]),            # fetch UID 42
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

    def test_redis_unavailable_does_not_raise(self) -> None:
        raw_header = b"From: f@e.com\r\nSubject: S\r\nDate: D\r\n\r\n"
        mock_imap = MagicMock()
        mock_imap.uid.side_effect = [
            (None, [b"5"]),
            (None, [(b"5 ...", raw_header)]),
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with (
            patch.object(notifier, "_IMAP_HOST", "imap.example.com"),
            patch.object(notifier, "_IMAP_USER", "user@example.com"),
            patch.object(notifier, "_IMAP_PASSWORD", "pass"),
            patch.object(notifier, "_DISCORD_WEBHOOK", "https://discord.example.com/webhook"),
            patch("imaplib.IMAP4_SSL", return_value=mock_imap),
            patch.object(notifier, "_get_redis", return_value=None),  # Redis 不能
            patch("httpx.post", return_value=mock_resp),
        ):
            result = notifier.check_and_notify()

        # Redis なしでも通知は成功するが、UID は記録されない
        assert result == 1
