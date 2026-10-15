#!/bin/bash
# scripts/backup.sh と scripts/backup_to_s3.sh の write_success_timestamp 関数を試す。
# 関数は書き写さず、2 本のスクリプトから取り出して読み込む（スクリプトの関数そのものを試す）。
# ADR-1012 段階1 便6。bash 3.2（macOS）で動くこと。
#
# 実行: bash scripts/tests/test-backup-timestamp.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "${TMPDIR_TEST}"' EXIT

FAIL=0

check() {
  # check <説明> <終了コード> : 0 なら PASS
  if [ "$2" -eq 0 ]; then
    echo "PASS: $1"
  else
    echo "FAIL: $1"
    FAIL=1
  fi
}

run_for() {
  local name="$1" metric="$2" prom="$3"
  local script="${SCRIPTS_DIR}/${name}"
  local fn
  fn=$(sed -n '/^write_success_timestamp() {$/,/^}$/p' "${script}")

  echo "=== ${name} ==="

  # 3. 取り出せた
  local lines
  lines=$(printf '%s\n' "${fn}" | grep -c . || true)
  [ "${lines}" -gt 0 ] && r=0 || r=1; check "${name}: 関数を取り出せた（${lines} 行）" $r

  # 1. 書ける
  local d="${TMPDIR_TEST}/${name}.ok"
  mkdir -p "${d}/bk"
  (
    TEXTFILE_DIR="${d}/tf"
    BACKUP_DIR="${d}/bk"
    eval "${fn}"
    write_success_timestamp
  )
  local f="${d}/tf/${prom}"
  [ -f "${f}" ] && r=0 || r=1; check "${name}: ${prom} ができた" $r
  local line3 key val now diff
  line3=$(sed -n 3p "${f}")
  key=${line3%% *}
  val=${line3#* }
  [ "${key}" = "${metric}" ] && r=0 || r=1; check "${name}: 3 行目の指標名が ${metric}" $r
  case "${val}" in ''|*[!0-9]*) check "${name}: 値が数字" 1 ;; *) check "${name}: 値が数字" 0 ;; esac
  now=$(date +%s)
  diff=$(( now - val ))
  [ "${diff}" -ge -1 ] && [ "${diff}" -le 5 ] && r=0 || r=1; check "${name}: 値が今との差 5 秒以内（差 ${diff}）" $r
  [ "$(ls -l "${f}" | cut -c1-10)" = "-rw-r--r--" ] && r=0 || r=1; check "${name}: 権限が 644" $r
  local leftover
  leftover=$(ls -a "${d}/tf" | grep -c '^\.backup_' || true)
  [ "${leftover}" -eq 0 ] && r=0 || r=1; check "${name}: 一時ファイルが残っていない" $r

  # 2. 書けない（普通のファイルの下のパス → mkdir が必ず失敗）
  local d2="${TMPDIR_TEST}/${name}.ng"
  mkdir -p "${d2}/bk"
  : > "${d2}/plainfile"
  local out rc
  rc=0
  out=$(
    set -euo pipefail
    trap 'echo TRAPPED' ERR
    TEXTFILE_DIR="${d2}/plainfile/sub"
    BACKUP_DIR="${d2}/bk"
    eval "${fn}"
    write_success_timestamp || true
    echo AFTER
  ) || rc=$?
  [ "${rc}" -eq 0 ] && r=0 || r=1; check "${name}: 書けないときもサブシェルの終了コードが 0" $r
  case "${out}" in *AFTER*) check "${name}: 書けないときも後ろの行まで進む" 0 ;; *) check "${name}: 書けないときも後ろの行まで進む" 1 ;; esac
  case "${out}" in *TRAPPED*) check "${name}: ERR の trap に届かない" 1 ;; *) check "${name}: ERR の trap に届かない" 0 ;; esac

  # 2b. 関数単体が || true 無しで 0 を返す
  rc=0
  (
    TEXTFILE_DIR="${d2}/plainfile/sub"
    BACKUP_DIR="${d2}/bk"
    eval "${fn}"
    rc=0
    write_success_timestamp >/dev/null || rc=$?
    exit "${rc}"
  ) || rc=$?
  [ "${rc}" -eq 0 ] && r=0 || r=1; check "${name}: 書けないとき関数自身が 0 を返す（|| true 無し）" $r
}

run_for backup.sh backup_local_last_success_timestamp backup_local.prom
run_for backup_to_s3.sh backup_s3_last_success_timestamp backup_s3.prom

if [ "${FAIL}" -ne 0 ]; then
  echo "FAILED"
  exit 1
fi
echo "ALL PASSED"
