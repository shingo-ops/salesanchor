#!/usr/bin/env bash
# build-on-github 便2（docs/handoff/build-on-github/card-bin2.md §2-6 の 7.）の試験。
# scripts/deploy/pull-images.sh・prune-images.sh・rollback-images.sh と、deploy.yml から抜き出した塊
# （Step 2 の指紋の書き込み・Step 3b の切替失敗の戻し・Finalize の戻し）を、偽の docker・偽の git を PATH の先頭に置いて流す。
# 本物の docker・VPS・ネットワークには触れない。呼ばれ方は一時ディレクトリの calls.log に 1 行ずつ記録する。
# 「build を含む呼び出し」は、引数の中に build という単語（--no-build は含めない）がある呼び出しのこと。
# 使い方: bash scripts/tests/test-deploy-pull-prune.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
YML="${ROOT}/.github/workflows/deploy.yml"
T="$(mktemp -d)"
trap 'rm -rf "${T}"' EXIT
FAILS=0
PASSES=0
pass() { echo "PASS: $*"; PASSES=$((PASSES + 1)); }
fail() { echo "FAIL: $*"; FAILS=$((FAILS + 1)); }
eq() { # eq "説明" 期待 実際
  if [ "$2" = "$3" ]; then pass "$1 (一致: $(printf '%s' "$3" | head -c 60 | tr '\n' ' '))"; else fail "$1 (期待 $2 / 実際 $3)"; fi
}
ck() { # ck "説明" コマンド...
  local d="$1"; shift
  if "$@" >/dev/null 2>&1; then pass "${d}"; else fail "${d}"; fi
}
cnt() { # cnt 正規表現 ファイル（0 件でも 0 を返す）
  local n
  n="$(grep -cE "$1" "$2" 2>/dev/null || true)"
  echo "${n:-0}"
}
ref() { printf 'ghcr.io/org/salesanchor-%s@sha256:%064d\n' "$1" "$2"; }

# ---------------------------------------------------------------- 偽の docker・偽の git
mkdir -p "${T}/bin"
cat > "${T}/bin/docker" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_DIR}/calls.log"
case "$1" in
  compose)
    case "$2" in
      version) echo "Docker Compose version v2.99.0"; exit 0 ;;
      config)
        if [ -f "${FAKE_DIR}/compose.json" ]; then cat "${FAKE_DIR}/compose.json"; else echo '{"services":{"backend":{"image":"x"}}}'; fi
        exit 0 ;;
    esac
    exit 0 ;;
  login) cat >/dev/null; exit 0 ;;
  logout) exit 0 ;;
  pull)
    _r="${*: -1}"
    if [ -f "${FAKE_DIR}/pull_fail" ] && printf '%s' "${_r}" | grep -qFf "${FAKE_DIR}/pull_fail"; then exit 1; fi
    exit 0 ;;
  image)
    case "$2" in
      inspect) [ -f "${FAKE_DIR}/inspect_fail" ] && exit 1; exit 0 ;;
      rm) exit 0 ;;
    esac
    exit 0 ;;
  images) [ -f "${FAKE_DIR}/images.txt" ] && cat "${FAKE_DIR}/images.txt"; exit 0 ;;
  exec)
    _n="$(cat "${FAKE_DIR}/exec_n" 2>/dev/null || echo 0)"
    _n=$((_n + 1)); echo "${_n}" > "${FAKE_DIR}/exec_n"
    _f="$(cat "${FAKE_DIR}/exec_fail_n" 2>/dev/null || echo 0)"
    [ "${_n}" -le "${_f}" ] && exit 1
    exit 0 ;;
  ps) exit 0 ;;
esac
exit 0
EOF
cat > "${T}/bin/git" <<'EOF'
#!/usr/bin/env bash
printf 'git %s\n' "$*" >> "${FAKE_DIR}/calls.log"
if [ "$1" = "show" ]; then cat "${FAKE_DIR}/git_compose" 2>/dev/null; exit 0; fi
exit 0
EOF
chmod 755 "${T}/bin/docker" "${T}/bin/git"

# 1 つの場合の作業場所。mk 名前 → ${T}/名前/{repo,fake}。repo は REPO_DIR の先
mk() {
  mkdir -p "${T}/$1/repo" "${T}/$1/fake"
  : > "${T}/$1/fake/calls.log"
}
# run 名前 コマンド... : 偽の PATH・FAKE_DIR・REPO_DIR で流し、出力を out.txt・終了コードを rc.txt に残す
run() {
  local n="$1"; shift
  ( export PATH="${T}/bin:${PATH}" FAKE_DIR="${T}/${n}/fake" REPO_DIR="${T}/${n}/repo" PULL_RETRY_SLEEP=0 ROLLBACK_HC_SLEEP=0 \
      SECRETARY_ENV_FILE="${T}/${n}/sec.env" CUTOVER_SCRIPT="${T}/${n}/cutover.sh" GHCR_USER=u GHCR_PULL_TOKEN=tok
    "$@" ) > "${T}/${n}/out.txt" 2>&1
  echo $? > "${T}/${n}/rc.txt"
}
rc() { cat "${T}/$1/rc.txt"; }
calls() { echo "${T}/$1/fake/calls.log"; }
env5() { # 5 つの必須の行を .env 形式で書く: env5 番号
  printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\nGEMINI_EGRESS_IMAGE=%s\nGHA_EXPORTER_IMAGE=%s\nSECRETARY_AGENT_IMAGE=%s\n' \
    "$(ref backend "$1")" \
    "$(ref frontend "$1")" "$(ref gemini-egress "$1")" "$(ref gha-exporter "$1")" "$(ref secretary-agent "$1")"
}
REQ_RE='^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE='
PULL="${ROOT}/scripts/deploy/pull-images.sh"
PRUNE="${ROOT}/scripts/deploy/prune-images.sh"
ROLLBACK="${ROOT}/scripts/deploy/rollback-images.sh"

# ---------------------------------------------------------------- deploy.yml から塊を抜き出す
mkdir -p "${T}/tpl"
python3 -I - "${YML}" "${T}/tpl" <<'PYEOF'
import sys, yaml
yml, out = sys.argv[1], sys.argv[2]
d = yaml.safe_load(open(yml))
steps = d["jobs"]["deploy"]["steps"]
def script(prefix):
    m = [s for s in steps if s.get("name", "").startswith(prefix)]
    assert len(m) == 1, (prefix, len(m))
    return m[0]["with"]["script"]
def cut(text, start, end):
    a = text.index(start)
    a = text.rindex("\n", 0, a) + 1
    b = text.index(end, a)
    b = text.rindex("\n", 0, b) + 1
    return text[a:b]
dep = script("Deploy to VPS")
fin = script("Finalize")
open(out + "/step2.sh", "w").write(cut(dep, "# build-on-github 便2（design.md §26）: GitHub で組み立てた完成品の指紋を", 'echo "Step 2b'))
open(out + "/step3b.sh", "w").write(cut(dep, "if ! bash scripts/blue-green-cutover.sh; then", "# backend 以外（frontend/celery-beat/discord）"))
open(out + "/finalize_rb.sh", "w").write(cut(fin, "# build-on-github 便2（design.md §9-2・§26-1 6.）", 'if [ "${_rb_build}" = "true" ]; then'))
PYEOF
for f in step2 step3b finalize_rb; do
  if [ ! -s "${T}/tpl/${f}.sh" ]; then echo "FAIL: deploy.yml から ${f} の塊を抜き出せない"; exit 1; fi
done

# ================================================================ T1 正しい 5 行・全部成功
echo "=== T1 pull: 正しい 5 行"
mk t1; env5 1 > "${T}/t1/repo/.env"
run t1 bash "${PULL}"
eq "T1 終了コード" 0 "$(rc t1)"
eq "T1 docker pull の回数" 5 "$(cnt '^pull ' "$(calls t1)")"
eq "T1 docker logout ghcr.io の回数" 1 "$(cnt '^logout ghcr\.io$' "$(calls t1)")"
eq "T1 build を含む呼び出し" 0 "$(cnt '(^| )build( |$)' "$(calls t1)")"
ck "T1 出力に pull ok (5 images)" grep -q 'pull ok (5 images)' "${T}/t1/out.txt"
echo "=== T1b pull: SECRETARY_CODEX_IMAGE の行も在る"
mk t1b; { env5 1; printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 7)"; } > "${T}/t1b/repo/.env"
run t1b bash "${PULL}"
eq "T1b 終了コード" 0 "$(rc t1b)"
eq "T1b docker pull の回数" 6 "$(cnt '^pull ' "$(calls t1b)")"
ck "T1b 出力に pulled salesanchor-secretary-codex@" grep -q 'pulled salesanchor-secretary-codex@' "${T}/t1b/out.txt"

# ================================================================ T2 build: を持つサービスが 1 つ
echo "=== T2 pull: compose に build: が在る"
mk t2; env5 1 > "${T}/t2/repo/.env"
echo '{"services":{"backend":{"image":"x"},"frontend":{"build":{"context":"./frontend"}}}}' > "${T}/t2/fake/compose.json"
run t2 bash "${PULL}"
eq "T2 終了コード" 1 "$(rc t2)"
eq "T2 docker login の回数" 0 "$(cnt '^login ' "$(calls t2)")"

# ================================================================ T3 形が違う
echo "=== T3 pull: .env の 1 行が @sha256: でない"
mk t3; env5 1 | sed 's#^FRONTEND_IMAGE=.*#FRONTEND_IMAGE=ghcr.io/org/salesanchor-frontend:latest#' > "${T}/t3/repo/.env"
run t3 bash "${PULL}"
eq "T3 終了コード" 1 "$(rc t3)"
eq "T3 docker login の回数" 0 "$(cnt '^login ' "$(calls t3)")"

# ================================================================ T4 pull が 3 回とも失敗
echo "=== T4 pull: 1 つが 3 回とも失敗"
mk t4; env5 1 > "${T}/t4/repo/.env"
echo 'salesanchor-gemini-egress@' > "${T}/t4/fake/pull_fail"
run t4 bash "${PULL}"
eq "T4 終了コード" 1 "$(rc t4)"
eq "T4 docker logout ghcr.io の回数（trap）" 1 "$(cnt '^logout ghcr\.io$' "$(calls t4)")"

# ================================================================ T4b secretary-codex だけ失敗
echo "=== T4b pull: secretary-codex だけ 3 回とも失敗（控えに別の行）"
mk t4b; { env5 1; printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 7)"; } > "${T}/t4b/repo/.env"
printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 3)" > "${T}/t4b/repo/.deploy_prev_images.env"
echo 'salesanchor-secretary-codex@' > "${T}/t4b/fake/pull_fail"
run t4b bash "${PULL}"
eq "T4b 終了コード" 0 "$(rc t4b)"
ck "T4b 出力に ::warning::" grep -q '::warning::' "${T}/t4b/out.txt"
eq "T4b .env の SECRETARY_CODEX_IMAGE の行が控えと同じ" "SECRETARY_CODEX_IMAGE=$(ref secretary-codex 3)" "$(grep '^SECRETARY_CODEX_IMAGE=' "${T}/t4b/repo/.env")"
eq "T4b .env の SECRETARY_CODEX_IMAGE の行は 1 つだけ" 1 "$(cnt '^SECRETARY_CODEX_IMAGE=' "${T}/t4b/repo/.env")"
eq "T4b docker logout ghcr.io の回数" 1 "$(cnt '^logout ghcr\.io$' "$(calls t4b)")"
echo "=== T4b' 控えに SECRETARY_CODEX の行が無い"
mk t4c; { env5 1; printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 7)"; } > "${T}/t4c/repo/.env"
: > "${T}/t4c/repo/.deploy_prev_images.env"
echo 'salesanchor-secretary-codex@' > "${T}/t4c/fake/pull_fail"
run t4c bash "${PULL}"
eq "T4b' 終了コード" 0 "$(rc t4c)"
eq "T4b' .env に SECRETARY_CODEX_IMAGE の行が無い" 0 "$(cnt '^SECRETARY_CODEX_IMAGE=' "${T}/t4c/repo/.env")"
echo "=== T4b'' SECRETARY_CODEX_IMAGE の形が違う（@sha256: 無し）"
mk t4d; { env5 1; echo 'SECRETARY_CODEX_IMAGE=ghcr.io/org/salesanchor-secretary-codex:latest'; } > "${T}/t4d/repo/.env"
printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 3)" > "${T}/t4d/repo/.deploy_prev_images.env"
run t4d bash "${PULL}"
eq "T4b'' 終了コード" 0 "$(rc t4d)"
eq "T4b'' docker pull の回数（必須の 5 つだけ）" 5 "$(cnt '^pull ' "$(calls t4d)")"
eq "T4b'' .env の SECRETARY_CODEX_IMAGE の行が控えと同じ" "SECRETARY_CODEX_IMAGE=$(ref secretary-codex 3)" "$(grep '^SECRETARY_CODEX_IMAGE=' "${T}/t4d/repo/.env")"

# ================================================================ T5 prune
echo "=== T5 prune: 今・1 つ前・古い 2 つ"
mk t5
env5 2 > "${T}/t5/repo/.env"; env5 1 > "${T}/t5/repo/.deploy_prev_images.env"
{ ref backend 2; ref backend 1
  ref backend 8; ref backend 9
  echo 'astro-webapp-backend@<none>'; } > "${T}/t5/fake/images.txt"
run t5 bash "${PRUNE}"
eq "T5 終了コード" 0 "$(rc t5)"
eq "T5 docker image rm の回数" 2 "$(cnt '^image rm ' "$(calls t5)")"
ck "T5 古い 2 つだけを消した" bash -c "grep '^image rm ' '$(calls t5)' | grep -q '0008$' && grep '^image rm ' '$(calls t5)' | grep -q '0009$'"
eq "T5 今・1 つ前・<none> は消さない" 0 "$(grep '^image rm ' "$(calls t5)" | grep -cE '0001$|0002$|<none>' || true)"

# ================================================================ T6 prune: 指紋が読めない
echo "=== T6 prune: .env にも控えにも指紋が無い"
mk t6; echo 'FOO=bar' > "${T}/t6/repo/.env"
echo "$(ref backend 8)" > "${T}/t6/fake/images.txt"
run t6 bash "${PRUNE}"
eq "T6 終了コード" 0 "$(rc t6)"
eq "T6 docker image rm の回数" 0 "$(cnt '^image rm ' "$(calls t6)")"

# ================================================================ T7 Finalize の戻しの塊
echo "=== T7 Finalize の戻し: 控えが 1 行"
mk t7
{ echo 'FOO=bar'; env5 2; } > "${T}/t7/repo/.env"
printf 'BACKEND_IMAGE=%s\n' "$(ref backend 1)" > "${T}/t7/repo/.deploy_prev_images.env"
{ echo 'set -e'; cat "${T}/tpl/finalize_rb.sh"; echo 'echo "rb=${_rb_build}"'; } > "${T}/t7/block.sh"
run t7 bash -c "cd '${T}/t7/repo' && bash '${T}/t7/block.sh'"
eq "T7 終了コード" 0 "$(rc t7)"
eq "T7 BACKEND_IMAGE の行だけ控えと同じ" "BACKEND_IMAGE=$(ref backend 1)" "$(grep '^BACKEND_IMAGE=' "${T}/t7/repo/.env")"
eq "T7 FRONTEND_IMAGE の行は変わらない" "FRONTEND_IMAGE=$(ref frontend 2)" "$(grep '^FRONTEND_IMAGE=' "${T}/t7/repo/.env")"
eq "T7 *_IMAGE の行は 5 つのまま" 5 "$(cnt '_IMAGE=' "${T}/t7/repo/.env")"
ck "T7 _rb_build=true" grep -q '^rb=true$' "${T}/t7/out.txt"
echo "=== T7b Finalize の戻し: 控えが空・戻り先の compose に BACKEND_IMAGE が無い"
mk t7b
{ echo 'FOO=bar'; env5 2; printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 2)"; } > "${T}/t7b/repo/.env"
: > "${T}/t7b/repo/.deploy_prev_images.env"
echo 'services: {}' > "${T}/t7b/fake/git_compose"
{ echo 'set -e'; cat "${T}/tpl/finalize_rb.sh"; echo 'echo "rb=${_rb_build}"'; } > "${T}/t7b/block.sh"
run t7b bash -c "cd '${T}/t7b/repo' && bash '${T}/t7b/block.sh'"
eq "T7b 終了コード" 0 "$(rc t7b)"
eq "T7b *_IMAGE の行が全部消えた" 0 "$(cnt '_IMAGE=' "${T}/t7b/repo/.env")"
eq "T7b FOO=bar は残る" 1 "$(cnt '^FOO=bar$' "${T}/t7b/repo/.env")"
ck "T7b _rb_build=true" grep -q '^rb=true$' "${T}/t7b/out.txt"

# ================================================================ T8 rollback-images.sh
echo "=== T8 rollback: 控えが 5 行・全部成功"
mk t8
{ echo 'FOO=bar'; env5 2; printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 2)"; } > "${T}/t8/repo/.env"
env5 1 > "${T}/t8/repo/.deploy_prev_images.env"
env5 2 > "${T}/t8/orig5.env"
printf '#!/usr/bin/env bash\necho called >> "%s/t8/cutover.log"\n' "${T}" > "${T}/t8/cutover.sh"
echo 'SECRETARY_AGENT_TOKEN=x' > "${T}/t8/sec.env"
run t8 bash "${ROLLBACK}"
eq "T8 終了コード" 0 "$(rc t8)"
eq "T8 .env の必須 5 行が控えと同じ" "$(grep -E "${REQ_RE}" "${T}/t8/repo/.deploy_prev_images.env" | sort)" "$(grep -E "${REQ_RE}" "${T}/t8/repo/.env" | sort)"
eq "T8 .deploy_rollback_from.env が元の 5 行" "$(sort "${T}/t8/orig5.env")" "$(sort "${T}/t8/repo/.deploy_rollback_from.env")"
eq "T8 .env の SECRETARY_CODEX_IMAGE は変わらない" "SECRETARY_CODEX_IMAGE=$(ref secretary-codex 2)" "$(grep '^SECRETARY_CODEX_IMAGE=' "${T}/t8/repo/.env")"
eq "T8 偽の切替が呼ばれた回数" 1 "$(cnt '^called$' "${T}/t8/cutover.log")"
eq "T8 stop -t 60 celery-worker の回数" 1 "$(cnt '^compose stop -t 60 celery-worker$' "$(calls t8)")"
eq "T8 up -d と --no-build を両方含む呼び出し（本体・秘書）" 2 "$(grep -E 'up -d' "$(calls t8)" | grep -c -- '--no-build' || true)"
eq "T8 build を含む呼び出し" 0 "$(cnt '(^| )build( |$)' "$(calls t8)")"
ck "T8 出力に rollback done in" grep -q 'rollback done in' "${T}/t8/out.txt"
echo "=== T8b rollback: 控えが 4 行"
mk t8b
env5 2 > "${T}/t8b/repo/.env"
env5 1 | head -4 > "${T}/t8b/repo/.deploy_prev_images.env"
cp "${T}/t8b/repo/.env" "${T}/t8b/env.before"
printf '#!/usr/bin/env bash\necho called >> "%s/t8b/cutover.log"\n' "${T}" > "${T}/t8b/cutover.sh"
run t8b bash "${ROLLBACK}"
eq "T8b 終了コード" 1 "$(rc t8b)"
ck "T8b .env は変わらない" cmp -s "${T}/t8b/env.before" "${T}/t8b/repo/.env"
echo "=== T8c rollback: 健康確認が 1 回目だけ失敗"
mk t8c
env5 2 > "${T}/t8c/repo/.env"; env5 1 > "${T}/t8c/repo/.deploy_prev_images.env"
printf '#!/usr/bin/env bash\necho called >> "%s/t8c/cutover.log"\n' "${T}" > "${T}/t8c/cutover.sh"
echo 1 > "${T}/t8c/fake/exec_fail_n"
echo 'x=1' > "${T}/t8c/sec.env"
run t8c bash "${ROLLBACK}"
eq "T8c 終了コード" 0 "$(rc t8c)"
eq "T8c docker exec の回数" 2 "$(cnt '^exec ' "$(calls t8c)")"

# ================================================================ T9 Step 2・Step 3b の塊
echo "=== T9 Step 2: BACKEND_REF に @sha256: が無い"
mk t9
{ echo 'FOO=bar'; env5 2; } > "${T}/t9/repo/.env"
env5 2 > "${T}/t9/repo/.deploy_prev_images.env"
{ echo 'set -e'; cat "${T}/tpl/step2.sh"; } > "${T}/t9/block.sh"
run t9 env BACKEND_REF="ghcr.io/org/salesanchor-backend:latest" FRONTEND_REF="$(ref frontend 5)" GEMINI_EGRESS_REF="$(ref gemini-egress 5)" \
  GHA_EXPORTER_REF="$(ref gha-exporter 5)" SECRETARY_AGENT_REF="$(ref secretary-agent 5)" SECRETARY_CODEX_REF="" \
  bash -c "cd '${T}/t9/repo' && bash '${T}/t9/block.sh'"
eq "T9 終了コード" 1 "$(rc t9)"
eq "T9 .env の必須 5 行が控えの 5 行と同じ" "$(sort "${T}/t9/repo/.deploy_prev_images.env")" "$(grep -E "${REQ_RE}" "${T}/t9/repo/.env" | sort)"
echo "=== T9b Step 3b: 切替が終了 1"
mk t9b
{ echo 'FOO=bar'; env5 5; } > "${T}/t9b/repo/.env"
env5 2 > "${T}/t9b/repo/.deploy_prev_images.env"
mkdir -p "${T}/t9b/repo/scripts"
printf '#!/usr/bin/env bash\nexit 1\n' > "${T}/t9b/repo/scripts/blue-green-cutover.sh"
{ echo 'set -e'; cat "${T}/tpl/step3b.sh"; } > "${T}/t9b/block.sh"
run t9b bash -c "cd '${T}/t9b/repo' && bash '${T}/t9b/block.sh'"
eq "T9b 終了コード" 1 "$(rc t9b)"
eq "T9b .env の必須 5 行が控えと同じ" "$(sort "${T}/t9b/repo/.deploy_prev_images.env")" "$(grep -E "${REQ_RE}" "${T}/t9b/repo/.env" | sort)"

# ================================================================ T10 secretary-codex の指紋の書き込み
echo "=== T10 Step 2: SECRETARY_CODEX_REF が空・.env に行が無い"
mk t10
{ echo 'FOO=bar'; env5 2; } > "${T}/t10/repo/.env"
env5 2 > "${T}/t10/repo/.deploy_prev_images.env"
{ echo 'set -e'; cat "${T}/tpl/step2.sh"; } > "${T}/t10/block.sh"
run t10 env BACKEND_REF="$(ref backend 5)" FRONTEND_REF="$(ref frontend 5)" GEMINI_EGRESS_REF="$(ref gemini-egress 5)" \
  GHA_EXPORTER_REF="$(ref gha-exporter 5)" SECRETARY_AGENT_REF="$(ref secretary-agent 5)" SECRETARY_CODEX_REF="" \
  bash -c "cd '${T}/t10/repo' && bash '${T}/t10/block.sh'"
eq "T10 終了コード" 0 "$(rc t10)"
eq "T10 .env に SECRETARY_CODEX_IMAGE の行が無い" 0 "$(cnt '^SECRETARY_CODEX_IMAGE=' "${T}/t10/repo/.env")"
eq "T10 .env の BACKEND_IMAGE が新しい指紋" "BACKEND_IMAGE=$(ref backend 5)" "$(grep '^BACKEND_IMAGE=' "${T}/t10/repo/.env")"
echo "=== T10b Step 2: SECRETARY_CODEX_REF が正しい値"
mk t10b
{ echo 'FOO=bar'; env5 2; } > "${T}/t10b/repo/.env"
env5 2 > "${T}/t10b/repo/.deploy_prev_images.env"
{ echo 'set -e'; cat "${T}/tpl/step2.sh"; } > "${T}/t10b/block.sh"
run t10b env BACKEND_REF="" FRONTEND_REF="" GEMINI_EGRESS_REF="" GHA_EXPORTER_REF="" SECRETARY_AGENT_REF="" SECRETARY_CODEX_REF="$(ref secretary-codex 9)" \
  bash -c "cd '${T}/t10b/repo' && bash '${T}/t10b/block.sh'"
eq "T10b 終了コード" 0 "$(rc t10b)"
eq "T10b .env に SECRETARY_CODEX_IMAGE の 1 行" "SECRETARY_CODEX_IMAGE=$(ref secretary-codex 9)" "$(grep '^SECRETARY_CODEX_IMAGE=' "${T}/t10b/repo/.env")"
eq "T10b 必須 5 行は変わらない" "$(env5 2 | sort)" "$(grep -E "${REQ_RE}" "${T}/t10b/repo/.env" | sort)"

# ================================================================ T11 prune: secretary-codex
echo "=== T11 prune: SECRETARY_CODEX の今と古いの 2 つ"
mk t11
{ env5 2; printf 'SECRETARY_CODEX_IMAGE=%s\n' "$(ref secretary-codex 2)"; } > "${T}/t11/repo/.env"
{ ref secretary-codex 2; ref secretary-codex 1; } > "${T}/t11/fake/images.txt"
run t11 bash "${PRUNE}"
eq "T11 終了コード" 0 "$(rc t11)"
eq "T11 docker image rm の回数" 1 "$(cnt '^image rm ' "$(calls t11)")"
ck "T11 古い 1 つだけを消した" bash -c "grep '^image rm ' '$(calls t11)' | grep -q '0001$'"

echo
echo "結果: PASS=${PASSES} FAIL=${FAILS}"
[ "${FAILS}" -eq 0 ]
