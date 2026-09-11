"""
時刻の扱いの静的検査（time-handling-ssot）。

対象ADR: ADR-151
design: docs/handoff/time-handling-ssot/design.md
recon:  docs/handoff/time-handling-ssot/recon.md

方式: ソースを正規表現で読む方式。
理由: DB 接続なしに静的に検証できる。既存の pytest 環境でそのまま動く。
     先例: backend/tests/test_tcg_schema_qualification.py

規則は精度で2段に分ける（design.md §3-3）。
本ファイルに実装するのは「停止させる規則」T1・T3 のみ。
T2 は 2026-09-08 の実測で精度0%（検出2件・真の違反0件）だったため除去した。
同種の誤りは境界テスト（design.md §3-4）で捕捉する。
警告規則 T4・T5 は人が読むため、機械強制しない。

導入順序（design.md §4）:
  1. 検査を作る（CIに接続しない）  ← 本ファイル
  2. 既存の違反6件を直す
  3. 検査をCIに接続する
"""
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
_APP_ROOT = _REPO_ROOT / "backend" / "app"

# 検査対象から除外するファイル（正本そのもの）
_EXEMPT = {
    "backend/app/services/time.py",
}


def _python_sources() -> list[tuple[str, str]]:
    """backend/app 配下の .py を (相対パス, 中身) で返す。"""
    results: list[tuple[str, str]] = []
    for path in sorted(_APP_ROOT.rglob("*.py")):
        rel = str(path.relative_to(_REPO_ROOT))
        if rel in _EXEMPT:
            continue
        if "__pycache__" in rel:
            continue
        results.append((rel, path.read_text(encoding="utf-8")))
    return results


def _line_of(source: str, index: int) -> int:
    """文字位置から行番号（1始まり）を返す。"""
    return source.count("\n", 0, index) + 1


def test_t1_no_utcnow():
    """
    T1: datetime.utcnow() を使わない。

    utcnow() はタイムゾーン情報を持たない値を返す。Python 3.12 で非推奨。
    代わりに datetime.now(timezone.utc) を使う。

    根拠: recon.md §6-2（実測4箇所）
    """
    violations: list[str] = []
    pattern = re.compile(r"\butcnow\s*\(")

    for rel, source in _python_sources():
        for m in pattern.finditer(source):
            violations.append(f"{rel}:{_line_of(source, m.start())}")

    assert not violations, (
        "T1 違反: utcnow() は使わない。datetime.now(timezone.utc) を使うこと。\n"
        + "\n".join(violations)
    )


def test_t3_no_at_time_zone_utc():
    """
    T3: SQL で AT TIME ZONE 'UTC' を使わない。

    timestamptz に AT TIME ZONE 'UTC' を適用すると、
    タイムゾーン情報が剥がれた naive な値になる。
    API が返すとブラウザがローカル時刻と解釈し、表示がずれる。

    AT TIME ZONE 'Asia/Tokyo' は正しい変換なので検出しない。

    根拠: recon.md §6-3（3箇所中、誤りは1箇所）
    """
    violations: list[str] = []
    pattern = re.compile(r"AT\s+TIME\s+ZONE\s+'UTC'", re.IGNORECASE)

    for rel, source in _python_sources():
        for m in pattern.finditer(source):
            violations.append(f"{rel}:{_line_of(source, m.start())}")

    assert not violations, (
        "T3 違反: AT TIME ZONE 'UTC' はタイムゾーン情報を剥がす。\n"
        "timestamptz のまま返し、表示側で変換すること。\n"
        + "\n".join(violations)
    )
