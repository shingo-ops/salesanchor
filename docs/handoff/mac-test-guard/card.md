# 実装カード — AI が Mac で重い試験を回す命令を止める見張り（mac-test-guard）

> この文書は何か：design.md の見張りを作る指示書です（ADR-113 様式）。~/.claude への書き込み（導入）は含みません。

- 設計: docs/handoff/mac-test-guard/design.md（判定の正本は §3 の表）
- 下調べ: docs/handoff/mac-test-guard/recon.md
- 手本（同じ作りの見張り・読むだけ）: ~/.claude/scripts/mac-vm-guard.py の写し ref-mac-vm-guard.py.txt。クラウドの担当が使った後（2026-11-02 commit 29091ae68）に消した。写しの中の仮想マシンの命令の説明文が、GitHub の確かめ「Mac で仮想マシンを作る命令を足さない」に掛かったため
- 導入・戻しの手本: scripts/agent-hooks/confidential-quote-guard/install.sh・rollback.sh
- 危険便: いいえ（migrations/・deploy.yml・本番 scripts/・.github/ を含まない）
- 担当: 実装 Sonnet（クラウド）／審査 Opus
- 読んだ節: guards/00-common.md（cd 接頭辞・出力上限・commit の実在確認）、guards/05-pr.md（PR はこの便では作らない）、guards/12-guard-authoring.md（対象は guards 文書とカード検査。本件の Claude Code の見張りは対象外と照合）

受領確認: 作業を始める前に、報告の1行目に「受領確認: mac-test-guard card」と書く。

## 1. 目的

AI が Mac の Bash で重い試験（npm test・vitest・playwright test・pytest など）を打ったら、実行前に exit 2 で止めて GitHub とクラウドへ案内する。試験でない命令・文章の中の文字列は止めない。

## 2. 作るファイル（すべて新規。ほかのファイルは触らない）

1. `scripts/agent-hooks/mac-test-guard/guard.py`
2. `scripts/agent-hooks/mac-test-guard/test_guard.py`
3. `scripts/agent-hooks/mac-test-guard/install.sh`
4. `scripts/agent-hooks/mac-test-guard/rollback.sh`

## 3. 中身の要点

### guard.py（標準ライブラリのみ・python3）
- 先頭コメント1行: `# 設計: docs/handoff/mac-test-guard/design.md §3〜§6`
- 手本 ~/.claude/scripts/mac-vm-guard.py（写し ref-mac-vm-guard.py.txt は使用後に削除）の `strip_heredoc_bodies`・`split_parts`・`tokens`・`drop_redirections`・`log_event`・`consume_permit`・`main` と全体の流れをそのまま写す。変えるのは次だけ。
  - `MSG` は design.md §4 の文を一字一句そのまま。
  - `PERMIT_OP = 'mac test'`。
  - 記録の `hook` は `'mac-test-guard'`。記録先の上書き用の環境変数名は `MAC_TEST_GUARD_LOG`。券の理由文は `'mac test permit consumed'`。
  - 券置き場は `~/.claude/permits`（手本と同じ。試験では HOME を一時ディレクトリにして使う）。
  - colima・limactl の判定と `VALUE_FLAGS`・`colima_profile` は消す。
  - `bad_part` を design.md §3 の表どおりに書く。先頭語は `os.path.basename` で見る。各語は `drop_redirections` を通し、語末の `)` `}` を落としてから比べる。
    - `npm`: 旗を飛ばす（`--prefix`・`-C`・`-w`・`--workspace` は次の1語も飛ばす。`--prefix=x` の形は1語）。最初の語が `test`・`t`・`tst` なら止める。最初の語が `run`・`run-script` なら、次の語（旗を飛ばす）が `test` で始まり `:install` で終わらないとき止める。
    - `npx`: 旗を飛ばした次の語が `vitest` なら止める。`playwright` で、その次が `test` なら止める。
    - `pnpm`: `exec` の後を npx と同じに見る。`pnpm test`・`pnpm run test*` も npm と同じに止める。
    - `yarn`: 次の語を npx と同じに見る。`yarn test`・`yarn run test*` も npm と同じに止める。
    - `vitest`: 止める。
    - `playwright`: 次が `test` なら止める。
    - `pytest`・`py.test`: 止める。
    - `python`・`python3`・`python3.12` のような版付き（正規表現 `^python[0-9.]*$`）: 語の並びに `-m` があり、その次が `pytest` なら止める。
    - `uv`: `run` の後（旗を飛ばす）が `pytest` か、`python` 系で `-m pytest` なら止める。
    - `docker`: 語に `compose` があり、`exec` か `run` があれば、その後ろの語のどこかから始まる並びを先頭語として上の規則で見直す（1回だけ）。どれかで止まれば止める。（この docker の規則は card-fix1.md で「旗とサービス名を飛ばした残りだけを見る」に置き換え済み。正本は design.md §3）
    - `bash`・`sh`・`zsh`: 手本と同じ。`-c` の文字列を1段だけ `bad_command` で見直す。
    - それ以外は止めない。

### test_guard.py（python3 で単独で動く。外部の試験道具を使わない）
- 使い方: `python3 scripts/agent-hooks/mac-test-guard/test_guard.py [guard.py のパス]`。引数が無ければ同じフォルダの guard.py。
- guard.py を `subprocess` で起動し、標準入力に `{"tool_input":{"command": ...}}` を渡して終了値を見る。環境変数は `HOME` を一時ディレクトリ、`MAC_TEST_GUARD_LOG` を一時ファイルにする。
- 止める（exit 2・標準エラーに `GitHub` を含む）: `npm test`、`npm t`、`npm --prefix frontend test`、`npm -C agent-console test`、`npm run test:e2e`、`npm run test:unit`、`npm run-script test`、`npx vitest run`、`npx playwright test`、`pnpm exec vitest`、`yarn test`、`vitest run`、`playwright test`、`pytest backend/tests`、`py.test`、`python3 -m pytest -q`、`python3.12 -m pytest`、`uv run pytest`、`docker compose exec -T backend pytest`、`cd frontend && npm test`、`bash -c "npm test"`、`/usr/local/bin/npm test`、`FOO=1 npm test 2>&1 | tail -5`
- 止めない（exit 0）: `npm ci`、`npm run build`、`npm run lint`、`npm run test:e2e:install`、`npm install`、`npx playwright install chromium`、`npx tsc --noEmit`、`playwright install`、`python3 scripts/tests/test_x.py`、`python3 -I scripts/ci/check_doc_index.py`、`uv run ruff check`、`docker compose ps`、`bash scripts/dev/check-before-submit.sh`、`node --test scripts/tests/x.js`、`git push`、`git status`、`ls`
- 文章では止めない（exit 0）: `echo "npm test"`、`grep -n "npm test" README.md`、`git commit -m "npm test を止める"`、ヒアドキュメント本文に `npm test` を含む `cat <<'EOF' > /tmp/x.txt` の形
- 券: 一時 HOME の `.claude/permits/danger-permit-1.json` に `{"op":"mac test","created_by":"manual","expires_at":(1時間後の UTC、%Y-%m-%dT%H:%M:%SZ)}` を置く → `npm test` が exit 0、券ファイルが消える → もう一度 `npm test` が exit 2。`op` が `mac vm` の券・期限切れの券・`created_by` が `manual` でない券では exit 2。
- 壊れた入力（JSON でない）は exit 0。
- 記録: 止めたとき一時ファイルに `"hook": "mac-test-guard"` の行が1行増える。
- 最後に `OK 通った件数/全件数`（例 `OK 47/47`） を出し、1件でも違えば失敗した命令を出して exit 1。

### install.sh・rollback.sh
- confidential-quote-guard の install.sh・rollback.sh と同じ型。LaunchAgent・原文の写し・`--check` の部分は無い。
- install.sh: ①`$CLAUDE_DIR/scripts/mac-test-guard/guard.py` に写して `chmod 555` ②原本と `diff -q` ③写した先の guard.py で `test_guard.py` を流し、通らなければ settings.json に触らず `INSTALL_FAILED` で exit 1 ④settings.json を `.bak-mac-test-guard-` に UTC の時刻を付けた名前 に写してから、PreToolUse の matcher `Bash` の中で command が `mac-vm-guard.py` で終わる項目の直後に `{"type":"command","command":"python3 <DEST>/guard.py"}` を入れる。見つからなければ matcher `Bash` の項目を末尾に足す。同じ command が既にあれば足さない ⑤JSON として読めるか確かめてから置き換え ⑥`INSTALL_OK`。
- rollback.sh: settings.json を写してから、その command の項目1つだけを外す。写した guard.py は消さない。`ROLLBACK_OK`。
- どちらも `CLAUDE_DIR` を環境変数で差し替えられる（試験用）。

## 4. 触らない範囲

`.github/`・`migrations/`・`frontend/`・`backend/`・`agent-console`・ほかの `scripts/`・`~/.claude/agents/evaluator.md`・docs（このカードの4ファイル以外は作らない・直さない）。

## 5. 想定分岐

| 場合 | 動き |
|---|---|
| test_guard.py が1件でも落ちる | guard.py を直して流し直す。3回直しても落ちるなら commit せず停止し、落ちた命令と出力を報告 |
| design.md §3 の表と本カードの例が食い違う | §3 の表を正として停止し、食い違いを報告（推測で決めない） |
| shlex が読めない命令（引用符の閉じ忘れ） | 手本どおり空白で分けて判定を続ける |
| push が拒否される | 迂回せず停止し、拒否の文を報告 |

## 6. 手順（クラウドの作業場所で）

手順1 ブランチを作る
    cd "$REPO" && git fetch origin main && git switch -c release/mac-test-guard-impl origin/main
手順2 §2 の4ファイルを作る（§3 のとおり）
手順3 試験を流す
    cd "$REPO" && python3 scripts/agent-hooks/mac-test-guard/test_guard.py 2>&1 | tail -40
    期待する出力: 最後の行が OK で始まり、通った件数と全件数が同じ
手順4 導入の試験を一時の場所で流す（本物の ~/.claude には触らない）
    cd "$REPO" && mkdir -p /tmp/mtg-claude/scripts && printf '%s\n' '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"python3 /x/mac-vm-guard.py"}]}]}}' > /tmp/mtg-claude/settings.json
    cd "$REPO" && CLAUDE_DIR=/tmp/mtg-claude bash scripts/agent-hooks/mac-test-guard/install.sh
    cd "$REPO" && CLAUDE_DIR=/tmp/mtg-claude bash scripts/agent-hooks/mac-test-guard/install.sh
    cd "$REPO" && python3 -c "import json;d=json.load(open('/tmp/mtg-claude/settings.json'));print([h['command'] for h in d['hooks']['PreToolUse'][0]['hooks']])"
    期待する出力: INSTALL_OK が2回。一覧は mac-vm-guard.py の次に mac-test-guard の guard.py が1件だけ
    cd "$REPO" && CLAUDE_DIR=/tmp/mtg-claude bash scripts/agent-hooks/mac-test-guard/rollback.sh
    cd "$REPO" && python3 -c "import json;d=json.load(open('/tmp/mtg-claude/settings.json'));print([h['command'] for h in d['hooks']['PreToolUse'][0]['hooks']])"
    期待する出力: ROLLBACK_OK。一覧は mac-vm-guard.py の1件だけ
手順5 記録して送る
    cd "$REPO" && git add scripts/agent-hooks/mac-test-guard/
    cd "$REPO" && git commit -m "feat: add mac-test-guard hook that blocks heavy tests on the Mac"
    cd "$REPO" && git log --oneline -1
    cd "$REPO" && git push -u origin release/mac-test-guard-impl

PR はこの便では作らない（手元の Opus が作る）。

## 7. 報告

1行目に受領確認。続けて手順3・手順4の出力の最後の40行、`git log --oneline -1`、push の結果を生のまま書く。止まったときは、止まった手順・命令・出力を書いて停止する。

END OF CARD
