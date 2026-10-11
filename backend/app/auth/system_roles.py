"""システムロールの安定識別子と、権限計算に使う定数・関数。

owner / admin の権限は role_permissions の行ではなく、権限マスタ（public.permissions）から
check 時に計算する。新しい権限キーが増えても、owner / admin には行の追加なしで届く。
"""
from __future__ import annotations

ROLE_KEY_OWNER = "owner"
ROLE_KEY_ADMIN = "admin"
SYSTEM_MANAGE_KEY = "system.manage"  # admin だけが持たない権限キー（唯一の定義場所）

# 運営者用のロール。super admin（public.users.is_super_admin）以外には一覧に見せず、付けさせない。
# 見分けは roles.system_key で行い、名前では分岐しない（唯一の定義場所。ADR-147 追補 2026-10-10）
TENANT_HIDDEN_SYSTEM_KEYS = frozenset({ROLE_KEY_ADMIN})


def compute_permission_keys(
    stored_keys: set[str],
    system_keys: set[str],
    all_keys: set[str],
) -> set[str]:
    """保存済みの付与（全ロールの和集合）に、システムロールの計算結果を和集合で加える。

    - owner: 全キー
    - admin: 全キー - system.manage（他ロールが system.manage を明示付与していれば、保存済みの分として残る）
    - どちらでもない: 保存済みの付与そのまま
    """
    if ROLE_KEY_OWNER in system_keys:
        return stored_keys | all_keys
    if ROLE_KEY_ADMIN in system_keys:
        return stored_keys | (all_keys - {SYSTEM_MANAGE_KEY})
    return set(stored_keys)
