# recon: 状態書き係が使い捨ての作業箱を数えて誤検知する件（ADR-1012 段階4 順番1）

調べた人: Claude Opus（読み取りのみ）・2026-11-17〜18。根拠は origin/main（27a932373）と本番の読み取り。

## 既存 ADR の検索
- `git grep -il "oneoff\|one-off" origin/main -- docs/adr` → ADR-092（deploy の同時実行）だけ。状態書き係の one-off の扱いを決めた ADR は無い
- 対象 ADR: ADR-1012（段階3 便D・便E で健康診断と状態書き係を作った）。この直しは ADR-1012 の範囲内の不具合直しで、新しい判断は足さない

## 観測事実
1. 不健康の区間: Prometheus `max(salesanchor_container_unhealthy{service="celery-worker"})` を 1 分刻みで 30 日読むと 39 区間（10/19〜11/17）
2. 39 区間すべてで、区間の約 2 分前に記録を出し始め、区間の終わりに記録が止まる別の箱が Loki にある。38 区間は 1 つの箱で、10/19 15:37-16:56 は 2 つの箱（15:35-16:45・15:48-16:57）が重なって覆う
3. 見本で読んだ箱の中身は、どれも手で流した作業（prompt_ab・再解析 jobs 1044・`[PRE] lock_timeout=1s` の点検走行・`[preflight]`）。worker の起動の記録（`celery@… ready`）は無い
4. 11/17 17:35-18:24: 作業箱は 17:32:06 開始・18:24:07 `RESULT MODE=dryrun 合格` で終了。同じ時間、本物の worker は毎分の心拍 `ai_ops_heartbeat.celery_heartbeat` を受けて成功している
5. 知らせ: `count_over_time(ALERTS{alertname="ContainerUnhealthy",alertstate="firing"}[30d])` は celery-worker 3840・discord-gateway 1（評価の回数。鳴っていた時間の目安）
6. 本番の箱の目印（2026-11-18 ssh で `docker ps --format {{.Label "com.docker.compose.oneoff"}}`）: celery-worker・celery-beat・discord-gateway・gemini-egress・backend の 5 つとも `oneoff=False`。Docker Compose v5.1.1

## 仕組み（コード）
- `scripts/ops/container_state.py:39-45` read_states(): `docker ps -a -q --filter label=com.docker.compose.service=<service>` で箱を全部集め、`docker inspect` の State を返す。one-off（`docker compose run`）の箱も同じ service の目印を持つので入る
- `scripts/ops/container_state.py:48-52` summarize(): 動いている箱が 1 つでも unhealthy なら unhealthy=1
- `docker-compose.yml` celery-worker の healthcheck: `/tmp/celery-worker-alive` の更新が 120 秒以内でなければ失敗（interval 30s・retries 3・start_period 60s）
- `backend/app/celery_alive.py:18-34` WorkerAliveStep: worker として起動したときだけ 30 秒ごとに印を更新する。`docker compose run … celery-worker python …` は worker を起動しないので印が更新されず、約 2 分で unhealthy になる
- Docker Compose の作り（Context7 `/docker/compose`）: `run` の箱には `com.docker.compose.oneoff=True`（pkg/compose/run.go doPrepareRun）、`up` の箱には `False`（internal/projectloader/loader.go）を付ける

## 数の使われ先（全走査）
`git grep -n "salesanchor_container_running\|salesanchor_container_unhealthy\|container_healthcheck_missing" origin/main -- ':!docs'`
- monitoring/prometheus/alert_rules.yml:339 ContainerUnhealthy・:363 ContainerHealthcheckMissing
- monitoring/prometheus/tests/alert_rules_test.yml（数を直接与える試験・状態書き係は通らない）
- scripts/tests/test_container_state.py・tests/sandbox/container-state.sh（状態書き係の試験）
- salesanchor_container_running を使う見張りは無い

## 本番への届き方
- prod1 の ubuntu の cron が毎分 `/home/ubuntu/salesanchor/scripts/ops/container_state.py` を動かす（docs/handoff/ai-ops-247/card-stage3-bin-e.md:496）
- deploy.yml:319-320 の `git fetch origin main` / `git reset --hard origin/main` で入れ替わり、次の cron から新しい形で書く（card-stage3-teichaku-t1.md:491 と同じ道）
