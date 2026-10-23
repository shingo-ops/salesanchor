# 実装カード 段1b — 調査記録の置き場への保存を、商品マスタ登録の見張りの対象から外す

> この文書は何か：doc-agenda-nav 段1b の作業指示書です。調査記録（監視語を説明として引用しただけのメモ）を、リポジトリ外の記録置き場2か所へ保存しようとすると、商品マスタ登録の見張りに止められる誤作動を直します。変えるのは `scripts/agent-hooks/master-register-rules-guard.py` の :23 の1行と、その試験です。この Mac の見張りの本体（ホームの `.claude/scripts/` の同名ファイル）への写しは、マージの後に PO が `!` で行います（§8）。

- 設計: docs/handoff/doc-agenda-nav/design.md §6（KGI-2 の行 :161）・§8（段1b の行 :187）・§10-7
- recon: docs/handoff/doc-agenda-nav/recon.md
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076・ADR-113
- 前の段: 段1（card-stage1.md、PR #4665 マージ済み）。同じ試験ファイルに足すので段1のマージ後に作る（design §8 段1b・審査8回目 参考2）
- 状態: 設計は審査済み（PR #4649）。PO の指示原文「1,りせきするので要件通りにKGIを達成できるように完走させてくれ」（2026-10-23）
- 危険便（ADR-136 の危険パス）: はい。`scripts/` を触るため PR 本文に `### GO記録` が要る。GO は ADR-1003 の委譲名義で Opus が出す
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と試験は Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、GO・マージは Opus、見張りの本体への写しは PO

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（:23 の1行と、その試験だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/doc-agenda-nav-stage1b） |
| 6 | 書式は実例で示した | ○（§4） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（試験名と PASS/FAIL を1行ずつ出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（§2） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段1b の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `scripts/agent-hooks/master-register-rules-guard.py` の :23 の1行（`EXEMPT_PATHS`）に2つの文字列を足す
2. `scripts/agent-hooks/test_master_register_rules_guard.sh` に試験 T19〜T21 を足す（§4-2）

入れない:
- :25 の `PROMPT_RE`（段1で変更済み）・:53-84 の判定の流れ
- ホームの `.claude/settings.json`
- `.github/workflows/agent-hooks-test.yml`
- ホームの `.claude/scripts/` への写し（§8。PO が行う）

## 2. 前提の事実（2026-10-23 Opus が origin/main c4f67d058 の作業場所で確認）

| # | 事実 | 出典 |
|---|---|---|
| F1 | :23 は `EXEMPT_PATHS = ("/backend/", "/frontend/", "/docs/", "/migrations/", "/tests/")` | 見張りの実物 |
| F2 | 免除の判定は :66 `if tool in ("Write", "Edit") and any(p in fpath for p in EXEMPT_PATHS): return`。file_path（絶対パス）への部分一致で、`~` は展開されない。だから文字列は `~/` を付けずに書く | 見張りの実物・design §8 段1b（審査8回目 直6） |
| F3 | Bash は :62 で fpath が空になり、:66 の免除を通らない。Bash の登録コマンドは今までどおり止まる | 見張りの実物 :60-72 |
| F4 | 試験は T1〜T8 と、段1で足した T9〜T18（全78行。最後の行が `exit $FAIL`） | 試験の実物 |
| F5 | 試験は CI で動かない（agent-hooks-test.yml は review-gate の試験だけ）。手元の実行が証拠 | card-stage1.md F5 |
| F6 | ホームの本体とリポジトリの版は、段1の写しの後に入った :14 の1行だけ違う（本体 `REPO = "/Users/tanizawashingo/salesanchor"`／repo `REPO = os.environ.get("CLAUDE_PROJECT_DIR") or "/Users/tanizawashingo/salesanchor"`。commit 4ca6c9104 便2）。§8 で写すとこの1行も一緒に入る。環境変数が無ければ同じパスに戻るので、この Mac での動きは変わらない | Opus 実測 diff（2026-10-23） |

決めたこと:
- 足す文字列は `/CC報告ファイル-keep/` と `/tmp/CC報告ファイル/` の2つ（design §8 段1b）。
- 代替案と採らなかった理由: ①監視語の引用を許す印を本文に書かせる → 記録のたびに手間が増え、印の書き忘れで止まる。②免除をやめず見張り全体を止める → 本当の登録操作も止まらなくなる。③`/CC報告ファイル` の1語で免除 → 他の置き場まで広がる。

## 3. 触るファイル（これ以外は触らない）

- 変更: `scripts/agent-hooks/master-register-rules-guard.py`（:23 の1行だけ）
- 変更: `scripts/agent-hooks/test_master_register_rules_guard.sh`（最後の `exit $FAIL` の前に試験を足すだけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage1b.md`（このカード。担当は §13 報告欄の追記だけ）

## 4. 作り方

4-1. :23 の次の1行（変更前）:

```python
EXEMPT_PATHS = ("/backend/", "/frontend/", "/docs/", "/migrations/", "/tests/")
```

を、次の1行にする（他の行は変えない）:

```python
EXEMPT_PATHS = ("/backend/", "/frontend/", "/docs/", "/migrations/", "/tests/", "/CC報告ファイル-keep/", "/tmp/CC報告ファイル/")
```

4-2. 試験ファイルの最後の `exit $FAIL` の前に、次を足す（完成形。1字も変えない）:

```bash
# T19〜T21: 調査記録の置き場の免除（doc-agenda-nav 段1b。docs/handoff/doc-agenda-nav/card-stage1b.md §4-2）
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' /Users/tanizawashingo/CC報告ファイル-keep/x.md | python3 "$G")"
[ -z "$O" ]; check "T19 記録置き場(keep)への Write は素通り" $?
O="$(mk PreToolUse Write content 'create_product(x) の説明を引用したメモ' /tmp/CC報告ファイル/x.md | python3 "$G")"
[ -z "$O" ]; check "T20 記録置き場(tmp)への Write は素通り" $?
O="$(mk PreToolUse Bash command 'python3 /tmp/CC報告ファイル/x.py create_product(x)' | python3 "$G")"
echo "$O" | grep -q '"permissionDecision": "deny"'; check "T21 Bash の登録コマンドは止まる" $?
```

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. `git diff "$(git merge-base origin/main HEAD)" -- scripts/agent-hooks/master-register-rules-guard.py` の全文（期待: `-` 1行・`+` 1行。どちらも :23 の `EXEMPT_PATHS`）。
5-2. `bash scripts/agent-hooks/test_master_register_rules_guard.sh; echo "rc=$?"` の全文（期待: PASS が T1〜T8 の8行・T9〜T18 の10行・T19〜T21 の3行の計21行。FAIL 0行。最後の行が `rc=0`）。
5-3. わざと壊して落ちることを確かめる: :23 を Edit で §4-1 の変更前の1行に戻し、5-2 を実行する（期待: T19・T20 の2行が FAIL、T21 は PASS、`rc=1`）。確かめたら Edit で §4-1 の変更後の1行に戻し（`git checkout` は使わない）、5-1 と 5-2 をもう一度実行して貼る。
5-4. `python3 -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" scripts/agent-hooks/master-register-rules-guard.py; echo "rc=$?"` と `bash -n scripts/agent-hooks/test_master_register_rules_guard.sh; echo "rc=$?"`（どちらも `rc=0`）。
5-5. `git diff "$(git merge-base origin/main HEAD)" --stat` が §3 の3ファイルだけ。

## 6. 分岐ごとの対処

- 5-2 で T1〜T18 のどれかが FAIL → :23 以外を触っていないか 5-1 で確かめ、触っていなければ BLOCKED:。
- T21 が FAIL → 式や試験を変えずに BLOCKED:（F3 の前提と食い違うため Opus が判断する）。
- 5-3 の FAIL が T19・T20 の2行でない → 実際の行を貼って NEEDS_DECISION:。
- 見張りに止められた（この試験の文字列自体が監視語に当たる場合を含む） → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 記録置き場2か所への監視語入りの保存が止まらない | §5-2 の T19・T20 が PASS |
| Bash の登録コマンドは今までどおり止まる | §5-2 の T21 が PASS |
| 既存の T1〜T18 が通る | §5-2 |
| 変えたのは :23 の1行だけ | §5-1・§5-5 |
| 試験が元の1行では落ちる | §5-3 |
| ホームの見張りの本体がリポジトリの版と同じになる | §8 の diff の出力が空（`SAME`） |

## 8. 見張りの本体への写し（マージの後。PO が `!` で行う。担当はしない）

- 型は card-stage1.md §8 と同じ（写す前に .bak → `.new` に書いて空でないことを確かめる → 本体へ → diff で一致）。
- マージの後、Opus が本店で `git fetch origin` を行い、写す日の日付を入れた1行を PO に渡す（`.bak-` の後の日付は写す日。段1の `.bak-20261023` を上書きしない日付・名前にする）。
- 期待: 最後の行が `SAME`。F6 のとおり :14 の1行も一緒に入る。
- 反映の確かめ（Opus）: 写した後、`/tmp/CC報告ファイル/` へ監視語を引用したメモを Write して止まらないこと。

## 9. 戻し方

- 見張りの本体: PO が `!` で .bak から戻し、repo 版との diff で確かめる（写しはファイルごと。審査8回目 参考3）。
- repo: この PR の revert を main にマージする。
- 戻すと、調査記録の保存がまた止まる（段1b 以前と同じ）。

## 10. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage1b は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage1b`（origin/main c4f67d058 起点・2026-10-23）で作成済みで、このカードのコミットも載っている。担当は作り直さない。`ls -1d` と `git worktree list` で実在を確かめ、以後はすべてそこに `cd` してから行う。
- push は `git push -u origin release/doc-agenda-nav-stage1b`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage1b -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage1b/pr-body.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る（`--draft` を付けない）。base は main。担当はマージしない。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` に recon・設計・このカード、`対象ADR: ADR-1040（関連: ADR-076・ADR-113）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`Opus 審査記録: コード審査はこれから` を書く。`触るファイル:` と `削除するファイル:` は1行・カンマ区切り・バッククォートなし。`削除するファイル:` には行を書き換えた既存ファイル（見張りと試験の2本）を書く。
- 本文に `### GO記録` の見出しを置き、その下に「Opus が審査の後に記入する」とだけ書く。
- 本文に、§8 の写しはマージ後に PO が行うこと、この試験は CI で動かず §5-2 の手元実行が証拠であること、F6 を書く。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 11. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-5 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/an-stage1b/）／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない
- ファイルの作成と編集は Write/Edit ツールで行う
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
