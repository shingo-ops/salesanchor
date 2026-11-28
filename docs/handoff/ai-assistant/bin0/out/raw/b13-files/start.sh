#!/usr/bin/env bash
# 使い方: start.sh <容器名> <volume> <固定設定ディレクトリ> ; 作り方は README 手順 3 の守り + --network none + 固定設定 ro
set -u
N=$1; V=$2; M=$3
D=nousresearch/hermes-agent@sha256:ef0650d523ee1b5ab32c779acabc446d9936869a9932591553688a62bcf0c42f
docker run -d --name $N --network none --read-only --cap-drop ALL --cap-add SETGID --cap-add CHOWN --cap-add SETUID --cap-add FOWNER \
  --security-opt no-new-privileges:true --tmpfs /tmp --tmpfs /run:exec --env-file /tmp/bin0-secrets/default.env \
  -v $V:/opt/data -v $M:/etc/hermes:ro -v /tmp/b13/fake:/fake:ro $D gateway run >/dev/null
docker exec -d $N python3 /fake/fake_ai.py
