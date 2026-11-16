"""ADR-1061 決定9・A46: 列名の拒否の一覧が3か所でそろっていることを確かめる（DB は使わない）。

正本は backend/app/ops/readonly_query.py の DENY_COLUMN_RE。SQL の2か所（ai_ro と ai_cloud を作る処理）は
Python から読めないので、ファイルの文字を読んで同じことを確かめる。試験の2ファイルは文字を自分で持たない。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.ops.readonly_query import DENY_COLUMN_RE

_ROOT = Path(__file__).resolve().parents[3]
_SQL_FILES = (
    "migrations/20261017_130100_create_ai_ro_views.sql",
    "migrations/20261024_100000_create_ai_cloud_meta.sql",
)
_TEST_FILES = (
    "backend/tests/ops/test_ai_cloud_views.py",
    "backend/tests/ops/test_ai_ro_views.py",
)
_DECL_RE = re.compile(r"deny constant text := '([^']*)';")


@pytest.mark.parametrize("rel", _SQL_FILES)
def test_sql_deny_list_is_same_as_python(rel):
    text = (_ROOT / rel).read_text("utf-8")
    assert _DECL_RE.findall(text) == [DENY_COLUMN_RE.pattern]


@pytest.mark.parametrize("rel", _TEST_FILES)
def test_test_files_import_instead_of_copying(rel):
    text = (_ROOT / rel).read_text("utf-8")
    assert "from app.ops.readonly_query import DENY_COLUMN_RE" in text
    assert "private_key|credential" not in text


@pytest.mark.parametrize(
    "column,hidden",
    [
        ("bank_account_number", True),
        ("iban", True),
        ("IBAN", True),
        ("password_hash", True),
        ("account_number_encrypted", True),
        ("account_holder_name", False),
        ("iban_note", False),
        ("bank_name", False),
    ],
)
def test_new_names_are_hidden_and_neighbours_are_not(column, hidden):
    assert bool(DENY_COLUMN_RE.search(column.lower())) is hidden
