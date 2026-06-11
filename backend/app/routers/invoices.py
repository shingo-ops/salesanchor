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
import os
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
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
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceItemResponse,
    InvoiceResponse,
    InvoiceUpdate,
    VoidRequest,
)
from app.services import paypal_payments
from app.services.audit import record_audit_log
from app.services.fx_rate import get_fx_rate
from app.services.invoice_renderer import render_invoice_pdf, render_quote_pdf

router = APIRouter()


async def _get_tenant_schema(tenant_id: int) -> str:
    """tenant_id からスキーマ名 (tenant_NNN) を生成する。"""
    return f"tenant_{tenant_id:03d}"


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
                   c.name AS company_name
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


async def _fetch_tenant_profile(db: AsyncSession, tenant_schema: str) -> dict:
    """tenant_profile からテナント情報を取得する。"""
    result = await db.execute(
        text(f"""
            SELECT company_name, company_name_en, address, phone, email, website
            FROM {tenant_schema}.tenant_profile
            ORDER BY id LIMIT 1
        """),
    )
    row = result.mappings().first()
    if not row:
        return {}
    return {
        "name": row["company_name"] or row["company_name_en"] or "",
        "address": row["address"] or "",
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "website": row["website"] or "",
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
    paypal_order_id, paypal_approval_url, payment_fee
"""

_UPDATABLE_COLUMNS = {"payment_method", "due_date", "exchange_rate_jpy", "exchange_rate_usd", "notes"}


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


def _calc_currency_amounts(total: Decimal, currency: str,
                           rate_jpy: Decimal | None, rate_usd: Decimal | None) -> tuple[Decimal | None, Decimal | None]:
    """通貨換算額を算出。"""
    amount_jpy = None
    amount_usd = None
    if currency == "JPY":
        amount_jpy = total
        if rate_usd and rate_usd > 0:
            amount_usd = round(total / rate_usd, 2)
    elif currency == "USD":
        amount_usd = total
        if rate_jpy:
            amount_jpy = round(total * rate_jpy, 2)
    elif currency == "EUR":
        if rate_jpy:
            amount_jpy = round(total * rate_jpy, 2)
        if rate_usd:
            amount_usd = round(total * rate_usd, 2)
    return amount_jpy, amount_usd


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
    items = await _get_invoice_items(db, invoice_id)
    return InvoiceDetailResponse(**dict(row), items=[InvoiceItemResponse(**i) for i in items])


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="見積もりが見つかりません")
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

    # 為替レート取得（JPY 以外の場合）
    currency = q["currency"]
    fx_snap = get_fx_rate(currency) if currency and currency.upper() != "JPY" else None

    # 請求書ヘッダー作成（Step 5d: quote から company_id/contact_id を継承）
    inv_result = await db.execute(
        text("""
            INSERT INTO invoices (
                tenant_id, invoice_number, quote_id, company_id, contact_id, currency,
                subtotal, shipping_fee, tax_amount, total_amount,
                payment_method, status, branch_number, erp_key, notes, created_by,
                ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot
            ) VALUES (
                :tid, :inv_num, :qid, :company_id, :contact_id, :currency,
                :subtotal, :shipping, :tax, :total,
                NULL, 'draft', 1, :erp_key, :notes, :created_by,
                :ship_to, :bill_to, :fx_rate
            ) RETURNING id
        """),
        {
            "tid": tenant_id, "inv_num": invoice_number, "qid": quote_id,
            "company_id": company_id, "contact_id": q.get("contact_id"),
            "currency": currency,
            "subtotal": q["subtotal"], "shipping": q["shipping_fee"],
            "tax": q["tax_amount"], "total": q["total_amount"],
            "erp_key": erp_key, "notes": q["notes"], "created_by": current_user.id,
            "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
            "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
            "fx_rate": json.dumps(fx_snap) if fx_snap else None,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定された担当者が見つかりません")
    if contact_row[0] != data.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定された担当者は指定会社に所属していません",
        )

    subtotal = sum(item.quantity * item.unit_price for item in data.items)
    shipping = data.shipping_fee or Decimal(0)
    tax = data.tax_amount or Decimal(0)
    total = subtotal + shipping + tax
    amount_jpy, amount_usd = _calc_currency_amounts(total, data.currency, data.exchange_rate_jpy, data.exchange_rate_usd)

    # スナップショット取得
    ship_to_snap = await _fetch_address_snapshot(db, data.company_id, "delivery")
    bill_to_snap = await _fetch_address_snapshot(db, data.company_id, "billing")

    # 為替レート取得（JPY 以外の場合）
    fx_snap = get_fx_rate(data.currency) if data.currency and data.currency.upper() != "JPY" else None

    max_result = await db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM invoices"))
    next_id = max_result.scalar()
    invoice_number = f"IN-{next_id:04d}-01"
    erp_key = str(uuid.uuid4())[:8].upper()

    inv_result = await db.execute(
        text("""
            INSERT INTO invoices (
                tenant_id, invoice_number, company_id, contact_id, currency,
                subtotal, shipping_fee, tax_amount, total_amount,
                exchange_rate_jpy, exchange_rate_usd, amount_jpy, amount_usd,
                payment_method, status, branch_number, erp_key,
                due_date, notes, created_by,
                ship_to_snapshot, bill_to_snapshot, fx_rate_snapshot
            ) VALUES (
                :tid, :inv_num, :company_id, :contact_id, :currency,
                :subtotal, :shipping, :tax, :total,
                :rate_jpy, :rate_usd, :amt_jpy, :amt_usd,
                :payment, 'draft', 1, :erp_key,
                :due_date, :notes, :created_by,
                :ship_to, :bill_to, :fx_rate
            ) RETURNING id
        """),
        {
            "tid": tenant_id, "inv_num": invoice_number,
            "company_id": data.company_id, "contact_id": data.contact_id,
            "currency": data.currency, "subtotal": subtotal, "shipping": shipping,
            "tax": tax, "total": total, "rate_jpy": data.exchange_rate_jpy,
            "rate_usd": data.exchange_rate_usd, "amt_jpy": amount_jpy, "amt_usd": amount_usd,
            "payment": data.payment_method, "erp_key": erp_key,
            "due_date": data.due_date, "notes": data.notes, "created_by": current_user.id,
            "ship_to": json.dumps(ship_to_snap) if ship_to_snap else None,
            "bill_to": json.dumps(bill_to_snap) if bill_to_snap else None,
            "fx_rate": json.dumps(fx_snap) if fx_snap else None,
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
            "total": str(total),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
    if old_row["status"] != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="draft状態の請求書のみ編集できます")

    update_data = data.model_dump(exclude_unset=True)
    update_data = {k: v for k, v in update_data.items() if k in _UPDATABLE_COLUMNS}
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="更新するフィールドを指定してください")

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
    result = await db.execute(
        text(f"UPDATE invoices SET status = 'issued', issued_at = NOW(), updated_at = NOW() WHERE id = :id AND status = 'draft' RETURNING {_INVOICE_COLUMNS}"),
        {"id": invoice_id},
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
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """入金を登録する（issued/overdue → paid）"""
    result = await db.execute(
        text(f"UPDATE invoices SET status = 'paid', paid_at = NOW(), updated_at = NOW() WHERE id = :id AND status IN ('issued', 'overdue') RETURNING {_INVOICE_COLUMNS}"),
        {"id": invoice_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="issued/overdue状態の請求書のみ入金登録できます")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
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
    await record_audit_log(db=db, tenant_id=tenant_id, user_id=current_user.id,
                           action="paypal_link", table_name="invoices", record_id=invoice_id,
                           new_data={"paypal_invoice_id": result["paypal_invoice_id"]})
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="請求書が見つかりません")
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
    upd = await db.execute(
        text(f"""
            UPDATE invoices
            SET status = 'paid', paid_at = NOW(), payment_fee = :fee,
                payment_method = 'paypal', updated_at = NOW()
            WHERE id = :id AND status IN ('issued', 'overdue')
            RETURNING {_INVOICE_COLUMNS}
        """),
        {"id": invoice_id, "fee": result.get("fee")},
    )
    row = upd.mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="発行済み（issued/overdue）の請求書のみ入金確認できます")
    # ADR-104: 入金確認で紐づく受注を「支払い待ち→仕入れ中」へ自動遷移（awaiting_payment のみ）
    await db.execute(
        text("UPDATE orders SET status = 'sourcing', paid_at = NOW(), updated_at = NOW() "
             "WHERE invoice_id = :iid AND status = 'awaiting_payment'"),
        {"iid": invoice_id},
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
    tenant_schema = await _get_tenant_schema(tenant_id)
    tenant_profile = await _fetch_tenant_profile(db, tenant_schema)

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

    pdf_bytes = render_invoice_pdf(invoice_data, tenant_profile)
    filename = f"{invoice_data['invoice_code']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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

    tenant_schema = await _get_tenant_schema(tenant_id)
    tenant_profile = await _fetch_tenant_profile(db, tenant_schema)

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
    tenant_id: int = Depends(get_current_tenant),  # noqa: ARG001
    current_user: User = Depends(get_current_user),  # noqa: ARG001
):
    """
    指定通貨の為替レートをライブ取得する（C-7）。

    JPY 指定時は {"currency":"JPY","rate":1.0,"fetched_at":null} を返す。
    取得失敗時は 503 を返す。
    """
    if currency.upper() == "JPY":
        return {"currency": "JPY", "rate": 1.0, "fetched_at": None}

    result = get_fx_rate(currency)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"為替レートの取得に失敗しました: {currency}",
        )
    return result
