#!/usr/bin/env bash
# nginx-case-api-guard.sh — case-api の入口（ADR-1052 段2）の守りを、起動した本物の nginx に当てる台本
#
# 使い方（.github/workflows/nginx-config-check.yml が呼ぶ。手元でも同じに動く）:
#   nginx-case-api-guard.sh prepare <nginx.conf> <出力先>   nginx.conf が読む証明書の名前ごとに自己署名の証明書と、空の取り付け物を作る
#   nginx-case-api-guard.sh sni-echo-conf <出力先>          受けた SNI をそのまま返す試験専用の nginx の設定を作る（本番の設定とは別）
#   nginx-case-api-guard.sh sni-check <host:port>           試験専用の nginx に末尾の点つきの SNI を送り、届いた名前に点が残ることを確かめる
#   nginx-case-api-guard.sh guard <ip>                      守りの台本。ip は 127.0.0.1 か ::1。1 つでも期待と違えば exit 1
#   nginx-case-api-guard.sh snapshot <ip>                   5 つの名前の「/」の応答コードと Location を「名前 コード Location」で出す
#
# 外部へは何も送らない（接続先は引数の ip の 443 と試験専用の nginx だけ）。
set -u

CASE=case-api.salesanchor.jp
# case-api 以外で 443 を受ける 5 つの名前
OTHERS=(jarvis-claude.uk app.salesanchor.jp api.salesanchor.jp monitor.salesanchor.jp salesanchor.jp)
UUID_LOWER=11111111-2222-3333-4444-555555555555
UUID_UPPER=AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE

FAILS=0
PASSES=0

ok() { PASSES=$((PASSES + 1)); echo "PASS: $1"; }
ng() { FAILS=$((FAILS + 1)); echo "FAIL: $1"; }

# raw <ip> <sni> <host> <path> [method] → 応答の全文（ヘッダ）。openssl s_client で SNI を指定して手で HTTP の 1 行を書く
raw() {
  local ip=$1 sni=$2 host=$3 path=$4 method=${5:-GET} target
  if [[ "$ip" == *:* ]]; then target="[${ip}]:443"; else target="${ip}:443"; fi
  { printf '%s %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n' "$method" "$path" "$host"; sleep 0.6; } \
    | timeout 15 openssl s_client -quiet -connect "$target" -servername "$sni" 2>/dev/null | tr -d '\r'
}

status_of() { awk 'NR==1 && $2 != "" { print $2; found=1 } END { if (!found) print "000" }'; }
location_of() { awk 'tolower($1)=="location:" { print $2; exit }'; }

# expect <label> <期待のコード> <ip> <sni> <host> <path> [method]
expect() {
  local label=$1 want=$2 ip=$3 sni=$4 host=$5 path=$6 method=${7:-GET} got
  got=$(raw "$ip" "$sni" "$host" "$path" "$method" | status_of)
  if [ "$got" = "$want" ]; then ok "[$ip] $label → $got"; else ng "[$ip] $label → $got（期待 $want） sni=$sni host=$host path=$path"; fi
}

cmd_prepare() {
  local conf=$1 out=$2 name path mapped n=0
  mkdir -p "$out/letsencrypt/live" "$out/htpasswd.d" "$out/www/certbot" "$out/www/salesanchor" "$out/www/design-site"
  : > "$out/htpasswd.d/design-site"
  for name in $(grep -oE '/etc/letsencrypt/live/[^/ ;]+/' "$conf" | sed -E 's#.*/live/([^/]+)/#\1#' | sort -u); do
    mkdir -p "$out/letsencrypt/live/$name"
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 2 -subj "/CN=$name" \
      -addext "subjectAltName=DNS:$name" -keyout "$out/letsencrypt/live/$name/privkey.pem" \
      -out "$out/letsencrypt/live/$name/fullchain.pem" 2>/dev/null || { echo "証明書を作れません: $name"; return 1; }
    n=$((n + 1))
  done
  # conf が読む証明書の道が全部作った物に当たること（数え漏れ・名前の違いを止める）
  for path in $(grep -E '^\s*ssl_certificate(_key)?\s' "$conf" | awk '{ gsub(";", "", $2); print $2 }'); do
    mapped="$out${path/#\/etc\//\/}"
    if [ ! -s "$mapped" ]; then echo "conf が読む $path に当たる物がありません"; return 1; fi
  done
  echo "prepared: ${n} 個の名前の自己署名の証明書を ${out}/letsencrypt に作りました"
}

cmd_sni_echo_conf() {
  local out=$1
  mkdir -p "$out/echo"
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 2 -subj "/CN=echo" \
    -keyout "$out/echo/key.pem" -out "$out/echo/cert.pem" 2>/dev/null || return 1
  cat > "$out/echo/echo.conf" <<'EOF'
# 試験専用: 受けた SNI をそのまま返す（本番の nginx.conf とは別のファイル）
server {
    listen 127.0.0.1:18443 ssl default_server;
    ssl_certificate /echo/cert.pem;
    ssl_certificate_key /echo/key.pem;
    location / {
        default_type text/plain;
        return 200 "sni=[$ssl_server_name]";
    }
}
EOF
  echo "echo conf: $out/echo/echo.conf"
}

cmd_sni_check() {
  local target=$1 sent got
  for sent in "case-api.salesanchor.jp." "CASE-API.salesanchor.jp"; do
    got=$({ printf 'GET / HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n'; sleep 0.6; } \
      | timeout 15 openssl s_client -quiet -connect "$target" -servername "$sent" 2>/dev/null | tr -d '\r' | grep -o 'sni=\[[^]]*\]' | head -n 1)
    echo "sent=[$sent] received: ${got:-（応答なし）}"
    if [ "$got" != "sni=[$sent]" ]; then
      echo "FAIL: 送った SNI がそのまま届いていない。末尾の点・大文字の試験が何も試さずに通る恐れがある。止めて Opus へ"
      return 1
    fi
  done
  echo "PASS: 末尾の点つき・大文字の SNI が、そのまま nginx に届く"
}

cmd_guard() {
  local ip=$1 n p
  # 1. case-api の SNI で Host を 5 つの名前に替える → 421
  for n in "${OTHERS[@]}"; do expect "SNI=case-api Host=$n" 421 "$ip" "$CASE" "$n" /; done
  # 2. 5 つの名前の SNI で Host を case-api → 421
  for n in "${OTHERS[@]}"; do expect "SNI=$n Host=case-api" 421 "$ip" "$n" "$CASE" /; done
  # 3. 末尾の点・大文字の SNI（openssl で送る）で Host を app → 421。Host を case-api・道を / → 404
  for n in "case-api.salesanchor.jp." "CASE-API.salesanchor.jp"; do
    expect "SNI=$n Host=app" 421 "$ip" "$n" app.salesanchor.jp /
    expect "SNI=$n Host=case-api /" 404 "$ip" "$n" "$CASE" /
  done
  # 4. case-api の許可外の道 → 404（管理の口・uuid でない {id}・大文字の uuid を含む）
  for p in \
    / /api/v1/auth/login /api/v1/ops/case/pending "/api/v1/ops/case/${UUID_LOWER}/ticket" \
    "/api/v1/ops/case/unmask-requests/${UUID_LOWER}/decision" /api/v1/ops/case/audits /api/v1/ops/case/audit-inputs \
    /api/v1/ops/case/not-a-uuid/report /api/v1/ops/case/unmask-requests/not-a-uuid \
    "/api/v1/ops/case/${UUID_UPPER}/report" "/api/v1/ops/case/unmask-requests/${UUID_UPPER}" /ops/unmask/other /api/v1/ops/read-window; do
    expect "case-api $p" 404 "$ip" "$CASE" "$CASE" "$p"
  done
  # 5. 道の正規化のすり抜け → 400
  expect "case-api %2e%2e" 400 "$ip" "$CASE" "$CASE" "/api/v1/ops/case/%2e%2e/pending"
  expect "case-api //ops/unmask/read" 400 "$ip" "$CASE" "$CASE" "//ops/unmask/read"
  expect "case-api %2f" 400 "$ip" "$CASE" "$CASE" "/api/v1/ops/case%2fpending"
  expect "case-api .." 400 "$ip" "$CASE" "$CASE" "/api/v1/ops/case/../pending"
  # 6. 通す道は location に届く（本物の入れ物は無いので、許可外の方法が 403 になることで届いたと分かる）
  expect "case-api GET read-window（POST だけ）" 403 "$ip" "$CASE" "$CASE" /api/v1/ops/read-window/query
  expect "case-api GET report（POST だけ）" 403 "$ip" "$CASE" "$CASE" "/api/v1/ops/case/${UUID_LOWER}/report"
  expect "case-api GET unmask-requests（POST だけ）" 403 "$ip" "$CASE" "$CASE" "/api/v1/ops/case/${UUID_LOWER}/unmask-requests"
  expect "case-api POST unmask-requests/{id}（GET だけ）" 403 "$ip" "$CASE" "$CASE" "/api/v1/ops/case/unmask-requests/${UUID_LOWER}" POST
  expect "case-api GET /ops/unmask/read（POST だけ）" 403 "$ip" "$CASE" "$CASE" /ops/unmask/read
  echo "guard[$ip]: PASS=${PASSES} FAIL=${FAILS}"
  [ "$FAILS" -eq 0 ]
}

cmd_snapshot() {
  local ip=$1 n resp
  for n in "${OTHERS[@]}"; do
    resp=$(raw "$ip" "$n" "$n" /)
    echo "$n $(printf '%s\n' "$resp" | status_of) $(printf '%s\n' "$resp" | location_of)"
  done
}

sub=${1:-}
shift || true
case "$sub" in
  prepare) cmd_prepare "$@" ;;
  sni-echo-conf) cmd_sni_echo_conf "$@" ;;
  sni-check) cmd_sni_check "$@" ;;
  guard) cmd_guard "$@" ;;
  snapshot) cmd_snapshot "$@" ;;
  *) echo "usage: $0 {prepare|sni-echo-conf|sni-check|guard|snapshot} ..." >&2; exit 2 ;;
esac
