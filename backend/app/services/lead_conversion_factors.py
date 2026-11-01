"""成約しやすさの分析（ロジスティック回帰・標準ライブラリだけ）。

docs/handoff/lead-regression/card-a-backend.md §2 の決まりを実装する。
本番の入口（GET /analytics/lead-conversion-factors）と、本番の外の確かめ
（scripts/lead_regression/k3_run.py）の両方が、この 1 ファイルだけを使う。

- 入力は LeadRow / MessageRow に揃えてから渡す（DB の読み方は呼び出し側）
- 計算は float・ニュートン法（IRLS と同じ）・自前のガウス・ジョルダン法
- 丸めない（丸めは画面だけ）
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from app.schemas.lead import (
    LeadCustomerType,
    LeadScale,
    LeadStatus,
    LeadTemperature,
)

# ── 値の綴り ───────────────────────────────────────────────
# 状態・温度・規模・顧客タイプは backend/app/schemas/lead.py の列挙から取る。
STATUS_WON = LeadStatus.existing_customer.value
STATUS_LOST = LeadStatus.lost.value
TEMPERATURE_HOT = LeadTemperature.hot.value
TEMPERATURE_WARM = LeadTemperature.warm.value
TEMPERATURE_COLD = LeadTemperature.cold.value
SCALE_SMALL = LeadScale.small.value
SCALE_MEDIUM = LeadScale.medium.value
SCALE_LARGE = LeadScale.large.value
CUSTOMER_TYPE_TRUST = LeadCustomerType.trust.value
CUSTOMER_TYPE_PRICE = LeadCustomerType.price.value

# initiative は schemas に列挙が無い（LeadType は旧 type 用の別物）。ここ 1 か所に置く。
INITIATIVE_INBOUND = "inbound"
INITIATIVE_OUTBOUND = "outbound"

# channel_type は channel_masters の platform の値。
CHANNEL_MESSENGER = "messenger"
CHANNEL_INSTAGRAM = "instagram"
CHANNEL_WHATSAPP = "whatsapp"
META_CHANNELS = (CHANNEL_INSTAGRAM, CHANNEL_MESSENGER)  # meta_messages を読む
CHANNELS = (CHANNEL_MESSENGER, CHANNEL_INSTAGRAM, CHANNEL_WHATSAPP)

COUNTRY_US = "US"
COUNTRY_GB = "GB"
COUNTRY_AU = "AU"
COUNTRIES = (COUNTRY_US, COUNTRY_GB, COUNTRY_AU)

SALES_FORM_WHOLESALE = "wholesale"

DIRECTION_INBOUND = "inbound"
DIRECTION_OUTBOUND = "outbound"

# ── 決まりの数値 ───────────────────────────────────────────
FIRST_REPLY_LIMIT_SECONDS = 3600  # ≦
PARTNER_REPLY_LIMIT_SECONDS = 21600  # ≦
REQUIRED_PER_ITEM = 10
Z_975 = 1.959963984540054
NEWTON_MAX_ITER = 100
NEWTON_TOL = 1e-10
PIVOT_MIN = 1e-12
BETA_ABS_MAX = 20.0

# 15 項目（この順・この名前で固定。カード B も同じ）
ITEM_KEYS: tuple[str, ...] = (
    "initiative_inbound",
    "sales_form_wholesale",
    "first_reply_within_1h",
    "partner_reply_within_6h",
    "channel_whatsapp",
    "channel_instagram",
    "country_gb",
    "country_au",
    "temperature_hot",
    "temperature_warm",
    "message_count",
    "scale_large",
    "scale_medium",
    "customer_type_trust",
    "competitor_found",
)
ITEM_COUNT = len(ITEM_KEYS)

EXCLUDED_KEYS: tuple[str, ...] = (
    "by_status",
    "other_values",
    "no_inbound",
    "no_outbound",
    "no_reply_pair",
    "no_sales_form",
    "missing_scale_or_type",
)


# ── 入力の形 ───────────────────────────────────────────────
@dataclass(frozen=True)
class LeadRow:
    id: int
    status: str
    initiative: str | None
    channel_type: str | None
    country: str | None
    temperature: str | None
    estimated_scale: str | None
    customer_type: str | None
    competitor_check: bool
    sales_form_values: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MessageRow:
    lead_id: int
    id: int
    direction: str  # "inbound" / "outbound"
    ts: datetime  # timezone 付き


# ── 特徴の作成 ─────────────────────────────────────────────
def _ordered_messages(messages: list[MessageRow]) -> dict[int, list[MessageRow]]:
    """lead_id ごとに 時刻の昇順・同時刻は id の昇順 に並べる。"""
    by_lead: dict[int, list[MessageRow]] = {}
    for m in messages:
        by_lead.setdefault(m.lead_id, []).append(m)
    for rows in by_lead.values():
        rows.sort(key=lambda m: (m.ts, m.id))
    return by_lead


def first_reply_seconds(msgs: list[MessageRow]) -> float | None:
    """最初の inbound から、並びでそれより後ろの最初の outbound までの秒数。"""
    first_in = next((i for i, m in enumerate(msgs) if m.direction == DIRECTION_INBOUND), None)
    if first_in is None:
        return None
    for m in msgs[first_in + 1 :]:
        if m.direction == DIRECTION_OUTBOUND:
            return (m.ts - msgs[first_in].ts).total_seconds()
    return None


def partner_reply_mean_seconds(msgs: list[MessageRow]) -> float | None:
    """すぐ前の行が outbound である inbound それぞれの、その outbound からの秒数の算術平均。"""
    gaps = [
        (msgs[j].ts - msgs[j - 1].ts).total_seconds()
        for j in range(1, len(msgs))
        if msgs[j].direction == DIRECTION_INBOUND and msgs[j - 1].direction == DIRECTION_OUTBOUND
    ]
    if not gaps:
        return None
    return sum(gaps) / len(gaps)


@dataclass
class Prepared:
    lead_ids: list[int]  # id 昇順
    x: list[list[float]]  # 定数 1 の列 ＋ 15 列
    y: list[int]
    excluded: dict[str, int]

    @property
    def won_count(self) -> int:
        return sum(self.y)

    @property
    def lost_count(self) -> int:
        return len(self.y) - sum(self.y)


def prepare(leads: list[LeadRow], messages: list[MessageRow]) -> Prepared:
    """§2-3〜§2-5: 外す決まりを上から当て、説明の行列を作る。"""
    by_lead = _ordered_messages(messages)
    excluded = {k: 0 for k in EXCLUDED_KEYS}
    ids: list[int] = []
    x_rows: list[list[float]] = []
    y: list[int] = []

    for lead in sorted(leads, key=lambda r: r.id):
        # 1. by_status
        if lead.status not in (STATUS_WON, STATUS_LOST):
            excluded["by_status"] += 1
            continue
        # 2. other_values（空・対象外の値。温度は列挙外の値もここに入れる）
        if (
            lead.channel_type not in CHANNELS
            or lead.country not in COUNTRIES
            or lead.temperature not in (TEMPERATURE_HOT, TEMPERATURE_WARM, TEMPERATURE_COLD)
            or lead.initiative not in (INITIATIVE_INBOUND, INITIATIVE_OUTBOUND)
        ):
            excluded["other_values"] += 1
            continue
        msgs = by_lead.get(lead.id, [])
        n_in = sum(1 for m in msgs if m.direction == DIRECTION_INBOUND)
        n_out = sum(1 for m in msgs if m.direction == DIRECTION_OUTBOUND)
        # 3. no_inbound / 4. no_outbound
        if n_in == 0:
            excluded["no_inbound"] += 1
            continue
        if n_out == 0:
            excluded["no_outbound"] += 1
            continue
        # 5. no_reply_pair
        first_reply = first_reply_seconds(msgs)
        partner_mean = partner_reply_mean_seconds(msgs)
        if first_reply is None or partner_mean is None:
            excluded["no_reply_pair"] += 1
            continue
        # 6. no_sales_form
        if not lead.sales_form_values:
            excluded["no_sales_form"] += 1
            continue
        # 7. missing_scale_or_type（空、または列挙に無い値）
        if lead.estimated_scale not in (SCALE_SMALL, SCALE_MEDIUM, SCALE_LARGE) or lead.customer_type not in (
            CUSTOMER_TYPE_TRUST,
            CUSTOMER_TYPE_PRICE,
        ):
            excluded["missing_scale_or_type"] += 1
            continue

        row = [
            1.0,
            1.0 if lead.initiative == INITIATIVE_INBOUND else 0.0,
            1.0 if SALES_FORM_WHOLESALE in lead.sales_form_values else 0.0,
            1.0 if first_reply <= FIRST_REPLY_LIMIT_SECONDS else 0.0,
            1.0 if partner_mean <= PARTNER_REPLY_LIMIT_SECONDS else 0.0,
            1.0 if lead.channel_type == CHANNEL_WHATSAPP else 0.0,
            1.0 if lead.channel_type == CHANNEL_INSTAGRAM else 0.0,
            1.0 if lead.country == COUNTRY_GB else 0.0,
            1.0 if lead.country == COUNTRY_AU else 0.0,
            1.0 if lead.temperature == TEMPERATURE_HOT else 0.0,
            1.0 if lead.temperature == TEMPERATURE_WARM else 0.0,
            float(n_in + n_out),
            1.0 if lead.estimated_scale == SCALE_LARGE else 0.0,
            1.0 if lead.estimated_scale == SCALE_MEDIUM else 0.0,
            1.0 if lead.customer_type == CUSTOMER_TYPE_TRUST else 0.0,
            1.0 if lead.competitor_check else 0.0,
        ]
        ids.append(lead.id)
        x_rows.append(row)
        y.append(1 if lead.status == STATUS_WON else 0)

    return Prepared(lead_ids=ids, x=x_rows, y=y, excluded=excluded)


# ── ロジスティック回帰（ニュートン法・標準ライブラリだけ） ─────────
def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _invert(matrix: list[list[float]]) -> list[list[float]] | None:
    """部分ピボット付きガウス・ジョルダン法。ピボットの絶対値が 1e-12 以下なら None。"""
    n = len(matrix)
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot_row][col]) <= PIVOT_MIN:
            return None
        if pivot_row != col:
            a[col], a[pivot_row] = a[pivot_row], a[col]
        piv = a[col][col]
        a[col] = [v / piv for v in a[col]]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            if factor != 0.0:
                src = a[col]
                a[r] = [v - factor * s for v, s in zip(a[r], src)]
    return [row[n:] for row in a]


def _hessian_and_gradient(
    x: list[list[float]], y: list[int], beta: list[float]
) -> tuple[list[list[float]], list[float]]:
    k = len(beta)
    h = [[0.0] * k for _ in range(k)]
    g = [0.0] * k
    for xi, yi in zip(x, y):
        z = sum(b * v for b, v in zip(beta, xi))
        p = _sigmoid(z)
        w = p * (1.0 - p)
        r = yi - p
        for a in range(k):
            xa = xi[a]
            if xa == 0.0:
                continue
            g[a] += xa * r
            wxa = w * xa
            row = h[a]
            for b in range(a, k):
                row[b] += wxa * xi[b]
    for a in range(k):
        for b in range(a):
            h[a][b] = h[b][a]
    return h, g


@dataclass
class FitResult:
    computable: bool
    beta: list[float] = field(default_factory=list)
    se: list[float] = field(default_factory=list)
    iterations: int = 0


def fit_logistic(x: list[list[float]], y: list[int]) -> FitResult:
    """初期値は全係数 0。更新の最大の絶対値が 1e-10 以下で収束（上限 100 回）。

    上限まで収束しない・逆行列が作れない・|β| が 20 を超える、のどれかで computable=False。
    """
    k = len(x[0]) if x else 0
    if k == 0:
        return FitResult(computable=False)
    beta = [0.0] * k
    for it in range(1, NEWTON_MAX_ITER + 1):
        h, g = _hessian_and_gradient(x, y, beta)
        inv = _invert(h)
        if inv is None:
            return FitResult(computable=False, iterations=it)
        step = [sum(inv[a][b] * g[b] for b in range(k)) for a in range(k)]
        beta = [b + s for b, s in zip(beta, step)]
        if any(not math.isfinite(b) or abs(b) > BETA_ABS_MAX for b in beta):
            return FitResult(computable=False, iterations=it)
        if max(abs(s) for s in step) <= NEWTON_TOL:
            # 標準誤差は収束した β で作った H⁻¹ の対角の平方根
            h, _ = _hessian_and_gradient(x, y, beta)
            inv = _invert(h)
            if inv is None or any(inv[a][a] < 0 for a in range(k)):
                return FitResult(computable=False, iterations=it)
            se = [math.sqrt(inv[a][a]) for a in range(k)]
            return FitResult(computable=True, beta=beta, se=se, iterations=it)
    return FitResult(computable=False, iterations=NEWTON_MAX_ITER)


# ── 1 回の分析 ─────────────────────────────────────────────
def item_results(fit: FitResult) -> list[dict]:
    """§2-5 の 15 項目の強さ・幅。計算できないときは全項目 computable=False・値 None。"""
    items: list[dict] = []
    for idx, key in enumerate(ITEM_KEYS, start=1):
        if not fit.computable:
            items.append(
                {
                    "key": key,
                    "odds_ratio": None,
                    "ci_low": None,
                    "ci_high": None,
                    "significant": False,
                    "computable": False,
                }
            )
            continue
        b = fit.beta[idx]
        s = fit.se[idx]
        lo = math.exp(b - Z_975 * s)
        hi = math.exp(b + Z_975 * s)
        items.append(
            {
                "key": key,
                "odds_ratio": math.exp(b),
                "ci_low": lo,
                "ci_high": hi,
                "significant": bool(lo > 1.0 or hi < 1.0),
                "computable": True,
            }
        )
    return items


@dataclass
class Analysis:
    status: str  # "ok" / "insufficient" / "not_computable"
    included_count: int
    won_count: int
    lost_count: int
    excluded: dict[str, int]
    items: list[dict]  # status が ok のときだけ 15 個
    fit: FitResult | None
    prepared: Prepared


def analyze(leads: list[LeadRow], messages: list[MessageRow]) -> Analysis:
    prep = prepare(leads, messages)
    won, lost = prep.won_count, prep.lost_count
    if min(won, lost) / ITEM_COUNT < REQUIRED_PER_ITEM:
        return Analysis("insufficient", len(prep.y), won, lost, prep.excluded, [], None, prep)
    fit = fit_logistic(prep.x, prep.y)
    if not fit.computable:
        return Analysis("not_computable", len(prep.y), won, lost, prep.excluded, [], fit, prep)
    return Analysis("ok", len(prep.y), won, lost, prep.excluded, item_results(fit), fit, prep)
