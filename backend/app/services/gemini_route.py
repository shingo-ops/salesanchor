"""Gemini への道（直接 / prod2 の中継）を選ぶ正本。ADR-1062。道の選び方はここ1か所だけ。"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time

import httpx

try:  # google-genai は aiohttp が入っていると非同期の呼び出しに aiohttp を使う
    import aiohttp
except ImportError:  # pragma: no cover - 本番には discord.py 経由で入っている
    aiohttp = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ROUTE_DIRECT = "direct"
ROUTE_RELAY = "relay"

# docker-compose.yml の gemini-egress。GEMINI_PROXY_URL が空のときの中継の先。
DEFAULT_RELAY_URL = "http://gemini-egress:18888"

STICKY_SECONDS = 600
SWITCH_COUNT_PREFIX = "gemini_route:switch:"
SWITCH_COUNT_TTL_SECONDS = 24 * 60 * 60
REASON_MAX_CHARS = 300
_CHAIN_MAX_DEPTH = 5
_LOCATION_REFUSAL_TEXT = "location is not supported"

# プロセスの中だけの「切り替えて成功した道」の記憶
_sticky: dict = {"route": None, "until": 0.0}


def relay_url() -> str:
    return os.getenv("GEMINI_PROXY_URL", "").strip() or DEFAULT_RELAY_URL


def preferred_route() -> str:
    return ROUTE_RELAY if os.getenv("GEMINI_PROXY_URL", "").strip() else ROUTE_DIRECT


def first_route() -> str:
    route = _sticky["route"]
    if route and time.monotonic() < _sticky["until"]:
        return route
    return preferred_route()


def other_route(route: str) -> str:
    return ROUTE_DIRECT if route == ROUTE_RELAY else ROUTE_RELAY


def remember(route: str) -> None:
    _sticky["route"] = route
    _sticky["until"] = time.monotonic() + STICKY_SECONDS


def reset_state() -> None:
    """道の記憶を初期値に戻す（試験用）。"""
    _sticky["route"] = None
    _sticky["until"] = 0.0


def build_client(route: str):
    """google.genai.Client を道に合わせて生成して返す。"""
    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types as _types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai がインストールされていません: pip install google-genai"
        ) from exc
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY が未設定です。Gemini 抽出は実行できません。"
        )
    if route == ROUTE_RELAY:
        url = relay_url()
        return genai.Client(
            api_key=api_key,
            http_options=_types.HttpOptions(
                client_args={"proxy": url},
                async_client_args={"proxy": url},
            ),
        )
    return genai.Client(api_key=api_key)


def _exception_chain(exc: BaseException) -> list:
    chain: list = []
    seen: set[int] = set()
    cur = exc
    while cur is not None and len(chain) < _CHAIN_MAX_DEPTH and id(cur) not in seen:
        chain.append(cur)
        seen.add(id(cur))
        cur = cur.__cause__ if cur.__cause__ is not None else cur.__context__
    return chain


def is_location_refusal(exc: BaseException) -> bool:
    from google.genai import errors as genai_errors

    for e in _exception_chain(exc):
        if isinstance(e, genai_errors.APIError) and getattr(e, "code", None) == 400:
            text = str(getattr(e, "message", "") or e).lower()
            if _LOCATION_REFUSAL_TEXT in text:
                return True
    return False


def _unreachable_types() -> tuple:
    types: tuple = (httpx.ConnectError, httpx.ConnectTimeout, httpx.ProxyError)
    if aiohttp is not None:
        types = types + (aiohttp.ClientConnectorError,)
    return types


def is_route_unreachable(exc: BaseException) -> bool:
    types = _unreachable_types()
    return any(isinstance(e, types) for e in _exception_chain(exc))


def should_switch(exc: BaseException) -> bool:
    return is_location_refusal(exc) or is_route_unreachable(exc)


_KEY_PARAM_RE = re.compile(r"key=[^\s&\"'<>]*")
_API_KEY_RE = re.compile(r"AIza[0-9A-Za-z_-]{6,}")


def failure_reason(exc: BaseException) -> str:
    from google.genai import errors as genai_errors

    chain = _exception_chain(exc)
    reason = None
    for e in chain:
        if isinstance(e, genai_errors.APIError):
            reason = f"{e.code} {e.status}: {e.message}"
            break
    if reason is None:
        for e in chain:
            if isinstance(e, httpx.TransportError):
                reason = f"{type(e).__name__}: {e}"
                break
    if reason is None:
        reason = f"{type(exc).__name__}: {exc}"
    reason = _KEY_PARAM_RE.sub("key=(省略)", reason)
    reason = _API_KEY_RE.sub("(APIキー省略)", reason)
    return reason[:REASON_MAX_CHARS]


def _get_redis():
    """同期 Redis クライアント。使えなければ None。"""
    try:
        import redis  # noqa: PLC0415

        client = redis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini_route] Redis unavailable (skip): %s", type(exc).__name__)
        return None


def _count_switch(from_route: str, to_route: str) -> None:
    try:
        client = _get_redis()
        if client is None:
            return
        key = SWITCH_COUNT_PREFIX + f"{from_route}_to_{to_route}"
        client.incr(key)
        client.expire(key, SWITCH_COUNT_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[gemini_route] switch count failed: %s", type(exc).__name__)


def generate_content_routed(client, *, model, contents, config):
    """同期。道の断り・届かないときだけ、もう一方の道で1回だけやり直す。"""
    route = first_route()
    try:
        return client.models.generate_content(model=model, contents=contents, config=config)
    except Exception as exc:
        if not should_switch(exc):
            raise
        to = other_route(route)
        logger.warning(
            "[gemini_route] 道を切り替えます: %s -> %s 理由=%s", route, to, failure_reason(exc)
        )
        # Client は消えると __del__ で接続を閉じる（google-genai）。呼び出しが終わるまで変数に持つ
        other = build_client(to)
        response = other.models.generate_content(
            model=model, contents=contents, config=config
        )
        remember(to)
        _count_switch(route, to)
        return response


async def agenerate_content_routed(*, model, contents, config):
    """非同期。切り替えの決まりは同期と同じ。"""
    route = first_route()
    client = build_client(route)
    try:
        return await client.aio.models.generate_content(
            model=model, contents=contents, config=config
        )
    except Exception as exc:
        if not should_switch(exc):
            raise
        to = other_route(route)
        logger.warning(
            "[gemini_route] 道を切り替えます: %s -> %s 理由=%s", route, to, failure_reason(exc)
        )
        # Client は消えると __del__ で接続を閉じる（google-genai）。呼び出しが終わるまで変数に持つ
        other = build_client(to)
        response = await other.aio.models.generate_content(
            model=model, contents=contents, config=config
        )
        remember(to)
        await asyncio.to_thread(_count_switch, route, to)
        return response
