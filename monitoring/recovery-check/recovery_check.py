"""復旧後の点検の判定部品（outage-recovery-watch 便2）。

標準ライブラリだけで書く。ネットワークに触る関数（http_get・prom_query）は
run_check / server_responding に引数で渡すので、試験では偽物に差し替えられる。
"""
import json
import logging
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("recovery-check")

APP_URL = os.environ.get("APP_URL", "https://app.salesanchor.jp/")
API_HEALTH_URL = os.environ.get("API_HEALTH_URL", "https://api.salesanchor.jp/api/health")
LP_URL = os.environ.get("LP_URL", "https://salesanchor.jp/")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://prometheus:9090")

# (item, item_ja)。この順・この名前
ITEMS = [
    ("app", "アプリ画面"),
    ("api", "API"),
    ("database", "データベース"),
    ("redis", "Redis"),
    ("celery", "裏方の処理の受け手"),
    ("lp", "紹介ページ"),
    ("prometheus", "監視の読み取り"),
    ("clock", "本番サーバーの時計"),
    ("celery_heartbeat", "裏方の処理"),
    ("container_state", "コンテナの状態記録"),
]

CLOCK_EXPR = (
    'abs(node_time_seconds{job="node-exporter",instance="app-vps"} '
    '- timestamp(node_time_seconds{job="node-exporter",instance="app-vps"}))'
)
HEARTBEAT_EXPR = 'time() - max(celery_heartbeat_last_success_timestamp_seconds{job="backend"})'
CONTAINER_EXPR = (
    'time() - max(salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps"})'
)

CLOCK_LIMIT_SEC = 60
HEARTBEAT_LIMIT_SEC = 600
CONTAINER_LIMIT_SEC = 300

STATE_KEYS = (
    "phase",
    "ng_streak",
    "attempt",
    "next_check_at",
    "failed_items",
    "passed_until",
    "last_poll_at",
)


def http_get(url):
    """GET して (status, body) を返す。つながらないときは (None, b"")。"""
    req = urllib.request.Request(url, headers={"User-Agent": "salesanchor-recovery-check/1"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body
    except Exception:
        return None, b""


def prom_query(expr):
    """Prometheus の即時問い合わせ。値の並び、または失敗なら None。"""
    url = PROMETHEUS_URL + "/api/v1/query?query=" + urllib.parse.quote(expr, safe="")
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read())
        if data.get("status") != "success":
            return None
        return [float(r["value"][1]) for r in data["data"]["result"]]
    except Exception:
        return None


def _parse_health(body):
    """health 本文を dict で返す。JSON の object でなければ None。"""
    try:
        data = json.loads(body)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def run_check(get, query):
    """NG の item の並びを返す。全部 OK なら空。判定しない項目は入れない。"""
    ng = set()

    app_status, _ = get(APP_URL)
    if app_status != 200:
        ng.add("app")

    api_status, api_body = get(API_HEALTH_URL)
    if api_status != 200:
        ng.add("api")
    health = _parse_health(api_body) if api_body else None
    if health is None or "database" not in health or health.get("database") != "connected":
        ng.add("database")
    else:
        if health.get("redis") != "connected":
            ng.add("redis")
        if health.get("celery") != "connected":
            ng.add("celery")

    lp_status, _ = get(LP_URL)
    if lp_status != 200:
        ng.add("lp")

    clock_vals = query(CLOCK_EXPR)
    hb_vals = query(HEARTBEAT_EXPR)
    cs_vals = query(CONTAINER_EXPR)
    if clock_vals is None or hb_vals is None or cs_vals is None:
        ng.add("prometheus")
    else:
        if not clock_vals or not all(v < CLOCK_LIMIT_SEC for v in clock_vals):
            ng.add("clock")
        else:
            if len(hb_vals) != 1 or not hb_vals[0] < HEARTBEAT_LIMIT_SEC:
                ng.add("celery_heartbeat")
            if len(cs_vals) != 1 or not cs_vals[0] < CONTAINER_LIMIT_SEC:
                ng.add("container_state")

    return [item for item, _ in ITEMS if item in ng]


def server_responding(get):
    """本番の本体が応答したか。値（database 等）では判定しない。"""
    status, body = get(API_HEALTH_URL)
    if status is not None and body:
        health = _parse_health(body)
        if health is not None and "status" in health:
            return True
    app_status, _ = get(APP_URL)
    return app_status == 200


def initial_state(now=0):
    return {
        "phase": "ok",
        "ng_streak": 0,
        "attempt": 0,
        "next_check_at": 0,
        "failed_items": [],
        "passed_until": 0,
        "last_poll_at": now,
    }


def _checking_step(state, now, check):
    if now < state["next_check_at"]:
        return
    result = check()
    state["attempt"] += 1
    if not result:
        state["passed_until"] = now + 600
        state["phase"] = "ok"
        state["ng_streak"] = 0
        state["failed_items"] = []
    elif state["attempt"] >= 4:
        state["failed_items"] = list(result)
        state["phase"] = "failed"
        state["next_check_at"] = now + 300
    else:
        state["next_check_at"] = now + 110


def tick(state, now, responding, check, simulate_down):
    """1 回分の進め方。新しい state を返す。"""
    if state is None:
        return initial_state(now)
    state = dict(state)
    state["failed_items"] = list(state.get("failed_items", []))

    if simulate_down:
        state["phase"] = "down"
        state["ng_streak"] = 0
        state["last_poll_at"] = now
        return state

    if state["phase"] == "ok" and now - state["last_poll_at"] > 300:
        state["phase"] = "checking"
        state["attempt"] = 0
        state["next_check_at"] = now
        state["last_poll_at"] = now
        return state

    phase = state["phase"]
    if phase == "ok":
        if responding:
            state["ng_streak"] = 0
        else:
            state["ng_streak"] += 1
            if state["ng_streak"] >= 2:
                state["phase"] = "down"
    elif phase == "down":
        if responding:
            state["phase"] = "checking"
            state["attempt"] = 0
            state["next_check_at"] = now
            _checking_step(state, now, check)
    elif phase == "checking":
        _checking_step(state, now, check)
    elif phase == "failed":
        if now >= state["next_check_at"]:
            result = check()
            if not result:
                state["failed_items"] = []
                state["phase"] = "ok"
                state["ng_streak"] = 0
            else:
                state["failed_items"] = list(result)
                state["next_check_at"] = now + 300

    state["last_poll_at"] = now
    return state


def load_state(path):
    """状態ファイルを読む。無い・壊れている・キーが欠けているときは None。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        log.warning("state file unreadable; treating as first run")
        return None
    if not isinstance(data, dict) or any(k not in data for k in STATE_KEYS):
        log.warning("state file missing keys; treating as first run")
        return None
    return {k: data[k] for k in STATE_KEYS}


def save_state(path, state):
    """同じディレクトリの一時ファイルに書いて os.replace で置き換える。"""
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
