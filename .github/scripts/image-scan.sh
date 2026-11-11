#!/usr/bin/env bash
# build-on-github 便1: 完成品の秘密検査（docs/handoff/build-on-github/design.md §7-2・§25 C1/C5/C6/C16・§25-6 E1〜E4）
# 使い方: image-scan.sh <image ref>
#   SCAN_REPORT_ONLY=1 … 当たりがあっても 0 で終わる（試験場の調べ用・tests/sandbox/image-scan-survey.sh）
#   GITLEAKS_CONFIG=<path> … gitleaks の設定を差し替える（既定は置き場の .gitleaks.toml）
# 出力に値は出さない（gitleaks は --redact、名前と履歴はパスと変数名だけ）。記録は公開される。
set -euo pipefail
REF="${1:?usage: image-scan.sh <image ref>}"
ROOT="$(git rev-parse --show-toplevel)"
CONFIG="${GITLEAKS_CONFIG:-$ROOT/.gitleaks.toml}"
PIN_FILE="$ROOT/.github/workflows/secret-scan.yml"  # gitleaks の版と sha256 の正本（design.md §25-9）
GL_VERSION="$( (grep -m1 -E '^[[:space:]]+GITLEAKS_VERSION:' "$PIN_FILE" || true) | sed -E 's/^[^:]*:[[:space:]]*"?([^"[:space:]]*)"?.*$/\1/')"
GL_SHA256="$( (grep -m1 -E '^[[:space:]]+GITLEAKS_SHA256:' "$PIN_FILE" || true) | sed -E 's/^[^:]*:[[:space:]]*"?([^"[:space:]]*)"?.*$/\1/')"
if ! [[ "$GL_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || ! [[ "$GL_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
  echo "SCAN error: gitleaks pin not found in .github/workflows/secret-scan.yml"
  exit 1
fi
WORK="$(mktemp -d)"
CID=""
cleanup() {  # 片付けの失敗で、通った走査を落とさない（設計審査 REVISE 2）
  if [ -n "$CID" ]; then docker rm -f "$CID" >/dev/null 2>&1 || true; fi
  chmod -R u+rwX "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# 0. gitleaks（版と sha256 を固定・design.md §25-1）
GL_TGZ="gitleaks_${GL_VERSION}_linux_x64.tar.gz"
curl -fsSL -o "$WORK/$GL_TGZ" "https://github.com/gitleaks/gitleaks/releases/download/v${GL_VERSION}/${GL_TGZ}"
echo "${GL_SHA256}  $WORK/$GL_TGZ" | sha256sum -c -
mkdir "$WORK/bin"
tar -xzf "$WORK/$GL_TGZ" -C "$WORK/bin" gitleaks
GL="$WORK/bin/gitleaks"

# 1. 完成品の中身を取り出す
CID="$(docker create "$REF" /scan-noop)"
docker export "$CID" -o "$WORK/fs.tar"
tar -tf "$WORK/fs.tar" > "$WORK/list.txt"
mkdir "$WORK/fs"
if ! tar -xf "$WORK/fs.tar" -C "$WORK/fs" --no-same-owner --no-same-permissions \
     --exclude='dev/*' --exclude='proc/*' --exclude='sys/*' 2>"$WORK/tar.err"; then
  echo "SCAN error: extract failed"; tail -20 "$WORK/tar.err"; exit 1
fi
rm -f "$WORK/fs.tar"
chmod -R u+rwX "$WORK/fs"

# 2. 名前の走査（パスだけ出す）
NAME_RE='(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_(rsa|ed25519).*|.*credentials.*\.json|auth\.json|\.npmrc|\.netrc|\.git/.*)$'  # design.md §7-2 の型のまま（C6）
# 公開の配布物だけを除く（§25-6 E1）。除いたファイルも、中に PRIVATE KEY があれば当たりに戻す（E2）
NAME_EXCLUDE_RE='^(etc/ssl/certs/[^/]+\.pem|etc/ssl/cert\.pem|etc/ssl1\.1/cert\.pem|usr/lib/ssl/cert\.pem|.+/certifi/cacert\.pem|.+/grpc/_cython/_credentials/roots\.pem|.+/googleapiclient/discovery_cache/documents/[^/]+\.json|usr/local/lib/node_modules/npm/\.npmrc)$'
grep -E "$NAME_RE" "$WORK/list.txt" > "$WORK/name_all.txt" || true
grep -vE "$NAME_EXCLUDE_RE" "$WORK/name_all.txt" > "$WORK/name_hit.txt" || true
grep -E "$NAME_EXCLUDE_RE" "$WORK/name_all.txt" > "$WORK/name_skip.txt" || true
NAME_HITS="$(wc -l < "$WORK/name_hit.txt" | tr -d ' ')"
sed 's/^/NAME_HIT /' "$WORK/name_hit.txt"
NAME_SKIPPED="$(wc -l < "$WORK/name_skip.txt" | tr -d ' ')"
SKIP_PK=0
while IFS= read -r f; do
  # 繋ぎ（symlink）は辿らない。行き先が完成品の外（実行機）になることがあるため。行き先の中身は 3. の走査が見る
  if [ -f "$WORK/fs/$f" ] && [ ! -L "$WORK/fs/$f" ] && grep -q 'PRIVATE KEY' "$WORK/fs/$f"; then
    echo "NAME_HIT_PRIVATE_KEY $f"; SKIP_PK=$((SKIP_PK + 1))
  fi
done < "$WORK/name_skip.txt"
echo "NAME_SKIPPED $NAME_SKIPPED"
NAME_HITS=$((NAME_HITS + SKIP_PK))

# 3. 中身の走査（gitleaks dir・値は伏せる。場所は行と桁だけ出す・E4）
if ! "$GL" dir "$WORK/fs" --config "$CONFIG" --no-banner --redact --exit-code 0 \
     --report-format json --report-path "$WORK/gl.json" > "$WORK/gl.log" 2>&1; then
  echo "SCAN error: gitleaks failed"; tail -20 "$WORK/gl.log"; exit 1
fi
LEAK_HITS="$(jq 'length' "$WORK/gl.json")"
jq -r --arg p "$WORK/fs/" '.[] | "LEAK_HIT \(.RuleID) \(.File | ltrimstr($p)) L\(.StartLine):C\(.StartColumn)-\(.EndColumn)"' "$WORK/gl.json"

# 4. 履歴の走査（変数名だけ出す）
HIST_RE='[A-Za-z0-9_]*(_TOKEN|_SECRET|PASSWORD|API_KEY)[A-Za-z0-9_]*='
docker history --no-trunc --format '{{.CreatedBy}}' "$REF" > "$WORK/hist.txt"
HISTORY_HITS="$(grep -cE "$HIST_RE" "$WORK/hist.txt" || true)"
grep -oE "$HIST_RE" "$WORK/hist.txt" | sed 's/=$//' | sort -u | sed 's/^/HISTORY_HIT /' || true

echo "SCAN_SUMMARY image=$REF name_hits=$NAME_HITS leak_hits=$LEAK_HITS history_hits=$HISTORY_HITS"
TOTAL=$((NAME_HITS + LEAK_HITS + HISTORY_HITS))
if [ "$TOTAL" -gt 0 ] && [ "${SCAN_REPORT_ONLY:-0}" != "1" ]; then
  echo "SCAN failed"; exit 1
fi
