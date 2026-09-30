from __future__ import annotations

"""
spec.md v1.1 F4 / Sprint 4: LLM コスト管理サービス。

`public.tenant_llm_budgets` テーブル (migration 062) に対し、月次予算チェック /
コスト記録 / 月初リセット を行う薄い service レイヤ。

設計思想:
  - public.tenant_llm_budgets は **マーケットプレイス中央テーブル**（tenant_id PK だが
    schema は public）。tenant 分離なし、admin が中央でレコード作成 → 各 LLM 呼び出し
    で参照・更新。memory: project_jarvis_inventory_marketplace.md
  - hard_stop = TRUE （migration 062 デフォルト）→ 超過時は API 呼ばない
  - last_reset_at < 当月 1 日 (JST 想定だが時刻計算は UTC) → current_month_usd = 0
  - row が存在しない tenant は「予算未設定」扱い (status = no_budget_row、デフォルト
    挙動は呼び出し側で「LLM 使用しない」とする)

  AC4.3: monthly_budget_usd = 0.01 設定 → 超過後 budget_exhausted で API 呼ばない
  AC4.4: 月初 `last_reset_at` が前月以前なら 0 リセット

Pricing:
  Gemini 2.5 Flash (2026-05 時点公式)
    - Input:  $0.075 / 1M tokens
    - Output: $0.30  / 1M tokens
  仕様で「ハードコード許容、別 ADR で外出し検討」と明記 (spec F4 AC4.2)。
  本ファイル末尾の `LLM_PRICING` 定数で集中管理。

Why this file is NOT a config module:
  pricing は LLM 呼び出しと結合度が高く、config (Settings) ではなく budget service
  と同居させた方が「呼び出し → record_cost で usage→USD 変換 → DB 更新」の流れが
  追いやすい。別 ADR で外出しする際は `LLM_PRICING` をそのまま `app/config.py` に
  移動すれば良い (Generator 判断: 4 — LLM_PRICING のハードコード位置 = llm_budget.py)。
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pricing constants (Gemini 2.5 Flash, 2026-05 時点公式)
# 別 ADR で外出し検討（spec F4 AC4.2）
# ---------------------------------------------------------------------------

# 1 token あたりの USD コスト。1M = 1_000_000 で割って単価化。
LLM_PRICING: dict[str, dict[str, Decimal]] = {
    "gemini-2.5-flash": {
        # $0.075 / 1M input tokens
        "input_per_token": Decimal("0.075") / Decimal("1000000"),
        # $0.30 / 1M output tokens
        "output_per_token": Decimal("0.30") / Decimal("1000000"),
    },
    # ADR-110: 送信英訳は最上位モデル必須
    "gemini-2.5-pro": {
        # $1.25 / 1M input tokens (2026-05 時点公式)
        "input_per_token": Decimal("1.25") / Decimal("1000000"),
        # $10.00 / 1M output tokens
        "output_per_token": Decimal("10.00") / Decimal("1000000"),
    },
    "gemini-2.5-flash-lite": {
        # $0.10 / 1M input tokens
        "input_per_token": Decimal("0.10") / Decimal("1000000"),
        # $0.40 / 1M output tokens
        "output_per_token": Decimal("0.40") / Decimal("1000000"),
    },
    "gemini-3.1-flash-lite": {
        # Standard text pricing, USD per 1M tokens (2026-09-11).
        "input_per_token": Decimal("0.25") / Decimal("1000000"),
        "output_per_token": Decimal("1.50") / Decimal("1000000"),
    },
    "gemini-3.5-flash-lite": {
        # $0.30 / 1M input tokens
        "input_per_token": Decimal("0.30") / Decimal("1000000"),
        # $2.50 / 1M output tokens
        "output_per_token": Decimal("2.50") / Decimal("1000000"),
    },
}

DEFAULT_MODEL = "gemini-3.5-flash-lite"


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class BudgetStatus(str, Enum):
    """check_budget() の戻り値。"""

    UNDER = "under"  # 予算内（API 呼んでよい）
    HARD_STOP = "hard_stop"  # 予算超過 + hard_stop=true（API 呼ばない）
    NO_BUDGET_ROW = "no_budget_row"  # tenant_llm_budgets に行なし（API 呼ばない）
    OVER_SOFT = "over_soft"  # 超過したが hard_stop=false（warn のみ、API 呼んで OK）


@dataclass(frozen=True)
class BudgetSnapshot:
    """tenant_llm_budgets の 1 行スナップショット。"""

    tenant_id: int
    monthly_budget_usd: Decimal
    current_month_usd: Decimal
    last_reset_at: datetime
    hard_stop: bool
    notify_admin: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _month_start_utc(now: datetime | None = None) -> datetime:
    """当月 1 日 00:00:00 UTC を返す（month boundary 判定用）。

    JST と UTC は最大 9 時間ズレるが、月次リセットの「1 日早い / 遅い」は
    spec 上問題なし（hard_stop で抑止できる）。シンプル優先で UTC 固定。
    """
    n = now or datetime.now(timezone.utc)
    return datetime(n.year, n.month, 1, 0, 0, 0, tzinfo=timezone.utc)


def calculate_cost(
    input_tokens: int, output_tokens: int, model: str = DEFAULT_MODEL
) -> Decimal:
    """token 数から USD コストを算出。

    Why Decimal: float では `0.075 / 1_000_000 * 1` が `7.5e-08` で
    Decimal NUMERIC(10,4) に丸めると 0 になる。Decimal で正確に計算してから
    DB 列の精度に丸める（DB 側で NUMERIC(10,4) に CAST されて quantize される）。
    """
    pricing = LLM_PRICING.get(model)
    if pricing is None:
        raise ValueError(f"unknown LLM model for pricing: {model!r}")
    in_cost = Decimal(input_tokens) * pricing["input_per_token"]
    out_cost = Decimal(output_tokens) * pricing["output_per_token"]
    return in_cost + out_cost


# ---------------------------------------------------------------------------
# llm_usage_events 台帳（ADR-1004: design docs/handoff/llm-usage-ledger/design.md §3）
#
# Gemini を呼ぶたびに1行、量の種類ごと・使いみちごとに記録する SSOT。
# extraction_attempts / extraction_shadow_runs への input_tokens/output_tokens/cost_usd
# の書き込みは本 PR 以降廃止し、この台帳に一本化する（旧列は残置・DROP なし）。
# ---------------------------------------------------------------------------

# purpose: 使いみち（design.md §3-1 CHECK 制約と同一の集合）
USAGE_PURPOSES: frozenset[str] = frozenset(
    {
        "line_extraction",
        "line_extraction_shadow",
        "inventory_parse_fallback",
        "translation_inbound",
        "translation_inbound_escalation",
        "translation_outbound",
    }
)

# sdk: どの SDK の usage_metadata から読んだか（design.md §3-1 CHECK 制約と同一の集合）
USAGE_SDKS: frozenset[str] = frozenset({"google-genai", "google-generativeai"})


@dataclass(frozen=True)
class UsageCounts:
    """Gemini usage_metadata から読んだトークン数（SDK が返さない値は None）。

    0 と None を区別する：SDK が値を返さなかった場合は None のまま記録し、
    「0 だった」と推測で埋めない（design.md §3-1）。
    """

    prompt_tokens: int | None = None
    cached_content_tokens: int | None = None
    candidates_tokens: int | None = None
    thoughts_tokens: int | None = None
    tool_use_prompt_tokens: int | None = None
    total_tokens: int | None = None


def usage_counts_from(usage: object) -> UsageCounts:
    """SDK の usage_metadata オブジェクトから UsageCounts を作る。

    属性が無い、または値が None の場合は None のまま（getattr の default は None、
    値取得後に int() するのは非 None のときだけ）。usage 自体が None でも安全。
    """

    def _read(name: str) -> int | None:
        value = getattr(usage, name, None)
        return int(value) if value is not None else None

    return UsageCounts(
        prompt_tokens=_read("prompt_token_count"),
        cached_content_tokens=_read("cached_content_token_count"),
        candidates_tokens=_read("candidates_token_count"),
        thoughts_tokens=_read("thoughts_token_count"),
        tool_use_prompt_tokens=_read("tool_use_prompt_token_count"),
        total_tokens=_read("total_token_count"),
    )


def calculate_usage_cost(counts: UsageCounts, model: str) -> Decimal | None:
    """UsageCounts から USD コストを算出（design.md §3-3）。

    cost = prompt_tokens × 入力単価 + (candidates_tokens + thoughts_tokens) × 出力単価。
    NULL は 0 として計算するが、prompt/candidates+thoughts の両方が None なら cost も None。
    単価表に無いモデルは None（例外にしない。台帳は「不明」を許容する設計）。
    """
    pricing = LLM_PRICING.get(model)
    if pricing is None:
        return None
    if counts.prompt_tokens is None and counts.candidates_tokens is None and counts.thoughts_tokens is None:
        return None
    prompt = counts.prompt_tokens or 0
    output = (counts.candidates_tokens or 0) + (counts.thoughts_tokens or 0)
    in_cost = Decimal(prompt) * pricing["input_per_token"]
    out_cost = Decimal(output) * pricing["output_per_token"]
    return in_cost + out_cost


def _usage_event_columns(
    *,
    purpose: str,
    model: str,
    sdk: str,
    counts: UsageCounts,
    tenant_id: int | None,
    extraction_attempt_id: str | None,
    extraction_shadow_run_id: str | None,
    discord_inbound_message_id: int | None,
    source_ref: str | None,
) -> dict[str, Any]:
    if purpose not in USAGE_PURPOSES:
        raise ValueError(f"unknown llm_usage_events purpose: {purpose!r}")
    if sdk not in USAGE_SDKS:
        raise ValueError(f"unknown llm_usage_events sdk: {sdk!r}")
    cost = calculate_usage_cost(counts, model)
    return {
        "id": str(uuid4()),
        "purpose": purpose,
        "tenant_id": tenant_id,
        "model": model,
        "sdk": sdk,
        "prompt_tokens": counts.prompt_tokens,
        "cached_content_tokens": counts.cached_content_tokens,
        "candidates_tokens": counts.candidates_tokens,
        "thoughts_tokens": counts.thoughts_tokens,
        "tool_use_prompt_tokens": counts.tool_use_prompt_tokens,
        "total_tokens": counts.total_tokens,
        "cost_usd": str(cost) if cost is not None else None,
        "extraction_attempt_id": extraction_attempt_id,
        "extraction_shadow_run_id": extraction_shadow_run_id,
        "discord_inbound_message_id": discord_inbound_message_id,
        "source_ref": source_ref,
    }


_INSERT_USAGE_EVENT_SQL = """
    INSERT INTO public.llm_usage_events
        (id, purpose, tenant_id, model, sdk,
         prompt_tokens, cached_content_tokens, candidates_tokens, thoughts_tokens,
         tool_use_prompt_tokens, total_tokens, cost_usd,
         extraction_attempt_id, extraction_shadow_run_id, discord_inbound_message_id, source_ref)
    VALUES
        (:id, :purpose, :tenant_id, :model, :sdk,
         :prompt_tokens, :cached_content_tokens, :candidates_tokens, :thoughts_tokens,
         :tool_use_prompt_tokens, :total_tokens, :cost_usd,
         :extraction_attempt_id, :extraction_shadow_run_id, :discord_inbound_message_id, :source_ref)
"""


def record_usage_event_sync(
    session: Session,
    *,
    purpose: str,
    model: str,
    sdk: str,
    counts: UsageCounts,
    tenant_id: int | None = None,
    extraction_attempt_id: str | None = None,
    extraction_shadow_run_id: str | None = None,
    discord_inbound_message_id: int | None = None,
    source_ref: str | None = None,
) -> str:
    """llm_usage_events に1行 INSERT する（sync Session 版、呼び出し元のトランザクション内）。

    commit しない（呼び出し元がまとめて commit する）。戻り値は生成した id。
    """
    cols = _usage_event_columns(
        purpose=purpose, model=model, sdk=sdk, counts=counts, tenant_id=tenant_id,
        extraction_attempt_id=extraction_attempt_id, extraction_shadow_run_id=extraction_shadow_run_id,
        discord_inbound_message_id=discord_inbound_message_id, source_ref=source_ref,
    )
    session.execute(text(_INSERT_USAGE_EVENT_SQL), cols)
    return cols["id"]


async def record_usage_event(
    db: AsyncSession,
    *,
    purpose: str,
    model: str,
    sdk: str,
    counts: UsageCounts,
    tenant_id: int | None = None,
    extraction_attempt_id: str | None = None,
    extraction_shadow_run_id: str | None = None,
    discord_inbound_message_id: int | None = None,
    source_ref: str | None = None,
) -> str:
    """llm_usage_events に1行 INSERT する（async Session 版、呼び出し元のトランザクション内）。

    commit しない（呼び出し元がまとめて commit する）。戻り値は生成した id。
    """
    cols = _usage_event_columns(
        purpose=purpose, model=model, sdk=sdk, counts=counts, tenant_id=tenant_id,
        extraction_attempt_id=extraction_attempt_id, extraction_shadow_run_id=extraction_shadow_run_id,
        discord_inbound_message_id=discord_inbound_message_id, source_ref=source_ref,
    )
    await db.execute(text(_INSERT_USAGE_EVENT_SQL), cols)
    return cols["id"]


# ---------------------------------------------------------------------------
# DB ops
# ---------------------------------------------------------------------------


async def _load_budget(db: AsyncSession, tenant_id: int) -> BudgetSnapshot | None:
    result = await db.execute(
        text(
            """
            SELECT tenant_id, monthly_budget_usd, current_month_usd,
                   last_reset_at, hard_stop, notify_admin
              FROM public.tenant_llm_budgets
             WHERE tenant_id = :tid
            """
        ),
        {"tid": tenant_id},
    )
    row = result.mappings().first()
    if row is None:
        return None
    return BudgetSnapshot(
        tenant_id=row["tenant_id"],
        monthly_budget_usd=Decimal(row["monthly_budget_usd"]),
        current_month_usd=Decimal(row["current_month_usd"]),
        last_reset_at=row["last_reset_at"],
        hard_stop=row["hard_stop"],
        notify_admin=row["notify_admin"],
    )


async def reset_monthly_if_needed(
    db: AsyncSession, tenant_id: int, *, now: datetime | None = None
) -> bool:
    """月初判定。last_reset_at が当月 1 日より前なら current_month_usd を 0 にリセット。

    呼び出しタイミング: parse_inventory_message() の冒頭。
    cron でも可だが、起動時 check の方が新規テナント直後でも安全。

    戻り値:
        True: リセットを実行した
        False: リセット不要 (当月内) または budget 行なし
    """
    snap = await _load_budget(db, tenant_id)
    if snap is None:
        return False
    boundary = _month_start_utc(now)
    if snap.last_reset_at >= boundary:
        return False
    # 月跨ぎ。リセット。
    await db.execute(
        text(
            """
            UPDATE public.tenant_llm_budgets
               SET current_month_usd = 0,
                   last_reset_at     = :now
             WHERE tenant_id = :tid
            """
        ),
        {"tid": tenant_id, "now": now or datetime.now(timezone.utc)},
    )
    logger.info(
        "[llm_budget] monthly reset: tenant_id=%s prev_usage=%s",
        tenant_id,
        snap.current_month_usd,
    )
    return True


async def check_budget(db: AsyncSession, tenant_id: int) -> BudgetStatus:
    """予算チェック。LLM API を呼ぶ前に必ず呼ぶ。

    判定:
        - budget row 無し → NO_BUDGET_ROW （API 呼ばない）
        - current_month_usd >= monthly_budget_usd かつ hard_stop=true → HARD_STOP
        - current_month_usd >= monthly_budget_usd かつ hard_stop=false → OVER_SOFT
        - それ以外 → UNDER
    """
    snap = await _load_budget(db, tenant_id)
    if snap is None:
        return BudgetStatus.NO_BUDGET_ROW
    if snap.monthly_budget_usd > 0 and snap.current_month_usd >= snap.monthly_budget_usd:
        return BudgetStatus.HARD_STOP if snap.hard_stop else BudgetStatus.OVER_SOFT
    return BudgetStatus.UNDER


async def record_cost(
    db: AsyncSession,
    tenant_id: int,
    input_tokens: int,
    output_tokens: int,
    *,
    model: str = DEFAULT_MODEL,
) -> Decimal:
    """LLM 呼び出し後にコストを加算。返り値はこの呼び出しのコスト（USD）。

    DB 列は NUMERIC(10, 4) なので 4 桁精度に quantize した値を SUM 加算する。
    Decimal の文字列化を SQL に通すと PostgreSQL 側で NUMERIC へ自動 cast される。
    """
    cost = calculate_cost(input_tokens, output_tokens, model=model)
    # NUMERIC(10,4) に合わせて 4 桁丸め (ROUND_HALF_UP は Python Decimal の default)
    cost_4 = cost.quantize(Decimal("0.0001"))
    await db.execute(
        text(
            """
            UPDATE public.tenant_llm_budgets
               SET current_month_usd = current_month_usd + :cost
             WHERE tenant_id = :tid
            """
        ),
        {"tid": tenant_id, "cost": str(cost_4)},
    )
    logger.info(
        "[llm_budget] cost recorded: tenant_id=%s in_tokens=%s out_tokens=%s cost_usd=%s",
        tenant_id,
        input_tokens,
        output_tokens,
        cost_4,
    )
    return cost_4


async def get_budget_snapshot(
    db: AsyncSession, tenant_id: int
) -> BudgetSnapshot | None:
    """テスト / admin API 用に snapshot を公開。"""
    return await _load_budget(db, tenant_id)


async def ensure_budget_row(
    db: AsyncSession,
    tenant_id: int,
    *,
    monthly_budget_usd: Decimal = Decimal("0"),
    hard_stop: bool = True,
    notify_admin: bool = True,
) -> BudgetSnapshot:
    """テナント作成 / 初回設定時に行を作成。冪等。

    AC4.6 admin UI から PUT で更新する経路は別だが、未存在 tenant に対する
    初期化は本関数で行う（ON CONFLICT DO NOTHING）。
    """
    await db.execute(
        text(
            """
            INSERT INTO public.tenant_llm_budgets
                (tenant_id, monthly_budget_usd, current_month_usd,
                 last_reset_at, hard_stop, notify_admin)
            VALUES
                (:tid, :budget, 0, NOW(), :hard_stop, :notify_admin)
            ON CONFLICT (tenant_id) DO NOTHING
            """
        ),
        {
            "tid": tenant_id,
            "budget": str(monthly_budget_usd),
            "hard_stop": hard_stop,
            "notify_admin": notify_admin,
        },
    )
    snap = await _load_budget(db, tenant_id)
    assert snap is not None  # noqa: S101 - INSERT or existing row
    return snap


__all__ = [
    "BudgetStatus",
    "BudgetSnapshot",
    "DEFAULT_MODEL",
    "LLM_PRICING",
    "USAGE_PURPOSES",
    "USAGE_SDKS",
    "UsageCounts",
    "calculate_cost",
    "calculate_usage_cost",
    "check_budget",
    "ensure_budget_row",
    "get_budget_snapshot",
    "record_cost",
    "record_usage_event",
    "record_usage_event_sync",
    "reset_monthly_if_needed",
    "usage_counts_from",
]
