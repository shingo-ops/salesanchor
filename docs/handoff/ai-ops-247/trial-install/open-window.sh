#!/usr/bin/env bash
# 03-po-login.md の B の 1 行を台本にしたもの（PO が sudo で流す。G2・G8 の上限付き・G7 なし）
set -euo pipefail
exec systemd-run --uid=ops-agent --pty --wait --collect --working-directory=/home/ops-agent/work -p MemoryHigh=1200M -p MemoryMax=1500M -p MemorySwapMax=0 -p OOMScoreAdjust=1000 -p ProtectSystem=strict -p ReadWritePaths=/home/ops-agent -p "InaccessiblePaths=/home/ubuntu /root /opt/salesanchor-monitoring" -p PrivateTmp=yes -p NoNewPrivileges=yes -E HOME=/home/ops-agent -E PATH=/home/ops-agent/.local/bin:/home/ops-agent/.bun/bin:/usr/local/bin:/usr/bin:/bin /bin/bash
