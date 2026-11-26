#!/usr/bin/env bash
# 03b-put-discord-keys.sh — ボットの鍵と PO の番号を置く（管理者が `sudo bash 03b-put-discord-keys.sh` で流す。PO が見えない入力に貼る）
# 正の設計: docs/handoff/ai-ops-247/server-agent-design.md §12-3
#
# 出どころ: 道具の本体 external_plugins/discord/server.ts
#   （anthropics/claude-plugins-official 668a0c65）39-56 行（.env の読み方・DISCORD_ACCESS_MODE=static）・
#   183-200 行（static では名簿を書き換えない）、同じ道具の ACCESS.md の Config file 欄（access.json の形）。
#
# なぜ手で置くか: /discord:configure と /discord:access は中で Write の道具を使い、01 の制限（G4）で止まる。
#   また鍵が会話の記録に残る。だからこの台本で、窓の外から置く。
# 鍵の値は表示しない・ログに出さない。set -x は使わない。

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "NG: root で流してください（sudo bash 03b-put-discord-keys.sh）" >&2
  exit 1
fi
if ! id ops-agent >/dev/null 2>&1; then
  echo "NG: 利用者 ops-agent がありません。01 を先に流してください。" >&2
  exit 1
fi

if pgrep -u ops-agent >/dev/null; then
  echo "NG: ops-agent の仕事が動いています。03 の窓を閉じてから流してください。" >&2
  exit 1
fi

read -rs -p "ボットの鍵を貼って Enter（画面に出ません）: " TOKEN
echo
if [ -z "${TOKEN}" ]; then
  echo "NG: 鍵が空です。止めます。" >&2
  exit 1
fi
read -r -p "PO の Discord の利用者番号（数字）: " UID_PO
if ! [[ "${UID_PO}" =~ ^[0-9]{17,20}$ ]]; then
  echo "NG: 利用者番号は 17〜20 桁の数字です。止めます。" >&2
  exit 1
fi

D=/home/ops-agent/.claude/channels/discord
for p in /home/ops-agent/.claude /home/ops-agent/.claude/channels "${D}"; do
  if [ -L "${p}" ]; then
    echo "NG: ${p} がシンボリックリンクです。止めます。" >&2
    exit 1
  fi
done
install -d -o ops-agent -g ops-agent -m 700 /home/ops-agent/.claude
install -d -o ops-agent -g ops-agent -m 700 /home/ops-agent/.claude/channels
install -d -o ops-agent -g ops-agent -m 700 "${D}"

for p in /home/ops-agent/.claude /home/ops-agent/.claude/channels "${D}"; do
  if [ -L "${p}" ]; then
    echo "NG: ${p} がシンボリックリンクです。止めます。" >&2
    exit 1
  fi
done

for f in "${D}/.env" "${D}/access.json"; do
  if [ -L "${f}" ]; then
    echo "NG: ${f} がシンボリックリンクです。止めます。" >&2
    exit 1
  fi
done

umask 077
TMP_ENV="$(mktemp "${D}/.tmp.XXXXXX")"
TMP_ACC="$(mktemp "${D}/.tmp.XXXXXX")"
trap 'rm -f "${TMP_ENV}" "${TMP_ACC}"' EXIT
printf '%s\n' "DISCORD_BOT_TOKEN=${TOKEN}" "DISCORD_ACCESS_MODE=static" > "${TMP_ENV}"
printf '%s\n' "{\"dmPolicy\":\"allowlist\",\"allowFrom\":[\"${UID_PO}\"],\"groups\":{},\"pending\":{}}" > "${TMP_ACC}"
chown ops-agent:ops-agent "${TMP_ENV}" "${TMP_ACC}"
chmod 600 "${TMP_ENV}" "${TMP_ACC}"
mv -fT "${TMP_ENV}" "${D}/.env"
mv -fT "${TMP_ACC}" "${D}/access.json"

unset TOKEN
echo "置きました（持ち主と権限だけ表示。中身は出しません）:"
ls -l "${D}/.env" "${D}/access.json"
echo "完了。次は 03-po-login.md の E。"
