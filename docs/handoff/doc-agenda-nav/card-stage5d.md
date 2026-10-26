# 実装カード 段5d — 手元で止まらない検査2つ（書き方・暗い画面の色）を止まるようにする

> この文書は何か：doc-agenda-nav 段5d の作業指示書です。frontend/.husky/pre-commit（commit の直前に動く見張り）で、書き方の検査（lint-staged）と暗い画面の色の検査（dark-parity）の失敗が無視されているのを直し、frontend/AGENTS.md の説明を実際の動きに合わせます。

- 設計: docs/handoff/doc-agenda-nav/design.md
  - §27: 段5d の設計判断（この便の根拠。§27-3 が作り方、§27-4 が受け入れ基準）
  - §26-5: 残していた項目（§27 へ移した）
- 対象ADR: ADR-1040（Accepted）。関連: ADR-067・ADR-027
- 状態: 設計は Opus の設計判断（§27、2026-10-25）。PO の承認は 2026-10-25 の「1」（直し方を別の段として設計する）。実装の承認は PO にこれから聞く（承認の前に担当へ渡さない）。
- 危険便かどうか: 触るファイルは scripts/check-process-artifacts.js の DANGEROUS_PATTERNS に当たらない（§27-3）。workflow-lint.yml は触らない。GO は ADR-1003 の委譲により Opus が書きます（担当は GO 記録を書かず、マージもしない）。
- 作業の最初に: 作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）。
- 担当:
  - 実装と確かめ: Sonnet（model "sonnet"）
  - 審査: Opus（reviewer を model "opus" で新しく起こす）
  - GO とマージ: Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段5d の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

- やること: §3 の2ファイルの書き換えと、§5 の確かめ。
- やらないこと:
  - フックに `set -e` を入れない。:1-41・:50 以降（worktree の見張り・check-claude-size・ruff・lint_tenant_schema）を変えない。
  - frontend/package.json（lint-staged の欄）・scripts/new-worktree.sh・CI のファイルを触らない。
  - 作業場所に `npm ci`・`npm install` をしない（部品を入れない。§5 の試しは本店の部品を symlink で借りる）。
  - 本店（/Users/tanizawashingo/salesanchor）の frontend/node_modules の中を変えない。消さない。
  - `git checkout -- .` を使わない（見張りに止められる。試しは使い捨ての作業場所ごと捨てる）。

## 2. 前提の事実（Opus が 2026-10-25 に確かめた。起点は origin/main 00a8e3c38）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | pre-commit:42-49 は §4 の「変更前」の8行 | frontend/.husky/pre-commit |
| F2 | :38 で cwd は frontend になる | 同 :38 `cd "$REPO_ROOT/frontend" \|\| exit 1` |
| F3 | frontend/AGENTS.md:25 は §4 の「変更前」の1行で、ファイルは77行（上限90） | frontend/AGENTS.md、frontend/scripts/check-claude-size.js |
| F4 | この作業場所に frontend/node_modules は無い | `ls -d frontend/node_modules` |
| F5 | 本店に frontend/node_modules/.bin/lint-staged・eslint・stylelint がある | `ls -l /Users/tanizawashingo/salesanchor/frontend/node_modules/.bin/{lint-staged,eslint,stylelint}` |

一つでも実物と違えば、§6 の分岐に従う。

## 3. 触るファイル（これ以外は触らない）

| ファイル | 変えるところ |
|---|---|
| frontend/.husky/pre-commit | :42-49 |
| frontend/AGENTS.md | :25 |

（docs/handoff/doc-agenda-nav/card-stage5d.md の §11 に報告を書く。design.md は Opus のコミット済み）

## 4. 作り方（Edit。変更前の文を置き換える）

### 4-1. frontend/.husky/pre-commit:42-49

変更前:

```sh
# lint-staged で変更ファイルのみチェック
npx lint-staged

# index.css が変更された場合はパリティチェック
if git diff --cached --name-only | grep -q "frontend/src/index.css"; then
  echo "📋 index.css 変更検出 → ダークモード変数パリティチェック実行"
  node scripts/check-dark-parity.js
fi
```

変更後:

```sh
# lint-staged で変更ファイルのみチェック（ADR-1040 段5d）
# 部品（frontend/node_modules）が揃っていれば違反で止める。揃っていなければ飛ばして知らせる
# （npx でネットから版の違う道具を取らない。CI の必須チェック「Lint & Dark Mode Check (ADR-067)」で検査される）
if [ -x node_modules/.bin/lint-staged ] && [ -x node_modules/.bin/eslint ] && [ -x node_modules/.bin/stylelint ]; then
  node_modules/.bin/lint-staged || exit 1
else
  echo "⚠️  frontend/node_modules が無いため、書き方の検査（lint-staged）を飛ばしました。CI の Lint & Dark Mode Check で検査されます"
fi

# index.css が変更された場合はパリティチェック
if git diff --cached --name-only | grep -q "frontend/src/index.css"; then
  echo "📋 index.css 変更検出 → ダークモード変数パリティチェック実行"
  node scripts/check-dark-parity.js || exit 1
fi
```

- 字下げは2つの空白（今のファイルと同じ）。行は6行増える。

### 4-2. frontend/AGENTS.md:25

変更前:

```
`lint-staged` により **コミット前に自動ブロック**（`--max-warnings=0`）。
```

変更後:

```
`lint-staged` により **コミット前に自動ブロック**（`--max-warnings=0`）。frontend/node_modules が無い作業場所では手元の検査を飛ばして警告だけ出し、CI の必須チェック「Lint & Dark Mode Check (ADR-067)」で検査される。
```

- 行数は 77 のまま。

## 5. 確かめ方

生出力はすべて `/tmp/CC報告ファイル/an-s5d/impl/` に保存する（無ければ作る）。各コマンドは作業場所への cd から始める。作業場所は /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage5d（以下 S）。

### 5-1. 試しの台本（§4 の前に作る）

Write で `/tmp/CC報告ファイル/an-s5d/impl/trial.sh` を次の中身で作る（引数: 部品 A|B・場合 i|ii|iii・版 before|after）。

```sh
R=/Users/tanizawashingo/salesanchor
S=/Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage5d
O=/tmp/CC報告ファイル/an-s5d/impl
F=src/components/AccountCompanySaveButtonMigration.test.tsx
W=$1; K=$2; V=$3; N=$W-$K-$V; T=/Users/tanizawashingo/worktrees/salesanchor/s5d-trial-$N
git -C $R worktree add --detach $T 00a8e3c38 > $O/$N.wt 2>&1 || { echo "worktree add failed" >> $O/$N.wt; exit 2; }
[ $V = after ] && cp $S/frontend/.husky/pre-commit $T/frontend/.husky/pre-commit
[ $W = B ] && ln -s $R/frontend/node_modules $T/frontend/node_modules
cd $T/frontend || exit 2
case $K in
 i) echo "// probe" >> $F; git add $F;;
 ii) echo 'const x = "日本語";' >> $F; git add $F;;
 iii) perl -0pi -e 's/:root\s*\{/:root {\n  --probe-x: 1px;/' src/index.css; git add src/index.css;;
esac
cd $T && perl -e 'alarm 300; exec @ARGV' sh frontend/.husky/pre-commit > $O/$N.out 2>&1; echo rc=$? >> $O/$N.out
git -C $T diff --cached --name-only > $O/$N.cached
[ $W = B ] && rm $T/frontend/node_modules
git -C $R worktree remove --force $T >> $O/$N.wt 2>&1
```

- `rm $T/frontend/node_modules` は symlink だけを消す（末尾に `/` を付けない）。本店の部品は消えない。
- 作業場所の外だとフックの :14-25 が止めるので、試しの場所は `/Users/tanizawashingo/worktrees/salesanchor/` の下にする。

### 5-2. 変更前（§4 より先に実行する）

`bash /tmp/CC報告ファイル/an-s5d/impl/trial.sh <W> <K> before` を A-i・A-iii・B-i・B-ii・B-iii の5つ、1つずつ順に実行する（同時に動かさない）。期待: 5つとも rc=0（失敗が無視されている今の状態）。A-i の出力に「Task failed to spawn」が出る。

### 5-3. 変更後（§4 の後）

同じ5つを `after` で実行する。期待:

| 基準 | 期待 |
|---|---|
| T1 A-i-after | rc=0。「⚠️  frontend/node_modules が無いため」の行が出る。「Task failed to spawn」が出ない |
| T2 A-iii-after | rc=1。dark-parity の FAILED が出る |
| T3 B-ii-after | rc=1。`local/no-japanese-literal` が出る |
| T4 B-i-after | rc=0 |
| T5 B-iii-after | rc=1 |
| T6 | B-ii-after.cached・B-iii-after.cached・A-iii-after.cached に足したファイルが1行ある |
| T7 | after の5つの .out に `npm warn exec`・`Need to install` が無い（`grep -c` の結果を t7.txt に保存） |

### 5-4. T8（文法と行数）

`sh -n frontend/.husky/pre-commit; echo rc=$?` と `node frontend/scripts/check-claude-size.js; echo rc=$?` を t8.txt に保存。期待: どちらも rc=0、frontend/AGENTS.md は 77行。

### 5-5. 後片付けと差分

- `git -C /Users/tanizawashingo/salesanchor worktree list | grep s5d-trial` が0件（残っていれば、一覧に出た場所それぞれに `git -C /Users/tanizawashingo/salesanchor worktree remove --force` を実行する）。結果を cleanup.txt に保存。
- `git diff $(git merge-base origin/main HEAD) --stat > /tmp/CC報告ファイル/an-s5d/impl/diff-stat.txt` と同じ起点の `git diff` 全文を diff.txt に保存。期待: 製品側の変更は §3 の2ファイルだけ（design.md・card-stage5d.md は docs）。

## 6. 分岐ごとの対処

| 起きたこと | 対処 |
|---|---|
| §2 の F1〜F5 のどれかが実物と違う | 書き換えずに NEEDS_DECISION: 違った事実と実物の出力 |
| 5-2 で rc=0 でないものがある | 書き換えずに NEEDS_DECISION: その .out の全文のパス |
| 5-3 が期待と違う | §4 を見直す（変更前と同じ文になっているか）。直らなければ BLOCKED: .out の全文のパス |
| worktree add / remove が失敗する・見張りに止められる | 言い換えて再試行しない。止めた文の原文で BLOCKED: |
| 本店の frontend/node_modules が無い（F5） | 試しの B を行わずに NEEDS_DECISION: |
| commit がフックで止まる | 言い換えて再試行しない。`--no-verify` を使わない。止めた文の原文で BLOCKED: |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 部品なし・違反なしは今と同じく通る | T1 |
| 部品なしでも暗い画面の色の違反は止まる | T2（変更前 A-iii-before は rc=0） |
| 部品ありで書き方の違反は止まる | T3（変更前 B-ii-before は rc=0） |
| 部品ありで違反なしは通る | T4 |
| 部品ありで暗い画面の色の違反は止まる | T5 |
| 止まっても記録しようとした変更は消えない | T6 |
| ネットから道具を取らない | T7 |
| 文法・行数 | T8 |
| 触ったのは2ファイルだけ・試しの場所が残っていない | diff-stat.txt・cleanup.txt |
| CI | この便の PR の CI が緑（Opus が確かめる） |

## 8. 戻し方

PR を revert する（2ファイル）。

## 9. PR

- 作業場所は S。Opus が作成済み（origin/main 00a8e3c38 が起点）で、このカードと design.md の追記のコミットも入っている。担当は作り直さない。
- commit は1つ（2ファイルとカードの §11）。メッセージは `fix: 手元の書き方・暗い画面の色の検査を失敗で止める（doc-agenda-nav 段5d）`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。
- push は `git push -u origin release/doc-agenda-nav-stage5d`。
  - commit の後に `git log -1 --oneline` で確かめる。
  - push の後に `git log origin/release/doc-agenda-nav-stage5d -1 --oneline` で確かめる。
- PR は担当が作らない（Opus が作る。設計の PR に同じブランチで載る）。担当は PR の本文に足す結果の下書きを Write ツールで `/tmp/CC報告ファイル/an-s5d/pr-body-impl.md` に作るところまでを行う（§7 の各基準の rc と該当行）。
- validate-pr-body.sh は担当が実行しない（Opus が実行する）。

## 10. 報告

- 完了の報告に書くこと:
  - 冒頭の受領文
  - §5-2〜5-5 の結果（rc と該当行。全文はファイルのパス）
  - 新しい HEAD の sha
  - 判断が必要だった点（事実のみ）
- 停止したときに書くこと:
  - 止まった手順の番号
  - 最後に実行したコマンド
  - 止まった理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれかにする。
- 委任のときの決まり:
  - sleep しない。
  - ファイルの作成と編集は Write/Edit ツールで行う（§5-1 の台本の中の echo・perl・cp・ln・rm を除く）。
  - フックや自動判定に止められたら、言い換えて再試行しない。

## 11. 報告欄（担当が追記）

本報告はカード doc-agenda-nav 段5d の実行結果である。

- 実装承認: PO「1」2026-10-25
- 前提 F1〜F5: 実物と一致（preflight rc=0）
- 5-2 変更前（A-i・A-iii・B-i・B-ii・B-iii）: 5つとも rc=0。A-i の出力に「Task failed to spawn」1件
- 5-3 変更後: T1 A-i rc=0（警告行あり・Task failed to spawn 0件）／T2 A-iii rc=1（FAILED あり）／T3 B-ii rc=1（local/no-japanese-literal あり）／T4 B-i rc=0／T5 B-iii rc=1／T6 3つの .cached に足したファイル1行ずつ／T7 5つとも 0件（t7.txt）
- T8: sh -n rc=0・check-claude-size rc=0・frontend/AGENTS.md 77行
- 後片付け: s5d-trial の worktree 0件（cleanup.txt）。差分は製品側 frontend/.husky/pre-commit・frontend/AGENTS.md の2ファイルのみ（diff-stat.txt）
- 生出力: /tmp/CC報告ファイル/an-s5d/impl/
- 判断が必要だった点: 台本の引数は zsh で "A i" が1語になるため、1語ずつ分けて実行した（台本の中身は変更なし）


END OF CARD
