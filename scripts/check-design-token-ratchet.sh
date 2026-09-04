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

count_hex_in_ref_file() {
  local ref="$1"
  local file="$2"

  if ! git cat-file -e "${ref}:${file}" 2>/dev/null; then
    echo 0
    return 0
  fi

  local matches
  # (# ... ) 形式（PRリンク・ui-allow番号等）を除去してから計測する。
  # -E grep は後読みが使えないため sed で前処理する（macOS/Linux 両対応）。
  matches=$(git show "${ref}:${file}" 2>/dev/null | sed -E 's/\(#[0-9a-fA-F]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
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
