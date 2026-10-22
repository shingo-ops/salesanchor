# 実装カード 便1 — 時計ずれの警報と、その間の誤警報の抑止

> この文書は何か：outage-recovery-watch 便1 の作業指示書です。本番サーバーの時計が 60 秒以上ずれたら鳴る警報 `ClockSkew` と、時刻合わせが止まったら鳴る警報 `ClockSyncStopped` を足します。`ClockSkew` が鳴っている間は、時刻を比べる 7 本の警報を Alertmanager で止めます（2026-10-22 のさくらメンテの後、prod1 の時計が約 40 分遅れ、誤警報が 3 件鳴ったため）。本番への配置は §8 で、マージの後に Opus が PO の同意票を受けて行います。

- 設計: docs/handoff/outage-recovery-watch/design.md §1 G3・§3-3・受け入れ基準
- recon: docs/handoff/outage-recovery-watch/recon.md
- 事実確認の生出力:
  - /tmp/CC報告ファイル/outage-bin1-facts2/（Q1〜Q10。2026-10-22 Sonnet。repo は origin/main・本番は読んでいない）
  - ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/prevention/u1u2/（時計の指標 3 つの実測）
  - ~/CC報告ファイル-keep/v102-shipdate-range/routine/20261022_1200/outage/prevention/bin1-facts/alert_rules.yml（ルール全文の写し）
- 対象ADR: ADR-1012（AI保守運用24時間化。通知経路の正本は Alertmanager）
- 状態: 設計は PO 承認済み（2026-10-22 PO 返信「1」）。PO の「これを対策」「つぎを進める」（2026-10-22）と GO 委任に基づく実装便
- 前提: このカードの PR（文書だけ）が main にマージされていること（§10 で確かめる）
- 危険便: いいえ（触るのは `monitoring/`・`docs/` だけ。`migrations/`・`deploy.yml`・`scripts/`・`.github/` を触らない）
- 担当: 実装と配置台本の下書きは Sonnet、コード審査は Opus（reviewer）、GO・マージ・本番配置・反映確認は Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（時計ずれの警報 2 本と、その間の抑止だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§5-6。件数とルール名・警報名を対で出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。今は 27 本・手順書 33 節・時刻合わせは両機とも 1） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8 は prod2 だけ。担当は本番に接続しない。配置は Opus が同意票を受けて行う） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード outage-recovery-watch 便1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/prometheus/alert_rules.yml` に新しいグループ `clock_alerts`（2 本）
2. `monitoring/prometheus/tests/alert_rules_test.yml` に 2 本の試験
3. `monitoring/alertmanager/alertmanager.yml` に `inhibit_rules`（1 本）
4. `monitoring/scripts/check_alert_rules.py` に「抑止の対象の警報名が実在するか」の検査
5. `docs/runbooks/alerts.md` に 2 節
6. `monitoring/tokens.yml` に閾値 1 行・for 2 行
7. 本番配置の台本（リポジトリの外 `/tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh`。commit しない。§8）

入れない:
- 復旧後の点検係（便2）とメールの見張り（便3）
- 時計を自動で直す仕組み（設計 §2 で対象外）
- `.github/workflows/monitoring-check.yml` などの workflow（抑止の名前の検査は既存の `check_alert_rules.py` の step（monitoring-check.yml:59-61）が CI で動かす）
- 既存の 27 本のルールの式・for・札
- alertmanager.yml の route と receivers
- 本番への接続（担当は prod1・prod2 に接続しない）

## 2. 前提の事実（facts2 の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | Prometheus のルールは今 27 本（8 グループ）。最後のグループは `container_state_alerts` | bin1-facts/alert_rules.yml・alert_rules_test.yml:4「全 27 本」 |
| F2 | 時刻を比べる 7 本（式の行）: :121 F2CleanupStale・:184 CeleryHeartbeatStale・:222 ViewerInventoryStale・:233 ViewerInventoryStaleOnHold・:248 BackupLocalStale・:261 BackupS3Stale・:327 ContainerStateStale。7 本に共通の札は無い（CeleryHeartbeatStale・ViewerInventoryStale・ViewerInventoryStaleOnHold は `job="backend"`、他は `instance="app-vps"` 等） | bin1-facts/alert_rules.yml |
| F3 | `node_time_seconds`・`node_timex_offset_seconds`・`node_timex_sync_status` は app-vps・mgmt-vps とも値がある。2026-10-22 の測定で sync_status は両機とも 1、offset は両機とも 1 ミリ秒未満 | u1u2/q_node_timex_sync_status.json・q_node_timex_offset_seconds.json |
| F4 | 2026-10-22 の障害の後、`node_time_seconds - timestamp(node_time_seconds)` は app-vps で -2436.7 秒だった | prom_skew.txt |
| F5 | alertmanager.yml は 25 行。`inhibit_rules` は無い。group_wait 30s・group_interval 5m・repeat_interval 4h。受け手は discord-server-alerts（:12）と ops-api（:16、送り先は本番 API） | facts2 Q1 |
| F6 | 版は Prometheus `prom/prometheus:v3.11.3`（compose :5）、Alertmanager `prom/alertmanager:v0.28.1`（compose :177）。CI も同じ版（monitoring-check.yml:70-88） | facts2 Q2・Q7 |
| F7 | Prometheus は設定をディレクトリでマウント（compose :12 `./monitoring/prometheus:/etc/prometheus:ro`）。Alertmanager は設定をファイル 1 本でマウント（compose :179）。データの保存場所は無い（:178-181 の 3 行だけ） | Opus 2026-10-22（`grep` で確認） |
| F8 | `check_alert_rules.py` の成功時の出力は `OK: Prometheus {N} rules, Loki {M} rules, runbook {K} sections`（:79-82）。失敗時は `NG: ...` を出し、最後に `FAILED: {n} errors` を出して exit 1（:74-78）。tier・runbook_url・見出しを検査し、severity は検査しない | facts2 Q5 |
| F9 | 手順書の見出しは 33 節。:3 は「Prometheus 27 本」。各節の形は `- 札：`・`- 何が起きているか：`・（`- 影響：`）・`- 最初に見るもの：`・`- 直し方：`・`- 止め方：` | facts2 Q4 |
| F10 | `validate_tokens.py` は thresholds の 4 キーだけを照合し、for_durations は照合しない | facts2 Q6 |
| F11 | Alertmanager の inhibit は「source に当たる警報が 1 つ以上ある間、target に当たる警報を止める」。`equal` は任意で、`equal` に挙げた札が source と target の両方に無ければ当たる。source と target の両方に当たる警報は抑止されない。そのため、両方に当たらない matcher を選ぶよう勧められている | 公式 https://prometheus.io/docs/alerting/latest/configuration/ の inhibit_rule の節（2026-10-22 Opus が WebFetch で確認。Context7 は月の上限で使えなかった） |

決めたこと:
- `ClockSkew` の式は、設計 §3-3 のとおり `abs(node_time_seconds{job="node-exporter"} - timestamp(node_time_seconds{job="node-exporter"})) > 60` とし、for は 2m、札は critical/page にする。
  - 右辺の `timestamp()` は、Prometheus（prod2）が値を読み取った時刻。
  - そのため、この式が見るのは「各機体の時計と prod2 の時計の差」。
  - prod2 自身の時計が正しい時刻からずれても、この式では見えない（prod2 の差はいつもほぼ 0）。prod2 のずれは `ClockSyncStopped` で見る。手順書に書く。
- `ClockSyncStopped` は `node_timex_sync_status{job="node-exporter"} == 0` が 10m 続いたら warning/ticket で鳴らす。今は両機とも 1（F3）なので、配置しても鳴らない。
- 抑止は `equal` を付けず、target を警報名の並びで指定する（F2 に共通の札が無いため）。
  - `equal` を付けない理由: どちらの時計がずれても、「prod1 が書いた時刻」と「prod2 の `time()`」の比較が狂う。札を揃えて相手を絞る意味が無い。
  - target の名前の並びは、`check_alert_rules.py` で実在を確かめる。将来ルール名が変わったときに、抑止が黙って外れることを CI で止めるため。
- 抑止の source（ClockSkew）と target（7 本）は名前が重ならないので、F11 の「両方に当たる」には当たらない。
- 抑止の試験は promtool ではできない。代わりに、本番と同じ版の Alertmanager を手元で外部通信なし（`--network none`）で起動し、疑似の警報を入れて `inhibitedBy` を読む（§5-7）。本番の Alertmanager には疑似の警報を入れない（Discord と障害記録に残るため）。
- 閾値は tokens.yml に足す（F10 のとおり照合はされないが、既存便と揃える）。

## 3. 触るファイル（これ以外は触らない）

- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `monitoring/alertmanager/alertmanager.yml`
- 変更: `monitoring/scripts/check_alert_rules.py`
- 変更: `monitoring/tokens.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/outage-recovery-watch/card-bin1.md`（このカード。§13 報告欄の追記のみ）
- リポジトリの外（commit しない）: `/tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh`・`/tmp/CC報告ファイル/outage-bin1/deploy/rollback-bin1.sh`

## 4. 作り方

4-1. `monitoring/prometheus/alert_rules.yml` の最後（`container_state_alerts` グループの後）に、新しいグループを足す（完成形。他の行は変えない）:

```yaml
  - name: clock_alerts
    rules:
      # 各機体の時計と、Prometheus（prod2）が値を読み取った時刻の差が 60 秒超（tokens.yml: clock_skew_sec=60）
      # 2026-10-22 のさくらメンテの後、prod1 が約 40 分遅れて時刻を比べる警報が誤って鳴った（outage-recovery-watch 便1）
      # この警報が鳴っている間、時刻を比べる 7 本は alertmanager.yml の inhibit_rules で止める
      - alert: ClockSkew
        expr: abs(node_time_seconds{job="node-exporter"} - timestamp(node_time_seconds{job="node-exporter"})) > 60
        for: 2m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "サーバー {{ $labels.instance }} の時計が 60 秒以上ずれています"
          description: "{{ $labels.instance }} の時計と監視サーバーの時計の差が {{ $value | humanizeDuration }} です。この間、時刻を比べる警報（裏方の処理が止まった等）は止めています。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#clockskew"

      # 時刻合わせ（NTP）が止まった。ずれる前の兆候
      - alert: ClockSyncStopped
        expr: node_timex_sync_status{job="node-exporter"} == 0
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "サーバー {{ $labels.instance }} の時刻合わせが止まっています"
          description: "{{ $labels.instance }} で時刻合わせ（NTP）が 10 分以上同期していません。このままだと時計がずれ、時刻を比べる警報が誤って鳴ります。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#clocksyncstopped"
```

4-2. `monitoring/alertmanager/alertmanager.yml` の最後（`receivers:` の段の後）に足す（完成形。既存の 25 行は変えない）:

```yaml

inhibit_rules:
  # ClockSkew が鳴っている間は、時刻を比べる 7 本を止める（outage-recovery-watch 便1・design.md §3-3）
  # equal は付けない: どちらの機体の時計がずれても「prod1 が書いた時刻」と「prod2 の time()」の比較が狂うため
  # target の名前は monitoring/scripts/check_alert_rules.py が alert_rules.yml に実在するかを確かめる
  - source_matchers:
      - alertname="ClockSkew"
    target_matchers:
      - alertname=~"F2CleanupStale|CeleryHeartbeatStale|ViewerInventoryStale|ViewerInventoryStaleOnHold|BackupLocalStale|BackupS3Stale|ContainerStateStale"
```

4-3. `monitoring/scripts/check_alert_rules.py` に検査を 1 つ足す（形は既存の検査に合わせる。既存の検査と出力文言は変えない）:
- `monitoring/alertmanager/alertmanager.yml` を読む（パスは既存のファイルの決め方に合わせる）。
- `inhibit_rules` の各ルールについて、`source_matchers`・`target_matchers` の各要素を調べる。`alertname="名前"` か `alertname=~"名前|名前|…"`（名前は英数字だけ）の形なら、名前を取り出す。
- 取り出した名前が Prometheus と Loki のルール名のどれにも無ければ、`inhibit_rules[i] の alertname が見つかりません: 名前` を既存のエラーの一覧に足す（一覧には接頭辞を付けない。出すときに既存の処理（:76）が `NG: ` を付ける）。
- `alertname` の matcher で、上の 2 つの形に当たらないもの（正規表現に記号がある等）も `inhibit_rules[i] の alertname を読めません: 元の文字列` を一覧に足す（読めないものは止まる側に倒す）。
- `alertname` 以外の matcher は見ない。`inhibit_rules` が無いときは何もしない。
- 成功時の出力 1 行（F8）は変えない。
- 既存の試験の置き場所に `check_alert_rules.py` の試験があれば、そこへ 1 件足す（名前が実在しない場合に exit 1）。無ければ足さず、§5-5 のわざと壊す確認で代える（報告に「試験の置き場所は無い」と書く）。

4-4. `monitoring/prometheus/tests/alert_rules_test.yml`（他の試験は変えない。:4 の「全 27 本」を「全 29 本」に直す）。最後に足す。入力ごとに test group を分ける。promtool の `timestamp()` は、試験の中の値の時刻（0 から 1m おき）になる。
1. ClockSkew 鳴る（遅れ）: `node_time_seconds{job="node-exporter", instance="app-vps"}` を `'-2436+60x30'`（interval 1m。値と読み取り時刻の差がいつも -2436 秒）。`eval_time` 5m で 1 件（`exp_labels` は job・instance・severity・tier）。同じ入力で `eval_time` 1m は 0 件（for より前）。
2. ClockSkew 鳴る（進み・境目の上）: `'61+60x30'` で `eval_time` 5m に 1 件。
3. ClockSkew 鳴らない（境目の下）: `'59+60x30'` で `eval_time` 5m に 0 件。
4. ClockSkew 鳴らない（ずれ無し）: `'0+60x30'` で `eval_time` 5m に 0 件。
5. ClockSyncStopped 鳴る: `node_timex_sync_status{job="node-exporter", instance="mgmt-vps"}` を `'0x30'` で `eval_time` 15m に 1 件（`exp_labels` は job・instance・severity・tier）。同じ入力で `eval_time` 5m は 0 件。
6. ClockSyncStopped 鳴らない: `'1x30'` で `eval_time` 15m に 0 件。
- description の展開後の文字列は、`promtool test rules --diff` の got 側から写してよい（便3 カード §6 と同じ扱い）。

4-5. `docs/runbooks/alerts.md`（:3 の「Prometheus 27 本」を「29 本」に直す）。最後に `## ClockSkew`・`## ClockSyncStopped` の 2 節を足す。形は F9 のとおり。書くこと:
- ClockSkew:
  - 札：page
  - 何が起きているか：その機体の時計と監視サーバーの時計の差が 60 秒を超えた。さくらのメンテや機体の再起動の後に起きうる（2026-10-22 に prod1 が約 40 分遅れた）。
  - 影響：時刻を比べる警報 7 本（F2CleanupStale・CeleryHeartbeatStale・ViewerInventoryStale・ViewerInventoryStaleOnHold・BackupLocalStale・BackupS3Stale・ContainerStateStale）は、この警報の間 Alertmanager で止めている。止めている間、それらの本物の停止にも気づけない。DB に書く時刻もずれる。
  - 最初に見るもの：Grafana か Prometheus で `node_time_seconds - timestamp(node_time_seconds)` を機体ごとに見る。`node_timex_sync_status` が 1 か。
  - 直し方：時刻合わせが動いていれば数分で自然に直る（2026-10-22 は約 11 分）。直らなければ Opus に報告する（時計を手で直す操作は本番の変更なので PO の判断）。
  - prod2 自身の時計のずれはこの警報では見えない（差はいつもほぼ 0）。prod2 は ClockSyncStopped で見る。
  - 止め方：`amtool silence add alertname=ClockSkew --duration=PERIOD --comment=REASON`
- ClockSyncStopped:
  - 札：ticket
  - 何が起きているか：その機体で時刻合わせが 10 分以上同期していない。
  - 影響：今は無いが、続くと時計がずれ、ClockSkew と誤警報が起きる。
  - 最初に見るもの：`node_timex_sync_status` と `node_timex_offset_seconds` を機体ごとに見る。
  - 直し方：Opus に報告する（時刻合わせの設定の変更は本番の変更なので PO の判断）。
  - 止め方：`amtool silence add alertname=ClockSyncStopped --duration=PERIOD --comment=REASON`
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

4-6. `monitoring/tokens.yml`:
- `thresholds:` の中で、:95 の行の後・:97 のログ異常検知の段の前に、空行と次の段を足す（作業の前に `sed -n '90,101p' monitoring/tokens.yml` で場所を確かめ、行番号がずれていれば段の並びで合わせる）:

```yaml
  # 時計ずれ（alert_rules.yml: clock_alerts）
  clock_skew_sec: 60  # ClockSkew: abs(node_time_seconds - timestamp(node_time_seconds)) > 60
```

- `for_durations:` の最後（:125 `config_check_stale` の後）に足す:

```yaml
  clock_skew:         "2m"   # ClockSkew
  clock_sync_stopped: "10m"  # ClockSyncStopped
```

4-7. 本番配置の台本（リポジトリの外。commit しない）`/tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh` を Write で作る。担当は実行しない（実行は Opus が PO の同意票を受けて行う）。
- 接続方法（機体 prod2・利用者名・鍵のパス）はメモリの reference_vps_monitor_access.md から写す。推測で利用者名を書かない（fail2ban に当たる）。無ければ台本を作らずに NEEDS_DECISION:。
- 引数は 1 つ: 実装 PR のマージ commit の sha。`set -euo pipefail`。生出力は `/tmp/CC報告ファイル/outage-bin1/deploy/` に `tee` で残す。秘密（webhook・token の値）は出さない。
- 手順（この順。外れたらその場で止まり、以降を行わない）:
  1. prod2 の本番の `monitoring/prometheus/alert_rules.yml` と `monitoring/alertmanager/alertmanager.yml` の sha256 が、マージ commit の 1 つ前（`git show "${MC}^1":パス`）と一致することを出す。違えば止まる。
  2. 控え: `/opt/salesanchor-monitoring/backups/outage-bin1/` に 2 本を `cp -p` で `.bak-` に日付を付けた名前で写し、sha256 を出す。
  3. Alertmanager の今の silence の数（コンテナの中の `amtool --alertmanager.url=http://localhost:9093 silence query -q` の行数）と、鳴っている警報の数（`/api/v2/alerts` の件数と alertname の一覧）を出す。どちらかが 1 以上なら止まる（F7: データの保存場所が無いので、作り直すと silence と送信の記録が消える。鳴っている警報があると Discord と ops-api にもう一度届く）。
  4. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-outage-bin1/` に、マージ commit の版の 2 本を scp で送る。
  5. 同じ版のイメージで検査する: `docker run --rm --entrypoint promtool -v 一時ディレクトリ:/w:ro prom/prometheus:v3.11.3 check rules /w/alert_rules.yml`（期待 "SUCCESS: 29 rules found"）と、`--entrypoint amtool ... prom/alertmanager:v0.28.1 check-config /w/alertmanager.yml`。amtool の検査は、受け手のファイル参照（webhook・token）が一時ディレクトリに無いことで落ちるかもしれない。その場合は、実在する secrets のディレクトリを読み取り専用で同じパスにマウントして通す（値は出さない）。どちらか落ちたら止まる。
  6. 2 本を `install -m 644` で本番の場所に置き、本番のファイルとマージ commit の版の sha256 が一致することを出す。
  7. Prometheus: コンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送る（F7: ディレクトリのマウントなので読み直しで足りる）。
  8. Alertmanager: `docker compose -f docker-compose.monitoring.yml up -d --force-recreate alertmanager`（F7: ファイル 1 本のマウントは、`install` で置き換えると中のコンテナに古い中身が見えたままになる。そのため作り直す）。`/-/ready` が 200 になるまで、最大 12 回・5 秒おきに確かめる（台本の中の待ちはこれだけ）。
  9. 読み取りで確かめて出す:
     - Prometheus `/api/v1/rules`: ルール数（期待 29）、`clock_alerts` の 2 本の名前と `health`（期待 ok）、`health` が ok でないルールの数（期待 0）。
     - Prometheus `/api/v1/query`: `abs(node_time_seconds{job="node-exporter"} - timestamp(node_time_seconds{job="node-exporter"}))` の機体ごとの値（期待 60 未満）、`node_timex_sync_status{job="node-exporter"}` の機体ごとの値（期待 1）。
     - Alertmanager `/api/v2/status` の `config.original` に `inhibit_rules` と `ClockSkew` の語があるか（出すのは語の有無だけ。設定の全文は出さない）。
     - Alertmanager `/api/v2/alerts` の alertname と状態の一覧。silence の数（手順 3 と同じ数）。
- 一時ディレクトリは消さない（削除はフックに止められる）。中身の一覧（`ls -la`）だけ出す。
- 戻し方の台本 `/tmp/CC報告ファイル/outage-bin1/deploy/rollback-bin1.sh` も同じ形で作る（手順 2 の控えを `install -m 644` で戻す → Prometheus を読み直す → Alertmanager を作り直す → 9 と同じ確認）。
- 2 本とも `bash -n` が通ることを §5-9 で出す。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 作業場所で `python3 -c "import yaml; [print(g['name'], r['alert'], r.get('for'), r['labels']) for g in yaml.safe_load(open('monitoring/prometheus/alert_rules.yml'))['groups'] for r in g['rules']]"` を実行する。`git show origin/main:monitoring/prometheus/alert_rules.yml > /tmp/CC報告ファイル/outage-bin1/rules-main.yml` の版にも同じ 1 行を実行し、`diff` に通す（期待: 足された 2 行（clock_alerts の 2 本）だけが違う）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 29 rules, Loki 6 rules, runbook 35 sections`。Loki の本数が 6 でなければ、main の版での実行結果と並べて貼る（Loki は変えていないので main と同じ数なら合格）。
5-3. `git diff --numstat origin/main -- monitoring/prometheus/alert_rules.yml monitoring/alertmanager/alertmanager.yml` の出力（期待: 2 本とも 2 列目（削除行数）が 0。足すだけ）。
5-4. 本番と同じ版のイメージで `promtool check rules`（期待 "SUCCESS: 29 rules found"）と `promtool test rules`（期待 "SUCCESS"）を実行し、出力と終了コードを貼る（`-v` が効かなければ `docker create` → `docker cp` → `docker start -a`）。`prom/alertmanager:v0.28.1` の `amtool check-config monitoring/alertmanager/alertmanager.yml` も同じく実行する（CI と同じ形。monitoring-check.yml:77-81 を見て合わせる）。`config routes test` も CI と同じ 2 回（monitoring-check.yml:83-88）を実行する。
5-5. わざと壊して落ちることを確かめる（一時的な書き換え。確かめたら `git checkout -- <file>` で戻し、`git diff --stat` で戻ったことを出す）:
  - alertmanager.yml の target の `ContainerStateStale` を `ContainerStateStaleX` にすると、`check_alert_rules.py` が `NG: inhibit_rules[0] の alertname が見つかりません: ContainerStateStaleX` を出して exit 1。
  - ClockSkew の `> 60` を `> 6000` にすると、§4-4 の試験 1 が落ちる。`promtool test rules` の出力と終了コード 1 を貼る。
5-6. 手順書の見出しを数える: `grep -c '^## ' docs/runbooks/alerts.md`（期待 35）と、`grep -n '^## Clock' docs/runbooks/alerts.md`（期待 ClockSkew・ClockSyncStopped の 2 行）。
5-7. 抑止の確かめ（手元・外部通信なし）:
  - `/tmp/CC報告ファイル/outage-bin1/am-test/secrets/` に `discord-webhook`（中身 `http://127.0.0.1:9/dummy` の 1 行）と `ops-ingest-token`（中身 `dummy` の 1 行）を Write で作る（本物の値は使わない。参照先は alertmanager.yml:14・:25 の `/etc/alertmanager/secrets/` の 2 本）。
  - ファイルはマウントせず、`docker cp` で中に入れる（Docker は colima で動いており、colima が見せるのは $HOME だけで /tmp は見えないため）。次の順に実行する:
    - `docker create --rm --name outage-bin1-am --network none prom/alertmanager:v0.28.1 --config.file=/etc/alertmanager/alertmanager.yml --cluster.listen-address=`
    - `docker cp monitoring/alertmanager/alertmanager.yml outage-bin1-am:/etc/alertmanager/alertmanager.yml`（作業場所から）
    - `docker cp /tmp/CC報告ファイル/outage-bin1/am-test/secrets outage-bin1-am:/etc/alertmanager/secrets`
    - `docker start outage-bin1-am`
  - `--network none` は必ず付ける（ops-api の送り先は本番 API のため）。`--cluster.listen-address=`（値は空）も必ず付ける（v0.28.1 は既定で仲間探しの機能を 0.0.0.0:9094 で開こうとし、`--network none` では自分の IP が見つからず起動に失敗するため。空にするとこの機能が切れる）。
  - 起動の直後に `docker ps --filter name=outage-bin1-am --format '{{.Names}} {{.Status}}'` を出し、1 行あることを確かめる（無ければ `--rm` で消えている。上の 4 つを `--rm` 無しでやり直して `docker logs outage-bin1-am` を貼り、BLOCKED:。その場合の後始末は `docker stop` だけでよい）。
  - `api/v2/alerts` の読み取りは `docker exec outage-bin1-am wget -q -O- http://127.0.0.1:9093/api/v2/alerts` の出力を、手元（Mac）の `python3` にパイプで渡して 3 列にする（イメージの中に python3 は無い）。
  - 段 1（ClockSkew なし）: コンテナの中の amtool（`--alertmanager.url=http://127.0.0.1:9093`）で `alert add` を送る。送るのは 3 本: `alertname=CeleryHeartbeatStale job=backend severity=critical`、`alertname=ContainerStateStale instance=app-vps job=node-exporter severity=critical`、比べ役の `alertname=ServiceDown job=backend severity=critical`。コンテナの中から `wget -q -O- http://127.0.0.1:9093/api/v2/alerts` を読み、`python3` で alertname・`status.state`・`status.inhibitedBy` の 3 列にして出す（期待: 3 本とも active・inhibitedBy は空）。
  - 段 2（ClockSkew あり）: `alertname=ClockSkew instance=app-vps job=node-exporter severity=critical` を足して、同じ 3 列を出す（期待: CeleryHeartbeatStale と ContainerStateStale は suppressed で inhibitedBy が 1 件、ServiceDown と ClockSkew は active）。
  - 最後に `docker stop outage-bin1-am`（`--rm` なので消える）と、`docker ps -a --filter name=outage-bin1-am --format '{{.Names}}'` が空であることを出す。
5-8. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「閾値ズレ」の行（期待: exit 0・閾値ズレ 0 行）。値の一致は、`grep -n -A1 "alert: Clock" monitoring/prometheus/alert_rules.yml` の式の行（閾値 60）と §5-1 の for の値を、tokens.yml の 3 行と並べて報告に貼って示す。
5-9. `bash -n /tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh` と `bash -n /tmp/CC報告ファイル/outage-bin1/deploy/rollback-bin1.sh` の終了コード（期待 0）。台本 2 本の全文を報告に貼る（鍵のパスと利用者名は伏せずに貼ってよい。秘密の値は台本に書かない）。
5-10. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md monitoring/alertmanager/alertmanager.yml` の該当（期待: 0 行。版の番号の形に当たった行は、その行を貼って IP でないことを書く）。
5-11. `git diff origin/main --stat` が §3 のリポジトリ内のファイルであること（§13 の追記前なら 6 ファイル、追記後なら 7 ファイル）。

## 6. 分岐ごとの対処

- 5-1〜5-3・5-6・5-8〜5-11 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-4 で promtool の test が落ちる → 試験の期待値（展開後の文字列・札）を直してやり直す。§4-1 の式・for・閾値を変えて合わせることはしない。3 回直しても通らなければ、出力を貼って BLOCKED:。
- 5-4 で amtool の check-config が落ちる → 出力を貼って BLOCKED:（§4-2 の書き方を自分で変えない）。
- 5-7 で段 2 の 2 本が suppressed にならない → 出力を貼って BLOCKED:（§4-2 を自分で変えない）。
- 作業の最初に `docker version` が接続できない → `colima start` を 1 回だけ実行してから（`>` などの書き先を付けずにそのまま実行する。書き先を付けると見張り mac-vm-guard が別の起動と読んで止める） `docker version` をもう一度出す（Docker は colima で動かす。2026-10-22 の審査の時点では止まっていた）。それでも動かなければ、5-4・5-7 を飛ばさずに BLOCKED:。
- reference_vps_monitor_access.md に接続方法が無い → 台本を作らずに NEEDS_DECISION:。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → 便3（ai-ops-247）カード §6 と同じく `quay.io` の同じ版に替えてよい。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 警報 2 本が §4-1 の完成形で入り、既存の 27 本は変わらない | §5-1・§5-3 |
| ClockSkew は 60 秒超のずれ（遅れ・進みとも）が 2 分続くと鳴り、59 秒・ずれ無し・2 分より前は鳴らない。ClockSyncStopped は同期 0 が 10 分続くと鳴る（単体試験） | §5-4・§5-5・PR の CI |
| ClockSkew の間、時刻を比べる警報が止まり、ServiceDown は止まらない | §5-7 |
| 抑止の対象の名前が消えたり変わったりすると CI が止める | §5-5・PR の CI（monitoring-check.yml:59-61） |
| 札・手順書リンク・見出しの検査が通る（29 本・35 節） | §5-2・§5-6 |
| 本番の Prometheus に 2 本が入って評価の失敗が無く、今は両機とも鳴っていない | §8（台本の手順 9） |
| 本番の Alertmanager が抑止の設定を読み込み、silence の数が変わらない | §8（台本の手順 9） |

## 8. 本番への配置（マージの後。Opus が行う。担当はしない）

- 機体は prod2 だけ。制限付き鍵では書けないため無制限鍵を使う。無制限鍵は、PO の同意票（ADR-1033）を受けた Opus だけが使う。担当は使わない。
- 8-1. Opus が台本 `deploy-bin1.sh` を読み、§4-7 と合うか確かめる。
- 8-2. Opus が PO に同意票 `操作1: bash /tmp/CC報告ファイル/outage-bin1/deploy/deploy-bin1.sh マージcommitのsha` を出す。
- 8-3. PO の「1」を受けて Opus が実行し、生出力を `/tmp/CC報告ファイル/outage-bin1/deploy/` に残す。
- 8-4. 手順 9 の結果を PR にコメントで追記する。
- マージから配置までの間に、毎日の設定ずれの見回り（monitoring-config-drift.yml:8、日本時間 09:23）を過ぎると、設定ずれの警報 MonitoringConfigDrift（warning）が 1 件鳴る（check_config_drift.sh:19・:22 が 2 本を見ているため）。Opus はマージをこの時刻の前に配置まで終えられる時間に行う。鳴った場合は配置の後の次の見回りで消えることを確かめる。
- 本番の Alertmanager に疑似の警報は入れない（§2 決めたこと）。抑止の動きの確かめは §5-7 で代える。本物で確かめられるのは次に時計がずれたとき。そのときは Opus が、時刻を比べる警報が Discord に届かなかったことを記録する（設計「継続」）。

§8 の分岐:
- 手順 1 で sha256 が一致しない → 置かずに止まる（Opus が PO に報告）。
- 手順 3 で silence か鳴っている警報が 1 以上 → 置かずに止まる（作り直すと silence が消え、警報がもう一度届くため。Opus が時間を置いてやり直すか PO に報告）。
- 手順 5 の検査が落ちる → 置かずに止まる。
- 手順 9 で `health` が ok でないルールがある、または `/-/ready` が 200 にならない → `rollback-bin1.sh` を同意票で出し直して戻す。

## 9. 戻し方

- prod2: `rollback-bin1.sh`（§4-7。控えの 2 本を戻し、Prometheus を読み直し、Alertmanager を作り直す）。無制限鍵を使うので、同意票を受けて Opus が実行する。
- repo: この PR の revert を main にマージする。
- 戻すと、時計がずれたときに再び誤警報が鳴る状態に戻る（10/22 以前と同じ）。

## 10. PR

- 作業場所: このカードの PR が main にマージされたことを `gh pr list --state merged --head release/outage-bin1-card --limit 1 --json number,state` で確かめる（合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）。その後 `cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/outage-clock-skew-alert --claude`（origin/main 起点）を実行する。
  - 出力はパイプに通さない。
  - 最後に「Input must be provided」と出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-22 実測）。
  - 作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-outage-clock-skew-alert` と `git worktree list` の両方で実在を確かめる。
  - `ls docs/handoff/outage-recovery-watch/card-bin1.md` でこのカードが実在することを確かめる。
  - 以後の作業はすべてその作業場所に `cd` してから行う。
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/outage-clock-skew-alert -1 --oneline` で実在を確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイルを作り、`--body "$(cat 本文ファイル)"` の形で渡す。作成後に `gh pr list --head release/outage-clock-skew-alert --limit 1 --json number,isDraft` で 1 件・isDraft が false を確かめる。
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
- PR は ready で作る（`--draft` を付けない）。base は main。マージは Opus の審査と GO 記録の後に限る（担当はマージしない）。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` には次を書く:
  - recon（docs/handoff/outage-recovery-watch/recon.md）・設計（docs/handoff/outage-recovery-watch/design.md）・このカード
  - `対象ADR:` は ADR-1012
  - `設計仕様書（あるべき姿）:` は docs/specs/ai-ops-247/README.md
  - `区分:` は A（ADR-1015:16。新機能。PO 承認は設計の PO 承認 2026-10-22「1」と「つぎを進める」）
  - `Opus 審査記録:` は「コード審査はこれから」（審査の後に Opus が書き換える）
  - `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には、行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
- 本文に、§8 の本番配置はマージ後に Opus が同意票を受けて行うことを書く。台本はリポジトリの外にあり commit しないことも書く。
- 本文に IP・URL の秘密・鍵のパス・利用者名・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（2 分以上かかるので timeout を長めにする）。

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-11 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う。§4-7 の台本の中の `/-/ready` の確認だけは例外で、台本は担当が実行しない）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
