# 実装カード 段階2 便C — Alertmanager の送り先に保守 API を足す

> この文書は何か：AI保守運用24時間化 段階2 便C の作業指示書です。監視サーバ（prod2）の Alertmanager が、今までどおり Discord に通知しながら、同じ通知を保守 API の受け口（便B）にも送るようにします。担当が変えるのはリポジトリの設定 3 ファイルだけです。prod2 への配置と鍵の作成は、Opus が作る PO の `!` スクリプトで行います（§8）。

- 設計: docs/handoff/ai-ops-247/stage2-design.md §2 便C（:133-176）・§5・§6・§8
- 親設計: docs/handoff/ai-ops-247/design.md §5 段階2
- 前便: 便A（#4357）・便B（#4366 マージ 6aa8f3c77・本番で受け口 403／保守の鍵で一覧 200・空／鍵なし 401。/tmp/CC報告ファイル/ai-ops-stage2-bin-b/verify_prod_4366.txt）
- 対象ADR: ADR-1012（本テーマ）
- 状態: 設計は Opus 自己審査 APPROVE（stage2-design.md §9）。このカードの §2-2 の細部の決定は Opus の技術判断（親設計の目的・範囲を変えない）
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。ただし prod2 への手作業の配置と secrets の登録があるので、マージと配置は Opus が §8 の順で行う。担当はマージしない
- 担当: 実装 Sonnet／審査・マージ・配置の準備・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（Alertmanager の送り先を足すことだけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に 3 ファイルの完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-3） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行の目印は origin/main 6aa8f3c77 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/08-vps.md | 本番（prod1・prod2）には触らない（配置と確認は Opus と PO が行う） | ○（§8） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 段階2 便C の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `monitoring/alertmanager/alertmanager.yml` に子ルート 2 つと受け先 `ops-api` を足す（§4-1）
2. `docker-compose.monitoring.yml` の alertmanager に秘密ファイルのマウント 1 行を足す（§4-2）
3. `.github/workflows/monitoring-check.yml` に、送り先の試験（`amtool config routes test`）の段を 1 つ足す（§4-3）

入れない:
- prod2 への配置・鍵の作成・GitHub secret の登録（§8。Opus と PO）
- backend・nginx の変更（便B で済み。受け口・IP 制限・env の配線はある）
- Alertmanager の送信失敗を見張るルール（設計 §7 V3。反映後 7 日の数を見て決める）
- `monitoring/scripts/check_config_drift.sh` の変更（alertmanager.yml は既に照合の対象。compose も対象）

## 2. 前提の事実と設計の細部

### 2-1. 事実（origin/main 6aa8f3c77・生出力 /tmp/CC報告ファイル/ai-ops-stage2-bin-c/recon_raw.md）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 今の alertmanager.yml は 11 行。route の受け先は `discord-server-alerts` 1 つ、子ルートなし、`webhook_configs`・`http_config` は未使用 | `monitoring/alertmanager/alertmanager.yml:1-11` |
| F2 | alertmanager の image は `prom/alertmanager:v0.28.1`。volumes は設定ファイルと Discord の秘密ファイルの 2 行で、データの volume は無い | `docker-compose.monitoring.yml:177-180` |
| F3 | CI の amtool の段は `check-config` だけ。同じ版の image を docker run で使う | `.github/workflows/monitoring-check.yml:70-74` |
| F4 | CI の検査は、`monitoring/`・`docker-compose.monitoring.yml`・`.github/workflows/monitoring-check.yml` などが変わったときに走る | `.github/workflows/monitoring-check.yml:25-35` |
| F5 | prod2 から prod1 へは、IP 直＋`tls_config.server_name` の形で既に届いている（Prometheus の `/metrics` の取得） | `monitoring/prometheus/prometheus.yml:36-45`・`nginx/nginx.conf:246-248` |
| F6 | 受け口 `location = /api/v1/ops/alertmanager` は `allow 49.212.160.98; deny all;`（prod2 の IP だけ）。nginx に `real_ip` の設定は無く、`$remote_addr` で判定する | `nginx/nginx.conf:388-404` |
| F7 | 受け口は `OPS_INGEST_TOKEN` を Bearer で照合し、env が空なら必ず 401。env は deploy.yml と docker-compose.yml で配線済み | `backend/app/routers/ops.py:85-99`・`.github/workflows/deploy.yml:290-291`・`:335-336`・`docker-compose.yml:137-138` |
| F8 | 受け口は同じ (fingerprint, startsAt) を 1 行にまとめ、`notify_count` を 1 足す。resolved なら `resolved_at` を入れる | `backend/app/routers/ops.py` の `_UPSERT_INCIDENT_SQL` |
| F9 | prod2 への設定の自動配布は無い。手作業（控え → 置く → main と diff 0 → 反映）。prod2 の毎日の照合は alertmanager.yml と compose を含む 6 本の sha256 を main と比べる | `docs/handoff/ai-ops-247/stage1-design.md:29`・`monitoring/scripts/check_config_drift.sh:22` |
| F10 | `amtool config routes test` は、`--verify.receivers` の受け先と合わなければ終了コード 1。受け先は経路の定義の順にカンマでつないで出す | 公式ソース `cli/test_routing.go`（v0.28.1） |
| F11 | `amtool alert add` は、ラベルを `key=value` で並べ、`--start`・`--end` を RFC3339 で受ける | 公式ソース `cli/alert_add.go`（v0.28.1） |
| F12 | 今の CI は、prod2 にしか無い Discord の秘密ファイル（`webhook_url_file`）を含む設定で `check-config` が通っている | F3 の段・`monitoring/alertmanager/alertmanager.yml:10` |

### 2-2. 設計の細部の決定（Opus・stage2-design.md からの補い）

| # | 決めたこと | 理由 |
|---|---|---|
| D1 | 受け口の鍵（`OPS_INGEST_TOKEN`）は便C で作る。設計 §2 の「置くのは便B の反映の前」は、便B カード D1 で「便C で作る」に改めた。設計の該当行（stage2-design.md:50）もこのカードの PR で直す | 使うのは Alertmanager だけで、置き場所の prod2 を触るのは便C |
| D2 | 鍵の登録 → backend への反映 → Alertmanager の切り替え、の順にする（§8） | 先に Alertmanager を切り替えると、backend の鍵が空の間は 401 が続き、再送が積もる（Discord は別の子ルートなので止まらない） |
| D3 | 子ルートの 1 つ目を Discord（`continue: true`）、2 つ目を ops-api にする | 保守 API が落ちていても、Discord への通知は先に、別に送られる（設計 §5） |
| D4 | Alertmanager はコンテナを作り直す（再読込では足りない） | マウントを足すため。データの volume が無いので（F2）、作り直しで通知の記録と silence が消え、いま鳴っている通知が Discord と障害記録に 1 回ずつ送り直される。§8 で切り替えの前に silence の数を読み、PO に時刻を伝える |
| D5 | 本番の試験用の擬似アラートは、`alertname=OpsPipelineTest`・`severity=info` で 1 件。試験の行は消せない（表に DELETE の権限が無い）ので、注記の口で「試験」と書き残す | 記録は消せない設計（便A）。後で数えるときに区別できるようにする |

## 3. 触るファイル（これ以外は触らない）

- 変更: `monitoring/alertmanager/alertmanager.yml`（§4-1 の完成形に置き換え）
- 変更: `docker-compose.monitoring.yml`（alertmanager の volumes に 1 行の追記のみ）
- 変更: `.github/workflows/monitoring-check.yml`（段 1 つの追記のみ）
- 変更: `docs/handoff/ai-ops-247/card-stage2-bin-c.md`（このカード。§13 報告欄の追記のみ）

## 4. 作り方

### 4-1. `monitoring/alertmanager/alertmanager.yml` の完成形（ファイル全体をこれにする）

```yaml
route:
  receiver: discord-server-alerts
  group_by: ["alertname", "job", "instance"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - receiver: discord-server-alerts
      continue: true
    - receiver: ops-api
receivers:
  - name: discord-server-alerts
    discord_configs:
      - webhook_url_file: /etc/alertmanager/secrets/discord-webhook
        send_resolved: true
  - name: ops-api
    webhook_configs:
      - url: https://49.212.137.46/api/v1/ops/alertmanager
        send_resolved: true
        max_alerts: 100
        timeout: 10s
        http_config:
          authorization:
            type: Bearer
            credentials_file: /etc/alertmanager/secrets/ops-ingest-token
          tls_config:
            server_name: api.salesanchor.jp
```

### 4-2. `docker-compose.monitoring.yml`

目印の行 `      - ./secrets/alertmanager-discord-webhook:/etc/alertmanager/secrets/discord-webhook:ro`（:180）の次に、同じ字下げで 1 行を足す:

```yaml
      - ./secrets/ops-ingest-token:/etc/alertmanager/secrets/ops-ingest-token:ro
```

### 4-3. `.github/workflows/monitoring-check.yml`

目印の段 `      - name: Alertmanager 設定検査（amtool）`（:70-74）の直後（次の段 `      - name: Loki ルール構文検査（lokitool）` の前）に、次の段を足す:

```yaml
      - name: Alertmanager 送り先の試験（amtool routes test）
        if: steps.changes.outputs.relevant == 'true'
        run: |
          # どの通知も Discord と保守 API の両方に届くこと（ADR-1012 段階2 便C）
          docker run --rm -v "$PWD/monitoring/alertmanager:/a:ro" --entrypoint amtool prom/alertmanager:v0.28.1 config routes test --config.file=/a/alertmanager.yml --verify.receivers=discord-server-alerts,ops-api alertname=CiRoutesTest
          docker run --rm -v "$PWD/monitoring/alertmanager:/a:ro" --entrypoint amtool prom/alertmanager:v0.28.1 config routes test --config.file=/a/alertmanager.yml --verify.receivers=discord-server-alerts,ops-api alertname=CiRoutesTest severity=critical job=node
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. YAML の形：作業場所で `python3 -c "import yaml,sys; [yaml.safe_load(open(p)) for p in sys.argv[1:]]; print('ok')" monitoring/alertmanager/alertmanager.yml docker-compose.monitoring.yml .github/workflows/monitoring-check.yml` が `ok`。

5-2. 差分：`git diff origin/main --stat` が §3 の 4 ファイル。加えて `git diff origin/main -- docker-compose.monitoring.yml .github/workflows/monitoring-check.yml | grep -c "^-[^-]"` が 0（削除の行が無い）。

5-3. 送り先の名前の対：`grep -n -E "receiver:|name: (discord-server-alerts|ops-api)|continue:" monitoring/alertmanager/alertmanager.yml` が、route の `receiver: discord-server-alerts`・子の `receiver: discord-server-alerts`・`continue: true`・子の `receiver: ops-api`・受け先の `name: discord-server-alerts`・`name: ops-api` の 6 行。

5-4. 手元に docker があれば、§4-3 の 2 本のコマンドをそのまま実行し、出力が `discord-server-alerts,ops-api` で終了コード 0。docker が無ければ「手元では未実行・CI の監視スタック整合性チェックで実行」と書く。

5-5. PR の CI の結果は担当が待たない。PR を作ったら URL を報告して終える（CI は Opus が見る）。

## 6. 分岐ごとの対処

- §4-2・§4-3 の目印の行が見つからない（ほかの PR が先に変えた）→ `git show origin/main:docker-compose.monitoring.yml | grep -n "alertmanager-discord-webhook"` のように origin/main で探し直し、同じ意味の位置に足す。決められなければ NEEDS_DECISION: で grep の出力を貼る
- CI の `check-config` が `credentials_file` のファイルが無いことで落ちる → F12 と食い違うので、失敗の原文を貼って BLOCKED:（Opus が CI の段の作りを決める。担当は CI に空のファイルを作る段などを足さない）
- CI の `config routes test` が `WARNING: Expected receivers did not match` で落ちる → §4-1 の子ルートの順と `continue: true` を見直す。§4-1 のとおりで落ちるなら原文を貼って BLOCKED:
- 「CI設定整合性チェック」などワークフローの検査が落ちる → 失敗の原文を貼って BLOCKED:

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| どの通知も Discord と ops-api の両方に送られる設定になっている | CI の監視スタック整合性チェック（§4-3 の 2 本） |
| 設定が Alertmanager 0.28.1 で読める | CI の `check-config` |
| 触ったファイルが 4 つで、compose と CI から既存の行を消していない | §5-2 |
| 本番：擬似アラート 1 件が Discord に 1 件、障害記録に 1 行。resolved で同じ行の `notify_count` が 2・`resolved_at` が入る | §8 の 5（PO の `!` スクリプトの生出力と、保守の鍵での一覧） |
| 本番：Discord への通知は今までどおり届く | §8 の 5 の Discord の投稿（PO の目視 y/n） |
| prod2 の設定が main と一致 | §8 の 4 の sha256 と、翌日の毎日の照合 |

## 8. 反映の手順（Opus が行う。担当はしない）

1. 鍵：Opus が PO の `!` スクリプト A を作る。`secrets.token_urlsafe(32)` → `gh secret set OPS_INGEST_TOKEN` → prod2 の `/opt/salesanchor-monitoring/secrets/ops-ingest-token` に置く（Discord の秘密ファイルと同じ持ち主・権限）。値は画面に出さない。secrets の変更なので、実行の前に PO に y/n を聞く
2. この PR をマージ → deploy.yml（main への push で起動）の成功を Actions の記録で確かめる。これで backend の env に鍵が入る
3. prod2 から受け口に届くか：スクリプト B の最初に、prod2 で `curl --resolve api.salesanchor.jp:443:49.212.137.46` と鍵で `{"alerts": []}` を POST し、200 と `"received":0` を確かめる。違えば切り替えずに止める
4. 切り替え：スクリプト B が prod2 で、alertmanager.yml と compose を控えに写す → silence の数を記録 → main の 2 ファイルを置く → main と sha256 が一致することを確かめる → `docker compose -f docker-compose.monitoring.yml up -d alertmanager`（作り直し・D4）→ `/-/ready` が 200
5. 試験：スクリプト B が、固定の `--start` で `OpsPipelineTest` を 1 件送る → 60 秒後に保守の鍵で一覧に 1 行（`notify_count` 1）→ 同じ `--start` と `--end` で resolved を送る → 6 分後に同じ行の `notify_count` 2・`resolved_at` あり。最後に注記の口で「便C の本番試験」と書く（D5）。PO に Discord に試験の通知が 2 件（発火と解消）届いたかを y/n で聞く
6. マージから 4 までは同じ日に続けて行う（prod2 の毎日の照合が、main と prod2 のずれを知らせるため）
7. 生出力は /tmp/CC報告ファイル/ai-ops-stage2-bin-c/deploy/ に置く

## 9. 戻し方と未解決事項

- 戻し方：prod2 で控えの alertmanager.yml と compose を戻して `up -d alertmanager`（Discord だけの元の形）。リポジトリはこの PR の revert を main にマージ。秘密ファイルと GitHub secret は残しても害は無い
- 鍵の作り直し：スクリプト A をもう一度実行 → deploy → prod2 で `up -d alertmanager`
- V3（設計から）：`alertmanager_notifications_failed_total{integration="webhook"}` を見張るかは、反映後 7 日の数を見て決める

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/ai-ops-stage2-bin-c --claude`（origin/main 起点）。出力はパイプに通さない。最後に「Input must be provided」という表示が出て終了コードが 1 になることがあるが、作業場所の作成とは無関係（2026-10-14・10-16 実測）。作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-ai-ops-stage2-bin-c` と `git worktree list` の両方で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- commit は `PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:$PATH" git commit ...` で行う（`--no-verify` は使わない）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/ai-ops-stage2-bin-c -1 --oneline` で実在を確かめる
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）。作成後に `.pr-number` と `gh pr list --head release/ai-ops-stage2-bin-c --json number` の一致を確かめる
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/ai-ops-247/recon.md）・設計（docs/handoff/ai-ops-247/stage2-design.md）・このカード・ADR-1012 を書く。`触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし（良い例: 触るファイル: monitoring/alertmanager/alertmanager.yml, docker-compose.monitoring.yml, .github/workflows/monitoring-check.yml, docs/handoff/ai-ops-247/card-stage2-bin-c.md ／ 削除するファイル: に書くのは、差分に削除の行があるファイルだけ（§4-1 で置き換える alertmanager.yml と、§13 の「（未記入）」を書き換えるこのカード））
- 本文に「マージと prod2 への配置は Opus がカード §8 の順で行う」と 1 行書く
- 本文に鍵の値・鍵のパスを書かない。実在しないパスをバッククォートで書かない
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-4 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/ai-ops-stage2-bin-c/impl/）／判断を要した点（事実のみ）
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
