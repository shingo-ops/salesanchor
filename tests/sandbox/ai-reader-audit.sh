#!/bin/bash
# ADR-1024 K3 改訂 G5: ai-reader の AUDIT が /dev/log → journald に届き、logging none でも attach で出力が届くことを確かめる。
# 実行: gh workflow run sandbox-test.yml --ref (ブランチ名) -f test=ai-reader-audit
# 出荷する docker-compose.ai-reader.yml と ./backend の Dockerfile のイメージ（appuser）をそのまま使う。
# secrets・本番には触れない（接続文字列は届かないダミー値）。後始末は trap で行う。
# README の「失敗時に docker logs」の代わり: logging none では docker logs が使えない。
# このため attach の出力（stdout・stderr）をファイルへ保存し、trap の中で出す。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
OUT="$(mktemp -d)"
COMPOSE=docker-compose.ai-reader.yml
BAD_SRC=/nonexistent-ai-reader-log
export AI_READER_DATABASE_URL='postgresql://x:y@127.0.0.1:1/none'

cleanup() {
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "== 失敗: 保存した出力を出す"
    for f in "$OUT"/*; do
      [ -f "$f" ] || continue
      echo "--- $f"
      head -c 3000 "$f" || true
    done
  fi
  docker network rm astro-webapp_backnet >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

ng() { echo "NG: $1"; exit 1; }

echo "== 0. 準備（ネットワーク・イメージ）"
docker network create astro-webapp_backnet >/dev/null
docker compose -f "$COMPOSE" build ai-reader
ls -l /dev/log

echo "== 1. (a)(b) 64KB 超の SQL → rc=2、stderr に AUDIT、journald に同じ行"
python3 -c "import sys; sys.stdout.write('SELECT 1 -- ' + 'a' * (64 * 1024 + 10))" > "$OUT/big.sql"
SINCE="$(date '+%Y-%m-%d %H:%M:%S')"
sleep 1
set +e
docker compose -f "$COMPOSE" run --rm -T --no-deps ai-reader < "$OUT/big.sql" > "$OUT/a.out" 2> "$OUT/a.err"
rc=$?
set -e
[ "$rc" = 2 ] || ng "(a) rc=$rc (expected 2)"
grep -q '^AUDIT ts=.* result=rejected ' "$OUT/a.err" || ng "(a) stderr に AUDIT 行が無い"
sha=$(grep -o 'sha=[0-9a-f]\{12\}' "$OUT/a.err" | head -1 | cut -d= -f2)
[ -n "$sha" ] || ng "(a) sha が取れない"
sleep 2
sudo journalctl -t ai-reader-audit --since "$SINCE" --no-pager > "$OUT/journal.txt"
n=$(grep -c "AUDIT ts=.* sha=$sha " "$OUT/journal.txt" || true)
[ "$n" = 1 ] || ng "(b) journald の sha=$sha の行が $n 行（期待 1）"
echo "OK (a)(b): rc=2, sha=$sha"

echo "== 2. (c) logging none でも attach で stdout・stderr が届く"
docker compose -f "$COMPOSE" run --rm -T --no-deps --entrypoint sh ai-reader -c 'echo OUT; echo ERR >&2' > "$OUT/c.out" 2> "$OUT/c.err"
grep -qx OUT "$OUT/c.out" || ng "(c) stdout に OUT が無い"
grep -qx ERR "$OUT/c.err" || ng "(c) stderr に ERR が無い"
echo "OK (c)"

echo "== 3. (d) source の /dev/log が無い → rc≠0 で、ホストにディレクトリが作られない"
cat > "$OUT/override.yml" <<EOF
services:
  ai-reader:
    volumes: !override
      - type: bind
        source: $BAD_SRC
        target: /dev/log
        bind:
          create_host_path: false
EOF
set +e
docker compose -f "$COMPOSE" -f "$OUT/override.yml" run --rm -T --no-deps ai-reader < "$OUT/big.sql" > "$OUT/d.out" 2> "$OUT/d.err"
rc=$?
set -e
[ "$rc" != 0 ] || ng "(d) rc=0（失敗するはず）"
[ ! -e "$BAD_SRC" ] || ng "(d) ホストに $BAD_SRC が作られた"
echo "OK (d): rc=$rc"

echo "ALL OK"
