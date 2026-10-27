import asyncio
import time

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from app.cache import get_redis
from app.celery_health import read_celery_health

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ("method", "handler", "status"),
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "handler", "status"),
)

IN_FLIGHT_REQUESTS = Gauge(
    "http_requests_in_flight",
    "Current in-flight HTTP requests handled by this backend process",
)

SSE_CONNECTIONS_ACTIVE = Gauge(
    "sse_connections_active",
    "Current active SSE connections",
    ("stream",),
)

CELERY_HEARTBEAT_TS = Gauge(
    "celery_heartbeat_last_success_timestamp_seconds",
    "Unix time of the last celery heartbeat task run (0 when missing)",
)

CELERY_TASK_FAILURES = Gauge(
    "celery_task_failures",
    "Cumulative celery task failures per task name, as recorded in Redis",
    ("task",),
)

CELERY_QUEUE_LENGTH = Gauge(
    "celery_queue_length",
    "Current length of the default celery queue",
)

VIEWER_INVENTORY_UPDATED_TS = Gauge(
    "viewer_inventory_updated_timestamp_seconds",
    "閲覧ページの在庫の作り置きを最後に書けた時刻（UNIX 秒）",
)

VIEWER_INVENTORY_LAST_HOLD_TS = Gauge(
    "viewer_inventory_last_hold_timestamp_seconds",
    "閲覧ページの作り置きで、配信の保留を最後に確かめた時刻（UNIX 秒）",
)

OPS_MAIL_LAST_SAKURA_MAIL_TS = Gauge(
    "salesanchor_ops_mail_last_sakura_mail_timestamp_seconds",
    "運用の受け箱で、さくらの差出人のメールを最後に見た時刻（UNIX 秒。0 は未設定）",
)

OPS_MAIL_LAST_POLL_OK_TS = Gauge(
    "salesanchor_ops_mail_last_poll_success_timestamp_seconds",
    "運用の受け箱を最後に読めた時刻（UNIX 秒。0 は未設定）",
)

_VIEWER_TS_READ_TIMEOUT_SEC = 1.0


async def _read_ts(redis_client, key: str) -> float:
    """Redis の時刻キーを数として読む。無い・数でない・例外は 0（「ずっと前」と同じ扱い）。"""
    try:
        raw = await asyncio.wait_for(redis_client.get(key), _VIEWER_TS_READ_TIMEOUT_SEC)
        return float(raw) if raw else 0.0
    except Exception:
        return 0.0


async def _update_viewer_inventory_gauges() -> None:
    from app.tasks.viewer_inventory_cache import LAST_HOLD_TS_KEY, UPDATED_TS_KEY  # noqa: PLC0415

    redis_client = get_redis()
    if redis_client is None:
        VIEWER_INVENTORY_UPDATED_TS.set(0)
        VIEWER_INVENTORY_LAST_HOLD_TS.set(0)
        return
    VIEWER_INVENTORY_UPDATED_TS.set(await _read_ts(redis_client, UPDATED_TS_KEY))
    VIEWER_INVENTORY_LAST_HOLD_TS.set(await _read_ts(redis_client, LAST_HOLD_TS_KEY))


async def _update_ops_mail_gauges() -> None:
    from app.services.ops_mail_notifier import LAST_POLL_OK_TS_KEY, LAST_SAKURA_MAIL_TS_KEY  # noqa: PLC0415

    redis_client = get_redis()
    if redis_client is None:
        OPS_MAIL_LAST_SAKURA_MAIL_TS.set(0)
        OPS_MAIL_LAST_POLL_OK_TS.set(0)
        return
    OPS_MAIL_LAST_SAKURA_MAIL_TS.set(await _read_ts(redis_client, LAST_SAKURA_MAIL_TS_KEY))
    OPS_MAIL_LAST_POLL_OK_TS.set(await _read_ts(redis_client, LAST_POLL_OK_TS_KEY))


def _handler_name(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return request.url.path


def register_metrics(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        IN_FLIGHT_REQUESTS.inc()
        started = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            elapsed = time.perf_counter() - started
            labels = (request.method, _handler_name(request), status)
            REQUEST_COUNT.labels(*labels).inc()
            REQUEST_DURATION.labels(*labels).observe(elapsed)
            IN_FLIGHT_REQUESTS.dec()

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        health = await read_celery_health()
        if health is not None:
            heartbeat_ts, failures, queue_len = health
            CELERY_HEARTBEAT_TS.set(heartbeat_ts)
            for task_name, count in failures.items():
                CELERY_TASK_FAILURES.labels(task_name).set(count)
            CELERY_QUEUE_LENGTH.set(queue_len)
        try:
            await _update_viewer_inventory_gauges()
        except Exception:
            VIEWER_INVENTORY_UPDATED_TS.set(0)
            VIEWER_INVENTORY_LAST_HOLD_TS.set(0)
        try:
            await _update_ops_mail_gauges()
        except Exception:
            OPS_MAIL_LAST_SAKURA_MAIL_TS.set(0)
            OPS_MAIL_LAST_POLL_OK_TS.set(0)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
