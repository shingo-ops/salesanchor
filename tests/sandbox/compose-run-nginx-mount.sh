#!/bin/bash
# ADR-1052 段2 カード第6.1版 §3(j)(m): deploy.yml の「Recreate nginx」の前の点検の形を、本物の docker compose で確かめる。
#   ①〜④ = §3(j): docker compose run --rm --no-deps -T nginx nginx -t が、サービスの取り付けと networks をそのまま使い、ports を開かない
#   ⑤〜⑦ = §3(m): run の -v がサービスの取り付け（同じ道）を置き換える / 取り付け元を mv で入れ替えた後の作り直し
# 実行: gh workflow run sandbox-test.yml --ref release/cloud-case-ai-stage2 -f test=compose-run-nginx-mount
# secrets・本番には触れない。nginx のイメージは docker-compose.yml の nginx と同じ版。後始末は trap で行う。
# 各番号で「== ①」の見出しと PASS/FAIL の行を出し、どれかが FAIL なら最後に 0 でない終わり方をする。
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# docker-compose.yml の nginx サービスのイメージ（本番と同じ版）
IMG=$(awk '/^  nginx:/{f=1; next} f && /^    image:/{print $2; exit} f && /^  [a-z]/{exit}' docker-compose.yml)
[ -n "${IMG}" ] || { echo "FAIL: docker-compose.yml の nginx のイメージを読めない"; exit 1; }

WORK="$(mktemp -d)"
PROJ="cnmtest"
PROBE="probe-run"
FAILS=0

dc() { docker compose -p "${PROJ}" -f "${WORK}/compose.yml" "$@"; }
dcb() { docker compose -p "${PROJ}" -f "${WORK}/compose-broken.yml" "$@"; }
pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }

cleanup() {
  rc=$?
  if [ "${rc}" -ne 0 ] || [ "${FAILS}" -ne 0 ]; then
    # 片付ける前に原因を出す（先に消すと追えない）
    echo "---- docker logs（失敗のため）"
    docker logs "${PROJ}-nginx-1" 2>&1 | tail -50 || true
    docker logs "${PROBE}" 2>&1 | tail -20 || true
    docker ps -a --format '{{.Names}} {{.Status}}' 2>&1 | head -20 || true
  fi
  docker rm -f "${PROBE}" >/dev/null 2>&1 || true
  dc down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "${WORK}"
  exit "${rc}"
}
trap cleanup EXIT

mkdir -p "${WORK}/x" "${WORK}/y" "${WORK}/bad" "${WORK}/z"
# サービスの取り付けの中身 / -v で渡す別の中身 / 壊れた設定 / 入れ替え後の中身（443 は使わない。置き換わりの目印だけを見る）
printf 'server { listen 8080; location / { return 200 "SERVICE"; } }\n' > "${WORK}/x/nginx.conf"
printf 'server { listen 8080; location / { return 200 "OTHER"; } }\n' > "${WORK}/y/other.conf"
printf 'server { listen 8080; bogus_directive on; }\n' > "${WORK}/bad/nginx.conf"
printf 'server { listen 8080; location / { return 200 "REPLACED"; } }\n' > "${WORK}/z/new.conf"

# docker-compose.yml の nginx と同じ形: 単一ファイルの取り付け（:ro）・ports に 443 を 1 つ・networks frontnet
cat > "${WORK}/compose.yml" <<EOF
name: ${PROJ}
services:
  nginx:
    image: ${IMG}
    ports:
      - "443:443"
    volumes:
      - ./x/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    networks:
      - frontnet
networks:
  frontnet:
EOF
sed 's#./x/nginx.conf#./bad/nginx.conf#' "${WORK}/compose.yml" > "${WORK}/compose-broken.yml"

echo "== 0. 準備: イメージ=${IMG}"
docker version --format 'docker {{.Server.Version}}'
docker compose version
df -h / | tail -1
dc up -d
dc ps

echo "== ① run --rm --no-deps -T nginx nginx -t が 0 で終わり、起きている容器と ports がぶつからない"
rc1=0
dc run --rm --no-deps -T nginx nginx -t || rc1=$?
echo "rc(--service-ports 無し)=${rc1}"
rc1b=0
dc run --rm --no-deps -T --service-ports nginx nginx -t || rc1b=$?
echo "rc(--service-ports 付き。起きている容器と 443 がぶつかるはず)=${rc1b}"
if [ "${rc1}" -eq 0 ] && [ "${rc1b}" -ne 0 ]; then
  pass "① ports を開かずに nginx -t が 0（--service-ports を付けるとぶつかって失敗＝ports は開いていない）"
else
  fail "① rc=${rc1} / --service-ports 付き rc=${rc1b}（期待: 0 と 0 でない）"
fi

echo "== ② 同じ run で /etc/nginx/conf.d/default.conf が compose の取り付けの中身"
out2=$(dc run --rm --no-deps -T nginx cat /etc/nginx/conf.d/default.conf) || true
echo "${out2}"
if [ "${out2}" = "$(cat "${WORK}/x/nginx.conf")" ]; then
  pass "② run の中の default.conf がサービスの取り付けの中身（SERVICE）"
else
  fail "② run の中の default.conf がサービスの取り付けの中身でない"
fi

echo "== ③ run -d の容器の networks に ${PROJ}_frontnet があり、Ports に HostPort が無い"
dc run -d --no-deps --name "${PROBE}" nginx sleep 60 >/dev/null
nets=$(docker inspect -f '{{json .NetworkSettings.Networks}}' "${PROBE}")
ports=$(docker inspect -f '{{json .NetworkSettings.Ports}}' "${PROBE}")
echo "Networks=${nets}"
echo "Ports=${ports}"
docker rm -f "${PROBE}" >/dev/null 2>&1 || true
if echo "${nets}" | grep -q "\"${PROJ}_frontnet\"" && ! echo "${ports}" | grep -q 'HostPort'; then
  pass "③ ${PROJ}_frontnet に繋がり、HostPort が無い"
else
  fail "③ networks か ports が期待と違う"
fi

echo "== ④ 中身の壊れた設定を取り付けたとき nginx -t が 0 でない（点検が本当に効く）"
rc4=0
dcb run --rm --no-deps -T nginx nginx -t || rc4=$?
echo "rc=${rc4}"
if [ "${rc4}" -ne 0 ]; then
  pass "④ 壊れた設定で nginx -t が 0 でない（rc=${rc4}）"
else
  fail "④ 壊れた設定でも nginx -t が 0 で終わった"
fi

echo "== ⑤ -v で同じ道を置き換える（cat が -v の中身で、nginx -t が 0）"
rc5=0
out5=$(dc run --rm --no-deps -T -v "${WORK}/y/other.conf:/etc/nginx/conf.d/default.conf:ro" nginx sh -c 'cat /etc/nginx/conf.d/default.conf; nginx -t') || rc5=$?
echo "${out5}"
echo "rc=${rc5}"
if [ "${rc5}" -eq 0 ] && echo "${out5}" | grep -q 'OTHER' && ! echo "${out5}" | grep -q 'SERVICE'; then
  pass "⑤ -v がサービスの取り付けを置き換え（OTHER が見え、SERVICE は見えない）、nginx -t が 0"
else
  fail "⑤ -v で置き換わらない、または nginx -t が 0 でない（rc=${rc5}）。置き換わらないなら /tmp/candidate.conf と nginx -t -c の形に替える"
fi

echo "== ⑥ -v に壊れた設定を渡すと nginx -t が 0 でない"
rc6=0
dc run --rm --no-deps -T -v "${WORK}/bad/nginx.conf:/etc/nginx/conf.d/default.conf:ro" nginx nginx -t || rc6=$?
echo "rc=${rc6}"
if [ "${rc6}" -ne 0 ]; then
  pass "⑥ -v の壊れた設定で nginx -t が 0 でない（rc=${rc6}）"
else
  fail "⑥ -v の壊れた設定でも nginx -t が 0 で終わった"
fi

echo "== ⑦ 取り付け元を mv で入れ替えた後、up -d --no-deps --force-recreate nginx で新しい中身になる"
before7=$(dc exec -T nginx cat /etc/nginx/conf.d/default.conf) || true
echo "入れ替え直後・作り直し前の容器の中（参考。古い inode に束縛されている）: ${before7}"
mv "${WORK}/z/new.conf" "${WORK}/x/nginx.conf"
dc up -d --no-deps --force-recreate nginx
after7=$(dc exec -T nginx cat /etc/nginx/conf.d/default.conf) || true
echo "作り直した後の容器の中: ${after7}"
if [ "${after7}" = "$(cat "${WORK}/x/nginx.conf")" ] && echo "${after7}" | grep -q 'REPLACED'; then
  pass "⑦ 作り直した容器の中身が新しい中身（REPLACED）"
else
  fail "⑦ 作り直した容器の中身が新しい中身でない"
fi

echo "== まとめ"
if [ "${FAILS}" -ne 0 ]; then
  echo "FAIL: ${FAILS} 件"
  exit 1
fi
echo "ALL PASS"
