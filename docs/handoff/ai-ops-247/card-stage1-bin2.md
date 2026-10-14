# 実装カード 段階1 便2 — 利用者向けの見張り（Kuma 3 件と Prometheus ルールの入れ替え）

> この文書は何か：AI保守運用24時間化 段階1 便2 の作業指示書です。App・API・LP を外から見張る Kuma の見張りを 3 件足し、計器が無くて一度も働いていない Prometheus のルール 4 本を消して、Kuma の結果で鳴るルール 3 本に置き換えます。本番への配置は §8 で、マージの後に行います。

- 設計: docs/handoff/ai-ops-247/stage1-design.md §2 便2・§1 S2・S9〜S13
- 事実確認の生出力: /tmp/CC報告ファイル/ai-ops-stage1-bin2-recon/facts.md（R1〜R7・P1〜P6。2026-10-14 Sonnet）
- 対象ADR: ADR-1012（本テーマ）
- 状態: 設計は再審査 APPROVE（stage1-design.md・Fable 2026-10-14）。PO の一任（2026-10-14「PRマージ、デプロイまで完走させてくれ」）に基づく実装便
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない。新規 script は `monitoring/scripts/` に置く）
- 担当: 実装と本番配置 Sonnet／コード審査 Fable／マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（利用者向けの見張りの入れ替えのみ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5・§8） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1・§8-4・§8-7） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（Kuma 4 件・通知の紐付け 4 行・ルール 15 本） | ○（§2） |
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

作業を始める前に、報告の冒頭へ「本報告はカード 段階1 便2 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/uptime-kuma-monitors.yml` を本番の実物に合わせて書き直す（監視基盤 4 件＋App・API・LP の 3 件。届かない 4 件は消す）
2. 新規 monitoring/scripts/register_kuma_monitors.py（正本の yml を読み、無い見張りだけを足す。何度実行しても同じ結果）と、その依存を固定する新規 monitoring/scripts/requirements-kuma.txt
3. `monitoring/prometheus/alert_rules.yml` から計器の無い 4 本を消し、Kuma の結果で鳴る 3 本を足す
4. `monitoring/tokens.yml` と `monitoring/scripts/validate_tokens.py` の、消す 4 本のトークンと検査を消し、足す 3 本の分を足す

入れない:
- 既存 Kuma 4 件の Discord 直通通知（stage1-design.md U5。触らない）
- `tier` ラベル・`runbook_url`・promtool の CI 検査（便3）
- `scripts/setup_uptime_kuma.sh` の削除（便6）
- Alertmanager の設定（`monitoring/alertmanager/alertmanager.yml`）
- Kuma の管理者パスワードの変更（PO 判断待ち。この便では扱わない。script は実行時に認証ファイルを読むので、先に変わっても手順は同じ）

## 2. 前提の事実（facts.md の番号）

| # | 事実 | 出典 |
|---|---|---|
| F1 | repo の Prometheus ルールは 3 グループ計 15 本（`grep -c "alert:"` で 15。facts.md R1 の「計 17 本」は数え違い）。消す 4 本（HighDbConnections・PostgresDown・HighErrorRate・High502Rate）は直前のコメント行込みで `monitoring/prometheus/alert_rules.yml:49-88` の連続 40 行 | R1 |
| F2 | 本番の alert_rules.yml と origin/main は差 0 行。置き場は prod2 の `/opt/salesanchor-monitoring/monitoring/prometheus/`（コンテナの `/etc/prometheus`）。git 作業木ではない。`--web.enable-lifecycle` あり＝ `POST /-/reload` で読み直せる | P3 |
| F3 | tokens.yml の消す行: thresholds の `db_connection_warning`(:70)・`nginx_5xx_per_5m`(:74)・`nginx_502_per_2m`(:75)、for_durations の `db_down`(:96)・`nginx_5xx`(:97)・`nginx_502`(:98)、見出し :69 とコメント :72-73。`resource_warning`(:94) は残し、コメントの「/ HighDbConnections」だけ削る | R2 |
| F4 | `validate_tokens.py` で 4 本を見ているのは threshold_checks 配列の 3 タプル（:178-186）だけ。照合は CHECK 3（:189-205）。for_durations を読むコードは無い | R2 |
| F5 | 正本 yml の書式: `monitors:` のリスト。各要素は name・type（http/tcp）・interval（秒）・description。http は url。通知のキーは無い | R3 |
| F6 | 本番 Kuma（1.23.16）の見張りは 4 件（app-vps node-exporter・Loki・Alertmanager・Prometheus）。全件 http・60 秒・retry 60・maxretries 1・accepted 200-299 | P1 |
| F7 | 本番 Kuma の通知先は 1 件（discord-server-alerts）で `is_default=1`。`monitor_notification` は 4 行（既存 4 件すべてが通知先 1 に紐付く） | P1 |
| F8 | prod2 に uptime-kuma-api は入っておらず、pip も venv も無い。`python:3.12-slim` のイメージはある。PyPI の最新は 1.2.1 | P2 |
| F9 | Kuma のログイン情報は prod2 の `/opt/salesanchor-monitoring/secrets/uptime-kuma-admin.cred`（「ユーザー:パスワード」の 1 行） | P2 |
| F10 | `monitor_status` は 4 系列（ラベル `monitor_name` ほか）。`monitor_cert_days_remaining`・`monitor_cert_is_valid` は 0 系列 | P4 |
| F11 | prod2 から App・API（`/api/health`）・LP への https の GET は 200 | P5 |
| F12 | ルールの書式: 日本語コメント → alert → expr → for → labels.severity → annotations の summary・description（`alert_rules.yml:90-97` の ServiceDown） | R7 |

## 3. 触るファイル（これ以外は触らない）

- 変更: `monitoring/uptime-kuma-monitors.yml`
- 新規: monitoring/scripts/register_kuma_monitors.py
- 新規: monitoring/scripts/requirements-kuma.txt
- 変更: `monitoring/prometheus/alert_rules.yml`
- 変更: `monitoring/tokens.yml`
- 変更: `monitoring/scripts/validate_tokens.py`
- 変更: `docs/handoff/ai-ops-247/card-stage1-bin2.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

4-1. 書く前に、uptime-kuma-api 1.2.1 の公式ドキュメント（PyPI のページと、そこから辿れる公式の API リファレンス）で `UptimeKumaApi`・`login`・`get_monitors`・`add_monitor`・`MonitorType` の引数名を確かめ、確かめた URL と引数名を報告に書く（Context7 は 2026-10-14 に上限超過で使えなかったため、公式ドキュメントの直接確認で代える）。特に `add_monitor` の `notificationIDList` に空を渡したとき既定の通知先が付かないか、ドキュメントの記述を写す（記述が無ければ「記述なし」と書く。最終的には §8-5 の SELECT で確かめる）。

4-2. `monitoring/uptime-kuma-monitors.yml` の完成形（書式は今の yml を引き継ぎ、キー `register` を足す）:
- 先頭のコメントに「正本。登録は monitoring/scripts/register_kuma_monitors.py。register: false は既に本番にある見張りで、script は触らない」と書く。
- 監視基盤の 4 件: name は本番と同じ文字列（`app-vps node-exporter`・`Loki`・`Alertmanager`・`Prometheus`）、type http、interval 60、`register: false`、description。**url は書かない**（本番は内部向けの宛先で、公開リポジトリに書かないため）。
- 利用者向けの 3 件: name は `App 本番`・`API ヘルスチェック`・`LP`、type http、url は今の yml にある https の宛先をそのまま使う（App・API は `/api/health`・LP）、interval 60、`register: true`、description。interval を今の yml の 30 秒から 60 秒にするのは、既存 4 件（60 秒）と揃え、KumaMonitorDown の for 2m の間に 2 回以上の判定が入るため。
- 今の PostgreSQL・Redis・Meta Graph API・Firebase の 4 件は消す。

4-3. monitoring/scripts/requirements-kuma.txt は `uptime-kuma-api==1.2.1` の 1 行。

4-4. monitoring/scripts/register_kuma_monitors.py の仕様:
- 引数: `--yml PATH`・`--url URL`（Kuma の宛先）・`--cred-file PATH`・`--apply`（無ければ確認だけで変更しない）。
- ログイン情報は `--cred-file` から読み、最初の `:` で分けてユーザーとパスワードにする。**値を出力・ログ・例外の文面に出さない**（例外を捕まえたら型名だけ出す）。
- 動き: ログイン → `get_monitors()` で名前の一覧を取る → yml の各要素について、本番に同じ名前があれば「有り」、無くて `register: true` なら「足す」、無くて `register: false` なら「欠落」と判定 → 判定表（名前と判定だけ）を出す。`--apply` のときだけ「足す」を `add_monitor` で登録する。登録の引数: type HTTP・name・url・interval・retryInterval は interval と同じ・maxretries 1・accepted_statuscodes `["200-299"]`・`notificationIDList` は空。
- 登録の後にもう一度 `get_monitors()` を読み、yml の全名前が本番にあるかを出す。本番にあって yml に無い名前は「正本外」として名前だけ出す（消さない）。
- 終了コード: 「欠落」が 1 件以上、または登録後に yml の名前が欠けていれば 1。それ以外は 0。
- 同じ名前の見張りは作らない（何度実行しても同じ結果）。
- 依存は uptime-kuma-api と PyYAML だけ。repo の CI では実行しない（Kuma に届かないため）。`python3 -m py_compile` が通ること。

4-5. `monitoring/prometheus/alert_rules.yml`:
- :49-88 の 40 行（4 本とそれぞれの直前のコメント・後ろの空行）を消す。`application_alerts` グループに残るのは ServiceDown 以降の 5 本。
- ファイルの末尾に新しいグループ `uptime_kuma` を足し、次の 3 本を F12 の書式で書く（summary・description は日本語。`{{ $labels.monitor_name }}` で見張りの名前を出す）:

```yaml
  - name: uptime_kuma
    rules:
      # Kuma の見張りが失敗している（App・API・LP・監視基盤）
      - alert: KumaMonitorDown
        expr: monitor_status == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "見張り {{ $labels.monitor_name }} が失敗しています"
          description: "Uptime Kuma の見張り {{ $labels.monitor_name }} が 2 分以上失敗しています"

      # 証明書の期限が近い
      - alert: CertExpiringSoon
        expr: monitor_cert_days_remaining < 14
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.monitor_name }} の証明書の期限が近づいています"
          description: "残り {{ $value }} 日です（14 日未満）"

      # 証明書が無効
      - alert: CertInvalid
        expr: monitor_cert_is_valid == 0
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.monitor_name }} の証明書が無効です"
          description: "Uptime Kuma が証明書を無効と判定しています"
```

- 結果は 4 グループ計 14 本（15 − 4 ＋ 3）。

4-6. `monitoring/tokens.yml`: F3 の行を消す。thresholds に `kuma_cert_days_warning: 14` を、for_durations に `kuma_monitor_down: "2m"`・`kuma_cert_expiring: "1h"`・`kuma_cert_invalid: "10m"` を、今の書式（行末コメントにルール名と式）で足す。見出しのコメントは `# Uptime Kuma`。

4-7. `monitoring/scripts/validate_tokens.py`: threshold_checks 配列（:178-186）の、消す 3 タプルを消す。次のタプルを 1 つ足す（既存はすべて `>` 用なので `<` 用の完成形をそのまま使う）: `("kuma_cert_days_warning", r"monitor_cert_days_remaining\s*<\s*(\d+)", "CertExpiringSoon"),`

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `cd` で作業場所に入り `python3 -c "import yaml; d=yaml.safe_load(open('monitoring/prometheus/alert_rules.yml')); print([(g['name'], [r['alert'] for r in g['rules']]) for g in d['groups']]); print(sum(len(g['rules']) for g in d['groups']))"` の出力が次と一致すること:
`[('system_alerts', ['HighCpuUsage', 'HighMemoryUsage', 'HighDiskUsage', 'CriticalDiskUsage']), ('application_alerts', ['ServiceDown', 'BackendHighErrorRate', 'BackendHighLatency', 'BackendWorkerSaturated', 'BackendSseConnectionsHigh']), ('f2_cleanup', ['F2CleanupStale', 'F2CleanupAbsent']), ('uptime_kuma', ['KumaMonitorDown', 'CertExpiringSoon', 'CertInvalid'])]` と `14`
5-2. `python3 -c "import yaml; d=yaml.safe_load(open('monitoring/uptime-kuma-monitors.yml')); print([(m['name'], m['register']) for m in d['monitors']])"` が 7 件（register false 4 件・true 3 件）。あわせて `grep -nE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" monitoring/uptime-kuma-monitors.yml` の該当が 0 行。
5-3. `python3 -m py_compile monitoring/scripts/register_kuma_monitors.py` が exit 0。
5-4. `python3 monitoring/scripts/validate_tokens.py` の全出力を保存し、終了コードと「不一致」「スキップ」の行を報告する（期待: 不一致 0・`✅ CertExpiringSoon: 14` の行がある）。
5-5. 本番と同じ版の Prometheus のイメージで `promtool check rules` を通す（例: `docker run --rm -v "$PWD/monitoring/prometheus:/r:ro" --entrypoint promtool prom/prometheus:v3.11.3 check rules /r/alert_rules.yml`。v3.11.3 は `docker-compose.monitoring.yml:5` の本番の版）。手元に docker が無ければ §8-3 で本番のコンテナの promtool を使う、と報告に書く。
5-6. `git grep -nE "HighDbConnections|PostgresDown|High502Rate|db_connection_warning|nginx_5xx_per_5m|nginx_502_per_2m" -- ':!docs'` の該当を報告する（期待 0 行。docs の中は対象外）。
5-7. `git diff origin/main --stat` が §3 の 7 ファイルであること。

## 6. 分岐ごとの対処

- 4-1 で引数名が §4-4 と違う → ドキュメントの名前に合わせて書き、違いを報告に書く（記録のみで続行）。
- 5-1〜5-4・5-7 の出力が違う → 直してやり直す（記録のみで続行）。
- 5-5 で promtool が落ちる → 直してやり直す。直せなければ出力を貼って BLOCKED:。
- 5-6 で docs 以外に参照が残る → その箇所を報告して止まる（NEEDS_DECISION:）。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| repo のルールが 4 グループ 14 本で、計器の無い 4 本が消えている | §5-1・§5-6 |
| 正本 yml が 7 件で、IP を含まない | §5-2 |
| トークンの検査が不一致 0 | §5-4 |
| 本番 Kuma の見張りが正本の 7 件と一致 | §8-4 の判定表 |
| 新規 3 件に Discord 直通の通知が付いていない | §8-5（`monitor_notification` が 4 行のまま・新規 3 件の行 0） |
| 本番 Prometheus で `monitor_status` 7 系列・`monitor_cert_days_remaining` 3 系列 | §8-7 |
| 本番のルールファイルが main と sha256 一致・ルール 14 本が読み込まれ評価失敗 0 | §8-3・§8-7 |
| ルールが使う全指標の系列数が 1 以上 | §8-7 |

## 8. 本番への配置（マージの後。Opus の合図を受けてから行う）

SSH は制限付き鍵で書けないため無制限鍵 `~/.ssh/manual-only/id_ed25519` を使ってよい。PO 原文（2026-10-14）:「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」 接続方法はメモリの reference_vps_monitor_access.md・reference_prod_server_config.md。機体は prod2 だけ。本番で行う操作は下の 8-1〜8-8 だけ。

**認証ファイルの扱い**: `uptime-kuma-admin.cred` は中身を表示しない（cat・head・sed・grep の対象にしない）。確かめるのは `wc -c` と `wc -l` だけ。script にはパスとして渡す。

8-1. 控え: 控えはルールの置き場の外に置く。`mkdir -p /opt/salesanchor-monitoring/backups/ai-ops-stage1/` に、`alert_rules.yml` を `cp -p` で `alert_rules.yml.bak-20261014-` に PR 番号を付けた名前で写し、sha256 を出す。Kuma の DB は Kuma のコンテナの中で `sqlite3 -readonly /app/data/kuma.db` で `monitor` の件数と `monitor_notification` の行数（期待 4 と 4）を出す。
8-2. Kuma への登録: main の `monitoring/uptime-kuma-monitors.yml`・`monitoring/scripts/register_kuma_monitors.py`・`monitoring/scripts/requirements-kuma.txt` を scp で prod2 の一時ディレクトリ（`/opt/salesanchor-monitoring/tmp-ai-ops-bin2/`）へ送る。Kuma のコンテナが属する docker のネットワーク名を `docker inspect` で出す（ネットワーク名だけ）。`python:3.12-slim` を `--rm`・そのネットワーク・一時ディレクトリと認証ファイルを読み取り専用で付けて起動し、中で `pip install -q -r requirements-kuma.txt` の後、まず `--url http://uptime-kuma:3001`（`monitoring/prometheus/prometheus.yml:81` と同じサービス名）・`--apply` 無しで実行して判定表を出す（期待: 有り 4・足す 3・欠落 0）。期待どおりなら同じ形で `--apply` 付きで 1 回実行する。
8-3. ルールの配置: main の `monitoring/prometheus/alert_rules.yml` を scp で一時ディレクトリへ送り、Prometheus のコンテナの promtool で `check rules` を通してから、本番の場所に `install -m` で元と同じ権限で置く。本番のファイルと main の sha256 が一致することを出す。
8-4. もう一度 `--apply` 無しで実行し、判定表が「有り 7・足す 0・欠落 0」であることを出す（何度実行しても同じ結果の確認）。
8-5. Kuma のコンテナの中で `sqlite3 -readonly /app/data/kuma.db` を読み、`monitor` の件数（期待 7）と名前、`monitor_notification` の行数（期待 4）と、新規 3 件の id に紐付く行数（期待 0）を出す。
8-6. Prometheus のコンテナの中から `wget -q -O- --post-data= http://localhost:9090/-/reload` を 1 回送り、終了コードを出す（ホスト側から IP 宛に送らない。コマンドに IP が入るため）。8-7 の読み取りも同じくコンテナの中から localhost 宛に行う。
8-7. Prometheus の API（読み取り）で次を出す。2 分おきに最大 3 回読んでよいが、待ちに sleep は使わず、1 回目で揃わなければ報告を返し、続きは Opus が依頼する:
  - `/api/v1/rules` のルール数（期待 14）・グループ名・`health` が ok でないルールの数（期待 0）
  - `count(monitor_status)`（期待 7）と `monitor_name` の一覧、`count(monitor_cert_days_remaining)`（期待 3）、`count(monitor_cert_is_valid)`（期待 3）
  - 14 本のルールの式が使う指標名ごとの系列数（0 のものの名前。期待 0 件）
  - `ALERTS{alertstate="firing"}` の alertname の一覧
8-8. 一時ディレクトリ `/opt/salesanchor-monitoring/tmp-ai-ops-bin2/` を消す（自分で作ったもののみ）。生出力はすべて /tmp/CC報告ファイル/ai-ops-stage1-bin2/deploy/ に保存する。

§8 の分岐:
- 8-1 の件数が 4 と 4 でない → 止まる（NEEDS_DECISION:）。
- 8-2 で pip が入らない（外へ出られない等） → 何も登録せず止まる（BLOCKED:）。ルールの配置（8-3）にも進まない。
- 8-2 の 1 回目の判定表が期待と違う → `--apply` をせず止まる（NEEDS_DECISION:）。
- 8-3 の promtool が落ちる → 置かずに止まる（BLOCKED:）。Kuma に足した 3 件はそのまま残し、報告に書く。
- 8-5 で新規 3 件に通知の行がある → Kuma の画面での外し方は外部 GUI の操作になるため自分では外さず、id と行数を書いて止まる（NEEDS_DECISION:）。
- 8-7 で `monitor_cert_days_remaining` が 0 系列のまま（設計 S11 の【未確認】が外れた） → 戻さずに数字を報告する（CertExpiringSoon・CertInvalid は鳴らないだけで害は無い。扱いは Opus が決める）。
- 8-7 で KumaMonitorDown が鳴っている → 見張りの名前と Kuma 側の状態を出して止まる（NEEDS_DECISION:）。

## 9. 戻し方

- 本番のルール: 8-1 の控えを `alert_rules.yml` に戻し、`POST /-/reload`。
- 本番 Kuma: 足した 3 件を Kuma の画面で消す（script に消す動きは作らない。設計 stage1-design.md §戻し方）。画面の操作は外部 GUI のため PO が行う。Opus が消す見張りの名前を PO に伝える。
- repo: この PR の revert。

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage1-bin2 --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出ることがあるが、作業場所の作成とは無関係（2026-10-14 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage1-bin2` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage1-bin2 -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを渡して作る。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage1-bin2 --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main
- PR 本文に §8 の PO 原文と、本番で実行する操作の番号（8-1〜8-8）を書く。配置はマージ後なので、配置後に Opus が PR にコメントで追記する
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage1-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし
- 本文に IP・URL の秘密・鍵のパス・認証ファイルの中身を書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§4-1 の確認結果（URL と引数名）／§5-1〜5-7 の出力／PR の URL／生出力のパス／判断を要した点（事実のみ）
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
