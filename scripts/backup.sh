#!/bin/bash
# PostgreSQL 日次バックアップスクリプト
# cronで毎日深夜3:00に実行: 0 3 * * * /home/ubuntu/salesanchor/scripts/backup.sh
#
# 使い方:
#   手動実行: bash /home/ubuntu/salesanchor/scripts/backup.sh
#   リストア: bash /home/ubuntu/salesanchor/scripts/restore.sh <バックアップファイル>
#
# 本番環境:
#   DB_USER=jarvis, DB_NAME=jarvis_db (.envから読み込み)

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/backups/postgres"
COMPOSE_FILE="/home/ubuntu/salesanchor/docker-compose.yml"
DB_USER="${POSTGRES_USER:-jarvis}"
DB_NAME="${POSTGRES_DB:-jarvis_db}"
RETENTION_DAYS=30
BACKUP_PREFIX="salesanchor_db"

mkdir -p "${BACKUP_DIR}"

BACKUP_FILE="${BACKUP_DIR}/${BACKUP_PREFIX}_${DATE}.sql.gz"

# PostgreSQLのフルバックアップ（圧縮）
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump -U "${DB_USER}" "${DB_NAME}" \
  | gzip > "${BACKUP_FILE}"

# ファイルの権限を制限（所有者のみ読み書き可能）
chmod 600 "${BACKUP_FILE}"

# 保持期間を超えたバックアップを自動削除
# 注: 旧名 jarvis_db_* と新名 salesanchor_db_* の両方を対象にする（移行期間中）
find "${BACKUP_DIR}" -name 'salesanchor_db_*.sql.gz' -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name 'jarvis_db_*.sql.gz' -mtime +${RETENTION_DAYS} -delete

# 件数ベースの保持（2026-10-02 prod1 ディスクフル事故の再発防止）
# 日次cron(3:00) + デプロイ前バックアップが重なると30日保持だけでは
# 20〜34件/日生成されてディスクを食い尽くすため、新しい10件のみ残す。
# `ls | head` はパイプ (SIGPIPE) で set -o pipefail 下で誤判定するため、
# process substitution + mapfile で読み込む（パイプを経由しない）。
KEEP_COUNT=10
mapfile -t BACKUP_FILES < <(ls -1t "${BACKUP_DIR}"/salesanchor_db_*.sql.gz 2>/dev/null || true)
if [ "${#BACKUP_FILES[@]}" -gt "${KEEP_COUNT}" ]; then
  REMOVED_COUNT=0
  for ((i = KEEP_COUNT; i < ${#BACKUP_FILES[@]}; i++)); do
    rm -f "${BACKUP_FILES[$i]}"
    REMOVED_COUNT=$((REMOVED_COUNT + 1))
  done
  echo "[$(date)] Count-based retention: removed ${REMOVED_COUNT} old backup(s), kept newest ${KEEP_COUNT}" \
    >> "${BACKUP_DIR}/backup.log"
fi

# ログに記録
FILESIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup completed: ${BACKUP_PREFIX}_${DATE}.sql.gz (${FILESIZE})" \
  >> "${BACKUP_DIR}/backup.log"
