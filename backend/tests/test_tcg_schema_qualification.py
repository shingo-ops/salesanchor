"""
TCG テーブルのスキーマ修飾テスト。

tcg_line_import.py / tcg_line_import_svc.py の全 text(...) SQL が
tenant_004 スキーマを修飾していることを確認する。

方式: ソースを正規表現で読む方式。
理由: SQL は DB 接続なしに静的に検証できる。
     text() の引数文字列を抽出し、テーブル名の前にスキーマ修飾があるかを確認する。
     DB を立てずに済むため既存の pytest -v 環境でそのまま動く。

対象テーブル: import_jobs（ルーター）、
              import_jobs / source_messages / supplier_channels /
              extraction_jobs（サービス）
IMP-09 マージ後に tcg_extraction.py 等を追加すればよい。
"""
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# 共通ユーティリティ
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parents[2]


def _extract_sql_from_text_calls(source: str) -> list[str]:
    """
    text("...") / text(f"...") / text('''...''') / text(f'''...''') 等の
    引数文字列をすべて抽出して返す。

    シングル / ダブル / トリプルクォート + f/r プレフィックスに対応。
    """
    pattern = re.compile(
        r'\btext\(\s*'
        r'[fFrR]*'                       # f/r プレフィックス（任意）
        r'(?:'
        r'"""([\s\S]*?)"""'              # triple double
        r"|'''([\s\S]*?)'''"             # triple single
        r'|"((?:[^"\\]|\\.)*)"'         # double
        r"|'((?:[^'\\]|\\.)*)'"         # single
        r')',
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(source):
        sql = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ""
        results.append(sql)
    return results


def _bare_table_refs(sql: str, table: str) -> list[str]:
    """
    SQL 文字列中に `table` が スキーマ修飾なしで登場する箇所を返す。

    スキーマ修飾あり（tenant_004.table または {TCG_SCHEMA}.table）は無視。
    """
    hits = []
    for m in re.finditer(re.escape(table), sql):
        start = m.start()
        # 直前の文字列を取得（スキーマ修飾の確認）
        prefix = sql[max(0, start - 14) : start]
        if "tenant_004." not in prefix and "{TCG_SCHEMA}." not in prefix:
            hits.append(
                f"  bare ref: ...{sql[max(0, start-20):start+len(table)+10].strip()}..."
            )
    return hits


# ---------------------------------------------------------------------------
# テスト対象ファイル
# ---------------------------------------------------------------------------

TARGETS = [
    (
        "backend/app/routers/tcg_line_import.py",
        ["import_jobs"],
    ),
    (
        "backend/app/services/tcg_line_import_svc.py",
        ["import_jobs", "source_messages", "supplier_channels", "extraction_jobs"],
    ),
]


# ---------------------------------------------------------------------------
# テスト本体
# ---------------------------------------------------------------------------


def test_all_tcg_sql_are_schema_qualified():
    """
    各ファイルの text() SQL において、対象テーブルが必ずスキーマ修飾されている。

    期待: tenant_004.<table> または {TCG_SCHEMA}.<table> の形式のみ。
    """
    all_errors: list[str] = []

    for rel_path, tables in TARGETS:
        path = _REPO_ROOT / rel_path
        assert path.exists(), f"{rel_path} が存在しません"
        source = path.read_text(encoding="utf-8")
        sql_blocks = _extract_sql_from_text_calls(source)

        for sql in sql_blocks:
            for table in tables:
                if table not in sql:
                    continue
                bare_refs = _bare_table_refs(sql, table)
                for ref in bare_refs:
                    all_errors.append(f"[{rel_path}] {table} がスキーマ未修飾:\n{ref}")

    assert not all_errors, (
        "以下の SQL にスキーマ修飾がありません:\n" + "\n".join(all_errors)
    )


def test_no_literal_tcg_schema_placeholder():
    """
    text() 呼び出しが f-string でない場合、{TCG_SCHEMA} がそのまま残る。
    f-string になっていれば source 上では {TCG_SCHEMA} と書かれているが、
    それは正常（実行時に tenant_004 に展開される）。

    このテストでは逆に「{TCG_SCHEMA} を書いているのに f-string でない」ケースを検出する。
    """
    errors: list[str] = []
    # f-string でない text() 呼び出しに {TCG_SCHEMA} が含まれていないか確認
    # パターン: text( に f プレフィックスなし、かつ引数に {TCG_SCHEMA} を含む
    non_f_with_placeholder = re.compile(
        r'\btext\(\s*(?![fF])'      # f プレフィックスなし
        r'(?:"""([\s\S]*?)"""|'
        r"'''([\s\S]*?)'''|"
        r'"((?:[^"\\]|\\.)*)"'
        r"|'((?:[^'\\]|\\.)*)')",
        re.DOTALL,
    )

    for rel_path, _ in TARGETS:
        path = _REPO_ROOT / rel_path
        source = path.read_text(encoding="utf-8")
        for m in non_f_with_placeholder.finditer(source):
            sql = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ""
            if "{TCG_SCHEMA}" in sql:
                errors.append(
                    f"[{rel_path}] f-string でない text() に {{TCG_SCHEMA}} が残っています"
                )

    assert not errors, "\n".join(errors)


def test_supplier_channels_insert_columns_match_ddl():
    """
    tcg_line_import.py の supplier_channels INSERT に DDL 外の列がないことを確認。

    方式: DDL から列名を抽出し、INSERT 列リストと照合する（静的解析）。

    RED:   created_at など DDL 外の列を含む INSERT がある場合
    GREEN: DDL の列（id/supplier_id/channel/external_id/is_active）のみの場合
    """
    # --- DDL から supplier_channels の列名を抽出 ---
    ddl_path = (
        _REPO_ROOT
        / "migrations/20260831_110000_create_tcg_analysis_tables_t004.sql"
    )
    assert ddl_path.exists(), f"DDL ファイルが存在しません: {ddl_path}"
    ddl_source = ddl_path.read_text(encoding="utf-8")

    # CREATE TABLE supplier_channels (...) ブロックを括弧の深さで抽出
    start_match = re.search(
        r"CREATE TABLE IF NOT EXISTS %I\.supplier_channels\s*\(",
        ddl_source,
    )
    assert start_match, "DDL に supplier_channels テーブルが見つかりません"

    body_start = start_match.end()  # 開き括弧の次
    depth = 1
    pos = body_start
    while pos < len(ddl_source) and depth > 0:
        if ddl_source[pos] == "(":
            depth += 1
        elif ddl_source[pos] == ")":
            depth -= 1
        pos += 1
    ddl_block = ddl_source[body_start : pos - 1]  # 最後の ) を除く

    # 列名抽出: 先頭が識別子（CONSTRAINT/REFERENCES/PRIMARY/UNIQUE 以外）の行
    _DDL_SKIP = {"constraint", "references", "primary", "unique", "check", "foreign"}
    ddl_columns: set[str] = set()
    for line in ddl_block.splitlines():
        line = line.strip()
        if not line:
            continue
        col_name = line.split()[0].lower()
        if col_name and col_name.isidentifier() and col_name not in _DDL_SKIP:
            ddl_columns.add(col_name)

    assert ddl_columns, "DDL から列名を抽出できませんでした"

    # --- router から supplier_channels INSERT 列リストを抽出 ---
    router_path = _REPO_ROOT / "backend/app/routers/tcg_line_import.py"
    assert router_path.exists(), f"router ファイルが存在しません: {router_path}"
    router_source = router_path.read_text(encoding="utf-8")

    insert_match = re.search(
        r"INSERT INTO [^\n]*supplier_channels\s*\n\s*\(([^)]+)\)",
        router_source,
        re.DOTALL,
    )
    assert insert_match, "router に supplier_channels の INSERT 文が見つかりません"
    insert_cols_str = insert_match.group(1)
    insert_columns = {c.strip().lower() for c in insert_cols_str.split(",")}

    # --- DDL 外の列を検出 ---
    extra_cols = insert_columns - ddl_columns
    assert not extra_cols, (
        f"supplier_channels INSERT に DDL 外の列があります: {extra_cols}\n"
        f"DDL 列: {sorted(ddl_columns)}\n"
        f"INSERT 列: {sorted(insert_columns)}"
    )
