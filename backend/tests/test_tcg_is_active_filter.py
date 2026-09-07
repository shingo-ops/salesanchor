"""
TCG source_messages is_active フィルタ存在確認テスト（IMP-35）。

IMP-32 で特定した3サービスの SQL が、source_messages を JOIN する箇所で
is_active = TRUE を含むことを静的に検証する。

方式: ソースコードを文字列として読み込み、SQL ブロックごとに
  「source_messages を参照する SQL には is_active = TRUE が���ず含まれる」
  を正規表現で確認する。DB 接続不要。

対象:
  backend/app/services/tcg_supplier_quality_svc.py
  backend/app/services/tcg_distribution_svc.py
  backend/app/services/tcg_analysis_review_svc.py
"""
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]

# ---------------------------------------------------------------------------
# ユーティリティ（test_tcg_schema_qualification.py と同方��）
# ---------------------------------------------------------------------------

_TEXT_CALL_RE = re.compile(
    r'\btext\(\s*'
    r'[fFrR]*'
    r'(?:'
    r'"""([\s\S]*?)"""'
    r"|'''([\s\S]*?)'''"
    r'|"((?:[^"\\]|\\.)*)"'
    r"|'((?:[^'\\]|\\.)*)')",
    re.DOTALL,
)

# f-string 文字列リテラル（text() 外の f"""...""" を含む）
_FSTRING_RE = re.compile(
    r'\bf"""([\s\S]*?)"""'
    r'|\bf\'\'\'([\s\S]*?)\'\'\''
    r'|\bf"((?:[^"\\]|\\.)*)"'
    r"|f'((?:[^'\\]|\\.)*)'",
    re.DOTALL,
)


def _extract_all_sql(source: str) -> list[str]:
    """
    text() 呼び出しと f-string SQL 変数（_BASE_FROM 等）を両方抽出して返す。
    """
    results = []
    for m in _TEXT_CALL_RE.finditer(source):
        sql = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ""
        results.append(sql)
    for m in _FSTRING_RE.finditer(source):
        sql = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ""
        if sql:
            results.append(sql)
    return results


def _sql_references_source_messages(sql: str) -> bool:
    """SQL が source_messages テーブルを参照しているか。"""
    return "source_messages" in sql


def _sql_has_is_active_true(sql: str) -> bool:
    """SQL に is_active = TRUE が含まれているか（大文字小文字無視）。"""
    return bool(re.search(r"is_active\s*=\s*TRUE", sql, re.IGNORECASE))


# ---------------------------------------------------------------------------
# テスト対象ファイル
# ---------------------------------------------------------------------------

TARGETS = [
    "backend/app/services/tcg_supplier_quality_svc.py",
    "backend/app/services/tcg_distribution_svc.py",
    "backend/app/services/tcg_analysis_review_svc.py",
]

# ---------------------------------------------------------------------------
# テスト本体
# ---------------------------------------------------------------------------


def test_source_messages_sql_always_filters_is_active():
    """
    3サービスファイルの SQL ブロックにおいて、
    source_messages を参照する全 SQL が is_active = TRUE を含む。

    IMP-32 で特定した二重計上リスクの修正（IMP-35）を保護するテスト。
    修正前: source_messages を JOIN する SQL に is_active フィルタなし → RED
    修正後: is_active = TRUE を含む              → GREEN
    """
    errors: list[str] = []

    for rel_path in TARGETS:
        path = _REPO_ROOT / rel_path
        assert path.exists(), f"{rel_path} が存在しません"
        source = path.read_text(encoding="utf-8")
        sql_blocks = _extract_all_sql(source)

        for i, sql in enumerate(sql_blocks):
            if not _sql_references_source_messages(sql):
                continue
            if not _sql_has_is_active_true(sql):
                snippet = sql.strip()[:200].replace("\n", " ")
                errors.append(
                    f"[{rel_path}] SQL ブロック #{i} が source_messages を参照しているが "
                    f"is_active = TRUE を含んでいません:\n  SQL(先頭200文字): {snippet!r}"
                )

    assert not errors, (
        "以下の SQL に is_active = TRUE フィルタがありません:\n" + "\n".join(errors)
    )
