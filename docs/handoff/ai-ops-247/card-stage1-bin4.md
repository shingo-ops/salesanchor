# 実装カード 段階1 便4 — 遅さの見張り BackendHighLatency の条件の決め直し

> この文書は何か：AI保守運用24時間化 段階1 便4 の作業指示書です。14 日で 393 回鳴っていた見張り BackendHighLatency の条件を、「死活確認の口 /api/health を除いた利用者のリクエストのうち、2.5 秒を超えたものが 5% を超える状態が 5 分続いたら鳴らす」に変えます。閾値の正本 `monitoring/tokens.yml`・単体試験・手順書も同じ値にそろえます。本番への配置は §8 で、マージの後に行います。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便4（PO 決定 2026-10-15 の追記を含む）・§6 受け入れ基準
- 事実確認の生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin4-recon/facts.md（Q1〜Q11。2026-10-15 Sonnet。prod2 読み取りのみ）・同 decision.md
- 対象ADR: ADR-1012（本テーマ）
- 状態: 条件と合格基準の直しは PO 決定済み（2026-10-15「Y」）。PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」）に基づく実装便
- 前提: 便3 の実装 PR が main にマージされ、本番に配置済みであること（このカードは便3 で入る `tier`・`runbook_url`・単体試験・手順書を前提にする）。このカードの PR（文書だけ）が main にマージされていること（§10 で `ls` により実在を確かめる）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable／マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（BackendHighLatency 1 本の条件のみ。他のルールは変えない） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§8-5） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（14 日 393 回・新条件 1 回） | ○（§2） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り。commit・push・PR 作成の各段で実在を確かめる | ○（§10） |
| guards/08-vps.md | どの機体・どの鍵かをカードに書く | ○（§8 は prod2・無制限鍵） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便4 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/prometheus/alert_rules.yml` の BackendHighLatency（直前のコメント行を含む）の expr・for・summary・description
2. `monitoring/tokens.yml` の `backend_p99_latency_sec` の 1 行を、新しい閾値の 2 行に置き換える
3. `monitoring/prometheus/tests/alert_rules_test.yml`（便3 で作られたもの）の BackendHighLatency の試験を新しい条件に合わせ、「/api/health だけが遅いときは鳴らない」試験を足す
4. docs/runbooks/alerts.md（便3 で作られたもの）の `## BackendHighLatency` の節の中身

入れない:
- BackendHighLatency の `severity`（warning のまま）・`tier`（ticket のまま）・`runbook_url`（page に上げるかは設計の未解決事項 U10）
- 他の 13 本の Prometheus ルールと Loki の 6 本
- `/api/health` が毎回 1〜2.5 秒かかる原因の調査と修正（設計の未解決事項 U9）
- `backend/app/metrics.py`（指標の出し方は変えない）
- `monitoring/scripts/validate_tokens.py`・`monitoring/scripts/check_alert_rules.py`（検査の仕組みは変えない）

## 2. 前提の事実（facts.md の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 今の式は `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="backend"}[5m])) by (le)) > 2.0`・`for: 2m`・`severity: warning` | `monitoring/prometheus/alert_rules.yml:111-118`（origin/main 4c9d037ef。便2・便3 のマージ後は行番号が変わるため、ルール名で探す） |
| F2 | 14 日（10-01〜10-15）で実際に鳴った回数は 393 回。今の条件を 60 秒刻みで再現すると 386 回 | Q5・Q9 |
| F3 | `/api/health` の 14 日の 6451 件はすべて 1.0〜2.5 秒の区間に入る。P99 は区間の中の補間で 2.485 付近に張り付き、2.0 を常に超える | Q8 |
| F4 | 採用する条件「/api/health を除き 2.5 秒を超えた割合 > 0.05 が 5 分続く」は 14 日で 1 回（10-12 13:20・/api/v1/conversations） | Q11・decision.md |
| F5 | 今の条件で 5xx・Kuma 失敗と同時刻だった回（10-01）は、/api/health を除いて数えると 0 回。重なった回は /api/health の補間で鳴っていた | Q9 (g) |
| F6 | 指標のラベル名は `handler` と `status`。`le` の境界は 0.005〜10 で、2.5 はあり 2.0 は無い。`http_request_duration_seconds_count` は本番に存在する | Q3・Q4・Q10 |
| F7 | `monitoring/tokens.yml:80` は `backend_p99_latency_sec: 2.0`。`validate_tokens.py` はこの値を検査していない（`grep -n 'p99\|latency' monitoring/scripts/validate_tokens.py` が 0 件。2026-10-15 Opus が実行） | `monitoring/tokens.yml:80` |
| F8 | 利用者のリクエストが 0 件の 5 分（夜間など）は割り算の分母が 0 になり、結果は値なし（NaN）になる。NaN は `> 0.05` を満たさないので鳴らない | Prometheus の演算の仕様（`0/0` は NaN・比較は偽） |

## 3. 触るファイル（これ以外は触らない）

- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `monitoring/prometheus/tests/alert_rules_test.yml`
- 変更: `docs/runbooks/alerts.md`
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin4.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. `monitoring/prometheus/alert_rules.yml` の BackendHighLatency を次の完成形にする（`tier`・`runbook_url` の 2 行は便3 で入った値をそのまま残す）:

```yaml
      # FastAPI バックエンドの遅いリクエストの割合（/api/health を除く。tokens.yml: backend_slow_request_sec=2.5・backend_slow_ratio=0.05）
      - alert: BackendHighLatency
        expr: (1 - (sum(rate(http_request_duration_seconds_bucket{job="backend",handler!="/api/health",le="2.5"}[5m])) / sum(rate(http_request_duration_seconds_count{job="backend",handler!="/api/health"}[5m])))) > 0.05
        for: 5m
        labels:
          severity: warning
          tier: ticket
        annotations:
          summary: "バックエンドの遅いリクエストの割合が高い"
          description: "/api/health を除くリクエストのうち 2.5 秒を超えた割合が {{ $value | humanizePercentage }} です（閾値: 5%・5 分継続）"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#backendhighlatency"
```

- 変えるのはコメント 1 行・expr・for・summary・description の 5 行だけ。ルール名・severity・tier・runbook_url は変えない（§5-3 で確かめる）。

4-2. `monitoring/tokens.yml` の `backend_p99_latency_sec: 2.0` の 1 行を、次の 2 行に置き換える（桁そろえは周りの行に合わせる）:

```yaml
  backend_slow_request_sec: 2.5  # BackendHighLatency: 2.5 秒を超えたリクエストを「遅い」と数える（/api/health を除く）
  backend_slow_ratio:       0.05 # BackendHighLatency: 遅いリクエストの割合 > 0.05 が 5 分続いたら鳴らす
```

4-3. `monitoring/prometheus/tests/alert_rules_test.yml` の BackendHighLatency の試験:
- 便3 で書かれた BackendHighLatency の試験（P99 の形の入力）を消し、次の 3 つに置き換える。他のルールの試験は変えない。
  1. 鳴る: `http_request_duration_seconds_bucket{job="backend",handler="/api/v1/conversations",le="2.5"}` が 1 分に 90 増え、`http_request_duration_seconds_count{job="backend",handler="/api/v1/conversations"}` が 1 分に 100 増える（遅い割合 0.1）。`eval_time` は 15m。`exp_alerts` に 1 件（`exp_labels` は `severity: warning`・`tier: ticket`。sum で集約するので job・handler は付かない。`exp_annotations` は summary・description・runbook_url を全部書く）
  2. 鳴らない（/api/health だけが遅い）: `handler="/api/health"` の bucket（`le="2.5"`）が 1 分に 0 増え、count が 1 分に 100 増える。あわせて `handler="/api/v1/conversations"` の bucket と count がどちらも 1 分に 100 増える（遅い割合 0）。`eval_time` 15m で `exp_alerts` を空
  3. 鳴らない（for より前）: 1 と同じ入力で `eval_time` を 4m にして `exp_alerts` を空
- `values` の刻みは便3 の試験ファイルの `interval`（書かれていなければ既定の 1m）に合わせる。1m のときの入力の例（2026-10-15 Fable が同じ版で 3 試験とも通した形）: 試験 1 は bucket `0+90x20`・count `0+100x20`。試験 2 は /api/health の bucket `0x20`・count `0+100x20`、/api/v1/conversations の bucket と count がどちらも `0+100x20`。
- description の展開後の文字列（`humanizePercentage` の結果）は、`promtool test rules --diff` の got 側から写してよい（便3 カード §6 と同じ扱い）。

4-4. docs/runbooks/alerts.md の `## BackendHighLatency` の節:
- 見出しは変えない。5 項目（札・何が起きているか・最初に見るもの・直し方・止め方）の形も便3 のまま。
- `何が起きているか` を新しい条件の平易な説明にする: /api/health を除いた利用者のリクエストのうち、2.5 秒を超えたものの割合が 5% を超える状態が 5 分続いた。
- `最初に見るもの` に、どの `handler` が遅いかを出す式を足す: `topk(5, sum by (handler) (rate(http_request_duration_seconds_count{job="backend",handler!="/api/health"}[5m])) - sum by (handler) (rate(http_request_duration_seconds_bucket{job="backend",handler!="/api/health",le="2.5"}[5m])))`
- 次の 1 文を足す: 「2026-10-15 に条件を P99 > 2.0 秒から変えた。/api/health が毎回 1〜2.5 秒かかり、P99 を常に 2.0 秒より上に押し上げていたため（14 日で 393 回鳴っていた）。/api/health が遅い原因は未調査（設計 docs/handoff/ai-ops-247/stage1-design.md の U9）」
- 次の 1 文を足す: 「Grafana の backend の画面の P99 のパネルは /api/health を含んだまま変えていない（設計 U3 の扱い）。画面の P99 が高くても、この見張りは鳴らないことがある」
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `cd` で作業場所に入り、次の出力の BackendHighLatency の行が §4-1 の完成形と一致し、他の 13 本の行が origin/main と同じであること:
`python3 -c "import yaml; [print(r['alert'], r.get('for'), r['labels'], r['expr'][:60]) for g in yaml.safe_load(open('monitoring/prometheus/alert_rules.yml'))['groups'] for r in g['rules']]"` を作業場所で実行し、次に `git show origin/main:monitoring/prometheus/alert_rules.yml > /tmp/CC報告ファイル/ai-ops-stage1-bin4/rules-main.yml` で出した main の版に対して、同じ 1 行の `open(...)` のパスを `/tmp/CC報告ファイル/ai-ops-stage1-bin4/rules-main.yml` に差し替えて実行し、2 つの出力を `diff` に通す（期待: 違う行は BackendHighLatency の 1 行だけ）。
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 14 rules, Loki 6 rules, runbook 20 sections`。
5-3. `git diff origin/main -- monitoring/prometheus/alert_rules.yml` の `+` の行と `-` の行がそれぞれ 5 行（コメント・expr・for・summary・description）。`grep -c '^+ '` と `grep -c '^- '` の値と、`+` の行の全文を貼る。
5-4. 本番と同じ版のイメージで `promtool check rules`（期待 "SUCCESS: 14 rules found"）と `promtool test rules`（期待 "SUCCESS"）を実行し、出力と終了コードを貼る。形は便3 カード §5-4 と同じ（`-v` が効かなければ `docker create` → `docker cp` → `docker start -a`）。
5-5. わざと壊して落ちることを確かめる（一時的な書き換え。確かめたら `git checkout -- <file>` で戻し、`git diff --stat` で戻ったことを出す）: expr の `handler!="/api/health"` を 2 か所とも消すと、§4-3 の試験 2（/api/health だけが遅い）が落ちる。`promtool test rules` の出力と終了コード 1 を貼る。
5-6. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「不一致」の行（期待: origin/main と同じ結果。不一致 0）。あわせて `grep -n 'backend_p99_latency_sec\|backend_slow' monitoring/tokens.yml monitoring/prometheus/alert_rules.yml monitoring/scripts/validate_tokens.py` の出力を貼る（期待: `backend_p99_latency_sec` が 0 件・`backend_slow_` が tokens.yml に 2 件と alert_rules.yml のコメントに 1 行）。
5-7. `git grep -n 'backend_p99_latency_sec'` の出力を貼る（期待: docs/handoff/ai-ops-247/stage1-design.md と docs/handoff/ai-ops-247/card-stage1-bin4.md の記録だけ。`monitoring/` に 0 件）。記録は直さない。
5-8. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md` の該当が 0 行（版の番号の形に当たった行は、その行を貼って IP でないことを書く）。
5-9. `git diff origin/main --stat` が §3 の 5 ファイルであること。

## 6. 分岐ごとの対処

- 5-1〜5-3・5-6〜5-9 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-4 で promtool の test が落ちる → 試験の期待値（展開後の文字列など）を直してやり直す。§4-1 の式・for・閾値を変えて合わせることはしない。3 回直しても通らなければ出力を貼って BLOCKED:。
- 5-5 で試験 2 が落ちない → 試験 2 の入力が「/api/health だけが遅い」形になっていない。入力を見直してやり直す。3 回で直らなければ BLOCKED:。
- 前提の便3 のファイル（`tier`・`runbook_url`・単体試験・手順書）が作業場所に無い → 作業を始めずに止まる（BLOCKED:）。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → 便3 カード §6 と同じく `quay.io` の同じ版に替えてよい。替えたら報告に書く。
- PR の CI で `monitoring-check` が落ちる → 出力の該当行を報告し、直せるものは直す。CI の作りの問題で直せなければ BLOCKED:。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| BackendHighLatency が §4-1 の完成形で、他の 19 本は変わらない | §5-1・§5-3 |
| 閾値の正本が新しい値になり、古いキーが `monitoring/` に残らない | §5-6・§5-7 |
| /api/health だけが遅いときに鳴らず、利用者のリクエストが遅いときに鳴る（単体試験） | §5-4・§5-5・PR の CI |
| 札・手順書リンク・見出しの検査が通る | §5-2 |
| 本番の Prometheus に新しい式が入り、評価の失敗が無い | §8-5（`/api/v1/rules` の expr と `health`） |
| 本番のルールファイルが main と sha256 一致 | §8-3 |
| 古い条件で鳴っていたアラートが解決になる | §8-5（`/api/v2/alerts` に BackendHighLatency が無い。または新しい条件で鳴っているなら、その時の遅い割合の値） |
| 鳴る回数が 14 日で 386 回 → 38 回以下・利用者のリクエストが遅かった回の取りこぼし 0 | 実測済み（F4・F5。14 日で 1 回・取りこぼし 0）。配置後 14 日の実回数を Opus が段階1 の終わりに数え直す |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

SSH は制限付き鍵で書けないため無制限鍵 `~/.ssh/manual-only/id_ed25519` を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md・reference_prod_server_config.md。機体は prod2 だけ。本番で行う操作は下の 8-1〜8-6 だけ。Loki・Alertmanager・tokens.yml は本番に配らない（tokens.yml は repo の中の正本で、本番では読まれない）。

8-1. 控え: `/opt/salesanchor-monitoring/backups/ai-ops-stage1/` に、本番の `alert_rules.yml` を `cp -p` で `.bak-20261015-` に PR 番号を付けた名前で写し、元と控えの sha256 を出す。あわせて本番のファイルと、便3 のマージ後の origin/main の版（この PR の 1 つ前）の sha256 が一致することを出す（一致しなければ止まる）。あわせて `/api/v2/alerts` から今鳴っている BackendHighLatency の有無と開始時刻を出す。
8-2. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-ai-ops-bin4/` を作り、main の `monitoring/prometheus/alert_rules.yml` を scp で送る。Prometheus のコンテナの promtool で `check rules` を通す（"SUCCESS: 14 rules found"）。
8-3. 本番の場所に `install -m` で元と同じ権限で置き、本番のファイルと main の sha256 が一致することを出す。Prometheus のコンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送り、終了コードを出す（ホスト側から IP 宛に送らない）。
8-4. 一時ディレクトリを消す（自分で作ったもののみ）。
8-5. 読み取りで次を出す。2 分おきに最大 3 回読んでよいが、待ちに sleep は使わず、1 回目で揃わなければ報告を返し、続きは Opus が依頼する:
  - Prometheus の `/api/v1/rules`（コンテナの中から localhost 宛）: ルール数（期待 14）・BackendHighLatency の `query`（期待は次の文字列。Prometheus v3.11.3 はラベルの並びを `handler`・`job`・`le` の順に並べ替えて返すため、§4-1 と並びが違うのは正常。2026-10-15 Fable が同じ版で実測: `(1 - (sum(rate(http_request_duration_seconds_bucket{handler!="/api/health",job="backend",le="2.5"}[5m])) / sum(rate(http_request_duration_seconds_count{handler!="/api/health",job="backend"}[5m])))) > 0.05`）・`duration`（期待 300）・`health`（期待 ok）・`health` が ok でないルールの数（期待 0）
  - Prometheus の `/api/v1/query` で、§4-1 の expr から `> 0.05` を外した式の今の値（遅い割合。値なしなら「値なし」と書く）
  - Alertmanager の `/api/v2/alerts` の BackendHighLatency の有無（8-1 で鳴っていたものが、読み直しの後に消えているか）
8-6. 生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin4/deploy/ に保存する。

§8 の分岐:
- 8-1 で本番と main（1 つ前）の sha256 が一致しない → 置かずに止まる（NEEDS_DECISION:）。本番が手作業で変えられている。
- 8-2 の promtool が落ちる → 置かずに止まる（BLOCKED:）。
- 8-3 の reload の終了コードが 0 でない、または `prometheus_config_last_reload_successful` が 0 → 8-1 の控えに戻して読み直し、止まる（BLOCKED:）。
- 8-5 で BackendHighLatency の `health` が ok でない、または `query` が §8-5 の期待の文字列と違う → 8-1 の控えに戻して読み直し、止まる（BLOCKED:）。
- 8-5 で新しい条件のアラートが鳴っている → 戻さない。遅い割合の値と、`topk` の式（§4-4）で出した handler の上位 5 件を報告する（利用者のリクエストが実際に遅い可能性があるため、Opus が判断する）。

## 9. 戻し方

- 本番: 8-1 の控えを元の場所へ `install -m` で戻し、Prometheus に `POST /-/reload`。
- repo: この PR の revert。

## 10. PR

- 作業場所: 便3 の実装 PR が main にマージされたことを `gh pr list --state merged --head release/ai-ops-stage1-bin3 --json number,state` で確かめてから（合格は 1 件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）、`cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/ai-ops-stage1-bin4 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出ることがあるが、作業場所の作成とは無関係（2026-10-14 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin4` と `git worktree list` の両方で実在を確かめる。作業場所に `monitoring/prometheus/tests/alert_rules_test.yml` と docs/runbooks/alerts.md があること、`grep -c 'tier: ' monitoring/prometheus/alert_rules.yml` が 14 であること（便3 の版であること）、`ls docs/handoff/ai-ops-247/card-stage1-bin4.md` でこのカードが実在することを確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin4 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを `--body "$(cat 本文ファイル)"` の形で渡して作る（ファイル指定の引数は使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage1-bin4 --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main
- PR 本文に §8 の PO 原文と、本番で実行する操作の番号（8-1〜8-6）と、PO の条件の決定（2026-10-15「Y」）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし
- 本文に IP・URL の秘密・鍵のパス・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-9 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
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
