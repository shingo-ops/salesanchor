"""FedEx Trade Documents Upload API クライアント（ADR-137）。

Upload Image（レターヘッド/署名）専用サービス。
出荷ごとの自前書類（COMMERCIAL_INVOICE 等）は docId を返すが DB 保存しない（poka-yoke）。

API 区分（Shingo C-Q1確認 2026-06-18）:
  - Upload Image → imageIndex（再利用可・無期限）→ Ship 時に customerImageUsages で参照
  - Upload Document/Multiple/Encoded → docId（使い捨て）→ Ship 時に etdDetail.attachedDocuments で参照

変更履歴:
  2026-06-18: 初版（ADR-137 ETD骨格）
"""
from __future__ import annotations

import logging
from typing import Literal

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.fedex_rates import (
    _BASE_URLS,
    FedExAPIError,
    FedExAuthError,
    get_or_refresh_token,
)

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=3.0, read=30.0, write=15.0, pool=5.0)

# TODO(C-Q1): 正確なパスは Portal の Trade Documents Upload API リファレンスから取得。
# 現在は placeholder。G3（APIキーへの追加）完了後に Sandbox 疎通で確認する。
_UPLOAD_IMAGE_PATH = "/documents/v1/etds/upload/image"  # TODO(C-Q1): Portal確認必須

# LETTERHEAD/SIGNATURE のみ DB 永続化対象（Eva Q3 poka-yoke）
# 出荷ごとの書類 docId は本モジュールでは扱わない
ImageTypeLiteral = Literal["LETTERHEAD", "SIGNATURE"]
PERSISTENT_IMAGE_TYPES: frozenset[str] = frozenset({"LETTERHEAD", "SIGNATURE"})

# 画像仕様（Shingo C-Q1確認 2026-06-18）
IMAGE_CONSTRAINTS: dict[str, dict[str, object]] = {
    "LETTERHEAD": {"width": 700, "height": 50, "max_bytes": 5 * 1024 * 1024, "formats": ("GIF", "PNG")},
    "SIGNATURE":  {"width": 240, "height": 25, "max_bytes": 5 * 1024 * 1024, "formats": ("GIF", "PNG")},
}


def _guard_persistent_only(image_type: str) -> None:
    """出荷ごとの書類 docId を誤って永続化しようとしたら例外（S5 poka-yoke）。

    Eva Q3: レターヘッド/署名のみ DB 保存。出荷ごとの自前書類は使い捨て。
    """
    if image_type not in PERSISTENT_IMAGE_TYPES:
        raise ValueError(
            f"image_type={image_type!r} は使い捨て書類です。"
            "fedex_etd_images への保存禁止（ADR-137 J1 / Eva Q3 poka-yoke）"
        )


def upload_etd_image(
    tenant_id: int,
    environment: str,
    image_type: ImageTypeLiteral,
    image_bytes: bytes,
    client_id: str,
    client_secret: str,
) -> str:
    """Trade Documents Upload API で画像をアップロードし imageIndex を返す。

    Args:
        tenant_id: テナントID（ログ用）
        environment: "sandbox" | "production"
        image_type: "LETTERHEAD" | "SIGNATURE"
        image_bytes: 画像バイナリ（GIF/PNG・サイズ制限は呼び出し元で検証）
        client_id: FedEx API クライアントID
        client_secret: FedEx API クライアントシークレット

    Returns:
        imageIndex（文字列）。docId ではない。

    Raises:
        FedExAuthError: OAuth 認証失敗
        FedExAPIError: Upload API エラー
        ValueError: image_type が PERSISTENT_IMAGE_TYPES 外（poka-yoke）
    """
    _guard_persistent_only(image_type)

    base_url = _BASE_URLS.get(environment, _BASE_URLS["sandbox"])
    token = get_or_refresh_token(tenant_id, environment, client_id, client_secret)

    # TODO(C-Q1): リクエスト形式（multipart/form-data か JSON base64 か）をPortal確認後に確定。
    # 現在は multipart/form-data を仮定。
    try:
        resp = httpx.post(
            f"{base_url}{_UPLOAD_IMAGE_PATH}",
            files={"image": image_bytes},
            data={"imageType": image_type},
            headers={
                "Authorization": f"Bearer {token}",
                "X-locale": "en_US",
            },
            timeout=_TIMEOUT,
        )
    except httpx.TimeoutException as e:
        raise FedExAPIError("Trade Documents Upload API タイムアウト") from e
    except httpx.HTTPError as e:
        raise FedExAPIError(f"Trade Documents Upload API 通信エラー: {e}") from e

    if resp.status_code in (401, 403):
        raise FedExAuthError("Trade Documents Upload API 認証失敗（トークン期限切れの可能性）")

    if resp.status_code not in (200, 201):
        try:
            errors = resp.json().get("errors", [])
            codes = [e.get("code", "") for e in errors]
        except Exception:  # noqa: BLE001
            codes = []
        logger.warning(
            "[fedex_etd] Upload Image エラー: HTTP %d codes=%s tenant_id=%d",
            resp.status_code, codes, tenant_id,
        )
        raise FedExAPIError(
            f"Trade Documents Upload API エラー: HTTP {resp.status_code}",
            status_code=resp.status_code,
        )

    # TODO(C-Q1): レスポンスの imageIndex フィールド名をPortal確認後に確定。
    try:
        data = resp.json()
        image_index: str = data["imageIndex"]  # TODO(C-Q1): フィールド名確認
    except (KeyError, Exception) as e:
        raise FedExAPIError(f"Trade Documents Upload API レスポンス解析失敗: {e}") from e

    logger.info(
        "[fedex_etd] Upload Image 成功: tenant_id=%d image_type=%s env=%s imageIndex=%s",
        tenant_id, image_type, environment, image_index,
    )
    return image_index


async def upsert_etd_image(
    db: AsyncSession,
    tenant_id: int,
    image_type: str,
    environment: str,
    image_index: str,
) -> None:
    """fedex_etd_images に imageIndex を upsert（同一テナント×種別×環境は上書き）。

    Eva Q3/Q4: 無期限・再利用 → 再アップロード時は上書き。履歴管理不要。
    """
    _guard_persistent_only(image_type)

    await db.execute(
        text("""
            INSERT INTO public.fedex_etd_images
                (tenant_id, image_type, environment, fedex_image_index, updated_at)
            VALUES
                (:tid, :itype, :env, :idx, NOW())
            ON CONFLICT (tenant_id, image_type, environment)
            DO UPDATE SET
                fedex_image_index = EXCLUDED.fedex_image_index,
                updated_at = NOW()
        """),
        {
            "tid": tenant_id,
            "itype": image_type,
            "env": environment,
            "idx": image_index,
        },
    )


async def get_etd_images(
    db: AsyncSession,
    tenant_id: int,
    environment: str,
) -> dict[str, str]:
    """登録済みの ETD 画像 imageIndex を返す。

    Returns:
        {"LETTERHEAD": "...", "SIGNATURE": "..."} のような辞書。
        未登録のキーは含まれない。
    """
    result = await db.execute(
        text("""
            SELECT image_type, fedex_image_index
            FROM public.fedex_etd_images
            WHERE tenant_id = :tid AND environment = :env
        """),
        {"tid": tenant_id, "env": environment},
    )
    return {row.image_type: row.fedex_image_index for row in result}
