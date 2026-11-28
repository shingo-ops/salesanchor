#!/usr/bin/env bash
# 使い方: send.sh <容器名> <部屋> <本文JSON ファイル(容器の /tmp/b13 に置く)>  ; 鍵は /tmp/bin0-secrets/key-<部屋>（値は出さない）
N=$1; R=$2; BODY=$3
K=$(cat /tmp/bin0-secrets/key-$R)
docker exec -i $N curl -s -D - -w '\nHTTP_CODE=%{http_code}\n' -H "Authorization: Bearer $K" -H 'Content-Type: application/json' \
  --data-binary @- http://127.0.0.1:8642/p/$R/v1/chat/completions < $BODY
