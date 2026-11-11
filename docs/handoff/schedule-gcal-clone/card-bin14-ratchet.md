# 実装カード 便14 追補: 色の数の見張りに Google の色 13 個の例外（G68）（2026-11-11）

設計: `docs/handoff/schedule-gcal-clone/design.md` §10。PO の承認: 同 §10-6（選択「1」）。

## 0. 作業者への決まり

- ブランチ `release/schedule-gcal-editor-page` の上で作業する（新しいブランチは作らない）。作業の前に `git pull` で最新にする。
- 触るのは §1 の 3 ファイルだけ。frontend・docs・ほかの scripts・ほかの workflow は触らない。
- 推測で埋めない。カードと実物が合わないとき、試験が通らないときは止まって `BLOCKED:` で返す。
- コミットの最後の行: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。push は 1 回。force-push・rebase・amend はしない。

## 1. 触るファイル

| ファイル | 種類 |
|---|---|
| `scripts/check-design-token-ratchet.sh` | 変更 |
| `scripts/tests/test-design-token-ratchet.sh` | 新規 |
| `.github/workflows/design-token-guard.yml` | 変更 |

## 2. `scripts/check-design-token-ratchet.sh`

`ALLOWED_EXCEPTIONS=()` の行（今の :13）のすぐ後ろに、次を足す（文字どおり）。

```bash

# ADR-1074（PO 2026-11-11 の選択「1」・design.md §10）: 予定の画面だけで使う Google の実測色の素材。
# 色の正本 frontend/src/index.css の中で、次の 13 個の名前の「1 行に 1 宣言だけ」の行は数えない。
# 名前を足す・ファイルを足す・形をゆるめる変更は PO 承認必須。
GCAL_PALETTE_FILE="frontend/src/index.css"
GCAL_PALETTE_LINE_RE='^[[:space:]]*--gcal-(surface|surface-lowest|surface-container|surface-filled|on-surface|on-surface-variant|outline-variant|gridline|primary|on-primary|secondary-container|on-secondary-container|now)[[:space:]]*:[[:space:]]*#[0-9a-fA-F]{3,8}[[:space:]]*;[[:space:]]*$'

drop_gcal_palette_lines() {
  if [ "$1" = "${GCAL_PALETTE_FILE}" ]; then
    grep -vE "${GCAL_PALETTE_LINE_RE}" || true
  else
    cat
  fi
}
```

`count_hex_in_ref_file` の中の 1 行（今の :25）を次のように変える。ほかの行は変えない。

変更前:
```bash
  matches=$(git show "${ref}:${file}" 2>/dev/null | sed -E 's/\(#[0-9]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```
変更後:
```bash
  matches=$(git show "${ref}:${file}" 2>/dev/null | drop_gcal_palette_lines "${file}" | sed -E 's/\(#[0-9]+\)//g' | grep -oE '#[0-9a-fA-F]{3,8}\b' || true)
```

## 3. `scripts/tests/test-design-token-ratchet.sh`（新規）

- `#!/usr/bin/env bash` と `set -euo pipefail`。`mktemp -d` で使い捨ての場所を作り、`trap` で消す。
- その場所で `git init -q`、`git config user.email t@example.com`、`git config user.name t`。リポジトリの `scripts/check-design-token-ratchet.sh` の絶対パスを試験の頭で求めて、それを流す（写さない）。
- 元の状態: `frontend/src/index.css` に次を書いてコミットし、その SHA を BASE とする。

```css
:root {
  --base-color: #111111;
}
:root.force-dark {
  --base-color: #eeeeee;
}
```
`frontend/src/pages/a.css` に `.a { color: var(--base-color); }` を書いて同じコミットに入れる。

- 場合ごとに BASE から枝を作り（`git checkout -q -B case<N> <BASE>`）、変更をコミットし、その SHA を HEAD として `BASE_SHA=<BASE> HEAD_SHA=<HEAD> bash <見張り>` を流す。終了コードを比べる。

| 場合 | 変更 | 期待する終了コード |
|---|---|---|
| 1 | index.css の `:root` と `:root.force-dark` に 13 個の名前を全部、1 行ずつ `  --gcal-<名前>: #a1b2c3;` で足す（26 行） | 0 |
| 2 | index.css の `:root` に `  --gcal-extra: #123456;` を足す | 1 |
| 3 | index.css の `:root` に `  --gcal-surface: #ffffff; --x: #000000;` の 1 行を足す | 1 |
| 4 | index.css の `:root` に `  --other-color: #222222;` を足す | 1 |
| 5 | `frontend/src/pages/a.css` に `  --gcal-surface: #ffffff;` の行を足す（`.a { }` の中） | 1 |
| 6 | `frontend/src/pages/a.css` に `.b { color: var(--base-color); }` を足す（hex なし） | 0 |

- 各場合の結果を `ok 場合N` / `NG 場合N 期待X 実際Y` で 1 行ずつ出す。1 つでも NG があれば最後に終了コード 1、全部 ok なら 0。
- `chmod +x` は不要（`bash` で呼ぶ）。

## 4. `.github/workflows/design-token-guard.yml`

- `on.pull_request.paths` に 2 行を足す: `'scripts/check-design-token-ratchet.sh'` と `'scripts/tests/test-design-token-ratchet.sh'`。`'frontend/src/**'` は残す。
- `steps` の `actions/checkout@v5` の段の後ろ・今の見張りの段の前に、次の 1 段を足す。

```yaml
      - name: 見張りの試験（ADR-1074 の例外を含む）
        run: bash scripts/tests/test-design-token-ratchet.sh
```
- job 名 `guard-hex-increase`・今の見張りの段の名前・env・`run` は変えない。

## 5. 終わりの確かめと返し方

次を流し、生の出力をファイルに残して、最後の数行と終了コードを返す。

1. `bash scripts/tests/test-design-token-ratchet.sh` → 6 行とも `ok`・終了コード 0
2. `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=$(git rev-parse HEAD) bash scripts/check-design-token-ratchet.sh` → `PASS:`・終了コード 0
3. `git diff --stat origin/main...HEAD -- scripts .github` → §1 の 3 ファイルだけ
4. `bash -n scripts/check-design-token-ratchet.sh scripts/tests/test-design-token-ratchet.sh` → 何も出ない
5. `python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/design-token-guard.yml'))"` → 何も出ない

返す形: 最後の行に `DONE` か `BLOCKED: <理由>`。コミットの SHA と push の結果を書く。
