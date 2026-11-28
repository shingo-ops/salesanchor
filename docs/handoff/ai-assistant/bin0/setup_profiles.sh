#!/usr/bin/env bash
# 便0: 試しの Hermes のデータの置き場（Docker の名前付き volume）に 3 部屋を作る台本（card-bin0a.md 手順 4c）。
# 使い方: bash setup_profiles.sh [VOLUME]   （既定 bin0-data）
# 前提: /tmp/bin0-secrets/key-default・key-coordinator・key-calendar・key-invoice（中身は鍵の値だけ・本台本は値を出さない）
# 固定設定は置かない（管理者の固定設定は run_bin0.py --set fixed-config で作り /etc/hermes に読み取り専用で渡す）。
# 人格: coordinator は coordinator-soul.md。calendar・invoice は secretary-agent/prompt.txt を「作るときに写す」（正本は prompt.txt）。
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
VOLUME="${1:-bin0-data}"
SECRETS="${BIN0_SECRETS:-/tmp/bin0-secrets}"
IMAGE="nousresearch/hermes-agent@sha256:ef0650d523ee1b5ab32c779acabc446d9936869a9932591553688a62bcf0c42f"

for f in key-default key-coordinator key-calendar key-invoice; do
  [ -s "$SECRETS/$f" ] || { echo "鍵のファイルが無い: $f" >&2; exit 1; }
done
echo "prompt_txt_sha256=$(sha256sum "$REPO/secretary-agent/prompt.txt" | cut -d' ' -f1)"

docker volume create "$VOLUME" >/dev/null
INNER='
set -eu
for room in coordinator calendar invoice; do
  hermes profile create "$room" --no-alias --no-skills >/dev/null 2>&1 || true
  [ -d /opt/data/profiles/$room ] || { echo "部屋を作れなかった: $room" >&2; exit 1; }
  if [ "$room" = coordinator ]; then cp /setup/coordinator-soul.md /opt/data/profiles/$room/SOUL.md
  else cp /prompt/prompt.txt /opt/data/profiles/$room/SOUL.md; fi
  # 鍵は部屋の .env にだけ置く（既にある行は除く）。値は出さない
  grep -v "^API_SERVER_KEY=" /opt/data/profiles/$room/.env > /tmp/env.new || true
  eval "KEYVAL=\${KEY_$room}"
  [ "${#KEYVAL}" -ge 16 ] || { echo "鍵が短い・空: $room" >&2; exit 1; }
  printf "API_SERVER_KEY=%s\n" "$KEYVAL" >> /tmp/env.new
  cat /tmp/env.new > /opt/data/profiles/$room/.env
  echo "room=$room soul_bytes=$(wc -c < /opt/data/profiles/$room/SOUL.md) key_len=${#KEYVAL} cfg_key_lines=$(grep -c -E "(level|memory_enabled|user_profile_enabled|api_server|background_review|title_generation|fallback_providers|multiplex_profiles)" /opt/data/profiles/$room/config.yaml || true)"
done
'
# 鍵は環境変数ファイル（600）で渡す（容器の中の hermes 利用者は /secrets を読めないため）。終わったら消す
ENVF="$SECRETS/setup.env"
( umask 077; for r in coordinator calendar invoice; do printf 'KEY_%s=%s\n' "$r" "$(cat "$SECRETS/key-$r")"; done > "$ENVF" )
set +e
docker run --rm --env-file "$ENVF" -v "$VOLUME":/opt/data -v "$HERE":/setup:ro \
  -v "$REPO/secretary-agent":/prompt:ro "$IMAGE" sh -c "$INNER" 2>&1 | grep -E "^(room=|部屋を作れなかった|鍵が短い)"
rc=${PIPESTATUS[0]}
rm -f "$ENVF"
exit "$rc"
