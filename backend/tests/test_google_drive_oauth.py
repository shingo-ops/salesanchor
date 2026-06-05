"""
Google Drive OAuth 連携サービスの単体テスト。

Redis・Google API は全てモックする。google_calendar の同等テストを雛形にミラー。

カバー範囲:
  - _is_token_expired
  - 環境変数ヘルパー / is_oauth_configured
  - extract_folder_id
  - issue_state / consume_state（Redis mock）
  - get_auth_url（Flow mock）
  - exchange_code（Flow mock + state 検証）
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

# テスト用環境変数を先に設定
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("GOOGLE_DRIVE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_DRIVE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_DRIVE_REDIRECT_URI", "https://api.example.com/callback")


# ---------------------------------------------------------------------------
# _is_token_expired
# ---------------------------------------------------------------------------
class TestIsTokenExpired:
    def test_expired_when_none(self):
        from app.services.google_drive_oauth import _is_token_expired

        assert _is_token_expired(None) is True

    def test_expired_when_past(self):
        from app.services.google_drive_oauth import _is_token_expired

        assert _is_token_expired(datetime.now(timezone.utc) - timedelta(hours=2)) is True

    def test_not_expired_when_future(self):
        from app.services.google_drive_oauth import _is_token_expired

        assert _is_token_expired(datetime.now(timezone.utc) + timedelta(hours=1)) is False

    def test_expired_within_buffer(self):
        from app.services.google_drive_oauth import _is_token_expired

        assert _is_token_expired(datetime.now(timezone.utc) + timedelta(minutes=3)) is True


# ---------------------------------------------------------------------------
# 環境変数ヘルパー / is_oauth_configured
# ---------------------------------------------------------------------------
class TestEnvHelpers:
    def test_get_client_id_raises_when_missing(self):
        from app.services import google_drive_oauth as svc

        with patch.dict(os.environ, {"GOOGLE_DRIVE_CLIENT_ID": ""}):
            with pytest.raises(RuntimeError, match="GOOGLE_DRIVE_CLIENT_ID"):
                svc._get_client_id()

    def test_get_client_secret_raises_when_missing(self):
        from app.services import google_drive_oauth as svc

        with patch.dict(os.environ, {"GOOGLE_DRIVE_CLIENT_SECRET": ""}):
            with pytest.raises(RuntimeError, match="GOOGLE_DRIVE_CLIENT_SECRET"):
                svc._get_client_secret()

    def test_get_redirect_uri_raises_when_missing(self):
        from app.services import google_drive_oauth as svc

        with patch.dict(os.environ, {"GOOGLE_DRIVE_REDIRECT_URI": ""}):
            with pytest.raises(RuntimeError, match="GOOGLE_DRIVE_REDIRECT_URI"):
                svc._get_redirect_uri()

    def test_is_oauth_configured_true(self):
        from app.services.google_drive_oauth import is_oauth_configured

        assert is_oauth_configured() is True

    def test_is_oauth_configured_false(self):
        from app.services.google_drive_oauth import is_oauth_configured

        with patch.dict(os.environ, {"GOOGLE_DRIVE_CLIENT_ID": ""}):
            assert is_oauth_configured() is False


# ---------------------------------------------------------------------------
# extract_folder_id
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://drive.google.com/drive/folders/0ABCdef_123", "0ABCdef_123"),
        ("https://drive.google.com/drive/u/0/folders/0ABCdef_123?usp=sharing", "0ABCdef_123"),
        ("0ABCdef_1234567", "0ABCdef_1234567"),
        ("", None),
        ("https://drive.google.com/drive/my-drive", None),
    ],
)
def test_extract_folder_id(url, expected):
    from app.services.google_drive_oauth import extract_folder_id

    assert extract_folder_id(url) == expected


# ---------------------------------------------------------------------------
# issue_state / consume_state
# ---------------------------------------------------------------------------
class TestOAuthState:
    @pytest.fixture
    def mock_redis(self):
        r = AsyncMock()
        pipeline_mock = MagicMock()
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock(return_value=None)
        pipeline_mock.get = MagicMock(return_value=None)
        pipeline_mock.delete = MagicMock(return_value=None)
        pipeline_mock.execute = AsyncMock(return_value=[None, 0])
        r.pipeline = MagicMock(return_value=pipeline_mock)
        with patch("app.services.google_drive_oauth.get_redis", return_value=r):
            yield r, pipeline_mock

    async def test_issue_state_returns_state_string(self, mock_redis):
        from app.services.google_drive_oauth import issue_state

        r, _ = mock_redis
        state = await issue_state(tenant_id=1, user_id=42)
        assert isinstance(state, str)
        assert len(state) > 20
        r.setex.assert_called_once()

    async def test_issue_state_no_redis_raises(self):
        from app.services.google_drive_oauth import issue_state

        with patch("app.services.google_drive_oauth.get_redis", return_value=None):
            with pytest.raises(RuntimeError, match="Redis"):
                await issue_state(tenant_id=1, user_id=1)

    async def test_consume_state_not_found_returns_none(self, mock_redis):
        from app.services.google_drive_oauth import consume_state

        assert await consume_state("nonexistent-state") is None

    async def test_consume_state_empty_string_returns_none(self, mock_redis):
        from app.services.google_drive_oauth import consume_state

        assert await consume_state("") is None

    async def test_consume_state_no_redis_raises(self):
        from app.services.google_drive_oauth import consume_state

        with patch("app.services.google_drive_oauth.get_redis", return_value=None):
            with pytest.raises(RuntimeError, match="Redis"):
                await consume_state("some-state")

    async def test_consume_state_found_returns_payload(self):
        from app.services import encryption
        from app.services.google_drive_oauth import consume_state

        payload = {"tenant_id": 1, "user_id": 42, "nonce": "abc"}
        encrypted = encryption.encrypt(json.dumps(payload))

        r = AsyncMock()
        pipeline_mock = AsyncMock()
        pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
        pipeline_mock.__aexit__ = AsyncMock(return_value=None)
        pipeline_mock.execute = AsyncMock(return_value=[encrypted, 1])
        r.pipeline = MagicMock(return_value=pipeline_mock)

        with patch("app.services.google_drive_oauth.get_redis", return_value=r):
            result = await consume_state("valid-state-token")

        assert result is not None
        assert result["tenant_id"] == 1
        assert result["user_id"] == 42


# ---------------------------------------------------------------------------
# get_auth_url
# ---------------------------------------------------------------------------
class TestGetAuthUrl:
    async def test_returns_string_url(self):
        from app.services.google_drive_oauth import get_auth_url

        mock_flow = MagicMock()
        mock_flow.authorization_url = MagicMock(return_value=("https://accounts.google.com/o/oauth2/auth?state=x", "x"))
        r = AsyncMock()
        r.setex = AsyncMock(return_value=True)

        with patch("app.services.google_drive_oauth.get_redis", return_value=r):
            with patch("google_auth_oauthlib.flow.Flow") as MockFlow:
                MockFlow.from_client_config.return_value = mock_flow
                url = await get_auth_url(tenant_id=1, user_id=2)

        assert url.startswith("https://accounts.google.com")


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------
class TestExchangeCode:
    async def test_invalid_state_raises_value_error(self):
        from app.services.google_drive_oauth import exchange_code

        with patch("app.services.google_drive_oauth.consume_state", AsyncMock(return_value=None)):
            with pytest.raises(ValueError, match="無効"):
                await exchange_code("auth-code", "bad-state")

    async def test_no_refresh_token_raises(self):
        from app.services.google_drive_oauth import exchange_code

        payload = {"tenant_id": 1, "user_id": 2, "nonce": "x"}
        mock_creds = MagicMock()
        mock_creds.token = "access-token"
        mock_creds.refresh_token = None
        mock_creds.expiry = None
        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds
        mock_flow.fetch_token = MagicMock()

        with patch("app.services.google_drive_oauth.consume_state", AsyncMock(return_value=payload)):
            with patch("google_auth_oauthlib.flow.Flow") as MockFlow:
                MockFlow.from_client_config.return_value = mock_flow
                with pytest.raises(RuntimeError, match="refresh_token"):
                    await exchange_code("auth-code", "valid-state")

    async def test_successful_exchange(self):
        from app.services.google_drive_oauth import exchange_code

        payload = {"tenant_id": 5, "user_id": 10, "nonce": "y"}
        expiry = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_creds = MagicMock()
        mock_creds.token = "access-abc"
        mock_creds.refresh_token = "refresh-xyz"
        mock_creds.expiry = expiry
        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds
        mock_flow.fetch_token = MagicMock()

        with patch("app.services.google_drive_oauth.consume_state", AsyncMock(return_value=payload)):
            with patch("google_auth_oauthlib.flow.Flow") as MockFlow:
                MockFlow.from_client_config.return_value = mock_flow
                with patch(
                    "app.services.google_drive_oauth._fetch_account_email",
                    return_value="u@example.com",
                ):
                    result = await exchange_code("auth-code", "valid-state")

        assert result["tenant_id"] == 5
        assert result["access_token"] == "access-abc"
        assert result["refresh_token"] == "refresh-xyz"
        assert result["expiry"] == expiry
        assert result["account_email"] == "u@example.com"
