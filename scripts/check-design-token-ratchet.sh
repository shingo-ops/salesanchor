#!/usr/bin/env bash
# design-system移行 便0b。ページ側hexベタ書きの新規増加を止めるラチェット。掃除は別便。
# 既存の週次design-token-audit.ymlとは別物（あちらは未使用トークン監査）。

set -euo pipefail

if [ -z "${BASE_SHA:-}" ] || [ -z "${HEAD_SHA:-}" ]; then
  echo "BASE_SHA と HEAD_SHA を指定してください" >&2
  exit 2
fi

# 正当な例外（外部埋め込み等）はここに追加。変更はPO承認必須。
ALLOWED_EXCEPTIONS=()

# ADR-1074（PO 2026-11-11 の選択「1」・design.md §10）: 予定の画面だけで使う Google の実測色の素材。
# 色の正本 frontend/src/index.css の中で、次の 13 個の名前の「1 行に 1 宣言だけ」の行を、
# 1 つの名前につき先頭から 2 行（明るい色と暗い色の 1 組）まで数えない。3 行目からは数える。
# 名前を足す・ファイルを足す・行数をゆるめる・形をゆるめる変更は PO 承認必須。
GCAL_PALETTE_FILE="frontend/src/index.css"
GCAL_PALETTE_LINE_RE='^[[:space:]]*--gcal-(surface|surface-lowest|surface-container|surface-filled|on-surface|on-surface-variant|outline-variant|gridline|primary|on-primary|secondary-container|on-secondary-container|now)[[:space:]]*:[[:space:]]*#[0-9a-fA-F]{3,8}[[:space:]]*;[[:space:]]*$'

drop_gcal_palette_lines() {
  if [ "$1" != "${GCAL_PALETTE_FILE}" ]; then
    cat
    return 0
  fi
  local body skip
  body=$(cat)
  skip=$(printf '%s\n' "${body}" | grep -nE "${GCAL_PALETTE_LINE_RE}" | awk -F: '{ name = $2; sub(/^[ \t]*--gcal-/, "", name); sub(/[ \t]+$/, "", name); if (++seen[name] <= 2) { printf "%s%s", sep, $1; sep = "," } }' || true)
  printf '%s\n' "${body}" | awk -v skip="${skip}" 'BEGIN { n = split(skip, a, ","); for (i = 1; i <= n; i++) drop[a[i]] = 1 } !(NR in drop)'
}

count_hex_in_ref_file() {
  local ref="$1"
  local file="$2"

  if ! git cat-file -e "${ref}:${file}" 2>/dev/null; then
    echo 0
    return 0
  fi

  local matches
  matches=$(git show "${ref}:${file}" 2>/dev/null | drop_gcal_palette_lines "${file}" | sed -E 's/\(#[0-9]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
  if [ -z "${matches}" ]; then
    echo 0
  else
    printf '%s\n' "${matches}" | wc -l | tr -d ' '
  fi
}

is_allowed_exception() {
  local file="$1"
  local exception
  for exception in "${ALLOWED_EXCEPTIONS[@]:-}"; do
    if [ "${file}" = "${exception}" ]; then
      return 0
    fi
  done
  return 1
}

target_files=()
while IFS= read -r file; do
  [ -n "${file}" ] || continue
  case "${file}" in
    frontend/src/*)
      case "${file}" in
        frontend/src/tokens.css) continue ;;
      esac
      case "${file}" in
        *.css|*.tsx|*.jsx|*.ts)
          if ! is_allowed_exception "${file}"; then
            target_files+=("${file}")
          fi
          ;;
      esac
      ;;
  esac
done < <(git diff --name-only "${BASE_SHA}" "${HEAD_SHA}")

failures=()
if [ "${#target_files[@]}" -gt 0 ]; then
  for file in "${target_files[@]}"; do
    base_count=$(count_hex_in_ref_file "${BASE_SHA}" "${file}")
    head_count=$(count_hex_in_ref_file "${HEAD_SHA}" "${file}")
    if [ "${head_count}" -gt "${base_count}" ]; then
      failures+=("${file}")
    fi
  done

  if [ "${#failures[@]}" -gt 0 ]; then
    echo "FAIL: hex増加を検出"
    for file in "${target_files[@]}"; do
      base_count=$(count_hex_in_ref_file "${BASE_SHA}" "${file}")
      head_count=$(count_hex_in_ref_file "${HEAD_SHA}" "${file}")
      echo "${file} ${base_count}->${head_count}"
    done
    exit 1
  fi
fi

echo "PASS: 対象${#target_files[@]}ファイル・増加なし"
