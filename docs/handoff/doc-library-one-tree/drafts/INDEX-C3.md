# 目次（AI 向け）

> 依頼・相談を受けたら、計画や答えを書く前に、合う行の文書を Read で開く。パスは docs/ から。設計: specs/doc-agenda-nav/README.md。行は「いつ読むか」を空にしない。

| いつ読むか | 読むもの |
|---|---|
| 新しい依頼で何をどの順に作るか決める前 | STANDARD-WORKFLOW.md |
| 作業前・commit 前・PR 前 | ai-agents/executor-checklist.md |
| 作業場所・ブランチを用意する前、PR・マージの前 | specs/branch-operations/README.md・PARALLEL_TERMINAL_GUIDE.md |
| PO の相談を設計にまとめるとき | ai-agents/design-partner.md |
| 実装役に作業を渡す指示を書くとき | ai-agents/executor-preamble.md |
| 過去の失敗を確かめるとき | [ai-agents/lessons.d/](ai-agents/lessons.d/)（`bash scripts/lessons-view.sh`） |
| 役割分担・Codex・引き継ぎ | ai-agents/codex-operations.md |
| venv・検査・試験を手元で動かすとき | ai-agents/dev-commands.md |
| KPI を決める・測るとき | ai-agents/kpi.md |
| AI の運用ルールを ADR に起案・ADR を直すとき | ai-agents/adr-template.md・adr/README.md（直したら `node scripts/generate-adr-index.js`） |
| 入口・目次に決まりを足す前 | ai-agents/entry-rule-add.md |
| 新しいテーマを始める前 | specs/README.md・adr/FEATURE-INDEX.md・業務の仕様書 salesanchor_system_overview.docx 他3冊（PO から入手） |
| frontend/ を触るとき | ../frontend/AGENTS.md |
| 画面に欄・ボタン・部品を足す・直すとき | CC_UI_GOVERNANCE.md |
| backend/ を触るとき | ../backend/AGENTS.md |
| 商品マスタに登録・直すとき | specs/product-master/registration-rules.md |
| VPS・本番コンテナ・自前の実行機で作業するとき | ops/runner-commands.md・ops/self-hosted-runner-credential-trap.md・runbooks/vps-runner-setup.md |
| 監視の通知が来た・監視を置く・移す・鍵を扱う | runbooks/alerts.md・runbooks/claude-monitor-access.md・runbooks/monitoring-step7-vps.md・runbooks/monitoring-vps-migration.md |
| 秘密の値（secrets）を入れ替えるとき | runbooks/secret-rotation.md |
| 定期の通知・自動の確認が届かない・失敗した | runbooks/weekly-stale-tasks.md・runbooks/qa-smoke-operations.md |
| 仕入元がまとめ売りに新しい書き方を使い始めた | runbooks/bundle-sale-new-wording.md |
| Discord・テナント・ボット・外部サービス（Meta・Firebase・Cloudflare 等） | runbooks/discord-gateway-operations.md・runbooks/discord-role-order-guide.md・runbooks/tenant-deletion-operations.md・runbooks/review-tenant-operations.md・runbooks/shingo-cc-bot-setup.md・runbooks/external-state-operations.md・runbooks/meta-domain-verification-dns.md |
| Gemini 接続停止・画面の一時デプロイ | runbooks/gemini-egress-emergency.md・runbooks/adr-019-english-ui-temporary-deploy.md・runbooks/funnel-pr1-deploy.md |
| 上に無い運用の手順を探すとき | [runbooks/](runbooks/) |
