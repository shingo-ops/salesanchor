"""共有 DB の後片付けを、札（public_bootstrap_lock）の外で流す試験を止める見張り（静的・DB を使わない）。

何を見るか:
backend/tests/ の .py を ast で全部読み、関数ごとに、その関数自身の本文の文字列に
「後片付けの文」（スキーマを消す・役割を消す・`public.` の表／行を消す・TRUNCATE）があり、
かつ関数の原文に札の語（`public_bootstrap_lock` など）が無いものを探す。
CI は 1 つの PostgreSQL `jarvis_test_db` を全 worker で共有するため、札なしで消すと別の試験とぶつかる。

新しく足すときの決まり:
1. 共有 DB の後片付けは `public_bootstrap_lock(<その試験の admin engine>)` で囲む。
   消す文の commit まで札の中で終える（札の中で engine.begin() を開く）。
   札の中から、札を取る関数（public_bootstrap_lock を使う関数・bootstrap_public_products など）を呼ばない。
   tenant_schema_lock と並べるときは tenant_schema_lock → public_bootstrap_lock の順（逆にしない）。
   同期 engine は同じ接続で `pg_advisory_lock(20260623, 1)` を取り、finally で外す。
2. 囲めない（使い捨て DB・文字として読むだけ・拒否される前提の文など）ときは、下の `_REVIEWED` に
   `"ファイル(backend/tests からの相対)::関数名": (分類, 理由)` を足す。理由は根拠の file:line を短く書く。
   書くまでこの試験は落ちる。

分類（5 つだけ）:
- own_database   : その試験が CREATE DATABASE した使い捨て DB（ファイルに CREATE DATABASE がある、
                   または test_tcg_work_matching_integration の pg fixture を import している）
- text_only      : SQLite・偽の session・文字として読むだけ・docstring の語
- caller_locked  : 呼び出し元が public_bootstrap_lock の中（同じファイルに public_bootstrap_lock がある）
- tenant_locked  : テナント専用スキーマだけを消し、tenant_schema_lock の中（同じファイルに tenant_schema_lock がある）
- denied_check   : 拒否される前提の文で、取引は巻き戻す（後片付けではない）
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_SELF = Path(__file__).resolve()

# 後片付けの文の種類（正規表現は大文字小文字を区別しない）
KINDS = {
    "drop_schema": re.compile(r"\bDROP\s+SCHEMA\b", re.I),
    "drop_role": re.compile(r"\bDROP\s+(?:ROLE|USER|OWNED)\b", re.I),
    "drop_public_table": re.compile(r"\bDROP\s+TABLE\b(?:\s+IF\s+EXISTS)?\s+(?:ONLY\s+)?\"?public\"?\.", re.I),
    "delete_public_rows": re.compile(r"\bDELETE\s+FROM\s+(?:ONLY\s+)?\"?public\"?\.", re.I),
    "truncate": re.compile(r"\bTRUNCATE\b", re.I),
}

LOCK_WORDS = ("public_bootstrap_lock", "pg_advisory_lock", "pg_advisory_xact_lock", "_public_lock")


def own_strings(fn: ast.AST):
    """関数自身の文字列（入れ子の def の中身は除く）を (行, 文字列) で返す。"""
    stack = list(fn.body)  # type: ignore[attr-defined]
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # 入れ子は別の関数として数える
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.lineno, node.value
        stack.extend(ast.iter_child_nodes(node))


def _scan_source(rel: str, text: str) -> dict[str, set[str]]:
    """1 ファイルの原文を読み、札なしの後片付けの文を持つ関数を `rel::関数名 -> {文の種類}` で返す。"""
    found: dict[str, set[str]] = {}
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        kinds = {k for _ln, s in own_strings(node) for k, rx in KINDS.items() if rx.search(s)}
        if not kinds:
            continue
        segment = ast.get_source_segment(text, node) or ""
        if any(w in segment for w in LOCK_WORDS):
            continue
        found.setdefault(f"{rel}::{node.name}", set()).update(kinds)
    return found


def _actual() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in sorted(_TESTS_DIR.rglob("*.py")):
        if path.resolve() == _SELF:
            continue
        rel = path.relative_to(_TESTS_DIR).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for key, kinds in _scan_source(rel, text).items():
            found.setdefault(key, set()).update(kinds)
    return found


# 札で囲まずに残す関数の分類表。鍵は `ファイル(backend/tests からの相対)::関数名`（行番号は使わない）。値は（分類, 理由）。
# 根拠の file:line は docs/handoff/ci-test-cleanup-lock-guard/recon.md の分類表に対応する。
_REVIEWED: dict[str, tuple[str, str]] = {
    # --- own_database / text_only（recon §2-1） ---
    "ops/test_ai_job_assignments_db.py::test_d_history_is_append_only": (
        "own_database",
        "db fixture が CREATE DATABASE（:102）。文は失敗する前提の確認と使い捨て DB 内",
    ),
    "ops/test_ai_job_assignments_db.py::test_f_get_ai_assignment_reads_choice_and_raises_when_missing": (
        "own_database",
        "db fixture が CREATE DATABASE（:102）。削除は db.cursor()（:309）",
    ),
    "ops/test_ai_job_assignments_db.py::test_h_history_names_fall_back": (
        "own_database",
        "db fixture が CREATE DATABASE（:102）。削除は db.cursor()（:415）",
    ),
    "ops/test_ops_case_db.py::test_t6_app_cannot_change_read_count": (
        "own_database",
        "pg は _new_db（:135 → :91 CREATE DATABASE）。TRUNCATE は拒否の確認（:529）",
    ),
    "test_channel_masters_shared_pg.py::test_deleting_tenant_removes_its_rows_in_both_tables": (
        "own_database",
        "_fresh() が CREATE DATABASE（:58）、使用 :162",
    ),
    "test_discord_config_rls.py::test_update_delete_other_tenant_rows_affect_nothing": (
        "own_database",
        "_fresh()（:124）、使用 :262",
    ),
    "test_discord_server_records_rls.py::test_update_delete_other_tenant_rows_affect_nothing": (
        "own_database",
        "_fresh()（:88）、使用 :216",
    ),
    "test_google_webhook_subscriptions_rls.py::test_update_delete_other_tenant_rows_affect_nothing": (
        "own_database",
        "_fresh()（:74）、使用 :219",
    ),
    "test_inventory_distribution_rows_pg.py::test_b5_item_id_lookup_includes_inactive_posts_with_current_rows_but_the_plain_list_does_not": (
        "own_database",
        "pg fixture（:27 の import → test_tcg_work_matching_integration.py:398）。削除は pg[0]（:254）",
    ),
    "test_inventory_movements_rls.py::test_update_delete_other_tenant_rows_affect_nothing": (
        "own_database",
        "_fresh()（:67）、使用 :189",
    ),
    "test_llm_usage_events_migration_pg.py::test_extraction_shadow_run_id_has_no_fk": (
        "own_database",
        "pg fixture（:22 の import → test_tcg_work_matching_integration.py:398）。表を消すのは pg の接続（:69-71）",
    ),
    "test_meta_channels.py::pg_conn_scopes": (
        "text_only",
        "当たりは docstring の語（:760）。実際の削除は tenant_997 の表の行削除（:764）で public ではない",
    ),
    "test_paypal_regtoken_rls.py::test_other_tenant_and_no_context_cannot_write": (
        "own_database",
        "_fresh()（:61）、使用 :215",
    ),
    "test_paypal_regtoken_rls.py::test_own_tenant_can_insert_update_delete": (
        "own_database",
        "_fresh()（:61）、使用 :276",
    ),
    "test_paypal_regtoken_rls.py::test_tenant_delete_cascades_to_both_tables": (
        "own_database",
        "_fresh()（:61）、使用 :345",
    ),
    "test_product_format_game_links_pg.py::fmt_pg": (
        "own_database",
        "edit_pg（test_tcg_product_detail_pg.py:106）→ pg（test_tcg_work_matching_integration.py:398）",
    ),
    "test_product_format_game_links_pg.py::test_db_rejects_removing_link_in_use": (
        "own_database",
        "fmt_pg の使い捨て DB。削除は FK 違反で拒否される前提（:170）",
    ),
    "test_product_format_game_links_pg.py::test_physical_delete_of_format_in_use_is_rejected": (
        "own_database",
        "fmt_pg の使い捨て DB。拒否される前提（:187）",
    ),
    "test_product_format_game_links_pg.py::test_create_ignores_legacy_type_master_id_and_does_not_return_it": (
        "own_database",
        "fmt_pg の使い捨て DB。削除は fmt_pg['connection']（:307）",
    ),
    "test_rls_tenant_meta_config.py::pg_conn": (
        "text_only",
        "当たりは docstring の語（:172）。実際の削除は tenant_946/947 の表の行削除（:177-178）で public ではない",
    ),
    "test_secretary_rules_tables_pg.py::test_app_role_cannot_delete": (
        "own_database",
        "pg fixture（:17 の import → test_tcg_work_matching_integration.py:398）。削除は拒否の確認（:211 42501）",
    ),
    "test_tcg_condition_review.py::set_max_age_hours": (
        "own_database",
        "pg fixture が CREATE DATABASE（:60）",
    ),
    "test_tcg_import_progress_pg.py::test_later_tcg_schema_provisioning": (
        "own_database",
        "pg fixture が CREATE DATABASE（:59）。消すのは使い捨て DB 内の tenant_873（:409）",
    ),
    "test_tenant_budget_settings_rls.py::test_update_delete_other_tenant_rows_affect_nothing": (
        "own_database",
        "_fresh()（:79）、使用 :241",
    ),
    "test_tenant_deletion.py::test_physical_delete_success": (
        "text_only",
        "SQLite のメモリ（conftest.py:18）と mock（:293-294）。文字列を読むだけ（:322-323）",
    ),
    "test_tenant_service.py::test_named_dollar_tag_function_body": (
        "text_only",
        "SQL を文字列として分割関数へ渡すだけで流さない（:77-92）",
    ),
    "test_tenants_rls.py::test_tenant_context_and_no_context_cannot_write": (
        "own_database",
        "_fresh()（:73）、使用 :209",
    ),
    "test_tenants_rls.py::test_operator_context_can_insert_update_delete": (
        "own_database",
        "_fresh()（:73）、使用 :242",
    ),
    "test_tenants_rls.py::test_operator_delete_cascades_to_children": (
        "own_database",
        "_fresh()（:73）、使用 :261",
    ),
    "test_users_rls.py::test_no_context_cannot_write": (
        "own_database",
        "_fresh()（:95）、使用 :228",
    ),
    "test_users_rls.py::test_tenant_context_writes_only_own_rows": (
        "own_database",
        "_fresh()（:95）、使用 :263",
    ),
    "test_users_rls.py::test_operator_context_can_write_any_tenant": (
        "own_database",
        "_fresh()（:95）、使用 :312",
    ),
    "test_users_rls.py::test_operator_delete_tenant_cascades_to_users": (
        "own_database",
        "_fresh()（:95）、使用 :338",
    ),
    "test_viewer_billing_form_pg.py::test_deleting_viewer_deletes_profile": (
        "own_database",
        "pg fixture（:30 の import → test_tcg_work_matching_integration.py:398）",
    ),
    "test_viewer_contract_public_tables_pg.py::test_public_tables_rls_and_viewer_delete_sets_null": (
        "own_database",
        "pg fixture（:25 → :398）。アプリ接続も conn.info.dbname の同じ使い捨て DB（:82-84）",
    ),
    "test_viewer_discord_trial.py::test_cli_set_config_upserts_single_row": (
        "own_database",
        "pg fixture（:29 → test_tcg_work_matching_integration.py:398）、_prep（:771）",
    ),
    "test_viewer_discord_trial.py::test_list_viewers_returns_channel_url": (
        "own_database",
        "pg fixture（:29 → test_tcg_work_matching_integration.py:398）",
    ),
    "test_viewer_password.py::execute": (
        "text_only",
        "偽の session クラスの execute が文字列で振り分けるだけ（:89-123）。DB に繋がない",
    ),
    "test_viewer_signup.py::execute": (
        "text_only",
        "偽の session クラスの execute が文字列で振り分けるだけ（:78-103）。DB に繋がない",
    ),
    # --- own_database: 使い捨て DB 内の役割（recon §2-5 / design §4-2） ---
    "test_tenant_isolation_daily_check.py::test_b2_bypass_role": (
        "own_database",
        "scratch_db は使い捨て DB（:162）。DROP ROLE（:217）の役割は uuid の名前で一意（:200）",
    ),
    "test_tenant_isolation_daily_check.py::test_b3_plain_role": (
        "own_database",
        "scratch_db は使い捨て DB（:162）。DROP ROLE（:254）の役割は uuid の名前で一意（:227）",
    ),
    # --- caller_locked（recon §2-2） ---
    "test_permission_resolution_pg.py::_remove_test_tenant_rows": (
        "caller_locked",
        "呼び出し元 :98-100 と :241-243 がどちらも public_bootstrap_lock(admin_engine) の中（外側に tenant_schema_lock）",
    ),
    "test_rls_auth_audit.py::_remove_test_tenant_rows": (
        "caller_locked",
        "呼び出し元 :69-71 と :81-83 がどちらも public_bootstrap_lock(admin_engine) の中",
    ),
    # --- tenant_locked ---
    "test_tenant_user_ref_guard_pg.py::env": (
        "tenant_locked",
        "テナント専用スキーマだけを TRUNCATE（:167-169）し、tenant_schema_lock（:141）の中",
    ),
    # --- denied_check ---
    "test_analysis_error_report_tables_rls.py::test_event_update_and_delete_denied_even_with_operator_flag": (
        "denied_check",
        "拒否される前提の DELETE（:155、42501 を確認 :163）。後片付けではない",
    ),
    "test_ops_incident_tables_rls.py::test_delete_denied_even_with_operator_flag": (
        "denied_check",
        "拒否される前提の DELETE（:190、42501 :191）。取引は rollback（:193）",
    ),
    "test_permissions_rls.py::test_permissions_writes_denied_without_operator_flag": (
        "denied_check",
        "WHERE id > 0 の DELETE は行が見えず 0 行の確認（:91-92）で rollback（:94）。後片付けではない",
    ),
    "test_tenant_payment_versioning_pg.py::_check_rules": (
        "denied_check",
        "TRUNCATE は拒否される前提（:292-294）で取引は rollback（:341）。呼び出し元 :302 は tenant_schema_lock（:305）の中",
    ),
}

_CATEGORIES = {"own_database", "text_only", "caller_locked", "tenant_locked", "denied_check"}
_OWN_DB_IMPORT = re.compile(r"test_tcg_work_matching_integration\s+import\b")


def test_every_shared_db_cleanup_is_classified():
    actual = _actual()
    missing = sorted(set(actual) - set(_REVIEWED))
    assert not missing, (
        "共有 DB の後片付け（スキーマ・役割・public の表／行を消す・TRUNCATE）を札なしで流す関数が、"
        "分類表 _REVIEWED に無い。次のどちらかをする: "
        "(1) 後片付けを `async with public_bootstrap_lock(<admin engine>):` で囲む（消す文の commit まで札の中で終える）。"
        "(2) 囲めないなら _REVIEWED に `ファイル::関数名: (分類, 理由)` を足す。"
        "該当: " + "; ".join(f"{k}（{','.join(sorted(actual[k]))}）" for k in missing)
    )


def test_reviewed_entries_still_match():
    actual = _actual()
    stale = sorted(set(_REVIEWED) - set(actual))
    assert not stale, (
        "分類表 _REVIEWED にあるが、実物では当たらない関数（札で囲んだか、関数名・ファイルが変わった）。"
        "表からその行を消すか、名前を直す: " + "; ".join(stale)
    )


def test_classification_details_hold():
    for key, (kind, why) in _REVIEWED.items():
        assert kind in _CATEGORIES, f"{key}: 未知の分類 {kind}（使えるのは {sorted(_CATEGORIES)}）"
        assert why.strip(), f"{key}: 分類 {kind} に理由が無い（根拠の file:line を短く書く）"
        rel = key.split("::", 1)[0]
        path = _TESTS_DIR / rel
        assert path.is_file(), f"{key}: ファイル {rel} が backend/tests に無い"
        text = path.read_text(encoding="utf-8", errors="replace")
        if kind == "own_database":
            assert "CREATE DATABASE" in text or _OWN_DB_IMPORT.search(text), (
                f"{key}: own_database なのに使い捨て DB を作っていない"
                "（ファイルに CREATE DATABASE が無く、test_tcg_work_matching_integration の pg も import していない）"
            )
        elif kind == "caller_locked":
            assert "public_bootstrap_lock" in text, f"{key}: caller_locked なのに同じファイルに public_bootstrap_lock が無い"
        elif kind == "tenant_locked":
            assert "tenant_schema_lock" in text, f"{key}: tenant_locked なのに同じファイルに tenant_schema_lock が無い"


# 仮の原文（札なしで public の行・スキーマ・役割などを消す関数）。見張りの探し方が生きていることを確かめる。
_FAKE_UNLOCKED = '''
async def _cleanup(engine):
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM public.some_table WHERE id = 1"))
        await conn.execute(text("DROP SCHEMA IF EXISTS tenant_x CASCADE"))
        await conn.execute(text("DROP ROLE IF EXISTS some_role"))
        await conn.execute(text("DROP TABLE IF EXISTS public.some_table"))
        await conn.execute(text("TRUNCATE some_table"))
'''

_FAKE_LOCKED = '''
async def _cleanup(engine):
    async with public_bootstrap_lock(engine), engine.begin() as conn:
        await conn.execute(text("DELETE FROM public.some_table WHERE id = 1"))
'''


def test_scan_catches_unlocked_cleanup_and_accepts_locked_one():
    hit = _scan_source("fake.py", _FAKE_UNLOCKED)
    assert set(hit) == {"fake.py::_cleanup"}, "札なしで public の行を消す関数に当たらない（探し方が壊れている）"
    assert hit["fake.py::_cleanup"] == set(KINDS), "仮の原文の 5 種類の文のうち、当たらない種類がある"
    # 札の語（public_bootstrap_lock）を足すと当たらない
    assert _scan_source("fake.py", _FAKE_LOCKED) == {}, "public_bootstrap_lock で囲んだ関数に当たってしまう"
    # 札の語はどれでも外れる
    for word in LOCK_WORDS:
        patched = _FAKE_UNLOCKED.replace("    async with engine.begin()", f"    # {word}\n    async with engine.begin()")
        assert _scan_source("fake.py", patched) == {}, f"札の語 {word} を足しても当たったまま"
