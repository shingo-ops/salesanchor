# 実装カード 段階3 便H — deploy の migration の失敗を見張りに載せる

> この文書は何か：AI保守運用24時間化 段階3 便H の作業指示書です。今は本番への反映（deploy）の途中で DB の入れ替え（migration）が失敗しても、GitHub の画面が赤くなるだけで、見張り（アラート）は鳴りません。この便では、migration の手順が終わるたびに、その結果（成功・失敗）の時刻を prod1 の textfile に書き、「失敗の時刻が成功の時刻より新しい」間は見張り DeployMigrationFailed（札 page）が鳴るようにします。次の deploy で migration が成功すると自然に止みます。

- 設計: docs/handoff/ai-ops-247/stage3-design.md §2 便H・§6（:161）・§8（:182）
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階3
- 対象ADR: ADR-1012（本テーマ）
- 状態: 便の分け方は PO 承認 y（2026-10-16）。§2-2 の決定は Opus の技術判断（設計の目的・範囲を変えない）。実装の開始には PO の実装承認が要る
- 危険便: はい（`.github/workflows/deploy.yml` と `scripts/` を含む。ADR-135・ADR-136）。GO は「POの委任に基づくClaude Opus発行」で Opus が出し、マージと反映後の観測も Opus が行う。担当はマージしない
- 担当: 実装 Sonnet（クラウド）／審査・GO・マージ・反映確認 Opus。prod1 の crontab の変更は無い（PO の `!` は要らない）

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○（まだ無いファイルのパスは「新設の」を付けてバッククォートなしで書く） |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（migration の結果の時刻を書き、失敗で見張りが鳴ることだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-3 は数が違えば原文を貼る） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 334c7ec45 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番（prod1・prod2）には触らない | ○（§8 は Opus） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階3 便H の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 結果を書く係（新設の scripts/ops/deploy_migration_mark.py）（§4-1）
2. deploy.yml に、migration の手順の後で係を呼ぶ手順を 1 つ足す（`.github/workflows/deploy.yml`）（§4-2）
3. 係と deploy.yml の手順の試験（新設の scripts/tests/test_deploy_migration_mark.py）と、CI で走らせる設定（`.github/workflows/deploy-script-test.yml` に追記）（§4-3・§4-4）
4. 見張り DeployMigrationFailed（`monitoring/prometheus/alert_rules.yml`）（§4-5）
5. 見張りの単体試験（`monitoring/prometheus/tests/alert_rules_test.yml`）（§4-6）
6. 手順書（`docs/runbooks/alerts.md`）（§4-7）

入れない:
- migration の手順（`id: migrate`）そのものの変更（中身・条件・`set -e` での失敗の仕方は今のまま。設計 §2 便H）
- ロールバックの条件の変更（設計 §2 便H。変えるなら別カードの危険 PR）
- Alertmanager の設定・応急処置係（便G）の変更
- 本番での migration の失敗を起こす試し（設計 §2 便H「本番では失敗を起こさない」）

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 334c7ec45・生出力 /tmp/CC報告ファイル/ai-ops-stage3/bin-h-card/）

| # | 事実 | 出典 |
|---|---|---|
| F1 | migration の手順は `id: migrate`、条件は `success() && steps.gate.outputs.migrations == 'true'`。appleboy/ssh-action@v1 で prod1 に入り、`set -e` のもと `cd /home/ubuntu/salesanchor` → 取り残しの片付け → `bash scripts/run_all_migrations.sh`。打ち切りは 10 分 | `.github/workflows/deploy.yml:873-894` |
| F2 | その次は「Clean up DB orphans after failure」。条件は `always()` かつ backup か migrate の outcome が failure か cancelled（手で止めた回も含む）。その次が「Post-deploy smoke tests (SA-19)」で、条件は `success() && ...` | `.github/workflows/deploy.yml:896-913` |
| F3 | deploy は migration より前に prod1 で `git reset --hard origin/main` するので、scripts/ の新しいファイルは migration の時点で prod1 に届いている | `.github/workflows/deploy.yml:320` |
| F4 | migration を走らせるかの判定の対象に `scripts/**` と `.github/workflows/deploy.yml` が入っている。この便の最初の deploy でも migration は走る | `.github/workflows/deploy.yml:50-56`（生出力 recon4 の mig-filter） |
| F5 | 手順の失敗を許す前例：`continue-on-error: true` を付けた appleboy の手順が既にある（nginx の作り直しなど） | `.github/workflows/deploy.yml:582-590,733-737,768-773` |
| F6 | GitHub Actions の `steps.<id>.outcome` は success・failure・cancelled・skipped のどれかで、continue-on-error を当てる前の結果。`always()` は取り消しの回でも真で、取り消しの回でも条件が真の手順は動く（Context7 で docs.github.com を確かめた） | Context7（GitHub Actions の文書） |
| F7 | prod1 の node-exporter は `/home/ubuntu/node_exporter_textfile` を読む。deploy の前の控え（backup.sh）は、deploy の ssh の中から同じ場所に mktemp→chmod 644→mv で書いている（書けないときはログに書くだけで止めない） | `docker-compose.exporters.yml:11`・`scripts/backup.sh:104-122`・`.github/workflows/deploy.yml:246-270` |
| F8 | 書く係の型：一時ファイル→`os.replace`、mode 644、標準ライブラリだけ、置き場は環境変数で変えられる | `scripts/ops/container_state.py:19,97-104` |
| F9 | prod1 の python3 は `/usr/bin/python3`（cron の行で使っている。設計 §7 V2 は○） | `docs/handoff/ai-ops-247/card-stage3-bin-e.md:496`・`docs/handoff/ai-ops-247/stage3-design.md:168` |
| F10 | 見張りは Prometheus 38 本。本数は手順書の 3 行目と単体試験の 4 行目に書いてあり、検査の出力は `OK: Prometheus 38 rules, Loki 6 rules, runbook 44 sections`。最後のグループは `dockerd_state_alerts` | `docs/runbooks/alerts.md:3`・`monitoring/prometheus/tests/alert_rules_test.yml:4`・`monitoring/prometheus/alert_rules.yml:466` |
| F11 | deploy-script-test.yml は deploy.yml の変更で走り、係の試験を `python3 scripts/tests/test_container_state.py` などの形で 1 本ずつ順に流している | `.github/workflows/deploy-script-test.yml:9-31,47-54` |
| F12 | 便G（応急処置係）のカードも同じ見張り・試験・手順書のファイルに書き足す。どちらが先に main に入っても、もう片方は §6 の分岐で合わせる | 開いている便G のカードの PR（release/ai-ops-stage3-bin-g-card の docs/handoff/ai-ops-247/card-stage3-bin-g.md §3。origin/main 334c7ec45 にはまだ無い） |
| F13 | 2 つの値は同じ node-exporter（job node-exporter・instance app-vps）から取るので、付く印（ラベル）は同じ。片側 1 本ずつの比較に `on(...)` を付けると、結果の印が `on` に書いた印だけに削られる（Prometheus v3.11.3 の promql/engine.go:3138-3140。CI の promtool は prom/prometheus:v3.11.3） | `monitoring/prometheus/prometheus.yml:25,32`・`.github/workflows/monitoring-check.yml:77`・審査役の報告（2026-11-20） |

### 2-2. 決めたこと（Opus）

- E1 書く場所：設計 §2 便H は「migration の手順の中で書く」と書いたが、migration の手順の後に別の手順を 1 つ足して書く。理由：①migration の手順が打ち切り（10 分）や取り消しで終わった回も書ける（手順の中だと、その回は書く行まで届かない）②migration の手順そのものを変えない（F1 の中身・`set -e` の失敗の仕方が今のまま）。目的（成功と失敗の時刻を prod1 の textfile に書く）は変えない
- E2 足す手順の位置：「Clean up DB orphans after failure」の後、「Post-deploy smoke tests (SA-19)」の前。片付けを先にする（失敗の回に DB の取り残しを片付けるのを数秒でも遅らせない）
- E3 足す手順の条件：`always()` かつ migrate の outcome が success・failure・cancelled のどれか。migration の手順を飛ばした回（skipped）は何も書かない。`continue-on-error: true` と `command_timeout: 2m` を付け、書けなくても deploy の成否は変えない（F5 の前例）
- E4 cancelled は失敗として書く（DB が途中の形の可能性がある点は失敗と同じ）
- E5 ファイルは成功用と失敗用の 2 つに分け、書く側だけを入れ替える。もう片方は前の値のまま残す（比べるのは見張りの式）
- E6 見張りの式：失敗の値が成功の値より新しい、または成功の値が無く失敗の値だけがある。for 0m・札 page・severity critical。値が無いことでは鳴らさない（deploy は不定期なので「長く書かれていない」は異常ではない）
- E7 outcome の値は E3 の条件で 3 つに限られるので、`${{ steps.migrate.outcome }}` を script にそのまま書いてよい（外から入る文字は無い）
- E8 古い checkout（係のファイルが無い）のときは、片付けの手順と同じ形で「skipped」と出して終える
- E9 見張りの式には `on(instance)` を付けない（F13）。付けると、成功と失敗の両方がある回は印が instance だけになり、失敗だけの回は instance と job が残る。印が回によって違うと、Alertmanager のまとめ方（alertname・job・instance）で別の見張りとして扱われてしまう

## 3. 触るファイル（これ以外は触らない）

| ファイル | 中身 |
|---|---|
| 新設の scripts/ops/deploy_migration_mark.py | §4-1 の全体 |
| `.github/workflows/deploy.yml` | §4-2 の手順を 1 つ足す（足すだけ） |
| 新設の scripts/tests/test_deploy_migration_mark.py | §4-3 の試験 |
| `.github/workflows/deploy-script-test.yml` | §4-4 の追記（足すだけ） |
| `monitoring/prometheus/alert_rules.yml` | §4-5（末尾に足すだけ） |
| `monitoring/prometheus/tests/alert_rules_test.yml` | §4-6 |
| `docs/runbooks/alerts.md` | §4-7 |
| このカード | §13 の報告欄だけ |

## 4. 作り方

### 4-1. 新設の scripts/ops/deploy_migration_mark.py（ファイル全体）

```python
#!/usr/bin/env python3
"""ADR-1012 段階3 便H: deploy の migration の結果の時刻を node-exporter の textfile に書く。

deploy.yml の「Record migration result」の手順が prod1 に ssh して 1 回だけ呼ぶ。
引数は migration の手順の結果（success・failure・cancelled のどれか）。
success は成功の時刻を、failure と cancelled は失敗の時刻を、それぞれ別のファイルに書く。
もう片方のファイルには触らない（見張り DeployMigrationFailed が 2 つを比べる）。
書けたときは標準出力に 1 行書いて終了コード 0。書けないときは標準エラーに 1 行書いて終了コード 1、
引数が違うときは終了コード 2 で終わる。python3 の標準ライブラリだけを使う。
"""

import os
import sys
import tempfile
import time

TEXTFILE_DIR = os.environ.get("DEPLOY_MIGRATION_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
TARGETS = {
    "success": ("deploy_migration_success.prom", "salesanchor_deploy_migration_last_success_timestamp_seconds"),
    "failure": ("deploy_migration_failure.prom", "salesanchor_deploy_migration_last_failure_timestamp_seconds"),
}
OUTCOME_TO_KIND = {"success": "success", "failure": "failure", "cancelled": "failure"}
TMP_PREFIX = ".deploy_migration."


def render(metric: str, kind: str, now: float) -> str:
    return (
        f"# HELP {metric} Unix time of the last deploy migration {kind} (ADR-1012 stage3 bin H)\n"
        f"# TYPE {metric} gauge\n"
        f"{metric} {int(now)}\n"
    )


def write_atomic(name: str, body: str) -> str:
    fd, tmp = tempfile.mkstemp(prefix=TMP_PREFIX, dir=TEXTFILE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(tmp, 0o644)
        path = os.path.join(TEXTFILE_DIR, name)
        os.replace(tmp, path)
        return path
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in OUTCOME_TO_KIND:
        print("deploy_migration_mark: usage: deploy_migration_mark.py success|failure|cancelled", file=sys.stderr)
        return 2
    kind = OUTCOME_TO_KIND[argv[1]]
    name, metric = TARGETS[kind]
    try:
        path = write_atomic(name, render(metric, kind, time.time()))
    except OSError as e:
        print(f"deploy_migration_mark: write failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"deploy_migration_mark: wrote {kind} ({argv[1]}) to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

### 4-2. `.github/workflows/deploy.yml`

「Clean up DB orphans after failure」の手順の最後の行（`if [ -f scripts/deploy-db-orphan-cleanup.sh ]; then ...; fi`、origin/main 334c7ec45 で 909 行目）の次の空行の後、`      # SA-19: Post-deploy smoke tests (SA-18 Phase2)` の行の前に、次の 15 行と空行 1 つを足す。ほかの行は変えない（足すだけ）。

```yaml
      # ADR-1012 段階3 便H: migration の手順の結果（成功・失敗・取り消し）の時刻を prod1 の textfile に書く。
      # 見張り DeployMigrationFailed が「失敗の時刻が成功の時刻より新しい」間鳴る。migration を飛ばした回（skipped）は書かない。
      # 書けなくても deploy の成否は変えない（continue-on-error）。outcome は条件で 3 つに限られる。
      - name: Record migration result (ADR-1012 段階3 便H)
        if: ${{ always() && (steps.migrate.outcome == 'success' || steps.migrate.outcome == 'failure' || steps.migrate.outcome == 'cancelled') }}
        continue-on-error: true
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          command_timeout: 2m
          script: |
            cd /home/ubuntu/salesanchor
            if [ -f scripts/ops/deploy_migration_mark.py ]; then /usr/bin/python3 scripts/ops/deploy_migration_mark.py ${{ steps.migrate.outcome }}; else echo ">>> [mark] skipped: script not present (old checkout)"; fi
```

（上の 15 行が手順本体。そのあとに空行を 1 つ置いて、元の `      # SA-19: ...` の行に続ける）

### 4-3. 新設の scripts/tests/test_deploy_migration_mark.py

`scripts/tests/test_container_state.py` と同じく `unittest` で書き、最後に `if __name__ == "__main__": unittest.main()` を置く（pytest は使わない）。読み込みは `importlib.util.spec_from_file_location` で `scripts/ops/deploy_migration_mark.py` をこのファイルからの相対パスで読む。書き先は `tempfile.TemporaryDirectory()` にし、モジュールの `TEXTFILE_DIR` を `unittest.mock.patch.object` で差し替える。時刻は `time.time` を差し替えて `1700000000.7` にする。標準出力と標準エラーは `contextlib.redirect_stdout`・`redirect_stderr` で受ける。次の 10 件を書く（名前は `test_` ＋番号＋英小文字の説明。例 `test_01_success_writes_success_file`）:

| # | 条件 | 確かめること |
|---|---|---|
| 1 | `main(["x", "success"])` | 戻り値 0・`deploy_migration_success.prom` の中身が `# HELP` の行・`# TYPE salesanchor_deploy_migration_last_success_timestamp_seconds gauge`・`salesanchor_deploy_migration_last_success_timestamp_seconds 1700000000` の 3 行・`deploy_migration_failure.prom` が無い・標準出力が 1 行 |
| 2 | `main(["x", "failure"])` | 戻り値 0・`deploy_migration_failure.prom` に `salesanchor_deploy_migration_last_failure_timestamp_seconds 1700000000`・成功のファイルが無い |
| 3 | `main(["x", "cancelled"])` | 2 と同じく失敗のファイルに書く |
| 4 | 先に成功のファイルを書いた後に `failure` | 成功のファイルの中身が 1 バイトも変わらない |
| 5 | 引数が `skipped`・`""`・`SUCCESS`・無し・2 つ | 戻り値 2・置き場にファイルが 1 つも無い・標準エラーが 1 行 |
| 6 | `TEXTFILE_DIR` が無いディレクトリ | 戻り値 1・例外を投げない・標準エラーが 1 行で `deploy_migration_mark: write failed:` で始まる |
| 7 | `success` の後 | 成功のファイルの mode が `0o644`・置き場に `.deploy_migration.` で始まるファイルが残らない |
| 8 | `os.replace` を `OSError` で差し替えて `failure` | 戻り値 1・置き場に `.deploy_migration.` で始まるファイルが残らない |
| 9 | deploy.yml の文字を読む（このファイルから `../../.github/workflows/deploy.yml`。yaml の部品は使わず行で読む） | `- name: Record migration result (ADR-1012 段階3 便H)` が 1 回だけ・その行が `id: migrate` の行と `- name: Clean up DB orphans after failure` の行より後で、`- name: Post-deploy smoke tests (SA-19)` の行より前 |
| 10 | 9 の手順の行から次の `- name:` の行までを読む | `always()`・`steps.migrate.outcome == 'success'`・`steps.migrate.outcome == 'failure'`・`steps.migrate.outcome == 'cancelled'`・`continue-on-error: true`・`command_timeout: 2m`・`scripts/ops/deploy_migration_mark.py ${{ steps.migrate.outcome }}` の 7 つの文字が全部ある・`skipped` を条件に含まない（`if:` の行に `skipped` が無い） |

### 4-4. CI の追記

`.github/workflows/deploy-script-test.yml`：2 か所の paths の `'scripts/tests/test_dockerd_state.py'` の次の行（origin/main で 17 行目と 30 行目の次）に、同じ字下げで次の 2 行を足す。

```yaml
      - 'scripts/ops/deploy_migration_mark.py'
      - 'scripts/tests/test_deploy_migration_mark.py'
```

同じファイルの `run: python3 scripts/tests/test_dockerd_state.py`（54 行目）の次に空行を 1 つ置いて、次の手順を足す。

```yaml
      - name: Run deploy_migration_mark tests
        run: python3 scripts/tests/test_deploy_migration_mark.py
```

（`.github/workflows/monitoring-check.yml` は変えない。見張り・手順書の変更で既に走る）

### 4-5. `monitoring/prometheus/alert_rules.yml`

ファイルの末尾（最後のグループの後。origin/main では `dockerd_state_alerts`）に、空行を 1 つ置いて次のグループを足す。ほかの行は変えない。

```yaml
  - name: deploy_migration_alerts
    rules:
      # deploy の migration が失敗・取り消しで終わった（ADR-1012 段階3 便H）。deploy.yml の「Record migration result」が prod1 の textfile に書く。
      # 失敗の時刻が成功の時刻より新しい間、または成功の値がまだ無く失敗の値だけある間鳴る。次の deploy で migration が成功すると自然に止む
      - alert: DeployMigrationFailed
        expr: salesanchor_deploy_migration_last_failure_timestamp_seconds{instance="app-vps"} > salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps"} or (salesanchor_deploy_migration_last_failure_timestamp_seconds{instance="app-vps"} unless salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps"})
        for: 0m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "本番への反映で DB の入れ替え（migration）が失敗しました"
          description: "直近の deploy で migration の手順が失敗または取り消しで終わりました。DB が途中の形のままの可能性があります。次の deploy で migration が成功するまで鳴り続けます。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#deploymigrationfailed"
```

### 4-6. `monitoring/prometheus/tests/alert_rules_test.yml`

4 行目の本数を 1 つ増やす（origin/main では `# 全 38 本が…` → `# 全 39 本が…`。ほかの文字は変えない）。ファイルの末尾に、空行を 1 つ置いて次の 4 件を足す。

```yaml
  - name: DeployMigrationFailedFiring
    interval: 1m
    input_series:
      - series: 'salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '1000x10'
      - series: 'salesanchor_deploy_migration_last_failure_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '2000x10'
    alert_rule_test:
      - eval_time: 1m
        alertname: DeployMigrationFailed
        exp_alerts:
          - exp_labels:
              instance: app-vps
              job: node-exporter
              severity: critical
              tier: page
            exp_annotations:
              summary: "本番への反映で DB の入れ替え（migration）が失敗しました"
              description: "直近の deploy で migration の手順が失敗または取り消しで終わりました。DB が途中の形のままの可能性があります。次の deploy で migration が成功するまで鳴り続けます。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#deploymigrationfailed"

  - name: DeployMigrationFailedOnlyFailure
    interval: 1m
    input_series:
      - series: 'salesanchor_deploy_migration_last_failure_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '2000x10'
    alert_rule_test:
      - eval_time: 1m
        alertname: DeployMigrationFailed
        exp_alerts:
          - exp_labels:
              instance: app-vps
              job: node-exporter
              severity: critical
              tier: page
            exp_annotations:
              summary: "本番への反映で DB の入れ替え（migration）が失敗しました"
              description: "直近の deploy で migration の手順が失敗または取り消しで終わりました。DB が途中の形のままの可能性があります。次の deploy で migration が成功するまで鳴り続けます。"
              runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#deploymigrationfailed"

  - name: DeployMigrationRecovered
    interval: 1m
    input_series:
      - series: 'salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '3000x10'
      - series: 'salesanchor_deploy_migration_last_failure_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '2000x10'
    alert_rule_test:
      - eval_time: 1m
        alertname: DeployMigrationFailed
        exp_alerts: []

  - name: DeployMigrationOnlySuccess
    interval: 1m
    input_series:
      - series: 'salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps",job="node-exporter"}'
        values: '3000x10'
    alert_rule_test:
      - eval_time: 1m
        alertname: DeployMigrationFailed
        exp_alerts: []
```

### 4-7. `docs/runbooks/alerts.md`

3 行目の本数を 1 つ増やす（origin/main では `（Prometheus 38 本）` → `（Prometheus 39 本）`。ほかの文字は変えない）。ファイルの末尾に、空行を 1 つ置いて次の節を足す。

```markdown
## DeployMigrationFailed

- 札：page
- 何が起きているか：本番への反映（deploy.yml）で DB の入れ替え（migration）の手順が失敗または取り消しで終わった。deploy.yml の「Record migration result」が prod1 の `/home/ubuntu/node_exporter_textfile/deploy_migration_failure.prom` に失敗の時刻を書き、それが成功の時刻（`deploy_migration_success.prom`）より新しい。DB が途中の形のままの可能性がある。
- 最初に見るもの：GitHub の Actions の「Deploy to VPS」の直近の回 → 「Run database migrations」の手順の記録の最後の数十行（どの移行で止まったか・時間切れか）→ 「Clean up DB orphans after failure」が動いたか。
- 直し方：原因を切り分けて Opus に報告する。migration を直して次の deploy で成功すると、成功の時刻が書かれて自然に止む。migration の手順を飛ばした deploy（migration の判定が false の回）では何も書かれないので、止むのは migration が走って成功した回だけ。
- 止め方：`amtool silence add alertname=DeployMigrationFailed --duration=PERIOD --comment=REASON`
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-h-impl/ に置く）

5-1. 試験：作業場所で `python3 scripts/tests/test_deploy_migration_mark.py 2>&1 | tail -15` が `Ran 10 tests` と `OK`。python3 の版も `python3 --version` で記録する（標準ライブラリだけなので venv は作らない）
5-2. 見張りの検査：`python3 monitoring/scripts/check_alert_rules.py 2>&1 | tail -5` が `OK: Prometheus 39 rules, Loki 6 rules, runbook 45 sections`（便G が先に main に入っていれば、その時の本数＋1 と手順書の節の数＋1）。promtool は手元で動かさない（Mac でコンテナを動かさない。CI の monitoring-check が流す）
5-3. 差分：`git diff origin/main --stat` が §3 のファイルだけ。加えて `git diff origin/main | grep -E '^-' | grep -v '^--- '` の出力が次の 3 行だけ（`- ` で始まる箇条の旧行も数えるため、`^-[^-]` は使わない）：alert_rules_test.yml 1 行（4 行目の旧行）／alerts.md 1 行（3 行目の旧行）／このカード 1 行（§13 の「（未記入）」）。deploy.yml・deploy-script-test.yml・alert_rules.yml は足すだけなので旧行は出ない。数が違うときは、その行の原文を貼る
5-4. 書式の手元確認：`python3 -m py_compile scripts/ops/deploy_migration_mark.py scripts/tests/test_deploy_migration_mark.py; echo rc=$?` が `rc=0`。`python3 -c "import yaml,sys; [yaml.safe_load(open(p)) for p in sys.argv[1:]]; print('yaml ok')" .github/workflows/deploy.yml .github/workflows/deploy-script-test.yml monitoring/prometheus/alert_rules.yml monitoring/prometheus/tests/alert_rules_test.yml` が `yaml ok`（PyYAML が無ければ `pip install --user pyyaml` で入れてよい。入れられなければその旨を書いて飛ばす）
5-5. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI の結果は Opus が見る）

## 6. 分岐ごとの対処

- §4 の目印の行が見つからない（ほかの PR が先に変えた）→ `git show origin/main:monitoring/prometheus/alert_rules.yml | tail -20` のように、そのファイルを origin/main で読み直し、同じ意味の位置に足す。便G が先に main に入って見張りの本数・手順書の節の数が変わっていたら、`python3 monitoring/scripts/check_alert_rules.py` の出力の本数に合わせて「今の数＋1」にする。決められなければ NEEDS_DECISION: で出力を貼る
- deploy.yml の「Clean up DB orphans after failure」か「Post-deploy smoke tests (SA-19)」の名前が変わっている → 足さずに NEEDS_DECISION: で `grep -n 'name: ' .github/workflows/deploy.yml | sed -n '1,200p'` の該当部分を貼る
- 試験が落ちる → 試験ではなく §4 の完成形との違いを直す。§4 のとおりで落ちるなら原文を貼って BLOCKED:
- §4 の完成形に誤りと思われる箇所がある → 直さずに NEEDS_DECISION: で、行と理由を書く

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 書く係と手順の位置・条件の試験 10 件が pass | §5-1 と CI（deploy-script-test） |
| 失敗が新しいとき・失敗だけのときに DeployMigrationFailed が鳴り、成功が新しいとき・成功だけのときは鳴らない | CI（monitoring-check）の `promtool test rules`（既存を含め全部 pass） |
| 札と手順書リンクの欠けが 0 | §5-2 と CI（monitoring-check） |
| 触ったファイルが §3 だけで、migration の手順そのものは 1 行も変わっていない | §5-3（deploy.yml の旧行が 0 行） |
| 本番：この便の deploy の後、prod2 の Prometheus に `salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps"}` があり、値がその deploy の migration の手順の終わりの時刻から 5 分以内 | §8-3 の問い合わせの生出力と Actions の記録の時刻 |
| 本番：その後 `ALERTS{alertname="DeployMigrationFailed"}` が空（鳴っていない） | §8-3 の生出力 |
| 本番：その deploy の「Record migration result」の記録に `deploy_migration_mark: wrote success` が出ている | §8-2 の Actions の記録 |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 審査：差分を §4 の完成形と照らし、CI（deploy-script-test・monitoring-check を含む）が緑なら、危険 PR の GO 手順（ADR-136）で「POの委任に基づくClaude Opus発行」の GO を PR に記録してマージする
2. deploy.yml の成功を Actions の記録で確かめる。「Run database migrations」が動き（F4 によりこの便の deploy では動く）、「Record migration result (ADR-1012 段階3 便H)」の記録に `deploy_migration_mark: wrote success` が出ていること。`write failed` が出ていたら（書く権限が無いなど）、原因の原文を持って PO に戻す（deploy の成否は変わらないので急がない）。手順が skipped なら migration が走らなかった回なので、次に migration が走る deploy で確かめる
3. 書いた 2 分後に prod2 の Prometheus へ `salesanchor_deploy_migration_last_success_timestamp_seconds{instance="app-vps"}`・`ALERTS{alertname="DeployMigrationFailed"}`・`/api/v1/rules` の DeployMigrationFailed の有無を問い合わせる（読むだけ）
4. 本番で migration の失敗は起こさない（設計 §2 便H）。鳴る形は CI の promtool の試験で確かめたものとする
5. 生出力は /tmp/CC報告ファイル/ai-ops-stage3/bin-h-deploy/ に置く

## 9. 弊害と戻し方

- 弊害：deploy の手順が 1 つ増え、migration が走った回だけ ssh 1 回分（数秒）長くなる。打ち切りは 2 分で、失敗しても deploy の成否は変わらない
- 弊害：migration が失敗した後、migration を飛ばす deploy（判定が false の回）が続く間は鳴り続ける。前の deploy が失敗していれば次の deploy は判定で全部走る（`.github/workflows/deploy.yml:84-90`）ので、ふつうは次の deploy で止む。止まらないときは手順書の止め方で黙らせる
- 弊害：見張りが鳴っている間、Discord と障害記録に札 page で届く（Alertmanager は札で行き先を分けていない）
- 戻し方：この PR の revert を main にマージ → 次の deploy で手順・係・見張りが外れる。prod1 の `deploy_migration_success.prom`・`deploy_migration_failure.prom` は残っても、見張りが無ければ鳴らない（設計 §8 :182）。消すときは PO の `!` で消す

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-deploy-migration-alert-bin-h --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16・10-17・11-20 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-deploy-migration-alert-bin-h` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う（クラウドで動くときは、クラウドの作業場所の手順に従い、同じブランチ名で作る）
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-deploy-migration-alert-bin-h -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-deploy-migration-alert-bin-h --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage3-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: scripts/ops/deploy_migration_mark.py, scripts/tests/test_deploy_migration_mark.py, .github/workflows/deploy.yml, .github/workflows/deploy-script-test.yml, monitoring/prometheus/alert_rules.yml, monitoring/prometheus/tests/alert_rules_test.yml, docs/runbooks/alerts.md, docs/handoff/ai-ops-247/card-stage3-bin-h.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（alert_rules_test.yml・alerts.md と、§13 の「（未記入）」を書き換えるこのカード））
- 本文に「危険 PR（deploy.yml・scripts/）。GO・マージと反映後の観測は Opus がカード §8 の順で行う」と 1 行書く
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力（長いものは生出力のパスと要点の行）／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage3/bin-h-impl/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep は使わない。CI・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

本報告はカード 段階3 便H の実行結果である

- §5-1：Python 3.12.3。`Ran 10 tests` と `OK`
- §5-2：`OK: Prometheus 41 rules, Loki 6 rules, runbook 47 sections`（便G が main に入済みで今の数は 40・46 だったため、今の数＋1）
- §5-3：差分は §3 のファイルだけ。削除行は alert_rules_test.yml 1 行・alerts.md 1 行・このカード 1 行（3 行）
- §5-4：py_compile rc=0・yaml ok
- PR：作らない（依頼どおり）
- 判断を要した点（事実のみ）：origin/main の本数は 38 でなく 40 本・手順書は 46 節だった。uv の venv に pip が無く、`uv pip install --python /tmp/v312/bin/python pyyaml` で PyYAML を入れた。作業場所は /root/worktrees/salesanchor/release-ai-ops-deploy-migration-alert-bin-h（基点 ab92808c1）

END OF CARD
