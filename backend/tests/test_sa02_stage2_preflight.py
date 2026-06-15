"""SA-02 Stage2 移行スクリプト プレフライト検証テスト。

検証項目:
  1. --tenant-id 指定時に SQL が ORDER BY の前に WHERE 条件を持つ（SQL インジェクション防止含む）
  2. --dry-run では INSERT が実行されない（stats.inserted/skipped/errors は変化しない）
  3. --dry-run でも stats["total"] は取得できる
  4. --tenant-id なしではパラメータなしで全テナントを取得する
  5. rollback marker（analysis._source = 'sa02_stage2_migration'）が INSERT に含まれる
  6. verify スクリプトの --tenant-id が SQL に正しく反映される
  7. analysis->>'_source' の一致で rollback と verify が整合している
  8. _set_tenant_context が SET LOCAL ではなく set_config() を使う（asyncpg 対応）
  9. dry-run でテナントコンテキスト設定経路が検証される（INSERT なし）
  10. total=0 テナントでは dry-run でもコンテキスト設定が走らない

実行:
    pytest backend/tests/test_sa02_stage2_preflight.py -v
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# スクリプト本体を import するためにパスを通す
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_execute_mock(scalar_value=0, fetchone_value=True, fetchall_value=None):
    """db.execute() の戻り値モック。"""
    m = MagicMock()
    m.scalar.return_value = scalar_value
    m.fetchone.return_value = fetchone_value
    m.fetchall.return_value = fetchall_value or []
    return m


# ---------------------------------------------------------------------------
# 1. --tenant-id SQL: ORDER BY の後に条件が来ない
# ---------------------------------------------------------------------------

def test_migrate_tenant_id_sql_order():
    """--tenant-id 指定時、AND id = ... が ORDER BY の前に挿入される。"""
    from scripts.migrate_sa02_stage2_meta_to_conv_logs import main as _main
    import inspect
    src = inspect.getsource(_main)

    # q += " ORDER BY id" が AND id = の後にあることを確認
    # 修正後は ORDER BY の前に AND id = :target_tenant_id が入る
    assert "AND id = :target_tenant_id" in src, "パラメータ化された tenant_id 条件がない"
    # f-string で直接埋め込んでいないことを確認
    assert 'f" AND id = {target_tenant_id}"' not in src, "f-string で tenant_id を埋め込んでいる（SQLインジェクション危険）"


def test_migrate_tenant_id_sql_order_by_after_where():
    """ORDER BY が WHERE 句の後に来るよう SQL が構築される（ソース検査）。"""
    src = Path(_REPO_ROOT / "scripts" / "migrate_sa02_stage2_meta_to_conv_logs.py").read_text()

    # 修正後のパターン: WHERE ... AND id = :target_tenant_id ... ORDER BY id
    # "ORDER BY id" が q の末尾に append されているか確認
    assert 'q += " ORDER BY id"' in src, "ORDER BY が末尾に追加されていない"
    # AND id 条件が ORDER BY の前（コードテキスト上）に定義されている
    order_pos = src.index('q += " ORDER BY id"')
    and_pos = src.index('q += " AND id = :target_tenant_id"')
    assert and_pos < order_pos, "AND id 条件が ORDER BY より後に定義されている"


# ---------------------------------------------------------------------------
# 2. --dry-run では INSERT を実行しない
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_migrate_tenant_dry_run_no_insert():
    """dry_run=True では INSERT が呼ばれない。テナントコンテキスト設定は走る。"""
    from scripts.migrate_sa02_stage2_meta_to_conv_logs import migrate_tenant

    # engine.connect() — テーブル存在確認 + COUNT 用
    mock_conn = AsyncMock()
    exists_result = MagicMock()
    exists_result.fetchone.return_value = (1,)
    count_result = MagicMock()
    count_result.scalar.return_value = 10  # 10件あり
    mock_conn.execute = AsyncMock(side_effect=[exists_result, exists_result, count_result])

    mock_connect_ctx = AsyncMock()
    mock_connect_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_connect_ctx.__aexit__ = AsyncMock(return_value=False)

    # engine.begin() — dry-run テナントコンテキスト設定用
    mock_begin_conn = AsyncMock()
    mock_begin_conn.execute = AsyncMock(return_value=MagicMock())

    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_begin_conn)
    mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_connect_ctx)
    mock_engine.begin = MagicMock(return_value=mock_begin_ctx)

    stats = await migrate_tenant(mock_engine, tenant_id=1, tenant_code="test", dry_run=True)

    # dry_run=True では INSERT なし
    assert stats["total"] == 10
    assert stats["inserted"] == 0
    assert stats["skipped"] == 0
    assert stats["errors"] == 0

    # engine.begin() が1回呼ばれ（テナントコンテキスト設定）
    mock_engine.begin.assert_called_once()
    # begin() 内の execute は1回（set_config）のみ
    assert mock_begin_conn.execute.call_count == 1

    # set_config を使っていることを確認（SET LOCAL でないこと）
    call_sql = str(mock_begin_conn.execute.call_args[0][0])
    assert "set_config" in call_sql
    assert "SET LOCAL" not in call_sql


# ---------------------------------------------------------------------------
# 3. --dry-run で stats["total"] は取得できる
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_migrate_tenant_dry_run_returns_total():
    """dry_run=True でも stats['total'] が取得できる。"""
    from scripts.migrate_sa02_stage2_meta_to_conv_logs import migrate_tenant

    mock_conn = AsyncMock()
    exists_result = MagicMock()
    exists_result.fetchone.return_value = (1,)
    count_result = MagicMock()
    count_result.scalar.return_value = 42

    mock_conn.execute = AsyncMock(side_effect=[exists_result, exists_result, count_result])

    mock_connect_ctx = AsyncMock()
    mock_connect_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_connect_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_begin_conn = AsyncMock()
    mock_begin_conn.execute = AsyncMock(return_value=MagicMock())
    mock_begin_ctx = AsyncMock()
    mock_begin_ctx.__aenter__ = AsyncMock(return_value=mock_begin_conn)
    mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_connect_ctx)
    mock_engine.begin = MagicMock(return_value=mock_begin_ctx)

    stats = await migrate_tenant(mock_engine, tenant_id=1, tenant_code="test", dry_run=True)
    assert stats["total"] == 42


# ---------------------------------------------------------------------------
# 4. --tenant-id なしでは params が空
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_migrate_main_no_tenant_id_uses_empty_params():
    """target_tenant_id=None のとき、SQL パラメータは空辞書で実行される。"""
    from scripts.migrate_sa02_stage2_meta_to_conv_logs import main

    tenant_row = MagicMock()
    tenant_row.id = 1
    tenant_row.tenant_code = "tenant001"

    mock_conn = AsyncMock()
    tenant_result = MagicMock()
    tenant_result.__iter__ = MagicMock(return_value=iter([tenant_row]))
    mock_conn.execute = AsyncMock(return_value=tenant_result)

    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_ctx)
    mock_engine.dispose = AsyncMock()

    with (
        patch("scripts.migrate_sa02_stage2_meta_to_conv_logs.create_async_engine", return_value=mock_engine),
        patch("scripts.migrate_sa02_stage2_meta_to_conv_logs.migrate_tenant", new=AsyncMock(
            return_value={"total": 0, "inserted": 0, "skipped": 0, "errors": 0}
        )),
        patch.dict("os.environ", {"DATABASE_URL": "postgresql://test/db"}),
    ):
        await main(dry_run=True, target_tenant_id=None)

    # execute の第2引数（params）が空辞書であることを確認
    call_args = mock_conn.execute.call_args
    params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("parameters", {})
    assert params == {}, f"params が空でない: {params}"


# ---------------------------------------------------------------------------
# 5. rollback marker が INSERT 文に含まれる
# ---------------------------------------------------------------------------

def test_migrate_script_has_rollback_marker():
    """移行スクリプトの INSERT に 'sa02_stage2_migration' マーカーが含まれる。"""
    src = Path(_REPO_ROOT / "scripts" / "migrate_sa02_stage2_meta_to_conv_logs.py").read_text()
    assert "sa02_stage2_migration" in src, "rollback marker が INSERT に存在しない"


def test_rollback_marker_matches_verify_script():
    """verify スクリプトの検索条件が移行スクリプトの marker と一致する。"""
    migrate_src = Path(_REPO_ROOT / "scripts" / "migrate_sa02_stage2_meta_to_conv_logs.py").read_text()
    verify_src = Path(_REPO_ROOT / "scripts" / "verify_sa02_stage2_count_check.py").read_text()

    marker = "sa02_stage2_migration"
    assert marker in migrate_src, "移行スクリプトに marker がない"
    assert marker in verify_src, "verify スクリプトの WHERE 条件に marker がない"


# ---------------------------------------------------------------------------
# 6. verify スクリプトの --tenant-id SQL
# ---------------------------------------------------------------------------

def test_verify_script_has_tenant_id_option():
    """verify スクリプトに --tenant-id オプションが存在する。"""
    src = Path(_REPO_ROOT / "scripts" / "verify_sa02_stage2_count_check.py").read_text()
    assert "--tenant-id" in src, "verify スクリプトに --tenant-id がない"
    assert "AND id = :target_tenant_id" in src, "verify スクリプトの tenant_id 条件がパラメータ化されていない"
    assert 'f" AND id = {target_tenant_id}"' not in src, "f-string で直接埋め込んでいる"


def test_verify_script_order_by_after_tenant_condition():
    """verify スクリプトでも ORDER BY が WHERE 条件の後に来る。"""
    src = Path(_REPO_ROOT / "scripts" / "verify_sa02_stage2_count_check.py").read_text()
    assert 'q += " ORDER BY id"' in src, "ORDER BY が末尾に追加されていない"
    order_pos = src.index('q += " ORDER BY id"')
    and_pos = src.index('q += " AND id = :target_tenant_id"')
    assert and_pos < order_pos, "AND id 条件が ORDER BY より後に定義されている"


# ---------------------------------------------------------------------------
# 7. rollback.md と移行スクリプトの削除条件一致
# ---------------------------------------------------------------------------

def test_rollback_doc_marker_matches_script():
    """rollback.md に記載の削除条件が移行スクリプトの marker と一致する。"""
    rollback_md = Path(_REPO_ROOT / "docs" / "handoff" / "sa-02-stage2-migration" / "rollback.md").read_text()
    assert "sa02_stage2_migration" in rollback_md, "rollback.md の削除条件に marker がない"
    assert "analysis->>'_source'" in rollback_md, "rollback.md の条件が analysis JSON を参照していない"


# ---------------------------------------------------------------------------
# 8. _set_tenant_context が set_config() を使う（asyncpg 対応・ソース検査）
# ---------------------------------------------------------------------------

def test_set_tenant_context_uses_set_config():
    """_set_tenant_context が SET LOCAL でなく set_config() を使っている（ソース検査）。"""
    src = Path(_REPO_ROOT / "scripts" / "migrate_sa02_stage2_meta_to_conv_logs.py").read_text()

    assert "_set_tenant_context" in src, "_set_tenant_context 関数が存在しない"
    assert "set_config" in src, "set_config() 呼び出しが存在しない"
    # asyncpg 非互換パターンが SQL 実行コードとして使われていないこと
    # （docstring の説明として「SET LOCAL」が出ることは許容）
    assert 'text("SET LOCAL' not in src, "SET LOCAL を text() SQL として使っている（asyncpg 非互換）"


# ---------------------------------------------------------------------------
# 10. total=0 テナントでは engine.begin() が呼ばれない
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dry_run_total_zero_no_context_call():
    """total=0 のテナントでは dry_run でも engine.begin() が呼ばれない。"""
    from scripts.migrate_sa02_stage2_meta_to_conv_logs import migrate_tenant

    mock_conn = AsyncMock()
    exists_result = MagicMock()
    exists_result.fetchone.return_value = (1,)
    count_result = MagicMock()
    count_result.scalar.return_value = 0  # 0件

    mock_conn.execute = AsyncMock(side_effect=[exists_result, exists_result, count_result])

    mock_connect_ctx = AsyncMock()
    mock_connect_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_connect_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect = MagicMock(return_value=mock_connect_ctx)
    mock_engine.begin = MagicMock()  # begin が呼ばれたら NG

    stats = await migrate_tenant(mock_engine, tenant_id=1, tenant_code="test", dry_run=True)

    assert stats["total"] == 0
    assert stats["inserted"] == 0
    # total=0 のときは engine.begin() を呼ばない
    mock_engine.begin.assert_not_called()
