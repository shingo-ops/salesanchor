# 実装カード 段2a — 入口の文書を変えたときにも行数の検査が動くようにする

> この文書は何か：doc-agenda-nav 段2a の作業指示書です。行数の検査（CLAUDE.md Size Guard）は「CLAUDE.md が変わったときだけ動く」作りですが、変更の判定に使うパス指定 `'**/CLAUDE.md'` がリポジトリ直下の CLAUDE.md に当たらないため、直下の CLAUDE.md や AGENTS.md を変えても検査が飛ばされています。この判定のパス指定1行を直します。

- 設計: docs/handoff/doc-agenda-nav/design.md §8（段2a の行）・段0 の ③
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 危険便（ADR-136 の危険パス）: いいえ（`.github/workflows/check-claude-size.yml` は不可逆操作リストの workflow-lint.yml ではない。migrations・deploy.yml・本番 scripts も触らない）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、マージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段2a の実行結果である」と書くこと。

## 1. 範囲

入れる: `.github/workflows/check-claude-size.yml` の :23 の1行だけ。

入れない: 同じファイルの他の行（:3-4 の注記・:37-40 の実行の段を含む）、`frontend/scripts/check-claude-size.js`（上限の数値と AGENTS.md の検査は段3c で扱う）、必須チェックの設定。

## 2. 前提の事実（2026-10-23 Opus が origin/main 5cb04e081 で確認。生出力 /tmp/CC報告ファイル/an-stage2a-pathspec.txt）

| # | 事実 | 出典 |
|---|---|---|
| F1 | :23 は `CHANGED=$(git diff --name-only "${BASE_SHA}...HEAD" -- '**/CLAUDE.md' 2>/dev/null \|\| echo "")` | check-claude-size.yml の実物 |
| F2 | 直下の CLAUDE.md だけを変えたコミット 283a53328 で、今の指定は何も返さない。新しい指定は `CLAUDE.md` を返す | Opus 実測 |
| F3 | 直下の AGENTS.md を変えたコミット 93ca3e8e8 で、今の指定は何も返さない。新しい指定は `AGENTS.md` を返す | Opus 実測 |
| F4 | 検査の台本 check-claude-size.js は LIMITS の CLAUDE.md 5本だけを数える。今の行数は 直下 120（上限120）・frontend 78（90）・backend 70（70）で、全部通る。だから判定を広げても、今ある PR が新たに落ちることはない | 台本 :22-28・`git show origin/main:<path> \| wc -l` |
| F5 | このジョブの名前「CLAUDE.md line count check」は必須チェックに入っている（PR #4694 のチェック一覧に pass で出る） | /tmp/CC報告ファイル/pr4694/checks2.txt |

## 3. 触るファイル（これ以外は触らない）

- 変更: `.github/workflows/check-claude-size.yml`（:23 の1行だけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage2a.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

:23 を、次の1行にする（行頭の空白10個は変えない。1字も変えない）:

```
          CHANGED=$(git diff --name-only "${BASE_SHA}...HEAD" -- 'CLAUDE.md' 'AGENTS.md' '**/CLAUDE.md' '**/AGENTS.md' 'docs/INDEX.md' 2>/dev/null || echo "")
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `git diff "$(git merge-base origin/main HEAD)" -- .github/workflows/check-claude-size.yml` の全文（期待: `-` 1行・`+` 1行。どちらも :23）。
5-2. 次を実行した全文（期待: 283a53328 で `CLAUDE.md`、93ca3e8e8 で `AGENTS.md` が出る）:
`for c in 283a53328 93ca3e8e8; do echo "== $c"; git diff --name-only "$c~1...$c" -- 'CLAUDE.md' 'AGENTS.md' '**/CLAUDE.md' '**/AGENTS.md' 'docs/INDEX.md'; done`
5-3. わざと外れることを確かめる: 同じコマンドを `'**/CLAUDE.md'` だけで実行し、2つとも何も出ないこと。
5-4. `python3 -I -c "import sys,yaml; yaml.safe_load(open(sys.argv[1]))" .github/workflows/check-claude-size.yml; echo "rc=$?"`（rc=0。yaml が無ければ `ruby -ryaml -e 'YAML.load_file(ARGV[0])' <path>` で代える）。
5-5. `cd frontend && node scripts/check-claude-size.js; echo "rc=$?"`（期待: PASSED・rc=0）。
5-6. `git diff "$(git merge-base origin/main HEAD)" --stat` が §3 の2ファイルだけ。
5-7. PR を作った後、その PR の「CLAUDE.md line count check」のログに「CLAUDE.md に変更なし」が出ること（この PR は CLAUDE.md・AGENTS.md を変えないので、正しく飛ばされる）。`gh run view` でログの該当行を出して貼る。

## 6. 分岐ごとの対処

- 5-2 で期待どおり出ない → 式を変えずに BLOCKED:。
- 5-5 が FAIL → この便では触らない範囲なので、出力を貼って NEEDS_DECISION:。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 直下の CLAUDE.md を変えた変更が検査の対象になる | §5-2（283a53328 で `CLAUDE.md`） |
| 直下の AGENTS.md を変えた変更が検査の対象になる | §5-2（93ca3e8e8 で `AGENTS.md`） |
| 今の指定では外れていたことを示せる | §5-3 |
| 変えたのは :23 の1行だけ | §5-1・§5-6 |
| 今ある入口の行数で検査が通る | §5-5 |
| マージ後: 次に CLAUDE.md を変える PR で「Check CLAUDE.md sizes」が skip でなく実行される | 段3a 以降の PR のチェック一覧（試しの PR は作らない。Opus が段3a の PR で確かめる） |

## 8. 戻し方

この PR の revert を main にマージする。戻すと、直下の CLAUDE.md・AGENTS.md の変更でまた検査が飛ばされる。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage2a は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage2a`（origin/main 5cb04e081 起点・2026-10-23）で作成済みで、このカードのコミットも載っている。担当は作り直さない。以後はすべてそこに `cd` してから行う。
- push は `git push -u origin release/doc-agenda-nav-stage2a`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage2a -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage2a/pr-body.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る（`--draft` を付けない）。base は main。担当はマージしない。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` に recon・設計・このカード、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`PO承認: 「1」（2026-10-23。誤作動直し・目次の新設・決まりの引っ越しまでを順に進める選択肢への返事）`、`Opus 審査記録: コード審査はこれから` を書く。`触るファイル:` と `削除するファイル:` は1行・カンマ区切り・バッククォートなし。`削除するファイル:` には行を書き換えた既存ファイル（check-claude-size.yml）を書く。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-7 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/an-stage2a/）／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

- 2026-10-23 担当(Sonnet): :23 の1行を §4 のとおり変更。§5-1〜5-6 は期待どおり（5-5 は PASSED・rc=0。tools/claude-channels/intake/CLAUDE.md の LIMITS 未登録警告は既存で今回の範囲外）。生出力 /tmp/CC報告ファイル/an-stage2a/

END OF CARD
