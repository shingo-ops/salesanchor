# 実装カード 段2-2 — 目次から届くかを調べる検査（警告だけ）を足す

> この文書は何か：doc-agenda-nav 段2 の後半の作業指示書です。目次 docs/INDEX.md（段2-1 で新設）を起点に、手順書が「入口 → 目次 → 章 → 末端」の3段以内で届くか、届かない文書・「いつ読むか」の空欄・行き先の無いリンクが無いかを数える検査を作り、PR ごとに走る CI に警告だけで載せます。止める（失敗にする）のは段5で、連続5回の PR で警告0件になってからです。

- 設計: docs/handoff/doc-agenda-nav/design.md §6（:159 目次から辿れる・:160 同じ決まりを2か所に書かない）・§7（:326-327 守り手と数え方）・§8（段2・段5の行）、docs/handoff/doc-agenda-nav/unreachable-list.md §1（辺の定義）・§4（フォルダ登録）
- 対象ADR: ADR-1040（Proposed）。関連: ADR-076
- 状態: 設計は審査済み（PR #4649）。PO の実装承認: 2026-10-23「1」（Opus が示した選択肢1「誤作動直し、目次の新設、決まりの引っ越しまでを順に進めてよい」への返事）
- 段2-1 は PR #4697（2026-10-23T11:42:20Z マージ済み 3bed6a5f2・main に docs/INDEX.md がある）
- 危険便（ADR-136 の危険パス）: いいえ（新しい workflow 1本と docs/ 配下だけ。deploy.yml・workflow-lint.yml・migrations・scripts は触らない。必須チェックへの登録はしない＝段5で PO に別に聞く）
- 作業の最初に、作業場所で `./scripts/dev/executor-preflight.sh` を実行し、exit 0 を確かめる（0 でなければ BLOCKED:）
- 担当: 実装と確かめは Sonnet（model "sonnet"）、審査は Opus（reviewer を model "opus" で新しく起こす）、マージは Opus

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード doc-agenda-nav 段2-2 の実行結果である」と書くこと。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | このカードで効く決まり | 反映 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・報告に無い出力を成功と扱わない | ○（§5・§9・§10） |
| guards/01-read.md | `git diff` は merge-base 起点 | ○（§5-6） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは同一行カンマ区切り | ○（§9） |

## 1. 範囲

入れる: §3 の2ファイル（検査の台本と workflow）と、このカードの報告欄。

入れない（Opus の判断と理由）:
- 設計 :160・:326 の「CLAUDE.md と AGENTS.md の見出しの重複」「各 CLAUDE.md の @AGENTS.md 行」「安全見出しの存在」の3検査は、入口を入れ替える段3c のカードで足す。理由: 今の入口は入れ替え前なので、3検査は今入れても入れ替えまで必ず警告になり、段5の昇格条件「連続5回の PR で0件」の数え始めが段3c 以降にずれるだけで情報が増えない。また「安全見出し」の名前は段3c の案文で決まるため、今は書けない。
- 必須チェック（ruleset）への登録・失敗への昇格（段5）。
- 警告が出た文書の修正（数が分かってから別の便で直す。§5-3 の出力を段5の基準値にする）。

## 2. 前提の事実（Opus が 2026-10-23 に作業場所の実物で確かめた）

| # | 事実 | 出典 |
|---|---|---|
| F1 | 辺の定義: 本文中の「.md で終わるパス文字列」とリンク記法の行き先をすべて辺として幅優先で辿る（相対は書いた文書のフォルダ基準、見つからなければリポジトリ根基準も試す） | unreachable-list.md §1 :7、~/CC報告ファイル-keep/agenda-nav-20261022/unreach/reach.py :13-35（variant any） |
| F2 | 目次にフォルダとして登録された場所の直下の文書は届くとみなす | design.md :159、unreachable-list.md §4 |
| F3 | 末端（段数を数える文書）は docs/specs/ の1段下のフォルダ直下の README.md（例 docs/specs/inbox/README.md）と docs/ai-agents/*.md。テーマのフォルダ内の README.md 以外は子文書として段数を数えない。合格は「入口→目次→章→末端 = 3段以内」 | design.md :34・:159、docs/specs/doc-agenda-nav/kgi.md K5 |
| F4 | 「いつ読むか」を見る目次は docs/INDEX.md と docs/specs/README.md の表 | design.md :159 |
| F5 | 段2-1 の時点で、目次を起点に variant any で辿ると docs/specs 306本・docs/ai-agents 34本のうち届かないのは ai-agents の lessons.d 19本だけ（フォルダ規則 F2 を入れる前の数） | /tmp/CC報告ファイル/an-stage2/impl/5-7-any.txt :3-6 |
| F6 | 既存の検査 CI の書き方: paths を使わず常時実行、`runs-on: ubuntu-latest`、`actions/checkout@v5`。Python は `actions/setup-python@v5` に `python-version: '3.12'` | .github/workflows/check-claude-size.yml :3-17、.github/workflows/api-contract-check.yml :17-19 |
| F7 | 警告件数は job の要約（`$GITHUB_STEP_SUMMARY`）に1行で出す作りにする。昇格の判定は `gh run list --workflow doc-index-reachability.yml --event pull_request --limit 5` の5件で数える | design.md :327、前例 .github/workflows/brand-asset-monitor.yml :103 |
| F8 | 台本の置き場所は docs/handoff/doc-agenda-nav/（設計で決定済み） | design.md :33・:159 |

## 3. 触るファイル（これ以外は触らない）

- 新設: `docs/handoff/doc-agenda-nav/check_doc_index.py`
- 新設: `.github/workflows/doc-index-reachability.yml`
- 変更: `docs/handoff/doc-agenda-nav/card-stage2b.md`（このカード。担当は §11 報告欄の追記だけ）

## 4. 作り方

### 4-1. check_doc_index.py（Python 3.12・標準ライブラリだけ。`python3 -I` で動くこと）

使い方: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . [--strict]`

1. 対象の一覧: `git -C ROOT ls-files -z` の結果（作業ツリーのファイルを読む。git show は使わない）。
2. 起点: 入口6ファイル（CLAUDE.md・AGENTS.md・frontend/CLAUDE.md・frontend/AGENTS.md・backend/CLAUDE.md・backend/AGENTS.md）を段数0、docs/INDEX.md を段数1 とする（入口から目次へのリンクは段3c で入る。それまでは目次を1段目として扱う）。docs/INDEX.md が無ければ `ERROR no docs/INDEX.md` を出して exit 2。
3. 辺: F1 の定義どおり（reach.py の variant any の targets 関数と同じ取り方。外部 URL・`#` だけのリンクは辺にしない）。加えて F2: docs/INDEX.md の中のリンク記法の行き先がフォルダ（末尾 `/`、または一覧にそのフォルダ配下のファイルがある）なら、そのフォルダ直下の .md すべてへ辺を張る。
4. 幅優先で .md だけを辿る（.md 以外のファイルは届いた扱いにするが、その中は読まない）。
5. 出す行（1行1件。並びはパスの辞書順）:
   - `UNREACHED docs/specs/inbox/kgi.md` の形: docs/specs/ と docs/ai-agents/ 配下の .md で届かないもの
   - `DEEP 4 docs/specs/inbox/README.md` の形: F3 の末端で段数が 3 を超えるもの
   - `BLANK_WHEN docs/specs/README.md:12` の形: docs/INDEX.md と docs/specs/README.md の表のデータ行で、「いつ読むか」の列が空のもの。列は見出し行の中から「いつ読むか」という名前で探す（列番号を決め打ちしない）。見出しが見つからなければ `NO_WHEN_COLUMN docs/INDEX.md` の形の1行を出す
   - `BROKEN_LINK docs/INDEX.md:9 nothing-here.md` の形: docs/INDEX.md・入口6ファイル・docs/specs/ 配下と docs/ai-agents/ 配下の .md に書かれたリンク記法のうち、外部 URL・`#` だけ・`mailto:` 以外で、行き先（`#` 以降を除く）がファイルにもフォルダにも無いもの
   - 最後に `SUMMARY unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=5 warnings=7` の形の1行（warnings は5つの合計）と、末端の最大段数を `MAX_DEPTH_TERMINAL 3` の形の1行
6. 終わり方: 通常は exit 0。`--strict` のときは warnings が1以上なら exit 1（段5で使う。今の workflow では付けない）。内部の誤り（ファイルが読めない等）は exit 2。

（上の数字とパスは形を示す例。）

### 4-2. .github/workflows/doc-index-reachability.yml

- `name: Doc Index Reachability (warning)`
- 起動: `on: pull_request: branches: [main]`（paths は付けない＝F6 と同じ理由で常時実行）
- job 名 `check`、`name: doc index reachability (warning only)`、`runs-on: ubuntu-latest`
- 手順: `actions/checkout@v5` → `actions/setup-python@v5`（`python-version: '3.12'`）→ 実行の step:
  ```
  python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . | tee /tmp/doc-index.txt
  echo "doc-index: $(grep '^SUMMARY' /tmp/doc-index.txt)" >> "$GITHUB_STEP_SUMMARY"
  ```
  bash の `set -o pipefail` を有効にする（`shell: bash` を明示。台本が exit 2 なら job を失敗させる＝壊れたことに気づくため。警告だけなら exit 0 で緑）。
- `continue-on-error` は付けない（警告では exit 0 なので不要）。必須チェックには登録しない。

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は /tmp/CC報告ファイル/an-stage2b/impl/ に保存）

5-1. `python3 -I -m py_compile docs/handoff/doc-agenda-nav/check_doc_index.py` が exit 0。
5-2. 作業場所（HEAD）で `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` を実行し、全文を保存。exit 0 であること。
5-3. 5-2 の出力の SUMMARY と MAX_DEPTH_TERMINAL を報告に書く（件数が0でなくても合否にしない。段5の基準値になる）。UNREACHED が0件であること（F5 と F2 から期待。0でなければ一覧を貼って NEEDS_DECISION:）。
5-4. 止める例の試験: 作業場所を `git worktree add --detach /tmp/CC報告ファイル/an-stage2b/neg HEAD` で写し、写しの中だけで次の3つを変えて台本を実行し、それぞれ警告が増えることを示す。終わったら `git worktree remove --force /tmp/CC報告ファイル/an-stage2b/neg`。
   - docs/specs/README.md のデータ行1行の「いつ読むか」を空にする → BLANK_WHEN が1増える
   - docs/INDEX.md に `[x](nothing-here.md)` を1行足す → BROKEN_LINK が1増える
   - docs/specs/README.md から1テーマの行を消し、そのテーマの README を他に参照が無いものにする（どの行を選んだか書く。参照が残って届いてしまう場合は別の行を選ぶ） → UNREACHED が増える
   - `--strict` を付けると exit 1 になること
5-5. `actionlint .github/workflows/doc-index-reachability.yml` を実行（無ければ `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint:latest -color .github/workflows/doc-index-reachability.yml`。どちらも使えなければその事実を書き、CI の workflow-lint の結果で見る）。
5-6. `git status --short` と `git diff "$(git merge-base origin/main HEAD)" --stat`（期待: §3 のファイルだけ）。
5-7. PR を作った後、`gh pr checks` に作った PR の番号と `--repo shingo-ops/salesanchor` を付けたもの を1回だけ実行して貼る（待たない）。

## 6. 分岐ごとの対処

- 5-3 で UNREACHED が出る → 一覧を貼って NEEDS_DECISION:（台本の誤りか文書の未登録かを Opus が決める）。
- 5-4 で警告が増えない → 台本の誤り。直して 5-2 からやり直す（2回直しても増えなければ BLOCKED:）。
- 見張りや自動判定に止められた → 言い換えず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 台本が標準ライブラリだけで動き、HEAD で exit 0 | §5-1・§5-2 |
| 届かない specs・ai-agents の文書が 0 件（KGI-4 の CI による観測） | §5-3 |
| 4つの警告（届かない・3段超え・「いつ読むか」空欄・行き先の無いリンク）が、それぞれ壊した写しで実際に出る | §5-4 |
| workflow が PR で走り、警告だけでは緑のまま、要約に SUMMARY が1行出る | §5-7 と PR の Checks 画面の要約 |
| 触ったのは §3 のファイルだけ | §5-6 |

## 8. 戻し方

この PR の revert を main にマージする（workflow と台本が消えるだけ。他の検査には影響しない）。

## 9. PR

- 作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-doc-agenda-nav-stage2b は Opus が `bash scripts/new-worktree.sh release/doc-agenda-nav-stage2b`（origin/main 3bed6a5f2 = #4697 マージ後を起点・2026-10-23）で作成済みで、このカードのコミットも載っている。担当は作り直さない。以後はすべてそこに `cd` してから行う。
- push は `git push -u origin release/doc-agenda-nav-stage2b`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/doc-agenda-nav-stage2b -1 --oneline` で確かめる。
- PR は `scripts/gh-pr-create-safe.sh` で作る。先に Write ツールで本文ファイル `/tmp/CC報告ファイル/an-stage2b/pr-body.md` を作り、`--body-file` で渡す。作成前に `gh auth status` で `shingo-cc` 名義を確かめる。ready で作る。base は main。担当はマージしない。
- 本文は PR テンプレートに沿う。`### 標準ワークフロー確認` に設計・unreachable-list.md・このカード、`対象ADR: ADR-1040（関連: ADR-076）`、`設計仕様書（あるべき姿）: docs/specs/doc-agenda-nav/README.md`、`PO承認: 「1」（2026-10-23）`、`Opus 審査記録: コード審査はこれから` を書く。§5-3 の SUMMARY 行を本文に貼る（段5の基準値）。
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（Bash の timeout は 240000 以下）。

## 10. 報告

- 完了報告に: 冒頭の受領文／§5-1〜5-7 の出力（長いものはファイルのパス）／PR の URL／判断を要した点（事実のみ）
- 停止したとき: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 委任の定型: sleep しない／ファイルの作成と編集は Write/Edit ツールで行う／PR 作成前に validate-pr-body.sh で exit 0／フックや自動判定に止められたら言い換えて再試行しない

## 11. 報告欄（担当が追記）

- 受領: 本報告はカード doc-agenda-nav 段2-2 の実行結果である
- 5-1 py_compile exit 0 / 5-2 HEAD で exit 0
- 5-3 基準値: `SUMMARY unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10` / `MAX_DEPTH_TERMINAL 4`（DEEP は docs/ai-agents/adr-template.md と docs/specs/ledger-guard/README.md、いずれも 4）
- 5-4 壊した写し: BLANK_WHEN +1（specs/README.md:15）／BROKEN_LINK +1（INDEX.md に nothing-here.md）／UNREACHED 0→3（reaper-auto-cleanup の行を削除）／--strict で exit 1
- 5-5 actionlint exit 0
- 判断: workflow に timeout-minutes: 5 を足した（PR テンプレートの workflows 欄の決まり）
- 生出力: /tmp/CC報告ファイル/an-stage2b/impl/

END OF CARD
