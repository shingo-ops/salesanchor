#!/bin/bash
# test-disk-janitor.sh — scripts/disk-janitor.sh の試験（R1〜R4 の「消す」「保護」・dry-run・ガード）
#
# すべて mktemp -d で作った一時ディレクトリの中だけで動く。実機の根・npm キャッシュ・
# agent-console の版には触れない（根・保護先・versions・reaper は DJ_ 環境変数で一時ディレクトリへ差し替える）。
# 「使用中」は、試験内で sleep プロセスの cwd をその場所にして、lsof で検出されることを使う。
#
# 実行方法: bash scripts/tests/test-disk-janitor.sh
# 終了コード: 0=ng が 0 件 / 1=ng あり

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JANITOR="${SCRIPT_DIR}/../disk-janitor.sh"
OK=0
NG=0

ok() { echo "ok: $1"; OK=$(( OK + 1 )); }
ng() { echo "ng: $1"; NG=$(( NG + 1 )); }
check() { # check <説明> <コマンド...>（成功なら ok）
  local desc="$1"; shift
  if "$@"; then ok "${desc}"; else ng "${desc}"; fi
}
exists() { [ -e "$1" ] || [ -L "$1" ]; }
both_exist() { exists "$1" && exists "$2"; }
gone() { ! exists "$1"; }

T_RAW="$(mktemp -d "${TMPDIR:-/tmp}/disk-janitor-test.XXXXXX")" || { echo "mktemp 失敗"; exit 1; }
T="$(cd -P "${T_RAW}" && pwd -P)"
SLEEPERS=()
cleanup() {
  local p
  for p in ${SLEEPERS[@]+"${SLEEPERS[@]}"}; do kill "${p}" 2>/dev/null || true; wait "${p}" 2>/dev/null || true; done
  case "${T}" in
    */disk-janitor-test.*) rm -rf -- "${T}" ;;   # 一時ディレクトリの中だけを片付ける
  esac
}
trap cleanup EXIT

R_WT="${T}/worktrees"; R_ACWT="${T}/acwt"; R_SA="${T}/sa"; R_AC="${T}/ac"; R_VER="${T}/versions"
KEEP_CACHE="${R_SA}/keepcache/.npm-cache"
mkdir -p "${R_WT}/repoA" "${R_ACWT}" "${R_SA}" "${R_AC}" "${R_VER}" "${T}/outside"

# 一時ディレクトリの中だけを指す設定
export DJ_ROOT_WORKTREES="${R_WT}" DJ_ROOT_AC_WT="${R_ACWT}" DJ_ROOT_SALESANCHOR="${R_SA}" \
       DJ_ROOT_AGENT_CONSOLE="${R_AC}" DJ_ROOT_VERSIONS="${R_VER}" DJ_CURRENT_LINK="${T}/current" \
       DJ_NPM_CACHE_KEEP="${KEEP_CACHE}" DJ_NPM_CMD="echo ${KEEP_CACHE}" \
       DJ_LOCK_DIR="${T}/lock.d" DJ_LOG_FILE="" DJ_STALE_DAYS=14
# R5・R6 の根・last-ok・古さも一時ディレクトリへ（K9。実機の /private/tmp や ~/Library/Logs に触れない）
export DJ_ROOT_TMP_CC="${T}/tmpcc" DJ_ROOT_CLAUDE_TMP="${T}/claudetmp" DJ_CA_LAST_OK="${T}/ca.last-ok" \
       DJ_CA_FRESH_SEC=172800 DJ_TMP_STALE_DAYS=7
# K9: --execute より前に、全ての根・last-ok が $T の下であることを確かめる
for v in DJ_ROOT_WORKTREES DJ_ROOT_AC_WT DJ_ROOT_SALESANCHOR DJ_ROOT_AGENT_CONSOLE DJ_ROOT_VERSIONS DJ_CURRENT_LINK \
         DJ_NPM_CACHE_KEEP DJ_LOCK_DIR DJ_ROOT_TMP_CC DJ_ROOT_CLAUDE_TMP DJ_CA_LAST_OK; do
  case "${!v}" in "${T}"/*) ;; *) echo "ng: K9 ${v} が一時ディレクトリの外: ${!v}"; exit 1 ;; esac
done
ok "K9 全ての根・last-ok が一時ディレクトリの下（--execute より前に確認）"

start_sleeper() { # start_sleeper <dir>: dir を cwd にしたプロセスを起動
  ( cd "$1" && exec sleep 600 ) &
  SLEEPERS+=("$!")
}
age() { find "$1" -exec touch -t 202601010000 {} + ; } # 古い更新日時にする

# ── git 本体（R2 の作業用コピーを作る元）──────────────────────────────────────
GM="${T}/gitmain"
mkdir -p "${GM}"
git init -q -b main "${GM}"
echo base > "${GM}/README.md"
git -C "${GM}" add README.md
GIT_AUTHOR_DATE="2026-01-01T00:00:00" GIT_COMMITTER_DATE="2026-01-01T00:00:00" \
  git -C "${GM}" -c user.name=t -c user.email=t@t commit -q -m base

mkwt() { git -C "${GM}" worktree add -q -b "$2" "$1" HEAD 2>/dev/null; }
mk_nm() { # mk_nm <dir>: node_modules と package-lock.json（直下と frontend/）
  mkdir -p "$1/node_modules/pkg" "$1/frontend/node_modules/pkg"
  echo x > "$1/node_modules/pkg/index.js"; echo x > "$1/frontend/node_modules/pkg/index.js"
  echo '{}' > "$1/package-lock.json"; echo '{}' > "$1/frontend/package-lock.json"
}

# ── R1 の準備 ───────────────────────────────────────────────────────────────
mkdir -p "${R_WT}/repoA/wt1/.npm-cache/_cacache" "${R_SA}/.npm-cache" "${R_SA}/frontend/.npm-cache" \
         "${R_ACWT}/x/.npm-cache" "${KEEP_CACHE}" "${R_AC}/.npm-cache" "${T}/outside/.npm-cache"
echo d > "${R_WT}/repoA/wt1/.npm-cache/_cacache/f"
mkdir -p "${R_WT}/repoA/linkholder"
ln -s "${T}/outside/.npm-cache" "${R_WT}/repoA/linkholder/.npm-cache"     # シンボリックリンク
start_sleeper "${R_AC}/.npm-cache"                                        # 使用中

# ── R2 の準備 ───────────────────────────────────────────────────────────────
WT_DEL="${R_WT}/repoA/wt-del";           mkwt "${WT_DEL}" br-del;           mk_nm "${WT_DEL}"
WT_ACDEL="${R_ACWT}/wt-acdel";           mkwt "${WT_ACDEL}" br-acdel;       mk_nm "${WT_ACDEL}"
WT_NOLOCK="${R_WT}/repoA/wt-nolock";     mkwt "${WT_NOLOCK}" br-nolock;     mkdir -p "${WT_NOLOCK}/node_modules/p"
WT_RECENTFILE="${R_WT}/repoA/wt-recentfile"; mkwt "${WT_RECENTFILE}" br-recentfile; mk_nm "${WT_RECENTFILE}"
WT_RECENTCOMMIT="${R_WT}/repoA/wt-recentcommit"; mkwt "${WT_RECENTCOMMIT}" br-recentcommit; mk_nm "${WT_RECENTCOMMIT}"
WT_INUSE="${R_WT}/repoA/wt-inuse";       mkwt "${WT_INUSE}" br-inuse;       mk_nm "${WT_INUSE}"
WT_SYM="${R_WT}/repoA/wt-sym";           mkwt "${WT_SYM}" br-sym;           echo '{}' > "${WT_SYM}/package-lock.json"
WT_NOGIT="${R_WT}/repoA/wt-nogit";       mkdir -p "${WT_NOGIT}"; echo "gitdir: /nonexistent-gitdir" > "${WT_NOGIT}/.git"
mk_nm "${WT_NOGIT}"
mkdir -p "${R_SA}/node_modules/p" "${R_SA}/.git" "${R_AC}/node_modules/p"; echo '{}' > "${R_SA}/package-lock.json"

git -C "${WT_RECENTCOMMIT}" -c user.name=t -c user.email=t@t commit -q --allow-empty -m recent
for d in "${WT_DEL}" "${WT_ACDEL}" "${WT_NOLOCK}" "${WT_RECENTFILE}" "${WT_RECENTCOMMIT}" "${WT_INUSE}" "${WT_SYM}" "${WT_NOGIT}" "${R_SA}"; do age "${d}"; done
echo new > "${WT_RECENTFILE}/touched-now.txt"                              # 14日以内の更新
mkdir -p "${T}/outside/nm-target"; echo keep > "${T}/outside/nm-target/f"
ln -s "${T}/outside/nm-target" "${WT_SYM}/node_modules"                    # node_modules がシンボリックリンク
start_sleeper "${WT_INUSE}"                                                # 使用中

# ── R3 の準備 ───────────────────────────────────────────────────────────────
for v in v0.2.0 v0.3.0 v0.4.0 v0.7.0 v0.9.1 v1.0.0; do mkdir -p "${R_VER}/${v}/app"; echo x > "${R_VER}/${v}/app/f"; done
mkdir -p "${R_VER}/not-a-version" "${T}/outside/ver-target"; echo keep > "${T}/outside/ver-target/f"
ln -s "${T}/outside/ver-target" "${R_VER}/v0.5.0"                          # 版名のシンボリックリンク
ln -s "versions/v0.9.1" "${T}/current"
start_sleeper "${R_VER}/v0.4.0/app"                                        # 使用中の旧版

# ── R4 の準備（偽の reaper は呼ばれ方を記録するだけ）─────────────────────────────
REAPER_LOG="${T}/reaper.log"
FAKE_REAPER="${T}/fake-reaper.sh"
cat > "${FAKE_REAPER}" <<'EOF'
#!/bin/bash
echo "args=[$*] pwd=$(pwd -P) name=${REAPER_REPO_NAME:-} base=${REAPER_BASE_BRANCH:-} aw=${REAPER_ACTIVE_WORK_FILE:-} awdir=${ACTIVE_WORK_DIR:-}" >> "${REAPER_LOG_PATH}"
echo "fake reaper ran"
EOF
export REAPER_LOG_PATH="${REAPER_LOG}" DJ_REAPER="${FAKE_REAPER}"
for spec in repoX:owner/x repoY:owner/wrong; do
  mkdir -p "${T}/${spec%%:*}"; git init -q "${T}/${spec%%:*}"
  git -C "${T}/${spec%%:*}" remote add origin "git@github.com:${spec#*:}.git"
done
export DJ_REPOS="${T}/repoX|owner/x|develop
${T}/repoY|owner/y|main
${T}/missing|a/b|main
${GM}|owner/gm|main"

snapshot() { find -P "${T}" -path "${T}/gitmain" -prune -o -path "${T}/lock.d" -prune -o -path "${T}/reaper.log" -prune -o -print 2>/dev/null | sort; }

# ── 1. dry-run では何も消えない ──────────────────────────────────────────────
BEFORE="$(snapshot)"
OUT_DRY="$(bash "${JANITOR}" 2>&1)"; RC_DRY=$?
AFTER="$(snapshot)"
echo "=== dry-run 出力 ==="; echo "${OUT_DRY}"; echo "=== ここまで ==="
check "dry-run: exit 0" [ "${RC_DRY}" -eq 0 ]
check "dry-run: 何も消えない（前後の一覧が同一）" [ "${BEFORE}" = "${AFTER}" ]
[ "${BEFORE}" = "${AFTER}" ] || diff <(echo "${BEFORE}") <(echo "${AFTER}") | head -20
check "dry-run: R1 の候補が出る" grep -q "\[R1\] ${R_SA}/.npm-cache " <<<"${OUT_DRY}"
check "dry-run: R2 の候補が出る" grep -q "\[R2\] ${WT_DEL}/node_modules " <<<"${OUT_DRY}"
check "dry-run: R3 の候補が出る" grep -q "\[R3\] ${R_VER}/v0.2.0 " <<<"${OUT_DRY}"
check "dry-run: 見出しが dry-run" grep -q "mode=dry-run" <<<"${OUT_DRY}"
check "dry-run: R4 の reaper は --execute なしで呼ばれる" grep -q "args=\[\] pwd=${T}/repoX " "${REAPER_LOG}"
: > "${REAPER_LOG}"

# ── 2. --execute ────────────────────────────────────────────────────────────
OUT_EXE="$(bash "${JANITOR}" --execute 2>&1)"; RC_EXE=$?
echo "=== execute 出力 ==="; echo "${OUT_EXE}"; echo "=== ここまで ==="
check "execute: exit 0" [ "${RC_EXE}" -eq 0 ]

# R1 消す
check "R1 消す: worktree 内の .npm-cache" gone "${R_WT}/repoA/wt1/.npm-cache"
check "R1 消す: 本体直下の .npm-cache" gone "${R_SA}/.npm-cache"
check "R1 消す: 本体 frontend の .npm-cache" gone "${R_SA}/frontend/.npm-cache"
check "R1 消す: agent-console-wt 内の .npm-cache" gone "${R_ACWT}/x/.npm-cache"
# R1 保護
check "R1 保護: npm の設定先（保護する cache）" exists "${KEEP_CACHE}"
check "R1 保護: 使用中（プロセスが cwd にしている）" exists "${R_AC}/.npm-cache"
check "R1 保護: シンボリックリンク（リンク自身）" exists "${R_WT}/repoA/linkholder/.npm-cache"
check "R1 保護: シンボリックリンクの指し先（根の外）" exists "${T}/outside/.npm-cache"
check "R1 保護: 使用中は理由つきで飛ばしたと出る" grep -q "\[飛ばす\] ${R_AC}/.npm-cache （使用中" <<<"${OUT_EXE}"

# R2 消す
check "R2 消す: 直下の node_modules" gone "${WT_DEL}/node_modules"
check "R2 消す: frontend の node_modules" gone "${WT_DEL}/frontend/node_modules"
check "R2 消す: agent-console-wt 側" gone "${WT_ACDEL}/node_modules"
check "R2 消す: 作業用コピー自体と package-lock は残る" exists "${WT_DEL}/package-lock.json"
# R2 保護
check "R2 保護: package-lock.json なし" exists "${WT_NOLOCK}/node_modules"
check "R2 保護: 14日以内に更新されたファイルあり" exists "${WT_RECENTFILE}/node_modules"
check "R2 保護: 最終コミットが14日以内" exists "${WT_RECENTCOMMIT}/node_modules"
check "R2 保護: 使用中（cwd にしているプロセスあり）" exists "${WT_INUSE}/node_modules"
check "R2 保護: git の繋がりが合わない・git log が失敗する（L1: 使っていない判定にしない）" exists "${WT_NOGIT}/node_modules"
check "R2 保護: node_modules がシンボリックリンク（リンクも指し先も残る）" both_exist "${WT_SYM}/node_modules" "${T}/outside/nm-target/f"
check "R2 保護: 本体 salesanchor の node_modules" exists "${R_SA}/node_modules"
check "R2 保護: 本体 agent-console の node_modules" exists "${R_AC}/node_modules"

# R3 消す
check "R3 消す: v0.2.0" gone "${R_VER}/v0.2.0"
check "R3 消す: v0.3.0" gone "${R_VER}/v0.3.0"
# R3 保護
check "R3 保護: current (v0.9.1)" exists "${R_VER}/v0.9.1"
check "R3 保護: 1つ前 (v0.7.0)" exists "${R_VER}/v0.7.0"
check "R3 保護: current より新しい版 (v1.0.0)" exists "${R_VER}/v1.0.0"
check "R3 保護: 使用中の旧版 (v0.4.0)" exists "${R_VER}/v0.4.0"
check "R3 保護: シンボリックリンクの版（リンクも指し先も残る）" both_exist "${R_VER}/v0.5.0" "${T}/outside/ver-target/f"
check "R3 保護: 版名でないディレクトリ" exists "${R_VER}/not-a-version"

# R4
check "R4: reaper が --execute 付きで呼ばれる" grep -q "args=\[--execute\] " "${REAPER_LOG}"
check "R4: 作業場所・名前・行き先・台帳の無効化が渡る" grep -q "pwd=${T}/repoX name=owner/x base=develop aw=/dev/null awdir=/nonexistent-disk-janitor" "${REAPER_LOG}"
check "R4: origin が想定と違うリポジトリは呼ばれない" bash -c '! grep -q "repoY" "$1"' _ "${REAPER_LOG}"
check "R4: origin が想定と違うリポジトリは理由つきで飛ばす" grep -q "origin が想定と違う" <<<"${OUT_EXE}"
check "R4: 無いリポジトリは飛ばす" grep -q "\[飛ばす\] ${T}/missing" <<<"${OUT_EXE}"
check "R4: reaper は2回目の呼び出しを含めて repoX の1回だけ" [ "$(wc -l < "${REAPER_LOG}" | tr -d ' ')" -eq 1 ]

# ── 3. 2回目の dry-run は候補 0 件 ───────────────────────────────────────────
OUT_2="$(bash "${JANITOR}" 2>&1)"
check "2回目の dry-run: R1 の削除候補 0 件" grep -q "^\[R1\] 削除候補: 0 件" <<<"${OUT_2}"
check "2回目の dry-run: R2 の削除候補 0 件" grep -q "^\[R2\] 削除候補: 0 件" <<<"${OUT_2}"
check "2回目の dry-run: R3 の削除候補 0 件" grep -q "^\[R3\] 削除候補: 0 件" <<<"${OUT_2}"

# ── 4. 規則ごとの飛ばし条件 ──────────────────────────────────────────────────
mkdir -p "${R_SA}/again/.npm-cache"
OUT_LSOF="$(DJ_LSOF=false bash "${JANITOR}" --execute 2>&1)"
check "lsof 失敗: R1 全体を飛ばし何も消えない" exists "${R_SA}/again/.npm-cache"
check "lsof 失敗: R1〜R3 を飛ばすと出る" [ "$(grep -c '規則ごと飛ばす\] lsof が失敗' <<<"${OUT_LSOF}")" -eq 3 ]
OUT_REL="$(DJ_NPM_CMD="echo ${R_SA}/.npm-cache" bash "${JANITOR}" --execute 2>&1)"
check "npm の cache が根の下: R1 全体を飛ばし何も消えない" exists "${R_SA}/again/.npm-cache"
check "npm の cache が根の下: 警告が出る" grep -q "D1 未適用の可能性" <<<"${OUT_REL}"
# 相対パス設定を模した偽 npm: 呼ばれた場所（pwd）によって値が変わる
FAKE_NPM="${T}/fake-npm.sh"
printf '%s\n' '#!/bin/bash' 'echo "$(pwd -P)/.npm-cache"' > "${FAKE_NPM}"
OUT_REL2="$(DJ_NPM_CMD="bash ${FAKE_NPM}" bash "${JANITOR}" --execute 2>&1)"
check "相対パス設定（場所で値が変わる）: R1 全体を飛ばし何も消えない" exists "${R_SA}/again/.npm-cache"
check "相対パス設定（場所で値が変わる）: 警告が出る" grep -q "D1 未適用の可能性" <<<"${OUT_REL2}"
OUT_NOCUR="$(DJ_CURRENT_LINK="${T}/no-such-link" bash "${JANITOR}" --execute 2>&1)"
check "current が読めない: R3 全体を飛ばす" grep -q "current が読めない" <<<"${OUT_NOCUR}"
mkdir -p "${R_VER}/v0.1.0"
DJ_CURRENT_LINK="${T}/no-such-link" bash "${JANITOR}" --execute >/dev/null 2>&1
check "current が読めない: 旧版は消えない" exists "${R_VER}/v0.1.0"

# ── 5. ロックとログ ──────────────────────────────────────────────────────────
mkdir -p "${DJ_LOCK_DIR}"
OUT_LOCK="$(bash "${JANITOR}" 2>&1)"
check "ロック中: 実行せず skip と出る" grep -q "another instance is running" <<<"${OUT_LOCK}"
rmdir "${DJ_LOCK_DIR}"
LOGF="${T}/logs/disk-janitor.log"
mkdir -p "${T}/logs"; head -c 2000 /dev/zero | tr '\0' 'x' > "${LOGF}"
( DJ_LOG_FILE="${LOGF}" DJ_LOG_MAX_BYTES=100 bash "${JANITOR}" >/dev/null 2>&1 )
check "ログ: 上限超えは .1 に退避され1世代だけ" bash -c '[ -f "$1.1" ] && [ ! -e "$1.2" ]' _ "${LOGF}"
check "ログ: 新しいログに実行の記録が出る" grep -q "disk-janitor 開始" "${LOGF}"
check "ログ: 新しいログに規則ごとの件数・容量と df が出る" bash -c 'grep -q "^\[R1\] " "$1" && grep -q "df（開始）" "$1" && grep -q "df（終了）" "$1"' _ "${LOGF}"

# ── 6. ガード（dj_guard を直接呼ぶ）────────────────────────────────────────────
# shellcheck source=../disk-janitor.sh
source "${JANITOR}"
G_ROOT1="${R_WT}"; G_ROOT2="${R_SA}"
mkdir -p "${R_SA}/ok-case/.npm-cache" "${R_SA}/other-name"
g_pass() { dj_guard "$1" '^\.npm-cache$' "${G_ROOT1}" "${G_ROOT2}"; }
check "ガード: 条件を満たすパスは通る" g_pass "${R_SA}/ok-case/.npm-cache"
check "ガード: 空のパスは拒否" bash -c 'source "$1"; ! dj_guard "" "." "$2"' _ "${JANITOR}" "${R_SA}"
check "ガード: / は拒否" bash -c 'source "$1"; ! dj_guard "/" "." "$2"' _ "${JANITOR}" "${R_SA}"
check "ガード: HOME そのものは拒否" bash -c 'source "$1"; ! dj_guard "$HOME" "." "$HOME" "$2"' _ "${JANITOR}" "${R_SA}"
check "ガード: 根そのものは拒否" bash -c 'source "$1"; ! dj_guard "$2" "." "$2"' _ "${JANITOR}" "${R_SA}"
check "ガード: 相対パスは拒否" bash -c 'source "$1"; ! dj_guard "sa/.npm-cache" "." "$2"' _ "${JANITOR}" "${R_SA}"
check "ガード: .. を含むパスは拒否" bash -c 'source "$1"; ! dj_guard "$2/ok-case/../ok-case/.npm-cache" "." "$2"' _ "${JANITOR}" "${R_SA}"
check "ガード: 根の外は拒否" bash -c 'source "$1"; ! dj_guard "$2" "." "$3"' _ "${JANITOR}" "${T}/outside/.npm-cache" "${R_SA}"
check "ガード: シンボリックリンクは拒否" bash -c 'source "$1"; ! dj_guard "$2" "." "$3"' _ "${JANITOR}" "${R_WT}/repoA/linkholder/.npm-cache" "${R_WT}"
check "ガード: 名前が規則と一致しないものは拒否" bash -c 'source "$1"; ! dj_guard "$2" "^\.npm-cache$" "$3"' _ "${JANITOR}" "${R_SA}/other-name" "${R_SA}"
check "ガード: 存在しないパスは拒否" bash -c 'source "$1"; ! dj_guard "$2" "." "$3"' _ "${JANITOR}" "${R_SA}/nope" "${R_SA}"

# ── 7. K6: R5・R6（HDD 写しの成功が前提・.md と images/ と a*.output は消さない）─────────────
mk_k6() { # 毎回作り直す。8日前の物と1日前の物
  local d
  for d in "${DJ_ROOT_TMP_CC}" "${DJ_ROOT_CLAUDE_TMP}" "${T}/outside6"; do
    [ -d "${d}" ] && find -P "${d}" -depth -delete
    mkdir -p "${d}"
  done
  mkdir -p "${DJ_ROOT_TMP_CC}/sub" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/images" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/images" \
           "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/deep"
  echo x > "${DJ_ROOT_TMP_CC}/sub/raw.txt";   echo x > "${DJ_ROOT_TMP_CC}/sub/design.md"; echo x > "${DJ_ROOT_TMP_CC}/sub/new.txt"
  echo x > "${DJ_ROOT_TMP_CC}/sub/old.sql";   ln -s ../../outside6/target "${DJ_ROOT_TMP_CC}/sub/link.txt"
  echo x > "${T}/outside6/target"
  echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/memo.txt";        echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/new.txt"
  echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/images/pw.png";   echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/deep/a.log"
  echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/images/po.png"
  echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/b1.output";            echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/b2new.output"
  echo x > "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/other.txt"
  ln -s "${T}/outside6/target" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/alive.output"           # 指し先あり（a でなく名前外）
  ln -s "${T}/outside6/target" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-alive.output"         # a*.output で指し先あり
  ln -s "${T}/outside6/gone"   "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-dangling.output"      # 宙に浮いた a*.output
  ln -s "${T}/outside6/gone"   "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-dangling-new.output"
  local f
  for f in "${DJ_ROOT_TMP_CC}/sub/raw.txt" "${DJ_ROOT_TMP_CC}/sub/design.md" "${DJ_ROOT_TMP_CC}/sub/old.sql" \
           "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/memo.txt" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/images/pw.png" \
           "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/deep/a.log" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/images/po.png" \
           "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/b1.output" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/other.txt"; do
    touch -t 202601010000 "${f}"
  done
  touch -h -t 202601010000 "${DJ_ROOT_TMP_CC}/sub/link.txt" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-alive.output" \
        "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-dangling.output"
}
snap6() { find -P "${DJ_ROOT_TMP_CC}" "${DJ_ROOT_CLAUDE_TMP}" "${T}/outside6" 2>/dev/null | sort; }
fresh_ca() { echo "$(date +%s)" > "${DJ_CA_LAST_OK}"; }

mk_k6; fresh_ca
S6_BEFORE="$(snap6)"
OUT6_DRY="$(bash "${JANITOR}" 2>&1)"
echo "=== K6 dry-run 出力 ==="; echo "${OUT6_DRY}" | sed -n '/== R5/,/^--- df（終了）/p'; echo "=== ここまで ==="
check "K6 dry-run: 何も消えない（前後の一覧が同一）" [ "${S6_BEFORE}" = "$(snap6)" ]
check "K6 dry-run: R5 の候補に raw.txt が出る" grep -q "\[R5\] ${DJ_ROOT_TMP_CC}/sub/raw.txt " <<<"${OUT6_DRY}"
check "K6 dry-run: R5 の候補に old.sql が出る" grep -q "\[R5\] ${DJ_ROOT_TMP_CC}/sub/old.sql " <<<"${OUT6_DRY}"
check "K6 dry-run: R6 の候補に scratchpad の中が出る" grep -q "\[R6\] ${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad/memo.txt " <<<"${OUT6_DRY}"
check "K6 dry-run: R6 の候補に宙に浮いた a*.output が出る" grep -q "\[R6\] ${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-dangling.output " <<<"${OUT6_DRY}"
check "K6 dry-run: 見出し R5・R6 の削除候補" bash -c 'grep -q "^\[R5\] 削除候補: 2 件" <<<"$1" && grep -q "^\[R6\] 削除候補: 5 件" <<<"$1"' _ "${OUT6_DRY}"

bash "${JANITOR}" --execute >/dev/null 2>&1
check "K6 R5 消す: 7日より古い .md 以外" bash -c '[ ! -e "$1/sub/raw.txt" ] && [ ! -e "$1/sub/old.sql" ]' _ "${DJ_ROOT_TMP_CC}"
check "K6 R5 保護: .md" exists "${DJ_ROOT_TMP_CC}/sub/design.md"
check "K6 R5 保護: 7日以内" exists "${DJ_ROOT_TMP_CC}/sub/new.txt"
check "K6 R5 保護: シンボリックリンク（リンクも指し先も残る）" both_exist "${DJ_ROOT_TMP_CC}/sub/link.txt" "${T}/outside6/target"
check "K6 R6 消す: scratchpad の中（images/ と深い階層も）" bash -c '[ ! -e "$1/memo.txt" ] && [ ! -e "$1/images/pw.png" ] && [ ! -e "$1/deep/a.log" ]' _ "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/scratchpad"
check "K6 R6 消す: tasks/b*.output" gone "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/b1.output"
check "K6 R6 消す: 宙に浮いた a*.output（リンクだけ）" gone "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-dangling.output"
check "K6 R6 保護: <slug>/<uuid>/images/（PO の画像）" exists "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/images/po.png"
check "K6 R6 保護: 7日以内（scratchpad・b*.output・宙に浮いた a*.output）" bash -c '[ -e "$1/scratchpad/new.txt" ] && [ -e "$1/tasks/b2new.output" ] && [ -L "$1/tasks/a-dangling-new.output" ]' _ "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1"
check "K6 R6 保護: 指し先がある a*.output（リンクも指し先も残る）" both_exist "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-alive.output" "${T}/outside6/target"
check "K6 R6 保護: tasks の b*.output 以外" exists "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/other.txt"
check "K6 根の外は触らない" exists "${T}/outside6/target"

# last-ok が古い／無いと R5・R6 を見送る
mk_k6; echo $(( $(date +%s) - 3 * 86400 )) > "${DJ_CA_LAST_OK}"
S6_BEFORE="$(snap6)"
OUT6_OLD="$(bash "${JANITOR}" --execute 2>&1)"
check "K6 last-ok が3日前: 何も消えない" [ "${S6_BEFORE}" = "$(snap6)" ]
check "K6 last-ok が3日前: 見送りがログに出る" [ "$(grep -c 'R5/R6 見送り（HDD 写しが2日以上成功していない）' <<<"${OUT6_OLD}")" -eq 2 ]
mk_k6; rm -f -- "${DJ_CA_LAST_OK}"
S6_BEFORE="$(snap6)"
OUT6_NONE="$(bash "${JANITOR}" --execute 2>&1)"
check "K6 last-ok が無い: 何も消えない" [ "${S6_BEFORE}" = "$(snap6)" ]
check "K6 last-ok が無い: 見送りがログに出る" [ "$(grep -c 'R5/R6 見送り' <<<"${OUT6_NONE}")" -eq 2 ]
mk_k6; echo "abc" > "${DJ_CA_LAST_OK}"
bash "${JANITOR}" --execute >/dev/null 2>&1
check "K6 last-ok が数字でない: 何も消えない" exists "${DJ_ROOT_TMP_CC}/sub/raw.txt"
mk_k6; fresh_ca
OUT6_NOROOT="$(DJ_ROOT_TMP_CC="${T}/no-such-root" DJ_ROOT_CLAUDE_TMP="${T}/no-such-root2" bash "${JANITOR}" --execute 2>&1)"
check "K6 根が無い: 規則ごと飛ばす" [ "$(grep -c '規則ごと飛ばす\] 根が無い' <<<"${OUT6_NOROOT}")" -eq 2 ]

# dj_guard_file を直接呼ぶ
mk_k6
# shellcheck source=../disk-janitor.sh
source "${JANITOR}"
DJ_TMP_STALE_DAYS=7
GF_OLD="${DJ_ROOT_TMP_CC}/sub/raw.txt"
check "ガード(ファイル): 条件を満たすファイルは通る" dj_guard_file f "${GF_OLD}" '.' "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): 7日以内は拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2" "." "$3"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}/sub/new.txt" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): 根の外は拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2" "." "$3"' _ "${JANITOR}" "${T}/outside6/target" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): シンボリックリンクは f で拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2" "." "$3"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}/sub/link.txt" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): ディレクトリは拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2" "." "$3"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}/sub" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): 根そのものは拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2" "." "$2"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): .. を含むパスは拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2/sub/../sub/raw.txt" "." "$2"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): 相対パスは拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "sub/raw.txt" "." "$2"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): 名前が規則と一致しないものは拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file f "$2" "^b.*" "$3"' _ "${JANITOR}" "${GF_OLD}" "${DJ_ROOT_TMP_CC}"
check "ガード(ファイル): dangling は指し先がある物を拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ! dj_guard_file dangling "$2" "." "$3"' _ "${JANITOR}" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-alive.output" "${DJ_ROOT_CLAUDE_TMP}"
check "ガード(ファイル): dangling は宙に浮いたリンクを通す" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; dj_guard_file dangling "$2" "." "$3"' _ "${JANITOR}" "${DJ_ROOT_CLAUDE_TMP}/slug/uuid1/tasks/a-dangling.output" "${DJ_ROOT_CLAUDE_TMP}"
check "ガード(ファイル): 途中がシンボリックリンクなら拒否" bash -c 'source "$1"; DJ_TMP_STALE_DAYS=7; ln -s "$3" "$2/linkdir"; ! dj_guard_file f "$2/linkdir/target" "." "$2"' _ "${JANITOR}" "${DJ_ROOT_TMP_CC}" "${T}/outside6"

# J1(ADR-1039): git の守りを読めないとき、何も実行せず終了コード 1。読めるときは配列が定義される
J1_COPY="${T}/j1-copy"; mkdir -p "${J1_COPY}"
cp "${JANITOR}" "${J1_COPY}/disk-janitor.sh"
J1_RC=0; bash "${J1_COPY}/disk-janitor.sh" >/dev/null 2>&1 || J1_RC=$?
check "J1: git-safe.sh が無い写しは終了コード 1 で終わる" test "${J1_RC}" -eq 1
check "J1: git-safe.sh があれば GIT_SAFE_ARGS が定義される" bash -c 'source "$1"; [ "${#GIT_SAFE_ARGS[@]}" -gt 0 ]' _ "${JANITOR}"
# J2: git-safe.sh が空のとき、--execute でも終了コード 1・何も消さない（bash 3.2 + set -u で配列判定が止まらない問題の対策）
J2_COPY="${T}/j2-copy"; mkdir -p "${J2_COPY}"
cp "${JANITOR}" "${J2_COPY}/disk-janitor.sh"; : > "${J2_COPY}/git-safe.sh"
mkdir -p "${DJ_ROOT_SALESANCHOR}/j2probe/.npm-cache"
J2_RC=0; J2_OUT="$(bash "${J2_COPY}/disk-janitor.sh" --execute 2>&1)" || J2_RC=$?
check "J2: git-safe.sh が空なら終了コード 1" test "${J2_RC}" -eq 1
check "J2: 空のとき何も消さない（置いた .npm-cache が残る）" test -d "${DJ_ROOT_SALESANCHOR}/j2probe/.npm-cache"
check "J2: 空のとき削除の出力が無い" bash -c '! printf "%s" "$1" | grep -q "削除"' _ "${J2_OUT}"

# ── J3〜J5（ADR-1039 便2b-2）: git の繋がりの確かめ ────────────────────────────────
# 偽の置き場は gitmain の .git を worktrees 抜きで写して作る（rsync --exclude。消す操作を使わない）。
# 作り物はすべて $T の下（終了時の既存の後片付けに任せる）。
J_MARK="${T}/j-mark"
J_EVIL="${T}/j-evil-gitdir"
mkdir -p "${J_EVIL}"
rsync -a --exclude=/worktrees "${GM}/.git/" "${J_EVIL}/"
printf '[filter "evil"]\n\tclean = touch %s; cat\n' "${J_MARK}" >> "${J_EVIL}/config"
mkdir -p "${J_EVIL}/info"
printf 'README.md filter=evil\n' >> "${J_EVIL}/info/attributes"

# J3: R2 の対象の worktree。追跡している README.md を同じ長さで変え、commondir を偽の置き場へ
WT_J3="${R_WT}/repoA/wt-j3"; mkwt "${WT_J3}" br-j3; mk_nm "${WT_J3}"
printf 'bas2\n' > "${WT_J3}/README.md"       # 元は「base\n」（同じ5バイト）
J3_GD="$(git -C "${GM}" rev-parse --absolute-git-dir)/worktrees/wt-j3"
printf '%s\n' "${J_EVIL}" > "${J3_GD}/commondir"
rm -f "${J_MARK}"
git -C "${WT_J3}" -c core.fsmonitor=false -c core.hooksPath=/dev/null diff --no-ext-diff --no-textconv --ignore-submodules=all --numstat >/dev/null 2>&1
check "J3-対照: 偽の置き場を読む worktree では、上書き付きの git diff でも印ができる" test -e "${J_MARK}"
rm -f "${J_MARK}"
age "${WT_J3}"
# J4: 照らす一覧に無い元のリポジトリの worktree
GM2="${T}/gitmain2"
mkdir -p "${GM2}"
git init -q -b main "${GM2}"
echo base > "${GM2}/README.md"
git -C "${GM2}" add README.md
GIT_AUTHOR_DATE="2026-01-01T00:00:00" GIT_COMMITTER_DATE="2026-01-01T00:00:00" \
  git -C "${GM2}" -c user.name=t -c user.email=t@t commit -q -m base
WT_J4="${R_WT}/repoA/wt-j4"; git -C "${GM2}" worktree add -q -b br-j4 "${WT_J4}" HEAD 2>/dev/null; mk_nm "${WT_J4}"
age "${WT_J4}"
OUT_J34="$(bash "${JANITOR}" 2>&1)"
echo "=== J3・J4 dry-run 出力 ==="; echo "${OUT_J34}" | sed -n '/== R2/,/^\[R2\] /p'; echo "=== ここまで ==="
LINK_MSG="git の繋がりが知っている元のリポジトリと合わない"
check "J3: reaper でない janitor の dry-run で印の台本が動かない" test ! -e "${J_MARK}"
check "J3: 偽の commondir の worktree の node_modules が「残す」に入り、新しい理由の文が出る" bash -c 'grep -F "$1/node_modules" <<<"$3" | grep -q "$2"' _ "${WT_J3}" "${LINK_MSG}" "${OUT_J34}"
check "J3: 削除候補に入らない" bash -c '! grep -F "[R2] $1/node_modules " <<<"$2"' _ "${WT_J3}" "${OUT_J34}"
check "J4: 照らす一覧に無い元のリポジトリの worktree の node_modules が「残す」に入り、同じ文が出る" bash -c 'grep -F "$1/node_modules" <<<"$3" | grep -q "$2"' _ "${WT_J4}" "${LINK_MSG}" "${OUT_J34}"
check "J4: 削除候補に入らない" bash -c '! grep -F "[R2] $1/node_modules " <<<"$2"' _ "${WT_J4}" "${OUT_J34}"

# J5（R4）: .git/commondir を置いた作り物のリポジトリ。偽の reaper が呼ばれず、理由が出る
JR5="${T}/repoJ5"; git init -q "${JR5}"
git -C "${JR5}" remote add origin "git@github.com:owner/j5.git"
printf '%s\n' "${J_EVIL}" > "${JR5}/.git/commondir"
: > "${REAPER_LOG}"
OUT_J5="$(DJ_REPOS="${JR5}|owner/j5|main" bash "${JANITOR}" 2>&1)"
check "J5: そのリポジトリについて偽の reaper が呼ばれない" test ! -s "${REAPER_LOG}"
check "J5: 理由「git の繋がりを確かめられない（残す）」が出る" grep -q "git の繋がりを確かめられない（残す）" <<<"${OUT_J5}"

echo ""
echo "=== 合計 ==="
echo "ok: ${OK}"
echo "ng: ${NG}"
if [ "${NG}" -gt 0 ]; then
  echo "試験失敗あり"
  exit 1
fi
echo "全試験 ok"
exit 0
