#!/usr/bin/env bash
# 本番反映（deploy.yml）の「止まり」を回ごとに数える台本（毎週の数え）。
# 設計: docs/handoff/deploy-db-stall/design.md §19-4。数えるだけで、本番のサーバーと DB には触らない。
#
# 使い方:
#   count-deploy-lock-failures.sh [--days N | --since YYYY-MM-DD --until YYYY-MM-DD]
#                                 [--notify-file PATH] [--from-dir DIR]
#   既定は --days 7。期間は日本時間の 00:00 から 00:00 まで（since 以上・until 未満）。
#   --from-dir DIR は API を呼ばず、DIR に置いた API の返事を読む（試験用）。
#   --notify-file PATH は、知らせの対象が0でないときだけ本文を PATH に書く。
#
# 終わり方: 0 = 全部数えられた / 2 = API の失敗か読めなかった回がある（数えた分は出す）/ 1 = 引数の誤り
#
# 限界: 作ってから7日より後にやり直した回は数えない（run の一覧を期間の始めの7日前から引くため）。
#   11/1〜11/13 のやり直し6本は、どれも作ってから40分以内だった（design.md §19-4 の 2.）。
#
# 記録の読み方: 記録には文字以外のバイト（NUL）が混じる。grep は -a が要る（-a なしでは行が出ない）。
#   数えるときは grep -c・grep -q を使わない。-c・-q は -a なしでも数が出て、-a の抜けを試験で捕まえられないため。
#   grep -a で行を取り出してから、この台本の中で数える。決まった文字は grep -aF（文字どおり）で探す
#   （[precheck] は -F が無いと「p・r・e…のどれか1文字」の意味になる）。-E は retry [0-9] の1つだけ。
#   記録の各行の頭には時刻が付くので、行を読む前に頭の時刻（最初の空白までの1語とその後の空白1つ）を外す。

SELF_NAME="count-deploy-lock-failures"
REPO="${GITHUB_REPOSITORY:-shingo-ops/salesanchor}"
MIGRATE_STEP="Run database migrations"
CHECK_STEP="Check open DB transactions before deploy"

DAYS=""
SINCE=""
UNTIL=""
FROM_DIR=""
NOTIFY_FILE=""

usage_err() {
  echo "${SELF_NAME}: $*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --days) DAYS="${2:-}"; shift 2 ;;
    --since) SINCE="${2:-}"; shift 2 ;;
    --until) UNTIL="${2:-}"; shift 2 ;;
    --from-dir) FROM_DIR="${2:-}"; shift 2 ;;
    --notify-file) NOTIFY_FILE="${2:-}"; shift 2 ;;
    *) usage_err "unknown argument: $1" ;;
  esac
done

command -v jq >/dev/null 2>&1 || usage_err "jq is required"

if [ -n "${DAYS}" ] && { [ -n "${SINCE}" ] || [ -n "${UNTIL}" ]; }; then
  usage_err "--days cannot be combined with --since/--until"
fi
if [ -n "${SINCE}" ] || [ -n "${UNTIL}" ]; then
  [ -n "${SINCE}" ] && [ -n "${UNTIL}" ] || usage_err "--since and --until must be given together"
else
  DAYS="${DAYS:-7}"
  case "${DAYS}" in
    ''|*[!0-9]*) usage_err "--days must be a positive integer" ;;
  esac
  [ "${DAYS}" -ge 1 ] || usage_err "--days must be a positive integer"
  UNTIL="$(TZ=Asia/Tokyo date +%F)"
  SINCE="$(date -u -d "${UNTIL} -${DAYS} days" +%F)" || usage_err "date calculation failed"
fi
date_ok() { [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && date -u -d "$1" +%F >/dev/null 2>&1; }
date_ok "${SINCE}" || usage_err "invalid --since: ${SINCE}"
date_ok "${UNTIL}" || usage_err "invalid --until: ${UNTIL}"

# 期間: 日本時間の SINCE 00:00 以上、UNTIL 00:00 未満
SINCE_E="$(date -d "${SINCE} 00:00:00 +0900" +%s)"
UNTIL_E="$(date -d "${UNTIL} 00:00:00 +0900" +%s)"
[ "${SINCE_E}" -lt "${UNTIL_E}" ] || usage_err "--since must be before --until"

# 作業用の置き場（実行機の一時領域。終わりに残っても害は無い）
WORK="$(mktemp -d)"

API_CALLS=0
API_FAILED=0
UNREADABLE=0
MIG_RAN=0
CHK_RAN=0
LIMIT_FAIL=0
OTHER_FAIL=0
WAITING=0
STOP_HALT=0
OTHER_HALT=0
UNPARSED_HOLDERS=0
declare -A SEEN
declare -A HOLDERS
declare -A REASONS
LAST_FETCH_REASON=""
ROWS=""
FAILED_DAYS=""
UNREADABLE_RUNS=""
LIMIT_RUNS=""
OTHER_FAIL_RUNS=""
STOP_RUNS=""
OTHER_HALT_RUNS=""

# 引く: fetch <API のパス> <DIR 内の相対パス> <書き出し先>。引けなければ 1
fetch() {
  local api_path="$1" rel="$2" out="$3"
  if [ -n "${FROM_DIR}" ]; then
    if [ ! -f "${FROM_DIR}/${rel}" ]; then
      LAST_FETCH_REASON="作り物なし"
      return 1
    fi
    cp "${FROM_DIR}/${rel}" "${out}"
    LAST_FETCH_REASON=""
    return 0
  fi
  API_CALLS=$((API_CALLS + 1))
  # job の記録（/logs で終わる）は端末の制御文字を含みうる。新しい gh は既定で断るので、記録のときだけ許す（design.md §19-16 決め1）
  local -a gh_flags=()
  case "${api_path}" in
    */logs) gh_flags=(--allow-escape-sequences) ;;
  esac
  if gh api "${gh_flags[@]}" "${api_path}" > "${out}" 2> "${WORK}/fetch-err.txt"; then
    LAST_FETCH_REASON=""
    return 0
  fi
  API_FAILED=1
  # 失敗の文の最初の空でない行。? から後ろ（署名つき URL）を消し、160字で切る（design.md §19-15 決め1）
  local reason
  reason="$(grep -a -m1 '[^[:space:]]' "${WORK}/fetch-err.txt" 2>/dev/null | tr -d '\0')"
  reason="${reason%%\?*}"
  reason="${reason:0:160}"
  [ -n "${reason}" ] || reason="理由なし"
  LAST_FETCH_REASON="${reason}"
  return 1
}

# 記録のファイルから端末の制御文字を消す（design.md §19-16 決め2）。引数: 記録のファイル
strip_esc() {
  local lf="$1" esc
  esc="$(printf '\033')"
  LC_ALL=C sed "s/${esc}\[[0-9;]*[A-Za-z]//g" "${lf}" | LC_ALL=C tr -d '\033' > "${lf}.clean"
  mv "${lf}.clean" "${lf}"
}

# 読めなかった回を1つ数える。引数: 段の名前（回・job一覧・記録・一覧・未完了・時刻なし）、理由（省略時は -）
mark_unreadable() {
  local stage="$1" reason="${2:--}"
  UNREADABLE=$((UNREADABLE + 1))
  REASONS["${stage} / ${reason}"]=$(( ${REASONS["${stage} / ${reason}"]:-0} + 1 ))
}

# 行の頭の時刻（最初の空白までの1語とその後の空白1つ）を外す
strip_ts() {
  LC_ALL=C sed 's/^[^ ]* //'
}

add_row() {
  ROWS="${ROWS}$1 | $2 | $3 | $4 | $5 | $6 | $7"$'\n'
}

# 握り手の行を読む（待ちのあった全部の回から）。引数: 記録のファイル
collect_holders() {
  local log="$1" line rest f n after_header=0 users
  while IFS= read -r line; do
    if [[ "${line}" == *'lock holders (xact > 1s):'* ]]; then
      after_header=1
      continue
    fi
    [ "${after_header}" -eq 1 ] || continue
    if [[ "${line}" =~ ^'>>> ['[0-9]+/[0-9]+']'\ \ \ (.*)$ ]]; then
      rest="${BASH_REMATCH[1]}"
      n=1
      local -a parts=()
      while [[ "${rest}" == *' | '* ]]; do
        f="${rest%%' | '*}"
        rest="${rest#*' | '}"
        parts+=("${f}")
      done
      parts+=("${rest}")
      if [ "${#parts[@]}" -eq 8 ]; then
        local uname="${parts[1]}" aname="${parts[2]}"
        [ -n "${aname}" ] || aname="名前なし"
        HOLDERS["${uname} / ${aname}"]=$(( ${HOLDERS["${uname} / ${aname}"]:-0} + 1 ))
        LAST_HOLDER_USERS="${LAST_HOLDER_USERS}${LAST_HOLDER_USERS:+,}${uname}/${aname}"
      else
        UNPARSED_HOLDERS=$((UNPARSED_HOLDERS + 1))
      fi
    else
      after_header=0
    fi
  done < <(tr -d '\0' < "${log}" | strip_ts)
}

# 1つの (run, 回) を数える
process_attempt() {
  local id="$1" n="$2" created="$3" list_started="${4:-}" list_status="${5:-}" list_attempt="${6:-}" key="$1-$2"
  [ -z "${SEEN[${key}]:-}" ] || return 0
  SEEN["${key}"]=1

  local started status window_ts se af
  if [ "${n}" = "${list_attempt}" ] && [ -n "${list_started}" ] && [ -n "${list_status}" ]; then
    # 最後の回は、一覧の run_started_at と status を使い、回の API を呼ばない（design.md §19-4 の 2b. (ii)）
    started="${list_started}"
    status="${list_status}"
  else
    af="${WORK}/att-${key}.json"
    if ! fetch "repos/${REPO}/actions/runs/${id}/attempts/${n}" "attempts/${key}.json" "${af}" \
       || ! jq -e . "${af}" >/dev/null 2>&1; then
      mark_unreadable "回" "${LAST_FETCH_REASON:--}"
      UNREADABLE_RUNS="${UNREADABLE_RUNS} ${id}"
      add_row "${id}" "${n}" "-" "-" "読めなかった" "-" "-"
      return 0
    fi
    started="$(jq -r '.run_started_at // empty' "${af}")"
    status="$(jq -r '.status // empty' "${af}")"
  fi
  window_ts="${started}"
  se=""
  [ -n "${window_ts}" ] && se="$(date -d "${window_ts}" +%s 2>/dev/null)"
  if [ -z "${se}" ]; then
    mark_unreadable "時刻なし" "-"
    UNREADABLE_RUNS="${UNREADABLE_RUNS} ${id}"
    add_row "${id}" "${n}" "-" "-" "読めなかった" "-" "-"
    return 0
  fi
  # 期間の外の回は数えない（出力にも出さない）
  if [ "${se}" -lt "${SINCE_E}" ] || [ "${se}" -ge "${UNTIL_E}" ]; then
    return 0
  fi
  if [ "${status}" != "completed" ]; then
    mark_unreadable "未完了" "-"
    UNREADABLE_RUNS="${UNREADABLE_RUNS} ${id}"
    add_row "${id}" "${n}" "${started}" "-" "読めなかった" "-" "-"
    return 0
  fi

  local jf="${WORK}/jobs-${key}.json"
  if ! fetch "repos/${REPO}/actions/runs/${id}/attempts/${n}/jobs?per_page=100" "jobs/${key}.json" "${jf}" \
     || ! jq -e . "${jf}" >/dev/null 2>&1; then
    mark_unreadable "job一覧" "${LAST_FETCH_REASON:--}"
    UNREADABLE_RUNS="${UNREADABLE_RUNS} ${id}"
    add_row "${id}" "${n}" "${started}" "-" "読めなかった" "-" "-"
    return 0
  fi

  local job_lines job mc cc
  job_lines="$(jq -r --arg m "${MIGRATE_STEP}" --arg c "${CHECK_STEP}" '
    .jobs[]? | [ (.id | tostring),
      ([.steps[]? | select(.name == $m) | (.conclusion // "none")] | first // "none"),
      ([.steps[]? | select(.name == $c) | (.conclusion // "none")] | first // "none") ] | @tsv' "${jf}")"
  [ -n "${job_lines}" ] || return 0

  while IFS=$'\t' read -r job mc cc; do
    [ -n "${job}" ] || continue
    local mig_ran=0 chk_ran=0
    case "${mc}" in skipped|none) ;; *) mig_ran=1 ;; esac
    case "${cc}" in skipped|none) ;; *) chk_ran=1 ;; esac
    [ "${mig_ran}" -eq 1 ] || [ "${chk_ran}" -eq 1 ] || continue

    local lf="${WORK}/log-${job}.log"
    if ! fetch "repos/${REPO}/actions/jobs/${job}/logs" "logs/${job}.log" "${lf}"; then
      mark_unreadable "記録" "${LAST_FETCH_REASON:--}"
      UNREADABLE_RUNS="${UNREADABLE_RUNS} ${id}"
      add_row "${id}" "${n}" "${started}" "-" "読めなかった" "-" "-"
      continue
    fi
    strip_esc "${lf}"

    # grep -a で行を取り出してから、ここで数える（-c・-q は使わない）
    local limit_lines retry_lines stop_lines
    limit_lines="$(LC_ALL=C grep -aF 'lock conflict; retry limit reached' "${lf}" | tr -d '\0' | strip_ts)"
    retry_lines="$(LC_ALL=C grep -aE 'lock conflict; retry [0-9]' "${lf}" | tr -d '\0' | strip_ts)"
    stop_lines="$(LC_ALL=C grep -aF '[precheck] STOP:' "${lf}" | tr -d '\0' | strip_ts)"
    local wait_lines=0
    [ -z "${retry_lines}" ] || wait_lines="$(printf '%s\n' "${retry_lines}" | wc -l)"

    LAST_HOLDER_USERS=""
    # 握り手は、失敗の回だけでなく待ちのあった全部の回から取る
    if [ "${wait_lines}" -gt 0 ] || [ -n "${limit_lines}" ]; then
      collect_holders "${lf}"
    fi
    local holder_text="${LAST_HOLDER_USERS:--}"

    if [ "${mig_ran}" -eq 1 ]; then
      MIG_RAN=$((MIG_RAN + 1))
      local klass="失敗なし"
      case "${mc}" in
        failure)
          if [ -n "${limit_lines}" ]; then
            klass="上限失敗"; LIMIT_FAIL=$((LIMIT_FAIL + 1)); LIMIT_RUNS="${LIMIT_RUNS} ${id}"
          else
            klass="その他の失敗"; OTHER_FAIL=$((OTHER_FAIL + 1)); OTHER_FAIL_RUNS="${OTHER_FAIL_RUNS} ${id}"
          fi ;;
        cancelled|timed_out)
          klass="その他の失敗"; OTHER_FAIL=$((OTHER_FAIL + 1)); OTHER_FAIL_RUNS="${OTHER_FAIL_RUNS} ${id}" ;;
      esac
      [ "${wait_lines}" -gt 0 ] && WAITING=$((WAITING + 1))
      add_row "${id}" "${n}" "${started}" "移行" "${klass}" "${wait_lines}" "${holder_text}"
    fi
    if [ "${chk_ran}" -eq 1 ]; then
      CHK_RAN=$((CHK_RAN + 1))
      local kc="停止なし"
      case "${cc}" in
        failure)
          if [ -n "${stop_lines}" ]; then
            kc="STOP停止"; STOP_HALT=$((STOP_HALT + 1)); STOP_RUNS="${STOP_RUNS} ${id}"
          else
            kc="その他の停止"; OTHER_HALT=$((OTHER_HALT + 1)); OTHER_HALT_RUNS="${OTHER_HALT_RUNS} ${id}"
          fi ;;
        cancelled|timed_out)
          kc="その他の停止"; OTHER_HALT=$((OTHER_HALT + 1)); OTHER_HALT_RUNS="${OTHER_HALT_RUNS} ${id}" ;;
      esac
      add_row "${id}" "${n}" "${started}" "点検" "${kc}" "-" "-"
    fi
  done <<< "${job_lines}"
}

# run の一覧を1日ずつ引く。UTC の日付 D を渡す
list_day() {
  local d="$1" page=1 pf count total
  while true; do
    pf="${WORK}/runs-${d}-${page}.json"
    local rel="runs/${d}.json"
    [ "${page}" -eq 1 ] || rel="runs/${d}-p${page}.json"
    if ! fetch "repos/${REPO}/actions/workflows/deploy.yml/runs?created=${d}..${d}&per_page=100&page=${page}" "${rel}" "${pf}" \
       || ! jq -e . "${pf}" >/dev/null 2>&1; then
      mark_unreadable "一覧" "${LAST_FETCH_REASON:--}"
      FAILED_DAYS="${FAILED_DAYS} ${d}"
      return 0
    fi
    total="$(jq -r '.total_count // 0' "${pf}")"
    if [ "${total}" -ge 1000 ]; then
      # 1回の検索は1,000件まで。黙って切らず、読めなかったとして扱う
      mark_unreadable "一覧" "-"
      FAILED_DAYS="${FAILED_DAYS} ${d}"
      return 0
    fi
    jq -r '.workflow_runs[]? | [(.id | tostring), (.created_at // ""), ((.run_attempt // 1) | tostring), ((.run_started_at // "") | if . == "" then "-" else . end), ((.status // "") | if . == "" then "-" else . end)] | @tsv' "${pf}" >> "${WORK}/runs.tsv"
    count="$(jq -r '(.workflow_runs // []) | length' "${pf}")"
    [ "${count}" -ge 100 ] || return 0
    page=$((page + 1))
  done
}

# 引く日: 日本時間の日付で since-7 日から until-1 日までの各日を UTC の日付として並べ、始めを1日前・終わりを1日後に広げる
START_D="$(date -u -d "${SINCE} -8 days" +%F)"
END_D="$(date -u -d "${UNTIL} +0 days" +%F)"
FETCHED_DATES=""
: > "${WORK}/runs.tsv"
d="${START_D}"
while [ "$(date -u -d "${d}" +%s)" -le "$(date -u -d "${END_D}" +%s)" ]; do
  FETCHED_DATES="${FETCHED_DATES}${FETCHED_DATES:+ }${d}"
  list_day "${d}"
  d="$(date -u -d "${d} +1 day" +%F)"
done

# 一覧の列: id・created_at・run_attempt・run_started_at・status（空の列は "-"。タブの連続で列が詰まるのを防ぐ）
while IFS=$'\t' read -r rid rcreated rattempt rstart rstatus; do
  [ -n "${rid}" ] || continue
  [ "${rstart}" != "-" ] || rstart=""
  [ "${rstatus}" != "-" ] || rstatus=""
  # 決まり (i): 期間の外の run は、回の API も job の API も呼ばずに飛ばす（出力にも数にも入れない）
  if [ -n "${rstart}" ]; then
    rse="$(date -d "${rstart}" +%s 2>/dev/null)"
    if [ -n "${rse}" ] && [ "${rse}" -lt "${SINCE_E}" ]; then
      continue
    fi
  fi
  if [ -n "${rcreated}" ]; then
    rce="$(date -d "${rcreated}" +%s 2>/dev/null)"
    if [ -n "${rce}" ] && [ "${rce}" -ge "${UNTIL_E}" ]; then
      continue
    fi
  fi
  a=1
  while [ "${a}" -le "${rattempt}" ]; do
    process_attempt "${rid}" "${a}" "${rcreated}" "${rstart}" "${rstatus}" "${rattempt}"
    a=$((a + 1))
  done
done < "${WORK}/runs.tsv"

NOTIFY_TOTAL=$((LIMIT_FAIL + OTHER_FAIL + STOP_HALT + OTHER_HALT + UNREADABLE))
END_CODE=0
if [ "${API_FAILED}" -ne 0 ] || [ "${UNREADABLE}" -ne 0 ]; then
  END_CODE=2
fi

# ---- 出力 ----
OUT="${WORK}/out.txt"
{
  echo "本番反映 止まりの数え: ${SINCE} 00:00 JST 以上 〜 ${UNTIL} 00:00 JST 未満"
  echo "限界: 作ってから7日より後にやり直した回は数えない"
  echo "fetched dates: ${FETCHED_DATES}"
  echo ""
  echo "run id | 回 | 時刻 | 段 | 分け | 待ち行数 | 握り手（DBユーザー/名前）"
  printf '%s' "${ROWS}"
  echo ""
  echo "合計"
  echo "移行の段が動いた回数: ${MIG_RAN}"
  echo "点検の段が動いた回数: ${CHK_RAN}"
  echo "上限失敗: ${LIMIT_FAIL}"
  echo "その他の失敗: ${OTHER_FAIL}"
  echo "待ちあり: ${WAITING}"
  echo "STOP停止: ${STOP_HALT}"
  echo "その他の停止: ${OTHER_HALT}"
  echo "読めなかった: ${UNREADABLE}"
  echo "読めなかった理由:"
  for k in "${!REASONS[@]}"; do
    echo "  ${k}: ${REASONS[${k}]}"
  done | sort
  echo "握り手の行（名前ごと）:"
  for k in "${!HOLDERS[@]}"; do
    echo "  ${k}: ${HOLDERS[${k}]}"
  done | sort
  echo "握り手の行（8つに分けられない）: ${UNPARSED_HOLDERS}"
  [ -z "${FAILED_DAYS}" ] || echo "一覧を引けなかった日:${FAILED_DAYS}"
  echo "API呼び出し回数: ${API_CALLS}"
  echo "知らせの対象の合計: ${NOTIFY_TOTAL}"
  echo "終わり: ${END_CODE}"
} > "${OUT}"
cat "${OUT}"

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### 本番反映 止まりの数え"
    if [ "${NOTIFY_TOTAL}" -eq 0 ]; then
      echo ""
      echo "0回（${SINCE} 〜 ${UNTIL}）"
    fi
    echo ""
    echo '```'
    cat "${OUT}"
    echo '```'
  } >> "${GITHUB_STEP_SUMMARY}"
fi

# ---- 知らせの本文（対象が0でないときだけ書く）----
ids_text() {
  # 最大10件。多ければ「ほか N 件」
  local list="$1" shown=0 total=0 out="" x
  for x in ${list}; do
    total=$((total + 1))
    if [ "${shown}" -lt 10 ]; then
      out="${out}${out:+, }${x}"
      shown=$((shown + 1))
    fi
  done
  [ "${total}" -eq 0 ] && { echo "-"; return; }
  [ "${total}" -le 10 ] || out="${out} ほか $((total - 10)) 件"
  echo "${out}"
}

if [ -n "${NOTIFY_FILE}" ] && [ "${NOTIFY_TOTAL}" -ne 0 ]; then
  body="本番反映の止まり ${NOTIFY_TOTAL} 件（${SINCE} 00:00 JST 〜 ${UNTIL} 00:00 JST）
上限失敗 ${LIMIT_FAIL}: $(ids_text "${LIMIT_RUNS}")
その他の失敗 ${OTHER_FAIL}: $(ids_text "${OTHER_FAIL_RUNS}")
STOP停止 ${STOP_HALT}: $(ids_text "${STOP_RUNS}")
その他の停止 ${OTHER_HALT}: $(ids_text "${OTHER_HALT_RUNS}")
読めなかった ${UNREADABLE}: $(ids_text "${UNREADABLE_RUNS}")"
  reason_lines="$(for k in "${!REASONS[@]}"; do echo "  ${k}: ${REASONS[${k}]}"; done | sort | head -n 5)"
  if [ -n "${reason_lines}" ]; then
    body="${body}
${reason_lines}"
  fi
  if [ -n "${FAILED_DAYS}" ]; then
    body="${body}
一覧を引けなかった日:${FAILED_DAYS}"
  fi
  if [ "${#body}" -gt 1900 ]; then
    body="${body:0:1890}..."
  fi
  printf '%s\n' "${body}" > "${NOTIFY_FILE}"
fi

exit "${END_CODE}"
