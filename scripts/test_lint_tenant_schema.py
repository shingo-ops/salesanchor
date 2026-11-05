"""ADR-072 Phase 3: scripts/lint_tenant_schema.py の単体テスト。

positive (違反検出) / negative (clean) ケースを文字列で in-memory に与えて、
linter の出力を確認する。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

# scripts/ を sys.path に追加 (CI / ローカル両方で動くように)
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from lint_tenant_schema import lint_file  # noqa: E402


def _write_tmp(src: str) -> Path:
    """tmp .py を作って lint_file に渡せる Path を返す。"""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    f.write(textwrap.dedent(src))
    f.close()
    return Path(f.name)


# ──────────────────────────────────────────────────────────────────
# Negative cases (clean): 違反ゼロ
# ──────────────────────────────────────────────────────────────────


def test_get_endpoint_no_commit_is_clean():
    """read-only endpoint で bare-table があっても commit がなければ違反なし。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.get("/leads")
        async def list_leads(
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            await db.execute(text("SELECT * FROM leads"))
            return []
    """)
    assert lint_file(p) == []


def test_endpoint_with_tenant_table_ref_is_clean():
    """tenant_table_ref を使っている案 A 採用関数は違反なし。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.post("/leads")
        async def create_lead(
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            leads_t = tenant_table_ref(db, tenant_id, "leads")
            await db.execute(text(f"INSERT INTO {leads_t} ..."))
            await db.commit()
            return {}
    """)
    assert lint_file(p) == []


def test_endpoint_with_reset_tenant_context_is_clean():
    """reset_tenant_context を呼んでいる案 B 採用関数は違反なし。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.delete("/staff/{sid}")
        async def delete_staff(
            sid: int,
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            await db.execute(text("DELETE FROM staff WHERE id = :id"), {"id": sid})
            await db.commit()
            await reset_tenant_context(db, tenant_id)
    """)
    assert lint_file(p) == []


def test_endpoint_without_tenant_id_dep_is_skipped():
    """tenant_id 依存なし (super_admin 系) は対象外。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.post("/super-admin/foo")
        async def create_foo(
            db: AsyncSession = Depends(get_db),
        ):
            await db.execute(text("INSERT INTO leads ..."))
            await db.commit()
    """)
    assert lint_file(p) == []


def test_endpoint_with_url_path_tenant_id_is_skipped():
    """super_admin 系の URL path param `tenant_id: int` は対象外
    (`Depends(get_current_tenant)` 経由ではないため、public スキーマ操作前提)。
    """
    p = _write_tmp("""
        from sqlalchemy import text

        @router.put("/super-admin/foo/{tenant_id}")
        async def upsert_foo(
            tenant_id: int,
            db: AsyncSession = Depends(get_db),
        ):
            await db.execute(text("INSERT INTO public.foo (...) VALUES (...)"))
            await db.commit()
    """)
    assert lint_file(p) == []


def test_endpoint_with_query_param_tenant_id_is_skipped():
    """Query param の `tenant_id` も対象外
    (`Depends(get_current_tenant)` 経由ではない)。
    """
    p = _write_tmp("""
        from sqlalchemy import text

        @router.get("/super-admin/foo")
        async def list_foo(
            tenant_id: int = Query(...),
            db: AsyncSession = Depends(get_db),
        ):
            await db.execute(text("SELECT 1"))
    """)
    assert lint_file(p) == []


def test_non_router_function_is_skipped():
    """通常の async 関数 (内部 helper) は endpoint と認識しない（Rule A・B）。
    Rule C の対象だが commit が最後なので違反なし。"""
    p = _write_tmp("""
        from sqlalchemy import text

        async def _internal_helper(db, tenant_id: int):
            await db.execute(text("SELECT * FROM staff"))
            await db.commit()
    """)
    assert lint_file(p) == []


# ──────────────────────────────────────────────────────────────────
# Positive cases (violation): 検出されるべき
# ──────────────────────────────────────────────────────────────────


def test_rule_a_bare_table_with_commit_no_helper():
    """commit を含む endpoint で bare-table、helper も reset もなし → Rule A 違反。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.post("/leads")
        async def create_lead(
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            await db.execute(text("INSERT INTO leads (id) VALUES (1)"))
            await db.commit()
    """)
    violations = lint_file(p)
    rules = [v.rule for v in violations]
    assert "A" in rules
    assert any("leads" in v.message for v in violations)


def test_rule_b_write_endpoint_commit_without_reset():
    """write endpoint で commit > reset → Rule B 違反。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.post("/foo")
        async def create_foo(
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            await db.execute(text("SELECT 1"))
            await db.commit()
    """)
    violations = lint_file(p)
    rules = [v.rule for v in violations]
    assert "B" in rules


def test_rule_b_partial_reset_still_violation():
    """commit が 2 つあって reset が 1 つだけなら不足分が違反。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.patch("/foo")
        async def update_foo(
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            await db.execute(text("SELECT 1"))
            await db.commit()
            await db.execute(text("SELECT 2"))
            await db.commit()
            await reset_tenant_context(db, tenant_id)
    """)
    violations = lint_file(p)
    rules = [v.rule for v in violations]
    assert "B" in rules


def test_schema_qualified_text_is_not_flagged():
    """f-string で schema 修飾済の text は Rule A 違反にならない。"""
    p = _write_tmp("""
        from sqlalchemy import text

        @router.post("/leads")
        async def create_lead(
            db: AsyncSession = Depends(get_db),
            tenant_id: int = Depends(get_current_tenant),
        ):
            leads_t = tenant_table_ref(db, tenant_id, "leads")
            await db.execute(text(f"INSERT INTO {leads_t} ..."))
            await db.commit()
    """)
    violations = lint_file(p)
    # has_helper=True なので Rule A も Rule B も発火しないはず
    assert violations == []


# ──────────────────────────────────────────────────────────────────
# 終了コード (CI と同じく別プロセスの命令として流す)
# ──────────────────────────────────────────────────────────────────
# CI の必須チェックは `python3 scripts/lint_tenant_schema.py --mode strict <path>` の
# 終了コードだけで止まるかを決める。lint_file() だけでは sys.exit(main()) を通った
# 終了コードを確かめられないため、命令として流して returncode を見る。

_LINT_SCRIPT = _SCRIPT_DIR / "lint_tenant_schema.py"

_VIOLATION_SRC = """
    from sqlalchemy import text

    @router.post("/leads")
    async def create_lead(
        db: AsyncSession = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant),
    ):
        await db.execute(text("INSERT INTO leads (id) VALUES (1)"))
        await db.commit()
"""

_CLEAN_SRC = """
    from sqlalchemy import text

    @router.post("/leads")
    async def create_lead(
        db: AsyncSession = Depends(get_db),
        tenant_id: int = Depends(get_current_tenant),
    ):
        leads_t = tenant_table_ref(db, tenant_id, "leads")
        await db.execute(text(f"INSERT INTO {leads_t} ..."))
        await db.commit()
        await reset_tenant_context(db, tenant_id)
"""


def _run_lint(mode: str, src: str) -> "subprocess.CompletedProcess[str]":
    """一時ファイルを作って linter を別プロセスで流し、終了後に一時ファイルを消す。"""
    p = _write_tmp(src)
    try:
        return subprocess.run(
            [sys.executable, str(_LINT_SCRIPT), "--mode", mode, str(p)],
            capture_output=True,
            text=True,
        )
    finally:
        p.unlink(missing_ok=True)


def test_strict_mode_violation_exits_1():
    """strict + 違反ファイル → 終了コード 1、stderr に failing CI。"""
    r = _run_lint("strict", _VIOLATION_SRC)
    assert r.returncode == 1
    assert "mode=strict: failing CI" in r.stderr


def test_strict_mode_clean_exits_0():
    """strict + 正しいファイル → 終了コード 0。"""
    r = _run_lint("strict", _CLEAN_SRC)
    assert r.returncode == 0


def test_warning_mode_violation_exits_0():
    """warning + 違反ファイル → 終了コード 0 (strict との取り違えに気づく)。"""
    r = _run_lint("warning", _VIOLATION_SRC)
    assert r.returncode == 0


# ──────────────────────────────────────────────────────────────────
# Rule C (commit 後の会社付け直し漏れ): 合格の形 (K3) / 違反の形 / 直す前の形 (K1)
# ──────────────────────────────────────────────────────────────────


def _rule_c(src: str):
    return [v for v in lint_file(_write_tmp(src)) if v.rule == "C"]


def test_rule_c_ok_alias_reset_name():
    """別名 import (`reset_tenant_context as _reset_ctx`) で付け直しても違反なし。"""
    assert _rule_c("""
        from app.auth.dependencies import reset_tenant_context as _reset_ctx

        async def svc(db, tenant_id: int):
            await db.commit()
            await _reset_ctx(db, tenant_id)
            return await db.execute("x")
    """) == []


def test_rule_c_ok_url_tenant_id_endpoint():
    """URL の tenant_id を受ける endpoint (Depends でない) は対象外。"""
    assert _rule_c("""
        @router.post("/t/{tenant_id}")
        async def f(tenant_id: int, db=Depends(get_db)):
            await db.commit()
            return await db.execute("x")
    """) == []


def test_rule_c_ok_commit_is_last():
    """commit が最後の文なら違反なし。"""
    assert _rule_c("""
        async def svc(db, tenant_id: int):
            await db.execute("x")
            await db.commit()
    """) == []


def test_rule_c_ok_commit_in_try_then_return_only():
    """try の中の commit の後が db を使わない return だけなら違反なし。"""
    assert _rule_c("""
        async def svc(db, tenant_id: int):
            try:
                await db.commit()
            except Exception:
                raise
            return {}
    """) == []


def test_rule_c_ok_commit_in_if_reset_right_after_if():
    """if の中の commit の後、if の外の直後に reset があれば違反なし。"""
    assert _rule_c("""
        async def svc(db, tenant_id: int, flag):
            if flag:
                await db.commit()
            await reset_tenant_context(db, tenant_id)
            return await db.execute("x")
    """) == []


def test_rule_c_ok_sync_def_is_skipped():
    """同期の def は対象外。"""
    assert _rule_c("""
        def svc(db, tenant_id: int):
            db.commit()
            db.execute("x")
    """) == []


def test_rule_c_violation_conditional_reset():
    """commit の次が条件付きの付け直しなら違反。"""
    vs = _rule_c("""
        async def svc(db, tenant_id: int, x):
            await db.commit()
            if x:
                await reset_tenant_context(db, tenant_id)
            return 1
    """)
    assert len(vs) == 1
    assert vs[0].function == "svc"


def test_rule_c_violation_with_statement_uses_db():
    """commit の次が db を使う with 文なら違反。"""
    assert len(_rule_c("""
        async def svc(db, tenant_id: int):
            await db.commit()
            async with db.begin():
                pass
    """)) == 1


def test_rule_c_violation_decorated_non_router_function():
    """router 以外の飾り付きで db と tenant_id を持つ関数も対象。"""
    assert len(_rule_c("""
        @some_decorator
        async def svc(db, tenant_id: int):
            await db.commit()
            row = await db.execute("x")
            return row
    """)) == 1


def test_rule_c_violation_pre_fix_calendar_shape():
    """K1: 直す前の予定のコードの形 (commit の後に付け直さず db で読み直す)。"""
    vs = _rule_c("""
        async def create_event(db, tenant_id: int):
            db.add(1)
            await db.commit()
            await db.refresh(1)
            return 1

        async def delete_event(db, tenant_id: int):
            await db.commit()
            row = await db.execute("x")
            return row
    """)
    assert [v.function for v in vs] == ["create_event", "delete_event"]
    assert all(v.rule == "C" for v in vs)
