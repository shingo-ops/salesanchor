"""会社の分け方（RLS）の点検で使う SQL（ADR-1063 便5・便6）。

ここが唯一の正本。CI の点検（scripts/check_public_tenant_rls.py）と
本番の毎日点検（backend/app/tasks/tenant_isolation_daily_check.py）の両方がここを読む。ほかの場所に写さない。
許可一覧は backend/app/ops/tenant_rls_allowlist.py。
"""

from __future__ import annotations

# public の表のうち tenant_id 列を持つのに RLS の無いもの（名前順）。
PUBLIC_TABLES_WITHOUT_RLS_SQL = """
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = 'tenant_id' AND NOT a.attisdropped
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND NOT c.relrowsecurity
ORDER BY c.relname
"""

# 今つないでいる役の名前と、superuser・BYPASSRLS の印。
CURRENT_ROLE_SQL = """
SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname = current_user
"""

# RLS を飛び越せる役（BYPASSRLS の印を持つ役と superuser。superuser は印が無くても RLS を飛び越す）。
RLS_BYPASS_ROLES_SQL = """
SELECT rolname
FROM pg_roles
WHERE rolbypassrls OR rolsuper
ORDER BY rolname
"""
