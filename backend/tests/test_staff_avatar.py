"""担当者アイコン（ADR-159 便A）のテスト。

- POST/DELETE /api/v1/staff/me/avatar（本人のみ・形式/サイズ検証・EXIF 除去）
- GET /api/public/staff-avatars/{token}.webp（認証不要・パストラバーサル不可）
- 英語名（名・姓）の必須化（DB は NOT NULL にしない）

実 DB・外部には接続しない。画像は ATTACHMENT_ROOT を tmp_path に向けて保存する。
テーブル定義は conftest.py の setup_test_db に集約（CREATE TABLE は書かない）。
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pydantic import ValidationError
from sqlalchemy import text

from app.schemas.staff import StaffCreate, StaffProfileUpdate, StaffUpdate
from app.services.staff_avatar import (
    AVATAR_MAX_BYTES,
    AvatarError,
    detect_image_type,
    new_token,
    process_avatar,
)

API = "/api/v1/staff/me/avatar"
PUBLIC = "/api/public/staff-avatars"
EXIF_MARKER = b"SECRETCAMERA"


@pytest.fixture(autouse=True)
def _avatar_root(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTACHMENT_ROOT", str(tmp_path))
    return tmp_path


def _make_image(fmt: str, size=(300, 200), exif: bool = False) -> bytes:
    img = Image.new("RGB", size, (200, 30, 30))
    buf = io.BytesIO()
    kwargs = {}
    if exif:
        ex = Image.Exif()
        ex[0x010F] = EXIF_MARKER.decode()  # Make
        ex[0x0112] = 6  # Orientation: 90 度回転
        kwargs["exif"] = ex.tobytes()
    img.save(buf, format=fmt, **kwargs)
    return buf.getvalue()


async def _seed_staff(db_session, token: str | None = None) -> None:
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (1, 999, 'staff', '#888888', 0, FALSE)
    """))
    await db_session.execute(
        text("""
            INSERT INTO staff (
                id, tenant_id, staff_code, surname_jp, given_name_jp,
                primary_email, role_id, status, avatar_token
            ) VALUES (
                500, 999, 'EMP-AV01', '山田', '太郎',
                'test@example.com', 1, 'active', :token
            )
        """),
        {"token": token},
    )
    await db_session.commit()


def _files(root: Path) -> list[Path]:
    d = root / "staff_avatars"
    return sorted(d.glob("*.webp")) if d.exists() else []


# ---------------------------------------------------------------- service

def test_detect_image_type_by_magic_bytes():
    assert detect_image_type(_make_image("JPEG")) == "jpeg"
    assert detect_image_type(_make_image("PNG")) == "png"
    assert detect_image_type(_make_image("WEBP")) == "webp"
    assert detect_image_type(b"GIF89a" + b"\x00" * 20) is None
    assert detect_image_type(b"<html>not an image</html>") is None


def test_process_avatar_outputs_square_webp_without_metadata():
    raw = _make_image("JPEG", exif=True)
    assert EXIF_MARKER in raw  # 入力には EXIF がある（前提確認）

    out = process_avatar(raw)

    img = Image.open(io.BytesIO(out))
    assert img.format == "WEBP"
    assert img.size == (256, 256)
    assert "exif" not in img.info
    assert EXIF_MARKER not in out


def test_process_avatar_rejects_oversize_and_garbage():
    with pytest.raises(AvatarError) as too_large:
        process_avatar(b"\x89PNG\r\n\x1a\n" + b"0" * AVATAR_MAX_BYTES)
    assert too_large.value.code == "AVATAR_TOO_LARGE"

    with pytest.raises(AvatarError) as bad_type:
        process_avatar(b"not an image at all")
    assert bad_type.value.code == "AVATAR_INVALID_TYPE"

    with pytest.raises(AvatarError) as fake_png:
        process_avatar(b"\x89PNG\r\n\x1a\n" + b"garbage")  # 先頭だけ PNG の偽装
    assert fake_png.value.code == "AVATAR_INVALID_TYPE"


def test_process_avatar_rejects_too_many_pixels_before_decoding(monkeypatch):
    monkeypatch.setattr("app.services.staff_avatar.AVATAR_MAX_PIXELS", 100)  # 10x10 を超えると拒否

    with pytest.raises(AvatarError) as too_many:
        process_avatar(_make_image("PNG", (11, 10)))
    assert too_many.value.code == "AVATAR_INVALID_TYPE"


# ---------------------------------------------------------------- upload / delete

@pytest.mark.asyncio
@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
async def test_upload_accepts_jpg_png_webp(client, db_session, _avatar_root, fmt):
    await _seed_staff(db_session)

    res = await client.post(API, files={"image": ("a.img", _make_image(fmt), "application/octet-stream")})

    assert res.status_code == 200, res.text
    url = res.json()["avatar_url"]
    assert url.startswith("https://api.salesanchor.jp/api/public/staff-avatars/")
    assert url.endswith(".webp")
    assert len(_files(_avatar_root)) == 1


@pytest.mark.asyncio
async def test_upload_then_public_get_returns_image_without_exif(client, db_session, _avatar_root):
    await _seed_staff(db_session)
    res = await client.post(API, files={"image": ("a.jpg", _make_image("JPEG", exif=True), "image/jpeg")})
    token = res.json()["avatar_url"].rsplit("/", 1)[1]

    pub = await client.get(f"{PUBLIC}/{token}")

    assert pub.status_code == 200
    assert pub.headers["content-type"] == "image/webp"
    assert pub.headers["cache-control"] == "public, max-age=3600"
    assert pub.headers["x-content-type-options"] == "nosniff"
    assert EXIF_MARKER not in pub.content
    assert Image.open(io.BytesIO(pub.content)).size == (256, 256)


@pytest.mark.asyncio
async def test_staff_me_returns_avatar_url_after_upload(client, db_session):
    await _seed_staff(db_session)
    await client.post(API, files={"image": ("a.png", _make_image("PNG"), "image/png")})

    res = await client.get("/api/v1/staff/me")

    assert res.status_code == 200
    assert res.json()["avatar_url"].startswith("https://api.salesanchor.jp/api/public/staff-avatars/")


@pytest.mark.asyncio
async def test_staff_me_avatar_url_is_null_when_unset(client, db_session):
    await _seed_staff(db_session)

    res = await client.get("/api/v1/staff/me")

    assert res.json()["avatar_url"] is None


@pytest.mark.asyncio
async def test_upload_replaces_previous_file(client, db_session, _avatar_root):
    await _seed_staff(db_session)
    first = await client.post(API, files={"image": ("a.png", _make_image("PNG"), "image/png")})
    first_token = first.json()["avatar_url"].rsplit("/", 1)[1]

    second = await client.post(API, files={"image": ("b.png", _make_image("PNG", (50, 80)), "image/png")})

    second_token = second.json()["avatar_url"].rsplit("/", 1)[1]
    assert first_token != second_token
    assert [p.name for p in _files(_avatar_root)] == [second_token]
    assert (await client.get(f"{PUBLIC}/{first_token}")).status_code == 404


@pytest.mark.asyncio
async def test_upload_rejects_non_image_even_with_image_content_type(client, db_session, _avatar_root):
    await _seed_staff(db_session)

    res = await client.post(API, files={"image": ("a.png", b"<script>alert(1)</script>", "image/png")})

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "AVATAR_INVALID_TYPE"
    assert _files(_avatar_root) == []


@pytest.mark.asyncio
async def test_upload_rejects_gif(client, db_session):
    await _seed_staff(db_session)

    res = await client.post(API, files={"image": ("a.gif", b"GIF89a" + b"\x00" * 64, "image/gif")})

    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "AVATAR_INVALID_TYPE"


@pytest.mark.asyncio
async def test_upload_rejects_over_2mb(client, db_session, _avatar_root):
    await _seed_staff(db_session)
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (AVATAR_MAX_BYTES + 10)

    res = await client.post(API, files={"image": ("big.png", big, "image/png")})

    assert res.status_code == 413
    assert res.json()["detail"]["code"] == "AVATAR_TOO_LARGE"
    assert _files(_avatar_root) == []


@pytest.mark.asyncio
async def test_upload_without_staff_record_returns_404(client, db_session):
    res = await client.post(API, files={"image": ("a.png", _make_image("PNG"), "image/png")})

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_file_and_token(client, db_session, _avatar_root):
    await _seed_staff(db_session)
    up = await client.post(API, files={"image": ("a.png", _make_image("PNG"), "image/png")})
    token = up.json()["avatar_url"].rsplit("/", 1)[1]

    res = await client.delete(API)

    assert res.status_code == 200
    assert res.json()["avatar_url"] is None
    assert _files(_avatar_root) == []
    assert (await client.get(f"{PUBLIC}/{token}")).status_code == 404


@pytest.mark.asyncio
async def test_delete_is_idempotent_when_unset(client, db_session):
    await _seed_staff(db_session)

    res = await client.delete(API)

    assert res.status_code == 200
    assert res.json()["avatar_url"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["post", "delete"])
async def test_upload_and_delete_require_authentication(monkeypatch, method):
    from app.main import app

    monkeypatch.setattr(app, "dependency_overrides", {})  # 認証モックを外した素のアプリで検証する
    kwargs = {"files": {"image": ("a.png", _make_image("PNG"), "image/png")}} if method == "post" else {}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as anon:
        res = await getattr(anon, method)(API, **kwargs)

    assert res.status_code in (401, 403)


# ---------------------------------------------------------------- public route

@pytest.mark.asyncio
async def test_public_unknown_valid_token_returns_404(client):
    res = await client.get(f"{PUBLIC}/{new_token()}.webp")

    assert res.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    "short.webp",
    "..%2F..%2Fetc%2Fpasswd.webp",
    "../../etc/passwd.webp",
    "A" * 42 + ".webp",
    "A" * 44 + ".webp",
    "A" * 42 + "..webp",
    "A" * 42 + "%00.webp",
])
async def test_public_rejects_malformed_or_traversal_tokens(client, bad):
    res = await client.get(f"{PUBLIC}/{bad}")

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_public_does_not_serve_files_outside_avatar_dir(client, _avatar_root):
    (_avatar_root / "secret.webp").write_bytes(b"secret")

    res = await client.get(f"{PUBLIC}/secret.webp")

    assert res.status_code == 404


# ---------------------------------------------------------------- 英語名必須

def _create_payload(**over):
    base = dict(
        surname_jp="山田", given_name_jp="太郎", primary_email="a@example.com", role_id=1,
        surname_en="Yamada", given_name_en="Taro",
    )
    return {**base, **over}


def test_staff_create_requires_both_english_names():
    assert StaffCreate(**_create_payload()).given_name_en == "Taro"
    for missing in ("surname_en", "given_name_en"):
        payload = _create_payload()
        del payload[missing]
        with pytest.raises(ValidationError):
            StaffCreate(**payload)


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_staff_create_rejects_blank_english_names(blank):
    with pytest.raises(ValidationError):
        StaffCreate(**_create_payload(given_name_en=blank))
    with pytest.raises(ValidationError):
        StaffCreate(**_create_payload(surname_en=blank))


def test_staff_create_trims_english_names():
    data = StaffCreate(**_create_payload(given_name_en="  Taro ", surname_en=" Yamada  "))

    assert (data.given_name_en, data.surname_en) == ("Taro", "Yamada")


@pytest.mark.parametrize("schema", [StaffUpdate, StaffProfileUpdate])
def test_update_schemas_reject_blank_or_null_english_names_but_allow_omission(schema):
    assert schema().model_dump(exclude_unset=True) == {}
    for field in ("given_name_en", "surname_en"):
        for bad in ("", "  ", None):
            with pytest.raises(ValidationError):
                schema(**{field: bad})
    assert schema(given_name_en=" Taro ").given_name_en == "Taro"


@pytest.mark.asyncio
async def test_patch_profile_with_blank_given_name_en_returns_422(client, db_session):
    await _seed_staff(db_session)

    res = await client.patch("/api/v1/staff/me/profile", json={"given_name_en": "  ", "surname_en": "Yamada"})

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_patch_profile_saves_trimmed_english_names(client, db_session):
    await _seed_staff(db_session)

    res = await client.patch(
        "/api/v1/staff/me/profile", json={"given_name_en": " Taro ", "surname_en": " Yamada "},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["given_name_en"], body["surname_en"]) == ("Taro", "Yamada")


@pytest.mark.asyncio
async def test_post_staff_without_english_names_returns_422(client):
    payload = _create_payload()
    del payload["given_name_en"]

    res = await client.post("/api/v1/staff", json=payload)

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_patch_staff_with_blank_english_name_returns_422(client, db_session):
    await _seed_staff(db_session)

    res = await client.patch("/api/v1/staff/500", json={"given_name_en": ""})

    assert res.status_code == 422
