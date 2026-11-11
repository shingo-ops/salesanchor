# card-bin1-r2: 完成品の走査の除く道を足す（便1 の 2 回目の直し）

状態: カード発行（Opus、2026-11-04）。便1 の実装承認（PO 2026-11-04「1」・card-bin1.md の状態の行）の範囲の直し。design.md §24-3 の 3（試しの当たりを見て Opus が除く道を決め、直しの短いカードを出す）に当たる。
親: [design.md](./design.md) §24-6（E1〜E4）。前のカード: [card-bin1.md](./card-bin1.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」の 3 つだけ。本番・GitHub の secret と Variables・組織の設定には触らない。PR は作らない。

## 受領確認（最初の報告の 1 行目に書く）
`RECEIVED card-bin1-r2 HEAD=<git rev-parse HEAD の 40 桁>`

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/build-on-github-bin1` を origin から取り直し、このカードのファイルが在ること。`git merge-base --is-ancestor 0b29532e44b43f1eb5157b003081cc65bd17d9a3 HEAD` が終了 0 であること。
- P2 次の 3 つが 0b29532e4 の中身と同じであること（`git diff --quiet 0b29532e4 -- <3 つのパス>` が終了 0）。違えば違いを書いて BLOCKED。
  - `.github/scripts/image-scan.sh`・`.gitleaks.toml`・`tests/sandbox/image-scan-survey.sh`
- P3 `grep -c 'generic-api-key' .gitleaks.toml` が 0 であること。

## 1. 触るファイル（この 3 つだけ）
1. `.github/scripts/image-scan.sh`（全文を書き換える。実行権 100755 のまま）
2. `.gitleaks.toml`（末尾に足すだけ。既存の行は 1 文字も変えない）
3. `tests/sandbox/image-scan-survey.sh`（1 行足すだけ。実行権 100755 のまま）

触らない: 上の 3 つ以外のすべて（`.github/workflows/`・`docs/`・製品コードを含む）。

## 2. 変更の中身

### 2-1. `.github/scripts/image-scan.sh`（全文。この形のまま書く）
書いた後の sha256 は `dbe3764c27527bfe9e8548870a79875f496296de66a645db50fa9ef01c94bc5a`（80 行）。

```bash
#!/usr/bin/env bash
# build-on-github 便1: 完成品の秘密検査（docs/handoff/build-on-github/design.md §7-2・§24 C1/C5/C6/C16・§24-6 E1〜E4）
# 使い方: image-scan.sh <image ref>
#   SCAN_REPORT_ONLY=1 … 当たりがあっても 0 で終わる（試験場の調べ用・tests/sandbox/image-scan-survey.sh）
#   GITLEAKS_CONFIG=<path> … gitleaks の設定を差し替える（既定は置き場の .gitleaks.toml）
# 出力に値は出さない（gitleaks は --redact、名前と履歴はパスと変数名だけ）。記録は公開される。
set -euo pipefail
REF="${1:?usage: image-scan.sh <image ref>}"
ROOT="$(git rev-parse --show-toplevel)"
CONFIG="${GITLEAKS_CONFIG:-$ROOT/.gitleaks.toml}"
GL_VERSION="8.24.3"
GL_SHA256="9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c"
WORK="$(mktemp -d)"
CID=""
cleanup() {  # 片付けの失敗で、通った走査を落とさない（設計審査 REVISE 2）
  if [ -n "$CID" ]; then docker rm -f "$CID" >/dev/null 2>&1 || true; fi
  chmod -R u+rwX "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# 0. gitleaks（版と sha256 を固定・design.md §24-1）
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
# 公開の配布物だけを除く（§24-6 E1）。除いたファイルも、中に PRIVATE KEY があれば当たりに戻す（E2）
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
```

### 2-2. `.gitleaks.toml`（末尾に足す）
今の最後の行（`paths = ['''(^|/)usr/share/nginx/html/assets/[^/]+\.js$''']`）の後に、次をそのまま足す（先頭の空行 1 つを含む）。
書いた後のファイル全体の sha256 は `a56baa550c91be8e8caeb54a89d28e1e56ada9ed59d4894bbfe68e7bb25db5c8`。

```toml

# =============================================================
# build-on-github 便1 の 2 回目（docs/handoff/build-on-github/design.md §24-6 E3）
# 既定の規則 generic-api-key を名前で広げ、2 つの場所だけを例外にする。規則は外さない。
# (a) frontend の画面の JS の Firebase web API key。gcp-api-key を例外にすると同じ値に generic-api-key が残るため。
#     場所と値の形の両方がそろったときだけ外す。同じ JS の別の秘密は当たる。
# (b) OS と言語の配布物の C の見出しファイル。アプリのファイルはここに入らない（5 つの Dockerfile の COPY の先）。
# どちらの場所も置き場に無いので、置き場の走査（secret-scan.yml）の結果は変わらない。
# =============================================================
[[rules]]
id = "generic-api-key"

[[rules.allowlists]]
description = "frontend 完成品の画面の JS の Firebase web API key（gcp-api-key の例外と同じ値に別の規則が当たる）"
condition = "AND"
paths = ['''(^|/)usr/share/nginx/html/assets/[^/]+\.js$''']
regexes = ['''^AIza[0-9A-Za-z_\-]{35}$''']

[[rules.allowlists]]
description = "OS と言語の配布物の C の見出しファイル"
paths = [
  '''(^|/)usr/(local/)?include/.+\.h$''',
  '''(^|/)usr/lib/[^/]+/perl/[^/]+/CORE/.+\.h$''',
]
```

### 2-3. `tests/sandbox/image-scan-survey.sh`（1 行足す）
`echo "CONTROL_GCP_HITS ...` の行（今の 58 行目）の直後に、次の 1 行を足す（先頭は空白 2 つ）。
書いた後のファイル全体の sha256 は `4a1505724a8ae87c9c98c1c662b7243187bd900c84bfad31748230007ff24e70`。

```bash
  printf '%s\n' "$CONTROL_OUT" | grep '^LEAK_HIT ' | sed 's/^/CONTROL_/' || true
```

## 3. 確かめてから報告すること（生出力はファイルに残し、パスを書く）
1. 3 つのファイルの sha256 が §2 の値と一致すること。一致しなければ commit しない。
2. `bash -n` を 2 本の .sh に当てて終了 0。`shellcheck` を 2 本に当てた出力全文。
3. `python3 -c "import tomllib;tomllib.load(open('.gitleaks.toml','rb'))"` が終了 0。
4. `git diff HEAD --stat`（commit の前）に §1 の 3 ファイルだけが出ること。`git diff HEAD -- .gitleaks.toml tests/sandbox/image-scan-survey.sh` に `-` で始まる中身の行が 0。
5. `git ls-files -s .github/scripts/image-scan.sh tests/sandbox/image-scan-survey.sh` が 2 つとも 100755。

docker を使う試しは担当では行わない。Opus が GitHub の試験場で流す。

## 4. 想定される分岐
- P1〜P3 のどれかが外れた → 実装せず BLOCKED:。
- sha256 が合わない → 書き写しの違い（行末の空白・最後の改行・タブ）を直す。それでも合わなければ diff の全文を書いて NEEDS_DECISION:。
- shellcheck が警告を出す → 直さずに全文を書いて NEEDS_DECISION:（Opus の手元では rc=0）。
- 除く道・例外を広げる直しは、どんな理由でもしない。
- 迷ったら止まって NEEDS_DECISION:。

## 5. 終わり方
1. commit は 1 つ。名義は今の設定のまま（Opus が記録する）。文の最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
2. `git log -1 --format='%H %an %s'` を報告に書く。
3. 今の枝へ push する。force push はしない。
4. `git log origin/release/build-on-github-bin1 -1 --format=%H` が 2. と同じであること。
5. 報告の最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか 1 つ。

END OF CARD
