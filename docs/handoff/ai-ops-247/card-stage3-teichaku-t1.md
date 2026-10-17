# 実装カード 段階3 定着便 T1 — 健康診断の欠けを止めて鳴らす

> この文書は何か：AI保守運用24時間化 段階3 の定着便 T1 の作業指示書です。便D で 4 つのコンテナに付けた健康診断（healthcheck）が、誰かの変更で消えたり無効にされたりしたときに、①CI でマージ前に止め、②本番で動いているのに健康診断が無いコンテナがあれば見張りで知らせます。今は、健康診断が消えると状態書き係が「不健康 0」を書き続け、固まっても気づけません。

- 設計: docs/handoff/ai-ops-247/stage3-design.md §11（定着便）・§11-4 T1・§11-5
- 点検の結果: /tmp/CC報告ファイル/ai-ops-stage3/governance-e/evidence.md §2 #1（×）
- 対象ADR: ADR-1012（本テーマ）・ADR-135・ADR-136
- 状態: 定着便の着手は PO 承認 y（2026-10-17）。§2-2 の決定は Opus の技術判断（設計の目的・範囲を変えない）
- 危険便: はい（`scripts/` を含む。ADR-135・ADR-136）。GO は「POの委任に基づくClaude Opus発行」で Opus が出し、マージと反映後の観測も Opus が行う。担当はマージしない
- 担当: 実装 Sonnet／審査・GO・マージ・反映確認 Opus／prod2 への見張りの配置は PO の `!`

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○（まだ無いファイルのパスは「新設の」を付けてバッククォートなしで書く） |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（健康診断の欠けを止めて鳴らすことだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の試験名・§5-2 の NG 行） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 0cfcaee7f で確かめた） |
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

作業を始める前に、報告の冒頭へ「本報告はカード 段階3 定着便 T1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 健康診断の欠けの検査（新設の monitoring/scripts/check_app_healthchecks.py）と試験（新設の monitoring/scripts/tests/test_check_app_healthchecks.py）（§4-1・§4-2）
2. 状態書き係に「動いているのに健康診断が無い」の値を足す（`scripts/ops/container_state.py`）と試験の追加（`scripts/tests/test_container_state.py`）（§4-3・§4-4）
3. CI の常時起動の検査で 1・2 を走らせる（`.github/workflows/monitoring-check.yml`）（§4-5）
4. 見張り 1 本（`monitoring/prometheus/alert_rules.yml` の末尾）と単体試験 2 件（`monitoring/prometheus/tests/alert_rules_test.yml` の末尾）（§4-6・§4-7）
5. 手順書 1 節（`docs/runbooks/alerts.md`）（§4-8）

入れない:
- `docker-compose.yml` の変更（健康診断の中身は変えない）
- `.github/workflows/deploy-script-test.yml` の変更（今のまま残す）
- 処置（再起動）・保守 API の変更（便F・便G）
- 既存の見張りの式・札の変更
- prod2 への配置（反映後に PO の `!` で行う。§8）

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 0cfcaee7f・生出力 /tmp/CC報告ファイル/ai-ops-stage3/teichaku-recon/）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 状態書き係の summarize は、Health が無い動いているコンテナを unhealthy=0 とする。試験 test_running_without_health もこれを確かめている | `scripts/ops/container_state.py:48-52`・`scripts/tests/test_container_state.py:36-37` |
| F2 | 状態書き係の対象は 5 サービス（4 つ＋backend）。main は `{service: summarize(read_states(service))}` で 1 サービスにつき 1 回 docker を読む | `scripts/ops/container_state.py:18,92` |
| F3 | 4 サービスの healthcheck は CMD-SHELL のリスト形式 | `docker-compose.yml:277-282,317-322,368-373,404-409` |
| F4 | compose の `test` は文字列かリスト。リストの先頭は `NONE`・`CMD`・`CMD-SHELL` のどれかで、`NONE` は健康診断を無効にする。`disable: true` でも無効になる。文字列は `CMD-SHELL` と同じ | docs.docker.com/reference/compose-file/services/ の healthcheck（2026-10-17 WebFetch。Context7 は月の上限で使えず） |
| F5 | monitoring-check.yml は常に起動し、:30 の正規表現で関係ファイルかを判定する。関係があれば Python 3.12 と pyyaml を用意する（:37-45）。見張りの検査は :59-61、promtool は :63-68 | `.github/workflows/monitoring-check.yml` |
| F6 | 既存の validate_tokens.py の healthcheck 確認は監視用サービスだけで、警告のみ（advisory） | `monitoring/scripts/validate_tokens.py:11,57,202-225` |
| F7 | 見張りの検査：`runbook_url` は `alerts.md#` の後ろにルール名の小文字。見出しの無いルールと、ルールの無い見出しは CI で NG | `monitoring/scripts/check_alert_rules.py:17,55,62,70` |
| F8 | 見張りは今 26 本。手順書の冒頭（:3）と試験の冒頭（:4）に「26 本」と書いてある | `grep -c '^ *- alert:' monitoring/prometheus/alert_rules.yml` = 26・`docs/runbooks/alerts.md:3`・`monitoring/prometheus/tests/alert_rules_test.yml:4` |
| F9 | alert_rules.yml の最後のルールは ContainerStateStale（335 行で終わる）。試験の最後は ContainerStateFresh（763 行で終わる）。手順書の最後の節は `## ContainerStateStale`（281 行で終わる） | 各ファイルの `tail` |
| F10 | monitoring/scripts/tests/ に test_check_config_drift.sh がある（python の試験はまだ無い） | `ls monitoring/scripts/tests` |

### 2-2. 決めたこと（Opus）

| # | 決めたこと | 理由 |
|---|---|---|
| T1-1 | 検査の対象は 4 サービス。状態書き係の SERVICES から backend を除いたものと一致することを試験で確かめる | 対象の二重定義がずれたまま放置されないため |
| T1-2 | 合格の条件：healthcheck があり、`disable: true` でなく、`test` が空でない文字列か、先頭が `CMD`・`CMD-SHELL` で中身のあるリスト | F4 の公式の書き方で「無効」になる形を全部落とす |
| T1-3 | 状態書き係は summarize を変えず、別の関数 healthcheck_missing を足す。既存の 3 つの指標と既存の試験 8 件は変えない | 便E の見張りに影響させない（stage3-design.md §11-7） |
| T1-4 | 見張りは warning・ticket・for 10m | 診断が無いだけで今は動いているので、夜に人を起こさない（stage3-design.md §11-6） |
| T1-5 | `import yaml` は検査の main の中で行う | pyyaml の無い手元でも試験の大半が動くようにする。本物の docker-compose.yml を読む試験は pyyaml がある CI で必ず動く |

## 3. 触るファイル（これ以外は触らない）

- 新規: 新設の monitoring/scripts/check_app_healthchecks.py（§4-1）
- 新規: 新設の monitoring/scripts/tests/test_check_app_healthchecks.py（§4-2）
- 変更: `scripts/ops/container_state.py`（§4-3）
- 変更: `scripts/tests/test_container_state.py`（末尾に追記のみ・§4-4）
- 変更: `.github/workflows/monitoring-check.yml`（:30 の 1 行の置き換えと、1 ステップの追記・§4-5）
- 変更: `monitoring/prometheus/alert_rules.yml`（末尾に追記のみ・§4-6）
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`（冒頭のコメント 1 行の置き換えと、末尾に追記・§4-7）
- 変更: `docs/runbooks/alerts.md`（冒頭の本数の置き換えと、末尾に追記・§4-8）
- 変更: `docs/handoff/ai-ops-247/card-stage3-teichaku-t1.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. 新設の monitoring/scripts/check_app_healthchecks.py（ファイル全体）

```python
#!/usr/bin/env python3
"""ADR-1012 段階3 定着便 T1: アプリの 4 サービスの健康診断（healthcheck）が消えていないかを検査する。

docker-compose.yml を読み、対象の各サービスに healthcheck があり、disable で止められておらず、
test が空でも NONE でもないことを確かめる。1 つでも欠ければ NG の行を出して終了コード 1。
対象は scripts/ops/container_state.py の SERVICES から backend を除いたものと同じ（試験で一致を確かめる）。
使い方: python3 monitoring/scripts/check_app_healthchecks.py [docker-compose.yml のパス]
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGETS = ("celery-worker", "celery-beat", "discord-gateway", "gemini-egress")


def test_is_valid(test) -> bool:
    """compose の test が有効な健康診断か。文字列は CMD-SHELL と同じ。リストの先頭 NONE は無効。"""
    if isinstance(test, str):
        return bool(test.strip())
    if isinstance(test, list) and len(test) >= 2 and test[0] in ("CMD", "CMD-SHELL"):
        return all(isinstance(x, str) and x.strip() for x in test[1:])
    return False


def problems(compose: dict) -> list[str]:
    found = []
    services = (compose or {}).get("services") or {}
    for name in TARGETS:
        svc = services.get(name)
        if not isinstance(svc, dict):
            found.append(f"{name}: サービスがありません")
            continue
        hc = svc.get("healthcheck")
        if not isinstance(hc, dict):
            found.append(f"{name}: healthcheck がありません")
            continue
        if hc.get("disable") is True:
            found.append(f"{name}: healthcheck が disable: true です")
            continue
        if not test_is_valid(hc.get("test")):
            found.append(f"{name}: healthcheck の test が空か NONE です（{hc.get('test')!r}）")
    return found


def main(argv: list[str]) -> int:
    import yaml

    path = Path(argv[1]) if len(argv) > 1 else REPO / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    found = problems(compose)
    for p in found:
        print(f"NG {p}")
    if found:
        return 1
    print(f"OK healthcheck {len(TARGETS)} サービス（{path.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### 4-2. 新設の monitoring/scripts/tests/test_check_app_healthchecks.py（ファイル全体）

```python
#!/usr/bin/env python3
"""monitoring/scripts/check_app_healthchecks.py の試験（ADR-1012 段階3 定着便 T1）。"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


chk = load("check_app_healthchecks", HERE.parent / "check_app_healthchecks.py")
cs = load("container_state", REPO / "scripts" / "ops" / "container_state.py")

try:
    import yaml
except ImportError:
    yaml = None

GOOD = {"test": ["CMD-SHELL", "exit 0"], "interval": "30s"}


def compose_with(**overrides):
    services = {name: {"image": "x", "healthcheck": dict(GOOD)} for name in chk.TARGETS}
    services.update(overrides)
    return {"services": services}


class ProblemsTest(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(chk.problems(compose_with()), [])

    def test_string_test_is_good(self):
        self.assertEqual(chk.problems(compose_with(**{"celery-beat": {"healthcheck": {"test": "exit 0"}}})), [])

    def test_missing_healthcheck(self):
        found = chk.problems(compose_with(**{"celery-beat": {"image": "x"}}))
        self.assertEqual(found, ["celery-beat: healthcheck がありません"])

    def test_disable_true(self):
        found = chk.problems(compose_with(**{"discord-gateway": {"healthcheck": {"disable": True}}}))
        self.assertEqual(found, ["discord-gateway: healthcheck が disable: true です"])

    def test_none(self):
        found = chk.problems(compose_with(**{"gemini-egress": {"healthcheck": {"test": ["NONE"]}}}))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("gemini-egress: healthcheck の test が空か NONE です"))

    def test_empty_string(self):
        found = chk.problems(compose_with(**{"celery-worker": {"healthcheck": {"test": "  "}}}))
        self.assertEqual(len(found), 1)

    def test_cmd_shell_without_command(self):
        found = chk.problems(compose_with(**{"celery-worker": {"healthcheck": {"test": ["CMD-SHELL"]}}}))
        self.assertEqual(len(found), 1)

    def test_missing_service(self):
        c = compose_with()
        del c["services"]["celery-beat"]
        self.assertEqual(chk.problems(c), ["celery-beat: サービスがありません"])

    def test_targets_match_container_state(self):
        self.assertEqual(set(chk.TARGETS), set(cs.SERVICES) - {"backend"})


@unittest.skipIf(yaml is None, "pyyaml が無い（CI では入る）")
class RealFileTest(unittest.TestCase):
    def test_real_compose_passes(self):
        self.assertEqual(chk.main(["x", str(REPO / "docker-compose.yml")]), 0)

    def test_broken_copy_fails(self):
        with open(REPO / "docker-compose.yml", encoding="utf-8") as f:
            compose = yaml.safe_load(f)
        for broken in ("remove", "none", "disable"):
            c = yaml.safe_load(yaml.safe_dump(compose))
            if broken == "remove":
                del c["services"]["celery-beat"]["healthcheck"]
            elif broken == "none":
                c["services"]["celery-beat"]["healthcheck"]["test"] = ["NONE"]
            else:
                c["services"]["celery-beat"]["healthcheck"]["disable"] = True
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "docker-compose.yml")
                with open(path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(c, f, allow_unicode=True)
                with self.subTest(broken=broken):
                    self.assertEqual(chk.main(["x", path]), 1)


if __name__ == "__main__":
    unittest.main()
```

### 4-3. `scripts/ops/container_state.py`

3 か所を変える。ほかの行は変えない。

(a) summarize の関数（:48-52）の直後に、空行 2 行を挟んで次の関数を足す:

```python
def healthcheck_missing(states: list[dict]) -> int:
    """動いているコンテナに健康診断（State.Health）が無ければ 1（定着便 T1）。"""
    running = [s for s in states if s.get("Running")]
    return 1 if any("Health" not in s for s in running) else 0
```

(b) render の定義行（:55）と、`return "\n".join(lines) + "\n"`（:73）の直前を次のように変える:

変更前（:55）:
```python
def render(results: dict[str, tuple[int, int]], now: float) -> str:
```
変更後:
```python
def render(results: dict[str, tuple[int, int]], now: float, missing: dict[str, int] | None = None) -> str:
```

`return "\n".join(lines) + "\n"`（:73）の直前に足す（字下げは関数の中の 4 つ）:
```python
    if missing is not None:
        lines += [
            "# HELP salesanchor_container_healthcheck_missing 1 if a running container of the service has no healthcheck.",
            "# TYPE salesanchor_container_healthcheck_missing gauge",
        ]
        for service, value in missing.items():
            lines.append(f'salesanchor_container_healthcheck_missing{{service="{service}"}} {value}')
```

(c) main の try の中（:92-93）を変える:

変更前:
```python
        results = {service: summarize(read_states(service)) for service in SERVICES}
        write_atomic(render(results, time.time()))
```
変更後:
```python
        states = {service: read_states(service) for service in SERVICES}
        results = {service: summarize(s) for service, s in states.items()}
        missing = {service: healthcheck_missing(s) for service, s in states.items()}
        write_atomic(render(results, time.time(), missing))
```

### 4-4. `scripts/tests/test_container_state.py`

`if __name__ == "__main__":`（:80）の直前に、空行 2 行を挟んで次を足す（既存の試験は変えない）:

```python
class HealthcheckMissingTest(unittest.TestCase):
    def test_none_running(self):
        self.assertEqual(cs.healthcheck_missing([]), 0)

    def test_running_with_health(self):
        self.assertEqual(cs.healthcheck_missing([{"Running": True, "Health": {"Status": "starting"}}]), 0)

    def test_running_without_health(self):
        self.assertEqual(cs.healthcheck_missing([{"Running": True}]), 1)

    def test_stopped_without_health_not_counted(self):
        self.assertEqual(cs.healthcheck_missing([{"Running": False}, {"Running": True, "Health": {"Status": "healthy"}}]), 0)

    def test_main_writes_missing_line(self):
        def fake(args):
            if args[0] == "ps":
                return "abc\n"
            return json.dumps([{"State": {"Running": True}}])

        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(cs, "TEXTFILE_DIR", d), mock.patch.object(cs, "run_docker", side_effect=fake):
                self.assertEqual(cs.main(), 0)
            with open(os.path.join(d, "container_state.prom")) as f:
                lines = f.read().splitlines()
            self.assertIn('salesanchor_container_healthcheck_missing{service="celery-beat"} 1', lines)
            self.assertIn('salesanchor_container_unhealthy{service="celery-beat"} 0', lines)
```

### 4-5. `.github/workflows/monitoring-check.yml`

(a) :30 の 1 行を置き換える。

変更前:
```
          if echo "$CHANGED" | grep -qE "^(monitoring/|docker-compose(\.monitoring|\.exporters)?\.yml|\.env(\.monitoring)?\.example|\.github/workflows/monitoring-check\.yml|docs/runbooks/alerts\.md)"; then
```
変更後:
```
          if echo "$CHANGED" | grep -qE "^(monitoring/|docker-compose(\.monitoring|\.exporters)?\.yml|\.env(\.monitoring)?\.example|\.github/workflows/monitoring-check\.yml|docs/runbooks/alerts\.md|scripts/ops/container_state\.py|scripts/tests/test_container_state\.py)"; then
```

(b) 「アラートルールの札・手順書リンク検査」のステップ（:59-61）の直後に、空行 1 行を挟んで次のステップを足す:

```yaml
      - name: アプリの健康診断の欠け検査と状態書き係の試験（ADR-1012 段階3 定着便 T1）
        if: steps.changes.outputs.relevant == 'true'
        run: |
          python3 monitoring/scripts/check_app_healthchecks.py
          python3 monitoring/scripts/tests/test_check_app_healthchecks.py -v
          python3 scripts/tests/test_container_state.py -v
```

### 4-6. `monitoring/prometheus/alert_rules.yml` の末尾

ContainerStateStale の `runbook_url` の行（最終行）の後に、空行 1 行を挟んで次を足す（同じ container_state_alerts のグループの中。字下げは ContainerStateStale と同じ）:

```yaml
      # 動いているのに健康診断（healthcheck）が無い。この間 ContainerUnhealthy は鳴らない（ADR-1012 段階3 定着便 T1）
      - alert: ContainerHealthcheckMissing
        expr: salesanchor_container_healthcheck_missing{service=~"celery-worker|celery-beat|discord-gateway|gemini-egress"} == 1
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "コンテナ {{ $labels.service }} に健康診断がありません"
          description: "prod1 の {{ $labels.service }} は動いていますが、健康診断（healthcheck）がありません。固まっても ContainerUnhealthy が鳴りません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerhealthcheckmissing"
```

### 4-7. `monitoring/prometheus/tests/alert_rules_test.yml`

(a) :4 を置き換える。変更前 `# 全 26 本が擬似の系列で鳴ること、tier と runbook_url が付くことを確かめる。` → 変更後 `# 全 27 本が擬似の系列で鳴ること、tier と runbook_url が付くことを確かめる。`

(b) 末尾（ContainerStateFresh の `exp_alerts: []` の後）に、空行 1 行を挟んで次を足す:

```yaml
  # --- 定着便 T1 ---
  - name: ContainerHealthcheckMissingFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_container_healthcheck_missing{service="celery-beat",instance="app-vps",job="node-exporter"}'
        values: '1x20'
    alert_rule_test:
      - eval_time: 12m
        alertname: ContainerHealthcheckMissing
        exp_alerts:
          - exp_labels:
              service: celery-beat
              instance: app-vps
              job: node-exporter
              severity: warning
              tier: ticket
            exp_annotations:
              summary: "コンテナ celery-beat に健康診断がありません"
              description: "prod1 の celery-beat は動いていますが、健康診断（healthcheck）がありません。固まっても ContainerUnhealthy が鳴りません。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#containerhealthcheckmissing"

  - name: ContainerHealthcheckMissingQuiet
    interval: 1m
    input_series:
      - series: 'salesanchor_container_healthcheck_missing{service="celery-beat",instance="app-vps",job="node-exporter"}'
        values: '0x20'
      - series: 'salesanchor_container_healthcheck_missing{service="backend",instance="app-vps",job="node-exporter"}'
        values: '1x20'
    alert_rule_test:
      - eval_time: 15m
        alertname: ContainerHealthcheckMissing
        exp_alerts: []
```

### 4-8. `docs/runbooks/alerts.md`

(a) :3 の `（Prometheus 26 本）` を `（Prometheus 27 本）` に置き換える（ほかの文字は変えない）。

(b) 末尾（`## ContainerStateStale` の節の最後の行の後）に、空行 1 行を挟んで次を足す:

```markdown
## ContainerHealthcheckMissing

- 札：ticket
- 何が起きているか：prod1 の celery-worker・celery-beat・discord-gateway・gemini-egress のどれかが動いているのに、健康診断（docker-compose.yml の healthcheck）が無い状態が 10 分続いた。定義が消えた・無効にされた、または古い定義のまま作り直された。この間はそのコンテナが固まっても ContainerUnhealthy が鳴らない。値は prod1 の `scripts/ops/container_state.py` が毎分 textfile に書く。
- 影響：今の利用者への影響は無い。翌営業日までに直す。
- 最初に見るもの：main の docker-compose.yml の該当サービスの healthcheck（CI の `monitoring/scripts/check_app_healthchecks.py` が通っているか）→ prod1 で `docker inspect -f '{{json .Config.Healthcheck}}'`（該当のコンテナ）。
- 直し方：main に定義があれば、次の deploy で作り直されて戻る。main から消えていれば、消した変更を戻す PR を出して Opus に報告する。
- 止め方：`amtool silence add alertname=ContainerHealthcheckMissing --duration=PERIOD --comment=REASON`
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/ai-ops-stage3/teichaku-t1-impl/ に置く）

5-1. 試験：作業場所で次の 3 つを実行し、それぞれの最後の 15 行を貼る。python3 の版も `python3 --version` で記録する（3.12 以外で venv を作らない）
- `python3 scripts/tests/test_container_state.py -v 2>&1 | tail -15` → `Ran 13 tests` と `OK`
- `python3 monitoring/scripts/tests/test_check_app_healthchecks.py -v 2>&1 | tail -15` → `OK`（pyyaml が無ければ RealFileTest の 2 件が skipped と出る。そのときは skipped と書いて報告する。CI で動く）
- `python3 monitoring/scripts/check_app_healthchecks.py 2>&1 | tail -5` → `OK healthcheck 4 サービス（docker-compose.yml）`（pyyaml が無ければ ModuleNotFoundError と書いて報告する）

5-2. 見張りの検査：`python3 monitoring/scripts/check_alert_rules.py 2>&1 | tail -10` の出力（27 本と出る。pyyaml が無ければその旨を報告する。CI で動く）

5-3. 差分：`git diff origin/main --stat` が §3 のファイルだけ。加えて `git diff origin/main | grep "^-[^-]"` の出力が次の 6 行だけ：container_state.py の render の定義行・main の 2 行／monitoring-check.yml の :30 の旧行／alerts.md の :3 の旧行／試験ファイルの :4 の旧行

5-4. 書式の手元確認：`python3 -m py_compile scripts/ops/container_state.py scripts/tests/test_container_state.py monitoring/scripts/check_app_healthchecks.py monitoring/scripts/tests/test_check_app_healthchecks.py; echo rc=$?` が `rc=0`

5-5. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI の結果は Opus が見る）

## 6. 分岐ごとの対処

- §4 の目印の行が見つからない（ほかの PR が先に変えた）→ origin/main で該当のファイルを `git show origin/main:docs/runbooks/alerts.md | tail -20` のように読み直し、同じ意味の位置に足す。本数（26）が既に別の数に変わっていたら、その数に 1 を足した値にする。決められなければ NEEDS_DECISION: で出力を貼る
- 試験が落ちる → 試験ではなく §4 の完成形との違いを直す。§4 のとおりで落ちるなら原文を貼って BLOCKED:
- 本物の docker-compose.yml で check_app_healthchecks.py が NG を出す → 直さずに NG の行を貼って BLOCKED:（docker-compose.yml は触らない）

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 4 サービスのどれかの healthcheck を消す・`["NONE"]`・`disable: true` にすると検査が落ちる | CI（monitoring-check）の test_broken_copy_fails が pass |
| 本物の docker-compose.yml は検査を通る | CI の `OK healthcheck 4 サービス` |
| 状態書き係の試験 13 件が、常時起動の monitoring-check で動く | CI のログの `Ran 13 tests` と `OK` |
| 見張り 1 本が検査を通り、単体試験（既存を含め全部）が pass | CI（monitoring-check の check_alert_rules・promtool） |
| 触ったファイルが §3 だけで、消した行が §5-3 の 6 行だけ | §5-3 |
| 本番：反映後に `salesanchor_container_healthcheck_missing` が 5 サービスぶん読め、4 サービスが 0。ContainerHealthcheckMissing が鳴っていない | §8 の Prometheus の問い合わせの生出力 |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 の完成形と照らし、CI が緑なら、危険 PR の GO 手順（ADR-136）で「POの委任に基づくClaude Opus発行」の GO を PR に記録してマージする
2. deploy.yml の成功を Actions の記録で確かめる。deploy で prod1 の `scripts/ops/container_state.py` が入れ替わり、次の cron（毎分）から新しい値が書かれる
3. prod2 の Prometheus に `salesanchor_container_healthcheck_missing` を問い合わせ、5 サービスぶんの値があり、4 サービスが 0 であることを確かめる（Grafana の読み取りトークンで Opus が行う）
4. prod2 への見張りの配置は、便E と同じ形の PO の `!` スクリプト（scp → promtool で検査 → 控え → install → コンテナの中で reload → `/api/v1/rules` に ContainerHealthcheckMissing があることを確かめる）を Opus が用意する。定着便 T2 の workflow ができた後はそちらで行う
5. 配置の 15 分後に `ALERTS{alertname="ContainerHealthcheckMissing"}` が空であることを確かめる
6. 生出力は /tmp/CC報告ファイル/ai-ops-stage3/teichaku-t1-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：検査に誤りがあると、正しい docker-compose.yml の PR が落ちる → 本物のファイルで通る試験を置いた（§4-2）
- 弊害：prod1 の状態書き係の出力が 7 行増える。docker の呼び出しの回数は変わらない（読み取った結果を 2 つの関数で使う）
- 戻し方：この PR の revert を main にマージ → 次の deploy で状態書き係が元に戻る。prod2 の見張りは控え（§8-4 で取る）から戻して reload する。値が残っても見張りが無ければ鳴らない

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage3-teichaku-t1 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16・10-17 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage3-teichaku-t1` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage3-teichaku-t1 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage3-teichaku-t1 --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage3-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: monitoring/scripts/check_app_healthchecks.py, monitoring/scripts/tests/test_check_app_healthchecks.py, scripts/ops/container_state.py, scripts/tests/test_container_state.py, .github/workflows/monitoring-check.yml, monitoring/prometheus/alert_rules.yml, monitoring/prometheus/tests/alert_rules_test.yml, docs/runbooks/alerts.md, docs/handoff/ai-ops-247/card-stage3-teichaku-t1.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（scripts/ops/container_state.py・.github/workflows/monitoring-check.yml・docs/runbooks/alerts.md・monitoring/prometheus/tests/alert_rules_test.yml と、§13 の「（未記入）」を書き換えるこのカード））
- 本文に「危険 PR（scripts/）。GO・マージと反映後の観測は Opus がカード §8 の順で行う」と 1 行書く
- `.github/workflows/` の変更欄には「既存 monitoring-check.yml に 1 ステップ追記と判定の正規表現の拡張のみ。新規ワークフローなし」と書く
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力（長いものは生出力のパスと要点の行）／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage3/teichaku-t1-impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep は使わない。CI・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

本報告はカード 段階3 定着便 T1 の実行結果である。

- 試験: test_container_state 13 件 OK／test_check_app_healthchecks 11 件 OK（pyyaml あり・skipped なし）／check_app_healthchecks.py は OK healthcheck 4 サービス／check_alert_rules.py は Prometheus 27 rules／py_compile rc=0
- python3 は 3.14.3（手元）。promtool は手元に無く未実行（CI で実行）
- 生出力: /tmp/CC報告ファイル/ai-ops-stage3/teichaku-t1-impl/
- 判断を要した点: new-worktree.sh 作成後に origin/main が進み（#4409 マージ）、§5-3 の差分比較は origin/main ではなく作業場所の起点 64fedf14e（HEAD）に対して行った

END OF CARD
