#!/usr/bin/env bash
# a-github-token.sh — CASE_AGENT_TOKEN を作り、GitHub secret と Mac の Keychain に置く
# 実行: PO が Mac で `bash a-github-token.sh`（値は画面・ファイル・引数に出さない）
# 途中で止まったとき: GitHub secret だけできて Keychain が×なら、README の「途中で止まったとき」に従う。
set -euo pipefail
umask 077

REPO="shingo-ops/salesanchor"
NAME="CASE_AGENT_TOKEN"
KC_SERVICE="salesanchor-case-agent-token"

if ! gh auth status >/dev/null 2>&1; then
  echo "止まりました: gh auth status が通りません。先に gh auth login をしてください。"
  exit 1
fi

if gh secret list -R "$REPO" | awk '{print $1}' | grep -qx "$NAME"; then
  echo "止まりました: GitHub secret ${NAME} は既にあります（上書きしません）。"
  exit 1
fi

if security find-generic-password -s "$KC_SERVICE" >/dev/null 2>&1; then
  echo "止まりました: Keychain に ${KC_SERVICE} の項目が既にあります（上書きしません）。"
  exit 1
fi

step="鍵の生成"
trap 'rc=$?; if [ "$rc" -ne 0 ]; then echo "失敗: 「${step}」で止まりました。GitHub secret と Keychain の状態を下の確かめで見てください。"; fi; unset v' EXIT

v="$(openssl rand -hex 32)"

step="GitHub secret への登録"
printf '%s' "$v" | gh secret set "$NAME" -R "$REPO"

step="Keychain への登録"
printf 'add-generic-password -s %s -a case -w %s\n' "$KC_SERVICE" "$v" | security -i >/dev/null 2>&1

unset v

step="確かめ"
if gh secret list -R "$REPO" | awk '{print $1}' | grep -qx "$NAME"; then
  echo "○ GitHub secret ${NAME} があります"
else
  echo "× GitHub secret ${NAME} が見つかりません"
fi
if security find-generic-password -s "$KC_SERVICE" >/dev/null 2>&1; then
  echo "○ Keychain に ${KC_SERVICE} の項目があります"
else
  echo "× Keychain に ${KC_SERVICE} の項目がありません"
fi
