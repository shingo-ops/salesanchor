#!/bin/bash
# S4 の道具の試験 (a)〜(e) を1コマンドで再実行する。ダミーファイルだけを使う。
# 使い方: bash docs/handoff/design-approval-ticket/routine/test_sm_tools.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 -I "${HERE}/test_sm_tools.py"
