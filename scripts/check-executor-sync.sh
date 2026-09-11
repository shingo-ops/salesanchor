#!/usr/bin/env bash
# =============================================================================
# check-executor-sync.sh — CI 用: AGENTS.md のマーカー区間が SSOT と一致するか検証
# 差分があれば非ゼロで終了する。
# =============================================================================

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
exec bash "$REPO_ROOT/scripts/sync-executor-rules.sh" --check
