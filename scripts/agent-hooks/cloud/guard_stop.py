#!/usr/bin/env python3
"""元: ~/.claude/scripts/japanese-reply-guard.py（Stop）。K5。
最後の返事に日本語（ひらがな・カタカナ・漢字）が1文字も無ければ止める（exit 2）。
stop_hook_active が true（すでに続行中）なら止めない。読めない入力・空の返事は通す。
"""
import json
import re
import sys

_JA = re.compile(r"[぀-ヿ㐀-鿿]")
REASON = "直前の応答に日本語がありません。ユーザーへの応答は常に日本語で書きます。同じ内容を日本語で書き直してください（コード・コマンド・識別子はそのままでよい）。"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("stop_hook_active") is True:
        return 0
    msg = data.get("last_assistant_message")
    if not isinstance(msg, str) or not msg.strip():
        return 0
    if not _JA.search(msg):
        print(REASON, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
