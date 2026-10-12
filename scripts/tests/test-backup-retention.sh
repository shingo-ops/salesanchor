#!/bin/bash
# scripts/backup.sh の件数ベース保持ロジック と scripts/backup_to_s3.sh の
# 最新ファイル選定ロジックを、set -euo pipefail 下で検証するテスト。
# 2026-10-02 prod1 ディスクフル事故（多数バックアップ残留でS3転送が
# SIGPIPE/pipefailで失敗）の再発防止確認用。
#
# 実行: bash scripts/tests/test-backup-retention.sh

set -euo pipefail

TMPDIR_TEST=$(mktemp -d)
trap 'rm -rf "${TMPDIR_TEST}"' EXIT

FAIL=0

# --- テスト1: 件数ベース保持ロジック（backup.sh と同じロジック） ---
echo "=== テスト1: 15件作成 → 新しい10件のみ残ることを確認 ==="
for i in $(seq 1 15); do
  TS=$(printf "202610%02d_%02d0000" "$((i % 28 + 1))" "$i")
  touch "${TMPDIR_TEST}/salesanchor_db_${TS}.sql.gz"
  sleep 0.01
done

KEEP_COUNT=10
mapfile -t BACKUP_FILES < <(ls -1t "${TMPDIR_TEST}"/salesanchor_db_*.sql.gz 2>/dev/null || true)
if [ "${#BACKUP_FILES[@]}" -gt "${KEEP_COUNT}" ]; then
  for ((i = KEEP_COUNT; i < ${#BACKUP_FILES[@]}; i++)); do
    rm -f "${BACKUP_FILES[$i]}"
  done
fi

REMAINING=$(ls -1 "${TMPDIR_TEST}"/salesanchor_db_*.sql.gz 2>/dev/null | wc -l | tr -d '[:space:]')
if [ "${REMAINING}" -eq "${KEEP_COUNT}" ]; then
  echo "PASS: ${REMAINING}件残存（期待値 ${KEEP_COUNT}）"
else
  echo "FAIL: ${REMAINING}件残存（期待値 ${KEEP_COUNT}）"
  FAIL=1
fi

# --- テスト2: 0件・10件以下では削除しない ---
echo "=== テスト2: 5件のみ → 削除されないことを確認 ==="
TMPDIR_TEST2=$(mktemp -d)
for i in $(seq 1 5); do
  touch "${TMPDIR_TEST2}/salesanchor_db_2026100${i}_000000.sql.gz"
done
mapfile -t BACKUP_FILES2 < <(ls -1t "${TMPDIR_TEST2}"/salesanchor_db_*.sql.gz 2>/dev/null || true)
if [ "${#BACKUP_FILES2[@]}" -gt "${KEEP_COUNT}" ]; then
  for ((i = KEEP_COUNT; i < ${#BACKUP_FILES2[@]}; i++)); do
    rm -f "${BACKUP_FILES2[$i]}"
  done
fi
REMAINING2=$(ls -1 "${TMPDIR_TEST2}"/salesanchor_db_*.sql.gz 2>/dev/null | wc -l | tr -d '[:space:]')
rm -rf "${TMPDIR_TEST2}"
if [ "${REMAINING2}" -eq 5 ]; then
  echo "PASS: ${REMAINING2}件残存（5件のまま・削除なし）"
else
  echo "FAIL: ${REMAINING2}件残存（期待値 5）"
  FAIL=1
fi

# --- テスト3: S3アップロード対象選定ロジック（awk版）が多数ファイルでも
#     SIGPIPEせず50回連続成功することを確認（backup_to_s3.sh 修正版） ---
echo "=== テスト3: 50回の最新ファイル選定を set -o pipefail 下で実行 ==="
SUCCESS=0
TOTAL=50
for _ in $(seq 1 "${TOTAL}"); do
  LS_ERR_LOG=$(mktemp)
  set +e
  LATEST=$(ls -1t "${TMPDIR_TEST}"/salesanchor_db_*.sql.gz 2>"${LS_ERR_LOG}" | awk 'NR==1')
  RC=$?
  set -e
  rm -f "${LS_ERR_LOG}"
  if [ "${RC}" -eq 0 ] && [ -n "${LATEST}" ]; then
    SUCCESS=$((SUCCESS + 1))
  fi
done
echo "結果: ${SUCCESS}/${TOTAL} 回成功"
if [ "${SUCCESS}" -eq "${TOTAL}" ]; then
  echo "PASS: 50/50 成功"
else
  echo "FAIL: ${SUCCESS}/${TOTAL}（期待値 50/50）"
  FAIL=1
fi

if [ "${FAIL}" -eq 0 ]; then
  echo "=== 全テスト PASS ==="
  exit 0
else
  echo "=== テスト失敗あり ==="
  exit 1
fi
