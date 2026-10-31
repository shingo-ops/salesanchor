#!/usr/bin/env bash
# ADR-1052 段2 カード §5「nginx の作り直しの守り」①〜⑧の試験。
# deploy.yml の「Recreate nginx」（#9 の 1）・「Fail if nginx recreate failed」（1b）・「Emergency block」（1c）の
# script / run の本文を YAML から抜き出し、偽の docker・偽の curl・偽の sleep を PATH の先頭に置いて流す。
# 本物の docker・VPS・ネットワークには触れない（git だけ本物。使い捨ての作業場所の中）。
# 使い方: bash scripts/tests/test-deploy-nginx-recreate-guard.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
YML="${ROOT}/.github/workflows/deploy.yml"
T="$(mktemp -d)"
trap 'rm -rf "${T}"' EXIT
FAILS=0
PASSES=0
pass() { echo "PASS: $*"; PASSES=$((PASSES + 1)); }
fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }
ck() { # ck "説明" 条件のコマンド...
  local d="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "${d}"; else fail "${d}"; fi
}

# ---------------------------------------------------------------- 本文の抜き出し
mkdir -p "${T}/bin" "${T}/tpl"
python3 -I - "${YML}" "${T}/tpl" <<'PYEOF'
import sys, yaml
yml, out = sys.argv[1], sys.argv[2]
d = yaml.safe_load(open(yml))
steps = d["jobs"][[k for k, j in d["jobs"].items() if any(s.get("id") == "nginx_recreate" for s in j["steps"])][0]]["steps"]
names = [s.get("name", "") for s in steps]
def find(prefix):
    m = [i for i, n in enumerate(names) if n.startswith(prefix)]
    assert len(m) == 1, (prefix, m)
    return m[0]
ir = find("Recreate nginx")
i1b = find("Fail if nginx recreate failed")
ie = find("Emergency block")
ifin = find("Finalize")
iv = find("Verify deployment")
ik = find("Start ai-unmask-http")
open(out + "/recreate.sh", "w").write(steps[ir]["with"]["script"])
open(out + "/fail1b.sh", "w").write(steps[i1b]["run"])
open(out + "/emergency.sh", "w").write(steps[ie]["with"]["script"])
meta = []
meta.append("recreate_id=%s" % steps[ir].get("id"))
meta.append("recreate_coe=%s" % steps[ir].get("continue-on-error"))
meta.append("recreate_if=%s" % steps[ir].get("if"))
meta.append("fail1b_if=%s" % steps[i1b].get("if"))
meta.append("emergency_if=%s" % steps[ie].get("if"))
meta.append("order_fin_1b_verify=%s" % (ifin < i1b < iv))
meta.append("order_unmask_after_cloud=%s" % (find("Start ai-reader-cloud-http") + 1 == ik))
open(out + "/meta.txt", "w").write("\n".join(meta) + "\n")
PYEOF
if [ ! -s "${T}/tpl/recreate.sh" ] || [ ! -s "${T}/tpl/emergency.sh" ] || [ ! -s "${T}/tpl/fail1b.sh" ]; then
  echo "FAIL: deploy.yml から本文を抜き出せない"; exit 1
fi
echo "=== 抜き出した設定の確認（deploy.yml）"
cat "${T}/tpl/meta.txt"
ck "Recreate nginx に id: nginx_recreate" grep -qx 'recreate_id=nginx_recreate' "${T}/tpl/meta.txt"
ck "Recreate nginx に continue-on-error: true" grep -qx 'recreate_coe=True' "${T}/tpl/meta.txt"
ck "Recreate nginx の if が今のまま" grep -qxF "recreate_if=\${{ success() && steps.gate.outputs.nginx == 'true' }}" "${T}/tpl/meta.txt"
ck "1b の if が always() と outcome == 'failure'" grep -qxF "fail1b_if=\${{ always() && steps.nginx_recreate.outcome == 'failure' }}" "${T}/tpl/meta.txt"
ck "1c の if が failure() のまま" grep -qx 'emergency_if=failure()' "${T}/tpl/meta.txt"
ck "手順の順が Finalize < 1b < Verify" grep -qx 'order_fin_1b_verify=True' "${T}/tpl/meta.txt"
ck "Start ai-unmask-http が ai-reader-cloud-http の直後" grep -qx 'order_unmask_after_cloud=True' "${T}/tpl/meta.txt"

# ---------------------------------------------------------------- 偽の道具
cat > "${T}/bin/docker" <<'EOF'
#!/usr/bin/env bash
# 偽の docker。呼び出しを ${FAKE_STATE}/docker.log に追記する。
echo "docker $*" >> "${FAKE_STATE}/docker.log"
case "$1 $2" in
  "compose run")
    host=""; prev=""
    for a in "$@"; do
      if [ "${prev}" = "-v" ]; then host="${a%%:*}"; fi
      prev="$a"
    done
    if [ -n "${host}" ]; then target="${host}"; label="戻り先の点検"; else target="${PWD}/nginx/nginx.conf"; label="新しい設定の点検"; fi
    if grep -q BROKEN "${target}" 2>/dev/null; then
      echo "  [偽docker] ${label}: nginx -t 失敗 (${target##*/})"; exit 1
    fi
    echo "  [偽docker] ${label}: nginx -t 成功 (${target##*/})"; exit 0 ;;
  "compose up")
    n=$(cat "${FAKE_STATE}/up_count" 2>/dev/null || echo 0); n=$((n + 1)); echo "${n}" > "${FAKE_STATE}/up_count"
    rcvar="UP${n}_RC"; rc="${!rcvar:-0}"
    if [ "${rc}" -ne 0 ]; then echo "  [偽docker] compose up (${n} 回目) rc=${rc}"; exit "${rc}"; fi
    cp "${PWD}/nginx/nginx.conf" "${FAKE_STATE}/container_conf"
    echo "  [偽docker] compose up (${n} 回目): 容器の中の設定 = $(cat "${FAKE_STATE}/container_conf")"; exit 0 ;;
  "inspect --format={{.State.Running}}")
    echo true; exit 0 ;;
esac
echo "  [偽docker] 想定外の呼び出し: $*"; exit 99
EOF
cat > "${T}/bin/curl" <<'EOF'
#!/usr/bin/env bash
# 偽の curl。--resolve 付き（作り直しの後の確認）は up の回数ごとの台本、それ以外（/design/）は 500。
echo "curl $*" >> "${FAKE_STATE}/docker.log"
case "$*" in
  *--resolve*)
    n=$(cat "${FAKE_STATE}/up_count" 2>/dev/null || echo 0)
    cv="CURL_UP${n}"; code="${!cv:-200}"
    printf '%s' "${code}"
    [ "${code}" = "000" ] && exit 7
    exit 0 ;;
esac
printf '%s' 500; exit 0
EOF
cat > "${T}/bin/sleep" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat > "${T}/bin/mv" <<'EOF'
#!/usr/bin/env bash
# FAIL_GOOD_MV=1 のとき、good の tmp の mv だけ失敗させる（⑧）。ほかは本物の mv。
if [ "${FAIL_GOOD_MV:-0}" = 1 ] && [[ "$*" == *.deploy_nginx_good.conf.tmp* ]]; then echo "  [偽mv] 失敗させた"; exit 1; fi
exec /bin/mv "$@"
EOF
chmod +x "${T}/bin/"*

# ---------------------------------------------------------------- 作業場所
# mk 名前 → SB=作業場所（git の中に nginx/nginx.conf。コミット1 = PREV の設定 "PREV-CONF"、作業の写し = "NEW-CONF"）
mk() {
  SB="${T}/$1"; FS="${T}/$1.state"
  mkdir -p "${SB}/nginx" "${FS}"; : > "${FS}/docker.log"
  (
    cd "${SB}" || exit 1
    git init -q . && git config user.email t@example.invalid && git config user.name t
    echo "PREV-CONF" > nginx/nginx.conf; git add nginx/nginx.conf; git commit -q -m prev
    git rev-parse HEAD > .deploy_prev_sha
    echo "NEW-CONF" > nginx/nginx.conf
  )
}
# 本文を作業場所の道に差し替えて置く
inst() { for f in recreate fail1b emergency; do sed "s#/home/ubuntu/salesanchor#${SB}#g" "${T}/tpl/${f}.sh" > "${SB}/${f}.sh"; done; mkdir -p "${SB}/nginx/htpasswd.d"; echo x > "${SB}/nginx/htpasswd.d/design-site"; }
runs() { # runs スクリプト名 → rc を R に、出力を "${SB}/$1.out" に
  ( cd "${SB}" && env PATH="${T}/bin:${PATH}" FAKE_STATE="${FS}" bash "${SB}/$1.sh" ) > "${SB}/$1.out" 2>&1
  R=$?
  sed 's/^/  | /' "${SB}/$1.out"
  echo "  rc=${R}"
}
ups() { grep -c '^docker compose up' "${FS}/docker.log"; }
cont() { cat "${FS}/container_conf" 2>/dev/null; }

# 「GitHub Actions の流れ」を模す: Recreate（continue-on-error）→ 後ろの手順 → 1b → Verify
flow() {
  runs recreate; RR=$R
  if [ "${RR}" -eq 0 ]; then OUTC=success; else OUTC=failure; fi
  echo "  [流れ] Recreate nginx: outcome=${OUTC} conclusion=success（continue-on-error）"
  echo "  [流れ] 後ろの手順（Bootstrap・移行・smoke・Finalize の代わりの印）が動いた"
  AFTER=ran
  if [ "${OUTC}" = failure ]; then
    runs fail1b; R1B=$R
    if [ "${R1B}" -ne 0 ]; then echo "  [流れ] 1b が exit 1 → デプロイ全体が失敗の表示。Verify deployment（if: success()）は動かない"; fi
  else
    R1B=-; echo "  [流れ] outcome=success → 1b は動かない"
  fi
}

# =========================================================================================
echo
echo "=== ① 新しい設定の点検が通らない（good あり）"
mk s1a; inst; echo "GOOD-CONF" > "${SB}/.deploy_nginx_good.conf"; echo "NEW-CONF BROKEN" > "${SB}/nginx/nginx.conf"
flow
ck "①-a 作り直しをしない（compose up が 0 回）" test "$(ups)" = 0
ck "①-a 作業の写しが戻り先（good の写し）に替わった" test "$(cat "${SB}/nginx/nginx.conf")" = "GOOD-CONF"
ck "①-a nginx の手順が失敗（rc≠0）" test "${RR}" -ne 0
ck "①-a 後ろの手順は動いた" test "${AFTER}" = ran
ck "①-a 1b が exit 1" test "${R1B}" = 1
echo "  --- 1c（if: failure()。1b の失敗の後）"
runs emergency
ck "①-a 1c: good で点検を通して作り直した（容器の中 = GOOD-CONF）" test "$(cont)" = "GOOD-CONF"
ck "①-a 1c: 確認の結果が記録に出る" grep -q '確認 1/15' "${SB}/emergency.out"

echo
echo "=== ① 新しい設定の点検が通らない（good なし → 1c は戻り先の設定で）"
mk s1b; inst; echo "NEW-CONF BROKEN" > "${SB}/nginx/nginx.conf"
flow
ck "①-b 作り直しをしない" test "$(ups)" = 0
ck "①-b 作業の写しが戻り先（PREV の設定）に替わった" test "$(cat "${SB}/nginx/nginx.conf")" = "PREV-CONF"
ck "①-b nginx の手順が失敗・1b が exit 1" test "${RR}" -ne 0 -a "${R1B}" = 1
runs emergency
ck "①-b 1c: 戻り先の設定で点検を通して作り直した（容器の中 = PREV-CONF）" test "$(cont)" = "PREV-CONF"

# =========================================================================================
echo
echo "=== ② .deploy_prev_sha が空で good も無い"
mk s2; inst; : > "${SB}/.deploy_prev_sha"
flow
ck "② 作り直しをしない" test "$(ups)" = 0
ck "② 失敗（rc≠0）・理由の印" grep -q '戻り先の nginx.conf を用意できません' "${SB}/recreate.out"
ck "② 1b が exit 1" test "${R1B}" = 1
ck "② 作業の写しは新しいまま残る" test "$(cat "${SB}/nginx/nginx.conf")" = "NEW-CONF"

echo
echo "=== ②-1 1c: 作業の写しが nginx -t に落ちる回 → 作り直さず警告"
mk s21; inst; echo "NEW-CONF BROKEN" > "${SB}/nginx/nginx.conf"
runs emergency
ck "②-1 作り直さない（compose up が 0 回）" test "$(ups)" = 0
ck "②-1 警告が出る" grep -q 'nginx の設定が点検に通らないため作り直しません' "${SB}/emergency.out"

echo
echo "=== ②-2 1c: nginx -t に通る回 → 作り直して確認の結果が記録に出る"
mk s22; inst
runs emergency
ck "②-2 作り直した（compose up が 1 回）" test "$(ups)" = 1
ck "②-2 確認の結果が記録に出る" grep -q 'nginx の確認が通りました' "${SB}/emergency.out"

# =========================================================================================
echo
echo "=== ③ 戻り先の点検に落ちる（good が壊れている）"
mk s3; inst; echo "GOOD-CONF BROKEN" > "${SB}/.deploy_nginx_good.conf"
flow
ck "③ 作り直さない" test "$(ups)" = 0
ck "③ 失敗・1b が exit 1" test "${RR}" -ne 0 -a "${R1B}" = 1
ck "③ 戻り先の点検（-v 付き）が呼ばれ、新しい設定の点検は呼ばれていない" bash -c "grep -c '^docker compose run' '${FS}/docker.log' | grep -qx 1 && grep -q -- ' -v ' '${FS}/docker.log'"

# =========================================================================================
echo
echo "=== ④-a 作り直した後に起きない（curl が 000・終了コード 7）→ 戻り先に戻して作り直し、失敗の表示"
mk s4a; inst; echo "GOOD-CONF" > "${SB}/.deploy_nginx_good.conf"
HB=$(sha256sum "${SB}/.deploy_nginx_good.conf" | cut -d' ' -f1)
export CURL_UP1=000
flow
unset CURL_UP1
ck "④-a 作り直しが 2 回（新しい設定→戻して）" test "$(ups)" = 2
ck "④-a 戻した後の容器の中 = 戻り先（GOOD-CONF）" test "$(cont)" = "GOOD-CONF"
ck "④-a 作業の写しが戻り先に替わった" test "$(cat "${SB}/nginx/nginx.conf")" = "GOOD-CONF"
ck "④-a 失敗（rc≠0）・1b が exit 1" test "${RR}" -ne 0 -a "${R1B}" = 1
ck "④-a good は書き換わっていない" test "$(sha256sum "${SB}/.deploy_nginx_good.conf" | cut -d' ' -f1)" = "${HB}"

echo
echo "=== ④-b 作り直しの docker compose up が 0 でない → 戻り先に戻して作り直し、失敗の表示"
mk s4b; inst; echo "GOOD-CONF" > "${SB}/.deploy_nginx_good.conf"
export UP1_RC=1
flow
unset UP1_RC
ck "④-b compose up は 2 回呼ばれた（1 回目は失敗）" test "$(ups)" = 2
ck "④-b 戻した後の容器の中 = 戻り先（GOOD-CONF）" test "$(cont)" = "GOOD-CONF"
ck "④-b 失敗・1b が exit 1" test "${RR}" -ne 0 -a "${R1B}" = 1

# =========================================================================================
echo
echo "=== ⑤ 前の回で点検に落ちた後の次の回: 戻り先が good（PREV の壊れた設定ではない）"
mk s5; inst
( cd "${SB}" && echo "PREV-CONF BROKEN" > nginx/nginx.conf && git commit -q -am prev-broken && git rev-parse HEAD > .deploy_prev_sha && echo "NEW-CONF" > nginx/nginx.conf )
echo "GOOD-CONF" > "${SB}/.deploy_nginx_good.conf"
flow
ck "⑤ .deploy_prev_nginx.conf = good（GOOD-CONF）であって PREV の壊れた設定でない" test "$(cat "${SB}/.deploy_prev_nginx.conf")" = "GOOD-CONF"
ck "⑤ 戻り先の点検に通り、作り直しまで進んだ" test "${RR}" -eq 0 -a "$(ups)" = 1
ck "⑤ （対照）good が無ければ PREV の設定（壊れた方）で戻り先の点検に落ちる" bash -c "
  cd '${SB}' && rm -f .deploy_nginx_good.conf && : > '${FS}/docker.log' && rm -f '${FS}/up_count' &&
  env PATH='${T}/bin:${PATH}' FAKE_STATE='${FS}' bash '${SB}/recreate.sh' >/dev/null 2>&1; test \$? -ne 0 && test \"\$(cat .deploy_prev_nginx.conf)\" = 'PREV-CONF BROKEN'"

# =========================================================================================
echo
echo "=== ⑥ 成功の回: .deploy_nginx_good.conf が新しい設定になる"
mk s6; inst; echo "OLD-GOOD" > "${SB}/.deploy_nginx_good.conf"
flow
ck "⑥ 成功（rc=0）・1b は動かない" test "${RR}" -eq 0 -a "${R1B}" = "-"
ck "⑥ good = 新しい設定（NEW-CONF）" test "$(cat "${SB}/.deploy_nginx_good.conf")" = "NEW-CONF"
ck "⑥ tmp が残っていない" test ! -e "${SB}/.deploy_nginx_good.conf.tmp"

# =========================================================================================
echo
echo "=== ⑦-1 good がある状態で 1c が動く回: nginx の手順が飛んだ回（success() が偽で Recreate が動かない）"
mk s71; inst; echo "GOOD-CONF" > "${SB}/.deploy_nginx_good.conf"; echo "NEW-CONF" > "${SB}/nginx/nginx.conf"
echo "  [流れ] Recreate nginx は success() が偽で飛んだ（本文は流さない）。作業の写し = $(cat "${SB}/nginx/nginx.conf")"
runs emergency
ck "⑦-1 1c が作業の写しを good に替えてから作り直した（容器の中 = GOOD-CONF）" test "$(cont)" = "GOOD-CONF"
ck "⑦-1 作業の写しの設定（NEW-CONF）で作り直していない" test "$(cont)" != "NEW-CONF"
ck "⑦-1 容器の中の設定と good の diff が空" diff "${FS}/container_conf" "${SB}/.deploy_nginx_good.conf"

echo
echo "=== ⑦-2 good がある状態で 1c が動く回: Finalize の自動ロールバックで作業の写しが PREV の設定になった回"
mk s72; inst; echo "GOOD-CONF" > "${SB}/.deploy_nginx_good.conf"
( cd "${SB}" && git show "$(cat .deploy_prev_sha):nginx/nginx.conf" > nginx/nginx.conf )
echo "  [流れ] Finalize が PREV へ reset した。作業の写し = $(cat "${SB}/nginx/nginx.conf")"
runs emergency
ck "⑦-2 1c が作業の写しを good に替えてから作り直した（容器の中 = GOOD-CONF）" test "$(cont)" = "GOOD-CONF"
ck "⑦-2 PREV の設定（PREV-CONF）で作り直していない" test "$(cont)" != "PREV-CONF"
ck "⑦-2 容器の中の設定と good の diff が空" diff "${FS}/container_conf" "${SB}/.deploy_nginx_good.conf"

# =========================================================================================
echo
echo "=== ⑧ good の書き出しを失敗させた回 → 警告が出て、good も tmp も無い"
mk s8; inst; echo "OLD-GOOD" > "${SB}/.deploy_nginx_good.conf"
export FAIL_GOOD_MV=1
flow
unset FAIL_GOOD_MV
ck "⑧ 警告が出る" grep -q '最後に起きた nginx の設定を残せませんでした' "${SB}/recreate.out"
ck "⑧ good が無い（古い good も消えた）" test ! -e "${SB}/.deploy_nginx_good.conf"
ck "⑧ tmp が無い" test ! -e "${SB}/.deploy_nginx_good.conf.tmp"
ck "⑧ 手順は成功で終わる（rc=0）" test "${RR}" -eq 0

# =========================================================================================
echo
echo "=== まとめ: PASS=${PASSES} FAIL=${FAILS}"
if [ "${FAILS}" -ne 0 ]; then echo "FAIL"; exit 1; fi
echo "ALL PASS"
