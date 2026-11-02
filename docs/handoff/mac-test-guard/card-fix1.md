# 実装カード（直し1）— mac-test-guard の止めそこねと止めすぎを直す

> この文書は何か：card.md で作った見張りを、実装の審査で見つかった2点について直す指示書です（ADR-113 様式）。~/.claude への書き込み（導入）は含みません。

- 設計: docs/handoff/mac-test-guard/design.md §3（判定の正本。ブランチ origin/release/mac-test-guard-design の版を読む）
- 直す元: ブランチ release/mac-test-guard-impl（commit 29091ae68）
- 危険便: いいえ（migrations/・deploy.yml・本番 scripts/・.github/ を含まない）
- 担当: 実装 Sonnet（クラウド）／審査 Opus
- 読んだ節: guards/00-common.md（cd 接頭辞・出力上限・commit の実在確認）、guards/05-pr.md（PR はこの便では作らない）

受領確認: 作業を始める前に、報告の1行目に「受領確認: mac-test-guard card-fix1」と書く。

## 1. 目的

1. 止めそこね: `timeout 600 npx vitest run`・`nice npm test`・`nohup pytest` が今は通ってしまう。止める。
2. 止めすぎ: `docker compose exec backend echo vitest`・`docker compose exec backend pip show pytest` が今は止まる。通す。

## 2. 触るファイル（この2つだけ）

1. `scripts/agent-hooks/mac-test-guard/guard.py`
2. `scripts/agent-hooks/mac-test-guard/test_guard.py`

## 3. 直し方

### guard.py
- `tokens` の先頭の語を飛ばす部分を、何度重なっても飛ばすようにする。飛ばす語は次のとおり。
  - `sudo`・`env`・`time`・`nohup`。
  - `VAR=値` の形。
  - `timeout`: 続く旗を飛ばす。`-s`・`--signal`・`-k`・`--kill-after` は値の1語も飛ばし、`--signal=x` の形は1語として飛ばす。その次の1語（時間）も飛ばす。
  - `nice`: 続く `-n` と値の1語、`-数`（例 `-10`）、`--adjustment=x` を飛ばす。
- `heavy` の `docker` の部分を design.md §3 の docker の行どおりにする。
  - 語に `compose` があり、`exec` か `run` がある場合に見る。
  - その後ろの旗を飛ばす。`-e`・`--env`・`-u`・`--user`・`-w`・`--workdir`・`-v`・`--volume`・`--name`・`--entrypoint`・`-p`・`--publish`・`-l`・`--label`・`--index` は値の1語も飛ばす。それ以外の `-` で始まる語は1語だけ飛ばす。
  - 次の1語（サービス名）を飛ばす。
  - 残りの先頭語を `os.path.basename` で見て、`heavy(先頭語, 残り, False)` で判定する。どこかの語から始まる並びを全部見る今のやり方はやめる。
- ほかの部分は変えない。

### test_guard.py
- `BLOCK` に足す: `timeout 600 npx vitest run`、`timeout -s KILL 10m npm test`、`nice npm test`、`nice -n 10 pytest`、`nohup pytest`、`sudo nohup npm test`、`pnpm test`、`yarn run test:e2e`、`docker compose run --rm -e X=1 backend python -m pytest`
- `PASS` に足す: `docker compose exec backend echo vitest`、`docker compose exec backend pip show pytest`、`timeout 5 git status`、`nice ls`、`yarn install`、`pnpm run build`
- ほかの試験はそのまま残す。

## 4. 触らない範囲

install.sh・rollback.sh・docs・`.github/`・`migrations/`・`frontend/`・`backend/`・ほかの `scripts/`。

## 5. 想定分岐

| 場合 | 動き |
|---|---|
| 試験が1件でも落ちる | guard.py を直して流し直す。3回直しても落ちるなら commit せず停止し、落ちた命令と出力を報告 |
| design.md §3 とこのカードが食い違う | §3 を正として停止し、食い違いを報告（推測で決めない） |
| push が拒否される | 迂回せず停止し、拒否の文を報告 |

## 6. 手順（クラウドの作業場所で）

手順1 ブランチに入る
    cd "$REPO" && git fetch origin release/mac-test-guard-impl release/mac-test-guard-design && git switch -c release/mac-test-guard-impl origin/release/mac-test-guard-impl
手順2 設計の §3 を読む
    cd "$REPO" && git show origin/release/mac-test-guard-design:docs/handoff/mac-test-guard/design.md | sed -n '/^## 3/,/^## 4/p'
手順3 §3 のとおり2ファイルを直す
手順4 試験を流す
    cd "$REPO" && python3 scripts/agent-hooks/mac-test-guard/test_guard.py 2>&1 | tail -40
    期待する出力: 最後の行が OK で始まり、通った件数と全件数が同じ
手順5 記録して送る
    cd "$REPO" && git add scripts/agent-hooks/mac-test-guard/guard.py scripts/agent-hooks/mac-test-guard/test_guard.py
    cd "$REPO" && git commit -m "fix: catch timeout/nice/nohup prefixes and narrow docker check in mac-test-guard"
    cd "$REPO" && git log --oneline -2
    cd "$REPO" && git push origin release/mac-test-guard-impl

PR はこの便では作らない（手元の Opus が作る）。

## 7. 報告

1行目に受領確認。続けて手順4の出力の最後の40行、`git log --oneline -2`、push の結果を生のまま書く。止まったときは、止まった手順・命令・出力を書いて停止する。

END OF CARD
