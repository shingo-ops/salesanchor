#!/usr/bin/env bash
# 使い方: health.sh <容器名> [秒の上限] ; /health が 200 になるまで。出力: 200 になった時刻(epoch ms)
N=$1; T=${2:-120}
timeout $T bash -c "until [ \"\$(docker exec $N curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8642/health 2>/dev/null)\" = 200 ]; do sleep 1; done" && date +%s%3N
