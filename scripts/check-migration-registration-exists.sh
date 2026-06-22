#!/bin/bash
# check-migration-registration-exists.sh — run_all_migrations.sh の登録先ファイル実在点検
#
# 目的:
#   - run_all_migrations.sh に列挙された run_py / run_sql の参照先が実在するかを全件確認する
#   - 欠品は 1件ずつ集めてまとめて報告し、最初の1件で止めない
#   - CI と deploy 前 preflight の両方で同じ SSoT を使う
#
# 使い方:
#   bash scripts/check-migration-registration-exists.sh --mode host --repo-root "$GITHUB_WORKSPACE"
#   bash scripts/check-migration-registration-exists.sh --mode container --repo-root "$REPO_DIR" --backend-container astro-webapp-backend-1

set -euo pipefail

MODE=""
REPO_ROOT=""
BACKEND_CONTAINER=""
MIGRATIONS_SCRIPT="scripts/run_all_migrations.sh"

usage() {
  cat <<'USAGE'
Usage:
  check-migration-registration-exists.sh --mode host --repo-root PATH [--migrations-script PATH]
  check-migration-registration-exists.sh --mode container --repo-root PATH --backend-container NAME [--migrations-script PATH]
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --repo-root)
      REPO_ROOT="${2:-}"
      shift 2
      ;;
    --backend-container)
      BACKEND_CONTAINER="${2:-}"
      shift 2
      ;;
    --migrations-script)
      MIGRATIONS_SCRIPT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "❌ unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ -z "$MODE" ] || [ -z "$REPO_ROOT" ]; then
  usage >&2
  exit 1
fi

if [ "$MODE" != "host" ] && [ "$MODE" != "container" ]; then
  echo "❌ --mode must be host or container" >&2
  exit 1
fi

if [ "$MODE" = "container" ] && [ -z "$BACKEND_CONTAINER" ]; then
  echo "❌ --backend-container is required in container mode" >&2
  exit 1
fi

if [[ "$MIGRATIONS_SCRIPT" = /* ]]; then
  MIGRATIONS_PATH="$MIGRATIONS_SCRIPT"
else
  MIGRATIONS_PATH="${REPO_ROOT}/${MIGRATIONS_SCRIPT}"
fi

if [ ! -f "$MIGRATIONS_PATH" ]; then
  echo "❌ registration source not found: $MIGRATIONS_PATH" >&2
  exit 1
fi

missing=()
checked=0

while IFS=$'\t' read -r kind path; do
  [ -z "${kind:-}" ] && continue
  [ -z "${path:-}" ] && continue
  checked=$((checked + 1))

  case "$kind" in
    run_sql)
      target="${REPO_ROOT}/${path}"
      if [ ! -f "$target" ]; then
        missing+=("$kind $target")
      fi
      ;;
    run_py)
      target="${REPO_ROOT}/${path}"
      if [ "$MODE" = "container" ]; then
        if ! docker exec "$BACKEND_CONTAINER" test -f "/app/${path}"; then
          missing+=("$kind /app/${path}")
        fi
      else
        if [ ! -f "$target" ]; then
          missing+=("$kind $target")
        fi
      fi
      ;;
    *)
      echo "❌ unexpected registration kind: $kind" >&2
      exit 1
      ;;
  esac
done < <(grep -E '^run_(sql|py)[[:space:]]' "$MIGRATIONS_PATH" | awk '{print $1 "\t" $2}')

if [ "$checked" -eq 0 ]; then
  echo "❌ no migration registrations found in $MIGRATIONS_PATH" >&2
  exit 1
fi

if [ "${#missing[@]}" -ne 0 ]; then
  echo "❌ MIGRATION REGISTRATION EXISTENCE CHECK FAILED"
  printf ' - %s\n' "${missing[@]}"
  exit 1
fi

echo "✅ preflight OK: ${checked} files verified"
