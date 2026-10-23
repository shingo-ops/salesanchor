# 実装カード: 手順書15本の事実食い違いを直す（docs のみ）

- 設計: [design.md](./design.md)（§3 が変更内容の正本。§2 の決まり1〜6を守る）
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-runbook-fact-fix（ブランチ release/runbook-fact-fix）
- PO 承認: 2026-10-23「2」（15本を目次づくりの中で docs のみで直す）

## 手順
1. `./scripts/dev/executor-preflight.sh` を作業場所で実行（出力は /tmp/CC報告ファイル/an-stage1/runbook-fix/ へ）。
2. 事前確認（結果をファイルに残す）:
   - nginx/nginx.conf の api.salesanchor.jp 443 ブロックに `/api/` を backend へ渡す location があるか（design 3-4 の条件）
   - docker-compose.yml の discord-gateway ブロック（:350 から次のサービスまで）に GEMINI_API_KEY があるか（3-8 の条件）
   - secret-scan.yml で gitleaks / trivy / semgrep の各語の行（3-11）
   条件を満たさない項目は、その行の変更をせず報告に書く。
3. design §3 のとおり15本を Edit で直す。各行は文言で位置を確かめる。見つからなければその文書を止めて報告。
4. 照合: recon §1 の39行を、修正後のファイルで「行・今の文言・実物・判定（一致／注記あり／不一致）」の表に作り直し /tmp/CC報告ファイル/an-stage1/runbook-fix/recheck.md に保存。不一致 0 でなければコミットしない。
5. `git diff --name-only origin/main...HEAD` と、追加行に危険な操作の文字列が無いことを確かめる。
6. recon.md・design.md・card.md・15本・台帳（.claude-pipeline/active-work.d/ の本ブランチの項。無ければ公式手順で作る）を git add してコミット（`docs: fix fact mismatches in 15 ops runbooks`）。push・PR はまだしない。

## 禁止
- design §3 に無い行の変更、コード・yml・.sh・.json の変更
- 見張りに止められた後の言い換え・別ツールでの再試行（止まって BLOCKED で報告）
- サーバーへの接続

## 報告
DONE / BLOCKED: / NEEDS_DECISION: のどれかで始め、生出力のパス、コミットの HEAD、条件付き3項目の結果を書く。
