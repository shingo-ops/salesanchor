# recon: .claude/agents architect/reviewer の model を fable に変える PR

調査日 2026-10-12。基準は origin/main（worktree 作成時 HEAD ce15cb095）。worktree: /Users/tanizawashingo/worktrees/salesanchor/release-agents-model-fable（ブランチ release/agents-model-fable）。製品コード・agents 定義は未変更。

## preflight（./scripts/dev/executor-preflight.sh、worktree 内、exit 0）
```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [OK]   GitHub API 到達
[2/3] gh auth = shingo-cc
  [OK]   gh は shingo-cc
[3/3] git config user.name = shingo-cc
  [OK]   git user.name は shingo-cc
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
[G2.2 WARN] 本店(/Users/tanizawashingo/salesanchor)が origin/main より 1675 コミット遅れています
[G2.2 WARN] 本店に台帳以外の未保存 24 件あり — ff-pull不能の可能性。本店掃除便を検討してください
PREFLIGHT OK — 作業続行可
```
注記【事実】new-worktree.sh の末尾で claude 自動起動が `Error: Input must be provided either through stdin or as a prompt argument when using --print` で失敗したが、worktree 自体は作成済み。

## A. frontmatter と履歴（git show origin/main:）
```
.claude/agents/architect.md 1-8:
---
name: architect
description: Use this agent when a Planner package must be validated for implementation readiness before Generator receives it.
model: opus
tools: Read, Write, Edit, Bash, Grep, Glob
---

You are the **Architect** agent in the 4-stage pipeline (...)

.claude/agents/reviewer.md 1-8:
---
name: reviewer
description: Use after Generator to audit compliance with Planner, Architect, and PO Approval.
model: sonnet
---

You are the **Reviewer** in the pipeline:
```
【事実】reviewer.md には tools: 行なし（全ツール）。architect.md は 4行目 model: opus、reviewer.md は 4行目 model: sonnet。
```
git log -5 --format='%h %ad %s' --date=short -- .claude/agents/architect.md .claude/agents/reviewer.md
62fab633a 2026-06-06 docs(governance): ADR-113 2モード開発フロー + agent defs + CLAUDE.md更新
0ac577d48 2026-06-05 chore: ワークフロー再編 ADR-111 — 設計起点フロー v2 (#1677)
c88f89710 2026-05-30 feat: add aeon operation guide
eb7975852 2026-05-29 docs: standardize agent pipeline definitions
d5968e80d 2026-05-26 feat(dev-workflow): 作業開始時のworktree強制チェックを追加
```

## B. grep -n '^model:' .claude/agents/*.md
```
.claude/agents/architect.md:4:model: opus
.claude/agents/evaluator.md:4:model: sonnet
.claude/agents/planner.md:4:model: opus
.claude/agents/research.md:4:model: opus
.claude/agents/governance.md:4:model: sonnet
.claude/agents/generator.md:4:model: opus
.claude/agents/reviewer.md:4:model: sonnet
```
【事実】fable が既に入っている行はリポジトリ内 .claude/agents に無い。
【事実】別件: ユーザー側 ~/.claude/agents/architect.md:4 と reviewer.md:4 は既に `model: fable`（grep 生出力）。

## C. architect/reviewer とモデル名の同居（全37行、生出力 = 下記）
対象: AGENTS.md CLAUDE.md docs .claude .github scripts。ファイル別件数:
```
  17 docs/specs/design-system/design.md
   2 docs/handoff/migration-runner-redesign/design.md
   2 docs/handoff/hide-system-admin-role/design.md
   2 docs/handoff/gemini-extract-role-split/design.md
   2 docs/handoff/frontend-superadmin-dead-parts/design.md
   2 docs/handoff/design-system-recon/evidence-20260910/ay2f-design-appended.md
   1 docs/handoff/v102-gap-fill-review/design.md
   1 docs/handoff/predeploy-backup-db-filter/design.md
   1 docs/handoff/migration-runner-redesign/recon.md
   1 docs/handoff/migration-churn-guard/design.md
   1 docs/handoff/llm-usage-ledger/design.md
   1 docs/handoff/hide-system-admin-role/recon.md
   1 docs/handoff/gemini-extract-role-split/price-qty-resolver-design.md
   1 docs/handoff/frontend-superadmin-dup-pages/design.md
   1 docs/handoff/condition-box-by-product-category/design.md
   1 AGENTS.md
```
全文（各行 260 文字で切り詰め。全文は scratchpad の c.txt）:
```
AGENTS.md:10:- **Dev**: Claude Code / Sonnet (Hikky-dev) — 主Generator・実装・PR起票 | ChatGPT — Planner・Architect・Reviewer | Codex app / CLI — UI/UX補助・第二レビュー・Fallback
docs/handoff/condition-box-by-product-category/design.md:106:2. 段階1：Sonnet が実装し、PR を出す（DB の変更なし。`migrations/`・`.github/workflows/deploy.yml`・本番の scripts は含まない）。Reviewer の APPROVE と CI の通過の後、ADR-1003 の委任で Opus が GO を出し、マージする。反映後、新しい投稿で K1・K2 を確かめる。
docs/handoff/design-system-recon/evidence-20260910/ay2f-design-appended.md:4:AY-2e: PR #4092 merge 0caa64700137385bd45341e460b63cf772cd2a3b（2026-10-09T13:41:55Z、必須15/15成功）、Deploy 37938703727 success（headSha 0caa64700、13:41:58Z〜13:44:32Z）。本番の JS で `input w-full
docs/handoff/design-system-recon/evidence-20260910/ay2f-design-appended.md:69:Architect 自己審査（AY-2f）: APPROVE。根拠は次のとおり。同一AI（Opus）の自己審査で、独立した第二者のレビューではない。外部事例は不要（使われていないコードの削除のため）。
docs/handoff/frontend-superadmin-dead-parts/design.md:4:AY-2e: PR #4092 merge 0caa64700137385bd45341e460b63cf772cd2a3b（2026-10-09T13:41:55Z、必須15/15成功）、Deploy 37938703727 success（headSha 0caa64700、13:41:58Z〜13:44:32Z）。本番の JS で `input w-full`・`qty-input`・`manual
docs/handoff/frontend-superadmin-dead-parts/design.md:69:Architect 自己審査（AY-2f）: APPROVE。根拠は次のとおり。同一AI（Opus）の自己審査で、独立した第二者のレビューではない。外部事例は不要（使われていないコードの削除のため）。
docs/handoff/frontend-superadmin-dup-pages/design.md:89:Architect 自己審査（AY-2g）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（既存の Panel への一本化で、転送は既存の前例の型を使う）。
docs/handoff/gemini-extract-role-split/design.md:114:## 12. Architect 審査（Opus が自分で審査。独立した第二者によるレビューではない、2026-09-28）
docs/handoff/gemini-extract-role-split/design.md:251:## §Z Architect 審査（Opus が自分で審査。独立した第二者によるレビューではない）
docs/handoff/gemini-extract-role-split/price-qty-resolver-design.md:3:状態：**設計確定（PO 合意済み・2026-09-30）／Opus 自己審査済み／実装中（PR #3890）。Reviewer の指摘 R-1〜R-4 を反映済み**
docs/handoff/hide-system-admin-role/design.md:14:**担当**: Planner / Architect（Opus。同一 AI の自己審査）
docs/handoff/hide-system-admin-role/design.md:87:| 2 | 実装カードどおりに実装・試験（TDD）。security-reviewer と code-reviewer | Sonnet |
docs/handoff/hide-system-admin-role/recon.md:13:**担当**: architect（調査は Sonnet、照合は Opus）  
docs/handoff/llm-usage-ledger/design.md:3:- 状態: 設計案（Opus）→ Architect 審査（Opus 自己審査、独立レビューではない）→ PO 方針承認済み（2026-09-30「y」、原文は PR の GO記録）
docs/handoff/migration-churn-guard/design.md:72:| 7 | Reviewer指摘（引用識別子の誤検出、文字列/dollar-quote非対応のコメント除去）を修正。回帰テスト5ケース（i〜m）追加・実行 | Sonnet |
docs/handoff/migration-runner-redesign/design.md:9:**担当**: 設計担当 Opus（Planner／Architect 兼任。同じ AI による自己審査であり、独立した第三者レビューではない）  
docs/handoff/migration-runner-redesign/design.md:116:| 1 | 段階0の実装カード作成 → 実装 → Reviewer → CI → GO（PO 本人または委任 GO の範囲を ADR-1003 で確認）→ マージ・反映 | Opus（カード・審査）／Sonnet（実装） |
docs/handoff/migration-runner-redesign/recon.md:83:- 注：本 §4 と §3 の本番の数字は設計担当 Opus が読み取りで確認したもので、Architect 審査は本番に触れていない（第三者による再確認は未実施）。
docs/handoff/predeploy-backup-db-filter/design.md:105:- マージには GO が必要。deploy.yml の変更は ADR-1003 の例外（docs/handoff/go-record-transcription/opus-delegation.md「例外」）に当たらないため、必須CI通過と Reviewer APPROVE を確認したうえで、委任 GO（POの委任に基づくClaude Opus発行）で進める（PO 2026-10-03「PRマージ、デプロイま
docs/handoff/v102-gap-fill-review/design.md:132:## 9. 審査（Architect・Opus 自己審査）
docs/specs/design-system/design.md:2489:AY-2b: PR #4078 merge 468d49eddad56800ce305e4d41ac7ea221b27be3（2026-10-09T11:23:27Z、必須15/15成功）、Deploy 37923425874 success（headSha 468d49edd、11:23:30Z〜11:25:58Z）。本番 CSS index-DCunA6lC.css に `comp-input--login` 2・`.form-gr
docs/specs/design-system/design.md:2565:AY-2c: PR #4081 merge afa02b990cb9b371a5cadc1ab4ba881c88e6bf3a（2026-10-09T11:51:01Z、必須15/15成功）、Deploy 37926270574 success（headSha afa02b990、11:51:04Z〜11:53:39Z）。本番 CSS index-BJW2PBHr.css に `form-row input:not(` 0 件、`.for
docs/specs/design-system/design.md:2624:AY-2d: PR #4087 merge 1245dbac66d581a9344f648fa081e999aee66c9b（2026-10-09T12:48:32Z、必須15/15成功）、Deploy 37932481186 success（headSha 1245dbac6、12:48:35Z〜12:51:09Z）。本番の JS（index と遅延読み込みの全チャンク）で `className:"input"` 0 件。/regis
docs/specs/design-system/design.md:2690:AY-2e: PR #4092 merge 0caa64700137385bd45341e460b63cf772cd2a3b（2026-10-09T13:41:55Z、必須15/15成功）、Deploy 37938703727 success（headSha 0caa64700、13:41:58Z〜13:44:32Z）。本番の JS で `input w-full`・`qty-input`・`manual-record-datetime
docs/specs/design-system/design.md:2755:Architect 自己審査（AY-2f）: APPROVE。根拠は次のとおり。同一AI（Opus）の自己審査で、独立した第二者のレビューではない。外部事例は不要（使われていないコードの削除のため）。
docs/specs/design-system/design.md:2867:Architect 自己審査（AY-2g）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（既存の Panel への一本化で、転送は既存の前例の型を使う）。
docs/specs/design-system/design.md:2890:GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer の判定は APPROVE（LOW 1）。
docs/specs/design-system/design.md:2937:- GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer の判定は APPROVE（MEDIUM 1・LOW 1 は対応済み）。
docs/specs/design-system/design.md:2988:Architect 自己審査（AY-2h）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（AY-2g と同じ型）。
docs/specs/design-system/design.md:3020:- GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer の判定は APPROVE（指摘0件）。
docs/specs/design-system/design.md:3102:Architect 自己審査（AY-2i）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（AY-2g と同じ型）。
docs/specs/design-system/design.md:3155:- GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer の判定は APPROVE（LOW 2件）。
docs/specs/design-system/design.md:3234:Architect 自己審査（AY-2j）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（社内の金型 Drawer と、その onRowClick の前例をそのまま使うため）。
docs/specs/design-system/design.md:3292:- GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer の判定は APPROVE（LOW 2件）。
docs/specs/design-system/design.md:3350:Architect 自己審査（AY-2k）: APPROVE（条件: 実画面で並びと幅の保持を実装後に確認）。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（既存の金型を前例どおり使うため）。
docs/specs/design-system/design.md:3390:- GO: POの委任に基づくClaude Opus発行（ADR-1003）。Reviewer の判定は APPROVE（LOW 2件）。
docs/specs/design-system/design.md:3435:Architect 自己審査（AY-2l）: APPROVE。同一AI（Opus）による自己審査であり、独立した第二者のレビューではない。外部事例は不要（前例 #4098・#4107 と同じ削除の型）。
```
【事実】.claude/・.github/・scripts/ 配下でヒットは 0 件。設定・CI・フックがモデル名を役割に結び付ける箇所は見つからなかった。
【事実】AGENTS.md:10 は「ChatGPT — Planner・Architect・Reviewer」（Claude のモデル割当ではなく Codex/ChatGPT 側の役割表）。
【事実】docs/handoff 配下と docs/specs/design-system/design.md の件は過去の作業記録（「Architect 審査は Opus 自己審査」等）。
【事実】docs/agents/architect.md:4 `Model: GPT-5.5`、docs/agents/reviewer.md:4 `Model: GPT-5`（Codex 側定義。grep 生出力）。.claude/agents とは別系統。
【事実】docs/specs/agent-complete-design/README.md:45 と design.md:143-151 に「設計パートナー（Fable）」の記述あり（Claude Code の model 設定ではなく人間側の役割名）。

## D. .claude/agents を参照するもの
```
.claude/agents/governance.md:123:| **governance.md セクション網羅** | `grep -c "^## [A-F]\." ~/.claude/agents/governance.md` | 6（A〜F のセクションが全て存在する） |
.github/workflows/aeon-script-check.yml:19:      - '.claude/agents/*.md'
.github/workflows/aeon-script-check.yml:34:      - '.claude/agents/*.md'
.github/workflows/aeon-script-check.yml:70:            f=".claude/agents/${role}.md"
AGENTS.md:66:- `.claude/agents/*` が runtime の正本
AGENTS.md:276:  .claude/agents/generator.md 等の常設指示とカードが矛盾したら、カードが優先。
CLAUDE.md:48:- **`.claude/agents/` 変更前は必ず `git pull` で最新取得**（複数セッション同時書き込みによる上書き防止）
CLAUDE.md:113:5. Generator / Evaluator / Reviewer の動作手順か？ → YES: **`~/.claude/agents/`** の該当ファイルに追加
docs/specs/agent-complete-design/README.md:21:- F4 実装役パイプライン（.claude/agents 7役・scripts/codex-*.sh 8本）の実在: ○同上
scripts/gh-pr-create-safe.sh:12:#   - ~/.claude/agents/generator.md（gh pr create の代わりに必須）
scripts/gh-pr-create-safe.sh:13:#   - ~/.claude/agents/manager.md（同上）
scripts/gh-pr-merge-safe.sh:11:#   - ~/.claude/agents/manager.md（gh pr merge の代わりに必須）
scripts/validate-pr-ownership.sh:9:#   - ~/.claude/agents/generator.md の Step Final（gh pr create 前に手動実行）
scripts/validate-worktree-start.sh:8:#   - .claude/agents/generator.md の Step 0（実装開始前）
scripts/validate-worktree-start.sh:9:#   - .claude/agents/evaluator.md の Step 0（評価開始前）
scripts/validate-worktree-start.sh:10:#   - .claude/agents/reviewer.md の Step 0（レビュー開始前）
```
.github/workflows/aeon-script-check.yml:19,34 は .claude/agents/*.md の変更で発火する paths（push と pull_request 両方）。同 :66-72 の検査は roles=(research planner architect generator reviewer evaluator) について .claude/agents/${role}.md と docs/agents/${role}.md の存在確認のみ（model 行は見ない）。
【事実】aeon-script-check.yml:15-16 の他のパスも含め、model: の値を検査する CI・フック・スクリプトは今回の grep では見つからず。【未確認】.github/workflows 全体への `model` 文字列検索は未実施（C の正規表現のみ）。
CODEOWNERS: ./CODEOWNERS と docs/CODEOWNERS は無し。.github/CODEOWNERS は有り（23行）。`.claude` を含む行は 0 件。関係しうる行: `.github/workflows/ @shingo-ops`、`scripts/ @shingo-ops`、`migrations/ @shingo-ops`。→ 本 PR（.claude/agents/*.md と docs/handoff/ のみ）は Code Owner 対象外【事実: grep 'claude' .github/CODEOWNERS が空】。

## E. ADR 検索
```
git grep -il -E 'fable|model:|サブエージェント|subagent' -- docs/adr/   → 出力なし（rc=1）
git grep -n -i -E 'fable|model|サブエージェント|subagent' -- docs/adr/FEATURE-INDEX.md → 出力なし（rc=1）
```
【事実】docs/adr/ にモデル割当・サブエージェント・fable に関する記述なし。本文中で「ADR-1003」が Opus の委任 GO を指すが、agents の model 指定とは別件（docs/specs/design-system/design.md:2890 等）。

## F. PR 本文の検査（scripts/dev/validate-pr-body.sh 322行を全読）
python 部（stdin の PR 本文を検査、エラーは全列挙）:
1. `### 標準ワークフロー確認` 見出しの存在
2. `対象ADR:` 行に `ADR-\d[\w-]*` 形式の値（ADR-____ は NG）
3. `recon: docs/handoff/...md` 行があり、テンプレ値 `<...>` 無し、ファイルが実在
4. `設計: <パス>` 行（`（`で打ち切り）が記入され、`____`/`<...>` 無し、ファイルが実在
5. `触るファイル:` の宣言（同一行または次行以降 5 行以内のリスト）と `削除するファイル:` の宣言の存在
6. 宣言と `git diff --numstat origin/main...HEAD` の照合。変更した全ファイルが「触るファイル」にフルパス一致で載っていること（除外: package-lock.json、-snapshots/*.png、.claude-pipeline/active-work.md、バイナリ）。削除行が 1 行でもあるファイルは「削除するファイル:」にも載せる（model 行の置換は削除行を含むので該当）
7. 設計 doc に `^##...外部・過去事例...` 見出しがあり、本文 5 文字以上（空欄不可。「該当なし＋理由」可）
8. 設計 doc の `## 維持の仕組み` と `守り手:` 空欄は警告のみ（fail ではない）
9. 設計 doc と recon.md のバッククォート内の `*.tsx|ts|py|sql|yml|yaml|json|md|sh` パス（`:行番号` は除去）が全てリポジトリに実在すること（recon.md のバッククォート内の「~/.claude/...」や実在しないパスは失敗する。本 recon.md ではバッククォート内にそうしたパスを置かない）
その後 shell 部: node があること、`gh api user` の成功、`node scripts/check-process-artifacts.js`（LOCAL_PRECHECK=1、MOCK_PR_BODY 等を渡して CI と同じ検査）。GO 記録の検査はここでは行わない（マージ前 full gate）。
.github/pull_request_template.md の見出し: 
```
1:## なぜ  4:## 何を変えたか  7:## 変更規模  10:## 概要  13:## チェックリスト
15:### リリース PR（develop→main）の相乗り確認（ADR-135）
26:### 標準ワークフロー確認
39:### 共通   43:### DB スキーマ変更時   48:### デザイントークン変更時   54:### backend/app/routers/ 変更時
58:### セキュリティ   62:### CLAUDE.md 変更時   66:### .github/workflows/ 変更時
```

## G. fable が frontmatter で有効か
```
claude --version → 2.1.296 (Claude Code)
claude --help の --model: "Provide an alias for the latest model (e.g. 'fable', 'opus', or 'sonnet') or a model's full name."
```
【事実】CLI の --model ヘルプに alias として 'fable' が明記されている（セッション用）。
【事実】ユーザー側 ~/.claude/agents/architect.md:4 と reviewer.md:4 が既に `model: fable` で、このセッションの Agent ツールの agent 一覧に architect/reviewer が載っている。
【未確認】agent 定義 frontmatter の model: で fable が解釈されることを公式ドキュメント・実際のサブエージェント起動で確認していない（--help は --model の記述のみ。Context7/公式 docs は未参照）。

## 未確認一覧
- agent frontmatter での fable の有効性の公式根拠
- .github/workflows 全体での model 文字列検査の有無（C の正規表現外）
- scripts/check-process-artifacts.js が .claude/agents の変更に特別な検査を課すか（未読）
