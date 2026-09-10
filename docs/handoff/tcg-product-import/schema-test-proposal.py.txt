"""Static TCG schema checks, including product CSV import.

No application imports or database access. Adjacent Python strings are parsed
as one expression. Unsupported text() arguments fail rather than disappearing.
"""
import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_PRODUCT_SERVICE = "backend/app/services/tcg_product_import_svc.py"
_LOOKUP_TABLES = {
    "division_code": "tcg_major_categories",
    "work_code": "tcg_series",
    "manufacturer_code": "tcg_manufacturers",
    "product_category_code": "tcg_product_categories",
}
_TARGET_TOKENS = re.compile(
    r"--[^\n]*|/\*[\s\S]*?\*/|'(?:''|[^'])*'|"
    r'"(?:""|[^"])*"|\{(?:TCG_SCHEMA|table)\}|[A-Za-z_][A-Za-z_0-9]*'
)


def _text_calls(source: str, tree: ast.AST | None = None) -> list[ast.Call]:
    if tree is None:
        tree = ast.parse(source)
    calls = sorted(
        (node for node in ast.walk(tree)
         if isinstance(node, ast.Call)
         and isinstance(node.func, ast.Name) and node.func.id == "text"),
        key=lambda node: (node.lineno, node.col_offset),
    )
    for node in calls:
        assert len(node.args) == 1 and not node.keywords, (
            f"line {node.lineno}: unsupported text() call"
        )
    return calls


def _render_sql(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_render_sql(part) for part in node.values)
    if isinstance(node, ast.FormattedValue):
        assert node.conversion == -1 and node.format_spec is None, (
            f"line {node.lineno}: unsupported SQL formatting"
        )
        assert isinstance(node.value, ast.Name) and node.value.id in {
            "TCG_SCHEMA", "table"
        }, f"line {node.lineno}: unresolved SQL interpolation"
        return "{" + node.value.id + "}"
    raise AssertionError(f"line {node.lineno}: unresolved SQL expression")


def _extract_sql_from_text_calls(source: str) -> list[str]:
    return [_render_sql(call.args[0]) for call in _text_calls(source)]


def _literal_placeholders(source: str) -> list[int]:
    # A constant segment remains literal even next to an f-string segment.
    return [
        call.lineno
        for call in _text_calls(source)
        if any(
            isinstance(part, ast.Constant) and isinstance(part.value, str)
            and any(marker in part.value for marker in ("{TCG_SCHEMA}", "{table}"))
            for part in ast.walk(call.args[0])
        )
    ]


def _bare_table_refs(sql: str, table: str) -> list[str]:
    # Keep the original conservative table-name check, but ignore SQL comments
    # and string values and require the schema immediately before the identifier.
    tokens = [m for m in _TARGET_TOKENS.finditer(sql)
              if not m.group().startswith(("--", "/*", "'"))]
    hits = []
    for i, match in enumerate(tokens):
        if match.group().strip('"') != table:
            continue
        previous = tokens[i - 1] if i else None
        qualified = (
            previous is not None
            and previous.group().strip('"') in {"tenant_004", "{TCG_SCHEMA}"}
            and re.fullmatch(r"\s*\.\s*", sql[previous.end():match.start()])
        )
        if not qualified:
            hits.append(f"bare ref: {sql[max(0, match.start()-25):match.end()+15]}")
    return hits


TARGETS = [
    ("backend/app/routers/tcg_line_import.py", ["import_jobs"]),
    ("backend/app/services/tcg_line_import_svc.py",
     ["import_jobs", "source_messages", "supplier_channels", "extraction_jobs"]),
    (_PRODUCT_SERVICE,
     ["tcg_products", "product_search_keywords", "tcg_product_import_jobs",
      "tcg_product_import_rows", "{table}", *_LOOKUP_TABLES.values()]),
]


def _schema_errors(source: str, tables: list[str]) -> list[str]:
    calls = _text_calls(source)
    assert calls, "zero text() calls: inspection scope disappeared"
    sql_blocks = _extract_sql_from_text_calls(source)
    errors = [f"line {line}: literal SQL placeholder"
              for line in _literal_placeholders(source)]
    for call, sql in zip(calls, sql_blocks, strict=True):
        for table in tables:
            errors.extend(f"line {call.lineno}: {ref}"
                          for ref in _bare_table_refs(sql, table))
    return errors


def test_all_tcg_sql_are_schema_qualified():
    errors = []
    for path, tables in TARGETS:
        source = (_REPO_ROOT / path).read_text(encoding="utf-8")
        errors.extend(f"{path}: {message}" for message in _schema_errors(source, tables))
    assert not errors, "\n".join(errors)


def test_no_literal_tcg_schema_placeholder():
    errors = []
    for path, _ in TARGETS:
        source = (_REPO_ROOT / path).read_text(encoding="utf-8")
        errors.extend(f"{path}:{line}: literal placeholder"
                      for line in _literal_placeholders(source))
    assert not errors, "\n".join(errors)


def _assert_dynamic_lookup_contract(source: str):
    tree = ast.parse(source)
    declarations = [n for n in tree.body if isinstance(n, ast.AnnAssign)
                    and isinstance(n.target, ast.Name) and n.target.id == "LOOKUP_TABLES"]
    assert len(declarations) == 1, "lookup mapping declaration changed"
    assert ast.literal_eval(declarations[0].value) == _LOOKUP_TABLES
    stores = [n for n in ast.walk(tree) if isinstance(n, ast.Name)
              and n.id == "LOOKUP_TABLES" and isinstance(n.ctx, ast.Store)]
    assert len(stores) == 1, "lookup mapping rebound"
    parent = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    dynamic_calls = []
    for call in _text_calls(source, tree):
        if not any(isinstance(n, ast.FormattedValue) and isinstance(n.value, ast.Name)
                   and n.value.id == "table" for n in ast.walk(call.args[0])):
            continue
        dynamic_calls.append(call)
        loop = parent.get(call)
        while loop is not None and not isinstance(loop, (ast.For, ast.FunctionDef, ast.AsyncFunctionDef)):
            loop = parent.get(loop)
        assert isinstance(loop, ast.For), "dynamic table outside expected lookup loop"
        assert ast.unparse(loop.target) == "(column, table)"
        assert ast.unparse(loop.iter) == "LOOKUP_TABLES.items()"
        writes = [n for n in ast.walk(loop) if isinstance(n, ast.Name)
                  and n.id == "table" and isinstance(n.ctx, ast.Store)]
        assert len(writes) == 1, "dynamic table rebound inside loop"
    assert len(dynamic_calls) == 1, "dynamic lookup call inventory changed"


def test_product_dynamic_lookup_contract():
    source = (_REPO_ROOT / _PRODUCT_SERVICE).read_text(encoding="utf-8")
    _assert_dynamic_lookup_contract(source)


def test_sql_extraction_and_qualification_regressions():
    tables = ["tcg_products", "product_search_keywords"]
    cases = [
        ('text(f"SELECT * FROM {TCG_SCHEMA}.tcg_products " '
         'f"JOIN {TCG_SCHEMA}.product_search_keywords ON true")', False),
        ('text(f"SELECT * FROM {TCG_SCHEMA}.tcg_products " '
         'f"JOIN product_search_keywords ON true")', True),
        ('text("SELECT * FROM {TCG_SCHEMA}.tcg_products")', True),
        ('text(f"SELECT * FROM {TCG_SCHEMA}.tcg_products " '
         '"JOIN {TCG_SCHEMA}.product_search_keywords ON true")', True),
        ('text(f"SELECT \'FROM tcg_products\' FROM {TCG_SCHEMA}.tcg_products '
         '-- JOIN product_search_keywords")', False),
        ('text(\'SELECT * FROM "tenant_004"."tcg_products"\')', False),
        ('text(f"SELECT * FROM {TCG_SCHEMA} . tcg_products")', False),
        ('text("SELECT * FROM tenant_004.x, tcg_products")', True),
        ('text("SELECT * FROM tenant_004.tcg_products_archive")', False),
        ('text(f"SELECT * FROM {TCG_SCHEMA}.tcg_products, product_search_keywords")', True),
    ]
    for source, expected_error in cases:
        assert bool(_schema_errors(source, tables)) == expected_error, source
    for source in ['text(query)', 'text(f"SELECT * FROM {schema}.tcg_products")', 'pass']:
        try:
            _schema_errors(source, tables)
        except AssertionError:
            continue
        raise AssertionError(f"unresolved input passed: {source}")


def test_product_schema_removal_is_detected():
    source = (_REPO_ROOT / _PRODUCT_SERVICE).read_text(encoding="utf-8")
    tables = next(tables for path, tables in TARGETS if path == _PRODUCT_SERVICE)
    calls = _text_calls(source)
    assert len(calls) == 6, "review new/removed SQL calls and update inventory"
    positions = list(re.finditer(re.escape("{TCG_SCHEMA}."), source))
    assert len(positions) == 7, "review changed schema reference inventory"
    for match in positions:
        changed = source[:match.start()] + source[match.end():]
        assert _schema_errors(changed, tables), f"missed schema removal at {match.start()}"
    for table in _LOOKUP_TABLES.values():
        qualified = source.replace("{table}", table)
        assert not _schema_errors(qualified, tables)
        bare = qualified.replace("{TCG_SCHEMA}." + table, table)
        assert _schema_errors(bare, tables), f"missed dynamic table: {table}"


def test_dynamic_lookup_changes_require_review():
    source = (_REPO_ROOT / _PRODUCT_SERVICE).read_text(encoding="utf-8")
    changes = [
        source.replace('"division_code": "tcg_major_categories"', '"division_code": "other_table"'),
        source.replace('for column, table in LOOKUP_TABLES.items():',
                       'for column, table in external_tables.items():'),
        source.replace('for column, table in LOOKUP_TABLES.items():',
                       'for column, table in LOOKUP_TABLES.items():\n        table = "other_table"'),
    ]
    for changed in changes:
        assert changed != source
        try:
            _assert_dynamic_lookup_contract(changed)
        except AssertionError:
            continue
        raise AssertionError("changed dynamic table contract passed")


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
