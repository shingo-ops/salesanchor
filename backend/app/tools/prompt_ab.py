"""Gemini 書き写し v7/v8/v9/v10/v10.1 の比較試験の道具（読み取り＋費用の台帳だけ）。

設計: docs/handoff/gemini-v8/design.md §6
      docs/handoff/gemini-v9/design.md §5-1（v9）
      docs/handoff/gemini-v9-trial1/design.md §3（--prompt-name）
      docs/handoff/gemini-v10/design.md §3-5（v10）
      docs/handoff/gemini-v101/design.md §3-6（v101）
      docs/handoff/gemini-v102/design.md §3-3（v102）
      docs/handoff/gemini-supplier-rules-file/design.md §3（--supplier-rules-file）
      docs/handoff/prompt-ab-db-source/design.md §3（--prompt-key）
起動: python -m app.tools.prompt_ab --runs-file F --config v7|v8|v9|v10|v101|v102 [--prompt-name raw_copy_v9_NAME|raw_copy_v101_NAME] [--prompt-key raw_copy_v101_NAME]
        [--thinking-level L] [--no-thoughts] [--no-schema] [--temperature T] [--omit-supplier-field extraction_XXX ...] [--supplier-rules-file F] [--keep-legacy-supplier-fields] --repeat N --max-cost-usd X --test-id ID --out-dir /tmp/prompt_ab/ID [--dry-run]

（--config v102 で --prompt-name・--prompt-key なしのときの既定の指示書は DB の key raw_copy_v101_f_c）
結果は out-dir の JSONL にだけ書く（1回につき1行）。DB に書くのは llm_usage_events（費用の台帳）だけで、
purpose="line_extraction_shadow"・source_ref="prompt_ab:<test_id>" で区別する。
extraction_shadow_runs / extraction_jobs など本番の表には書かない。
"""
from __future__ import annotations

import argparse
import hashlib
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
    DEFAULT_V102_PROMPT_NAME,
    V101_PROMPT_NAME_RE,
    V101_RESPONSE_SCHEMA,
    V102_RESPONSE_SCHEMA,
    extract_v101_items,
    parse_v101_response,
)
from app.services.gemini_raw_copy_v102_product_first import load_product_first_masters
from app.services.line_analysis_v102_svc import (  # v102 の本番部品（移した関数は同じ名前でここから読む）
    LEGACY_SUPPLIER_FIELDS,
    V102_PROMPT_KEY,
    check_prompt_key_shape,
    load_prompt_from_db,
    run_v102_pipeline,
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
    "v102": V101_PROMPT_NAME_RE,
}
_PROMPT_NAME_CONFIGS = "v9・v101・v102"
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
        elif config in ("v101", "v102"):
            items, errors = parse_v101_response(
                response_text, raw_text, status_entries=(masters or {}).get("status_entries")
            )
        else:
            items, errors = parse_v8_response(response_text, raw_text)
    except Exception as exc:  # noqa: BLE001
        return 0, [{"error": f"{type(exc).__name__}: {_safe_error_message(exc)}"}]
    return len(items), errors


def _load_v10_masters(session: Session, *, product_first: bool = False) -> dict:
    """v10 の取り出しに使うマスタを読む（読み取りのみ。1回の実行で1回だけ呼ぶ）。

    product_first（試作版 v102）のときだけ、商品・商品の分類・状態ごとの単位・単位にしない言い回しも読む。
    これらが空なら ValueError で止める。v10・v101 には足さない（**masters で展開されるため）。
    """
    cond_entries = load_condition_entries(session)
    status_entries = load_status_master(session)
    (_pc, _ua, _uc, _ca, cond_canonical_to_uuid, unit_alias_to_info) = load_lookup_maps(session)
    masters = {
        "cond_entries": cond_entries, "cond_canonical_to_uuid": cond_canonical_to_uuid,
        "unit_alias_to_info": unit_alias_to_info, "status_entries": status_entries,
    }
    if product_first:
        return {**masters, "product_first": load_product_first_masters(session)}
    return masters


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


def _v102_row_fields(response_text: str, ctx, masters: dict) -> dict:
    """JSONL の v102 の行に足す v102_items・v102_flags。本体は本番と共通の run_v102_pipeline（services/line_analysis_v102_svc.py）。

    試験で pab.extract_v101_items を差し替えられるよう、ここの extract_v101_items を渡す。
    """
    return run_v102_pipeline(response_text, ctx, masters, extract_items=extract_v101_items)


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


_PROMPT_KEY_CONFIGS = ("v101", "v102")
V102_PROMPT = V102_PROMPT_KEY  # v102 で --prompt-name も --prompt-key もないときの既定の指示書（DB の prompt_key）
_check_prompt_key_shape = check_prompt_key_shape  # --prompt-key の形の検査（DB には触れない）


def _load_prompt_text(
    config: str, prompt_name: str | None = None, prompt_key: str | None = None, session: Session | None = None,
) -> str | None:
    """v8・v9・v10・v101・v102 の指示書の本文。v7 は DB の指示書を既存関数が読むので None。"""
    if prompt_key is not None:
        if session is None:
            raise ValueError("--prompt-key には DB の session が要ります")
        return load_prompt_from_db(session, prompt_key)
    if prompt_name is not None:
        return resolve_prompt_path(prompt_name, config).read_text(encoding="utf-8")
    if config == "v101":
        return resolve_prompt_path(DEFAULT_V101_PROMPT_NAME, config).read_text(encoding="utf-8")
    if config == "v102":
        return resolve_prompt_path(DEFAULT_V102_PROMPT_NAME, config).read_text(encoding="utf-8")
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
    if config == "v102":
        return _v102_row_fields(response_text, ctx, masters)
    return {}


_SUPPLIER_FIELD_PATTERN = re.compile(r"^extraction_[a-z_]+$")

# 新しい仕組み（v8 系）だけが読む欄。supplier_context ではなく new_system_rules 側で扱う。
_NEW_SYSTEM_FIELDS = ("extraction_layout_rules", "extraction_hard_cases")

def _supplier_field_name(value: str) -> str:
    """--omit-supplier-field の値の検査（extraction_ で始まる欄名だけ認める）。"""
    if not _SUPPLIER_FIELD_PATTERN.fullmatch(value):
        raise argparse.ArgumentTypeError(f"仕入元ルールの欄名は extraction_ で始まる英小文字だけ: {value!r}")
    return value


def _supplier_context_without(supplier_context: dict | None, omit: list[str] | None) -> dict | None:
    """指定した欄を除いた写しを返す（元の辞書は変えない）。指定なしなら元のものをそのまま返す。"""
    if not omit or supplier_context is None:
        return supplier_context
    return {k: v for k, v in supplier_context.items() if k not in omit}


def load_supplier_rules_file(path: Path) -> tuple[dict[str, dict], str]:
    """--supplier-rules-file の読み込みと検査。(仕入元 id → 欄の辞書, ファイルの sha256)。不正なら ValueError。

    形: {"<仕入元 id>": {"extraction_xxx": "値" または null, ...}, ...}
    """
    try:
        raw = Path(path).read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:  # JSONDecodeError・UnicodeDecodeError は ValueError の仲間
        raise ValueError(f"--supplier-rules-file を読めません: {path}: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise ValueError("--supplier-rules-file の中身は {仕入元 id: {欄名: 値}} の JSON オブジェクトにしてください")
    for supplier_id, fields in data.items():
        if not isinstance(fields, dict):
            raise ValueError(f"--supplier-rules-file: 仕入元 {supplier_id!r} の値は欄名と値のオブジェクトにしてください")
        for name, value in fields.items():
            if not _SUPPLIER_FIELD_PATTERN.fullmatch(name):
                raise ValueError(f"--supplier-rules-file: 欄名は extraction_ で始まる英小文字だけ: {name!r}")
            if value is not None and not isinstance(value, str):
                raise ValueError(f"--supplier-rules-file: {name} の値は文字列か null だけ")
    return data, hashlib.sha256(raw).hexdigest()


def _supplier_context_with_rules(
    ctx, rules: dict[str, dict] | None, rules_sha256: str | None,
) -> tuple[dict | None, dict | None]:
    """(差し替え後の supplier_context, JSONL に書く supplier_rules_override)。

    ctx.supplier_id がファイルに無いときは (元の supplier_context, None)。元の辞書は変えない。
    ファイルにない欄は元の値のまま。値が null の欄は外す。
    """
    if not rules or ctx.supplier_id is None or str(ctx.supplier_id) not in rules:
        return ctx.supplier_context, None
    fields = rules[str(ctx.supplier_id)]
    old_fields = {k: v for k, v in fields.items() if k not in _NEW_SYSTEM_FIELDS}
    if old_fields:
        merged = {**(ctx.supplier_context or {}), **old_fields}
        merged = {k: v for k, v in merged.items() if not (k in old_fields and old_fields[k] is None)}
    else:
        merged = ctx.supplier_context
    override = {"file_sha256": rules_sha256, "supplier_id": str(ctx.supplier_id), "fields": sorted(fields)}
    return merged, override


def _effective_supplier_context(
    ctx, rules: dict[str, dict] | None, rules_sha256: str | None, omit: list[str] | None,
) -> tuple[dict | None, dict | None]:
    """差し替えのあとに外す（設計 §3）。"""
    replaced, override = _supplier_context_with_rules(ctx, rules, rules_sha256)
    return _supplier_context_without(replaced, omit), override


def _effective_new_system_rules(
    ctx, rules: dict[str, dict] | None, omit: list[str] | None,
) -> dict | None:
    """v8 系にだけ渡す new_system_rules。ファイルの値で上書き（null は外す）し、--omit-supplier-field の欄を外す。

    元の辞書は変えない。空になったら None。v7 には渡さない。
    """
    base = dict(getattr(ctx, "new_system_rules", None) or {})
    if rules and ctx.supplier_id is not None and str(ctx.supplier_id) in rules:
        for name, value in rules[str(ctx.supplier_id)].items():
            if name not in _NEW_SYSTEM_FIELDS:
                continue
            if value is None:
                base.pop(name, None)
            else:
                base[name] = value
    for name in omit or []:
        base.pop(name, None)
    return base if any(base.values()) else None


def _print_dry_run(
    summary: AbSummary, config: str, ctx, v8_prompt: str | None, omit_supplier_fields: list[str] | None = None,
    rules: dict[str, dict] | None = None, rules_sha256: str | None = None,
) -> None:
    print(f"[dry-run] target_count={summary.target_count}")
    if ctx is None:
        return
    supplier_context, _override = _effective_supplier_context(ctx, rules, rules_sha256, omit_supplier_fields)
    if config in ("v8", "v9", "v10", "v101", "v102"):
        prompt = build_prompt_v8(
            ctx.raw_text, prompt_text=v8_prompt or "", supplier_context=supplier_context,
            knowledge_links=ctx.knowledge_links,
            new_system_rules=_effective_new_system_rules(ctx, rules, omit_supplier_fields),
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
    omit_supplier_fields: list[str] | None = None, supplier_rules_file: Path | None = None,
    prompt_key: str | None = None,
) -> AbSummary:
    summary = AbSummary(target_count=len(run_ids), dry_run=dry_run)
    rules: dict[str, dict] | None = None
    rules_sha256: str | None = None
    if supplier_rules_file is not None:  # 誤りはここで止まる（Gemini を呼ぶ前）
        if config == "v7":
            raise ValueError("--supplier-rules-file は --config v8・v9・v10・v101・v102 のときだけ使えます")
        rules, rules_sha256 = load_supplier_rules_file(supplier_rules_file)
    job_ids = fetch_job_ids(session, run_ids)
    if prompt_key is not None and (config not in _PROMPT_KEY_CONFIGS or prompt_name is not None):
        raise ValueError("--prompt-key は --config v101・v102 のときだけ、--prompt-name なしで使えます")
    if config == "v102" and prompt_name is None and prompt_key is None:
        prompt_key = V102_PROMPT
    v8_prompt = _load_prompt_text(config, prompt_name, prompt_key, session)  # 名前・ファイル・行の誤りはここで止まる（Gemini を呼ぶ前）
    prompt_source = "db" if prompt_key is not None else (None if config == "v7" else "file")
    prompt_sha256 = hashlib.sha256(v8_prompt.encode("utf-8")).hexdigest() if v8_prompt is not None else None
    if prompt_key is not None:
        logger.info("[prompt_ab] prompt_key=%s sha256=%s", prompt_key, prompt_sha256)
    row_prompt_name = prompt_key or {
        "v9": prompt_name or _DEFAULT_V9_PROMPT_NAME, "v101": prompt_name or DEFAULT_V101_PROMPT_NAME,
        "v102": prompt_name or DEFAULT_V102_PROMPT_NAME,
    }.get(config)
    source_ref = f"{_SOURCE_REF_PREFIX}{test_id}"
    out_path = Path(out_dir) / f"{test_id}.jsonl"
    contexts: dict[str, object] = {}

    if dry_run:
        first = next((job_ids[r] for r in run_ids if r in job_ids), None)
        ctx = load_extraction_context(session, first) if first else None
        _print_dry_run(summary, config, ctx, v8_prompt, omit_supplier_fields, rules, rules_sha256)
        return summary

    masters = (  # dry-run では読まない
        _load_v10_masters(session, product_first=(config == "v102")) if config in ("v10", "v101", "v102") else None
    )
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
            row["prompt_source"] = prompt_source
            row["prompt_sha256"] = prompt_sha256
            if omit_supplier_fields:
                row["omitted_supplier_fields"] = sorted(set(omit_supplier_fields))
            try:
                if job_id not in contexts:
                    ctx_loaded = load_extraction_context(session, job_id)
                    if ctx_loaded is None:
                        raise RuntimeError(f"job not found: {job_id}")
                    contexts[job_id] = ctx_loaded
                ctx = contexts[job_id]
                supplier_context, override = _effective_supplier_context(ctx, rules, rules_sha256, omit_supplier_fields)
                if override is not None:
                    row["supplier_rules_override"] = override
                if config == "v7":
                    result = _call_v7(ctx)
                else:
                    schemas = {
                        "v9": V9_RESPONSE_SCHEMA, "v10": V10_RESPONSE_SCHEMA,
                        "v101": V101_RESPONSE_SCHEMA, "v102": V102_RESPONSE_SCHEMA,
                    }
                    extra = {"response_schema": schemas[config]} if config in schemas else {}
                    result = call_gemini_raw_copy_v8(
                        ctx.raw_text, prompt_text=v8_prompt,
                        supplier_context=supplier_context,
                        new_system_rules=_effective_new_system_rules(ctx, rules, omit_supplier_fields),
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
    p = argparse.ArgumentParser(description="Gemini 書き写し v7/v8/v9/v10/v101/v102 の比較試験（結果は JSONL、DB は費用の台帳だけ）")
    p.add_argument("--runs-file", required=True, type=Path, help="対象の extraction_shadow_runs.id を1行1件で書いたファイル")
    p.add_argument("--config", required=True, choices=("v7", "v8", "v9", "v10", "v101", "v102"))
    p.add_argument("--prompt-name", help="--config v9・v101・v102 のみ。prompts/ の raw_copy_v9_<名前>.txt（v9）／raw_copy_v101_<名前>.txt（v101 は既定 raw_copy_v101_a、v102 は既定 DB の key raw_copy_v101_f_c）を指示書にする")
    p.add_argument("--prompt-key", help="--config v101・v102 のみ。public.extraction_prompt_config の prompt_key（raw_copy_v101_<名前>、is_active）の本文を指示書にする。--prompt-name とは同時に使えない")
    p.add_argument("--thinking-level", type=str.lower, choices=_THINKING_LEVELS, help="v8・v9 のみ。未指定なら level を入れない")
    p.add_argument("--no-thoughts", action="store_true", help="v8・v9 のみ。考えた過程の要約を求めない")
    p.add_argument("--no-schema", action="store_true", help="v8・v9 のみ。JSON の型指定を付けない")
    p.add_argument("--temperature", type=float, default=None, help="v8・v9 のみ。未指定なら指定しない（既定 1.0）")
    p.add_argument("--repeat", type=int, required=True)
    p.add_argument("--max-cost-usd", type=Decimal, required=True, help="費用の累計の上限（USD）。超えたら止まる")
    p.add_argument("--test-id", required=True)
    p.add_argument("--out-dir", required=True, type=Path)
    p.add_argument("--omit-supplier-field", action="append", type=_supplier_field_name, default=None,
                   help="仕入元ルールの欄（extraction_ で始まる名前）を指示から外す。何回でも指定できる。v7 では効かない")
    p.add_argument("--supplier-rules-file", type=Path, default=None,
                   help="仕入元 id ごとに extraction_* の欄を差し替える JSON（{\"id\": {\"extraction_x\": 値 or null}}）。ファイルに無い欄は DB の値のまま、null は欄を外す。--omit-supplier-field より先に適用。v7 では効かない")
    p.add_argument("--keep-legacy-supplier-fields", action="store_true",
                   help="--config v102 のみ。既定で外す元からある7欄（LEGACY_SUPPLIER_FIELDS）を外さずに渡す（比較試験用）")
    p.add_argument("--dry-run", action="store_true", help="対象の件数と組み立てた指示の先頭30行だけ表示する（Gemini は呼ばない）")
    args = p.parse_args(argv)
    if args.thinking_level:
        args.thinking_level = args.thinking_level.upper()
    if args.config == "v7" and (
        args.thinking_level or args.no_thoughts or args.no_schema or args.temperature is not None
    ):
        p.error("--thinking-level / --no-thoughts / --no-schema / --temperature は --config v8・v9・v10・v101・v102 のときだけ使えます")
    if args.config == "v7" and args.omit_supplier_field:
        p.error("--omit-supplier-field は --config v8・v9・v10・v101・v102 のときだけ使えます")
    if args.supplier_rules_file is not None:
        if args.config == "v7":
            p.error("--supplier-rules-file は --config v8・v9・v10・v101・v102 のときだけ使えます")
        try:
            load_supplier_rules_file(args.supplier_rules_file)
        except ValueError as exc:
            p.error(str(exc))
    if args.prompt_key is not None:
        if args.config not in _PROMPT_KEY_CONFIGS:
            p.error("--prompt-key は --config v101・v102 のときだけ使えます")
        if args.prompt_name is not None:
            p.error("--prompt-key と --prompt-name は同時に使えません")
        try:
            _check_prompt_key_shape(args.prompt_key)
        except ValueError as exc:
            p.error(str(exc))
    if args.prompt_name is not None:
        try:
            resolve_prompt_path(args.prompt_name, args.config)
        except ValueError as exc:
            p.error(str(exc))
    if args.repeat < 1:
        p.error("--repeat は 1 以上")
    if args.keep_legacy_supplier_fields and args.config != "v102":
        p.error("--keep-legacy-supplier-fields は --config v102 のときだけ使えます")
    if args.config == "v102" and not args.keep_legacy_supplier_fields:
        args.omit_supplier_field = sorted(set(args.omit_supplier_field or []) | set(LEGACY_SUPPLIER_FIELDS))
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
            omit_supplier_fields=args.omit_supplier_field, supplier_rules_file=args.supplier_rules_file,
            prompt_key=args.prompt_key,
        )
    finally:
        session.close()
    _print_summary(summary)
    return 0 if summary.stop_reason is None else 1


if __name__ == "__main__":
    sys.exit(main())
