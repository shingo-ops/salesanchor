#!/bin/bash
# migration_record.sh — 実行済みの記録（段5 5-3・ADR-1005 段階2）の部品。
# scripts/run_all_migrations.sh から source する。本番のサーバーで Python に頼らないよう、
# bash・grep・sha256sum だけで書く（設計 docs/handoff/migration-runner-redesign/design.md §5-7）。
#
# 置き場所の決め:
#   MR_ROOT: リポジトリの根（既定は REPO_DIR、無ければ今のフォルダ）。ファイルは MR_ROOT からの相対で読む。
# 関数名は run_ で始めない（本体の TOTAL は ^run_(sql|py) の行を数えるため）。

MR_ROOT="${MR_ROOT:-${REPO_DIR:-.}}"

# mr_py_sql_names <台本>
#   台本の本文から [A-Za-z0-9_./-]*[A-Za-z0-9_-]\.sql に合う文字列を、出てくる順に取る。
#   それぞれの basename が migrations/ に実在する物だけを、同じ名前は最初の1つにまとめて出す
#   （recon-5-0a/p13.md の機械の抽出と同じ決まり）。1行に1名前。
mr_py_sql_names() {
  local script="$1" hit base
  local -A seen=()
  while IFS= read -r hit; do
    base="${hit##*/}"
    [ -n "${base}" ] || continue
    if [ -f "${MR_ROOT}/migrations/${base}" ] && [ -z "${seen[${base}]:-}" ]; then
      seen["${base}"]=1
      printf '%s\n' "${base}"
    fi
  done < <(LC_ALL=C grep -oE '[A-Za-z0-9_./-]*[A-Za-z0-9_-]\.sql' "${MR_ROOT}/${script}")
}

# mr_checksum <種類> <ファイル> [登録の行の残りの引数...]
#   run_sql: ファイルの sha256（16進）。
#   run_py : 「台本の本文」「mr_py_sql_names の順に各 SQL の本文」「登録の行の残りの引数の文字列」を
#            この順につないだ物の sha256（設計 §5-7「run_py の台本が読む SQL」）。
mr_checksum() {
  local kind="$1" file="$2"
  shift 2
  local args="$*" name
  case "${kind}" in
    sql)
      sha256sum "${MR_ROOT}/${file}" | cut -d' ' -f1
      ;;
    py)
      {
        cat "${MR_ROOT}/${file}"
        while IFS= read -r name; do
          [ -n "${name}" ] || continue
          cat "${MR_ROOT}/migrations/${name}"
        done < <(mr_py_sql_names "${file}")
        printf '%s' "${args}"
      } | sha256sum | cut -d' ' -f1
      ;;
    *)
      echo "mr_checksum: unknown kind: ${kind}" >&2
      return 2
      ;;
  esac
}

# mr_targets <本体> [記録の外のファイル...]
#   本体の ^run_(sql|py)[[:space:]] の行を上から読み、記録の外の一覧を除いた
#   「種類<TAB>ファイル<TAB>残りの引数」を出す。同じファイルが2回出たら失敗する（何も出さない）。
mr_targets() {
  local body="$1"
  shift
  local -A outside=() seen=()
  local o line kind rest file extra
  for o in "$@"; do outside["${o}"]=1; done
  local out=""
  while IFS= read -r line; do
    kind="${line#run_}"
    kind="${kind%%[[:space:]]*}"
    rest="${line#run_"${kind}"}"
    rest="${rest#"${rest%%[![:space:]]*}"}"
    file="${rest%%[[:space:]]*}"
    extra="${rest#"${file}"}"
    extra="${extra#"${extra%%[![:space:]]*}"}"
    extra="${extra%"${extra##*[![:space:]]}"}"
    if [ -n "${seen[${file}]:-}" ]; then
      echo "mr_targets: duplicate registration: ${file}" >&2
      return 1
    fi
    seen["${file}"]=1
    [ -z "${outside[${file}]:-}" ] || continue
    out+="${kind}"$'\t'"${file}"$'\t'"${extra}"$'\n'
  done < <(LC_ALL=C grep -E '^run_(sql|py)[[:space:]]' "${body}")
  printf '%s' "${out}"
}
