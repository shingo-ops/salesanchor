# 実装カード 段1 — 商品マスタ登録ルールの差し込み条件を「マスタ」と「登録」が近くに出たときだけにする

> この文書は何か：doc-agenda-nav 段1 の作業指示書です。会話の入力に「商品」か「マスタ」と「登録」がどこかに出るだけで、商品マスタ登録ルール（約100行）が会話に差し込まれる今の条件を、「マスタ」と「登録」が同じ文の中で近くに出たときだけに狭めます。変えるのは見張りのファイル `scripts/agent-hooks/master-register-rules-guard.py` の :25 の1行と、その試験です。この Mac の見張りの本体（ホームの `.claude/scripts/` の同名ファイル）への写しは、マージの後に PO が `!` で行います（§8）。

- 設計: docs/handoff/doc-agenda-nav/design.md §6（KGI-2 の行 :159）・§8（段1 の行 :183）・受け入れ基準 K2（:259）
- recon: docs/handoff/doc-agenda-nav/recon.md（:68 に今の条件の原因）
- 対象ADR: ADR-1040（Proposed。Decision 6）。関連: ADR-076・ADR-113
- 事実確認の生出力: /tmp/CC報告ファイル/an-stage1-regex-check.txt（新旧の式に例文11本を通した結果。2026-10-22 Opus）・/tmp/CC報告ファイル/an-card1/facts.txt（試験ファイル全文・見張りの :15-30・CI の定義）
- 状態: 設計は審査済み（PR #4649 でマージ済み）。KGI は PO 承認済み（2026-10-22「1」）。**このカードの実装は、PO の実装承認がまだ無い。承認が出るまで担当に渡さない**
- 前提: 段0 の PR（ADR-1040 とこのカード。head は release/doc-agenda-nav-stage0）が main にマージされていること（§10 で確かめる）
- 危険便（ADR-136 の危険パス）: はい。`scripts/` を触るため scripts/check-process-artifacts.js:115-127 の DANGEROUS_PATTERNS に当たり、PR 本文に `### GO記録` が要る。GO は ADR-1003 の委譲名義で Opus が出す（PO の実装承認の後に限る）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と試験は Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、GO・マージは Opus、見張りの本体への写しは PO

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（差し込み条件の1行と、その試験だけ。免除パスの追加は段1b で別 PR） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（§10。release/doc-agenda-nav-stage1） |
| 6 | 書式は実例で示した | ○（§4 に変更後の1行と試験の完成形） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-2。試験名と PASS/FAIL を1行ずつ出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から | ○（§2。例文11本の新旧の結果は実測） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§10・§12） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○ |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§10） |
| guards/12-guard-authoring.md | 目的・影響範囲・誤検知・将来の弊害・代替案・戻し方を書く。通す例と止める例を1つ以上ずつ書き、両方を試験する | ○（§2・§4-2・§9）。評価 JSON（guard-evaluations）は不要: 対象は guards 文書とカード検査だけで（同 :22）、`scripts/agent-hooks/` は対象外（scripts/check-guard-evaluations.js の対象は docs/handoff/design-partner-card-ops/guards/ と scripts/card-lint.sh の2つ） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `scripts/agent-hooks/master-register-rules-guard.py` の :25 の1行（`PROMPT_RE`）だけを変える
2. `scripts/agent-hooks/test_master_register_rules_guard.sh` に試験 T9〜T18 を足す（§4-2）。先頭コメント :2（別テーマ master-register-rules-hook の設計書の T1〜T6 を指す）は変えない。T9〜T18 の出典は §4-2 の見出しコメントに書く

入れない:
- :23 の `EXEMPT_PATHS`（免除パスの追加は段1b。別 PR）
- PreToolUse 側の判定（:53-84。登録操作の直前に止める仕組み）。変えない
- ホームの `.claude/settings.json` の登録（:82・:423）。変えない
- `.github/workflows/agent-hooks-test.yml`（今は review-gate の試験だけを動かす。この試験を CI に足すのは本便の範囲外）
- ホームの `.claude/scripts/` への写し（§8。PO が行う。担当はしない）

## 2. 前提の事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | 今の式は :25 `PROMPT_RE = re.compile(r"(マスタ|商品).*登録|登録.*(マスタ|商品)", re.S)`。「商品」か「マスタ」と「登録」が入力のどこかに（順不同・距離無制限・改行をまたいで）出れば一致する | /tmp/CC報告ファイル/an-card1/facts.txt の :69・recon.md:68 |
| F2 | 見張りは UserPromptSubmit で `PROMPT_RE` に一致すると、ルール全文を `additionalContext` で差し込む（:87-100） | 見張りの実物 |
| F3 | リポジトリの版とホームの `.claude/scripts/` の版は同一（diff で差なし。2026-10-22 Opus） | recon・Opus 実測 |
| F4 | 既存の試験は T1〜T8。T4 は「この商品をマスタに登録して」で `additionalContext` が出ることを確かめる。書き方は `mk UserPromptSubmit x x '例文' \| python3 "$G"` と `check` | /tmp/CC報告ファイル/an-card1/facts.txt :29-57 |
| F5 | CI `Agent Hooks Test` は `scripts/agent-hooks/**` の変更で動くが、実行するのは review-gate の試験だけ（agent-hooks-test.yml:24）。この試験は CI で動かないので、手元の実行が合否の証拠になる。必須チェックでもない（同 :5） | /tmp/CC報告ファイル/an-card1/facts.txt |
| F6 | 例文11本を新旧の式に通した結果（左が今・右が新しい式）: 無関係4本と境界1本は True→False、関係あり4本は True→True、「商品を登録して」は True→False、「PR を作って」は False→False | /tmp/CC報告ファイル/an-stage1-regex-check.txt |

決めたこと:
- 新しい式は design §6:159 のとおり `re.compile(r"マスタ[^。\n]{0,40}登録|登録[^。\n]{0,20}マスタ")`。`re.S` は付けない（`[^。\n]` が改行を含まないので、付けても結果は変わらない。付けないことで「同じ文の中」の意図が読みやすい）。
- 「商品を登録して」（「マスタ」を含まない）は差し込まなくなる。これは設計どおりで、試験の期待値を「出ない」にする。実際に商品を登録する操作（create_product など）は、PreToolUse 側（:53-84）が今までどおり止めて全文を出すので、ルールを読まずに登録することにはならない。
- 「販売先を顧客マスタに登録して」（商品以外のマスタ）は差し込まれる。誤検知だが、約100行が入るだけで操作は止まらないので許容する（design §6:159）。
- 代替案と採らなかった理由: ①「商品マスタ」の語だけで判定する → 「共用マスタへ登録」「マスタに登録して」を拾えない。②差し込みをやめて PreToolUse 側だけにする → 登録の相談の段階でルールが読まれなくなる。③距離の上限を広げる → 無関係な例文（境界の1本）を拾い直す。

## 3. 触るファイル（これ以外は触らない）

- 変更: `scripts/agent-hooks/master-register-rules-guard.py`（:25 の1行だけ）
- 変更: `scripts/agent-hooks/test_master_register_rules_guard.sh`（:56 の T8 の後・:57 `exit $FAIL` の前に試験を足すだけ）
- 変更: `docs/handoff/doc-agenda-nav/card-stage1.md`（このカード。担当は §13 報告欄の追記だけ）

## 4. 作り方

4-1. `scripts/agent-hooks/master-register-rules-guard.py` の :25 の次の1行（変更前。この文字列と一致する行を探して置き換える）:

```python
PROMPT_RE = re.compile(r"(マスタ|商品).*登録|登録.*(マスタ|商品)", re.S)
```

を、次の1行にする（他の行は変えない）:

```python
PROMPT_RE = re.compile(r"マスタ[^。\n]{0,40}登録|登録[^。\n]{0,20}マスタ")
```

4-2. `scripts/agent-hooks/test_master_register_rules_guard.sh` の T8 の後（`exit $FAIL` の前）に、次を足す（完成形。例文は1字も変えない）:

```bash
# T9〜T18: 差し込み条件（doc-agenda-nav 段1。docs/handoff/doc-agenda-nav/card-stage1.md §4-2）
# 出ないこと（無関係4本・境界1本・マスタを含まない1本・無関係1本）
for P in \
  '在庫表の商品名の列幅を直して。あとログイン登録画面のバグも見て' \
  'ユーザー登録フォームで商品一覧が出ない' \
  'マスタ画面の表示が遅い。GitHub に登録してあるワークフローも確認' \
  'Discord の webhook を登録して商品の通知を流す' \
  'マスタを整備して正答率を上げたい。登録はまだしない' \
  '商品を登録して' \
  'PR を作って'; do
  O="$(mk UserPromptSubmit x x "$P" | python3 "$G")"
  [ -z "$O" ]; check "T9-15 出ない: $P" $?
done
# 出ること（関係あり2本・別マスタ1本）
for P in \
  '商品マスタに新しいカードを登録して' \
  '共用マスタへ登録する候補一覧を出して' \
  '販売先を顧客マスタに登録して'; do
  O="$(mk UserPromptSubmit x x "$P" | python3 "$G")"
  echo "$O" | grep -q '"additionalContext"' && echo "$O" | grep -q "$RULES_HEAD"; check "T16-18 出る: $P" $?
done
```

- T4（「この商品をマスタに登録して」）は残す（関係ありの例文として新しい式でも出る＝F6）。
- `:2` のコメントは変えない（§1）。

## 5. 確かめ方（担当が実行し、出力を報告に貼る）

5-1. 作業場所で `git diff "$(git merge-base origin/main HEAD)" -- scripts/agent-hooks/master-register-rules-guard.py` の全文（期待: `-` 1行・`+` 1行。どちらも :25 の `PROMPT_RE` の行）。
5-2. 作業場所で `bash scripts/agent-hooks/test_master_register_rules_guard.sh; echo "rc=$?"` の全文（期待: PASS が T1〜T8 の8行と、出ない7行・出る3行の計18行。FAIL は0行。最後の行が `rc=0`）。
5-3. わざと壊して落ちることを確かめる: :25 を一時的に元の式 `re.compile(r"(マスタ|商品).*登録|登録.*(マスタ|商品)", re.S)` に Edit で戻し、5-2 と同じコマンドを実行する（期待: 「出ない」のうち6行が FAIL（「PR を作って」だけ PASS）で `rc=1`）。確かめたら Edit で §4-1 の1行に戻す（`git checkout` は使わない）。戻した後に 5-1 と 5-2 をもう一度実行して貼る。
5-4. `python3 -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" scripts/agent-hooks/master-register-rules-guard.py; echo "rc=$?"`（期待 `rc=0`）と `bash -n scripts/agent-hooks/test_master_register_rules_guard.sh; echo "rc=$?"`（期待 `rc=0`）。
5-5. `git diff "$(git merge-base origin/main HEAD)" --stat` が §3 の3ファイルだけであること。

## 6. 分岐ごとの対処

- 5-2 で T1〜T8 のどれかが FAIL → :25 以外を触っていないか 5-1 で確かめ、触っていなければ BLOCKED:（式を自分で変えて合わせない）。
- 5-2 で「出る」3行のどれかが FAIL → 式や例文を変えずに BLOCKED:（設計の前提 F6 と食い違うため Opus が判断する）。
- 5-3 で「出ない」の FAIL が6行でない → 実際の行を貼って NEEDS_DECISION:。
- 見張りに止められた（このファイルの編集自体が見張りの監視語に当たる場合を含む） → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 関係ない例文（無関係4本・境界1本）で差し込みが 0/5（KGI-2・K2） | §5-2 の「出ない」の5行が PASS |
| 関係ある例文（商品マスタ・共用マスタの2本）で 2/2 のまま | §5-2 の「出る」の2行と T4 が PASS |
| 既存の試験 T1〜T8 が通る（PreToolUse 側が変わっていない） | §5-2 |
| 変えたのは :25 の1行だけ | §5-1・§5-5 |
| 試験が元の式では落ちる（試験が効いている） | §5-3 |
| ホームの見張りの本体がリポジトリの版と同じになる | §8 の diff の出力が空 |

## 8. 見張りの本体への写し（マージの後。PO が `!` で行う。担当はしない）

- 前例: docs/handoff/master-register-rules-hook/design.md:37 の型（PR で審査 → PO が写す → 写す前に .bak → 写した後に diff で一致を確かめる）。
- 8-1. マージの後、Opus が本店で `git fetch origin` を行い、PO に次の1行を渡す（PO が `!` で実行する）:
  `cp -p ~/.claude/scripts/master-register-rules-guard.py ~/.claude/scripts/master-register-rules-guard.py.bak-20261022 && git -C /Users/tanizawashingo/salesanchor show origin/main:scripts/agent-hooks/master-register-rules-guard.py > ~/.claude/scripts/master-register-rules-guard.py.new && test -s ~/.claude/scripts/master-register-rules-guard.py.new && cp ~/.claude/scripts/master-register-rules-guard.py.new ~/.claude/scripts/master-register-rules-guard.py && git -C /Users/tanizawashingo/salesanchor show origin/main:scripts/agent-hooks/master-register-rules-guard.py | diff - ~/.claude/scripts/master-register-rules-guard.py && echo SAME`
  （日付の部分は写す日に合わせて Opus が書き換える。いったん `.new` に書き、空でないことを `test -s` で確かめてから本体に写す。`git show` が失敗しても本体は空にならない。`cp` は既存の本体の権限を保つ。`.new` は消さずに残す）
- 8-2. 期待: 最後の行が `SAME`。出なければ §9 で戻す。
- 8-3. 反映の確かめ（Opus）: 新しい会話で無関係の例文「ユーザー登録フォームで商品一覧が出ない」を入れても、商品マスタ登録ルールが差し込まれないこと。新しい会話で関係ある例文「商品マスタに新しいカードを登録して」を入れると差し込まれること。結果を PR にコメントで残す（会話の記録ファイルは読まない）。
- ホームの `.claude/settings.json` は変えないので、写すだけで次の入力から効く。

## 9. 戻し方

- 見張りの本体: PO が `!` で `cp -p ~/.claude/scripts/master-register-rules-guard.py.bak-20261022 ~/.claude/scripts/master-register-rules-guard.py` を実行し、`git -C /Users/tanizawashingo/salesanchor show origin/main:scripts/agent-hooks/master-register-rules-guard.py | diff - ~/.claude/scripts/master-register-rules-guard.py` で差が :25 の1行だけになったことを確かめる（repo を revert した後なら差は0行）。
- repo: この PR の revert を main にマージする。
- 戻すと、関係ない入力でもルール約100行が入る状態に戻る（2026-10-22 以前と同じ）。

## 10. PR

- 作業場所: 段0 の PR が main にマージされたことを `gh pr list --state merged --head release/doc-agenda-nav-stage0 --limit 1 --json number,state` で確かめる（合格は1件で state が MERGED。`[]` なら作業を始めずに BLOCKED:）。その後 `cd /Users/tanizawashingo/salesanchor && git fetch origin && bash scripts/new-worktree.sh release/doc-agenda-nav-stage1 --claude`（origin/main 起点）を実行する。
  - 出力はパイプに通さない。
  - 最後に「Input must be provided」と出て exit 1 になることがあるが、作業場所の作成とは無関係（2026-10-22 実測）。
  - 作成後に `ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage1` と `git worktree list` の両方で実在を確かめる。
  - `ls docs/handoff/doc-agenda-nav/card-stage1.md` でこのカードが実在することを確かめる。
  - 以後の作業はすべてその作業場所に `cd` してから行う。
- push は `git push -u origin release/doc-agenda-nav-stage1`（素の `git push` は上流が main のため失敗する）。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage1 -1 --oneline` で実在を確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage1/pr-body.md` を作り、`--body-file /tmp/CC報告ファイル/an-stage1/pr-body.md` で渡す。作成後に `gh pr list --head release/doc-agenda-nav-stage1 --limit 1 --json number,isDraft` で1件・isDraft が false を確かめる。
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる。
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` には次を書く:
  - recon（docs/handoff/doc-agenda-nav/recon.md）・設計（docs/handoff/doc-agenda-nav/design.md）・このカード
  - `対象ADR:` の行は「対象ADR: ADR-076（関連: ADR-113）」とし、本文に ADR-1040 の Decision 6 も書く
  - `設計仕様書（あるべき姿）:` は docs/specs/doc-agenda-nav/README.md
  - `Opus 審査記録:` は「コード審査はこれから」（審査の後に Opus が書き換える）
  - `触るファイル:` と `削除するファイル:` は1行・カンマ区切り・バッククォートなし。`削除するファイル:` には、行を書き換えた既存ファイルを全部書く（3ファイルとも）
- 本文に `### GO記録` の見出しを置き、その下に「Opus が PO の実装承認と審査の後に記入する」とだけ書く（担当は GO の文を書かない。発行者・日時・GO原文・バックアップ確認は Opus が ADR-1003 の委譲名義で書く）。
- 本文に、§8 の写しはマージ後に PO が行うことと、この試験は CI で動かず §5-2 の手元実行が証拠であること（F5）を書く。
- 実在しないパスをバッククォートで書かない（ホームの `.claude/` のパスはバッククォートに入れない）。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（2分以上かかる。Bash の timeout は 240000 以下にする）。

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-5 の出力／PR の URL／生出力のパス（/tmp/CC報告ファイル/an-stage1/）／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

END OF CARD
