# recon: 仮想マシンが要る試験を GitHub で行う（vm-test-on-gha）

この文書は何か(専門用語なしの1行): 今どこで Mac の仮想マシンを使っているか、GitHub 側に何が既にあるかを、ファイルの行番号つきで調べた記録。

親: [docs/specs/vm-test-on-gha/README.md](../../specs/vm-test-on-gha/README.md)
基準: 2026-10-16 `git fetch origin` 後の origin/main（9c2b9c041）。調査担当 Sonnet（読み取りのみ）、生出力 /tmp/CC報告ファイル/vm-test-to-gha/。Opus が要点を再確認した行には（再確認）と付す。

## 既存 ADR 検索
`git grep -il workflow origin/main -- docs/adr` 46 件・docs/adr/FEATURE-INDEX.md を確認。workflow 新設を制約する専用 ADR は該当なし。関連: ADR-075（秘密は GitHub Secrets のみ: docs/adr/ADR-075-github-secrets-only-policy.md:15-20）、ADR-135/136（危険パス・GO 手順）、ADR-1003（GO 委譲）、ADR-1015（A/B 区分: docs/adr/ADR-1015-autonomy-b-class-no-po-approval.md:19-30）。

## 現在地（事実）
### Mac 上の一時 VM を指示している箇所
- docs/handoff/ai-ops-247/card-stage3-bin-d.md:307-308,324 — `colima start --profile ai-ops-bin-d --cpu 2 --memory 4 --disk 20`、終了後 delete（再確認）。2026-10-16 22:18 に実際に 4GB で稼働していた（ps 観測、/tmp/CC報告ファイル/agent-console-slow/top.txt）。実装中の他テーマ。
- 完了済みの記録: docs/handoff/ai-ops-247/card-stage1-bin6.md:238、card-stage1-bin3.md:75,251、card-stage1-bin2.md:246、docs/handoff/dist01-ar-created-at/design.md:112-113、docs/handoff/pmg-import-delivery-ssot/card-stage-actions.md:23。
- AGENTS.md / CLAUDE.md / .claude/agents / docs/ai-agents に `colima start` の指示は 0 件（1c-colima-cmds.txt）。
- AGENTS.md:117-124 — 開発用 `docker compose up -d postgres redis` → `make check`（Mac の profile default を使う開発手順。本テーマ対象外）。
- scripts で colima を起動するものは無い（colima-idle-stop.sh は stop のみ: scripts/colima-idle-stop.sh:19）。

### GitHub 側に既にあるもの
- 同種の試験が CI に存在: .github/workflows/monitoring-check.yml:67-81（`docker run prom/prometheus ... promtool check rules`）、.github/workflows/test.yml:118-140 / schema-check.yml:56 / migration-test.yml:97（services `postgres:16`）（再確認: `git grep "image: postgres"`）。
- 手動起動の書式前例: .github/workflows/line-import-operations.yml:3-22（inputs・`permissions: contents: read`・concurrency・timeout・actor 制限）（再確認）。monitoring-config-drift.yml:4 は「公開リポジトリなので secrets を使わない」。
- 本番 compose を CI で再現する前例: scripts/rehearsal_phase2.sh:179-379 ＋ .github/workflows/test-phase2-rehearsal.yml:12-45。

### 規則
- 危険パス: scripts/check-process-artifacts.js:115-124（migrations/・scripts/・ops/launchd/・deploy.yml・STANDARD-WORKFLOW.md・process-artifacts-gate.yml・PR テンプレ 等）。`.github/workflows/` 一般と `tests/` は含まれない（再確認）。PO 本人 GO 必須は workflow-lint.yml のみ（同 :49-51）。
- 必須チェックは Ruleset 15777895 に登録したものだけ（docs/BRANCH_PROTECTION_SETUP.md:153,325）。登録変更は PO 確認必須（CLAUDE.md の不可逆操作）。
- リポジトリは PUBLIC（`gh repo view` 2026-10-16 再確認）。
- 例外コメントの前例: `ui-allow: <理由> (#<番号>)`（CLAUDE.md・ADR-144）。

### GitHub の制約（公式）
- 公開リポジトリの標準 runner は無料・Linux 4CPU/16GB/SSD 14GB、1 ジョブ 6 時間、Free 同時 20 ジョブ（アカウント共有）。出典は design.md §8。

## 未確認
- profile `sa-private-ci` の用途（文書に記述なし）。本テーマでは触らない。
- PO アカウントのプラン（Free/Pro）。同時実行枠 20/40 の違いのみで設計に影響しない。
