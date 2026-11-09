# 実装カード build-on-github 便0 — dockerd のメモリを記録し、計画して入れ直せるようにする

> この文書は何か：build-on-github 便0 の作業指示書です。prod1 の docker の土台（dockerd）のメモリを毎分記録し、膨らんだら知らせ、PO が昼の決まった時間帯に安全に入れ直せる台本を作ります。2026-11-08 夜に dockerd が約 2.0GB まで膨らみ本番が止まったことへの対処です。

- 設計: docs/handoff/build-on-github/design.md §10-1・§12 便0・§23 件3・§24（本便の細部の確定）
- 状態: 便0 の範囲は PO 承認済み（2026-11-04 §23 件3「1」・2026-11-09「3」）。§24 の細部は Opus の技術判断（目的と範囲は変えない）
- 危険便: はい（`scripts/` を含む。ADR-135・ADR-136）。GO は「POの委任に基づくClaude Opus発行」で Opus が出し、マージと反映後の観測も Opus が行う。担当はマージしない
- 担当: 実装 Sonnet（クラウド）／審査・GO・マージ・反映確認 Opus／台本の実行は PO の `!`

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○（まだ無いファイルのパスは「新設の」を付けてバッククォートなしで書く） |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（dockerd の記録・見張り・入れ直しの台本だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/dockerd-memory-maintenance-impl） |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-3） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§11） |
| 11 | 期待値は実物から | ○（行の目印は origin/main 8b627c3f1 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード build-on-github 便0 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 値を書く係（新設の scripts/ops/dockerd_state.py）（§4-1）
2. その試験（新設の scripts/tests/test_dockerd_state.py）と CI の設定（`.github/workflows/deploy-script-test.yml`・`.github/workflows/monitoring-check.yml`）（§4-2・§4-3）
3. 見張り 2 本（`monitoring/prometheus/alert_rules.yml` の末尾に 1 グループ）（§4-4）
4. 見張りの単体試験（`monitoring/prometheus/tests/alert_rules_test.yml` の末尾に追記・冒頭の本数）（§4-5）
5. 手順書（`docs/runbooks/alerts.md` に 2 節・HighMemoryUsage に 1 行・冒頭の本数）（§4-6）
6. 入れ直しの台本（新設の scripts/ops/dockerd-restart-window.sh）（§4-7）
7. GitHub の試験場で動かす試験（新設の tests/sandbox/dockerd-state.sh）（§4-8）

入れない:
- prod1・prod2 への変更（cron の登録・ルールの配置は Opus が §8 で行う）
- `deploy.yml`・compose・製品コード・Alertmanager の設定
- 組み立ての移動（便1 以降）

## 2. 前提の事実（origin/main 8b627c3f1）

- `scripts/ops/container_state.py` が同じ型の係（一時ファイルに書いて置き換え・成功は無言・失敗は標準エラー 1 行と終了コード 1）。本便はこの型に合わせる。
- `/proc/<pid>/status` の `VmRSS`・`VmSwap` は `"148712 kB"` の形（数・空白・`kB`）。`Threads` は数だけ。`Name` は `dockerd`（2026-11-09 prod1 実測）。
- `/run/docker.pid` は root の 644 で、dockerd の起動時に書かれる（2026-11-09 prod1 実測: 更新時刻 = 入れ直しの時刻 16:13）。
- 見張りは今 36 本（`grep -c '^ *- alert:' monitoring/prometheus/alert_rules.yml`）。`monitoring/scripts/check_alert_rules.py` は `OK: Prometheus 36 rules, Loki 6 rules, runbook 42 sections` を出す。
- `monitoring/scripts/check_alert_rules.py` は、全ルールに札（page/auto/ticket）・`runbook_url`（`https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#` + ルール名の小文字）・手順書の同名の `## ` 見出しを求め、ルールに無い `## ` 見出しを許さない。
- 試験場: `.github/workflows/sandbox-test.yml` は `tests/sandbox/<名前>.sh` を `bash` で動かす。

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| 新設の scripts/ops/dockerd_state.py | §4-1 の全文 |
| 新設の scripts/tests/test_dockerd_state.py | §4-2 の全文 |
| `.github/workflows/deploy-script-test.yml` | §4-3（paths に 2 行×2・run の段 1 つ） |
| `.github/workflows/monitoring-check.yml` | §4-3（変更検出の正規表現・試験の 1 行） |
| `monitoring/prometheus/alert_rules.yml` | §4-4（末尾に 1 グループ） |
| `monitoring/prometheus/tests/alert_rules_test.yml` | §4-5（冒頭の本数・末尾に 6 試験） |
| `docs/runbooks/alerts.md` | §4-6（冒頭の本数・HighMemoryUsage に 1 行・末尾に 2 節） |
| 新設の scripts/ops/dockerd-restart-window.sh | §4-7 の全文 |
| 新設の tests/sandbox/dockerd-state.sh | §4-8 の全文 |
| `docs/handoff/build-on-github/card-bin0.md` | §13 の報告欄だけ |

## 4. 完成形

### 4-1 新設の scripts/ops/dockerd_state.py

```python
#!/usr/bin/env python3
"""build-on-github 便0: docker の土台（dockerd）のメモリを node-exporter の textfile に書く。

prod1 の ubuntu の cron で毎分 1 回動く。/run/docker.pid と /proc/<pid>/status を読んで書くだけで、処置はしない。
docker も root も要らない。成功したときは何も出力しない。失敗したときは標準エラーに 1 行書いて
終了コード 1 で終わり、ファイルは前のまま残す（書いた時刻が変わらなくなり、見張り DockerdStateStale が鳴る）。
python3 の標準ライブラリだけを使う。設計: docs/handoff/build-on-github/design.md §24。
"""

import os
import sys
import tempfile
import time

TEXTFILE_DIR = os.environ.get("DOCKERD_STATE_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
PID_FILE = os.environ.get("DOCKERD_STATE_PID_FILE", "/run/docker.pid")
PROC_DIR = os.environ.get("DOCKERD_STATE_PROC_DIR", "/proc")
OUTPUT_NAME = "dockerd_state.prom"


def read_pid(path: str) -> int:
    with open(path) as f:
        text = f.read().strip()
    pid = int(text)
    if pid <= 0:
        raise ValueError(f"bad pid: {text!r}")
    return pid


def parse_status(text: str) -> dict[str, str]:
    """/proc/<pid>/status の「名前:<空白>値」を辞書にする。"""
    out = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def kb_to_bytes(value: str) -> int:
    """'148712 kB' を 152281088 にする。単位が kB でなければ ValueError。"""
    parts = value.split()
    if len(parts) != 2 or parts[1] != "kB":
        raise ValueError(f"unexpected size: {value!r}")
    return int(parts[0]) * 1024


def read_state(pid_file: str, proc_dir: str) -> dict[str, int]:
    pid = read_pid(pid_file)
    with open(os.path.join(proc_dir, str(pid), "status")) as f:
        status = parse_status(f.read())
    if status.get("Name") != "dockerd":
        raise ValueError(f"pid {pid} is not dockerd: {status.get('Name')!r}")
    return {
        "rss_bytes": kb_to_bytes(status["VmRSS"]),
        "vmswap_bytes": kb_to_bytes(status["VmSwap"]),
        "threads": int(status["Threads"]),
        "start_time_seconds": int(os.stat(pid_file).st_mtime),
    }


METRICS = (
    ("rss_bytes", "salesanchor_dockerd_rss_bytes", "Resident memory of dockerd (VmRSS) in bytes."),
    ("vmswap_bytes", "salesanchor_dockerd_vmswap_bytes", "Swapped-out memory of dockerd (VmSwap) in bytes."),
    ("threads", "salesanchor_dockerd_threads", "Number of threads of dockerd."),
    ("start_time_seconds", "salesanchor_dockerd_start_time_seconds", "Unix time when dockerd wrote its pid file (its start)."),
)


def render(state: dict[str, int], now: float) -> str:
    lines = []
    for key, name, help_text in METRICS:
        lines += [f"# HELP {name} {help_text}", f"# TYPE {name} gauge", f"{name} {state[key]}"]
    lines += [
        "# HELP salesanchor_dockerd_state_last_run_timestamp_seconds Unix time of the last successful write.",
        "# TYPE salesanchor_dockerd_state_last_run_timestamp_seconds gauge",
        f"salesanchor_dockerd_state_last_run_timestamp_seconds {int(now)}",
    ]
    return "\n".join(lines) + "\n"


def write_atomic(text: str, textfile_dir: str) -> None:
    """一時ファイル（.prom で終わらない名前）に書いてから置き換える。node-exporter は *.prom だけを読む。"""
    fd, tmp = tempfile.mkstemp(prefix=".dockerd_state.", dir=textfile_dir)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, os.path.join(textfile_dir, OUTPUT_NAME))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    try:
        state = read_state(PID_FILE, PROC_DIR)
        write_atomic(render(state, time.time()), TEXTFILE_DIR)
    except (OSError, ValueError, KeyError) as e:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"{stamp} dockerd_state failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 4-2 新設の scripts/tests/test_dockerd_state.py

```python
#!/usr/bin/env python3
"""scripts/ops/dockerd_state.py の試験（build-on-github 便0）。偽の pid ファイルと /proc を使い、本物は読まない。"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parent.parent / "ops" / "dockerd_state.py"
spec = importlib.util.spec_from_file_location("dockerd_state", MODULE_PATH)
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)

STATUS = "Name:\tdockerd\nState:\tS (sleeping)\nVmRSS:\t  148712 kB\nVmSwap:\t       0 kB\nThreads:\t41\n"


class ParseTest(unittest.TestCase):
    def test_parse_status(self):
        s = ds.parse_status(STATUS)
        self.assertEqual(s["Name"], "dockerd")
        self.assertEqual(s["VmRSS"], "148712 kB")
        self.assertEqual(s["Threads"], "41")

    def test_kb_to_bytes(self):
        self.assertEqual(ds.kb_to_bytes("148712 kB"), 148712 * 1024)

    def test_kb_to_bytes_bad_unit(self):
        with self.assertRaises(ValueError):
            ds.kb_to_bytes("148712 MB")


class MainTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.textfile = os.path.join(root, "textfile")
        self.proc = os.path.join(root, "proc")
        self.pid_file = os.path.join(root, "docker.pid")
        os.makedirs(self.textfile)
        os.makedirs(os.path.join(self.proc, "1234"))
        self.write_status(STATUS)
        with open(self.pid_file, "w") as f:
            f.write("1234\n")
        os.utime(self.pid_file, (1762672380, 1762672380))

    def tearDown(self):
        self._tmp.cleanup()

    def write_status(self, text):
        with open(os.path.join(self.proc, "1234", "status"), "w") as f:
            f.write(text)

    def run_main(self):
        with mock.patch.object(ds, "TEXTFILE_DIR", self.textfile), \
             mock.patch.object(ds, "PID_FILE", self.pid_file), \
             mock.patch.object(ds, "PROC_DIR", self.proc):
            return ds.main()

    def output_path(self):
        return os.path.join(self.textfile, "dockerd_state.prom")

    def test_main_writes_file(self):
        self.assertEqual(self.run_main(), 0)
        with open(self.output_path()) as f:
            lines = f.read().splitlines()
        self.assertIn(f"salesanchor_dockerd_rss_bytes {148712 * 1024}", lines)
        self.assertIn("salesanchor_dockerd_vmswap_bytes 0", lines)
        self.assertIn("salesanchor_dockerd_threads 41", lines)
        self.assertIn("salesanchor_dockerd_start_time_seconds 1762672380", lines)
        self.assertTrue(any(l.startswith("salesanchor_dockerd_state_last_run_timestamp_seconds ") for l in lines))
        self.assertEqual(os.stat(self.output_path()).st_mode & 0o777, 0o644)
        self.assertEqual([n for n in os.listdir(self.textfile) if n.startswith(".dockerd_state.")], [])

    def assert_fails_and_keeps(self):
        with open(self.output_path(), "w") as f:
            f.write("old\n")
        self.assertEqual(self.run_main(), 1)
        with open(self.output_path()) as f:
            self.assertEqual(f.read(), "old\n")
        self.assertEqual([n for n in os.listdir(self.textfile) if n.startswith(".dockerd_state.")], [])

    def test_not_dockerd(self):
        self.write_status(STATUS.replace("dockerd", "bash"))
        self.assert_fails_and_keeps()

    def test_pid_file_missing(self):
        os.unlink(self.pid_file)
        self.assert_fails_and_keeps()

    def test_pid_file_garbage(self):
        with open(self.pid_file, "w") as f:
            f.write("abc\n")
        self.assert_fails_and_keeps()

    def test_vmswap_missing(self):
        self.write_status(STATUS.replace("VmSwap:\t       0 kB\n", ""))
        self.assert_fails_and_keeps()

    def test_process_gone(self):
        with open(self.pid_file, "w") as f:
            f.write("99999\n")
        self.assert_fails_and_keeps()


if __name__ == "__main__":
    unittest.main()
```

### 4-3 CI の設定

`.github/workflows/deploy-script-test.yml`:
- `pull_request.paths` と `push.paths` の両方で、`- 'scripts/tests/test_container_state.py'` の行の直後に次の 2 行を足す（同じ字下げ）:
  ```yaml
      - 'scripts/ops/dockerd_state.py'
      - 'scripts/tests/test_dockerd_state.py'
  ```
- 最後の段 `- name: Run container_state tests`（`run: python3 scripts/tests/test_container_state.py`）の後に足す:
  ```yaml

      - name: Run dockerd_state tests
        run: python3 scripts/tests/test_dockerd_state.py
  ```

`.github/workflows/monitoring-check.yml`:
- 変更検出の `grep -qE` の正規表現で、`scripts/tests/test_container_state\.py` の直後に `|scripts/ops/dockerd_state\.py|scripts/tests/test_dockerd_state\.py` を足す（閉じかっこ `)"` の前）。
- 段「アプリの健康診断の欠け検査と状態書き係の試験」の `python3 scripts/tests/test_container_state.py -v` の次の行に、同じ字下げで `python3 scripts/tests/test_dockerd_state.py -v` を足す。

### 4-4 `monitoring/prometheus/alert_rules.yml`（ファイルの末尾に足す。前のグループとの間に空行 1 つ）

```yaml
  - name: dockerd_state_alerts
    rules:
      # docker の土台（dockerd）のメモリが 1GiB を 30 分超えた（build-on-github 便0・design.md §24-3）
      # 2026-11-09 の停止の前は約 2.0GB、入れ直し後は約 0.15GB。値は prod1 の scripts/ops/dockerd_state.py が毎分 textfile に書く
      - alert: DockerdMemoryHigh
        expr: salesanchor_dockerd_rss_bytes{instance="app-vps"} > 1073741824
        for: 30m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "docker の土台（dockerd）のメモリが 1GiB を超えています"
          description: "prod1 の dockerd のメモリが 30 分続けて 1GiB を超えています。2026-11-09 は約 2.0GB まで膨らみ本番が止まりました。日本時間 14:00〜16:00 に入れ直しの台本を流してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#dockerdmemoryhigh"

      # dockerd の値を書く係が 10 分書いていない。書いた時刻の値が変わらないことで見る（時計のずれで誤って鳴らない）
      - alert: DockerdStateStale
        expr: changes(salesanchor_dockerd_state_last_run_timestamp_seconds{instance="app-vps"}[10m]) == 0 or absent(salesanchor_dockerd_state_last_run_timestamp_seconds{instance="app-vps"})
        for: 5m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "dockerd のメモリを書く係が 10 分以上動いていません"
          description: "prod1 の scripts/ops/dockerd_state.py が 10 分以上 textfile を書いていません。dockerd が膨らんでも DockerdMemoryHigh が鳴りません。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#dockerdstatestale"
```

### 4-5 `monitoring/prometheus/tests/alert_rules_test.yml`

- 4 行目の `# 全 36 本が擬似の系列で鳴ること、tier と runbook_url が付くことを確かめる。` の `36` を、§5-1 の `check_alert_rules.py` の出力の本数（期待 38）に変える。
- ファイルの末尾に足す（前の試験との間に空行 1 つ・`tests:` の下の字下げに合わせる）:

```yaml
  # --- build-on-github 便0: dockerd ---
  - name: DockerdMemoryHighFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_dockerd_rss_bytes{instance="app-vps",job="node-exporter"}'
        values: '1610612736x40'
    alert_rule_test:
      - eval_time: 35m
        alertname: DockerdMemoryHigh
        exp_alerts:
          - exp_labels:
              instance: app-vps
              job: node-exporter
              severity: warning
              tier: ticket
            exp_annotations:
              summary: "docker の土台（dockerd）のメモリが 1GiB を超えています"
              description: "prod1 の dockerd のメモリが 30 分続けて 1GiB を超えています。2026-11-09 は約 2.0GB まで膨らみ本番が止まりました。日本時間 14:00〜16:00 に入れ直しの台本を流してください。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#dockerdmemoryhigh"

  - name: DockerdMemoryHighShort
    interval: 1m
    input_series:
      - series: 'salesanchor_dockerd_rss_bytes{instance="app-vps",job="node-exporter"}'
        values: '1610612736x40'
    alert_rule_test:
      - eval_time: 20m
        alertname: DockerdMemoryHigh
        exp_alerts: []

  - name: DockerdMemoryHighQuiet
    interval: 1m
    input_series:
      - series: 'salesanchor_dockerd_rss_bytes{instance="app-vps",job="node-exporter"}'
        values: '268435456x40'
    alert_rule_test:
      - eval_time: 35m
        alertname: DockerdMemoryHigh
        exp_alerts: []

  - name: DockerdStateStaleFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_dockerd_state_last_run_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '1000+0x20'
    alert_rule_test:
      - eval_time: 16m
        alertname: DockerdStateStale
        exp_alerts:
          - exp_labels:
              instance: app-vps
              job: node-exporter
              severity: warning
              tier: ticket
            exp_annotations:
              summary: "dockerd のメモリを書く係が 10 分以上動いていません"
              description: "prod1 の scripts/ops/dockerd_state.py が 10 分以上 textfile を書いていません。dockerd が膨らんでも DockerdMemoryHigh が鳴りません。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#dockerdstatestale"

  - name: DockerdStateStaleAbsent
    interval: 1m
    input_series:
      - series: 'up{job="node-exporter",instance="app-vps"}'
        values: '1x20'
    alert_rule_test:
      - eval_time: 10m
        alertname: DockerdStateStale
        exp_alerts:
          - exp_labels:
              instance: app-vps
              severity: warning
              tier: ticket
            exp_annotations:
              summary: "dockerd のメモリを書く係が 10 分以上動いていません"
              description: "prod1 の scripts/ops/dockerd_state.py が 10 分以上 textfile を書いていません。dockerd が膨らんでも DockerdMemoryHigh が鳴りません。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#dockerdstatestale"

  - name: DockerdStateFresh
    interval: 1m
    input_series:
      - series: 'salesanchor_dockerd_state_last_run_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '0+60x20'
    alert_rule_test:
      - eval_time: 16m
        alertname: DockerdStateStale
        exp_alerts: []
```

### 4-6 `docs/runbooks/alerts.md`

- 3 行目の `（Prometheus 34 本）` の `34` を、§5-1 の `check_alert_rules.py` の出力の本数（期待 38）に変える。
- `## HighMemoryUsage` の節の `- 最初に見るもの：Grafana のサーバー資源のダッシュボード、`docker stats --no-stream`。` の行を次に置き換える:
  ```markdown
  - 最初に見るもの：Grafana のサーバー資源のダッシュボード、`docker stats --no-stream`。あわせて Prometheus で `salesanchor_dockerd_rss_bytes{instance="app-vps"}`（docker の土台そのもののメモリ。箱ごとの `docker stats` には出ない）。1GiB を超えていれば DockerdMemoryHigh の手順に進む。
  ```
- ファイルの末尾に足す（前の節との間に空行 1 つ）:

```markdown
## DockerdMemoryHigh

- 札：ticket
- 何が起きているか：prod1 の docker の土台（dockerd）のメモリが 1GiB を超えた状態が 30 分続いた。健康なときは約 0.15〜0.3GB。2026-11-08 夜は約 2.0GB まで膨らみ、空きメモリが尽きて本番が止まった（build-on-github design.md §24）。値は prod1 の `scripts/ops/dockerd_state.py` が毎分 textfile に書く。
- 影響：今すぐの影響は無い。放置すると空きメモリが減り、入れ替え（deploy）の組み立てが打ち切られたり、本番が止まったりする。
- 最初に見るもの：Prometheus の `salesanchor_dockerd_rss_bytes{instance="app-vps"}` の 7 日の増え方と、`salesanchor_dockerd_start_time_seconds` （最後に入れ直した時刻）。
- 直し方：日本時間 14:00〜16:00 に、PO が Mac の「ターミナル」で `bash scripts/ops/dockerd-restart-window.sh restart` を流す（live-restore が有効なら箱は止まらない）。live-restore が未設定なら、先に同じ台本の `live-restore` を流す。台本は入れ替えを止めて、終わりに必ず戻す。
- 入れ直しの許可：prod1 の `/etc/sudoers.d/90-sa-docker-restart` が、ubuntu に `/usr/bin/systemctl restart docker` と `/usr/bin/systemctl is-active docker` だけをパスワード無しで許している（2026-11-09 PO が設置）。あるかの確かめは prod1 で `sudo -n -l /usr/bin/systemctl restart docker`（終了コード 0 ならある）。外すときは `ssh -t prod1 'sudo rm /etc/sudoers.d/90-sa-docker-restart'`。
- 止め方：`amtool silence add alertname=DockerdMemoryHigh --duration=PERIOD --comment=REASON`

## DockerdStateStale

- 札：ticket
- 何が起きているか：prod1 の dockerd のメモリを書く係（`scripts/ops/dockerd_state.py`、ubuntu の cron で毎分）が 10 分以上 textfile を書いていない、または値が無い状態が 5 分続いた。この間は dockerd が膨らんでも DockerdMemoryHigh が鳴らない。
- 最初に見るもの：prod1 の `crontab -l` に dockerd_state の行があるか → `/tmp/dockerd-state.log` の最後の行（失敗のときだけ書かれる）→ `/home/ubuntu/node_exporter_textfile/dockerd_state.prom` の時刻。
- 直し方：ログの原因（pid ファイルが読めない・dockerd が動いていない・書けない）を切り分けて Opus に報告する。
- 止め方：`amtool silence add alertname=DockerdStateStale --duration=PERIOD --comment=REASON`
```

### 4-7 新設の scripts/ops/dockerd-restart-window.sh

```bash
#!/bin/bash
# build-on-github 便0（design.md §10-1・§24-4）: docker の土台（dockerd）を計画して入れ直す台本。
# PO が Mac の「ターミナル」で流す。prod1 には ssh prod1 で入る。
#   bash scripts/ops/dockerd-restart-window.sh live-restore … live-restore を入れる（箱は止まらない・管理者パスワードを 1 回聞かれる）
#   bash scripts/ops/dockerd-restart-window.sh restart      … dockerd を入れ直す（live-restore が有効なときだけ）
# どちらも: 日本時間 14:00〜15:44 だけ受け付ける／入れ替え（deploy.yml）が動いていれば止まる／
#           入れ替えを止め、終わりに必ず戻す（途中で止まっても戻す）／前後の値を出す／記録を Mac に残す。
# 戻し方: live-restore は prod1 で sudo rm /etc/docker/daemon.json → sudo systemctl reload docker。
set -euo pipefail

MODE="${1:-}"
REPO=shingo-ops/salesanchor
HOST=prod1
HEALTH_URL=https://api.salesanchor.jp/api/health
LOG_DIR="${DOCKERD_WINDOW_LOG_DIR:-$HOME/CC報告ファイル-keep/dockerd-restart-window}"

case "$MODE" in
  live-restore|restart) ;;
  *) echo "使い方: bash $0 live-restore|restart"; exit 2 ;;
esac

# 時間帯の確かめ（試験のときだけ DOCKERD_WINDOW_NOW_HHMM で時刻を与えられる）
now_hhmm="${DOCKERD_WINDOW_NOW_HHMM:-$(TZ=Asia/Tokyo date +%H%M)}"
case "$now_hhmm" in
  [0-9][0-9][0-9][0-9]) ;;
  *) echo "止めました: 時刻を読めません（$now_hhmm）"; exit 3 ;;
esac
now_num=$((10#$now_hhmm))
if [ "$now_num" -lt 1400 ] || [ "$now_num" -ge 1545 ]; then
  echo "止めました: 日本時間 14:00〜15:44 にだけ始められます（今 ${now_hhmm:0:2}:${now_hhmm:2:2}）"
  exit 3
fi

mkdir -p "$LOG_DIR"
STAMP="$(TZ=Asia/Tokyo date +%Y%m%d-%H%M%S)"
LOG="$LOG_DIR/$MODE-$STAMP.txt"
exec > >(tee -a "$LOG") 2>&1

DISABLED=0
HEALTH_PID=""
restore() {
  rc=$?
  set +e
  if [ -n "$HEALTH_PID" ]; then kill "$HEALTH_PID" 2>/dev/null; fi
  if [ "$DISABLED" = 1 ]; then
    gh workflow enable deploy.yml -R "$REPO"
    state="$(gh api "repos/$REPO/actions/workflows/deploy.yml" --jq .state)"
    echo "入れ替え（deploy.yml）の状態: $state"
    if [ "$state" != active ]; then
      echo "!! 入れ替えが戻っていません。Opus に知らせてください"
      rc=9
    fi
  fi
  echo "記録: $LOG"
  exit "$rc"
}
trap restore EXIT
trap 'exit 130' INT TERM HUP

HEALTH_LOG="$LOG_DIR/health-$STAMP.txt"
start_health() {
  (
    while :; do
      code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$HEALTH_URL" || true)"
      echo "$(date +%s) $code"
      sleep 2
    done
  ) > "$HEALTH_LOG" &
  HEALTH_PID=$!
  sleep 10
}
stop_health() {
  sleep 20
  kill "$HEALTH_PID" 2>/dev/null || true
  HEALTH_PID=""
  awk '$2!="200"{if(s==""){s=$1}; e=$1; n++} $2=="200"{if(s!=""){d=e-s+2; if(d>m){m=d}; s=""}} END{if(s!=""){d=e-s+2; if(d>m){m=d}}; printf "健康確認: %d 回のうち 200 以外 %d 回・最長の途切れ 約 %d 秒（記録 %s）\n", NR, n, m, FILENAME}' "$HEALTH_LOG"
}

busy_runs() {
  gh run list -R "$REPO" --workflow deploy.yml --limit 20 --json status \
    --jq '[.[] | select(.status != "completed")] | length'
}

snapshot() {
  echo "== $1 $(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S') JST"
  ssh "$HOST" 'pid=$(cat /run/docker.pid); grep -E "^(VmRSS|VmSwap|Threads):" "/proc/$pid/status"; echo "LiveRestore=$(docker info --format "{{.LiveRestoreEnabled}}")"; echo "running=$(docker ps -q | wc -l | tr -d " ")"; free -m'
}

echo "== 台本 $MODE を始めます"
busy="$(busy_runs)"
if [ "$busy" != 0 ]; then
  echo "止めました: 入れ替えが $busy 件動いています。終わってから流し直してください"
  exit 4
fi
gh workflow disable deploy.yml -R "$REPO"
DISABLED=1
busy="$(busy_runs)"
if [ "$busy" != 0 ]; then
  echo "止めました: 止める間に入れ替えが $busy 件始まりました"
  exit 4
fi
echo "入れ替えを止めました（終わりに戻します）"

snapshot "前"

if [ "$MODE" = live-restore ]; then
  before_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ')"
  start_health
  ssh -t "$HOST" 'set -e
if test -e /etc/docker/daemon.json; then echo "止めました: /etc/docker/daemon.json が既にあります（中身を変えないため）"; exit 5; fi
tmp=$(mktemp)
printf "%s\n" "{\"live-restore\": true}" > "$tmp"
sudo dockerd --validate --config-file "$tmp"
sudo install -m 644 -o root -g root "$tmp" /etc/docker/daemon.json
rm -f "$tmp"
sudo systemctl reload docker
v=false
for i in $(seq 1 15); do
  v=$(docker info --format "{{.LiveRestoreEnabled}}")
  if test "$v" = true; then break; fi
  sleep 2
done
echo "LiveRestore=$v"
test "$v" = true'
  stop_health
  after_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ')"
  echo "動いている箱: 前 $before_running → 後 $after_running"
else
  lr="$(ssh "$HOST" 'docker info --format "{{.LiveRestoreEnabled}}"')"
  if [ "$lr" != true ]; then
    echo "止めました: live-restore が有効ではありません。先に live-restore を流してください"
    exit 6
  fi
  if ! ssh "$HOST" 'sudo -n -l /usr/bin/systemctl restart docker >/dev/null'; then
    echo "止めました: 再起動の許可（/etc/sudoers.d/90-sa-docker-restart）がありません"
    exit 7
  fi
  before_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ')"
  start_health
  ssh "$HOST" 'sudo -n /usr/bin/systemctl restart docker && sudo -n /usr/bin/systemctl is-active docker'
  after_running=""
  for i in $(seq 1 30); do
    after_running="$(ssh "$HOST" 'docker ps -q | wc -l' | tr -d ' ' || true)"
    if [ "$after_running" = "$before_running" ]; then break; fi
    sleep 2
  done
  stop_health
  echo "動いている箱: 前 $before_running → 後 $after_running"
fi

snapshot "後"
echo "== 台本 $MODE を終えました"
```

### 4-8 新設の tests/sandbox/dockerd-state.sh

```bash
#!/bin/bash
# build-on-github 便0: dockerd の値を書く係（scripts/ops/dockerd_state.py）と見張り 2 本・台本の入口を GitHub の試験場で確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=dockerd-state
# secrets・本番には触れない。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
PROM=prom/prometheus:v3.11.3

echo "== 1. 係の試験"
python3 --version
python3 scripts/tests/test_dockerd_state.py

echo "== 2. 見張りの検査"
python3 monitoring/scripts/check_alert_rules.py
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" check rules /p/alert_rules.yml
docker run --rm -v "$PWD/monitoring/prometheus:/p:ro" --entrypoint promtool "$PROM" test rules /p/tests/alert_rules_test.yml

echo "== 3. 本物の dockerd で書く"
ls -l /run/docker.pid
pid="$(cat /run/docker.pid)"
grep -E '^(Name|VmRSS|VmSwap|Threads):' "/proc/$pid/status"
TF="$OUT/textfile"
mkdir -p "$TF"
time DOCKERD_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/dockerd_state.py
cat "$TF/dockerd_state.prom"
val() { grep -E "^$1 " "$TF/dockerd_state.prom" | awk '{print $2}'; }
rss="$(val salesanchor_dockerd_rss_bytes)"
thr="$(val salesanchor_dockerd_threads)"
start="$(val salesanchor_dockerd_start_time_seconds)"
[ "$rss" -gt 0 ] || { echo "NG: rss"; exit 1; }
[ "$thr" -gt 0 ] || { echo "NG: threads"; exit 1; }
[ "$start" = "$(stat -c %Y /run/docker.pid)" ] || { echo "NG: start time"; exit 1; }
for m in salesanchor_dockerd_rss_bytes salesanchor_dockerd_vmswap_bytes salesanchor_dockerd_threads salesanchor_dockerd_start_time_seconds salesanchor_dockerd_state_last_run_timestamp_seconds; do
  [ "$(grep -c "^$m " "$TF/dockerd_state.prom")" = 1 ] || { echo "NG: line $m"; exit 1; }
done
[ "$(stat -c %a "$TF/dockerd_state.prom")" = 644 ] || { echo "NG: mode"; exit 1; }
docker run --rm -i --entrypoint promtool "$PROM" check metrics < "$TF/dockerd_state.prom"

echo "== 4. 失敗の試験（pid ファイルが無い・dockerd でない → rc=1・ファイルは変わらない・一時ファイルが残らない）"
before="$(sha256sum "$TF/dockerd_state.prom")"
set +e
DOCKERD_STATE_PID_FILE=/nonexistent.pid DOCKERD_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/dockerd_state.py
rc1=$?
echo "$$" > "$OUT/not-dockerd.pid"
DOCKERD_STATE_PID_FILE="$OUT/not-dockerd.pid" DOCKERD_STATE_TEXTFILE_DIR="$TF" python3 scripts/ops/dockerd_state.py
rc2=$?
set -e
echo "rc1=$rc1 rc2=$rc2"
[ "$rc1" -eq 1 ] && [ "$rc2" -eq 1 ] || { echo "NG: rc"; exit 1; }
[ "$(sha256sum "$TF/dockerd_state.prom")" = "$before" ] || { echo "NG: file changed"; exit 1; }
ls -a "$TF"
if ls -A "$TF" | grep -q '^\.dockerd_state\.'; then echo "NG: temp left"; exit 1; fi

echo "== 5. 台本の入口（外の操作の前に止まること。gh・ssh は呼ばれない）"
bash -n scripts/ops/dockerd-restart-window.sh
set +e
bash scripts/ops/dockerd-restart-window.sh bogus; r1=$?
DOCKERD_WINDOW_NOW_HHMM=0900 bash scripts/ops/dockerd-restart-window.sh restart; r2=$?
DOCKERD_WINDOW_NOW_HHMM=1545 bash scripts/ops/dockerd-restart-window.sh live-restore; r3=$?
DOCKERD_WINDOW_NOW_HHMM=1359 bash scripts/ops/dockerd-restart-window.sh restart; r4=$?
DOCKERD_WINDOW_NOW_HHMM=ab12 bash scripts/ops/dockerd-restart-window.sh restart; r5=$?
set -e
echo "r1=$r1 r2=$r2 r3=$r3 r4=$r4 r5=$r5"
[ "$r1" -eq 2 ] && [ "$r2" -eq 3 ] && [ "$r3" -eq 3 ] && [ "$r4" -eq 3 ] && [ "$r5" -eq 3 ] || { echo "NG: entry"; exit 1; }
if command -v shellcheck >/dev/null; then shellcheck -S warning scripts/ops/dockerd-restart-window.sh tests/sandbox/dockerd-state.sh; else echo "shellcheck なし（スキップ）"; fi
echo "ALL OK"
```

## 5. 確かめ（担当が行う）

### 5-1 手元の試験（作業場所で）
1. `python3 scripts/tests/test_dockerd_state.py` → 期待: `Ran 9 tests` と `OK`
2. `python3 monitoring/scripts/check_alert_rules.py` → 期待: `OK: Prometheus 38 rules, Loki 6 rules, runbook 44 sections`。本数が違えば、その本数を §4-5・§4-6 の本数に使い、報告の「判断を要した点」に書く
3. `bash -n scripts/ops/dockerd-restart-window.sh && bash -n tests/sandbox/dockerd-state.sh && echo SYNTAX_OK` → 期待: `SYNTAX_OK`
4. `python3 -c "import yaml; [yaml.safe_load(open(p)) for p in ('monitoring/prometheus/alert_rules.yml','monitoring/prometheus/tests/alert_rules_test.yml','.github/workflows/deploy-script-test.yml','.github/workflows/monitoring-check.yml')]; print('YAML_OK')"` → 期待: `YAML_OK`

### 5-2 GitHub の試験場（push の後）
1. `gh workflow run sandbox-test.yml --ref release/dockerd-memory-maintenance-impl -f test=dockerd-state`
2. 10 秒置いて `gh run list --workflow sandbox-test.yml --branch release/dockerd-memory-maintenance-impl --limit 1 --json databaseId,status,conclusion,url` を出す。終わるのを待たない（待ちは Opus が行う）。run の URL を報告に書く

### 5-3 触ったファイルの確かめ
1. `git diff --name-only origin/main...HEAD` → 期待: §3 の 10 ファイルと、設計の 2 ファイル（`docs/handoff/build-on-github/design.md`・`docs/handoff/build-on-github/card-bin0.md`。設計ブランチから取り込んだもの）だけ
2. `git diff origin/main...HEAD --stat` を出す
3. 消した行の確かめ: `git diff origin/main...HEAD -- monitoring/prometheus/tests/alert_rules_test.yml docs/runbooks/alerts.md | grep -E '^-[^-]'` → 期待: 本数の旧行 2 行と HighMemoryUsage の「最初に見るもの」の旧行 1 行の計 3 行だけ

## 6. 止まる条件

- 本番（prod1・prod2）・secrets・main へのマージに触れる操作が必要になったとき（このカードでは不要）
- §5-1 の試験が通らず、§4 の完成形の通りに書いても直らないとき（直し方を推測で変えず、出力を貼って BLOCKED:）

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 係の試験 9 つが pass | §5-1・CI（deploy-script-test） |
| 見張り 2 本が検査を通り、単体試験（既存を含め全部）が pass | §5-1・試験場・CI（monitoring-check） |
| 本物の dockerd で値が書け、失敗のときはファイルを変えない・台本の入口が外の操作の前に止まる | 試験場の記録の `ALL OK` |
| 触ったファイルが §3 と設計の 2 つだけ | §5-3 |
| 本番の受け入れ基準（K0-3〜K0-6） | §8（Opus と PO） |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査役（reviewer・opus）の審査、CI が緑であることを確かめ、危険 PR の GO 手順（ADR-136）で「POの委任に基づくClaude Opus発行」の GO を PR に記録してマージする。
2. deploy.yml の run の成功を確かめ、prod1 に `scripts/ops/dockerd_state.py` が届いたことを確かめる。
3. prod1 の crontab に 1 行足す（手順: ①`crontab -l > /home/ubuntu/crontab.bak-dockerd-state` で控え ②`env -i PATH=/usr/bin:/bin /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/dockerd_state.py; echo rc=$?` で cron と同じ条件で 1 回試す（rc=0 でなければ登録しない）③`* * * * * /usr/bin/python3 /home/ubuntu/salesanchor/scripts/ops/dockerd_state.py >> /tmp/dockerd-state.log 2>&1` を足す（同じ行があれば足さない）④`crontab -l` と `dockerd_state.prom` の中身を出す）。鍵の都合で Opus が入れないときは PO の `!` の台本を用意する。
4. マージと同じ日に、prod2 の `/opt/salesanchor-monitoring/monitoring/prometheus/alert_rules.yml` を main の版にする（docs/handoff/ai-ops-247/card-stage1-bin7.md §8 の型: 控え→本番が 1 つ前の main と同じかの確かめ→一時ディレクトリへ送る→同じ版の promtool で `check rules`（38 本）→`install -m`→sha256 の一致→`POST /-/reload`→monitoring-config-drift の手動実行で `drift=0`）。
5. 登録の 5 分後に K0-3・K0-4 を Prometheus に問い合わせる（`salesanchor_dockerd_rss_bytes{instance="app-vps"}`・`time() - salesanchor_dockerd_state_last_run_timestamp_seconds{instance="app-vps"}`・`/api/v1/rules` の 2 本の health・`ALERTS{alertname=~"Dockerd.*"}`）。
6. 生出力は /tmp/CC報告ファイル/dockerd-bin0/deploy/ に置く。
7. PO へ「日本時間 14:00〜15:44 に `bash scripts/ops/dockerd-restart-window.sh live-restore` を `!` で流す」案内を出す（K0-5）。
8. PO が流した後、Opus が `gh api repos/shingo-ops/salesanchor/actions/workflows/deploy.yml --jq .state` で `active` に戻っていることを確かめる（戻っていなければ `gh workflow enable deploy.yml` を流して PO に伝える）。あわせて台本が出した健康確認の行（200 以外の回数・最長の途切れ）と「動いている箱 前→後」を受け取り、K0-5 を判定する。

## 9. 弊害と戻し方

設計 §24-6 のとおり。

## 10. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/dockerd-memory-maintenance-impl --claude`（origin/main 起点）。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめ、以後はその作業場所に `cd` してから行う
2. `git checkout origin/release/dockerd-memory-maintenance -- docs/handoff/build-on-github/design.md docs/handoff/build-on-github/card-bin0.md .claude-pipeline/active-work.d/release-dockerd-memory-maintenance.md` → 期待: 3 ファイルが入る。`git status --short` で 3 件を確かめる（枝の取り込みは使わない）
3. §4 のとおりに書く（Write/Edit ツール）。§5-1 を通す
4. commit（`--no-verify` は使わない）→ `git log -1 --oneline`
5. `git push -u origin release/dockerd-memory-maintenance-impl` → `git log origin/release/dockerd-memory-maintenance-impl -1 --oneline`
6. §5-2・§5-3

## 11. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1〜5-3 の出力（長いものは要点の行）・試験場の run の URL・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 12. 委任の定型

- sleep は §5-2 の 10 秒にだけ使ってよい。CI・試験場・デプロイは待たない
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）。rm は使わない
- PR は作らない。main にマージしない。本番に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

- （未記入）

END OF CARD
