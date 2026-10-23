# 目次（AI 向け指示文書）

> 入口（AGENTS.md・CLAUDE.md）には安全の決まりだけを置く。作業の型と手順書は、この目次から「章 → 末端」の順にたどり、必要になったときに読む。
> この目次の設計: [doc-agenda-nav](specs/doc-agenda-nav/README.md)（ADR-1040）。行を足すときは表の書式に合わせ、「いつ読むか」を空欄にしない。

| 章 | 末端（読むもの） | いつ読むか |
|---|---|---|
| A 開発の進め方 | [標準開発フロー](STANDARD-WORKFLOW.md) | 便（1回の作業）を始める前 |
| A 開発の進め方 | [実行役のチェックリスト](ai-agents/executor-checklist.md) | 実装・調査の作業前、commit の前、PR を作る前 |
| A 開発の進め方 | [ブランチ運用](specs/branch-operations/README.md) | ブランチと作業場所を作る前、PR を作る・マージする前 |
| A 開発の進め方 | [設計パートナーの手順](ai-agents/design-partner.md) | 設計の担当（Planner・Architect）を始めるとき |
| A 開発の進め方 | [実装役への指示の定型文](ai-agents/executor-preamble.md) | 実装役に作業を渡す指示を書くとき |
| A 開発の進め方 | [教訓メモのフォルダ](ai-agents/lessons.d/)（まとめて読む: `bash scripts/lessons-view.sh`） | 設計・審査で、過去の失敗を確かめるとき |
| A 開発の進め方 | [Codex の運用（役割分担・AEON・UI/UX補助・引き継ぎ）](ai-agents/codex-operations.md) | 役割分担を確かめるとき、Codex で作業する・Codex に作業を渡すとき、会話をまたいで作業を引き継ぐとき |
| A 開発の進め方 | [開発コマンド（venv・セットアップ・実行）](ai-agents/dev-commands.md) | 手元で venv を作るとき、frontend・backend の検査や試験を動かすとき |
| B 設計仕様書 | [設計仕様書の索引](specs/README.md) | 新しいテーマを始める前、索引に載る領域に触れる前 |
| C 設計判断（ADR） | [機能から ADR を引く索引](adr/FEATURE-INDEX.md) | 現状把握（recon）で既存の設計判断を探すとき |
| C 設計判断（ADR） | [ADR の一覧](adr/README.md) | ADR を足す・変えるとき（一覧は `node scripts/generate-adr-index.js` で作り直す） |
| D 領域別ルール | [frontend の決まり](../frontend/CLAUDE.md)・[frontend の AGENTS](../frontend/AGENTS.md) | frontend/ のファイルを触るとき |
| D 領域別ルール | [backend の決まり](../backend/CLAUDE.md)・[backend の AGENTS](../backend/AGENTS.md) | backend/ のファイルを触るとき |
| E 商品マスタ登録 | [商品マスタ登録の決まり](specs/product-master/registration-rules.md) | 商品マスタに商品を登録する・登録内容を直すとき |
| F 運用・本番 | [サーバーで使うコマンド](ops/runner-commands.md) | VPS・本番のコンテナで作業するとき |
| F 運用・本番 | [自前の実行機の資格情報の落とし穴](ops/self-hosted-runner-credential-trap.md) | GitHub の自前の実行機（self-hosted runner）を触るとき |
| F 運用・本番 | [手順書のフォルダ](runbooks/) | 監視・デプロイ・障害対応の手順を探すとき |
