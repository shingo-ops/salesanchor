#!/usr/bin/env bash
# 06-rollback.sh — 設計 §12-6 の戻し方（管理者が `sudo bash 06-rollback.sh` で流す）
# 止める → unit を消して daemon-reload → ops-agent を家の場所ごと消す。
# 監視の仕組みには触らない（担当の unit と利用者だけを対象にする）。
# 2 回流しても壊れない（無ければ飛ばす）。
# 注: これは試しを取りやめる台本。流す前に PO の指示を得ること。

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "NG: root で流してください（sudo bash 06-rollback.sh）" >&2
  exit 1
fi

UNIT_PATH="/etc/systemd/system/ops-agent.service"

echo "== 1/3 止める =="
if systemctl cat ops-agent.service >/dev/null 2>&1; then
  systemctl disable --now ops-agent.service || true
  systemctl reset-failed ops-agent.service || true
else
  echo "unit はありません。飛ばします。"
fi

echo "== 2/3 unit を消して daemon-reload =="
if [ -e "${UNIT_PATH}" ]; then
  rm -f "${UNIT_PATH}"
fi
systemctl daemon-reload

echo "== 3/3 ops-agent を家の場所ごと消す =="
if id ops-agent >/dev/null 2>&1; then
  if pgrep -u ops-agent >/dev/null 2>&1; then
    echo "NG: ops-agent のプロセスがまだ動いています。次を確認し、PO と相談してください:" >&2
    pgrep -u ops-agent -a >&2 || true
    exit 1
  fi
  userdel -r ops-agent   # 家の場所ごと消えるので、置いた .env（ボットの鍵）も消える
  echo "消しました。"
else
  echo "ops-agent はありません。飛ばします。"
fi

echo
echo "完了（担当の unit と利用者だけ。監視の仕組みには触っていません）。"
echo "残り（PO の手で行う。この台本は触らない）:"
echo "  1. Discord の Developer Portal で、ボットの鍵を作り直して古い鍵を無効にする（ボットごと消してもよい）"
echo "  2. claude.ai の設定で、このサーバーのログイン（セッション）を外す"
