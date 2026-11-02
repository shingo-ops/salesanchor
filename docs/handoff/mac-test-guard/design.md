# design: AI が Mac で重い試験を回す命令を実行前に止める（mac-test-guard）

この文書は何か(専門用語なしの1行): Claude が Mac で重い試験を回そうとしたら、命令が動く前に止めて GitHub とクラウドへ案内する見張りの設計。

下調べ: [recon.md](recon.md)。関係する ADR: ADR-1052（Mac が重くなるので Mac で動かさない判断の前例。:34・:54）、ADR-029・ADR-111（この Mac は GitHub の作業を受ける機械。recon R2(e)）。試験の実行場所そのものを決めた ADR は無い（recon §1）。手本: [../mac-vm-hook/design.md](../mac-vm-hook/design.md)（同じ形の見張り）。
状態: 設計案作成済み・Opus 自己審査済み（§10）。KGI T1〜T6 は PO 承認済み（2026-11-02 チャット、6つの基準の説明に「1」）。実装は PO の「PRマージ、デプロイまで完走させてくれ」（2026-11-02）を受けクラウドの担当（Sonnet）に委任。カード: [card.md](card.md)。

## 0. PO の願い（2026-11-02 チャット）
- 「Macで試験をする意図は？スペックが低いからクラウドとgithubで完結させたい、」
- 「1」×3（試験は GitHub とクラウドだけ／機械で止める見張りを作る／送る直前の軽い確かめは Mac に残し、AI が打つ重い試験だけを止める）。詳細は recon.md §0。

## 1. KGI（○×で判定）
| # | 基準 | 検証方法 | 合格ライン |
|---|---|---|---|
| T1 | AI が Mac で重い試験の命令を打つと止まる | 試験スクリプトに §3 の「止める」列の命令を全部入れて流す。入れた後、Claude Code の Bash で `npm test` を1回打たせる | 試験は全件 exit 2。実機の1回は実行前に止まり、案内文に「GitHub」と出る |
| T2 | 試験でない命令は今までどおり | 試験スクリプトに §3 の「止めない」列を全部入れる | 全件 exit 0 |
| T3 | 文章の中の文字列では止まらない | `echo`・`grep`・ヒアドキュメント本文・`git commit -m` に `npm test` を含める | 全件 exit 0 |
| T4 | 送る直前の確かめは今までどおり動く | 入れた後の最初の `git push` の記録 .git/check-before-submit.log に1行増える | 1行増え、終了コード列が 0 か 2（見張りで 1 にならない） |
| T5 | 例外は PO の許可券だけで、AI は自分で通せない | PO が `! bash scripts/permit-danger.sh "mac test"` → 1回だけ通る。2回目は止まる | 2点とも期待どおり |
| T6 | 誤って止めることが無い・Mac で重い試験が動かない | 入れてから7日間、~/.claude/logs/agent-events.jsonl の `mac-test-guard` の記録を読む | 試験以外を止めた件数 0。券なしで通った試験の命令 0 |

## 2. 対象と対象外
- 対象（リポジトリ内。正本）:
  - 新規 scripts/agent-hooks/mac-test-guard/guard.py（PreToolUse Bash の見張り。標準ライブラリのみ）
  - 新規 scripts/agent-hooks/mac-test-guard/test_guard.py（T1〜T3・T5 の試験。券は一時 HOME で作る）
  - 新規 scripts/agent-hooks/mac-test-guard/install.sh・rollback.sh（confidential-quote-guard/install.sh:22・:58-61 と同じ型。settings.json の写しを取ってから mac-vm-guard の直後に1件足す。何度流しても1件）
  - 本 design.md・card.md・results.md
- 対象（リポジトリ外。PO の `!` で install.sh が書く）: ~/.claude/scripts/mac-test-guard/guard.py、~/.claude/settings.json の1件。
- 対象外:
  - 送る直前の確かめ（frontend/.husky/pre-push → scripts/dev/check-before-submit.sh）。git の中から動くので見張りに掛からない。PO 決定で残す。
  - `npm run build`・`npm ci`・`npx playwright install`（試験でない。agent-console の入れ替えに要る。recon R2(c)）。
  - 見張り自身などの小さな台本の試験（`python3 scripts/tests/*.py`・`node scripts/tests/*.js`・`node --test`・`bash ~/.claude/scripts/tests/*`）。数秒で終わり、手元の見張りの確かめに要る。
  - 画面を開いて見る道具（Playwright MCP・Claude in Chrome）。Bash ではない。
  - クラウドの担当（~/.claude/settings.json を読まない。recon R2(d)）。人が自分のターミナルで直接打つ命令。
  - ~/.claude/agents/evaluator.md:126・:131 の手元の qa-smoke の手順は本件では書き換えない（変更は一度に1つ）。入れた後に打たれると止まり、案内文で GitHub へ誘導される。

## 3. 止める形（判定の正本はこの表）
命令を引用符の外の `; && || |` 改行で分け、各部分の先頭語で判定する（`sudo`・`env`・`time`・`VAR=` は飛ばす。絶対パスは末尾名で見る）。分け方・ヒアドキュメント本文の除き方・`bash -c` の1段の再判定は mac-vm-guard.py の split_parts・strip_heredoc_bodies・bad_part と同じにする。

| 先頭語 | 判定 | 止める例 | 止めない例 |
|---|---|---|---|
| `npm` | 旗（`--prefix x`・`-C x`・`-w x`・`--workspace x` は値も）を飛ばした最初の語が `test`・`t`・`tst` なら止める。`run`・`run-script` の次の語が `test` で始まり `:install` で終わらないなら止める | `npm test`、`npm --prefix frontend test`、`npm run test:e2e`、`npm run test:unit` | `npm ci`、`npm run build`、`npm run test:e2e:install`、`npm run lint` |
| `npx`・`pnpm exec`・`yarn` | 次の語（旗を飛ばす）が `vitest` か、`playwright` の次が `test` なら止める | `npx vitest run`、`npx playwright test` | `npx playwright install chromium`、`npx tsc` |
| `vitest` | 止める | `vitest run` | — |
| `playwright` | 次が `test` なら止める | `playwright test` | `playwright install` |
| `pytest`・`py.test` | 止める | `pytest backend/tests` | — |
| `python`・`python3`（版付きも） | `-m pytest` なら止める | `python3 -m pytest` | `python3 scripts/tests/test_x.py`、`python3 -I scripts/ci/check_doc_index.py` |
| `uv` | `run` の後に `pytest` か `python -m pytest` なら止める | `uv run pytest` | `uv run ruff check` |
| `docker`（`compose ... exec/run ...`） | 残りの語に上の止める形が含まれれば止める | `docker compose exec -T backend pytest` | `docker compose ps` |
| `bash`・`sh`・`zsh` | `-c` の文字列を同じ規則で再判定（1段） | `bash -c "npm test"` | `bash scripts/dev/check-before-submit.sh` |
| その他（`echo`・`grep`・`git`・`cat`・`node`） | 止めない | — | `git push`、`node --test scripts/tests/x.js` |

## 4. 止めたときの案内文（標準エラー、exit 2）
`🚫 BLOCKED [mac-test-guard]: この Mac では重い試験を回しません（8コア・8GB で時間切れが毎回出るため。PO 決定 2026-11-02）。試験は GitHub の確かめ（PR を push すると自動で回る）か、クラウドの担当に頼んでください（決まり: docs/handoff/mac-test-guard/design.md）。Mac でしか試せない場合は PO に許可券 "mac test" を依頼してください。`

## 5. 例外（許可券）
mac-vm-guard と同じ。許可券置き場の danger-permit-*.json のうち `op == "mac test"`・`created_by == "manual"`・`expires_at` 未到来のものが1つあれば削除して通す（1回限り）。発行は既存の scripts/permit-danger.sh（変更なし）。AI による券の作成は既存 agent-danger-hook.sh の自己発行ブロックで止まる（mac-vm-hook/design.md §5 と同じ根拠）。

## 6. 失敗時の扱い
内部エラーは通す（fail-open。mac-vm-guard と同じ）。見張りの不具合で全 Bash が止まる被害の方が大きいため。止めた・券を使った・内部エラーは agent-events.jsonl に1行記録する（T6 の観測源。`hook: mac-test-guard`）。

## 7. 代替案と選択理由
- A 採用: Claude Code の PreToolUse 見張り（新しいファイル1つ）。手本の mac-vm-guard と同じ作りで、保守の型が同じ。
- B 不採用: mac-vm-guard.py に足す。1つのファイルに仮想機械と試験の2つの決まりが混ざり、戻すときに片方だけ戻せない。
- C 不採用: vitest・playwright の設定に「Mac なら落とす」を書く。agent-console と Sales Anchor の両方の試験の設定を変えることになり、人が打つ試験も止まり、GitHub の macOS の確かめとの見分けが要る。
- D 不採用: 時間切れを延ばして Mac でも通るようにする。PO の願い（Mac を軽くする）に反する。

## 8. 外部・過去事例の参照と我々への応用
Claude Code 公式の hooks 仕様（PreToolUse で exit 2 は命令を止め、標準エラーを AI に返す）に従う。出典: Context7 `/websites/code_claude` → https://code.claude.com/docs/en/hooks の「Exit code 2」（2026-11-02 確認。「a `PreToolUse` hook blocks the tool call」「The message that comes with the block is your hook's stderr」。exit 0 は「No decision: the normal permission flow applies」）。同じ型の実績は mac-vm-hook（docs/handoff/mac-vm-hook/）と py312-guard（docs/handoff/py312-guard/results.md）。社外の数値事例は本件の成否の根拠にならないため使わない。

## 9. 実装の流れ（PO の実装承認の後）
1. クラウドの担当（Sonnet）が release ブランチで §2 のリポジトリ内のファイルを作り、`python3 scripts/agent-hooks/mac-test-guard/test_guard.py` を通して push（クラウドで試験を回す）。
2. 手元で PR を作り、手元の審査役（reviewer・opus）の審査 → 合流。
3. PO が `! bash scripts/agent-hooks/mac-test-guard/install.sh` を流す（~/.claude へ書くのはこの1回だけ）。
4. Opus が T1 の実機1回・T4・T5 を確かめ、7日後に T6 を数えて results.md に残す。

## 10. Opus 自己審査（同一 AI による審査。独立した第二者の審査ではない）
- 整合: 手本 mac-vm-hook と止める形・券・fail-open を揃えた。PO の3つの決定（recon §0）と §2 対象外が一致（送る直前の確かめは残す）。
- 根拠: Mac で毎回落ちる事実（recon R1）、GitHub 経由で試験が Mac に来る道が無い事実（recon R2(e)）、手元の担当を起動できないので PO の `!` で入れる事実（recon R3）。
- 検証可能性: T1〜T3・T5 は試験スクリプトで○×、T4 は記録の行数、T6 は7日の記録で件数。
- リスク: ①`npm run test:*` の名前で試験でないものを止める → 両リポジトリの package.json の test で始まる名前は test:e2e・test:e2e:ui・test:e2e:install・test:e2e:vl・test:unit・test:coverage（frontend/package.json:11-14,44-45）と test:e2e（agent-console）。install だけ除外すれば残りはすべて試験。②評価する係の手元の手順が止まる → 想定どおり（案内文で GitHub へ）。
- 未解決: なし（PreToolUse の公式の出典は §8 で確認済み）。
- 判定: APPROVE（KGI T1〜T6 は PO 承認済み。実装カード card.md を発行）。

## 11. 維持の仕組み
- 守り手: PreToolUse の見張り mac-test-guard（手元の全セッション・審査役・評価する係に自動で効く）。点検は Opus（T6）。
- 正本は scripts/agent-hooks/mac-test-guard/。~/.claude の写しは install.sh でだけ入れ替える。
- 戻し方: PO が `! bash scripts/agent-hooks/mac-test-guard/rollback.sh`（settings.json の1件を消し、写しを退避）。
