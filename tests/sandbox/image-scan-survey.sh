#!/usr/bin/env bash
# build-on-github 便1 の試し（docs/handoff/build-on-github/design.md §25 C8・§25-9）。
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
survey_one frontend ./frontend --build-arg VITE_FUNNEL_DASHBOARD=mock
survey_one gemini-egress ./monitoring/prod1/gemini-egress
survey_one gha-exporter ./monitoring/gha-exporter
survey_one secretary-agent ./secretary-agent
df -h /
echo "SURVEY_FAILURES $FAIL"
[ "$FAIL" -eq 0 ]
