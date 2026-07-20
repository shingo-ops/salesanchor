#!/usr/bin/env bash
# F2 auto-cleanup v2
# 消すのは (1) AGE_HOURSより古いexitedコンテナ (2) 古いbuild cache (3) 未使用イメージ(稼働中＋各系統最新2世代を除外・名指し1件ずつ・force不使用)
# volume には一切触れない(volume系コマンドを書かない)
set -uo pipefail
AGE_HOURS="${1:-168}"
TARGET="${2:-both}"   # both=従来2職務 / containers / cache / images=イメージのみ / all=全職務＋黒板
LOG="${F2_LOG:-/tmp/f2-cleanup.log}"
TEXTFILE_DIR="${F2_TEXTFILE_DIR:-/home/ubuntu/node_exporter_textfile}"
FAIL=0
ts(){ date '+%Y-%m-%d %H:%M:%S %Z'; }
log(){ echo "[$(ts)] $*" | tee -a "$LOG"; }
log "=== F2 START age=${AGE_HOURS}h target=${TARGET} ==="

run_containers(){
  NOW=$(date +%s); TH=$(( AGE_HOURS * 3600 ))
  log "-- exited containers --"
  for id in $(docker ps -a --filter status=exited --format '{{.ID}}'); do
    fin=$(docker inspect -f '{{.State.FinishedAt}}' "$id" 2>/dev/null)
    fe=$(date -d "$fin" +%s 2>/dev/null || echo 0)
    nm=$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null)
    if [ "${fe:-0}" -le 0 ]; then log "SKIP $id $nm (no FinishedAt)"; continue; fi
    age=$(( NOW - fe ))
    if [ "$age" -ge "$TH" ]; then
      docker rm "$id" >/dev/null 2>&1 && log "REMOVED $id $nm ($((age/3600))h old)" || { log "FAIL-RM $id $nm"; FAIL=$((FAIL+1)); }
    else
      log "KEEP $id $nm ($((age/3600))h < ${AGE_HOURS}h)"
    fi
  done
}

run_cache(){
  log "-- build cache (until=${AGE_HOURS}h) --"
  docker buildx prune --filter "until=${AGE_HOURS}h" --force 2>&1 | tee -a "$LOG"
}

run_images(){
  log "-- unused images (keep: running + latest2 per repo) --"
  KEEP=$( { docker ps -q | xargs -r docker inspect -f '{{.Image}}';
            docker images --no-trunc --format '{{.Repository}} {{.ID}}' \
            | awk '$1!="<none>" && !seen[$1" "$2]++ { c[$1]++; if (c[$1]<=2) print $2 }'; } | sort -u )
  ALL=$(docker images --no-trunc -q | sort -u)
  CAND=$(printf '%s\n' "$ALL" | grep -v -F -x -f <(printf '%s\n' "$KEEP") || true)
  NCAND=$(printf '%s\n' "$CAND" | grep -c . || true)
  log "MANIFEST keep=$(printf '%s\n' "$KEEP" | grep -c .) candidates=${NCAND}"
  printf '%s\n' "$CAND" | while read -r cid; do [ -n "$cid" ] && log "MANIFEST-ITEM $cid"; done
  for id in $CAND; do
    tags=$(docker images --no-trunc --format '{{.ID}} {{.Repository}}:{{.Tag}}' | awk -v i="$id" '$1==i && $2!="<none>:<none>" {print $2}')
    if [ -z "$tags" ]; then
      docker rmi "$id" >>"$LOG" 2>&1 && log "REMOVED $id (untagged)" || { log "FAIL-RM $id (untagged)"; FAIL=$((FAIL+1)); }
    else
      for t in $tags; do
        docker rmi "$t" >>"$LOG" 2>&1 && log "REMOVED $t ($id)" || { log "FAIL-RM $t ($id)"; FAIL=$((FAIL+1)); }
      done
    fi
  done
}

write_blackboard(){
  if [ "$FAIL" -eq 0 ]; then
    mkdir -p "$TEXTFILE_DIR" 2>/dev/null || { log "BLACKBOARD mkdir FAIL"; return; }
    tmp=$(mktemp "$TEXTFILE_DIR/.f2.XXXXXX") || { log "BLACKBOARD mktemp FAIL"; return; }
    {
      echo "# HELP f2_cleanup_last_success_timestamp F2 cleanup last full-success unix time"
      echo "# TYPE f2_cleanup_last_success_timestamp gauge"
      echo "f2_cleanup_last_success_timestamp $(date +%s)"
    } > "$tmp" && mv "$tmp" "$TEXTFILE_DIR/f2_cleanup.prom" && log "BLACKBOARD updated"
  else
    log "BLACKBOARD skipped (FAIL=${FAIL})"
  fi
}

case "$TARGET" in
  both) run_containers; run_cache ;;
  containers) run_containers ;;
  cache) run_cache ;;
  images) run_images ;;
  all) run_containers; run_cache; run_images; write_blackboard ;;
  *) log "UNKNOWN TARGET ${TARGET}"; exit 2 ;;
esac
log "=== F2 DONE (FAIL=${FAIL}) ==="
