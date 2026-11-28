#!/usr/bin/env bash
# 07-read-pane.sh — 担当の画面を読むだけ（管理者が sudo で流す。何も押さない・何も変えない）
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then echo "NG: sudo で流してください" >&2; exit 1; fi
out=/home/ubuntu/ops-trial/pane.txt
# shellcheck disable=SC2024  # 台本全体が root で動くので、書き出しは root でよい
sudo -u ops-agent tmux -S /home/ops-agent/.tmux/ops-agent.sock capture-pane -p -S -300 -t ops-agent > "${out}"
chown ubuntu:ubuntu "${out}"
echo "読みました（${out}・$(wc -l < "${out}") 行）。画面には出しません。"
