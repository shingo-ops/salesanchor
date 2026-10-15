# 実装カード 段階1 便7 — 本番の監視設定と repo の一致の見張り

> この文書は何か：AI保守運用24時間化 段階1 便7 の作業指示書です。監視用サーバー prod2 の self-hosted runner で毎日 1 回動く workflow を足し、prod2 に手作業で置いた監視設定 6 本と main の sha256 を比べ、ずれた件数を prod2 の pushgateway に送ります。ずれが 1 件以上で鳴る見張りと、確認そのものが止まったら鳴る見張りの 2 本を足します。本番への配置は §8 で、マージの後に行います（prod2 のルールの手作業の配置と、わざと 1 本ずらして鳴ることの確かめ）。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便7・§5 戻し方・§6 受け入れ基準
- 事実確認の生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin7-recon/facts.md（Q1〜Q8。2026-10-15 Sonnet。repo は origin/main 3d41e0c86・本番は読み取りのみ）
- 対象ADR: ADR-1012（本テーマ）・ADR-029（self-hosted runner）・ADR-1003（GO の委任）
- 状態: PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」・10-15 再送）に基づく実装便
- 前提: 便6 の実装 PR（release/ai-ops-stage1-bin6）が main にマージされ、prod2 に配置済みであること（ルール 20 本・手順書 26 節の状態から始める）。このカードの PR（文書だけ）が main にマージされていること（§10 で確かめる）
- 危険便: いいえ（`migrations/`・`deploy.yml`・`scripts/` 配下を触らない。`scripts/check-process-artifacts.js:115-124` の危険パス（`^scripts/` を含む）に当たらないよう、試験も `monitoring/scripts/tests/` に置く。2026-10-15 設計審査 H1 で直した）。workflow の追加はあるが `.github/workflows/workflow-lint.yml` は変えない（ADR-1003 の例外に当たらない）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable（利用上限の間は PO の許可で Opus が代行）／GO・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（監視設定のずれの見張りと、その確認の workflow だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§8-6。ずれの件数とファイル名を対で出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。今は 6 本すべて一致＝ずれ 0。pushgateway は prod2 の中から 127.0.0.1:9091） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8 は prod2 だけ。無制限鍵） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便7 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 新規 `.github/workflows/monitoring-config-drift.yml`（毎日 00:23 UTC と手動実行だけ。prod2 の runner で動く）
2. 新規 `monitoring/scripts/check_config_drift.sh`（6 本の sha256 を比べ、件数と実行時刻を pushgateway に送る）
3. 新規 `monitoring/scripts/tests/test_check_config_drift.sh`（上のスクリプトを一時ディレクトリで試す）
4. `monitoring/prometheus/alert_rules.yml` に新しいグループ `config_drift_alerts`（2 本）
5. `monitoring/prometheus/tests/alert_rules_test.yml` に 2 本の試験
6. docs/runbooks/alerts.md に 2 節
7. `monitoring/tokens.yml` に閾値 1 行・for 2 行

入れない:
- prod2 へ設定を自動で配る仕組み（設計 §7 U4。この便はずれを見つけるだけ）
- ダッシュボード JSON と `generate-nav.js`（設計 §7 U3）
- `.github/workflows/workflow-lint.yml`・`.github/workflows/monitoring-check.yml`・既存の workflow（新しい bash の試験を CI で毎回走らせることは段階1 の範囲外。§13 の後に Opus が未解決事項に足す）
- secrets・`.env`・`secrets/` の中（比べる対象に入れない）
- 既存の Prometheus 20 本と Loki 6 本

## 2. 前提の事実（facts.md の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | prod2 の runner は systemd の `actions.runner.shingo-ops-salesanchor.salesanchor-vps.service`（active）。利用者は ubuntu。workflow 側の指定は `runs-on: [self-hosted, salesanchor-vps]` | Q1 |
| F2 | 前例 `.github/workflows/external-state-snapshot.yml` は `schedule` と `workflow_dispatch` だけ・`concurrency` 固定・`actions/checkout@v5`・`permissions:` 無し | Q1・`.github/workflows/external-state-snapshot.yml:36-60` |
| F3 | prod2 の配置ルートは `/opt/salesanchor-monitoring`。repo と同じ相対パスに 6 本（§4-2 の一覧）があり、今は 6 本すべて main と sha256 一致（ずれ 0） | Q2 |
| F4 | 6 本とも `ubuntu:ubuntu`・644。ubuntu で `test -r` が通る。`secrets/` は 700、`.env` は 600 | Q3 |
| F5 | 6 本に秘密の直書きは無い（alertmanager の webhook はファイル参照、compose は環境変数参照） | Q4 |
| F6 | pushgateway は prod2 で v1.10.0。prod2 の中からは `127.0.0.1:9091`。Prometheus は job `pushgateway`・`honor_labels: true` で 60 秒ごとに読む | Q5・`monitoring/prometheus/prometheus.yml:63-67` |
| F7 | pushgateway は送りが止まっても最後の値を持ち続ける。だから「確認が止まった」は `absent()` ではなく、送った時刻の古さで見る | Q8 |
| F8 | `.github/workflows/workflow-lint.yml:50-96` は固定の 9 ファイルだけを検査する。新しい workflow を足しても workflow-lint.yml の変更は要らない | Q6 |
| F9 | Prometheus が読むルールは `alert_rules.yml` だけ | `monitoring/prometheus/prometheus.yml:9-10`（2026-10-15 Opus） |
| F10 | リポジトリは公開。Actions の権限設定と fork PR の承認設定は 403 で【未確認】 | Q7 |

決めたこと:
- トリガーは `schedule`（毎日 00:23 UTC＝09:23 JST。GitHub の公式ドキュメント（Events that trigger workflows の schedule の節）が「毎時 0 分は混み、遅れや抜けが起きうる。別の分にせよ」と書くため 0 分を外す）と `workflow_dispatch` だけ。`pull_request`・`push` は付けない（公開リポジトリの self-hosted runner で、外の人の変更を動かさないため。F10 の設定が【未確認】でも、この 2 つのトリガーは書き込み権限のある人と GitHub の時刻起動しか動かせない）。
- `permissions: contents: read`。checkout は `ref: main` 固定・`persist-credentials: false`。secrets は使わない。
- ログには件数とファイル名だけを出す。sha256 の値と中身は出さない。
- 送る値は 2 つ: ずれた件数 `monitoring_config_drift_files` と、送った時刻 `monitoring_config_drift_last_run_timestamp`。job 名は `monitoring_config_drift`。片方のファイルが無い・読めないときも「ずれ」に数える。比べる途中でスクリプトが失敗したときは送らない（時刻が進まず、§4-4 の 2 本目が鳴る）。
- 見張り 1（`MonitoringConfigDrift`）: ずれが 1 件以上の状態が 5 分続いたら鳴る。ticket（利用者に今の影響は無い。repo と本番の鳴らす条件が違うまま、という状態）。
- 見張り 2（`MonitoringConfigCheckStale`）: 送った時刻が 50 時間（180000 秒）より古い、または系列が無い状態が 1 時間続いたら鳴る。根拠: 毎日 1 回なので差は最大で約 24 時間。1 回抜けても鳴らず、2 回続けて抜けたら（48 時間超）鳴る。GitHub の時刻起動は遅れたり抜けたりすることがあるため、1 回の抜けでは鳴らさない。ticket。
- main にマージしてから prod2 に置くまでの間は、毎朝の確認で「ずれ 1 件」が出て鳴る。これは正しい動き（置き忘れを知らせる）。手順書に書く。
- 便7 の workflow 自体は外から動かす経路を足さない（`schedule` は既定ブランチの workflow だけが動き、手動実行は書き込み権限が要る）。ただし同じ runner を使う既存の `.github/workflows/qa-smoke.yml:42-50` は `pull_request` を持ち、fork の PR の承認設定は【未確認】（F10）。便7 では変えない。§13 の後に Opus が設計の未解決事項に書き、PO に GitHub の画面で fork の PR の承認設定を確かめてもらう。
- 設計 §2 便7（docs/handoff/ai-ops-247/stage1-design.md:141）の「`absent()` ルール」を、「送った時刻の古さ or absent」に変えた（F7: pushgateway は最後の値を持ち続けるため、absent だけでは止まったことに気づけない）。設計本文との差は Opus が §13 の後に設計の未解決事項に書く。
- 比べるのは決まった 6 本だけ。Loki のルールはディレクトリごと差しているので、今後ファイルが増えても自動では見張られない（手順書の MonitoringConfigDrift の節に書く。増やすときは `FILES` に足す）。

## 3. 触るファイル（これ以外は触らない）

- 新規: `.github/workflows/monitoring-config-drift.yml`
- 新規: `monitoring/scripts/check_config_drift.sh`
- 新規: `monitoring/scripts/tests/test_check_config_drift.sh`
- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin7.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. 新規 `.github/workflows/monitoring-config-drift.yml`（完成形。コメントの言葉は変えてよいが、トリガー・権限・runner・checkout の指定は変えない）:

```yaml
name: Monitoring config drift check

# 監視用サーバー(prod2)に置いた監視設定と main のずれを毎日数え、pushgateway に送る（ADR-1012 段階1 便7）
# 公開リポジトリの self-hosted runner なので、pull_request・push では動かさない。secrets も使わない
on:
  schedule:
    # 毎日 09:23 JST = 00:23 UTC（毎時 0 分は GitHub の時刻起動が混むため外す）
    - cron: '23 0 * * *'
  workflow_dispatch: {}

permissions:
  contents: read

concurrency:
  group: monitoring-config-drift
  cancel-in-progress: false

jobs:
  drift:
    name: 監視設定のずれの確認
    runs-on: [self-hosted, salesanchor-vps]
    timeout-minutes: 5

    steps:
      - name: Checkout
        uses: actions/checkout@v5
        with:
          ref: main
          persist-credentials: false

      - name: ずれを数えて pushgateway に送る
        run: bash monitoring/scripts/check_config_drift.sh "$GITHUB_WORKSPACE" /opt/salesanchor-monitoring
```

4-2. 新規 `monitoring/scripts/check_config_drift.sh`（完成形。実行権限 755 で commit する）:

```bash
#!/usr/bin/env bash
# 監視用サーバー(prod2)に置いた監視設定と main のずれを数え、pushgateway に送る（ADR-1012 段階1 便7）
# 使い方: check_config_drift.sh REPO_ROOT DEPLOY_ROOT（REPO_ROOT は main の作業ツリー、DEPLOY_ROOT は prod2 の配置ルート）
# 環境変数: PUSHGATEWAY_URL（既定 http://127.0.0.1:9091）。DRY_RUN=1 なら送らずに送る本文を出す
# ログには件数とファイル名だけを出す（公開リポジトリの Actions のログに中身と sha256 を残さない）
set -euo pipefail

REPO_ROOT="${1:?usage: check_config_drift.sh REPO_ROOT DEPLOY_ROOT}"
DEPLOY_ROOT="${2:?usage: check_config_drift.sh REPO_ROOT DEPLOY_ROOT}"
PUSHGATEWAY_URL="${PUSHGATEWAY_URL:-http://127.0.0.1:9091}"

# 配置ルートが無い機体（prod2 以外）で動いたら、数えずに失敗で終わる
[ -d "${DEPLOY_ROOT}" ] || { echo "DEPLOY_ROOT not found: ${DEPLOY_ROOT}"; exit 1; }

# 比べる 6 本（prod2 の配置ルートからの相対パスは repo と同じ）。secrets・.env は入れない
FILES=(
  docker-compose.monitoring.yml
  monitoring/prometheus/prometheus.yml
  monitoring/prometheus/alert_rules.yml
  monitoring/loki/loki-config.yaml
  monitoring/loki/rules/jarvis/alerts.yml
  monitoring/alertmanager/alertmanager.yml
)

drift=0
for f in "${FILES[@]}"; do
  if [ ! -r "${REPO_ROOT}/${f}" ] || [ ! -r "${DEPLOY_ROOT}/${f}" ]; then
    echo "DRIFT (missing or unreadable): ${f}"
    drift=$((drift + 1))
    continue
  fi
  repo_sum=$(sha256sum "${REPO_ROOT}/${f}" | cut -d' ' -f1)
  deploy_sum=$(sha256sum "${DEPLOY_ROOT}/${f}" | cut -d' ' -f1)
  if [ "${repo_sum}" != "${deploy_sum}" ]; then
    echo "DRIFT: ${f}"
    drift=$((drift + 1))
  fi
done
echo "checked=${#FILES[@]} drift=${drift}"

body="# TYPE monitoring_config_drift_files gauge
monitoring_config_drift_files ${drift}
# TYPE monitoring_config_drift_last_run_timestamp gauge
monitoring_config_drift_last_run_timestamp $(date +%s)
"

if [ "${DRY_RUN:-0}" = "1" ]; then
  printf '%s' "${body}"
  exit 0
fi

printf '%s' "${body}" | curl -fsS --max-time 10 --data-binary @- \
  "${PUSHGATEWAY_URL}/metrics/job/monitoring_config_drift"
echo "pushed job=monitoring_config_drift"
```

4-3. 新規 `monitoring/scripts/tests/test_check_config_drift.sh`（`scripts/tests/test-reaper-safety.sh` などと同じ書き方。`set -euo pipefail`・一時ディレクトリは `mktemp -d` と EXIT の trap・PASS/FAIL を echo・最後に FAIL があれば exit 1）。repo の作業ツリーの 6 本を一時ディレクトリの「repo 役」と「本番役」の 2 か所に写して、`DRY_RUN=1` で `monitoring/scripts/check_config_drift.sh` を呼ぶ。試すこと:
1. 同じ: 出力に `checked=6 drift=0` と `monitoring_config_drift_files 0` があり、`DRIFT` の行が 0。`monitoring_config_drift_last_run_timestamp` の数字が今の `date +%s` との差 5 秒以内
2. 1 本ずれ: 本番役の `monitoring/prometheus/alert_rules.yml` の末尾に `# drift test` の 1 行を足す → `DRIFT: monitoring/prometheus/alert_rules.yml` の 1 行だけ・`checked=6 drift=1`・`monitoring_config_drift_files 1`
3. 1 本無い: 本番役の `monitoring/loki/rules/jarvis/alerts.yml` を消す → `DRIFT (missing or unreadable): monitoring/loki/rules/jarvis/alerts.yml`・`drift=1`
4. ログに sha256 が出ない: 1〜3 の出力すべてで、64 桁の 16 進（`grep -cE '[0-9a-f]{64}' || true` で数を受ける。0 件のとき grep は終了コード 1 を返すため）が 0
5. 送れないときは失敗で終わる: `DRY_RUN` を付けず `PUSHGATEWAY_URL=http://127.0.0.1:9` で呼ぶ → 終了コードが 0 でない
6. 引数が無いときは失敗で終わる: 引数なしで呼ぶ → 終了コードが 0 でない
7. 配置ルートが無いときは失敗で終わる: 本番役に無いディレクトリを渡して `DRY_RUN=1` で呼ぶ → 終了コードが 0 でなく、出力に `DEPLOY_ROOT not found` があり、`monitoring_config_drift_files` の行が無い
- `set -euo pipefail` の下で書くので、終了コードを確かめる呼び出しは `rc=0; コマンド || rc=$?` の形で受ける。

4-4. `monitoring/prometheus/alert_rules.yml` の最後（便6 の `backup_alerts` グループの後）に、新しいグループを足す（完成形）:

```yaml
  - name: config_drift_alerts
    rules:
      # prod2 に置いた監視設定 6 本と main のずれ（.github/workflows/monitoring-config-drift.yml が毎日 pushgateway に送る）
      - alert: MonitoringConfigDrift
        expr: monitoring_config_drift_files{job="monitoring_config_drift"} > 0
        for: 5m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "監視サーバーの設定が main とずれています"
          description: "prod2 に置いた監視設定のうち {{ $value }} 本が main と一致しません。workflow の実行ログでファイル名を確認し、main の版を置き直してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#monitoringconfigdrift"

      # ずれの確認そのものが止まった（tokens.yml: config_check_stale_sec=180000）
      # pushgateway は最後の値を持ち続けるので、送った時刻の古さで見る
      - alert: MonitoringConfigCheckStale
        expr: (time() - monitoring_config_drift_last_run_timestamp{job="monitoring_config_drift"}) > 180000 or absent(monitoring_config_drift_last_run_timestamp{job="monitoring_config_drift"})
        for: 1h
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "監視設定のずれの確認が 50 時間以上動いていません"
          description: "monitoring-config-drift の workflow が 50 時間以上 pushgateway に送っていません。prod2 の runner と workflow の実行を確認してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#monitoringconfigcheckstale"
```

4-5. `monitoring/prometheus/tests/alert_rules_test.yml` の最後に 2 本の試験を足す（他の試験は変えない。冒頭のコメントの「全 20 本」は「全 22 本」に直す）。`time()` は 0 から始まる（F2CleanupStale の注記と同じ）。promtool は入力の系列が test group ごとなので、入力ごとに group を分ける（計 5 group: Drift「ずれ 1」（鳴る 10m・for より前 3m）・Drift「ずれ 0」・Stale「古い」・Stale「無い」（鳴る 2h・for より前 30m）・Stale「新しい」。「無い」を他の系列と同じ group に置くと absent が鳴らない）:
1. MonitoringConfigDrift 鳴る: `monitoring_config_drift_files{job="monitoring_config_drift"}` が `1x30`（interval 1m）で `eval_time` 10m に 1 件（`exp_labels` は job・severity・tier）。鳴らない（for より前）: 同じ入力で `eval_time` 3m に 0 件。鳴らない（ずれ 0）: `0x30` で `eval_time` 10m に 0 件
2. MonitoringConfigCheckStale 鳴る（古い）: `monitoring_config_drift_last_run_timestamp{job="monitoring_config_drift"}` が `-200000+0x200` で `eval_time` 2h に 1 件（`exp_labels` は job・severity・tier）。鳴る（無い）: 無関係の系列 `up{job="dummy", instance="x"}` を `1x200` だけ置いて `eval_time` 2h に 1 件（`exp_labels` は job・severity・tier。absent が付ける job の札）。鳴らない（for より前）: 「無い」と同じ入力で `eval_time` 30m に 0 件。鳴らない（新しい）: `0+60x200` で `eval_time` 2h に 0 件
- description の展開後の文字列は `promtool test rules --diff` の got 側から写してよい（便3 カード §6 と同じ扱い）。

4-6. docs/runbooks/alerts.md に 2 節を足す（あわせて冒頭 :3 の「Prometheus 20 本」を「22 本」に直す）。見出しは `## MonitoringConfigDrift`・`## MonitoringConfigCheckStale`。5 項目（札・何が起きているか・最初に見るもの・直し方・止め方）の形は既存のまま。書くこと:
- 2 節とも: 札 ticket。「利用者に今の影響は無い。翌営業日までに直す」。止め方は既存と同じ `amtool silence add alertname=… --duration=PERIOD --comment=REASON` の形。
- MonitoringConfigDrift: 何が起きているか（毎日 09:23 JST ごろの確認で、prod2 に置いた監視設定 6 本のうち 1 本以上が main と一致しない。main にマージしてから prod2 に置くまでの間も鳴る。置き忘れの知らせ）。最初に見るもの: GitHub の Actions の「Monitoring config drift check」の最新の実行ログ（`DRIFT:` の行にファイル名が出る）。直し方: どちらが正しいかを切り分ける。main が正しければ main の版を prod2 に置き直して読み直す（手順は各便のカード §8 と同じ）。prod2 の手直しが正しければ repo に PR で取り込む。置き直した後は workflow を手動で 1 回実行して、ずれ 0 を確かめる（pushgateway は次に送るまで古い値を持ち続ける）。迷ったら Opus に報告する。比べるのはスクリプトの `FILES` にある 6 本だけで、監視設定のファイルを増やしたら `FILES` にも足す、と 1 行書く。
- MonitoringConfigCheckStale: 何が起きているか（ずれの確認が 50 時間以上 pushgateway に送っていない。2 回続けて動かなかった）。最初に見るもの: Actions の実行の一覧（失敗か、そもそも起動していないか）、prod2 の runner のサービス（`systemctl status actions.runner.shingo-ops-salesanchor.salesanchor-vps`）、pushgateway のコンテナ。直し方: runner・workflow・pushgateway のどこで止まっているかを切り分けて Opus に報告する。
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

4-7. `monitoring/tokens.yml`:
- `thresholds:` の `# ログ異常検知` の段の前（便6 の backup の段の後）に、空行と次の段を足す:

```yaml
  # 監視設定のずれ（alert_rules.yml: config_drift_alerts）
  # .github/workflows/monitoring-config-drift.yml が prod2 の pushgateway に送る値を使用
  config_drift_files:          0  # MonitoringConfigDrift: monitoring_config_drift_files > 0
  config_check_stale_sec: 180000  # MonitoringConfigCheckStale: time() - 送った時刻 > 180000（50h）
```

- `for_durations:` の最後に足す:

```yaml
  config_drift:       "5m"  # MonitoringConfigDrift
  config_check_stale: "1h"  # MonitoringConfigCheckStale
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 作業場所で `python3 -c "import yaml; [print(g['name'], r['alert'], r.get('for'), r['labels']) for g in yaml.safe_load(open('monitoring/prometheus/alert_rules.yml'))['groups'] for r in g['rules']]"` を実行し、`git show origin/main:monitoring/prometheus/alert_rules.yml > /tmp/CC報告ファイル/ai-ops-stage1-bin7/rules-main.yml` の版に対しても同じ 1 行を実行して `diff` に通す（期待: 足された 2 行（config_drift_alerts の 2 本）だけが違う）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 22 rules, Loki 6 rules, runbook 28 sections`。
5-3. `git diff --numstat origin/main -- monitoring/prometheus/alert_rules.yml` の出力（期待: 2 列目（削除行数）が 0。足すだけ）。
5-4. `bash monitoring/scripts/tests/test_check_config_drift.sh` の出力全文と終了コード（期待 0・FAIL の行 0）。あわせて `bash -n monitoring/scripts/check_config_drift.sh` の終了コード（期待 0）と、`git ls-files -s monitoring/scripts/check_config_drift.sh` の mode（期待 100755）。`shellcheck` が手元にあれば 2 本に対して実行し、出力を貼る（無ければ「無い」と書く。指摘があれば直す）。
5-5. わざと壊して落ちることを確かめる（一時的な書き換え。確かめたら `git checkout -- <file>` で戻し、`git diff --stat` で戻ったことを出す。新規ファイルなので戻しは Write で元の完成形に戻す）: `monitoring/scripts/check_config_drift.sh` の `drift=$((drift + 1))`（sha256 が違うときの側）を消すと、§4-3 の試験 2 が落ちる。`bash monitoring/scripts/tests/test_check_config_drift.sh` の出力と終了コード 1 を貼る。
5-6. 本番と同じ版のイメージ（`prom/prometheus:v3.11.3`）で `promtool check rules`（期待 "SUCCESS: 22 rules found"）と `promtool test rules`（期待 "SUCCESS"）を実行し、出力と終了コードを貼る（`-v` が効かなければ `docker create` → `docker cp` → `docker start -a`）。
5-7. わざと壊して落ちることを確かめる: MonitoringConfigCheckStale の `> 180000` を `> 1800000` にすると、§4-5 の試験 2 の「鳴る（古い）」が落ちる。`promtool test rules` の出力と終了コード 1 を貼り、戻す。
5-8. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「不一致」の行（期待: 不一致 0）。このスクリプトは config_* を照合しないので、値の一致は §5-1 の出力と tokens.yml の 4 行を並べて報告に貼って示す。
5-9. workflow の安全の条件を出す: `grep -nE '^on:|schedule|workflow_dispatch|pull_request|push:|permissions|contents:|ref: main|persist-credentials|secrets\.' .github/workflows/monitoring-config-drift.yml`（期待: `pull_request` は §4-1 のコメント「pull_request・push では動かさない」の 1 行だけ。`push:`・`secrets.` は 0 行。`contents: read`・`ref: main`・`persist-credentials: false` が 1 行ずつ）。`actionlint` が手元にあれば `actionlint -ignore 'label "salesanchor-vps" is unknown' .github/workflows/monitoring-config-drift.yml` で実行し出力を貼る（無ければ「無い」と書く。独自ラベルの 1 件は repo に actionlint の設定が無いため出る想定内のもの）。あわせて `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/monitoring-config-drift.yml'))"` の終了コード（期待 0）。
5-10. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md monitoring/scripts/check_config_drift.sh .github/workflows/monitoring-config-drift.yml` の該当（期待: `127.0.0.1` の 2 行だけ（スクリプトの環境変数のコメントと既定値）。消しにいかない。版の番号の形に当たった行は、その行を貼って IP でないことを書く）。
5-11. `git diff origin/main --stat` が §3 のファイルであること（§13 の追記前なら 7 ファイル、追記後なら 8 ファイル）。

## 6. 分岐ごとの対処

- 5-1〜5-3・5-8〜5-11 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-4 の試験が落ちる → §4-2 の完成形と一字ずつ比べて直す。3 回直しても通らなければ出力を貼って BLOCKED:。
- 5-6 で promtool の test が落ちる → 試験の期待値（展開後の文字列・absent の札など）を直してやり直す。§4-4 の式・for・閾値を変えて合わせることはしない。3 回直しても通らなければ出力を貼って BLOCKED:。
- 前提の便6 の実装 PR がマージされていない → 作業を始めずに止まる（BLOCKED:）。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → 便3 カード §6 と同じく `quay.io` の同じ版に替えてよい。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 見張り 2 本が §4-4 の完成形で入り、既存の 20 本は変わらない | §5-1・§5-3 |
| 2 本とも鳴るときに鳴り、鳴らないときに鳴らない（単体試験） | §5-6・§5-7・PR の CI |
| 札・手順書リンク・見出しの検査が通る（22 本・28 節） | §5-2 |
| スクリプトがずれ・欠けを数え、ログに sha256 を出さず、送れないときは失敗で終わる | §5-4・§5-5 |
| workflow が `schedule`・`workflow_dispatch` だけで、`contents: read`・`ref: main`・secrets 無し | §5-9 |
| prod2 の runner で workflow が動き、今の本番で `drift=0` を送る | §8-3・§8-6 |
| 本番の Prometheus に 2 本が入り、評価の失敗が無い | §8-6 |
| わざと 1 本ずらすと MonitoringConfigDrift が 1 回鳴り、戻すと消える | §8-7・§8-8 |
| 翌日の時刻起動で送った時刻が進む | 配置の翌日 12:00 JST 以降に Opus が `monitoring_config_drift_last_run_timestamp` を読み、その日の 09:23〜12:00 JST の範囲にあることを確かめる（時刻起動は遅れることがあるため幅を取る） |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

機体は prod2 だけ。SSH は制限付き鍵で書けないため無制限鍵を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md。本番で行う操作は下の 8-1〜8-9 だけ。Loki・Alertmanager・tokens.yml は本番に配らない。待ちに sleep は使わない。待ちが要る手順（8-5・8-8）は、そこで報告を返して終える。続きは Opus が依頼する。

8-1. 控え: `/opt/salesanchor-monitoring/backups/ai-ops-stage1/` に、prod2 の本番の `alert_rules.yml` を `cp -p` で `.bak-20261015-` に PR 番号を付けた名前で写し、元と控えの sha256 を出す。あわせて本番のファイルが、この PR のマージ commit の 1 つ前の版と同じであることを出す（`MC=$(gh pr view PR --json mergeCommit -q .mergeCommit.oid)` → `git fetch origin && git show "$MC^1":monitoring/prometheus/alert_rules.yml | sha256sum`。PR は便7 の実装 PR の番号）。一致しなければ止まる。
8-2. prod2 で `command -v sha256sum curl` の 2 行が出ること（runner の利用者 ubuntu で）。
8-3. 1 回目の手動実行（ルールを置く前）: `gh workflow run monitoring-config-drift.yml --ref main` を実行し、`gh run list --workflow monitoring-config-drift.yml --limit 1 --json databaseId,status,conclusion,createdAt` を出す。終わっていれば `gh run view <id> --json jobs -q '.jobs[].runnerName'` で動いた runner の名前を出し（期待: prod2 の runner `salesanchor-vps`）、`gh run view <id> --log` のうち `DRIFT`・`checked=`・`pushed` の行だけを出す（期待: `DRIFT: monitoring/prometheus/alert_rules.yml` の 1 行・`checked=6 drift=1`・`pushed job=monitoring_config_drift`。main には 22 本のルールがあり、prod2 はまだ 20 本のため）。終わっていなければ状態を報告して終える（待たない）。
8-4. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-ai-ops-bin7/` を作り、main の `monitoring/prometheus/alert_rules.yml` を scp で送る。同じ版の promtool で `check rules` を通す（"SUCCESS: 22 rules found"）。本番の場所に `install -m` で元と同じ権限で置き、本番のファイルと main の sha256 が一致することを出す。Prometheus のコンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送り、終了コードを出す。一時ディレクトリは消さない（削除はフックに止められる）。中身の一覧（`ls -la`）だけ出す。8-4 の後は間を空けずに 8-5 に進む。8-3 で送った drift=1 が pushgateway に残っているため、8-5 で 0 を送るまでに 5 分を超えると MonitoringConfigDrift が 1 回鳴る。これは想定内で、8-5 で 0 になれば消える（止まらない）。
8-5. 2 回目の手動実行（ずれ 0 の確かめ）: 8-3 と同じ手順（期待: `DRIFT` の行 0・`checked=6 drift=0`・`pushed`）。その後に読み取りで次を出す:
  - Prometheus の `/api/v1/rules`: ルール数（期待 22）・`tier` が無いルール（期待 0 件）・`tier` ごとの数（期待 page 6・ticket 16）・`health` が ok でないルールの数（期待 0）・`config_drift_alerts` の 2 本の名前
  - Prometheus の `/api/v1/query`: `monitoring_config_drift_files` の値と全ての札（期待 0・job=monitoring_config_drift）・`time() - monitoring_config_drift_last_run_timestamp{job="monitoring_config_drift"}`（期待 600 未満）
  - Alertmanager の `/api/v2/alerts` の alertname と `tier` の一覧
  - Prometheus が pushgateway を読むのは 60 秒ごとなので、値が 1 のままなら報告を返して終える（Opus が時間を置いて続きを依頼する）
8-6. 生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin7/deploy/ に保存する。ここで 1 度報告を返す。
8-7. わざとずらす（Opus の合図の後）: 本番の `/opt/salesanchor-monitoring/monitoring/prometheus/alert_rules.yml` の末尾に `# drift test ADR-1012 bin7` の 1 行を `echo … >> …` で足す（コメントの行なので Prometheus の動きは変わらない。reload は送らない）。sha256 が main と違うことを出す。3 回目の手動実行をし、ログが `DRIFT: monitoring/prometheus/alert_rules.yml`・`checked=6 drift=1` であることを出して報告を返す。Opus が 6 分以上たってから Alertmanager で `MonitoringConfigDrift` が出ていることを読む。
8-8. 戻す（Opus の合図の後）: 8-1 で取った控えではなく、8-4 の一時ディレクトリの main 版を `install -m` で置き直し、sha256 が main と一致することを出す（reload は送らない。中身は 8-4 と同じ）。4 回目の手動実行をし、ログが `checked=6 drift=0` であることを出す。Opus が数分後に `monitoring_config_drift_files` が 0 で、Alertmanager から `MonitoringConfigDrift` が消えたことを読む。
8-9. 8-7・8-8 の生出力も /tmp/CC報告ファイル/ai-ops-stage1-bin7/deploy/ に保存する。

§8 の分岐:
- 8-1 で本番と main（1 つ前）の sha256 が一致しない → 置かずに止まる（NEEDS_DECISION:）。
- 8-2 で 2 行が出ない → 止まる（BLOCKED:）。
- 8-3 で `gh workflow run` が権限で拒まれる → 止まる（BLOCKED:。拒まれた出力を貼る）。代わりに prod2 で直接スクリプトを動かすことはしない。
- 8-3 で run が failure → `gh run view <id> --log` の最後の 20 行を貼って止まる（BLOCKED:。秘密が出る行は伏せる）。
- 8-3 の結果が `drift=1` でない → ルールを置かずに止まる（NEEDS_DECISION:。ずれたファイル名を貼る）。
- 8-4 の promtool が落ちる → 置かずに止まる（BLOCKED:）。
- 8-5 で `health` が ok でないルールがある → 8-1 の控えに戻して読み直し、止まる（BLOCKED:）。
- 8-7 の後に鳴らない → 8-8 で戻してから報告する（ずらしたまま放置しない）。

## 9. 戻し方

- 順番は「prod2 のルールを外して読み直す → repo の revert → pushgateway の値を消す」。逆にして値を先に消すと、MonitoringConfigCheckStale が absent で 1 時間後に鳴る。
- prod2: 8-1 の控えを元の場所へ `install -m` で戻し、Prometheus に `POST /-/reload`。8-1 の控えは便6 の状態なので、後の便で alert_rules.yml が変わっていたら、控えではなく main の版（config_drift_alerts の 2 本を除いたもの）を置く。その版は revert の PR のブランチの `monitoring/prometheus/alert_rules.yml` を使い、置く前に同じ版の promtool で `check rules` を通す。8-7 のずらしが残っていたら、8-4 の一時ディレクトリの main 版で置き直す。
- repo: この PR の revert を main にマージする（workflow が消え、毎日の確認が止まる）。その後、prod2 で `curl -X DELETE http://127.0.0.1:9091/metrics/job/monitoring_config_drift` で pushgateway に残った値を消す（設計 §5。残すと古い値が出続ける）。

## 10. PR

- 作業場所: 便6 の実装 PR が main にマージされたことを `gh pr list --state merged --head release/ai-ops-stage1-bin6 --json number,state` で確かめてから（合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）、`cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/ai-ops-stage1-bin7 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-15 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin7` と `git worktree list` の両方で実在を確かめる。`ls docs/handoff/ai-ops-247/card-stage1-bin7.md` でこのカードが実在することを確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin7 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを `--body "$(cat 本文ファイル)"` の形で渡して作る。作成後に `gh pr list --head release/ai-ops-stage1-bin7 --json number,isDraft` で 1 件・isDraft が false を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。マージは Opus の GO 記録の後に限る（担当はマージしない）
- PR 本文に §8 の PO 原文と、本番で実行する操作の番号（8-1〜8-9）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く（`対象ADR:` は ADR-1012 だけ。ADR-029・ADR-1003 は設計 doc から参照されていないため、書くと関所が落ちる）。`区分:` は A（ADR-1015:16-23。`.github/` を触る新機能。PO 承認は §8 の PO 原文）、`Opus 審査記録:` は「コード審査はこれから（Fable の利用上限の間は PO の許可で Opus が代行）」と書く（審査の後に Opus が記録のパスに書き換える）。`設計仕様書（あるべき姿）:` は「対象外」。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
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
