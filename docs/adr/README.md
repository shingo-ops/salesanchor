# ADR インデックス

> このファイルは `scripts/generate-adr-index.js` により自動生成されます。
> **手動編集禁止。** ADR ファイルを追加・変更後に `node scripts/generate-adr-index.js` を実行してください。

最終更新: 2026-06-07 / ADR 総数: 108 件

## 維持ルール（整合性を保つ・必須）

新ADRが過去の決定を変えるときは、**両方向＋索引を必ず更新する**:

1. **新ADR冒頭**に `Amends ADR-Y` / `Supersedes ADR-Y` を明記（後ろ向きリンク）。
2. **旧ADR-Y** の Status を「Amended by ADR-X」/「Superseded by ADR-X」に更新し前向きリンクを追加。
3. **本索引**に新ADR行を追加し、旧ADRの Amends/Superseded 欄を更新する。

> これが無いと旧ADRを読んだ人が修正に気づけず定義割れが再発する（取引額の定義割れが実例）。

## 一覧

| 番号 | タイトル | ステータス | Amends / Superseded | 日付 |
|------|---------|-----------|---------------------|------|
| [ADR-011](./ADR-011.md) | ADR-011: ADR駆動ワークフロー採用 (3者協調モデル) | Proposed | — | — |
| [ADR-012](./ADR-012-what-how-separation.md) | ADR-012: 開発フロー再設計 — What/How 役割分担モデル採用 | Proposed | Amends ADR-011 | — |
| [ADR-013](./ADR-013.md) | ADR-013: ヘッダーロゴと favicon を Sales Anchor 正式ブランドに統一 | Proposed | — | — |
| [ADR-014](./ADR-014-inventory-management.md) | ADR-014: 在庫管理モジュール — Discord 自動収集 + AI 解析 + 自己改善ループ | Proposed | — | — |
| [ADR-015](./ADR-015.md) | ADR-015: リード管理モジュール設計 | Proposed | — | — |
| [ADR-016](./ADR-016.md) | ADR-016: Facebook ドメイン認証メタタグの追加 | Proposed | — | — |
| [ADR-017](./ADR-017.md) | ADR-017: robots.txt に facebookexternalhit を許可 | Proposed | — | — |
| [ADR-018](./ADR-018_instagram_send_endpoint_fix.md) | ADR-018: Instagram Send API Endpoint 修正 | Accepted | — | — |
| [ADR-018](./ADR-018.md) | ADR-018: salesanchor.jp DNS TXTレコードによるMetaドメイン認証 | Proposed | — | — |
| [ADR-019](./ADR-019-screencast-test-data-creation.md) | ADR-019: Meta App Review 撮影用テストデータの作成方針 | Proposed | — | — |
| [ADR-019](./ADR-019.md) | ADR-019: Meta審査期間中の英語UI一時デプロイ | ## What | — | — |
| [ADR-020](./ADR-020.md) | ADR-020: recording/english-ui 本番デプロイ実行 | Superseded | — | — |
| [ADR-021](./ADR-021-order-management.md) | ADR-021: 受注管理モジュール — フルフィルメント・売上計算・報酬計算の Sales Anchor 統合 | ## コンテキスト | — | — |
| [ADR-022](./ADR-022.md) | ADR-022: UIをMeta Business Suite風に刷新（左サイドメニュー + 配色統一） | Proposed | — | — |
| [ADR-023](./ADR-023_staff_lifecycle_three_layer_sync.md) | ADR-023: スタッフライフサイクル操作における認証3層の同期化 | Proposed | — | — |
| [ADR-024](./ADR-024_meta_integration_structural_fix.md) | ADR-024: Meta 連携の構造的不整合の修正 | Proposed | — | — |
| [ADR-025](./ADR-025_meta_integration_operational_hardening.md) | ADR-025: Meta 連携の運用整備強化 - 環境変数注入の確実性とパートナー実装ガイドラインの強化 | Proposed | — | — |
| [ADR-026](./ADR-026_meta_messages_message_id_text.md) | ADR-026: meta_messages.message_id の TEXT 化（Instagram mid 受信対応） | Proposed | — | — |
| [ADR-027](./ADR-027-ui-internationalization.md) | ADR-027: Sales Anchor UI の i18n 対応（日本語/英語切り替え） | Accepted | — | — |
| [ADR-028](./ADR-028-screencast-tenant-isolation.md) | ADR-028: Meta App Review 撮影用テナント分離 | Superseded | — | — |
| [ADR-029](./ADR-029-self-hosted-runner-fleet.md) | ADR-029: Self-hosted runner fleet — 2 台 Mac 体制と labels 戦略の正式化 | Accepted | — | — |
| [ADR-032](./ADR-032.md) | ADR-032: Firebase Authentication カスタム認証ドメイン | Accepted | — | — |
| [ADR-033](./ADR-033-app-theme-switching.md) | ADR-033: アプリ内テーマ切り替え（ライト / ダーク） | Accepted | — | — |
| [ADR-034](./ADR-034-tenant-migration-automation.md) | ADR-034: 新規テナント migration 自動化 + 既存テナント整合化 | Proposed | — | — |
| [ADR-035](./ADR-035-external-state-verification.md) | ADR-035: External State Verification — 6 system × 5-layer defense | Proposed | — | — |
| [ADR-036](./ADR-036-tenant-schema-integrity.md) | ADR-036: テナントスキーマ整合性保証 | — | — | — |
| [ADR-037](./ADR-037-meta-page-connection-investigation.md) | ADR-037: Meta（Facebook/Instagram）ページ接続経路の現状調査 | Draft - 調査フェーズ | — | — |
| [ADR-038](./ADR-038-qa-smoke-suite.md) | ADR-038: QA Smoke Suite — Cross-feature UI verification against real backend | Accepted | — | — |
| [ADR-039](./ADR-039-generator-codebase-reconnaissance.md) | ADR-039: Generator Codebase Reconnaissance — ADR 概念と frontend/backend 実体の機械的突き合わせ | Proposed | — | — |
| [ADR-040](./ADR-040-claude-code-guardrail-investigation.md) | ADR-040: Claude Code 運用ガードレールの存在性調査 | Draft - 調査フェーズ | — | — |
| [ADR-041](./ADR-041-meta-page-connection-fallback-implementation.md) | ADR-041: Meta（Facebook）ページ接続フォールバック実装 | ## 背景 | — | — |
| [ADR-042](./ADR-042-guardrails-and-release-flow.md) | ADR-042: Claude Code 運用ガードレール強化 + リリース運用統一 | Accepted | — | — |
| [ADR-044](./ADR-044-ci-health-recovery.md) | ADR-044: develop ブランチ CI 健全性の回復 | Accepted | — | — |
| [ADR-045](./ADR-045-migration-055-deploy-automation.md) | ADR-045: ADR-041 migration 055 の本番適用と deploy.yml 自動化 | Accepted | — | — |
| [ADR-046](./ADR-046-lp-redesign.md) | ADR-046: Landing Page Redesign — English-only, Professional SaaS Style | Proposed | — | 2026-05-19 |
| [ADR-047](./ADR-047-lp-copy-refocus.md) | ADR-047: LP Copy Refocus — Customer-First Voice + Visual Polish | Proposed | — | 2026-05-20 |
| [ADR-048](./ADR-048-web-claude-external-planner.md) | ADR-048: Web Claude (claude.ai) as External Auxiliary Planner — Two-Document Reconciliation | Proposed | — | 2026-05-20 |
| [ADR-049](./ADR-049-lp-section-completion.md) | ADR-049: LP Section Completion Hot-fix — S3 Carousel Cards + S4 Ecosystem Diagram + S5 Metrics Band + S6 Why-us 4-column | Proposed | — | 2026-05-20 |
| [ADR-050](./ADR-050-release-pr-workflow-standardization.md) | ADR-050: Release PR Workflow Standardization — Pattern A Codification + Branch Protection | Accepted | — | 2026-05-20 |
| [ADR-051](./ADR-051-claude-pipeline-full-automation.md) | ADR-051: claude-pipeline Full Automation — Reviewer / Evaluator Auto-Trigger | Accepted | — | 2026-05-20 |
| [ADR-053](./ADR-053-claude-pipeline-decision-parsing-fix.md) | ADR-053: claude-pipeline Reviewer Decision Parsing Fix + Self-Approve Workaround | Proposed | — | 2026-05-20 |
| [ADR-054](./ADR-054-lp-hubspot-style-restructure.md) | ADR-054: LP Full Restructure — HubSpot-Style Layout + frontend Brand Color Unification | Proposed | — | 2026-05-20 |
| [ADR-055](./ADR-055-playwright-mcp-setup.md) | ADR-055: Playwright MCP Setup for claude-pipeline Evaluator | Proposed | — | 2026-05-20 |
| [ADR-056](./ADR-056-human-in-the-loop-minimization.md) | ADR-056: Human-in-the-Loop Minimization — Auto-Regenerate + Auto-Merge to develop + Notification Consolidation | Accepted | — | 2026-05-20 |
| [ADR-057](./ADR-057-lp-premium-restyle.md) | ADR-057: LP Premium Restyle — HubSpot Construct + Dark Navy Hero + Hub Card Grid | Proposed | — | 2026-05-20 |
| [ADR-058](./ADR-058-remove-contacts-from-sidebar.md) | ADR-058: サイドバーから「担当者」メニューを削除し会社ページに統合 | Proposed | — | — |
| [ADR-059](./ADR-059-lead-nav-unified-tabs.md) | ADR-059: リードナビゲーションをアコーディオン→クリック＋ページ内タブに統一 | Accepted | — | — |
| [ADR-060](./ADR-060-rename-company-to-client-profile.md) | ADR-060: 「会社」→「顧客情報」/ "Companies" → "Client Profile" リネーム | Proposed | — | — |
| [ADR-061](./ADR-061-inbox-meta-style-layout.md) | ADR-061: Inbox Meta Business Suite スタイル UI 再設計 | Proposed | — | — |
| [ADR-063](./ADR-063-inbox-page-level-tab-header.md) | ADR-063: Inbox ページレベル ヘッダー + 全幅タブバー | Proposed | — | — |
| [ADR-064](./ADR-064-inbox-meta-exact-replica.md) | ADR-064: Inbox Meta Business Suite 完全再現レイアウト | Accepted | — | — |
| [ADR-065](./ADR-065-asyncpg-prepared-statement-cache-disable.md) | ADR-065: asyncpg プリペアドステートメントキャッシュ無効化 | Accepted | — | — |
| [ADR-066](./ADR-066-dark-mode-logo-invert.md) | ADR-066: ダークモード時サイドバーロゴ白反転 | Accepted | — | — |
| [ADR-067](./ADR-067-design-token-enforcement.md) | ADR-067: デザイントークン強制システム（Design Token Enforcement） | Accepted | — | 2026-05-21 |
| [ADR-068](./ADR-068-platform-brand-asset-policy.md) | ADR-068: プラットフォームブランドアセットポリシー | Accepted | — | — |
| [ADR-069](./ADR-069-uptime-kuma-activation.md) | ADR-069: Uptime Kuma 監視ダッシュボードの有効化 | Accepted | — | — |
| [ADR-070](./ADR-070-grafana-monitoring-integration.md) | ADR-070: Grafana ドメイン移行 + Uptime Kuma→Prometheus 統合 | Accepted | — | — |
| [ADR-071](./ADR-071-orders-nav-placement.md) | ADR-071: 受注管理ナビゲーション導線の追加 | Accepted | — | — |
| [ADR-072](./ADR-072-tenant-schema-prefix-enforcement.md) | ADR-072: tenant schema 修飾の戦略統一（schema prefix と reset_tenant_context のハイブリッド） | Proposed | — | — |
| [ADR-073](./ADR-073-design-system-kgi-rubric.md) | ADR-073: デザインシステム KGI 100% ルーブリック | Accepted | — | — |
| [ADR-074](./ADR-074-worktree-agent-enforcement.md) | ADR-074: Worktree強制によるエージェントPR混入防止 | Accepted | — | — |
| [ADR-075](./ADR-075-github-secrets-only-policy.md) | ADR-075: GitHub Secrets 一元管理ポリシー | Accepted | — | — |
| [ADR-076](./ADR-076-claude-md-hierarchy.md) | ADR-076: CLAUDE.md 階層構造標準化 + サイズ上限改定 | Accepted | — | — |
| [ADR-076](./ADR-076-pipeline-efficiency-improvements.md) | ADR-076: パイプライン効率化（Evaluator自動スキップ・Governance自動化・重複検出改善・Researcher自動起動） | Accepted | — | — |
| [ADR-077](./ADR-077-github-actions-metrics.md) | ADR-077: GitHub Actions CI メトリクスの Prometheus/Grafana 可視化 | Accepted | — | — |
| [ADR-078](./ADR-078-vps-runner-registration.md) | ADR-078: VPS runner 登録計画 — さくらVPS への salesanchor-vps ラベル付き self-hosted runner 登録 | Accepted | — | — |
| [ADR-079](./ADR-079-claude-code-monitoring-access.md) | ADR-079: Claude Code 専用 VPS 読み取り専用監視アクセス | Accepted | — | — |
| [ADR-080](./ADR-080-monitoring-vps-separation.md) | ADR-080: 監視スタックの管理室VPS分離 — RAM危機の根本解決とCIランナー統合 | Proposed | — | — |
| [ADR-081](./ADR-081-monitoring-vps-final-operational-design.md) | ADR-081: 監視VPS分離の最終運用設計 — パケットフィルタ、UFW、proxy 経路、backend worker 数の固定 | Accepted | — | — |
| [ADR-081](./ADR-081-remove-design-review-gate.md) | ADR-081: design-review-gate 廃止 — develop までの自動化方針との整合 | Accepted | — | — |
| [ADR-082](./ADR-082-deploy-skip-migrations-on-frontend-only.md) | ADR-082: フロントのみのデプロイで DB マイグレーション実行をスキップする | Accepted | — | — |
| [ADR-082](./ADR-082-generator-executor-codex-fallback.md) | ADR-082: Generator Executor 選択 + Codex→Claude Code 自動フォールバック | Accepted | — | — |
| [ADR-083](./ADR-083-tcg-type-master.md) | ADR-083: TCG シリーズの「種別」をマスタ表 + UI 管理へ移行する | Accepted | — | — |
| [ADR-084](./ADR-084-pokeapi-dex-import.md) | ADR-084: ポケモン図鑑を PokeAPI から取込（差分プレビュー→一括反映） | Accepted | — | — |
| [ADR-085](./ADR-085-supplier-prompts.md) | ADR-085: 仕入先別 Gemini 解析プロンプトの管理 | Accepted | — | — |
| [ADR-086](./ADR-086-parallel-development-standardization.md) | ADR-086: 複数エージェント並行開発の標準化 — worktree / AEON / Evidence Registry / Release Gate | Proposed | — | 2026-05-31 |
| [ADR-087](./ADR-087-hub-shell-layout-standard.md) | ADR-087: hub-shell 共通シェルレイアウト標準 | Accepted | — | 2026-05-31 |
| [ADR-089](./ADR-089-deprecate-customers-unify-to-companies.md) | ADR-089: `customers` テーブル廃止と `companies` への一元化 | Accepted | — | — |
| [ADR-090](./ADR-090-products-central-unification.md) | ADR-090: products アーキテクチャ統一（tenant別 → public 中央）と Discord取込→在庫表反映 | Accepted | — | — |
| [ADR-091](./ADR-091-discord-bot-scope-definition.md) | ADR-091: Discord Bot 担当業務スコープ定義・実装記録 | Accepted | — | — |
| [ADR-092](./ADR-092-deploy-concurrency-control.md) | ADR-092: deploy.yml 多重実行防止（concurrency 制御 + コンテナ pre-cleanup） | Accepted | — | — |
| [ADR-093](./ADR-093-inventory-table-product-master-redesign.md) | ADR-093: 在庫表 / 仕入元オファー / 商品マスタ 再設計 | Accepted | — | — |
| [ADR-093](./ADR-093-sales-management-page.md) | ADR-093: 売上管理ページ（Single Source of Truth） | Proposed | — | — |
| [ADR-094](./ADR-094-crm-definition-and-deals-reorganization.md) | ADR-094: CRM定義の明文化と「案件」→「商談」へのリネーム・CRM移管 | Proposed | — | — |
| [ADR-094](./ADR-094-sales-management-page.md) | ADR-094: 売上管理ページ（Single Source of Truth） | Proposed | — | — |
| [ADR-095](./ADR-095-sa-ssot-two-backbone-architecture.md) | ADR-095: SSOT原則と「2本背骨」アーキテクチャ（ADR-SA-01） | Accepted | — | — |
| [ADR-096](./ADR-096-sa-customer-master-crm-data-model.md) | ADR-096: 顧客マスタ／CRMデータモデル（顧客背骨・商談・会話ログ）（ADR-SA-02） | Accepted | — | — |
| [ADR-097](./ADR-097-sa-customer-registration-form.md) | ADR-097: 顧客登録フォーム（署名トークン・テナント分離・住所帳・自動同期）（ADR-SA-03） | Accepted | — | — |
| [ADR-098](./ADR-098-sa-multi-channel-identity-resolution.md) | ADR-098: 多チャネル名寄せ＋直リンクテンプレSSOT（ADR-SA-04） | Accepted | — | — |
| [ADR-099](./ADR-099-sa-inventory-model.md) | ADR-099: 在庫モデル（商品/在庫マスタ分離・在庫ソースA/B・集計フィルタ・在庫イベント）（ADR-SA-05） | Accepted | — | — |
| [ADR-100](./ADR-100-sa-ingestion-analysis-pipeline.md) | ADR-100: 取り込み・解析パイプライン（提供元メッセージ→生オファー）（ADR-SA-06） | Accepted | — | — |
| [ADR-101](./ADR-101-sa-quotation-invoice-generation.md) | ADR-101: 見積・請求の生成（正規化2テーブル・テンプレSSOT・関税ポリシー・スナップショット・発行モード）（ADR-SA-07） | Accepted | — | — |
| [ADR-102](./ADR-102-sa-order-management.md) | ADR-102: 受注管理（引当・複数提供元分割・発注ステータス・発注最適化Lv2）（ADR-SA-08） | Accepted | — | — |
| [ADR-103](./ADR-103-sa-shipping-dispatch-timing.md) | ADR-103: 発送・出荷タイミング（同梱既定／分割オプトイン・出荷予定計算・発送元マスタ）（ADR-SA-09） | Accepted | — | — |
| [ADR-104](./ADR-104-sa-payment-confirmation-status-pnl.md) | ADR-104: 入金確認・受注ステータスライフサイクル・完了・売上P&L（ADR-SA-10） | Accepted | — | — |
| [ADR-105](./ADR-105-sa-trouble-refund.md) | ADR-105: トラブル／返金（ADR-SA-11） | Accepted | — | — |
| [ADR-106](./ADR-106-sa-multitenant-policy.md) | ADR-106: マルチテナント＆「標準エンジン＋テナント別ポリシー」方針（ADR-SA-12） | Accepted | — | — |
| [ADR-107](./ADR-107-sa-analytics-agent-a-customer-priority.md) | ADR-107 — 分析エージェント (A) 顧客優先度付け | Proposed | — | 2026-06-04 |
| [ADR-108](./ADR-108-inbox-karte-panel-redesign.md) | ADR-108: 受信箱カルテの表示再編（商談／顧客／連絡先の再編・段階出し分け） | Proposed | — | — |
| [ADR-109](./ADR-109-leads-status-ssot-immutable-codes.md) | ADR-109: status の SSOT化（不変コード＋i18nラベル） | Accepted | — | — |
| [ADR-110](./ADR-110-karte-reference-alignment.md) | ADR-110: 受信箱カルテをリファレンスに一致させる是正（ADR-108 実装是正） | Accepted | — | — |
| [ADR-110](./ADR-110-sa-translation-subsystem.md) | ADR-110: 会話ログ翻訳サブシステム | — | — | — |
| [ADR-111](./ADR-111-runner-label-isolation.md) | ADR-111: runner-label-isolation — Shingo-Mac-Temp 専用ラベルによる開発環境分離 | Accepted | — | — |
| [ADR-112](./ADR-112-workflow-redesign-design-origin-flow.md) | ADR-112: ワークフロー再編 — 設計起点フロー v2 | Accepted | — | — |
| [ADR-113](./ADR-113-two-mode-dev-flow.md) | ADR-113: 2モード開発フロー（terminal / handoff） | Accepted | — | — |
| [ADR-114](./ADR-114-worktree-auto-cleanup.md) | ADR-114: worktree ライフサイクルの完全自動化 — 単一真実・イベント駆動・矛盾ゼロ | Proposed | — | — |
| [ADR-115](./ADR-115-deploy-safety.md) | ADR-115: デプロイ安全策（自動ロールバック・環境差バグ対策） | 採用 | — | — |
| [ADR-999](./ADR-999-pipeline-test.md) | ADR-999: パイプライン動作テスト | テスト用（マージ後に削除予定） | — | — |

## ステータス凡例

| ステータス | 意味 |
|-----------|------|
| Accepted | 承認済み・有効 |
| Proposed | 提案中 / レビュー待ち |
| Deprecated | 非推奨（後継 ADR 参照） |
| Superseded | 別 ADR により上書き済み |
