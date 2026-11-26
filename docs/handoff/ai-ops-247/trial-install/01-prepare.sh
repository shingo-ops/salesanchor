#!/usr/bin/env bash
# 01-prepare.sh — 段取り 2（管理者が `sudo bash 01-prepare.sh` で流す）
# 正の設計: docs/handoff/ai-ops-247/server-agent-design.md §12（G1・G2・G4・G7・G8）
#
# やること: 利用者 ops-agent を作る(G1) → 作業の場所を作る → 道具の制限(G4)を置く → unit を置く(daemon-reload だけ。enable・start はしない)
# 2 回流しても壊れない（03 の D の前まで。あれば作らない・設定ファイルは同じ中身で置き直す）。
# 鍵・トークンの値はこの台本に無い。表示もしない。
#
# 公式資料で確かめた点（2026-11-26）:
#  - permissions.defaultMode "dontAsk": https://code.claude.com/docs/en/permission-modes
#  - 道具の名前 mcp__plugin_<plugin>_<server>__<tool>: https://code.claude.com/docs/en/mcp （plugin の章）と
#    https://code.claude.com/docs/en/permissions （MCP の章）。plugin 名 discord・サーバー名 discord は
#    https://github.com/anthropics/claude-plugins-official/tree/main/external_plugins/discord の .mcp.json の鍵 "discord" による。
#    道具 7 つ(reply・react・list_emojis・edit_message・fetch_messages・download_attachment・create_thread)は同じ README の表による。
#  - Read の絶対パスは「//」始まり（「/」始まりは設定ファイルの場所からの相対）: https://code.claude.com/docs/en/permissions （Read と Edit の章）
#  - deny は allow より先に効く: 同 permissions（未確認: 台本を書いた時に deny の優先順の行を原文で引いていない）
#  - systemd の各設定: systemd.resource-control・systemd.exec（systemd 255 の systemctl show で値が見える）。
#    この台本を書いた環境では公式の man ページを開けず、Context7 も使えなかったため、設計 §12-2 に書かれた確認結果に頼る。
#
# 未確認（導入の時に見る）:
#  - U-a: Type=forking と tmux の形で、再起動のあと確認の画面が出ずに立ち上がるか。
#  - tmux の中の claude が正常に終わったとき、tmux のサーバーも消えて unit が止まる。正常に終わっても立ち上げ直すため always にした。
#    10 分に 5 回で止まり（StartLimitIntervalSec=600・StartLimitBurst=5。[Unit] に置く: systemd.unit「StartLimitIntervalSec=」）、毎日の確認で見つける。
#  - Type=forking で tmux の親が抜けたあとの本体の見つけ方（PIDFile なし・systemd の推測）。

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "NG: root で流してください（sudo bash 01-prepare.sh）" >&2
  exit 1
fi

AGENT_USER="ops-agent"
AGENT_HOME="/home/${AGENT_USER}"
UNIT_PATH="/etc/systemd/system/ops-agent.service"

echo "== 1/4 利用者 ${AGENT_USER}（G1）=="
if id "${AGENT_USER}" >/dev/null 2>&1; then
  echo "既にあります。作りません。"
else
  useradd --create-home --shell /bin/bash "${AGENT_USER}"
  echo "作りました。"
fi
echo "id の表示:"
id "${AGENT_USER}"
# sudo・docker の組に入っていたら失敗で止める（G1）
for g in $(id -nG "${AGENT_USER}"); do
  case "${g}" in
    sudo|docker)
      echo "NG: ${AGENT_USER} が ${g} の組に入っています。G1 に反するので止めます。" >&2
      exit 1
      ;;
  esac
done
echo "OK: sudo・docker の組に入っていません。"

echo "== 2/4 作業の場所 ${AGENT_HOME}/work =="
install -d -o "${AGENT_USER}" -g "${AGENT_USER}" -m 0755 "${AGENT_HOME}/work"
ls -ld "${AGENT_HOME}/work"
# tmux のつなぎ口を家の場所に置く（PrivateTmp=yes で /tmp の中が管理者から見えないため）
install -d -o "${AGENT_USER}" -g "${AGENT_USER}" -m 0700 "${AGENT_HOME}/.tmux"

echo "== 3/4 道具の制限（G4）を置く =="
# 値は鍵ではない。道具の名前と許す・断るの一覧だけ。
install -d -o "${AGENT_USER}" -g "${AGENT_USER}" -m 0700 "${AGENT_HOME}/.claude"
if [ -f "${AGENT_HOME}/.claude/settings.json" ] && grep -q '"enabledPlugins"' "${AGENT_HOME}/.claude/settings.json"; then
  echo "NG: 道具を入れた後です。01 を流し直すと道具の記録が消えるので止めます。置き直すときは 06 で戻してから最初から。" >&2
  exit 1
fi
cat > "${AGENT_HOME}/.claude/settings.json" <<'EOF'
{
  "permissions": {
    "defaultMode": "dontAsk",
    "allow": [
      "mcp__plugin_discord_discord__reply",
      "mcp__plugin_discord_discord__react",
      "mcp__plugin_discord_discord__fetch_messages"
    ],
    "deny": [
      "Bash",
      "Write",
      "Edit",
      "NotebookEdit",
      "WebFetch",
      "WebSearch",
      "Agent",
      "mcp__plugin_discord_discord__download_attachment",
      "mcp__plugin_discord_discord__edit_message",
      "mcp__plugin_discord_discord__create_thread",
      "Read(//home/ops-agent/.claude/**)",
      "Read(//home/ops-agent/.claude.json)"
    ]
  }
}
EOF
chown "${AGENT_USER}:${AGENT_USER}" "${AGENT_HOME}/.claude/settings.json"
chmod 600 "${AGENT_HOME}/.claude/settings.json"
ls -l "${AGENT_HOME}/.claude/settings.json"

echo "== 4/4 unit ${UNIT_PATH}（置くだけ。enable も start もしない）=="
cat > "${UNIT_PATH}" <<'EOF'
[Unit]
StartLimitIntervalSec=600
StartLimitBurst=5
Description=ops-agent (Claude Code + Discord channel, trial)
After=network-online.target
Wants=network-online.target

[Service]
# 起動の形（U-a・未確認）: tmux の中で claude を動かす。止めるのは tmux kill-session。
# tmux のつなぎ口（-S）は家の場所: PrivateTmp=yes で /tmp の中が管理者から見えないため。
Type=forking
User=ops-agent
WorkingDirectory=/home/ops-agent/work
Environment=HOME=/home/ops-agent
Environment=PATH=/home/ops-agent/.local/bin:/home/ops-agent/.bun/bin:/usr/local/bin:/usr/bin:/bin
Environment=TERM=xterm-256color
ExecStart=/usr/bin/tmux -S /home/ops-agent/.tmux/ops-agent.sock new-session -d -s ops-agent '/home/ops-agent/.local/bin/claude --channels plugin:discord@claude-plugins-official'
ExecStop=-/usr/bin/tmux -S /home/ops-agent/.tmux/ops-agent.sock kill-session -t ops-agent
Restart=always
RestartSec=30

# G2 メモリ
MemoryHigh=1200M
MemoryMax=1500M
MemorySwapMax=0
OOMScoreAdjust=1000

# G7 本番と監視へ届く道を塞ぐ（名前を引く 127.0.0.53 だけ開ける。Allow は Deny より先に判定される）
# IPv6: localhost は ::1/128 も含む（systemd.resource-control）。prod2 には全体向けの IPv6 アドレスも既定の道も無い（2026-11-26 ip -6 で確認）。
IPAddressDeny=localhost link-local multicast 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 49.212.137.46 49.212.160.98
IPAddressAllow=127.0.0.53

# G8 監視の鍵と設定を読めなくする
ProtectSystem=strict
ReadWritePaths=/home/ops-agent
InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring
PrivateTmp=yes
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
EOF
chmod 644 "${UNIT_PATH}"
systemctl daemon-reload
echo "unit を置いて daemon-reload しました。まだ起動していません。"
systemctl is-enabled ops-agent.service || true
systemctl is-active ops-agent.service || true
echo "完了。次は 02-install.sh。"
