# card-bin1-r3: 便1 の作り直し（外した Firebase の値を抜き、本線に追いつかせる）

状態: カード発行（Opus、2026-11-11）。便1 の実装承認（PO 2026-11-04「1」・card-bin1.md の状態の行）の範囲の直し。新しい機能は足さない。
親: [design.md](./design.md) §25（旧 §24。番号が重なったので移した。§25 冒頭の注記）・§25-9（この作り直し）。前のカード: [card-bin1.md](./card-bin1.md)・[card-bin1-r2.md](./card-bin1-r2.md)。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」の 5 つだけ。本番・GitHub の secret と Variables・組織の設定には触らない。PR は作らない。

## なぜ作り直すか（事実）
- 本線は 2026-11-05 に Firebase を外した（317bfb653）。本線の `frontend/Dockerfile` の ARG は `VITE_FUNNEL_DASHBOARD` だけ（7 行目）。`docker-compose.yml:201` も同じ 1 つだけを渡す。
- 便1 の枝（653cc9847）は Firebase が在った頃に書いたので、Firebase の値 4 つ（secret 1・Variables 3）を求め、Firebase の鍵のための例外を `.gitleaks.toml` に持つ。いまは要らない。
- 便0-B3（#5394）が `.github/workflows/secret-scan.yml` に gitleaks の版と sha256 を固定した（`GITLEAKS_VERSION`・`GITLEAKS_SHA256`）。`image-scan.sh` も同じ値を自分で持つので、固定が 2 か所になる。正本を secret-scan.yml の 1 か所にする。

## 受領確認（最初の報告の 1 行目に書く）
`RECEIVED card-bin1-r3 HEAD=<git rev-parse HEAD の 40 桁>`

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/build-on-github-bin1-r3` を origin から取り直し、このカードのファイルが在ること。
- P2 `git merge-base --is-ancestor origin/main HEAD` が終了 0（本線を取り込み済み）。
- P3 `grep -c '^      GITLEAKS_VERSION: "' .github/workflows/secret-scan.yml` が 1、`grep -c '^      GITLEAKS_SHA256: "' .github/workflows/secret-scan.yml` が 1。
- P4 `grep -n '^ARG' frontend/Dockerfile` の出力が `7:ARG VITE_FUNNEL_DASHBOARD` の 1 行だけ。
- P5 `grep -c 'VITE_FIREBASE\|VITE_GCP_PROJECT_ID\|VITE_AUTH_PROVIDER' .github/workflows/build-images.yml` が 10（行の数）。

## 1. 触るファイル（この 5 つだけ）
1. `.github/workflows/build-images.yml`
2. `.github/scripts/image-scan.sh`（実行権 100755 のまま）
3. `.gitleaks.toml`
4. `tests/sandbox/image-scan-survey.sh`（実行権 100755 のまま）
5. `.github/scripts/ghcr-private-check.sh`（実行権 100755 のまま。番号の付け替えだけ）

触らない: 上の 5 つ以外のすべて（`docs/`・他の workflow・製品コードを含む）。

## 2. 変更の中身（上から順に。行番号は P1 の時点の値）

### 2-1. `.github/workflows/build-images.yml`
1. 「Check settings」の env から 28〜30 行目（`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID`・`VITE_AUTH_PROVIDER`）の 3 行を消す。
2. 33 行目を `          for n in GHCR_NAMESPACE GHCR_USER; do` にする。
3. paths-filter の `common` の `- '.gitleaks.toml'` の次の行に `              - '.github/workflows/secret-scan.yml'` を足す（字下げは前の行と同じ 14 空白）。理由: image-scan.sh が gitleaks の版をここから読むので、版を変えたら 5 つとも組み直して走査し直す。
4. build-frontend の「Check secret」の手順（128〜133 行目の 6 行。`- name: Check secret` から `echo "secret ok"` まで）を消す。
5. build-frontend の `build-args:` の中を次の 1 行だけにする（Firebase の 1 行と Variables の 3 行を消す）:
   `            VITE_FUNNEL_DASHBOARD=${{ secrets.VITE_FUNNEL_DASHBOARD }}`
6. 最後にファイル全体で `§24` を `§25` に置き換える（`sed -i 's/§24/§25/g'`）。

### 2-2. `.github/scripts/image-scan.sh`
1. 11〜12 行目（`GL_VERSION="8.24.3"` と `GL_SHA256="…"`）を次の 7 行に置き換える。
```bash
PIN_FILE="$ROOT/.github/workflows/secret-scan.yml"  # gitleaks の版と sha256 の正本（design.md §25-9）
GL_VERSION="$( (grep -m1 -E '^[[:space:]]+GITLEAKS_VERSION:' "$PIN_FILE" || true) | sed -E 's/^[^:]*:[[:space:]]*"?([^"[:space:]]*)"?.*$/\1/')"
GL_SHA256="$( (grep -m1 -E '^[[:space:]]+GITLEAKS_SHA256:' "$PIN_FILE" || true) | sed -E 's/^[^:]*:[[:space:]]*"?([^"[:space:]]*)"?.*$/\1/')"
if ! [[ "$GL_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || ! [[ "$GL_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
  echo "SCAN error: gitleaks pin not found in .github/workflows/secret-scan.yml"
  exit 1
fi
```
2. ファイル全体で `§24` を `§25` に置き換える。

### 2-3. `.gitleaks.toml`
1. 71〜82 行目（`# build-on-github 便1（…§24 C1）` の区切りの見出しから、gcp-api-key の `paths = [...]` の行まで）を消す。Firebase の鍵はもう完成品に載らないので、例外ごと要らない。
2. 85〜99 行目の generic-api-key の見出しの説明と例外を次の形にする（(a) の例外の 5 行 `[[rules.allowlists]]`〜`regexes = ...` を消し、(b) は 1 文字も変えない）:
```toml
# =============================================================
# build-on-github 便1（docs/handoff/build-on-github/design.md §25-6 E3・§25-9）
# 既定の規則 generic-api-key を名前で広げ、OS と言語の配布物の C の見出しファイルだけを例外にする。規則は外さない。
# アプリのファイルはここに入らない（5 つの Dockerfile の COPY の先）。この場所は置き場に無いので、置き場の走査（secret-scan.yml）の結果は変わらない。
# Firebase の web API key の例外は、本線が Firebase を外した（2026-11-05）ので消した。
# =============================================================
[[rules]]
id = "generic-api-key"

[[rules.allowlists]]
description = "OS と言語の配布物の C の見出しファイル"
paths = [
  '''(^|/)usr/(local/)?include/.+\.h$''',
  '''(^|/)usr/lib/[^/]+/perl/[^/]+/CORE/.+\.h$''',
]
```
3. 1〜70 行目は 1 文字も変えない（`AIzaSyE2E-dummy` などの全体の例外は、置き場の履歴の走査のために残す）。

### 2-4. `tests/sandbox/image-scan-survey.sh`
1. 2 行目の `§24 C8・C16` を `§25 C8・§25-9` にする。
2. 8 行目 `CTRL="$(mktemp)"`、15 行目 `printf '[extend]\nuseDefault = true\n' > "$CTRL"`、16 行目 `DUMMY_KEY=…` を消す。
3. cleanup の `rm -rf "$LOGDIR" "$CTRL"` を `rm -rf "$LOGDIR"` にする。
4. `survey_one frontend ./frontend \` から `--build-arg VITE_AUTH_PROVIDER=self` までの 6 行を次の 1 行にする:
   `survey_one frontend ./frontend --build-arg VITE_FUNNEL_DASHBOARD=mock`
5. その直後の `if docker image inspect survey/frontend:local …` から対応する `fi` まで（試しの鍵と対照の走査の塊）を消す。
6. `bash -n` が通り、`shellcheck`（入っていれば）が新しい警告を出さないこと。

### 2-5. `.github/scripts/ghcr-private-check.sh`
ファイル全体で `§24` を `§25` に置き換えるだけ。

## 3. 確かめ（全部を報告に生のまま書く）
- C1 `grep -c 'VITE_FIREBASE\|VITE_GCP_PROJECT_ID\|VITE_AUTH_PROVIDER\|DUMMY_KEY\|gcp-api-key\|AIza\[0-9' .github/workflows/build-images.yml .github/scripts/image-scan.sh tests/sandbox/image-scan-survey.sh` がすべて 0。`.gitleaks.toml` は `grep -c 'gcp-api-key\|AIza\[0-9'` が 0。
- C2 `grep -c '§24' <触った 5 つ>` がすべて 0。
- C3 `bash -n` が 3 つの .sh で通る。`python3 -c 'import yaml,sys;yaml.safe_load(open(".github/workflows/build-images.yml"))'` が通る。`python3 -c 'import tomllib;tomllib.load(open(".gitleaks.toml","rb"))'` が通る。
- C4 版の読み出しの実地: リポジトリの根で次を実行し、出力が `8.24.3 9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c` の 1 行であること。
  `ROOT=$(pwd); sed -n '/^PIN_FILE=/,/^GL_SHA256=/p' .github/scripts/image-scan.sh > /tmp/pin.sh; ROOT="$ROOT" bash -c 'set -euo pipefail; source /tmp/pin.sh; echo "$GL_VERSION $GL_SHA256"'`
- C5 版が見つからないときに止まること: `PIN_FILE` を存在しないパスにした写しで、`SCAN error: gitleaks pin not found` が出て終了 1 になること（写しは /tmp に作り、置き場には残さない）。
- C6 `git diff --stat origin/main...HEAD -- <触った 5 つ>` と `git diff HEAD~1 --stat`（このカードの commit の分）を貼る。触った 5 つ以外が変わっていないこと（`git diff --name-only HEAD~1` が 5 つ以下）。

## 4. commit と push
- commit 1 つ。文: `fix(build-on-github): drop Firebase build values and read gitleaks pin from secret-scan (card-bin1-r3)`。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- `git push origin release/build-on-github-bin1-r3`。force は使わない。
- 試験場（sandbox-test）は Opus が回す。担当は回さない。

## 5. 報告
1 行目は受領確認。最後の行は `DONE <commit の 40 桁>` か `BLOCKED: <理由>` か `NEEDS_DECISION: <問い>`。迷ったら止まる。

## 6. Opus が後で確かめること（担当は読むだけ）
- 試験場 sandbox-test（test=image-scan-survey）を r3 で回し、5 つとも `SCAN_SUMMARY … name_hits=0 leak_hits=0 history_hits=0`、`SURVEY_FAILURES 0`。
- 審査役の APPROVE、CI 全緑、GO 記録、確認済み、合流。合流後の最初の main の push で 5 つが倉庫に入り、非公開の確かめが通ること。
