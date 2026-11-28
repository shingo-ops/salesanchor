#!/usr/bin/env bash
# 使い方: get.sh <容器名> <部屋(鍵の選択)> <METHOD> <path> ; 鍵は /tmp/bin0-secrets/key-<部屋>（値は出さない）
N=$1; R=$2; M=$3; P=$4
K=$(cat /tmp/bin0-secrets/key-$R)
docker exec $N curl -s -X $M -w '\nHTTP_CODE=%{http_code}\n' -H "Authorization: Bearer $K" http://127.0.0.1:8642$P
