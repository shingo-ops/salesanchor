"""
APIレート制限ミドルウェア（P2-2）。

認証済みユーザー: メールアドレス単位で 100回/分 を超えたら HTTP 429 を返す。
未認証リクエスト: IPアドレス単位で 60回/分 を超えたら HTTP 429 を返す。

Redis 不通時は制限を適用しない（fail-open）。
ヘルスチェック・静的ファイルは除外。
"""

import hashlib
import logging
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# 認証済みユーザー: 300回/分
# データの多い画面は 1 ページで 10〜20 リクエスト飛ぶため、数ページの遷移で
# 旧上限(100)に達し正規ユーザーが 429 でブロックされていた。内部 B2B CRM の
# 想定利用に合わせ 300 に引き上げる（不正利用の抑止は維持できる水準）。
AUTHED_RATE_LIMIT = 300
AUTHED_WINDOW_SEC = 60

# 未認証 IP: 60回/分（認証エンドポイントへの試行抑制）
UNAUTHED_RATE_LIMIT = 60
UNAUTHED_WINDOW_SEC = 60

# レート制限を適用しないパス
_SKIP_PATHS = ("/health", "/metrics", "/docs", "/openapi", "/static", "/api/health")


def _extract_bearer_token(auth_header: str | None) -> str | None:
    """Authorization headerからBearer tokenを抽出する。

    JWT payloadは署名検証前に攻撃者が任意生成できるため、ここではdecodeしない。
    user bucketは、認証Dependencyが検証済みtokenとしてRedis cacheへ入れた場合だけ使う。
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header[7:].strip()
    return token or None


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _rate_limit_identity(request: Request) -> tuple[str, int, int]:
    """Rate limit bucketを決定する。

    SEC-01 PR-D:
    - 未検証JWT payload emailは信用しない。
    - get_cached_jwt(token) がemailを返す場合だけ verified user bucket を使う。
    - それ以外はIP bucketへ倒す。
    """
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token:
        try:
            from app.cache import get_cached_jwt

            cached = await get_cached_jwt(token)
            email = cached.get("email") if cached else None
            if email:
                return f"user:{email}", AUTHED_RATE_LIMIT, AUTHED_WINDOW_SEC
        except Exception:
            # bucket選択で例外が起きてもレート制限全体は従来どおり可用性優先。
            logger.warning("verified JWT cache lookup failed for rate bucket", exc_info=True)

    client_ip = _get_client_ip(request)
    return f"ip:{client_ip}", UNAUTHED_RATE_LIMIT, UNAUTHED_WINDOW_SEC


async def _check_rate_limit(identifier: str, limit: int, window_sec: int) -> bool:
    """レートリミットを確認し、超過時は True を返す。

    Returns:
        True  = 超過（429 を返すべき）
        False = 正常範囲内 or Redis 不通
    """
    try:
        from app.cache import get_redis
        r = get_redis()
        if not r:
            return False

        minute_bucket = int(time.time()) // window_sec
        key = f"rate:{hashlib.sha256(identifier.encode()).hexdigest()[:16]}:{minute_bucket}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_sec + 5)

        return count > limit
    except Exception:
        logger.warning("レートリミット確認失敗: fail-openとして通過")
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """認証済みユーザー/IPアドレス単位のAPIレートリミット"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # 除外パスはスキップ
        if any(path.startswith(p) for p in _SKIP_PATHS):
            return await call_next(request)

        identifier, limit, window_sec = await _rate_limit_identity(request)
        exceeded = await _check_rate_limit(identifier, limit, window_sec)

        if exceeded:
            return JSONResponse(
                status_code=429,
                content={"detail": "リクエスト数が上限に達しました。しばらく時間をおいてから再試行してください"},
                headers={"Retry-After": str(window_sec)},
            )

        return await call_next(request)
