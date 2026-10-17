#!/usr/bin/env bash
# 最初の試験: postgres:16 を起動して select 1 を実行する（sandbox-test の動作確認用）。
# パスワードは試験専用の固定値（秘密ではない）。
set -euo pipefail

NAME=sb-pg
cleanup() {
  docker logs "$NAME" 2>&1 | tail -50 || true
  docker rm -f "$NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run -d --name "$NAME" -e POSTGRES_PASSWORD=sandbox postgres:16

ready=0
for _ in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U postgres >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "postgres did not become ready within 60s"; exit 1; }

out=$(docker exec "$NAME" psql -U postgres -Atc 'select 1')
echo "select 1 => ${out}"
[ "$out" = "1" ] || { echo "unexpected output: ${out}"; exit 1; }
echo "smoke: OK"
