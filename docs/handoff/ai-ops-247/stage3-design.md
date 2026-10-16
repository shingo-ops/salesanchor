# 段階3 応急処置 — 便割りの設計

> この文書は何か：AI保守運用24時間化（ADR-1012）の段階3「応急処置」を、1便1目的の実装便に分けた設計です。親の設計は [design.md](design.md) §5 段階3（:112-118）。各便の作業指示書（カード）は、この文書を元に便ごとに作ります。

- 親設計: docs/handoff/ai-ops-247/design.md §5 段階3（:112-118）・受け入れ基準（:187）
- 前段: docs/handoff/ai-ops-247/stage2-design.md（段階2 は便A〜C の本番反映で完了。card-stage2-bin-c.md §15）
- KGI: docs/specs/ai-ops-247/kgi.md:22（KGI 3「一覧に載った症状は 5 分以内に機械が処置を終える。成功 95% 以上・悪化 0 件」）
- 対象ADR: ADR-1012（本テーマ・Proposed）、ADR-135（main マージ＝本番投入可）、ADR-136（危険 PR の GO）、ADR-1003（GO 委任）、ADR-079（cadvisor 無効化）
- 状態: 設計案作成済み・Opus 自己審査 APPROVE（§9）。段階3 の着手は PO の「次を進める」（2026-10-16）。便の分け方（§2）は PO 承認 y（2026-10-16）。V1 は便D のカード（card-stage3-bin-d.md §2-2）で解決。実装未着手
- 事実の生出力: /tmp/CC報告ファイル/ai-ops-stage3/recon_raw.md（Q1〜Q9）・recon_raw2.md（Q10〜Q16）。2026-10-16 取得・origin/main 057e12b16 基準。本番は読んでいない

## 1. 前提の事実（2026-10-16・origin/main 057e12b16 基準）

| # | 事実 | 出典 |
|---|---|---|
| F1 | celery-worker・celery-beat・discord-gateway・gemini-egress の 4 つに healthcheck が無い。4 つとも `restart: unless-stopped` | `docker-compose.yml:212-416`（healthcheck の行 0 件） |
| F2 | healthcheck があるのは backend など。backend は python の urllib で `localhost:8000/api/health` を叩く | `docker-compose.yml:151-156` |
| F3 | Docker の再起動の方針は「終了したとき」を契機に挙げており、unhealthy（健康診断の不合格）を契機とする記述は無い。repo に autoheal 相当の仕組みも無い | docs.docker.com/engine/containers/start-containers-automatically（2026-10-16 WebFetch。Context7 は月の上限で使えず）・`docs/handoff/ai-ops-247/recon.md:86` |
| F4 | HEALTHCHECK の既定は interval 30s・timeout 30s・start-period 0s・retries 3。連続して失敗すると unhealthy。終了コード 0=健康・1=不健康 | docs.docker.com/reference/dockerfile/#healthcheck（同上） |
| F5 | backend のイメージは python:3.12-slim で、curl・wget を入れる行が無い。gemini-egress は alpine＋openssh-client で、python・curl を入れる行が無い | `backend/Dockerfile:1,11-15`・`monitoring/prod1/gemini-egress/Dockerfile:3-5` |
| F6 | celery の生存は、60 秒ごとの heartbeat タスク（`backend/app/celery_app.py:176-180`）が backend の指標 `celery_heartbeat_last_success_timestamp_seconds`（`backend/app/metrics.py:34`）を更新し、CeleryHeartbeatStale（page）が見ている。このタスクは beat が出して worker が実行するので、止まったのがどちらかは区別できない | 同左・`monitoring/prometheus/alert_rules.yml` |
| F7 | Prometheus の scrape は 7 ジョブ。cadvisor は無効化済み（ADR-079）。コンテナごとの状態や unhealthy を表す指標は無い。4 サービスは scrape されないので ServiceDown（`up == 0`）に映らない | `monitoring/prometheus/prometheus.yml:69-72`・recon_raw2.md Q11 |
| F8 | prod1 の node-exporter は textfile ディレクトリ `/home/ubuntu/node_exporter_textfile` を読む。f2-cleanup はここに `f2_cleanup_last_success_timestamp` を mktemp→mv で書き、F2CleanupStale が見ている | `docker-compose.exporters.yml:11,17`・`scripts/f2-cleanup.sh:59-71` |
| F9 | tier=auto の見張りは 0 本（30 本中 page 13 本）。札 auto の意味は「段階3 で自動の応急処置が付いたもの」 | `docs/runbooks/alerts.md:9`・recon_raw.md Q4 |
| F10 | 保守 API の一覧（B2）の絞り込みは `status`・`since`・`limit` だけ。札（labels の tier）や処置済みかどうかでは絞れない。注記（B4）の kind は annotated/first_aid/ai。B4 は `first_aid_started_at`・`first_aid_done_at`・`first_aid_result` を更新できる。札は `labels` の jsonb に入る | `backend/app/routers/ops.py:275-281`・`:352`・`:238` |
| F11 | 全停止スイッチ（ops_control.halt_all）を読むコードは ops.py と試験のほかに 0 件。保守の鍵（OPS_API_TOKEN）で読む・ON にするはできるが、OFF（resume）は 403 | recon_raw.md Q6 追記・`backend/app/routers/ops.py:76-133` |
| F12 | nginx で IP を絞っているのは `/api/v1/ops/alertmanager` だけ。ほかの保守 API の口は `/api/` の扱いで、鍵だけで守る | `nginx/nginx.conf:388-390`・`:406-410` |
| F13 | OPS_API_TOKEN は deploy で GitHub secret から prod1 の `.env` に書かれる（prod1 に鍵の写しが既にある） | `.github/workflows/deploy.yml:290,335`・`docker-compose.yml:137` |
| F14 | prod1 の ubuntu の crontab は backup.sh・backup_to_s3.sh・f2-cleanup.sh の 3 本（root の crontab は未確認）。スクリプトは `/home/ubuntu/salesanchor/scripts/` を指し、通常の deploy で中身が入れ替わる | `docs/handoff/prod1-auto-cleanup/recon.md:120,123`・`docs/handoff/monitoring-disk-alerts/recon.md:116`・`docs/handoff/ai-ops-247/card-stage1-bin6.md:277` |
| F15 | prod1 のホストに python3 がある（deploy の ssh 内で使っている）。jq は repo に使用箇所 0 件（prod1 にあるかは未確認） | `.github/workflows/deploy.yml:362,491,662` |
| F16 | deploy は GitHub の runner から appleboy/ssh-action で prod1 に入って動く。migration のステップは `set -e` で失敗する。Finalize は `if: always()` で、backend の /api/health だけを待ち、通ればロールバックしない（migration の成否は見ない）。末尾の失敗通知は echo と exit 1 だけで Discord に出ない | `.github/workflows/deploy.yml:19-20`・`:526-544`・`:612-722`・`:1012-1017` |
| F17 | gha の指標を使う見張りは 0 本。deploy の失敗は今、障害記録にもアラートにも入らない | recon_raw2.md Q13 |
| F18 | deploy は 4 サービスを `docker compose up -d --no-deps --remove-orphans` で作り直す（celery-worker は直前に `stop -t 60`、ほかは `rm -f`）。4 サービスを `depends_on: condition: service_healthy` で待つ側は無い | `.github/workflows/deploy.yml:414-419`・`docker-compose.yml:144-147,264-268,305-307,349-351` |
| F19 | f2-cleanup は `set -uo pipefail`、ログは tee -a、成功のときだけ textfile を書く。二重起動の防止は無い | `scripts/f2-cleanup.sh:5,8,12,59-71` |
| F20 | 無制限鍵の例外は段階1 の完了で失効した。prod1 の crontab と prod2 の見張りの配置は PO の `!` スクリプトで行う | `docs/specs/ai-ops-247/kgi.md:43`・stage2-design.md:170 |

## 2. 便割り（1便1目的・上から順に 1 便ずつ反映して測る）

| 便 | 目的 | 触る場所 | 危険便 |
|---|---|---|---|
| D | 4 サービスに健康診断（healthcheck）を付ける。処置はしない | `docker-compose.yml`・discord-gateway の生存の印を書くコード（`backend/app/discord_gateway/`） | いいえ |
| E | コンテナの状態を見張りに載せる（記録まで。処置はしない） | scripts/ops/（新設）・`monitoring/prometheus/alert_rules.yml`・`docs/runbooks/alerts.md`・prod1 の crontab（PO の `!`）・prod2 の見張り（PO の `!`） | はい（`scripts/`） |
| F | 保守 API に「札 auto で未処置の一覧」と「直近の処置の数」の口を足す | `backend/app/routers/ops.py`・試験 | いいえ |
| G | 応急処置係（再起動とブレーキ） | scripts/ops/（新設）・処置の一覧（新設の scripts/ops/first_aid_actions.json）・`monitoring/prometheus/alert_rules.yml`・`docs/runbooks/alerts.md`・prod1 の crontab（PO の `!`） | はい（`scripts/`） |
| H | deploy の migration 失敗を見張りに載せる（障害記録と page） | `.github/workflows/deploy.yml`・`monitoring/prometheus/alert_rules.yml`・`docs/runbooks/alerts.md` | はい（deploy.yml） |

順番の理由：健康診断が無いと「不健康」という症状が生まれない（D → E）。症状が障害記録に載らないと応急処置係が読む物が無い（E → G）。応急処置係は F の口で「未処置」と「回数」を読む（F → G）。H は D〜G と独立しているので、G の後に行う（同時に 2 つ変えない）。

### 全体の流れ（親設計の「正本は障害記録 1 か所」を守る形）

```
コンテナが不健康（D の健康診断）
 → 状態書き係（E・prod1 の cron 毎分）が textfile に書く
 → prod2 の Prometheus が prod1 の node-exporter から読む
 → 見張り ContainerUnhealthy（札 auto）が鳴る
 → Alertmanager → Discord（人の目）＋ 保守 API（障害記録 1 件）
 → 応急処置係（G・prod1 の cron 毎分）が保守 API から「auto で未処置」を読む
 → 全停止スイッチ・回数の上限を確かめる → 一覧の処置（再起動）→ 前後の状態と結果を同じ障害記録へ
```

ホストで症状を見て直接処置を始めない（親設計 :116）。状態書き係は「記録の材料を書く」だけで、処置はしない。

### 便D 健康診断を付ける

- 4 サービスに healthcheck を足す。守ること:
  - 軽いこと：毎回アプリ全体を読み込む形（例：`celery inspect ping` は celery のアプリを毎回起動する）は避ける。prod1 はメモリが少ない（メモリ project prod1_memory_review）。目安は 1 回あたりの追加メモリ 30MB 以下・1 回 5 秒以内。
  - 自分自身を見ること：F6 の heartbeat のように、別のコンテナが止まっても不健康になる形は使わない（違うコンテナを再起動してしまう）。
  - イメージに無い道具を使わないこと（F5）。backend 系は python、gemini-egress は busybox の範囲。
- 方式の候補（どれにするかは便D のカードで、公式文書と手元の実測で決める。§7 V1）:
  - celery-worker：worker の中の印（ファイルの更新時刻）を python の 1 行で見る。印を何が書くか（celery の signal など）はカードで公式文書を確かめる
  - celery-beat：beat が書くファイル（`--schedule=/tmp/celerybeat-schedule`・`docker-compose.yml:296`）の更新時刻か、beat の signal で書く印
  - discord-gateway：gateway が接続を保っている間に印のファイルを更新する処理を足す（`backend/app/discord_gateway/main.py`）
  - gemini-egress：ssh のトンネルの待ち受けの口が開いているか（busybox の `nc -z`）
- 値の目安：interval 60s・timeout 10s・retries 3・start_period 120s（不健康と判定されるまで最長約 3 分。F4）
- 便D の測り方：手元の docker compose で、4 つとも健康になること、各プロセスを止める（`kill -STOP`）と 4 分以内に unhealthy になること。本番の反映後 24 時間、4 つが unhealthy に 1 回もならないこと（誤判定 0）

### 便E コンテナの状態を見張りに載せる

- 状態書き係 新設の scripts/ops/container_state.py（python3 の標準ライブラリだけ。F15）。prod1 の ubuntu の cron で毎分 1 回、`docker inspect` で 4 サービス（＋参考に backend）の状態を読み、textfile に次の 3 つを書く（F8 の f2-cleanup と同じ mktemp→mv の形）:
  - `salesanchor_container_unhealthy{service="..."}`（1 = unhealthy、0 = それ以外）
  - `salesanchor_container_running{service="..."}`（1 = 動いている）
  - `salesanchor_container_state_last_run_timestamp_seconds`（書いた時刻）
- 見張りを 2 本足す（`monitoring/prometheus/alert_rules.yml`）:
  - `ContainerUnhealthy`：`salesanchor_container_unhealthy == 1`、for 1m、札 **auto**、手順書リンクあり
  - `ContainerStateStale`：状態書き係が 5 分書いていない（`time() - ... > 300` か absent）、for 2m、札 page
- cron の 1 行は PO の `!` スクリプトで足す（F20）。ログは異常のときだけ書く（毎分の記録でディスクを使わない）
- 便E の測り方：手元で celery-beat を `kill -STOP` → ContainerUnhealthy が鳴り、障害記録に 1 行・Discord に 1 件。本番は反映後に `salesanchor_container_unhealthy` が 4 サービスぶん 0 で読めること（Prometheus の問い合わせ）と ContainerStateStale が鳴っていないこと

### 便F 保守 API の口を足す

| # | 口 | 鍵 | 動き |
|---|---|---|---|
| B7 | `GET /api/v1/ops/incidents` に `tier`・`first_aid`（`pending`）の絞り込みを足す | 保守の鍵 または super admin | `labels->>'tier' = 'auto'` かつ `status = 'firing'` かつ `first_aid_started_at IS NULL` の行。既存の引数はそのまま |
| B8 | `GET /api/v1/ops/events?kind=first_aid&since=...`（最大 100 件） | 同上 | 直近の処置の出来事（回数の上限の数えに使う。detail の `service` で数える） |

- 書き込み側は既存の B4（注記と first_aid_* 列の更新）を使う。新しい表・列・migration は作らない（処置の前後の状態は events.detail の 8KB に収まる）
- 便F の測り方：pytest（tier と pending の絞り込み・処置後は一覧から消える・events の kind と since の絞り込み・鍵なし 401・受け口の鍵では 401）

### 便G 応急処置係

- 新設の scripts/ops/first_aid.py（python3 の標準ライブラリだけ）。prod1 の ubuntu の cron で毎分 1 回、`flock -n` で二重起動を防ぐ（F19 の穴を塞ぐ）
- 保守 API へは `https://api.salesanchor.jp` を prod1 自身の 443 へ向けて呼ぶ（ホスト名は保ち、行き先を prod1 に固定する。届くかは便G のカードの前に PO の `!` で確かめる。§7 V2）。鍵は prod1 の `.env` の OPS_API_TOKEN を読む（F13。新しい鍵は作らない・画面にもログにも出さない）
- 1 回の流れ:
  1. `GET /control`。halt_all が true なら何もせず終わる（処置 0 件）。保守 API に届かないときも何もしない（親設計 :116）
  2. B7 で「auto で未処置」を読む
  3. 1 件ごとに、alertname と labels.service を処置の一覧（新設の scripts/ops/first_aid_actions.json）と照らす。一覧に無ければ何もしない
  4. 回数の上限：B8 で同じ service の直近 1 時間の処置を数え、3 回以上なら処置せず `first_aid_result=escalated` を書き、textfile に `salesanchor_first_aid_escalated_timestamp_seconds{service}` を書く（→ 見張り FirstAidEscalated・札 page が Discord と障害記録に上げる）
  5. 起動から 5 分以内のコンテナには処置しない（deploy の作り直し・起動直後と取り合わない。F18）。次の回にもう一度見る
  6. 先に `first_aid_started_at` を書く（同じ障害に 2 回処置しないための札）→ 前の状態（Health・StartedAt・RestartCount）を記録 → `docker compose restart <service>` → 最長 3 分、健康になるのを待つ → 後の状態を記録 → `first_aid_done_at` と `first_aid_result`（recovered/not_recovered）を書く。not_recovered は textfile の escalated にも書いて page に上げる
  7. `first_aid_started_at` があって 10 分たっても `first_aid_done_at` が無い行は escalated にする（係が途中で落ちたとき）
- 処置の一覧（初版）：ContainerUnhealthy で service が celery-worker・celery-beat・discord-gateway・gemini-egress のとき、そのコンテナを `docker compose restart`。backend・postgres・redis・nginx は載せない（利用者への影響が大きい、または DB の再起動は不可逆に近い）。一覧に足すのは PR だけ
- 見張りを 2 本足す：`FirstAidEscalated`（札 page）・`FirstAidStale`（係が 5 分動いていない。札 page）。ContainerUnhealthy の手順書に処置の内容を書く
- 便G の測り方：§6 の段階3 の基準

### 便H deploy の migration 失敗を見張りに載せる

- deploy.yml の migration のステップ（:526-544）の中で、成功したら `salesanchor_deploy_migration_last_success_timestamp_seconds`、失敗したら `salesanchor_deploy_migration_last_failure_timestamp_seconds` を prod1 の textfile に書く（ステップは既に prod1 に ssh して動いている。F16）。失敗の後に `exit 1` するのは今のまま
- 見張り `DeployMigrationFailed`：失敗の時刻が成功の時刻より新しい、for 0m、札 page。次の成功で自然に止む
- ロールバックの条件は変えない（親設計 :118。変えるなら別カードの危険 PR）
- 便H の測り方：手元で migration のステップの書き込みを試験し、見張りの式を promtool の単体試験（`promtool test rules`）で確かめる。本番では失敗を起こさない（成功の時刻が書かれ、見張りが鳴っていないことを確かめる）

## 3. 親設計からの変更点と理由

1. 症状の入り口：親設計は「札 auto の障害記録を読む」とだけ書き、その障害記録がどこから来るかは書いていない。コンテナの状態を表す指標が無い（F7）ので、prod1 の textfile に状態を書く係（便E）を足す。cadvisor（ADR-079 で無効化）や docker の操作権を持つ新しいコンテナ（親設計 :115 で不採用）は使わない
2. AI の処置依頼：親設計 :116 は「AI の処置依頼」も読むとする。依頼を出す AI は段階4 で作るので、段階3 では作らない。段階4 の設計で、依頼を障害記録の注記（kind=ai）で表し、同じ応急処置係が同じ一覧・同じブレーキで実行する形を決める
3. page への上げ方：応急処置係が Discord に直接書くのではなく、textfile → 見張り（FirstAidEscalated）→ Alertmanager の既存の経路で上げる。新しい鍵も新しい通知経路も作らず、上げたことも障害記録に残る
4. 処置前後の記録：専用の表は作らず、events.detail（8KB）と first_aid_* 列（段階2 で用意済み）を使う

## 4. 段階3 で決めると書いた未解決事項の扱い

- U5（Alertmanager を通らない直通通知を寄せるか・stage2-design.md:183）：**寄せない**。理由：直通の 2 経路（Kuma の既存 4 件・`scripts/backup_to_s3.sh:56-70`）は監視基盤とバックアップの失敗で、段階3 の処置の一覧（コンテナの再起動）の対象にならない。寄せると Alertmanager が止まったときに通知も止まる。段階6 の成績表で直通の分が KGI 1・2 の集計から漏れることは、段階6 の設計で扱う
- 段階2 から移した基準「全停止スイッチ ON で処置 0 件」（stage2-design.md:208）：§6 に入れる。AI 起動 0 件は段階4 の基準に残す

## 5. 弊害と対処

| 弊害 | 起きること | 対処 |
|---|---|---|
| 健康診断の誤判定 | 健康なのに unhealthy → 不要な再起動 | 便D の後 24 時間、処置なしで誤判定 0 を確かめてから便E・G に進む。回数の上限 1 時間 3 回 |
| 再起動の繰り返し（AWS 2025-10 の型） | 直らない原因で何度も再起動 | 1 時間 3 回で止めて page。全停止スイッチを毎回確認 |
| deploy との取り合い | deploy の作り直しの最中に再起動 | 起動から 5 分以内は処置しない。同じ障害は `first_aid_started_at` で 1 回だけ |
| 応急処置係が落ちる | 処置されないまま | FirstAidStale（page）。Discord の通知は Alertmanager から別に届くので人の目には残る |
| 鍵の写しが prod1 にある | prod1 を取られると保守の鍵も読まれる | 鍵は既に prod1 の `.env` にある（F13）ので、増える露出は無い。保守の鍵では止めを外せない（F11） |
| 健康診断の負荷 | prod1 のメモリが減る | 1 回 30MB 以下・5 秒以内を便D のカードの合格条件にする |
| 誤報の増加 | auto の通知も Discord に出る | auto は処置されると数分で resolved になる。雑音が多ければ段階6 で Discord への出し方を見直す |
| beat の再起動で予定が飛ぶ | 再起動の間の定期作業 1 回分が抜ける | 本番の試験は celery-beat で 1 回だけ、PO に日時を伝えてから（親設計 :187）。beat の予定表は今も deploy のたびに作り直している（`/tmp`・`docker-compose.yml:296`） |

## 6. 受け入れ基準（段階3 全体）

| 基準 | 検証方法 |
|---|---|
| 便D: 4 サービスが健康になり、プロセスを止めると 4 分以内に unhealthy。本番で 24 時間 unhealthy 0 回 | 手元の docker compose の `docker inspect` の生出力。本番は状態書き係の値（便E の後）または PO 実行の `docker ps` |
| 便D: 健康診断 1 回の追加メモリ 30MB 以下・5 秒以内 | 手元の実測（`docker stats` と所要時間） |
| 便E: 手元で celery-beat を止めると ContainerUnhealthy（札 auto）が鳴り、障害記録 1 行・Discord 1 件 | 手元の docker compose（`docker-compose.yml` と `docker-compose.monitoring.yml` を同時に起動）の生出力 |
| 便E: 本番で 4 サービスの値が読め、ContainerStateStale が鳴っていない | Prometheus の問い合わせの結果 |
| 便F: pytest で、auto かつ未処置だけが一覧に出る・処置後に消える・events の絞り込み・鍵の取り違えで 401 | CI の pytest |
| 段階3（便G）: 一覧の症状を起こすと、障害記録の `first_notified_at` から `first_aid_done_at` まで 5 分以内で、`first_aid_result=recovered` | 手元の docker compose で 4 サービス × 5 回 = 20 回。成功率（95% 以上 = 19 回以上）と時間を記録（親設計 :187） |
| 段階3: 上限を超えると止まって page | 手元で同じ service を 1 時間に 4 回不健康にし、4 回目は再起動せず escalated・FirstAidEscalated が鳴る |
| 段階3: 全停止スイッチ ON で処置 0 件（stage2-design.md:208 から移した基準） | 手元で ON にして症状を起こし、再起動 0 件・障害記録の first_aid_* が空のまま |
| 段階3: 一覧に無い症状・一覧に無いコンテナには処置 0 件 | 手元で backend を不健康にして再起動 0 件 |
| 段階3: 本番で celery-beat を 1 回だけ不健康にし、5 分以内に回復 | PO に日時を伝えてから 1 回（親設計 :187）。障害記録の時刻の生出力 |
| 便H: migration の失敗で DeployMigrationFailed が鳴り、成功で止む | `promtool test rules` の CI 結果と、手元での書き込みの試験。本番の反映後に成功の時刻が書かれていること |
| 悪化 0 件 | 処置の後 30 分に、同じ機体で新しく鳴った障害記録の数（手元の 20 回と本番の 1 回） |

## 7. 未解決事項

- V1: 便D の健康診断の方式（§2 便D の候補）。celery の signal など公式の仕様に依存するので、便D のカードの前に公式文書（Context7 か公式サイト）と手元の実測で決める。決まるまで便D のカードを出さない
  - 解決（2026-10-16・Opus 技術判断）：worker は bootstep の timer、beat は Scheduler の子クラスの tick、gateway は asyncio の定期処理で、/tmp の印のファイルを触る。健康診断は印の古さを sh・date・stat で見る。gemini-egress は待ち受けの口ではなく、トンネルの先の tinyproxy の統計ページまで busybox wget で通す（口が開いていても固まりは見えないため）。根拠と細部は card-stage3-bin-d.md §2
- V2: prod1 のホストから `api.salesanchor.jp` を prod1 自身に向けて呼べるか（ヘアピン）・ubuntu の cron から docker を操作できるか・prod1 の python3 の版。便E のカードの前に PO の `!`（読み取りだけ）で確かめる
- V3: （段階2 から）Alertmanager の webhook の失敗の見張り。10/23 に失敗の数を見て決める
- V4: prod1 の Prometheus の scrape の間隔（node-exporter app-vps）。5 分の予算（§6）に効くので便E のカードで `monitoring/prometheus/prometheus.yml` を読んで確かめる
- V5: 処置の一覧に CeleryHeartbeatStale（beat か worker か区別できない・F6）を足すか。便G の後、ContainerUnhealthy の実績を見て決める

## 8. 戻し方

- 全体を止める：全停止スイッチを ON（保守の鍵で可）。応急処置係は処置しなくなる
- 便G・便E：PO の `!` で crontab の 1 行を消す → PR の revert。見張りは revert して prod2 に再配置
- 便F：PR の revert（口が増えただけ。書き込みは無い）
- 便D：PR の revert → 次の deploy で healthcheck が外れる
- 便H：PR の revert（textfile の値は残っても、見張りが無ければ鳴らない）

## 9. 自己審査（Opus。同一 AI による審査で、独立した第二者レビューではない）

判定：APPROVE（便割りとして実装に渡せる。便ごとのカードは別に作り、card-lint を通す。V1・V2 が閉じるまで便D・便E のカードは出さない）

| 観点 | 結果 | 根拠 |
|---|---|---|
| 親設計の目的・範囲と合う | ○ | §3 の変更 4 点は、親設計が書いていなかった症状の入り口の補いと、AI 依頼を段階4 に寄せた点。親設計の「docker の操作権を持つコンテナを作らない」「記録より先に処置しない」「ブレーキ」は守る |
| 正本の 1 か所化 | ○ | 処置の契機も結果も障害記録（アプリ DB）。textfile は材料で、page への上げ方も Alertmanager の既存の経路 |
| 事実に根拠がある | ○ | §1 F1〜F20 に file:line・公式文書・生出力 |
| 受け入れ基準が○×で判定できる | ○ | §6 は回数・分・件数・結果の値で判定 |
| 実装の範囲が明確 | ○ | 便ごとに触る場所（§2 の表） |
| 未確認に依存する合格が無い | ○ | V1・V2・V4 はカードを出す前に閉じる条件にした。この設計の合格は便の分け方と仕組みの形に対してで、未確認の方式には依存しない |
| 外部の仕様 | ○（一部未確認） | Docker の healthcheck と再起動の方針は公式文書を直接読んだ（F3・F4）。celery の signal は V1 で確かめる |

## 10. 外部・過去事例の参照と我々への応用

- 親設計 design.md §7 の事例を引き継ぐ。段階3 に直接効くのは AWS us-east-1 の障害（AWS 公式ポストモーテム https://aws.amazon.com/message/101925/ 、2025-10-19〜20）。自動化が戻れない変更を書き、AWS は自動化を止めて 1 回に変えられる量の上限を足した → 応用：1 時間 3 回の上限・全停止スイッチ・処置前後の記録
- Google SRE book 第 6 章（https://sre.google/sre-book/monitoring-distributed-systems/ ）「ロボット的対応で済むものはページにしない」→ 応用：札 auto（人を起こさず機械が処置）と、直らないときだけ page に上げる形
- Docker 公式（F3・F4）：再起動の方針は終了を契機とし、unhealthy での再起動は書かれていない → 応用：健康診断を足すだけでは直らないので、応急処置係を作る
- 過去事例（社内）：f2-cleanup の textfile と見張り（F8）→ 応用：同じ置き方で状態と上げ方を作る。f2-cleanup に二重起動の防止が無い点（F19）は、応急処置係では flock で塞ぐ
- 限界：小さな 1 人運用のサービスで自動再起動の成功率を測った外部の数字は見つけていない。成否は §6 の実測（手元 20 回・本番 1 回）だけで判定する

## 維持の仕組み

- 守り手：CI の pytest（便F の絞り込み）・`monitoring/scripts/check_alert_rules.py`（札と手順書リンクの欠け）・`promtool test rules`（便H の見張り）・便7 の毎日の照合（alert_rules.yml の本番と repo のずれ）・FirstAidStale と ContainerStateStale（係そのものの見張り）
- 担当：処置の一覧（新設の scripts/ops/first_aid_actions.json）は ADR-1012 のテーマとして Opus が設計し、足すのは便ごとのカード → PR → 審査 → GO → 反映の順。本番で一覧を手で書き換えない
- 見直し：便G の後 30 日の障害記録で、成功率・escalated の数・誤判定の数を見て、一覧と上限を見直す（V5 もここで判断）
