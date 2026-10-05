"""Gemini 書き写し v7/v8/v9/v10/v10.1 の比較試験の道具（読み取り＋費用の台帳だけ）。

設計: docs/handoff/gemini-v8/design.md §6
      docs/handoff/gemini-v9/design.md §5-1（v9）
      docs/handoff/gemini-v9-trial1/design.md §3（--prompt-name）
      docs/handoff/gemini-v10/design.md §3-5（v10）
      docs/handoff/gemini-v101/design.md §3-6（v101）
起動: python -m app.tools.prompt_ab --runs-file F --config v7|v8|v9|v10|v101 [--prompt-name raw_copy_v9_NAME|raw_copy_v101_NAME]
        [--thinking-level L] [--no-thoughts] [--no-schema] [--temperature T] --repeat N --max-cost-usd X --test-id ID --out-dir /tmp/prompt_ab/ID [--dry-run]

結果は out-dir の JSONL にだけ書く（1回につき1行）。DB に書くのは llm_usage_events（費用の台帳）だけで、
purpose="line_extraction_shadow"・source_ref="prompt_ab:<test_id>" で区別する。
extraction_shadow_runs / extraction_jobs など本番の表には書かない。
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.extraction_judgement_svc import order_from_pattern
from app.services.gemini_extraction_svc import (
    _GEMINI_MODEL,
    _build_supplier_context_note,
    _load_db_raw_copy_prompt,
    _safe_error_message,
    call_gemini_raw_copy,
    format_prompt_input,
    parse_raw_copy_response,
)
from app.services.gemini_raw_copy_v8 import (
    build_prompt_v8,
    call_gemini_raw_copy_v8,
    load_v8_prompt,
    parse_v8_response,
)
from app.services.gemini_raw_copy_v9 import (
    V9_RESPONSE_SCHEMA,
    load_v9_prompt,
    parse_v9_response,
)
from app.services.gemini_raw_copy_v10 import (
    V10_RESPONSE_SCHEMA,
    extract_v10_items,
    load_v10_prompt,
    parse_v10_response,
)
from app.services.gemini_raw_copy_v101 import (
    DEFAULT_V101_PROMPT_NAME,
    V101_PROMPT_NAME_RE,
    V101_RESPONSE_SCHEMA,
    extract_v101_items,
    parse_v101_response,
)
from app.services.llm_budget import record_usage_event_sync
from app.services.tcg_analyzer_svc import load_condition_entries, load_lookup_maps, load_status_master
from app.tasks.tcg_extraction import TCG_SCHEMA, _get_sync_session, load_extraction_context

logger = logging.getLogger(__name__)

_LEDGER_PURPOSE = "line_extraction_shadow"  # purpose の追加は migration（CHECK 制約）が要るため source_ref で区別
_LEDGER_SDK = "google-genai"
_SOURCE_REF_PREFIX = "prompt_ab:"
_DRY_RUN_PROMPT_LINES = 30
_THINKING_LEVELS = ("minimal", "low", "medium", "high")
_DEFAULT_V9_PROMPT_NAME = "raw_copy_v9"
_PROMPT_NAME_RES = {  # パス区切りや「..」を通さない
    "v9": re.compile(r"^raw_copy_v9_[a-z0-9_]+$"),
    "v101": V101_PROMPT_NAME_RE,
}
_PROMPT_NAME_CONFIGS = "v9・v101"
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_JOB_IDS_SQL = f"""
    SELECT id::text, extraction_job_id::text
    FROM {TCG_SCHEMA}.extraction_shadow_runs
    WHERE id = ANY(CAST(:run_ids AS uuid[]))
"""

# 費用は source_ref で絞って合計する（時刻や purpose では絞らない）
_LEDGER_TOTALS_SQL = """
    SELECT COUNT(*), COUNT(*) FILTER (WHERE cost_usd IS NULL), COALESCE(SUM(cost_usd), 0)
    FROM public.llm_usage_events
    WHERE source_ref = :source_ref
"""


@dataclass(frozen=True)
class LedgerTotals:
    rows: int
    null_cost_rows: int
    cost_usd: Decimal


@dataclass
class AbSummary:
    target_count: int = 0
    calls: int = 0
    succeeded: int = 0
    failed: int = 0
    total_cost_usd: Decimal = Decimal("0")
    stop_reason: str | None = None  # job_failed / run_not_found / ledger_missing / cost_null / cost_limit
    dry_run: bool = False


# ---------------------------------------------------------------------------
# 起動時の確認・入力
# ---------------------------------------------------------------------------


def _sdk_field_names() -> tuple[set[str], set[str]]:
    """(GenerateContentConfig の項目名, ThinkingConfig の項目名)。試験ではここを差し替える。"""
    from google.genai import types as t  # type: ignore[import-untyped]

    return set(t.GenerateContentConfig.model_fields), set(t.ThinkingConfig.model_fields)


def check_sdk_capabilities() -> tuple[bool, str]:
    """GenerateContentConfig に response_json_schema / thinking_config、ThinkingConfig に thinking_level があるか。"""
    import importlib.metadata as md

    try:
        config_fields, thinking_fields = _sdk_field_names()
    except ImportError:
        return False, "google-genai が入っていません"
    try:
        version = md.version("google-genai")
    except md.PackageNotFoundError:
        version = "unknown"
    missing = [f"GenerateContentConfig.{n}" for n in ("response_json_schema", "thinking_config") if n not in config_fields]
    missing += [f"ThinkingConfig.{n}" for n in ("thinking_level", "include_thoughts") if n not in thinking_fields]
    if missing:
        return False, f"google-genai {version}: 次が無いため実行できません: {', '.join(missing)}"
    return True, f"google-genai {version}: OK"


def read_run_ids(path: Path) -> list[str]:
    ids: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            ids.append(value)
    return ids


def fetch_job_ids(session: Session, run_ids: list[str]) -> dict[str, str]:
    """run id → extraction_job_id（読み取り）。"""
    if not run_ids:
        return {}
    rows = session.execute(text(_JOB_IDS_SQL), {"run_ids": run_ids}).fetchall()
    return {str(r[0]): str(r[1]) for r in rows}


def fetch_ledger_totals(session: Session, source_ref: str) -> LedgerTotals:
    row = session.execute(text(_LEDGER_TOTALS_SQL), {"source_ref": source_ref}).one()
    return LedgerTotals(rows=int(row[0]), null_cost_rows=int(row[1]), cost_usd=Decimal(str(row[2])))


def _stop_reason(calls: int, totals: LedgerTotals, max_cost_usd: Decimal) -> str | None:
    """費用を見張れない状態（台帳の行が足りない・費用NULL）は安全側に止める。"""
    if totals.rows < calls:
        return "ledger_missing"
    if totals.null_cost_rows > 0:
        return "cost_null"
    if totals.cost_usd > max_cost_usd:
        return "cost_limit"
    return None


# ---------------------------------------------------------------------------
# 1回の実行
# ---------------------------------------------------------------------------


def _call_v7(ctx) -> dict:
    """本番 v7 の既存関数をそのまま呼ぶ（変更しない）。"""
    raw = call_gemini_raw_copy(
        ctx.raw_text, supplier_context=ctx.supplier_context, knowledge_links=ctx.knowledge_links
    )
    return {**raw, "thought_summaries": [], "usage_raw": asdict(raw["usage_counts"])}


def _parse(config: str, response_text: str, raw_text: str, masters: dict | None = None) -> tuple[int, list[dict]]:
    """(件数, errors)。パースの失敗は測定の対象なので errors に記録し、止めない。"""
    try:
        if config == "v7":
            items, errors = parse_raw_copy_response(response_text, raw_text)
        elif config == "v9":
            items, errors = parse_v9_response(response_text, raw_text)
        elif config == "v10":
            items, errors = parse_v10_response(response_text, raw_text)
        elif config == "v101":
            items, errors = parse_v101_response(
                response_text, raw_text, status_entries=(masters or {}).get("status_entries")
            )
        else:
            items, errors = parse_v8_response(response_text, raw_text)
    except Exception as exc:  # noqa: BLE001
        return 0, [{"error": f"{type(exc).__name__}: {_safe_error_message(exc)}"}]
    return len(items), errors


def _load_v10_masters(session: Session) -> dict:
    """v10 の取り出しに使うマスタを読む（読み取りのみ。1回の実行で1回だけ呼ぶ）。"""
    cond_entries = load_condition_entries(session)
    status_entries = load_status_master(session)
    (_pc, _ua, _uc, _ca, cond_canonical_to_uuid, unit_alias_to_info) = load_lookup_maps(session)
    return {
        "cond_entries": cond_entries, "cond_canonical_to_uuid": cond_canonical_to_uuid,
        "unit_alias_to_info": unit_alias_to_info, "status_entries": status_entries,
    }


def _v10_row_fields(response_text: str, ctx, masters: dict) -> dict:
    """JSONL の v10 の行に足す v10_items。取り出しに失敗しても試験は止めず、理由を残す。"""
    try:
        items, _errors = parse_v10_response(response_text, ctx.raw_text)
        order = order_from_pattern((ctx.supplier_context or {}).get("extraction_order_pattern"))
        return {"v10_items": extract_v10_items(items, ctx.raw_text, order=order, **masters)}
    except Exception as exc:  # noqa: BLE001
        return {"v10_items": [], "v10_items_error": f"{type(exc).__name__}: {_safe_error_message(exc)}"}


def _v101_row_fields(response_text: str, ctx, masters: dict) -> dict:
    """JSONL の v101 の行に足す v101_items（付け直しあり）・v101_items_norule（なし）・v101_flags。失敗しても止めない。"""
    try:
        items, _errors = parse_v101_response(response_text, ctx.raw_text, status_entries=masters["status_entries"])
        order = order_from_pattern((ctx.supplier_context or {}).get("extraction_order_pattern"))
        with_rule, flags = extract_v101_items(items, ctx.raw_text, order=order, reassign=True, **masters)
        no_rule, _flags = extract_v101_items(items, ctx.raw_text, order=order, reassign=False, **masters)
        return {"v101_items": with_rule, "v101_items_norule": no_rule, "v101_flags": flags}
    except Exception as exc:  # noqa: BLE001
        return {
            "v101_items": [], "v101_items_norule": [], "v101_flags": {},
            "v101_items_error": f"{type(exc).__name__}: {_safe_error_message(exc)}",
        }


def _append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        fh.flush()


def resolve_prompt_path(prompt_name: str, config: str = "v9") -> Path:
    """--prompt-name の名前から指示書のファイルを決める。形が違う・ファイルが無いときは ValueError。"""
    pattern = _PROMPT_NAME_RES.get(config)
    if pattern is None:
        raise ValueError(f"--prompt-name は --config {_PROMPT_NAME_CONFIGS} のときだけ使えます")
    if not pattern.fullmatch(prompt_name):
        raise ValueError(f"--prompt-name は {pattern.pattern} の形だけ使えます: {prompt_name!r}")
    path = _PROMPTS_DIR / f"{prompt_name}.txt"
    if not path.is_file():
        raise ValueError(f"指示書が見つかりません: {path}")
    return path


def _load_prompt_text(config: str, prompt_name: str | None = None) -> str | None:
    """v8・v9・v10・v101 の指示書の本文。v7 は DB の指示書を既存関数が読むので None。"""
    if prompt_name is not None:
        return resolve_prompt_path(prompt_name, config).read_text(encoding="utf-8")
    if config == "v101":
        return resolve_prompt_path(DEFAULT_V101_PROMPT_NAME, config).read_text(encoding="utf-8")
    if config == "v8":
        return load_v8_prompt()
    if config == "v9":
        return load_v9_prompt()
    if config == "v10":
        return load_v10_prompt()
    return None


def _master_row_fields(config: str, response_text: str, ctx, masters: dict | None) -> dict:
    if config == "v10":
        return _v10_row_fields(response_text, ctx, masters)
    if config == "v101":
        return _v101_row_fields(response_text, ctx, masters)
    return {}


def _print_dry_run(
    summary: AbSummary, config: str, ctx, v8_prompt: str | None,
) -> None:
    print(f"[dry-run] target_count={summary.target_count}")
    if ctx is None:
        return
    if config in ("v8", "v9", "v10", "v101"):
        prompt = build_prompt_v8(
            ctx.raw_text, prompt_text=v8_prompt or "", supplier_context=ctx.supplier_context,
            knowledge_links=ctx.knowledge_links,
        )
    else:  # 表示用の組み立て（実際の呼び出しは call_gemini_raw_copy 内で同じ材料から行われる）
        links = [lk for lk in (ctx.knowledge_links or []) if lk.get("category") == "block_delimiter"]
        note = _build_supplier_context_note(ctx.supplier_context or {}, knowledge_links=links)
        section = f"\n{note}\n" if note else ""
        prompt = f"{_load_db_raw_copy_prompt()}{section}\n原文:\n{format_prompt_input(ctx.raw_text)}"
    for line in prompt.split("\n")[:_DRY_RUN_PROMPT_LINES]:
        print(line)


def run_ab(
    session: Session, *, run_ids: list[str], config: str, repeat: int, max_cost_usd: Decimal,
    test_id: str, out_dir: Path, dry_run: bool, thinking_level: str | None,
    include_thoughts: bool, use_schema: bool, temperature: float | None, prompt_name: str | None = None,
) -> AbSummary:
    summary = AbSummary(target_count=len(run_ids), dry_run=dry_run)
    job_ids = fetch_job_ids(session, run_ids)
    v8_prompt = _load_prompt_text(config, prompt_name)  # 名前・ファイルの誤りはここで止まる（Gemini を呼ぶ前）
    row_prompt_name = {
        "v9": prompt_name or _DEFAULT_V9_PROMPT_NAME, "v101": prompt_name or DEFAULT_V101_PROMPT_NAME,
    }.get(config)
    source_ref = f"{_SOURCE_REF_PREFIX}{test_id}"
    out_path = Path(out_dir) / f"{test_id}.jsonl"
    contexts: dict[str, object] = {}

    if dry_run:
        first = next((job_ids[r] for r in run_ids if r in job_ids), None)
        ctx = load_extraction_context(session, first) if first else None
        _print_dry_run(summary, config, ctx, v8_prompt)
        return summary

    masters = _load_v10_masters(session) if config in ("v10", "v101") else None  # dry-run では読まない
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    for run_id in run_ids:
        job_id = job_ids.get(run_id)
        if job_id is None:
            summary.stop_reason = "run_not_found"
            logger.error("[prompt_ab] run id not found: %s", run_id)
            return summary
        for n in range(1, repeat + 1):
            summary.calls += 1
            started = time.monotonic()
            row = {"run_id": run_id, "job_id": job_id, "config": config, "repeat": n}
            if row_prompt_name is not None:
                row["prompt_name"] = row_prompt_name
            try:
                if job_id not in contexts:
                    ctx_loaded = load_extraction_context(session, job_id)
                    if ctx_loaded is None:
                        raise RuntimeError(f"job not found: {job_id}")
                    contexts[job_id] = ctx_loaded
                ctx = contexts[job_id]
                if config == "v7":
                    result = _call_v7(ctx)
                else:
                    schemas = {"v9": V9_RESPONSE_SCHEMA, "v10": V10_RESPONSE_SCHEMA, "v101": V101_RESPONSE_SCHEMA}
                    extra = {"response_schema": schemas[config]} if config in schemas else {}
                    result = call_gemini_raw_copy_v8(
                        ctx.raw_text, prompt_text=v8_prompt, supplier_context=ctx.supplier_context,
                        knowledge_links=ctx.knowledge_links, thinking_level=thinking_level,
                        include_thoughts=include_thoughts, use_schema=use_schema, temperature=temperature,
                        **extra,
                    )
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                summary.failed += 1
                summary.stop_reason = "job_failed"
                _append_jsonl(out_path, {**row, "error": f"{type(exc).__name__}: {_safe_error_message(exc)}",
                                         "elapsed_sec": round(time.monotonic() - started, 3)})
                logger.exception("[prompt_ab] stopped: run=%s repeat=%d", run_id, n)
                return summary

            item_count, errors = _parse(config, result["response_text"], ctx.raw_text, masters)
            _append_jsonl(out_path, {
                **row, "response_text": result["response_text"],
                "thought_summaries": result["thought_summaries"], "usage_raw": result["usage_raw"],
                "item_count": item_count, "errors": errors,
                **_master_row_fields(config, result["response_text"], ctx, masters),
                "elapsed_sec": round(time.monotonic() - started, 3),
            })
            try:
                record_usage_event_sync(
                    session, purpose=_LEDGER_PURPOSE, model=_GEMINI_MODEL, sdk=_LEDGER_SDK,
                    counts=result["usage_counts"], source_ref=source_ref,
                )
                session.commit()
                totals = fetch_ledger_totals(session, source_ref)
            except Exception:  # noqa: BLE001
                session.rollback()
                summary.failed += 1
                summary.stop_reason = "job_failed"
                logger.exception("[prompt_ab] ledger write failed: run=%s repeat=%d", run_id, n)
                return summary
            summary.succeeded += 1
            summary.total_cost_usd = totals.cost_usd
            reason = _stop_reason(summary.calls, totals, max_cost_usd)
            if reason is not None:
                summary.stop_reason = reason
                logger.warning("[prompt_ab] stopping: %s (cost=%s)", reason, totals.cost_usd)
                return summary
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gemini 書き写し v7/v8/v9/v10/v101 の比較試験（結果は JSONL、DB は費用の台帳だけ）")
    p.add_argument("--runs-file", required=True, type=Path, help="対象の extraction_shadow_runs.id を1行1件で書いたファイル")
    p.add_argument("--config", required=True, choices=("v7", "v8", "v9", "v10", "v101"))
    p.add_argument("--prompt-name", help="--config v9・v101 のみ。prompts/ の raw_copy_v9_<名前>.txt（v9）／raw_copy_v101_<名前>.txt（v101、既定 raw_copy_v101_a）を指示書にする")
    p.add_argument("--thinking-level", type=str.lower, choices=_THINKING_LEVELS, help="v8・v9 のみ。未指定なら level を入れない")
    p.add_argument("--no-thoughts", action="store_true", help="v8・v9 のみ。考えた過程の要約を求めない")
    p.add_argument("--no-schema", action="store_true", help="v8・v9 のみ。JSON の型指定を付けない")
    p.add_argument("--temperature", type=float, default=None, help="v8・v9 のみ。未指定なら指定しない（既定 1.0）")
    p.add_argument("--repeat", type=int, required=True)
    p.add_argument("--max-cost-usd", type=Decimal, required=True, help="費用の累計の上限（USD）。超えたら止まる")
    p.add_argument("--test-id", required=True)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--dry-run", action="store_true", help="対象の件数と組み立てた指示の先頭30行だけ表示する（Gemini は呼ばない）")
    args = p.parse_args(argv)
    if args.thinking_level:
        args.thinking_level = args.thinking_level.upper()
    if args.config == "v7" and (
        args.thinking_level or args.no_thoughts or args.no_schema or args.temperature is not None
    ):
        p.error("--thinking-level / --no-thoughts / --no-schema / --temperature は --config v8・v9・v10・v101 のときだけ使えます")
    if args.prompt_name is not None:
        try:
            resolve_prompt_path(args.prompt_name, args.config)
        except ValueError as exc:
            p.error(str(exc))
    if args.repeat < 1:
        p.error("--repeat は 1 以上")
    return args


def _print_summary(s: AbSummary) -> None:
    if s.dry_run:
        return
    print(
        f"calls={s.calls} succeeded={s.succeeded} failed={s.failed} "
        f"total_cost_usd={s.total_cost_usd} stop_reason={s.stop_reason}"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ok, message = check_sdk_capabilities()
    print(message)
    if not ok:
        return 2
    run_ids = read_run_ids(args.runs_file)
    session = _get_sync_session()
    try:
        summary = run_ab(
            session, run_ids=run_ids, config=args.config, repeat=args.repeat,
            max_cost_usd=args.max_cost_usd, test_id=args.test_id, out_dir=args.out_dir,
            dry_run=args.dry_run, thinking_level=args.thinking_level,
            include_thoughts=not args.no_thoughts, use_schema=not args.no_schema,
            temperature=args.temperature, prompt_name=args.prompt_name,
        )
    finally:
        session.close()
    _print_summary(summary)
    return 0 if summary.stop_reason is None else 1


if __name__ == "__main__":
    sys.exit(main())
