"""会社の分け方（RLS）の許可一覧（ADR-1063 便5・便6）。

ここが唯一の正本。CI の点検（scripts/check_public_tenant_rls.py）と
本番の毎日点検（便6）の両方がこのファイルを読む。ほかの場所に写さない。

PUBLIC_TABLES_WITHOUT_RLS: public の表のうち、tenant_id 列を持つのに RLS を付けない表。
  表名 → 理由（空にしない。空なら CI の点検が落ちる）。
BYPASSRLS_ROLES: BYPASSRLS を持ってよい役。役名 → 理由（便6 で初回の観測を PO に報告してから固定する）。

この一覧の行を足すときは、なぜ RLS が要らないかを理由に書く。推測で足さない。
"""

from __future__ import annotations

PUBLIC_TABLES_WITHOUT_RLS: dict[str, str] = {}

BYPASSRLS_ROLES: dict[str, str] = {}
