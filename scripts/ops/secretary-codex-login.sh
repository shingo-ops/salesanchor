#!/usr/bin/env bash
# ADR-1058 段3: secretary-codex の ChatGPT ログイン（PO の月額契約）。PO が手元で `!` で流す。AI は流さない。
# 中で codex login --device-auth を動かす。画面に出るアドレスを PO が手元のブラウザで開き、出たコードを入れる。
# ログインの鍵は VPS の名前付きボリューム secretary-codex-home の auth.json にだけ残る（画面に出さない・写さない）。
# 手元の Mac の codex のログインとは別に持つ（design.md §5-1）。
# 「device code を使えない」と出た時は、ChatGPT の設定でデバイスコードのログインを許してからもう一度流す。
# 接続先・鍵は AGENTS.md「VPS 直作業禁止」と docs/handoff/rehearsal-env/design-b-ssh-isolation.md に合わせる（前例 scripts/ops/place-secretary-token.sh）。
set -euo pipefail

SSH_OPTS=(-F /dev/null -i "$HOME/.ssh/manual-only/id_ed25519" -o IdentitiesOnly=yes)
HOST="ubuntu@49.212.137.46"

# 1) ログイン（端末をつなぐ。容器は read_only なので HOME は書ける /tmp にする。CODEX_HOME はイメージの /home/node/.codex）
ssh -t "${SSH_OPTS[@]}" "$HOST" 'docker exec -it -e HOME=/tmp secretary-codex codex login --device-auth'

# 2) /health の ready と last_refresh だけ出す（鍵の値は出ない）
ssh "${SSH_OPTS[@]}" "$HOST" \
  "docker exec secretary-codex node -e \"require('http').get('http://127.0.0.1:8090/health',r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>{const j=JSON.parse(b);console.log('ready='+j.ready+' last_refresh='+j.last_refresh)})})\""
