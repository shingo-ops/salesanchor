from __future__ import annotations

"""
配送・物流管理API（ゾーン/料金マスタ + 配送料自動計算）。

旧GAS版の13_Shipping.gs に相当。
国→ゾーン→重量帯→料金の3段階検索で配送料を算出。
キャリア未指定時はFedEx/DHL/UPS3社比較で最安値を返す。

変更履歴:
  2026-04-17: 初版作成（Phase 2）
  2026-06-09: ADR-125 — FedEx ライブ見積もり分岐追加
  2026-06-11: ADR-128 — FedEx ラベル発行・集荷予約エンドポイント追加
"""

import asyncio
import json
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.database import get_db
from app.models import User
from app.schemas.shipping import (
    CreatePickupRequest,
    CreatePickupResponse,
    CreateShipmentRequest,
    CreateShipmentResponse,
    ShippingCalcRequest,
    ShippingCalcResponse,
    ShippingCalcResult,
    ShippingRateCreate,
    ShippingRateResponse,
    ShippingZoneCreate,
    ShippingZoneResponse,
    SurchargeDetail,
)
from app.services import carrier_credentials, fedex_rates
from app.services.audit import record_audit_log
from app.services.fedex_rates import FedExAPIError, FedExAuthError

logger = logging.getLogger(__name__)

router = APIRouter()


# =========================================================================
# 配送ゾーン
# =========================================================================

@router.get(
    "/shipping/zones",
    response_model=list[ShippingZoneResponse],
    dependencies=[Depends(require_permission("shipping.view"))],
)
async def list_zones(
    carrier: str | None = Query(default=None),
    country_code: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    conditions = []
    params: dict = {}
    if carrier:
        conditions.append("carrier = :carrier")
        params["carrier"] = carrier
    if country_code:
        conditions.append("country_code = :cc")
        params["cc"] = country_code.upper()
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = await db.execute(
        text(f"SELECT id, country_code, country_name, carrier, zone, created_at FROM shipping_zones {where} ORDER BY country_name, carrier"),
        params,
    )
    return [ShippingZoneResponse(**row) for row in result.mappings().all()]


@router.post(
    "/shipping/zones",
    response_model=ShippingZoneResponse,
    status_code=201,
    dependencies=[Depends(require_permission("shipping.manage"))],
)
async def create_zone(
    data: ShippingZoneCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await db.execute(
            text("""
                INSERT INTO shipping_zones (tenant_id, country_code, country_name, carrier, zone)
                VALUES (:tid, :cc, :cn, :carrier, :zone)
                RETURNING id, country_code, country_name, carrier, zone, created_at
            """),
            {
                "tid": tenant_id,
                "cc": data.country_code.upper(),
                "cn": data.country_name,
                "carrier": data.carrier,
                "zone": data.zone,
            },
        )
        row = result.mappings().first()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同じ国・キャリアのゾーンが既に存在します")

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="shipping_zones", record_id=row["id"],
        new_data=data.model_dump(),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    return ShippingZoneResponse(**dict(row))


@router.delete(
    "/shipping/zones/{zone_id}",
    status_code=204,
    dependencies=[Depends(require_permission("shipping.manage"))],
)
async def delete_zone(
    zone_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text("DELETE FROM shipping_zones WHERE id = :id RETURNING id"),
        {"id": zone_id},
    )
    if not result.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ゾーンが見つかりません")
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="delete", table_name="shipping_zones", record_id=zone_id,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


# =========================================================================
# 配送料金
# =========================================================================

@router.get(
    "/shipping/rates",
    response_model=list[ShippingRateResponse],
    dependencies=[Depends(require_permission("shipping.view"))],
)
async def list_rates(
    carrier: str | None = Query(default=None),
    zone: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    conditions = []
    params: dict = {}
    if carrier:
        conditions.append("carrier = :carrier")
        params["carrier"] = carrier
    if zone:
        conditions.append("zone = :zone")
        params["zone"] = zone
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    result = await db.execute(
        text(f"""
            SELECT id, carrier, zone, weight_min, weight_max, price, currency, created_at, updated_at
            FROM shipping_rates {where}
            ORDER BY carrier, zone, weight_min
        """),
        params,
    )
    return [ShippingRateResponse(**row) for row in result.mappings().all()]


@router.post(
    "/shipping/rates",
    response_model=ShippingRateResponse,
    status_code=201,
    dependencies=[Depends(require_permission("shipping.manage"))],
)
async def create_rate(
    data: ShippingRateCreate,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text("""
            INSERT INTO shipping_rates (tenant_id, carrier, zone, weight_min, weight_max, price, currency)
            VALUES (:tid, :carrier, :zone, :wmin, :wmax, :price, :currency)
            RETURNING id, carrier, zone, weight_min, weight_max, price, currency, created_at, updated_at
        """),
        {
            "tid": tenant_id,
            "carrier": data.carrier,
            "zone": data.zone,
            "wmin": data.weight_min,
            "wmax": data.weight_max,
            "price": data.price,
            "currency": data.currency,
        },
    )
    row = result.mappings().first()

    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="create", table_name="shipping_rates", record_id=row["id"],
        new_data=data.model_dump(mode="json"),
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5
    return ShippingRateResponse(**dict(row))


@router.delete(
    "/shipping/rates/{rate_id}",
    status_code=204,
    dependencies=[Depends(require_permission("shipping.manage"))],
)
async def delete_rate(
    rate_id: int,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        text("DELETE FROM shipping_rates WHERE id = :id RETURNING id"),
        {"id": rate_id},
    )
    if not result.first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="料金が見つかりません")
    await record_audit_log(
        db=db, tenant_id=tenant_id, user_id=current_user.id,
        action="delete", table_name="shipping_rates", record_id=rate_id,
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2.5


# =========================================================================
# 配送料自動計算
# =========================================================================

async def calculate_shipping_fee(
    db: AsyncSession,
    country_code: str,
    weight_kg: Decimal,
    carrier: str | None = None,
) -> list[ShippingCalcResult]:
    """
    国コード＋重量から静的テーブルで配送料を計算する。
    carrier指定時はそのキャリアのみ、未指定時はFedEx/DHL/UPS全社を返す。
    source は常に 'static'。
    """
    conditions = ["sz.country_code = :cc"]
    params: dict = {"cc": country_code.upper(), "weight": weight_kg}
    if carrier:
        conditions.append("sz.carrier = :carrier")
        params["carrier"] = carrier

    where = " AND ".join(conditions)

    result = await db.execute(
        text(f"""
            SELECT sz.carrier, sz.zone, sr.price, sr.currency
            FROM shipping_zones sz
            JOIN shipping_rates sr
              ON sr.carrier = sz.carrier
             AND sr.zone = sz.zone
             AND sr.weight_min <= :weight
             AND sr.weight_max >= :weight
            WHERE {where}
            ORDER BY sr.price
        """),
        params,
    )
    rows = result.mappings().all()
    return [
        ShippingCalcResult(
            carrier=r["carrier"],
            zone=r["zone"],
            fee=r["price"],
            currency=r["currency"],
            source="static",
        )
        for r in rows
    ]


async def _try_fedex_live(
    creds: dict,
    tenant_id: int,
    destination_country_code: str,
    origin_country_code: str,
    weight_kg: Decimal,
    origin_postal_code: Optional[str] = None,
    destination_postal_code: Optional[str] = None,
) -> tuple[list[ShippingCalcResult], Optional[str], Optional[str]]:
    """FedEx Rates API を呼び出し、結果・live_error・rate_precision を返す。

    ADR-125 D5（暗黙フォールバック禁止）:
      - account_number が未設定 → live_error を返す（空リスト + エラー文字列）
      - API エラー → live_error を返す
      - 成功 → (results, None, precision)

    Returns:
        (results, live_error, rate_precision)
        rate_precision: 'exact'（郵便番号指定あり）または 'approximate'（代表値で補完）
    """
    account_number = creds.get("account_number")
    if not account_number:
        return [], "FedEx アカウント番号が未設定です（キャリア連携設定で登録してください）", None

    # 郵便番号の有無で精度を判定
    precision = "exact" if destination_postal_code else "approximate"

    try:
        quotes = await asyncio.to_thread(
            fedex_rates.get_rates,
            tenant_id=tenant_id,
            environment=creds["environment"],
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            account_number=account_number,
            origin_country_code=origin_country_code,
            destination_country_code=destination_country_code,
            weight_kg=weight_kg,
            origin_postal_code=origin_postal_code,
            destination_postal_code=destination_postal_code,
        )
    except FedExAuthError as e:
        logger.warning("[shipping] tenant=%d FedEx 認証エラー: %s", tenant_id, e)
        return [], f"FedEx 認証エラー: {e}", None
    except FedExAPIError as e:
        logger.warning("[shipping] tenant=%d FedEx API エラー: %s", tenant_id, e)
        return [], f"FedEx 見積もり取得失敗: {e}", None

    results = [
        ShippingCalcResult(
            carrier="fedex",
            zone=q.service_type,         # zone フィールドにサービスタイプを格納
            fee=q.total_net_charge,
            currency=q.currency,
            source="fedex_live",
            service_type=q.service_type,
            service_name=q.service_name,
            transit_days=q.transit_days,
            delivery_timestamp=q.delivery_timestamp,
            surcharges=[
                SurchargeDetail(
                    description=s.get("description", ""),
                    amount=s.get("amount") or 0,
                    currency=s.get("currency", q.currency),
                )
                for s in q.surcharges
                if s.get("amount") is not None
            ],
        )
        for q in quotes
    ]
    return results, None, precision


@router.post(
    "/shipping/calculate",
    response_model=ShippingCalcResponse,
    dependencies=[Depends(require_permission("shipping.calculate"))],
)
async def calc_shipping(
    data: ShippingCalcRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """配送料を計算する。

    carrier='fedex' 指定時:
      - FedEx 認証情報が設定済みかつ origin_country_code が指定されていれば
        FedEx Rates API からライブ見積もりを取得（source='fedex_live'）
      - 未設定または API エラーの場合は live_error に明示エラーを返す
        （ADR-125 D5: 暗黙フォールバック禁止 — 静的値をライブと偽らない）

    carrier 未指定または fedex 以外:
      - 静的テーブルから計算（source='static'）
    """
    # ADR-125: FedEx ライブ見積もり分岐
    if data.carrier == "fedex":
        if not data.origin_country_code:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="carrier='fedex' 指定時は origin_country_code が必須です",
            )
        creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")
        if creds:
            live_results, live_error, rate_precision = await _try_fedex_live(
                creds=creds,
                tenant_id=tenant_id,
                destination_country_code=data.country_code,
                origin_country_code=data.origin_country_code,
                weight_kg=data.weight_kg,
                origin_postal_code=data.origin_postal_code,
                destination_postal_code=data.destination_postal_code,
            )
            return ShippingCalcResponse(
                results=live_results,
                cheapest=live_results[0] if live_results else None,
                live_error=live_error,
                rate_precision=rate_precision,
            )
        # FedEx 未連携 → static に落とさず未連携状態を明示返却（ADR-125 D5 + PO C1判断）
        # 静的早見表は他キャリア（DHL/ヤマト等）専用として維持する（ADR-125 D4）
        return ShippingCalcResponse(
            results=[],
            cheapest=None,
            live_error="FedEx が未連携です。キャリア連携設定でアカウントを接続してください",
        )

    results = await calculate_shipping_fee(db, data.country_code, data.weight_kg, data.carrier)
    cheapest = results[0] if results else None
    return ShippingCalcResponse(results=results, cheapest=cheapest)


# =========================================================================
# ヘルパー
# =========================================================================


def _build_dimensions(data: CreateShipmentRequest) -> Optional[dict]:
    """CreateShipmentRequest から dimensions_cm dict を組み立てる。"""
    if data.length_cm and data.width_cm and data.height_cm:
        return {
            "length": float(data.length_cm),
            "width": float(data.width_cm),
            "height": float(data.height_cm),
        }
    return None


# =========================================================================
# FedEx ラベル発行（ADR-128）
# =========================================================================


@router.post(
    "/shipping/shipments",
    response_model=CreateShipmentResponse,
    status_code=201,
    dependencies=[Depends(require_permission("shipping.manage"))],
)
async def create_fedex_shipment(
    data: CreateShipmentRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """FedEx Ship API でラベルを発行し、Google Drive に保存する。"""
    from app.services import fedex_ship, google_drive_oauth

    creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")
    if not creds or not creds.get("account_number"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="FedEx 認証情報またはアカウント番号が未設定です",
        )

    try:
        result = await asyncio.to_thread(
            fedex_ship.create_shipment,
            tenant_id=tenant_id,
            environment=creds["environment"],
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            account_number=creds["account_number"],
            shipper=data.shipper.model_dump(),
            recipient=data.recipient.model_dump(),
            service_type=data.service_type,
            weight_kg=data.weight_kg,
            dimensions_cm=_build_dimensions(data),
            customs_clearance=data.customs_clearance,
        )
    except FedExAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except FedExAPIError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Google Drive にアップロード
    filename = f"fedex_label_{result.tracking_number}.pdf"
    try:
        drive_result = await google_drive_oauth.upload_pdf(
            db, tenant_id, result.label_bytes, filename
        )
        label_url = drive_result.get("web_view_link", "")
    except Exception as e:  # noqa: BLE001
        logger.warning("[shipping] Google Drive アップロード失敗: %s", e)
        label_url = ""

    # order_shipping_details に記録
    surcharges_json = [
        {"description": s.description, "amount": float(s.amount), "currency": s.currency}
        for s in result.surcharges
    ]
    osd_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
    await db.execute(
        text(f"""
            UPDATE {osd_t}
            SET tracking_number = :tn,
                label_issued_at = NOW(),
                label_drive_url = :lurl,
                confirmed_shipping_fee = :fee,
                confirmed_currency = :cur,
                surcharges = :sc::jsonb
            WHERE order_id = :oid AND tenant_id = :tid
        """),
        {
            "tn": result.tracking_number,
            "lurl": label_url,
            "fee": result.confirmed_fee,
            "cur": result.confirmed_currency,
            "sc": json.dumps(surcharges_json),
            "oid": data.order_id,
            "tid": tenant_id,
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    return CreateShipmentResponse(
        order_id=data.order_id,
        tracking_number=result.tracking_number,
        label_drive_url=label_url,
        confirmed_shipping_fee=result.confirmed_fee,
        confirmed_currency=result.confirmed_currency,
        surcharges=[
            SurchargeDetail(
                description=s.description,
                amount=s.amount,
                currency=s.currency,
            )
            for s in result.surcharges
        ],
    )


# =========================================================================
# FedEx 集荷予約（ADR-128）
# =========================================================================


@router.post(
    "/shipping/pickups",
    response_model=CreatePickupResponse,
    status_code=201,
    dependencies=[Depends(require_permission("shipping.manage"))],
)
async def create_fedex_pickup(
    data: CreatePickupRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
):
    """FedEx Pickup API で集荷を予約する。"""
    from app.services import fedex_ship

    creds = await carrier_credentials.get_credentials(db, tenant_id, "fedex")
    if not creds or not creds.get("account_number"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="FedEx 認証情報またはアカウント番号が未設定です",
        )

    try:
        result = await asyncio.to_thread(
            fedex_ship.create_pickup,
            tenant_id=tenant_id,
            environment=creds["environment"],
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            account_number=creds["account_number"],
            pickup_address=data.pickup_address,
            ready_datetime=data.ready_datetime,
            company_close_time=data.company_close_time,
            carrier_code=data.carrier_code,
            package_count=data.package_count,
            total_weight_kg=data.total_weight_kg,
        )
    except FedExAuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except FedExAPIError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # order_shipping_details に集荷確認番号を記録
    osd_t = tenant_table_ref(db, tenant_id, "order_shipping_details")
    await db.execute(
        text(f"""
            UPDATE {osd_t}
            SET pickup_confirmation_code = :pcc,
                pickup_requested_at = NOW()
            WHERE order_id = :oid AND tenant_id = :tid
        """),
        {
            "pcc": result.confirmation_code,
            "oid": data.order_id,
            "tid": tenant_id,
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    return CreatePickupResponse(
        order_id=data.order_id,
        pickup_confirmation_code=result.confirmation_code,
        location_code=result.location_code,
    )
