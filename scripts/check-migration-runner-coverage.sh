#!/bin/bash
# check-migration-runner-coverage.sh — run_all_migrations.sh 登録漏れの見張り
#
# 目的:
#   - diff モード: PR で追加された migrations/*.sql が run_all_migrations.sh に
#     登録されていなければ CI を赤にする
#   - repo モード: 現行-era の migrations/*.sql を棚卸しし、現状の未登録候補を
#     人間向けに列挙する（report 用）
#
# 注意:
#   - deploy/apply の仕組みは変更しない
#   - *_down.sql は対象外
#   - 088/089 は将来の条件/単位再編に向けた例外として diff モードでは allowlist
#     扱いにする

set -euo pipefail

MODE="diff"
BASE_SHA=""
HEAD_SHA=""
REPO_ROOT=""
MIGRATIONS_SCRIPT="scripts/run_all_migrations.sh"

usage() {
  cat <<'USAGE'
Usage:
  check-migration-runner-coverage.sh --mode diff --base SHA --head SHA [--repo-root PATH]
  check-migration-runner-coverage.sh --mode repo [--repo-root PATH]
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --base)
      BASE_SHA="${2:-}"
      shift 2
      ;;
    --head)
      HEAD_SHA="${2:-}"
      shift 2
      ;;
    --repo-root)
      REPO_ROOT="${2:-}"
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

if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
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

registered_sqls="$(
  grep -E '^run_sql[[:space:]]+' "$MIGRATIONS_PATH" \
    | awk '{print $2}' \
    | sed 's#^\./##' \
    | sort -u
)"

allowlist_reason() {
  case "$1" in
    088_standardize_unit_values.sql)
      cat <<'EOF'
allowlisted: unit は現行 DB では空欄で、段階2の梱包/単位再編で扱うため
EOF
      ;;
    089_standardize_condition_values.sql)
      cat <<'EOF'
allowlisted: condition は段階2で軸列置換へ進むため、旧 16 値 CHECK を runner で強制しない
EOF
      ;;
    *)
      return 1
      ;;
  esac
}

is_current_era_sql() {
  case "$1" in
    080_*.sql|08[1-9]_*.sql|09[0-9]_*.sql|100_*.sql|202606[0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_*.sql)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_registered() {
  local fname="$1"
  grep -Fxq "migrations/$fname" <<<"$registered_sqls"
}

if [ "$MODE" = "repo" ]; then
  missing=()
  checked=0
  while IFS= read -r path; do
    [ -z "$path" ] && continue
    fname="$(basename "$path")"
    if ! is_current_era_sql "$fname"; then
      continue
    fi
    checked=$((checked + 1))
    if ! is_registered "$fname"; then
      missing+=("$path")
    fi
  done < <(find "$REPO_ROOT/migrations" -maxdepth 1 -type f -name '*.sql' ! -name '*_down.sql' | sort)

  echo "checked current-era sql files: $checked"
  if [ "${#missing[@]}" -eq 0 ]; then
    echo "✅ repo audit OK: no missing current-era registrations"
    exit 0
  fi

  echo "❌ repo audit found missing current-era registrations"
  for path in "${missing[@]}"; do
    echo " - $path"
  done
  exit 1
fi

if [ -z "$BASE_SHA" ] || [ -z "$HEAD_SHA" ]; then
  echo "❌ --base and --head are required in diff mode" >&2
  usage >&2
  exit 1
fi

mapfile -t added_sqls < <(
  git diff --name-only --diff-filter=A "$BASE_SHA" "$HEAD_SHA" -- migrations \
    | grep -E '^migrations/.*\.sql$' \
    | grep -v '_down\.sql$' \
    | sort
)

checked=0
missing=()

for path in "${added_sqls[@]}"; do
  [ -z "$path" ] && continue
  fname="$(basename "$path")"
  if ! is_current_era_sql "$fname"; then
    continue
  fi
  checked=$((checked + 1))
  if allowlist_output="$(allowlist_reason "$fname" 2>/dev/null)"; then
    echo "🟡 $fname — $allowlist_output"
    continue
  fi
  if is_registered "$fname"; then
    echo "✅ $fname — run_all_migrations.sh 登録済み"
  else
    missing+=("$path")
  fi
done

if [ "$checked" -eq 0 ]; then
  echo "✅ no current-era migrations added in this diff"
  exit 0
fi

if [ "${#missing[@]}" -eq 0 ]; then
  echo "✅ migration runner coverage OK: ${checked} file(s) checked"
  exit 0
fi

echo "❌ migration runner coverage failed"
for path in "${missing[@]}"; do
  echo " - $path"
done
echo ""
echo "Add each missing file to scripts/run_all_migrations.sh with a run_sql line."
exit 1
