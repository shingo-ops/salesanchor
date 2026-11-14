"""全テナントを回す移行を、試験がどう扱うかの見張り（静的・DB を使わない）。

新しく足すときの決まり:
共有 DB で全テナントを回す移行を流すなら `_apply_migration_on_conn(..., schema_name=...)` で絞り、`_TENANT_LOOP_MIGRATIONS` に登録する。
絞れないなら使い捨て DB にする。そのうえで下の `_REVIEWED` に分類を書く（書くまでこの試験は落ちる）。
"""
from __future__ import annotations

import re
from pathlib import Path

from tests import rls_bootstrap

_TESTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"

# 全テナントを回す移行 = テナントのスキーマ名を正規表現・LIKE で選ぶ SQL
_LOOP_RE = re.compile(
    r"(?:nspname|schema_name|schemaname|table_schema)\s*(?:~\*?|I?LIKE|~~)\s*'\^?tenant_",
    re.IGNORECASE,
)
_MIGRATION_NAME_RE = re.compile(r"[0-9]{3}[0-9_]*_[a-z0-9_]+\.sql")

# 分類: scoped=1つのテナントに絞って流す / own_database=使い捨て DB / text_only=文字として読むだけ・コメント・SQLite
#       pg_url_only=TEST_PG_URL があるときだけ動く（CI では skip）
_REVIEWED: dict[str, tuple[str, str, frozenset[str]]] = {
    "rls_bootstrap.py": (
        "scoped",
        "",
        frozenset(
            {
                "078_create_calendar_events_tenant.sql",
                "090_add_lead_contact_links.sql",
                "091_add_leads_discord_messaging_columns.sql",
                "095_add_lead_social_links.sql",
                "099_add_discord_guild_config.sql",
                "20260602_120000_add_discord_ticket_config.sql",
                "20260604_090000_create_conversation_logs.sql",
                "20260604_180000_analytics_agent_a_tables.sql",
                "20260604_220000_create_translation_glossary.sql",
                "20260611_100000_create_channel_masters.sql",
                "20260614_100000_create_sales_form_tables.sql",
                "20260621_020000_add_schedule_calendar_category_and_owner_settings.sql",
                "20260715_100000_add_conversation_logs_lead_fk.sql",
                "20260902_100000_create_lead_attachments.sql",
                "20261005_150000_add_roles_system_key.sql",
                "20261103_200000_add_google_calendar_import_sync.sql",
                "20261104_161223_add_calendar_events_meet_url.sql",
                "20261112_170000_add_calendar_events_recurrence.sql",
                "20261106_150000_add_discord_role_link_tables.sql",
                "20261112_160000_create_tenant_issuer_and_payment_tables.sql",
                "20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql",
            }
        ),
    ),
    "test_calendar_sync_tenant_reset_pg.py": (
        "scoped",
        "",
        frozenset(
            {
                "078_create_calendar_events_tenant.sql",
                "20260621_020000_add_schedule_calendar_category_and_owner_settings.sql",
                "20261103_200000_add_google_calendar_import_sync.sql",
                "20261104_161223_add_calendar_events_meet_url.sql",
                "20261112_170000_add_calendar_events_recurrence.sql",
            }
        ),
    ),
    "test_lead_merge_pg.py": (
        "scoped",
        "",
        frozenset(
            {
                "090_add_lead_contact_links.sql",
                "091_add_leads_discord_messaging_columns.sql",
                "095_add_lead_social_links.sql",
                "099_add_discord_guild_config.sql",
                "20260602_120000_add_discord_ticket_config.sql",
                "20260604_090000_create_conversation_logs.sql",
                "20260604_180000_analytics_agent_a_tables.sql",
                "20260604_220000_create_translation_glossary.sql",
                "20260715_100000_add_conversation_logs_lead_fk.sql",
                "20260902_100000_create_lead_attachments.sql",
            }
        ),
    ),
    "test_tenant_user_ref_guard_pg.py": (
        "scoped",
        "",
        frozenset(
            {
                "090_add_lead_contact_links.sql",
                "091_add_leads_discord_messaging_columns.sql",
                "095_add_lead_social_links.sql",
                "099_add_discord_guild_config.sql",
                "20260602_120000_add_discord_ticket_config.sql",
            }
        ),
    ),
    "test_roles_system_key_ddl.py": (
        "scoped",
        "",
        frozenset({"20261005_150000_add_roles_system_key.sql"}),
    ),
    "test_discord_role_link_ddl.py": (
        "scoped",
        "",
        frozenset({"20261106_150000_add_discord_role_link_tables.sql"}),
    ),
    "test_tenant_issuer_tables_pg.py": (
        "scoped",
        "",
        frozenset({"20261112_160000_create_tenant_issuer_and_payment_tables.sql"}),
    ),
    "test_tenant_duty_rules_pg.py": (
        "scoped",
        "",
        frozenset({"20261113_120000_create_tenant_duty_rules_and_invoice_columns.sql"}),
    ),
    "test_notification_channels_blueprint_key_ddl.py": (
        "text_only",
        "文字として読むだけ",
        frozenset({"20261106_210000_add_notification_channels_blueprint_key.sql"}),
    ),
    "condition_value_columns.py": (
        "text_only",
        "コメント（:6）に名前が出るだけ",
        frozenset({"20260925_010000_conditions_add_match_type.sql"}),
    ),
    "conftest.py": (
        "text_only",
        "コメント（:214・:590）に名前が出るだけ",
        frozenset(
            {
                "20260917_020000_supplier_ssot_migration.sql",
                "20261015_090000_add_leads_assignment_opened_at.sql",
            }
        ),
    ),
    "test_inbox_new_assignment_badge.py": (
        "text_only",
        "SQLite で落ちることを確かめる（共有 DB には流さない）",
        frozenset({"20261015_090000_add_leads_assignment_opened_at.sql"}),
    ),
    "test_value_migrations_neutralized.py": (
        "text_only",
        "流すのは全テナントを回らない4本だけ",
        frozenset(
            {
                "20260611_100000_create_channel_masters.sql",
                "20260613_020000_funnel_close_reasons.sql",
            }
        ),
    ),
    "test_value_migrations_neutralized_3c.py": (
        "text_only",
        "文字として読むだけ",
        frozenset({"063_tenant_rbac_extensions.sql", "069_create_tenant_profile.sql"}),
    ),
    "test_inventory_sprint8_migrations.py": (
        "pg_url_only",
        "TEST_PG_URL があるときだけ動く（CI では skip）",
        frozenset({"069_create_tenant_profile.sql"}),
    ),
    "test_inventory_visibility_permissions.py": (
        "pg_url_only",
        "TEST_PG_URL があるときだけ動く（CI では skip）",
        frozenset({"063_tenant_rbac_extensions.sql"}),
    ),
    "test_leads_assignment_opened_at_pg.py": (
        "own_database",
        "",
        frozenset(
            {
                "20260729_043520_drop_deals.sql",
                "20261015_090000_add_leads_assignment_opened_at.sql",
            }
        ),
    ),
    "test_suppliers_rls.py": (
        "own_database",
        "",
        frozenset({"20260918_030000_supplier_ssot_phase2.sql"}),
    ),
    "test_tcg_condition_review.py": (
        "own_database",
        "",
        frozenset(
            {
                "20260910_160000_tcg_work_evidence.sql",
                "20260917_020000_supplier_ssot_migration.sql",
                "20260920_010000_phase3_fk_rewire_unit_condition.sql",
            }
        ),
    ),
    "test_tcg_extraction_record_pg.py": (
        "own_database",
        "",
        frozenset({"20260914_010000_tcg_extraction_attempts.sql"}),
    ),
    "test_tcg_import_progress_pg.py": (
        "own_database",
        "",
        frozenset(
            {
                "20260910_010000_tcg_import_message_links.sql",
                "20260917_020000_supplier_ssot_migration.sql",
            }
        ),
    ),
    "test_tcg_product_list_pg.py": (
        "own_database",
        "",
        frozenset({"20260920_010000_phase3_fk_rewire_unit_condition.sql"}),
    ),
    "test_tcg_sold_out_results.py": (
        "own_database",
        "",
        frozenset(
            {
                "20260910_010000_tcg_import_message_links.sql",
                "20260917_020000_supplier_ssot_migration.sql",
            }
        ),
    ),
    "test_tcg_work_comparison_pg.py": (
        "own_database",
        "",
        frozenset({"20260910_010000_tcg_import_message_links.sql"}),
    ),
    "test_tcg_work_matching_integration.py": (
        "own_database",
        "",
        frozenset(
            {
                "20260910_010000_tcg_import_message_links.sql",
                "20260910_160000_tcg_work_evidence.sql",
                "20260912_020000_tcg_resolved_work_id.sql",
                "20260914_010000_tcg_extraction_attempts.sql",
                "20260917_010000_add_product_code_to_extraction.sql",
                "20260917_020000_supplier_ssot_migration.sql",
                "20260920_010000_phase3_fk_rewire_unit_condition.sql",
            }
        ),
    ),
    "test_discord_config_rls.py": (
        "own_database",
        "",
        frozenset({"099_add_discord_guild_config.sql", "20260602_120000_add_discord_ticket_config.sql"}),
    ),
    "test_google_webhook_subscriptions_rls.py": (
        "own_database",
        "",
        frozenset({"20261103_200000_add_google_calendar_import_sync.sql"}),
    ),
    "test_tenant_budget_settings_rls.py": (
        "own_database",
        "",
        frozenset({"20260604_220000_create_translation_glossary.sql"}),
    ),
    "test_conversation_unify_bin1.py": (
        "text_only",
        "文字として読むだけ",
        frozenset({"20261108_100000_rebuild_company_stats_on_meta_messages.sql"}),
    ),
    "test_customer_statuses_pg.py": (
        "own_database",
        "",
        frozenset(
            {
                "037_add_pending_dedup_review_to_contacts_check.sql",
                "20261112_140000_customer_status_fk.sql",
            }
        ),
    ),
}

# 同じファイルに2種類の扱いがあるもの（消した表の照合は文字だけ）
_EXTRA_TEXT_ONLY: dict[str, tuple[str, frozenset[str]]] = {
    "test_lead_merge_pg.py": (
        "消した表の照合（:76-79）。文字の照合だけで流さない",
        frozenset(
            {
                "20260601_140000_drop_customers_tables.sql",
                "20260729_043520_drop_deals.sql",
            }
        ),
    ),
}


def _loop_migrations() -> set[str]:
    return {
        p.name
        for p in _MIGRATIONS_DIR.glob("*.sql")
        if _LOOP_RE.search(p.read_text(encoding="utf-8", errors="replace"))
    }


def _actual() -> dict[str, set[str]]:
    loop = _loop_migrations()
    found: dict[str, set[str]] = {}
    for path in sorted(_TESTS_DIR.rglob("*.py")):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        hit = {name for name in _MIGRATION_NAME_RE.findall(text) if name in loop}
        if hit:
            found[path.relative_to(_TESTS_DIR).as_posix()] = hit
    return found


def _expected() -> dict[str, set[str]]:
    expected: dict[str, set[str]] = {}
    for name, (_kind, _why, migrations) in _REVIEWED.items():
        expected.setdefault(name, set()).update(migrations)
    for name, (_why, migrations) in _EXTRA_TEXT_ONLY.items():
        expected.setdefault(name, set()).update(migrations)
    return expected


def test_every_tenant_loop_migration_reference_is_classified():
    actual = _actual()
    expected = _expected()
    pairs_actual = {(f, m) for f, ms in actual.items() for m in ms}
    pairs_expected = {(f, m) for f, ms in expected.items() for m in ms}
    missing = sorted(pairs_actual - pairs_expected)
    stale = sorted(pairs_expected - pairs_actual)
    assert not missing, (
        "全テナントを回す移行を参照する試験が分類表 _REVIEWED に無い（分類を書いてから足す）: "
        + "; ".join(f"{f} -> {m}" for f, m in missing)
    )
    assert not stale, (
        "分類表 _REVIEWED にあるが実物に無い組（表を直す）: " + "; ".join(f"{f} -> {m}" for f, m in stale)
    )


def test_classification_details_hold():
    registered = set(rls_bootstrap._TENANT_LOOP_MIGRATIONS) | set(rls_bootstrap._TENANT_BOOTSTRAP_MIGRATIONS)
    for name, (kind, why, migrations) in _REVIEWED.items():
        text = (_TESTS_DIR / name).read_text(encoding="utf-8", errors="replace")
        if kind == "scoped":
            unregistered = sorted(migrations - registered)
            assert not unregistered, f"{name}: 絞って流す移行が rls_bootstrap に未登録: {unregistered}"
        elif kind == "own_database":
            assert (
                "CREATE DATABASE" in text or "test_tcg_work_matching_integration import" in text
            ), f"{name}: 使い捨て DB を作っていない"
        elif kind == "text_only":
            assert why.strip(), f"{name}: text_only に理由が無い"
        elif kind == "pg_url_only":
            assert why.strip(), f"{name}: pg_url_only に理由が無い"
            assert "TEST_PG_URL" in text, f"{name}: TEST_PG_URL を使っていない"
        else:
            raise AssertionError(f"{name}: 未知の分類 {kind}")
    for name, (why, _migrations) in _EXTRA_TEXT_ONLY.items():
        assert why.strip(), f"{name}: text_only に理由が無い"
