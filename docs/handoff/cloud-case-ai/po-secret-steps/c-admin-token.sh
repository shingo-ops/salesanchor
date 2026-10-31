#!/usr/bin/env bash
# c-admin-token.sh — CASE_ADMIN_TOKEN（管理の口の鍵）を作り、GitHub secret と Mac の Keychain に置く
# 実行: PO が Mac で `bash c-admin-token.sh`（値は画面・ファイル・引数に出さない）
# 途中で止まったとき: GitHub secret だけできて Keychain が×なら、README-stage2.md の「途中で止まったとき」に従う（段1の README のコマンドは使わない）。
set -euo pipefail
umask 077

REPO="shingo-ops/salesanchor"
NAME="CASE_ADMIN_TOKEN"
KC_SERVICE="salesanchor-case-admin-token"
KC_AGENT="salesanchor-case-agent-token"

if ! gh auth status >/dev/null 2>&1; then
  echo "止まりました: gh auth status が通りません。先に gh auth login をしてください。"
  exit 1
fi

if ! list="$(gh secret list -R "$REPO")"; then
  echo "止まりました: GitHub の secret 一覧を読めません"
  exit 1
fi
names="$(printf '%s\n' "$list" | awk '{print $1}' || true)"
case "
${names}
" in
  *"
${NAME}
"*)
    echo "止まりました: GitHub secret ${NAME} は既にあります（上書きしません）。"
    exit 1
    ;;
esac

if security find-generic-password -s "$KC_SERVICE" >/dev/null 2>&1; then
  echo "止まりました: Keychain に ${KC_SERVICE} の項目が既にあります（上書きしません）。"
  exit 1
fi

# 確かめ（○/×。値は出さない）。trap EXIT からも呼ぶので、中の失敗は || true で守る。
show_status() {
  local slist snames
  slist="$(gh secret list -R "$REPO" 2>/dev/null || true)"
  snames="$(printf '%s\n' "$slist" | awk '{print $1}' || true)"
  case "
${snames}
" in
    *"
${NAME}
"*) echo "○ GitHub secret ${NAME} があります" ;;
    *) echo "× GitHub secret ${NAME} が見つかりません" ;;
  esac
  if security find-generic-password -s "$KC_SERVICE" >/dev/null 2>&1; then
    echo "○ Keychain に ${KC_SERVICE} の項目があります"
  else
    echo "× Keychain に ${KC_SERVICE} の項目がありません"
  fi
  return 0
}

step="鍵の生成"
on_exit() {
  local rc=$?
  trap - EXIT
  unset v agent
  if [ "$rc" -ne 0 ]; then
    echo "失敗: 「${step}」"
  fi
  show_status || true
}
trap on_exit EXIT

v="$(openssl rand -hex 32)"

# 段2の作業指示書 §4: CASE_AGENT_TOKEN と同じ値にしない（段1の控えの Keychain と比べる。値は出さない）
step="相談係の鍵と違う値かの確かめ"
agent="$(security find-generic-password -s "$KC_AGENT" -w 2>/dev/null || true)"
if [ -z "$agent" ]; then
  echo "止まりました: Keychain に ${KC_AGENT}（段1の相談係の鍵の控え）が読めません。比べられないので登録しません。"
  exit 1
fi
if [ "$agent" = "$v" ]; then
  echo "止まりました: 作った値が相談係の鍵と同じでした。もう一度実行してください。"
  exit 1
fi
unset agent
echo "○ 相談係の鍵とは違う値です（値は表示しません）"

step="GitHub secret への登録"
printf '%s' "$v" | gh secret set "$NAME" -R "$REPO"

step="Keychain への登録"
printf 'add-generic-password -s %s -a case-admin -w %s\n' "$KC_SERVICE" "$v" | security -i >/dev/null 2>&1

unset v

step="確かめ"
# 確かめの表示は終了時（trap）の show_status が行う。
