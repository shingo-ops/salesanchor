"""ADR-1052 段2: 許可された申請の値を 1 回だけ返す専用の HTTP 口 ai-unmask-http。

POST /ops/unmask/read {"request_id": "<uuid>"} を受け、ロール ai_unmask で
`SELECT ops_case.unmask_fetch(request_id, 件の札)` を 1 回流す。値を返すのはこの口だけ。
守りの本体は DB 側（unmask_fetch が申請・札・状態・期限・回数・列・元の表を全部確かめる）。

注意:
- 既存の app.* を import しない（DATABASE_URL に触れる可能性があるため）。
- 鍵は環境変数 CASE_AGENT_TOKEN（Authorization: Bearer）。空・未設定なら常に 401。件の札は X-Case-Ticket。
- DB は psycopg2 で AI_UNMASK_DATABASE_URL に繋ぐ。readonly_query.execute は使わない（読み取り専用の取引では記録が書けない）。
- 取引は autocommit を切り、unmask_fetch を 1 回流して COMMIT が成功してから値を返す。
- 関数が SQLSTATE 42501 で断れば 403 と印だけ。それ以外の失敗（接続・時間切れ・COMMIT の失敗を含む）は 503 で値を返さない。
- 記録（/dev/log）には request_id・件数・結果の種類・失敗のときは SQLSTATE だけ。値・札・鍵・エラーの文は書かない。
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
import threading
from datetime import datetime, timezone

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.ops import readonly_query

MAX_BODY_BYTES = 4096
VIA = "https-case-unmask"
# unmask_fetch が返す印（ops_case の migration と同じ 10 種。これ以外の文は返さない）
MARKS = frozenset(
    {"not_found", "ticket", "status", "expired", "used", "view", "source", "column", "key", "read_failed"}
)
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_MAX_TICKET_BYTES = 256

# ロールの接続数の上限が 2 なので、同時に動かすのも 2 本まで。超えたら 429
_slots = threading.Semaphore(2)
# 試験で差し替える。None なら psycopg2.connect を使う
_connect = None


def _json(status: int, payload: dict) -> Response:
    return JSONResponse(payload, status_code=status)


def _connection():
    url = os.environ.get("AI_UNMASK_DATABASE_URL", "")
    if not url:
        raise RuntimeError("AI_UNMASK_DATABASE_URL is empty")
    if _connect is not None:
        return _connect(url)
    import psycopg2

    return psycopg2.connect(url, connect_timeout=5)


def _audit_line(request_id: str, row_count: int, result: str, sqlstate: str = "") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = f" sqlstate={sqlstate}" if sqlstate else ""
    return f"AUDIT ts={ts} unmask request_id={request_id} rows={row_count} result={result}{state} via={VIA}"


def _send_audit(audit, line: str) -> None:
    sys.stderr.write(line + "\n")
    try:
        audit.send(f"<{readonly_query.AUDIT_PRI}>{readonly_query.AUDIT_IDENT}: {line}".encode("utf-8", "replace"))
    except OSError:
        sys.stderr.write("error: audit send failed\n")


def _sqlstate(exc: BaseException) -> str:
    code = getattr(exc, "pgcode", None)
    return code if isinstance(code, str) and code else ""


def _fetch(request_id: str, ticket: str, audit) -> tuple[int, dict]:
    """DB を 1 回だけ呼ぶ。(HTTP の状態, 本文)。値を返すのは COMMIT が成功したときだけ。"""
    conn = None
    try:
        conn = _connection()
        conn.autocommit = False
        cur = conn.cursor()
        cur.execute("SELECT ops_case.unmask_fetch(%s, %s)", (request_id, ticket))
        result = cur.fetchone()[0]
        if isinstance(result, str):
            result = json.loads(result)
        conn.commit()
    except Exception as exc:  # noqa: BLE001 - 失敗の種類は SQLSTATE だけ残す（文・値は出さない）
        state = _sqlstate(exc)
        mark = ""
        if state == "42501":
            diag = getattr(exc, "diag", None)
            mark = getattr(diag, "message_primary", "") or ""
        if conn is not None:
            try:
                conn.rollback()
            except Exception:  # noqa: BLE001
                pass
        if state == "42501" and mark in MARKS:
            _send_audit(audit, _audit_line(request_id, 0, f"denied:{mark}", state))
            return 403, {"error": mark}
        _send_audit(audit, _audit_line(request_id, 0, "unavailable", state or type(exc).__name__))
        return 503, {"error": "unavailable"}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
    row_count = result.get("row_count", 0) if isinstance(result, dict) else 0
    _send_audit(audit, _audit_line(request_id, int(row_count), "ok"))
    return 200, result


async def read(request: Request) -> Response:
    if request.method != "POST":
        return _json(404, {"error": "not_found"})

    expected = os.environ.get("CASE_AGENT_TOKEN", "")
    header = request.headers.get("authorization", "")
    given = header[len("Bearer ") :] if header.startswith("Bearer ") else ""
    ticket = request.headers.get("x-case-ticket", "")
    if not expected or not given or not secrets.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        return _json(401, {"error": "unauthorized"})
    if not ticket or len(ticket.encode("utf-8")) > _MAX_TICKET_BYTES:
        return _json(401, {"error": "unauthorized"})

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        return _json(413, {"error": "payload_too_large"})
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _json(400, {"error": "bad_request"})
    request_id = data.get("request_id") if isinstance(data, dict) and set(data) == {"request_id"} else None
    if not isinstance(request_id, str) or not _UUID_RE.fullmatch(request_id):
        return _json(400, {"error": "bad_request"})

    # 記録の送り口が開けないときは、値を返さない（DB にも触れない）
    try:
        audit = readonly_query._open_audit(readonly_query.AUDIT_SOCKET)
    except OSError:
        return _json(503, {"error": "unavailable"})
    if not _slots.acquire(blocking=False):
        _close(audit)
        return _json(429, {"error": "busy"})
    try:
        status, payload = await run_in_threadpool(_fetch, request_id, ticket, audit)
    finally:
        _slots.release()
        _close(audit)
    return _json(status, payload)


def _close(audit) -> None:
    try:
        audit.close()
    except Exception:  # noqa: BLE001
        pass


# 道は 1 つだけ。ほかの道・ほかの方法は 404（Starlette の既定の 405 を使わない）
app = Starlette(
    routes=[
        Route("/ops/unmask/read", read, methods=["POST", "GET", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]),
    ]
)
