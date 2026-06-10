"""ADR-072 / ADR-131 / ADR-132: テナントコンテキスト管理の回帰保護。

ADR-072 Phase 2 (PR #780):
  `reset_tenant_context` を shifts / suppliers / staff / roles の write endpoint に展開。
  各 router でのコール数を固定してリグレッションを防ぐ。

ADR-131 (PR #1900):
  `get_db` の finally ブロックで `clear_tenant_context` を呼び、コネクションプール返却前に
  テナント文脈を必ずクリアする。ソース検査 + 動作テスト（success/exception パス）で保証。

ADR-132 最小修正 (PR #1900):
  `process_messenger_event` の `async with AsyncSessionLocal()` ブロックを try/finally で
  ラップし、正常・例外・continue のすべてのパスで `clear_tenant_context` を呼ぶ。
"""
from __future__ import annotations

import inspect

import pytest

from app.routers import roles, shifts, staff, suppliers


# ─────────────────────────────────────────────────────────
# ADR-072 Phase 2: 既存 reset_tenant_context ロールアウト保護
# ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("module", [shifts, suppliers, staff, roles])
def test_phase_2_routers_import_reset_tenant_context(module):
    """4 router 全てで `reset_tenant_context` を import している。"""
    src = inspect.getsource(module)
    assert "reset_tenant_context" in src, (
        f"{module.__name__} should import reset_tenant_context from app.auth.dependencies"
    )


_EXPECTED_RESET_CALLS = {
    # router_module_name: count of `await reset_tenant_context(db, tenant_id)`
    # staff.py: create / update / delete / patch-me-profile の 4 箇所
    #   (L228 / L252 は public.users 操作なので Phase 2 対象外)
    "staff": 4,
    # suppliers.py: create / update / delete の 3 箇所
    "suppliers": 3,
    # roles.py: create / update / delete / set_permissions / set_user_roles の 5 箇所
    "roles": 5,
    # shifts.py: create / delete の 2 箇所
    "shifts": 2,
}


@pytest.mark.parametrize("name,expected", list(_EXPECTED_RESET_CALLS.items()))
def test_phase_2_routers_reset_call_count(name, expected):
    """各 router の `reset_tenant_context(db, tenant_id)` 呼び出し数が期待値と一致する。

    削除されたり commit と reset の対応が崩れると Phase 2 の意図が消えるため
    回帰保護として件数で固定する (ADR-072 §「決定」§5 / Phase 2 移行計画)。
    """
    mod = __import__(f"app.routers.{name}", fromlist=[""])
    src = inspect.getsource(mod)
    actual = src.count("await reset_tenant_context(db, tenant_id)")
    assert actual == expected, (
        f"{name}.py: expected {expected} reset_tenant_context() calls, got {actual}. "
        f"ADR-072 Phase 2 の意図が崩れている可能性。`docs/adr/ADR-072-*.md` §5 参照。"
    )


def test_dashboard_router_is_read_only():
    """ADR-072 Phase 2: dashboard.py は read-only (`commit()` ゼロ件) のため reset_tenant_context 不要。"""
    from app.routers import dashboard

    src = inspect.getsource(dashboard)
    assert "await db.commit()" not in src, (
        "dashboard.py is expected to be read-only (no commit). "
        "もし commit が追加されたなら ADR-072 Phase 2 の判定を更新すること。"
    )


# ─────────────────────────────────────────────────────────
# ADR-131: get_db finally による自動クリア（AC-1〜AC-5）
# ─────────────────────────────────────────────────────────

def test_get_db_has_clear_tenant_context_in_finally():
    """AC-5: get_db のソースに clear_tenant_context と finally が存在すること。

    このテストが CI で green であり続ける限り、get_db から
    clear_tenant_context を除去するとこのテストが red になる（AC-5）。
    """
    from app.database import get_db

    src = inspect.getsource(get_db)
    assert "clear_tenant_context" in src, (
        "get_db must call clear_tenant_context (ADR-131). "
        "database.py の get_db に finally ブロックがない。"
    )
    assert "finally" in src, (
        "get_db must have a finally block to guarantee cleanup (ADR-131)."
    )


@pytest.mark.asyncio
async def test_get_db_clears_context_on_success():
    """AC-1: 正常終了後に clear_tenant_context が呼ばれること。"""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, patch

    mock_session = AsyncMock()
    cleared: list = []

    async def fake_clear(db):
        cleared.append(db)

    @asynccontextmanager
    async def fake_session_factory():
        yield mock_session

    with patch("app.database.AsyncSessionLocal", fake_session_factory), \
         patch("app.auth.dependencies.clear_tenant_context", side_effect=fake_clear):
        from app.database import get_db
        async for session in get_db():
            assert session is mock_session

    assert len(cleared) == 1, "clear_tenant_context should be called exactly once on success"
    assert cleared[0] is mock_session


@pytest.mark.asyncio
async def test_get_db_clears_context_on_exception():
    """AC-2: 例外が発生した後も clear_tenant_context が呼ばれること。

    Python の async for はループ本体の例外でジェネレータを close しない（PEP 525: 非同期
    ジェネレータの finalize は GC / イベントループフックに委ねられる）。FastAPI は
    Depends で解決した generator を request 終了時に aclose() し、finally を保証する。
    このテストも明示的に gen.aclose() を呼んで FastAPI の動作を模倣する。
    """
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, patch

    mock_session = AsyncMock()
    cleared: list = []

    async def fake_clear(db):
        cleared.append(db)

    @asynccontextmanager
    async def fake_session_factory():
        yield mock_session

    with patch("app.database.AsyncSessionLocal", fake_session_factory), \
         patch("app.auth.dependencies.clear_tenant_context", side_effect=fake_clear):
        from app.database import get_db
        gen = get_db()
        try:
            async for session in gen:
                raise ValueError("simulated endpoint error")
        except ValueError:
            pass
        finally:
            # FastAPI が request 後に aclose() を呼ぶ動作を再現。
            # これにより get_db の finally ブロック（clear_tenant_context）が実行される。
            await gen.aclose()

    assert len(cleared) == 1, "clear_tenant_context should be called even when exception raised"
    assert cleared[0] is mock_session


def test_get_db_no_op_without_tenant_context():
    """AC-3: テナントコンテキスト未設定リクエストで clear_tenant_context を呼んでも
    500 にならないこと（SQLite では no-op）。

    clear_tenant_context は _dialect_supports_search_path で SQLite を検出し
    no-op になるため、テスト環境で例外を投げないことを確認する。
    """
    import asyncio
    from unittest.mock import MagicMock

    from sqlalchemy.ext.asyncio import AsyncSession

    mock_db = MagicMock(spec=AsyncSession)
    # SQLite dialect を模擬: get_bind() → bind.dialect.name = "sqlite"
    mock_bind = MagicMock()
    mock_bind.dialect.name = "sqlite"
    mock_db.get_bind.return_value = mock_bind

    from app.auth.dependencies import clear_tenant_context
    # no-op パスは同期的に返る（SET を実行しない）ため awaitable ではないが
    # asyncio.run で呼んでも例外が出ないことを確認する
    asyncio.run(clear_tenant_context(mock_db))


# ─────────────────────────────────────────────────────────
# ADR-132 最小修正: process_messenger_event finally クリア（AC-8）
# ─────────────────────────────────────────────────────────

def test_process_messenger_event_has_clear_tenant_context_in_finally():
    """AC-8: process_messenger_event の async with ブロックが finally で
    clear_tenant_context を呼ぶこと（正常・例外・continue のすべてのパスを保護）。

    このテストが CI で green であり続ける限り、finally 削除で red になる（AC-8 自己検証）。
    """
    from app.routers.webhook import process_messenger_event

    src = inspect.getsource(process_messenger_event)
    assert "clear_tenant_context" in src, (
        "process_messenger_event must call clear_tenant_context (ADR-132). "
        "webhook.py の async with ブロックに finally がない。"
    )
    assert "finally" in src, (
        "process_messenger_event must have a finally block for clear_tenant_context (ADR-132)."
    )
