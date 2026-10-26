# 証拠 便M1（生出力）

## P1〜P6（実装前・HEAD 44708e806）
```
## P1
.github/workflows/doc-index-reachability.yml:26:          python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . | tee /tmp/doc-index.txt
## P2
215 docs/handoff/doc-agenda-nav/check_doc_index.py
使い方: python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . [--strict]
    print("SUMMARY unreached=%d deep=%d blank_when=%d no_when_column=%d broken_link=%d warnings=%d"
          % (len(unreached), deep, blank, no_when, broken, warnings))
    print("MAX_DEPTH_TERMINAL %d" % max_depth)
    if a.strict and warnings >= 1:
        sys.exit(1)
## P3
## 不可逆操作は必ず PO 確認
## VPS 直作業禁止（技術的にも制限付き鍵のみ）
- `develop` / `main` への直接コミット禁止。`release/*` → `main` は PR 経由（直push禁止・Branch Protection で強制）
## P4
CLAUDE.md:
@AGENTS.md
frontend/CLAUDE.md:
@AGENTS.md
backend/CLAUDE.md:
@AGENTS.md
## P5
-- i18n
frontend/AGENTS.md:21:## i18n 強制（ADR-027）
-- ハードコード
frontend/AGENTS.md:23:全 UI 文字列は `t("key")` 経由（JSX / aria-label / placeholder / title すべて）。`ja.json` と `en.json` は同一キー必須。ハードコード日本語は絶対禁止。詳細: `docs/adr/ADR-027-ui-internationalization.md`
frontend/AGENTS.md:24:JSX / TS(X) 内の日本語ハードコードは ESLint ルール `local/no-japanese-literal`（ADR-027）が自動検出。
-- 不可逆
AGENTS.md:7:- **PO**: しんごさん（`shingo-ops`）— 本番アクセス・ADR起案・不可逆操作の最終判断
AGENTS.md:15:## 不可逆操作は必ず PO 確認
-- 推測
AGENTS.md:44:- 手順や作業方法を答える・計画する前に、必ず目次 `docs/INDEX.md` を開き、章→末端の順にたどって該当する手順書を読む（記憶や推測だけで答えない）
-- executor-preflight
AGENTS.md:41:- 実行役は作業開始前に必ず `./scripts/dev/executor-preflight.sh || exit 1` を実行する
-- squash
-- worktree
AGENTS.md:34:- 作業前に必ず（例外なし） `bash scripts/new-worktree.sh release/<topic>` で `origin/main` 起点の作業場所を `~/worktrees` 配下に作る（`<topic>` は作業内容を英語で簡潔に）
-- 日本語
frontend/AGENTS.md:23:全 UI 文字列は `t("key")` 経由（JSX / aria-label / placeholder / title すべて）。`ja.json` と `en.json` は同一キー必須。ハードコード日本語は絶対禁止。詳細: `docs/adr/ADR-027-ui-internationalization.md`
frontend/AGENTS.md:24:JSX / TS(X) 内の日本語ハードコードは ESLint ルール `local/no-japanese-literal`（ADR-027）が自動検出。
frontend/AGENTS.md:31:コメント内の日本語は OK。JSX / 文字列リテラル内は必ず `t()` 経由にすること。
backend/AGENTS.md:66:- **カラムコメント**: 新テーブル作成時は全カラムに `COMMENT ON COLUMN` を付与すること。後から見直しても意味が分かる日本語説明を書く
-- file:line
## P6
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## 実装後の最終確認（実装 commit 63398afb4）
```
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## V1 docs/INDEX.md から手順書への1行を消す
```
削除した行: docs/INDEX.md:
# 目次（AI 向け指示文書）

> 入口（AGENTS.md・CLAUDE.md）には安全の決まりだけを置く。作業の型と手順書は、この目次から「章 → 末端」の順にたどり、必要になったときに読む。
> この目次の設計: [doc-agenda-nav](specs/doc-agenda-nav/README.md)（ADR-1040）。行を足すときは表の書式に合わせ、「いつ読むか」を空欄にしない。

| 章 | 末端（読むもの） | いつ読むか |
|---|---|---|
| A 開発の進め方 | [標準開発フロー](STANDARD-WORKFLOW.md) | 便（1回の作業）を始める前 |
| A 開発の進め方 | [実行役のチェックリスト](ai-agents/executor-checklist.md) | 実装・調査の作業前、commit の前、PR を作る前 |
| A 開発の進め方 | [ブランチ運用](specs/branch-operations/README.md) | ブランチと作業場所を作る前、PR を作る・マージする前 |
| A 開発の進め方 | [並行ターミナルの使い方](PARALLEL_TERMINAL_GUIDE.md) | 作業場所（worktree）を複数並べて作業するとき |
| A 開発の進め方 | [設計パートナーの手順](ai-agents/design-partner.md) | 設計の担当（Planner・Architect）を始めるとき |
| A 開発の進め方 | [実装役への指示の定型文](ai-agents/executor-preamble.md) | 実装役に作業を渡す指示を書くとき |
| A 開発の進め方 | [教訓メモのフォルダ](ai-agents/lessons.d/)（まとめて読む: `bash scripts/lessons-view.sh`） | 設計・審査で、過去の失敗を確かめるとき |
| A 開発の進め方 | [Codex の運用（役割分担・AEON・UI/UX補助・引き継ぎ）](ai-agents/codex-operations.md) | 役割分担を確かめるとき、Codex で作業する・Codex に作業を渡すとき、会話をまたいで作業を引き継ぐとき |
| A 開発の進め方 | [開発コマンド（venv・セットアップ・実行）](ai-agents/dev-commands.md) | 手元で venv を作るとき、frontend・backend の検査や試験を動かすとき |
| A 開発の進め方 | [KPI の正本](ai-agents/kpi.md) | KPI を決める・測るとき |
| A 開発の進め方 | [ADR の下書きの雛形](ai-agents/adr-template.md) | AI の運用ルールを ADR として起案するとき |
| B 設計仕様書 | [設計仕様書の索引](specs/README.md) | 新しいテーマを始める前、索引に載る領域に触れる前 |
| B 設計仕様書 | 業務の仕様書 `salesanchor_system_overview.docx` 他 3 冊（リポジトリ外・PO から入手） | 業務の仕様（画面・データの意味）を確かめるとき |
| C 設計判断（ADR） | [機能から ADR を引く索引](adr/FEATURE-INDEX.md) | 現状把握（recon）で既存の設計判断を探すとき |
| C 設計判断（ADR） | [ADR の一覧](adr/README.md) | ADR を足す・変えるとき（一覧は `node scripts/generate-adr-index.js` で作り直してコミットする。CI「ADR index is up to date」が必須） |
| D 領域別ルール | [frontend の決まり](../frontend/AGENTS.md) | frontend/ のファイルを触るとき |
| D 領域別ルール | [backend の決まり](../backend/AGENTS.md) | backend/ のファイルを触るとき |
| E 商品マスタ登録 | [商品マスタ登録の決まり](specs/product-master/registration-rules.md) | 商品マスタに商品を登録する・登録内容を直すとき |
| F 運用・本番 | [サーバーで使うコマンド](ops/runner-commands.md) | VPS・本番のコンテナで作業するとき |
| F 運用・本番 | [自前の実行機の資格情報の落とし穴](ops/self-hosted-runner-credential-trap.md) | GitHub の自前の実行機（self-hosted runner）を触るとき |
| F 運用・本番 | [手順書のフォルダ](runbooks/) | 監視・デプロイ・障害対応の手順を探すとき |

## このファイルにルールを追加する前に

> この節は入口から写した決まり（doc-agenda-nav 段3b）。節の中の「このファイル」は入口の AGENTS.md を指す（段3c で本文の正本を CLAUDE.md から AGENTS.md へ移した）。

以下に順番に答える:

1. CI / ESLint / Husky が既に強制しているか？ → YES: **書かない**（CSS変数・アイコン・デザイントークン規約はこれ）
2. `frontend/` だけに関係するか？ → YES: **`frontend/AGENTS.md`** に追加
3. `backend/` だけに関係するか？ → YES: **`backend/AGENTS.md`** に追加
4. frontend と backend 両方に等しく関係するか？ → YES: **このファイル** に追加（不可逆操作・ブランチ運用 等）
5. Generator / Evaluator / Reviewer の動作手順か？ → YES: **`~/.claude/agents/`** の該当ファイルに追加
6. `~/.claude/rules/` に同等の内容が既にあるか？ → YES: **書かない**（Git workflow・coding-style 等）
7. 全セッションで Claude が知る必要があるか？ → NO: **書かない**（ADRリンクか docs/ 参照で十分）
8. 上記をすべて通過した場合のみ追加。既存セクションへの統合を最優先（新セクション追加は最後の手段）。
**入口の AGENTS.md が 80 行、CLAUDE.md が 10 行、この目次が 60 行を超えたら `frontend/scripts/check-claude-size.js` がコミットをブロックする。**
-- 変えた後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
UNREACHED docs/ai-agents/lessons.d/20260720-checkout-staged.md
UNREACHED docs/ai-agents/lessons.d/20260720-required-checks-change.md
UNREACHED docs/ai-agents/lessons.d/20260721-deploy-not-done.md
UNREACHED docs/ai-agents/lessons.d/20260721-moving-target-freeze.md
UNREACHED docs/ai-agents/lessons.d/20260721-process-hardening-recon.md
UNREACHED docs/ai-agents/lessons.d/20260721-server-resource-lessons.md
UNREACHED docs/ai-agents/lessons.d/20260722-design-partner-preflight.md
UNREACHED docs/ai-agents/lessons.d/20260724-card-output-markers.md
UNREACHED docs/ai-agents/lessons.d/20260724-merge-gate-mechanics.md
UNREACHED docs/ai-agents/lessons.d/20260725-card-hygiene.md
UNREACHED docs/ai-agents/lessons.d/20260725-merge-waits.md
UNREACHED docs/ai-agents/lessons.d/20260727-prnum-adr-index.md
UNREACHED docs/ai-agents/lessons.d/20260728-go-record-labels.md
UNREACHED docs/ai-agents/lessons.d/20260728-precheck-guards.md
UNREACHED docs/ai-agents/lessons.d/20260831-card-design-failures.md
UNREACHED docs/ai-agents/lessons.d/20260904-discord-reaction-recon.md
UNREACHED docs/ai-agents/lessons.d/20260907-note-ja-merge-cleanup.md
UNREACHED docs/ai-agents/lessons.d/20260916-haiku-readonly-governance.md
UNREACHED docs/ai-agents/lessons.d/20261015-go-record-delegated-issuer.md
NO_WHEN_COLUMN docs/INDEX.md
DEEP 4 docs/ai-agents/adr-template.md
DEEP 4 docs/ai-agents/dev-commands.md
SUMMARY unreached=19 deep=2 blank_when=0 no_when_column=1 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=22
MAX_DEPTH_TERMINAL 4
rc=1
-- 戻した後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## V2 AGENTS.md:23 の見出しから「VPS 直作業禁止」を消す
```
## （技術的にも制限付き鍵のみ）
-- 変えた後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
SAFETY_MISSING VPS 直作業禁止
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=1 agents_import_missing=0 warnings=1
MAX_DEPTH_TERMINAL 3
rc=1
-- 戻した後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## V3 AGENTS.md の最後に i18n の行を足す
```
-- 変えた後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
DUP_WORD i18n AGENTS.md:46,frontend/AGENTS.md:21
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=1 safety_missing=0 agents_import_missing=0 warnings=1
MAX_DEPTH_TERMINAL 3
rc=1
-- 戻した後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## V4 AGENTS.md の最後に 日本語 の行を足す
```
-- 変えた後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
DUP_WORD 日本語 AGENTS.md:46
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=1 safety_missing=0 agents_import_missing=0 warnings=1
MAX_DEPTH_TERMINAL 3
rc=1
-- 戻した後
$ python3 -I scripts/ci/check_doc_index.py --root . --strict; echo rc=$?
SUMMARY unreached=0 deep=0 blank_when=0 no_when_column=0 broken_link=0 dup_words=0 safety_missing=0 agents_import_missing=0 warnings=0
MAX_DEPTH_TERMINAL 3
rc=0
```

## 旧パス・差分
```
$ test ! -e docs/handoff/doc-agenda-nav/check_doc_index.py && echo ok
ok
$ grep -rn check_doc_index .github scripts frontend/scripts
.github/workflows/doc-index-reachability.yml:30:          python3 -I scripts/ci/check_doc_index.py --root . --strict | tee /tmp/doc-index.txt
scripts/ci/check_doc_index.py:4:使い方: python3 -I scripts/ci/check_doc_index.py --root . [--strict]
$ grep -rn "warning only\|doc-agenda-nav/check_doc_index" docs .github
docs/handoff/doc-agenda-nav/card-stage3a.md:45:| F8 | 目次から届くかの検査 docs/handoff/doc-agenda-nav/check_doc_index.py は PR #4698 で main に入った後にこの作業場所を作る（作業場所の起点に台本がある） | PR #4698 |
docs/handoff/doc-agenda-nav/card-stage3a.md:207:5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、起点で同じものを実行した結果と SUMMARY を並べて書く。期待: unreached・blank_when・no_when_column・broken_link が起点より増えない。新設2本が UNREACHED・DEEP・BROKEN_LINK に出ない。
docs/handoff/doc-agenda-nav/card-stage3c-swap.md:198:5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（F10）と並べて書く。期待は、どの数も増えないこと。
docs/handoff/doc-agenda-nav/card-stage2b.md:50:- 新設: `docs/handoff/doc-agenda-nav/check_doc_index.py`
docs/handoff/doc-agenda-nav/card-stage2b.md:58:使い方: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . [--strict]`
docs/handoff/doc-agenda-nav/card-stage2b.md:78:- job 名 `check`、`name: doc index reachability (warning only)`、`runs-on: ubuntu-latest`
docs/handoff/doc-agenda-nav/card-stage2b.md:81:  python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . | tee /tmp/doc-index.txt
docs/handoff/doc-agenda-nav/card-stage2b.md:89:5-1. `python3 -I -m py_compile docs/handoff/doc-agenda-nav/check_doc_index.py` が exit 0。
docs/handoff/doc-agenda-nav/card-stage2b.md:90:5-2. 作業場所（HEAD）で `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` を実行し、全文を保存。exit 0 であること。
docs/handoff/doc-agenda-nav/card-stage3b-runner.md:117:5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、SUMMARY 行を起点の値（PR #4700 のマージ時 = 起点 3b8124562 の値 `unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待: どの数も増えない。
docs/handoff/doc-agenda-nav/card-stage3c-prep.md:159:5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待は、どの数も増えないこと。
grep: docs/handoff/doc-agenda-nav/evidence-maintain-m1.md: input file is also the output
docs/handoff/doc-agenda-nav/card-stage3b-workflow.md:110:5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待: どの数も増えない。
docs/handoff/doc-agenda-nav/card-maintain-m1.md:12:| P2 | docs/handoff/doc-agenda-nav/check_doc_index.py の行数・:4・:206-210 | 215行。:4 が使い方の行。:206 が SUMMARY、:209 が `if a.strict and warnings >= 1:` |
docs/handoff/doc-agenda-nav/card-maintain-m1.md:16:| P6 | `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root . --strict; echo rc=$?` | rc=0（今の main は合格） |
docs/handoff/doc-agenda-nav/card-maintain-m1.md:23:- `git mv docs/handoff/doc-agenda-nav/check_doc_index.py scripts/ci/check_doc_index.py`。元の場所には何も残さない。
docs/handoff/doc-agenda-nav/card-maintain-m1.md:48:- job 名を `doc index reachability` にする（「(warning only)」を外す）。
docs/handoff/doc-agenda-nav/card-maintain-m1.md:72:- 旧パス・「warning only」を含む過去の記録（card-*.md・design.md の §32 以外の経緯）。`grep -rn "warning only\|doc-agenda-nav/check_doc_index" docs .github` の結果は証拠ファイルに貼るだけで直さない。
docs/handoff/doc-agenda-nav/card-maintain-m1.md:104:| 旧パスが残っていない | `test ! -e docs/handoff/doc-agenda-nav/check_doc_index.py` と P1 の grep を実装後にもう一度（workflow は新パスだけ） |
docs/handoff/doc-agenda-nav/card-stage3b-branchops.md:175:5-6. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存し、SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待: どの数も増えない。
docs/handoff/doc-agenda-nav/card-stage3b-index.md:54:| F5 | 目次の検査 docs/handoff/doc-agenda-nav/check_doc_index.py は、表の行（`\|` で始まる行）だけで「いつ読むか」の欄を数える（:161）。表の外の文は欄の数に入らない | check_doc_index.py:156-165 |
docs/handoff/doc-agenda-nav/card-stage3b-index.md:130:5-5. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（`unreached=0 deep=2 blank_when=0 no_when_column=0 broken_link=8 warnings=10`）と並べて書く。期待は、どの数も増えないこと。
docs/handoff/doc-agenda-nav/card-stage4.md:234:5-7. 目次から届くか: `python3 -I docs/handoff/doc-agenda-nav/check_doc_index.py --root .` の全文を保存する。SUMMARY 行を起点の値（F10）と並べて書く。期待は、どの数も増えないこと。
$ git diff --stat origin/main...HEAD
 .github/workflows/doc-index-reachability.yml       |  17 +++-
 docs/STANDARD-WORKFLOW.md                          |   2 +
 docs/adr/ADR-1040-doc-agenda-nav-entry-index.md    |   8 +-
 docs/handoff/doc-agenda-nav/card-maintain-m1.md    | 112 +++++++++++++++++++++
 docs/handoff/doc-agenda-nav/design.md              |   2 +-
 docs/specs/doc-agenda-nav/kgi.md                   |   1 +
 .../ci}/check_doc_index.py                         |  52 +++++++++-
 7 files changed, 182 insertions(+), 12 deletions(-)
```
