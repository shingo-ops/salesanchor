"""サーバーの失敗の応答（HTTPException の detail）に文を直書きしない見張り（ADR-1071 W1）。

数え方（docs/handoff/error-message-plain-language/card-guard.md §3-2）:
  - backend/app の全 .py を ast で読み、HTTPException の呼び出しの detail を見る。
  - detail は キーワード detail、無ければ位置引数の 2 つ目。
  - 違反: (a) detail の式の中の文字列定数に日本語がある
          (b) detail が文字列定数か f 文字列で、定数部分が識別子の形でない
  - 例外: 呼び出しの行かすぐ上の行に `error-detail-exempt: <理由>`。
基準値: backend/tests/error_detail_baseline.json（app/... の道すじ → 件数）。
基準を書き出す: python tests/test_error_detail_guard.py --write-baseline
DB・ネットワークは使わない。
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"
BASELINE_FILE = Path(__file__).resolve().parent / "error_detail_baseline.json"

_JA = re.compile("[぀-ヿ一-鿿]")
_IDENT = re.compile(r"^[A-Za-z0-9_.:\-]*$")
_EXEMPT = re.compile(r"error-detail-exempt:\s*\S")


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _detail_expr(node: ast.Call) -> ast.expr | None:
    for kw in node.keywords:
        if kw.arg == "detail":
            return kw.value
    if len(node.args) >= 2:
        return node.args[1]
    return None


def _is_violation(detail: ast.expr) -> bool:
    for sub in ast.walk(detail):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and _JA.search(sub.value):
            return True
    text: str | None = None
    if isinstance(detail, ast.Constant) and isinstance(detail.value, str):
        text = detail.value
    elif isinstance(detail, ast.JoinedStr):
        text = "".join(v.value for v in detail.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
    if text is not None and not _IDENT.match(text):
        return True
    return False


def count_source(source: str) -> int:
    """ソース 1 本の違反件数。解析に失敗したら SyntaxError を投げる。"""
    tree = ast.parse(source)
    lines = source.split("\n")
    n = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "HTTPException":
            continue
        detail = _detail_expr(node)
        if detail is None or not _is_violation(detail):
            continue
        idx = node.lineno - 1
        here = lines[idx] if 0 <= idx < len(lines) else ""
        above = lines[idx - 1] if 1 <= idx <= len(lines) else ""
        if _EXEMPT.search(here) or _EXEMPT.search(above):
            continue
        n += 1
    return n


def count_app(app_dir: Path = APP_DIR) -> tuple[dict[str, int], list[str]]:
    """(ファイルごとの件数, 解析に失敗したファイル名の一覧)。0 のファイルは載せない。"""
    counts: dict[str, int] = {}
    broken: list[str] = []
    for path in sorted(app_dir.rglob("*.py")):
        key = "app/" + path.relative_to(app_dir).as_posix()
        try:
            n = count_source(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            broken.append(key)
            continue
        if n > 0:
            counts[key] = n
    return counts, broken


def _load_baseline() -> dict[str, int]:
    return json.loads(BASELINE_FILE.read_text(encoding="utf-8"))


def _write_baseline() -> None:
    counts, broken = count_app()
    if broken:
        print("解析に失敗: " + ", ".join(broken))
        sys.exit(1)
    body = json.dumps(dict(sorted(counts.items())), indent=2, ensure_ascii=False) + "\n"
    BASELINE_FILE.write_text(body, encoding="utf-8")
    print(f"書き出し: {len(counts)} ファイル・{sum(counts.values())} 件")


_SELF_CASES = [
    ('raise HTTPException(status_code=400, detail="入力が正しくありません")', 1),
    ('raise HTTPException(status_code=404, detail="not_found")', 0),
    ('raise HTTPException(404, "Item not found")', 1),
    ('raise HTTPException(status_code=403, detail={"reason": "permission_denied"})', 0),
    ('raise HTTPException(status_code=409, detail={"message": "重複しています"})', 1),
    ('raise HTTPException(status_code=400, detail=f"{field}")', 0),
    ('raise HTTPException(status_code=400, detail=f"{field} は必須です")', 1),
    ('raise fastapi.HTTPException(status_code=400, detail="壊れています")', 1),
    (
        '# error-detail-exempt: 外部サービス向けの応答\nraise HTTPException(status_code=400, detail="Bad signature")',
        0,
    ),
    (
        '# error-detail-exempt:\nraise HTTPException(status_code=400, detail="Bad signature")',
        1,
    ),
]


def test_detail_guard_self_check():
    for source, expected in _SELF_CASES:
        assert count_source(source) == expected, source
    combined = "\n".join(src for src, _ in _SELF_CASES)
    assert count_source(combined) == 6


def test_detail_guard_no_increase():
    counts, broken = count_app()
    assert not broken, "解析に失敗: " + ", ".join(broken)
    baseline = _load_baseline()
    problems = [
        f"増えた: {name} 基準 {baseline.get(name, 0)} → 今 {n}"
        for name, n in sorted(counts.items())
        if n > baseline.get(name, 0)
    ]
    assert not problems, (
        "\n".join(problems) + "\nサーバーは文を作らず理由コードを返し、文は画面の対応表で出す（ADR-1071）。"
        "前例 frontend/src/features/discord-connect/discordConnectError.ts。"
        "外部サービス向けなどで文が要るときは、その行かすぐ上の行に error-detail-exempt: <理由> を書く"
    )


def test_detail_guard_no_stale_baseline():
    counts, _ = count_app()
    baseline = _load_baseline()
    problems = [
        f"減った: {name} 基準 {base} → 今 {counts.get(name, 0)}"
        f"（backend/tests/error_detail_baseline.json のこの行を {counts.get(name, 0)} に下げる。0 なら行を消す）"
        for name, base in sorted(baseline.items())
        if counts.get(name, 0) < base
    ]
    assert not problems, "\n".join(problems)


if __name__ == "__main__":
    if "--write-baseline" in sys.argv:
        _write_baseline()
    else:
        print("使い方: python tests/test_error_detail_guard.py --write-baseline")
