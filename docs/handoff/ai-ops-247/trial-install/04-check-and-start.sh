#!/usr/bin/env bash
# 04-check-and-start.sh — 段取り 5（管理者が `sudo bash 04-check-and-start.sh` で流す）
# 正の設計: server-agent-design.md §12-2（G3・G7・G8）・§12-3 段取り 5。
# 1 つでも期待と違えば、起動せずに止まる。全部合えば enable --now して値を表示する。
# 結果の各行は「期待」と「実際」を並べて出す。鍵の中身は表示しない（G3 はファイル名だけ）。
#
# 確かめ方の出どころ: 設計 §12-2 G7・G8 の「確かめ方」の列。systemd-run の書き方は systemd 255 の --help で確認。
# 未確認: G7 の下でログインと Discord の道具が動くか（試し T1 で見る）。
#
# 注: curl の「失敗」は終了コードが 0 以外であること。IPAddressDeny で塞がれた先は接続できず失敗になる。

set -uo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "NG: root で流してください（sudo bash 04-check-and-start.sh）" >&2
  exit 1
fi
for need in /etc/systemd/system/ops-agent.service /home/ops-agent/.claude/settings.json /home/ops-agent/.local/bin/claude; do
  if [ ! -e "${need}" ]; then
    echo "NG: ${need} がありません。01・02 を先に流してください。" >&2
    exit 1
  fi
done

# unit と同じ G2・G7・G8 の値
PROPS=(
  -p MemoryHigh=1200M
  -p MemoryMax=1500M
  -p MemorySwapMax=0
  -p OOMScoreAdjust=1000
  -p "IPAddressDeny=localhost link-local multicast 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 49.212.137.46 49.212.160.98"
  -p IPAddressAllow=127.0.0.53
  -p ProtectSystem=strict
  -p ReadWritePaths=/home/ops-agent
  -p "InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring"
  -p PrivateTmp=yes
  -p NoNewPrivileges=yes
)

run_as_agent() {
  systemd-run --uid=ops-agent --wait --collect --pipe -q \
    --working-directory=/home/ops-agent/work \
    -E HOME=/home/ops-agent \
    "${PROPS[@]}" \
    "$@"
}

# 守りを外した窓（G2・G8 だけ・G7 なし）: G7 の対照用
run_no_g7() {
  systemd-run --uid=ops-agent --wait --collect --pipe -q \
    --working-directory=/home/ops-agent/work \
    -E HOME=/home/ops-agent \
    -p MemoryHigh=1200M -p MemoryMax=1500M -p MemorySwapMax=0 -p OOMScoreAdjust=1000 \
    -p ProtectSystem=strict -p ReadWritePaths=/home/ops-agent \
    -p "InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring" \
    -p PrivateTmp=yes -p NoNewPrivileges=yes \
    "$@"
}

# 守りの外（G2 だけ）: G8 の対照用
run_g2_only() {
  systemd-run --uid=ops-agent --wait --collect --pipe -q \
    --working-directory=/home/ops-agent/work \
    -E HOME=/home/ops-agent \
    -p MemoryHigh=1200M -p MemoryMax=1500M -p MemorySwapMax=0 -p OOMScoreAdjust=1000 \
    "$@"
}

FAILS=0
report() {
  # report <名前> <期待> <実際> <ok|ng>
  local mark="OK"
  if [ "$4" != "ok" ]; then
    mark="NG"
    FAILS=$((FAILS + 1))
  fi
  printf '[%s] %s\n    期待: %s\n    実際: %s\n' "${mark}" "$1" "$2" "$3"
}

expect_fail() {
  # expect_fail <名前> <命令...> : 失敗（終了コード 0 以外）が期待
  local name="$1"
  shift
  if run_as_agent "$@" >/dev/null 2>&1; then
    report "${name}" "失敗する（届かない・読めない）" "成功した（届いた・読めた）" ng
  else
    report "${name}" "失敗する（届かない・読めない）" "失敗した" ok
  fi
}

echo "== 対照: 上限の書き方が合っているか（/bin/true が 0 で終わる）=="
if ! run_as_agent /bin/true >/dev/null 2>&1; then
  echo "NG: 上限の書き方が違います（G2・G7・G8 の同じ値で /bin/true が 0 で終わりません）。確かめにならないので止めます。" >&2
  exit 1
fi
echo "OK: /bin/true が 0 で終わりました。"

echo "== G1: sudo も docker も使えない =="
sudo_out="$(sudo -l -U ops-agent 2>&1)"
case "${sudo_out}" in
  *"not allowed"*) report "G1 sudo -l -U ops-agent" "not allowed を含む" "含む" ok ;;
  *) report "G1 sudo -l -U ops-agent" "not allowed を含む" "含まない" ng ;;
esac
if test -S /run/docker.sock; then
  report "G1 /run/docker.sock がある" "ある" "ある" ok
else
  report "G1 /run/docker.sock がある" "ある" "無い" ng
fi
expect_fail "G1 docker.sock に書けない（守りの下）" /usr/bin/test -w /run/docker.sock
if run_g2_only /usr/bin/test -w /run/docker.sock >/dev/null 2>&1; then
  report "G1 docker.sock に書けない（守りの外）" "失敗する（組に入っていない）" "成功した" ng
else
  report "G1 docker.sock に書けない（守りの外）" "失敗する（組に入っていない）" "失敗した" ok
fi

echo "== G7: 本番と監視へ届かない・名前は引ける =="
# 対照: 守りを外した窓（G7 なし）では届く。届かなければ「確かめにならない」
if run_no_g7 /usr/bin/curl -m 5 -sS -o /dev/null http://127.0.0.1:19187/metrics >/dev/null 2>&1; then
  report "G7 対照: 守り無しで 19187 番へ届く" "届く" "届いた" ok
else
  report "G7 対照: 守り無しで 19187 番へ届く" "届く（届かないと確かめにならない）" "届かなかった" ng
fi
expect_fail "G7 監視の 19187 番へ届かない" /usr/bin/curl -m 5 -sS -o /dev/null http://127.0.0.1:19187/metrics
if run_no_g7 /usr/bin/curl -m 5 -sS -o /dev/null http://49.212.160.98:3000 >/dev/null 2>&1; then
  report "G7 対照: 守り無しで 3000 番へ届く" "届く" "届いた" ok
else
  report "G7 対照: 守り無しで 3000 番へ届く" "届く（届かないと確かめにならない）" "届かなかった" ng
fi
expect_fail "G7 prod2 自身の 3000 番へ届かない" /usr/bin/curl -m 5 -sS http://49.212.160.98:3000

if run_as_agent /usr/bin/getent hosts api.anthropic.com >/dev/null 2>&1; then
  report "G7 名前が引ける（api.anthropic.com）" "引ける" "引けた" ok
else
  report "G7 名前が引ける（api.anthropic.com）" "引ける" "引けなかった" ng
fi

code="$(run_as_agent /usr/bin/curl -m 10 -sS -o /dev/null -w '%{http_code}' https://api.anthropic.com 2>/dev/null)"
case "${code}" in
  [1-9][0-9][0-9])
    report "G7 api.anthropic.com に繋がる" "3 桁の数（000 以外）" "${code}" ok
    ;;
  *)
    report "G7 api.anthropic.com に繋がる" "3 桁の数（000 以外）" "${code:-（空）}" ng
    ;;
esac

echo "== G8: 監視の鍵と設定が読めない（場所の権限 stat -c %a で見る）=="
# 出どころ: systemd の CONTAINER_INTERFACE「all zero access mode」と namespace.c の MOUNT_INACCESSIBLE
for d in /home/ubuntu /root /opt/salesanchor-monitoring; do
  under="$(run_as_agent /usr/bin/stat -c %a "${d}" 2>/dev/null)"
  outside="$(run_g2_only /usr/bin/stat -c %a "${d}" 2>/dev/null)"
  if [ "${under}" = "0" ] && [ -n "${outside}" ] && [ "${outside}" != "0" ]; then
    report "G8 ${d}" "守りの下 0・守りの外 0 以外" "下 ${under}・外 ${outside}" ok
  else
    report "G8 ${d}" "守りの下 0・守りの外 0 以外" "下 ${under:-（空）}・外 ${outside:-（空）}" ng
  fi
done

echo "== G3: 家の場所に SSH の鍵が無い（ファイル名だけ。中身は見ない）=="
ssh_names="$(find /home/ops-agent -path '*/.ssh' -o -path '*/.ssh/*' 2>/dev/null | sort)"
if [ -z "${ssh_names}" ]; then
  report "G3 .ssh の下のファイル" "0 件" "0 件" ok
else
  report "G3 .ssh の下のファイル" "0 件" "あり（下の名前）" ng
  echo "${ssh_names}"
fi

echo "== G4: 道具の制限の設定がある =="
G4_PY='
import json, sys
try:
    p = json.load(open("/home/ops-agent/.claude/settings.json")).get("permissions", {})
    allow = set(p.get("allow", []))
    deny = set(p.get("deny", []))
    need_allow = {"mcp__plugin_discord_discord__" + n for n in ("reply", "react", "fetch_messages")}
    need_deny = {"Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Agent",
                 "mcp__plugin_discord_discord__download_attachment",
                 "mcp__plugin_discord_discord__edit_message",
                 "mcp__plugin_discord_discord__create_thread",
                 "Read(//home/ops-agent/.claude/**)", "Read(//home/ops-agent/.claude.json)"}
    ok = p.get("defaultMode") == "dontAsk" and need_allow <= allow and need_deny <= deny
except Exception:
    ok = False
sys.exit(0 if ok else 1)
'
if python3 -c "${G4_PY}" >/dev/null 2>&1; then
  report "G4 settings.json の制限（dontAsk・許す 3・断る 12）" "全部ある" "全部ある" ok
else
  report "G4 settings.json の制限（dontAsk・許す 3・断る 12）" "全部ある" "1 つ以上欠けている" ng
fi
# 道具（discord プラグイン）が有効か。中身は表示せず ○× だけ
if python3 -c 'import json,sys; d=json.load(open("/home/ops-agent/.claude/settings.json")); sys.exit(0 if d.get("enabledPlugins",{}).get("discord@claude-plugins-official") is True else 1)' >/dev/null 2>&1; then
  report "G4 enabledPlugins の discord@claude-plugins-official" "true" "true" ok
else
  report "G4 enabledPlugins の discord@claude-plugins-official" "true" "true ではない" ng
fi
if test -d /home/ops-agent/.claude/plugins; then
  report "G4 /home/ops-agent/.claude/plugins の場所" "ある" "ある" ok
else
  report "G4 /home/ops-agent/.claude/plugins の場所" "ある" "無い" ng
fi
# 持ち主と権限だけ見る（中身は読まない）
for f in /home/ops-agent/.claude/channels/discord/.env /home/ops-agent/.claude/channels/discord/access.json; do
  got="$(stat -c '%U %a' "${f}" 2>/dev/null)"
  if [ "${got}" = "ops-agent 600" ]; then
    report "G4 ${f##*/} の持ち主と権限" "ops-agent 600" "${got}" ok
  else
    report "G4 ${f##*/} の持ち主と権限" "ops-agent 600" "${got:-（ファイル無し）}" ng
  fi
done

echo
if [ "${FAILS}" -ne 0 ]; then
  echo "NG が ${FAILS} 件あります。起動せずに止めます。設計担当（Opus）へ上の表をそのまま渡してください。" >&2
  exit 1
fi

echo "全部 OK。起動します。"
systemctl enable --now ops-agent.service
echo "== 起動後 =="
systemctl is-active ops-agent.service
systemctl show -p MemoryHigh,MemoryMax,MemorySwapMax,IPAddressDeny,IPAddressAllow,InaccessiblePaths ops-agent.service
echo "（注）G4 の最終確認は Discord で「一覧に無い命令」を頼み、断る返事が来ること。G8 の証拠は上の stat の確かめだけ（Read は作業の場所の外なので、守りが無くても dontAsk で断られ、証拠にならない）。"
