"""請求書の額の計算（invoice-create-portfolio 便C・design.md §3-3・§3-4）。

ここが唯一の計算の場所。試算・作る・見積から作る・発行の道がこれを呼ぶ。
- compute_totals: 純粋な関数（DB を読まない）。
- load_totals_inputs: 計算に要る行を DB から読む（税率・関税の条件・関税の行・為替）。
端数は請求書の通貨の最小単位へ切り捨て（design.md §7 の1）。為替の列は今と同じ round(x, 2)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import ROUND_FLOOR, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import tenant_table_ref

JST = ZoneInfo("Asia/Tokyo")

# 「未計算」の理由（この順に並べる。作る道は先頭で止める。design.md §3-4）
REASON_SHIPPING = "shipping_required"
REASON_FX = "fx_rate"
REASON_TAX = "tax_rate"
REASON_DUTY_CARRIER = "duty_needs_carrier"
REASON_ORDER = (REASON_SHIPPING, REASON_FX, REASON_TAX, REASON_DUTY_CARRIER)

SHIPPING_MODES = ("calculate", "quote", "none")
DUTY_BASES = ("subtotal", "subtotal_shipping", "subtotal_shipping_prior")


def today_jst() -> date:
    return datetime.now(JST).date()


def normalize_carrier(value: str | None) -> str | None:
    """送料の会社の比べ方: 前後の空白を除き小文字。空は None（design.md §3-3 の3）。"""
    if value is None:
        return None
    s = value.strip().lower()
    return s or None


def minor_unit(currency: str) -> Decimal:
    return Decimal("1") if currency == "JPY" else Decimal("0.01")


def floor_minor(value: Decimal, currency: str) -> Decimal:
    return value.quantize(minor_unit(currency), rounding=ROUND_FLOOR)


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class TotalsItem:
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class ShippingChoice:
    mode: str  # calculate / quote / none
    carrier: str | None = None
    service_type: str | None = None
    fee: Decimal | None = None
    currency: str | None = None


@dataclass(frozen=True)
class FxRow:
    currency: str
    rate_jpy: Decimal
    fetched_at: datetime


@dataclass(frozen=True)
class TaxRow:
    rate_percent: Decimal
    effective_from: date


@dataclass(frozen=True)
class DutyComponent:
    sort_order: int
    label: str
    base: str
    rate_pct: Decimal
    min_amount: Decimal | None
    max_amount: Decimal | None
    amount_currency: str | None


@dataclass(frozen=True)
class DutyRule:
    id: int
    carrier: str | None
    label: str
    source_url: str
    effective_from: date
    effective_to: date | None
    components: tuple[DutyComponent, ...]


@dataclass(frozen=True)
class TotalsInputs:
    base_date: date
    incoterms: str
    tax: TaxRow | None
    duty_rules: tuple[DutyRule, ...]
    fx: dict[str, FxRow]


@dataclass
class TotalsResult:
    currency: str
    subtotal: Decimal
    shipping_fee: Decimal | None
    tax_amount: Decimal | None
    tax_rate_percent: Decimal | None
    duty_amount: Decimal | None
    duty_label: str | None
    duty_components: list[dict]
    total_amount: Decimal | None
    uncomputed: list[str]
    shipping_carrier: str | None
    shipping_service: str | None
    shipping_snapshot: dict | None
    duty_policy_snapshot: dict
    fx_rate_snapshot: dict | None
    exchange_rate_jpy: Decimal | None
    exchange_rate_usd: Decimal | None
    amount_jpy: Decimal | None
    amount_usd: Decimal | None
    _reasons: set[str] = field(default_factory=set, repr=False)


class _FxMissing(Exception):
    pass


def _fx_record(row: FxRow) -> dict:
    return {"currency": row.currency, "rate_jpy": str(row.rate_jpy), "fetched_at": _iso_utc(row.fetched_at)}


def _rate(fx: dict[str, FxRow], currency: str) -> Decimal:
    if currency == "JPY":
        return Decimal("1")
    row = fx.get(currency)
    if row is None:
        raise _FxMissing(currency)
    return row.rate_jpy


def _convert(amount: Decimal, src: str, dst: str, fx: dict[str, FxRow], used: list[dict]) -> Decimal:
    """src の額を dst の通貨へ（円を通す）。dst の最小単位へ切り捨て。使った為替の行を used に足す。"""
    if src == dst:
        return floor_minor(amount, dst)
    jpy = amount * _rate(fx, src)
    out = jpy / _rate(fx, dst)
    for cur in (src, dst):
        if cur != "JPY":
            rec = _fx_record(fx[cur])
            if rec not in used:
                used.append(rec)
    return floor_minor(out, dst)


def destination_country(ship_to: dict | None, bill_to: dict | None) -> str | None:
    """届け先の国＝発送先の写しの国、無ければ請求先の写しの国（design.md §3-3 の1）。"""
    for snap in (ship_to, bill_to):
        if snap and snap.get("country"):
            return str(snap["country"]).upper()
    return None


def destination_postal_code(ship_to: dict | None, bill_to: dict | None) -> str | None:
    """届け先の郵便番号（国と同じ写しから取る。design.md §3-4 の FedEx の項）。"""
    for snap in (ship_to, bill_to):
        if snap and snap.get("country"):
            return snap.get("postal_code") or None
    return None


def compute_totals(
    *,
    currency: str,
    items: list[TotalsItem],
    shipping: ShippingChoice | None,
    destination: str | None,
    inputs: TotalsInputs,
) -> TotalsResult:
    currency = currency.upper()
    reasons: set[str] = set()
    subtotal = sum((Decimal(it.quantity) * it.unit_price for it in items), Decimal("0"))

    # ── 送料 ────────────────────────────────────────────────
    shipping_fee: Decimal | None
    shipping_snapshot: dict | None
    ship_fx: list[dict] = []
    if shipping is None:
        reasons.add(REASON_SHIPPING)
        shipping_fee = None
        shipping_snapshot = None
        carrier_raw = None
        service = None
    elif shipping.mode == "none":
        shipping_fee = Decimal("0")
        carrier_raw = None
        service = None
        shipping_snapshot = {
            "source": "none", "original_fee": None, "original_currency": None,
            "carrier": None, "service_type": None, "fx": [], "no_charge": True,
        }
    else:
        carrier_raw = shipping.carrier
        service = shipping.service_type
        src_cur = (shipping.currency or currency).upper()
        fee = shipping.fee if shipping.fee is not None else Decimal("0")
        try:
            shipping_fee = _convert(fee, src_cur, currency, inputs.fx, ship_fx)
        except _FxMissing:
            reasons.add(REASON_FX)
            shipping_fee = None
        shipping_snapshot = {
            "source": shipping.mode, "original_fee": str(fee), "original_currency": src_cur,
            "carrier": carrier_raw, "service_type": service, "fx": ship_fx, "no_charge": False,
        }

    # ── 消費税（JP 宛だけ）──────────────────────────────────
    tax_amount: Decimal | None
    tax_rate_percent: Decimal | None
    if destination == "JP":
        if inputs.tax is None:
            reasons.add(REASON_TAX)
            tax_amount = None
            tax_rate_percent = None
        else:
            tax_rate_percent = inputs.tax.rate_percent
            if shipping_fee is None:
                tax_amount = None
            else:
                tax_amount = floor_minor((subtotal + shipping_fee) * tax_rate_percent / Decimal("100"), currency)
    else:
        tax_amount = Decimal("0")
        tax_rate_percent = None

    # ── 関税（DDP だけ）────────────────────────────────────
    duty_amount: Decimal | None = None
    duty_label: str | None = None
    duty_components: list[dict] = []
    duty_fx: list[dict] = []
    rule_snap: dict | None = None
    if inputs.incoterms == "DDP" and inputs.duty_rules:
        carrier = normalize_carrier(carrier_raw)
        matched = [r for r in inputs.duty_rules if carrier is not None and r.carrier == carrier]
        generic = [r for r in inputs.duty_rules if r.carrier is None]
        rule = matched[0] if matched else (generic[0] if generic else None)
        if rule is None:
            reasons.add(REASON_DUTY_CARRIER)
        else:
            duty_label = rule.label
            rule_snap = {
                "id": rule.id, "carrier": rule.carrier, "label": rule.label, "source_url": rule.source_url,
                "effective_from": rule.effective_from.isoformat(),
                "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
            }
            if shipping_fee is not None:
                prior = Decimal("0")
                total_duty = Decimal("0")
                try:
                    for comp in sorted(rule.components, key=lambda c: c.sort_order):
                        if comp.base == "subtotal":
                            base = subtotal
                        elif comp.base == "subtotal_shipping":
                            base = subtotal + shipping_fee
                        else:
                            base = subtotal + shipping_fee + prior
                        raw = base * comp.rate_pct / Decimal("100")
                        comp_cur = (comp.amount_currency or currency).upper()
                        lo = _convert(comp.min_amount, comp_cur, currency, inputs.fx, duty_fx) if comp.min_amount is not None else None
                        hi = _convert(comp.max_amount, comp_cur, currency, inputs.fx, duty_fx) if comp.max_amount is not None else None
                        if lo is not None and raw < lo:
                            raw = lo
                        if hi is not None and raw > hi:
                            raw = hi
                        amount = floor_minor(raw, currency)
                        prior += amount
                        total_duty += amount
                        duty_components.append({
                            "label": comp.label, "base": comp.base, "rate_pct": str(comp.rate_pct),
                            "min_amount": str(comp.min_amount) if comp.min_amount is not None else None,
                            "max_amount": str(comp.max_amount) if comp.max_amount is not None else None,
                            "amount_currency": comp.amount_currency, "amount": str(amount),
                        })
                    duty_amount = total_duty
                except _FxMissing:
                    reasons.add(REASON_FX)
                    duty_components = []
                    duty_amount = None

    duty_policy_snapshot = {
        "incoterms": inputs.incoterms, "base_date": inputs.base_date.isoformat(),
        "rule": rule_snap, "components": duty_components, "fx": duty_fx,
    }

    # ── 合計 ─────────────────────────────────────────────
    total_amount: Decimal | None = None
    blocked = bool(reasons) or shipping_fee is None or tax_amount is None
    if inputs.incoterms == "DDP" and rule_snap is not None and duty_amount is None:
        blocked = True
    if not blocked:
        total_amount = subtotal + shipping_fee + tax_amount + (duty_amount or Decimal("0"))

    # ── 請求書の通貨の為替（fx_rate_snapshot・exchange_rate_jpy）──────
    fx_rate_snapshot: dict | None = None
    exchange_rate_jpy: Decimal | None = None
    if currency != "JPY":
        row = inputs.fx.get(currency)
        if row is None:
            reasons.add(REASON_FX)
            total_amount = None
        else:
            exchange_rate_jpy = row.rate_jpy
            fx_rate_snapshot = {"currency": currency, "rate": float(row.rate_jpy), "fetched_at": _iso_utc(row.fetched_at)}

    usd_row = inputs.fx.get("USD")
    exchange_rate_usd = usd_row.rate_jpy if (currency != "USD" and usd_row is not None) else None
    amount_jpy: Decimal | None = None
    amount_usd: Decimal | None = None
    if total_amount is not None:
        amount_jpy = total_amount if currency == "JPY" else round(total_amount * exchange_rate_jpy, 2)
        if currency == "USD":
            amount_usd = total_amount
        elif usd_row is not None and usd_row.rate_jpy > 0:
            amount_usd = round(amount_jpy / usd_row.rate_jpy, 2)

    return TotalsResult(
        currency=currency,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        tax_amount=tax_amount,
        tax_rate_percent=tax_rate_percent,
        duty_amount=duty_amount,
        duty_label=duty_label,
        duty_components=duty_components,
        total_amount=total_amount,
        uncomputed=[r for r in REASON_ORDER if r in reasons],
        shipping_carrier=carrier_raw.strip() if carrier_raw and carrier_raw.strip() else None,
        shipping_service=service,
        shipping_snapshot=shipping_snapshot,
        duty_policy_snapshot=duty_policy_snapshot,
        fx_rate_snapshot=fx_rate_snapshot,
        exchange_rate_jpy=exchange_rate_jpy,
        exchange_rate_usd=exchange_rate_usd,
        amount_jpy=amount_jpy,
        amount_usd=amount_usd,
    )


# ── DB を読む ─────────────────────────────────────────────────


async def load_latest_fx(db: AsyncSession) -> dict[str, FxRow]:
    result = await db.execute(text("""
        SELECT DISTINCT ON (currency) currency, rate_jpy, fetched_at
        FROM public.app_fx_rate_history
        ORDER BY currency, fetched_at DESC
    """))
    return {
        r["currency"]: FxRow(currency=r["currency"], rate_jpy=Decimal(r["rate_jpy"]), fetched_at=r["fetched_at"])
        for r in result.mappings().all()
    }


async def load_tax_row(db: AsyncSession, base_date: date) -> TaxRow | None:
    result = await db.execute(
        text("""
            SELECT rate_percent, effective_from FROM public.tax_rates
            WHERE effective_from <= :d ORDER BY effective_from DESC LIMIT 1
        """),
        {"d": base_date},
    )
    row = result.mappings().first()
    return None if row is None else TaxRow(rate_percent=Decimal(row["rate_percent"]), effective_from=row["effective_from"])


async def load_incoterms(db: AsyncSession, tenant_id: int) -> str:
    result = await db.execute(
        text("SELECT duty_incoterms FROM public.tenant_settings WHERE tenant_id = :tid"),
        {"tid": int(tenant_id)},
    )
    row = result.first()
    return (row[0] if row and row[0] else "DAP").upper()


async def load_duty_rules(db: AsyncSession, tenant_id: int, country: str, base_date: date) -> tuple[DutyRule, ...]:
    rules_t = tenant_table_ref(db, tenant_id, "tenant_duty_rules")
    comps_t = tenant_table_ref(db, tenant_id, "tenant_duty_rule_components")
    result = await db.execute(
        text(f"""
            SELECT id, carrier, label, source_url, effective_from, effective_to
            FROM {rules_t}
            WHERE destination_country_code = :country
              AND is_active = TRUE
              AND effective_from <= :d
              AND COALESCE(effective_to, DATE '9999-12-31') >= :d
            ORDER BY id
        """),
        {"country": country, "d": base_date},
    )
    rules: list[DutyRule] = []
    for r in result.mappings().all():
        comp_rows = await db.execute(
            text(f"""
                SELECT sort_order, label, base, rate_pct, min_amount, max_amount, amount_currency
                FROM {comps_t} WHERE rule_id = :rid ORDER BY sort_order, id
            """),
            {"rid": r["id"]},
        )
        comps = tuple(
            DutyComponent(
                sort_order=c["sort_order"], label=c["label"], base=c["base"],
                rate_pct=Decimal(c["rate_pct"]),
                min_amount=Decimal(c["min_amount"]) if c["min_amount"] is not None else None,
                max_amount=Decimal(c["max_amount"]) if c["max_amount"] is not None else None,
                amount_currency=(c["amount_currency"].strip() if c["amount_currency"] else None),
            )
            for c in comp_rows.mappings().all()
        )
        rules.append(DutyRule(
            id=r["id"], carrier=r["carrier"], label=r["label"], source_url=r["source_url"],
            effective_from=r["effective_from"], effective_to=r["effective_to"], components=comps,
        ))
    return tuple(rules)


async def load_totals_inputs(
    db: AsyncSession, tenant_id: int, *, destination: str | None, base_date: date,
) -> TotalsInputs:
    incoterms = await load_incoterms(db, tenant_id)
    duty_rules: tuple[DutyRule, ...] = ()
    if incoterms == "DDP" and destination:
        duty_rules = await load_duty_rules(db, tenant_id, destination, base_date)
    return TotalsInputs(
        base_date=base_date,
        incoterms=incoterms,
        tax=await load_tax_row(db, base_date),
        duty_rules=duty_rules,
        fx=await load_latest_fx(db),
    )


def first_block(result: TotalsResult) -> tuple[int, str] | None:
    """作る道の止め方（D5）。止めないときは None。"""
    if not result.uncomputed:
        return None
    reason = result.uncomputed[0]
    return (422 if reason == REASON_SHIPPING else 409), reason


def to_db_params(result: TotalsResult) -> dict[str, Any]:
    """INSERT・UPDATE に渡す値（写しは JSON の文字）。"""
    import json

    return {
        "subtotal": result.subtotal,
        "shipping": result.shipping_fee,
        "tax": result.tax_amount,
        "tax_rate_percent": result.tax_rate_percent,
        "duty_amount": result.duty_amount,
        "total": result.total_amount,
        "rate_jpy": result.exchange_rate_jpy,
        "rate_usd": result.exchange_rate_usd,
        "amt_jpy": result.amount_jpy,
        "amt_usd": result.amount_usd,
        "shipping_carrier": result.shipping_carrier,
        "shipping_service": result.shipping_service,
        "shipping_snapshot": json.dumps(result.shipping_snapshot) if result.shipping_snapshot is not None else None,
        "duty_policy_snapshot": json.dumps(result.duty_policy_snapshot),
        "fx_rate": json.dumps(result.fx_rate_snapshot) if result.fx_rate_snapshot is not None else None,
    }
