# 実装カード 段階1 便6 — バックアップの鮮度の見張り

> この文書は何か：AI保守運用24時間化 段階1 便6 の作業指示書です。毎日 3:00 の DB バックアップ（`scripts/backup.sh`）と 3:30 の S3 への写し（`scripts/backup_to_s3.sh`）が、成功したら最後にその時刻を node-exporter の textfile に書くようにし、26 時間より古くなったら鳴る見張りを 3 本足します。動かない `scripts/setup_uptime_kuma.sh` を消します。本番の `scripts/` を触るので危険便です。本番への配置は §8 で、マージの後に行います（prod1 は通常の deploy と、確かめのための 1 回の手動実行。prod2 はルールの手作業の配置）。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便6・§6 受け入れ基準
- 事実確認の生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin6-recon/facts.md（Q1〜Q10。2026-10-15 Sonnet。repo は origin/main aca4b51bb・本番は読み取りのみ）
- 対象ADR: ADR-1012（本テーマ）・ADR-135・ADR-136（危険便）・ADR-1003（GO の委任）
- 状態: PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」・10-15 再送）に基づく実装便
- 前提: 便5 の実装 PR（release/ai-ops-stage1-bin5）が main にマージされ、本番に配置済みであること。このカードの PR（文書だけ）が main にマージされていること（§10 で確かめる）
- 危険便: はい（本番 `scripts/` を含む）。GO は ADR-1003 の委任の範囲で Opus が発行する（DROP を含む migration・データの大量 DELETE・secrets の変更・workflow の変更を含まない）。GO は ADR-1003:27-29 の 3 条件（CI 全通過・コード審査 APPROVE・PO への 3 行のまとめ（対象・変更内容・バックアップ確認））を満たした後に限る（担当の作業ではない）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable（利用上限の間は PO の許可で Opus が代行）／GO・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（バックアップの鮮度の見張りと、その時刻の書き込みだけ。動かないスクリプト 1 本の削除は設計 §2 便6 が同じ便に入れたもの） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§8-6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。backup.sh の 1 回は最大 81 秒・S3 は最大 37 秒・cron は毎日 1 回ずつ） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8 は prod1 が通常 deploy と無制限鍵での 1 回の手動実行、prod2 が無制限鍵） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便6 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `scripts/backup.sh` の最後（:59 の後）に、成功時刻を書く関数と呼び出し
2. `scripts/backup_to_s3.sh` の :157 と :159 の間に、成功時刻を書く関数と呼び出し
3. 新規 `scripts/tests/test-backup-timestamp.sh`（2 つのスクリプトから関数をそのまま取り出して試す）
4. `monitoring/prometheus/alert_rules.yml` に新しいグループ `backup_alerts`（3 本）
5. `monitoring/prometheus/tests/alert_rules_test.yml` に 3 本の試験
6. docs/runbooks/alerts.md に 3 節
7. `monitoring/tokens.yml` に閾値 1 行・for 2 行
8. `scripts/setup_uptime_kuma.sh` を `git rm`

入れない:
- バックアップ本体の処理（pg_dump・保持・S3 の転送・月次の Glacier）は 1 行も変えない
- `scripts/backup_to_s3.sh:56-72` の Discord 直通の失敗通知（残す。設計 §2 便6・U5）
- `.github/workflows/deploy.yml`（Pre-deploy DB backup の呼び出しは変えない）
- 新しい試験を CI で毎回走らせる workflow（workflow の変更になるため段階1 の範囲外。§13 の後に Opus が未解決事項に足す）
- root の crontab（【未確認】のまま。backup は ubuntu の crontab で動いていることは事実 F5）
- 既存の Prometheus 17 本と Loki 6 本

## 2. 前提の事実（facts.md の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | `scripts/backup.sh` は全 59 行。`set -euo pipefail` が :12。失敗は set -e による終了だけで、明示の exit は無い。成功は :58-59 の `Backup completed` の追記まで到達して終わる | Q1 |
| F2 | `scripts/backup_to_s3.sh` は全 159 行。`set -euo pipefail` が :40、`trap 'notify_failure' ERR` が :72、明示の `exit 1` が :99・:119・:155、完了の echo が :159 | Q2 |
| F3 | backup.sh の呼び出し元は cron（03:00 JST）と `.github/workflows/deploy.yml:191`（Pre-deploy DB backup。`db_migrations` のときだけ。`set -e` の中）。backup_to_s3.sh は cron（03:30 JST）だけ | Q3 |
| F4 | cron が読むのは `/home/ubuntu/salesanchor/scripts/` で、deploy が `git reset --hard origin/main`（deploy.yml:236）する作業ツリーそのもの。本番の 2 本は origin/main と sha256 一致。Pre-deploy の backup は reset より前に走る（そのデプロイでは旧版で動く）。`scripts/**` の変更は `db_migrations` の filter（deploy.yml:55-58）に当たらない | Q4・`.github/workflows/deploy.yml:38-58` |
| F5 | prod1 の ubuntu の crontab に backup.sh（03:00）・backup_to_s3.sh（03:30）・f2-cleanup.sh（日曜 04:00）がある | Q3 |
| F6 | textfile の置き場は prod1 の `/home/ubuntu/node_exporter_textfile`（ubuntu 所有・775）。node-exporter のコンテナに `/textfile:ro` で渡り、`--collector.textfile.directory=/textfile`。今の中身は `f2_cleanup.prom` だけ | Q5・`docker-compose.exporters.yml:11,17` |
| F7 | f2 の書き方は `scripts/f2-cleanup.sh:59-71` の `write_blackboard`（mktemp → 書く → chmod 644 → mv。失敗は `|| { log; return; }`） | Q5 |
| F8 | 本番 Prometheus は prod1 の node-exporter を instance=app-vps で読んでいる（up=1）。`f2_cleanup_last_success_timestamp{instance="app-vps"}` が実際に取れている。`node_textfile_scrape_error` は 0 | Q6・`monitoring/prometheus/prometheus.yml:25-32` |
| F9 | 1 回の所要は backup.sh が最大 81 秒、backup_to_s3.sh が最大 37 秒。cron の実行は backup.sh が 10-10〜10-15 の 6 日連続、S3 が 10-08〜10-15 の 8 日連続で、すべて成功（読めた範囲） | Q7 |
| F10 | `scripts/setup_uptime_kuma.sh` の参照は自身と docs だけ（workflow・scripts・monitoring・docker-compose・cron からの呼び出しは 0） | Q8 |
| F11 | 既存の F2CleanupStale・F2CleanupAbsent（`monitoring/prometheus/alert_rules.yml:120-139`）と試験（`monitoring/prometheus/tests/alert_rules_test.yml:190-226`）が、同じ textfile の時刻を見張る前例 | Q9 |
| F12 | `scripts/tests/` の bash の試験は CI で走っていない（`.github/workflows/` で `scripts/tests/test-backup-retention.sh` を呼ぶものは 0 件） | `git grep -n "scripts/tests/" origin/main -- .github/workflows`（2026-10-15 Opus） |

決めたこと:
- 書く場所: backup.sh は最後（:59 の後。後ろに失敗しうる行が無い）。backup_to_s3.sh は :157 の後・:159 の前（後ろは完了の echo だけ。月次の Glacier の失敗 :155 より後なので、月次が失敗した日は書かれない）。
- 指標とファイルは 2 本に分ける: `backup_local_last_success_timestamp`（`backup_local.prom`）と `backup_s3_last_success_timestamp`（`backup_s3.prom`）。f2 は `.prom` を丸ごと置き換えるので、同じファイルには書かない。同じ名前の指標を 2 つのファイルに置いたときの node-exporter の扱いは確かめていないので、名前も分ける。
- 書けなくてもバックアップは成功のまま終える（呼び出しを `|| true` にする）。理由: backup.sh はデプロイの `set -e` の中でも呼ばれ、非 0 にするとデプロイが落ちる。backup_to_s3.sh は ERR の trap があり、失敗が trap に届くと偽の Discord 失敗通知が出る。`||` の左側の関数の中では set -e も ERR の trap も効かない（bash の仕様。§5-4 の試験で実際に確かめる）。
- local の時刻はデプロイの Pre-deploy でも更新される（意味は「最後に dump が成功した時刻」）。S3 は cron だけ。
- 閾値: 26 時間（93600 秒）より古い状態が 10 分続いたら鳴る。根拠: cron は毎日 1 回（F5）、所要は最大 81 秒（F9）。1 日 1 回の成功なら差は最大で約 24 時間 2 分で、26 時間には届かない。1 回抜けると、抜けた回の約 2 時間後（最終成功から 26 時間 10 分）に鳴る。札は ticket（今は利用者に影響が無い。手順書に「翌営業日までに復旧」と書く。設計 §2 便6）。`severity` は warning（便5 と同じ決め方）。
- 時刻の系列そのものが無い: 30 時間続いたら鳴る（`BackupTimestampAbsent`）。30 時間は、配置から最初の cron（最大約 24 時間）までの空きを誤報にしない長さ。§8-5 の手動の 1 回は、本番の書き込み（権限・置き場・node-exporter の取り込み）を当日に確かめるためだけに行う。
- 設計 §2 便6（docs/handoff/ai-ops-247/stage1-design.md:131）の `BackupStale` 1 本を、Stale 2 本（どちらが止まったかを名前で分ける）と absent 1 本（系列が消えると Stale は鳴らないため。F2CleanupAbsent と同じ形）に分けた。設計本文との差は Opus が §13 の後に設計の未解決事項に書く。

## 3. 触るファイル（これ以外は触らない）

- 変更: `scripts/backup.sh`
- 変更: `scripts/backup_to_s3.sh`
- 新規: `scripts/tests/test-backup-timestamp.sh`
- 削除: `scripts/setup_uptime_kuma.sh`
- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin6.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. `scripts/backup.sh` の :59 の後に、空行 1 行と次を足す（完成形。コメントの言葉は変えてよいが、名前・パス・動きは変えない。`# shellcheck disable=SC2015` の行は消さない。4-2 も同じ）:

```bash
# 成功時刻を node-exporter の textfile に書く（ADR-1012 段階1 便6。見張り BackupLocalStale が読む）
# 書き方は scripts/f2-cleanup.sh の write_blackboard と同じ。書けなくてもバックアップは成功のまま終える
# （cron とデプロイの Pre-deploy DB backup を落とさない）
TEXTFILE_DIR="${BACKUP_TEXTFILE_DIR:-/home/ubuntu/node_exporter_textfile}"
write_success_timestamp() {
  local tmp
  mkdir -p "${TEXTFILE_DIR}" 2>/dev/null \
    || { echo "[$(date)] TEXTFILE mkdir FAIL" >> "${BACKUP_DIR}/backup.log"; return 0; }
  tmp=$(mktemp "${TEXTFILE_DIR}/.backup_local.XXXXXX") \
    || { echo "[$(date)] TEXTFILE mktemp FAIL" >> "${BACKUP_DIR}/backup.log"; return 0; }
  # shellcheck disable=SC2015  # && の連鎖のどこかが失敗したら右の後始末だけを動かす（意図どおり）
  {
    echo "# HELP backup_local_last_success_timestamp scripts/backup.sh last success unix time"
    echo "# TYPE backup_local_last_success_timestamp gauge"
    echo "backup_local_last_success_timestamp $(date +%s)"
  } > "${tmp}" && chmod 644 "${tmp}" && mv "${tmp}" "${TEXTFILE_DIR}/backup_local.prom" \
    || { rm -f "${tmp}"; echo "[$(date)] TEXTFILE write FAIL" >> "${BACKUP_DIR}/backup.log"; }
  return 0
}
write_success_timestamp || true
```

4-2. `scripts/backup_to_s3.sh` の :157（`fi`）の次に、空行 1 行と次を入れる（既存の :158 の空行はそのまま残し、その後ろが :159 の完了の echo になる。完成形。ログは標準出力。cron が s3_backup.log に追記する）:

```bash
# 6. 成功時刻を node-exporter の textfile に書く（ADR-1012 段階1 便6。見張り BackupS3Stale が読む）
# 書き方は scripts/f2-cleanup.sh の write_blackboard と同じ。書けなくても成功のまま終える
# （|| の左側の関数の中では set -e と ERR の trap が効かないので、偽の Discord 失敗通知を出さない）
TEXTFILE_DIR="${BACKUP_TEXTFILE_DIR:-/home/ubuntu/node_exporter_textfile}"
write_success_timestamp() {
  local tmp
  mkdir -p "${TEXTFILE_DIR}" 2>/dev/null || { echo "  WARN: TEXTFILE mkdir FAIL"; return 0; }
  tmp=$(mktemp "${TEXTFILE_DIR}/.backup_s3.XXXXXX") || { echo "  WARN: TEXTFILE mktemp FAIL"; return 0; }
  # shellcheck disable=SC2015  # && の連鎖のどこかが失敗したら右の後始末だけを動かす（意図どおり）
  {
    echo "# HELP backup_s3_last_success_timestamp scripts/backup_to_s3.sh last success unix time"
    echo "# TYPE backup_s3_last_success_timestamp gauge"
    echo "backup_s3_last_success_timestamp $(date +%s)"
  } > "${tmp}" && chmod 644 "${tmp}" && mv "${tmp}" "${TEXTFILE_DIR}/backup_s3.prom" \
    || { rm -f "${tmp}"; echo "  WARN: TEXTFILE write FAIL"; }
  return 0
}
write_success_timestamp || true
```

- 既存の行は 1 行も変えない（§5-3 で削除行数が 0 であることを確かめる）。

4-3. 新規 `scripts/tests/test-backup-timestamp.sh`（`scripts/tests/test-backup-retention.sh` と同じ書き方。`set -euo pipefail`・一時ディレクトリは `mktemp -d` と EXIT の trap・PASS/FAIL を echo・最後に FAIL があれば exit 1）。関数は書き写さず、2 本のスクリプトから `sed -n '/^write_success_timestamp() {$/,/^}$/p'` で取り出して `eval` で読み込む（スクリプトの関数そのものを試すため）。2 本それぞれについて試すこと:
- 手元の bash は 3.2（macOS）なので、`mapfile` など bash 4 以降の機能と GNU だけの `stat -c` は使わない。
1. 書ける: `TEXTFILE_DIR` と `BACKUP_DIR` を一時ディレクトリにして呼ぶ → `.prom` ファイルがあり、3 行目が指標名と数字で、数字が今の `date +%s` との差 5 秒以内。権限が 644（`[ "$(ls -l "$f" | cut -c1-10)" = "-rw-r--r--" ]` の形で確かめる）。一時ファイル（`.backup_*.` で始まるもの）が残っていない
2. 書けない: `TEXTFILE_DIR` を「普通のファイルの下のパス」（mkdir が必ず失敗する）にして、`set -euo pipefail` と `trap 'echo TRAPPED' ERR` を張ったサブシェルの中で `write_success_timestamp || true` の次の行に `echo AFTER` を置く → サブシェルの終了コード 0・出力に `AFTER` があり `TRAPPED` が無い。あわせて、同じ書けない条件で関数が自分で 0 を返すことを、試験全体を止めない次の形で確かめる: `rc=0; write_success_timestamp || rc=$?` → `rc` が 0 なら PASS、それ以外は FAIL を echo（§5-5 で壊して落とす相手）
3. 取り出せた: `sed` で取り出した関数の行数が 0 でない（取り出しの失敗で試験が空振りしないため）

4-4. `monitoring/prometheus/alert_rules.yml` の最後（便5 の `celery_alerts` グループの後）に、新しいグループを足す（完成形）:

```yaml
  - name: backup_alerts
    rules:
      # DB バックアップ（scripts/backup.sh）の最終成功から 26 時間（tokens.yml: backup_stale_sec=93600）
      # prod1 の node-exporter の textfile（backup_local.prom）を使用
      - alert: BackupLocalStale
        expr: (time() - backup_local_last_success_timestamp{instance="app-vps"}) > 93600
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "DB バックアップが 26 時間以上成功していません"
          description: "scripts/backup.sh の最終成功から {{ $value | humanizeDuration }} たちました（閾値: 26 時間）。翌営業日までに復旧してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#backuplocalstale"

      # S3 への写し（scripts/backup_to_s3.sh）の最終成功から 26 時間（tokens.yml: backup_stale_sec=93600）
      # prod1 の node-exporter の textfile（backup_s3.prom）を使用
      - alert: BackupS3Stale
        expr: (time() - backup_s3_last_success_timestamp{instance="app-vps"}) > 93600
        for: 10m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "S3 へのバックアップの写しが 26 時間以上成功していません"
          description: "scripts/backup_to_s3.sh の最終成功から {{ $value | humanizeDuration }} たちました（閾値: 26 時間）。翌営業日までに復旧してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#backups3stale"

      # 成功時刻の系列そのものが無い（textfile の断線・ファイルの消失）
      - alert: BackupTimestampAbsent
        expr: absent(backup_local_last_success_timestamp{instance="app-vps"}) or absent(backup_s3_last_success_timestamp{instance="app-vps"})
        for: 30h
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "バックアップの成功時刻が取れていません(app-vps)"
          description: "backup_local.prom か backup_s3.prom の時刻が 30 時間取れていません。textfile の置き場と 2 つのファイルの有無を確認してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#backuptimestampabsent"
```

4-5. `monitoring/prometheus/tests/alert_rules_test.yml` の最後に 3 本の試験を足す。promtool は入力の系列が test group ごとなので、入力ごとに group を分ける（下の 1〜3 で計 7 group: Stale 2 本×「古い」「正常」・Absent の「無い」「2 本ともある」「local だけある」）（他の試験は変えない。冒頭のコメントの「全 17 本」は「全 20 本」に直す）。`time()` は 0 から始まる（F2CleanupStale の注記と同じ）:
1. BackupLocalStale 鳴る: `backup_local_last_success_timestamp{instance="app-vps"}` が `-100000+0x30`（interval 1m）で `eval_time` 15m に 1 件（`exp_labels` は instance・severity・tier）。鳴らない（for より前）: 同じ入力で `eval_time` 5m に 0 件。鳴らない（正常）: `0+60x30` で `eval_time` 20m に 0 件
2. BackupS3Stale: 1 と同じ形で `backup_s3_last_success_timestamp`
3. BackupTimestampAbsent 鳴る: 無関係の系列 `up{job="dummy", instance="x"}` を `1x1900` だけ置いて `eval_time` 31h に 1 件（`exp_labels` は instance・severity・tier）。鳴らない（for より前）: 同じ入力で `eval_time` 29h に 0 件。鳴らない（2 本ともある）: 2 本の系列を `0+60x1900` で置いて `eval_time` 31h に 0 件。鳴る（local だけある）: `backup_local_last_success_timestamp{instance="app-vps"}` だけを `0+60x1900` で置いて `eval_time` 31h に 1 件（`or` の片側だけ欠けた場合）
- description の展開後の文字列は `promtool test rules --diff` の got 側から写してよい（便3 カード §6 と同じ扱い）。

4-6. docs/runbooks/alerts.md に 3 節を足す（あわせて冒頭 :3 の「Prometheus 17 本」を「20 本」に直す）。見出しは `## BackupLocalStale`・`## BackupS3Stale`・`## BackupTimestampAbsent`。5 項目（札・何が起きているか・最初に見るもの・直し方・止め方）の形は既存のまま。書くこと:
- 3 節とも: 札 ticket。「利用者に今の影響は無い。翌営業日までに復旧する」。止め方は既存と同じ `amtool silence add alertname=… --duration=PERIOD --comment=REASON` の形。
- BackupLocalStale: 何が起きているか（毎日 3:00 の `scripts/backup.sh` が 26 時間以上成功していない。デプロイの Pre-deploy DB backup の成功でも時刻は進む）。最初に見るもの: prod1 の `/home/ubuntu/backups/postgres/backup.log` の末尾（成功の行と `TEXTFILE ... FAIL` の行）、`/home/ubuntu/backups/cron.log`（失敗の出力先）、ubuntu の crontab。直し方: 失敗の原因（postgres のコンテナ・ディスクの空き）を切り分けて Opus に報告する。手動で 1 回実行してよい（`bash /home/ubuntu/salesanchor/scripts/backup.sh`）。
- BackupS3Stale: 何が起きているか（毎日 3:30 の `scripts/backup_to_s3.sh` が 26 時間以上成功していない。毎月 1 日は Glacier への月次の保存の失敗でも成功時刻が書かれない）。最初に見るもの: `/home/ubuntu/backups/s3_backup.log` の末尾（`ERROR`・`WARN: TEXTFILE` の行）、Discord の ops チャンネルの「S3バックアップ失敗」の通知。直し方: AWS の認証・S3 の応答・ローカルのバックアップの有無を切り分けて Opus に報告する。
- BackupTimestampAbsent: 何が起きているか（2 本のどちらかの時刻が 30 時間取れていない）。最初に見るもの: prod1 の `/home/ubuntu/node_exporter_textfile/` に `backup_local.prom` と `backup_s3.prom` があるか、`node_textfile_scrape_error{instance="app-vps"}`、backup.log の `TEXTFILE ... FAIL` の行。直し方: 断線の箇所を切り分けて Opus に報告する。
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

4-7. `monitoring/tokens.yml`:
- `thresholds:` の `# ログ異常検知` の段の前（便5 の celery の段の後）に、空行と次の段を足す:

```yaml
  # バックアップの鮮度（alert_rules.yml: backup_alerts）
  # scripts/backup.sh・scripts/backup_to_s3.sh が prod1 の textfile に書く *_last_success_timestamp を使用
  backup_stale_sec:         93600  # BackupLocalStale / BackupS3Stale: time() - 成功時刻 > 93600（26h）
```

- `for_durations:` の最後に足す:

```yaml
  backup_stale:      "10m"  # BackupLocalStale / BackupS3Stale
  backup_absent:     "30h"  # BackupTimestampAbsent
```

4-8. `git rm scripts/setup_uptime_kuma.sh`。消す前に `git grep -n "setup_uptime_kuma" -- . ':!docs/'` の出力を報告に貼る（期待: 自身の :16 の 1 行だけ）。docs の中の言及（履歴の記録）は直さない。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-0. 始めに `mkdir -p /tmp/CC報告ファイル/ai-ops-stage1-bin6/deploy` を実行する。`docker info` が失敗したら `colima start` を実行してから §5-6 に進む（手元の colima は自動停止で止まっていることがある）。

5-1. 作業場所で `python3 -c "import yaml; [print(g['name'], r['alert'], r.get('for'), r['labels']) for g in yaml.safe_load(open('monitoring/prometheus/alert_rules.yml'))['groups'] for r in g['rules']]"` を実行し、`git show origin/main:monitoring/prometheus/alert_rules.yml > /tmp/CC報告ファイル/ai-ops-stage1-bin6/rules-main.yml` の版に対しても同じ 1 行を実行して `diff` に通す（期待: 足された 3 行（backup_alerts の 3 本）だけが違う）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 20 rules, Loki 6 rules, runbook 26 sections`。
5-3. `git diff --numstat origin/main -- monitoring/prometheus/alert_rules.yml scripts/backup.sh scripts/backup_to_s3.sh` の出力（期待: 3 行とも 2 列目（削除行数）が 0。足すだけ）と、`git diff origin/main --summary -- scripts/backup.sh scripts/backup_to_s3.sh` の出力（期待: 空。mode change が無い。cron は 2 本を直に実行するので 755 が落ちるとバックアップが止まる）。
5-4. `bash scripts/tests/test-backup-timestamp.sh` の出力全文と終了コード（期待 0・FAIL の行 0）。あわせて `bash -n scripts/backup.sh` と `bash -n scripts/backup_to_s3.sh` の終了コード（期待 0）。`shellcheck` が手元にあれば 2 本に対して実行し、出力を貼る（無ければ「無い」と書く。完成形には SC2015 の無効化の行を入れてあるので、足した行に当たる指摘は 0 の想定。足した行に指摘が出たら、完成形の動きは変えずに出力を貼るだけにする。既存の行の指摘は直さない。`scripts/backup_to_s3.sh` は既存の :91 の SC2012（info）で shellcheck の終了コードが 1 になる。origin/main の版でも同じなので、それは失敗と扱わない）。
5-5. わざと壊して落ちることを確かめる（一時的な書き換え。確かめたら `git checkout -- <file>` で戻し、`git diff --stat` で戻ったことを出す）: `scripts/backup.sh` の関数の中の mkdir の失敗の側の `return 0` を `return 1` に変える。§4-3 の試験 2 は呼び出しを `|| true` で包むので、この書き換えだけでは落ちない。そこで試験 2 に「関数を `|| true` 無しで呼んだときの終了コードが 0」の確かめを足しておき（§4-3 の 2 の追加の確かめとして書く）、その確かめが落ちることを見る。`bash scripts/tests/test-backup-timestamp.sh` の出力（期待: FAIL の行が 1 行以上）と終了コード 1 を貼る。
5-6. 本番と同じ版のイメージ（`prom/prometheus:v3.11.3`）で `promtool check rules`（期待 "SUCCESS: 20 rules found"）と `promtool test rules`（期待 "SUCCESS"）を実行し、出力と終了コードを貼る（`-v` が効かなければ `docker create` → `docker cp` → `docker start -a`）。
5-7. わざと壊して落ちることを確かめる: BackupLocalStale の `> 93600` を `> 936000` にすると、§4-5 の試験 1 の「鳴る」が落ちる。`promtool test rules` の出力と終了コード 1 を貼り、戻す。
5-8. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「不一致」の行（期待: 不一致 0）。このスクリプトは backup_* を照合しないので、値の一致は §5-1 の出力と tokens.yml の 3 行を並べて報告に貼って示す。
5-9. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md` の該当が 0 行（版の番号の形に当たった行は、その行を貼って IP でないことを書く）。
5-10. `git diff origin/main --stat` が §3 のファイルであること（削除 1 を含む。§13 の追記前なら 8 ファイル、追記後なら 9 ファイル）。

## 6. 分岐ごとの対処

- 5-1〜5-3・5-8〜5-10 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-4 の試験が落ちる → §4-1・§4-2 の完成形と一字ずつ比べて直す。完成形の動き（`|| true`・`return 0`）を変えて合わせることはしない。3 回直しても通らなければ出力を貼って BLOCKED:。
- 5-6 で promtool の test が落ちる → 試験の期待値（展開後の文字列など）を直してやり直す。§4-4 の式・for・閾値を変えて合わせることはしない。3 回直しても通らなければ出力を貼って BLOCKED:。
- 4-8 の `git grep` で docs 以外の参照が見つかる → 消さずに止まる（NEEDS_DECISION:）。
- 前提の便5 の実装 PR がマージされていない → 作業を始めずに止まる（BLOCKED:）。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → 便3 カード §6 と同じく `quay.io` の同じ版に替えてよい。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 見張り 3 本が §4-4 の完成形で入り、既存の 17 本は変わらない | §5-1・§5-3 |
| 3 本とも鳴るときに鳴り、鳴らないときに鳴らない（単体試験） | §5-6・§5-7・PR の CI |
| 札・手順書リンク・見出しの検査が通る（20 本・26 節） | §5-2 |
| 時刻が書けないときもバックアップは成功のまま終わり、ERR の trap に届かない | §5-4・§5-5 |
| 2 本のスクリプトの既存の行が変わっていない | §5-3 |
| 本番の 2 本のスクリプトが main と sha256 一致 | §8-1 |
| 本番 Prometheus で 2 つの時刻の系列が出て、26 時間より新しい | §8-6 |
| 本番の Prometheus に 3 本が入り、評価の失敗が無い | §8-6 |
| 本番のルールファイルが main と sha256 一致 | §8-4 |
| 翌日 3:00・3:30 の cron で 2 つの時刻が進む | 配置の翌日 4:00 以降に Opus が 2 つの指標の値を読み、その日の 3:00〜3:35 JST の範囲にあることを確かめる |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

機体は 2 つ。prod1 は main へのマージで動く通常の deploy（`.github/workflows/deploy.yml`）でスクリプトが入れ替わる。8-5 の手動実行だけは prod1 に無制限鍵 `~/.ssh/manual-only/id_ed25519` で入って行う。prod2 はルールの手作業の配置で、SSH は制限付き鍵で書けないため無制限鍵を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md・reference_prod_server_config.md。本番で行う操作は下の 8-1〜8-7 だけ。Loki・Alertmanager・tokens.yml は本番に配らない。

8-1. prod1 の deploy の確認（読み取り）: マージの commit の deploy の run が success であること（`gh run list --workflow deploy.yml --limit 3 --json headSha,conclusion,createdAt`）。prod1 の `git -C /home/ubuntu/salesanchor log -1 --oneline` がマージの commit であること、`/home/ubuntu/salesanchor/scripts/backup.sh` と `backup_to_s3.sh` の sha256 が main と一致すること、`/home/ubuntu/salesanchor/scripts/setup_uptime_kuma.sh` が無いこと、`stat -c '%a %n' /home/ubuntu/salesanchor/scripts/backup.sh /home/ubuntu/salesanchor/scripts/backup_to_s3.sh` が 2 本とも 755 であること。deploy の run がまだ終わっていなければ、その状態を報告して終える（待たない）。
8-2. 控え: `/opt/salesanchor-monitoring/backups/ai-ops-stage1/` に、prod2 の本番の `alert_rules.yml` を `cp -p` で `.bak-20261015-` に PR 番号を付けた名前で写し、元と控えの sha256 を出す。あわせて本番のファイルが、この PR のマージ commit の 1 つ前の版と同じであることを出す（`MC=$(gh pr view PR --json mergeCommit -q .mergeCommit.oid)` → `git fetch origin && git show "$MC^1":monitoring/prometheus/alert_rules.yml | sha256sum`。PR は便6 の実装 PR の番号）。一致しなければ止まる。
8-3. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-ai-ops-bin6/` を作り、main の `monitoring/prometheus/alert_rules.yml` を scp で送る。同じ版の promtool で `check rules` を通す（"SUCCESS: 20 rules found"）。
8-4. 本番の場所に `install -m` で元と同じ権限で置き、本番のファイルと main の sha256 が一致することを出す。Prometheus のコンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送り、終了コードを出す。一時ディレクトリは消さない（削除はフックに止められる）。中身の一覧（`ls -la`）だけ出す。
8-5. prod1 で 1 回だけ手動で実行し、2 つの系列を作る（本番の書き込み（権限・置き場・node-exporter の取り込み）を当日に確かめるため。cron やデプロイの backup と同じ処理で、1 日に何回も動いている（F9: デプロイ経由が 6 日で 19 回））。件数の保持（`scripts/backup.sh:44-54`）で、最も古いローカルの控えが 1 本消える（デプロイ経由と同じ動き）。始める前に次の 4 つを出し、1 つでも当たれば実行せずに止まり、報告を返す（Opus が時刻をずらして依頼し直す）:
  - JST の時刻が 02:30〜04:30 の間（cron と日曜 04:00 の f2-cleanup と重ねない）
  - JST の日付が 01 日（`scripts/backup_to_s3.sh:139-157` が Glacier の月次保存をもう 1 本作るため）
  - `gh run list --workflow deploy.yml --limit 3 --json status,conclusion,createdAt` に in_progress か queued がある（deploy の作業ツリーの入れ替えと重ねない）
  - `whoami` が ubuntu でない（cron と同じ利用者で動かす）
  当たらなければ、cron と同じ出力先に追記して実行する:
  - `cd /home/ubuntu/salesanchor && bash scripts/backup.sh >> /home/ubuntu/backups/cron.log 2>&1; echo rc=$?`
  - `cd /home/ubuntu/salesanchor && TZ=Asia/Tokyo bash scripts/backup_to_s3.sh >> /home/ubuntu/backups/s3_backup.log 2>&1; echo rc=$?`
  - その後に `ls -la /home/ubuntu/node_exporter_textfile/`・2 つの `.prom` の中身（3 行ずつ）・`tail -n 3 /home/ubuntu/backups/postgres/backup.log`・`tail -n 12 /home/ubuntu/backups/s3_backup.log` を出す（webhook の URL が出る行があれば伏せる）
8-6. 読み取りで次を出す（待ちに sleep は使わず、1 回目で揃わなければ報告を返し、続きは Opus が依頼する）:
  - Prometheus の `/api/v1/rules`: ルール数（期待 20）・`tier` が無いルール（期待 0 件）・`tier` ごとの数（期待 page 6・ticket 14）・`health` が ok でないルールの数（期待 0）・`backup_alerts` の 3 本の名前
  - Prometheus の `/api/v1/query`: `backup_local_last_success_timestamp{instance="app-vps"}`・`backup_s3_last_success_timestamp{instance="app-vps"}` の値と、それぞれの `time() - …` の値（期待: 8-5 の実行時刻に一致し、差が 3600 未満）・`node_textfile_scrape_error{instance="app-vps"}`（期待 0）・`f2_cleanup_last_success_timestamp{instance="app-vps"}`（f2 の値が消えていないこと）
  - Alertmanager の `/api/v2/alerts` の alertname と `tier` の一覧
8-7. 生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin6/deploy/ に保存する。

§8 の分岐:
- 8-1 で deploy が failure、または sha256 が一致しない → 手動実行も prod2 の配置もせずに止まる（BLOCKED:）。
- 8-2 で本番と main（1 つ前）の sha256 が一致しない → 置かずに止まる（NEEDS_DECISION:）。
- 8-3 の promtool が落ちる → 置かずに止まる（BLOCKED:）。
- 8-5 で `rc` が 0 でない → もう一度は実行しない。ログの末尾を貼って止まる（BLOCKED:）。バックアップの失敗は本番の事故なので、Opus がすぐ PO に報告する。
- 8-5 で `rc=0` なのに `.prom` が無い → 止まる（BLOCKED:）。backup.log と s3_backup.log の `TEXTFILE` の行を貼る。
- 8-6 で `health` が ok でないルールがある → 8-2 の控えに戻して読み直し、止まる（BLOCKED:）。
- 8-6 で backup の見張りが鳴っている → 戻さない。値を報告する（Opus が判断する）。

## 9. 戻し方

- prod2: 8-2 の控えを元の場所へ `install -m` で戻し、Prometheus に `POST /-/reload`。
- repo と prod1: この PR の revert を main にマージして deploy（スクリプトが元に戻り、`scripts/setup_uptime_kuma.sh` も戻る）。prod1 に残る `backup_local.prom`・`backup_s3.prom` は、ルールが無くなれば害は無い。消すかどうかは PO に確かめる。バックアップ本体の処理は、この便の前後で変わらない。

## 10. PR

- 作業場所: 便5 の実装 PR が main にマージされたことを `gh pr list --state merged --head release/ai-ops-stage1-bin5 --json number,state` で確かめてから（合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）、`cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/ai-ops-stage1-bin6 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-15 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin6` と `git worktree list` の両方で実在を確かめる。`ls docs/handoff/ai-ops-247/card-stage1-bin6.md` でこのカードが実在することを確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin6 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを `--body "$(cat 本文ファイル)"` の形で渡して作る。作成後に `gh pr list --head release/ai-ops-stage1-bin6 --json number,isDraft` で 1 件・isDraft が false を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。危険便なので、マージは Opus の GO 記録の後に限る（担当はマージしない）
- PR 本文に §8 の PO 原文と、本番で実行する操作の番号（8-1〜8-7）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし。`削除するファイル:` には `scripts/setup_uptime_kuma.sh` と、行を書き換えた既存ファイルを全部書く（`validate-pr-body.sh` の規則）
- 本文に IP・URL の秘密・鍵のパス・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-10 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（2026-10-15 Sonnet。§8 は未実施。マージ後に Opus の合図を受けて行う）

- 受領: 本報告はカード 段階1 便6 の実行結果である。便5 の実装 PR #4308 は MERGED を確認（`gh pr list --state merged --head release/ai-ops-stage1-bin5`）。
- §5-1: 足された 3 行（backup_alerts の 3 本）だけが違う。
- §5-2: `OK: Prometheus 20 rules, Loki 6 rules, runbook 26 sections`（exit 0）。
- §5-3: 削除行数は 3 ファイルとも 0（追加 40・21・19）。`--summary` は空（mode change 無し）。
- §5-4: 試験 ALL PASSED（FAIL 0・exit 0）。`bash -n` 2 本とも 0。shellcheck は `scripts/backup.sh` が exit 0、`scripts/backup_to_s3.sh` は既存 :91 の SC2012（info）のみ。
- §5-5: mkdir 側の `return 0` を `return 1` にすると、試験が FAIL 1 行・exit 1 で落ちた。戻して `--numstat` で追加のみに復帰。
- §5-6: `SUCCESS: 20 rules found`／`test rules` SUCCESS（exit 0）。展開後の description（`1d 4h 1m 40s`）は got 側から写した。
- §5-7: 閾値を 936000 にすると BackupLocalStaleFiring が FAILED（exit 1）。戻した。
- §5-8: exit 0・不一致 0。§5-9: 該当 0 行。
- 生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin6/

END OF CARD
