#!/usr/bin/env python3
"""ADR-1012 段階3 便G: 応急処置係。

prod1 の ubuntu の cron で毎分 1 回（flock -n で二重起動を防ぐ）。
保守 API から「札 auto で鳴っていて、まだ処置していない障害」を読み、
処置の一覧（first_aid_actions.json）に載ったものだけ `docker compose restart` する。
結果は障害記録に注記し、直らない・回数の上限・途中で止まったときは textfile に書いて
見張り FirstAidEscalated（札 page）で人を呼ぶ。
python3 の標準ライブラリだけを使う。鍵は prod1 の .env から読み、画面にもログにも出さない。
設計: docs/handoff/ai-ops-247/card-stage3-bin-g.md
"""
from __future__ import annotations

import http.client
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone


def _int_env(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


API_BASE = os.environ.get("FIRST_AID_API_BASE", "https://app.salesanchor.jp/api/v1")
CONNECT_IP = os.environ.get("FIRST_AID_CONNECT_IP", "127.0.0.1")
ENV_FILE = os.environ.get("FIRST_AID_ENV_FILE", "/home/ubuntu/salesanchor/.env")
COMPOSE_DIR = os.environ.get("FIRST_AID_COMPOSE_DIR", "/home/ubuntu/salesanchor")
TEXTFILE_DIR = os.environ.get("FIRST_AID_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
ACTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "first_aid_actions.json")
RUN_PROM = "first_aid_run.prom"
ESCALATED_PROM = "first_aid_escalated.prom"

HTTP_TIMEOUT = 15
DOCKER_TIMEOUT = 20
RESTART_TIMEOUT = 150  # compose の stop_grace_period の最長 60s（docker-compose.yml:309）に余白
LIMIT_PER_HOUR = _int_env("FIRST_AID_LIMIT_PER_HOUR", 3)
FRESH_SECONDS = _int_env("FIRST_AID_FRESH_SECONDS", 300)
STALE_SECONDS = _int_env("FIRST_AID_STALE_SECONDS", 600)
HEALTHY_WAIT_SECONDS = _int_env("FIRST_AID_HEALTHY_WAIT_SECONDS", 180)
POLL_SECONDS = _int_env("FIRST_AID_POLL_SECONDS", 5)

NOTE_RESTART_PREFIX = "restart:start"
SERVICE_LABEL = "com.docker.compose.service"
ONEOFF_LABEL = "com.docker.compose.oneoff"
SERVICE_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
ESCALATED_LINE_RE = re.compile(
    r'^salesanchor_first_aid_escalated_timestamp_seconds\{service="([a-z0-9_-]{1,64})"\} ([0-9]+)$'
)


class ApiError(Exception):
    """保守 API が 200 以外を返した。文面に鍵と本文を入れない。"""


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """ホスト名（証明書の確かめと Host）は保ち、つなぐ先だけ connect_ip に固定する。"""

    def __init__(self, host: str, connect_ip: str, port: int, timeout: float):
        super().__init__(host, port=port, timeout=timeout, context=ssl.create_default_context())
        self._connect_ip = connect_ip
        self._ssl_ctx = ssl.create_default_context()

    def connect(self) -> None:
        sock = socket.create_connection((self._connect_ip, self.port), self.timeout)
        self.sock = self._ssl_ctx.wrap_socket(sock, server_hostname=self.host)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_api_time(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_docker_time(value: str) -> datetime:
    # docker の StartedAt は "2026-11-20T02:47:33.123456789Z"。秒までで足りる
    return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)


def read_token(path: str | None = None) -> str:
    with open(path or ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.startswith("OPS_API_TOKEN="):
                continue
            value = line[len("OPS_API_TOKEN="):].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            if value:
                return value
    raise ValueError("OPS_API_TOKEN not found in env file")


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    u = urllib.parse.urlsplit(API_BASE)
    if u.scheme == "https":
        conn: http.client.HTTPConnection = PinnedHTTPSConnection(
            u.hostname or "", CONNECT_IP, u.port or 443, HTTP_TIMEOUT
        )
    elif u.scheme == "http":  # 試験場の代わりの API だけ（tests/sandbox/first-aid.sh）
        conn = http.client.HTTPConnection(u.hostname or "", u.port or 80, timeout=HTTP_TIMEOUT)
    else:
        raise ValueError(f"unsupported scheme: {u.scheme}")
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        conn.request(method, u.path.rstrip("/") + path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
    finally:
        conn.close()
    if resp.status != 200:
        raise ApiError(f"{method} {path.split('?')[0]} -> HTTP {resp.status}")
    return json.loads(raw.decode("utf-8"))


def query(path: str, params: dict) -> str:
    return path + "?" + urllib.parse.urlencode(params)


def is_halted(token: str) -> bool:
    return bool(api("GET", "/ops/control", token).get("halt_all"))


def annotate(token: str, incident_id: str, note: str, **fields) -> None:
    body = {
        "kind": "first_aid",
        "note": note[:2000],
        "fields": {k: (iso(v) if isinstance(v, datetime) else v) for k, v in fields.items()},
    }
    api("POST", f"/ops/incidents/{incident_id}/events", token, body)


def load_actions(path: str | None = None) -> list[dict]:
    with open(path or ACTIONS_FILE, encoding="utf-8") as f:
        doc = json.load(f)
    if doc.get("version") != 1 or not isinstance(doc.get("actions"), list):
        raise ValueError("first_aid_actions.json: version 1 and actions list are required")
    for a in doc["actions"]:
        if set(a) != {"alertname", "service", "action"} or a["action"] != "compose_restart":
            raise ValueError(f"first_aid_actions.json: bad action {a!r}")
        if not SERVICE_RE.match(a["service"]):
            raise ValueError(f"first_aid_actions.json: bad service {a['service']!r}")
    return doc["actions"]


def labels_of(incident: dict) -> dict:
    labels = incident.get("labels") or {}
    if isinstance(labels, str):
        labels = json.loads(labels)
    return labels


def match_action(actions: list[dict], incident: dict) -> dict | None:
    service = labels_of(incident).get("service")
    for a in actions:
        if a["alertname"] == incident.get("alertname") and a["service"] == service:
            return a
    return None


def incident_id_of(incident: dict) -> str:
    return str(uuid.UUID(str(incident["id"])))


def docker_bin() -> str:
    return shutil.which("docker") or "/usr/bin/docker"


def run_docker(args: list[str]) -> str:
    return subprocess.run(
        [docker_bin(), *args], capture_output=True, text=True, timeout=DOCKER_TIMEOUT, check=True
    ).stdout


def read_containers(service: str) -> list[dict]:
    """動いているコンテナ（compose run の使い捨ては除く）の健康と起動時刻。"""
    ids = run_docker(["ps", "-q", "--filter", f"label={SERVICE_LABEL}={service}"]).split()
    if not ids:
        return []
    out = []
    for c in json.loads(run_docker(["inspect", *ids])):
        labels = (c.get("Config") or {}).get("Labels") or {}
        if str(labels.get(ONEOFF_LABEL, "")).lower() == "true":
            continue
        state = c.get("State") or {}
        out.append(
            {
                "health": (state.get("Health") or {}).get("Status", "none"),
                "started_at": state.get("StartedAt", ""),
                "restart_count": c.get("RestartCount", 0),
            }
        )
    return out


def state_text(containers: list[dict]) -> str:
    if not containers:
        return "missing"
    return ";".join(
        f"health={c['health']} started_at={c['started_at'][:19]} restart_count={c['restart_count']}"
        for c in containers
    )


def compose_restart(service: str) -> None:
    subprocess.run(
        [docker_bin(), "compose", "restart", service],
        cwd=COMPOSE_DIR,
        capture_output=True,
        text=True,
        timeout=RESTART_TIMEOUT,
        check=True,
    )


def write_atomic(name: str, body: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".first_aid.", dir=TEXTFILE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(tmp, 0o644)
        os.replace(tmp, os.path.join(TEXTFILE_DIR, name))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_run(halted: bool) -> None:
    write_atomic(
        RUN_PROM,
        "# HELP salesanchor_first_aid_last_run_timestamp_seconds Last time first_aid.py made progress.\n"
        "# TYPE salesanchor_first_aid_last_run_timestamp_seconds gauge\n"
        f"salesanchor_first_aid_last_run_timestamp_seconds {time.time():.0f}\n"
        "# HELP salesanchor_first_aid_halted 1 when ops_control.halt_all stopped first aid.\n"
        "# TYPE salesanchor_first_aid_halted gauge\n"
        f"salesanchor_first_aid_halted {1 if halted else 0}\n",
    )


def write_escalated(service: str, ts: float) -> None:
    if not SERVICE_RE.match(service):
        service = "unknown"
    values: dict[str, str] = {}
    try:
        with open(os.path.join(TEXTFILE_DIR, ESCALATED_PROM), encoding="utf-8") as f:
            for line in f:
                m = ESCALATED_LINE_RE.match(line.strip())
                if m:
                    values[m.group(1)] = m.group(2)
    except FileNotFoundError:
        pass
    values[service] = f"{ts:.0f}"
    lines = [
        "# HELP salesanchor_first_aid_escalated_timestamp_seconds Last time first aid called a human, by service.",
        "# TYPE salesanchor_first_aid_escalated_timestamp_seconds gauge",
    ]
    lines += [
        f'salesanchor_first_aid_escalated_timestamp_seconds{{service="{s}"}} {v}'
        for s, v in sorted(values.items())
    ]
    write_atomic(ESCALATED_PROM, "\n".join(lines) + "\n")


def restarts_last_hour(token: str, service: str) -> int:
    path = query(
        "/ops/events",
        {"kind": "first_aid", "service": service, "since": iso(now_utc() - timedelta(hours=1)), "limit": 100},
    )
    count = 0
    for e in api("GET", path, token)["items"]:
        detail = e.get("detail") or {}
        if isinstance(detail, str):
            detail = json.loads(detail)
        if str(detail.get("note") or "").startswith(NOTE_RESTART_PREFIX):
            count += 1
    return count


def wait_healthy(service: str) -> tuple[bool, str]:
    last = "unknown"
    for _ in range(max(1, HEALTHY_WAIT_SECONDS // POLL_SECONDS)):
        time.sleep(POLL_SECONDS)
        write_run(False)  # 待つ間も生きている印を書く（FirstAidStale が誤って鳴らない）
        try:
            containers = read_containers(service)
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            last = "error:" + type(e).__name__
            continue
        last = state_text(containers)
        if containers and all(c["health"] == "healthy" for c in containers):
            return True, last
    return False, last


def sweep_stale(token: str, actions: list[dict]) -> None:
    """開始の記録があって 10 分たっても終わりの記録が無い処置を escalated にする（係が途中で落ちたとき）。"""
    now = now_utc()
    path = query("/ops/incidents", {"since": iso(now - timedelta(hours=24)), "limit": 100})
    for inc in api("GET", path, token)["items"]:
        if not inc.get("first_aid_started_at") or inc.get("first_aid_done_at"):
            continue
        action = match_action(actions, inc)
        if action is None:
            continue
        if (now - parse_api_time(inc["first_aid_started_at"])).total_seconds() <= STALE_SECONDS:
            continue
        annotate(token, incident_id_of(inc), "escalated:stale", first_aid_done_at=now, first_aid_result="escalated")
        write_escalated(action["service"], now.timestamp())


def handle(token: str, action: dict, inc: dict) -> str:
    service = action["service"]
    inc_id = incident_id_of(inc)
    if is_halted(token):
        return "halted"
    if restarts_last_hour(token, service) >= LIMIT_PER_HOUR:
        t = now_utc()
        annotate(
            token, inc_id, "escalated:limit",
            first_aid_started_at=t, first_aid_done_at=t, first_aid_result="escalated",
        )
        write_escalated(service, t.timestamp())
        return "escalated_limit"
    containers = read_containers(service)
    if not any(c["health"] == "unhealthy" for c in containers):
        return "skip_not_unhealthy"
    t = now_utc()
    if any((t - parse_docker_time(c["started_at"])).total_seconds() < FRESH_SECONDS for c in containers):
        return "skip_fresh"
    annotate(token, inc_id, f"{NOTE_RESTART_PREFIX} before={state_text(containers)}", first_aid_started_at=t)
    write_run(False)
    t0 = time.monotonic()
    try:
        compose_restart(service)
        ok, after = wait_healthy(service)
    except (OSError, subprocess.SubprocessError) as e:
        ok, after = False, "restart_error:" + type(e).__name__
    secs = int(time.monotonic() - t0)
    result = "recovered" if ok else "not_recovered"
    done = now_utc()
    annotate(
        token, inc_id, f"restart:done result={result} after={after} secs={secs}",
        first_aid_done_at=done, first_aid_result=result,
    )
    if not ok:
        write_escalated(service, done.timestamp())
    return result


def main() -> int:
    try:
        token = read_token()
        if is_halted(token):
            write_run(True)
            return 0
        actions = load_actions()
        sweep_stale(token, actions)
        path = query("/ops/incidents", {"tier": "auto", "first_aid": "pending", "limit": 100})
        items = sorted(api("GET", path, token)["items"], key=lambda i: i.get("first_notified_at") or "")
        for inc in items:
            action = match_action(actions, inc)
            if action is None:
                continue
            if handle(token, action, inc) == "halted":
                write_run(True)
                return 0
            write_run(False)
        write_run(False)
        return 0
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, ApiError, http.client.HTTPException) as e:
        stamp = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"{stamp} first_aid failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
