# card-bin1: GitHub で 5 つの完成品を組み立て、走査して、組織の非公開の倉庫へしまう（便1 実装）

状態: カード発行（Opus、2026-11-04）・設計審査 APPROVE（2 回目・design.md §24-5）。実装は PO の明示の実装承認の後にだけ始める。
親: [design.md](./design.md) §12 便1・§24（§24 が §12 便1 に優先する）。目標: [kgi.md](../../specs/build-on-github/kgi.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番（prod1・prod2）・GitHub の secret と Variables・組織の設定には触らない。PR は作らない（Opus が作る）。
読んだ決まり: `docs/ai-agents/executor-checklist.md`（作業前・commit 前の点検）。この便で当てはまる点は次のとおり。新しいファイルは全文を書く。commit と push の後に `git log` で確かめる。クラウドでは PR を作らない。出力は長ければファイルに残す。パスは正確に書く。

## 受領確認（最初の報告の 1 行目に書く）
`RECEIVED card-bin1 HEAD=<git rev-parse HEAD の 40 桁>`

## 0. 実装前点検（結果を報告に書く。外れたら実装せず BLOCKED: で止まる）
- P1 `.gitleaks.toml` の `:3-5` が `[extend]` と `useDefault = true` であること。`grep -n 'gcp-api-key' .gitleaks.toml` が 0 件であること（既にあれば BLOCKED）。
- P2 `.github/workflows/monthly-secret-expiry.yml:22` が `WATCH_LIST="PIPELINE_PAT SSH_PRIVATE_KEY META_APP_SECRET DISCORD_WEBHOOK_OWNER_PING DISCORD_WEBHOOK_SCHEDULED_REPORT DISCORD_WEBHOOK_PR METADATA_FERNET_KEY GHA_APP_KEY_PATH"` であること（行番号か中身が違えば、違いを書いて BLOCKED）。
- P3 `.github/workflows/sandbox-test.yml` の Run の段が `bash "tests/sandbox/${TEST_NAME}.sh"` であること。
- P4 新しく作る 4 つのファイル（§1 の 1〜4）がまだ無いこと（あれば BLOCKED）。
- P5 次の 5 か所に `Dockerfile` があること: `backend/`、`frontend/`、`monitoring/prod1/gemini-egress/`、`monitoring/gha-exporter/`、`secretary-agent/`。
- P6 `frontend/Dockerfile` に `ARG` が 5 つあること: `VITE_FIREBASE_API_KEY`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID`・`VITE_FUNNEL_DASHBOARD`・`VITE_AUTH_PROVIDER`。

## 1. 触るファイル（この 6 つだけ）
1. `.github/workflows/build-images.yml`（新規）
2. `.github/scripts/image-scan.sh`（新規・実行権を付ける）
3. `.github/scripts/ghcr-private-check.sh`（新規・実行権を付ける）
4. `tests/sandbox/image-scan-survey.sh`（新規・実行権を付ける）
5. `.gitleaks.toml`（末尾に足すだけ）
6. `.github/workflows/monthly-secret-expiry.yml`（`:22` の 1 行だけ）

触らない: `.github/workflows/deploy.yml`・`docker-compose*.yml`・`scripts/`・`docs/`（このカードを含む。仕様書は Opus が書く）・`.claude-pipeline/`・製品コード（`backend/`・`frontend/` などの中身）。

## 2. 変更の中身

### 2-1. `.github/workflows/build-images.yml`（全文。この形のまま書く）
決めごと（理由は design.md §24）:
- `concurrency` は書かない（C17）。
- `uses:` はすべて 40 桁の SHA で固定する（§24-1）。
- 設定の確かめは `changes` に 1 回だけ置く（C12）。
- 走査が通るまで倉庫へ送らない。順番は `push: false` → 走査 → `docker push`（§12 便1）。
- frontend だけはキャッシュを使わない（§7-3）。

```yaml
name: Build images (GitHub → GHCR)
# build-on-github 便1（docs/handoff/build-on-github/design.md §12 便1・§24）。
# 5 つの完成品を GitHub で組み立てて走査し、組織の非公開の倉庫（ghcr.io）へ送る。本番（prod1）には触らない。
# 便2 で deploy.yml に移してこのファイルは消す。
on:
  push:
    branches: [main]
permissions:
  contents: read   # 倉庫へは secrets.GHCR_PUSH_TOKEN（classic PAT・write:packages）で書く。GITHUB_TOKEN に packages は与えない
env:
  REGISTRY: ghcr.io
  NAMESPACE: ${{ vars.GHCR_NAMESPACE }}   # 名前の正本はここ 1 か所（design.md §5-1）
jobs:
  changes:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    outputs:
      backend: ${{ steps.f.outputs.backend }}
      frontend: ${{ steps.f.outputs.frontend }}
      gemini_egress: ${{ steps.f.outputs.gemini_egress }}
      gha_exporter: ${{ steps.f.outputs.gha_exporter }}
      secretary_agent: ${{ steps.f.outputs.secretary_agent }}
    steps:
      - name: Check settings (design.md §24 C7/C12)
        env:
          GHCR_NAMESPACE: ${{ vars.GHCR_NAMESPACE }}
          GHCR_USER: ${{ vars.GHCR_USER }}
          VITE_FIREBASE_AUTH_DOMAIN: ${{ vars.VITE_FIREBASE_AUTH_DOMAIN }}
          VITE_GCP_PROJECT_ID: ${{ vars.VITE_GCP_PROJECT_ID }}
          VITE_AUTH_PROVIDER: ${{ vars.VITE_AUTH_PROVIDER }}
        run: |
          missing=""
          for n in GHCR_NAMESPACE GHCR_USER VITE_FIREBASE_AUTH_DOMAIN VITE_GCP_PROJECT_ID VITE_AUTH_PROVIDER; do
            if [ -z "${!n}" ]; then missing="$missing $n"; fi
          done
          if [ -n "$missing" ]; then echo "::error::Variables が未登録:$missing"; exit 1; fi
          if ! [[ "$GHCR_NAMESPACE" =~ ^[a-z0-9-]+$ ]]; then echo "::error::GHCR_NAMESPACE は英小文字・数字・ハイフンだけにする"; exit 1; fi
          echo "settings ok"
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5
        with:
          persist-credentials: false
      - uses: dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d # v4.0.3
        id: f
        with:
          filters: |
            common: &common
              - '.github/workflows/build-images.yml'
              - '.github/scripts/image-scan.sh'
              - '.github/scripts/ghcr-private-check.sh'
              - '.gitleaks.toml'
            backend:
              - *common
              - 'backend/**'
            frontend:
              - *common
              - 'frontend/**'
            gemini_egress:
              - *common
              - 'monitoring/prod1/gemini-egress/**'
            gha_exporter:
              - *common
              - 'monitoring/gha-exporter/**'
            secretary_agent:
              - *common
              - 'secretary-agent/**'

  build-backend:
    needs: changes
    if: needs.changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    env:
      IMAGE: salesanchor-backend
    outputs:
      ref: ${{ steps.push.outputs.ref }}
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5
        with:
          persist-credentials: false
      - uses: docker/setup-buildx-action@f87e5991a6d7451dcb8d9637bfbc97413f497069 # v4.4.1
      - uses: docker/login-action@81c6f93d4bc991e510b342a00b419b3bb4efc5c6 # v4.7.0
        with:
          registry: ghcr.io
          username: ${{ vars.GHCR_USER }}
          password: ${{ secrets.GHCR_PUSH_TOKEN }}
      - uses: docker/build-push-action@c3c9e263c25d99ce0380d002d59b67737d91b0dc # v7.4.0
        with:
          context: ./backend
          platforms: linux/amd64
          push: false
          load: true
          provenance: false
          sbom: false
          tags: ${{ env.REGISTRY }}/${{ env.NAMESPACE }}/${{ env.IMAGE }}:${{ github.sha }}
          cache-from: type=gha,scope=backend
          cache-to: type=gha,scope=backend
      - name: Scan image (design.md §7-2)
        run: bash .github/scripts/image-scan.sh "$REGISTRY/$NAMESPACE/$IMAGE:$GITHUB_SHA"
      - name: Push and record digest (design.md §24 C13)
        id: push
        run: |
          TAG="$REGISTRY/$NAMESPACE/$IMAGE:$GITHUB_SHA"
          docker push "$TAG"
          DIGEST="$(docker buildx imagetools inspect "$TAG" --format '{{json .Manifest}}' | jq -r '.digest')"
          if ! [[ "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ ]]; then echo "::error::digest の形が違う"; exit 1; fi
          REF="$REGISTRY/$NAMESPACE/$IMAGE@$DIGEST"
          echo "ref=$REF" >> "$GITHUB_OUTPUT"
          echo "- $IMAGE: \`$REF\`" >> "$GITHUB_STEP_SUMMARY"
      - name: Check package is private (design.md §24 C4/C15)
        env:
          REF: ${{ steps.push.outputs.ref }}
        run: bash .github/scripts/ghcr-private-check.sh "$REF"
```

続けて、残りの 4 つの job を `build-backend` と同じ形で書く。違うのは次の点だけ。

| job | `if:` の出力 | `IMAGE` | `context` | キャッシュ |
|---|---|---|---|---|
| `build-frontend` | `frontend` | `salesanchor-frontend` | `./frontend` | `cache-from`・`cache-to` の 2 行を書かない |
| `build-gemini-egress` | `gemini_egress` | `salesanchor-gemini-egress` | `./monitoring/prod1/gemini-egress` | `type=gha,scope=gemini-egress` |
| `build-gha-exporter` | `gha_exporter` | `salesanchor-gha-exporter` | `./monitoring/gha-exporter` | `type=gha,scope=gha-exporter` |
| `build-secretary-agent` | `secretary_agent` | `salesanchor-secretary-agent` | `./secretary-agent` | `type=gha,scope=secretary-agent` |

`tags:` は `${{ env.IMAGE }}` を使うので、4 つの job でも書き換えない（名前の正本は job の `env.IMAGE` の 1 か所）。

`build-frontend` だけは、さらに次の 2 つを足す。
- `docker/login-action` の前に、次の段を置く:
  ```yaml
      - name: Check secret (design.md §24 C12)
        env:
          VITE_FIREBASE_API_KEY: ${{ secrets.VITE_FIREBASE_API_KEY }}
        run: |
          if [ -z "$VITE_FIREBASE_API_KEY" ]; then echo "::error::secret VITE_FIREBASE_API_KEY が未登録"; exit 1; fi
          echo "secret ok"
  ```
- `docker/build-push-action` の `with:` に、次を足す:
  ```yaml
          build-args: |
            VITE_FIREBASE_API_KEY=${{ secrets.VITE_FIREBASE_API_KEY }}
            VITE_FUNNEL_DASHBOARD=${{ secrets.VITE_FUNNEL_DASHBOARD }}
            VITE_FIREBASE_AUTH_DOMAIN=${{ vars.VITE_FIREBASE_AUTH_DOMAIN }}
            VITE_GCP_PROJECT_ID=${{ vars.VITE_GCP_PROJECT_ID }}
            VITE_AUTH_PROVIDER=${{ vars.VITE_AUTH_PROVIDER }}
  ```
  その直前の行に、注記 `# frontend は第 1 段の ENV VITE_* が層に残るためキャッシュを使わない（design.md §7-3）` を書く。

### 2-2. `.github/scripts/image-scan.sh`（全文）
```bash
#!/usr/bin/env bash
# build-on-github 便1: 完成品の秘密検査（docs/handoff/build-on-github/design.md §7-2・§24 C1/C5/C6/C16）
# 使い方: image-scan.sh <image ref>
#   SCAN_REPORT_ONLY=1 … 当たりがあっても 0 で終わる（試験場の調べ用・tests/sandbox/image-scan-survey.sh）
#   GITLEAKS_CONFIG=<path> … gitleaks の設定を差し替える（既定は置き場の .gitleaks.toml）
# 出力に値は出さない（gitleaks は --redact、名前と履歴はパスと変数名だけ）。記録は公開される。
set -euo pipefail
REF="${1:?usage: image-scan.sh <image ref>}"
ROOT="$(git rev-parse --show-toplevel)"
CONFIG="${GITLEAKS_CONFIG:-$ROOT/.gitleaks.toml}"
GL_VERSION="8.24.3"
GL_SHA256="9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c"
WORK="$(mktemp -d)"
CID=""
cleanup() {  # 片付けの失敗で、通った走査を落とさない（設計審査 REVISE 2）
  if [ -n "$CID" ]; then docker rm -f "$CID" >/dev/null 2>&1 || true; fi
  chmod -R u+rwX "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# 0. gitleaks（版と sha256 を固定・design.md §24-1）
GL_TGZ="gitleaks_${GL_VERSION}_linux_x64.tar.gz"
curl -fsSL -o "$WORK/$GL_TGZ" "https://github.com/gitleaks/gitleaks/releases/download/v${GL_VERSION}/${GL_TGZ}"
echo "${GL_SHA256}  $WORK/$GL_TGZ" | sha256sum -c -
mkdir "$WORK/bin"
tar -xzf "$WORK/$GL_TGZ" -C "$WORK/bin" gitleaks
GL="$WORK/bin/gitleaks"

# 1. 名前の走査（パスだけ出す）
CID="$(docker create "$REF" /scan-noop)"
docker export "$CID" -o "$WORK/fs.tar"
tar -tf "$WORK/fs.tar" > "$WORK/list.txt"
NAME_RE='(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_(rsa|ed25519).*|.*credentials.*\.json|auth\.json|\.npmrc|\.netrc|\.git/.*)$'  # design.md §7-2 の型のまま（C6）
NAME_HITS="$(grep -cE "$NAME_RE" "$WORK/list.txt" || true)"
grep -E "$NAME_RE" "$WORK/list.txt" | sed 's/^/NAME_HIT /' || true

# 2. 中身の走査（gitleaks dir・値は伏せる）
mkdir "$WORK/fs"
if ! tar -xf "$WORK/fs.tar" -C "$WORK/fs" --no-same-owner --no-same-permissions \
     --exclude='dev/*' --exclude='proc/*' --exclude='sys/*' 2>"$WORK/tar.err"; then
  echo "SCAN error: extract failed"; tail -20 "$WORK/tar.err"; exit 1
fi
rm -f "$WORK/fs.tar"
chmod -R u+rwX "$WORK/fs"
if ! "$GL" dir "$WORK/fs" --config "$CONFIG" --no-banner --redact --exit-code 0 \
     --report-format json --report-path "$WORK/gl.json" > "$WORK/gl.log" 2>&1; then
  echo "SCAN error: gitleaks failed"; tail -20 "$WORK/gl.log"; exit 1
fi
LEAK_HITS="$(jq 'length' "$WORK/gl.json")"
jq -r --arg p "$WORK/fs/" '.[] | "LEAK_HIT \(.RuleID) \(.File | ltrimstr($p))"' "$WORK/gl.json"

# 3. 履歴の走査（変数名だけ出す）
HIST_RE='[A-Za-z0-9_]*(_TOKEN|_SECRET|PASSWORD|API_KEY)[A-Za-z0-9_]*='
docker history --no-trunc --format '{{.CreatedBy}}' "$REF" > "$WORK/hist.txt"
HISTORY_HITS="$(grep -cE "$HIST_RE" "$WORK/hist.txt" || true)"
grep -oE "$HIST_RE" "$WORK/hist.txt" | sed 's/=$//' | sort -u | sed 's/^/HISTORY_HIT /' || true

echo "SCAN_SUMMARY image=$REF name_hits=$NAME_HITS leak_hits=$LEAK_HITS history_hits=$HISTORY_HITS"
TOTAL=$((NAME_HITS + LEAK_HITS + HISTORY_HITS))
if [ "$TOTAL" -gt 0 ] && [ "${SCAN_REPORT_ONLY:-0}" != "1" ]; then
  echo "SCAN failed"; exit 1
fi
```

### 2-3. `.github/scripts/ghcr-private-check.sh`（全文）
```bash
#!/usr/bin/env bash
# build-on-github 便1: 倉庫の完成品が非公開かを確かめる（docs/handoff/build-on-github/design.md §24 C4・C15）
# ログインしたままなら読める・ログイン無しでは読めない、の両方。ログイン無しで読めたら落とす。
# 使い方: ghcr-private-check.sh <ghcr.io/<namespace>/<name>@sha256:<64桁>>
set -euo pipefail
REF="${1:?usage: ghcr-private-check.sh <ref@sha256:...>}"
if ! [[ "$REF" =~ @sha256:[0-9a-f]{64}$ ]]; then echo "PRIVATE_CHECK error: ref must end with @sha256:<64 hex>"; exit 1; fi
if ! docker manifest inspect "$REF" > /dev/null; then echo "PRIVATE_CHECK error: logged-in read failed"; exit 1; fi
ANON_DIR="$(mktemp -d)"
trap 'rm -rf "$ANON_DIR" 2>/dev/null || true' EXIT
set +e
ANON_OUT="$(DOCKER_CONFIG="$ANON_DIR" docker manifest inspect "$REF" 2>&1)"
ANON_RC=$?
set -e
if [ "$ANON_RC" -eq 0 ]; then
  echo "PRIVATE_CHECK error: anonymous read succeeded (package is not private)"; exit 1
fi
echo "ANON_MESSAGE ${ANON_OUT:0:300}"
case "$ANON_OUT" in
  *unauthorized*|*UNAUTHORIZED*|*denied*|*DENIED*) echo "PRIVATE_CHECK ok" ;;
  *) echo "::warning::PRIVATE_CHECK anonymous read failed without unauthorized/denied (design.md §24-2 U23)" ;;
esac
```

### 2-4. `tests/sandbox/image-scan-survey.sh`（全文）
```bash
#!/usr/bin/env bash
# build-on-github 便1 の試し（docs/handoff/build-on-github/design.md §24 C8・C16）。
# 5 つの完成品を GitHub の実行機で組み立てて走査し、当たり（パスと規則名だけ）と所要秒を出す。
# 倉庫へは送らない。secrets は使わない。記録は公開されるので値を出さない。試しの鍵はその場で作る。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
LOGDIR="$(mktemp -d)"
CTRL="$(mktemp)"
BUILT=()
cleanup() {
  for t in ${BUILT[@]+"${BUILT[@]}"}; do docker image rm -f "$t" >/dev/null 2>&1 || true; done
  rm -rf "$LOGDIR" "$CTRL" 2>/dev/null || true
}
trap cleanup EXIT
printf '[extend]\nuseDefault = true\n' > "$CTRL"
DUMMY_KEY="AIza$(python3 -c 'import secrets,string;a=string.ascii_letters+string.digits+"-_";print("".join(secrets.choice(a) for _ in range(35)))')"
FAIL=0
df -h /

survey_one() {  # <name> <context> [docker build の追加の引数...]
  local name="$1" ctx="$2"; shift 2
  local tag="survey/$name:local" t0 t1
  t0=$(date +%s)
  if ! docker build --progress=plain -t "$tag" "$@" "$ctx" > "$LOGDIR/$name.log" 2>&1; then
    echo "BUILD_FAILED $name"; tail -60 "$LOGDIR/$name.log"; FAIL=$((FAIL + 1)); return 0
  fi
  BUILT+=("$tag")
  t1=$(date +%s)
  echo "BUILD_SEC $name $((t1 - t0))"
  echo "IMAGE_BYTES $name $(docker image inspect --format '{{.Size}}' "$tag")"
  t0=$(date +%s)
  if ! SCAN_REPORT_ONLY=1 bash .github/scripts/image-scan.sh "$tag"; then
    echo "SCAN_FAILED $name"; FAIL=$((FAIL + 1))
  fi
  t1=$(date +%s)
  echo "SCAN_SEC $name $((t1 - t0))"
}

survey_one backend ./backend
survey_one frontend ./frontend \
  --build-arg "VITE_FIREBASE_API_KEY=$DUMMY_KEY" \
  --build-arg VITE_FIREBASE_AUTH_DOMAIN=survey.invalid \
  --build-arg VITE_GCP_PROJECT_ID=survey \
  --build-arg VITE_FUNNEL_DASHBOARD=mock \
  --build-arg VITE_AUTH_PROVIDER=self
if docker image inspect survey/frontend:local > /dev/null 2>&1; then
  # 試しの鍵が画面の JS に載ったか（載るのが設計どおり）と、既定の規則だけなら当たるか（例外が効いた証拠・C16）
  # shellcheck disable=SC2016
  echo "KEY_IN_ASSETS $(docker run --rm --entrypoint sh survey/frontend:local -c 'grep -rlF "$1" /usr/share/nginx/html/assets | wc -l' sh "$DUMMY_KEY")"
  # 対照の走査が落ちても試し全体を止めず、落ちた理由を記録に出す（設計審査 REVISE 3）
  set +e
  CONTROL_OUT="$(GITLEAKS_CONFIG="$CTRL" SCAN_REPORT_ONLY=1 bash .github/scripts/image-scan.sh survey/frontend:local 2>&1)"
  CONTROL_RC=$?
  set -e
  if [ "$CONTROL_RC" -ne 0 ]; then
    echo "CONTROL_FAILED rc=$CONTROL_RC"; printf '%s\n' "$CONTROL_OUT"; FAIL=$((FAIL + 1))
  fi
  echo "CONTROL_GCP_HITS $(printf '%s\n' "$CONTROL_OUT" | grep -c '^LEAK_HIT gcp-api-key ' || true)"
fi
survey_one gemini-egress ./monitoring/prod1/gemini-egress
survey_one gha-exporter ./monitoring/gha-exporter
survey_one secretary-agent ./secretary-agent
df -h /
echo "SURVEY_FAILURES $FAIL"
[ "$FAIL" -eq 0 ]
```

### 2-5. `.gitleaks.toml`（ファイルの末尾に足す。既存の行は 1 文字も変えない）
```toml

# =============================================================
# build-on-github 便1（docs/handoff/build-on-github/design.md §7-2・§24 C1）
# frontend の完成品の画面の JS には Firebase の web API key が載る（設計どおり・画面を開く人に届く値）。
# 既定の規則 gcp-api-key を名前で広げ、その場所だけを例外にする。他の規則・他の場所は今のまま当てる。
# この場所は置き場に無いので、置き場の走査（secret-scan.yml）の結果は変わらない。
# =============================================================
[[rules]]
id = "gcp-api-key"

[[rules.allowlists]]
description = "frontend 完成品の画面の JS（Firebase web API key は設計どおり載る）"
paths = ['''(^|/)usr/share/nginx/html/assets/[^/]+\.js$''']
```

### 2-6. `.github/workflows/monthly-secret-expiry.yml:22`
- 変更前: `          WATCH_LIST="PIPELINE_PAT SSH_PRIVATE_KEY META_APP_SECRET DISCORD_WEBHOOK_OWNER_PING DISCORD_WEBHOOK_SCHEDULED_REPORT DISCORD_WEBHOOK_PR METADATA_FERNET_KEY GHA_APP_KEY_PATH"`
- 変更後: `          WATCH_LIST="PIPELINE_PAT SSH_PRIVATE_KEY META_APP_SECRET DISCORD_WEBHOOK_OWNER_PING DISCORD_WEBHOOK_SCHEDULED_REPORT DISCORD_WEBHOOK_PR METADATA_FERNET_KEY GHA_APP_KEY_PATH GHCR_PUSH_TOKEN"`
- この行のほかは変えない。

## 3. 確かめてから報告すること（生出力はファイルに残し、パスを書く）
1. `python3 -c "import yaml,sys;[yaml.safe_load(open(p)) for p in sys.argv[1:]]" .github/workflows/build-images.yml .github/workflows/monthly-secret-expiry.yml` が終了 0。
2. `actionlint .github/workflows/build-images.yml .github/workflows/monthly-secret-expiry.yml` の出力全文（入っていなければ、入れ方と版を書く）。指摘が 1 件でもあれば、直す前に報告に全文を書く。
3. `bash -n` を 3 本の .sh に当てて終了 0。`shellcheck` を 3 本に当てた出力全文。
4. `grep -nE 'uses: ' .github/workflows/build-images.yml` の全行が `@<40 桁の英数字> # v` の形であること。
5. `python3 -c "import tomllib;tomllib.load(open('.gitleaks.toml','rb'))"` が終了 0（3.11 未満なら使った方法を書く）。
6. `git diff origin/main --stat` に §1 の 6 ファイルだけが出ること。`git diff origin/main -- .gitleaks.toml` が追加の行だけであること（`-` で始まる行が 0）。
7. 3 本の .sh の実行権（`git ls-files -s` の 100755）。

docker を使う試し（`tests/sandbox/image-scan-survey.sh` を流すこと）は担当では行わない。Opus が GitHub の試験場で流す（design.md §24-3 の 2）。

## 4. 想定される分岐
- P1〜P6 のどれかが外れた → 実装せず BLOCKED:（どこが違うかを書く）。
- actionlint が paths-filter の `filters` の中身（YAML の anchor）に何か言う → 直さずに全文を報告して NEEDS_DECISION:。
- shellcheck が SC2016 以外の警告を出す → 直せるものは直し、何をどう直したかを書く。意味を変える直しは NEEDS_DECISION:。
- `.gitleaks.toml` の末尾が空行で終わっていない → 1 行空けてから足す。それ以外の既存の行には触らない。
- 規則を外す・`[allowlist]` を広げる直しは、どんな理由でもしない。
- 迷ったら止まって NEEDS_DECISION: で Opus に戻す。

## 5. 終わり方
1. commit は shingo-cc 名義で 1 つ。文の最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
2. `git log -1 --format='%H %an %s'` を報告に書く。
3. 今の枝（`release/build-on-github-bin1`）へ push する。force push はしない。
4. `git log origin/release/build-on-github-bin1 -1 --format=%H` が 2. と同じであること。
5. 報告の最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか 1 つ。

END OF CARD
