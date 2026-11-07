#!/usr/bin/env bash
# U2: 登録されたサーバーにボットが入っているかを読むだけで確かめる（docs/handoff/discord-guild-membership-check/design.md）。
# PO が手元で `!` で流す。書き込みなし。出力にサーバーの番号・名前・鍵は出ない。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SSH_OPTS=(-F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes)
HOST="ubuntu@49.212.137.46"
OUT_DIR="/tmp/CC報告ファイル/u2"
mkdir -p "$OUT_DIR"
ssh "${SSH_OPTS[@]}" "$HOST" 'docker exec -i -w /app astro-webapp-backend-1 python -' \
  < "$HERE/discord_guild_membership_check.py" 2>&1 | tee "$OUT_DIR/run.txt"
