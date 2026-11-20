# 実装カード 段階3 便G — 応急処置係（不健康なコンテナをその場で再起動する）

> この文書は何か：AI保守運用24時間化 段階3 便G の作業指示書です。便E で「コンテナが不健康」と見張りが鳴るようになりました。この便では、prod1 の「応急処置係」が毎分、鳴っている障害を保守 API から読み、決められた 4 つのコンテナに限って再起動し、直ったかどうかを障害記録に書きます。直らないとき・1 時間に 3 回を超えるとき・係が止まったときは、人を呼ぶ見張り（札 page）が鳴ります。

- 設計: docs/handoff/ai-ops-247/stage3-design.md §2 便G・§5・§6・§7 V2・V6
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階3
- 対象ADR: ADR-1012（本テーマ）
- 状態: 便の分け方は PO 承認 y（2026-10-16）。V6 は 2026-11-20 に○（§2-1 F15）。§2-2 の決定は Opus の技術判断（設計の目的・範囲を変えない）。実装の開始には PO の実装承認が要る
- 危険便: はい（`scripts/` を含む。ADR-135・ADR-136）。GO は「POの委任に基づくClaude Opus発行」で Opus が出し、マージと反映後の観測も Opus が行う。担当はマージしない
- 担当: 実装 Sonnet（クラウド）／審査・GO・マージ・反映確認 Opus／prod1 の crontab への 1 行追加と本番での 1 回の試しは PO の `!`

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○（まだ無いファイルのパスは「新設の」を付けてバッククォートなしで書く） |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（決めた 4 つのコンテナをその場で再起動し、結果を記録することだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§4-8 の expect と §5-3） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 47e7f505e で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番（prod1・prod2）には触らない | ○（§8 は Opus と PO） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階3 便G の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 応急処置係（新設の scripts/ops/first_aid.py）と処置の一覧（新設の scripts/ops/first_aid_actions.json）（§4-1・§4-2）
2. その試験（新設の scripts/tests/test_first_aid.py）と、CI で走らせる設定（`.github/workflows/deploy-script-test.yml`・`.github/workflows/monitoring-check.yml` に追記）（§4-3・§4-4）
3. ContainerUnhealthy の札を page から auto に変える・見張り 2 本（FirstAidEscalated・FirstAidStale）を足す（`monitoring/prometheus/alert_rules.yml`）（§4-5）
4. 見張りの単体試験（`monitoring/prometheus/tests/alert_rules_test.yml`）（§4-6）
5. 手順書（`docs/runbooks/alerts.md`）（§4-7）
6. GitHub の試験場（sandbox-test）で動かす試験（新設の tests/sandbox/first-aid.sh・新設の tests/sandbox/first_aid_stub.py・新設の tests/sandbox/first-aid-compose.yml）（§4-8）

入れない:
- 保守 API（`backend/app/routers/ops.py`）の変更（便F で済み。この便は読むだけ）
- 処置の一覧に 4 サービス以外を足すこと（backend・postgres・redis・nginx は載せない。設計 §2 便G）
- prod1 の crontab への登録（反映後に PO の `!` で行う。§8）
- Alertmanager の設定・`deploy.yml` の変更（deploy の migration の見張りは便H）

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 47e7f505e・生出力 /tmp/CC報告ファイル/ai-ops-stage3/bin-g-card/）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 障害の一覧 `GET /ops/incidents` は status・since（first_notified_at で絞る）・limit（1〜100）・tier（labels の tier）・first_aid=pending（firing で first_aid_started_at が空）で絞れ、first_notified_at の新しい順に `{"items":[...]}` を返す | `backend/app/routers/ops.py:292-328` |
| F2 | 出来事の一覧 `GET /ops/events` は kind・service（障害の labels の service）・since（occurred_at）・limit で絞れ、各行に id・incident_id・occurred_at・kind・actor・detail・alertname・service が入る | `backend/app/routers/ops.py:359-397` |
| F3 | 注記 `POST /ops/incidents/{id}/events` は `{"kind":"first_aid","note":(2000字まで),"fields":{...}}`。fields は first_aid_started_at・first_aid_done_at・first_aid_result（recovered／not_recovered／escalated）などで、知らない項目は 422。detail に `{"fields":[...],"note":...,"user_id":...}` が残る | `backend/app/routers/ops.py:400-411,458-470,478-541` |
| F4 | `GET /ops/control` は `{"halt_all": ...}` を返す（行が無いときは false） | `backend/app/routers/ops.py:738-756` |
| F5 | 保守 API の鍵は Bearer の OPS_API_TOKEN で、名乗りは actor `ops_token` になる | `backend/app/routers/ops.py:117-130` |
| F6 | API の道の頭は `/api/v1` | `backend/app/main.py:836` |
| F7 | prod1 の `/home/ubuntu/salesanchor/.env` に `OPS_API_TOKEN='...'`（単引用符つき）が deploy で書かれる。`COMPOSE_FILE` も同じ .env にある | `.github/workflows/deploy.yml:444,450`・`docker-compose.yml:142` |
| F8 | nginx は app.salesanchor.jp の正規の証明書を持ち、`/api/` を backend に渡す（毎秒 30 件の制限つき） | `nginx/nginx.conf:87,294-296` |
| F9 | deploy は既に prod1 の中から `--resolve app.salesanchor.jp:443:127.0.0.1` で自分自身を呼んでいる | `.github/workflows/deploy.yml:603` |
| F10 | deploy は prod1 で `git reset --hard origin/main` するので、scripts/ は配備で prod1 に届く | `.github/workflows/deploy.yml:320` |
| F11 | `docker compose restart` は `-t` を付けないとコンテナの `stop_grace_period` を使う（Context7 の docker compose の文書で確かめた）。compose の最長は 60s | `docker-compose.yml:174,309` |
| F12 | 状態書き係の型：textfile の置き場・docker の呼び方・ラベルでの探し方・一時ファイル→`os.replace`・失敗は標準エラーに 1 行で rc=1 | `scripts/ops/container_state.py:19` 以下 |
| F13 | Alertmanager は札で行き先を分けていない。札 auto でも Discord と障害記録の両方に届く | `monitoring/alertmanager/alertmanager.yml:7-10` |
| F14 | 見張りは 38 本。ContainerUnhealthy は札 page（コメントで「便G で auto に変える」）。札の値は検査が確かめる | `monitoring/prometheus/alert_rules.yml:334-347`・`monitoring/scripts/check_alert_rules.py:85-87` |
| F15 | V6 は○：2026-11-20T02:47:33Z の直近 24 時間、4 サービスとも `max_over_time(salesanchor_container_unhealthy[24h])` が 0（K3・K4 合格は 11/18） | /tmp/CC報告ファイル/ai-ops-stage3/v6-worker/v6-now.txt |
| F16 | 障害は (fingerprint, starts_at) で 1 行。同じ見張りが止んでからもう一度鳴ると別の行になる | `backend/app/routers/ops.py:185` |
| F17 | 試験場は `tests/sandbox/<test>.sh` を ubuntu-latest で動かす | `.github/workflows/sandbox-test.yml:8,19,30,36` |
| F18 | CI：`deploy-script-test.yml` の paths と手順、`monitoring-check.yml` の変更の判定と試験の実行に、便E の係の名前が並んでいる | `.github/workflows/deploy-script-test.yml:9-31,53-54`・`.github/workflows/monitoring-check.yml:30,69` |

### 2-2. 決めたこと（Opus）

- E1 呼ぶ先：設計 §2 便G は `api.salesanchor.jp` と書いたが、`https://app.salesanchor.jp/api/v1` を prod1 自身（127.0.0.1:443）に向けて呼ぶ。理由：deploy が同じ形で既に呼んでいる（F9）・証明書と `/api/` の道が実物で確かめられる（F8）。証明書の確かめは省かない（`-k` 相当にしない）。目的（ホスト名を保ち、行き先を prod1 に固定する）は変えない
- E2 再起動の待ち時間：`docker compose restart` に `-t` を付けず、compose の `stop_grace_period` を正とする（F11）。係の側の打ち切りは 150 秒
- E3 回数の上限の数え方：出来事の note が `restart:start` で始まるものだけを数える（再起動を始めた回数）。上限で止めたとき（`escalated:limit`）や終わりの記録（`restart:done`）は数えない
- E4 処置しない場合：今そのコンテナが不健康でない（もう直った）・起動から 5 分以内（deploy の作り直しと取り合わない）のときは注記も書かずに次の回へ回す。見張りが止めば障害は resolved になり一覧から消える。ただし回数の上限（E3）の判定は E4 より先に行う（上限に達していれば、もう健康でも `escalated:limit` を書く。§4-1 の handle・試験 #8・§4-8 の 4 はこの順を前提にしている）
- E5 生きている印：係は最後まで動いたとき、各障害の処置の後、健康になるのを待つ間の 5 秒ごとに `salesanchor_first_aid_last_run_timestamp_seconds` を書く。FirstAidStale は DockerdStateStale と同じ「5 分間値が変わらない、または値が無い」形（時計のずれで誤って鳴らない）・for 2m
- E6 FirstAidEscalated は「人を呼んだ時刻から 30 分」鳴る形（`time() - 時刻 < 1800`）。`changes()` にすると最初の 1 回目（系列が初めて現れたとき）に鳴らないため
- E7 止める札（halt_all）が立っているときは処置 0 件で、印には `salesanchor_first_aid_halted 1` を書く（止めている間に FirstAidStale が鳴らないように）。止める札は障害 1 件ごとにも読み直す
- E8 試験のためのつまみ：5 分・10 分・3 分・5 秒・1 時間 3 回は環境変数で変えられるが、本番の cron の行には何も付けない（初期値＝本番の値）
- E9 途中で止まった処置（開始の記録があり 10 分たっても終わりの記録が無い）を escalated にするのは、処置の一覧に載った障害だけ。二重起動は `flock -n` で防ぐ（§8）ので、10 分を超えて動き続ける係は無い

## 3. 触るファイル（これ以外は触らない）

| ファイル | 中身 |
|---|---|
| 新設の scripts/ops/first_aid.py | §4-1 の全体 |
| 新設の scripts/ops/first_aid_actions.json | §4-2 の全体 |
| 新設の scripts/tests/test_first_aid.py | §4-3 の試験 |
| `.github/workflows/deploy-script-test.yml` | §4-4 の追記 |
| `.github/workflows/monitoring-check.yml` | §4-4 の追記 |
| `monitoring/prometheus/alert_rules.yml` | §4-5 |
| `monitoring/prometheus/tests/alert_rules_test.yml` | §4-6 |
| `docs/runbooks/alerts.md` | §4-7 |
| 新設の tests/sandbox/first-aid.sh | §4-8 の全体 |
| 新設の tests/sandbox/first_aid_stub.py | §4-8 の全体 |
| 新設の tests/sandbox/first-aid-compose.yml | §4-8 の全体 |
| このカード | §13 の報告欄だけ |

## 4. 作り方

### 4-1. 新設の scripts/ops/first_aid.py（ファイル全体）

```python
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
```

### 4-2. 新設の scripts/ops/first_aid_actions.json（ファイル全体）

```json
{
  "version": 1,
  "actions": [
    {"alertname": "ContainerUnhealthy", "service": "celery-worker", "action": "compose_restart"},
    {"alertname": "ContainerUnhealthy", "service": "celery-beat", "action": "compose_restart"},
    {"alertname": "ContainerUnhealthy", "service": "discord-gateway", "action": "compose_restart"},
    {"alertname": "ContainerUnhealthy", "service": "gemini-egress", "action": "compose_restart"}
  ]
}
```

### 4-3. 新設の scripts/tests/test_first_aid.py

`scripts/tests/test_container_state.py` と同じく `unittest` で、`importlib` で `scripts/ops/first_aid.py` を読み込む。`api`・`read_containers`・`compose_restart`・`time.sleep` は `unittest.mock.patch.object` で差し替え、`TEXTFILE_DIR` は `tempfile.TemporaryDirectory()` に向ける。docker と通信は使わない。次の 19 件を書く（名前は `test_` ＋番号＋英小文字の説明。例 `test_05_recovers`）:

| # | 条件 | 確かめること |
|---|---|---|
| 1 | .env の行が `OPS_API_TOKEN='abc'`・`"abc"`・`abc` | `read_token` が 3 つとも `abc` |
| 2 | .env に OPS_API_TOKEN の行が無い／値が空 | `ValueError`。文面に .env のほかの行の値が入らない |
| 3 | 本物の first_aid_actions.json | 4 件・service が celery-worker・celery-beat・discord-gateway・gemini-egress |
| 4 | action が compose_restart 以外／キーが足りない | `load_actions` が `ValueError` |
| 5 | 止める札 true | `main()` が 0・`first_aid_run.prom` に `salesanchor_first_aid_halted 1`・`compose_restart` 0 回・障害の一覧を読まない |
| 6 | `/ops/control` が `ApiError` | `main()` が 1・`first_aid_run.prom` が無い・標準エラーが 1 行で鍵の文字列を含まない |
| 7 | 未処置 1 件（ContainerUnhealthy・celery-beat）・出来事 0 件・不健康で 1 時間前に起動→再起動後は健康 | `compose_restart("celery-beat")` 1 回。注記 2 回：1 回目は fields が `first_aid_started_at` だけで note が `restart:start` で始まる。2 回目は `first_aid_done_at` と `first_aid_result="recovered"`。`first_aid_escalated.prom` が無い |
| 8 | 出来事に note `restart:start ...` が 3 件 | 再起動 0 回・注記 1 回（note `escalated:limit`・result `escalated`・started と done の両方）・escalated の prom に celery-beat の行 |
| 9 | 出来事に note `restart:done ...` が 5 件・`escalated:limit` が 2 件 | 数は 0 として再起動する（数えるのは `restart:start` だけ） |
| 10 | 再起動後も不健康のまま（`HEALTHY_WAIT_SECONDS` を待ち切る） | result `not_recovered`・escalated の prom に celery-beat の行・`time.sleep` の回数が `HEALTHY_WAIT_SECONDS // POLL_SECONDS` |
| 11 | `compose_restart` が `subprocess.CalledProcessError` | result `not_recovered`・2 回目の注記の note に `restart_error:CalledProcessError` |
| 12 | コンテナが既に健康 | 注記 0 回・再起動 0 回 |
| 13 | 起動から 60 秒 | 注記 0 回・再起動 0 回 |
| 14 | service が backend／alertname が ContainerStateStale | 何もしない（control と一覧を読む以外の呼び出し 0 回） |
| 15 | labels が JSON の文字列で来る | 7 と同じく処置する |
| 16 | 掃除：開始 11 分前で終わり無し／開始 5 分前／終わり有り／一覧に無い alertname | 1 件目だけ注記（note `escalated:stale`・result `escalated`・done あり）・escalated の prom に書く |
| 17 | escalated の prom に celery-worker の行がある状態で gemini-egress を書く | 2 行とも残る・mode 644・`.first_aid.` で始まる一時ファイルが残らない |
| 18 | 処置の途中で止める札が立つ（1 回目の control は false・2 回目は true） | 再起動 0 回・`main()` が 0・`salesanchor_first_aid_halted 1` |
| 19 | `api` が `PinnedHTTPSConnection` を使う（`socket.create_connection` と `ssl.SSLContext.wrap_socket` を差し替え） | つなぐ先が `("127.0.0.1", 443)`・`server_hostname` が `app.salesanchor.jp`・応答 500 で `ApiError` の文面が `GET /ops/control -> HTTP 500` で鍵を含まない |

### 4-4. CI の追記

`.github/workflows/deploy-script-test.yml`：2 か所の paths の `'scripts/tests/test_dockerd_state.py'` の次の行に、同じ字下げで次の 3 行を足す。

```yaml
      - 'scripts/ops/first_aid.py'
      - 'scripts/ops/first_aid_actions.json'
      - 'scripts/tests/test_first_aid.py'
```

同じファイルの `run: python3 scripts/tests/test_dockerd_state.py` の次に空行を 1 つ置いて、次の手順を足す。

```yaml
      - name: Run first_aid tests
        run: python3 scripts/tests/test_first_aid.py
```

`.github/workflows/monitoring-check.yml`：30 行目の判定の正規表現の `|scripts/tests/test_dockerd_state\.py)` を `|scripts/tests/test_dockerd_state\.py|scripts/ops/first_aid\.py|scripts/ops/first_aid_actions\.json|scripts/tests/test_first_aid\.py)` に変える。69 行目の `python3 scripts/tests/test_dockerd_state.py -v` の次の行に同じ字下げで `python3 scripts/tests/test_first_aid.py -v` を足す。

### 4-5. `monitoring/prometheus/alert_rules.yml`

ContainerUnhealthy（337 行目付近）のコメントと札を変える。

```yaml
      # prod1 の scripts/ops/container_state.py が毎分 textfile に書く。札 auto：応急処置係（scripts/ops/first_aid.py・便G）が再起動する
      - alert: ContainerUnhealthy
        expr: salesanchor_container_unhealthy{service=~"celery-worker|celery-beat|discord-gateway|gemini-egress"} == 1
        for: 1m
        labels:
          severity: critical
          tier: auto
```

（337 行目の旧行は `# prod1 の scripts/ops/container_state.py が毎分 textfile に書く。札は処置の付く便G で auto に変える`。ほかの行は変えない）

ファイルの末尾（`dockerd_state_alerts` の後）に、空行を 1 つ置いて次のグループを足す。

```yaml
  - name: first_aid_alerts
    rules:
      # 応急処置で直らない・1 時間に 3 回を超えた・処置が途中で止まった（ADR-1012 段階3 便G）
      # prod1 の scripts/ops/first_aid.py が人を呼んだ時刻を service ごとに textfile に書く。30 分鳴って自然に止む
      - alert: FirstAidEscalated
        expr: (time() - salesanchor_first_aid_escalated_timestamp_seconds{instance="app-vps"}) < 1800
        for: 0m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "応急処置で {{ $labels.service }} が直りませんでした"
          description: "prod1 の応急処置係が {{ $labels.service }} を直せませんでした（再起動しても健康に戻らない・直近 1 時間に 3 回再起動した・処置が途中で止まった のどれか）。人が原因を見てください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#firstaidescalated"

      # 応急処置係が 5 分動いていない（cron の停止・保守 API に届かない・鍵が読めない）。止める札で止めている間は印を書くので鳴らない
      - alert: FirstAidStale
        expr: changes(salesanchor_first_aid_last_run_timestamp_seconds{instance="app-vps"}[5m]) == 0 or absent(salesanchor_first_aid_last_run_timestamp_seconds{instance="app-vps"})
        for: 2m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "応急処置係が 5 分以上動いていません"
          description: "prod1 の scripts/ops/first_aid.py が 5 分以上、最後まで動いていません。この間、コンテナが不健康になっても自動で再起動されません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#firstaidstale"
```

### 4-6. `monitoring/prometheus/tests/alert_rules_test.yml`

- 4 行目 `# 全 38 本が擬似の系列で鳴ること、tier と runbook_url が付くことを確かめる。` の 38 を 40 にする
- ContainerUnhealthyFiring（700 行目付近）の `tier: page` を `tier: auto` にする
- 末尾（DockerdStateFresh の後）に空行を 1 つ置いて次を足す

```yaml
  - name: FirstAidEscalatedFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_first_aid_escalated_timestamp_seconds{service="celery-beat",instance="app-vps",job="node-exporter"}'
        values: '240x10'
    alert_rule_test:
      - eval_time: 5m
        alertname: FirstAidEscalated
        exp_alerts:
          - exp_labels:
              service: celery-beat
              instance: app-vps
              job: node-exporter
              severity: critical
              tier: page
            exp_annotations:
              summary: "応急処置で celery-beat が直りませんでした"
              description: "prod1 の応急処置係が celery-beat を直せませんでした（再起動しても健康に戻らない・直近 1 時間に 3 回再起動した・処置が途中で止まった のどれか）。人が原因を見てください。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#firstaidescalated"

  - name: FirstAidEscalatedQuiet
    interval: 1m
    input_series:
      - series: 'salesanchor_first_aid_escalated_timestamp_seconds{service="celery-beat",instance="app-vps",job="node-exporter"}'
        values: '0x40'
    alert_rule_test:
      - eval_time: 40m
        alertname: FirstAidEscalated
        exp_alerts: []

  - name: FirstAidStaleFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_first_aid_last_run_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '60x20'
    alert_rule_test:
      - eval_time: 10m
        alertname: FirstAidStale
        exp_alerts:
          - exp_labels:
              instance: app-vps
              job: node-exporter
              severity: critical
              tier: page
            exp_annotations:
              summary: "応急処置係が 5 分以上動いていません"
              description: "prod1 の scripts/ops/first_aid.py が 5 分以上、最後まで動いていません。この間、コンテナが不健康になっても自動で再起動されません。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#firstaidstale"

  - name: FirstAidStaleAbsent
    interval: 1m
    input_series:
      - series: 'up{job="node-exporter",instance="app-vps"}'
        values: '1x20'
    alert_rule_test:
      - eval_time: 5m
        alertname: FirstAidStale
        exp_alerts:
          - exp_labels:
              instance: app-vps
              severity: critical
              tier: page
            exp_annotations:
              summary: "応急処置係が 5 分以上動いていません"
              description: "prod1 の scripts/ops/first_aid.py が 5 分以上、最後まで動いていません。この間、コンテナが不健康になっても自動で再起動されません。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#firstaidstale"

  - name: FirstAidFresh
    interval: 1m
    input_series:
      - series: 'salesanchor_first_aid_last_run_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '0+60x20'
    alert_rule_test:
      - eval_time: 16m
        alertname: FirstAidStale
        exp_alerts: []
```

### 4-7. `docs/runbooks/alerts.md`

- 3 行目の `（Prometheus 38 本）` を `（Prometheus 40 本）` にする
- 9 行目 `- \`auto\`：段階3 で自動の応急処置が付いたもの。今は該当なし。` を次の 1 行にする

```markdown
- `auto`：段階3 で自動の応急処置が付いたもの。prod1 の応急処置係（`scripts/ops/first_aid.py`）が処置の一覧（`scripts/ops/first_aid_actions.json`）に載ったものだけ処置し、結果を障害記録に書く。直らないときは FirstAidEscalated（page）で人を呼ぶ。今は ContainerUnhealthy の 4 サービスだけ。
```

- ContainerUnhealthy の節の `- 札：page（処置の付く段階3 便G で auto に変える）` を `- 札：auto（応急処置係が再起動する。段階3 便G）` に、`- 直し方：` の行を次の 1 行にする

```markdown
- 直し方：応急処置係が毎分、鳴っている件を読み、起動から 5 分を過ぎた不健康なコンテナを `docker compose restart` して最長 3 分、健康に戻るのを待つ。結果は障害記録の first_aid_result（recovered／not_recovered／escalated）に残る。直らない・1 時間に 3 回を超えたときは FirstAidEscalated が鳴るので、その節を見る。人が直すときは gemini-egress は prod2 の tinyproxy の状態も見る。
```

- 末尾（DockerdStateStale の節の後）に、空行を 1 つ置いて次の 2 節を足す

```markdown
## FirstAidEscalated

- 札：page
- 何が起きているか：prod1 の応急処置係（`scripts/ops/first_aid.py`）が、該当のサービスを直せなかった。次のどれか：再起動しても 3 分以内に健康に戻らない（not_recovered）・直近 1 時間に 3 回再起動していて 4 回目をしなかった（escalated:limit）・処置を始めてから 10 分たっても終わりの記録が無い（escalated:stale）。人を呼んだ時刻から 30 分鳴って自然に止む。
- 影響：ContainerUnhealthy の節と同じ。再起動で直らないので、止まったままの可能性が高い。
- 最初に見るもの：障害記録のその件の出来事（kind first_aid の note に、処置の前後の健康と所要秒が入っている）→ prod1 で `docker inspect -f '{{json .State.Health}}'`（該当のコンテナ）→ Loki の該当コンテナのログの直近。
- 直し方：原因を切り分けて Opus に報告する。同じサービスで繰り返すなら、健康診断の閾値か、コンテナの中の処理そのものを見直す。
- 止め方：`amtool silence add alertname=FirstAidEscalated --duration=PERIOD --comment=REASON`

## FirstAidStale

- 札：page
- 何が起きているか：prod1 の応急処置係が 5 分以上、最後まで動いていない、または値が無い状態が 2 分続いた。この間、コンテナが不健康になっても自動で再起動されない（ContainerUnhealthy は鳴る）。止める札（halt_all）で止めている間は印を書くので鳴らない。
- 最初に見るもの：prod1 の `crontab -l` に first_aid の行があるか → `/tmp/first-aid.log` の最後の行（失敗のときだけ書かれる。保守 API に届かない・鍵が読めない・docker が読めない など）→ `/home/ubuntu/node_exporter_textfile/first_aid_run.prom` の時刻。
- 直し方：ログの原因を切り分けて Opus に報告する。応急処置を急いで止めたいときは、保守 API の止める札を立てる。
- 止め方：`amtool silence add alertname=FirstAidStale --duration=PERIOD --comment=REASON`
```

### 4-8. GitHub の試験場の試験（新設 3 ファイル）

新設の tests/sandbox/first-aid-compose.yml（ファイル全体）:

```yaml
# ADR-1012 段階3 便G の試験場用（tests/sandbox/first-aid.sh が使う）。本番の 4 サービスと同じ名前で、健康診断を外から切り替えられる。
# /tmp/bad を作ると不健康、再起動で消える。flag/stuck-<service> を作ると再起動しても不健康のまま。
x-svc: &svc
  image: alpine:3.24
  command: ["sh", "-c", "rm -f /tmp/bad; exec sleep 3600"]
  stop_grace_period: 3s
  volumes:
    - ./flag:/flag:ro
  healthcheck:
    test: ["CMD-SHELL", "test ! -f /tmp/bad && test ! -f /flag/stuck-$${SVC}"]
    interval: 2s
    timeout: 2s
    retries: 1

services:
  celery-worker:
    <<: *svc
    environment: ["SVC=celery-worker"]
  celery-beat:
    <<: *svc
    environment: ["SVC=celery-beat"]
  discord-gateway:
    <<: *svc
    environment: ["SVC=discord-gateway"]
  gemini-egress:
    <<: *svc
    environment: ["SVC=gemini-egress"]
```

新設の tests/sandbox/first_aid_stub.py（ファイル全体）:

```python
#!/usr/bin/env python3
"""ADR-1012 段階3 便G の試験場用の保守 API の代わり（tests/sandbox/first-aid.sh が起動する）。

本物（backend/app/routers/ops.py）と同じ形で、応急処置係が使う 4 つの口だけを返す。
/admin/ の口は試験の台本が障害を作る・止める札を立てる・500 を返させるためのもの。
"""
import json
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PORT = int(sys.argv[1])
TOKEN = sys.argv[2]
LOCK = threading.Lock()
STATE = {"halt": False, "fail": False, "incidents": {}, "events": []}
FIELDS = {"first_aid_started_at", "first_aid_done_at", "first_aid_result"}


def now():
    return datetime.now(timezone.utc)


def parse(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def api_ready(self):
        if self.headers.get("Authorization") != "Bearer " + TOKEN:
            self.reply(401, {"detail": "unauthorized"})
            return False
        if STATE["fail"]:
            self.reply(500, {"detail": "forced"})
            return False
        return True

    def do_GET(self):
        u = urlsplit(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        with LOCK:
            if u.path == "/admin/health":
                return self.reply(200, {"ok": True})
            if u.path.startswith("/admin/incident/"):
                return self.reply(200, STATE["incidents"].get(u.path.rsplit("/", 1)[1], {}))
            if not self.api_ready():
                return None
            if u.path == "/api/v1/ops/control":
                return self.reply(200, {"halt_all": STATE["halt"]})
            if u.path == "/api/v1/ops/incidents":
                items = list(STATE["incidents"].values())
                if "since" in q:
                    items = [i for i in items if parse(i["first_notified_at"]) >= parse(q["since"])]
                if "tier" in q:
                    items = [i for i in items if i["labels"].get("tier") == q["tier"]]
                if q.get("first_aid") == "pending":
                    items = [i for i in items if i["status"] == "firing" and i["first_aid_started_at"] is None]
                items.sort(key=lambda i: i["first_notified_at"], reverse=True)
                return self.reply(200, {"items": items[: int(q.get("limit", "50"))]})
            if u.path == "/api/v1/ops/events":
                items = list(STATE["events"])
                if "kind" in q:
                    items = [e for e in items if e["kind"] == q["kind"]]
                if "service" in q:
                    items = [e for e in items if e["service"] == q["service"]]
                if "since" in q:
                    items = [e for e in items if parse(e["occurred_at"]) >= parse(q["since"])]
                items.sort(key=lambda e: e["occurred_at"], reverse=True)
                return self.reply(200, {"items": items[: int(q.get("limit", "50"))]})
            return self.reply(404, {"detail": "not found"})

    def do_POST(self):
        u = urlsplit(self.path)
        body = self.read_body()
        with LOCK:
            if u.path == "/admin/incident":
                t = now()
                inc_id = str(uuid.uuid4())
                offset = int(body.get("started_offset", 0))
                STATE["incidents"][inc_id] = {
                    "id": inc_id,
                    "alertname": body.get("alertname", "ContainerUnhealthy"),
                    "labels": {"service": body["service"], "tier": body.get("tier", "auto")},
                    "status": "firing",
                    "first_notified_at": t.isoformat(),
                    "first_aid_started_at": (t - timedelta(seconds=offset)).isoformat() if offset else None,
                    "first_aid_done_at": None,
                    "first_aid_result": None,
                }
                return self.reply(200, {"id": inc_id})
            if u.path in ("/admin/halt", "/admin/fail"):
                STATE[u.path.rsplit("/", 1)[1]] = bool(body.get("on"))
                return self.reply(200, {"ok": True})
            if not self.api_ready():
                return None
            parts = u.path.split("/")
            if len(parts) == 7 and parts[1:5] == ["api", "v1", "ops", "incidents"] and parts[6] == "events":
                inc = STATE["incidents"].get(parts[5])
                if inc is None:
                    return self.reply(404, {"detail": "OPS_INCIDENT_NOT_FOUND"})
                fields = body.get("fields") or {}
                if body.get("kind") != "first_aid" or not set(fields) <= FIELDS:
                    return self.reply(422, {"detail": "bad body"})
                inc.update(fields)
                STATE["events"].append(
                    {
                        "id": len(STATE["events"]) + 1,
                        "incident_id": inc["id"],
                        "occurred_at": now().isoformat(),
                        "kind": "first_aid",
                        "actor": "ops_token",
                        "detail": {"fields": sorted(fields), "note": body.get("note"), "user_id": None},
                        "alertname": inc["alertname"],
                        "service": inc["labels"]["service"],
                    }
                )
                return self.reply(200, {"incident_id": inc["id"], "updated_fields": sorted(fields)})
            return self.reply(404, {"detail": "not found"})


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
```

新設の tests/sandbox/first-aid.sh（ファイル全体）:

```bash
#!/bin/bash
# ADR-1012 段階3 便G: 応急処置係（scripts/ops/first_aid.py）と見張りを GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=first-aid
# 保守 API は tests/sandbox/first_aid_stub.py の代わりを使う。secrets・本番には触れない。後始末は trap で行う。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
PROM=prom/prometheus:v3.11.3
CD="$OUT/compose"
STUB=http://127.0.0.1:18080
TOKEN=sandbox-only-token-not-secret
STUB_PID=""
dc() { docker compose --project-directory "$CD" "$@"; }
cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    dc ps -a 2>&1 | head -20 || true
    tail -20 "$OUT/fa.err" 2>/dev/null || true
  fi
  dc down -t 1 >/dev/null 2>&1 || true
  [ -n "$STUB_PID" ] && kill "$STUB_PID" >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

field() { python3 -c 'import json,sys; v=json.load(sys.stdin).get(sys.argv[1]); print("" if v is None else v)' "$1"; }
new_inc() { curl -fsS -X POST -H 'Content-Type: application/json' -d "{\"service\":\"$1\",\"started_offset\":${2:-0}}" "$STUB/admin/incident" | field id; }
inc_field() { curl -fsS "$STUB/admin/incident/$1" | field "$2"; }
admin() { curl -fsS -X POST -H 'Content-Type: application/json' -d "{\"on\":$2}" "$STUB/admin/$1" >/dev/null; }
cid() { dc ps -q "$1"; }
health() { docker inspect -f '{{.State.Health.Status}}' "$(cid "$1")"; }
started() { docker inspect -f '{{.State.StartedAt}}' "$(cid "$1")"; }
wait_health() {
  for _ in $(seq 1 30); do
    [ "$(health "$1")" = "$2" ] && return 0
    sleep 1
  done
  echo "NG: $1 is not $2"
  return 1
}
fa() { python3 scripts/ops/first_aid.py 2>>"$OUT/fa.err"; }
ng() { echo "NG: $1"; exit 1; }

echo "== 1. 応急処置係の試験と見張りの検査"
python3 --version
python3 scripts/tests/test_first_aid.py
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml

echo "== 2. 代わりの保守 API と 4 つのコンテナを立てる"
python3 tests/sandbox/first_aid_stub.py 18080 "$TOKEN" >"$OUT/stub.log" 2>&1 &
STUB_PID=$!
for _ in $(seq 1 20); do curl -fsS "$STUB/admin/health" >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS "$STUB/admin/health" >/dev/null || ng "stub not up"
mkdir -p "$CD/flag" "$OUT/textfile"
cp tests/sandbox/first-aid-compose.yml "$CD/docker-compose.yml"
printf "COMPOSE_PROJECT_NAME=binfg\nOPS_API_TOKEN='%s'\n" "$TOKEN" >"$CD/.env"
dc up -d --wait
export FIRST_AID_API_BASE="$STUB/api/v1" FIRST_AID_ENV_FILE="$CD/.env" FIRST_AID_COMPOSE_DIR="$CD"
export FIRST_AID_TEXTFILE_DIR="$OUT/textfile" FIRST_AID_FRESH_SECONDS=0 FIRST_AID_HEALTHY_WAIT_SECONDS=60
export FIRST_AID_POLL_SECONDS=2 FIRST_AID_LIMIT_PER_HOUR=100

echo "== 3. 20 回：不健康にする → 係が再起動 → 5 分以内に recovered（19 回以上で合格）"
SERVICES=(celery-worker celery-beat discord-gateway gemini-egress)
ok=0
for i in $(seq 0 19); do
  s=${SERVICES[$((i % 4))]}
  dc exec -T "$s" touch /tmp/bad
  wait_health "$s" unhealthy
  id=$(new_inc "$s")
  t0=$(date +%s)
  fa || ng "rc at round $i"
  secs=$(( $(date +%s) - t0 ))
  r=$(inc_field "$id" first_aid_result)
  echo "round=$i service=$s result=$r secs=$secs"
  if [ "$r" = recovered ] && [ "$secs" -le 300 ] && [ "$(health "$s")" = healthy ]; then ok=$((ok + 1)); fi
done
echo "recovered=$ok/20"
[ "$ok" -ge 19 ] || ng "recovered $ok/20"

echo "== 4. 回数の上限：直近 1 時間に 5 回 → 再起動せず escalated"
before=$(started celery-worker)
id=$(new_inc celery-worker)
FIRST_AID_LIMIT_PER_HOUR=3 fa || ng "rc limit"
[ "$(inc_field "$id" first_aid_result)" = escalated ] || ng "limit result"
[ "$(started celery-worker)" = "$before" ] || ng "restarted over limit"
grep -qx 'salesanchor_first_aid_escalated_timestamp_seconds{service="celery-worker"} [0-9]*' "$OUT/textfile/first_aid_escalated.prom" || ng "escalated line celery-worker"

echo "== 5. 止める札：処置 0 件 → 札を外すと処置する"
admin halt true
dc exec -T celery-beat touch /tmp/bad
wait_health celery-beat unhealthy
before=$(started celery-beat)
id=$(new_inc celery-beat)
fa || ng "rc halt"
[ "$(started celery-beat)" = "$before" ] || ng "restarted while halted"
[ -z "$(inc_field "$id" first_aid_started_at)" ] || ng "annotated while halted"
grep -qx 'salesanchor_first_aid_halted 1' "$OUT/textfile/first_aid_run.prom" || ng "halted line"
admin halt false
fa || ng "rc after halt"
[ "$(inc_field "$id" first_aid_result)" = recovered ] || ng "not recovered after halt"
grep -qx 'salesanchor_first_aid_halted 0' "$OUT/textfile/first_aid_run.prom" || ng "halted 0 line"

echo "== 6. 保守 API が 500：rc=1・再起動しない・印を書かない"
admin fail true
dc exec -T discord-gateway touch /tmp/bad
wait_health discord-gateway unhealthy
before=$(started discord-gateway)
id=$(new_inc discord-gateway)
run_before=$(sha256sum "$OUT/textfile/first_aid_run.prom")
set +e
fa
rc=$?
set -e
echo "rc=$rc"
[ "$rc" -eq 1 ] || ng "rc on 500"
[ "$(started discord-gateway)" = "$before" ] || ng "restarted on 500"
[ "$(sha256sum "$OUT/textfile/first_aid_run.prom")" = "$run_before" ] || ng "run prom changed on 500"
admin fail false
fa || ng "rc after fail"
[ "$(inc_field "$id" first_aid_result)" = recovered ] || ng "not recovered after fail"

echo "== 7. 再起動しても直らない：not_recovered → escalated の行"
touch "$CD/flag/stuck-gemini-egress"
wait_health gemini-egress unhealthy
id=$(new_inc gemini-egress)
FIRST_AID_HEALTHY_WAIT_SECONDS=10 fa || ng "rc stuck"
[ "$(inc_field "$id" first_aid_result)" = not_recovered ] || ng "stuck result"
grep -qx 'salesanchor_first_aid_escalated_timestamp_seconds{service="gemini-egress"} [0-9]*' "$OUT/textfile/first_aid_escalated.prom" || ng "escalated line gemini-egress"
grep -qx 'salesanchor_first_aid_escalated_timestamp_seconds{service="celery-worker"} [0-9]*' "$OUT/textfile/first_aid_escalated.prom" || ng "escalated merge lost celery-worker"
rm -f "$CD/flag/stuck-gemini-egress"

echo "== 8. 途中で止まった処置：11 分前に始めて終わりが無い → escalated・5 分前のものはそのまま"
old=$(new_inc celery-beat 660)
young=$(new_inc celery-beat 300)
fa || ng "rc stale"
[ "$(inc_field "$old" first_aid_result)" = escalated ] || ng "stale not escalated"
[ -z "$(inc_field "$young" first_aid_done_at)" ] || ng "young touched"

echo "== 9. 書いたファイルの形・鍵が出ていないこと"
cat "$OUT/textfile/first_aid_run.prom" "$OUT/textfile/first_aid_escalated.prom"
for f in first_aid_run.prom first_aid_escalated.prom; do
  docker run --rm -i --entrypoint promtool "$PROM" check metrics <"$OUT/textfile/$f"
  [ "$(stat -c %a "$OUT/textfile/$f")" = 644 ] || ng "mode $f"
done
if ls -A "$OUT/textfile" | grep -q '^\.first_aid\.'; then ng "temp left"; fi
wc -l "$OUT/fa.err"
if grep -qF "$TOKEN" "$OUT/fa.err"; then ng "token in stderr"; fi
echo "ALL OK"
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-g-impl/ に置く）

5-1. 試験：作業場所で `python3 scripts/tests/test_first_aid.py 2>&1 | tail -15` が `OK`（19 件）。python3 の版も `python3 --version` で記録する（標準ライブラリだけなので venv は作らない）
5-2. GitHub の試験場で試す（Mac で仮想マシンやコンテナを動かさない）:
- §10 の push の後に、作業場所で `gh workflow run sandbox-test.yml --ref release/ai-ops-first-aid-bin-g -f test=first-aid` を実行し、10 秒後に `gh run list --workflow sandbox-test.yml --branch release/ai-ops-first-aid-bin-g -L 1 --json databaseId,url,status` の出力を貼る
- 結果は待たない（Opus が見る）。報告に run の URL を書く
- 中身（§4-8）：試験 19 件・見張りの検査と単体試験・20 回の再起動（19 回以上 recovered・各 5 分以内）・回数の上限・止める札・API の 500・直らないとき・途中で止まった処置・ファイルの形と鍵が出ていないこと。最後に `ALL OK` が出れば合格
5-3. 差分：`git diff origin/main --stat` が §3 のファイルだけ。加えて `git diff origin/main | grep -E '^-' | grep -v '^--- '` の出力が次の 10 行だけ（`- ` で始まる箇条の旧行も数えるため、`^-[^-]` は使わない）：alert_rules.yml 2 行（ContainerUnhealthy のコメントの旧行・`tier: page`）／alert_rules_test.yml 2 行（4 行目の旧行・ContainerUnhealthyFiring の `tier: page`）／alerts.md 4 行（3 行目・9 行目・ContainerUnhealthy の節の札と直し方の旧行）／monitoring-check.yml 1 行（30 行目の旧行）／このカード 1 行（§13 の「（未記入）」）。数が違うときは、その行の原文を貼る
5-4. 書式の手元確認：`bash -n tests/sandbox/first-aid.sh; echo rc=$?` が `rc=0`、`python3 -m py_compile scripts/ops/first_aid.py scripts/tests/test_first_aid.py tests/sandbox/first_aid_stub.py; echo rc=$?` が `rc=0`、`python3 -c "import json; print(len(json.load(open('scripts/ops/first_aid_actions.json'))['actions']))"` が `4`
5-5. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI と試験場の結果は Opus が見る）

## 6. 分岐ごとの対処

- §4 の目印の行が見つからない（ほかの PR が先に変えた）→ `git show origin/main:docs/runbooks/alerts.md | tail -20` のように該当のファイルを読み直し、同じ意味の位置に足す。本数（38）が既に別の数に変わっていたら、`python3 monitoring/scripts/check_alert_rules.py` の出力の本数に合わせる。決められなければ NEEDS_DECISION: で出力を貼る
- §5-2 の `gh workflow run` が権限や名前の誤りで起動しない → 出力の原文を貼り、PR は作って報告する（Opus が起動する）
- 試験が落ちる → 試験ではなく §4 の完成形との違いを直す。§4 のとおりで落ちるなら原文を貼って BLOCKED:
- §4-1 の完成形に誤りと思われる箇所がある → 直さずに NEEDS_DECISION: で、行と理由を書く

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 応急処置係の試験 19 件が pass | §5-1 と CI（deploy-script-test・monitoring-check） |
| 見張りが検査を通り、単体試験（既存を含め全部）が pass。ContainerUnhealthy の札が auto | 試験場（§5-2）と CI（monitoring-check） |
| 手元相当（試験場）で 20 回中 19 回以上、不健康にしてから 5 分以内に recovered | 試験場の記録の `recovered=N/20` |
| 止める札が立っている間・保守 API に届かない間は再起動 0 回 | 試験場の §4-8 の 5・6 |
| 直らない・回数の上限・途中で止まった処置で escalated の行が書かれる | 試験場の §4-8 の 4・7・8 |
| 鍵が標準エラーにもファイルにも出ない | 試験場の §4-8 の 9 と試験 #6・#19 |
| 触ったファイルが §3 だけ | §5-3 |
| 本番：cron 登録の後、`salesanchor_first_aid_last_run_timestamp_seconds` が毎分変わり、FirstAidStale が鳴っていない | §8-5 の Prometheus の問い合わせの生出力 |
| 本番：celery-beat を 1 回だけ不健康にし、不健康になってから 5 分以内に healthy に戻り、障害記録の first_aid_result が recovered | §8-6 の生出力（障害記録の時刻と docker の健康の記録） |
| 悪化 0 件：本番の 1 回の処置の後 30 分に、prod1 で新しく鳴った障害記録が 0 件（その件の resolved を除く） | §8-6 の `GET /ops/incidents?since=` の生出力 |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 の完成形と照らし、CI と試験場（§5-2）が緑なら、危険 PR の GO 手順（ADR-136）で「POの委任に基づくClaude Opus発行」の GO を PR に記録してマージする
2. deploy.yml の成功を Actions の記録で確かめる。prod2 の Prometheus の `/api/v1/rules` に FirstAidEscalated・FirstAidStale があり、ContainerUnhealthy の札が auto であることを確かめる
3. 届いた後、FirstAidStale は値が無い（absent）ので 2 分後から鳴る。マージの前に §8-4 の台本を用意しておき、deploy の成功の直後に PO に頼む。鳴った場合は登録後に止むことを確かめる
4. PO の `!` スクリプトで prod1 の crontab に 1 行足す。中身：①`crontab -l > /home/ubuntu/crontab.bak-first-aid` で控え ②`env -i PATH=/usr/bin:/bin /usr/bin/flock -n /tmp/first-aid.lock /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/first_aid.py; echo rc=$?` で cron と同じ条件で 1 回試す（rc=0 でなければ登録しない。証明書の確かめで失敗したら、確かめを外さずに止めて Opus に戻す。この 1 回でも、その時に鳴っている件があれば本当に処置する）③`* * * * * /usr/bin/flock -n /tmp/first-aid.lock /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/first_aid.py >> /tmp/first-aid.log 2>&1` を足す（同じ行が既にあれば足さない）④`crontab -l | grep first_aid` と `first_aid_run.prom` の中身を出す
5. 登録の 5 分後に、prod2 の Prometheus に `salesanchor_first_aid_last_run_timestamp_seconds`・`changes(salesanchor_first_aid_last_run_timestamp_seconds[5m])`・`ALERTS{alertname=~"FirstAid.*"}` を問い合わせる（読むだけ）
6. 本番での 1 回の試し：PO に日時を伝えてから 1 回（設計 §6・親設計 :187）。PO の `!` で celery-beat の中の beat の処理を `kill -STOP` して不健康にし（便D の試験と同じやり方）、応急処置係が再起動するのを待つ。生出力：障害記録のその件（first_notified_at・first_aid_started_at・first_aid_done_at・first_aid_result と出来事の note）・`docker inspect` の健康の記録・その後 30 分の `GET /ops/incidents?since=` の件数。5 分を超えた・recovered でない・悪化が 1 件でもあれば、cron の行を外して（控えから戻す）原因を調べる
7. 生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-g-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：再起動の間（最長でコンテナの停止の猶予 60 秒＋起動）は、そのサービスの処理（LINE 解析・翻訳・定期の集計・Discord の受信）が止まる。不健康のまま放置するより短い。1 時間に 3 回を超える再起動はしない
- 弊害：deploy の作り直しの最中に重なると、作り直したばかりのコンテナには「起動から 5 分」の条件で触らない。作り直しの前の古いコンテナを再起動する可能性は残る（deploy は同じサービスを止めて作り直すので、結果は deploy の側が勝つ）
- 弊害：ContainerUnhealthy の札が page から auto に変わる。Alertmanager は札で行き先を分けていない（F13）ので、Discord への通知は今までどおり届く。直らないときは FirstAidEscalated（page）がもう一度知らせる
- 弊害：prod1 の nginx の `/api/` の制限（毎秒 30 件）に対し、係は 1 回に数件しか呼ばない
- 急いで止める：保守 API の止める札（halt_all）を立てる（処置 0 件になり、FirstAidStale も鳴らない）
- 戻し方：PO の `!` で prod1 の crontab から first_aid の行を消す（控えから戻す）→ この PR の revert を main にマージ → 次の deploy で係と見張りが外れ、ContainerUnhealthy の札が page に戻る。`first_aid_run.prom`・`first_aid_escalated.prom` は revert の後に PO の `!` で消す（残すと最後の値が読まれ続ける）

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-first-aid-bin-g --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16・10-17・11-20 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-first-aid-bin-g` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う（クラウドで動くときは、クラウドの作業場所の手順に従い、同じブランチ名で作る）
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-first-aid-bin-g -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-first-aid-bin-g --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage3-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: scripts/ops/first_aid.py, scripts/ops/first_aid_actions.json, scripts/tests/test_first_aid.py, tests/sandbox/first-aid.sh, tests/sandbox/first_aid_stub.py, tests/sandbox/first-aid-compose.yml, .github/workflows/deploy-script-test.yml, .github/workflows/monitoring-check.yml, monitoring/prometheus/alert_rules.yml, monitoring/prometheus/tests/alert_rules_test.yml, docs/runbooks/alerts.md, docs/handoff/ai-ops-247/card-stage3-bin-g.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（alert_rules.yml・alert_rules_test.yml・alerts.md・monitoring-check.yml と、§13 の「（未記入）」を書き換えるこのカード））
- 本文に「危険 PR（scripts/）。GO・マージと反映後の観測は Opus がカード §8 の順で行う」と 1 行書く
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力（長いものは生出力のパスと要点の行）／PR の URL／試験場の run の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage3/bin-g-impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep は §5-2 の run の一覧を読む前の 10 秒にだけ使ってよい。CI・試験場・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

本報告はカード 段階3 便G の実行結果である。

- 場所: release/ai-ops-first-aid-bin-g（origin/main d4bea69c1 起点）
- §5-1: python3 3.11.18。`python3 scripts/tests/test_first_aid.py` は 19 件 OK
- §5-3: 差分は §3 の 11 ファイル＋このカード。削除行は alert_rules.yml 2・alert_rules_test.yml 2・alerts.md 4・monitoring-check.yml 1・このカード 1 の 10 行
- §5-4: `bash -n` rc=0・`py_compile` rc=0・first_aid_actions.json の actions は 4
- §5-2・§5-5 は指示によりしていない（試験場・PR は Opus）
- 判断した点: §4-3 の試験 19 件は表の条件どおりに新規に書いた（完成形の本文が無いため）。python3 が 3.12 ではなく 3.11.18 の環境で確かめた。§4 の完成形に誤りと思える箇所は見つからなかった

END OF CARD
