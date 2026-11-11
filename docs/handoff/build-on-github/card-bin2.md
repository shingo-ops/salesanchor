# card-bin2: 本番の受け取りを指紋に切り替える（prod1 で組み立てない）

状態: カード草案（Opus、2026-11-11）。設計審査はまだ。実装の承認はまだ（PO の明示の実装承認が要る）。この PR を main に入れることは、deploy.yml・compose・本番の scripts を変えるので危険 PR（ADR-136）。PO の「GO #番号」が要る。切り替えは 14:00〜16:00（日本時間）、PO が見ている時間に限る（design.md §23）。
親: [design.md](./design.md) §12 便2（中身の正本）・§26（このカードを出す前の直し）・§9（控えと戻し）。前の段のカード: [card-bin1-r3.md](./card-bin1-r3.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret と Variables・組織の設定には触らない。PR は作らない（枝に push して報告するまで）。

## なぜ（事実）
- 2026-11-08 に prod1 のメモリが足りなくなり、本番の組み立てが 2 回途中で切れた（design.md §1）。
- 便1（#5397・9bb56d7d6）で 5 つの完成品は GitHub で組み立てて倉庫に入るようになった。prod1 はまだ自分で組み立てている（`.github/workflows/deploy.yml:481-492` の `docker compose build` の 3 回試行）。
- この段で prod1 の組み立てを 0 にし、倉庫から指紋（`@sha256:`）で受け取るだけにする。

## 受領確認（最初の報告の 1 行目に書く）
`RECEIVED card-bin2 HEAD=<git rev-parse HEAD の 40 桁>`

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/build-on-github-bin2` を `origin/main` から `bash scripts/new-worktree.sh release/build-on-github-bin2 --claude` で作る。`git merge-base --is-ancestor 26a050a10 HEAD` が終了 0。
- P2 `wc -l < .github/workflows/deploy.yml` が 1352。違えば、下の行番号を「その行の文字列」で探し直す。文字列が見つからなければ BLOCKED。
- P3 `grep -n 'if docker compose build; then' .github/workflows/deploy.yml` が `482:` の 1 行。`grep -n 'if docker compose build 2>&1; then' .github/workflows/deploy.yml` が `965:` の 1 行。
- P4 `grep -c '^  push:' .github/workflows/build-images.yml` が 1。`grep -c 'workflow_call' .github/workflows/build-images.yml` が 0。
- P5 `grep -n 'j\["steps"\]' scripts/tests/test-deploy-nginx-recreate-guard.sh` が `27:` の 1 行。
- P6 `grep -c 'GHCR_PUSH_TOKEN' .github/workflows/monthly-secret-expiry.yml` が 1。

## 1. 触るファイル（この 19 個だけ）
1. `.github/workflows/build-images.yml`
2. `.github/workflows/deploy.yml`
3. `.github/workflows/monthly-secret-expiry.yml`
4. `.github/workflows/deploy-script-test.yml`
5. `docker-compose.yml`
6. `docker-compose.override.yml`（新規）
7. `docker-compose.secretary-agent.yml`
8. `docker-compose.ai-reader.yml`
9. `docker-compose.ai-reader-http.yml`
10. `docker-compose.ai-reader-cloud-http.yml`
11. `docker-compose.ai-unmask-http.yml`
12. `scripts/blue-green-cutover.sh`
13. `scripts/deploy/app-services-plan.sh` と `scripts/tests/test_app_services_plan.py`
14. `scripts/ops/place-secretary-token.sh`
15. `scripts/deploy/pull-images.sh`・`scripts/deploy/prune-images.sh`・`scripts/deploy/rollback-images.sh`（3 つとも新規・実行権 100755）と `scripts/tests/test-deploy-pull-prune.sh`（新規・100755）
16. `scripts/rehearsal_phase2.sh`
17. `scripts/test_rollback_simulation.sh`
18. `scripts/dry-run-blue-green.sh`・`tests/sandbox/ai-reader-audit.sh`
19. `scripts/tests/test-deploy-nginx-recreate-guard.sh`（27 行目だけ）

触らない: 上以外のすべて。特に deploy.yml の `on:`（3-6）・`concurrency`（14-16）・LP・design-site・backup・nginx・Bootstrap・migrations・smoke の段、`scripts/run_all_migrations.sh`、nginx・certbot・redis・postgres の定義、`docker-compose.monitoring.yml`、`scripts/f2-cleanup.sh`、`.github/workflows/workflow-lint.yml`、`docs/`。builder prune（`deploy.yml:1044-1047`）は便3 で消すので残す。

## 2. 変更の中身（行番号は P1 の時点）

### 2-1. `.github/workflows/build-images.yml`（design.md §26-1 の 1.・2.）
1. 1〜7 行目を次にする（`on: push` を消し、deploy.yml から呼ばれる形にする）。
```yaml
name: Build images (GitHub → GHCR)
# build-on-github 便1・便2（docs/handoff/build-on-github/design.md §12・§26）。
# 5 つの完成品を GitHub で組み立てて走査し、組織の非公開の倉庫（ghcr.io）へ送る。
# 便2 から deploy.yml の build job が呼ぶ（uses:）。単独では動かない。名前・走査・push の正本はこのファイル 1 か所。
on:
  workflow_call:
    secrets:
      GHCR_PUSH_TOKEN:
        required: true
      VITE_FUNNEL_DASHBOARD:
        required: false
    outputs:
      backend:
        value: ${{ jobs.build-backend.outputs.ref }}
      frontend:
        value: ${{ jobs.build-frontend.outputs.ref }}
      gemini_egress:
        value: ${{ jobs.build-gemini-egress.outputs.ref }}
      gha_exporter:
        value: ${{ jobs.build-gha-exporter.outputs.ref }}
      secretary_agent:
        value: ${{ jobs.build-secretary-agent.outputs.ref }}
```
2. `changes` job の `timeout-minutes: 10` の次に、次の 3 行を足す（字下げは `timeout-minutes` と同じ 4 空白）。
```yaml
    permissions:
      contents: read
      actions: read   # 前回の deploy の成否を読むため（§26-1 の 2.）
```
3. `changes` job の `outputs:` の 5 行の `steps.f.outputs.` を、すべて `steps.g.outputs.` にする。
4. `changes` job の最後（paths-filter の `secretary_agent:` の塊の後・空行の前）に次の段を足す。
```yaml
      - name: Check previous deploy completed (design.md §26-1 2.)
        id: g
        env:
          GH_TOKEN: ${{ github.token }}
          BEFORE: ${{ github.event.before }}
          F_BACKEND: ${{ steps.f.outputs.backend }}
          F_FRONTEND: ${{ steps.f.outputs.frontend }}
          F_GEMINI_EGRESS: ${{ steps.f.outputs.gemini_egress }}
          F_GHA_EXPORTER: ${{ steps.f.outputs.gha_exporter }}
          F_SECRETARY_AGENT: ${{ steps.f.outputs.secretary_agent }}
        run: |
          last=$(gh api "repos/${GITHUB_REPOSITORY}/actions/workflows/deploy.yml/runs?branch=main&event=push&status=success&per_page=1" --jq '.workflow_runs[0].head_sha // ""' 2>/dev/null || echo "")
          if [ -n "$last" ] && [ "$last" = "$BEFORE" ]; then
            echo "前回デプロイは成功（${last:0:7}）→ 差分どおり"
            { echo "backend=$F_BACKEND"; echo "frontend=$F_FRONTEND"; echo "gemini_egress=$F_GEMINI_EGRESS"; echo "gha_exporter=$F_GHA_EXPORTER"; echo "secretary_agent=$F_SECRETARY_AGENT"; } >> "$GITHUB_OUTPUT"
          else
            echo "::warning::前回の成功デプロイ(${last:0:7})が push 直前(${BEFORE:0:7})と違う／取れない → 5 つ全部を組み立てる"
            { echo "backend=true"; echo "frontend=true"; echo "gemini_egress=true"; echo "gha_exporter=true"; echo "secretary_agent=true"; } >> "$GITHUB_OUTPUT"
          fi
```
5. `common` の filter の一覧に `              - '.github/workflows/deploy.yml'` を足す（`- '.github/workflows/secret-scan.yml'` の次の行・14 空白）。理由: deploy.yml の受け取りの形を変えたら 5 つとも組み直して指紋を揃える。
6. ほかの job（build-*）は変えない。

### 2-2. `.github/workflows/deploy.yml`
1. 18-20 行目（`jobs:`・`  deploy:`・`    runs-on: ubuntu-latest`）を次にする。
```yaml
jobs:
  # build-on-github 便2（docs/handoff/build-on-github/design.md §26）: 5 つの完成品を GitHub で組み立てて倉庫へ。
  # 正本は build-images.yml。落ちたら deploy は動かない（prod1 には触らない）。
  build:
    uses: ./.github/workflows/build-images.yml
    permissions:
      contents: read
      actions: read
    secrets:
      GHCR_PUSH_TOKEN: ${{ secrets.GHCR_PUSH_TOKEN }}
      VITE_FUNNEL_DASHBOARD: ${{ secrets.VITE_FUNNEL_DASHBOARD }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
```
2. 「Deploy to VPS (code + env + docker compose)」の段（272 行目の `- name:`）の `uses: appleboy/ssh-action@v1` の前に `env:` を、`with:` の中の `key:` の次に `envs:` を足す。
```yaml
        env:
          GHCR_USER: ${{ vars.GHCR_USER }}
          GHCR_PULL_TOKEN: ${{ secrets.GHCR_PULL_TOKEN }}
          BACKEND_REF: ${{ needs.build.outputs.backend }}
          FRONTEND_REF: ${{ needs.build.outputs.frontend }}
          GEMINI_EGRESS_REF: ${{ needs.build.outputs.gemini_egress }}
          GHA_EXPORTER_REF: ${{ needs.build.outputs.gha_exporter }}
          SECRETARY_AGENT_REF: ${{ needs.build.outputs.secretary_agent }}
```
```yaml
          envs: GHCR_USER,GHCR_PULL_TOKEN,BACKEND_REF,FRONTEND_REF,GEMINI_EGRESS_REF,GHA_EXPORTER_REF,SECRETARY_AGENT_REF
```
3. 290 行目 `echo "${PREV_SHA}" > .deploy_prev_sha` の次に足す（字下げは 12 空白）。
```bash
            # build-on-github 便2（design.md §9-1）: 書き換える前の指紋 5 行を控える（無ければ空）。Finalize の戻し先
            grep -E '^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=' .env > .deploy_prev_images.env 2>/dev/null || : > .deploy_prev_images.env
```
4. 438 行目 `rm -f .env.secrets.new .env.bak` の次に足す。
```bash
            # build-on-github 便2（design.md §26）: GitHub で組み立てた完成品の指紋を .env に書く。
            # 組み立てなかった完成品（出力が空）は今の行を残す。5 行が揃わなければ箱に触る前に止める。
            for _pair in "BACKEND_IMAGE=${BACKEND_REF:-}" "FRONTEND_IMAGE=${FRONTEND_REF:-}" "GEMINI_EGRESS_IMAGE=${GEMINI_EGRESS_REF:-}" "GHA_EXPORTER_IMAGE=${GHA_EXPORTER_REF:-}" "SECRETARY_AGENT_IMAGE=${SECRETARY_AGENT_REF:-}"; do
              _k="${_pair%%=*}"; _v="${_pair#*=}"
              if [ -n "${_v}" ]; then sed -i "/^${_k}=/d" .env; echo "${_k}=${_v}" >> .env; fi
            done
            for _k in BACKEND_IMAGE FRONTEND_IMAGE GEMINI_EGRESS_IMAGE GHA_EXPORTER_IMAGE SECRETARY_AGENT_IMAGE; do
              if ! grep -qE "^${_k}=ghcr\.io/[a-z0-9-]+/salesanchor-[a-z0-9-]+@sha256:[0-9a-f]{64}$" .env; then
                echo "❌ .env に ${_k} の指紋の行がありません（箱には触っていません）"
                exit 1
              fi
            done
```
5. 470-495 行目（`echo "Step 3: Rebuilding and restarting containers..."` から `fi`（`exit 1` の次の行）まで）を次にする。
```bash
            echo "Step 3: Pulling images by digest (build-on-github 便2)..."
            # prod1 では組み立てない（2026-11-08 のメモリ不足の再発防止・design.md §1）。
            # 受け取れなければ .env の指紋を控えに戻して止める（箱には触らない・design.md §26-1 3.）。
            if ! bash scripts/deploy/pull-images.sh; then
              sed -i -E '/^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=/d' .env
              cat .deploy_prev_images.env >> .env
              echo "❌ 完成品を受け取れませんでした。.env の指紋は控えに戻し、箱には触っていません"
              exit 1
            fi
```
6. 520 行目 `docker compose up -d --no-deps --remove-orphans frontend …` の `up -d` の後に ` --no-build` を足す。523 行目 `docker compose up -d --no-deps node-exporter promtail` も同じ。
7. 647 行目の注記の `image は backend と同じ astro-webapp-backend。` を `image は backend と同じ（.env の BACKEND_IMAGE。無ければ既定の astro-webapp-backend）。` にする。
8. 716-719 行目（`if ! docker build -t astro-webapp-secretary-agent ./secretary-agent; then` から `fi` まで）を次にする。721 行目の `docker run … astro-webapp-secretary-agent node /app/probe.mjs` の `astro-webapp-secretary-agent` を `"${_sa_img}"` にする。
```bash
            _sa_img="$(grep -m1 '^SECRETARY_AGENT_IMAGE=' .env | cut -d= -f2-)"
            if [ -z "${_sa_img}" ] || ! docker image inspect "${_sa_img}" >/dev/null 2>&1; then
              echo "::warning::secretary-agent の完成品が prod1 にありません（アプリの反映には影響しません）"
              exit 0
            fi
```
9. 782 行目 `docker compose up -d --force-recreate celery-worker celery-beat discord-gateway` の `up -d` の後に ` --no-build` を足す。
10. 962-971 行目（`# 旧コードでビルド（最大3回リトライ）` から `done` まで）を次にする。
```bash
                # build-on-github 便2（design.md §9-2・§26-1 6.）: 組み立てずに、控えの指紋を .env に戻す
                _rb_build=false
                if [ -s .deploy_prev_images.env ]; then
                  while IFS= read -r _l; do
                    _k="${_l%%=*}"
                    sed -i "/^${_k}=/d" .env
                    echo "${_l}" >> .env
                  done < .deploy_prev_images.env
                  _rb_build=true
                elif ! git show HEAD:docker-compose.yml | grep -q 'BACKEND_IMAGE'; then
                  # 便2 の初回の戻し: 戻り先の compose は build: の形。prod1 に残る astro-webapp-* の完成品で起こす
                  sed -i -E '/^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=/d' .env
                  _rb_build=true
                fi
```
11. 979 行目 `docker compose up -d --remove-orphans` を `docker compose up -d --no-build --remove-orphans` にする。
12. 1040-1041 行目（`echo "Step 8: Cleaning up old Docker images..."`・`docker image prune -f`）を次にする。
```bash
            echo "Step 8: Cleaning up old pulled images (keep current and previous digests)..."
            bash scripts/deploy/prune-images.sh || echo "::warning::prune-images.sh が失敗しました（反映には影響しません）"
```

### 2-3. `.github/workflows/monthly-secret-expiry.yml`
22 行目の WATCH_LIST の最後の `GHCR_PUSH_TOKEN` の後に ` GHCR_PULL_TOKEN` を足す。

### 2-4. `.github/workflows/deploy-script-test.yml`
1. `pull_request.paths` と `push.paths` の両方の `- 'scripts/tests/test_app_services_plan.py'` の次の行に `      - 'scripts/tests/test-deploy-pull-prune.sh'` を足す。
2. 最後の段の後に足す。
```yaml
      - name: Run pull/prune image tests (build-on-github 便2)
        run: bash scripts/tests/test-deploy-pull-prune.sh
```

### 2-5. compose
1. `docker-compose.yml`
   - 68 行目 `    build: ./backend` → `    image: ${BACKEND_IMAGE:-astro-webapp-backend}`。231・336・380 行目も同じ。
   - 198-201 行目（`    build:`・`      context: ./frontend`・`      args:`・`        VITE_FUNNEL_DASHBOARD: ${VITE_FUNNEL_DASHBOARD}`）→ `    image: ${FRONTEND_IMAGE:-astro-webapp-frontend}` の 1 行。
   - 435 行目 → `    image: ${GEMINI_EGRESS_IMAGE:-astro-webapp-gemini-egress}`。
   - 548-549 行目（`    build:`・`      context: ./monitoring/gha-exporter`）→ `    image: ${GHA_EXPORTER_IMAGE:-astro-webapp-gha-exporter}`。
2. `docker-compose.override.yml`（新規）: 先頭に「手元で組み立てる人のためのファイル。本番は .env の COMPOSE_FILE で読むファイルを決めているので、このファイルは読まない（design.md §26-1 5.）」の注記。中身は上で消した `build:` を 7 サービス（backend・frontend（args ごと）・celery-worker・celery-beat・discord-gateway・gemini-egress・gha-exporter）にそのまま書く（`services:` の下にサービス名と `build:` だけ）。
3. `docker-compose.secretary-agent.yml`: 14-15 行目 → `    image: ${SECRETARY_AGENT_IMAGE:-astro-webapp-secretary-agent}` の 1 行。3 行目の注記の後に `# 完成品は deploy が .env の SECRETARY_AGENT_IMAGE の指紋で受け取る（design.md §26）。` を足す。
4. `docker-compose.ai-reader.yml`: 12-14 行目（注記・`build:`・`image:`）→ `    # backend と同じ完成品（.env の BACKEND_IMAGE。無ければ既定の名前）。` と `    image: ${BACKEND_IMAGE:-astro-webapp-backend}` の 2 行。
5. `docker-compose.ai-reader-http.yml:14-15`・`docker-compose.ai-reader-cloud-http.yml:15-16`・`docker-compose.ai-unmask-http.yml:15-16`: 注記を `    # backend と同じ完成品（deploy が .env の BACKEND_IMAGE の指紋で受け取る）。`、`image:` を `    image: ${BACKEND_IMAGE:-astro-webapp-backend}` にする。

### 2-6. 本番の scripts
1. `scripts/blue-green-cutover.sh`: 9 行目を `#   - .env の BACKEND_IMAGE（無ければ astro-webapp-backend）の完成品がローカルにある（deploy の Step 3 で受け取り済み）`、69 行目を `# compose の image: と同じ名前。prod1 では .env（38 行目で読み込み済み）の指紋`、70 行目を `BACKEND_IMAGE="${BACKEND_IMAGE:-${COMPOSE_PROJECT}-backend}"`、73 行目の文を `deploy の Step 3（pull-images.sh）を先に実行してください。` にする。
2. `scripts/deploy/app-services-plan.sh:63` を次の 2 行にする。`scripts/tests/test_app_services_plan.py` の偽の docker に `compose config --format json` の応答（`{"services": {"<svc>": {"image": "astro-webapp-<svc>"}}}` の形）を足し、今の試験がすべて通ること。
```bash
  expected_ref="$(docker compose config --format json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["services"][sys.argv[1]].get("image",""))' "${svc}" 2>/dev/null)"
  expected_image="$(docker image inspect -f '{{.Id}}' "${expected_ref:-${PROJECT}-${svc}}" 2>/dev/null)"
```
3. `scripts/ops/place-secretary-token.sh:25` の `docker build -t astro-webapp-secretary-agent ./secretary-agent && ` を消す。
4. `scripts/deploy/pull-images.sh`（新規）
```bash
#!/usr/bin/env bash
# build-on-github 便2（docs/handoff/build-on-github/design.md §12 便2 9.・§26）。
# prod1 で .env の 5 つの指紋を倉庫から受け取る。組み立てはしない。箱には触らない。
# 使い方（deploy.yml の Step 3 から）: GHCR_USER と GHCR_PULL_TOKEN を env で渡して bash scripts/deploy/pull-images.sh
set -euo pipefail
cd "${REPO_DIR:-/home/ubuntu/salesanchor}"
docker compose version
# 守り（K1・§26-1 5.）: 本番の compose に build: が 1 つも無いこと
_nb="$(docker compose config --format json | python3 -c 'import json,sys;print(sum(1 for s in json.load(sys.stdin)["services"].values() if "build" in s))')"
if [ "${_nb}" != "0" ]; then
  echo "❌ compose に build: を持つサービスが ${_nb} 個ある（本番では 0 のはず。override が読まれていないか確かめる）"
  exit 1
fi
_refs=()
for _k in BACKEND_IMAGE FRONTEND_IMAGE GEMINI_EGRESS_IMAGE GHA_EXPORTER_IMAGE SECRETARY_AGENT_IMAGE; do
  _v="$(grep -m1 "^${_k}=" .env | cut -d= -f2- || true)"
  if ! [[ "${_v}" =~ ^ghcr\.io/[a-z0-9-]+/salesanchor-[a-z0-9-]+@sha256:[0-9a-f]{64}$ ]]; then
    echo "❌ .env の ${_k} の形が違う"
    exit 1
  fi
  _refs+=("${_v}")
done
if [ -z "${GHCR_PULL_TOKEN:-}" ] || [ -z "${GHCR_USER:-}" ]; then
  echo "❌ GHCR_PULL_TOKEN か GHCR_USER が空（GitHub の secret と Variables を確かめる）"
  exit 1
fi
# 鍵は受け取りの間だけ置く（design.md §23・§26-1 7.）
trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT
printf '%s' "${GHCR_PULL_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin >/dev/null
for _r in "${_refs[@]}"; do
  _ok=false
  for _a in 1 2 3; do
    if docker pull -q "${_r}" >/dev/null; then _ok=true; break; fi
    echo "pull attempt ${_a} failed (${_r##*/}). 15秒後にリトライ..."
    sleep "${PULL_RETRY_SLEEP:-15}"
  done
  if [ "${_ok}" != "true" ]; then
    echo "❌ ${_r##*/} を 3 回受け取れませんでした"
    exit 1
  fi
  echo "pulled ${_r##*/}"
done
echo "pull ok (5 images)"
```
5. `scripts/deploy/prune-images.sh`（新規）
```bash
#!/usr/bin/env bash
# build-on-github 便2（design.md §9-1）: 倉庫から受け取った完成品のうち、今（.env）と 1 つ前（.deploy_prev_images.env）の指紋以外を消す。
# docker image prune は呼ばない（指紋だけの完成品が消えるかは未確認 U30）。使用中の完成品は docker が消さない（-f を付けない）。
set -uo pipefail
cd "${REPO_DIR:-/home/ubuntu/salesanchor}"
_keep="$(cat .env .deploy_prev_images.env 2>/dev/null | grep -E '^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=' | cut -d= -f2- | sort -u)"
if [ -z "${_keep}" ]; then
  echo "prune: 残す指紋が読めないので何も消さない"
  exit 0
fi
docker images --digests --format '{{.Repository}}@{{.Digest}}' | sort -u | while read -r _ref; do
  case "${_ref}" in ghcr.io/*/salesanchor-*@sha256:*) ;; *) continue ;; esac
  if printf '%s\n' "${_keep}" | grep -qxF "${_ref}"; then continue; fi
  if docker image rm "${_ref}" >/dev/null 2>&1; then echo "prune: removed ${_ref##*/}"; else echo "prune: kept (in use) ${_ref##*/}"; fi
done
exit 0
```
6. `scripts/deploy/rollback-images.sh`（新規・手で流す戻し・design.md §9-2「手動」）: (1) `.deploy_prev_images.env` が 5 行（`^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=` の行数が 5）でなければ止まる、(2) 今の 5 行を `.deploy_rollback_from.env` に写す、(3) `.env` の 5 行を控えで置き換える、(4) 5 つの指紋が `docker image inspect` でローカルに在ることを確かめる（無ければ「GHCR_PULL_TOKEN と GHCR_USER を渡して pull-images.sh を流す」と出して止まる）、(5) `bash scripts/blue-green-cutover.sh`、(6) `docker compose up -d --no-build --no-deps frontend celery-worker celery-beat discord-gateway gemini-egress gha-exporter`。冒頭に `set -euo pipefail` と `cd "${REPO_DIR:-/home/ubuntu/salesanchor}"`。
7. `scripts/tests/test-deploy-pull-prune.sh`（新規）: `scripts/tests/test-deploy-nginx-recreate-guard.sh` と同じ「偽の docker を PATH の先頭に置き、呼ばれ方をファイルに記録する」型。一時ディレクトリに偽の `.env` を置き `REPO_DIR` で指す。`PULL_RETRY_SLEEP=0`。最低限の場合:
   - T1 正しい 5 行・偽の docker が全部成功 → 終了 0、`docker pull` が 5 回、`docker logout ghcr.io` が 1 回、`build` を含む呼び出しが 0 回。
   - T2 compose config の応答に `build` を持つサービスが 1 つ → 終了 1、`docker login` が 0 回。
   - T3 `.env` の 1 行が `@sha256:` でない → 終了 1、`docker login` が 0 回。
   - T4 1 つの pull が 3 回とも失敗 → 終了 1、`docker logout ghcr.io` が 1 回（trap）。
   - T5 prune: 偽の `docker images` が 4 つの ghcr 指紋（今・1 つ前・古い 2 つ）と `astro-webapp-backend@<none>` を返す → `docker image rm` は古い 2 つだけ。
   - T6 prune: `.env` と控えの両方に指紋が無い → `docker image rm` が 0 回、終了 0。
   - T7 deploy.yml の Finalize の戻しの塊（2-2 の 10.）を YAML から抜き出し、控えが 1 行のとき `.env` のその行だけが入れ替わること。控えが空で `git show HEAD:docker-compose.yml` に `BACKEND_IMAGE` が無いとき 5 行が消えること（偽の git を置く）。

### 2-7. 抜き出す試験・砂場（design.md §12 便2 12.〜15.・§26-3）
1. `scripts/tests/test-deploy-nginx-recreate-guard.sh:27` の `for s in j["steps"]` を `for s in j.get("steps", [])` にする。ほかは変えない。
2. `scripts/rehearsal_phase2.sh`: design.md §12 便2 12. の (i)〜(iii) のとおり。今の行番号: 自前 compose の backend の `build: .` は 183 行目（`image: \${BACKEND_IMAGE:-phase2-rehearsal-backend}` を足す。heredoc は 180 行目の引用符なしの `<< COMPOSE` なので `$` の前に `\` が要る）、`git reset --hard "${BAD_SHA}"` は 331 行目、B-1 の予備の `docker compose up -d` は 379 行目、SUBSTITUTIONS の一覧は 16-20 行目。309・332 行目の `docker compose build --quiet` は変えない。
3. `scripts/test_rollback_simulation.sh`: design.md §12 便2 13. のとおり。今の行番号: 自前 compose の backend は 52-55 行目（heredoc は 37 行目の `'DCEOF'` で引用符付きなので `\` は要らない）、戻しの写しは 397-402 行目（2-2 の 10. と同じ形にする）、408 行目に `--no-build`。282・346 行目の `docker compose build -q` は変えない。
4. `scripts/dry-run-blue-green.sh`: design.md §12 便2 14. のとおり（9・27・47-58 行目）。
5. `tests/sandbox/ai-reader-audit.sh:34` `docker compose -f "$COMPOSE" build ai-reader` → `docker build -t astro-webapp-backend ./backend`。

## 3. 試験（実装役が流して生の出力をファイルに残す）
- `bash scripts/tests/test-deploy-pull-prune.sh` が全部 PASS。
- `python3 scripts/tests/test_app_services_plan.py` が全部 PASS。
- `bash scripts/tests/test-deploy-nginx-recreate-guard.sh`・`bash scripts/tests/test-deploy-orphan-cleanup.sh` が全部 PASS。
- `actionlint .github/workflows/build-images.yml .github/workflows/deploy.yml .github/workflows/deploy-script-test.yml .github/workflows/monthly-secret-expiry.yml` が 0 件。
- `bash -n` を新しい 3 つの script と変えた script に。`shellcheck` がある場合は新しい 3 つに。
- `docker compose -f docker-compose.yml config -q`（`.env.example` を `.env` に写した一時の場所で）が終了 0。手元の組み立ての確かめに、`docker compose config --format json | python3 -c '…build の数…'` が override ありで 7、COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml ありで 0。

## 4. 確かめ（PR の審査で貼る）
- K1 の形: `git grep -nE 'docker( compose)?( -[fp] \S+)* build([[:space:]]|$)|docker build([[:space:]]|$)' -- ':!docs' ':!*.md'` の当たりが、`scripts/rehearsal_phase2.sh:309,332`・`scripts/test_rollback_simulation.sh:282,346`・`tests/sandbox/ai-reader-audit.sh:34`・`tests/sandbox/image-scan-survey.sh:22`（すべて GitHub の実行機の上）だけ。deploy.yml の当たりは 0。
- `gh workflow run test-rollback.yml --ref release/build-on-github-bin2` が緑。`gh workflow run test-phase2-rehearsal.yml --ref release/build-on-github-bin2` が緑（secret が無くて動かないときは、そのことを報告に書く）。`gh workflow run sandbox-test.yml --ref release/build-on-github-bin2 -f test=ai-reader-audit` が緑。
- 報告: 枝の HEAD の 40 桁、触ったファイルの一覧（`git diff --stat origin/main...HEAD`）、上の試験の生の出力の置き場。

## 5. 想定の分岐（実装中に当たったら BLOCKED: で止まり、推測で直さない）
- (a) actionlint が `uses:` の job の `permissions` か `secrets` を拒む → 止まる。
- (b) `test_app_services_plan.py` の偽の docker が `compose config --format json` を足すと既存の試験が落ちる → 落ちた試験名と出力を報告して止まる。
- (c) 行番号の文字列が P2 の時点で見つからない → 止まる。
- (d) `docker-compose.yml` に、上に無い `build:` が見つかる（`grep -n 'build:' docker-compose.yml` が 2-5 の 1. の 7 か所以外を返す）→ 止まる。

## 6. 本番への出し方（実装の後・この順で。Opus と PO）
1. 実装の PR を Draft で作る。PR 本文に変更 3 行の要約・`git diff main...HEAD --name-only`・GO の前提（下の 2.〜4.）。
2. PO が GitHub に secret `GHCR_PULL_TOKEN`（classic PAT・read:packages だけ・180 日）を登録する（design.md §23）。
3. K8 の関所（20 回の見込みの中央値 ≤ 3.1 分・design.md §12 便1 の完了条件 5.）が通っている。
4. 審査役（reviewer・opus）の APPROVE と CI の全部の緑。
5. PO の「GO #番号」→ 14:00〜16:00 に PO が見ている状態でマージ。最初の run を見る: 組み立て 5 つ → Step 2 の 5 行 → pull の `pull ok (5 images)` → 切替 → 健康確認 → `grep -c ghcr.io ~/.docker/config.json` が 0。
6. 戻し方: 前進の revert の PR（compose の `build:` と Step 3 の組み立てが戻る）。`.env` の 5 行は残しても害は無い（旧 compose は `image:` を読まない）。
