#!/usr/bin/env bash
# 提出前に、必須チェックと同じ検査（CI と同じ台本）を手元でまとめて流す入口（R4a・第1段）
#
# 使い方:
#   bash scripts/dev/check-before-submit.sh            # 速い組（毎回・約 80 秒）
#   bash scripts/dev/check-before-submit.sh --full     # 重い組（test-guard-evaluations・見本の全件）も流す
#   bash scripts/dev/check-before-submit.sh --list-fixtures   # 今の変更で選ばれる見本の名前だけ表示して終わる
#   bash scripts/dev/check-before-submit.sh --only a,b # 検査の id を絞る（試験と切り分け用）
#
# 終了コード: 0 = 流した検査が全部 ○ / 1 = 1 つでも × / 2 = commit していない変更がある（または origin/main が無い）
#
# 決まり:
#   ・CI と同じ台本を呼ぶ（検査の中身は写さない）。呼び方は各ワークフローの記述に合わせてある
#   ・比べる元は origin/main との分岐点。fetch はしない（使った origin/main の SHA を表示する）
#   ・流さない必須チェックは名前と理由を「CI で確かめる」として全部表示する（黙って通さない）。
#     名前は docs/specs/rule-enforcement/required-checks.txt から読む（台本に名前の一覧は持たない）
#   ・最後の判定は CI。この入口は提出前の補助（手元と CI は python・node の版が違う）
# 設計: docs/handoff/rule-enforcement/design.md の R4 / R4a

set -u

FULL=0
ONLY=""
LIST_FIX=0
while test $# -gt 0; do
  case "$1" in
    --full) FULL=1 ;;
    --list-fixtures) LIST_FIX=1 ;;
    --only) shift; ONLY="${1:-}" ;;
    -h|--help) sed -n 2,14p "$0"; exit 0 ;;
    *) echo "不明な引数: $1" >&2; exit 2 ;;
  esac
  shift
done

cd "$(git rev-parse --show-toplevel)" || exit 2
REQ_FILE="docs/specs/rule-enforcement/required-checks.txt"

# --- commit していない変更があれば止める（見本の runner は commit 済みの HEAD から写しを作るため） ---
if test -n "$(git status --porcelain)"; then
  echo "commit していない変更があります。commit してから流してください（終了コード 2）。"
  git status --short | head -20
  exit 2
fi

MAIN_SHA=$(git rev-parse --verify -q origin/main) || { echo "origin/main が見つかりません（fetch は自動では行いません）。終了コード 2"; exit 2; }
BASE_SHA=$(git merge-base origin/main HEAD) || { echo "origin/main との分岐点が見つかりません。終了コード 2"; exit 2; }
HEAD_SHA=$(git rev-parse HEAD)
CHANGED=$(git diff --name-only "${BASE_SHA}...HEAD")

# --- 変更ファイルから選ぶ見本（case.json の argv にある台本、または見本のフォルダの中） ---
FIX_SHORTS=$(printf '%s\n' "$CHANGED" | python3 -I -c '
import sys, json, glob
changed = set(l.strip() for l in sys.stdin if l.strip())
root = "scripts/tests/rule-fixtures"
out = set()
for cj in glob.glob(root + "/*/*/case.json"):
    short = cj.split("/")[-3]
    try:
        argv = json.load(open(cj, encoding="utf-8")).get("argv", [])
    except Exception:
        continue
    prefix = root + "/" + short + "/"
    if any(a in changed for a in argv if isinstance(a, str)) or any(f.startswith(prefix) for f in changed):
        out.add(short)
print("\n".join(sorted(out)))
')

if test "$LIST_FIX" = "1"; then
  printf '%s\n' "$FIX_SHORTS"
  exit 0
fi

LOGDIR=$(mktemp -d "${TMPDIR:-/tmp}/check-before-submit.XXXXXX")
now() { perl -MTime::HiRes=time -e 'printf "%.2f", time'; }
elapsed() { perl -e 'printf "%.1f", $ARGV[1] - $ARGV[0]' "$1" "$2"; }

echo "== 提出前の検査（check-before-submit）=="
echo "比べる元: origin/main = ${MAIN_SHA}（分岐点 ${BASE_SHA}）"
echo "HEAD: ${HEAD_SHA}"
echo "変更ファイル: $(printf '%s\n' "$CHANGED" | grep -c . ) 件 / ログ置き場: ${LOGDIR}"
echo ""

N=0
R_ID=(); R_LABEL=(); R_REQ=(); R_RC=(); R_SECS=(); R_NOTE=()
T_START=$(now)

record() { # id label req rc secs note
  R_ID[$N]="$1"; R_LABEL[$N]="$2"; R_REQ[$N]="$3"; R_RC[$N]="$4"; R_SECS[$N]="$5"; R_NOTE[$N]="$6"
  N=$((N + 1))
}

selected() { # --only が無ければ全部、あれば id が含まれるものだけ
  if test -z "$ONLY"; then return 0; fi
  case ",$ONLY," in *",$1,"*) return 0 ;; *) return 1 ;; esac
}

# run_check <id> <表示名> <対応する必須名の一部（無ければ -）> <作業フォルダ> <命令...>
run_check() {
  local id="$1" label="$2" req="$3" dir="$4"
  shift 4
  if ! selected "$id"; then
    record "$id" "$label" "$req" skip 0 "--only で選ばれていない"
    return 0
  fi
  local t0 t1 secs rc
  t0=$(now)
  ( cd "$dir" && "$@" ) > "${LOGDIR}/${id}.log" 2>&1
  rc=$?
  t1=$(now)
  secs=$(elapsed "$t0" "$t1")
  record "$id" "$label" "$req" "$rc" "$secs" ""
  if test "$rc" = "0"; then
    printf '  ○ %-48s %6s 秒\n' "$label" "$secs"
  else
    printf '  × %-48s %6s 秒 (終了コード %s)\n' "$label" "$secs" "$rc"
    echo "    --- ${LOGDIR}/${id}.log の末尾 ---"
    tail -n 15 "${LOGDIR}/${id}.log" | sed 's/^/    | /'
  fi
}

skip_check() { # id label req note
  record "$1" "$2" "$3" skip 0 "$4"
  printf '  - %-48s %s\n' "$2" "$4"
}

echo "-- 速い組（毎回）--"
run_check doc-index "check_doc_index --strict" "doc index" . python3 -I scripts/ci/check_doc_index.py --root . --strict
run_check rule-registry "check_rule_registry" "-" . python3 -I scripts/ci/check_rule_registry.py
run_check tenant-lint "lint_tenant_schema (strict)" "tenant schema lint" . python3 scripts/lint_tenant_schema.py --mode strict backend/app/routers/
run_check claude-size "check-claude-size" "line count" frontend node scripts/check-claude-size.js
run_check adr-index "generate-adr-index --check" "ADR index" . node scripts/generate-adr-index.js --check
run_check ui-tests "test-ui-governance" "UI governance" . node scripts/tests/test-ui-governance.js
run_check ui-gate "check-ui-governance" "UI governance" . env BASE_SHA="$BASE_SHA" HEAD_SHA="$HEAD_SHA" node scripts/check-ui-governance.js
run_check dangling "check-dangling-routes" "dangling-route" . env BASE_SHA="$BASE_SHA" HEAD_SHA="$HEAD_SHA" node scripts/check-dangling-routes.js
run_check dangling-tests "test-dangling-routes" "dangling-route" . node scripts/tests/test-dangling-routes.js

# check-lessons-section: SEC6_ADDED が 0 でなければ失敗ではなく注意（ラベルは提出後にしか付けられない）
LESSONS_NOTE=""
if selected lessons; then
  t0=$(now)
  bash scripts/check-lessons-section.sh "$BASE_SHA" > "${LOGDIR}/lessons.log" 2>&1
  rc=$?
  t1=$(now); secs=$(elapsed "$t0" "$t1")
  record lessons "check-lessons-section" "warn-direct-lesson" "$rc" "$secs" ""
  if test "$rc" = "0"; then
    printf '  ○ %-48s %6s 秒\n' "check-lessons-section" "$secs"
    ADDED=$(grep '^SEC6_ADDED=' "${LOGDIR}/lessons.log" | cut -d= -f2)
    if test "${ADDED:-0}" != "0"; then
      LESSONS_NOTE="注意: design-partner.md の教訓ゾーンに ${ADDED} 行の追記があります。PR に lessons-cleanup ラベルが要ります（ラベルは提出後にしか付けられません）"
      echo "    ${LESSONS_NOTE}"
    fi
  else
    printf '  × %-48s %6s 秒 (終了コード %s)\n' "check-lessons-section" "$secs" "$rc"
    tail -n 15 "${LOGDIR}/lessons.log" | sed 's/^/    | /'
  fi
else
  record lessons "check-lessons-section" "warn-direct-lesson" skip 0 "--only で選ばれていない"
fi

run_check migreg-exists "check-migration-registration-exists" "実行テスト（実DB）" . bash scripts/check-migration-registration-exists.sh --mode host --repo-root "$(pwd)"
run_check migreg-tests "test-migration-registration-exists" "実行テスト（実DB）" . node scripts/tests/test-migration-registration-exists.js

# migration-guard.yml のうち、独立した台本ファイルを呼ぶ step だけ（ワークフロー内に直接書かれた grep 等は CI で確かめる）
run_check mg-7 "migration-value-writes diff --check 7" "新 Column" . python3 scripts/check-migration-value-writes.py diff "$BASE_SHA" "$HEAD_SHA" --check 7
run_check mg-8 "migration-value-writes diff --check 8" "新 Column" . python3 scripts/check-migration-value-writes.py diff "$BASE_SHA" "$HEAD_SHA" --check 8
run_check mg-repo "migration-value-writes repo" "新 Column" . python3 scripts/check-migration-value-writes.py repo
run_check mg-vw-tests "test_migration_value_writes" "新 Column" . python3 scripts/tests/test_migration_value_writes.py -v
# 次の 2 つは migration-guard.yml の detect_churn_paths と同じ条件のときだけ流す
if printf '%s\n' "$CHANGED" | grep -qE '^(migrations/|scripts/run_all_migrations\.sh$|scripts/migrate_.*\.py$|scripts/check-migration-column-churn\.js$|scripts/check-migration-duplicate-registration\.sh$|scripts/migration-column-churn-allowlist\.json$)'; then
  run_check mg-churn "check-migration-column-churn" "新 Column" . node scripts/check-migration-column-churn.js
  run_check mg-dupreg "check-migration-duplicate-registration" "新 Column" . bash scripts/check-migration-duplicate-registration.sh
else
  skip_check mg-churn "check-migration-column-churn" "新 Column" "関連パスの変更なし（CI と同じ条件で対象外）"
  skip_check mg-dupreg "check-migration-duplicate-registration" "新 Column" "関連パスの変更なし（CI と同じ条件で対象外）"
fi

run_check heading-dup "check-doc-heading-duplicates" "-" . bash scripts/check-doc-heading-duplicates.sh
run_check test-rule-registry "test_check_rule_registry" "-" . python3 -I scripts/tests/test_check_rule_registry.py

# 違反の見本: 変更が見本の台本・見本のフォルダに当たるときだけ、その見本を --only で流す
echo ""
echo "-- 違反の見本（変更に関係するものだけ）--"
if test -z "$FIX_SHORTS"; then
  echo "  - 変更に関係する見本はありません（全件は --full で流せます）"
else
  for short in $FIX_SHORTS; do
    run_check "fixture-${short}" "run_rule_fixtures --only ${short}" "-" . python3 -I scripts/tests/run_rule_fixtures.py --only "$short"
  done
fi

echo ""
echo "-- 重い組（--full のときだけ）--"
if test "$FULL" = "1"; then
  run_check guard-eval "test-guard-evaluations (node --test)" "-" . node --test scripts/tests/test-guard-evaluations.js
  run_check fixtures-all "run_rule_fixtures（全件）" "-" . python3 -I scripts/tests/run_rule_fixtures.py
else
  skip_check guard-eval "test-guard-evaluations (node --test)" "-" "CI で確かめる（約 120 秒。--full で流せます）"
  skip_check fixtures-all "run_rule_fixtures（全件）" "-" "CI で確かめる（約 375 秒。--full で流せます）"
fi

T_END=$(now)
TOTAL=$(elapsed "$T_START" "$T_END")

# --- 必須チェック 16 件それぞれを「流した」か「CI で確かめる」かで全部表示する ---
reason_for() { # 必須名 → 手元で流さない理由
  case "$1" in
    *pytest*) echo "DB・redis が要る" ;;
    *テナントスキーマ整合性*) echo "DB が要る" ;;
    *Lint*Dark*) echo "npm ci が要り時間がかかる" ;;
    *gitleaks*) echo "履歴の走査は手元の見張りで止まるため、この段では流さない" ;;
    *guard-authoring*) echo "評価本体は GitHub のイベントと権限が要る（台本の試験は --full で流せる）" ;;
    *process-artifacts*) echo "PR 本文が要る。PR 作成時に validate-pr-body.sh が確かめる" ;;
    *API*contract*) echo "uv と npm ci が要る" ;;
    *) echo "手元の入口は未対応" ;;
  esac
}
partial_for() { # 一部だけ流した必須名の注記
  case "$1" in
    *実DB*) echo "（登録ファイルの存在確認だけ。実DBでの実行は CI）" ;;
    *"新 Column"*) echo "（独立した台本の step だけ。ワークフロー内に直接書かれた step は CI）" ;;
    *) echo "" ;;
  esac
}

echo ""
echo "== 必須チェック（${REQ_FILE}）=="
FAILS=0
i=0
while test $i -lt $N; do
  if test "${R_RC[$i]}" != "0" && test "${R_RC[$i]}" != "skip"; then FAILS=$((FAILS + 1)); fi
  i=$((i + 1))
done
REQ_TOTAL=0
while IFS= read -r line || test -n "$line"; do
  case "$line" in ''|'#'*) continue ;; esac
  name="${line%%$'\t'*}"
  REQ_TOTAL=$((REQ_TOTAL + 1))
  ran=0; bad=0
  i=0
  while test $i -lt $N; do
    req="${R_REQ[$i]}"
    if test "$req" != "-" && test -n "$req" && test "${R_RC[$i]}" != "skip"; then
      case "$name" in *"$req"*)
        ran=$((ran + 1))
        if test "${R_RC[$i]}" != "0"; then bad=$((bad + 1)); fi ;;
      esac
    fi
    i=$((i + 1))
  done
  if test $ran -gt 0 && test $bad -gt 0; then
    echo "  × ${name} — 手元で流して落ちた"
  elif test $ran -gt 0; then
    echo "  ○ ${name} — 手元で流した$(partial_for "$name")"
  else
    echo "  - ${name} — CI で確かめる（$(reason_for "$name")）"
  fi
done < "$REQ_FILE"

echo ""
echo "== 流した検査 =="
i=0
while test $i -lt $N; do
  if test "${R_RC[$i]}" = "skip"; then
    printf '  - %-48s 流していない: %s\n' "${R_LABEL[$i]}" "${R_NOTE[$i]}"
  elif test "${R_RC[$i]}" = "0"; then
    printf '  ○ %-48s %6s 秒\n' "${R_LABEL[$i]}" "${R_SECS[$i]}"
  else
    printf '  × %-48s %6s 秒\n' "${R_LABEL[$i]}" "${R_SECS[$i]}"
  fi
  i=$((i + 1))
done
test -n "$LESSONS_NOTE" && echo "$LESSONS_NOTE"

echo ""
echo "== 版の違い（手元と CI）=="
echo "  手元: $(python3 --version 2>&1) / node $(node --version 2>&1)"
echo "  CI  : Python 3.12 / node 22（guard-authoring だけ 24）"
echo "  版が違うので、最後の判定は CI です（この入口は提出前の補助）"
echo ""
echo "合計 ${TOTAL} 秒 / 必須 ${REQ_TOTAL} 件を表示 / 落ちた検査 ${FAILS} 件 / ログ ${LOGDIR}"
if test $FAILS -gt 0; then
  echo "結果: × （終了コード 1）"
  exit 1
fi
echo "結果: ○ 流した検査は全部通りました（終了コード 0）"
exit 0
