"""
SEC-01: Gemini エラーメッセージに API キーが含まれないことを保証するテスト。

対象:
  - gemini_extraction_svc._safe_error_message()
  - gemini_extraction_svc.extract_message() の error_message フィールド
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.gemini_extraction_svc import _safe_error_message, extract_message


class TestSafeErrorMessage:
    """_safe_error_message のユニットテスト。"""

    def test_key_pattern_is_redacted(self):
        """key=<値> が伏せ字になること（URLクエリパラメータ形式）。"""
        exc = Exception(
            "POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=AIzaSyABCD1234 returned 429"
        )
        result = _safe_error_message(exc)
        assert "key=" not in result

    def test_429_returns_rate_limit_message(self):
        """HTTP 429 は「レート制限超過 (HTTP 429)」を返す。"""
        exc = Exception("429 Too Many Requests: quota exceeded key=AIzaSyXXX")
        result = _safe_error_message(exc)
        assert result == "レート制限超過 (HTTP 429)"

    def test_401_returns_auth_error(self):
        """HTTP 401 は「認証エラー (HTTP 401)」を返す。"""
        exc = Exception("401 Unauthorized key=invalid")
        result = _safe_error_message(exc)
        assert result == "認証エラー (HTTP 401)"

    def test_403_returns_access_denied(self):
        """HTTP 403 は「アクセス拒否 (HTTP 403)」を返す。"""
        exc = Exception("Error 403: forbidden ?key=AIzaSyXXX")
        result = _safe_error_message(exc)
        assert result == "アクセス拒否 (HTTP 403)"

    def test_500_returns_server_error(self):
        """HTTP 500 は「サーバーエラー (HTTP 500)」を返す。"""
        exc = Exception("500 Internal Server Error")
        result = _safe_error_message(exc)
        assert result == "サーバーエラー (HTTP 500)"

    def test_unknown_http_code_uses_generic(self):
        """マッピングにない 4xx/5xx は「HTTPエラー (HTTP NNN)」を返す。"""
        exc = Exception("502 Bad Gateway")
        result = _safe_error_message(exc)
        assert result == "HTTPエラー (HTTP 502)"

    def test_no_http_code_redacts_key(self):
        """HTTP ステータスなし・key= あり → key= を含まない文字列を返す。"""
        exc = RuntimeError("connection refused to api?key=secret123")
        result = _safe_error_message(exc)
        assert "key=" not in result
        assert "secret123" not in result

    def test_no_sensitive_data_passes_through(self):
        """センシティブ情報なし → メッセージはそのまま通過。"""
        exc = RuntimeError("GEMINI_API_KEY が未設定です")
        result = _safe_error_message(exc)
        assert result == "GEMINI_API_KEY が未設定です"


class TestExtractMessageErrorRedact:
    """extract_message() の error_message フィールドに key= が入らないことを確認。"""

    def test_api_exception_with_key_in_url_is_redacted(self):
        """
        Gemini SDK が key= を含む URL を持つ例外を送出した場合、
        extract_message() が返す error_message に key= が含まれないこと。
        """
        fake_exc = Exception(
            "POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent"
            "?key=AIzaSyABCD1234EFGH5678 returned 429"
        )

        with patch(
            "app.services.gemini_extraction_svc.call_gemini_extraction",
            side_effect=fake_exc,
        ):
            result = extract_message("テスト商品 1個 100円")

        assert result["status"] == "error"
        assert result["error_message"] is not None
        assert "key=" not in result["error_message"], (
            f"error_message に key= が含まれています: {result['error_message']!r}"
        )

    def test_rate_limit_error_shows_japanese_reason(self):
        """429 エラーは日本語の理由を返す。"""
        fake_exc = Exception("429 Rate limit exceeded ?key=AIzaSyXXX")

        with patch(
            "app.services.gemini_extraction_svc.call_gemini_extraction",
            side_effect=fake_exc,
        ):
            result = extract_message("テスト")

        assert result["status"] == "error"
        assert result["error_message"] == "レート制限超過 (HTTP 429)"

    def test_success_has_no_error_message(self):
        """正常時は error_message が None。"""
        fake_response = (
            "RAW_PRODUCT_NAME｜RAW_QUANTITY｜RAW_PRICE｜RAW_UNIT｜RAW_STATE｜RAW_MEMO｜RAW_SOURCE_LINE_SPAN\n"
            "テスト商品｜1｜100｜個｜｜｜L0001\n"
        )

        with patch(
            "app.services.gemini_extraction_svc.call_gemini_extraction",
            return_value=fake_response,
        ):
            result = extract_message("テスト商品 1個 100円")

        assert result["status"] == "done"
        assert result["error_message"] is None
