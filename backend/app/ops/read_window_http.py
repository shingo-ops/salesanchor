"""ADR-1042 便1: クラウドから本番を「読むだけ」の HTTP 窓口。

POST /api/v1/ops/read-window/query に SQL を 1 文送ると、readonly_query.execute
（ai_reader の読み取り専用接続・文字列検査・AUDIT）で実行して TSV を返す。
守りの本体は DB の権限（ai_reader は ai_ro ビューだけ読める）。

注意:
- 既存の app.* を import しない（DATABASE_URL に触れる可能性があるため）。
- 鍵は環境変数 READ_WINDOW_TOKEN。空・未設定なら常に 401。ヘッダは X-Read-Window-Token のみ。
- 同時に実行するのは 1 本だけ。2 本目は 429。
"""

from __future__ import annotations

import os
import secrets
import threading

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

from app.ops import readonly_query

MAX_BODY_BYTES = readonly_query.MAX_SQL_BYTES
TOKEN_HEADER = "X-Read-Window-Token"
RC_HEADER = "X-Read-Window-Rc"

_slot = threading.Semaphore(1)
# 試験で差し替える。None なら readonly_query が psycopg2.connect を使う
_connect = None


def _reply(status: int, text: str = "", rc: int | None = None, media: str = "text/plain") -> Response:
    headers = {RC_HEADER: str(rc)} if rc is not None else {}
    return PlainTextResponse(text, status_code=status, headers=headers, media_type=media)


def _error_lines(err: str, prefix: str) -> str:
    """AUDIT 行などを返さず、指定の接頭辞で始まる行だけを返す。"""
    lines = [ln for ln in err.splitlines() if ln.startswith(prefix)]
    return "\n".join(lines) + ("\n" if lines else "")


def _run_query(sql_text: str) -> readonly_query.Result:
    try:
        audit = readonly_query._open_audit(readonly_query.AUDIT_SOCKET)
    except OSError:
        return readonly_query.Result(5, "", "")
    try:
        return readonly_query.execute(sql_text, _connect, audit, via="https")
    finally:
        try:
            audit.close()
        except Exception:
            pass


async def query(request: Request) -> Response:
    expected = os.environ.get("READ_WINDOW_TOKEN", "")
    given = request.headers.get(TOKEN_HEADER, "")
    if not expected or not secrets.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        return _reply(401, "unauthorized")

    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        return _reply(413, "payload too large")

    if not _slot.acquire(blocking=False):
        return _reply(429, "busy")
    try:
        res = await run_in_threadpool(_run_query, body.decode("utf-8", "replace"))
    finally:
        _slot.release()

    if res.rc == 0:
        return _reply(200, res.body, 0, "text/tab-separated-values")
    if res.rc == 2:
        return _reply(400, _error_lines(res.err, "rejected:"), 2)
    if res.rc == 4:
        return _reply(400, _error_lines(res.err, "db error:"), 4)
    return _reply(503, "", res.rc)


app = Starlette(routes=[Route("/api/v1/ops/read-window/query", query, methods=["POST"])])
