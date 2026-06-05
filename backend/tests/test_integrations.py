"""API連携ルーター + google_drive_oauth サービスのテスト（OAuth ユーザー委任方式）。

- extract_folder_id: URL/ID パース
- is_oauth_configured: 環境変数の有無
- /integrations/google-drive/status, /connect/start, /test-upload: エンドポイント
  （google_drive_oauth をモック）
"""

import pytest

from app.services import google_drive_oauth as drive_svc


# ─────────────────────────────────────────────────────────────
# extract_folder_id
# ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://drive.google.com/drive/folders/0ABCdef_123", "0ABCdef_123"),
        (
            "https://drive.google.com/drive/u/0/folders/0ABCdef_123?usp=sharing",
            "0ABCdef_123",
        ),
        ("0ABCdef_1234567", "0ABCdef_1234567"),
        ("", None),
        ("   ", None),
        ("https://drive.google.com/drive/my-drive", None),
    ],
)
def test_extract_folder_id(url, expected):
    assert drive_svc.extract_folder_id(url) == expected


# ─────────────────────────────────────────────────────────────
# is_oauth_configured
# ─────────────────────────────────────────────────────────────
def test_oauth_configured_true(monkeypatch):
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_DRIVE_REDIRECT_URI", "https://app/cb")
    assert drive_svc.is_oauth_configured() is True


def test_oauth_configured_false(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_REDIRECT_URI", raising=False)
    assert drive_svc.is_oauth_configured() is False


# ─────────────────────────────────────────────────────────────
# エンドポイント
# ─────────────────────────────────────────────────────────────
async def test_status_not_connected(client, monkeypatch):
    async def _no_conn(db, tid):
        return None

    monkeypatch.setattr(drive_svc, "get_connection", _no_conn)
    monkeypatch.setattr(drive_svc, "is_oauth_configured", lambda: True)
    resp = await client.get("/api/v1/integrations/google-drive/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is False
    assert body["oauth_configured"] is True
    assert body["account_email"] is None


async def test_status_connected(client, monkeypatch):
    async def _conn(db, tid):
        return {"account_email": "u@example.com", "folder_id": None, "connected_at": None}

    monkeypatch.setattr(drive_svc, "get_connection", _conn)
    monkeypatch.setattr(drive_svc, "is_oauth_configured", lambda: True)
    resp = await client.get("/api/v1/integrations/google-drive/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["account_email"] == "u@example.com"


async def test_connect_start_returns_auth_url(client, monkeypatch):
    async def _auth_url(tid, uid):
        return "https://accounts.google.com/o/oauth2/auth?x=1"

    monkeypatch.setattr(drive_svc, "get_auth_url", _auth_url)
    resp = await client.get("/api/v1/integrations/google-drive/connect/start")
    assert resp.status_code == 200
    assert resp.json()["auth_url"].startswith("https://accounts.google.com/")


async def test_test_upload_success(client, monkeypatch):
    async def _upload(db, tid, pdf, name, folder):
        return {
            "id": "FILE1",
            "name": name,
            "web_view_link": "https://drive.google.com/file/d/FILE1/view",
        }

    monkeypatch.setattr(drive_svc, "upload_pdf", _upload)
    monkeypatch.setattr("app.routers.integrations.render_test_pdf", lambda text="テスト": b"%PDF-1.4 test")
    resp = await client.post("/api/v1/integrations/google-drive/test-upload", json={"drive_url": None})
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_id"] == "FILE1"
    assert body["file_name"] == "salesanchor-test.pdf"


async def test_test_upload_not_connected(client, monkeypatch):
    async def _upload(db, tid, pdf, name, folder):
        raise RuntimeError("Google ドライブが接続されていません")

    monkeypatch.setattr(drive_svc, "upload_pdf", _upload)
    monkeypatch.setattr("app.routers.integrations.render_test_pdf", lambda text="テスト": b"%PDF-1.4 test")
    resp = await client.post("/api/v1/integrations/google-drive/test-upload", json={"drive_url": None})
    assert resp.status_code == 400


async def test_test_upload_bad_url(client):
    resp = await client.post("/api/v1/integrations/google-drive/test-upload", json={"drive_url": "not-a-url"})
    assert resp.status_code == 400


async def test_test_upload_failure_is_502_without_leak(client, monkeypatch):
    async def _boom(db, tid, pdf, name, folder):
        raise Exception("secret-token-AKIA-EXAMPLE")

    monkeypatch.setattr(drive_svc, "upload_pdf", _boom)
    monkeypatch.setattr("app.routers.integrations.render_test_pdf", lambda text="テスト": b"%PDF-1.4 test")
    resp = await client.post("/api/v1/integrations/google-drive/test-upload", json={"drive_url": None})
    assert resp.status_code == 502
    assert "secret-token" not in resp.text
