# 実装カード 段階1 便1 — 鳴らす条件を repo と本番で一致させる（Loki・Grafana）

> この文書は何か：AI保守運用24時間化 段階1 便1 の作業指示書です。Loki のルールの名前の重複を直して本番と同じ形にし、本番で退避済みの Grafana の通知設定を repo からも消します。本番への配置は §8 で、マージの後に行います。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便1・§1 S5〜S8・S14・S23・S24
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階1-5・7(a)(c)（:95・:98・:100）
- 対象ADR: ADR-1012（本テーマ）
- 状態: 設計は再審査 APPROVE（stage1-design.md・Fable 2026-10-14）。PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」）に基づく実装便
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable／マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（鳴らす条件の一致のみ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2・§8） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（6 本＝本番 4 本＋Discord 2 本） | ○ |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り。commit・push・PR 作成の各段で実在を確かめる | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§5-2・§5-4・§8 は prod2・無制限鍵） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/loki/rules/jarvis/alerts.yml` の 2 つ目の `error_anomaly` グループ（postgres のログを見るルール）を、名前を `DatabaseError` に変えて 1 つ目の `error_anomaly` グループへ移す
2. `monitoring/grafana/provisioning/alerting/alerting.yml` を削除する

入れない:
- ルールの条件式・閾値・ラベルの変更（便3・便4）
- Prometheus のルール（便2〜）
- ダッシュボード JSON と `generate-nav.js` の本番とのずれ（stage1-design.md U3）

## 2. 前提の事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | repo の Loki ルールは 6 本。同名ルール `BackendErrorSpike` が :32 と :69、同名グループ `error_anomaly` が :29 と :66 | `monitoring/loki/rules/jarvis/alerts.yml` |
| F2 | 本番の同ファイルは「repo から discord_gateway グループ（:42-64 付近）を除き、postgres 版を 1 つ目の error_anomaly に `DatabaseError` として入れたもの」。本番で評価中は 4 本 | /tmp/CC報告ファイル/ai-ops-stage1-recon2/prod2/ の diff（B2_loki_rules.diff）・B3b_loki_metrics.txt |
| F3 | 本番の Grafana の alerting は空。repo の alerting.yml と同じ中身が本番で退避済み | recon2 facts B1・B7 |
| F4 | Loki の ruler は `local` 置き場で `/loki/rules` を読み、`/tmp/loki/rules` に写して評価する | `monitoring/loki/loki-config.yaml:32-36` |

## 3. 触るファイル（これ以外は触らない）

- 変更: `monitoring/loki/rules/jarvis/alerts.yml`
- 削除: `monitoring/grafana/provisioning/alerting/alerting.yml`
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin1.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. `monitoring/loki/rules/jarvis/alerts.yml` で、1 つ目の `error_anomaly` グループの `BackendErrorSpike`（backend のログ）の直後に、2 つ目のグループにある postgres のルールを移す。移すときに `- alert: BackendErrorSpike` を `- alert: DatabaseError` に、その直前のコメントを `# PostgreSQLエラーログ検知` に変える。条件式・for・labels・annotations は 1 文字も変えない。
4-2. 空になった 2 つ目の `- name: error_anomaly` と `rules:` の行を消す。
4-3. 完成形の形（グループの並び）: `auth_anomaly`（2 本）→ `error_anomaly`（`BackendErrorSpike`・`DatabaseError` の 2 本）→ `discord_gateway`（2 本）。
4-4. `monitoring/grafana/provisioning/alerting/alerting.yml` を `git rm` する。その前に、このファイル名を参照している箇所を `git grep -n "provisioning/alerting"` で出して報告に貼る（参照が `docker-compose.monitoring.yml` のディレクトリ丸ごとのマウント以外にあれば、§6 の分岐）。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `cd` で作業場所に入り `python3 -c "import yaml,sys; d=yaml.safe_load(open('monitoring/loki/rules/jarvis/alerts.yml')); print([ (g['name'], [r['alert'] for r in g['rules']]) for g in d['groups']])"` の出力が次と一致すること:
`[('auth_anomaly', ['BruteForceAttempt', 'SustainedAuthFailure']), ('error_anomaly', ['BackendErrorSpike', 'DatabaseError']), ('discord_gateway', ['DiscordGatewayReconnectFailure', 'DiscordDmWriterError'])]`
5-2. 本番の同ファイルとの差を取る: 本番の `/opt/salesanchor-monitoring/monitoring/loki/rules/jarvis/alerts.yml` を読み取り（cat のみ）で /tmp/CC報告ファイル/ai-ops-stage1-bin1/prod2-alerts-before.yml に保存し、`diff` を取る。期待: 差は `discord_gateway` グループの追加だけ。差の全文をファイルに保存し、差に含まれる `alert:` の名前を列挙して報告する。
5-3. `git diff origin/main --stat` が 2 ファイル（alerts.yml 変更・alerting.yml 削除）であること。
5-4. Discord の 2 本が入った途端に鳴り続けないかの事前測定（本番の Loki に読み取りの問い合わせだけ）: 2 本の条件式（`sum(count_over_time(...))`）を、本番の Loki の `/loki/api/v1/query_range`（step 5m、直近 7 日）で問い合わせ、閾値（3 と 5）を超えた点の数と最初・最後の時刻をルールごとに記録する。生の応答は /tmp/CC報告ファイル/ai-ops-stage1-bin1/ に保存。

## 6. 分岐ごとの対処

- 5-1 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-2 の差に discord_gateway 以外の変化がある → その差を報告に貼る。直せる（自分の編集のずれ）なら直す。本番側に repo に無い変更があるなら作業を止めて NEEDS_DECISION: で報告。
- 4-4 でディレクトリのマウント以外の参照がある → 参照箇所を報告して止まる（NEEDS_DECISION:）。
- 5-4 で超えた点が 1 日あたり平均 12 点（5 分刻みで 1 時間分）を超える → PR は作るが、報告の 1 行目を NEEDS_DECISION: にして数字を書く（配置するかは Opus が決める）。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| Loki のルール名とグループ名の重複が 0 | §5-1 の出力 |
| repo と本番の差は Discord の 2 本の追加だけ | §5-2 の diff |
| repo から Grafana の通知設定が消え、本番（退避済み）と一致 | §5-3 |
| 配置後、本番 Loki が 6 本を評価し評価失敗 0 | §8 の ruler 指標 |
| 配置後 1 時間、Loki の再起動 0 回・OOM なし | §8 の docker inspect |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

SSH は制限付き鍵で書けないため無制限鍵 `~/.ssh/manual-only/id_ed25519` を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md・reference_prod_server_config.md。本番で行う操作は下の 8-1〜8-6 だけ。

8-1. 控え: `cp -p` で `alerts.yml` を同じディレクトリに `alerts.yml.bak-20261014-` に PR 番号を付けた名前で写す。Grafana の provisioning の alerting は本番で既に空なので触らない。
8-2. main の `monitoring/loki/rules/jarvis/alerts.yml` を scp で一時ファイルとして送り、本番の場所に置く（`install -m` で元と同じ権限）。
8-3. 本番のファイルと main の sha256 が一致することを出力する。
8-4. Loki の ruler 指標（Loki の `:3100/metrics` の `loki_ruler_` で始まる行のうち `jarvis` を含むもの）を 1 分ごとに最大 5 回読み、グループ 3 つ・ルール計 6 本になった時刻を記録する。5 回で 6 本にならなければ `docker compose -f docker-compose.monitoring.yml restart loki` を 1 回だけ行い、もう一度 5 回読む。それでもならなければ 8-1 の控えを戻して止まる（BLOCKED:）。
8-5. 6 本になってから 1 時間後に、Loki の `docker inspect` の `RestartCount`・`OOMKilled`・`docker stats --no-stream` のメモリ欄を記録する。待ちは担当がしない（8-4 までで報告を返し、1 時間後の記録は Opus が別に依頼する）。
8-6. 生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin1/deploy/ に保存する。

## 9. 戻し方

- 本番: 8-1 の控えを `alerts.yml` に戻す。Loki は自動で読み直す（読み直さなければ restart loki）。
- repo: この PR の revert。

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage1-bin1 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出ることがあるが、作業場所の作成とは無関係（2026-10-14 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin1` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin1 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを渡して作る。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage1-bin1 --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main
- PR 本文に §8 の PO 原文と、本番で実行した操作の番号（8-1〜8-6 のうち実行したもの）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし（良い例: 触るファイル: monitoring/loki/rules/jarvis/alerts.yml, docs/handoff/ai-ops-247/card-stage1-bin1.md ／禁止形: 箇条書き・改行・バッククォート付き）
- 本文に IP・URL の秘密・鍵のパスを書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力（5-4 は数字の表）／PR の URL／生出力のパス／判断を要した点（事実のみ）
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
