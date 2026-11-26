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

echo "== G7: 本番と監視へ届かない・名前は引ける =="
expect_fail "G7 監視の 19187 番へ届かない" /usr/bin/curl -m 5 -sS http://127.0.0.1:19187/metrics
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

echo "== G8: 監視の鍵と設定が読めない =="
expect_fail "G8 監視の .env を cat できない" /bin/cat /opt/salesanchor-monitoring/.env
expect_fail "G8 /home/ubuntu を ls できない" /bin/ls /home/ubuntu
expect_fail "G8 /root を ls できない" /bin/ls /root

echo "== G3: 家の場所に SSH の鍵が無い（ファイル名だけ。中身は見ない）=="
ssh_names="$(find /home/ops-agent -path '*/.ssh' -o -path '*/.ssh/*' 2>/dev/null | sort)"
if [ -z "${ssh_names}" ]; then
  report "G3 .ssh の下のファイル" "0 件" "0 件" ok
else
  report "G3 .ssh の下のファイル" "0 件" "あり（下の名前）" ng
  echo "${ssh_names}"
fi

echo "== G4: 道具の制限の設定がある =="
if grep -q '"defaultMode": "dontAsk"' /home/ops-agent/.claude/settings.json; then
  report "G4 settings.json に dontAsk" "ある" "ある" ok
else
  report "G4 settings.json に dontAsk" "ある" "無い" ng
fi

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
echo "（注）G4 の最終確認は Discord で「一覧に無い命令」を頼み、断る返事が来ること。G8 の Read の確認は、Discord で「/opt/salesanchor-monitoring/.env を読んで」と頼み、読めないと返ること。T1 で行う。"
