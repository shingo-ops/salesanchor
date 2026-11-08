"""画面の共通の理由コードの表（frontend/src/lib/apiErrorReason.ts）とサーバーの突き合わせ（ADR-1071 便2）。

サーバーだけを変えた PR でも、表のコードが backend/app から消えていないことを確かめる。
画面だけを変えた PR は frontend/src/lib/apiErrorReason.test.ts が同じことを確かめる。
DB・ネットワークは使わない。
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TABLE = REPO / "frontend" / "src" / "lib" / "apiErrorReason.ts"
APP_DIR = REPO / "backend" / "app"

_ROW = re.compile(r'^\s+([a-z0-9_]+): "apiError\.[A-Za-z0-9]+",?$', re.MULTILINE)


def _codes() -> list[str]:
    return _ROW.findall(TABLE.read_text(encoding="utf-8"))


def test_table_rows_are_read():
    assert _codes() == ["no_fields_to_update", "conflict_constraint"]


def test_table_codes_are_used_in_app():
    sources = "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP_DIR.rglob("*.py")))
    missing = [c for c in _codes() if f'"{c}"' not in sources]
    assert not missing, "表のコードがサーバーで使われていない: " + ", ".join(missing)
