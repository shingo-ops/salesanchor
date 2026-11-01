#!/usr/bin/env bash
# ADR-1056 段2: チャット秘書の容器に渡すログイン情報（CLAUDE_CODE_OAUTH_TOKEN）を VPS に置き、容器を作り直す。
# PO が手元で `!` で流す。トークンは画面に出さず（read -rs）、ssh の引数にも入れず（標準入力で渡す）、
# AI は値を見ない・書かない。置き場の正本は VPS の /home/ubuntu/.config/salesanchor/secretary-agent.env（chmod 600）。
# 接続先・鍵は AGENTS.md「VPS 直作業禁止」と docs/handoff/rehearsal-env/design-b-ssh-isolation.md に合わせる。
set -euo pipefail

SSH_OPTS=(-F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes)
HOST="ubuntu@49.212.137.46"

read -rs -p "トークンを貼って Enter: " TOKEN
echo
if [ -z "$TOKEN" ]; then
  echo "トークンが空です。中止します。" >&2
  exit 1
fi

# 1) 専用ファイルに書く（トークンは標準入力。リモートのコマンド文字列には入らない）
printf '%s' "$TOKEN" | ssh "${SSH_OPTS[@]}" "$HOST" \
  'umask 077; install -d -m 700 /home/ubuntu/.config/salesanchor; printf "CLAUDE_CODE_OAUTH_TOKEN=%s\n" "$(cat)" > /home/ubuntu/.config/salesanchor/secretary-agent.env; chmod 600 /home/ubuntu/.config/salesanchor/secretary-agent.env'
unset TOKEN

# 2) イメージを作って容器を作り直す
ssh "${SSH_OPTS[@]}" "$HOST" \
  'cd /home/ubuntu/salesanchor && docker build -t astro-webapp-secretary-agent ./secretary-agent && docker compose -p astro-webapp-secretary -f docker-compose.secretary-agent.yml up -d --force-recreate --no-build'

# 3) /health の ready だけ出す（true/false。値は出ない）
ssh "${SSH_OPTS[@]}" "$HOST" \
  "docker exec secretary-agent node -e \"require('http').get('http://127.0.0.1:8090/health',r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>console.log('ready='+JSON.parse(b).ready))})\""

# 4) つながりの試し（K4 の記録。出力をそのまま出す。トークンは出ない）
ssh "${SSH_OPTS[@]}" "$HOST" 'docker exec secretary-agent node /app/probe.mjs' || echo "（probe の終了コードが 0 以外: K4 不合格の可能性。上の connected を確認）"
