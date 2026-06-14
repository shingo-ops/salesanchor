# Active Work Registry — 並列エージェント作業の唯一の真実（SSoT）

> **新しいターミナルで作業を開始する前に必ずこのファイルを確認すること。**
> 重複が見つかった場合は STOP → しんごさんに確認。

## ルール

| # | タイミング | 操作 |
|---|-----------|------|
| 1 | 作業開始前 | このファイルを読んで、同じ機能エリアで進行中の作業がないか確認する |
| 2 | Worktree 作成時 | `scripts/new-worktree.sh` が自動でエントリを追記する |
| 3 | PR マージ完了後 | 該当行を `DONE` に更新する（削除しない・ログとして残す） |
| 4 | 重複発見時 | STOP → しんごさんに確認してから開始する |

## 現在進行中の作業

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |
|-----------|--------------|---------|------|-----|------|------|
| docs/fedex-pr-a4-recon-design | FedEx A4 接続テスト結果保存 recon/design（docs-only） | 2026-06-14 | DONE | | | |
| feature/morimoto/dev-workflow-improvements | 開発ワークフロー改善 | 2026-06-02 | DONE | | | |
| feature/morimoto/invoice-issuer-path-fix | 請求書作成 発行者情報ボタンパス修正 | 2026-06-02 | DONE | | | |

| feature/morimoto/pre-commit-active-work-exception | （記入してください） | 2026-06-02 10:40 | DONE | | | |
| feature/morimoto/fix-release-pr-drawbacks | （記入してください） | 2026-06-02 10:42 | DONE | | | |
| feature/morimoto/discord-ticket-phase1 | ADR-091 KPI3 Phase 1+2 | 2026-06-02 12:53 | DONE | #1404 | | |
| feature/morimoto/discord-ticket-phase3 | ADR-091 KPI3 Phase 3 | 2026-06-02 13:30 | DONE | #1406 | | |
| feature/morimoto/discord-kpi4-announce | ADR-091 KPI4 アナウンス投稿 | 2026-06-02 14:00 | DONE | | | |
| feature/morimoto/discord-newtab | （記入してください） | 2026-06-02 22:12 | DONE | | | |
| feature/morimoto/worktree-guard-auto-recovery | worktreeガード自動リカバリー機能 | 2026-06-02 23:00 | DONE | | | |
| feature/morimoto/discord-oauth-redirect-fix | Discord OAuth リダイレクト修正・テスト追加 | 2026-06-02 23:30 | DONE | | | |
| feature/morimoto/migrate-consolidation | マイグレーション一括化 | 2026-06-02 23:30 | DONE | | | |
| feature/morimoto/grafana-sidebar-nav | Grafana ナビ横タブ→サイドバー移行 | 2026-06-03 | DONE | | | |
| feature/morimoto/schedule-card-style | スケジュール カードスタイル（背景透明化・カード化） | 2026-06-03 | DONE | | | |
| feature/morimoto/grafana-sidebar-nav-v2 | Grafana 左列サイドバー実装（B案） | 2026-06-03 | DONE | | | |
| feature/morimoto/schedule-responsive-tokens | スケジュール スロット高・終日エリア レスポンシブ対応 | 2026-06-03 | DONE | | | |
| feature/morimoto/schedule-modal-polish | スケジュール 予定編集モーダル Googleカレンダー準拠デザイン改善 | 2026-06-03 | DONE | #1563 | | |
| feature/morimoto/schedule-event-popover | スケジュール 既存予定クリック 詳細ポップオーバー | 2026-06-03 | DONE | #1566 | | |
| feature/morimoto/schedule-popover-style | スケジュール ポップオーバー スタイル調整 | 2026-06-03 | DONE | #1569 | | |
| feature/morimoto/schedule-popover-v2 | スケジュール ポップオーバー 色・作成者・配置改善 | 2026-06-03 | DONE | | | |
| feature/morimoto/crm-hub-fix-titles | （記入してください） | 2026-06-03 23:55 | DONE | | | |
| feature/morimoto/fix-space9-token | デザイントークン --space-9 未定義バグ修正 | 2026-06-03 | DONE | | | |
| feature/morimoto/admin-hub-bottom-nav | SaaS管理者ハブ ボトムタブ統合 | 2026-06-04 00:06 | DONE | | | |
| feature/morimoto/schedule-update-popover-fix | スケジュール 更新ADR-072バグ修正＋ポップオーバー説明・場所表示 | 2026-06-04 01:01 | DONE | #1593 | | |
| feature/morimoto/sa-foundation-step0-claude-md | （記入してください） | 2026-06-04 09:24 | DONE | | | |
| feature/morimoto/sa-foundation-pr2-audit-fix | （記入してください） | 2026-06-04 09:40 | DONE | | | |
| feature/morimoto/sa-foundation-pr1-tenant-policy | テナントポリシー列追加（ADR-106） | 2026-06-04 | DONE | | | |
| feature/morimoto/schedule-modal-description-display | スケジュール モーダル 説明・場所の表示追加 | 2026-06-04 10:06 | DONE | | | |
| feature/morimoto/sa-foundation-pr3-reg-token | （記入してください） | 2026-06-04 10:50 | DONE | | | |
| feature/morimoto/sa-foundation-pr4-conv-logs | （記入してください） | 2026-06-04 10:50 | DONE | | | |
| feature/morimoto/sa-foundation-pr5-link-templates | （記入してください） | 2026-06-04 10:50 | DONE | | | |
| feature/morimoto/sa-foundation-pr7-parse-logs | （記入してください） | 2026-06-04 10:50 | DONE | | | |
| feature/morimoto/sa-foundation-pr8-invoice-snapshot | （記入してください） | 2026-06-04 11:48 | DONE | | | |
| feature/morimoto/sa-foundation-pr6-own-inventory | A在庫テナント私有化（ADR-099） | 2026-06-04 | DONE | | | |
| feature/morimoto/fix-company-stats-view-total-col | #1606 CI修正: v_company_stats i.total→i.total_amount | 2026-06-04 | DONE | #1615 | | |
| feature/morimoto/hotfix-develop-conflict-markers | develop conflict marker修正（run_all_migrations.sh） | 2026-06-04 | DONE | #1616 | | |
| feature/morimoto/remove-trust-level-ui | trust_level UI撤去（Issue #1607 / C-2） | 2026-06-04 | DONE | #1619 | | |
| hotfix/back-merge-main-into-develop | develop←mainバックマージ | 2026-06-04 | DONE | | | |
| feature/morimoto/analytics-agent-a-priority | ADR-107 ADR文書起案 | 2026-06-04 14:50 | DONE | #1622 | | ADR文書のみ、マージ済み |
| feature/morimoto/adr-107-analytics-agent-a-impl | ADR-107 分析エージェント(A) 顧客優先度付け 実装 | 2026-06-04 | DONE | | | |
| feature/morimoto/adr-108-karte-redesign | （記入してください） | 2026-06-04 15:56 | DONE | | | |
| feature/morimoto/adr-109-status-ssot | ADR-109 status SSOT化（ADR文書のみ） | 2026-06-04 15:56 | DONE | #1630 | | ADR文書のみ、マージ済み |
| feature/morimoto/adr-109-status-ssot-impl | ADR-109 status SSOT化 実装 | 2026-06-07 | IN_PROGRESS | | | |
| claude-impl/20260604-074511 | ADR-108 受信箱カルテ再設計 自動実装 | 2026-06-04 | IN_PROGRESS | #1635 | | |
| feature/morimoto/adr-107-safety-schedule | ADR-107 §13 安全装置 Celery beat 登録 | 2026-06-04 | DONE | #1648 | | |
| feature/morimoto/fix-priority-check-conn-leak | priority_scoring_check DB接続リーク修正 | 2026-06-04 | DONE | #1652 | | |
| feature/morimoto/fix-translation-import | translation.py ImportError 緊急修正 | 2026-06-04 | DONE | | | |
| feature/morimoto/adr-110-translation-subsystem | ADR-110 会話ログ翻訳サブシステム（グロッサリ・確信度・送信下訳・3点セット） | 2026-06-04 | DONE | #1641 | | |
| hotfix/morimoto/fix-smoke-check5-parsing | smoke[5] psql -t SET出力偽陰性修正 | 2026-06-06 | DONE | #1697 | | |
| hotfix/morimoto/fix-cross-tenant-fk-schema-collision | test_products_cross_tenant_fk テナント998スキーマ衝突修正 | 2026-06-06 | DONE | #1699 | | |
| hotfix/morimoto/fix-smoke-check6-failclose | smoke[6] fail-close ON_ERROR_STOP=1 修正（ロケール依存除去） | 2026-06-06 | DONE | #1700 | | |
| hotfix/morimoto/fix-smoke-check6-v2 | smoke[6] -c オプション修正（docker exec stdin非接続対応） | 2026-06-06 | DONE | | | |
| feature/morimoto/sa-18-phase2-auto-url | SA-18 Bootstrap auto-URL（SA18_PHASE2_ENABLED → salesanchor_app URL 自動組み立て） | 2026-06-07 10:35 | IN_PROGRESS | #1716 | | |
| feature/morimoto/adr-116-deploy-rollback | ADR-118 ロールバック堅牢化（deploy_rollback.sh 共有・LAST_GOOD_SHA）棚上げ中 | 2026-06-07 | IN_PROGRESS | #1713 | | 棚上げ中 |
| feature/morimoto/fix-rls-policy-variable-name | RLS ポリシー変数名修正（Phase2 前提条件） | 2026-06-07 | DONE | #1730 | | |
| feature/morimoto/preview-section-split | DesignPreview セクション分割（衝突防止）+ §9 DataTable（PR#1759/#1761 解消） | 2026-06-08 | IN_PROGRESS | | | |
| release/main-0608 | （記入してください） | 2026-06-08 12:00 | IN_PROGRESS | | | |
| feature/morimoto/tabs-component | Tabs 金型 + デザインプレビュー §10（Task 5C+5D） | 2026-06-08 | DONE | #1772 | | |
| feature/morimoto/fix-register-company-lookup | （記入してください） | 2026-06-08 12:11 | IN_PROGRESS | | | |
| feature/morimoto/submenu-and-preview-rooms | SubMenu 金型 ＋ デザインプレビュー部品別ルーム再構成（Task 6C+6D） | 2026-06-08 12:42 | DONE | #1776 | | |
| feature/morimoto/button-outline-variant | Button outline バリアント追加 | 2026-06-08 13:18 | DONE | #1779 | | |
| feature/morimoto/icon-button-recon-and-standard | アイコンボタン実物基準作り直し＋プレビュー更新 | 2026-06-08 14:19 | DONE | #1780 | | |
| feature/morimoto/fix-register-form-ux | （記入してください） | 2026-06-08 14:28 | IN_PROGRESS | | | |
| feature/morimoto/icon-btn-size-fix | （記入してください） | 2026-06-08 14:44 | IN_PROGRESS | | | |
| feature/morimoto/icon-btn-root-cause-fix | （記入してください） | 2026-06-08 15:09 | IN_PROGRESS | | | |
| feature/morimoto/fix-address-empty-str-422 | （記入してください） | 2026-06-08 15:27 | IN_PROGRESS | | | |
| feature/morimoto/caffeinate-failure-visibility | （記入してください） | 2026-06-08 15:35 | IN_PROGRESS | | | |
| feature/morimoto/register-form-input-contract | （記入してください） | 2026-06-08 15:57 | IN_PROGRESS | | | |
| feature/morimoto/modal-component | （記入してください） | 2026-06-08 15:57 | IN_PROGRESS | | | |
| feature/morimoto/empty-state-component | （記入してください） | 2026-06-08 16:56 | IN_PROGRESS | | | |
| feature/morimoto/empty-state-icon-fix | （記入してください） | 2026-06-08 20:57 | IN_PROGRESS | | | |
| feature/morimoto/definition-audit-2026-06-08 | （記入してください） | 2026-06-08 22:10 | IN_PROGRESS | | | |
| feature/morimoto/decision-layer-01-recon | 決定レイヤー① recon 差分可視化 | 2026-06-09 00:17 | DONE | #1799 | | |
| feature/morimoto/status-presentation-ssot | 決定レイヤー 1 ステップ1 — SSoT中央表・補助関数 | 2026-06-09 01:30 | DONE | #1800 | | |
| feature/morimoto/status-ssot-step2a | 決定レイヤー 1 ステップ2a — 差分可視化 + staff/bot 現状維持 | 2026-06-09 08:22 | DONE | #1801 | | |
| feature/morimoto/status-ssot-step2b | 決定レイヤー 1 ステップ2b — 全29サイト getStatusPresentation() 置換 | 2026-06-09 10:00 | DONE | #1803 | | |
| feature/morimoto/sop-kpi2-impl | SOPコンプライアンス保証機構（ADR-119 KPI2）— process-artifacts gate | 2026-06-08 | IN_PROGRESS | | | |
| hotfix/back-merge-main-into-develop-2 | （記入してください） | 2026-06-09 10:34 | IN_PROGRESS | | | |
| feature/morimoto/claude-md-sop-update | CLAUDE.md 標準開発フロー節を新SOPに差し替え（ADR-121） | 2026-06-09 | IN_PROGRESS | | | |
| feature/morimoto/status-ssot-step3-lint-error | （記入してください） | 2026-06-09 11:01 | IN_PROGRESS | | | |
| feature/morimoto/sop-dedup-fix | sop-followup重複ガード PR番号単位修正（Reviewer指摘）| 2026-06-09 | IN_PROGRESS | | | |
| feature/morimoto/gate-trigger-fix | process-artifacts gate trigger develop のみに修正（リリースPR誤検知解消） | 2026-06-09 | IN_PROGRESS | | | |
| feature/morimoto/gate-release-skip | process-artifacts gate リリースPRスキップ修正（#1811誤修正の正確な対処） | 2026-06-09 | IN_PROGRESS | | | |
| feature/morimoto/products-page-edit | ProductsPage モーダル→専用ページ化（ADR-122 Phase D） | 2026-06-09 | DONE | #1828 | | |
| feature/morimoto/modal-xl-replacements | OrdersPage modal-overlay 3件→Modal(xl)置換（ADR-122） | 2026-06-09 | DONE | #1827 | | |
| feature/morimoto/datatable-invoices-pilot | InvoicesPage DataTable パイロット（ADR-067） | 2026-06-09 | DONE | #1841 | | |
| feature/morimoto/datatable-preview | DataTable 金型 + onRowClick + 制御型ページ送り（Task 4C+4D+step2） | 2026-06-08 | DONE | #1847 | | |
| feature/morimoto/brand-navy-accent | （記入してください） | 2026-06-11 04:16 | IN_PROGRESS | | | |
| docs/morimoto/sa-02-recon | （記入してください） | 2026-06-11 04:45 | IN_PROGRESS | | | |
| feature/morimoto/adr-127-registration-post-forms | （記入してください） | 2026-06-11 04:46 | IN_PROGRESS | | | |
| feature/morimoto/sa-02-stage1-channel-webhook | （記入してください） | 2026-06-11 10:29 | IN_PROGRESS | | | |
| feature/morimoto/active-work-done-cleanup | （記入してください） | 2026-06-11 10:44 | IN_PROGRESS | | | |
| feature/morimoto/adr127-phase1-address-form | （記入してください） | 2026-06-11 11:11 | IN_PROGRESS | | | |
| feature/morimoto/zero-downtime-deploy | （記入してください） | 2026-06-11 11:25 | IN_PROGRESS | | | |
| feature/morimoto/sa-02-post-deploy-docs | （記入してください） | 2026-06-11 11:27 | IN_PROGRESS | | | |
| feature/morimoto/sa-02-stage3-manual-record | （記入してください） | 2026-06-11 11:33 | IN_PROGRESS | | | |
| feature/morimoto/adr127-phase2-dual-gate | ADR-127 §4 第1層ゲート | 2026-06-11 11:35 | IN_PROGRESS | #1936 | | |
| feature/morimoto/adr127-phase2b-registered-label | （記入してください） | 2026-06-11 12:51 | IN_PROGRESS | | | |
| feature/morimoto/zero-downtime-polish | （記入してください） | 2026-06-11 12:53 | IN_PROGRESS | | | |
| feature/morimoto/sa-02-stage3-plan-update | （記入してください） | 2026-06-11 13:06 | IN_PROGRESS | | | |
| feature/morimoto/sa-02-stage4-company-conv-logs | SA-02 段階4: 会社詳細会話履歴タブ | 2026-06-11 13:09 | DONE | #1945 | ✅ | |
| feature/morimoto/sa-02-stage4-docs | SA-02 進捗ドキュメント更新 | 2026-06-11 13:15 | IN_PROGRESS | | | |
| feature/morimoto/adr127-phase2c-button-color | （記入してください） | 2026-06-11 13:50 | IN_PROGRESS | | | |
| feature/morimoto/sa-02-stage2-migration-prep | SA-02 段階2 移行スクリプト準備 | 2026-06-11 13:58 | DONE | #1952 | | |
| feature/morimoto/sa-02-stage2-rollback-fix | SA-02 段階2 rollback条件修正 | 2026-06-11 16:50 | DONE | #1965 | | |
| feature/morimoto/sa-02-stage2-plan-update | SA-02 段階2 plan記録更新 | 2026-06-11 17:00 | IN_PROGRESS | | | |
| feature/morimoto/sync-main-develop-adr128 | main/develop 同期（ADR-128 migration 競合解消） | 2026-06-11 14:07 | DONE | #1953 | | |
| feature/morimoto/add-fedex-migration-to-main | （未使用ブランチ） | 2026-06-11 14:16 | DONE | | | |
| feature/morimoto/nginx-reload-migration-total | （記入してください） | 2026-06-11 15:54 | IN_PROGRESS | | | |
| feature/morimoto/adr127-phase2c-css-fix | （記入してください） | 2026-06-11 16:45 | IN_PROGRESS | | | |
| feature/morimoto/gate-bug-note | （記入してください） | 2026-06-11 18:12 | IN_PROGRESS | | | |
| feature/morimoto/sa-03-recon | （記入してください） | 2026-06-11 18:18 | IN_PROGRESS | | | |
| feature/morimoto/deploy-timeout-fix | （記入してください） | 2026-06-11 20:58 | IN_PROGRESS | | | |
| feature/morimoto/fedex-pickup-carriercod-fix | （記入してください） | 2026-06-11 20:59 | IN_PROGRESS | | | |
| feature/morimoto/sa-03-change-billing | SA-03 change_billing一式（ADR-127 A-1〜A-3, B-1/B-2, E-1/E-2）+ migration | 2026-06-12 04:00 | IN_PROGRESS | | | |
| feature/morimoto/adr109-db-migration | （記入してください） | 2026-06-12 12:09 | IN_PROGRESS | | | |
| feature/morimoto/sa02-daily-recon-notify | （記入してください） | 2026-06-12 12:17 | IN_PROGRESS | | | |
| feature/morimoto/remove-review-locale-en | （記入してください） | 2026-06-12 12:53 | IN_PROGRESS | | | |
| feature/morimoto/design-site-stage1 | SA設計図書サイト Stage 1 HTML + Stage 0 GO申請 | 2026-06-12 13:00 | IN_PROGRESS | #1997 | | |
| feature/morimoto/design-site-stage0 | SA設計図書サイト Stage 0 インフラ（nginx/docker-compose/deploy.yml） | 2026-06-12 13:15 | IN_PROGRESS | | | |
| feature/morimoto/company-stats-ssot | 取引額SSOT化 v_company_stats 公式定義統一（ADR-136） | 2026-06-12 | IN_PROGRESS | #2020 | | |
| feature/morimoto/fedex-a4-test-result-persistence | FedEx A4 接続テスト結果保存 | 2026-06-14 03:29 | DONE | #2140 | 2026-06-14 | PR #2138 release にて main 反映済み |
| feature/morimoto/fedex-last-tested-position-fix | 最終確認バッジ配置修正（margin-left: auto → 0） | 2026-06-14 08:32 | DONE | #2151 | 2026-06-14 | PR #2158 release にて main 反映済み |
| feature/fedex-last-tested-date-format | 最終確認 日時フォーマット修正（時刻のみ→日付+時刻） | 2026-06-14 09:06 | DONE | #2157 | 2026-06-14 | PR #2158 release にて main 反映済み |
| feature/morimoto/sa02-kgi-assessment | SA-02 KGI G1〜G4 本番実測・docs更新 | 2026-06-14 09:56 | IN_PROGRESS | | | |
---

## 記入例

```
| feature/morimoto/your-feature-name | 受信箱 UI    | 2026-05-26 10:00 | IN_PROGRESS |     | | タブ1で作業中 |
| feature/morimoto/your-other-feature | スケジュール  | 2026-05-26 11:30 | REVIEW      | 923 | | タブ2で作業中 |
```

## 状態の種類

| 状態 | 意味 |
|------|------|
| `IN_PROGRESS` | 現在作業中（Generator が動いている） |
| `REVIEW` | PR 提出済み・Reviewer/Evaluator 待ち |
| `BLOCKED` | 問題があり停止中（しんごさん確認待ち） |
| `DONE` | PR マージ完了（ログとして永続保持） |
| feature/morimoto/adr-129-backlog-notes | ADR-129 未対応バックログ記録 | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/role-badge-color | オーナーロール色 赤→インディゴ（全テナント冪等マイグレーション） | 2026-06-11 | IN_PROGRESS | #1920 | | |
| docs/morimoto/sa-foundation-recon-audit | SA土台バッチ全体監査レポート（ADR-131/132 実装・監査文書クローズ） | 2026-06-10 | IN_PROGRESS | #1900 | | |
| feature/morimoto/adr126-error-handling | ADR-126 公開フォームエラーハンドリング（409 already_registered + i18n） | 2026-06-11 | IN_PROGRESS | #1918 | | |
| feature/morimoto/main-deploy-stamp | main デプロイ成功スタンプ（ADR-116） | 2026-06-07 | IN_PROGRESS | #1712 | | |
| feature/morimoto/ui-consistency-a | 集計枠 fieldset → Card 統一（SalesPage + CommissionsPage） | 2026-06-10 | DONE | #1919 | | |
| feature/morimoto/datatable-p2-pilot | DataTable標準化フェーズ2 Pilot（SupplierParseStatsTab） | 2026-06-10 | DONE | #1915 | | |
| feature/morimoto/fedex-ship-stage2 | ADR-128 FedEx ラベル発行・集荷予約 Stage 2 実装 | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/back-merge-main-for-adr128 | main → develop バックマージ（SA-02 Stage 3 migration 取り込み） | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/fix-develop-migration-order | develop migration 順序修正（SA-02 Stage 3 追加） | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/sync-main-to-develop-3 | main → develop フルマージ（SA-02 Stage 3 コード取り込み） | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/release-fix | develop → main リリース競合解消（run_all_migrations.sh ADR-128挿入） | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/nginx-resolver-adr133 | ADR-133 nginx resolver+proxy_pass変数化 IP固着502恒久解 | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/karte-visual-gate | カルテ見た目忠実度ゲート⑤（Phase 5a CSS 寸法是正 + 5b 視覚ゲート） | 2026-06-11 | IN_PROGRESS | | | |
| feature/morimoto/fedex-label-validation-wizard | ADR-129 FedEx Label Validation 申請支援ウィザード | 2026-06-12 | IN_PROGRESS | #1993 | | |
| feature/morimoto/design-site-smoke-autoblock | smoke④ FAIL 時 /design/ 自動遮断（ADR-134 D） | 2026-06-12 | IN_PROGRESS | | | |
| feature/morimoto/back-merge-main-for-2032 | main → develop バックマージ（hotfix f2a33605 取り込み・PR #2032 競合解消） | 2026-06-12 | DONE | | | |
| feature/morimoto/adr-135-final-checkboxes | ADR-135 受け入れ条件チェックボックス更新 + 経緯記録 | 2026-06-12 | IN_PROGRESS | #2033 | | |
| feature/morimoto/adr-135-cleanup-approvers | ADR-135 AUTHORIZED_APPROVERS/AUTHORS 一時追加削除 | 2026-06-12 | IN_PROGRESS | #2034 | | |
| feature/morimoto/migration-full-dryrun-ci | migration-test.yml 全件ドライランジョブ追加（ADR-135強化） | 2026-06-12 | DONE | #2051 | | |
| feature/morimoto/release-pr-migration-manifest | auto-release-pr.yml migration manifest バナー自動記載 | 2026-06-12 | DONE | #2052 | | |
| feature/morimoto/adr-137-company-stats-ssot | ADR-137 起案 + migration ヘッダ修正（取引額SSOT） | 2026-06-12 | DONE | #2049 | | |
| feature/morimoto/design-301-redirect | nginx /design 301リダイレクト + smoke⑤ | 2026-06-12 | DONE | #2050 | | |
| feature/morimoto/tenant-deletion-clean | テナント論理削除・物理削除 API | 2026-06-14 | DONE | #2149 | 2026-06-14 | PR #2159 release にて main 反映済み。物理削除APIは未実行・個別PO GO待ち |
| feature/morimoto/tenant-deletion-cache-fix | 論理削除・物理削除後の Redis tenant cache 無効化 | 2026-06-14 | DONE | #2154 | 2026-06-14 | PR #2159 release にて main 反映済み |
| release/develop-to-main-2159 | develop → main release（tenant deletion / ADR-108 B-1 / Discord Auto Setup） | 2026-06-14 | DONE | #2159 | 2026-06-14 | Deploy to VPS run 27486632360 success / migration success |
