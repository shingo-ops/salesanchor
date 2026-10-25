#!/bin/bash
# git-safe.sh — 囲いの外で作業場所に向けて動かす git に付ける上書き（ADR-1039・discord-pdca 設計 §4-5）
#
# Discord 発のセッションが件の作業場所に仕込んだ設定（core.fsmonitor・core.hooksPath）で、
# 自動回収（reaper-worktree.sh）や片付け（disk-janitor.sh）の git が別の命令を動かさないようにする。
# 使い方: source して、作業場所に向けた git に `git "${GIT_SAFE_ARGS[@]}" -C <場所> ...` と付ける。
# source 時に何も実行しない（配列を定義するだけ）。
# shellcheck disable=SC2034  # source 先で使う
GIT_SAFE_ARGS=(-c core.fsmonitor=false -c core.hooksPath=/dev/null)
