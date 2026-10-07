#!/usr/bin/env bash
# =============================================================
# B-8: S3遠隔バックアップスクリプト
#
# 目的:
#   PostgreSQLバックアップをAWS S3に転送する。
#   VPS障害時の復旧手段として、3-2-1ルールに対応する。
#   （3コピー、2種類の媒体、1つはオフサイト）
#
# 使い方:
#   既存のbackup.shの後に実行する。
#
# cron登録（毎日 3:30 = backup.sh完了後）:
#   30 3 * * * TZ=Asia/Tokyo /path/to/scripts/backup_to_s3.sh >> /var/log/s3_backup.log 2>&1
#
# 前提:
#   - AWS CLI v2 がインストール済み
#   - IAMユーザーに以下の権限が必要:
#       s3:PutObject, s3:GetObject, s3:DeleteObject, s3:ListBucket,
#       s3:GetObjectAttributes, s3:RestoreObject
#   - 環境変数 or ~/.aws/credentials に認証情報を設定済み
#
# Glacier月次アーカイブからの復元手順（3〜5時間かかります）:
#   1. 復元リクエスト:
#      aws s3api restore-object --bucket salesanchor-backups \
#        --key "monthly-archives/2026-01/salesanchor_db_20260101_030000.sql.gz" \
#        --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Standard"}}'
#   2. 復元完了確認（3〜5時間後）:
#      aws s3api head-object --bucket salesanchor-backups \
#        --key "monthly-archives/2026-01/salesanchor_db_20260101_030000.sql.gz"
#      → "Restore" フィールドに ongoing-request="false" と表示されれば完了
#   3. ダウンロード:
#      aws s3 cp "s3://salesanchor-backups/monthly-archives/2026-01/..." /tmp/
#   4. リストア: bash restore.sh /tmp/salesanchor_db_20260101_030000.sql.gz
#
# アーカイブ一覧確認:
#   aws s3 ls "s3://salesanchor-backups/monthly-archives/" --recursive --human-readable
# =============================================================

set -euo pipefail
export TZ=Asia/Tokyo

REPO_DIR="${REPO_DIR:-/home/ubuntu/salesanchor}"

# AWS CLI v2 がホームディレクトリインストールの場合に PATH を補完（cron環境対応）
export PATH="/home/ubuntu/.local/bin:${PATH}"

# .env を読み込み（DISCORD_WEBHOOK_OPS 等を環境変数に反映）
if [ -f "${REPO_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_DIR}/.env"
  set +a
fi

# 失敗時にDiscord通知（DISCORD_WEBHOOK_OPS が設定されている場合のみ）
notify_failure() {
  if [ -z "${DISCORD_WEBHOOK_OPS:-}" ]; then
    return 0
  fi
  local when
  when=$(date +'%Y-%m-%d %H:%M')
  local body
  body=$(printf '{"content":"[ALERT] S3バックアップ失敗: %s"}' "${when}")
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$DISCORD_WEBHOOK_OPS" \
    -H "Content-Type: application/json" \
    -d "${body}" 2>/dev/null || echo "000")
  echo "  Discord通知の応答コード: ${code}"
}

trap 'notify_failure' ERR

# --- 設定 ---
S3_BUCKET="${S3_BACKUP_BUCKET:-salesanchor-backups}"
S3_PREFIX="postgres-backups"
LOCAL_BACKUP_DIR="/home/ubuntu/backups/postgres"
RETENTION_DAYS=90  # S3上の保持日数（monthly-archives/ は対象外）

echo "=== S3バックアップ転送開始: $(date) ==="

# 1. 最新のバックアップファイルを特定
# 注: 2026-10-02 事故以降、ローカルに salesanchor_db_*.sql.gz が多数(100+)
# 残っていると `ls | head -1` が SIGPIPE (head が最初の1行だけ読んで
# パイプを閉じる) を受けて ls が非0終了し、set -o pipefail 下で ERR trap に
# 飛んで S3 転送が丸ごとスキップされるバグがあった
# （ローカル再現: 10件で0/50失敗、156件で48/50失敗）。
# awk は標準入力を最後まで読み切るため ls が SIGPIPE を受けない。
# また対象を salesanchor_db_*.sql.gz に限定し、tenant_* 等の無関係ファイルを除外する。
LS_ERR_LOG=$(mktemp)
LATEST_BACKUP=$(ls -1t "$LOCAL_BACKUP_DIR"/salesanchor_db_*.sql.gz 2>"${LS_ERR_LOG}" | awk 'NR==1')
if [ -s "${LS_ERR_LOG}" ]; then
  echo "WARN: ls でエラー: $(cat "${LS_ERR_LOG}")"
fi
rm -f "${LS_ERR_LOG}"

if [ -z "$LATEST_BACKUP" ]; then
  echo "ERROR: バックアップファイルが見つかりません: ${LOCAL_BACKUP_DIR}"
  exit 1
fi

FILENAME=$(basename "$LATEST_BACKUP")
echo "  転送対象: ${FILENAME}"

# 2. S3に転送
echo "  S3にアップロード中..."
aws s3 cp "$LATEST_BACKUP" "s3://${S3_BUCKET}/${S3_PREFIX}/${FILENAME}" \
  --storage-class STANDARD_IA \
  --only-show-errors

# 3. アップロード検証
S3_SIZE=$(aws s3api head-object --bucket "$S3_BUCKET" --key "${S3_PREFIX}/${FILENAME}" --query ContentLength --output text 2>/dev/null)
LOCAL_SIZE=$(stat -c%s "$LATEST_BACKUP" 2>/dev/null || stat -f%z "$LATEST_BACKUP")

if [ "$S3_SIZE" = "$LOCAL_SIZE" ]; then
  echo "  OK: サイズ一致（${LOCAL_SIZE} bytes）"
else
  echo "  ERROR: サイズ不一致 local=${LOCAL_SIZE} s3=${S3_SIZE}"
  exit 1
fi

# 4. 古いS3オブジェクトの削除（90日以上前）
# 注: monthly-archives/ は別プレフィックスのため、このステップの影響なし（永久保存）
echo "  古いバックアップを削除中（${RETENTION_DAYS}日以上前）..."
CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)

aws s3api list-objects-v2 \
  --bucket "$S3_BUCKET" \
  --prefix "${S3_PREFIX}/" \
  --query "Contents[?LastModified<='${CUTOFF_DATE}'].Key" \
  --output text 2>/dev/null | while read -r KEY; do
    [ "$KEY" = "None" ] && continue
    [ -z "$KEY" ] && continue
    echo "    削除: ${KEY}"
    aws s3api delete-object --bucket "$S3_BUCKET" --key "$KEY"
done

# 5. 月次アーカイブ（毎月1日のバックアップをGlacierに永久保存）
if [ "$(date +%d)" = "01" ]; then
  MONTHLY_KEY="monthly-archives/$(date +%Y-%m)/${FILENAME}"
  echo "  月次アーカイブをGlacierにアップロード中..."
  aws s3 cp "$LATEST_BACKUP" "s3://${S3_BUCKET}/${MONTHLY_KEY}" \
    --storage-class GLACIER \
    --only-show-errors

  # アップロード検証（LOCAL_SIZEはステップ3で取得済み）
  GLACIER_SIZE=$(aws s3api head-object \
    --bucket "$S3_BUCKET" \
    --key "$MONTHLY_KEY" \
    --query ContentLength --output text 2>/dev/null)
  if [ "$GLACIER_SIZE" = "$LOCAL_SIZE" ]; then
    echo "  月次アーカイブ完了（検証OK）: ${MONTHLY_KEY}"
  else
    echo "  ERROR: 月次アーカイブのサイズ不一致 local=${LOCAL_SIZE} glacier=${GLACIER_SIZE}"
    exit 1
  fi
fi

echo "=== S3バックアップ転送完了: $(date) ==="
