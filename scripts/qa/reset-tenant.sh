#!/usr/bin/env bash
# =============================================================================
# ADR-038 / QA Smoke Suite: tenant_006 reset スクリプト
#
# 目的:
#   QA Gate tenant_006 を「known state」に戻す冪等スクリプト。
#   スプリント開始時 / CI 失敗復旧時 / 撮影直前にも実行可能。
#
# 動作:
#   1. flock 排他 (/tmp/qa-tenant-006.lock) で撮影との時間衝突を防止
#   2. Discord webhook で開始/完了通知 (QA_DISCORD_WEBHOOK_URL 未設定なら skip)
#   3. tenant_code='tenant-review' を assert (誤実行ガード — SQL 内でも assert)
#   4. seed-tenant.sql を psql で投入 (TRUNCATE → seed → 行数 assert)
#   5. psql -v で Firebase UID / password hash を seed に注入
#
# 必須環境変数 (CI secrets で渡される):
#   DATABASE_URL                postgresql:// or postgresql+asyncpg:// (asyncpg は剥がす)
#   QA_ADMIN_FIREBASE_UID       admin ユーザーの Firebase UID
#   QA_STAFF_FIREBASE_UID       staff ユーザーの Firebase UID
#   QA_VIEWER_FIREBASE_UID      viewer ユーザーの Firebase UID
#
# 任意環境変数:
#   QA_DISCORD_WEBHOOK_URL      Discord webhook URL (未設定なら通知 skip)
#   QA_LOCK_FILE                flock 用ファイル (default: /tmp/qa-tenant-006.lock)
#   QA_LOCK_TIMEOUT_SEC         flock タイムアウト秒 (default: 600)
#
# 使い方:
#   docker compose exec -T backend \
#       env DATABASE_URL=$DATABASE_URL \
#           QA_ADMIN_FIREBASE_UID=... \
#           QA_STAFF_FIREBASE_UID=... \
#           QA_VIEWER_FIREBASE_UID=... \
#       bash /app/scripts/qa/reset-tenant.sh
#
# 関連:
#   docs/adr/ADR-038-qa-smoke-suite.md
#   scripts/qa/seed-tenant.sql
#   scripts/qa/cleanup-smoke-data.sh
#
# 変更履歴:
#   2026-05-15: ADR-038 初版
#   2026-06-16: ADR-138 に従い password_hash 依存を完全削除
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_SQL="${SCRIPT_DIR}/seed-tenant.sql"

LOCK_FILE="${QA_LOCK_FILE:-/tmp/qa-tenant-006.lock}"
LOCK_TIMEOUT="${QA_LOCK_TIMEOUT_SEC:-600}"

log() {
    echo "[reset-tenant] $(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >&2
}

discord_notify() {
    local content="$1"
    if [[ -z "${QA_DISCORD_WEBHOOK_URL:-}" ]]; then
        return 0
    fi
    # best-effort — Discord 通知失敗で reset 全体を落とさない
    curl -fsS -X POST -H 'Content-Type: application/json' \
        -d "$(printf '{"content":%s}' "$(printf '%s' "$content" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')")" \
        "$QA_DISCORD_WEBHOOK_URL" >/dev/null 2>&1 || \
        log "WARN: Discord notify failed (ignored)"
}

require_env() {
    local var="$1"
    if [[ -z "${!var:-}" ]]; then
        log "FATAL: required env var '${var}' is not set"
        exit 1
    fi
}

# --- 0. 環境変数チェック ---
require_env DATABASE_URL

# DATABASE_URL の asyncpg drivername を psql 互換に戻す (UID 自動取得で先行使用)
PSQL_URL="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"

# Firebase UID 自動取得: env 未設定時は既存 tenant_006.staff から読む (冪等リセット用)
# 初回シード時は secrets で渡す必要あり。2回目以降は DB から自動取得できる。
if [[ -z "${QA_ADMIN_FIREBASE_UID:-}" ]]; then
    log "QA_ADMIN_FIREBASE_UID unset — querying tenant_006.staff (QA-ADMIN-001)..."
    QA_ADMIN_FIREBASE_UID=$(psql "$PSQL_URL" -At -c \
        "SELECT firebase_uid FROM tenant_006.staff WHERE staff_code='QA-ADMIN-001' LIMIT 1;" 2>/dev/null || true)
fi
if [[ -z "${QA_STAFF_FIREBASE_UID:-}" ]]; then
    log "QA_STAFF_FIREBASE_UID unset — querying tenant_006.staff (QA-STAFF-001)..."
    QA_STAFF_FIREBASE_UID=$(psql "$PSQL_URL" -At -c \
        "SELECT firebase_uid FROM tenant_006.staff WHERE staff_code='QA-STAFF-001' LIMIT 1;" 2>/dev/null || true)
fi
if [[ -z "${QA_VIEWER_FIREBASE_UID:-}" ]]; then
    log "QA_VIEWER_FIREBASE_UID unset — querying tenant_006.staff (QA-VIEWER-001)..."
    QA_VIEWER_FIREBASE_UID=$(psql "$PSQL_URL" -At -c \
        "SELECT firebase_uid FROM tenant_006.staff WHERE staff_code='QA-VIEWER-001' LIMIT 1;" 2>/dev/null || true)
fi

require_env QA_ADMIN_FIREBASE_UID
require_env QA_STAFF_FIREBASE_UID
require_env QA_VIEWER_FIREBASE_UID

if [[ ! -f "$SEED_SQL" ]]; then
    log "FATAL: seed SQL not found at $SEED_SQL"
    exit 1
fi

# --- 1. flock 排他取得 ---
exec 9>"$LOCK_FILE"
log "acquiring flock (timeout=${LOCK_TIMEOUT}s, lockfile=$LOCK_FILE)..."
if ! flock -w "$LOCK_TIMEOUT" 9; then
    log "FATAL: flock timeout — 撮影中 or 他 reset 実行中の可能性。$LOCK_FILE を確認"
    exit 2
fi
log "flock acquired (fd=9)"

# --- 2. 開始通知 ---
discord_notify "🟡 [QA-smoke] tenant_006 reset 開始 ($(date -u +%FT%TZ))"

# --- 3. tenant_code assert (psql 経由でも seed-tenant.sql 内でも assert) ---
log "asserting tenant_006 maps to tenant_code=tenant-review..."
ACTUAL_CODE=$(psql "$PSQL_URL" -At -c "SELECT tenant_code FROM public.tenants WHERE id=6;")
if [[ "$ACTUAL_CODE" != "tenant-review" ]]; then
    log "FATAL: tenant_id=6 maps to tenant_code='$ACTUAL_CODE', expected 'tenant-review'"
    discord_notify "🔴 [QA-smoke] reset abort: tenant_code mismatch ('$ACTUAL_CODE')"
    exit 3
fi
log "tenant_code assert OK"

# --- 4. seed SQL 投入 ---
log "applying seed-tenant.sql..."
if ! psql "$PSQL_URL" \
    -v ON_ERROR_STOP=1 \
    -v "qa_admin_firebase_uid=$QA_ADMIN_FIREBASE_UID" \
    -v "qa_staff_firebase_uid=$QA_STAFF_FIREBASE_UID" \
    -v "qa_viewer_firebase_uid=$QA_VIEWER_FIREBASE_UID" \
    -f "$SEED_SQL"; then
    log "FATAL: seed-tenant.sql failed"
    discord_notify "🔴 [QA-smoke] reset FAILED — seed-tenant.sql のエラーを CI ログで確認"
    exit 4
fi

log "reset completed successfully"
discord_notify "🟢 [QA-smoke] tenant_006 reset 完了 ($(date -u +%FT%TZ))"

# flock は exec 9>$LOCK_FILE で開いた fd が exit と共に閉じられる
