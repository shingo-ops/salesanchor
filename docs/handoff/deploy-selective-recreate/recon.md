# recon: deploy の「全 app コンテナ rm -f → up」を「残り物と重複だけ消す + up 既定」に変える

- 基準: origin/main 57090e457（worktree `/Users/tanizawashingo/worktrees/salesanchor/release-deploy-selective-recreate`）
- 調査日: 2026-10-07。本番は読み取りのみ（`docker ps` / `docker inspect` / `docker compose config --hash`）。製品コード・deploy.yml・本番は未変更。
- 引用パスは worktree 基準のフルパス（以下 `W` = `/Users/tanizawashingo/worktrees/salesanchor/release-deploy-selective-recreate`）。

## KGI（PO 承認済み 2026-10-07）
1. 画面だけ変えたデプロイ後、celery-worker の StartedAt が変わらない。
2. backend のプログラムを変えたデプロイ後は、celery-worker が作り直されている。
3. デプロイ後、各サービスのコンテナがちょうど1つずつ。重複も別プロジェクト名の残り物もない。

## a. 既存 ADR の検索結果
検索: `W/docs/adr/FEATURE-INDEX.md` と `git grep -i`（deploy / rm -f / recreate / blue-green / orphan / ADR-092 / astro-webapp）。

関係するもの:
| ADR | ファイル | 関係 |
|---|---|---|
| ADR-092 | `W/docs/adr/ADR-092-deploy-concurrency-control.md:43-57` | 本変更の対象そのもの（pre-cleanup = rm -f の根拠）。要点は e 節 |
| ADR-137 | `W/docs/adr/ADR-137-nginx-config-deploy-reliability.md`（FEATURE-INDEX `W/docs/adr/FEATURE-INDEX.md:50`） | nginx のみ条件付き force-recreate。今回の対象外（維持） |
| ADR-082 | `W/docs/adr/ADR-082-deploy-skip-migrations-on-frontend-only.md` | 画面のみデプロイで migration を skip。KGI 1 の「画面だけ変えたデプロイ」の判定と同じ paths-filter（`W/.github/workflows/deploy.yml:33-46`） |
| ADR-115 | `W/docs/adr/ADR-115-deploy-safety.md` | deploy 安全性。ロールバックの節に関係（内容の精読は未実施） |
| ADR-135 / ADR-136 | `W/docs/adr/FEATURE-INDEX.md:37`、CLAUDE.md | deploy.yml は危険パス。PO の「GO #PR番号」が必要 |
| ADR-130 | `W/docs/adr/ADR-130-nginx-reload-policy.md` | nginx reload。blue-green と bootstrap 後の reload |
| 参考 | `W/docs/adr/FEATURE-INDEX.md:59` | ADD 系 migration は blue-green cutover 前に実行される、という既知リスク |

関連 handoff: `W/docs/handoff/blue-green-cutover-error-handling/`、`W/docs/handoff/extraction-job-recovery/design.md`（celery-worker warm shutdown §B-3）、`W/docs/handoff/gemini-egress-via-prod2/`。
「rm -f を毎回やめて差分だけにする」を扱う ADR は、検索の範囲では**見つからなかった**（ADR-092 の中で「別Issueで最適化」と PR #1402 のレビューに書かれているのみ。e 節）。

## b. deploy.yml の処理（origin/main、全文引用）

### 並行実行の制御 `W/.github/workflows/deploy.yml:8-16`
```
# 連続リリースで deploy.yml が並行実行されると、Docker コンテナ名衝突
# （Conflict. The container name "/astro-webapp-backend-1" is already in use）で
# backend が起動できず 502 になる（2026-06-02 #1390/1395/1396 の 9 分間連続マージで実発生）。
# 同一グループで直列化し、並行実行を防ぐ。
# cancel-in-progress: false — migration 実行中に後続がキャンセルすると DB が
# 中途半端な状態になる危険があるため、キャンセルせずキュー待ちにする（ADR-092）。
concurrency:
  group: deploy-production
  cancel-in-progress: false
```

### 変更検出 `W/.github/workflows/deploy.yml:33-46`
```
      - name: Detect backend / migration changes
        uses: dorny/paths-filter@v4
        id: changes
        with:
          filters: |
            migrations:
              - 'migrations/**'
              - 'scripts/**'
              - 'backend/**'
              - 'docker-compose.yml'
              - '.github/workflows/deploy.yml'
            nginx:
              - 'nginx/**'
              - 'docker-compose.yml'
```

### .env への COMPOSE_FILE 追記 `W/.github/workflows/deploy.yml:282,315`
```
              -e '/^COMPOSE_FILE=/d' \
...
            COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml
```

### build `W/.github/workflows/deploy.yml:348-370`
```
            echo "Step 3: Rebuilding and restarting containers..."
            # build と up を分離してダウンタイムを最小化する。
            # --build を up と一体で実行すると旧コンテナ停止後にビルドが走り（最大2分程度）
            # その間 nginx が 502 を返す問題があった（2026-05-30 障害）。
            # build を先に完了させてから up（切り替えのみ）を実行することで
            # ダウンタイムをコンテナ再起動の数秒に短縮する。
            #
            # Docker bridge 一時エラー対策（2026-06-02 調査）:
            # VPS カーネルが "adding interface veth to bridge docker0 failed: Device does not exist"
            # を返す場合がある（一時的な netns 状態異常）。15秒待ってリトライすると解消する。
            BUILD_OK=false
            for _build_attempt in 1 2 3; do
              if docker compose build; then
                BUILD_OK=true
                break
              fi
              echo "Build attempt ${_build_attempt} failed. 15秒後にリトライ..."
              sleep 15
            done
            if [ "$BUILD_OK" != "true" ]; then
              echo "docker compose build が3回失敗しました"
              exit 1
            fi
```

### blue-green の呼び出しと、非 backend の rm -f + up `W/.github/workflows/deploy.yml:371-396`
```
            # blue-green: backend を無停止で切替（scripts/blue-green-cutover.sh）
            #   旧コンテナを先に削除しないことで、Python 初期化 (~22s) 中の 502 を排除する。
            #   [before] docker rm -f backend → up → 22s 502 → healthy
            #   [after]  green 起動 → health 確認 → nginx 切替 → 旧停止 → 502 ゼロ
            echo "Step 3b: Blue-green backend cutover..."
            bash scripts/blue-green-cutover.sh

            # backend 以外（frontend/celery-beat/discord）は従来の force-rm + up で切替。
            # これらは nginx 経由の同期 API のリクエストパスに関与しないため
            # 数秒のダウンは発生しない（frontend は静的配信、celery-beat/discord は非同期）。
            # discord-gateway: 重複起動による Discord 再接続storm→token reset を防ぐため
            # 旧コンテナを先に削除してから起動する（従来動作を維持）。
            #
            # celery-worker だけは別扱い（docs/handoff/extraction-job-recovery/design.md §B-3）:
            # task_acks_late=True で実行中タスクを抱えている場合があるため、
            # 強制削除（docker rm -f）の前に `docker compose stop -t 60` で
            # warm shutdown（SIGTERM→最大60秒待って実行中タスクを終える）してから止める。
            echo "Step 3c: Updating non-backend services (frontend/celery/discord)..."
            docker compose stop -t 60 celery-worker 2>/dev/null || true
            for _svc in frontend celery-beat discord-gateway; do
              docker ps -a --filter "name=astro-webapp-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
            done
            docker ps -a --filter "name=astro-webapp-celery-worker" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
            docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress
            echo "Step 3d: Ensuring monitoring collectors are up..."
            docker compose up -d --no-deps node-exporter promtail
```
（`W/.github/workflows/deploy.yml:371-396` を逐語で引用。）

### 条件付き force-recreate（nginx）`W/.github/workflows/deploy.yml:419-434`
```
      - name: Recreate nginx (apply config/volume changes)
        if: ${{ success() && steps.changes.outputs.nginx == 'true' }}
...
            docker compose up -d --no-deps --force-recreate nginx
```
（`:430` が本体。`:406-418` のコメントは ADR-137 の inode ズレ対策の説明。）

### 条件付き force-recreate（SA-18、DATABASE_URL 変更時のみ）`W/.github/workflows/deploy.yml:476-486`
```
              if [ "${_url_changed}" = "true" ]; then
                # DATABASE_URL が変更 → backend/celery/discord を再起動する。
                # --force-recreate ではなく blue-green で無停止切替する（ダウンタイム排除）。
                # celery/discord は非同期・非ユーザー向けのため従来の force-recreate を維持。
                echo "ℹ️  SA18: DATABASE_URL が変更 → blue-green で backend を再起動します..."
                BG_HEALTH_TIMEOUT=90 bash scripts/blue-green-cutover.sh
                echo "ℹ️  SA18: celery/discord を --force-recreate で切替..."
                docker compose up -d --force-recreate celery-worker celery-beat discord-gateway
              else
                echo "ℹ️  SA18: DATABASE_URL 変更なし → blue-green をスキップ（切替1回のみ）"
              fi
```
（`:483` が force-recreate。`SA18_PHASE2_ENABLED=1` が .env にあるときだけ入る分岐 `:463`。）

### ロールバックの節 `W/.github/workflows/deploy.yml:642-672`
```
                # 旧コードでビルド（最大3回リトライ）
                _rb_build=false
                for _attempt in 1 2 3; do
                  if docker compose build 2>&1; then
                    _rb_build=true
                    break
                  fi
                  echo "Rollback build attempt ${_attempt} failed. 15秒後にリトライ..."
                  sleep 15
                done

                if [ "${_rb_build}" = "true" ]; then
                  # コンテナ差し替え（通常デプロイと同じパターン）
                  for _svc in backend frontend celery-worker celery-beat discord-gateway; do
                    docker ps -a --filter "name=astro-webapp-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
                  done
                  docker compose up -d --remove-orphans
```
（`:655-658`。ロールバックは backend も rm -f する別経路。blue-green を使わない。）

### prune `W/.github/workflows/deploy.yml:719-726`
```
            echo "Step 8: Cleaning up old Docker images..."
            docker image prune -f

            echo "Step 8b: Cleaning up Docker build cache (keep 3GB)..."
            ...
            docker builder prune -f --max-used-space 3GB || true
```

## c. scripts/blue-green-cutover.sh が backend にすること
- `W/scripts/blue-green-cutover.sh:26` プロジェクト名を `COMPOSE_PROJECT="astro-webapp"` と**直書き**。
- `:58-65` 残留 green（`astro-webapp-backend-green`）があれば `docker rm -f`。
- `:70` イメージは `astro-webapp-backend`（直前の `docker compose build` の産物）。
- `:80-105` **`docker run -d --name astro-webapp-backend-green`** で起動（compose 経由ではない）。`--label com.docker.compose.project/service/container-number/project.working_dir/project.config_files/oneoff` を手で付与。`com.docker.compose.config-hash` と `com.docker.compose.image` は**付けていない**。
- `:113-124` /api/health を最大 60s（既定）ポーリング。失敗なら green を除去して exit 1（旧 backend は継続）。
- `:142` green を frontnet に `--alias backend` で接続、`:145` 旧 backend を frontnet から切断、`:150` `nginx -s reload`。
- `:155-156` 旧 backend を `docker stop --time=40` → `docker rm`。
- `:161` green を `astro-webapp-backend-1` に `docker rename`。
- 結果: 本番の backend コンテナは compose が作ったものではなく、手作りラベルのコンテナ（i 節で実測）。

## d. docker-compose.yml の各 app サービス（`W/docker-compose.yml`）
| 項目 | 結果（根拠） |
|---|---|
| トップレベル `name:` | **無し**（`grep -n '^name:' W/docker-compose.yml` が 0 件） |
| `container_name` | **どのサービスにも指定無し**（grep 0 件）。名前は Compose が `<project>-<service>-1` で付ける |
| `labels:` | **指定無し**（grep 0 件） |
| `COMPOSE_PROJECT_NAME` | リポジトリ（docs/adr 除く）に記載無し。**本番 `.env` に `COMPOSE_PROJECT_NAME=astro-webapp` が 1 行ある**（i 節の実測。値は project 名で秘密ではない） |
| `COMPOSE_FILE` | deploy が毎回 `.env` に `COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml` を書き込む（`W/.github/workflows/deploy.yml:282,315`）。本番 `.env` にも同値を確認 |
| サービス行 | nginx `:5` / certbot `:42` / backend `:63` / frontend `:162` / celery-worker `:198` / celery-beat `:272` / discord-gateway `:309` / gemini-egress `:357` / redis `:395` / postgres `:425` / gha-exporter `:463`（`W/docker-compose.yml`）。node-exporter / promtail は `W/docker-compose.exporters.yml:4,85` |
| celery-worker の停止猶予 | `W/docker-compose.yml:252-253` `stop_signal: SIGTERM` / `stop_grace_period: 60s` |
| gemini-egress | `W/docker-compose.yml:357-392`。`build: ./monitoring/prod1/gemini-egress`、`restart: unless-stopped`、volume は ssh 鍵、environment 無し、depends_on 無し |

project 名の出どころ: 本番 `/home/ubuntu/salesanchor/.env` の `COMPOSE_PROJECT_NAME=astro-webapp`（作業ディレクトリ名 `salesanchor` ではない）。この行が .env に入った経緯（誰がいつ入れたか）は**未確認**。deploy.yml が `.env` を sed で再構成する箇所（`:282` 付近）に COMPOSE_PROJECT_NAME の行は無い＝デプロイでは触られず、手で置かれたまま残っている形。

## e. ADR-092 の要点と PR #1402

### ADR-092（`W/docs/adr/ADR-092-deploy-concurrency-control.md`）
- `:14-25` 背景: deploy.yml に concurrency が無く、連続マージで並行実行 → `Conflict. The container name "/astro-webapp-backend-1" is already in use`（+ `Error while Stopping`）→ backend が Created のまま → nginx 502。2026-06-02 10:53〜11:04 JST、#1390 / #1395 / #1396。
- `:29-41` 決定1: `concurrency: group deploy-production / cancel-in-progress: false`。
- `:43-49` 決定2（今回の対象）: 「`docker compose up` の前に、graceful stop に失敗した / ハッシュ付きプロジェクト名の残留コンテナ（前回デプロイの失敗残骸）を `docker rm -f` で明示的に削除する。`docker compose up --remove-orphans` ではプロジェクト名が異なる残留コンテナを削除できないため直接対処する。postgres / redis / nginx / certbot は filter 名が一致しないため削除対象外。」
- `:51-57` pre-cleanup は PR #1402 で実装済み。「discord-gateway を含めることで、デプロイ時の gateway 重複起動による Discord 再接続storm（→ Bot Token 自動リセット）も防ぐ」。
- `:63` 「2026-05-30 障害対策『build 先行によるダウンタイム最小化』は維持（`down` を使わない）」。

### PR #1402（`gh pr view 1402 --repo shingo-ops/salesanchor`、MERGED 2026-06-02T03:13:48Z、タイトル「fix(ops): デプロイの名前衝突502 と discord-gateway 再接続storm を防止」）
本文より:
- 「**502**: 11:02 JST の release デプロイが `docker compose up` 時の **backend コンテナ名衝突**（`"astro-webapp-backend-1" is already in use` + `Error while Stopping`）で失敗 → backend 未起動 → 502。既存の up前掃除は **frontend のみ**で backend を対象外だった。」
- 「up 前のコンテナ掃除を frontend のみ → 全 app 系（backend/frontend/celery-worker/celery-beat/discord-gateway）に拡張。」「効果: (a) graceful stop 失敗/ハッシュ付き重複コンテナを force 削除 → 名前衝突 502 を防止、(b) discord-gateway の重複起動を防止」
- 「postgres/redis/nginx/certbot は状態保持のため対象外。」

レビューコメント（Hikky-dev、「APPROVE 相当」）より:
- 「`<hash>_astro-webapp-backend-1` は `astro-webapp-backend` を substring として含むため確実に force 削除される（本来の目的どおり）。」
- 「Out-of-scope follow-ups: 毎デプロイで app 系 5 コンテナを force 削除 → 数秒ダウンは本 PR で受容するトレードオフ。`docker compose up -d --force-recreate` は名前衝突（ハッシュ付き孤児コンテナ）を解消できないため、本障害の根本対処としては force 削除のほうが正しい選択。ただし『正常稼働中も毎回 force 削除』する点は、将来 `docker rm -f` 対象を『孤児/重複コンテナのみ（`docker compose ps -q <svc>` の結果と差分を取る）』に絞れば無停止デプロイに近づけられる。緊急対応としては現状で妥当、最適化は別 Issue。」
- → 本件の設計方針（残り物と重複だけ消す）は、レビュー時点で想定済みの最適化。

## f. 6月の障害2件の原因（記録の引用）
### 1. 名前の衝突（なぜ別プロジェクト名のコンテナが残ったか）
- 記録されている原因（ADR-092 `:14-20`、PR #1402 本文）: deploy の**並行実行**で、先行ジョブが stop 中に後続が同名コンテナを作ろうとし `Conflict ... already in use` + `Error while Stopping`。backend が Created のまま止まった。
- 「ハッシュ付きプロジェクト名の残留コンテナ」（ADR-092 `:45`）と「`<hash>_astro-webapp-backend-1`」（PR #1402 レビュー）という記述はある。これは Compose が stop/recreate の途中で作る一時名のコンテナ（`<12桁hash>_<元の名前>`）の形を指すとレビューは述べている。
- **なぜ「別のプロジェクト名」になるのか、の一次記録（ログ・実物の docker ps 出力）は、リポジトリ内の検索では見つからなかった**（`git grep` で ADR-092 以外に記述無し）。→ 未確認。
- 現在の本番にはそのような残り物は無い（i 節）。

### 2. discord-gateway の重複起動
- ADR-092 `:55-57`: 「デプロイ時の gateway 重複起動による Discord 再接続storm（→ Bot Token 自動リセット、別途 #1402 で対処）」「2026-06-02 障害記録: discord-gateway Bot Token リセット（短時間 >1000 接続検知による Discord 側自動リセット）」。
- PR #1402 本文: 「Discord が『短時間に1000回以上接続』を検知し Bot Token を自動リセット → 旧トークンで LoginFailure。`run_gateway` のアプリ内再接続 + Docker `restart: unless-stopped` の二層増幅 + （デプロイ時の）gateway 重複起動が storm の温床。」
- 対策は二つ: ①deploy の rm -f（重複を作らない）、②`backend/app/discord_gateway/main.py` の致命時クールダウン（`DISCORD_GATEWAY_FATAL_COOLDOWN` 既定 60s）。**②は今回変更しない限り残る**。
- 設計上の含意【事実からの整理】: discord-gateway は「同時に2つ起動させない」ことが要件。compose の既定の recreate は「古いのを stop → 新しいのを作る」順で、同名コンテナが同時に走らない形（公式 `docker compose up` の説明 g 節）。ただし、これが discord-gateway で重複を起こさないことの実証は未実施（未確認）。

## g. docker compose の公式の動作
Context7（`/docker/docs`、`/docker/compose`）と docs.docker.com で確認。

- **up の既定**: https://docs.docker.com/reference/cli/docker/compose/up/ ／ Context7 `/docker/docs` の `compose_up.md`: 「If there are existing containers for a service, and the service's configuration or image was changed after the container's creation, `docker compose up` picks up the changes by stopping and recreating the containers (preserving mounted volumes). To prevent Compose from picking up changes, use the `--no-recreate` flag.」「`--force-recreate`: Recreate containers even if their configuration and image haven't changed」
- **--remove-orphans**: 同ページ: 「Remove containers for services not defined in the Compose file」。Context7 `envvars.md` の COMPOSE_REMOVE_ORPHANS: 「Orphaned containers are those that were created by a previous configuration but are no longer defined in the current compose.yaml file.」
  - 「同じ project 名のものだけが対象か」は、取得した公式文面には**明記されていない**（未確認）。ADR-092 `:47` は「プロジェクト名が異なる残留コンテナを削除できない」と書くが、これは ADR の主張であり、本調査では公式文面で裏取りできていない。Compose はコンテナの `com.docker.compose.project` ラベルで project を絞る（下記ラベルの定義から読めるが、孤児判定コードの精読はしていない）。
- **ラベル**（Context7 `/docker/docs` `services.md`、`/docker/compose` `pkg/api/labels.go`・`loader.go`）:
  - `com.docker.compose.project`: 「set on all resources created by Compose to the user project name」
  - `com.docker.compose.service`: 「set on service containers with service name as defined in the Compose file」
  - `com.docker.compose.config-hash`: `pkg/compose/create.go` で、計算したハッシュをラベルとして付け、「later compared against this same label in the reconciler to detect divergence」（ネットワーク/ボリュームの例として記載。コンテナも同じ label 定数 `ConfigHashLabel = "com.docker.compose.config-hash"`）。
  - `com.docker.compose` 接頭辞は予約: 「Specifying labels with this prefix in the Compose file results in a runtime error.」
- **単一サービスの再デプロイ**: https://docs.docker.com/compose/how-tos/production/ 「This first command rebuilds the image for `web` and then stops, destroys, and recreates just the `web` service.」「The `--no-deps` flag prevents Compose from also recreating any services that `web` depends on.」
- **実測（本番 compose v5.1.1）**: `docker compose config --hash gemini-egress` の値と、稼働中コンテナの `config-hash` ラベルが一致（i 節）。

## h. gemini-egress が rm 対象でないのに毎回 Recreate になる理由
事実:
- rm 対象は frontend / celery-beat / discord-gateway / celery-worker のみ（`W/.github/workflows/deploy.yml:390-393`）。gemini-egress は含まれない。
- デプロイログ（run 37545822874、2026-10-06T23:18Z、sha 57090e457）: `Container astro-webapp-gemini-egress-1 Recreate` → `Recreated` → `Started`（2026-10-06T23:20:33Z）。同時刻に他4つは `Creating`（rm 済みのため）。
- 直前の run 37463123321（2026-10-06T12:25Z）でも `Container astro-webapp-gemini-egress-1 Recreate / Recreated / Started`（12:29:51Z）。2回連続で Recreate。
- イメージ: build ログでは `[gemini-egress 2/2] RUN apk add ... CACHED`、`naming to docker.io/library/astro-webapp-gemini-egress:latest done`。本番の現イメージ ID `sha256:fa2738441f09...` = 稼働コンテナのイメージ ID（同一）。イメージ作成時刻は 2026-10-06T14:24:32+09:00（= 05:24Z）で、23:18Z のデプロイより前。つまり**イメージ ID は今回のデプロイで変わっていない**。
- `docker compose config --hash gemini-egress`（本番で実行、読み取りのみ）= `d3e1fa33...4a99` = 稼働中コンテナの `config-hash` ラベル。つまり**今の定義と今のコンテナは一致**している。
- `docker-compose.exporters.yml` には gemini-egress の定義は無い（サービスは node-exporter / postgres-exporter / nginx-exporter / redis-exporter / promtail、`W/docker-compose.exporters.yml:4,30,48,66,85`）。

未確認: **Recreate が起きた理由そのもの**。Compose のログは理由（設定差分 / イメージ差分 / 依存先の再作成など）を出さない。デプロイ中の `.env` 書き換え（`:282-316`）後の hash がデプロイ時点で違っていたのか、`docker compose build` の再タグが影響するのか、どちらも本調査では切り分けていない。切り分け方（設計フェーズでの提案）: デプロイ直前に `docker compose config --hash gemini-egress` とラベルを比較し、`up` に `--dry-run` を付けて差分を出す。ただし、現時点の hash が一致している事実から、「いつも差分がある」わけではなく、**デプロイ手順の中のどこかで差が生まれている**。KGI の達成確認では gemini-egress の StartedAt も観測対象に入れるのが妥当。

## i. 本番の各コンテナのラベル（読み取りのみ）
実行: `docker ps -a --format '{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.service"}}|{{.Status}}'`（2026-10-07、ホストは start_stage5.sh の `K` と同じ）。生出力:
```
astro-webapp-gemini-egress-1|astro-webapp|gemini-egress|Up About an hour
astro-webapp-frontend-1|astro-webapp|frontend|Up About an hour (healthy)
astro-webapp-discord-gateway-1|astro-webapp|discord-gateway|Up About an hour
astro-webapp-celery-worker-1|astro-webapp|celery-worker|Up About an hour
astro-webapp-celery-beat-1|astro-webapp|celery-beat|Up About an hour
astro-webapp-backend-1|astro-webapp|backend|Up About an hour
astro-webapp-nginx-1|astro-webapp|nginx|Up 19 hours (healthy)
astro-webapp-gha-exporter-1|astro-webapp|gha-exporter|Up 9 days
astro-webapp-postgres-1|astro-webapp|postgres|Up 4 days (healthy)
astro-webapp-redis-1|astro-webapp|redis|Up 2 weeks (healthy)
astro-webapp-certbot-1|astro-webapp|certbot|Up 2 weeks
astro-webapp-node-exporter-1|astro-webapp|node-exporter|Up 2 weeks
astro-webapp-promtail-1|astro-webapp|promtail|Up 2 weeks
pushgateway|||Up 2 weeks
```
追加の読み取り（`docker inspect`）:
- backend（blue-green の `docker run` 産）: ラベルは `project.config_files=/home/ubuntu/salesanchor/docker-compose.yml`（**exporters 無し**）、`working_dir`、`version=5.1.1`（←これは `docker run` で付けたラベルに無い値のため、実際に誰が付けたかは未確認。cutover 後に何かが付与した可能性）。**`config-hash` ラベルと `com.docker.compose.image` ラベルが無い**。作成 2026-10-06T23:20:11Z。
- celery-worker / frontend / gemini-egress（compose 産）: `config-hash` あり、`project.config_files=.../docker-compose.yml,.../docker-compose.exporters.yml`、`version=5.1.1`。作成 2026-10-06T23:20:33Z（デプロイの Step 3c と一致）。
- `pushgateway` は compose ラベル無し（compose 管理外）。今回の「各サービスちょうど1つ」の対象外だが、KGI 3 の判定式では除外が必要。
- 重複・別 project 名の残り物: 現時点で**無し**（上の一覧に `astro-webapp` 以外の project 名は無し、同一サービスの重複も無し）。

【含意（事実の並べ替え。実証はしていない）】
- backend は compose 管理下に見えるが config-hash が無いので、`docker compose up` の対象に backend を入れた場合の挙動は**未確認**（hash 不一致として recreate される可能性は設計で検証が必要）。現行どおり backend は blue-green に任せ、compose の up からは外す、という選択肢が設計の論点になる。
- KGI 2（backend 変更後に celery-worker が作り直される）は、backend と celery-worker が同じ `build: ./backend`（`W/docker-compose.yml:199`）を使う＝同じ build 出力でイメージが変わる、という点に依存する。イメージ ID が変われば up の既定で recreate される（g 節の公式動作）。

## j. 外部事例
- Docker 公式（推奨）: https://docs.docker.com/compose/how-tos/production/ （取得 2026-10-07。ページに更新日の表示は確認できず、日付は未確認）。「rebuilds the image for `web` and then stops, destroys, and recreates just the `web` service」「`--no-deps` ... prevents Compose from also recreating any services that `web` depends on」。→ 変更したサービスだけを再作成する運用が公式推奨。
- Docker 公式リファレンス: https://docs.docker.com/reference/cli/docker/compose/up/ （g 節）。
- OSS: wowu/docker-rollout（https://github.com/wowu/docker-rollout）。`docker compose up -d <service>` を置き換えて、サービスを2倍にスケール → 新コンテナの ready 待ち → 旧を削除する方式（WebSearch の要約による）。本件の「backend は blue-green」と同型だが、本変更（rm -f を減らすこと）への直接の事例ではない。日付は未確認。
- 名前のある企業・プロジェクトで、「毎デプロイの全コンテナ rm -f を、差分のみの recreate に変えた」ことを数値付きで公開している記録: **無し**（今回の検索範囲では見つからなかった）。数値は創作しない。

## 【事実】一覧
1. origin/main（57090e457）の deploy.yml は、毎回 frontend / celery-beat / discord-gateway / celery-worker を `docker rm -f`（celery-worker は先に `stop -t 60`）してから up している（`W/.github/workflows/deploy.yml:389-394`）。
2. backend は blue-green で `docker run` 起動し、`astro-webapp-backend-1` へ rename（`W/scripts/blue-green-cutover.sh:80-161`）。config-hash ラベルは付けない。
3. ロールバックは backend 含む 5 サービスを rm -f し、`up -d --remove-orphans`（`W/.github/workflows/deploy.yml:655-658`）。
4. docker-compose.yml に `name:` / `container_name` / `labels:` は無い。project 名は本番 `.env` の `COMPOSE_PROJECT_NAME=astro-webapp`。COMPOSE_FILE は deploy が `.env` に `docker-compose.yml:docker-compose.exporters.yml` として書く。
5. ADR-092 と PR #1402 は、名前衝突 502 と discord-gateway 重複起動 storm の再発防止として全 app 系の rm -f を入れた。PR #1402 のレビューが「孤児/重複のみに絞る最適化は別 Issue」と明記している。
6. 公式: up は設定/イメージが変わったコンテナだけ recreate、`--force-recreate` で強制、`--remove-orphans` は定義に無いサービスのコンテナを削除。
7. 本番の現在: 各サービス 1 つずつ、project は全て `astro-webapp`、重複・別 project の残りなし。compose 外は `pushgateway` のみ。
8. gemini-egress は rm 対象外なのに、直近 2 回のデプロイで Recreate。イメージ ID は不変、現在の config-hash はラベルと一致。
9. 本番 compose は v5.1.1。

## 【未確認】一覧
1. 6月の「別プロジェクト名（ハッシュ付き）の残り物」が実際にどういう名前で、なぜ残ったかの一次記録（docker ps 出力・ログ）。ADR-092 とレビューの記述のみ。
2. `--remove-orphans` が「同じ project の孤児だけ」を対象にするかを、公式文面で明記した箇所（取得した範囲では未記載）。
3. gemini-egress が毎回 Recreate になる原因（hash の差か、依存か、build の影響か）。現在の hash は一致している。
4. backend（config-hash ラベル無し、config_files に exporters 無し）を compose の up の対象にしたときの挙動（recreate されるか）。
5. 本番 `.env` に `COMPOSE_PROJECT_NAME=astro-webapp` が入った経緯と、`docker rm`/`rename` 後の backend に `com.docker.compose.version` ラベルが付いている理由。
6. 既定の recreate が discord-gateway の二重起動を起こさないことの実証（stop→create の順序の実測）。
7. ADR-115 の本文との整合（本調査では本文を精読していない）。
8. 外部事例: Docker 公式 production ページの公開日・更新日、docker-rollout の日付、および「rm -f から差分 recreate へ移行した企業事例」（無し）。
9. frontend のみのデプロイで celery-worker の config-hash / イメージ ID が変わらないことの実測（KGI 1 の前提。build 出力が決定的か、`.env` の再書き込みで hash が変わらないか）。
