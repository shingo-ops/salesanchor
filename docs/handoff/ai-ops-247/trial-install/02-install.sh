#!/usr/bin/env bash
# 02-install.sh — 段取り 3（管理者が `sudo bash 02-install.sh` で流す。端末のある窓で）
# 正の設計: server-agent-design.md §12-3 段取り 3。導入も、担当と同じ上限（G2・G8）の下で行う。G7 は付けない（段取り 3・4 は G7 なし）。
#
# 公式資料で確かめた点（2026-11-26）:
#  - Claude Code の入れ方 `curl -fsSL https://claude.ai/install.sh | bash`、入る場所 ~/.local/bin/claude:
#    https://code.claude.com/docs/en/setup
#    注意: 同じ頁の「System requirements」は「4 GB+ RAM」。prod2 の空きは 2,579MB（段取り 1）。設計は「空きが約 512MB 要る」としている。
#    公式の 4GB は動作条件の目安で、導入が通るかは未確認。通らなければ止まるだけで、サーバーは壊れない。
#  - Bun の入れ方 `curl -fsSL https://bun.com/install | bash`: https://github.com/oven-sh/bun の README（bun.sh は取得できなかったため README を使用）。
#  - systemd-run の --uid・--pty・--wait・--collect・--property(-p)・--working-directory: systemd 255 の `systemd-run --help` で確認。
#    公式の man ページ（freedesktop.org）は取得できなかった。
# 未確認: Bun の入れ方は unzip を使う（README に明記なし）。無ければ止める（下の確認）。

set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "NG: root で流してください（sudo bash 02-install.sh）" >&2
  exit 1
fi

if ! id ops-agent >/dev/null 2>&1; then
  echo "NG: ops-agent がありません。先に 01-prepare.sh を流してください。" >&2
  exit 1
fi
for c in curl unzip; do
  if ! command -v "${c}" >/dev/null 2>&1; then
    echo "NG: ${c} がありません。管理者が入れてから流し直してください（この台本は入れません）。" >&2
    exit 1
  fi
done

avail_mb() { free -m | awk '/^Mem:/ {print $7}'; }

check_free() {
  local a
  a="$(avail_mb)"
  echo "空きメモリ(available): ${a} MB（止める基準: 600 MB 未満）"
  if [ "${a}" -lt 600 ]; then
    echo "NG: 空きが 600MB を切っています。入れずに止めます。PO に報告してください。" >&2
    exit 1
  fi
}

# G2 と G8 と同じ値（G7 は付けない）
PROPS=(
  -p MemoryHigh=1200M
  -p MemoryMax=1500M
  -p MemorySwapMax=0
  -p OOMScoreAdjust=1000
  -p ProtectSystem=strict
  -p ReadWritePaths=/home/ops-agent
  -p "InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring"
  -p PrivateTmp=yes
  -p NoNewPrivileges=yes
)
ENVS=(
  -E HOME=/home/ops-agent
  -E PATH=/home/ops-agent/.local/bin:/home/ops-agent/.bun/bin:/usr/local/bin:/usr/bin:/bin
)

run_as_agent() {
  systemd-run --uid=ops-agent --pty --wait --collect \
    --working-directory=/home/ops-agent/work \
    "${PROPS[@]}" "${ENVS[@]}" \
    "$@"
}

echo "== 入れる前 =="
free -m
check_free

echo "== Claude Code（公式の入れ方）=="
run_as_agent /bin/bash -c 'curl -fsSL https://claude.ai/install.sh | bash'

echo "== Bun（公式の入れ方）=="
run_as_agent /bin/bash -c 'curl -fsSL https://bun.com/install | bash'

echo "== 入れた後 =="
free -m
check_free

echo "== 版の確認（上限の下で）=="
run_as_agent /home/ops-agent/.local/bin/claude --version
run_as_agent /home/ops-agent/.bun/bin/bun --version
echo "完了。次は PO の手で 03-po-login.md。"
