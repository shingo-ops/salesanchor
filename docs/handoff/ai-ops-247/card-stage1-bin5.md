# 実装カード 段階1 便5 — celery の止まり・失敗・待ち行列の見張り

> この文書は何か：AI保守運用24時間化 段階1 便5 の作業指示書です。裏方の処理（celery。LINE 解析・翻訳・定期の集計などを動かす仕組み）が止まった・失敗が続いた・仕事が溜まった、の 3 つを Prometheus で見張れるようにします。backend に指標を 3 つ足し、見張りを 3 本足し、単体試験・手順書・閾値の正本も同じ値にそろえます。本番への配置は §8 で、マージの後に行います（prod1 は通常の deploy、prod2 はルールの手作業の配置）。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便5・§6 受け入れ基準
- 事実確認の生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin5-recon/facts.md（Q1〜Q9。2026-10-15 Sonnet。repo は origin/main・本番は読み取りのみ）
- 対象ADR: ADR-1012（本テーマ）
- 状態: PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」・10-15 再送）に基づく実装便。閾値は設計 §2 便5「本番の直近 14 日の最長タスク時間を実測してからカードで決める」に従い、§2 の実測から決めた
- 前提: 便4 の実装 PR（release/ai-ops-stage1-bin4）が main にマージされ、本番に配置済みであること。このカードの PR（文書だけ）が main にマージされていること（§10 で確かめる）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable／マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（celery の見張り 3 本と、その指標だけ。Gemini の失敗率は §1 で外す） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§8-6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。短い定期タスクの受付から完了までの最大 60.033 秒（F14）・失敗は 1 時間に最大 1 件・10 分の受付は最大 58 件） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8 は prod1 が通常 deploy、prod2 が無制限鍵） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便5 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新規 `backend/app/celery_health.py`（Redis への記録と読み取りの 1 か所）
2. 新規 `backend/app/tasks/ai_ops_heartbeat.py`（1 分ごとの軽いタスク 1 本）
3. `backend/app/celery_app.py`（include に 1 行・beat_schedule に 1 項目・失敗の signal 1 つ）
4. `backend/app/metrics.py`（指標 3 つと、`/metrics` で読む前に値を入れる処理）
5. 新規 `backend/tests/test_celery_health.py`
6. `monitoring/prometheus/alert_rules.yml` に新しいグループ `celery_alerts`（3 本）
7. `monitoring/prometheus/tests/alert_rules_test.yml` に 3 本の試験
8. docs/runbooks/alerts.md に 3 節
9. `monitoring/tokens.yml` に閾値 3 行・for 3 行

入れない:
- Gemini の失敗率。14 日の失敗のログが 0 件で、ルールが実際に拾えるかを確かめられないため（Q6）。設計の判断どおり段階1 から外し、未解決事項 U2 に残す
- 既存の失敗（translate_pending_messages が毎日 2〜3 回失敗している・Q9a）と、worker に登録されていないタスク（`Received unregistered task` が tcg_mirror と sa02_recon で各 14 件・Q5）の原因の調査と修正。見つけた事実として未解決事項に足す（§13 の後に Opus が設計に追記する）
- worker・beat の compose の healthcheck（Q1。今は無い）
- Redis の設定（`allkeys-lru`・`maxmemory 256mb`）
- 既存の Prometheus 14 本と Loki 6 本

## 2. 前提の事実（facts.md の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | Celery の定義は `backend/app/celery_app.py:17-42`。broker は `CELERY_BROKER_URL`（Redis DB1）。キュー名の指定は無く既定の `celery` | Q1・`backend/app/celery_app.py:14-15` |
| F2 | beat_schedule は 19 件。最短の間隔は 300 秒。1 分ごとの項目は無い | Q1・`backend/app/celery_app.py:60-178` |
| F3 | worker は `--concurrency=2`（`docker-compose.yml:209`）。worker・beat に healthcheck は無い | Q1 |
| F4 | celery の signal（`task_failure` 等）を使っている箇所は backend に 0 件 | Q2 |
| F5 | backend の `/metrics` は `backend/app/metrics.py` の既定レジストリ。uvicorn は 1 プロセス（`backend/Dockerfile:37` `--workers 1`）。multiprocess モードは使っていない | Q3 |
| F6 | backend にも `CELERY_BROKER_URL` が渡っている（`docker-compose.yml:73`。worker は :217、beat は :296） | `docker-compose.yml` |
| F7 | 同期の Redis クライアントの既存の書き方は `backend/app/realtime/publisher.py:52-58`（`redis.from_url(..., decode_responses=True, socket_connect_timeout=2, socket_timeout=2)`）。非同期は同 :43-49 | `backend/app/realtime/publisher.py` |
| F8 | 本番 Prometheus は job `backend` で `/metrics` を読んでいる（`monitoring/prometheus/prometheus.yml:34-47`。target は up）。celery の名前の系列は今 0 | Q4 |
| F9 | 14 日（10-01〜10-15）の最長の実行時間は `tcg.extract_source_message` の 147.57 秒。60 秒を超えるタスクが 2 本同時に走ったのは 1 回（72.6 秒）。受付から完了までの重なりは最大 3 本・最長 88.5 秒 | Q5・Q9c |
| F10 | 14 日の失敗（`raised unexpected`）は 38 件。1 時間あたりの最大は 1 件 | Q5・Q9a |
| F11 | 14 日の受付（`Task ... received`）は 1 分あたり最大 29 件、10 分あたり最大 58 件（10-08 11:40〜11:50） | Q9b |
| F12 | Redis は `allkeys-lru`・`maxmemory 256mb`（`docker-compose.yml:414`）。メモリが一杯になると、どのキーも消されることがある | Q1 |
| F13 | 本番の既定キューの長さは、読んだ時点で 0（キーが無い） | Q8 |
| F14 | 受付 12234 件と完了 12197 件のログを id でつなぎ、12193 件で計算した。全タスクの最大は `buyback.fetch_all_prices` の 3724.576 秒（10-02）。これは F9 の実行時間の最長（147.57 秒）と合わない。worker が受け取ってから実際に動き出すまで待っていた可能性があるが、原因は【未確認】で、未解決事項に足す。ログの時刻のタイムゾーンも【未確認】。 短い定期タスク（300 秒・600 秒ごとの 3 種、計 7493 件）の受付から完了までの最大は 60.033 秒（2 位以下は 2.3 秒以下） | /tmp/CC報告ファイル/ai-ops-stage1-bin5-recon/latency/result.txt（2026-10-15 Sonnet） |

閾値の決め方:
- 止まり（`CeleryHeartbeatStale`）: 1 分ごとに記録する。10 分（600 秒）より古くなったら鳴らす。`for: 2m`。根拠は実測 F14：heartbeat と同じ短い定期タスク（300 秒・600 秒ごとの 3 種、計 7493 件）について、worker の受付から完了までの 14 日の最大は 60.033 秒（2 位以下は 2.3 秒以下）。600 秒はその約 10 倍。測れていない部分: broker の待ち行列で worker に受け取られるまでの時間（ログに出ない）。そこで、反映の 24 時間後に §7 の最後の行で、heartbeat の遅れの最大を本番で確かめる。誤報の見込み: 14 日の実測では、worker の受付以降で短いタスクが 600 秒待たされた例は 0 件（受付より前の待ちは測れていない）。
- 失敗（`CeleryTaskFailuresHigh`）: 1 時間に同じタスクで 3 回以上の失敗。根拠は F10：14 日の最大は 1 時間に 1 件なので、14 日で 0 回鳴る。`for: 0m`。効く範囲（決めた範囲として明示）: 1 日 1〜2 回しか動かないタスク（`backend/app/celery_app.py:129-157` の sa02・為替・tcg_mirror 等）の失敗では鳴らない。タスク名の系列ができた最初の 1 件は `increase()` に数えられない。日次タスクの失敗の見張りは段階1 の範囲外とし、未解決事項に足す。
- 溜まり（`CeleryQueueBacklog`）: 待ち行列が 100 件を超える状態が 10 分続く。根拠は F11：10 分の受付の最大は 58 件なので、その 10 分に 1 件も片付かなくても 100 に届かない。`for: 10m`。
- 札: 止まりは page（LINE 解析・翻訳・定期の処理が全部止まり、利用者に今影響が出る）。失敗と溜まりは ticket（他のタスクは動いている）。`severity` は page が critical、ticket が warning（既存の決め方 `monitoring/prometheus/alert_rules.yml` と同じ）。

## 3. 触るファイル（これ以外は触らない）

- 新規: `backend/app/celery_health.py`
- 新規: `backend/app/tasks/ai_ops_heartbeat.py`
- 新規: `backend/tests/test_celery_health.py`
- 変更: `backend/app/celery_app.py`
- 変更: `backend/app/metrics.py`
- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin5.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. 新規 `backend/app/celery_health.py`（完成形。コメントの言葉は変えてよいが、名前・キー・動きは変えない）:

```python
"""celery の健康の記録と読み取り（ADR-1012 段階1 便5）。

記録は worker が行い、読み取りは backend の /metrics が行う。置き場は broker と同じ Redis（CELERY_BROKER_URL）。
どちらも失敗してもログのみで例外を出さない（本来の処理を止めない）。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")

HEARTBEAT_KEY = "ai_ops:celery:heartbeat_ts"
FAILURES_KEY = "ai_ops:celery:task_failures"
QUEUE_KEY = "celery"

_sync_client: Optional[redis.Redis] = None
_async_client: Optional[aioredis.Redis] = None


def _get_sync() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(
            BROKER_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _sync_client


def _get_async() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(
            BROKER_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _async_client


def record_heartbeat() -> None:
    """worker が 1 分ごとに呼ぶ。今の時刻（秒）を書く。"""
    try:
        _get_sync().set(HEARTBEAT_KEY, str(time.time()))
    except Exception:
        logger.warning("celery heartbeat の記録に失敗（処理は継続）", exc_info=True)


def record_task_failure(task_name: str) -> None:
    """worker の task_failure から呼ぶ。タスク名ごとの失敗の数を 1 増やす。"""
    try:
        _get_sync().hincrby(FAILURES_KEY, task_name or "unknown", 1)
    except Exception:
        logger.warning("celery 失敗数の記録に失敗（処理は継続）: task=%s", task_name, exc_info=True)


READ_TIMEOUT_SEC = 1.5  # /metrics を遅らせない上限（Prometheus の scrape の制限時間より十分短く）


async def _read_raw():
    pipe = _get_async().pipeline(transaction=False)
    pipe.get(HEARTBEAT_KEY)
    pipe.hgetall(FAILURES_KEY)
    pipe.llen(QUEUE_KEY)
    return await pipe.execute()


async def read_celery_health() -> Optional[tuple[float, dict[str, int], int]]:
    """(最後の heartbeat の時刻, タスク名ごとの失敗の数, 待ち行列の長さ) を返す。読めなければ None。

    Redis へは 1 往復（pipeline）で、全体を READ_TIMEOUT_SEC で打ち切る。
    heartbeat のキーが無いときは時刻 0.0 を返す（見張りは「古い」と判定して鳴る）。
    """
    try:
        ts_raw, failures_raw, queue_len = await asyncio.wait_for(_read_raw(), READ_TIMEOUT_SEC)
        ts = float(ts_raw) if ts_raw else 0.0
        failures = {name: int(count) for name, count in (failures_raw or {}).items()}
        return ts, failures, int(queue_len)
    except Exception:
        logger.warning("celery の健康の読み取りに失敗", exc_info=True)
        return None
```

4-2. 新規 `backend/app/tasks/ai_ops_heartbeat.py`（完成形）:

```python
"""1 分ごとの heartbeat タスク（ADR-1012 段階1 便5）。beat が動き、worker が拾ったときだけ時刻が進む。"""

from app.celery_app import celery_app
from app.celery_health import record_heartbeat


@celery_app.task(name="app.tasks.ai_ops_heartbeat.celery_heartbeat", ignore_result=True)
def celery_heartbeat() -> None:
    record_heartbeat()
```

- 既存のタスクの書き方（`backend/app/tasks/` の他のファイル）が `@celery_app.task` と違う形（`shared_task` など）なら、既存の形に合わせる。合わせたら報告に書く。名前（`app.tasks.ai_ops_heartbeat.celery_heartbeat`）は変えない。

4-3. `backend/app/celery_app.py`:
- `include=[...]` の最後（`"app.tasks.buyback_scraper",` の行の後）に 1 行足す: `"app.tasks.ai_ops_heartbeat",  # ADR-1012 段階1 便5: celery の止まりの見張り`
- `beat_schedule` の最後の項目（`tcg.recover_stale_extraction_jobs` の項目）の後に足す:

```python
    # ADR-1012 段階1 便5: 1 分ごとの heartbeat（見張り CeleryHeartbeatStale が読む）
    "ai-ops-celery-heartbeat": {
        "task": "app.tasks.ai_ops_heartbeat.celery_heartbeat",
        "schedule": 60.0,  # 1分
    },
```

- ファイルの最後に足す（`from celery.signals import task_failure` は、このブロックの中で import する。ファイル冒頭の import の並びは変えない）:

```python
# ADR-1012 段階1 便5: タスクの失敗をタスク名ごとに数える（見張り CeleryTaskFailuresHigh が読む）
from celery.signals import task_failure  # noqa: E402

from app.celery_health import record_task_failure  # noqa: E402


@task_failure.connect
def _count_task_failure(sender=None, **kwargs):
    record_task_failure(getattr(sender, "name", None) or "unknown")
```

- 既存の lint（ruff 等）が `E402` 以外で落ちる場合は、lint の指示に合わせて直し、報告に書く。

4-4. `backend/app/metrics.py`:
- `SSE_CONNECTIONS_ACTIVE` の定義の後に、Gauge を 3 つ足す:

```python
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
```

- `async def metrics()` の中身を次にする（`generate_latest()` の前に 1 回だけ読む。読めなければ前の値のまま出す）:

```python
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        health = await read_celery_health()
        if health is not None:
            heartbeat_ts, failures, queue_len = health
            CELERY_HEARTBEAT_TS.set(heartbeat_ts)
            for task_name, count in failures.items():
                CELERY_TASK_FAILURES.labels(task_name).set(count)
            CELERY_QUEUE_LENGTH.set(queue_len)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

- import に `from app.celery_health import read_celery_health` を足す。
- 名前の注記 1: 設計 §2 便5 は止まりの指標を `celery_beat_last_run_timestamp` と書いているが、時刻を書くのは beat ではなく worker がタスクを実行したとき（beat と worker の両方が動いて初めて進む）なので、意味に合わせて `celery_heartbeat_last_success_timestamp_seconds` にする（単位の `_seconds` は prometheus_client の慣習）。
- 名前の注記 2: 設計 §2 便5 は失敗の指標を `celery_task_failures_total` と書いているが、値は Redis の数を写す Gauge で、prometheus_client の慣習で `_total` は Counter の名前に付けるため、`celery_task_failures` にする（見張りは `increase()` で増え方を見る。Redis の数が消えて 0 に戻っても `increase()` はリセットとして扱う）。

4-5. 新規 `backend/tests/test_celery_health.py`（試すこと。書き方は `backend/tests/test_metrics.py` に合わせる。Redis は使わず、`unittest.mock` で `_get_sync`・`_get_async` を差し替える）:
1. `record_heartbeat()` が `HEARTBEAT_KEY` に数字の文字列を `set` する
2. `record_task_failure("x")` が `FAILURES_KEY` の `x` を 1 増やす（`hincrby` が `(FAILURES_KEY, "x", 1)` で呼ばれる）
3. `record_heartbeat()` と `record_task_failure()` は Redis が例外を出しても例外を出さない
4. `read_celery_health()` が `(時刻, {"x": 2}, 5)` の形を返す。heartbeat のキーが無いときは時刻 0.0（`_read_raw` を差し替える）
5. `read_celery_health()` は、Redis が例外を出したとき・壊れた値（数字でない文字列）が入っていたとき・`READ_TIMEOUT_SEC` を超えたとき（`_read_raw` を `asyncio.sleep` で長く待つものに差し替え、`READ_TIMEOUT_SEC` を 0.05 に差し替える）に None
6. `/metrics` の応答に `celery_heartbeat_last_success_timestamp_seconds`・`celery_task_failures{task="x"} 2.0`・`celery_queue_length 5.0` が出る（`app.metrics.read_celery_health` を差し替える）
7. `/metrics` は `read_celery_health()` が None でも 200 を返す
8. `celery_app.conf.beat_schedule["ai-ops-celery-heartbeat"]` の task が `app.tasks.ai_ops_heartbeat.celery_heartbeat`、schedule が 60.0
9. `task_failure` の signal を送ると `record_task_failure` がタスク名で呼ばれる（`task_failure.send(sender=名前を持つ偽物)` と `app.celery_app.record_task_failure` の差し替えで確かめる）

4-6. `monitoring/prometheus/alert_rules.yml` の最後（`uptime_kuma` グループの後）に、新しいグループを足す（完成形）:

```yaml
  - name: celery_alerts
    rules:
      # celery の heartbeat が古い（beat の停止・worker の停止や詰まり。tokens.yml: celery_heartbeat_stale_sec=600）
      # backend/app/metrics.py が Redis から読んで出す celery_heartbeat_last_success_timestamp_seconds を使用
      - alert: CeleryHeartbeatStale
        expr: (time() - celery_heartbeat_last_success_timestamp_seconds{job="backend"}) > 600
        for: 2m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "裏方の処理（celery）が 10 分以上動いていません"
          description: "1 分ごとの heartbeat が {{ $value | humanizeDuration }} 前から更新されていません（閾値: 10 分）。beat か worker が止まっているか詰まっています。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#celeryheartbeatstale"

      # 同じタスクの失敗が 1 時間に 3 回以上（tokens.yml: celery_task_failures_per_1h=3）
      - alert: CeleryTaskFailuresHigh
        expr: sum by (task) (increase(celery_task_failures{job="backend"}[1h])) >= 3
        for: 0m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "裏方の処理（celery）の {{ $labels.task }} が失敗を繰り返しています"
          description: "{{ $labels.task }} が直近 1 時間に {{ $value | humanize }} 回失敗しました（閾値: 3 回）。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#celerytaskfailureshigh"

      # 待ち行列が溜まっている（tokens.yml: celery_queue_length_max=100）
      - alert: CeleryQueueBacklog
        expr: celery_queue_length{job="backend"} > 100
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "裏方の処理（celery）の待ち行列が溜まっています"
          description: "待ち行列が {{ $value | humanize }} 件です（閾値: 100 件・10 分継続）。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#celeryqueuebacklog"
```

4-7. `monitoring/prometheus/tests/alert_rules_test.yml` の最後に 3 本の試験を足す（他の試験は変えない。冒頭のコメントの「全 14 本」は「全 17 本」に直す）:
1. CeleryHeartbeatStale（試験の中の `time()` は 0 から始まる。`alert_rules_test.yml` の F2CleanupStale の注記と同じ）。鳴る: `celery_heartbeat_last_success_timestamp_seconds{job="backend",instance="api"}` が `0x30`（ずっと 0）。差が 600 を超えるのは 11m（660 秒）からで、for 2m を足して `eval_time` 15m に 1 件（`exp_labels` は severity・tier・job・instance）。鳴らない（for より前）: 同じ入力で `eval_time` 12m に 0 件。鳴らない（正常）: 値が `0+60x30`（1 分ごとに進む＝評価の時刻と同じ。差は常に 0）で `eval_time` 20m に 0 件
2. CeleryTaskFailuresHigh 鳴る: `celery_task_failures{job="backend",instance="api",task="t1"}` が `0+1x60`（1 分に 1 件）で `eval_time` 30m に 1 件（`exp_labels` は severity・tier・task）。鳴らない: `0+0.02x60`（1 時間に約 1 件）で `eval_time` 60m に 0 件
3. CeleryQueueBacklog 鳴る: `celery_queue_length{job="backend",instance="api"}` が `150x30` で `eval_time` 15m に 1 件。鳴らない（for より前）: 同じ入力で `eval_time` 9m に 0 件。鳴らない（閾値以下）: `58x30` で `eval_time` 15m に 0 件
- description の展開後の文字列は `promtool test rules --diff` の got 側から写してよい（便3 カード §6 と同じ扱い）。

4-8. docs/runbooks/alerts.md に 3 節を足す（あわせて冒頭 :3 の「Prometheus 14 本」を「17 本」に直す）。見出しは `## CeleryHeartbeatStale`・`## CeleryTaskFailuresHigh`・`## CeleryQueueBacklog`。5 項目（札・何が起きているか・最初に見るもの・直し方・止め方）の形は便3 のまま。書くこと:
- CeleryHeartbeatStale: 札 page。最初に見るもの: prod1 の celery-beat と celery-worker のコンテナの状態（`docker compose ps`）→ worker が今処理中のタスク数（`celery -A app.celery_app inspect active`）→ Loki の worker のログの直近の `received`／`succeeded`。直し方: 止まっている方のコンテナを `docker compose restart`。止め方: Alertmanager の silence（理由と期限を書く）。閾値の根拠（heartbeat と同じ短い定期タスクの、worker の受付から完了までの 14 日の最大は 60 秒。600 秒はその約 10 倍。worker に受け取られる前の待ちは測れていないので、反映後に本番で確かめた）を 1 文で書く。
- CeleryTaskFailuresHigh: 札 ticket。最初に見るもの: Loki で `|= "raised unexpected"` とタスク名で絞ったログ。注記: 「2026-10-15 時点で translate_pending_messages が毎日 2〜3 回失敗している（1 時間に 1 回まで。この見張りは鳴らない）。原因は未調査」。効く範囲の注記: 「1 日に 1〜2 回しか動かないタスク（sa02・為替・tcg_mirror 等）の失敗ではこの見張りは鳴らない。またタスク名の系列ができた最初の 1 件は increase に数えられない。どちらも段階1 で決めた範囲で、日次タスクの失敗の見張りは別の便で扱う」。
- CeleryQueueBacklog: 札 ticket。最初に見るもの: 待ち行列の長さの推移（`celery_queue_length`）と、worker が処理中のタスク（長いタスク `tcg.extract_source_message` 等が並んでいないか）。閾値の根拠（10 分の受付の最大 58 件）を 1 文で書く。
- 3 節とも、指標の出どころ（backend の `/metrics` が Redis から読む。Redis が読めないときは前の値のまま）と、Redis がメモリ一杯で記録を消すことがある（`allkeys-lru`）ので、heartbeat のキーが消えると CeleryHeartbeatStale が鳴ること、を 1 文で書く。
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

4-9. `monitoring/tokens.yml`:
- `thresholds:` の `# ログ異常検知` の段の前に、空行と次の段を足す:

```yaml
  # celery（alert_rules.yml: celery_alerts）
  # backend/app/metrics.py が Redis から読んで出す celery_* を使用
  celery_heartbeat_stale_sec:   600  # CeleryHeartbeatStale: time() - heartbeat > 600
  celery_task_failures_per_1h:    3  # CeleryTaskFailuresHigh: 同じタスクの increase([1h]) >= 3
  celery_queue_length_max:      100  # CeleryQueueBacklog: celery_queue_length > 100
```

- `for_durations:` の最後に足す:

```yaml
  celery_heartbeat:  "2m"   # CeleryHeartbeatStale
  celery_failures:   "0m"   # CeleryTaskFailuresHigh
  celery_queue:      "10m"  # CeleryQueueBacklog
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 作業場所で `python3 -c "import yaml; [print(g['name'], r['alert'], r.get('for'), r['labels']) for g in yaml.safe_load(open('monitoring/prometheus/alert_rules.yml'))['groups'] for r in g['rules']]"` を実行し、`git show origin/main:monitoring/prometheus/alert_rules.yml > /tmp/CC報告ファイル/ai-ops-stage1-bin5/rules-main.yml` の版に対しても同じ 1 行を実行して `diff` に通す（期待: 足された 3 行（celery_alerts の 3 本）だけが違う）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 17 rules, Loki 6 rules, runbook 23 sections`。
5-3. `git diff origin/main -- monitoring/prometheus/alert_rules.yml` の `- ` の行が 0（足すだけ）。`grep -c '^- '` の値を貼る。
5-4. 本番と同じ版のイメージ（`prom/prometheus:v3.11.3`）で `promtool check rules`（期待 "SUCCESS: 17 rules found"）と `promtool test rules`（期待 "SUCCESS"）を実行し、出力と終了コードを貼る（`-v` が効かなければ `docker create` → `docker cp` → `docker start -a`）。
5-5. わざと壊して落ちることを確かめる（一時的な書き換え。確かめたら `git checkout -- <file>` で戻し、`git diff --stat` で戻ったことを出す）: CeleryHeartbeatStale の `> 600` を `> 6000` にすると、§4-7 の試験 1 の「鳴る」（eval 15m＝900 秒）が落ちる。あわせて、壊す前の 5-4 で試験 1 が通っていたこと（壊す前から落ちていたのではないこと）を、5-4 の出力で示す。`promtool test rules` の出力と終了コード 1 を貼る。
5-6. backend の試験: `backend/tests/test_celery_health.py` と `backend/tests/test_metrics.py` と `backend/tests/test_celery.py` を、backend の CI と同じ方法で実行する（実行方法は `.github/workflows/` の backend の pytest を走らせる workflow を読んで合わせる。読んだファイル名と行を報告に書く）。全件 pass の行を貼る。CI は `CELERY_BROKER_URL` を渡さない（`.github/workflows/test.yml:206-241`）。このため、既存の test_metrics.py の試験は差し替えないまま Redis に読みに行き、失敗して None になる（試験は落ちない）。その試験の所要時間と警告の行数を貼る。test_metrics.py は直さない。
5-7. 5-6 で `read_celery_health` の差し替えを外すと試験 6 が落ちること（一時的な書き換えで確かめ、戻す）。落ちた行を貼る。
5-8. backend の lint（CI と同じもの。ruff 等）を変更したファイルに対して実行し、exit 0 を貼る。
5-9. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「不一致」の行（期待: 不一致 0）。注記: このスクリプトは celery_* のキーを照合しない（`monitoring/scripts/validate_tokens.py:168-181` は cpu・memory・disk・kuma_cert だけ）。壊していないことの確かめにとどまり、値が合っていることの証拠にはならない。値の一致は §5-1 の出力と tokens.yml の 3 行を並べて報告に貼って示す。
5-10. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md` の該当が 0 行（版の番号の形に当たった行は、その行を貼って IP でないことを書く）。
5-11. `git diff origin/main --stat` が §3 の 10 ファイルであること。

## 6. 分岐ごとの対処

- 5-1〜5-3・5-8〜5-11 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-4 で promtool の test が落ちる → 試験の期待値（展開後の文字列など）を直してやり直す。§4-6 の式・for・閾値を変えて合わせることはしない。3 回直しても通らなければ出力を貼って BLOCKED:。
- 5-6 で既存の試験（test_metrics.py・test_celery.py）が落ちる → この便の変更が原因なら直す。変更の前から落ちていた（origin/main でも落ちる）なら、その事実を貼って続行。
- 4-2 の既存のタスクの書き方が違う → 既存に合わせて続行（報告に書く）。
- 前提の便4 の実装 PR がマージされていない → 作業を始めずに止まる（BLOCKED:）。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → 便3 カード §6 と同じく `quay.io` の同じ版に替えてよい。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 見張り 3 本が §4-6 の完成形で入り、既存の 14 本は変わらない | §5-1・§5-3 |
| 3 本とも鳴るときに鳴り、鳴らないときに鳴らない（単体試験） | §5-4・§5-5・PR の CI |
| 札・手順書リンク・見出しの検査が通る（17 本・23 節） | §5-2 |
| backend が指標 3 つを出し、Redis が読めなくても `/metrics` が 200 を返す | §5-6・§5-7 |
| 本番 Prometheus で heartbeat と待ち行列の系列が 1 以上 | §8-6 |
| 本番 Prometheus で失敗の系列が 1 以上（失敗が 1 件も起きなければ系列はできないため、配置の直後には確かめない。translate_pending_messages が毎日 2〜3 回失敗しているので、24 時間以内にできる見込み） | 反映の 24 時間後に Opus が `count(celery_task_failures{job="backend"})` を読む。0 なら、Loki で同じ 24 時間の `raised unexpected` の件数を数えて並べる（失敗が 0 件なら合格、1 件以上あれば不合格として調べる） |
| 本番の heartbeat が 1 分ごとに進んでいる | §8-6（`time() - celery_heartbeat_last_success_timestamp_seconds` が 120 未満） |
| 本番の Prometheus に 3 本が入り、評価の失敗が無い | §8-6 |
| 本番のルールファイルが main と sha256 一致 | §8-4 |
| 反映後 24 時間の heartbeat の更新間隔の最大が閾値 600 秒未満 | 反映の 24 時間後に Opus が `max_over_time((time() - celery_heartbeat_last_success_timestamp_seconds{job="backend"})[24h:1m])` を読む。600 秒以上なら不合格とし、Opus が閾値の見直しか、札を page から ticket に下げることを設計に戻して決める（その間は Alertmanager の silence で止める） |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

機体は 2 つ。prod1 は main へのマージで動く通常の deploy（`.github/workflows/deploy.yml`）で反映され、担当は prod1 に書き込まない。prod2 はルールの手作業の配置で、SSH は制限付き鍵で書けないため無制限鍵 `~/.ssh/manual-only/id_ed25519` を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md・reference_prod_server_config.md。本番で行う操作は下の 8-1〜8-7 だけ。Loki・Alertmanager・tokens.yml は本番に配らない。

8-1. prod1 の deploy の確認（読み取り）: マージの commit の deploy の run が success であること（`gh run list --workflow deploy.yml --limit 3 --json headSha,conclusion,createdAt`）。（prod1 のコンテナの起動時刻は読まない。heartbeat の値は、新しい backend・beat・worker の 3 つがそろって初めて出るので、次の確かめで足りる。）本番 Prometheus（prod2 の Prometheus のコンテナの中から localhost 宛）で `celery_heartbeat_last_success_timestamp_seconds{job="backend"}` が 0 でなく、`time()` との差が 120 秒未満であること。deploy の run がまだ終わっていなければ、その状態を報告して終える（待たない）。
8-2. 控え: `/opt/salesanchor-monitoring/backups/ai-ops-stage1/` に、prod2 の本番の `alert_rules.yml` を `cp -p` で `.bak-20261015-` に PR 番号を付けた名前で写し、元と控えの sha256 を出す。あわせて本番のファイルが、この PR のマージ commit の 1 つ前の版と同じであることを出す。コマンドは、PR は便5 の実装 PR の番号として `MC=$(gh pr view PR --json mergeCommit -q .mergeCommit.oid)` → `git fetch origin && git show "$MC^1":monitoring/prometheus/alert_rules.yml | sha256sum`。一致しなければ止まる。
8-3. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-ai-ops-bin5/` を作り、main の `monitoring/prometheus/alert_rules.yml` を scp で送る。同じ版の promtool で `check rules` を通す（"SUCCESS: 17 rules found"）。
8-4. 本番の場所に `install -m` で元と同じ権限で置き、本番のファイルと main の sha256 が一致することを出す。Prometheus のコンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送り、終了コードを出す。
8-5. 一時ディレクトリは消さない（削除はフックに止められる。中身はルールファイル 1 つだけ）。中身の一覧（`ls -la`）だけ出す。
8-6. 読み取りで次を出す（待ちに sleep は使わず、1 回目で揃わなければ報告を返し、続きは Opus が依頼する）:
  - Prometheus の `/api/v1/rules`: ルール数（期待 17）・`tier` が無いルール（期待 0 件）・`tier` ごとの数（期待 page 6・ticket 11）・`health` が ok でないルールの数（期待 0）・`celery_alerts` の 3 本の名前
  - Prometheus の `/api/v1/query`: `celery_heartbeat_last_success_timestamp_seconds{job="backend"}`・`celery_queue_length{job="backend"}`・`count(celery_task_failures{job="backend"})` の値（系列が無いものは「値なし」と書く。失敗の系列は配置の後に失敗が 1 件も無ければ値なしで正常）・`time() - celery_heartbeat_last_success_timestamp_seconds{job="backend"}` の値
  - Alertmanager の `/api/v2/alerts` の alertname と `tier` の一覧（便3 で【未確認】だった SustainedAuthFailure の `tier` 付きの鳴り直しがあれば、それも書く）
8-7. 生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin5/deploy/ に保存する。

§8 の分岐:
- 8-1 で deploy が failure → prod2 に置かずに止まる（BLOCKED:）。
- 8-1 で heartbeat が 0 のまま、または差が 120 秒以上 → prod2 に置かずに止まる（BLOCKED:）。beat・worker のログの直近 20 行（`docker compose logs --tail 20`。秘密が出る行は伏せる）を報告に貼る。
- 8-2 で本番と main（1 つ前）の sha256 が一致しない → 置かずに止まる（NEEDS_DECISION:）。
- 8-3 の promtool が落ちる → 置かずに止まる（BLOCKED:）。
- 8-6 で `health` が ok でないルールがある → 8-2 の控えに戻して読み直し、止まる（BLOCKED:）。
- 8-6 で celery の見張りが鳴っている → 戻さない。値を報告する（Opus が判断する）。

## 9. 戻し方

- prod2: 8-2 の控えを元の場所へ `install -m` で戻し、Prometheus に `POST /-/reload`。
- repo と prod1: この PR の revert を main にマージして deploy。指標が消えるだけで、本体の処理は変わらない。Redis に残ったキー `ai_ops:celery:heartbeat_ts`・`ai_ops:celery:task_failures` は害が無いので残してよい。

## 10. PR

- 作業場所: 便4 の実装 PR が main にマージされたことを `gh pr list --state merged --head release/ai-ops-stage1-bin4 --json number,state` で確かめてから（合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）、`cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/ai-ops-stage1-bin5 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-15 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin5` と `git worktree list` の両方で実在を確かめる。`ls docs/handoff/ai-ops-247/card-stage1-bin5.md` でこのカードが実在することを確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin5 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを `--body "$(cat 本文ファイル)"` の形で渡して作る。作成後に `gh pr list --head release/ai-ops-stage1-bin5 --json number,isDraft` で 1 件・isDraft が false を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main
- PR 本文に §8 の PO 原文と、本番で実行する操作の番号（8-1〜8-7）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
- 本文に IP・URL の秘密・鍵のパス・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-11 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
