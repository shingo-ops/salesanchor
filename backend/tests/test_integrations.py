"""API連携ルーター + google_drive サービスのテスト。

- extract_folder_id: URL/ID パース
- is_configured / get_service_account_email: 環境変数（生 JSON / base64）
- /integrations/google-drive/status, /test-upload: エンドポイント（google_drive をモック）
"""

import base64
import json

import pytest

from app.services import google_drive


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
        ("  0ABCdef_1234567  ", "0ABCdef_1234567"),
        ("", None),
        ("   ", None),
        ("https://drive.google.com/drive/my-drive", None),
    ],
)
def test_extract_folder_id(url, expected):
    assert google_drive.extract_folder_id(url) == expected


# ─────────────────────────────────────────────────────────────
# is_configured / get_service_account_email
# ─────────────────────────────────────────────────────────────
def _sa_dict():
    return {
        "type": "service_account",
        "client_email": "salesanchor-drive@x.iam.gserviceaccount.com",
    }


def test_configured_via_raw_json(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_SA_JSON_B64", raising=False)
    monkeypatch.setenv("GOOGLE_DRIVE_SA_JSON", json.dumps(_sa_dict()))
    assert google_drive.is_configured() is True
    assert google_drive.get_service_account_email() == "salesanchor-drive@x.iam.gserviceaccount.com"


def test_configured_via_base64(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_SA_JSON", raising=False)
    b64 = base64.b64encode(json.dumps(_sa_dict()).encode()).decode()
    monkeypatch.setenv("GOOGLE_DRIVE_SA_JSON_B64", b64)
    assert google_drive.is_configured() is True
    assert google_drive.get_service_account_email() == "salesanchor-drive@x.iam.gserviceaccount.com"


def test_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_SA_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_DRIVE_SA_JSON_B64", raising=False)
    assert google_drive.is_configured() is False
    assert google_drive.get_service_account_email() is None


def test_invalid_json_is_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_DRIVE_SA_JSON_B64", raising=False)
    monkeypatch.setenv("GOOGLE_DRIVE_SA_JSON", "{not json")
    assert google_drive.is_configured() is False


# ─────────────────────────────────────────────────────────────
# エンドポイント
# ─────────────────────────────────────────────────────────────
async def test_status_endpoint(client, monkeypatch):
    monkeypatch.setattr(google_drive, "is_configured", lambda: True)
    monkeypatch.setattr(
        google_drive,
        "get_service_account_email",
        lambda: "sa@x.iam.gserviceaccount.com",
    )
    resp = await client.get("/api/v1/integrations/google-drive/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["service_account_email"] == "sa@x.iam.gserviceaccount.com"


async def test_test_upload_success(client, monkeypatch):
    monkeypatch.setattr(google_drive, "is_configured", lambda: True)
    monkeypatch.setattr(google_drive, "extract_folder_id", lambda url: "FOLDER123")
    monkeypatch.setattr(
        google_drive,
        "upload_pdf",
        lambda pdf, name, folder: {
            "id": "FILE1",
            "name": name,
            "web_view_link": "https://drive.google.com/file/d/FILE1/view",
        },
    )
    monkeypatch.setattr("app.routers.integrations.render_test_pdf", lambda text="テスト": b"%PDF-1.4 test")
    resp = await client.post(
        "/api/v1/integrations/google-drive/test-upload",
        json={"drive_url": "https://drive.google.com/drive/folders/FOLDER123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_id"] == "FILE1"
    assert body["file_name"] == "salesanchor-test.pdf"
    assert body["web_view_link"].endswith("/view")


async def test_test_upload_not_configured(client, monkeypatch):
    monkeypatch.setattr(google_drive, "is_configured", lambda: False)
    resp = await client.post(
        "/api/v1/integrations/google-drive/test-upload",
        json={"drive_url": "https://drive.google.com/drive/folders/X"},
    )
    assert resp.status_code == 400


async def test_test_upload_bad_url(client, monkeypatch):
    monkeypatch.setattr(google_drive, "is_configured", lambda: True)
    monkeypatch.setattr(google_drive, "extract_folder_id", lambda url: None)
    resp = await client.post(
        "/api/v1/integrations/google-drive/test-upload",
        json={"drive_url": "not-a-url"},
    )
    assert resp.status_code == 400
