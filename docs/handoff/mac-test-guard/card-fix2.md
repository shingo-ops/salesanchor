# 実装カード（直し2）— mac-test-guard の止めそこねを直す

> この文書は何か：本線に入った見張り（PR #5039）が、前に付く語の旗や一部の書き方を見落とす点を直す指示書です（ADR-113 様式）。~/.claude への書き込み（導入）は含みません。

- 設計: docs/handoff/mac-test-guard/design.md §3（判定の正本。ブランチ origin/release/mac-test-guard-fix2 の版を読む）
- 直す元: origin/main の scripts/agent-hooks/mac-test-guard/（PR #5039 で合流済み）
- 危険便: いいえ（migrations/・deploy.yml・本番 scripts/・.github/ を含まない）
- 担当: 実装 Sonnet（クラウド）／審査 Opus
- 読んだ節: guards/00-common.md（cd 接頭辞・出力上限・commit の実在確認）、guards/05-pr.md（PR はこの便では作らない）

受領確認: 作業を始める前に、報告の1行目に「受領確認: mac-test-guard card-fix2」と書く。

## 1. 目的

次の止めそこねを止める。止めない形は今のまま通す。

1. 前に付く語の旗: `time -p npm test`・`env -i npm test`・`sudo -u x npm test`
2. 値を取る旗: `pnpm --filter web test`・`yarn --cwd frontend test`・`uv run --with pytest-cov pytest`
3. 書き方の違い: `docker-compose exec backend pytest`・`bash -lc "npm test"`・`pnpm vitest`・`pnpm dlx vitest`・`npm exec vitest`

## 2. 触るファイル（この2つだけ）

1. `scripts/agent-hooks/mac-test-guard/guard.py`
2. `scripts/agent-hooks/mac-test-guard/test_guard.py`

## 3. 直し方（guard.py。行番号は origin/main の版）

- 10行目付近に定数を足す。
  - `PREFIX_VALUE_FLAGS = {'sudo': {'-u','-g','-h','-p','-C','-D','-U','-r','-t'}, 'env': {'-u','-C'}, 'time': {'-f','-o'}}`
  - `UV_VALUE_FLAGS = {'--with','--project','--directory','--python','-p','--package','--extra','--group','--env-file','--with-requirements','--with-editable','--index'}`
- 16行目 `NPM_VALUE_FLAGS` に `'--filter'`・`'-F'`・`'--dir'`・`'--cwd'` を足す。
- `tokens()`（96〜97行目）: `w in PREFIXES` のとき、`t = t[1:]` の後に、続く `-` で始まる語を飛ばす。`PREFIX_VALUE_FLAGS[w]` にある語は値の1語も飛ばす。`nohup` は旗を飛ばさなくてよい。
  - 変更前: `elif w in PREFIXES:\n    t = t[1:]`
  - 変更後: `elif w in PREFIXES:` で `t = t[1:]` のあと、`while t and t[0].startswith('-'): t = t[2:] if t[0] in PREFIX_VALUE_FLAGS.get(w, ()) else t[1:]`
- `is_npm_test()`（148〜158行目）: `rest[0] in ('exec', 'x')` なら `return is_npx_test(rest[1:])` を足す。
- `heavy()` の `pnpm`（174〜178行目）: `rest[0]` が `exec` か `dlx` なら `is_npx_test(rest[1:])`。それ以外は `is_npm_test(args) or is_npx_test(args)`。
- `heavy()` の `uv`（189〜197行目）: `run` の後の旗を飛ばすところ（193行目）を、`UV_VALUE_FLAGS` の語は値の1語も飛ばす形にする（skip_flags と同じ書き方で別の関数にしてよい）。
- `heavy()` の `docker`（198〜208行目）: `base == 'docker-compose' and allow_docker` のときも同じ判定に入れる。そのとき `'compose' not in args` の確かめはしない。
- `bad_part()`（218行目）: `'-c' in args` を「`-c`、または `re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', 語)` に当たる最初の語」に変える。再判定する文字列はその語の次の1語。
- ほかの部分は変えない。

## 4. 試験（test_guard.py）

- `BLOCK` に足す: `time -p npm test`、`env -i npm test`、`sudo -u nobody npm test`、`pnpm --filter web test`、`yarn --cwd frontend test`、`uv run --with pytest-cov pytest`、`docker-compose exec backend pytest`、`bash -lc "npm test"`、`pnpm vitest`、`pnpm dlx vitest`、`npm exec vitest`
- `PASS` に足す: `time -p ls`、`env -i PATH=/usr/bin ls`、`sudo -u nobody ls`、`pnpm --filter web build`、`pnpm tsc`、`npm exec tsc`、`uv run --with rich python scripts/x.py`、`docker-compose ps`、`bash -lc "echo hi"`
- ほかの試験はそのまま残す。

## 5. 触らない範囲

install.sh・rollback.sh・docs・`.github/`・`migrations/`・`frontend/`・`backend/`・ほかの `scripts/`。

## 6. 想定分岐

| 場合 | 動き |
|---|---|
| 試験が1件でも落ちる | guard.py を直して流し直す。3回直しても落ちるなら commit せず停止し、落ちた命令と出力を報告 |
| design.md §3 とこのカードが食い違う | §3 を正として停止し、食い違いを報告（推測で決めない） |
| 行番号の中身がカードの説明と違う | 停止して、実際の行を報告 |
| push が拒否される | 迂回せず停止し、拒否の文を報告 |

## 7. 手順（クラウドの作業場所で）

手順1 ブランチに入る
    cd "$REPO" && git fetch origin release/mac-test-guard-fix2 && git switch -c release/mac-test-guard-fix2 origin/release/mac-test-guard-fix2
手順2 設計の §3 を読む
    cd "$REPO" && sed -n '/^## 3/,/^## 4/p' docs/handoff/mac-test-guard/design.md
手順3 §3 とこのカードのとおり2ファイルを直す
手順4 試験を流す
    cd "$REPO" && python3 scripts/agent-hooks/mac-test-guard/test_guard.py 2>&1 | tail -40
    期待する出力: 最後の行が OK で始まり、通った件数と全件数が同じ
手順5 記録して送る
    cd "$REPO" && git add scripts/agent-hooks/mac-test-guard/guard.py scripts/agent-hooks/mac-test-guard/test_guard.py
    cd "$REPO" && git commit -m "fix: catch prefix flags, value flags and alternate forms in mac-test-guard"
    cd "$REPO" && git log --oneline -3
    cd "$REPO" && git push origin release/mac-test-guard-fix2

PR はこの便では作らない（手元の Opus が作る）。

## 8. 報告

1行目に受領確認。続けて手順4の出力の最後の40行、`git log --oneline -3`、push の結果を生のまま書く。止まったときは、止まった手順・命令・出力を書いて停止する。

END OF CARD
