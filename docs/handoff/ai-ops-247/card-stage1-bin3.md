# 実装カード 段階1 便3 — 札と手順書と CI 検査

> この文書は何か：AI保守運用24時間化 段階1 便3 の作業指示書です。見張りのルール全 20 本（Prometheus 14 本・Loki 6 本）に、急ぎ度の札 `tier`（page／ticket）と、手順書へのリンク `runbook_url` を付けます。手順書 docs/runbooks/alerts.md を新しく作り、CI で「札の欠け・リンク切れ・名前の重複・ルールの書き間違い」を機械で止めます。本番への配置は §8 で、マージの後に行います。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便3（:91-105）・§6 受け入れ基準・維持の仕組み
- 事実確認の生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin3-recon/facts.md（Q1〜Q10。2026-10-15 Sonnet）
- 対象ADR: ADR-1012（本テーマ）
- 状態: 設計は再審査 APPROVE（stage1-design.md・Fable 2026-10-14）。PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」）に基づく実装便
- 前提: 便2（PR #4278）が main にマージされていること。このカードの PR（文書だけ）が main にマージされていること（§10 で `ls` により実在を確かめる）。便3 の作業場所は便2 のマージ後の origin/main から作る（§10）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない。新規 script は `monitoring/scripts/` に置く）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable／マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（札・手順書・その検査のみ。鳴らす条件は変えない） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§8-6） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（Prometheus 14 本・Loki 6 本・手順書なし・検査なし） | ○（§2） |
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

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便3 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/prometheus/alert_rules.yml` の 14 本と `monitoring/loki/rules/jarvis/alerts.yml` の 6 本に、ラベル `tier` と注記 `runbook_url` を足す（式・for・severity・summary・description は変えない）
2. 新規の手順書 docs/runbooks/alerts.md（ルールごとに見出し 1 つ。計 20）
3. 新規の検査 script monitoring/scripts/check_alert_rules.py
4. 新規の Prometheus ルールの単体試験 monitoring/prometheus/tests/alert_rules_test.yml
5. `.github/workflows/monitoring-check.yml` に検査の手順を足す（検査 script・`promtool check rules`・`promtool test rules`・`amtool check-config`・lokitool の `rules check`）

入れない:
- 鳴らす条件（expr・for・閾値）の変更（BackendHighLatency は便4）
- Alertmanager の通知の経路（`monitoring/alertmanager/alertmanager.yml` は触らない。札で通知の数は変わらない。設計 :104）
- `monitoring/tokens.yml`・`monitoring/scripts/validate_tokens.py`（札は閾値ではないため）
- 札 `auto`（段階1 時点で該当なし。設計 :94。検査 script は値として受け付けるだけ）

## 2. 前提の事実（facts.md の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 便2 の後の Prometheus ルールは 4 グループ 14 本（system_alerts・application_alerts・f2_cleanup・uptime_kuma）。全ルールの labels は `severity` だけ、annotations は `summary`・`description` だけ | Q1・`monitoring/prometheus/alert_rules.yml`（origin/release/ai-ops-stage1-bin2） |
| F2 | Loki ルールは 3 グループ 6 本（auth_anomaly・error_anomaly・discord_gateway）。labels・annotations のキーは F1 と同じ。expr は `|` の複数行 | Q2・`monitoring/loki/rules/jarvis/alerts.yml:4-75` |
| F3 | 設計の札の表（stage1-design.md:98-99）の 20 本は、F1 の 14 本と F2 の 6 本と名前が全て一致する | Q2 |
| F4 | `tier`・`runbook_url` は monitoring・.github・docs/runbooks に 0 件。docs/runbooks/alerts.md は無い | Q4・Q5 |
| F5 | Alertmanager の route は `group_by: ["alertname", "job", "instance"]` だけで、子 route・inhibit・テンプレートは無い。`tier` を足しても通知のまとめ方は変わらない | Q4・Q10・`monitoring/alertmanager/alertmanager.yml:3` |
| F6 | `monitoring-check.yml` は paths フィルタが無く、:25-35 の手順で変更されたファイルを見て、監視に関係が無ければ後の手順を飛ばす。今の検出の形（:30）に docs/runbooks/ は入っていない | Q3・`.github/workflows/monitoring-check.yml:25-35` |
| F7 | 本番の版: `prom/prometheus:v3.11.3`・`prom/alertmanager:v0.28.1`・`grafana/loki:3.7.2` | Q6・`docker-compose.monitoring.yml:5`・`:177`・`:198` |
| F8 | `promtool check rules` は便2 版で "SUCCESS: 14 rules found"。`promtool test rules` は使える | Q7 a・b |
| F9 | `amtool check-config` は `webhook_url_file` の指すファイルが無くても SUCCESS（rc=0）。CI にダミーのファイルは要らない | Q7 c |
| F10 | Loki のイメージには sh が無く、実行ファイルは loki だけ。ルールの検査の道具は入っていない。lokitool は Docker のイメージが無く、GitHub の grafana/loki のリリース v3.7.2 の資産に lokitool-linux-amd64.zip がある。lokitool の `rules check` は正しいルールで rc=0、式を壊した版で rc=1。`rules lint` はファイルを書き換えるので CI では使わない | Q7 d |
| F11 | `validate_tokens.py` は alert_rules.yml を生のテキストとして正規表現で読む（メトリクス名の後の最初の `>` の数字）。labels・annotations は expr の後にあるので、足しても読み方に影響しない | Q8・`monitoring/scripts/validate_tokens.py:168-205` |
| F12 | 手元の docker（colima）は `/tmp` を VM に共有していないため `-v /tmp/...` が効かない。作業場所（ホーム配下）なら共有される前提だが【未確認】。効かなければ `docker create` → `docker cp` → `docker start -a` で渡す | Q7 |
| F13 | Loki の ruler の API は本番で groups=[] を返し、ルールの一覧を読めない（設計 S7）。本番の Loki ルールの確認は、ファイルの sha256 と ruler の指標で行う | stage1-design.md S7・便1 の 1 時間後点検（PR #4276 のコメント） |

## 3. 触るファイル（これ以外は触らない）

- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/loki/rules/jarvis/alerts.yml`
- 変更: `.github/workflows/monitoring-check.yml`
- 新規: docs/runbooks/alerts.md
- 新規: monitoring/scripts/check_alert_rules.py
- 新規: monitoring/prometheus/tests/alert_rules_test.yml
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin3.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. 札の割り当て（設計 stage1-design.md:96-99 の表のとおり。変えない）:

| 札 | ルール |
|---|---|
| `page` | ServiceDown・KumaMonitorDown・CriticalDiskUsage・BackendHighErrorRate・BackendErrorSpike・DatabaseError・BruteForceAttempt・DiscordGatewayReconnectFailure・CertInvalid（9 本） |
| `ticket` | HighCpuUsage・HighMemoryUsage・HighDiskUsage・BackendWorkerSaturated・BackendSseConnectionsHigh・BackendHighLatency・SustainedAuthFailure・DiscordDmWriterError・F2CleanupStale・F2CleanupAbsent・CertExpiringSoon（11 本） |

4-2. 各ルールへの足し方（Prometheus・Loki 共通。完成形の例は ServiceDown）:

```yaml
      - alert: ServiceDown
        expr: up == 0
        for: 2m
        labels:
          severity: critical
          tier: page
        annotations:
          summary: "{{ $labels.job }}がダウンしています"
          description: "Exporterからの応答がありません。即時確認してください。"
          runbook_url: "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#servicedown"
```

- `tier` は `severity` の次の行。`runbook_url` は `description` の次の行。
- `runbook_url` は `https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#` の後ろに、ルール名を小文字にしたもの（例 `KumaMonitorDown` → `kumamonitordown`）。
- 既存の行（expr・for・severity・summary・description・コメント）は 1 文字も変えない。`git diff` で `+` の行が `tier:` と `runbook_url:` の 2 行×20 本＝40 行だけになること（§5-6）。

4-3. 手順書 docs/runbooks/alerts.md:
- 先頭に「この文書は何か」（見張りのルールごとの手順書。ルールの正本は monitoring/prometheus/alert_rules.yml と monitoring/loki/rules/jarvis/alerts.yml。見出しはルール名と同じにする。検査は monitoring/scripts/check_alert_rules.py）と、札の意味（page＝利用者に今影響が出ている／出る直前。すぐ見る。ticket＝急がないが放置すると悪化する。翌営業日までに見る。auto＝段階3 で自動の応急処置が付いたもの。今は無い）を書く。
- ルールごとに見出し `## ` の後にルール名をそのまま書いた見出し（例 `## KumaMonitorDown`）を 20 個。並びは Prometheus のファイル順 → Loki のファイル順。
- 各見出しの下に、次の 5 項目を箇条書きで書く: `札`（page／ticket）／`何が起きているか`（ルールの式を平易に。閾値と for を含める）／`最初に見るもの`（Grafana・Loki・Kuma・`docker compose ps` など。repo の既存の手順書 docs/runbooks/monitoring-vps-migration.md・docs/runbooks/discord-gateway-operations.md など、関係するものがあれば相対リンク）／`直し方`（repo の事実から言える範囲。言えない場合は「原因を切り分けて Opus に報告する」と書く。推測で手順を作らない）／`止め方`（鳴り止まないときに Alertmanager の silence を、prod2 の Alertmanager のコンテナの中の `amtool silence add alertname=RULE --duration=PERIOD --comment=REASON` で入れる（RULE はルール名、PERIOD は期間、REASON は理由に置き換える）。期間と理由は記録に残す）。
- F2CleanupStale は、2026-10 に 27,420 分鳴っていた原因が「掃除が実際に成功していなかった」ことで、通知としては正しかった、と書く（設計 :110）。
- IP・URL の秘密・鍵のパス・webhook を書かない（公開リポジトリ）。

4-4. 検査 script monitoring/scripts/check_alert_rules.py:
- 引数なしで、作業場所の直下から実行する前提（`monitoring/scripts/validate_tokens.py` と同じ。パスはファイルの場所から組み立てる）。依存は PyYAML だけ。
- 読むもの: `monitoring/prometheus/alert_rules.yml`・`monitoring/loki/rules/jarvis/alerts.yml`（どちらも `yaml.safe_load`）・docs/runbooks/alerts.md（`## ` で始まる行を見出しとして読む）。
- 検査（どれか 1 つでも欠けたら、欠けたルール名と理由を 1 行ずつ出し、最後に件数を出して exit 1）:
  1. 全ルールに `labels.tier` があり、値が `page`・`auto`・`ticket` のどれか
  2. 全ルールに `annotations.runbook_url` があり、`https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#` ＋ ルール名の小文字 と完全に一致する
  3. 手順書に `## ` の後にルール名を書いた見出しがある（全ルール）。かつ、手順書の `## ` 見出しで、どのルールにも当たらないものが無い（ただし「この文書は何か」など、ルール用でない見出しを使うなら `### ` 以下にする、と手順書の書き方で避ける）
  4. ルール名（`alert`）が Prometheus と Loki を通して重複しない
  5. 1 つのファイルの中でグループ名が重複しない
- 全部通ったら `OK: Prometheus 14 rules, Loki 6 rules, runbook 20 sections` の形（数は実際の数）を出して exit 0。
- 出力に秘密は含まれない（ルール名と理由だけ）。

4-5. 単体試験 monitoring/prometheus/tests/alert_rules_test.yml:
- 書く前に、Prometheus 公式の https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/ で書式を確かめ、URL を報告に書く（Context7 は 2026-10-14 に上限超過のため直接確認で代える）。`rule_files` は `../alert_rules.yml`（試験ファイルからの相対）。相対で読めない場合は、CI の実行の形（§4-6）に合わせて直し、直した形を報告に書く。
- Prometheus の 14 本それぞれに、少なくとも 1 つの「鳴る」試験（擬似の系列 `input_series`・`eval_time` を for より後・`exp_alerts` に `exp_labels` と `exp_annotations` を全部書く。`tier` と `runbook_url` を含む）を書く。`exp_annotations` を全部書くので、`summary`・`description` のテンプレートの展開後の文字列（`$value` の値を含む）と一致させる。
- 少なくとも KumaMonitorDown と ServiceDown には「鳴らない」試験（for より前の `eval_time` で `exp_alerts` を空）も書く。
- F2CleanupAbsent は `absent()` の試験なので、系列を与えない形で鳴ることを確かめる。
- 公式ドキュメントに「`exp_annotations` を省いたときの扱い」が書かれていないため（2026-10-15 Opus が確認）、省かずに全部書く。

4-6. `.github/workflows/monitoring-check.yml`:
- :30 の検出の形に `docs/runbooks/alerts\.md` を足す（手順書だけを直した PR でも検査が走るように）。完成形: `grep -qE "^(monitoring/|docker-compose(\.monitoring|\.exporters)?\.yml|\.env(\.monitoring)?\.example|\.github/workflows/monitoring-check\.yml|docs/runbooks/alerts\.md)"`
- :57 の後ろに次の手順を足す（どれも `if: steps.changes.outputs.relevant == 'true'`）:
  1. `アラートルールの札・手順書リンク検査`: `python3 monitoring/scripts/check_alert_rules.py`
  2. `Prometheus ルール構文と単体試験（promtool）`: `docker run --rm -v "$PWD/monitoring/prometheus:/r:ro" --entrypoint promtool prom/prometheus:v3.11.3 check rules /r/alert_rules.yml` と、同じ形の `test rules /r/tests/alert_rules_test.yml`
  3. `Alertmanager 設定検査（amtool）`: `docker run --rm -v "$PWD/monitoring/alertmanager:/a:ro" --entrypoint amtool prom/alertmanager:v0.28.1 check-config /a/alertmanager.yml`
  4. `Loki ルール構文検査（lokitool）`: GitHub の grafana/loki のリリース v3.7.2 から lokitool-linux-amd64.zip を `curl -fsSL` で取り、**sha256 を固定して照合してから**展開し、`rules check monitoring/loki/rules/jarvis/alerts.yml` を実行する。固定する sha256 は、担当が同じ zip を手元で取って `shasum -a 256` で出した値を書き、報告にも書く。zip の中の実行ファイル名は展開して確かめる（推測で書かない）。手順は 1 行ずつ次の形にする（`EXE` は担当が §5-5 で確かめた実行ファイル名、`SHA` は §5-5 で出した値に置き換える）:
     - `curl -fsSL -o /tmp/lokitool.zip https://github.com/grafana/loki/releases/download/v3.7.2/lokitool-linux-amd64.zip`
     - `echo "SHA  /tmp/lokitool.zip" | sha256sum -c -`
     - `unzip -o /tmp/lokitool.zip -d /tmp/lokitool`
     - `chmod +x /tmp/lokitool/EXE`
     - `/tmp/lokitool/EXE rules check monitoring/loki/rules/jarvis/alerts.yml`
- 版（v3.11.3・v0.28.1・3.7.2）は F7 の本番の版と同じにする。版の文字列の横に、出典として compose の行をコメントで書く（例 `# docker-compose.monitoring.yml:5 と同じ版`）。
- :17 の `timeout-minutes: 5` は `10` に上げてよい（イメージ 2 つの取得・lokitool の取得・`for: 24h` のルールの単体試験で 5 分を超え得るため）。
- 既存の手順（:1-57）の中身は、:30 と :17 の 2 か所以外は変えない。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `cd` で作業場所に入り、次の出力が §4-1 の表と一致すること（page 9・ticket 11・計 20）:
`python3 -c "import yaml; [print(f, r['alert'], r['labels'].get('tier'), r['annotations'].get('runbook_url','').rsplit('#',1)[-1]) for f in ['monitoring/prometheus/alert_rules.yml','monitoring/loki/rules/jarvis/alerts.yml'] for g in yaml.safe_load(open(f))['groups'] for r in g['rules']]"`
5-2. `python3 monitoring/scripts/check_alert_rules.py` が exit 0 で `OK: Prometheus 14 rules, Loki 6 rules, runbook 20 sections`。
5-3. わざと壊して落ちることを 4 通り確かめる（一時的な書き換え。確かめたら `git checkout -- <file>` で戻し、`git diff --stat` で戻ったことを出す）: (a) ServiceDown の `tier:` 行を消す (b) BruteForceAttempt の `runbook_url` の `#` の後ろを `bruteforce` に変える (c) 手順書の `## CertInvalid` を消す (d) Loki のファイルの `DatabaseError` の `alert:` を `BackendErrorSpike` に変える。それぞれ exit 1 と、出た行を貼る。
5-4. 本番と同じ版のイメージで、§4-6 の 2・3 と同じコマンドを手元で実行し、出力と終了コードを貼る（期待: check rules "SUCCESS: 14 rules found"・test rules "SUCCESS"・check-config "SUCCESS"）。F12 のとおり `-v` が効かなければ `docker create` → `docker cp` → `docker start -a` の形で行い、その形を報告に書く。
5-5. lokitool v3.7.2（手元の機種の版）で `rules check monitoring/loki/rules/jarvis/alerts.yml` が rc=0。あわせて CI に固定する linux-amd64 の zip の sha256 を出す。
5-6. `git diff origin/main -- monitoring/prometheus/alert_rules.yml monitoring/loki/rules/jarvis/alerts.yml | grep -c '^+ '` が 40、`grep -c '^- '` が 0（既存の行を変えていない）。あわせて `+` の行が `tier:` と `runbook_url:` だけであることを `grep '^+ ' | grep -vcE 'tier: (page|ticket)$|runbook_url: '` が 0 で示す。`grep -c` は該当が 0 行のとき 0 を出して終了コード 1 になる。0 が出れば合格で、終了コード 1 は正常。
5-7. `python3 monitoring/scripts/validate_tokens.py` の終了コードと「不一致」の行（期待: 便2 のマージ後と同じ結果。不一致 0）。
5-8. `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" docs/runbooks/alerts.md` の該当が 0 行（版の番号の形に当たった行は、その行を貼って IP でないことを書く）。
5-9. `git diff origin/main --stat` が §3 の 7 ファイルであること。

## 6. 分岐ごとの対処

- 5-1〜5-3・5-6〜5-9 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-4 で promtool の test が落ちる → 試験の期待値（展開後の文字列など）を直してやり直す。ルールの式や for を直して合わせることはしない（範囲外）。3 回直しても通らなければ出力を貼って BLOCKED:。期待値を書くときの落とし穴: (1) 試験の中の `time()` は 0 から始まる（公式 unit_testing_rules「start_timestamp (which defaults to 0)」）。F2CleanupStale を鳴らすには系列の値を負（例 `-700000x200`）にする (2) `absent()`（F2CleanupAbsent）は `instance="app-vps"` のラベルを持つ 1 系列を返すので `exp_labels` に `instance: app-vps` を書く (3) `exp_labels` には入力系列のラベル（job・instance・monitor_name など）も含める。食い違いは `promtool test rules --diff` で読め、got 側から写してよい。
- PR の CI で Docker Hub の取得回数の制限に当たって落ちる → 同じ版の公式ミラー（`quay.io/prometheus/prometheus:v3.11.3`・`quay.io/prometheus/alertmanager:v0.28.1`）に替えてよい。替えたら報告に書く。
- 5-4 で docker が使えない → 手元での実行を飛ばし、その旨と理由を報告に書く。CI の結果で確かめる（PR の CI が緑になるまでマージしない）。
- 5-5 で lokitool が取れない（ネットワーク等） → 出力を貼って BLOCKED:。
- PR の CI で `monitoring-check` の新しい手順が落ちる → 出力の該当行を報告し、直せるものは直す。CI の作りの問題（docker の権限など）で直せなければ BLOCKED:。
- process-artifacts gate が workflow の変更について GO 記録などを求める → 求められた内容の原文を報告して止まる（NEEDS_DECISION:）。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 全 20 本に札があり、表のとおり（page 9・ticket 11） | §5-1 |
| 全 20 本の手順書リンクが手順書の実在する見出しを指す | §5-2 |
| 札・リンク・見出し・名前の重複の欠けを検査が止める | §5-3 の 4 通りが exit 1 |
| Prometheus の 14 本が擬似の系列で鳴る（単体試験） | §5-4・PR の CI |
| Loki の 6 本の構文が通る | §5-5・PR の CI |
| 鳴らす条件を変えていない | §5-6（足した行 40・消した行 0） |
| 本番の Prometheus 14 本に札が付く | §8-6（`/api/v1/rules` の `labels.tier`） |
| 本番の Loki 6 本に札が付く | §8-4 の sha256 一致で代える（Loki の ruler API は読めないため） |
| 本番のルールファイルが main と sha256 一致・評価失敗 0 | §8-3・§8-4・§8-6 |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

SSH は制限付き鍵で書けないため無制限鍵 `~/.ssh/manual-only/id_ed25519` を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md・reference_prod_server_config.md。機体は prod2 だけ。本番で行う操作は下の 8-1〜8-7 だけ。

8-1. 控え: `/opt/salesanchor-monitoring/backups/ai-ops-stage1/`（ルールの置き場の外）に、本番の `alert_rules.yml` と Loki の `alerts.yml` を `cp -p` で、それぞれ `.bak-20261015-` に PR 番号を付けた名前で写し、元と控えの sha256 を出す。あわせて本番の 2 ファイルと、便2 のマージ後の origin/main の版（この PR の 1 つ前）の sha256 が一致することを出す（一致しなければ止まる）。
8-2. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-ai-ops-bin3/` を作り、main の `monitoring/prometheus/alert_rules.yml` と `monitoring/loki/rules/jarvis/alerts.yml` を scp で送る。Prometheus のコンテナの promtool で `check rules` を通す（"SUCCESS: 14 rules found"）。
8-3. Prometheus のルール: 本番の場所に `install -m` で元と同じ権限で置き、本番のファイルと main の sha256 が一致することを出す。Prometheus のコンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送り、終了コードを出す（ホスト側から IP 宛に送らない）。
8-4. Loki のルール: 本番の Loki のルールの置き場（便1 と同じ場所。`docker-compose.monitoring.yml` の loki の volume で確かめる）に `install -m` で元と同じ権限で置き、sha256 が main と一致することを出す。Loki は置き場を定期に読み直すので再起動しない（設計 S24）。
8-5. 一時ディレクトリを消す（自分で作ったもののみ）。
8-6. 読み取りで次を出す。2 分おきに最大 3 回読んでよいが、待ちに sleep は使わず、1 回目で揃わなければ報告を返し、続きは Opus が依頼する:
  - Prometheus の `/api/v1/rules`（コンテナの中から localhost 宛）: ルール数（期待 14）・`labels.tier` が無いルールの名前（期待 0 件）・`tier` ごとの数（期待 page 5・ticket 9）・`health` が ok でないルールの数（期待 0）
  - Loki の ruler の指標: `loki_prometheus_rule_group_rules`（3 グループ計 6）・`loki_prometheus_rule_evaluation_failures_total`（3 グループとも 0 のまま）・`loki_ruler_config_last_reload_successful`（1）・最終の読み直し時刻が 8-4 より後
  - Alertmanager の `/api/v2/alerts` の alertname と `tier` の一覧（便3 の前から出ているアラートに `tier` が付いたかを見るため）
  - 注: 配置の時点で鳴っているアラートは、`tier` を足すとラベルの組が変わるため別のアラートとして扱われる。新しい方は `for` の時間（SustainedAuthFailure は 5 分）が過ぎてから鳴り直し、古い方は約 4 評価間隔後に「解決」になる。通知グループは alertname/job/instance で同じなので、Discord には「解決」と「発生」が 1 通にまとまるか 2 通に分かれて届く。いずれも異常ではない（Prometheus はソースで確認。Loki も同じ挙動と見込むが【未確認】）。配置前に鳴っていたアラートの名前を 8-1 の時点で `/api/v2/alerts` から出しておき、報告で対にして示す（便1 の 1 時間後点検の時点では SustainedAuthFailure の 1 件）
8-7. 生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin3/deploy/ に保存する。

§8 の分岐:
- 8-1 で本番と main（1 つ前）の sha256 が一致しない → 置かずに止まる（NEEDS_DECISION:）。本番が手作業で変えられている。
- 8-2 の promtool が落ちる → 置かずに止まる（BLOCKED:）。
- 8-6 で Prometheus のルールに `tier` が無いものがある、または評価失敗が出る → 8-1 の控えに戻して読み直し、止まる（BLOCKED:）。
- 8-6 で Loki の読み直し時刻が 8-4 より後にならない → 5 分後に 1 回だけ読み直してよい。それでも古ければ数字を報告して止まる（`docker compose restart loki` は Opus の合図を受けてから）。

## 9. 戻し方

- 本番: 8-1 の控えを元の場所へ `install -m` で戻し、Prometheus は `POST /-/reload`、Loki は定期の読み直しを待つ。
- repo: この PR の revert。

## 10. PR

- 作業場所: 便2（PR #4278）が main にマージされたことを `gh pr view 4278 --json state` が MERGED で確かめてから、`cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/ai-ops-stage1-bin3 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出ることがあるが、作業場所の作成とは無関係（2026-10-14 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin3` と `git worktree list` の両方で実在を確かめる。作業場所の `monitoring/prometheus/alert_rules.yml` に `KumaMonitorDown` があること（便2 の版であること）を `grep -c` で確かめ、`ls docs/handoff/ai-ops-247/card-stage1-bin3.md` でこのカードが実在することを確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin3 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを渡して作る。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage1-bin3 --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main
- PR 本文に §8 の PO 原文と、本番で実行する操作の番号（8-1〜8-7）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし
- 本文に IP・URL の秘密・鍵のパス・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§4-5 の確認結果（URL）／§4-6 の lokitool の sha256 と zip の中の実行ファイル名／§5-1〜5-9 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
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
