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
