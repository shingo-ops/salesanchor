#!/bin/bash
# テナント物理削除前バックアップスクリプト
# 物理削除（DROP SCHEMA CASCADE）を実行する前に対象テナントのスキーマをダンプする。
#
# 使い方:
#   bash scripts/backup_tenant_before_drop.sh <tenant_id>
#   例: bash scripts/backup_tenant_before_drop.sh 3
#
# 出力先: /home/ubuntu/backups/tenant_drop/<timestamp>_tenant_NNN.sql
# 環境変数 DATABASE_URL（postgresql+asyncpg://...）または PG_DUMP_DATABASE_URL（libpq形式）を参照。

set -euo pipefail

TENANT_ID="${1:-}"
if [[ -z "${TENANT_ID}" ]]; then
    echo "Usage: $0 <tenant_id>" >&2
    exit 1
fi

# tenant_id が整数か確認
if ! [[ "${TENANT_ID}" =~ ^[0-9]+$ ]]; then
    echo "ERROR: tenant_id must be a positive integer" >&2
    exit 1
fi

SCHEMA_NAME="$(printf 'tenant_%03d' "${TENANT_ID}")"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/home/ubuntu/backups/tenant_drop"
OUTPUT_FILE="${BACKUP_DIR}/${TIMESTAMP}_${SCHEMA_NAME}.sql"

mkdir -p "${BACKUP_DIR}"

# .env から DATABASE_URL を読み込む（なければ PG_DUMP_DATABASE_URL を直接使用）
ENV_FILE="$(dirname "$0")/../.env"
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
fi

# asyncpg URL（postgresql+asyncpg://...）を libpq 形式（postgresql://...）に変換
if [[ -n "${PG_DUMP_DATABASE_URL:-}" ]]; then
    RAW_URL="${PG_DUMP_DATABASE_URL}"
elif [[ -n "${DATABASE_URL:-}" ]]; then
    RAW_URL="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"
else
    echo "ERROR: DATABASE_URL または PG_DUMP_DATABASE_URL が設定されていません" >&2
    exit 1
fi

echo "バックアップ開始: schema=${SCHEMA_NAME}, 出力先=${OUTPUT_FILE}"

pg_dump \
    --schema="${SCHEMA_NAME}" \
    --no-owner \
    --no-acl \
    "${RAW_URL}" \
    > "${OUTPUT_FILE}"

echo "バックアップ完了: ${OUTPUT_FILE}"
echo "ファイルサイズ: $(du -sh "${OUTPUT_FILE}" | cut -f1)"
