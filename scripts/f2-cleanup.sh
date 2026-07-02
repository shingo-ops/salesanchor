#!/usr/bin/env bash
# F2 prod1 auto-cleanup
# 消すのは (1) AGE_HOURS より古い exited コンテナ（FinishedAt基準） (2) AGE_HOURS より古い build cache のみ
# volume / image / 稼働中コンテナには一切触れない（volume・image系コマンドを書かない）
set -uo pipefail
AGE_HOURS="${1:-168}"     # 既定 7日
TARGET="${2:-both}"       # both | containers | cache
LOG="${F2_LOG:-/tmp/f2-cleanup.log}"
ts(){ date '+%Y-%m-%d %H:%M:%S %Z'; }
log(){ echo "[$(ts)] $*" | tee -a "$LOG"; }
log "=== F2 START age=${AGE_HOURS}h target=${TARGET} ==="
if [ "$TARGET" = "both" ] || [ "$TARGET" = "containers" ]; then
  NOW=$(date +%s); TH=$(( AGE_HOURS * 3600 ))
  log "-- exited containers --"
  for id in $(docker ps -a --filter status=exited --format '{{.ID}}'); do
    fin=$(docker inspect -f '{{.State.FinishedAt}}' "$id" 2>/dev/null)
    fe=$(date -d "$fin" +%s 2>/dev/null || echo 0)
    nm=$(docker inspect -f '{{.Name}}' "$id" 2>/dev/null)
    if [ "${fe:-0}" -le 0 ]; then log "SKIP $id $nm (no FinishedAt)"; continue; fi
    age=$(( NOW - fe ))
    if [ "$age" -ge "$TH" ]; then
      docker rm "$id" >/dev/null 2>&1 && log "REMOVED $id $nm ($((age/3600))h old)" || log "FAIL-RM $id $nm"
    else
      log "KEEP $id $nm ($((age/3600))h < ${AGE_HOURS}h)"
    fi
  done
fi
if [ "$TARGET" = "both" ] || [ "$TARGET" = "cache" ]; then
  log "-- build cache (until=${AGE_HOURS}h) --"
  docker buildx prune --filter "until=${AGE_HOURS}h" --force 2>&1 | tee -a "$LOG"
fi
log "=== F2 DONE ==="
