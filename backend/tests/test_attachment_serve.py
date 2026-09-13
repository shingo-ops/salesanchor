"""serve_lead_attachment エンドポイントのユニットテスト（attachment-storage 便4）。

実 DB・Discord CDN には接続しない。
テーブル定義は conftest.py の setup_test_db に集約されているため、
本ファイルでは CREATE TABLE を書かない（check_test_schema_dup.py の要求）。

テスト対象: GET /api/v1/leads/{lead_id}/attachments/{attachment_id}
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# conftest.py の client フィクスチャは tenant_id=999 でログイン済み扱いにする。
TENANT_A = 999
TENANT_B = 998


async def _insert_attachment(
    db: AsyncSession,
    *,
    tenant_id: int,
    lead_id: int,
    message_id: str,
    file_path: str,
) -> int:
    """lead_attachments に1行 INSERT して採番された id を返す。"""
    result = await db.execute(
        text("""
            INSERT INTO lead_attachments
                (tenant_id, lead_id, message_id, platform,
                 file_path, file_size, content_type, original_filename)
            VALUES
                (:tenant_id, :lead_id, :message_id, 'discord',
                 :file_path, 1024, 'image/png', 'test.png')
            RETURNING id
        """),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "message_id": message_id,
            "file_path": file_path,
        },
    )
    row = result.first()
    await db.commit()
    return int(row[0])


@pytest.mark.asyncio
async def test_serve_not_found_attachment_id(client, db_session):
    """存在しない attachment_id で 404 が返ること。"""
    resp = await client.get("/api/v1/leads/1/attachments/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "attachment_not_found"


@pytest.mark.asyncio
async def test_serve_other_tenant_returns_404(client, db_session):
    """他テナントの attachment_id に対して 404 が返ること（テナント分離の確認）。"""
    attachment_id = await _insert_attachment(
        db_session,
        tenant_id=TENANT_B,
        lead_id=1,
        message_id="msg-other-tenant",
        file_path="tenant_998/lead_1/msg-other-tenant.png",
    )
    resp = await client.get(f"/api/v1/leads/1/attachments/{attachment_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "attachment_not_found"


@pytest.mark.asyncio
async def test_serve_missing_file_returns_404(client, db_session, tmp_path, monkeypatch):
    """DB に行があっても実体ファイルが無い場合に 404 が返ること。"""
    monkeypatch.setenv("ATTACHMENT_ROOT", str(tmp_path))
    attachment_id = await _insert_attachment(
        db_session,
        tenant_id=TENANT_A,
        lead_id=10,
        message_id="msg-no-file",
        file_path="tenant_999/lead_10/msg-no-file.png",
    )
    resp = await client.get(f"/api/v1/leads/10/attachments/{attachment_id}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "attachment_file_missing"


@pytest.mark.asyncio
async def test_serve_success_returns_file(client, db_session, tmp_path, monkeypatch):
    """正常時に 200 と正しい media_type と中身が返ること。"""
    monkeypatch.setenv("ATTACHMENT_ROOT", str(tmp_path))

    file_dir = tmp_path / "tenant_999" / "lead_20"
    file_dir.mkdir(parents=True)
    file_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    (file_dir / "msg-ok.png").write_bytes(file_content)

    attachment_id = await _insert_attachment(
        db_session,
        tenant_id=TENANT_A,
        lead_id=20,
        message_id="msg-ok",
        file_path="tenant_999/lead_20/msg-ok.png",
    )

    resp = await client.get(f"/api/v1/leads/20/attachments/{attachment_id}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/png")
    assert resp.content == file_content
