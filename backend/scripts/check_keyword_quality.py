"""
キーワード品質検査の実行入口。

設計: docs/handoff/tcg-keyword-quality/design.md
recon: docs/handoff/tcg-keyword-quality/recon.md
対象ADR: ADR-154

DB から検索語・除外語・有効商品コードを読み、tcg_keyword_lint に渡して結果を表示する。
読み取りのみ。書き込みは一切しない（SQL は本ファイル内の text( ） 1 箇所だけ）。
停止規則に該当があれば終了コード 1、無ければ 0 を返す。

使い方:
  python backend/scripts/check_keyword_quality.py

接続先は TCG_DB_URL、無ければ DATABASE_URL を使う
（backend/app/tasks/tcg_extraction.py と同じ作り）。
出力に含めるのは商品コードと語のみ。商品名・仕入元・原文は出さない。
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.tcg_analyzer_svc import load_product_keywords
from app.services.tcg_keyword_lint import run_all
from app.tcg_config import TCG_SCHEMA

_DB_URL_RAW = os.environ.get("TCG_DB_URL", os.environ.get("DATABASE_URL", ""))
_DB_URL = _DB_URL_RAW.replace("postgresql+asyncpg", "postgresql+psycopg2").replace(
    "asyncpg://", "psycopg2://"
)

_LABEL = {
    "R1": "検索語0件の有効商品",
    "R2-stop": "1文字の日本語トークン",
    "R2-warn": "2文字の日本語トークン",
    "R3": "複数商品に同じ語",
    "R4": "除外語が自商品の検索語を殺す",
    "R5": "除外語で守られていない相乗り",
    "R6": "同一商品内の重複",
    "R7": "空白を含む日本語語",
}


def load_active_codes(session: Session) -> list[str]:
    """照合が読むのと同じ範囲（is_active=TRUE）の商品コード。"""
    rows = session.execute(
        text(f"SELECT code FROM {TCG_SCHEMA}.tcg_products WHERE is_active = TRUE ORDER BY code")
    ).fetchall()
    return [r[0] for r in rows]


def format_report(result: dict, sample: int = 10) -> list[str]:
    """表示用の行を組み立てる。一覧は先頭 sample 件まで。"""
    lines: list[str] = []
    for rule, (level, items) in result["findings"].items():
        head = ", ".join(items[:sample])
        more = f" ... 他 {len(items) - sample} 件" if len(items) > sample else ""
        lines.append(f"{rule:<8} {level:<4} {_LABEL[rule]}: {len(items)} 件  [{head}{more}]")
    stop_count = len(result["stop_rules"])
    lines.append(f"RESULT: STOP={stop_count} rules, exit {result['exit_code']}")
    return lines


def main() -> int:
    if not _DB_URL:
        print("TCG_DB_URL も DATABASE_URL も設定されていません。", file=sys.stderr)
        return 2
    engine = create_engine(_DB_URL, echo=False)
    try:
        with Session(engine) as session:
            search_kw, exclude_kw = load_product_keywords(session)
            active_codes = load_active_codes(session)
    finally:
        engine.dispose()

    result = run_all(active_codes, search_kw, exclude_kw)
    print(f"対象スキーマ: {TCG_SCHEMA}")
    print(f"有効商品: {len(active_codes)} 件 / 検索語を持つ商品: {len(search_kw)} 件")
    for line in format_report(result):
        print(line)
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
