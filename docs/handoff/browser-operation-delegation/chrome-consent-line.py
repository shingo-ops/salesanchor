#!/usr/bin/env python3
"""chrome-consent-line.py - 同意票に書く「画面操作の1行」を作る台本（ADR-1085 便1）。

使い方: python3 chrome-consent-line.py '<tool_input の JSON>' <道具の短い名>
  例: python3 chrome-consent-line.py '{"action":"left_click","action_summary":"保存ボタンを押す"}' computer
標準出力に1行。中身は hooks/chrome_common.py の consent_line() と同じ（見張りが作る1行と一致する・T19）。
"""
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
# 取り付け後の置き場（~/.claude/scripts/chrome-op-guard）があればそちら、無ければ試作の hooks を使う
for cand in (os.path.join(HERE, "hooks"), os.path.join(HERE, "chrome-op-guard")):
    if os.path.isfile(os.path.join(cand, "chrome_common.py")):
        sys.path.insert(0, cand)
        break
import chrome_common as cm  # noqa: E402


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("使い方: chrome-consent-line.py '<tool_input の JSON>' <道具の短い名>\n")
        return 2
    try:
        ti = json.loads(argv[1])
    except Exception:
        sys.stderr.write("tool_input が JSON として読めません\n")
        return 2
    if not isinstance(ti, dict):
        sys.stderr.write("tool_input は JSON の連想配列にしてください\n")
        return 2
    t = argv[2]
    if t.startswith(cm.PREFIX):
        t = t[len(cm.PREFIX):]
    line = cm.consent_line(t, ti)
    if any(c in line for c in ("\n", "\r", "$", "`")):
        sys.stderr.write("この1行は改行・$・バッククォートを含み、同意票では通りません。action_summary を直してください\n")
        return 1
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
