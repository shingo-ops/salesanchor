"""ADR-1037 便1.2（K12）：移行中の読み取り計測の表一覧が、在庫表の GET が読む表とずれないことを止める試験。

DB は使わない。在庫表の GET（list_inventory_view）が呼ぶ6関数のソースから表名を拾い、
scripts/run_all_migrations.sh の READ_PROBE_TABLES と突き合わせる（design.md §14-5）。
限界: この6関数が呼ぶ先の関数はたどらない。list_inventory_view が新しい関数を呼ぶようになったら、下の一覧に足す。
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "run_all_migrations.sh"

# (ファイル, 関数名)。認証（auth/dependencies.py）は users だけを別枠で足す。
INVENTORY_FUNCTIONS = [
    ("backend/app/services/tcg_distribution_svc.py", "load_distribution_settings"),
    ("backend/app/services/tcg_distribution_svc.py", "distribution_rows_parts"),
    ("backend/app/services/tcg_condition_review_svc.py", "source_cte"),
    ("backend/app/services/tcg_condition_review_svc.py", "review_joins"),
    ("backend/app/services/tcg_result_order.py", "result_order_sql"),
    ("backend/app/routers/inventory_offers.py", "_build_inventory_view_sql"),
]
# ビュー → 元の表（ビューを読むと移行と鍵の取る順が逆になり、deadlock の相手になりうるため表を直接読む）
VIEW_TO_TABLE = {"conditions": "line_conditions"}
# 認証が毎回読む表（dependencies.py:95）。関数の拾い出しの対象外なので別に足す
AUTH_TABLES = {"users"}

TABLE_RE = re.compile(r"(?:public|\{TCG_SCHEMA\}|\{schema\})\.([a-z_]+)")


def _function_source(rel_path: str, name: str) -> str:
    src = (ROOT / rel_path).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            seg = ast.get_source_segment(src, node)
            assert seg, f"{rel_path}: {name} のソースが取れない"
            return seg
    raise AssertionError(f"{rel_path}: 関数 {name} が見つからない（名前が変わった。この試験の一覧を直す）")


def _inventory_tables() -> set[str]:
    found: set[str] = set()
    for rel_path, name in INVENTORY_FUNCTIONS:
        found |= set(TABLE_RE.findall(_function_source(rel_path, name)))
    return {VIEW_TO_TABLE.get(t, t) for t in found}


def _probe_tables(text: str | None = None) -> set[str]:
    text = SCRIPT.read_text(encoding="utf-8") if text is None else text
    block = re.search(r"^# >>> read-probe begin$(.*?)^# <<< read-probe end$", text, re.S | re.M)
    assert block, "read-probe の目印（begin / end）が見つからない"
    lines = re.findall(r'^READ_PROBE_TABLES="\$\{READ_PROBE_TABLES:-([^}]*)\}"$', block.group(1), re.M)
    assert len(lines) == 1, f"READ_PROBE_TABLES の行が {len(lines)} 件（ちょうど1件のはず）"
    return set(lines[0].split())


def _compare(inventory: set[str], probe: set[str]) -> tuple[set[str], set[str]]:
    missing = (inventory | AUTH_TABLES) - probe  # 在庫表が読むのに計測に無い
    extra = probe - inventory - AUTH_TABLES  # 計測にあるのに在庫表が読まない
    return missing, extra


def test_inventory_tables_are_found():
    tables = _inventory_tables()
    assert len(tables) >= 10, f"拾えた表が少なすぎる（正規表現かソースの書き方が変わった）: {sorted(tables)}"


def test_probe_tables_match_inventory_query():
    missing, extra = _compare(_inventory_tables(), _probe_tables())
    assert not missing, f"在庫表のクエリが読むのに READ_PROBE_TABLES に無い: {sorted(missing)}"
    assert not extra, f"READ_PROBE_TABLES にあるのに在庫表のクエリが読まない: {sorted(extra)}"


def test_mismatch_is_detected_when_a_table_is_removed_or_added():
    inventory = _inventory_tables()
    probe = _probe_tables()
    victim = sorted(probe - AUTH_TABLES)[0]
    missing, _ = _compare(inventory, probe - {victim})
    assert victim in missing  # 1表抜くと「無い」で落ちる
    _, extra = _compare(inventory, probe | {"zz_new_table"})
    assert "zz_new_table" in extra  # 1表足すと「余り」で落ちる
    # スクリプトの本文を差し替えても、試験の読み取りが差を見つける（ファイルは変えない）
    text = SCRIPT.read_text(encoding="utf-8").replace(" users}\"", " users zz_new_table}\"", 1)
    assert "zz_new_table" in _probe_tables(text)


def test_marker_lines_exist_exactly_once():
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.count("# >>> read-probe begin\n") == 1
    assert text.count("# <<< read-probe end\n") == 1
