#!/usr/bin/env bash
# 01 と 02 を順に流し、画面の記録を同じ場所に残す（PO が sudo で流す）
set -euo pipefail
cd /home/ubuntu/ops-trial
bash 01-prepare.sh 2>&1 | tee 01.log
script -q -e -c "bash /home/ubuntu/ops-trial/02-install.sh" 02.log
chmod 644 01.log 02.log
echo "=== 01 と 02 が終わりました。この窓は閉じてかまいません ==="
