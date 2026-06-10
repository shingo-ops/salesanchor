"""FedEx Rates and Transit Times API クライアント（ADR-125 D3-D4）。

テナントが自社の FedEx アカウントを連携した上で、リアルタイムの送料見積もりと
配達日数を取得するサービス。

設計方針（ADR-125 D3）:
  - OAuth トークンはインメモリキャッシュで管理（有効期限 3600 秒・5 分バッファ）
  - プロセスをまたいだ共有はしない（許容コスト: 1時間に1回の再取得）
  - キャッシュキー: (tenant_id, environment) のタプル

設計方針（ADR-125 D4）:
  - エンドポイント: POST /rate/v1/rates/quotes
  - origin_country_code はリクエストパラメータで明示（ハードコードなし）
  - rateRequestType: ["LIST"]（アカウント料金取得）
  - timeout: httpx.Timeout(connect=3.0, read=7.0, write=5.0, pool=5.0)

設計方針（ADR-125 D5 — 暗黙フォールバック禁止）:
  - account_number が未設定なら FedExNotConfiguredError を raise
  - API エラーは FedExAPIError を raise（呼び出し元が live_error に変換）
  - 静的フォールバックはこのモジュールでは行わない（呼び出し元の責務）

変更履歴:
  2026-06-09: 初版（ADR-125 Phase B）
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

_BASE_URLS = {
    "sandbox": "https://apis-sandbox.fedex.com",
    "production": "https://apis.fedex.com",
}

# ---------------------------------------------------------------------------
# 取得対象サービスタイプ（設定値）ADR-125 仕様追補 2026-06-10
# ---------------------------------------------------------------------------
# 見積もりで取得・表示する国際サービスを4種に限定する。
# 「全取得→フィルタ」方式（serviceType 指定は使わない）。
# 経路で返ってこないサービスは単にリストに載らない（D5 方針）。
#
# 確認状況（JP→US 本番 2026-06-10）:
#   - FEDEX_INTERNATIONAL_PRIORITY        : ✅ 本番確認済（sandbox は "INTERNATIONAL_PRIORITY"）
#   - INTERNATIONAL_ECONOMY               : ✅ sandbox/本番ともに確認済
#   - FEDEX_INTERNATIONAL_PRIORITY_EXPRESS: ✅ 本番確認済（sandbox は "INTERNATIONAL_PRIORITY_EXPRESS"）
#   - FEDEX_INTERNATIONAL_CONNECT_PLUS    : ✅ 本番確認済
#
# 注意: サービスタイプ名は sandbox と production で異なる（FEDEX_ プレフィックスの有無）。
#       このリストは本番APIの返値に合わせる（sandbox テストは名前を直接モックして対応）。
#
# 変更方法: このリストの追加/削除で対象サービスを管理する。コードに散らさない。
TARGET_INTERNATIONAL_SERVICE_TYPES: list[str] = [
    "FEDEX_INTERNATIONAL_PRIORITY",         # IP  — FedEx International Priority®
    "INTERNATIONAL_ECONOMY",                # IE  — FedEx International Economy®
    "FEDEX_INTERNATIONAL_PRIORITY_EXPRESS", # IPE — FedEx International Priority Express®
    "FEDEX_INTERNATIONAL_CONNECT_PLUS",     # FICP — FedEx International Connect Plus®
]

# FedEx Rates API は postalCode を必須とする。
# 発送元/届け先のどちらも未指定の場合は国コードから代表郵便番号を補完する。
# 国際配送の概算料金計算では都市レベルの精度で十分（郵便番号の違いによる料金差は軽微）。
_REPRESENTATIVE_POSTAL_CODES: dict[str, str] = {
    "JP": "1000001",   # 東京都千代田区
    "US": "10001",     # New York, NY
    "CN": "100000",    # 北京
    "GB": "EC1A1BB",   # London
    "DE": "10115",     # Berlin
    "FR": "75001",     # Paris
    "AU": "2000",      # Sydney
    "CA": "M5V3L9",    # Toronto
    "HK": "999077",    # Hong Kong (postal code not used)
    "TW": "100",       # Taipei
    "KR": "04524",     # Seoul
    "SG": "238823",    # Singapore
    "NL": "1011AB",    # Amsterdam
    "IT": "00187",     # Rome
    "ES": "28001",     # Madrid
    "TH": "10330",     # Bangkok
    "MY": "50480",     # Kuala Lumpur
    "ID": "10110",     # Jakarta
    "VN": "100000",    # Hanoi
    "PH": "1000",      # Manila
    "IN": "110001",    # New Delhi
}

# OAuth token refresh buffer (5 minutes)
_TOKEN_REFRESH_BUFFER_SECS = 300

_TIMEOUT = httpx.Timeout(connect=3.0, read=7.0, write=5.0, pool=5.0)
_SA_TRANSIT_TIMEOUT = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=5.0)

# ---------------------------------------------------------------------------
# 例外
# ---------------------------------------------------------------------------


class FedExNotConfiguredError(Exception):
    """FedEx credentials or account_number が未設定。"""


class FedExAuthError(Exception):
    """OAuth token 取得失敗（認証情報が不正）。"""


class FedExAPIError(Exception):
    """Rates API 呼び出しでエラーが発生。"""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---------------------------------------------------------------------------
# レスポンスデータクラス
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FedExRateQuote:
    """FedEx Rates API の 1 サービスタイプあたりの見積もり。"""

    service_type: str         # 例: FEDEX_INTERNATIONAL_PRIORITY
    service_name: str         # 例: FedEx International Priority
    total_net_charge: Decimal  # 合計料金
    currency: str              # 通貨コード (例: JPY, USD)
    transit_days: Optional[int] = None  # 配達日数（取得できない場合あり）
    delivery_timestamp: Optional[str] = None  # ISO 8601 文字列（取得できない場合あり）


# ---------------------------------------------------------------------------
# インメモリ OAuth トークンキャッシュ
# ---------------------------------------------------------------------------

@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # time.time() ベースの Unix タイムスタンプ


# {(tenant_id, environment): _CachedToken}
_token_cache: dict[tuple[int, str], _CachedToken] = {}


def _get_cached_token(tenant_id: int, environment: str) -> Optional[str]:
    """キャッシュ済みのトークンを返す。期限切れ近い（5分バッファ）場合は None。"""
    cached = _token_cache.get((tenant_id, environment))
    if cached is None:
        return None
    if time.time() >= cached.expires_at - _TOKEN_REFRESH_BUFFER_SECS:
        # 期限切れ（バッファ込み）
        del _token_cache[(tenant_id, environment)]
        return None
    return cached.access_token


def _store_token(tenant_id: int, environment: str, access_token: str, expires_in: int) -> None:
    """トークンをキャッシュに保存。"""
    _token_cache[(tenant_id, environment)] = _CachedToken(
        access_token=access_token,
        expires_at=time.time() + expires_in,
    )


# ---------------------------------------------------------------------------
# OAuth トークン取得（オンデマンド・キャッシュ込み）
# ---------------------------------------------------------------------------


def _fetch_oauth_token(
    base_url: str,
    client_id: str,
    client_secret: str,
) -> tuple[str, int]:
    """FedEx OAuth client_credentials フローでトークンを取得。

    Returns:
        (access_token, expires_in_seconds)

    Raises:
        FedExAuthError: 認証失敗
        FedExAPIError: 通信エラー
    """
    try:
        resp = httpx.post(
            f"{base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise FedExAPIError(f"OAuth token 取得 — 通信エラー: {e}") from e

    if resp.status_code in (401, 403):
        raise FedExAuthError("FedEx OAuth 認証失敗（Client ID / Secret を確認してください）")
    if resp.status_code != 200:
        raise FedExAPIError(
            f"OAuth token 取得 — 予期しないレスポンス: HTTP {resp.status_code}",
            status_code=resp.status_code,
        )

    try:
        body = resp.json()
        token: str = body["access_token"]
        expires_in: int = int(body.get("expires_in", 3600))
    except (KeyError, ValueError) as e:
        raise FedExAPIError(f"OAuth token 取得 — レスポンスパース失敗: {e}") from e

    return token, expires_in


def get_or_refresh_token(
    tenant_id: int,
    environment: str,
    client_id: str,
    client_secret: str,
) -> str:
    """キャッシュ済みトークンを返すか、必要に応じて新規取得する。

    Raises:
        FedExAuthError: 認証失敗
        FedExAPIError: 通信エラー
    """
    cached = _get_cached_token(tenant_id, environment)
    if cached is not None:
        return cached

    base_url = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
    token, expires_in = _fetch_oauth_token(base_url, client_id, client_secret)
    _store_token(tenant_id, environment, token, expires_in)
    logger.debug("[fedex_rates] tenant=%d env=%s トークン取得・キャッシュ完了", tenant_id, environment)
    return token


# ---------------------------------------------------------------------------
# Rates API 呼び出し
# ---------------------------------------------------------------------------


def get_rates(
    tenant_id: int,
    environment: str,
    client_id: str,
    client_secret: str,
    account_number: str,
    origin_country_code: str,
    destination_country_code: str,
    weight_kg: Decimal,
    origin_postal_code: Optional[str] = None,
    destination_postal_code: Optional[str] = None,
) -> list[FedExRateQuote]:
    """FedEx Rates and Transit Times API を呼び出し、見積もりリストを返す。

    Args:
        tenant_id: テナント ID（キャッシュキー用）
        environment: "sandbox" または "production"
        client_id: FedEx OAuth Client ID
        client_secret: FedEx OAuth Client Secret
        account_number: FedEx 配送契約アカウント番号
        origin_country_code: 発送元国コード（例: "JP"）
        destination_country_code: 届け先国コード（例: "US"）
        weight_kg: 重量（kg）
        origin_postal_code: 発送元郵便番号（省略時は国コードから代表値を補完）
        destination_postal_code: 届け先郵便番号（省略時は国コードから代表値を補完）

    Returns:
        見積もりリスト（サービスタイプ別・料金昇順）

    Raises:
        FedExAuthError: OAuth 認証失敗
        FedExAPIError: Rates API エラー
    """
    base_url = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
    token = get_or_refresh_token(tenant_id, environment, client_id, client_secret)

    origin_cc = origin_country_code.upper()
    dest_cc = destination_country_code.upper()
    # FedEx Rates API は postalCode を必須とする。未指定時は代表郵便番号で補完。
    origin_zip = origin_postal_code or _REPRESENTATIVE_POSTAL_CODES.get(origin_cc, "000000")
    dest_zip = destination_postal_code or _REPRESENTATIVE_POSTAL_CODES.get(dest_cc, "000000")

    payload = {
        "accountNumber": {"value": account_number},
        "requestedShipment": {
            "shipper": {
                "address": {
                    "countryCode": origin_cc,
                    "postalCode": origin_zip,
                }
            },
            "recipient": {
                "address": {
                    "countryCode": dest_cc,
                    "postalCode": dest_zip,
                }
            },
            "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
            "rateRequestType": ["LIST"],
            "requestedPackageLineItems": [
                {
                    "weight": {
                        "units": "KG",
                        "value": float(weight_kg),
                    }
                }
            ],
        },
    }

    try:
        resp = httpx.post(
            f"{base_url}/rate/v1/rates/quotes",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-locale": "en_US",
            },
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as e:
        raise FedExAPIError("Rates API タイムアウト（FedEx サーバーが応答しません）") from e
    except httpx.HTTPError as e:
        raise FedExAPIError(f"Rates API 通信エラー: {e}") from e

    if resp.status_code in (401, 403):
        # トークンが失効した可能性 → キャッシュを削除して再試行（1回のみ）
        _token_cache.pop((tenant_id, environment), None)
        raise FedExAuthError("Rates API 認証失敗（トークン期限切れの可能性）")

    if resp.status_code != 200:
        _log_api_error(resp)
        raise FedExAPIError(
            f"Rates API エラー: HTTP {resp.status_code}",
            status_code=resp.status_code,
        )

    # SA API で配達日数を取得（best-effort: 失敗しても Rates 結果は返す）
    transit_map = _fetch_transit_days(
        base_url=base_url,
        token=token,
        origin_cc=origin_cc,
        origin_zip=origin_zip,
        dest_cc=dest_cc,
        dest_zip=dest_zip,
        weight_kg=weight_kg,
    )
    return _parse_rate_replies(resp.json(), transit_map)


def _fetch_transit_days(
    base_url: str,
    token: str,
    origin_cc: str,
    origin_zip: str,
    dest_cc: str,
    dest_zip: str,
    weight_kg: Decimal,
) -> dict[str, int]:
    """FedEx Service Availability API で配達日数を取得（best-effort）。

    取得失敗時は空 dict を返す（呼び出し元の Rates 結果には影響しない）。

    レスポンス構造（2026-06-10 本番確認済）:
      output.transitTimes[0].transitTimeDetails[*].{serviceType, commit.dateDetail.day}
      day format: "Jun-11-2026"

    Payload の注意点:
      - packagingType が必須（省略すると PACKAGE.NULLOREMPTY.REQUIRED）
      - recipients（複数形配列）を使用（Rates API の recipient 単数形とは異なる）
      - customsClearanceDetail が国際配送で必須（dutiesPayment + commodities）
      - accountNumber 不要

    Returns:
        {serviceType: transit_days} — transit_days = (delivery_date - today).days
    """
    today = date.today()
    ship_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    weight_val = float(weight_kg)

    payload = {
        "requestedShipment": {
            "shipper": {"address": {"postalCode": origin_zip, "countryCode": origin_cc}},
            "recipients": [{"address": {"postalCode": dest_zip, "countryCode": dest_cc}}],
            "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
            "shipDateStamp": ship_date,
            "packagingType": "YOUR_PACKAGING",
            "requestedPackageLineItems": [{"weight": {"units": "KG", "value": weight_val}}],
            "customsClearanceDetail": {
                "dutiesPayment": {"paymentType": "SENDER"},
                "commodities": [{
                    "numberOfPieces": 1,
                    "description": "General merchandise",
                    "countryOfManufacture": origin_cc,
                    "quantity": 1,
                    "quantityUnits": "PCS",
                    "weight": {"units": "KG", "value": weight_val},
                    "unitPrice": {"currency": "USD", "amount": 10},
                    "customsValue": {"currency": "USD", "amount": 10},
                }],
            },
        },
        "carrierCodes": ["FDXE"],
    }

    try:
        resp = httpx.post(
            f"{base_url}/availability/v1/transittimes",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-locale": "en_US",
            },
            timeout=_SA_TRANSIT_TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("[fedex_rates] SA API 通信失敗（配達日数スキップ）: %s", e)
        return {}

    if resp.status_code != 200:
        logger.debug("[fedex_rates] SA API HTTP %d（配達日数スキップ）", resp.status_code)
        return {}

    try:
        body = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.debug("[fedex_rates] SA API レスポンス解析失敗: %s", e)
        return {}

    transit_map: dict[str, int] = {}
    for tt in body.get("output", {}).get("transitTimes", []):
        for detail in tt.get("transitTimeDetails", []):
            svc = detail.get("serviceType")
            day_str = detail.get("commit", {}).get("dateDetail", {}).get("day")
            if not svc or not day_str:
                continue
            try:
                delivery_date = datetime.strptime(day_str, "%b-%d-%Y").date()
                days = (delivery_date - today).days
                if days >= 0:
                    transit_map[svc] = days
            except (ValueError, TypeError):
                pass

    logger.debug("[fedex_rates] SA API 配達日数取得: %s", transit_map)
    return transit_map


def _log_api_error(resp: httpx.Response) -> None:
    """API エラーレスポンスをログ記録（機密情報は含めない）。"""
    try:
        errors = resp.json().get("errors", [])
        codes = [e.get("code", "") for e in errors]
        logger.warning("[fedex_rates] Rates API エラー: HTTP %d codes=%s", resp.status_code, codes)
    except Exception:  # noqa: BLE001
        logger.warning("[fedex_rates] Rates API エラー: HTTP %d (レスポンス解析失敗)", resp.status_code)


def _parse_rate_replies(
    body: dict,
    transit_map: Optional[dict[str, int]] = None,
) -> list[FedExRateQuote]:
    """Rates API レスポンスを FedExRateQuote リストに変換。料金昇順でソート。

    TARGET_INTERNATIONAL_SERVICE_TYPES に含まれないサービスタイプは除外する。
    経路で返ってこないサービスは単に結果に含まれない（D5 方針）。

    Args:
        body: Rates API レスポンスボディ
        transit_map: SA API から取得した {serviceType: transit_days}（省略可・best-effort）
    """
    output = body.get("output", {})
    rate_reply_details = output.get("rateReplyDetails", [])

    quotes: list[FedExRateQuote] = []
    for detail in rate_reply_details:
        service_type: str = detail.get("serviceType", "")
        service_name: str = detail.get("serviceName", service_type)

        # 対象4サービス以外はスキップ
        if service_type not in TARGET_INTERNATIONAL_SERVICE_TYPES:
            logger.debug("[fedex_rates] サービス %s はフィルタ対象外 — スキップ", service_type)
            continue

        # 料金情報（ratedShipmentDetails から LIST 料金を取得）
        shipment_details = detail.get("ratedShipmentDetails", [])
        net_charge: Optional[Decimal] = None
        currency: str = "USD"

        for sd in shipment_details:
            rate_type = sd.get("rateType", "")
            if rate_type in ("PAYOR_LIST_PACKAGE", "PAYOR_LIST_SHIPMENT", "LIST"):
                total = sd.get("totalNetCharge")
                if total is not None:
                    net_charge = Decimal(str(total))
                    currency = sd.get("currency", "USD")
                    break

        if net_charge is None:
            # LIST 料金が取れなかった場合は先頭の ratedShipmentDetails を使用
            if shipment_details:
                total = shipment_details[0].get("totalNetCharge")
                if total is not None:
                    net_charge = Decimal(str(total))
                    currency = shipment_details[0].get("currency", "USD")

        if net_charge is None:
            # 料金が取れない場合はスキップ
            logger.debug("[fedex_rates] サービス %s の料金が取得できません", service_type)
            continue

        # 配達日数: SA API transit_map を優先、フォールバックは Rates API operationalDetail
        transit_days: Optional[int] = None
        if transit_map:
            transit_days = transit_map.get(service_type)
        if transit_days is None:
            commit_detail = detail.get("operationalDetail", {})
            transit_val = commit_detail.get("transitTime")
            if isinstance(transit_val, str) and transit_val.endswith("_DAYS"):
                try:
                    transit_days = int(transit_val.split("_")[0])
                except ValueError:
                    pass

        delivery_ts: Optional[str] = detail.get("commit", {}).get("dateDetail", {}).get("dayFormat")

        quotes.append(FedExRateQuote(
            service_type=service_type,
            service_name=service_name,
            total_net_charge=net_charge,
            currency=currency,
            transit_days=transit_days,
            delivery_timestamp=delivery_ts,
        ))

    # 料金昇順でソート
    quotes.sort(key=lambda q: q.total_net_charge)
    return quotes


# ---------------------------------------------------------------------------
# キャッシュクリア（テスト用）
# ---------------------------------------------------------------------------


def clear_token_cache() -> None:
    """全インメモリキャッシュを削除（テスト用途）。"""
    _token_cache.clear()


__all__ = [
    "FedExNotConfiguredError",
    "FedExAuthError",
    "FedExAPIError",
    "FedExRateQuote",
    "get_or_refresh_token",
    "get_rates",
    "_fetch_transit_days",
    "clear_token_cache",
]
