"""ADR-1024 便3a: AI 用の読み取り台本。

標準入力から SQL を 1 文読み、AI_READER_DATABASE_URL の読み取り専用ユーザー(ai_reader)で
実行し、結果を TSV で標準出力へ出す。

守りの本体は DB の権限（ai_reader は ai_ro スキーマのビューだけ読める）。
この台本の文字列検査は使いやすさと二重目であり、境界ではない。

終了コード: 0 成功 / 2 拒否 / 3 環境変数が未設定 / 4 DB エラー / 5 AUDIT の送り口を開けない・送れない
(stdout の書き込みに失敗したときは Python の既定で rc=1。AUDIT は ok で記録済み)
注意:
- 環境変数は AI_READER_DATABASE_URL だけを読む。他の接続情報には切り替えない。
- 既存の app.* を import しない（DATABASE_URL に触れる可能性があるため）。
- 接続文字列の値は画面・ログ・エラー文に出さない。
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone

MAX_SQL_BYTES = 64 * 1024
DEFAULT_LIMIT = 200
MAX_LIMIT = 5000
MAX_VALUE_CHARS = 10 * 1024
STATEMENT_TIMEOUT = "60s"

# AUDIT は stderr に加えて /dev/log（syslog）へ送る。ホストで auth.log → Loki に届く（ADR-1024 K3 改訂）
AUDIT_SOCKET = "/dev/log"
AUDIT_IDENT = "ai-reader-audit"
AUDIT_PRI = 38  # auth(4) * 8 + info(6)
AUDIT_TIMEOUT = 2.0

# ai_ro ビュー生成（migrations/*_create_ai_ro_views.sql）の拒否リストと同じ正規表現
DENY_COLUMN_RE = re.compile(r"^password|_encrypted$|_secret|_token|hash|^secret|^api_key|private_key|credential")

_ALLOWED_FIRST_WORDS = {"select", "with", "show", "explain"}
_FORBIDDEN_RES = [
    re.compile(r"set_config\s*\(", re.I),
    re.compile(r"\bset\s", re.I),
    re.compile(r"\bcopy\b", re.I),
    re.compile(r"pg_read_file", re.I),
    re.compile(r"pg_sleep", re.I),
    re.compile(r"\blo_", re.I),
    re.compile(r"pg_catalog\s*\.\s*set_config", re.I),
]
# 書き込み系の語（WITH 内の DELETE 等と EXPLAIN INSERT 等を拒否。迷ったら拒否側）
_WRITE_RE = re.compile(r"\b(insert|update|delete|truncate|drop|alter|create|grant)\b", re.I)
_LIMIT_RE = re.compile(r"^\s*--\s*limit\s*=\s*(\d+)\s*$")


class Rejected(Exception):
    pass


def _strip_comments(sql: str) -> str:
    """コメントを除く。文字列・引用識別子・ドル引用の中は触らない。"""
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        two = sql[i : i + 2]
        if two == "--":
            j = sql.find("\n", i)
            i = n if j == -1 else j
            out.append(" ")
        elif two == "/*":
            depth, i = 1, i + 2
            while i < n and depth:
                if sql[i : i + 2] == "/*":
                    depth, i = depth + 1, i + 2
                elif sql[i : i + 2] == "*/":
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            out.append(" ")
        elif ch in ("'", '"'):
            j = i + 1
            while j < n:
                if sql[j] == ch:
                    if sql[j + 1 : j + 2] == ch:
                        j += 2
                        continue
                    break
                j += 1
            out.append(sql[i : j + 1])
            i = j + 1
        elif ch == "$":
            m = re.match(r"\$[A-Za-z_0-9]*\$", sql[i:])
            if m:
                tag = m.group(0)
                j = sql.find(tag, i + len(tag))
                end = n if j == -1 else j + len(tag)
                out.append(sql[i:end])
                i = end
            else:
                out.append(ch)
                i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _has_second_statement(body: str) -> bool:
    """引用の外の ; のあとに、空白以外があれば True。"""
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        if ch in ("'", '"'):
            j = i + 1
            while j < n:
                if body[j] == ch:
                    if body[j + 1 : j + 2] == ch:
                        j += 2
                        continue
                    break
                j += 1
            i = j + 1
        elif ch == "$":
            m = re.match(r"\$[A-Za-z_0-9]*\$", body[i:])
            if m:
                tag = m.group(0)
                j = body.find(tag, i + len(tag))
                i = n if j == -1 else j + len(tag)
            else:
                i += 1
        elif ch == ";":
            return body[i + 1 :].strip() != ""
        else:
            i += 1
    return False


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
        raise Rejected("only SELECT / WITH / SHOW / EXPLAIN are allowed")
    if first == "explain" and re.search(r"\banalyze\b", body, re.I):
        raise Rejected("EXPLAIN ANALYZE is not allowed")
    for rx in _FORBIDDEN_RES:
        if rx.search(body):
            raise Rejected("forbidden token: " + rx.pattern)
    if _WRITE_RE.search(body):
        raise Rejected("write keyword is not allowed")
    return body


def parse_limit(sql: str) -> int:
    first_line = sql.lstrip("﻿").split("\n", 1)[0]
    m = _LIMIT_RE.match(first_line)
    if not m:
        return DEFAULT_LIMIT
    n = int(m.group(1))
    if n < 1:
        return DEFAULT_LIMIT
    return min(n, MAX_LIMIT)


def _escape(value: object) -> str:
    s = "" if value is None else str(value)
    truncated = len(s) > MAX_VALUE_CHARS
    if truncated:
        s = s[:MAX_VALUE_CHARS]
    s = s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
    return s


def _open_audit(path: str):
    """AUDIT の送り口を開く。失敗は OSError（timeout も含む）をそのまま投げる。"""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        sock.settimeout(AUDIT_TIMEOUT)
        sock.connect(path)
    except OSError:
        sock.close()
        raise
    return sock


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
        return _run(stdin, stdout, stderr, connect, audit)
    finally:
        try:
            audit.close()
        except Exception:
            pass


def _run(stdin, stdout, stderr, connect, audit) -> int:
    started = time.monotonic()

    def ms() -> int:
        return int((time.monotonic() - started) * 1000)

    raw = stdin.read(MAX_SQL_BYTES + 1)
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    if len(raw.encode("utf-8", "replace")) > MAX_SQL_BYTES:
        stderr.write("rejected: SQL is larger than 64KB\n")
        return 2 if _log(stderr, raw[:500], 0, 0, "rejected", audit) else 5

    try:
        check_sql(raw)
    except Rejected as e:
        stderr.write(f"rejected: {e}\n")
        return 2 if _log(stderr, raw, 0, ms(), "rejected", audit) else 5

    url = os.environ.get("AI_READER_DATABASE_URL")
    if not url:
        stderr.write("error: AI_READER_DATABASE_URL is not set\n")
        return 3 if _log(stderr, raw, 0, 0, "env_missing", audit) else 5

    limit = parse_limit(raw)
    if connect is None:
        import psycopg2

        connect = psycopg2.connect

    conn = None
    names: list = []
    redact: list = []
    fetched: list = []
    try:
        conn = connect(url)
        conn.set_session(readonly=True)
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = '%s'" % STATEMENT_TIMEOUT)
        cur.execute(raw)
        if cur.description is None:
            stderr.write("error: statement returned no result set\n")
            return 4 if _log(stderr, raw, 0, ms(), "no_result", audit) else 5
        names = [d[0] for d in cur.description]
        redact = [bool(DENY_COLUMN_RE.search(nm.lower())) for nm in names]
        fetched = cur.fetchmany(limit + 1)
        if len(fetched) > limit:
            fetched = fetched[:limit]
            stderr.write(f"打ち切り: {limit} 行で打ち切りました\n")
    except Exception as e:  # DB エラー。種類だけを出す（接続文字列・メッセージ本文は出さない）
        kind = type(e).__name__
        code = getattr(e, "pgcode", None) or "-"
        stderr.write(f"db error: {kind} pgcode={code}\n")
        return 4 if _log(stderr, raw, 0, ms(), f"db_error:{kind}", audit) else 5
    finally:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass

    # AUDIT を先に送る。送れなければ結果は出さない。stdout の書き込みは DB の try の外
    if not _log(stderr, raw, len(fetched), ms(), "ok", audit):
        return 5
    stdout.write("\t".join(_escape(nm) for nm in names) + "\n")
    for row in fetched:
        cells = ["<redacted>" if redact[i] else _escape(v) for i, v in enumerate(row)]
        stdout.write("\t".join(cells) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
