"""prompt_ab が保存した応答（response_text）から、後処理だけをやり直す道具（Gemini は呼ばない）。

設計: docs/handoff/prompt-ab-recompute/design.md
起動: python -m app.tools.prompt_ab_recompute --from-jsonl <prompt_ab の JSONL> --out-dir <出力先>

各行の run_id から原文と仕入元の文脈を prompt_ab と同じ関数で読み、マスタも prompt_ab と同じ読み込みを使う。
parse_v101_response → extract_v101_items(v102_fixes=True) を今のコードで通し直し、
1行1投稿の JSONL（recompute-<入力ファイル名>.jsonl）に v102_items・v102_flags を書く。
DB は読むだけ。費用の台帳（llm_usage_events）にも書かない。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.gemini_extraction_svc import _safe_error_message
from app.services.line_analysis_v102_svc import load_followup_reference, masters_with_followup
from app.tasks.tcg_extraction import _get_sync_session
from app.tools import prompt_ab as pab

logger = logging.getLogger(__name__)

_COPIED_FIELDS = ("run_id", "job_id", "prompt_name", "omitted_supplier_fields")
_REQUIRED_MASTERS = ("cond_entries", "status_entries", "unit_alias_to_info")


@dataclass
class RecomputeSummary:
    read: int = 0
    written: int = 0
    errors: int = 0


def _load_masters(session: Session) -> dict:
    """prompt_ab と同じ読み込み。読めない・空のときは黙って続けず止める。"""
    masters = pab._load_v10_masters(session, product_first=True)
    empty = [name for name in _REQUIRED_MASTERS if not masters.get(name)]
    if empty:
        raise ValueError(f"マスタが空です: {', '.join(empty)}")
    return masters


def _load_line(line: str) -> dict:
    row = json.loads(line)
    if not isinstance(row, dict):
        raise ValueError("JSON の行がオブジェクトではありません")
    return row


def _check_row(row: dict) -> None:
    response_text = row.get("response_text")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("response_text がありません")
    if not row.get("run_id"):
        raise ValueError("run_id がありません")


def _context_for(session: Session, run_id: str, contexts: dict[str, object]):
    job_id = pab.fetch_job_ids(session, [run_id]).get(run_id)
    if job_id is None:
        raise ValueError(f"run id not found: {run_id}")
    if job_id not in contexts:
        loaded = pab.load_extraction_context(session, job_id)
        if loaded is None:
            raise ValueError(f"job not found: {job_id}")
        contexts[job_id] = loaded
    return contexts[job_id]


def _recompute_row(session: Session, row: dict, masters: dict, contexts: dict[str, object]) -> dict:
    ctx = _context_for(session, row["run_id"], contexts)
    copied = {k: row[k] for k in _COPIED_FIELDS if k in row}
    job_id = pab.fetch_job_ids(session, [row["run_id"]])[row["run_id"]]
    followup = load_followup_reference(session, job_id)  # 本番（run_v102_analysis）と同じ関数
    return {**copied, **pab._v102_row_fields(row["response_text"], ctx, masters_with_followup(masters, followup))}


def recompute(session: Session, *, from_jsonl: Path, out_dir: Path) -> RecomputeSummary:
    """from_jsonl の各行を作り直して out_dir に書く。1行の失敗は記録して次へ進み、件数を返す。"""
    lines = [ln for ln in Path(from_jsonl).read_text(encoding="utf-8").splitlines() if ln.strip()]
    masters = _load_masters(session)  # 空ならここで止まる
    out_path = Path(out_dir) / f"recompute-{Path(from_jsonl).stem}.jsonl"
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path.unlink(missing_ok=True)  # 実行のたびに作り直す（追記しない）
    summary = RecomputeSummary()
    contexts: dict[str, object] = {}
    for number, line in enumerate(lines, start=1):
        summary.read += 1
        source: dict = {}
        try:
            source = _load_line(line)
            _check_row(source)
            result = _recompute_row(session, source, masters, contexts)
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            summary.errors += 1
            pab._append_jsonl(out_path, {
                **{k: source[k] for k in _COPIED_FIELDS if k in source},
                "input_line": number, "error": f"{type(exc).__name__}: {_safe_error_message(exc)}",
            })
            logger.error("[prompt_ab_recompute] line %d: %s", number, exc)
            continue
        pab._append_jsonl(out_path, result)
        if "v102_items_error" in result:  # 取り出しの失敗も件数に数える
            summary.errors += 1
        else:
            summary.written += 1
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="prompt_ab の保存済み応答から v102 の後処理だけをやり直す（Gemini は呼ばない）")
    p.add_argument("--from-jsonl", required=True, type=Path, help="prompt_ab が書いた JSONL")
    p.add_argument("--out-dir", required=True, type=Path)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    session = _get_sync_session()
    try:
        summary = recompute(session, from_jsonl=args.from_jsonl, out_dir=args.out_dir)
    finally:
        session.close()
    print(f"read={summary.read} written={summary.written} errors={summary.errors}")
    return 0 if summary.errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
