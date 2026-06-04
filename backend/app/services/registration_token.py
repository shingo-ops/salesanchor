"""
顧客登録トークン生成・検証サービス（ADR-SA-03）。

担当者がリードに個別登録リンクを発行し、顧客が自分で住所・連絡先を登録する仕組み。
テナントはトークン（HMAC-SHA256 署名）が決める——フォーム入力ではなく構造で分離。

トークン生成:
  1. os.urandom(32) でランダムバイト列を生成
  2. hex エンコードして raw token（URL に載せる文字列）を作成
  3. HMAC-SHA256(secret, raw_token) で hash を計算し DB に保存

検証:
  - 署名一致 / 期限切れ / 単回使用 の 3 点チェック
  - テナント ID・リード ID はトークンから確定（リクエストボディから取らない）
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 環境変数からトークン署名用シークレットを取得
# 本番では必ず設定すること
_TOKEN_SECRET = os.getenv("REGISTRATION_TOKEN_SECRET", "dev-registration-secret")

# デフォルト有効期限: 7 日
DEFAULT_EXPIRY_DAYS = 7


def _compute_hash(raw_token: str) -> str:
    """raw token から HMAC-SHA256 hash を計算する。"""
    return hmac.new(
        _TOKEN_SECRET.encode(),
        raw_token.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_token() -> tuple[str, str]:
    """ランダムトークンを生成し、(raw_token, token_hash) を返す。

    raw_token: URL に載せる文字列（顧客に送る）
    token_hash: DB に保存する HMAC-SHA256 の hex
    """
    raw_token = os.urandom(32).hex()
    token_hash = _compute_hash(raw_token)
    return raw_token, token_hash


async def create_registration_token(
    db: AsyncSession,
    *,
    tenant_id: int,
    lead_id: int,
    created_by: int,
    token_type: str = "register",
    expiry_days: int = DEFAULT_EXPIRY_DAYS,
) -> tuple[str, datetime]:
    """登録トークンを DB に保存し、(raw_token, expires_at) を返す。

    担当者が呼び出す。raw_token を含む URL を顧客に送付する。
    """
    raw_token, token_hash = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

    await db.execute(
        text("""
            INSERT INTO public.registration_tokens
                (tenant_id, lead_id, token_hash, type, expires_at, created_by)
            VALUES
                (:tenant_id, :lead_id, :token_hash, :type, :expires_at, :created_by)
        """),
        {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "token_hash": token_hash,
            "type": token_type,
            "expires_at": expires_at,
            "created_by": created_by,
        },
    )

    logger.info(
        "登録トークン発行 (tenant=%d, lead=%d, type=%s, expires=%s)",
        tenant_id, lead_id, token_type, expires_at.isoformat(),
    )
    return raw_token, expires_at


async def verify_token(
    db: AsyncSession,
    raw_token: str,
) -> Optional[dict]:
    """raw token を検証し、有効なら token 情報を返す。

    検証項目:
      1. 署名一致（HMAC-SHA256 hash が DB に存在する）
      2. 期限切れでない
      3. 未使用（used_at IS NULL）

    Returns:
        有効時: {
            "id": UUID,
            "tenant_id": int,
            "lead_id": int,
            "type": str,
            "expires_at": datetime,
        }
        無効時: None
    """
    token_hash = _compute_hash(raw_token)

    result = await db.execute(
        text("""
            SELECT id, tenant_id, lead_id, type, expires_at, used_at
            FROM public.registration_tokens
            WHERE token_hash = :hash
        """),
        {"hash": token_hash},
    )
    row = result.mappings().first()

    if not row:
        logger.warning("登録トークン検証失敗: hash が見つからない")
        return None

    if row["used_at"] is not None:
        logger.warning("登録トークン検証失敗: 使用済み (id=%s)", row["id"])
        return None

    if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        logger.warning("登録トークン検証失敗: 期限切れ (id=%s)", row["id"])
        return None

    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "lead_id": row["lead_id"],
        "type": str(row["type"]),
        "expires_at": row["expires_at"],
    }


async def mark_token_used(db: AsyncSession, token_id: str) -> None:
    """トークンを使用済みにマークする。"""
    await db.execute(
        text("""
            UPDATE public.registration_tokens
            SET used_at = NOW()
            WHERE id = :id
        """),
        {"id": token_id},
    )
    logger.info("登録トークン使用済みにマーク (id=%s)", token_id)
