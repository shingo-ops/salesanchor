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

# ロール画面の編集の決まり（ADR-147 追補 2026-11-09）
ROLE_KEY_MANAGER = "manager"
ROLE_KEY_INSPECTOR = "inspector"  # 点検用（見るだけ）ADR-1051
ROLE_KEY_SMOKE = "smoke"  # スモーク専用 ADR-1017
# ロール画面（GET /roles?scope=role_page）に出さないロール
ROLE_PAGE_HIDDEN_KEYS = frozenset({ROLE_KEY_OWNER, ROLE_KEY_ADMIN, ROLE_KEY_INSPECTOR, ROLE_KEY_SMOKE})
# ロール画面を開いて直せるロール
ROLE_EDITOR_KEYS = frozenset({ROLE_KEY_OWNER, ROLE_KEY_ADMIN, ROLE_KEY_MANAGER})
ALL_ROLE_KEYS = frozenset({"roles.view", "roles.create", "roles.update", "roles.delete", "roles.assign"})
ROLE_PAGE_KEYS = ALL_ROLE_KEYS  # マネージャーにも作成・削除・割当を渡す（PO「2」）
# 付けられるのが owner/admin だけのロール（マネージャーは付けられない）
OWNER_ADMIN_ONLY_KEYS = ROLE_PAGE_HIDDEN_KEYS | {ROLE_KEY_MANAGER}


def is_tenant_admin(system_keys: set[str]) -> bool:
    """owner または admin のシステムロールを持つか（権限判定の正本は user_roles。users.role は使わない）。"""
    return bool(system_keys & {ROLE_KEY_OWNER, ROLE_KEY_ADMIN})


def is_tenant_owner(system_keys: set[str]) -> bool:
    """オーナー（system_key=owner）だけか。admin は入れない（ADR-1063）。"""
    return ROLE_KEY_OWNER in system_keys


def compute_permission_keys(
    stored_keys: set[str],
    system_keys: set[str],
    all_keys: set[str],
) -> set[str]:
    """保存済みの付与（全ロールの和集合）に、システムロールの計算結果を和集合で加える。

    - owner: 全キー
    - admin: 全キー - system.manage（他ロールが system.manage を明示付与していれば、保存済みの分として残る）
    - manager: 保存済みの付与から roles.* を除き、roles.* を計算で足す
    - それ以外: 保存済みの付与から roles.* を除く（ロール画面の鍵は計算で決まる）
    """
    if ROLE_KEY_OWNER in system_keys:
        return stored_keys | all_keys
    if ROLE_KEY_ADMIN in system_keys:
        return stored_keys | (all_keys - {SYSTEM_MANAGE_KEY})
    if ROLE_KEY_MANAGER in system_keys:
        return (set(stored_keys) - ALL_ROLE_KEYS) | (ROLE_PAGE_KEYS & all_keys)
    return set(stored_keys) - ALL_ROLE_KEYS
