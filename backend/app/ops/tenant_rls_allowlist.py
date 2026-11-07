"""会社の分け方（RLS）の許可一覧（ADR-1063 便5・便6）。

ここが唯一の正本。CI の点検（scripts/check_public_tenant_rls.py）と
本番の毎日点検（便6）の両方がこのファイルを読む。ほかの場所に写さない。

PUBLIC_TABLES_WITHOUT_RLS: public の表のうち、tenant_id 列を持つのに RLS を付けない表。
  表名 → 理由（空にしない。空なら CI の点検が落ちる）。
BYPASSRLS_ROLES: BYPASSRLS を持ってよい役。役名 → 理由（便6 で初回の観測を PO に報告してから固定する）。

この一覧の行を足すときは、なぜ RLS が要らないかを理由に書く。推測で足さない。
"""

from __future__ import annotations

# 2026-11-07 時点の本番の 11 件（ADR-1063 便5 段2・ADR-1067）。
# 「会社の画面から会社の行を足せる」6 件は全社共用ではない。RLS は次の段で読み方と一緒に付ける（PO 2026-11-07「ｃ1」）。
PUBLIC_TABLES_WITHOUT_RLS: dict[str, str] = {
    "line_conditions": (
        "状態の表（別名 public.conditions）。運営の全社共用の行に加えて、会社の画面（backend/app/routers/conditions.py）から会社の行も足せる。"
        "解析が会社で絞らずに読む（backend/app/services/tcg_analyzer_svc.py）ため、RLS は次の段で読み方と一緒に付ける。"
    ),
    "line_units": (
        "単位の表（別名 public.units）。運営の全社共用の行に加えて、会社の画面（backend/app/routers/units.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "payment_fee_settings": (
        "支払い手数料の表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/payment_fee_settings.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "tcg_note_master": (
        "備考の表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/note_master.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "tcg_status_master": (
        "ステータスの表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/status_master.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "tcg_product_categories": (
        "商品区分の表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/product_categories.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "meta_page_routing": (
        "Meta の Webhook を受けた時点では会社が決まっていないため、全社の行から page_id で会社を探す表（backend/app/routers/webhook.py）。"
        "会社の表の trigger（SECURITY DEFINER、backend/app/services/tenant.py）が書く。"
    ),
    "llm_usage_events": (
        "AI の使用量の記録。会社が決まらない呼び出しもあるため会社番号は任意（backend/app/services/llm_budget.py）。運営が全社分を集計して読む。"
    ),
    "data_deletion_logs": "運営のデータ削除の記録（backend/app/tasks/data_deletion.py が書く）。会社の画面からは読み書きしない。",
    "tenant_deletion_audit": "運営の会社削除の記録（backend/app/routers/super_admin_tenants.py が書く）。会社の画面からは読み書きしない。",
    "products_category_classification_backup": "移行で作った商品区分の控え。アプリは読み書きしない。",
}

BYPASSRLS_ROLES: dict[str, str] = {}
