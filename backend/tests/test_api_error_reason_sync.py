"""画面の理由コードの表（frontend/src/lib/apiErrorReason.ts）とサーバーの突き合わせ（ADR-1071 便2・便3）。

サーバーだけを変えた PR でも、表とサーバーの理由コードがずれていないことを確かめる。
画面だけを変えた PR は frontend/src/lib/apiErrorReason.test.ts が同じことを確かめる。
DB・ネットワークは使わない。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "frontend" / "src" / "lib" / "apiErrorReason.ts"
APP_DIR = REPO / "backend" / "app"

# 便2 の表の行（例 `  no_fields_to_update: "apiError.noFieldsToUpdate",`）
_ROW = re.compile(r'^\s+([a-z0-9_]+): "apiError\.[A-Za-z0-9]+",?$', re.MULTILINE)
# 便3 の表の行（例 `  lead: "apiError.notFoundTarget.lead",`。キーと対象が同じ名前のものだけ）
_TARGET_ROW = re.compile(r'^\s+([a-z0-9_]+): "apiError\.notFoundTarget\.\1",?$', re.MULTILINE)
# サーバーの「見つからない」の detail（例 "not_found:lead"）
_APP_TARGET = re.compile(r'"not_found:([a-z0-9_]+)"')


def _table() -> str:
    return TABLE.read_text(encoding="utf-8")


def _codes() -> list[str]:
    return _ROW.findall(_table())


def _targets() -> list[str]:
    return _TARGET_ROW.findall(_table())


def _app_sources() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_DIR.rglob("*.py")))


def test_table_rows_are_read():
    assert _codes() == [
        "no_fields_to_update",
        "conflict_constraint",
        "role_not_editable_here",
        "role_not_deletable",
        "role_permissions_edit_forbidden",
        "role_permissions_not_editable_here",
        "role_page_keys_not_savable",
        "role_not_assignable",
        "merge_target_archived",
        "bill_to_country",
        "recurrence_meet_not_allowed",
        "recurrence_not_available",
        "recurrence_after_until",
        "recurrence_scope_not_allowed",
        "recurrence_google_source",
        "recurrence_scope_required",
        "recurrence_occurrence_invalid",
        "recurrence_this_not_allowed",
    ]


def test_table_codes_are_used_in_app():
    sources = _app_sources()
    missing = [c for c in _codes() if f'"{c}"' not in sources]
    assert not missing, "表のコードがサーバーで使われていない: " + ", ".join(missing)


def test_not_found_table_rows_are_read():
    targets = _targets()
    assert len(targets) == 66
    assert len(set(targets)) == 66


def test_not_found_targets_match_app():
    used = set(_APP_TARGET.findall(_app_sources()))
    table = set(_targets())
    assert not used - table, "サーバーの not_found の対象が画面の表に無い: " + ", ".join(sorted(used - table))
    assert not table - used, "画面の表の対象がサーバーで使われていない: " + ", ".join(sorted(table - used))
