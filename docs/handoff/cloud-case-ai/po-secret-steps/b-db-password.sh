#!/usr/bin/env bash
# b-db-password.sh — ai_reader_cloud のパスワードを VPS の上で作り、ai-reader-cloud.env に置く
# 実行: PO が Mac で `bash b-db-password.sh`（パスワードは VPS の上で作り、Mac に戻さない）
# 再実行: 新しい env が無ければ何度でも実行してよい（パスワードは作り直される）。
# 接続確認について: pg_hba はループバック宛の host が trust のため、postgres 容器の中からの
#   TCP 接続では scram の確かめにならない（docs/handoff/ai-readonly-db-path/recon.md:40）。
#   接続確認は「次のデプロイ後に窓口の容器から」行い、この台本では行わない。
# 記録について: 同じ接続で log_statement=none と log_min_error_statement=panic にしてから ALTER ROLE を流す。psql の出力は捨てる（失敗時は「失敗: 4. ...」の 1 行だけ出る）。
set -euo pipefail
umask 077

ssh -i ~/.ssh/manual-only/id_ed25519 -o IdentitiesOnly=yes ubuntu@49.212.137.46 'bash -s' <<'REMOTE'
set -euo pipefail
umask 077

DIR=/home/ubuntu/.config/salesanchor
CUR="$DIR/ai-reader.env"
NEW="$DIR/ai-reader-cloud.env"
step="開始"
tmp=""

on_exit() {
  rc=$?
  unset pw url newurl
  [ -n "$tmp" ] && rm -f "$tmp"
  if [ "$rc" -ne 0 ]; then
    echo "失敗: 「${step}」で止まりました。${NEW} が無ければ、もう一度実行してよい（パスワードは作り直されます）。"
  fi
}
trap on_exit EXIT

step="1. 新しい env の有無と今の env の読み取り"
if [ -e "$NEW" ]; then
  echo "止まりました: ${NEW} は既にあります（上書きしません）。"
  exit 1
fi
if [ ! -r "$CUR" ]; then
  echo "止まりました: ${CUR} が無い、または読めません。"
  exit 1
fi

step="2. 今の env の形の確認"
url="$(cat "$CUR")"
lines="$(grep -c '' "$CUR" || true)"
prefix_ok="×"
case "$url" in
  AI_READER_DATABASE_URL=postgresql://ai_reader:*) prefix_ok="○" ;;
esac
echo "今の env: 行数=${lines} / 先頭が AI_READER_DATABASE_URL=postgresql://ai_reader: ${prefix_ok}（中身は表示しません）"
if [ "$lines" != "1" ] || [ "$prefix_ok" != "○" ]; then
  echo "止まりました: 今の env が想定の形（1 行・AI_READER_DATABASE_URL=postgresql://ai_reader: で始まる）ではありません。"
  exit 1
fi
rest="${url##*@}"
if [ "$rest" = "$url" ] || [ -z "$rest" ]; then
  echo "止まりました: 今の env の URL に @ 以降（host:port/db）が見つかりません。"
  exit 1
fi

step="3. パスワードの生成"
pw="$(openssl rand -hex 32)"

step="4. DB の ai_reader_cloud にパスワードを設定"
printf "SET log_statement = 'none';\nSET log_min_error_statement = 'panic';\nALTER ROLE ai_reader_cloud PASSWORD '%s';\n" "$pw" \
  | docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -q >/dev/null 2>&1

step="5. 新しい env の書き込み"
newurl="AI_READER_DATABASE_URL=postgresql://ai_reader_cloud:${pw}@${rest}"
tmp="$(mktemp "$DIR/.ai-reader-cloud.env.XXXXXX")"
printf '%s\n' "$newurl" > "$tmp"
chmod 600 "$tmp"
mv "$tmp" "$NEW"
tmp=""

step="6. 確かめ"
chk() { if "${@:2}"; then echo "○ $1"; else echo "× $1"; fi; }
is_cloud_line() { case "$(cat "$NEW")" in AI_READER_DATABASE_URL=postgresql://ai_reader_cloud:*) return 0 ;; *) return 1 ;; esac; }
chk "新しい env がある" test -f "$NEW"
chk "権限が 600" test "$(stat -c %a "$NEW")" = "600"
chk "持ち主が ubuntu" test "$(stat -c %U "$NEW")" = "ubuntu"
chk "1 行だけ" test "$(grep -c '' "$NEW")" = "1"
chk "AI_READER_DATABASE_URL=postgresql://ai_reader_cloud: で始まる" is_cloud_line

has_pw="$(printf "SELECT rolpassword IS NOT NULL FROM pg_authid WHERE rolname='ai_reader_cloud';\n" \
  | docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -t -A -q)"
if [ "$has_pw" = "t" ]; then echo "○ ai_reader_cloud にパスワードが設定されている"; else echo "× ai_reader_cloud にパスワードが設定されていない"; fi

echo "接続確認はこの台本では行いません。次のデプロイ後に窓口の容器（ai-reader-cloud-http）から確かめます。"
step="完了"
REMOTE
