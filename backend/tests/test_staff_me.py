"""
B-1: GET /api/v1/staff/me および PATCH /api/v1/staff/me/profile のスモークテスト。

staff.user_id == current_user.id で本人の名簿行を引く経路（ADR-1008）と、
user_id が一致する行が無い場合の 404、電話番号更新を検証する。メールの一致では引かない。
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_get_my_staff_by_user_id_even_if_email_differs(client, db_session):
    """
    conftest の mock_user は id=999・email='test@example.com'。
    名簿の primary_email は別のメールにしても、user_id=999 で引けることを確認する。
    """
    # 役割を1件作成
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (1, 999, 'staff', '#888888', 0, FALSE)
    """))
    # mock_user.id（999）に紐付く名簿行。primary_email は mock_user と別
    await db_session.execute(text("""
        INSERT INTO staff (
            id, tenant_id, user_id, staff_code, surname_jp, given_name_jp,
            primary_email, status
        ) VALUES (
            500, 999, 999, 'EMP-TEST01', '山田', '太郎',
            'other@example.com', 'active'
        )
    """))
    # 名簿のロールの正本は user_roles（ADR-1008 P4a）。staff.role_id は NULL のまま
    await db_session.execute(text(
        "INSERT INTO user_roles (user_id, role_id) VALUES (999, 1)"
    ))
    # ui_preferences 行を作る（dark_mode のみ true）
    await db_session.execute(text("""
        INSERT INTO staff_ui_preferences (
            staff_id, dark_mode, show_chat_menu, show_sales_menu,
            show_settings_menu, show_admin_menu, show_sidebar
        ) VALUES (500, 1, 1, 1, 1, 0, 1)
    """))
    await db_session.commit()

    res = await client.get("/api/v1/staff/me")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["id"] == 500
    assert data["primary_email"] == "other@example.com"
    assert data["role_id"] == 1
    assert data["role_name"] == "staff"
    assert data["ui_preferences"] is not None
    assert data["ui_preferences"]["dark_mode"] is True
    assert data["ui_preferences"]["show_admin_menu"] is False
    assert data["ui_preferences"]["show_sidebar"] is True


@pytest.mark.asyncio
async def test_get_my_staff_404_when_no_link(client, db_session):
    """user_id が一致する名簿行が無いユーザは、メールが同じ行があっても 404 を返す"""
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (6, 999, 'noone', '#777777', 0, FALSE)
    """))
    # 別の user_id（12345）の名簿行。primary_email は mock_user と同じ
    await db_session.execute(text("""
        INSERT INTO staff (
            id, tenant_id, user_id, staff_code, surname_jp, given_name_jp,
            primary_email, role_id, status
        ) VALUES (
            450, 999, 12345, 'EMP-NOONE', '別', '人',
            'test@example.com', 6, 'active'
        )
    """))
    await db_session.commit()
    res = await client.get("/api/v1/staff/me")
    assert res.status_code == 404
    body = res.json()
    assert "staff" in body["detail"] or "見つかりません" in body["detail"]


@pytest.mark.asyncio
async def test_get_my_staff_picks_own_row_when_shared_email(client, db_session):
    """
    primary_email が同じ名簿行が複数あっても、user_id が自分の行（id の大きい方）だけが返る。
    """
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (3, 999, 'shared', '#555555', 0, FALSE)
    """))
    # 同じ primary_email の名簿行を 2 件。id の小さい方（700）は別人（user_id=1001）、自分は 701
    await db_session.execute(text("""
        INSERT INTO staff (
            id, tenant_id, user_id, staff_code, surname_jp, given_name_jp,
            primary_email, role_id, status
        ) VALUES
            (701, 999, 999, 'EMP-SHARE2', '佐藤', '次郎', 'test@example.com', 3, 'active'),
            (700, 999, 1001, 'EMP-SHARE1', '佐藤', '一郎', 'test@example.com', 3, 'active')
    """))
    await db_session.commit()

    for _ in range(3):
        res = await client.get("/api/v1/staff/me")
        assert res.status_code == 200, res.text
        assert res.json()["id"] == 701


@pytest.mark.asyncio
async def test_get_my_staff_no_ui_preferences_returns_null(client, db_session):
    """staff_ui_preferences 行が存在しない場合は ui_preferences=null を返す"""
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (2, 999, 'staff2', '#999999', 0, FALSE)
    """))
    await db_session.execute(text("""
        INSERT INTO staff (
            id, tenant_id, user_id, staff_code, surname_jp, given_name_jp,
            primary_email, role_id, status
        ) VALUES (
            600, 999, 999, 'EMP-TEST02', '鈴木', '花子',
            'test@example.com', 2, 'active'
        )
    """))
    # ui_preferences は意図的に作らない
    await db_session.commit()

    res = await client.get("/api/v1/staff/me")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["id"] == 600
    assert data["ui_preferences"] is None


@pytest.mark.asyncio
async def test_patch_my_profile_phone(client, db_session):
    """PATCH /staff/me/profile で phone を登録・更新できる"""
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (4, 999, 'member', '#aaaaaa', 0, FALSE)
    """))
    await db_session.execute(text("""
        INSERT INTO staff (
            id, tenant_id, user_id, staff_code, surname_jp, given_name_jp,
            primary_email, role_id, status
        ) VALUES (
            800, 999, 999, 'EMP-PHONE01', '田中', '三郎',
            'test@example.com', 4, 'active'
        )
    """))
    await db_session.commit()

    # 電話番号を登録
    res = await client.patch(
        "/api/v1/staff/me/profile",
        json={"phone": "09012345678"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["phone"] == "09012345678"

    # phone=null でクリア可能
    res = await client.patch(
        "/api/v1/staff/me/profile",
        json={"phone": None},
    )
    assert res.status_code == 200, res.text
    assert res.json()["phone"] is None


@pytest.mark.asyncio
async def test_patch_my_profile_phone_invalid(client, db_session):
    """不正な phone 値は 422 を返す"""
    await db_session.execute(text("""
        INSERT INTO roles (id, tenant_id, name, color, priority, is_system)
        VALUES (5, 999, 'member2', '#bbbbbb', 0, FALSE)
    """))
    await db_session.execute(text("""
        INSERT INTO staff (
            id, tenant_id, user_id, staff_code, surname_jp, given_name_jp,
            primary_email, role_id, status
        ) VALUES (
            900, 999, 999, 'EMP-PHONE02', '高橋', '四郎',
            'test@example.com', 5, 'active'
        )
    """))
    await db_session.commit()

    res = await client.patch(
        "/api/v1/staff/me/profile",
        json={"phone": "不正な値abc"},
    )
    assert res.status_code == 422
