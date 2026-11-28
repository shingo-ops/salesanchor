#!/usr/bin/env bash
# 03c-add-allow-id.sh — 返事をする相手（PO のアカウント）を1つ足し、担当を起動し直す（PO 本人が自分の端末で sudo で流す）
# 出どころ: 道具の説明書 ACCESS.md（allowFrom の形）。DISCORD_ACCESS_MODE=static は起動時の内容に固定するので、足したあとに起動し直す。
# 鍵（.env）には触らない。足すのは利用者番号だけ。
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then echo "NG: sudo で流してください" >&2; exit 1; fi
F=/home/ops-agent/.claude/channels/discord/access.json
if [ -L "${F}" ] || [ ! -f "${F}" ]; then echo "NG: ${F} がありません（またはリンクです）。止めます。" >&2; exit 1; fi
read -r -p "足す Discord の利用者番号（数字）: " NEW_ID
NEW_ID="${NEW_ID//[[:space:]]/}"
if ! [[ "${NEW_ID}" =~ ^[0-9]{17,20}$ ]]; then echo "NG: 利用者番号は 17〜20 桁の数字です。止めます。" >&2; exit 1; fi
umask 077
TMP="$(mktemp "$(dirname "${F}")/.tmp.XXXXXX")"
trap 'rm -f "${TMP}"' EXIT
python3 -I - "${F}" "${NEW_ID}" "${TMP}" <<'PY'
import json, sys
src, new_id, dst = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(src))
allow = d.get("allowFrom", [])
if new_id not in allow:
    allow.append(new_id)
d["allowFrom"] = allow
if d.get("dmPolicy") != "allowlist" or d.get("groups") != {}:
    sys.exit("NG: access.json の形が想定と違います（dmPolicy allowlist・groups 空）。止めます。")
json.dump(d, open(dst, "w"))
print("返事をする相手の数:", len(allow))
PY
chown ops-agent:ops-agent "${TMP}"
chmod 600 "${TMP}"
mv -fT "${TMP}" "${F}"
ls -l "${F}"
systemctl restart ops-agent.service
sleep 5
echo "== 起動し直し後 =="
systemctl is-active ops-agent.service
