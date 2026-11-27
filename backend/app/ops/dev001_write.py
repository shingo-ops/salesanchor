"""ADR-1093 便2: AI 用の tenant_001 書き込み台本。

標準入力から SQL を 1 文読み、AI_DEV001_WRITER_DATABASE_URL の専用ユーザー(ai_dev001_writer)で
実行する。台本が毎回 SET LOCAL app.tenant_id = '1' と SET LOCAL search_path = tenant_001, public を入れる。
SELECT / RETURNING の結果は TSV で標準出力へ出す。

守りの本体は DB の権限（ai_dev001_writer は tenant_001 の表と列にだけ権限を持つ。design.md §3-2）。
この台本の文字列検査は事故よけであり、境界ではない。スキーマ名では拒まない（K2・K3 を DB の権限エラーで測るため）。

順番: 文を流す → AUDIT を送る → 送れたら commit、送れなければ rollback。
DB エラーのときは AUDIT を送る → 必ず rollback。

終了コード: 0 成功 / 2 拒否 / 3 成功したが AUDIT を送れず rollback した / 4 DB エラー /
          5 拒否・DB エラーで AUDIT を送れない（送り口を開けないときも） / 6 環境変数が未設定
(stdout の書き込みに失敗したときは Python の既定で rc=1。AUDIT は ok で記録済み・commit 済み)
注意:
- 環境変数は AI_DEV001_WRITER_DATABASE_URL だけを読む。他の接続情報には切り替えない。
- 既存の app.* は readonly_query（同じ ops の台本）以外を import しない（DATABASE_URL に触れる可能性があるため）。
- 接続文字列の値は画面・ログ・エラー文に出さない。
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone

from app.ops.readonly_query import (
    AUDIT_PRI,
    AUDIT_SOCKET,
    DENY_COLUMN_RE,
    MAX_SQL_BYTES,
    Rejected,
    _escape,
    _has_second_statement,
    _open_audit,
    _strip_comments,
    parse_limit,
)

AUDIT_IDENT = "ai-dev001-writer-audit"

# 先頭の語がこれ以外なら拒む。SET・RESET は含まれないので先頭にあれば拒まれる（UPDATE ... SET は先頭が UPDATE なので通る）
_ALLOWED_FIRST_WORDS = {"insert", "update", "delete", "select", "with"}
# 文のどこにあっても拒む（readonly_query.py の set_config 2 つと同じ）
_FORBIDDEN_RES = [
    re.compile(r"set_config\s*\(", re.I),
    re.compile(r"pg_catalog\s*\.\s*set_config", re.I),
]

# 台本が毎回入れる 2 文（tenant_001 固定）
_PRELUDE = (
    "SET LOCAL app.tenant_id = '1'",
    "SET LOCAL search_path = tenant_001, public",
)


def check_sql(sql: str) -> str:
    """拒否なら Rejected(理由)。通るなら、コメントを除いた本文を返す。"""
    body = _strip_comments(sql).strip()
    if not body:
        raise Rejected("empty statement")
    if body.startswith("\\"):
        raise Rejected("backslash command is not allowed")
    if _has_second_statement(body):
        raise Rejected("multiple statements are not allowed")
    m = re.match(r"[A-Za-z_]+", body)
    first = m.group(0).lower() if m else ""
    if first not in _ALLOWED_FIRST_WORDS:
        raise Rejected("only INSERT / UPDATE / DELETE / SELECT / WITH are allowed")
    for rx in _FORBIDDEN_RES:
        if rx.search(body):
            raise Rejected("forbidden token: " + rx.pattern)
    return body


def _log(stderr, sql: str, rows: int, ms: int, result: str, audit) -> bool:
    """AUDIT を stderr と送り口へ出す。送れたら True、送れなければ False。"""
    sha = hashlib.sha256(sql.encode("utf-8", "replace")).hexdigest()[:12]
    head = sql[:500].replace("\n", " ").replace("\r", " ")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"AUDIT ts={ts} sha={sha} rows={rows} ms={ms} result={result} sql={head}"
    stderr.write(line + "\n")
    try:
        audit.send(f"<{AUDIT_PRI}>{AUDIT_IDENT}: {line}".encode("utf-8", "replace"))
    except OSError:
        stderr.write("error: audit send failed\n")
        return False
    return True


def main(argv=None, stdin=None, stdout=None, stderr=None, connect=None, audit=None, audit_path=AUDIT_SOCKET) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    if audit is None:
        try:
            audit = _open_audit(audit_path)
        except OSError:
            stderr.write("error: audit channel unavailable\n")
            return 5
    try:
        raw = stdin.read(MAX_SQL_BYTES + 1)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        return _execute(raw, stdout, stderr, connect, audit)
    finally:
        try:
            audit.close()
        except Exception:
            pass


def _execute(raw: str, stdout, stderr, connect, audit) -> int:
    started = time.monotonic()

    def ms() -> int:
        return int((time.monotonic() - started) * 1000)

    if len(raw.encode("utf-8", "replace")) > MAX_SQL_BYTES:
        stderr.write("rejected: SQL is larger than 64KB\n")
        return 2 if _log(stderr, raw[:500], 0, 0, "rejected", audit) else 5

    try:
        check_sql(raw)
    except Rejected as e:
        stderr.write(f"rejected: {e}\n")
        return 2 if _log(stderr, raw, 0, ms(), "rejected", audit) else 5

    url = os.environ.get("AI_DEV001_WRITER_DATABASE_URL")
    if not url:
        stderr.write("error: AI_DEV001_WRITER_DATABASE_URL is not set\n")
        return 6 if _log(stderr, raw, 0, 0, "env_missing", audit) else 5

    limit = parse_limit(raw)
    if connect is None:
        import psycopg2

        connect = psycopg2.connect

    conn = None
    names: list = []
    redact: list = []
    fetched: list = []
    rows = 0
    try:
        conn = connect(url)
        cur = conn.cursor()
        for prelude in _PRELUDE:
            cur.execute(prelude)
        cur.execute(raw)
        if cur.description is not None:
            names = [d[0] for d in cur.description]
            redact = [bool(DENY_COLUMN_RE.search(nm.lower())) for nm in names]
            fetched = cur.fetchmany(limit + 1)
            if len(fetched) > limit:
                fetched = fetched[:limit]
                stderr.write(f"打ち切り: {limit} 行で打ち切りました\n")
            rows = len(fetched)
        else:
            rows = max(int(getattr(cur, "rowcount", 0) or 0), 0)
        # AUDIT を先に送る。送れたら commit、送れなければ rollback して終了コード 3
        if not _log(stderr, raw, rows, ms(), "ok", audit):
            conn.rollback()
            return 3
        conn.commit()
    except Exception as e:  # DB エラー。種類だけを出す（接続文字列・メッセージ本文は出さない）
        kind = type(e).__name__
        code = getattr(e, "pgcode", None) or "-"
        stderr.write(f"db error: {kind} pgcode={code}\n")
        # AUDIT → 必ず rollback（rollback は finally）
        return 4 if _log(stderr, raw, 0, ms(), f"db_error:{kind}", audit) else 5
    finally:
        if conn is not None:
            try:
                conn.rollback()  # commit 済みなら何も起きない
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    if names:
        stdout.write("\t".join(_escape(nm) for nm in names) + "\n")
        for row in fetched:
            cells = ["<redacted>" if redact[i] else _escape(v) for i, v in enumerate(row)]
            stdout.write("\t".join(cells) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
