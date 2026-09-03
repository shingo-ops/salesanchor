"""
PARITY-03 MANUAL 保護テスト。

再解析（R-1: analyze_extraction_job）が pid_basis='MANUAL' の行を
上書きしないことを検証する。

カバー:
  - _apply_pid_guard: MANUAL 行は locked 値を返す（純 Python）
  - _apply_pid_guard: 非 MANUAL 行はエンジン計算値を返す（純 Python）
  - _apply_pid_guard: manual_locks が空の場合は全行がエンジン計算値を返す

DB 不要（純 Python ロジックのみ）。
"""
from __future__ import annotations

import pytest

from app.services.tcg_analyzer_svc import _apply_pid_guard

# ---------------------------------------------------------------------------
# テストデータ
# ---------------------------------------------------------------------------

_ITEM_ID_MANUAL = "aaaaaaaa-0000-0000-0000-000000000001"
_ITEM_ID_AUTO = "bbbbbbbb-0000-0000-0000-000000000002"
_LOCKED_PRODUCT_UUID = "cccccccc-0000-0000-0000-000000000003"
_COMPUTED_PRODUCT_UUID = "dddddddd-0000-0000-0000-000000000004"

_MANUAL_LOCKS = {
    _ITEM_ID_MANUAL: (_LOCKED_PRODUCT_UUID, "MANUAL"),
}


# ---------------------------------------------------------------------------
# _apply_pid_guard
# ---------------------------------------------------------------------------


class TestApplyPidGuard:
    """pid_basis='MANUAL' 行の再解析上書き防止ロジックを検証する。"""

    def test_manual_locked_item_preserves_locked_product(self):
        """MANUAL ロック済み行: エンジン計算値でなく locked product_id を返す。"""
        product_uuid, pid_resolved, pid_basis = _apply_pid_guard(
            _MANUAL_LOCKS,
            _ITEM_ID_MANUAL,
            computed_product_uuid=_COMPUTED_PRODUCT_UUID,
            computed_pid_resolved=False,
            computed_pid_basis="NONE",
        )
        assert product_uuid == _LOCKED_PRODUCT_UUID
        assert pid_resolved is True
        assert pid_basis == "MANUAL"

    def test_manual_locked_item_ignores_computed_values(self):
        """MANUAL ロック済み行: エンジンが別の product を返しても上書きしない。"""
        some_other_uuid = "eeeeeeee-0000-0000-0000-000000000005"
        product_uuid, pid_resolved, pid_basis = _apply_pid_guard(
            _MANUAL_LOCKS,
            _ITEM_ID_MANUAL,
            computed_product_uuid=some_other_uuid,
            computed_pid_resolved=True,
            computed_pid_basis="SK:ポケモン",
        )
        assert product_uuid == _LOCKED_PRODUCT_UUID
        assert pid_resolved is True
        assert pid_basis == "MANUAL"

    def test_non_manual_item_uses_computed_values(self):
        """MANUAL ロックなし行: エンジン計算値をそのまま返す。"""
        product_uuid, pid_resolved, pid_basis = _apply_pid_guard(
            _MANUAL_LOCKS,
            _ITEM_ID_AUTO,
            computed_product_uuid=_COMPUTED_PRODUCT_UUID,
            computed_pid_resolved=True,
            computed_pid_basis="SK:ポケモン",
        )
        assert product_uuid == _COMPUTED_PRODUCT_UUID
        assert pid_resolved is True
        assert pid_basis == "SK:ポケモン"

    def test_empty_locks_always_uses_computed_values(self):
        """manual_locks が空: 全行がエンジン計算値を返す（MANUAL 行なし時の正常系）。"""
        product_uuid, pid_resolved, pid_basis = _apply_pid_guard(
            {},
            _ITEM_ID_MANUAL,
            computed_product_uuid=_COMPUTED_PRODUCT_UUID,
            computed_pid_resolved=False,
            computed_pid_basis="NONE",
        )
        assert product_uuid == _COMPUTED_PRODUCT_UUID
        assert pid_resolved is False
        assert pid_basis == "NONE"

    def test_manual_item_with_none_product_uuid_preserves_none(self):
        """MANUAL ロック済み行: locked product_id が None でも保持する（エッジケース）。"""
        locks_with_none = {_ITEM_ID_MANUAL: (None, "MANUAL")}
        product_uuid, pid_resolved, pid_basis = _apply_pid_guard(
            locks_with_none,
            _ITEM_ID_MANUAL,
            computed_product_uuid=_COMPUTED_PRODUCT_UUID,
            computed_pid_resolved=True,
            computed_pid_basis="SK:ポケモン",
        )
        assert product_uuid is None
        assert pid_resolved is True
        assert pid_basis == "MANUAL"
