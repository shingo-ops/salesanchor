"""FedEx Ship API / Pickup API クライアント（ADR-128）。
自社 Shipper 組織（793322011）でのラベル発行と集荷予約。
認証は fedex_rates.get_or_refresh_token() を共用。

変更履歴:
  2026-06-11: 初版（ADR-128）
"""
from __future__ import annotations

import os
import base64
import logging
from decimal import Decimal
from typing import Optional

import httpx

from app.services.carrier_adapter import PickupResult, ShipmentResult, SurchargeDetail
from app.services.fedex_rates import (
    _BASE_URLS,
    FedExAPIError,
    FedExAuthError,
    get_or_refresh_token,
)

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=3.0, read=15.0, write=10.0, pool=5.0)


def _log_api_error(resp: httpx.Response, context: str) -> None:
    """API エラーレスポンスをログ記録（機密情報は含めない）。"""
    try:
        errors = resp.json().get("errors", [])
        codes = [e.get("code", "") for e in errors]
        logger.warning("[fedex_ship] %s エラー: HTTP %d codes=%s", context, resp.status_code, codes)
    except Exception:  # noqa: BLE001
        logger.warning("[fedex_ship] %s エラー: HTTP %d (レスポンス解析失敗)", context, resp.status_code)


def _parse_surcharges(surcharge_list: list[dict]) -> list[SurchargeDetail]:
    """FedEx API の surCharges リストを SurchargeDetail リストに変換する。"""
    result: list[SurchargeDetail] = []
    for s in surcharge_list:
        desc = s.get("description") or s.get("surchargeKey", "")
        amount_raw = s.get("amount")
        currency = s.get("currency", "USD")
        if amount_raw is None:
            continue
        result.append(SurchargeDetail(
            description=desc,
            amount=Decimal(str(amount_raw)),
            currency=currency,
        ))
    return result


# J3 dormant フラグ（ADR-137）
# FE / BE ともに FEDEX_ETD_ENABLED で切り替える。
# 既定は false で、CTS回答（C-Q6）確定後に go-live 時だけ true にする。
_ETD_ENABLED: bool = os.getenv("FEDEX_ETD_ENABLED", "false").strip().lower() == "true"


def create_shipment(
    tenant_id: int,
    environment: str,
    client_id: str,
    client_secret: str,
    account_number: str,
    shipper: dict,
    recipient: dict,
    service_type: str,
    weight_kg: Decimal,
    packaging_type: str = "YOUR_PACKAGING",
    pickup_type: str = "DROPOFF_AT_FEDEX_LOCATION",
    label_image_type: str = "PDF",
    label_stock_type: str = "PAPER_85X11_TOP_HALF_LABEL",
    dimensions_cm: Optional[dict] = None,
    customs_clearance: Optional[dict] = None,
    etd_image_indices: Optional[dict] = None,
) -> ShipmentResult:
    """FedEx Ship API でラベルを発行する。

    Args:
        tenant_id: テナント ID（トークンキャッシュキー用）
        environment: "sandbox" または "production"
        client_id: FedEx OAuth Client ID
        client_secret: FedEx OAuth Client Secret
        account_number: FedEx 配送契約アカウント番号
        shipper: 発送者情報 {"contact": {...}, "address": {...}}
        recipient: 受取人情報 {"contact": {...}, "address": {...}}
        service_type: サービスタイプ（例: FEDEX_INTERNATIONAL_PRIORITY）
        weight_kg: 重量（kg）
        packaging_type: 梱包タイプ
        pickup_type: ピックアップタイプ
        label_image_type: ラベル画像タイプ（PDF / PNG / ZPLII 等）
        label_stock_type: ラベルストックタイプ（ZPLII 用に STOCK_4X6 等）
        dimensions_cm: 寸法 {"length": float, "width": float, "height": float}（任意）
        customs_clearance: 国際便用関税情報（任意）

    Returns:
        ShipmentResult

    Raises:
        FedExAuthError: OAuth 認証失敗
        FedExAPIError: Ship API エラー
    """
    base_url = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
    token = get_or_refresh_token(tenant_id, environment, client_id, client_secret)

    pkg_item: dict = {
        "weight": {"units": "KG", "value": float(weight_kg)},
    }
    if dimensions_cm:
        pkg_item["dimensions"] = {
            "length": float(dimensions_cm["length"]),
            "width": float(dimensions_cm["width"]),
            "height": float(dimensions_cm["height"]),
            "units": "CM",
        }

    requested_shipment: dict = {
        "shipper": shipper,
        "recipients": [recipient],
        "serviceType": service_type,
        "packagingType": packaging_type,
        "pickupType": pickup_type,
        "shippingChargesPayment": {"paymentType": "SENDER"},
        "labelSpecification": {
            "imageType": label_image_type,
            "labelFormatType": "COMMON2D",
            "labelStockType": label_stock_type,
        },
        "requestedPackageLineItems": [pkg_item],
    }
    if customs_clearance:
        requested_shipment["customsClearanceDetail"] = customs_clearance

    # J3 dormant: ETD customerImageUsages フック（ADR-137 S4）
    # _ETD_ENABLED=False の間は本番フローに影響しない。
    # TODO(C-Q6/CTS): stampType(INCLUSIVE/EXCLUSIVE) / requestedDocumentCopies /
    #                  workflow(ETDPreShipment/PostShipment) / customerImageUsages 構造 確定後に実装。
    if _ETD_ENABLED and etd_image_indices:
        requested_shipment["shippingDocumentSpecification"] = {
            # TODO(C-Q6): 正確な customerImageUsages 構造を CTS 回答後に埋める
            "customerImageUsages": etd_image_indices,
        }

    payload: dict = {
        "labelResponseOptions": "LABEL",
        "accountNumber": {"value": account_number},
        "requestedShipment": requested_shipment,
    }

    try:
        resp = httpx.post(
            f"{base_url}/ship/v1/shipments",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-locale": "en_US",
            },
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as e:
        raise FedExAPIError("Ship API タイムアウト（FedEx サーバーが応答しません）") from e
    except httpx.HTTPError as e:
        raise FedExAPIError(f"Ship API 通信エラー: {e}") from e

    if resp.status_code in (401, 403):
        raise FedExAuthError("Ship API 認証失敗（トークン期限切れの可能性）")

    if resp.status_code not in (200, 201):
        _log_api_error(resp, "Ship API")
        raise FedExAPIError(
            f"Ship API エラー: HTTP {resp.status_code}",
            status_code=resp.status_code,
        )

    try:
        body = resp.json()
        txn = body["output"]["transactionShipments"][0]
        tracking_number: str = txn["masterTrackingNumber"]

        encoded_label: str = txn["pieceResponses"][0]["packageDocuments"][0]["encodedLabel"]
        # サイズ上限チェック（Base64 で 10MB ≒ 実データ約 7.5MB が上限）
        _MAX_LABEL_B64_BYTES = 10 * 1024 * 1024
        if len(encoded_label) > _MAX_LABEL_B64_BYTES:
            raise FedExAPIError(
                f"ラベルサイズが上限（10MB）を超えています: {len(encoded_label)} bytes"
            )
        label_bytes = base64.b64decode(encoded_label)

        rate_details = txn.get("shipmentRating", {}).get("shipmentRateDetails", [])
        if rate_details:
            rd = rate_details[0]
            confirmed_fee = Decimal(str(rd.get("totalNetCharge", "0")))
            confirmed_currency = rd.get("currency", "USD")
            surcharges = _parse_surcharges(rd.get("surCharges", []))
        else:
            confirmed_fee = Decimal("0")
            confirmed_currency = "USD"
            surcharges = []

    except (KeyError, IndexError, ValueError) as e:
        raise FedExAPIError(f"Ship API レスポンスパース失敗: {e}") from e

    return ShipmentResult(
        tracking_number=tracking_number,
        label_bytes=label_bytes,
        confirmed_fee=confirmed_fee,
        confirmed_currency=confirmed_currency,
        surcharges=surcharges,
    )


def create_pickup(
    tenant_id: int,
    environment: str,
    client_id: str,
    client_secret: str,
    account_number: str,
    pickup_address: dict,
    ready_datetime: str,
    company_close_time: str,
    carrier_code: str = "FDXE",
    package_count: int = 1,
    total_weight_kg: Decimal = Decimal("1.0"),
) -> PickupResult:
    """FedEx Pickup API で集荷を予約する。

    Args:
        tenant_id: テナント ID（トークンキャッシュキー用）
        environment: "sandbox" または "production"
        client_id: FedEx OAuth Client ID
        client_secret: FedEx OAuth Client Secret
        account_number: FedEx 配送契約アカウント番号
        pickup_address: 集荷先住所 {"contact": {...}, "address": {...}}
        ready_datetime: 集荷準備完了日時（ISO 8601）
        company_close_time: 会社の営業終了時刻（"HH:MM" または "HH:MM:SS" 形式）
        carrier_code: キャリアコード（FDXE=Express, FDXG=Ground）
        package_count: 荷物数
        total_weight_kg: 総重量（kg）

    Returns:
        PickupResult

    Raises:
        FedExAuthError: OAuth 認証失敗
        FedExAPIError: Pickup API エラー
    """
    base_url = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
    token = get_or_refresh_token(tenant_id, environment, client_id, client_secret)

    # FedEx API v1 は customerCloseTime を HH:MM:SS 形式で要求する
    close_time = company_close_time if len(company_close_time) == 8 else f"{company_close_time}:00"

    # associatedAccountNumberType はキャリアコードに対応させる
    account_number_type = "FEDEX_EXPRESS" if carrier_code == "FDXE" else "FEDEX_GROUND"

    payload: dict = {
        "associatedAccountNumber": {"value": account_number},
        "carrierCode": carrier_code,
        "associatedAccountNumberType": account_number_type,
        "originDetail": {
            "pickupAddressType": "ACCOUNT",
            "pickupLocation": {
                "contact": pickup_address["contact"],
                "address": pickup_address["address"],
                "accountNumber": {"value": account_number},
                "deliveryInstructions": "",
            },
            "packageLocation": "FRONT",
            "readyDateTimestamp": ready_datetime,
            "customerCloseTime": close_time,
        },
        "totalWeight": {"units": "KG", "value": float(total_weight_kg)},
        "packageCount": package_count,
    }

    try:
        resp = httpx.post(
            f"{base_url}/pickup/v1/pickups",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-locale": "en_US",
            },
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as e:
        raise FedExAPIError("Pickup API タイムアウト（FedEx サーバーが応答しません）") from e
    except httpx.HTTPError as e:
        raise FedExAPIError(f"Pickup API 通信エラー: {e}") from e

    if resp.status_code in (401, 403):
        raise FedExAuthError("Pickup API 認証失敗（トークン期限切れの可能性）")

    if resp.status_code not in (200, 201):
        _log_api_error(resp, "Pickup API")
        raise FedExAPIError(
            f"Pickup API エラー: HTTP {resp.status_code}",
            status_code=resp.status_code,
        )

    try:
        body = resp.json()
        output = body["output"]
        confirmation_code: str = output["pickupConfirmationCode"]
        location_code: Optional[str] = output.get("location")
    except (KeyError, ValueError) as e:
        raise FedExAPIError(f"Pickup API レスポンスパース失敗: {e}") from e

    return PickupResult(
        confirmation_code=confirmation_code,
        location_code=location_code,
    )


def check_pickup_availability(
    tenant_id: int,
    environment: str,
    client_id: str,
    client_secret: str,
    account_number: str,
    pickup_address: dict,
    pickup_date: str,
    carrier_code: str = "FDXE",
) -> dict:
    """FedEx Pickup Availability API で集荷可能日時・締切時刻を確認する。

    Args:
        tenant_id: テナント ID（トークンキャッシュキー用）
        environment: "sandbox" または "production"
        client_id: FedEx OAuth Client ID
        client_secret: FedEx OAuth Client Secret
        account_number: FedEx 配送契約アカウント番号
        pickup_address: 集荷先住所 {"contact": {...}, "address": {...}}
        pickup_date: 集荷希望日（YYYY-MM-DD）
        carrier_code: キャリアコード（FDXE=Express, FDXG=Ground）

    Returns:
        FedEx Pickup Options レスポンスをそのまま返す（UI が締切時刻等を表示するため）

    Raises:
        FedExAuthError: OAuth 認証失敗
        FedExAPIError: Pickup Availability API エラー
    """
    base_url = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
    token = get_or_refresh_token(tenant_id, environment, client_id, client_secret)

    payload: dict = {
        "associatedAccountNumber": {"value": account_number},
        "pickupAddress": pickup_address.get("address", {}),
        "pickupRequestType": ["SAME_DAY"],
        "dispatchDate": pickup_date,
        "packageCount": 1,
        "carrierCode": carrier_code,
    }

    try:
        resp = httpx.post(
            f"{base_url}/pickup/v1/pickupoptions",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-locale": "en_US",
            },
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as e:
        raise FedExAPIError("Pickup Options API タイムアウト（FedEx サーバーが応答しません）") from e
    except httpx.HTTPError as e:
        raise FedExAPIError(f"Pickup Options API 通信エラー: {e}") from e

    if resp.status_code in (401, 403):
        raise FedExAuthError("Pickup Options API 認証失敗（トークン期限切れの可能性）")

    if resp.status_code not in (200, 201):
        _log_api_error(resp, "Pickup Options API")
        raise FedExAPIError(
            f"Pickup Options API エラー: HTTP {resp.status_code}",
            status_code=resp.status_code,
        )

    try:
        return resp.json()
    except Exception as e:  # noqa: BLE001
        raise FedExAPIError(f"Pickup Options API レスポンスパース失敗: {e}") from e


__all__ = [
    "create_shipment",
    "create_pickup",
    "check_pickup_availability",
]
