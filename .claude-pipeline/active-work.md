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

| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | 備考 |
|-----------|--------------|---------|------|-----|------|
| feature/morimoto/dev-workflow-improvements | 開発ワークフロー改善 | 2026-06-02 | IN_PROGRESS | | |
| feature/morimoto/invoice-issuer-path-fix | 請求書作成 発行者情報ボタンパス修正 | 2026-06-02 | IN_PROGRESS | | |

| feature/morimoto/pre-commit-active-work-exception | （記入してください） | 2026-06-02 10:40 | IN_PROGRESS | | |
| feature/morimoto/fix-release-pr-drawbacks | （記入してください） | 2026-06-02 10:42 | IN_PROGRESS | | |
| feature/morimoto/discord-ticket-phase1 | ADR-091 KPI3 Phase 1+2 | 2026-06-02 12:53 | DONE | #1404 | |
| feature/morimoto/discord-ticket-phase3 | ADR-091 KPI3 Phase 3 | 2026-06-02 13:30 | DONE | #1406 | |
| feature/morimoto/discord-kpi4-announce | ADR-091 KPI4 アナウンス投稿 | 2026-06-02 14:00 | IN_PROGRESS | | |
| feature/morimoto/discord-newtab | （記入してください） | 2026-06-02 22:12 | IN_PROGRESS | | |
| feature/morimoto/worktree-guard-auto-recovery | worktreeガード自動リカバリー機能 | 2026-06-02 23:00 | IN_PROGRESS | | |
| feature/morimoto/discord-oauth-redirect-fix | Discord OAuth リダイレクト修正・テスト追加 | 2026-06-02 23:30 | IN_PROGRESS | | |
| feature/morimoto/migrate-consolidation | マイグレーション一括化 | 2026-06-02 23:30 | IN_PROGRESS | | |
| feature/morimoto/grafana-sidebar-nav | Grafana ナビ横タブ→サイドバー移行 | 2026-06-03 | IN_PROGRESS | | |
| feature/morimoto/schedule-card-style | スケジュール カードスタイル（背景透明化・カード化） | 2026-06-03 | IN_PROGRESS | | |
| feature/morimoto/grafana-sidebar-nav-v2 | Grafana 左列サイドバー実装（B案） | 2026-06-03 | IN_PROGRESS | | |
| feature/morimoto/schedule-responsive-tokens | スケジュール スロット高・終日エリア レスポンシブ対応 | 2026-06-03 | IN_PROGRESS | | |
| feature/morimoto/schedule-modal-polish | スケジュール 予定編集モーダル Googleカレンダー準拠デザイン改善 | 2026-06-03 | DONE | #1563 | |
| feature/morimoto/schedule-event-popover | スケジュール 既存予定クリック 詳細ポップオーバー | 2026-06-03 | DONE | #1566 | |
| feature/morimoto/schedule-popover-style | スケジュール ポップオーバー スタイル調整 | 2026-06-03 | DONE | #1569 | |
| feature/morimoto/schedule-popover-v2 | スケジュール ポップオーバー 色・作成者・配置改善 | 2026-06-03 | IN_PROGRESS | | |
| feature/morimoto/crm-hub-fix-titles | （記入してください） | 2026-06-03 23:55 | IN_PROGRESS | | |
| feature/morimoto/fix-space9-token | デザイントークン --space-9 未定義バグ修正 | 2026-06-03 | IN_PROGRESS | | |
| feature/morimoto/admin-hub-bottom-nav | SaaS管理者ハブ ボトムタブ統合 | 2026-06-04 00:06 | IN_PROGRESS | | |
| feature/morimoto/schedule-update-popover-fix | スケジュール 更新ADR-072バグ修正＋ポップオーバー説明・場所表示 | 2026-06-04 01:01 | DONE | #1593 | |
| feature/morimoto/sa-foundation-step0-claude-md | （記入してください） | 2026-06-04 09:24 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr2-audit-fix | （記入してください） | 2026-06-04 09:40 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr1-tenant-policy | テナントポリシー列追加（ADR-106） | 2026-06-04 | IN_PROGRESS | | |
| feature/morimoto/schedule-modal-description-display | スケジュール モーダル 説明・場所の表示追加 | 2026-06-04 10:06 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr3-reg-token | （記入してください） | 2026-06-04 10:50 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr4-conv-logs | （記入してください） | 2026-06-04 10:50 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr5-link-templates | （記入してください） | 2026-06-04 10:50 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr7-parse-logs | （記入してください） | 2026-06-04 10:50 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr8-invoice-snapshot | （記入してください） | 2026-06-04 11:48 | IN_PROGRESS | | |
| feature/morimoto/sa-foundation-pr6-own-inventory | A在庫テナント私有化（ADR-099） | 2026-06-04 | IN_PROGRESS | | |
| feature/morimoto/fix-company-stats-view-total-col | #1606 CI修正: v_company_stats i.total→i.total_amount | 2026-06-04 | DONE | #1615 | |
| feature/morimoto/hotfix-develop-conflict-markers | develop conflict marker修正（run_all_migrations.sh） | 2026-06-04 | DONE | #1616 | |
| feature/morimoto/remove-trust-level-ui | trust_level UI撤去（Issue #1607 / C-2） | 2026-06-04 | DONE | #1619 | |
| hotfix/back-merge-main-into-develop | develop←mainバックマージ | 2026-06-04 | IN_PROGRESS | | |
| feature/morimoto/analytics-agent-a-priority | ADR-107 ADR文書起案 | 2026-06-04 14:50 | DONE | #1622 | ADR文書のみ、マージ済み |
| feature/morimoto/adr-107-analytics-agent-a-impl | ADR-107 分析エージェント(A) 顧客優先度付け 実装 | 2026-06-04 | IN_PROGRESS | | |
| feature/morimoto/adr-108-karte-redesign | （記入してください） | 2026-06-04 15:56 | IN_PROGRESS | | |
| feature/morimoto/adr-109-status-ssot | ADR-109 status SSOT化（ADR文書のみ） | 2026-06-04 15:56 | DONE | #1630 | ADR文書のみ、マージ済み |
| feature/morimoto/adr-109-status-ssot-impl | ADR-109 status SSOT化 実装 | 2026-06-07 | IN_PROGRESS | | |
| claude-impl/20260604-074511 | ADR-108 受信箱カルテ再設計 自動実装 | 2026-06-04 | IN_PROGRESS | #1635 | |
| feature/morimoto/adr-107-safety-schedule | ADR-107 §13 安全装置 Celery beat 登録 | 2026-06-04 | DONE | #1648 | |
| feature/morimoto/fix-priority-check-conn-leak | priority_scoring_check DB接続リーク修正 | 2026-06-04 | DONE | #1652 | |
| feature/morimoto/fix-translation-import | translation.py ImportError 緊急修正 | 2026-06-04 | IN_PROGRESS | | |
| feature/morimoto/adr-110-translation-subsystem | ADR-110 会話ログ翻訳サブシステム（グロッサリ・確信度・送信下訳・3点セット） | 2026-06-04 | IN_PROGRESS | #1641 | |
| hotfix/morimoto/fix-smoke-check5-parsing | smoke[5] psql -t SET出力偽陰性修正 | 2026-06-06 | DONE | #1697 | |
| hotfix/morimoto/fix-cross-tenant-fk-schema-collision | test_products_cross_tenant_fk テナント998スキーマ衝突修正 | 2026-06-06 | DONE | #1699 | |
| hotfix/morimoto/fix-smoke-check6-failclose | smoke[6] fail-close ON_ERROR_STOP=1 修正（ロケール依存除去） | 2026-06-06 | DONE | #1700 | |
| hotfix/morimoto/fix-smoke-check6-v2 | smoke[6] -c オプション修正（docker exec stdin非接続対応） | 2026-06-06 | IN_PROGRESS | | |
| feature/morimoto/sa-18-phase2-auto-url | SA-18 Bootstrap auto-URL（SA18_PHASE2_ENABLED → salesanchor_app URL 自動組み立て） | 2026-06-07 10:35 | IN_PROGRESS | #1716 | |
| feature/morimoto/adr-116-deploy-rollback | ADR-118 ロールバック堅牢化（deploy_rollback.sh 共有・LAST_GOOD_SHA）棚上げ中 | 2026-06-07 | IN_PROGRESS | #1713 | 棚上げ中 |
| feature/morimoto/fix-rls-policy-variable-name | RLS ポリシー変数名修正（Phase2 前提条件） | 2026-06-07 | DONE | #1730 | |
| feature/morimoto/preview-section-split | DesignPreview セクション分割（衝突防止）+ §9 DataTable（PR#1759/#1761 解消） | 2026-06-08 | IN_PROGRESS | | |
| release/main-0608 | （記入してください） | 2026-06-08 12:00 | IN_PROGRESS | | |
| feature/morimoto/tabs-component | Tabs 金型 + デザインプレビュー §10（Task 5C+5D） | 2026-06-08 | DONE | #1772 | |
| feature/morimoto/fix-register-company-lookup | （記入してください） | 2026-06-08 12:11 | IN_PROGRESS | | |
| feature/morimoto/submenu-and-preview-rooms | SubMenu 金型 ＋ デザインプレビュー部品別ルーム再構成（Task 6C+6D） | 2026-06-08 12:42 | DONE | #1776 | |
| feature/morimoto/button-outline-variant | Button outline バリアント追加 | 2026-06-08 13:18 | DONE | #1779 | |
| feature/morimoto/icon-button-recon-and-standard | アイコンボタン実物基準作り直し＋プレビュー更新 | 2026-06-08 14:19 | DONE | #1780 | |
| feature/morimoto/fix-register-form-ux | （記入してください） | 2026-06-08 14:28 | IN_PROGRESS | | |
| feature/morimoto/icon-btn-size-fix | （記入してください） | 2026-06-08 14:44 | IN_PROGRESS | | |
| feature/morimoto/icon-btn-root-cause-fix | （記入してください） | 2026-06-08 15:09 | IN_PROGRESS | | |
| feature/morimoto/fix-address-empty-str-422 | （記入してください） | 2026-06-08 15:27 | IN_PROGRESS | | |
| feature/morimoto/caffeinate-failure-visibility | （記入してください） | 2026-06-08 15:35 | IN_PROGRESS | | |
| feature/morimoto/register-form-input-contract | （記入してください） | 2026-06-08 15:57 | IN_PROGRESS | | |
| feature/morimoto/modal-component | （記入してください） | 2026-06-08 15:57 | IN_PROGRESS | | |
| feature/morimoto/empty-state-component | （記入してください） | 2026-06-08 16:56 | IN_PROGRESS | | |
| feature/morimoto/empty-state-icon-fix | （記入してください） | 2026-06-08 20:57 | IN_PROGRESS | | |
| feature/morimoto/definition-audit-2026-06-08 | （記入してください） | 2026-06-08 22:10 | IN_PROGRESS | | |
| feature/morimoto/decision-layer-01-recon | 決定レイヤー① recon 差分可視化 | 2026-06-09 00:17 | DONE | #1799 | |
| feature/morimoto/status-presentation-ssot | 決定レイヤー 1 ステップ1 — SSoT中央表・補助関数 | 2026-06-09 01:30 | DONE | #1800 | |
| feature/morimoto/status-ssot-step2a | 決定レイヤー 1 ステップ2a — 差分可視化 + staff/bot 現状維持 | 2026-06-09 08:22 | DONE | #1801 | |
| feature/morimoto/status-ssot-step2b | 決定レイヤー 1 ステップ2b — 全29サイト getStatusPresentation() 置換 | 2026-06-09 10:00 | DONE | #1803 | |
| feature/morimoto/sop-kpi2-impl | SOPコンプライアンス保証機構（ADR-119 KPI2）— process-artifacts gate | 2026-06-08 | IN_PROGRESS | | |
| hotfix/back-merge-main-into-develop-2 | （記入してください） | 2026-06-09 10:34 | IN_PROGRESS | | |
| feature/morimoto/claude-md-sop-update | CLAUDE.md 標準開発フロー節を新SOPに差し替え（ADR-121） | 2026-06-09 | IN_PROGRESS | | |
| feature/morimoto/status-ssot-step3-lint-error | （記入してください） | 2026-06-09 11:01 | IN_PROGRESS | | |
| feature/morimoto/sop-dedup-fix | sop-followup重複ガード PR番号単位修正（Reviewer指摘）| 2026-06-09 | IN_PROGRESS | | |
| feature/morimoto/gate-trigger-fix | process-artifacts gate trigger develop のみに修正（リリースPR誤検知解消） | 2026-06-09 | IN_PROGRESS | | |
| feature/morimoto/gate-release-skip | process-artifacts gate リリースPRスキップ修正（#1811誤修正の正確な対処） | 2026-06-09 | IN_PROGRESS | | |
| feature/morimoto/products-page-edit | ProductsPage モーダル→専用ページ化（ADR-122 Phase D） | 2026-06-09 | DONE | #1828 | |
| feature/morimoto/modal-xl-replacements | OrdersPage modal-overlay 3件→Modal(xl)置換（ADR-122） | 2026-06-09 | DONE | #1827 | |
| feature/morimoto/datatable-invoices-pilot | InvoicesPage DataTable パイロット（ADR-067） | 2026-06-09 | DONE | #1841 | |
| feature/morimoto/datatable-preview | DataTable 金型 + onRowClick + 制御型ページ送り（Task 4C+4D+step2） | 2026-06-08 | DONE | #1847 | |
| feature/morimoto/fedex-smoke-switch | FedEx live smoke スイッチ ON（SMOKE_SERVICE_TOKEN + deploy.yml 修正） | 2026-06-10 | DONE | #1892 | |
| feature/morimoto/fedex-smoke-path-fix | FedEx smoke スクリプト API パス修正（/api/v1/shipping/calculate） | 2026-06-10 | IN_PROGRESS | | |
| feature/morimoto/audit-log-coverage-medium | 監査ログ中重要度4系統 | 2026-06-11 | DONE | #1916 | |
| feature/morimoto/adr-129-backlog-notes | ADR-129 未対応バックログ記録 | 2026-06-11 | IN_PROGRESS | | |
| docs/morimoto/sa-foundation-recon-audit | SA土台バッチ全体監査レポート（ADR-095〜106 適合確認） | 2026-06-10 | IN_PROGRESS | | |
---

## 記入例

```
| feature/morimoto/your-feature-name | 受信箱 UI    | 2026-05-26 10:00 | IN_PROGRESS |     | タブ1で作業中 |
| feature/morimoto/your-other-feature | スケジュール  | 2026-05-26 11:30 | REVIEW      | 923 | タブ2で作業中 |
```

## 状態の種類

| 状態 | 意味 |
|------|------|
| `IN_PROGRESS` | 現在作業中（Generator が動いている） |
| `REVIEW` | PR 提出済み・Reviewer/Evaluator 待ち |
| `BLOCKED` | 問題があり停止中（しんごさん確認待ち） |
| `DONE` | PR マージ完了（ログとして永続保持） |
