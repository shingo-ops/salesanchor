"""名簿（スタッフ画面）からの「1人に1つのロールを付ける」処理の一本化（ADR-1008 P4a）。

ロールの正本は user_roles。staff.role_id は読まない・書かない。
この関数は commit しない（呼び出し側のトランザクションで commit し、その後に
invalidate_user_permissions を呼ぶ）。
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.routers.roles import (
    _hidden_role_params,
    _max_priority_for_user,
    _visible_role_sql,
    _visible_text,
)
from app.services.audit import record_audit_log


async def ensure_target_below_me(
    db: AsyncSession, target_user_id: int, my_max: int
) -> None:
    """対象の人の今の最大 priority が自分の最大 priority 以上なら 403。"""
    target_max = await _max_priority_for_user(db, target_user_id)
    if target_max >= my_max:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="自分と同格以上のスタッフのロールは変更できません",
        )


async def assign_single_role(
    db: AsyncSession,
    tenant_id: int,
    current_user: User,
    target_user_id: int,
    role_id: int,
) -> None:
    """target_user_id の「見えるロール」をすべて外し、role_id の1つだけにする。

    - role_id が同テナントに存在し、隠すロールでない（super admin 以外）こと → 違えば 400
    - 付与するロールの priority が自分の最大 priority 未満であること → 違えば 403
    - 対象の人の今の最大 priority が自分の最大 priority 未満であること → 違えば 403
    - 隠すロール（super admin 向け）は super admin 以外の操作では外さない
    """
    hidden_params = _hidden_role_params(current_user)
    found = await db.execute(
        _visible_text(
            "SELECT id, priority FROM roles WHERE id = :rid AND tenant_id = :tid "
            f"AND {_visible_role_sql()}"
        ),
        {"rid": role_id, "tid": tenant_id, **hidden_params},
    )
    role = found.mappings().first()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定の role_id はこのテナントに存在しません",
        )

    my_max = await _max_priority_for_user(db, current_user.id)
    if role["priority"] >= my_max:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"自分の最大priority以上のロール（id={role_id}）は付与できません",
        )
    await ensure_target_below_me(db, target_user_id, my_max)

    await db.execute(
        _visible_text(
            "DELETE FROM user_roles WHERE user_id = :uid AND role_id IN ("
            f"SELECT id FROM roles WHERE {_visible_role_sql()})"
        ),
        {"uid": target_user_id, **hidden_params},
    )
    await db.execute(
        text(
            "INSERT INTO user_roles (user_id, role_id, assigned_by) "
            "VALUES (:uid, :rid, :by)"
        ),
        {"uid": target_user_id, "rid": role_id, "by": current_user.id},
    )
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="assign_roles", table_name="user_roles", record_id=target_user_id,
        new_data={"role_ids": [role_id]},
    )
