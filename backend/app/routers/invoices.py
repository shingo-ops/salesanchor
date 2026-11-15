from __future__ import annotations

"""
請求書管理API。

見積もりからの変換 or 直接作成。多通貨対応（為替レート記録）。
枝番（branch_number）で修正版を追跡。void/revision フロー。

変更履歴:
  2026-04-17: 初版作成（Phase 2）
  2026-04-27: Phase 1-B-2 Step 5d — 旧 customer_id 系統撤去
    （customer 経路廃止、company_id + contact_id を唯一の正に）
"""

import json
import logging
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.cache import invalidate_dashboard_cache
from app.database import get_db
from app.models import User
from app.schemas.invoice import (
    DraftContextResponse,
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceItemResponse,
    InvoicePreviewRequest,
    InvoicePreviewResponse,
    InvoiceResponse,
    InvoiceUpdate,
    VoidRequest,
)
from app.services import invoice_payment_methods, invoice_totals, paypal_payments
from app.services.audit import record_audit_log
from app.services.fx_currencies import list_invoice_currencies
from app.services.invoice_payment_methods import PaymentMethodInvalid
from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf
from app.services.issuer import decide_issuer_region, get_issuer, get_issuer_country_code
from app.services.payment_dates import PAID_AT_SQL, paid_at_from_date, paypal_paid_at

router = APIRouter()
logger = logging.getLogger(__name__)


class PayInvoiceRequest(BaseModel):
    """入金登録 POST ボディ（paid_date は省略可・日付のみ）。"""
    paid_date: date | None = None


async def _fetch_address_snapshot(
    db: AsyncSession,
    company_id: int | None,
    address_type: str,
) -> dict | None:
    """
    company_addresses から指定タイプ (delivery / billing) のデフォルト住所を取得し
    JSONB スナップショット形式で返す。company_id が None の場合は None を返す。
    """
    if company_id is None:
        return None
    result = await db.execute(
        text("""
            SELECT a.branch_name, a.zip, a.address_line_1, a.address_line_2,
                   a.city, a.state, a.country_code, a.telephone,
                   c.name AS company_name, c.billing_display_name
            FROM company_addresses a
            JOIN companies c ON c.id = a.company_id
            WHERE a.company_id = :cid
              AND a.address_type = :atype
              AND a.is_default = TRUE
            LIMIT 1
        """),
        {"cid": company_id, "atype": address_type},
    )
    row = result.mappings().first()
    if not row:
        return None
    return {
        "company_name": row["company_name"],
        "billing_display_name": row["billing_display_name"],
        "label": row["branch_name"],
        "postal_code": row["zip"],
        "address": " ".join(
            filter(None, [row["address_line_1"], row["address_line_2"]])
        ),
        "city": row["city"],
        "state": row["state"],
        "country": row["country_code"],
        "phone": row["telephone"],
    }


_INVOICE_COLUMNS = """
    id, invoice_number, quote_id, company_id, contact_id, currency,
    subtotal, shipping_fee, tax_amount, total_amount,
    exchange_rate_jpy, exchange_rate_usd, amount_jpy, amount_usd,
    payment_method, status, branch_number,
    pdf_url, erp_key,
    issued_at, due_date, paid_at, voided_at, void_reason,
    notes, created_by, created_at, updated_at,
    ship_to_snapshot, bill_to_snapshot, issue_mode,
    duty_amount, duty_policy_snapshot, fx_rate_snapshot,
    paypal_order_id, paypal_approval_url, payment_fee,
    paypal_invoicer_view_url, paypal_copy_pdf_at,
    issuer_region,
    payment_method_id, tax_rate_percent, shipping_carrier, shipping_service, shipping_snapshot
"""

_UPDATABLE_COLUMNS = {"due_date", "notes"}


async def _get_invoice_items(db: AsyncSession, invoice_id: int) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT id, product_id, product_name, name_en, condition, unit,
                   quantity, unit_price, weight, subtotal, sort_order, hs_code
            FROM invoice_items WHERE invoice_id = :iid ORDER BY sort_order, id
        """),
        {"iid": invoice_id},
    )
    return [dict(row) for row in result.mappings().all()]


_INSERT_INVOICE_SQL = """
    INSERT INTO invoices (
        tenant_id, invoice_number, quote_id, company_id, contact_id, currency,
        subtotal, shipping_fee, tax_amount, total_amount,
        exchange_rate_jpy, exchange_rate_usd, amount_jpy, amount_usd,
        payment_method, payment_method_id, status, branch_number, erp_key,
        due_date, notes, created_by,
        ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot, issuer_region,
        duty_amount, duty_policy_snapshot, tax_rate_percent,
        shipping_carrier, shipping_service, shipping_snapshot
    ) VALUES (
        :tid, :inv_num, :qid, :company_id, :contact_id, :currency,
        :subtotal, :shipping, :tax, :total,
        :rate_jpy, :rate_usd, :amt_jpy, :amt_usd,
        :payment, :payment_method_id, 'draft', 1, :erp_key,
        :due_date, :notes, :created_by,
        :ship_to, :bill_to, :fx_rate, :issuer_region,
        :duty_amount, :duty_policy_snapshot, :tax_rate_percent,
        :shipping_carrier, :shipping_service, :shipping_snapshot
    ) RETURNING id
"""

_RECOMPUTE_SET_SQL = """
    subtotal = :subtotal, shipping_fee = :shipping, tax_amount = :tax, total_amount = :total,
    exchange_rate_jpy = :rate_jpy, exchange_rate_usd = :rate_usd, amount_jpy = :amt_jpy, amount_usd = :amt_usd,
    fx_rate_snapshot = :fx_rate, duty_amount = :duty_amount, duty_policy_snapshot = :duty_policy_snapshot,
    tax_rate_percent = :tax_rate_percent, shipping_snapshot = :shipping_snapshot
"""


def _load_snapshot(value):
    """写しの列は PG では dict、SQLite の試験では JSON の文字。"""
    if isinstance(value, str):
        return json.loads(value)
    return value


def _raise_if_blocked(result: invoice_totals.TotalsResult) -> None:
    blocked = invoice_totals.first_block(result)
    if blocked is not None:
        raise HTTPException(status_code=blocked[0], detail=blocked[1])


def _shipping_choice(body) -> invoice_totals.ShippingChoice | None:
    if body is None:
        return None
    if body.mode == "none":
        return invoice_totals.ShippingChoice(mode="none")
    return invoice_totals.ShippingChoice(
        mode="calculate", carrier=body.carrier, service_type=body.service_type,
        fee=body.fee, currency=body.currency.upper(),
    )


def _shipping_from_stored(row) -> invoice_totals.ShippingChoice:
    """発行の時に保存した送料の写しから選び方を戻す（D10）。"""
    snap = _load_snapshot(row["shipping_snapshot"])
    if snap and snap.get("source") in ("calculate", "quote"):
        return invoice_totals.ShippingChoice(
            mode=snap["source"], carrier=snap.get("carrier"), service_type=snap.get("service_type"),
            fee=Decimal(snap["original_fee"]), currency=snap.get("original_currency") or row["currency"],
        )
    if snap and snap.get("source") == "none":
        return invoice_totals.ShippingChoice(mode="none")
    fee = Decimal(row["shipping_fee"] or 0)
    if fee > 0:
        return invoice_totals.ShippingChoice(
            mode="quote", carrier=row["shipping_carrier"], fee=fee, currency=row["currency"],
        )
    return invoice_totals.ShippingChoice(mode="none")


async def _compute(db, tenant_id, *, currency, items, shipping, ship_to, bill_to, base_date=None):
    destination = invoice_totals.destination_country(ship_to, bill_to)
    inputs = await invoice_totals.load_totals_inputs(
        db, tenant_id, destination=destination, base_date=base_date or invoice_totals.today_jst(),
    )
    return invoice_totals.compute_totals(
        currency=currency, items=items, shipping=shipping, destination=destination, inputs=inputs,
    )


@router.get(
    "/invoices",
    response_model=list[InvoiceResponse],
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def list_invoices(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    company_id: int | None = Query(default=None),
    contact_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * per_page
    conditions = []
    params: dict = {"limit": per_page, "offset": offset}
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter
    if company_id:
        conditions.append("company_id = :company_id")
        params["company_id"] = company_id
    if contact_id:
        conditions.append("contact_id = :contact_id")
        params["contact_id"] = contact_id
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = await db.execute(
        text(f"SELECT {_INVOICE_COLUMNS} FROM invoices {where} ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"),
        params,
    )
    return [InvoiceResponse(**row) for row in result.mappings().all()]


@router.get(
    "/invoices/draft-context",
    response_model=DraftContextResponse,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def get_invoice_draft_context(
    company_id: int | None = Query(default=None, ge=1),
    contact_id: int | None = Query(default=None, ge=1),
    invoice_id: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """作成画面と下書きの詳細画面の材料（書かない。design.md §3-4 の表の1行目）。"""
    stored = None
    if invoice_id is not None:
        res = await db.execute(
            text("SELECT company_id, contact_id, currency, issuer_region FROM invoices WHERE id = :id"),
            {"id": invoice_id},
        )
        stored = res.mappings().first()
        if stored is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
        if company_id is not None and company_id != stored["company_id"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invoice_company_mismatch")
        company_id = stored["company_id"]
        if contact_id is None:
            contact_id = stored["contact_id"]
    if company_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="draft_context_target")

    co = await db.execute(text("SELECT id FROM companies WHERE id = :id"), {"id": company_id})
    if co.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:company")

    contact_name = None
    contact_email = None
    if contact_id is not None:
        ct = await db.execute(
            text("SELECT company_id, display_name, surname, given_name, primary_email FROM contacts WHERE id = :id"),
            {"id": contact_id},
        )
        ct_row = ct.mappings().first()
        if ct_row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:contact")
        if ct_row["company_id"] != company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指定された担当者は指定会社に所属していません")
        contact_name = ct_row["display_name"] or " ".join(
            p for p in (ct_row["surname"], ct_row["given_name"]) if p
        ) or None
        contact_email = ct_row["primary_email"]

    ship_to = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, company_id, "billing")
    if stored is not None:
        region = stored["issuer_region"] or "overseas"
    else:
        region = decide_issuer_region(bill_to)

    fx = await invoice_totals.load_latest_fx(db)
    currencies = await list_invoice_currencies(db)
    tax_row = await invoice_totals.load_tax_row(db, invoice_totals.today_jst())
    policy = await db.execute(
        text("SELECT default_currency FROM public.tenant_settings WHERE tenant_id = :tid"),
        {"tid": int(tenant_id)},
    )
    policy_row = policy.first()
    return DraftContextResponse(
        company_id=company_id,
        ship_to=ship_to,
        bill_to=bill_to,
        contact_name=contact_name,
        contact_email=contact_email,
        issuer_region=region,
        origin_country_code=await get_issuer_country_code(db, tenant_id, region),
        destination_country_code=invoice_totals.destination_country(ship_to, bill_to),
        destination_postal_code=invoice_totals.destination_postal_code(ship_to, bill_to),
        currencies=currencies,
        fx_rates=[
            {"currency": cur, "rate": float(row.rate_jpy), "fetched_at": invoice_totals._iso_utc(row.fetched_at)}
            for cur, row in sorted(fx.items())
        ],
        default_currency=(policy_row[0] if policy_row else None),
        currency=(stored["currency"] if stored is not None else None),
        payment_methods=await invoice_payment_methods.list_payment_choices(db, tenant_id, region),
        tax_rate_percent=(tax_row.rate_percent if tax_row else None),
        incoterms=await invoice_totals.load_incoterms(db, tenant_id),
    )


@router.post(
    "/invoices/preview",
    response_model=InvoicePreviewResponse,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def preview_invoice(
    data: InvoicePreviewRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """試算（書かない）。未計算でも 200 で理由を返す（D5）。"""
    co = await db.execute(text("SELECT id FROM companies WHERE id = :id"), {"id": data.company_id})
    if co.first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:company")
    ship_to = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to = await _fetch_address_snapshot(db, data.company_id, "billing")
    destination = invoice_totals.destination_country(ship_to, bill_to)
    inputs = await invoice_totals.load_totals_inputs(
        db, tenant_id, destination=destination, base_date=invoice_totals.today_jst(),
    )
    result = invoice_totals.compute_totals(
        currency=data.currency,
        items=[invoice_totals.TotalsItem(quantity=i.quantity, unit_price=i.unit_price) for i in data.items],
        shipping=_shipping_choice(data.shipping),
        destination=destination,
        inputs=inputs,
    )
    return InvoicePreviewResponse(
        currency=result.currency, subtotal=result.subtotal, shipping_fee=result.shipping_fee,
        tax_amount=result.tax_amount, tax_rate_percent=result.tax_rate_percent,
        duty_amount=result.duty_amount, duty_label=result.duty_label, duty_components=result.duty_components,
        total_amount=result.total_amount, uncomputed=result.uncomputed, incoterms=inputs.incoterms,
    )


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceDetailResponse,
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"), {"id": invoice_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
    items = await _get_invoice_items(db, invoice_id)
    label = await invoice_payment_methods.load_payment_label(db, tenant_id, row["payment_method_id"])
    return InvoiceDetailResponse(
        **dict(row), items=[InvoiceItemResponse(**i) for i in items],
        payment_method_display_name=(label or {}).get("display_name"),
        payment_method_type=(label or {}).get("method_type"),
    )


@router.post(
    "/invoices/from-quote/{quote_id}",
    response_model=InvoiceDetailResponse,
    status_code=201,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def create_invoice_from_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """承認済み見積もりから請求書を作成する（atomic変換）"""
    # アトミック性: 見積もりステータスをSELECT FOR UPDATEで排他ロックし、
    # 並行変換を防止。全操作が同一トランザクション内で完結する。
    quote = await db.execute(
        text("SELECT * FROM quotes WHERE id = :id FOR UPDATE"),
        {"id": quote_id},
    )
    q = quote.mappings().first()
    if not q:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:quote")
    if q["status"] != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="承認済みの見積もりのみ請求書に変換できます")

    # 請求番号生成
    max_result = await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM invoices"))
    next_id = max_result.scalar()
    invoice_number = f"IN-{next_id:04d}-01"
    erp_key = str(uuid.uuid4())[:8].upper()

    # スナップショット取得
    company_id = q.get("company_id")
    ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")
    # ADR-1061 便2-2c2a: 発行元の地域は請求先の国で決めて保存する（国が無いと作らない）
    issuer_region = decide_issuer_region(bill_to_snap)
    if issuer_region is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bill_to_country")

    currency = (q["currency"] or "JPY").upper()
    quote_items_rows = (await db.execute(
        text("SELECT quantity, unit_price FROM quote_items WHERE quote_id = :qid ORDER BY sort_order"),
        {"qid": quote_id},
    )).mappings().all()
    q_fee = Decimal(q["shipping_fee"] or 0)
    shipping = (
        invoice_totals.ShippingChoice(mode="quote", carrier=q.get("shipping_carrier"), fee=q_fee, currency=currency)
        if q_fee > 0 else invoice_totals.ShippingChoice(mode="none")
    )
    totals = await _compute(
        db, tenant_id, currency=currency,
        items=[invoice_totals.TotalsItem(quantity=r["quantity"], unit_price=Decimal(r["unit_price"])) for r in quote_items_rows],
        shipping=shipping, ship_to=ship_to_snap, bill_to=bill_to_snap,
    )
    _raise_if_blocked(totals)

    inv_result = await db.execute(
        text(_INSERT_INVOICE_SQL),
        {
            "tid": tenant_id, "inv_num": invoice_number, "qid": quote_id,
            "company_id": company_id, "contact_id": q.get("contact_id"),
            "currency": currency,
            "payment": None, "payment_method_id": None,
            "erp_key": erp_key, "due_date": None, "notes": q["notes"], "created_by": current_user.id,
            "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
            "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
            "issuer_region": issuer_region,
            **invoice_totals.to_db_params(totals),
        },
    )
    invoice_id = inv_result.scalar_one()

    # 見積明細をコピー（hs_code を含む）
    quote_items = await db.execute(
        text("SELECT product_id, product_name, name_en, condition, unit, quantity, unit_price, weight, subtotal, sort_order, hs_code FROM quote_items WHERE quote_id = :qid ORDER BY sort_order"),
        {"qid": quote_id},
    )
    for item in quote_items.mappings().all():
        await db.execute(
            text("""
                INSERT INTO invoice_items (invoice_id, product_id, product_name, name_en, condition, unit, quantity, unit_price, weight, subtotal, sort_order, hs_code)
                VALUES (:iid, :product_id, :product_name, :name_en, :condition, :unit, :quantity, :unit_price, :weight, :subtotal, :sort_order, :hs_code)
            """),
            {"iid": invoice_id, **dict(item)},
        )

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create_from_quote", table_name="invoices", record_id=invoice_id,
        new_data={"quote_id": quote_id, "invoice_number": invoice_number},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)

    fetched = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"), {"id": invoice_id})
    row = fetched.mappings().first()
    items = await _get_invoice_items(db, invoice_id)
    return InvoiceDetailResponse(**dict(row), items=[InvoiceItemResponse(**i) for i in items])


@router.post(
    "/invoices",
    response_model=InvoiceDetailResponse,
    status_code=201,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """請求書を直接作成する（見積もりを経由しない場合）"""
    # Step 5d: contact / company の存在 + 所属一致確認のみ
    contact_check = await db.execute(
        text("SELECT company_id FROM contacts WHERE id = :id"),
        {"id": data.contact_id},
    )
    contact_row = contact_check.first()
    if not contact_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:contact")
    if contact_row[0] != data.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定された担当者は指定会社に所属していません",
        )

    # スナップショット取得
    ship_to_snap = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, data.company_id, "billing")
    # ADR-1061 便2-2c2a: 発行元の地域は請求先の国で決めて保存する（国が無いと作らない）
    issuer_region = decide_issuer_region(bill_to_snap)
    if issuer_region is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="bill_to_country")

    currency = data.currency.upper()
    totals = await _compute(
        db, tenant_id, currency=currency,
        items=[invoice_totals.TotalsItem(quantity=i.quantity, unit_price=i.unit_price) for i in data.items],
        shipping=_shipping_choice(data.shipping), ship_to=ship_to_snap, bill_to=bill_to_snap,
    )
    _raise_if_blocked(totals)

    payment_text = None
    payment_method_id = None
    if data.payment_method_ref is not None:
        try:
            payment_text, payment_method_id = await invoice_payment_methods.resolve_payment_ref(
                db, tenant_id, method_type=data.payment_method_ref.method_type,
                method_id=data.payment_method_ref.id, region=issuer_region, currency=currency,
            )
        except PaymentMethodInvalid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payment_method")

    max_result = await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM invoices"))
    next_id = max_result.scalar()
    invoice_number = f"IN-{next_id:04d}-01"
    erp_key = str(uuid.uuid4())[:8].upper()

    inv_result = await db.execute(
        text(_INSERT_INVOICE_SQL),
        {
            "tid": tenant_id, "inv_num": invoice_number, "qid": None,
            "company_id": data.company_id, "contact_id": data.contact_id,
            "currency": currency,
            "payment": payment_text, "payment_method_id": payment_method_id,
            "erp_key": erp_key, "due_date": data.due_date, "notes": data.notes, "created_by": current_user.id,
            "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
            "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
            "issuer_region": issuer_region,
            **invoice_totals.to_db_params(totals),
        },
    )
    invoice_id = inv_result.scalar_one()

    for i, item in enumerate(data.items):
        line_subtotal = item.quantity * item.unit_price
        await db.execute(
            text("""
                INSERT INTO invoice_items (invoice_id, product_id, product_name, name_en, condition, unit, quantity, unit_price, weight, subtotal, sort_order)
                VALUES (:iid, :pid, :pname, :name_en, :condition, :unit, :qty, :price, :weight, :sub, :sort)
            """),
            {
                "iid": invoice_id, "pid": item.product_id, "pname": item.product_name,
                "name_en": item.name_en, "condition": item.condition, "unit": item.unit,
                "qty": item.quantity, "price": item.unit_price, "weight": item.weight,
                "sub": line_subtotal, "sort": i,
            },
        )

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="invoices", record_id=invoice_id,
        new_data={
            "company_id": data.company_id,
            "contact_id": data.contact_id,
            "invoice_number": invoice_number,
            "total": str(totals.total_amount),
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)

    fetched = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"), {"id": invoice_id})
    row = fetched.mappings().first()
    items = await _get_invoice_items(db, invoice_id)
    return InvoiceDetailResponse(**dict(row), items=[InvoiceItemResponse(**i) for i in items])


@router.patch(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    dependencies=[Depends(require_permission("invoices.update"))],
)
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """請求書ヘッダーを更新する（draft のみ編集可）"""
    old = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"), {"id": invoice_id})
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
    if old_row["status"] != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ編集できます")

    sent = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in sent.items() if k in _UPDATABLE_COLUMNS}
    if "payment_method_ref" in sent:
        ref = data.payment_method_ref
        if ref is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payment_method")
        try:
            payment_text, payment_method_id = await invoice_payment_methods.resolve_payment_ref(
                db, tenant_id, method_type=ref.method_type, method_id=ref.id,
                region=old_row["issuer_region"] or "overseas", currency=old_row["currency"],
            )
        except PaymentMethodInvalid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payment_method")
        update_data["payment_method"] = payment_text
        update_data["payment_method_id"] = payment_method_id
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_fields_to_update")

    set_clauses = ", ".join(f"{k} = :{k}" for k in update_data)
    update_data["id"] = invoice_id

    result = await db.execute(
        text(f"UPDATE invoices SET {set_clauses}, updated_at = NOW() WHERE id = :id RETURNING {_INVOICE_COLUMNS}"),
        update_data,
    )
    row = result.mappings().first()

    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="update", table_name="invoices", record_id=invoice_id,
                           old_data=dict(old_row), new_data=update_data)
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    return InvoiceResponse(**dict(row))


@router.post(
    "/invoices/{invoice_id}/issue",
    response_model=InvoiceResponse,
    dependencies=[Depends(require_permission("invoices.create"))],
)
async def issue_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """請求書を発行する（draft → issued）"""
    cur = await db.execute(
        text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id FOR UPDATE"),
        {"id": invoice_id},
    )
    old = cur.mappings().first()
    if not old or old["status"] != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ発行できます")

    if old["payment_method_id"] is not None:
        ok = await invoice_payment_methods.is_current_choice(
            db, tenant_id, payment_method_id=old["payment_method_id"],
            region=old["issuer_region"] or "overseas", currency=old["currency"],
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payment_method")

    items = await _get_invoice_items(db, invoice_id)
    totals = await _compute(
        db, tenant_id, currency=old["currency"],
        items=[invoice_totals.TotalsItem(quantity=i["quantity"], unit_price=Decimal(i["unit_price"])) for i in items],
        shipping=_shipping_from_stored(old),
        ship_to=_load_snapshot(old["ship_to_snapshot"]), bill_to=_load_snapshot(old["bill_to_snapshot"]),
    )
    _raise_if_blocked(totals)
    params = invoice_totals.to_db_params(totals)
    params.pop("shipping_carrier")
    params.pop("shipping_service")
    result = await db.execute(
        text(
            f"UPDATE invoices SET {_RECOMPUTE_SET_SQL}, status = 'issued', issued_at = NOW(), updated_at = NOW() "
            f"WHERE id = :id AND status = 'draft' RETURNING {_INVOICE_COLUMNS}"
        ),
        {**params, "id": invoice_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ発行できます")

    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="issue", table_name="invoices", record_id=invoice_id,
                           new_data={"status": "issued"})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)
    return InvoiceResponse(**dict(row))


@router.post(
    "/invoices/{invoice_id}/pay",
    response_model=InvoiceResponse,
    dependencies=[Depends(require_permission("invoices.update"))],
)
async def pay_invoice(
    invoice_id: int,
    body: PayInvoiceRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """入金を登録する（issued/overdue → paid）。body.paid_date（日付のみ）を渡すとその日の入金として登録できる。"""
    paid_date = body.paid_date if body else None
    # 未来日は不可（時差で「今日」が UTC の明日になる地域を許容するため UTC の明日までは通す）
    if paid_date is not None and paid_date > (datetime.now(timezone.utc) + timedelta(days=1)).date():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="入金日に未来の日付は指定できません")
    paid_at_value = paid_at_from_date(paid_date)
    result = await db.execute(
        text(f"UPDATE invoices SET status = 'paid', paid_at = {PAID_AT_SQL}, updated_at = NOW() WHERE id = :id AND status IN ('issued', 'overdue') RETURNING {_INVOICE_COLUMNS}"),
        {"id": invoice_id, "paid_at": paid_at_value},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="issued/overdue状態の請求書のみ入金登録できます")

    # ADR-104: 紐づく受注を 支払い待ち→仕入れ中 へ自動遷移（awaiting_payment のみ）
    await db.execute(
        text(f"UPDATE orders SET status='sourcing', paid_at={PAID_AT_SQL}, updated_at=NOW() "
             "WHERE invoice_id=:iid AND status='awaiting_payment'"),
        {"iid": invoice_id, "paid_at": paid_at_value},
    )
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="pay", table_name="invoices", record_id=invoice_id,
                           new_data={"status": "paid"})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)
    return InvoiceResponse(**dict(row))


@router.post(
    "/invoices/{invoice_id}/void",
    response_model=InvoiceResponse,
    dependencies=[Depends(require_permission("invoices.void"))],
)
async def void_invoice(
    invoice_id: int,
    data: VoidRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """請求書を無効化する"""
    old = await db.execute(text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"), {"id": invoice_id})
    old_row = old.mappings().first()
    if not old_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
    if old_row["status"] == "voided":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="既に無効化されています")
    if old_row["status"] == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="入金済みの請求書は無効化できません")

    voided_number = f"[VOID]{old_row['invoice_number']}"
    result = await db.execute(
        text(f"""
            UPDATE invoices
            SET status = 'voided', invoice_number = :vnum, voided_at = NOW(),
                void_reason = :reason, updated_at = NOW()
            WHERE id = :id
            RETURNING {_INVOICE_COLUMNS}
        """),
        {"id": invoice_id, "vnum": voided_number, "reason": data.reason},
    )
    row = result.mappings().first()

    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="void", table_name="invoices", record_id=invoice_id,
                           old_data=dict(old_row), new_data={"status": "voided", "reason": data.reason})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)
    return InvoiceResponse(**dict(row))


# ──────────────────────────────────────────────────────────────────────
# ADR-101 §6 PayPal mode1 (Increment 1): 決済リンク発行 / 入金確認
# ──────────────────────────────────────────────────────────────────────

# 顧客が承認後に戻る URL。Increment 1 は手動 capture のため導線確認用（env で上書き可）。
_APP_BASE_URL = os.getenv("APP_BASE_URL", "https://app.salesanchor.jp").rstrip("/")
# Increment 2: 顧客が PayPal 承認後に戻る公開エンドポイント（API 側）のベース。
_API_BASE_URL = os.getenv("API_BASE_URL", "https://api.salesanchor.jp").rstrip("/")


async def _require_paypal_creds(db: AsyncSession, tenant_id: int) -> dict:
    creds = await paypal_payments.get_credentials(db, tenant_id)
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PayPal が未接続です（管理センター > API連携 > PayPal で認証情報を登録してください）",
        )
    return creds


@router.post(
    "/invoices/{invoice_id}/paypal-link",
    response_model=InvoiceResponse,
    dependencies=[Depends(require_permission("invoices.update"))],
)
async def issue_paypal_link(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """請求書から PayPal 請求書を発行・送付する（issued/overdue のみ）。

    ADR-101 改訂 2026-06-12: PayPal Invoicing 方式。自社請求書のデータから PayPal Invoice を
    生成し、PayPal が顧客にメール送付＋ホスト決済ページを提供する。送付先 email 必須。
    """
    inv = await db.execute(
        text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"),
        {"id": invoice_id},
    )
    inv_row = inv.mappings().first()
    if not inv_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
    if inv_row["status"] not in ("issued", "overdue"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみリンク発行できます")
    if inv_row["total_amount"] is None or Decimal(inv_row["total_amount"]) <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="請求金額が未確定です")

    # Invoicing 方式は送付先 email 必須（PayPal が顧客にメール送付するため）
    if inv_row["contact_id"] is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="請求書に担当者（contact）が紐づいていません")
    email_row = (await db.execute(
        text("SELECT primary_email FROM contacts WHERE id = :cid"),
        {"cid": inv_row["contact_id"]},
    )).mappings().first()
    recipient_email = (email_row or {}).get("primary_email")
    if not recipient_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="送付先メールアドレスが未登録のため PayPal 請求書を発行できません",
        )

    creds = await _require_paypal_creds(db, tenant_id)
    result = await run_in_threadpool(
        paypal_payments.create_and_send_invoice,
        creds["environment"], creds["client_id"], creds["client_secret"],
        invoice_number=inv_row["invoice_number"],
        currency=inv_row["currency"],
        amount=inv_row["total_amount"],
        recipient_email=recipient_email,
        reference=f"{tenant_id}:{invoice_id}",  # webhook ルーティング用（detail.reference）
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("message", "PayPal 請求書の発行に失敗しました"),
        )

    # status ガードを UPDATE にも入れる（事前 SELECT 後に void 等された TOCTOU 防御）。
    # paypal_order_id=PayPal Invoice ID, paypal_approval_url=recipient_view_url を流用（migration 不要）。
    upd = await db.execute(
        text(f"""
            UPDATE invoices
            SET paypal_order_id = :oid, paypal_approval_url = :url,
                payment_method = COALESCE(payment_method, 'paypal'), updated_at = NOW()
            WHERE id = :id AND status IN ('issued', 'overdue')
            RETURNING {_INVOICE_COLUMNS}
        """),
        {"id": invoice_id, "oid": result["paypal_invoice_id"], "url": result["recipient_view_url"]},
    )
    row = upd.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみリンク発行できます")

    # ADR-101改訂(2) Inc1: 発行者ビューURLを保存し、写しPDFを自動生成・DB保存する。
    # 写しPDF 生成失敗はリンク発行を失敗にしない（致命にしない・後で再生成可能）。
    copy_pdf: bytes | None = None
    try:
        copy_pdf = await _render_paypal_copy_pdf(
            db, tenant_id, row, invoice_id,
            result["paypal_invoice_id"], result.get("recipient_view_url"),
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("[paypal] 写しPDF 生成失敗 invoice=%s: %s", invoice_id, e)
    upd2 = await db.execute(
        text(f"""
            UPDATE invoices
            SET paypal_invoicer_view_url = :iv,
                paypal_copy_pdf = COALESCE(:pdf, paypal_copy_pdf),
                paypal_copy_pdf_at = CASE WHEN :pdf IS NULL THEN paypal_copy_pdf_at ELSE NOW() END,
                updated_at = NOW()
            WHERE id = :id
            RETURNING {_INVOICE_COLUMNS}
        """),
        {"id": invoice_id, "iv": result.get("invoicer_view_url"), "pdf": copy_pdf},
    )
    row = upd2.mappings().first() or row
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="paypal_link", table_name="invoices", record_id=invoice_id,
                           new_data={"paypal_invoice_id": result["paypal_invoice_id"],
                                     "copy_pdf_saved": copy_pdf is not None})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)
    return InvoiceResponse(**dict(row))


@router.post(
    "/invoices/{invoice_id}/paypal-confirm",
    response_model=InvoiceResponse,
    dependencies=[Depends(require_permission("invoices.update"))],
)
async def confirm_paypal_payment(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """PayPal 請求書の支払い状況を取得し、PAID なら請求書を paid にする（issued/overdue のみ）。

    ADR-101 改訂 2026-06-12: Invoicing 方式。paypal_order_id=PayPal Invoice ID で
    GET /v2/invoicing/invoices/{id} を引き、status=PAID を確認する。
    """
    inv = await db.execute(
        text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"),
        {"id": invoice_id},
    )
    inv_row = inv.mappings().first()
    if not inv_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found:invoice")
    if not inv_row["paypal_order_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="先に PayPal 請求書を発行してください")
    if inv_row["status"] not in ("issued", "overdue"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみ入金確認できます")

    creds = await _require_paypal_creds(db, tenant_id)
    result = await run_in_threadpool(
        paypal_payments.get_invoice_status,
        creds["environment"], creds["client_id"], creds["client_secret"],
        inv_row["paypal_order_id"],
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("message", "PayPal 入金確認に失敗しました"),
        )
    if not result.get("paid"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result.get("message", "まだ入金が確認できません"),
        )

    # status ガードを UPDATE にも入れる（既に paid/voided への二重適用を atomic に防ぐ TOCTOU 防御）
    paid_at_value = paypal_paid_at(result.get("payment_date"))
    upd = await db.execute(
        text(f"""
            UPDATE invoices
            SET status = 'paid', paid_at = {PAID_AT_SQL}, payment_fee = :fee,
                payment_method = 'paypal', updated_at = NOW()
            WHERE id = :id AND status IN ('issued', 'overdue')
            RETURNING {_INVOICE_COLUMNS}
        """),
        {"id": invoice_id, "fee": result.get("fee"), "paid_at": paid_at_value},
    )
    row = upd.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみ入金確認できます")
    # ADR-104: 入金確認で紐づく受注を「支払い待ち→仕入れ中」へ自動遷移（awaiting_payment のみ）
    await db.execute(
        text(f"UPDATE orders SET status = 'sourcing', paid_at = {PAID_AT_SQL}, updated_at = NOW() "
             "WHERE invoice_id = :iid AND status = 'awaiting_payment'"),
        {"iid": invoice_id, "paid_at": paid_at_value},
    )
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="paypal_confirm", table_name="invoices", record_id=invoice_id,
                           new_data={"status": "paid", "payment_fee": result.get("fee")})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    await invalidate_dashboard_cache(tenant_id)
    return InvoiceResponse(**dict(row))


# ──────────────────────────────────────────────────────────────────────
# C-8: PDF ダウンロード（請求書 / 見積書）
# ──────────────────────────────────────────────────────────────────────

async def _pdf_payment(db: AsyncSession, tenant_id: int, row) -> dict | None:
    """PDF の支払方法の区切り（design.md §3-7）。版は古くても消されていてもその版を読む。"""
    if row["payment_method_id"] is not None:
        return await invoice_payment_methods.load_payment_version(db, tenant_id, row["payment_method_id"])
    if row["payment_method"] == "paypal":
        return {"method_type": "paypal"}
    return None


@router.get(
    "/invoices/{invoice_id}/pdf",
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def download_invoice_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """請求書 PDF を生成して返す（C-8）。"""
    result = await db.execute(
        text(f"SELECT {_INVOICE_COLUMNS} FROM invoices WHERE id = :id"),
        {"id": invoice_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")

    items = await _get_invoice_items(db, invoice_id)
    tenant_profile = await get_issuer(db, tenant_id, row["issuer_region"] or "overseas")

    invoice_data = {
        "invoice_code": row["invoice_number"] or f"IN-{invoice_id:04d}-01",
        "issued_at": row["issued_at"].isoformat() if row["issued_at"] else None,
        "ship_to_snapshot": row["ship_to_snapshot"],
        "bill_to_snapshot": row["bill_to_snapshot"],
        "items": [
            {
                "name_en": it.get("name_en") or it.get("product_name") or "-",
                "quantity": it["quantity"],
                "unit_price": float(it["unit_price"] or 0),
                "subtotal": float(it["subtotal"] or 0),
                "hs_code": it.get("hs_code"),
            }
            for it in items
        ],
        "subtotal": float(row["subtotal"] or 0),
        "shipping_fee": float(row["shipping_fee"] or 0),
        "tax_amount": float(row["tax_amount"] or 0),
        "total_amount": float(row["total_amount"] or 0),
        "currency": row["currency"],
        "duty_amount": float(row["duty_amount"]) if row["duty_amount"] is not None else None,
        "fx_rate_snapshot": row["fx_rate_snapshot"],
        "notes": row["notes"],
        "tax_rate_percent": float(row["tax_rate_percent"]) if row["tax_rate_percent"] is not None else None,
        "payment": await _pdf_payment(db, tenant_id, row),
    }

    pdf_bytes = await run_in_threadpool(render_invoice_pdf, invoice_data, tenant_profile)
    filename = f"{invoice_data['invoice_code']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────────────────────────────
# ADR-101改訂(2) Inc1: PayPal 請求書の写しPDF（自動保存・取得）
# ──────────────────────────────────────────────────────────────────────

async def _render_paypal_copy_pdf(db: AsyncSession, tenant_id: int, row, invoice_id: int,
                                  pp_invoice_number: str, original_url: str | None) -> bytes:
    """請求書データ＋テナント情報から写しPDF（PayPal 請求書の写し注記＋原本リンク＋QR）を生成。"""
    items = await _get_invoice_items(db, invoice_id)
    tenant_profile = await get_issuer(db, tenant_id, row["issuer_region"] or "overseas")
    invoice_data = {
        "invoice_code": row["invoice_number"] or f"IN-{invoice_id:04d}-01",
        "issued_at": row["issued_at"].isoformat() if row["issued_at"] else None,
        "ship_to_snapshot": row["ship_to_snapshot"],
        "bill_to_snapshot": row["bill_to_snapshot"],
        "items": [
            {
                "name_en": it.get("name_en") or it.get("product_name") or "-",
                "quantity": it["quantity"],
                "unit_price": float(it["unit_price"] or 0),
                "subtotal": float(it["subtotal"] or 0),
                "hs_code": it.get("hs_code"),
            }
            for it in items
        ],
        "subtotal": float(row["subtotal"] or 0),
        "shipping_fee": float(row["shipping_fee"] or 0),
        "tax_amount": float(row["tax_amount"] or 0),
        "total_amount": float(row["total_amount"] or 0),
        "currency": row["currency"],
        "duty_amount": float(row["duty_amount"]) if row["duty_amount"] is not None else None,
        "fx_rate_snapshot": row["fx_rate_snapshot"],
        "notes": row["notes"],
    }
    paypal_copy = {"pp_invoice_number": pp_invoice_number, "original_url": original_url}
    return await run_in_threadpool(render_invoice_pdf, invoice_data, tenant_profile, paypal_copy)


@router.get(
    "/invoices/{invoice_id}/paypal-copy-pdf",
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def download_paypal_copy_pdf(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),  # noqa: ARG001
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """保存済みの PayPal 写しPDF（送信時に自動生成）を返す。未保存は 404。"""
    res = await db.execute(
        text("SELECT invoice_number, paypal_copy_pdf FROM invoices WHERE id = :id"),
        {"id": invoice_id},
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
    pdf = row["paypal_copy_pdf"]
    if not pdf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="写しPDFはまだ生成されていません")
    filename = f"{row['invoice_number'] or f'IN-{invoice_id:04d}-01'}-paypal-copy.pdf"
    return Response(
        content=bytes(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/invoices/{invoice_id}/paypal-disputes",
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def list_invoice_paypal_disputes(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),  # noqa: ARG001
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """請求書に紐づく PayPal ケース（dispute）一覧（ADR-101改訂(2) Inc4 Step B）。"""
    res = await db.execute(
        text("""
            SELECT dispute_id, pp_status, reason, amount, currency, created_at, updated_at
            FROM paypal_disputes WHERE invoice_id = :id ORDER BY created_at DESC
        """),
        {"id": invoice_id},
    )
    def _iso(v):
        return v.isoformat() if hasattr(v, "isoformat") else v

    return [
        {
            "dispute_id": r["dispute_id"],
            "status": r["pp_status"],
            "reason": r["reason"],
            "amount": float(r["amount"]) if r["amount"] is not None else None,
            "currency": r["currency"],
            "created_at": _iso(r["created_at"]),
            "updated_at": _iso(r["updated_at"]),
        }
        for r in res.mappings().all()
    ]


@router.get(
    "/quotes/{quote_id}/pdf",
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def download_quote_pdf(
    quote_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """見積書 PDF を生成して返す（C-8）。"""
    result = await db.execute(
        text("""
            SELECT id, quote_code, company_id, currency,
                   subtotal, shipping_fee, tax_amount, total_amount,
                   notes, created_at
            FROM quotes WHERE id = :id
        """),
        {"id": quote_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")

    items_result = await db.execute(
        text("""
            SELECT product_id, product_name, name_en, condition, unit,
                   quantity, unit_price, weight, subtotal, sort_order, hs_code
            FROM quote_items WHERE quote_id = :qid ORDER BY sort_order, id
        """),
        {"qid": quote_id},
    )
    items = [dict(r) for r in items_result.mappings().all()]

    company_id = row["company_id"]
    ship_to_snap = await _fetch_address_snapshot(db, company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, company_id, "billing")

    # ADR-1061 便2-2c2a: 見積は地域を持たないので海外用の発行元を使う
    tenant_profile = await get_issuer(db, tenant_id, "overseas")

    quote_data = {
        "quote_code": row["quote_code"] or f"QT-{quote_id:04d}",
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "ship_to_snapshot": ship_to_snap,
        "bill_to_snapshot": bill_to_snap,
        "items": [
            {
                "name_en": it.get("name_en") or it.get("product_name") or "-",
                "quantity": it["quantity"],
                "unit_price": float(it["unit_price"] or 0),
                "subtotal": float(it["subtotal"] or 0),
                "hs_code": it.get("hs_code"),
            }
            for it in items
        ],
        "subtotal": float(row["subtotal"] or 0),
        "shipping_fee": float(row["shipping_fee"] or 0),
        "tax_amount": float(row["tax_amount"] or 0),
        "total_amount": float(row["total_amount"] or 0),
        "currency": row["currency"],
        "notes": row["notes"],
    }

    pdf_bytes = render_quote_pdf(quote_data, tenant_profile)
    filename = f"{quote_data['quote_code']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/fx-rate/{currency}",
    dependencies=[Depends(require_permission("invoices.view"))],
)
async def fetch_fx_rate(
    currency: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),  # noqa: ARG001
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """
    指定通貨の為替レートを為替の表（public.app_fx_rate_history）の最新行から返す（invoice-create-portfolio 便C・K24）。

    JPY 指定時は {"currency":"JPY","rate":1.0,"fetched_at":null} を返す。
    取得失敗時は 503 を返す。
    """
    if currency.upper() == "JPY":
        return {"currency": "JPY", "rate": 1.0, "fetched_at": None}

    fx = await invoice_totals.load_latest_fx(db)
    row = fx.get(currency.upper())
    result = (
        None if row is None
        else {"currency": row.currency, "rate": float(row.rate_jpy), "fetched_at": invoice_totals._iso_utc(row.fetched_at)}
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"為替レートの取得に失敗しました: {currency}",
        )
    return result
