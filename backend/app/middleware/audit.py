"""
認証・データアクセス自動記録ミドルウェア。

記録対象:
  [auth_events]
    - 認証関連APIリクエスト（/api/v1/auth/*）
    - 認証失敗（HTTP 401, 403）

  [data_access_events] ← P2-1/P2-3 追加、S6 で閲覧を追加
    - 全書き込み操作（data_write: POST / PATCH / PUT / DELETE）
    - 書き込みの大量検知（bulk_export_alert: 500件/10分 超過）
    - 全件取得・ファイル出力の GET（data_export: 応答が 400 未満のもの）
    - 閲覧の大量検知（bulk_read_alert: GET が 500件/10分 超過、1窓1回）

注意:
  - パスワード・トークン等の機密情報は記録しない
  - 応答の生成後に記録する（失敗しても応答は変えない）
  - 大量アクセスはRedisで追跡（Redis不通時は追跡省略）
"""

import base64
import json
import logging
import time
from typing import Callable

from fastapi import Request, Response
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from app.client_ip import get_client_ip
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# 認証イベントを記録する対象パス
_AUTH_PATHS = ("/api/v1/auth/",)

# 認証失敗として記録するステータスコード
_AUTH_FAILURE_CODES = {401, 403}

# 書き込み操作として記録するHTTPメソッド
_WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

# 除外パス（ヘルスチェック・静的ファイル等）
_SKIP_PATHS = ("/health", "/metrics", "/docs", "/openapi", "/static")

# 大量エクスポート検知: 500件/10分超過で管理者アラート
BULK_EXPORT_WINDOW_SEC = 600   # 10分
BULK_EXPORT_MAX_CALLS = 500    # 10分間に500APIコール超でアラート

# 一覧の全件取得・ファイル出力として記録する GET（docs/specs/get-access-audit/）
_EXPORT_PATH_SUFFIXES = ("/export", "/elogi-csv", "/download")
_EXPORT_PATHS = frozenset({
    "/api/v1/financials/orders",
    "/api/v1/companies/duplicates",
})


def _is_export_get(method: str, path: str) -> bool:
    """全件取得・ファイル出力の GET か。"""
    if method != "GET":
        return False
    return path in _EXPORT_PATHS or path.endswith(_EXPORT_PATH_SUFFIXES)


def _decode_jwt_email(auth_header: str | None) -> str | None:
    """Bearer トークンのペイロードから email を取得する（署名検証なし・ログ用途のみ）。"""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    try:
        token = auth_header[7:]
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload.get("email")
    except Exception:
        return None


async def _check_and_record_bulk_export(user_email: str | None) -> bool:
    """大量エクスポート検知: Redisで10分間のAPIコール数を追跡する。

    Returns:
        True = 閾値超過（アラート対象）
        False = 正常範囲内
    """
    if not user_email:
        return False

    try:
        import hashlib

        from app.cache import get_redis
        r = get_redis()
        if not r:
            return False

        window = int(time.time()) // BULK_EXPORT_WINDOW_SEC
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        key = f"bulk_access:{email_hash}:{window}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, BULK_EXPORT_WINDOW_SEC + 60)

        return count > BULK_EXPORT_MAX_CALLS
    except Exception:
        logger.warning("大量エクスポート追跡に失敗")
        return False


async def _count_read_and_check(user_email: str | None) -> bool:
    """閲覧（GET）の回数を利用者ごと 10 分で数え、閾値を超えた最初の 1 回だけ True。"""
    if not user_email:
        return False
    try:
        import hashlib

        from app.cache import get_redis
        r = get_redis()
        if not r:
            return False
        window = int(time.time()) // BULK_EXPORT_WINDOW_SEC
        email_hash = hashlib.sha256(user_email.encode()).hexdigest()[:16]
        key = f"bulk_read:{email_hash}:{window}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, BULK_EXPORT_WINDOW_SEC + 60)
        return count == BULK_EXPORT_MAX_CALLS + 1
    except Exception:
        logger.warning("閲覧回数の追跡に失敗")
        return False


async def _insert_data_access(
    event_type: str,
    request: Request,
    status_code: int,
    user_email: str | None,
    client_ip: str,
    duration_ms: int,
) -> None:
    """data_access_events に 1 行入れる（INSERT 文はここだけ）。"""
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("""
                INSERT INTO public.data_access_events
                    (event_type, method, path, status_code,
                     user_email, client_ip, user_agent, duration_ms)
                VALUES
                    (:event_type, :method, :path, :status_code,
                     :user_email, :client_ip, :user_agent, :duration_ms)
            """),
            {
                "event_type": event_type,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "user_email": user_email,
                "client_ip": client_ip,
                "user_agent": (request.headers.get("User-Agent") or "")[:500],
                "duration_ms": duration_ms,
            },
        )
        await db.commit()


class AuditMiddleware(BaseHTTPMiddleware):
    """認証イベント・データアクセスを自動記録するミドルウェア"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        path = request.url.path
        method = request.method
        status_code = response.status_code

        # 除外パスはスキップ
        if any(path.startswith(p) for p in _SKIP_PATHS):
            return response

        is_auth_path = any(path.startswith(p) for p in _AUTH_PATHS)
        is_auth_failure = status_code in _AUTH_FAILURE_CODES
        is_write_op = method in _WRITE_METHODS

        # 認証イベント記録（既存）
        if is_auth_path or is_auth_failure:
            await self._record_auth_event(
                request=request,
                status_code=status_code,
                duration_ms=duration_ms,
                is_auth_path=is_auth_path,
            )

        # データアクセス記録（P2-1: 書き込み操作）
        if is_write_op and status_code < 500:
            await self._record_data_access(
                request=request,
                status_code=status_code,
                duration_ms=duration_ms,
            )

        # 閲覧の記録（S6: 全件取得・ファイル出力の GET と、閲覧の大量検知）
        if method == "GET" and status_code < 500:
            await self._record_read_access(
                request=request,
                status_code=status_code,
                duration_ms=duration_ms,
            )

        return response

    async def _record_auth_event(
        self,
        request: Request,
        status_code: int,
        duration_ms: int,
        is_auth_path: bool,
    ) -> None:
        """認証イベントをDBに記録する"""
        try:
            client_ip = get_client_ip(request)

            if status_code in _AUTH_FAILURE_CODES:
                event_type = "auth_failure"
            elif is_auth_path and 200 <= status_code < 300:
                event_type = "auth_success"
            else:
                event_type = "auth_request"

            # 口の中で入れた request.state.auth_audit（ADR-1055 D7・K9）。
            # starlette の request.state は scope["state"] を共有するので、middleware から読める。
            # 値は user_id・reason・is_new_device・event_type（任意）だけ。パスワード・合言葉・Cookie の値は入れない。
            audit = getattr(request.state, "auth_audit", None)
            audit = audit if isinstance(audit, dict) else {}
            if audit.get("event_type"):
                event_type = str(audit["event_type"])[:50]
            reason = audit.get("reason")

            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        INSERT INTO public.auth_events
                            (event_type, path, method, status_code,
                             client_ip, user_agent, duration_ms,
                             user_id, reason, is_new_device)
                        VALUES
                            (:event_type, :path, :method, :status_code,
                             :client_ip, :user_agent, :duration_ms,
                             :user_id, :reason, :is_new_device)
                    """),
                    {
                        "user_id": audit.get("user_id"),
                        "reason": str(reason)[:50] if reason else None,
                        "is_new_device": audit.get("is_new_device"),
                        "event_type": event_type,
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": status_code,
                        "client_ip": client_ip,
                        "user_agent": (request.headers.get("User-Agent") or "")[:500],
                        "duration_ms": duration_ms,
                    },
                )
                await db.commit()
        except Exception:
            logger.exception("認証イベント記録に失敗")

    async def _record_data_access(
        self,
        request: Request,
        status_code: int,
        duration_ms: int,
    ) -> None:
        """書き込み操作をdata_access_eventsに記録する（P2-1）。
        大量アクセス閾値超過時はアラートも記録する（P2-3）。
        """
        try:
            client_ip = get_client_ip(request)
            user_email = _decode_jwt_email(request.headers.get("Authorization"))
            event_type = "data_write"

            # P2-3: 大量エクスポート検知
            is_bulk_alert = await _check_and_record_bulk_export(user_email)
            if is_bulk_alert:
                event_type = "bulk_export_alert"
                logger.warning(
                    "大量APIアクセス検知: user=%s ip=%s path=%s",
                    user_email,
                    client_ip,
                    request.url.path,
                )

            await _insert_data_access(
                event_type, request, status_code, user_email, client_ip, duration_ms
            )
        except Exception:
            logger.exception("データアクセスイベント記録に失敗")

    async def _record_read_access(
        self,
        request: Request,
        status_code: int,
        duration_ms: int,
    ) -> None:
        """閲覧（GET）を記録する（S6）。

        全件取得・ファイル出力（応答 400 未満）は data_export、
        閲覧回数が閾値を超えた最初の 1 回は bulk_read_alert を記録する。
        """
        try:
            client_ip = get_client_ip(request)
            user_email = _decode_jwt_email(request.headers.get("Authorization"))
            path = request.url.path

            if status_code not in _AUTH_FAILURE_CODES and await _count_read_and_check(user_email):
                logger.warning(
                    "大量閲覧検知: user=%s ip=%s path=%s",
                    user_email,
                    client_ip,
                    path,
                )
                await _insert_data_access(
                    "bulk_read_alert", request, status_code, user_email, client_ip, duration_ms
                )

            if _is_export_get(request.method, path) and status_code < 400:
                await _insert_data_access(
                    "data_export", request, status_code, user_email, client_ip, duration_ms
                )
        except Exception:
            logger.exception("閲覧アクセスイベント記録に失敗")
