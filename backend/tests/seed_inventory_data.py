"""在庫・テナント設定まわりの試験が、自分で用意する seed（ADR-1007 段3c）。

migration 063・069 は、権限キーとテナントの既定行を入れなくなった（値を書く文を外した）。
これらを入力にしていた試験が、自分で同じ値を入れられるようにする。DB は使わない純粋な関数だけ。
SQL は ON CONFLICT／WHERE NOT EXISTS で冪等。実行は conn.exec_driver_sql。
"""

from __future__ import annotations


def _permissions_sql(rows: list[tuple[str, str, str, str, str]]) -> str:
    values = ",\n".join(
        "(" + ", ".join("'" + part.replace("'", "''") + "'" for part in row) + ")" for row in rows
    )
    return (
        "INSERT INTO public.permissions (key, resource, action, description, category) VALUES\n"
        + values
        + "\nON CONFLICT (key) DO NOTHING"
    )


# migration 063 が入れていた 4 キー（key, resource, action, description, category）
_INVENTORY_VISIBILITY_ROWS = [
    (
        "inventory.visibility.full",
        "inventory_visibility",
        "view_full",
        "在庫の数量・単価・状態をすべて閲覧（営業 / オーナー想定）",
        "在庫",
    ),
    (
        "inventory.visibility.staff",
        "inventory_visibility",
        "view_staff",
        "在庫の品名・単価は閲覧、数量は ***マスク（経理 / 観測者想定）",
        "在庫",
    ),
    (
        "inventory.visibility.viewer",
        "inventory_visibility",
        "view_viewer",
        "在庫の品名のみ閲覧、単価・数量はすべて ***マスク（外部観測者想定）",
        "在庫",
    ),
    (
        "tenant.inventory_visibility.edit",
        "tenant_inventory_visibility",
        "edit",
        "自社内ロールに inventory.visibility.* を割り当てる（テナント admin 専用）",
        "在庫",
    ),
]

# migration 069 が入れていた 2 キー
_TENANT_PROFILE_ROWS = [
    (
        "tenant.profile.view",
        "tenant_profile",
        "view",
        "自社の発行者情報 (会社名・印鑑・連絡先) を閲覧",
        "テナント設定",
    ),
    (
        "tenant.profile.edit",
        "tenant_profile",
        "edit",
        "自社の発行者情報 (PO PDF / メール差出人欄) を編集",
        "テナント設定",
    ),
]


def inventory_visibility_permissions_seed_sql() -> str:
    """public.permissions へ inventory.visibility.* の 3 キーと tenant.inventory_visibility.edit を入れる SQL。"""
    return _permissions_sql(_INVENTORY_VISIBILITY_ROWS)


def tenant_profile_permissions_seed_sql() -> str:
    """public.permissions へ tenant.profile.view／edit を入れる SQL。"""
    return _permissions_sql(_TENANT_PROFILE_ROWS)


def tenant_profile_default_row_sql(schema: str) -> str:
    """{schema}.tenant_profile に既定の 1 行（default_language='ja'）を入れる SQL。schema は tenant_NNN の形だけを許す。"""
    import re

    if not re.fullmatch(r"tenant_[0-9]+", schema):
        raise ValueError("Invalid tenant schema")
    return (
        f"INSERT INTO {schema}.tenant_profile (default_language) "
        f"SELECT 'ja' WHERE NOT EXISTS (SELECT 1 FROM {schema}.tenant_profile)"
    )
