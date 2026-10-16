# 実装カード 段階3 便D — 4 サービスに健康診断を付ける

> この文書は何か：AI保守運用24時間化 段階3 便D の作業指示書です。今は「動いているか固まっているか」を Docker が判定できない 4 つのコンテナ（celery-worker・celery-beat・discord-gateway・gemini-egress）に、健康診断（healthcheck）を付けます。この便は診断を付けるだけで、不健康になっても何もしません（記録は便E、処置は便G）。

- 設計: docs/handoff/ai-ops-247/stage3-design.md §2 便D・§5・§6・§7 V1
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階3
- 対象ADR: ADR-1012（本テーマ）
- 状態: 便の分け方は PO 承認 y（2026-10-16）。このカードの §2-2 の方式の決定は Opus の技術判断（設計の目的・範囲を変えない。stage3-design.md §7 V1 の解決）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。マージと反映後の観測は Opus が行う。担当はマージしない
- 担当: 実装 Sonnet／審査・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○（まだ無いファイルのパスは「新設の」を付けてバッククォートなしで書く） |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（健康診断を付けることだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§5-5） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 38613d63f で確かめた） |
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

作業を始める前に、報告の冒頭へ「本報告はカード 段階3 便D の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 生きている印を書く小さな部品（新設の backend/app/container_alive.py・backend/app/celery_alive.py）（§4-1・§4-2）
2. worker に印を書く仕組みを登録（`backend/app/celery_app.py` の末尾に追記）（§4-3）
3. discord-gateway に印を書く定期処理（`backend/app/discord_gateway/main.py`）（§4-4）
4. `docker-compose.yml` の 4 サービスに healthcheck、celery-beat の command に scheduler の指定（§4-5）
5. 試験 2 本（新設の backend/tests/test_celery_alive.py・backend/tests/test_discord_gateway_alive.py）（§4-6）

入れない:
- 不健康を記録する・知らせる仕組み（便E）、再起動する仕組み（便G）
- `deploy.yml` の変更（健康を待つのは backend だけで、4 サービスは待たない。F7）
- prod2 の tinyproxy の設定の変更
- celery の `-E`（events）の追加

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 38613d63f・生出力 /tmp/CC報告ファイル/ai-ops-stage3/bin-d-recon.md・bin-d-recon2.md・bin-d-recon3.md）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 4 サービスに healthcheck が無い。worker の command は `celery -A app.celery_app worker --loglevel=info --concurrency=2`、beat は `celery -A app.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule`、gateway は `python -m app.discord_gateway.main` | `docker-compose.yml:214`・`:296`・`:333` |
| F2 | 3 サービスは backend のイメージ（python:3.12-slim、appuser で動く）で、`/tmp` は tmpfs（worker 64M・beat 16M・gateway 16M） | `backend/Dockerfile:1,28-29`・`docker-compose.yml:288-289`・`:321-322`・`:365-366` |
| F3 | gemini-egress は alpine:3.24＋openssh-client で、`-N -L 0.0.0.0:18888:127.0.0.1:8888` で prod2 の tinyproxy に中継する。2026-10-02 から Gemini は直接接続が既定で、中継は緊急用に起動したまま残している | `monitoring/prod1/gemini-egress/Dockerfile:3-5`・`docker-compose.yml:379-400`・`:96-100` |
| F4 | prod2 の tinyproxy は `Listen 127.0.0.1`・`Allow 127.0.0.1`・`FilterDefaultDeny Yes`・許可先は generativelanguage.googleapis.com だけ。`StatHost` の行は無い（公式文書では既定値 `tinyproxy.stats`。その宛先への要求には転送せず統計ページを返す） | `monitoring/prod2/gemini-egress/tinyproxy/tinyproxy.conf:1-11`・tinyproxy 公式文書（bin-d-recon2.md Q6） |
| F5 | backend の既存の healthcheck は interval 30s・timeout 10s・retries 3・start_period 15s | `docker-compose.yml:151-156` |
| F6 | celery 公式の拡張の例（DeadlockDetection）は、`StartStopStep` を継承し、`requires` に Timer を入れ、`start` で `worker.timer.call_repeatedly` を予約し、`stop` で取り消す。登録は `app.steps['worker'].add(クラス)` | celery 公式 extending（bin-d-recon2.md Q8） |
| F7 | `celery beat -S`（`--scheduler`）で scheduler のクラスを指定できる。既定は `celery.beat:PersistentScheduler` | celery 公式 configuration・cli（bin-d-recon2.md Q8） |
| F8 | beat の予定には 60 秒ごとのもの（heartbeat と閲覧ページの作り置き）が 2 つある | `backend/app/celery_app.py:177-185` |
| F9 | deploy は 4 サービスを `up -d --no-deps` で起こすだけで、健康を待つのは backend だけ（`docker exec ... /api/health` を最大 36 回） | `.github/workflows/deploy.yml:419`・`:632-645` |
| F10 | リポジトリに、4 サービスの健康状態を読むものは無い | bin-d-recon3.md Q2 |
| F11 | gateway は token が無いとき `stop_event.wait()` で待つ。あるときは `run_gateway` のタスクと待ちを並べる | `backend/app/discord_gateway/main.py:40-101` |
| F12 | 手元の Mac に Docker Desktop は無いが colima がある（`/opt/homebrew/bin/colima`）。過去に専用 profile を作って試験し、終わったら消した記録がある | bin-d-recon2.md Q9・`docs/ai-agents/evidence-registry.md:3230` |

### 2-2. 方式の決定（Opus・stage3-design.md §7 V1 の解決）

| # | 決めたこと | 理由 |
|---|---|---|
| D1 | 3 つの python のサービスは「生きている印」のファイルを `/tmp` に置き、本体の処理の中から定期的に更新する。健康診断は、その更新時刻の古さを `sh`・`date`・`stat` だけで見る | 本体が固まると印が古くなる。健康診断のたびに python を起動しない（メモリの上限が 128M の beat もある） |
| D2 | worker は bootstep を足し、worker の timer で 30 秒ごとに印を更新する（F6 の型）。120 秒古ければ不健康 | 公式の拡張の型。`-E` を足すと全タスクのイベントが流れ、負荷が増える |
| D3 | beat は `PersistentScheduler` の子クラスにし、予定の確認（tick）のたびに印を更新する。150 秒古ければ不健康 | 60 秒ごとの予定がある（F8）ので tick は 60 秒以内に回る。予定表のファイルの時刻は 3 分ごとにしか変わらない |
| D4 | gateway は asyncio の定期処理で 30 秒ごとに印を更新する。token が無くて待っている間も更新する。120 秒古ければ不健康 | 見るのはプロセスとイベントループが回っていることまで。Discord との接続は既存の見張り（Loki の DiscordGatewayReconnectFailure）に任せる |
| D5 | gemini-egress は、待ち受けの口が開いているかではなく、トンネルの先の tinyproxy の統計ページ（`http://tinyproxy.stats/`）まで busybox の wget で通るかを見る。60 秒ごと | ssh が固まっても、口への接続はカーネルが受けてしまうので、口の確認では固まりが見えない（bin-d-recon.md R5）。統計ページは外へ出ないので Google には要求が飛ばない。prod2 の tinyproxy が落ちていても不健康になる（中継の経路として正しい） |
| D6 | 印のファイルが書けなくても本体の処理は止めない（警告のログだけ） | 健康診断のために本体を壊さない |
| D7 | 不健康になっても Docker は何もしない（`restart: unless-stopped` は止まったときだけ再起動する）。この便で利用者に見える変化は無い | 記録は便E、処置は便G。便D の後 24 時間、誤判定 0 を確かめてから進む（設計 §5） |

## 3. 触るファイル（これ以外は触らない）

- 新規: 新設の backend/app/container_alive.py（§4-1）
- 新規: 新設の backend/app/celery_alive.py（§4-2）
- 変更: `backend/app/celery_app.py`（末尾に追記のみ・§4-3）
- 変更: `backend/app/discord_gateway/main.py`（§4-4）
- 変更: `docker-compose.yml`（§4-5 の追記 4 か所と、beat の command 1 行の置き換え）
- 新規: 新設の backend/tests/test_celery_alive.py・backend/tests/test_discord_gateway_alive.py（§4-6）
- 変更: `docs/handoff/ai-ops-247/card-stage3-bin-d.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. 新設の backend/app/container_alive.py（ファイル全体）

```python
"""ADR-1012 段階3 便D: コンテナの健康診断が読む「生きている印」。

docker-compose.yml の healthcheck が、印のファイルの更新時刻の古さで判定する。
印は /tmp（tmpfs）に置く。書けなくても本来の処理は止めない。
このファイルは celery を import しない（discord-gateway からも使うため）。
"""

import logging
import os

logger = logging.getLogger(__name__)

WORKER_ALIVE_PATH = "/tmp/celery-worker-alive"
BEAT_ALIVE_PATH = "/tmp/celery-beat-alive"
GATEWAY_ALIVE_PATH = "/tmp/discord-gateway-alive"
TOUCH_INTERVAL_SECONDS = 30.0


def touch_alive(path: str) -> None:
    """印のファイルを作るか、更新時刻を今にする。失敗しても例外を出さない。"""
    try:
        with open(path, "a"):
            pass
        os.utime(path, None)
    except OSError:
        logger.warning("生きている印の更新に失敗（処理は継続）: %s", path, exc_info=True)
```

### 4-2. 新設の backend/app/celery_alive.py（ファイル全体）

```python
"""ADR-1012 段階3 便D: celery の worker と beat が「生きている印」を更新する仕組み。

worker: bootstep が worker の timer で 30 秒ごとに更新する（celery 公式 extending の DeadlockDetection と同じ形）。
beat: celery beat -S app.celery_alive:AliveScheduler で起動し、予定の確認（tick）のたびに更新する。
"""

from celery import bootsteps
from celery.beat import PersistentScheduler

from app.container_alive import (
    BEAT_ALIVE_PATH,
    TOUCH_INTERVAL_SECONDS,
    WORKER_ALIVE_PATH,
    touch_alive,
)


class WorkerAliveStep(bootsteps.StartStopStep):
    requires = {"celery.worker.components:Timer"}

    def __init__(self, worker, **kwargs):
        super().__init__(worker, **kwargs)
        self.tref = None

    def start(self, worker):
        touch_alive(WORKER_ALIVE_PATH)
        self.tref = worker.timer.call_repeatedly(
            TOUCH_INTERVAL_SECONDS, touch_alive, (WORKER_ALIVE_PATH,), priority=10,
        )

    def stop(self, worker):
        if self.tref is not None:
            self.tref.cancel()
            self.tref = None


class AliveScheduler(PersistentScheduler):
    def tick(self, *args, **kwargs):
        interval = super().tick(*args, **kwargs)
        touch_alive(BEAT_ALIVE_PATH)
        return interval
```

### 4-3. `backend/app/celery_app.py` の末尾

目印の最終行 `    record_task_failure(getattr(sender, "name", None) or "unknown")`（:196）の後ろに、空行 2 つを挟んで次を足す（既存の行は変えない）:

```python
# ADR-1012 段階3 便D: コンテナの健康診断が読む印を worker が 30 秒ごとに更新する
# （beat は docker-compose.yml の -S app.celery_alive:AliveScheduler で更新する）
from app.celery_alive import WorkerAliveStep  # noqa: E402

celery_app.steps["worker"].add(WorkerAliveStep)
```

### 4-4. `backend/app/discord_gateway/main.py`

(a) 目印の行 `from app.discord_gateway.client import run_gateway`（:7）の直前に 1 行足す（import の並びは英字順で `app.container_alive` が先）:

```python
from app.container_alive import GATEWAY_ALIVE_PATH, TOUCH_INTERVAL_SECONDS, touch_alive
```

(b) 目印の関数 `async def _main_async() -> int:`（:95-101）の直前に、次の関数を足す:

```python
async def _alive_loop() -> None:
    """ADR-1012 段階3 便D: イベントループが回っている間、30 秒ごとに印を更新する。"""
    while True:
        touch_alive(GATEWAY_ALIVE_PATH)
        await asyncio.sleep(TOUCH_INTERVAL_SECONDS)


```

(c) `_main_async` を次の形にする（token が無くて待つ間も印を更新するため、設定を読む前に始める）:

```python
async def _main_async() -> int:
    alive_task = asyncio.create_task(_alive_loop(), name="gw-alive")
    try:
        try:
            config = load_single_bot_config()
        except RuntimeError as e:
            logger.warning("[discord-gateway] %s — idle で待機します", e)
            config = None
        return await _run_with_shutdown(config)
    finally:
        alive_task.cancel()
        await asyncio.gather(alive_task, return_exceptions=True)
```

### 4-5. `docker-compose.yml`

各ブロックの目印の行の直後に、同じ字下げ（4 スペース）で足す。`$$` は compose が `$` を変数として読まないための書き方なので、そのまま書く。

(a) celery-worker：目印 `    stop_grace_period: 60s`（:275・celery-worker のブロックの中）の直後:

```yaml
    # ADR-1012 段階3 便D: 印（app/container_alive.py）の更新が 120 秒止まったら不健康。不健康でも Docker は何もしない
    healthcheck:
      test: ["CMD-SHELL", "t=$$(stat -c %Y /tmp/celery-worker-alive 2>/dev/null || echo 0); [ $$(( $$(date +%s) - t )) -lt 120 ] || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s
```

(b) celery-beat：command の行（:296）を次に置き換える:

```yaml
    command: celery -A app.celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule --scheduler app.celery_alive:AliveScheduler
```

目印 `    restart: unless-stopped`（:308・celery-beat のブロックの中）の直後:

```yaml
    # ADR-1012 段階3 便D: 印の更新が 150 秒止まったら不健康（tick は 60 秒ごとの予定で回る）
    healthcheck:
      test: ["CMD-SHELL", "t=$$(stat -c %Y /tmp/celery-beat-alive 2>/dev/null || echo 0); [ $$(( $$(date +%s) - t )) -lt 150 ] || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s
```

(c) discord-gateway：目印 `    restart: unless-stopped`（:352・discord-gateway のブロックの中）の直後:

```yaml
    # ADR-1012 段階3 便D: 印の更新が 120 秒止まったら不健康（Discord との接続は Loki の見張りが見る）
    healthcheck:
      test: ["CMD-SHELL", "t=$$(stat -c %Y /tmp/discord-gateway-alive 2>/dev/null || echo 0); [ $$(( $$(date +%s) - t )) -lt 120 ] || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 60s
```

(d) gemini-egress：目印 `    restart: unless-stopped`（:381・gemini-egress のブロックの中）の直後:

```yaml
    # ADR-1012 段階3 便D: トンネルの先の tinyproxy の統計ページまで通るか（外へは出ない）。口が開いているだけでは固まりが見えない
    healthcheck:
      test: ["CMD-SHELL", "http_proxy=http://127.0.0.1:18888 wget -q -T 10 -O /dev/null http://tinyproxy.stats/ || exit 1"]
      interval: 60s
      timeout: 15s
      retries: 3
      start_period: 30s
```

### 4-6. 試験（新設の 2 ファイル）

backend/tests/test_celery_alive.py に次の 5 つを書く（`tmp_path` と `unittest.mock` を使い、本物の worker・beat・redis は起こさない）:
1. `touch_alive` が無いファイルを作り、ある場合は更新時刻を進める（`os.utime` で過去にしてから呼び、`os.stat(...).st_mtime` が増えること）
2. `touch_alive` に書けない場所（`tmp_path / "no-dir" / "x"`）を渡しても例外が出ない
3. `AliveScheduler.tick` が親の `tick` の戻り値をそのまま返し、印を更新する（`PersistentScheduler.tick` を patch し、`app.celery_alive.BEAT_ALIVE_PATH` を `tmp_path` の下に patch する）
4. `WorkerAliveStep.start` が `worker.timer.call_repeatedly(30.0, touch_alive, (WORKER_ALIVE_PATH,), priority=10)` を 1 回呼び、`stop` が戻り値の `cancel()` を 1 回呼ぶ（worker は `MagicMock`）
5. `app.celery_app.celery_app.steps["worker"]` に `WorkerAliveStep` が入っている

backend/tests/test_discord_gateway_alive.py に次の 2 つを書く（`pytest.mark.asyncio`。既存の `backend/tests/test_discord_gateway_reconnect.py` と同じ書き方）:
1. `_alive_loop` が最初に印を更新してから `asyncio.sleep(30.0)` を呼ぶ（`asyncio.sleep` を 1 回目で `asyncio.CancelledError` を出す mock にし、`GATEWAY_ALIVE_PATH` を `tmp_path` の下に patch して、ファイルができていること）
2. `_main_async` が、token の無い場合（`load_single_bot_config` が `RuntimeError`）でも印の定期処理を始め、終わるときに止める（`_run_with_shutdown` を即 0 を返す mock にし、戻り値が 0、終了後に `gw-alive` という名前のタスクが残っていないこと）

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-d-impl/ に置く）

5-1. 試験：作業場所の `backend` で、python 3.12 の環境があれば `python -m pytest tests/test_celery_alive.py tests/test_discord_gateway_alive.py tests/test_celery_beat_registered.py tests/test_celery_health.py tests/test_discord_gateway_reconnect.py -q 2>&1 | tail -15` が全部 pass。3.12 の環境が無ければ「手元では未実行・CI で実行」と書く（3.12 以外で venv を作らない）

5-2. 差分：`git diff origin/main --stat` が §3 のファイルだけ。加えて `git diff origin/main -- docker-compose.yml | grep "^-[^-]"` の出力が beat の command の旧行 1 行だけ

5-3. compose の形：`docker compose -f docker-compose.yml config --services 2>&1 | head -20` に 4 サービスの名前がある（`.env` が無いことの警告は出てよい）。`docker compose -f docker-compose.yml config 2>/dev/null | grep -n -A2 "test:" | head -40` で、4 サービスの test の中の `$$` が `$` 1 つに直っていること

5-4. 手元の Docker で試す（colima の専用 profile。§5-6 で必ず消す）:
- `colima start --profile ai-ops-bin-d --cpu 2 --memory 4 --disk 20` → `docker context ls` で `colima-ai-ops-bin-d` が選ばれていること
- 作業場所で `docker compose -p bind-test -f docker-compose.yml up -d --build --no-deps redis celery-worker celery-beat discord-gateway`
- 起動から 90 秒以内に、次が 3 つとも `healthy` になる: `docker inspect -f '{{.Name}} {{.State.Health.Status}}' bind-test-celery-worker-1 bind-test-celery-beat-1 bind-test-discord-gateway-1`
- 固まりの試験：3 つに `docker kill -s STOP`（上の 3 つのコンテナ名） を同時に送り、送った時刻を記録 → 5 秒ごとに状態を読み、3 つとも `unhealthy` になった時刻を記録（上限 300 秒）。各サービスで「STOP から unhealthy まで 240 秒以内」が合格
- 戻りの試験：`docker kill -s CONT` を送り、180 秒以内に 3 つとも `healthy` に戻る
- 所要時間：`docker inspect -f '{{range .State.Health.Log}}{{.Start}} {{.End}} {{.ExitCode}}{{"\n"}}{{end}}' bind-test-celery-beat-1` の Start と End の差が全部 5 秒以内
- メモリ：`docker exec bind-test-celery-beat-1 sh -c 't=$(stat -c %Y /tmp/celery-beat-alive); grep VmHWM /proc/$$/status'` の値が 30MB 以下（30720 kB 以下）

5-5. gemini-egress の健康診断の部品を試す（prod2 には繋がないので、tinyproxy を手元で同じ設定で動かす）:
- `docker run --rm alpine:3.24 wget --help 2>&1 | head -30`（`-T` の有無を記録）
- `docker build -t bind-tinyproxy monitoring/prod2/gemini-egress/tinyproxy`
- `docker run -d --name bind-tp -v "$PWD/monitoring/prod2/gemini-egress/tinyproxy/tinyproxy.conf:/etc/tinyproxy/tinyproxy.conf:ro" -v "$PWD/monitoring/prod2/gemini-egress/tinyproxy/filter:/etc/tinyproxy/filter:ro" bind-tinyproxy tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf`
- 通る試験：`docker run --rm --network container:bind-tp alpine:3.24 sh -c 'http_proxy=http://127.0.0.1:8888 wget -q -T 10 -O - http://tinyproxy.stats/ | head -5; echo rc=$?'` で統計ページの HTML が出て、`http_proxy=http://127.0.0.1:8888 wget -q -T 10 -O /dev/null http://tinyproxy.stats/; echo rc=$?` が `rc=0`
- 固まりの試験：`docker pause bind-tp` の後に同じ `-O /dev/null` のコマンドが 15 秒以内に `rc=0` 以外で終わる（`time` を付けて所要時間も記録）→ `docker unpause bind-tp`
- 外へ出ない試験：`docker logs bind-tp 2>&1 | tail -20` に、generativelanguage など外への接続の行が無い

5-6. 片付け（成否に関わらず必ず行う）：`docker compose -p bind-test down -v`、`docker rm -f bind-tp`、`colima stop --profile ai-ops-bin-d`、`colima delete --profile ai-ops-bin-d --force`、`docker context use default`。最後に `colima list` と `docker context ls` の出力を貼る（`ai-ops-bin-d` が無いこと）

5-7. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI は Opus が見る）

## 6. 分岐ごとの対処

- §4 の目印の行が見つからない（ほかの PR が先に変えた）→ `git show origin/main:docker-compose.yml | grep -n "restart: unless-stopped"` のように origin/main で探し直し、同じ意味の位置に足す。決められなければ NEEDS_DECISION: で grep の出力を貼る
- §5-5 で `wget --help` に `-T` が無い → §4-5(d) の test から ` -T 10` を消し（healthcheck の timeout 15s が代わりに切る）、§5-5 の試験も `-T 10` なしで行う。判断を要した点に書く
- §5-5 の通る試験で統計ページが出ない（403・Filtered・rc が 0 以外）→ §4-5(d) は入れたまま変えず、`docker logs bind-tp 2>&1 | tail -20` と wget の出力を貼って NEEDS_DECISION:（Opus が gemini-egress の診断の方式を決め直す）
- §5-4 で起動しない・90 秒で healthy にならない → `docker compose -p bind-test logs --tail 40`（起動しないサービス名を付ける） を貼る。原因が「`.env` が無い・DB が無い」なら、`docker compose -p bind-test up -d --no-deps postgres` を足して 1 回だけ試し直す。それでも駄目なら BLOCKED:（勝手に compose や本体のコードを足して直さない）
- §5-4 で 240 秒を超える、または戻らない → 時刻の記録と `docker inspect -f '{{json .State.Health}}'`（該当のコンテナ名を付け、`| head -c 3000`） を貼って BLOCKED:
- colima が起動しない・ディスクが足りない → `colima start` の出力の最後 20 行と `df -h /` を貼り、§5-4・§5-5 を「未実行」として残りを進める（PR は作る。Opus が測り方を決め直す）
- 試験が落ちる → 試験ではなく §4 の完成形との違いを直す。§4 のとおりで落ちるなら原文を貼って BLOCKED:

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 3 サービスが起動から 90 秒以内に healthy | §5-4 の `docker inspect` の生出力 |
| 3 サービスとも、固めてから 240 秒以内に unhealthy、戻すと 180 秒以内に healthy | §5-4 の時刻の記録 |
| gemini-egress の診断は、tinyproxy に通れば成功、固まっていれば 15 秒以内に失敗、外へ要求を出さない | §5-5 の生出力 |
| 健康診断 1 回が 5 秒以内・30MB 以下 | §5-4 の Health.Log と VmHWM |
| 試験 7 つが pass、既存の celery と gateway の試験も pass | §5-1 と CI |
| 触ったファイルが §3 だけで、compose から消した行は beat の command の旧行だけ | §5-2 |
| 本番：反映後 24 時間、4 サービスが unhealthy に 1 回もならない（誤判定 0） | §8 の PO の `!`（読み取りだけ）の生出力 |
| 本番：4 サービスの再起動の回数が反映の前後で増えない | §8 の `RestartCount` |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 の完成形と照らし、CI が緑ならマージする（危険便ではない）
2. deploy.yml（main への push で起動）の成功を Actions の記録で確かめる（4 サービスは `up -d --no-deps` で作り直される・F9）
3. 反映の 1 時間後と 24 時間後に、PO の `!` で読み取りだけのスクリプトを実行してもらう。中身：4 サービスの `docker inspect` の `State.Health.Status`・`FailingStreak`・`RestartCount`・`StartedAt`、`Health.Log` の終了コードの数、`docker events`（`--since` に反映の時刻、`--until` に今、`--filter event=health_status`） の行のうち unhealthy の数
4. gemini-egress が本番で unhealthy なら、Gemini は直接接続なので利用者への影響は無い（F3）。prod2 の tinyproxy の状態を PO の `!` で読み、原因を記録してから便E に進むかを決める
5. 生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-d-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：prod2 の tinyproxy のログに 1 分 1 件の統計ページの要求が増える（1 日 1,440 件）。`docker-compose.yml` の gemini-egress は `max-size` でログを抑えているが、prod2 側の tinyproxy の compose にログの上限は無い（`monitoring/prod2/gemini-egress/docker-compose.yml:1-9`）。便D の 24 時間後に prod2 のログの大きさを 1 回読む
- 弊害：beat の scheduler の指定が変わる。`AliveScheduler` は `PersistentScheduler` の子で tick の後に印を書くだけなので、予定表の扱いは変わらない（§4-2・§5-1 の試験 3）
- 戻し方：この PR の revert を main にマージ → 次の deploy で healthcheck と scheduler の指定が外れる。本番のデータには何も残らない（印は tmpfs）

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage3-bin-d --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage3-bin-d` と `git worktree list` の両方で実在を確かめる（名前の似た `release-ai-ops-stage3-bin-d-card` と取り違えない）。以後の作業はすべてその作業場所に `cd` してから行う
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage3-bin-d -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage3-bin-d --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage3-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: backend/app/container_alive.py, backend/app/celery_alive.py, backend/app/celery_app.py, backend/app/discord_gateway/main.py, docker-compose.yml, backend/tests/test_celery_alive.py, backend/tests/test_discord_gateway_alive.py, docs/handoff/ai-ops-247/card-stage3-bin-d.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（docker-compose.yml・backend/app/discord_gateway/main.py と、§13 の「（未記入）」を書き換えるこのカード））
- 本文に「マージと反映後の観測は Opus がカード §8 の順で行う」と 1 行書く
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-6 の出力（長いものは生出力のパスと要点の行）／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage3/bin-d-impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep は §5-4・§5-5 の状態を読む待ち（5 秒ごと・各上限 300 秒）にだけ使ってよい。CI やデプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

実行結果（担当 Sonnet・2026-10-16・生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-d-impl/）:

- §5-1: 手元に celery 等を入れた python 3.12 の環境が無いため pytest は未実行・CI で実行。`python3.12 -m py_compile` で §3 の python 6 ファイルが通ることだけ確認（compile=0）
- §5-2: `git diff origin/main --stat` は §3 の 7 ファイル（カードを除く）。compose から消えた行は beat の command の旧行 1 行だけ（5-2-stat.txt・5-2-minus.txt）
- §5-3: 4 サービス名あり。`docker-compose config` の出力では test の中の `$$` はそのまま `$$` で表示された（5-3-test.txt）
- §5-4: 起動は .env が無く DATABASE_URL が空で 3 サービスとも異常終了を繰り返した（5-4-logs.txt）。§6 に従い postgres を足して 1 回だけ試し直し（シェルの環境変数で試験用の値を渡した）。discord-gateway は healthy（Health.Log 全て ExitCode 0・所要 1 秒未満）、STOP から unhealthy まで 170 秒、CONT から healthy まで 27 秒（5-4-gw-stop.txt）。celery-beat・celery-worker は再試行後も SQLAlchemy URL が空の例外で起動せず、healthy 確認・STOP 試験・VmHWM は未実施（5-4-beat-log-full.txt）
- §5-5: alpine:3.24 の wget は `-T SEC` あり。通る試験は `HTTP/1.1 403 Filtered`・wget rc=1。tinyproxy ログ: `Proxying refused on filtered domain "tinyproxy.stats"`（5-5-tp-logs.txt）。固まりの試験・外へ出ない試験は未実施。§6 に従い §4-5(d) は変えず NEEDS_DECISION
- §5-6: 片付け済み。`colima list` に ai-ops-bin-d なし、`docker context` は default（5-6-final.txt）

判断を要した点:
- ブランチ名は new-worktree.sh の部分一致の不具合を避けるため Opus の指示で変更（release/ai-ops-stage3-bin-d → release/ai-ops-healthcheck-bin-d）
- 手元に `docker compose` プラグインが無く、`docker-compose`（v5.5.1）で代用した
- §5-4 の試し直しで、カードに無い試験用の環境変数（DATABASE_URL・POSTGRES_*・GCP_PROJECT_ID の仮の値）をシェルから渡した（ファイルには書いていない）

END OF CARD
