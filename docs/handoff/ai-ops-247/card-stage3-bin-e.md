# 実装カード 段階3 便E — コンテナの状態を見張りに載せる

> この文書は何か：AI保守運用24時間化 段階3 便E の作業指示書です。便D で 4 つのコンテナに付けた健康診断の結果を、prod1 の「状態書き係」が毎分ファイルに書き、prod2 の見張り（Prometheus）が読んで、不健康になったら Discord と障害記録に知らせます。この便は知らせるまでで、再起動などの処置はしません（処置は便G）。

- 設計: docs/handoff/ai-ops-247/stage3-design.md §2 便E・§5・§6・§7 V2・V4
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階3
- 対象ADR: ADR-1012（本テーマ）
- 状態: 便の分け方は PO 承認 y（2026-10-16）。§2-2 の決定は Opus の技術判断（設計の目的・範囲を変えない）。V2 は PO の `!`（2026-10-17 00:26Z・読むだけ）で全項目合格。V4 は §2-1 F7 で解決
- 危険便: はい（`scripts/` を含む。ADR-135・ADR-136）。GO は「POの委任に基づくClaude Opus発行」で Opus が出し、マージと反映後の観測も Opus が行う。担当はマージしない
- 担当: 実装 Sonnet／審査・GO・マージ・反映確認 Opus／prod1 の crontab への 1 行追加は PO の `!`

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○（まだ無いファイルのパスは「新設の」を付けてバッククォートなしで書く） |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（状態を書いて見張りに載せることだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-3・§4-7 の expect） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 15114e878 で確かめた） |
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

作業を始める前に、報告の冒頭へ「本報告はカード 段階3 便E の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 状態書き係（新設の scripts/ops/container_state.py）（§4-1）
2. その試験（新設の scripts/tests/test_container_state.py）と、CI で走らせる設定（`.github/workflows/deploy-script-test.yml` に追記）（§4-2・§4-3）
3. 見張り 2 本（`monitoring/prometheus/alert_rules.yml` の末尾に 1 グループ）（§4-4）
4. 見張りの単体試験（`monitoring/prometheus/tests/alert_rules_test.yml` の末尾に追記）（§4-5）
5. 手順書 2 節（`docs/runbooks/alerts.md`）（§4-6）
6. GitHub の試験場（sandbox-test）で動かす試験（新設の tests/sandbox/container-state.sh）（§4-7）

入れない:
- 処置（再起動）・保守 API の変更（便F・便G）
- prod1 の crontab への登録（反映後に PO の `!` で行う。§8）
- `alert_rules.yml` のほかのルール・Alertmanager の設定の変更
- `deploy.yml` の変更

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 15114e878・生出力 /tmp/CC報告ファイル/ai-ops-stage3/bin-e-recon/recon.md・/tmp/CC報告ファイル/ai-ops-stage3/v2_result.txt）

| # | 事実 | 出典 |
|---|---|---|
| F1 | textfile は prod1 の `/home/ubuntu/node_exporter_textfile`。既存の書き手は一時ファイルに `# HELP`・`# TYPE gauge`・値を書き、`chmod 644` して `mv` で `*.prom` に置く | `scripts/f2-cleanup.sh:59-71`・`scripts/backup.sh:64-80` |
| F2 | prod1 の ubuntu は docker グループに入っていて sudo なしで docker を使える。cron は動いている。python3 は 3.12.3。textfile の置き場は ubuntu が書ける（drwxrwxr-x ubuntu） | v2_result.txt（PO の `!`・2026-10-17 00:26Z） |
| F3 | Alertmanager は札で行き先を分けていない。全ての見張りが Discord と保守 API（障害記録）の両方に届く | `monitoring/alertmanager/alertmanager.yml:7-10` |
| F4 | 手順書の札の定義：`auto` は「段階3 で自動の応急処置が付いたもの。今は該当なし」 | `docs/runbooks/alerts.md:9` |
| F5 | 見張りの検査：`runbook_url` は `alerts.md#` の後ろにルール名の小文字、見出しの無いルールと、ルールの無い見出しは CI で NG。札は page・auto・ticket のどれか | `monitoring/scripts/check_alert_rules.py:17,55,62,70` |
| F6 | CI の `monitoring-check.yml` が `check_alert_rules.py`・`promtool check rules`・`promtool test rules`・`amtool check-config` を走らせる | `.github/workflows/monitoring-check.yml:61-74` |
| F7 | prod2 の Prometheus は prod1 の node-exporter（`host-gateway:19100`）を `job="node-exporter"`・`instance="app-vps"` で 15 秒ごとに読む（V4 の解決） | `monitoring/prometheus/prometheus.yml:5,25-32` |
| F8 | compose のコンテナには `com.docker.compose.service` のラベルが付き、既存のスクリプトもそれで探す。同じサービスに古いコンテナが残った前歴がある | `scripts/deploy/app-services-plan.sh:21`・`.github/workflows/deploy.yml:9,416` |
| F9 | scripts の python の試験は `scripts/tests/` に置き、`python3 scripts/tests/test_*.py` で直接走らせる。CI の型は `deploy-script-test.yml`（必須チェックではない） | `.github/workflows/deploy-script-test.yml:1-35` |
| F10 | 既存の page の例は `severity: critical`・`tier: page`（CeleryHeartbeatStale） | `monitoring/prometheus/alert_rules.yml:183-193` |
| F11 | 手順書の冒頭と試験の冒頭に「22 本」と本数が書いてある | `docs/runbooks/alerts.md:3`・`monitoring/prometheus/tests/alert_rules_test.yml:4` |

### 2-2. 決めたこと（Opus）

| # | 決めたこと | 理由 |
|---|---|---|
| E1 | ContainerUnhealthy の札は、この便では `page` にする。処置が付く便G で `auto` に変える | 手順書の定義（F4）では auto は「応急処置が付いたもの」。便E では処置する者がいないので、人が見る札にする。設計 §2 の「札 auto」は便G の完成時の姿として扱い、便G のカードで切り替える（設計の目的・範囲は変えない） |
| E2 | 見る対象は 4 サービス。backend は参考として値だけ書き、見張りの対象にしない | 設計 §2 便E のとおり。backend の不調は既存の見張り（Uptime Kuma 等）が見る |
| E3 | コンテナは `com.docker.compose.service` のラベルで探し、止まったものも含めて読む。動いているコンテナが 1 つでも unhealthy なら 1 | compose のプロジェクト名に依存しない（F8）。古いコンテナが残っていても、動いている方だけで判断する |
| E4 | docker が読めない・書けないときは、ファイルを書き換えずに終了コード 1 で終わる | 書いた時刻が古くなり、ContainerStateStale が鳴る。間違った 0 を書かない |
| E5 | 成功したときは何も出力しない。失敗のときだけ標準エラーに 1 行 | 毎分の記録でディスクを使わない（設計 §2） |
| E6 | 設計 §6 の「手元で Alertmanager まで通して Discord 1 件・障害記録 1 行」は、GitHub の試験場（sandbox-test）の本物の docker で状態書き係の出力を確かめる試験と、見張りの単体試験（どちらも §4-7・§5-2）に置き換える。Mac で仮想マシンは作らない（`docs/ops/runner-commands.md:351`） | 見張りから Discord と障害記録への経路は既存で、札に関係なく全部届く（F3）。手元で Discord の鍵を使わない |

## 3. 触るファイル（これ以外は触らない）

- 新規: 新設の scripts/ops/container_state.py（§4-1）
- 新規: 新設の scripts/tests/test_container_state.py（§4-2）
- 変更: `.github/workflows/deploy-script-test.yml`（§4-3 の追記のみ）
- 変更: `monitoring/prometheus/alert_rules.yml`（末尾に追記のみ・§4-4）
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`（冒頭のコメント 1 行の置き換えと、末尾に追記・§4-5）
- 変更: `docs/runbooks/alerts.md`（冒頭の本数の置き換えと、末尾に追記・§4-6）
- 新規: 新設の tests/sandbox/container-state.sh（§4-7）
- 変更: `docs/handoff/ai-ops-247/card-stage3-bin-e.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. 新設の scripts/ops/container_state.py（ファイル全体）

```python
#!/usr/bin/env python3
"""ADR-1012 段階3 便E: コンテナの状態を node-exporter の textfile に書く（状態書き係）。

prod1 の ubuntu の cron で毎分 1 回動く。docker の状態を読んで書くだけで、処置はしない。
成功したときは何も出力しない。失敗したときは標準エラーに 1 行書いて終了コード 1 で終わり、
ファイルは前のまま残す（書いた時刻が古くなり、見張り ContainerStateStale が鳴る）。
python3 の標準ライブラリだけを使う。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SERVICES = ("celery-worker", "celery-beat", "discord-gateway", "gemini-egress", "backend")
TEXTFILE_DIR = os.environ.get("CONTAINER_STATE_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
OUTPUT_NAME = "container_state.prom"
DOCKER_TIMEOUT_SECONDS = 20


def docker_bin() -> str:
    return shutil.which("docker") or "/usr/bin/docker"


def run_docker(args: list[str]) -> str:
    result = subprocess.run(
        [docker_bin(), *args],
        capture_output=True,
        text=True,
        timeout=DOCKER_TIMEOUT_SECONDS,
        check=True,
    )
    return result.stdout


def read_states(service: str) -> list[dict]:
    """そのサービスのコンテナの State を返す（compose のラベルで探す。止まったものも含む）。"""
    ids = run_docker(["ps", "-a", "-q", "--filter", f"label=com.docker.compose.service={service}"]).split()
    if not ids:
        return []
    data = json.loads(run_docker(["inspect", *ids]))
    return [c.get("State") or {} for c in data]


def summarize(states: list[dict]) -> tuple[int, int]:
    """(running, unhealthy) を返す。動いているコンテナが 1 つでも unhealthy なら unhealthy=1。"""
    running = [s for s in states if s.get("Running")]
    unhealthy = any((s.get("Health") or {}).get("Status") == "unhealthy" for s in running)
    return (1 if running else 0, 1 if unhealthy else 0)


def render(results: dict[str, tuple[int, int]], now: float) -> str:
    lines = [
        "# HELP salesanchor_container_unhealthy 1 if a running container of the service is unhealthy.",
        "# TYPE salesanchor_container_unhealthy gauge",
    ]
    for service, (_, unhealthy) in results.items():
        lines.append(f'salesanchor_container_unhealthy{{service="{service}"}} {unhealthy}')
    lines += [
        "# HELP salesanchor_container_running 1 if a container of the service is running.",
        "# TYPE salesanchor_container_running gauge",
    ]
    for service, (running, _) in results.items():
        lines.append(f'salesanchor_container_running{{service="{service}"}} {running}')
    lines += [
        "# HELP salesanchor_container_state_last_run_timestamp_seconds Unix time of the last successful write.",
        "# TYPE salesanchor_container_state_last_run_timestamp_seconds gauge",
        f"salesanchor_container_state_last_run_timestamp_seconds {int(now)}",
    ]
    return "\n".join(lines) + "\n"


def write_atomic(text: str) -> None:
    """一時ファイル（.prom で終わらない名前）に書いてから置き換える。node-exporter は *.prom だけを読む。"""
    fd, tmp = tempfile.mkstemp(prefix=".container_state.", dir=TEXTFILE_DIR)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, os.path.join(TEXTFILE_DIR, OUTPUT_NAME))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    try:
        results = {service: summarize(read_states(service)) for service in SERVICES}
        write_atomic(render(results, time.time()))
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"{stamp} container_state failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 4-2. 新設の scripts/tests/test_container_state.py

`unittest` で書き、最後に `if __name__ == "__main__": unittest.main()` を置く（`python3 scripts/tests/test_container_state.py` で走る。pytest は使わない）。読み込みは `importlib.util.spec_from_file_location` で `scripts/ops/container_state.py` をこのファイルからの相対パスで読む。docker は `run_docker` を `unittest.mock.patch.object` で差し替え、本物の docker は呼ばない。書き先は `tempfile.TemporaryDirectory()` にし、モジュールの `TEXTFILE_DIR` を patch する。次の 8 つを書く:

1. `summarize`：`[]` → `(0, 0)`
2. `summarize`：動いていて Health が healthy → `(1, 0)`
3. `summarize`：動いていて unhealthy → `(1, 1)`
4. `summarize`：止まっていて unhealthy（`{"Running": False, "Health": {"Status": "unhealthy"}}`）と、動いていて healthy の 2 つ → `(1, 0)`（止まった古いコンテナを数えない）
5. `summarize`：動いていて Health が無い（`{"Running": True}`）→ `(1, 0)`
6. `main`：`run_docker` が `ps` に `"abc\n"`、`inspect` に `[{"State": {"Running": true, "Health": {"Status": "unhealthy"}}}]` の JSON を返すと、終了コード 0 で `container_state.prom` ができ、`salesanchor_container_unhealthy{service="celery-beat"} 1` の行と `salesanchor_container_state_last_run_timestamp_seconds ` で始まる行があり、ファイルの権限が `0o644`、書き先に `.container_state.` で始まるファイルが残っていない
7. `main`：`run_docker` が `subprocess.CalledProcessError(1, ["docker"])` を出すと、終了コード 1 で、前から置いてあった `container_state.prom` の中身が変わらない
8. `main`：`run_docker` が `subprocess.TimeoutExpired(["docker"], 20)` を出すと、終了コード 1

### 4-3. `.github/workflows/deploy-script-test.yml`

(a) `pull_request:` と `push:` の `paths:` の両方で、目印の行 `      - 'scripts/tests/test_app_services_plan.py'` の直後に 2 行足す:

```yaml
      - 'scripts/ops/container_state.py'
      - 'scripts/tests/test_container_state.py'
```

(b) 目印の最終行 `        run: python3 scripts/tests/test_app_services_plan.py` の後ろに、空行 1 つを挟んで足す:

```yaml
      - name: Run container_state tests
        run: python3 scripts/tests/test_container_state.py
```

### 4-4. `monitoring/prometheus/alert_rules.yml` の末尾

最終行（MonitoringConfigCheckStale の `runbook_url` の行）の後ろに、空行 1 つを挟んで足す（字下げは既存のグループと同じ 2 スペース）:

```yaml
  - name: container_state_alerts
    rules:
      # 健康診断（docker-compose.yml の healthcheck・便D）が unhealthy（ADR-1012 段階3 便E）
      # prod1 の scripts/ops/container_state.py が毎分 textfile に書く。札は処置の付く便G で auto に変える
      - alert: ContainerUnhealthy
        expr: salesanchor_container_unhealthy{service=~"celery-worker|celery-beat|discord-gateway|gemini-egress"} == 1
        for: 1m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "コンテナ {{ $labels.service }} が不健康です"
          description: "prod1 の {{ $labels.service }} の健康診断が unhealthy です。固まっている可能性があります。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerunhealthy"

      # 状態書き係が 5 分書いていない（cron の停止・docker が読めない・ファイルが無い）
      - alert: ContainerStateStale
        expr: (time() - salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps"}) > 300 or absent(salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps"})
        for: 2m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "コンテナの状態書き係が 5 分以上動いていません"
          description: "prod1 の scripts/ops/container_state.py が 5 分以上 textfile を書いていません。コンテナの不健康を知らせられない状態です。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerstatestale"
```

### 4-5. `monitoring/prometheus/tests/alert_rules_test.yml`

(a) 4 行目 `# 全 22 本が擬似の系列で鳴ること、tier と runbook_url が付くことを確かめる。` の `22` を `24` にする。

(b) 末尾に、空行 1 つを挟んで足す（既存の tests の項目と同じ字下げ）:

```yaml
  # --- container_state_alerts（段階3 便E） ---
  - name: ContainerUnhealthyFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_container_unhealthy{service="celery-beat",instance="app-vps",job="node-exporter"}'
        values: '1x10'
    alert_rule_test:
      - eval_time: 3m
        alertname: ContainerUnhealthy
        exp_alerts:
          - exp_labels:
              service: celery-beat
              instance: app-vps
              job: node-exporter
              severity: critical
              tier: page
            exp_annotations:
              summary: "コンテナ celery-beat が不健康です"
              description: "prod1 の celery-beat の健康診断が unhealthy です。固まっている可能性があります。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerunhealthy"

  - name: ContainerUnhealthyQuiet
    interval: 1m
    input_series:
      - series: 'salesanchor_container_unhealthy{service="celery-beat",instance="app-vps",job="node-exporter"}'
        values: '0x10'
      - series: 'salesanchor_container_unhealthy{service="backend",instance="app-vps",job="node-exporter"}'
        values: '1x10'
    alert_rule_test:
      - eval_time: 5m
        alertname: ContainerUnhealthy
        exp_alerts: []

  - name: ContainerStateStaleFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '-1000+0x10'
    alert_rule_test:
      - eval_time: 5m
        alertname: ContainerStateStale
        exp_alerts:
          - exp_labels:
              instance: app-vps
              job: node-exporter
              severity: critical
              tier: page
            exp_annotations:
              summary: "コンテナの状態書き係が 5 分以上動いていません"
              description: "prod1 の scripts/ops/container_state.py が 5 分以上 textfile を書いていません。コンテナの不健康を知らせられない状態です。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerstatestale"

  - name: ContainerStateStaleAbsent
    interval: 1m
    input_series:
      - series: 'up{job="node-exporter",instance="app-vps"}'
        values: '1x10'
    alert_rule_test:
      - eval_time: 5m
        alertname: ContainerStateStale
        exp_alerts:
          - exp_labels:
              instance: app-vps
              severity: critical
              tier: page
            exp_annotations:
              summary: "コンテナの状態書き係が 5 分以上動いていません"
              description: "prod1 の scripts/ops/container_state.py が 5 分以上 textfile を書いていません。コンテナの不健康を知らせられない状態です。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerstatestale"

  - name: ContainerStateFresh
    interval: 1m
    input_series:
      - series: 'salesanchor_container_state_last_run_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '0+60x10'
    alert_rule_test:
      - eval_time: 8m
        alertname: ContainerStateStale
        exp_alerts: []
```

### 4-6. `docs/runbooks/alerts.md`

(a) 3 行目の `（Prometheus 22 本）` を `（Prometheus 24 本）` にする。

(b) 末尾（MonitoringConfigCheckStale の節の最後の行）の後ろに、空行 1 つを挟んで足す:

```markdown
## ContainerUnhealthy

- 札：page（処置の付く段階3 便G で auto に変える）
- 何が起きているか：prod1 の celery-worker・celery-beat・discord-gateway・gemini-egress のどれかの健康診断（docker-compose.yml の healthcheck）が unhealthy で、その状態が 1 分続いた。健康診断は、コンテナの中の「生きている印」が 2〜2 分半更新されないと失敗する（gemini-egress は中継の先の tinyproxy が答えないと失敗する）。値は prod1 の `scripts/ops/container_state.py` が毎分 textfile に書く。
- 影響：worker・beat は LINE 解析・翻訳・定期の集計が止まる。discord-gateway は Discord の受信が止まる。gemini-egress は緊急用の中継なので、Gemini が直接接続のままなら利用者への影響は無い。
- 最初に見るもの：prod1 で `docker inspect -f '{{json .State.Health}}'`（該当のコンテナ）の最後の記録 → Loki の該当コンテナのログの直近。
- 直し方：該当のコンテナを `docker compose restart`。gemini-egress は prod2 の tinyproxy の状態も見る。繰り返すときは原因を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=ContainerUnhealthy --duration=PERIOD --comment=REASON`

## ContainerStateStale

- 札：page
- 何が起きているか：prod1 の状態書き係（`scripts/ops/container_state.py`、ubuntu の cron で毎分）が 5 分以上 textfile を書いていない、または値が無い状態が 2 分続いた。この間はコンテナが不健康になっても ContainerUnhealthy が鳴らない。
- 最初に見るもの：prod1 の `crontab -l` に container_state の行があるか → `/tmp/container-state.log` の最後の行（失敗のときだけ書かれる）→ `/home/ubuntu/node_exporter_textfile/container_state.prom` の時刻。
- 直し方：ログの原因（docker が読めない・書けない）を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=ContainerStateStale --duration=PERIOD --comment=REASON`
```

### 4-7. 新設の tests/sandbox/container-state.sh（ファイル全体）

置き方の規則は `tests/sandbox/README.md`。GitHub の試験場（`.github/workflows/sandbox-test.yml`）で動かす。secrets と本番には触れない。

```bash
#!/bin/bash
# ADR-1012 段階3 便E: 状態書き係（scripts/ops/container_state.py）と見張り 2 本を GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=container-state
# secrets・本番には触れない。後始末は trap で行う。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
PROM=prom/prometheus:v3.11.3
cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    docker inspect -f '{{.Name}} {{.State.Running}} {{json .State.Health}}' bine-worker bine-beat bine-beat-old 2>&1 | head -c 3000 || true
  fi
  docker rm -f bine-worker bine-beat bine-beat-old >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

echo "== 1. 状態書き係の試験"
python3 --version
python3 scripts/tests/test_container_state.py

echo "== 2. 見張りの検査"
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml

echo "== 3. 本物の docker で状態を書く（健康・不健康・止まった古いもの・無いもの）"
docker run -d --name bine-worker --label com.docker.compose.service=celery-worker --health-cmd true --health-interval 2s alpine:3.24 sleep 600 >/dev/null
docker run -d --name bine-beat --label com.docker.compose.service=celery-beat --health-cmd false --health-interval 2s --health-retries 1 alpine:3.24 sleep 600 >/dev/null
docker run --name bine-beat-old --label com.docker.compose.service=celery-beat alpine:3.24 true
for i in $(seq 1 15); do
  w=$(docker inspect -f '{{.State.Health.Status}}' bine-worker)
  b=$(docker inspect -f '{{.State.Health.Status}}' bine-beat)
  if [ "$w" = healthy ] && [ "$b" = unhealthy ]; then break; fi
  sleep 2
done
docker inspect -f '{{.Name}} {{.State.Running}} {{.State.Health.Status}}' bine-worker bine-beat
docker inspect -f '{{.Name}} {{.State.Running}}' bine-beat-old
TF="$OUT/textfile"
mkdir -p "$TF"
time CONTAINER_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/container_state.py
cat "$TF/container_state.prom"
expect() { grep -qxF "$1" "$TF/container_state.prom" || { echo "NG: missing line: $1"; exit 1; }; }
expect 'salesanchor_container_unhealthy{service="celery-worker"} 0'
expect 'salesanchor_container_running{service="celery-worker"} 1'
expect 'salesanchor_container_unhealthy{service="celery-beat"} 1'
expect 'salesanchor_container_running{service="celery-beat"} 1'
for s in discord-gateway gemini-egress backend; do
  expect "salesanchor_container_unhealthy{service=\"$s\"} 0"
  expect "salesanchor_container_running{service=\"$s\"} 0"
done
[ "$(grep -c '^salesanchor_container_state_last_run_timestamp_seconds ' "$TF/container_state.prom")" = 1 ] || { echo "NG: timestamp line"; exit 1; }
[ "$(stat -c %a "$TF/container_state.prom")" = 644 ] || { echo "NG: mode"; exit 1; }
docker run --rm -i --entrypoint promtool "$PROM" check metrics < "$TF/container_state.prom"

echo "== 4. 失敗の試験（docker に繋がらない → rc=1・ファイルは変わらない・一時ファイルが残らない）"
before=$(sha256sum "$TF/container_state.prom")
set +e
DOCKER_HOST=unix:///nonexistent.sock CONTAINER_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/container_state.py
rc=$?
set -e
echo "rc=$rc"
[ "$rc" -eq 1 ] || { echo "NG: rc"; exit 1; }
[ "$(sha256sum "$TF/container_state.prom")" = "$before" ] || { echo "NG: file changed"; exit 1; }
ls -a "$TF"
if ls -A "$TF" | grep -q '^\.container_state\.'; then echo "NG: temp left"; exit 1; fi
echo "ALL OK"
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-e-impl/ に置く）

5-1. 試験：作業場所で `python3 scripts/tests/test_container_state.py 2>&1 | tail -15` が `OK`（8 件）。python3 の版も `python3 --version` で記録する（3.12 以外で venv を作らない。標準ライブラリだけなので venv は要らない）

5-2. GitHub の試験場で試す（Mac で仮想マシンを作らない。`docs/ops/runner-commands.md:351`）:
- §10 の push の後に、作業場所で `gh workflow run sandbox-test.yml --ref release/ai-ops-container-state-bin-e -f test=container-state` を実行し、10 秒後に `gh run list --workflow sandbox-test.yml --branch release/ai-ops-container-state-bin-e -L 1 --json databaseId,url,status` の出力を貼る
- 結果は待たない（Opus が見る）。報告に run の URL を書く
- 中身（§4-7）：状態書き係の試験 8 つ・`check_alert_rules.py`・`promtool check rules`・`promtool test rules`・本物の docker での 0/1 の書き出しと `promtool check metrics`・docker に繋がらないときの rc=1 とファイル不変。最後に `ALL OK` が出れば合格

5-3. 差分：`git diff origin/main --stat` が §3 のファイルだけ。加えて `git diff origin/main | grep "^-[^-]"` の出力が、alerts.md の 3 行目の旧行と、試験ファイルの 4 行目の旧行の 2 行だけ

5-4. 書式の手元確認：`bash -n tests/sandbox/container-state.sh; echo rc=$?` が `rc=0`、`python3 -m py_compile scripts/ops/container_state.py scripts/tests/test_container_state.py; echo rc=$?` が `rc=0`

5-5. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI と試験場の結果は Opus が見る）

## 6. 分岐ごとの対処

- §4 の目印の行が見つからない（ほかの PR が先に変えた）→ origin/main で `git show origin/main:docs/runbooks/alerts.md | tail -20` のように該当のファイルを読み直し、同じ意味の位置（末尾）に足す。本数（22）が既に別の数に変わっていたら、その数に 2 を足した値にする。決められなければ NEEDS_DECISION: で出力を貼る
- §5-2 の `gh workflow run` が権限や名前の誤りで起動しない → 出力の原文を貼り、PR は作って報告する（Opus が起動する）
- 試験が落ちる → 試験ではなく §4 の完成形との違いを直す。§4 のとおりで落ちるなら原文を貼って BLOCKED:

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 状態書き係の試験 8 つが pass | §5-1 と CI（deploy-script-test） |
| 見張り 2 本が検査を通り、単体試験 5 つ（既存を含め全部）が pass | 試験場（§5-2）と CI（monitoring-check） |
| 本物の docker で、健康・不健康・止まった古いもの・無いものを正しく 0/1 で書き、失敗のときはファイルを変えない | 試験場（§5-2）の記録の `ALL OK` |
| 触ったファイルが §3 だけで、消した行は本数の旧行 2 行だけ | §5-3 |
| 本番：cron 登録の後、prod2 の Prometheus で `salesanchor_container_unhealthy` が 4 サービスぶん 0 で読め、ContainerStateStale が鳴っていない | §8 の Prometheus の問い合わせの生出力 |
| 本番：便D の誤判定 0 の確認として、cron 登録から 24 時間 `max_over_time(salesanchor_container_unhealthy{service=~"celery-worker\|celery-beat\|discord-gateway\|gemini-egress"}[24h])` が 4 サービスとも 0 | §8 の Prometheus の問い合わせの生出力 |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 の完成形と照らし、CI が緑なら、危険 PR の GO 手順（ADR-136）で「POの委任に基づくClaude Opus発行」の GO を PR に記録してマージする
2. deploy.yml の成功を Actions の記録で確かめる。prod2 の見張りの設定（alert_rules.yml）が prod2 に届いたかを、prod2 の Prometheus の `/api/v1/rules` に ContainerUnhealthy と ContainerStateStale があることで確かめる（届かない場合は既存の監視設定の配置手順を確かめて PO の `!` を用意する）
3. 登録の前に、prod1 に `scripts/ops/container_state.py` が届いていることを確かめる。届いた後、ContainerStateStale は値が無い（absent）ので 2 分後から鳴る。鳴る前に登録を終えるか、鳴った場合は登録後に止むことを確かめる
4. PO の `!` スクリプトで prod1 の crontab に 1 行足す。中身：①`crontab -l > /home/ubuntu/crontab.bak-container-state` で控え ②`env -i PATH=/usr/bin:/bin /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/container_state.py; echo rc=$?` で cron と同じ条件で 1 回試す（rc=0 でなければ登録しない）③`* * * * * /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/container_state.py >> /tmp/container-state.log 2>&1` を足す（同じ行が既にあれば足さない）④`crontab -l` と `container_state.prom` の中身と、サービスごとのコンテナの名前（4 サービスと backend の 5 つについて `docker ps -a --filter label=com.docker.compose.service=celery-beat --format '{{.Names}} {{.Status}}'`）を出す
5. 登録の 5 分後に、prod2 の Prometheus に `salesanchor_container_unhealthy` と `ALERTS{alertname=~"Container.*"}` を問い合わせる（PO の `!`・読むだけ）
6. 登録の 24 時間後に §7 の `max_over_time` を問い合わせ、便D の 24 時間の誤判定 0 を確かめる。0 でなければ便G に進まず、該当サービスの健康診断の閾値を見直す
7. 生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-e-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：prod1 で毎分 docker を数回呼ぶ（5 サービス × ps と inspect）。1 回の所要は試験場の `time` の記録で見る。毎分のログは書かない
- 弊害：ContainerUnhealthy は page なので、健康診断の誤判定があると Discord に通知が出る（処置はしない）。誤判定は便D の 24 時間の観測で 0 を確かめる（§8-6）
- 弊害：gemini-egress は prod2 の tinyproxy が落ちると unhealthy になり、利用者への影響が無くても page が鳴る（手順書に影響を書いた）
- 戻し方：PO の `!` で prod1 の crontab から container_state の行を消す（控えから戻す）→ この PR の revert を main にマージ → 次の deploy で見張りと状態書き係が外れる。`container_state.prom` は revert の後に PO の `!` で消す（残すと最後の値が読まれ続ける）

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-container-state-bin-e --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16・10-17 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-container-state-bin-e` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-container-state-bin-e -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-container-state-bin-e --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage3-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: scripts/ops/container_state.py, scripts/tests/test_container_state.py, tests/sandbox/container-state.sh, .github/workflows/deploy-script-test.yml, monitoring/prometheus/alert_rules.yml, monitoring/prometheus/tests/alert_rules_test.yml, docs/runbooks/alerts.md, docs/handoff/ai-ops-247/card-stage3-bin-e.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（docs/runbooks/alerts.md・monitoring/prometheus/tests/alert_rules_test.yml と、§13 の「（未記入）」を書き換えるこのカード））
- 本文に「危険 PR（scripts/）。GO・マージと反映後の観測は Opus がカード §8 の順で行う」と 1 行書く
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力（長いものは生出力のパスと要点の行）／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage3/bin-e-impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep は §5-2 の run の一覧を読む前の 10 秒にだけ使ってよい。CI・試験場・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

- 実装担当（Sonnet）の報告（2026-10-17）。試験 8 件 OK・check_alert_rules.py OK（Prometheus 26 本）。
- 判断を要した点（事実）：origin/main の alert_rules.yml は便E 前で 24 本（`grep -c '^ *- alert:'`）だったが、手順書と試験の冒頭は 22 本のままだった。カードの「24」ではなく、検査の出力（26 本）に合わせて 26 に書いた。
- GitHub の試験場の run と PR の URL は PR 本文と担当の完了報告に記載。

END OF CARD
