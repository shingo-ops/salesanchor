> 【凍結アーカイブ】この台帳への新規登録は廃止されました。
> 新規登録は .claude-pipeline/active-work.d/（1ブランチ1ファイル・机作りで自動作成）へ。
> 既存行の状態更新のみ scripts/ledger-update.sh 経由で可。一覧表示は scripts/ledger-view.sh。

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
| release/reaper-concurrency-design | reaper並行実行の構造問題と改善設計の引き継ぎ追記 | 2026-07-23 14:33 | IN_PROGRESS | | main | base=origin/main・handoff追記予約 |
| release/infra-uptime-kuma-v1 | uptime-kuma 1.23系への載せ替え（API自動登録互換） | 2026-07-18 21:00 | DONE | | main | base=origin/main・PO GO済み |
| release/resource-optimization-evidence | サーバーリソース最適化 ①未使用Dockerイメージの排除(prod1) | 2026-07-20 | DONE | | main | base=origin/main・docs-only |
| release/secrets-permission-ssot | 権限・秘密SSOT化テーマの正本化 | 2026-07-20 | DONE | #3006 | main | merged: PR #3006 / e0b46756c4752fef520babdb61cbf6ebb9b57cf4 |
| release/deal-removal-stage2-q-orders | deal-removal stage2-Q: orders deal_id dependency removed | 2026-07-20 | DONE | #2995 | main | merged: PR #2995 / d791de092a07bdff7718442470c1063103873243 |
| release/ledger-done-2988 | ledger-done: register #2988 | 2026-07-20 | DONE | #2993 | main | merged: PR #2993 / d791de092a07bdff7718442470c1063103873243 |
| release/page-header-v2-rev5-fix | ページヘッダー金型v2 改訂5本文の是正追記 | 2026-07-20 | DONE | #3000 | main | merged: PR #3000 / bdb8e4c847643077dcd03ece86f5e7d2dd49d7a6 |
| release/page-header-v2-ideal-rev5 | ページヘッダー金型v2 改訂5（操作台金型・design/README追記） | 2026-07-20 | DONE | #2998 | main | merged: PR #2998 / eb111a010cdc1a8aa389ade98a87de8f6cd61460 |
| release/field-size-tokens | 入力部品 寸法金型トークン新設 | 2026-07-21 | DONE | | main | base=origin/main・docs-only |
| release/field-size-leads | リードの操作台に寸法金型を適用 | 2026-07-21 | DONE | | main | base=origin/main・frontend/leads |
| release/toolbar-edge-4px | 操作台の最右ボタンに4px右余白を金型化 | 2026-07-21 | DONE | | main | base=origin/main・frontend/content-toolbar |
| release/toolbar-part | 操作台ContentToolbar部品の新設 | 2026-07-20 | DONE | | | 本カード作業中 |
| release/toolbar-leads | リード1画面を操作台ContentToolbarへ差し替え | 2026-07-20 | DONE | | | 本カード作業中 |
| release/rev5-tidy | 教訓重複8行の削除＋改訂5を時系列末尾へ移動 | 2026-07-20 | DONE | | | 本カード作業中 |
| release/page-title-design | ページタイトル設計図一式（component-ssot 優先1） | 2026-07-18 00:00 | DONE | | main | base=origin/main・docs-only |
| release/page-title-d2b | 詳細・作成5ページのページ題名を金型へ一括統一（便2b/D2） | 2026-07-18 23:43 | DONE | #2955 | main | merged: PR #2955 / 9a815e38705775bbe0d8b3ebb3376afae27c69dd |
| release/header-ben3a-listpages | 一覧系の新規作成/実行ボタンを本文一覧直上へ移動（便3a） | 2026-07-19 22:50 | DONE | | main | base=origin/main・frontend/listpages |
| release/sched-padding-fix | スケジュール外枠の二重余白解消（schedule.css padding 削除） | 2026-07-19 10:50 | DONE | | main | base=origin/main・frontend/css |
| release/infra-alert-delivery | 通知配達係 Alertmanager 追加＋誤報掃除（Discord 集約・重い exporter 隔離） | 2026-07-18 19:48 | DONE | | main | base=origin/main・PO GO済み |
| release/agent-complete-design | エージェント完結の設計体制(To-Be) 3ファイル標準への分割と索引登録 | 2026-07-03 06:43 | DONE | #2757 | main | merged: PR #2757 / f965e8e6 |
| release/agent-complete-design-lessons | エージェント完結の設計体制(To-Be) 教訓便（起因ラベル・#2761記帳・5W2H-002） | 2026-07-03 12:46 | DONE | #2764 | main | merged: PR #2764 / 2ed5826a |
| release/doc-estate-theme | 文書体系（ナレッジベース）起票 | 2026-07-03 13:52 | DONE | | main | base=main・docs-only |
| release/txn-order-items-ben2 | 便2 実装（order_items 新設＋仕入接続） | 2026-07-03 | REVIEW | #2756 | main | base=main・PR提出済み |
| release/txn-conv-ben1b | 便1b 会話ログの背骨必須化（echo穴埋め・遡及backfill・NOT NULL） | 2026-07-03 | DONE | | main | base=main・push/PR待ち |
| release/branch-guardrail-close-main | process-artifacts gate 二重定義検出（docs / script） | 2026-07-02 | DONE | | main | base=main・PO GO待ち |
| release/worktree-canon-main | worktree 手順の正典化（docs / script） | 2026-07-02 | DONE | | main | base=main・new-worktree.sh 正典化・PO GO待ち |
| release/go-record-transcription-auto | GO記録の自動転記（案X）正本変更（docs-only） | 2026-07-02 | DONE | | main | base=main・docs-only・PO GO待ち |
| release/stop-gas-compat-seed-main | migrate_roles_gas_compat 停止（run_all_migrations.sh 1行のみ・base=main） | 2026-06-28 | DONE | #2658 | main | merged #2658 |
| release/morimoto/ticket-hide-start | チケット発行後 ticket-start を本人非表示（1人1チケット徹底・ADR-091） | 2026-06-28 | DONE | #2655 | main | merged #2655 |
| feature/morimoto/ticket-hide-start | チケット発行後 ticket-start を本人非表示（1人1チケット徹底・ADR-091） | 2026-06-28 | DONE | | | 実装済み・release/* に移行 |
| release/merge-develop-to-main | develop→main 競合解消リリースブランチ（#2641含む全9ファイル develop優先解消） | 2026-06-28 | IN_PROGRESS | | main | base=develop+main merge |
| release/db-ssot-conv-unif | 会話データの一元化（conversation-unification）設計図追加 | 2026-07-10 09:32 | DONE | #2870 | main | merged: PR #2870 |
| release/db-ssot-theme | DB設計のSSOT化 新テーマ器（あるべき姿・KGI・表紙＋索引） | 2026-07-10 07:38 | DONE | #2868 | main | merged: PR #2868 / 1e938f34 |
| release/db-ssot-handover | 引き継ぎメモ追加＋親READMEにリンク | 2026-07-10 10:49 | DONE | #2871 | main | merged: PR #2871 |
| release/db-ssot-handover-next | 引き継ぎメモに次回の入り口を追記 | 2026-07-10 12:37 | DONE | #2872 | main | closed: PR #2872 |
| release/db-ssot-handover-rewrite | 引き継ぎメモの次回入り口を『作り直し範囲の見極め』に書き直し | 2026-07-10 13:04 | DONE | #2873 | main | merged: PR #2873 |
| release/db-ssot-forecast-separation | 予測値の分離 設計図追加 | 2026-07-10 14:24 | DONE | #2875 | main | merged: PR #2875 |
| release/db-ssot-money-consolidation | 金額の集約 設計図追加 | 2026-07-10 15:49 | DONE | #2876 | main | merged: PR #2876 |
| release/db-ssot-impl-plan | 本丸実装の計画 追加 | 2026-07-11 06:52 | DONE | #2883 | main | merged: PR #2883 / e75da4cf |
| release/db-ssot-leads-dead-columns-decision | leads未使用疑い7列をSSOT化完了後の削除候補としてメモ | 2026-07-14 06:19 | DONE | #2904 | main | merged: PR #2904 / 9b75c7d268909818a3dc2e7995d76befe76159fd |
| release/dp-sec6-ledger-done-branch | design-partner §6 の台帳DONE化教訓追記 | 2026-07-18 16:24 | DONE | #2944 | main | merged: PR #2944 / 81165c73a7a7ae71dc8e8326b0c465d88ba37db9 |
| release/dp-sec6-20260720-lessons | design-partner.md §6 の本日教訓追記 | 2026-07-20 | DONE | | main | dp-sec6-20260720 |
| release/deal-removal-stage1-design | deal-removal 段階①の差分設計（README・design.md） | 2026-07-18 17:02 | DONE | #2948 | main | merged: PR #2948 / 28bb3bda6913177b3add8971756202d505214b70 |
| release/deal-removal-stage1-impl-be | deal-removal 段階①のバックエンド実装（leads 3列追加・商談化でdeals書き込み停止） | 2026-07-18 17:30 | DONE | #2956 | main | merged: PR #2956 / d9c58814aae510139d88fede5238a208ac49c2d4 |
| release/db-ssot-deal-removal-design | deals廃止設計の正本化（README・design.md） | 2026-07-18 15:48 | DONE | #2942 | main | merged: PR #2942 / 82d5c2132a7d5c6701c48c4000c743d090c33854 |
| release/i18n-missing-key-guard | i18n 全 prefix CI ガード（check-i18n-dashboard-schedule → check-i18n-missing-keys リネーム＋全prefix対応） | 2026-06-26 | DONE | #2646 | main | merged #2646 |
| feature/morimoto/fedex-guide-step1-7-cta | FedEx ETD ガイド 1-7 保存成功後 CTA テキスト追加（FE のみ・ADR-027） | 2026-06-26 | DONE | #2625 | | base=develop |
| release/morimoto/translation-model-flashlite | 送信翻訳モデル切替（MODEL_SEND: gemini-2.5-pro → flash-lite） | 2026-06-26 | DONE | #2627 | main | main マージ済み・本番デプロイ済み |
| feature/morimoto/tenant-feature-switch-mvp | テナント単位フィーチャーフラグ MVP（tenant_features テーブル・require_feature・FeatureGate） | 2026-06-27 | DONE | #2631 |  | merged #2631 |
| release/carrier-credentials-reset-tenant-ctx | ADR-072 鍵保存後 reset_tenant_context 挿入（cherry-pick #2621） | 2026-06-26 | DONE | #2623 | main | merged #2623 |
| release/fedex-guide-step1-7 | FedEx ETD ガイド Step1-7 main リリース（cherry-pick #2611） | 2026-06-26 | DONE | #2615 | main | main マージ済み |
| release/carrier-credential-form-refactor | CarrierCredentialForm 切り出し main リリース（cherry-pick #2601） | 2026-06-26 | DONE | #2608 | main | main マージ済み |
| feature/morimoto/carrier-credential-form | CarrierCredentialForm 切り出し（挙動不変リファクタ・第1段） | 2026-06-26 | DONE | #2601 |  | merged #2601 |
| feature/morimoto/fix-tenant-create-tx-double-begin | テナント作成時 SQLAlchemy tx 二重開始解消（壁1） | 2026-06-24 | DONE | #2604 | | develop マージ済み 2026-06-26 |
| release/morimoto/outbound-translation-fix | outbound送信翻訳バグ修正（段階A）draft_id経由確認済み英訳適用 | 2026-06-26 | DONE | #2606 | main | base=main |
| release/morimoto/inventory-ui-cleanup | /inventory UI整理 — アクションバー削除・タブ集約・警告移動（ADR-093） | 2026-06-24 | DONE | | main | base=main |
| release/setup-guide-screenshot-maxwidth | FedExセットアップガイド スクショ幅修正本番リリース | 2026-06-24 | DONE | #2536 | - | merged #2536 |
| release/fedex-guide-fullscreen-to-main | FedEx ETD セットアップガイド独立レイアウト化＋進捗バー固定 → main リリース | 2026-06-23 | DONE | #2524 |  | merged #2524 |
| feature/morimoto/fedex-guide-fullscreen | FedEx ETD セットアップガイド独立レイアウト化＋進捗バー固定 | 2026-06-23 | DONE | #2523 | | develop マージ済み |
| release/morimoto/schedule-i18n-main | スケジュールナビの文言追加（nav.scheduleSettings） | 2026-06-22 | DONE | | | frontend/src/locales/ja.json + en.json |
| release/fedex-etd-step1-to-main | FedEx ETD Step1 ガイド develop→main リリース | 2026-06-22 | DONE | #2479 |  | merged #2479 |
| feature/morimoto/rls-message-translations | SA-18 ③-b(5) message_translations RLS 有効化 | 2026-06-23 | DONE | #2518 |  | merged #2518 |
| feature/morimoto/remove-chromatic-ci | Chromatic CI 削除（Chromatic Snapshot / UI Tests の配線整理） | 2026-06-23 | DONE | #2519 |  | merged #2519 |
| feature/morimoto/priority-prospects-bootstrap | ② priority-prospects PG/RLS bootstrap 修正（Track B 分離） | 2026-06-23 | DONE | #2520 |  | merged #2520 |
| feature/morimoto/inventory-aggregated | GET /inventory/aggregated エンドポイント（集計ピボット・best-pick） | 2026-06-23 | DONE | #2514 |  | merged #2514 |
| feature/morimoto/trackb-order-based | Track B決定1 成約定義の一本化（受注ベース） | 2026-06-23 | DONE | #2507 |  | PR #2507 クローズ・不採用 |
| feature/morimoto/ssot-tcg-type-fk | SSOT大掃除② `products.tcg_type` FK固定 | 2026-06-22 | DONE | #2484 |  | merged #2484 |
| feature/fedex-etd-guide-clean | FedEx ETD 設定ガイド Level1 / ETD upload 422 ガード | 2026-06-22 | DONE | #2464 |  | merged #2464 |
| feature/morimoto/advisor-weekly-w1-defensive-api | Advisor Phase 1 PR-W1 守り3種 集計＋離脱スコア＋ランク API | 2026-06-20 | DONE | #2396 |  | merged #2396 |
| codex/advisor-phase1-new-goal-advice-root | Advisor Phase 1 PR-4 新規モード 逆算アドバイスAPI | 2026-06-20 | DONE | #2386 |  | merged #2386 |
| codex/advisor-phase1-customer-contact | Advisor Phase 1 PR-3 顧客別 接触集計API | 2026-06-20 | DONE | #2384 |  | merged #2384 |
| feature/morimoto/sidebar-click-collapse | サイドバーの自動展開抑止（クリック後だけ一時停止） | 2026-06-19 | DONE | | | click後の hover 再展開を抑止 |
| feature/morimoto/schedule-gcal-pr1-tokens | Schedule Google Calendar UI PR2/PR3/PR4 カレンダー本体 + settings + backend category | 2026-06-20 | DONE | | | `SchedulePage.tsx` を内製グリッドへ置換し、`/schedule/settings` と backend の `calendar_events.category` / `/calendar/events` レスポンス拡張、フロントの API 優先正規化、保守的 backfill migration 追加まで完了 |
| feature/morimoto/paypal-sandbox-failcheck | PayPal Sandbox smoke coverage閾値除去 | 2026-06-20 | COMPLETED | #2354 | green | run 27833818674 / gate 27833818677 を確認済み |
| dashboard-pr2 | Discord ticket gateway visibility + lead紐付け修正 | 2026-06-19 | DONE | | | #2360 反映後の follow-up 修正 |
| docs/fedex-pr-a4-recon-design | FedEx A4 接続テスト結果保存 recon/design（docs-only） | 2026-06-14 | DONE | | | |
| feature/morimoto/dev-workflow-improvements | 開発ワークフロー改善 | 2026-06-02 | DONE | | | |
| feature/morimoto/invoice-issuer-path-fix | 請求書作成 発行者情報ボタンパス修正 | 2026-06-02 | DONE | | | |
| feature/morimoto/etd-scaffold-adr137 | ADR-137 ETD骨格 / owner: shingo | 2026-06-19 09:00 | DONE | #2340 | | merged:ce03ca3 |

| feature/morimoto/pre-commit-active-work-exception | （記入してください） | 2026-06-02 10:40 | DONE | | | |
| feature/morimoto/fix-release-pr-drawbacks | （記入してください） | 2026-06-02 10:42 | DONE | | | |
| feature/morimoto/discord-ticket-phase1 | ADR-091 KPI3 Phase 1+2 | 2026-06-02 12:53 | DONE | #1404 | | |
| feature/morimoto/discord-ticket-phase3 | ADR-091 KPI3 Phase 3 | 2026-06-02 13:30 | DONE | #1406 | | |
| feature/morimoto/discord-kpi4-announce | ADR-091 KPI4 アナウンス投稿 | 2026-06-02 14:00 | DONE | | | |
| feature/morimoto/discord-newtab | （記入してください） | 2026-06-02 22:12 | DONE | | | |
 - release/inbox-invoice-form-send-spec : reserve docs/specs/README.md, docs/specs/inbox/README.md (spec create)
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
| feature/morimoto/adr-109-status-ssot-impl | ADR-109 status SSOT化 実装 | 2026-06-07 | DONE | #1726 |  | merged #1726 |
| claude-impl/20260604-074511 | ADR-108 受信箱カルテ再設計 自動実装 | 2026-06-04 | IN_PROGRESS | #1635 | | |
| feature/morimoto/adr-107-safety-schedule | ADR-107 §13 安全装置 Celery beat 登録 | 2026-06-04 | DONE | #1648 | | |
| feature/morimoto/fix-priority-check-conn-leak | priority_scoring_check DB接続リーク修正 | 2026-06-04 | DONE | #1652 | | |
| feature/morimoto/fix-translation-import | translation.py ImportError 緊急修正 | 2026-06-04 | DONE | | | |
| feature/morimoto/adr-110-translation-subsystem | ADR-110 会話ログ翻訳サブシステム（グロッサリ・確信度・送信下訳・3点セット） | 2026-06-04 | DONE | #1641 | | |
| hotfix/morimoto/fix-smoke-check5-parsing | smoke[5] psql -t SET出力偽陰性修正 | 2026-06-06 | DONE | #1697 | | |
| hotfix/morimoto/fix-cross-tenant-fk-schema-collision | test_products_cross_tenant_fk テナント998スキーマ衝突修正 | 2026-06-06 | DONE | #1699 | | |
| hotfix/morimoto/fix-smoke-check6-failclose | smoke[6] fail-close ON_ERROR_STOP=1 修正（ロケール依存除去） | 2026-06-06 | DONE | #1700 | | |
| hotfix/morimoto/fix-smoke-check6-v2 | smoke[6] -c オプション修正（docker exec stdin非接続対応） | 2026-06-06 | DONE | | | |
| feature/morimoto/sa-18-phase2-auto-url | SA-18 Bootstrap auto-URL（SA18_PHASE2_ENABLED → salesanchor_app URL 自動組み立て） | 2026-06-07 10:35 | DONE | #1716 |  | merged #1716 |
| feature/morimoto/adr-116-deploy-rollback | ADR-118 ロールバック堅牢化（deploy_rollback.sh 共有・LAST_GOOD_SHA）棚上げ中 | 2026-06-07 | DONE | #1713 |  | PR #1713 クローズ・不採用 |
| feature/morimoto/fix-rls-policy-variable-name | RLS ポリシー変数名修正（Phase2 前提条件） | 2026-06-07 | DONE | #1730 | | |
| feature/morimoto/preview-section-split | DesignPreview セクション分割（衝突防止）+ §9 DataTable（PR#1759/#1761 解消） | 2026-06-08 | DONE | | | |
| release/main-0608 | （記入してください） | 2026-06-08 12:00 | DONE | | | |
| feature/morimoto/tabs-component | Tabs 金型 + デザインプレビュー §10（Task 5C+5D） | 2026-06-08 | DONE | #1772 | | |
| feature/morimoto/fix-register-company-lookup | （記入してください） | 2026-06-08 12:11 | DONE | #1773 |  | merged #1773 |
| feature/morimoto/submenu-and-preview-rooms | SubMenu 金型 ＋ デザインプレビュー部品別ルーム再構成（Task 6C+6D） | 2026-06-08 12:42 | DONE | #1776 | | |
| feature/morimoto/button-outline-variant | Button outline バリアント追加 | 2026-06-08 13:18 | DONE | #1779 | | |
| feature/morimoto/icon-button-recon-and-standard | アイコンボタン実物基準作り直し＋プレビュー更新 | 2026-06-08 14:19 | DONE | #1780 | | |
| feature/morimoto/fix-register-form-ux | （記入してください） | 2026-06-08 14:28 | DONE | #1782 |  | merged #1782 |
| feature/morimoto/icon-btn-size-fix | （記入してください） | 2026-06-08 14:44 | DONE | #1783 |  | merged #1783 |
| feature/morimoto/icon-btn-root-cause-fix | （記入してください） | 2026-06-08 15:09 | DONE | #1786 |  | merged #1786 |
| feature/morimoto/fix-address-empty-str-422 | （記入してください） | 2026-06-08 15:27 | DONE | #1785 |  | merged #1785 |
| feature/morimoto/caffeinate-failure-visibility | （記入してください） | 2026-06-08 15:35 | DONE | #1788 |  | merged #1788 |
| feature/morimoto/register-form-input-contract | （記入してください） | 2026-06-08 15:57 | DONE | #1790 |  | merged #1790 |
| feature/morimoto/modal-component | （記入してください） | 2026-06-08 15:57 | DONE | #1791 |  | merged #1791 |
| feature/morimoto/empty-state-component | （記入してください） | 2026-06-08 16:56 | DONE | #1792 |  | merged #1792 |
| feature/morimoto/empty-state-icon-fix | （記入してください） | 2026-06-08 20:57 | DONE | #1796 |  | merged #1796 |
| feature/morimoto/definition-audit-2026-06-08 | （記入してください） | 2026-06-08 22:10 | DONE | #1798 |  | merged #1798 |
| feature/morimoto/decision-layer-01-recon | 決定レイヤー① recon 差分可視化 | 2026-06-09 00:17 | DONE | #1799 | | |
| feature/morimoto/status-presentation-ssot | 決定レイヤー 1 ステップ1 — SSoT中央表・補助関数 | 2026-06-09 01:30 | DONE | #1800 | | |
| feature/morimoto/status-ssot-step2a | 決定レイヤー 1 ステップ2a — 差分可視化 + staff/bot 現状維持 | 2026-06-09 08:22 | DONE | #1801 | | |
| feature/morimoto/status-ssot-step2b | 決定レイヤー 1 ステップ2b — 全29サイト getStatusPresentation() 置換 | 2026-06-09 10:00 | DONE | #1803 | | |
| feature/morimoto/sop-kpi2-impl | SOPコンプライアンス保証機構（ADR-119 KPI2）— process-artifacts gate | 2026-06-08 | DONE | #1802 |  | merged #1802 |
| hotfix/back-merge-main-into-develop-2 | （記入してください） | 2026-06-09 10:34 | DONE | #1805 |  | merged #1805 |
| feature/morimoto/claude-md-sop-update | CLAUDE.md 標準開発フロー節を新SOPに差し替え（ADR-121） | 2026-06-09 | DONE | #1808 |  | merged #1808 |
| feature/morimoto/status-ssot-step3-lint-error | （記入してください） | 2026-06-09 11:01 | DONE | #1809 |  | merged #1809 |
| feature/morimoto/sop-dedup-fix | sop-followup重複ガード PR番号単位修正（Reviewer指摘） | 2026-06-09 | DONE | #1810 |  | merged #1810 |
| feature/morimoto/gate-trigger-fix | process-artifacts gate trigger develop のみに修正（リリースPR誤検知解消） | 2026-06-09 | DONE | #1811 |  | merged #1811 |
| feature/morimoto/gate-release-skip | process-artifacts gate リリースPRスキップ修正（#1811誤修正の正確な対処） | 2026-06-09 | DONE | #1812 |  | merged #1812 |
| feature/morimoto/products-page-edit | ProductsPage モーダル→専用ページ化（ADR-122 Phase D） | 2026-06-09 | DONE | #1828 | | |
| feature/morimoto/modal-xl-replacements | OrdersPage modal-overlay 3件→Modal(xl)置換（ADR-122） | 2026-06-09 | DONE | #1827 | | |
| feature/morimoto/datatable-invoices-pilot | InvoicesPage DataTable パイロット（ADR-067） | 2026-06-09 | DONE | #1841 | | |
| feature/morimoto/datatable-preview | DataTable 金型 + onRowClick + 制御型ページ送り（Task 4C+4D+step2） | 2026-06-08 | DONE | #1847 | | |
| feature/morimoto/brand-navy-accent | （記入してください） | 2026-06-11 04:16 | DONE | #1925 |  | merged #1925 |
| docs/morimoto/sa-02-recon | （記入してください） | 2026-06-11 04:45 | DONE | #1929 |  | merged #1929 |
| feature/morimoto/adr-127-registration-post-forms | （記入してください） | 2026-06-11 04:46 | DONE | #1927 |  | merged #1927 |
| feature/morimoto/sa-02-stage1-channel-webhook | （記入してください） | 2026-06-11 10:29 | DONE | #1932 |  | merged #1932 |
| feature/morimoto/active-work-done-cleanup | （記入してください） | 2026-06-11 10:44 | DONE | #1933 |  | merged #1933 |
| feature/morimoto/adr127-phase1-address-form | （記入してください） | 2026-06-11 11:11 | DONE | #1934 |  | merged #1934 |
| feature/morimoto/zero-downtime-deploy | （記入してください） | 2026-06-11 11:25 | DONE | #1938 |  | merged #1938 |
| feature/morimoto/sa-02-post-deploy-docs | （記入してください） | 2026-06-11 11:27 | DONE | #1935 |  | merged #1935 |
| feature/morimoto/sa-02-stage3-manual-record | （記入してください） | 2026-06-11 11:33 | DONE | #1937 |  | merged #1937 |
| feature/morimoto/adr127-phase2-dual-gate | ADR-127 §4 第1層ゲート | 2026-06-11 11:35 | DONE | #1936 |  | merged #1936 |
| feature/morimoto/adr127-phase2b-registered-label | （記入してください） | 2026-06-11 12:51 | DONE | #1942 |  | merged #1942 |
| feature/morimoto/zero-downtime-polish | （記入してください） | 2026-06-11 12:53 | DONE | #1946 |  | merged #1946 |
| feature/morimoto/sa-02-stage3-plan-update | （記入してください） | 2026-06-11 13:06 | DONE | #1943 |  | merged #1943 |
| feature/morimoto/sa-02-stage4-company-conv-logs | SA-02 段階4: 会社詳細会話履歴タブ | 2026-06-11 13:09 | DONE | #1945 | ✅ | |
| feature/morimoto/sa-02-stage4-docs | SA-02 進捗ドキュメント更新 | 2026-06-11 13:15 | DONE | #1949 |  | merged #1949 |
| feature/morimoto/adr127-phase2c-button-color | （記入してください） | 2026-06-11 13:50 | DONE | #1950 |  | merged #1950 |
| feature/morimoto/sa-02-stage2-migration-prep | SA-02 段階2 移行スクリプト準備 | 2026-06-11 13:58 | DONE | #1952 | | |
| feature/morimoto/sa-02-stage2-rollback-fix | SA-02 段階2 rollback条件修正 | 2026-06-11 16:50 | DONE | #1965 | | |
| feature/morimoto/sa-02-stage2-plan-update | SA-02 段階2 plan記録更新 | 2026-06-11 17:00 | DONE | | | |
| feature/morimoto/sync-main-develop-adr128 | main/develop 同期（ADR-128 migration 競合解消） | 2026-06-11 14:07 | DONE | #1953 | | |
| feature/morimoto/add-fedex-migration-to-main | （未使用ブランチ） | 2026-06-11 14:16 | DONE | | | |
| feature/morimoto/nginx-reload-migration-total | （記入してください） | 2026-06-11 15:54 | DONE | #1963 |  | merged #1963 |
| feature/morimoto/adr127-phase2c-css-fix | （記入してください） | 2026-06-11 16:45 | DONE | #1966 |  | merged #1966 |
| feature/morimoto/gate-bug-note | （記入してください） | 2026-06-11 18:12 | DONE | #1973 |  | merged #1973 |
| feature/morimoto/sa-03-recon | （記入してください） | 2026-06-11 18:18 | DONE | #1975 |  | merged #1975 |
| feature/morimoto/deploy-timeout-fix | （記入してください） | 2026-06-11 20:58 | DONE | #1978 |  | merged #1978 |
| feature/morimoto/carrier-credential-form | CarrierCredentialForm 切り出し（挙動不変リファクタ・第1段） | 2026-06-26 | DONE | #2601 |  | merged #2601 |
| feature/morimoto/fedex-pickup-carriercod-fix | （記入してください） | 2026-06-11 20:59 | DONE | #2330 |  | merged #2330 |
| feature/morimoto/sa-03-change-billing | SA-03 change_billing一式（ADR-127 A-1〜A-3, B-1/B-2, E-1/E-2）+ migration | 2026-06-12 04:00 | DONE | #1979 |  | merged #1979 |
| feature/morimoto/adr109-db-migration | （記入してください） | 2026-06-12 12:09 | DONE | #1994 |  | merged #1994 |
| feature/morimoto/sa02-daily-recon-notify | （記入してください） | 2026-06-12 12:17 | DONE | #1995 |  | merged #1995 |
| feature/morimoto/remove-review-locale-en | （記入してください） | 2026-06-12 12:53 | DONE | #1998 |  | merged #1998 |
| feature/morimoto/design-site-stage1 | SA設計図書サイト Stage 1 HTML + Stage 0 GO申請 | 2026-06-12 13:00 | DONE | #1997 |  | merged #1997 |
| feature/morimoto/design-site-stage0 | SA設計図書サイト Stage 0 インフラ（nginx/docker-compose/deploy.yml） | 2026-06-12 13:15 | DONE | #2021 |  | merged #2021 |
| feature/morimoto/company-stats-ssot | 取引額SSOT化 v_company_stats 公式定義統一（ADR-136） | 2026-06-12 | DONE | #2020 |  | merged #2020 |
| feature/morimoto/fedex-a4-test-result-persistence | FedEx A4 接続テスト結果保存 | 2026-06-14 03:29 | DONE | #2140 | 2026-06-14 | PR #2138 release にて main 反映済み |
| feature/morimoto/fedex-last-tested-position-fix | 最終確認バッジ配置修正（margin-left: auto → 0） | 2026-06-14 08:32 | DONE | #2151 | 2026-06-14 | PR #2158 release にて main 反映済み |
| feature/fedex-last-tested-date-format | 最終確認 日時フォーマット修正（時刻のみ→日付+時刻） | 2026-06-14 09:06 | DONE | #2157 | 2026-06-14 | PR #2158 release にて main 反映済み |
| feature/morimoto/sa02-kgi-assessment | SA-02 KGI G1〜G4 本番実測・docs更新 | 2026-06-14 09:56 | DONE | #2162 | | |
| feature/morimoto/sa02-r1-r2-convlog-links | SA-02 残課題 R1（contact_id補完）/ R2（手動記録company_id補完） | 2026-06-14 | DONE | #2208 | 2026-06-15 | R3 Stage 2 は Shingo GO 待ち |
| feature/morimoto/adr090-pr3-fk-remap-design | ADR-090 PR3 下流FK再マップ 設計（recon/design・docs-only） | 2026-06-15 16:23 | DONE | #2228 | | |
| feature/morimoto/seed-mega-products | 商品マスタ ポケモンカードゲームMEGAシリーズ 追加 | 2026-06-15 23:10 | DONE | #2231 | | |
| feature/morimoto/fix-tcg-type-dedup | tcg_type_master 重複 code 統合（pokemon/weiss→正規 code） | 2026-06-15 23:52 | DONE | #2235 | | |
| feature/morimoto/paypal-invoice-422-debug | PayPal テスト請求書 422 エラー詳細露出・デバッグ | 2026-06-16 00:30 | DONE | #2237 | | |
| feature/morimoto/paypal-invoice-invoicer-fix | PayPal 請求書 422 根本修正（invoicer email 明示） | 2026-06-16 01:00 | DONE | #2239 |  | merged #2239 |
| main | （自動登録） | 2026-06-18 05:04 | DONE | #2314 | | merged:42d4d8a merged時自動登録・要確認 |
| feature/morimoto/funnel-dashboard-stage1-seed-fix | （自動登録・要補完） | 2026-06-18 08:07 | REVIEW | #2346 | | 自動登録 |
| feature/morimoto/etd-scaffold-adr137 | （自動登録・要補完） | 2026-06-18 13:13 | DONE | #2340 | | 自動登録 merged:ce03ca3 |
| feature/morimoto/executor-preflight-hook | （自動登録） | 2026-06-19 00:27 | DONE | #2347 | | merged:1e0efff merged時自動登録・要確認 |
| feature/morimoto/paypal-sandbox-smoke | （自動登録・要補完） | 2026-06-19 00:46 | DONE | #2341 | | 自動登録 merged:db00260 |
| feature/morimoto/develop-delete-guardrails | （自動登録・要補完） | 2026-06-19 01:02 | DONE | #2350 | | 自動登録 merged:93f0d22 |
| feature/morimoto/qa-smoke-playwright-package | （自動登録・要補完） | 2026-06-19 01:03 | REVIEW | #2351 | | 自動登録 |
| feature/morimoto/develop-guard-workflow | （自動登録・要補完） | 2026-06-19 01:12 | REVIEW | #2353 | | 自動登録 |
| feature/morimoto/paypal-external-api-smoke | PayPal external API smoke ワークフロー復旧 | 2026-06-19 09:43 | DONE | #2349 | | merged:a8a6eca |
| feat/loading-parts | loading / feedback 共用部品追加 | 2026-06-19 15:27 | DONE | #2363 | 2026-06-19 | PR #2363 merged / main deploy #2361 success |
| feature/morimoto/sidebar-auto-collapse-fix | （記入してください） | 2026-06-19 22:56 | DONE | #2372 |  | merged #2372 |
| feature/morimoto/sidebar-hover-suppression | （記入してください） | 2026-06-20 00:08 | DONE | | | |
| feature/morimoto/discord-ticket-immediate-translation-2 | Meta受信の即時二言語翻訳 A2（Messenger/Instagram） | 2026-06-20 00:19 | DONE | #2397 |  | merged #2397 |
| feature/morimoto/advisor-phase1-pr3-customer-contact | （記入してください） | 2026-06-20 02:15 | DONE | | | |
| feature/morimoto/advisor-phase1-pr4-new-goal-advice | （記入してください） | 2026-06-20 03:30 | DONE | | | |
| feature/morimoto/external-api-change-detect-ci | detector/workflow を修正し、PR #2387 で `discord` / `firebase` 検出、PR #2388 で外部 API 変更なし skip を GitHub Actions 実機で確認済み | 2026-06-20 09:11 | REVIEW | #2387 | | codex/prc-external-api-ci, codex/external-api-unrelated-docs-ci |
| release/session-handoff-resume | 色実装立て直しの現在地を引き継ぎ | 2026-07-18 00:00 | DONE | | main | base=origin/main・docs-only |
| feature/morimoto/advisor-phase1-pr5-goal-advisor-ui | 目標設定逆算アドバイザーUIの実装と PR 化 | 2026-06-20 21:13 | DONE | #2390 |  | merged #2390 |
| feature/morimoto/discord-bot-token-6 | （記入してください） | 2026-06-26 07:39 | DONE | | | |
| release/lead-edit-select-only | （記入してください） | 2026-06-26 07:58 | DONE | | | |
| feature/morimoto/select-arrow-padding | （記入してください） | 2026-06-26 10:51 | DONE | | | |
| feature/morimoto/adr-144-discord-b-method | （記入してください） | 2026-06-26 11:05 | IN_PROGRESS | | | |
| feature/morimoto/fedex-guide-step1-7-form | FedEx ETD ガイド Step1-7 新設（CarrierCredentialForm 埋め込み・第2段） | 2026-06-26 | DONE | #2611 |  | merged #2611 |
| release/select-arrow-padding-only | （記入してください） | 2026-06-26 11:46 | DONE | | | |
| release/morimoto/inbox-ui-text-j1-j5 | 送信ガード/翻訳プレビュー UI 微調整（便1 J1-J5）文言+自動生成 | 2026-06-26 | DONE | #2614 | main | merged #2614 |
| feature/morimoto/fix-migration-030000-rename | develop の 030000_add_products_tcg_type_fk を 060000 にリネーム（#2540 CONFLICTING 解消） | 2026-06-26 | DONE | #2613 |  | merged #2613 |
| feature/morimoto/fix-carrier-reset-tenant-ctx | （記入してください） | 2026-06-26 19:22 | DONE | #2621 |  | merged #2621 |
| release/evidence-ben1a | （記入してください） | 2026-07-03 02:38 | DONE | | | |
| release/ledger-cleanup-20260703 | （記入してください） | 2026-07-03 16:55 | DONE | | | merged #2758 |
| codex/inventory-aggregation-preserve | （記入してください） | 2026-06-22 | IN_PROGRESS | | | ⑥清書便で補記 |
| codex/inventory-tabs-ci-cloud | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| codex/process-artifacts-precision-fix-root | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| codex/ssot-message-translations-tenant-id | （記入してください） | 2026-06-22 | DONE | | | ⑥清書便で補記 |
| docs/dev-workflow-spec | （記入してください） | 2026-06-30 | IN_PROGRESS | | | ⑥清書便で補記 |
| docs/product-master-overview-2layer | （記入してください） | 2026-06-30 | DONE | | | ⑥清書便で補記 |
| feature/condition-stage2-base | （記入してください） | 2026-06-23 | DONE | | | ⑥清書便で補記 |
| feature/desk-check-tool | （記入してください） | 2026-06-30 | IN_PROGRESS | | | ⑥清書便で補記 |
| feature/morimoto/advisor-weekly-w1b2 | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| feature/morimoto/analytics-rls-fix | （記入してください） | 2026-06-22 | DONE | | | ⑥清書便で補記 |
| feature/morimoto/discord-config-card-tidy | （記入してください） | 2026-06-28 | IN_PROGRESS | | | ⑥清書便で補記 |
| feature/morimoto/external-api-change-detect-ci2 | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| feature/morimoto/inventory-migration-schema-aware | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| feature/morimoto/inventory-v2-repo-formalize | （記入してください） | 2026-06-24 | DONE | | | ⑥清書便で補記 |
| feature/morimoto/migration-timestamp-dup-guard | （記入してください） | 2026-06-24 | DONE | | | ⑥清書便で補記 |
| feature/morimoto/schedule-token-root-defs | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| feature/morimoto/w2-conversion-by-attribute | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| fix/exporter-port-align-v4 | （記入してください） | 2026-06-29 | DONE | | | ⑥清書便で補記 |
| hotfix/analytics-rls-fix4 | （記入してください） | 2026-06-22 | IN_PROGRESS | | | ⑥清書便で補記 |
| hotfix/fedex-etd-docs-main | （記入してください） | 2026-06-16 | IN_PROGRESS | | | ⑥清書便で補記 |
| hotfix/morimoto/admin-set-tenant-ctx | （記入してください） | 2026-06-30 | IN_PROGRESS | | | ⑥清書便で補記 |
| hotfix/morimoto/fx-rate-null-guard | （記入してください） | 2026-06-29 | IN_PROGRESS | | | ⑥清書便で補記 |
| hotfix/morimoto/paypal-smoke-no-cov-root | （記入してください） | 2026-07-03 | DONE | | | 机は本店内入れ子のため④便で honten-untracked/ へ移動退避・未保存はディレクトリごと保全・ブランチ存続・再開可 |
| hotfix/morimoto/wall2-audit-tenant-ctx | （記入してください） | 2026-06-30 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/branch-guardrail-close | （記入してください） | 2026-07-02 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/doc-heading-duplicates-20260702 | （記入してください） | 2026-07-02 | DONE | | | ⑥清書便で補記 |
| release/fidelity-finish | （記入してください） | 2026-07-02 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/generator-fidelity | （記入してください） | 2026-07-02 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/morimoto/crm-hub-submenu-2662 | （記入してください） | 2026-06-29 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/morimoto/inbox-image-proxy | （記入してください） | 2026-06-29 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/morimoto/manual-record-to-meta-messages | （記入してください） | 2026-06-29 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/morimoto/select-control-bare-select | （記入してください） | 2026-06-28 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/morimoto/ticket-msg-en | （記入してください） | 2026-06-29 | IN_PROGRESS | | | ⑥清書便で補記 |
| release/agent-complete-design-recon | （記入してください） | 2026-07-03 21:54 | DONE | | | |
| release/agent-complete-design-record | （記入してください） | 2026-07-03 22:25 | DONE | | | |
| release/agent-complete-design-design2 | （記入してください） | 2026-07-08 05:58 | DONE | | | |
| release/inventory-theme-split | （記入してください） | 2026-07-04 02:39 | DONE | | | |
| release/sales-anchor-app-theme | （記入してください） | 2026-07-04 03:00 | DONE | | | |
| release/design-system-parent-theme-docs | design-system 親テーマ仕様書一式の新設＋索引登録 | 2026-07-04 03:11 | DONE | #2770 | main | merged: PR #2770 / 06ecc06187696b151f274dae18e770e30a9c999f |
| release/inventory-split-record | （記入してください） | 2026-07-04 03:13 | DONE | | | |
| release/order-management-specs | 受注管理(業務画面)の器作成(3ファイル+索引登録) | 2026-07-04 03:24 | DONE | #2771 | main | merged: PR #2771 / 9a4882e150bd89cdac3c389a61830f6214e89d31 |
| release/lesson-card-preamble | （記入してください） | 2026-07-04 03:25 | DONE | | | |
| release/inbox-theme | 受信箱（inbox）親テーマ一式の新設（5ファイル＋索引1行） | 2026-07-04 03:34 | DONE | #2773 | main | merged: PR #2773 / 1822d21c |
| release/dev-continuity-recon | （記入してください） | 2026-07-04 03:38 | DONE | | | |
| release/executor-checklist | （記入してください） | 2026-07-04 03:45 | DONE | | | |
| release/design-system-recon | design-system recon便（KGI現在値の実測記録） | 2026-07-04 03:57 | DONE | #2777 | main | merged: PR #2777 / 679b669cf0812fdf407e5ca420acb1088e8cd97a |
| release/executor-preamble | （記入してください） | 2026-07-04 03:58 | DONE | | | |
| release/order-management-design | 受注管理(業務画面)design.md+SVG3枚の収納 | 2026-07-04 04:10 | DONE | #2779 | main | merged: PR #2779 / 96fcae90529be713391ed61100ab25ee6203fa96 |
| release/inbox-records-salvage | （記入してください） | 2026-07-04 10:34 | DONE | | | |
| release/design-partner-lesson-20260708 | design-partner.md §6.5 優先順位ルール追記 | 2026-07-08 06:26 | DONE | #2847 | main | merged 2026-07-07 / 台帳残骸を2026-07-19に事後DONE化 |
| release/color-tokens-ssot-recon | （記入してください） | 2026-07-09 02:55 | DONE | | | |
| release/worktree-sync-guard-consolidated | worktree/台帳整合性チェックの再発防止 | 2026-07-14 16:02 | DONE | #2905 | main | merged: PR #2905 / 16bd04eca9466486e04332119e779c4c489405e6 |
| ―（掃き出し便 2026-07-18: 以下61行は未コミット退避分の保全・出所 salesanchor-evacuation/20260718-202133）― | | | | | | |
| release/color-accent-unification | 土台色ネイビーをvar(--accent)に統一（SVG/カレンダー/ロール除く） | 2026-07-14 | CLOSED | #2877 | main | closed by request |
| release/calendar-color-impl | カレンダー色CSS変数化の実装（index.css 定義 / calendars.config.ts var参照化 / cssVar除去） | 2026-07-12 06:40 | IN_PROGRESS | | main | docs/specs/design-tokens-ssot/color/calendar/design.md |
| release/profile-account-settings-theme-v2 | （記入してください） | 2026-07-12 16:03 | DONE | | | |
| release/db-ssot-missing-file-recurrence-prevention | （記入してください） | 2026-07-12 17:05 | DONE | | | |
| release/icon-mono-design | （記入してください） | 2026-07-12 21:46 | DONE | | | |
| release/icon-color-design | （記入してください） | 2026-07-12 23:04 | DONE | | | |
| release/icon-color-impl | （記入してください） | 2026-07-12 23:59 | IN_PROGRESS | | | |
| release/inventory-management-parent-kgi | （記入してください） | 2026-07-13 00:09 | DONE | | | |
| release/design-partner-lesson-20260713 | （記入してください） | 2026-07-13 11:49 | DONE | #2896 | main | merged: PR #2896 / 594efb059fcb0d05d9c6f07688737a509d9ca850 |
| release/db-ssot-classification-master-v2 | （記入してください） | 2026-07-13 11:50 | DONE | | | |
| release/db-ssot-classification-master-table-design | （記入してください） | 2026-07-13 14:10 | DONE | | | |
| release/executor-preamble-index-guard | （記入してください） | 2026-07-13 15:31 | DONE | #2899 | main | merged: PR #2899 / 103d8efb6e56fa95e28dfd897230eff1e469727a |
| release/db-ssot-classification-master-16items | （記入してください） | 2026-07-13 16:20 | DONE | | | |
| release/feed-translation-line-scope | （記入してください） | 2026-07-14 07:44 | DONE | | | |
| release/db-ssot-lead-deal-status-unify | （記入してください） | 2026-07-14 11:50 | DONE | #2902 | main | merged: PR #2902 / 270420f4cbd53f511e21b206bd874bd9edb52888 |
| release/design-def-testlog | docs/specs/design-partner-loop/design-phase-definition.md §11 追記 | 2026-07-14 13:19 | DONE | PR #2903 | a4a48d6c0ef6c00e0f873ed71af024ee14397dfa | |
| release/active-work-fill-blank | worktree/台帳整合性チェックの再発防止 | 2026-07-14 16:30 | DONE | #2906 | main | merged: PR #2906 / 9ca0db6c722c27560810749306c2fb4dce044ba0 |
| release/icon-design-gate-fit | docs/specs/design-tokens-ssot/color/icon/design.md gate要件追記 | 2026-07-14 16:30 | DONE | PR #2907 | ddadf67abb9f4c89ae755b45b5de68b2718fbc09 | |
| release/icon-design-maint-fix | docs/specs/design-tokens-ssot/color/icon/design.md 維持の仕組み欄整備 | 2026-07-14 17:33 | DONE | PR #2908 | f7d56f7dffd88584820d0a8629e3052031992abe | |
| release/db-ssot-step2-note-and-step1-kickoff | （記入してください） | 2026-07-14 17:49 | DONE | | | |
| release/db-ssot-handover-20260714 | （記入してください） | 2026-07-14 21:39 | DONE | | | |
| release/color-tokens-ssot-merge | （記入してください） | 2026-07-14 21:51 | IN_PROGRESS | | | |
| release/feed-translation-tobe-kgi2 | （記入してください） | 2026-07-15 00:44 | DONE | | | |
| release/hex-c3-tokenize | （記入してください） | 2026-07-15 04:36 | DONE | | | |
| release/txn-flow-ben1-design | 便1 design.md 配置（lead起点の親子構造確立） | 2026-07-15 05:25 | DONE | PR #2913 | f8de2bc5d53e5fbd6ffff653e704d42dc7a942cc | merged: PR #2913 / f8de2bc5d53e5fbd6ffff653e704d42dc7a942cc |
| release/color-token-dedup | （記入してください） | 2026-07-15 06:29 | IN_PROGRESS | | | |
| release/txn-flow-ben1-design-amend | 便1 design.md 追記（§4-4 ON DELETE確定＋§11 ソフトデリート予約） | 2026-07-15 09:38 | DONE | PR #2915 | 55ded567af588ea45cc3493db76341a609547a7c | merged: PR #2915 / 55ded567af588ea45cc3493db76341a609547a7c |
| release/inventory-analytics-tobe-kgi | （記入してください） | 2026-07-15 09:44 | DONE | | | |
| release/txn-flow-ben1-convlog-fk | （記入してください） | 2026-07-15 15:29 | DONE | | | |
| release/management-center-theme | （記入してください） | 2026-07-15 15:30 | DONE | | | |
| release/inbox-invoice-form-send-spec | （記入してください） | 2026-07-15 15:39 | DONE | | | |
| release/color-dup2-alias | （記入してください） | 2026-07-15 15:39 | IN_PROGRESS | | | |
| release/color-ssot-evidence | 色トークン SSOT 完成エビデンス（基準SHA: 36de75ea） | 2026-07-15 16:41 | DONE | #2921 | 6d614858 | merged: PR #2921 / 6d61485815e291279bd09913da9c7931986bb6b9 |
| release/txn-flow-ben1-reserve3 | （記入してください） | 2026-07-15 16:42 | DONE | | | |
| release/management-center-role-theme | （記入してください） | 2026-07-15 16:52 | DONE | | | |
| release/inbox-invoice-form-send-design | （記入してください） | 2026-07-15 17:05 | DONE | | | |
| release/management-center-shift-theme | （記入してください） | 2026-07-15 22:45 | DONE | | | |
| release/guard-tsx-style-color | （記入してください） | 2026-07-15 22:46 | IN_PROGRESS | | | |
| release/evidence-2924-guard-gap | （記入してください） | 2026-07-15 23:44 | DONE | | | |
| release/color-evidence-update | （記入してください） | 2026-07-16 00:03 | DONE | | | |
| release/evidence-2924-repro-2927 | （記入してください） | 2026-07-16 04:02 | DONE | | | |
| release/management-center-report-theme | （記入してください） | 2026-07-16 04:07 | DONE | | | |
| release/design-partner-s6-guard-lesson | （記入してください） | 2026-07-16 04:34 | DONE | | | |
| release/component-ssot-plan | UI部品の金型化 全体計画書 | 2026-07-16 23:10 | DONE | #2930 | main | merged: PR #2930 / a5ce9b79 |
| release/session-handoff | （記入してください） | 2026-07-16 23:39 | DONE | | | |
| release/session-handoff-v2 | （記入してください） | 2026-07-17 00:05 | DONE | | | |
| release/management-center-compensation-theme | （記入してください） | 2026-07-17 07:09 | DONE | | | |
| release/dp-sec6-gate-lessons | design-partner.md §6 関所教訓5行追記 | 2026-07-18 20:12 | DONE | #2952 | main | merged: PR #2952 / 8aa93fac9ba937ca3378a7aa4488673b1f777150 |
| release/session-handoff-refresh | （記入してください） | 2026-07-18 12:17 | DONE | | | |
| release/claude-md-size-fix | （記入してください） | 2026-07-18 13:51 | DONE | | | |
| release/ledger-guard-ben3-1 | （記入してください） | 2026-07-18 14:29 | DONE | | | |
| release/management-center-invoice-info-theme | （記入してください） | 2026-07-18 14:48 | DONE | | | |
| release/page-title-d1 | ページタイトル金型 D1 追記（recon証跡・相互参照） | 2026-07-18 14:53 | DONE | #2941 | main | merged: PR #2941 / 0cfba1a2 |
| release/ledger-done-2942 | （記入してください） | 2026-07-18 16:00 | DONE | | | |
| release/infra-exporters-persist | exporters/promtail デプロイ導線恒久化（node-exporter/promtail 起動 + heavy-exporters profiles） | 2026-07-18 16:16 | DONE | #2945 | main | merged: PR #2945 / 21c400ef |
| release/strict-test-red | （記入してください） | 2026-07-18 16:45 | DONE | | | |
| release/strict-test-green | （記入してください） | 2026-07-18 16:48 | DONE | | | |
| release/cleanup-strict-test-branches | （記入してください） | 2026-07-18 16:52 | DONE | | | |
| release/ledger-done-2948 | （記入してください） | 2026-07-18 17:15 | DONE | | | |
| release/page-title-d2a | merged: PR #2950 / 73150e7f5733641ec1c13a00fdd6af413edd0df5 | 2026-07-18 17:22 | DONE | #2950 | main | merged: PR #2950 / 73150e7f5733641ec1c13a00fdd6af413edd0df5 |
| release/ledger-guard-ben3-2 | （記入してください） | 2026-07-18 19:54 | DONE | | | |
| release/rls-bootstrap-txn-fix | rls_bootstrap を同一トランザクション化 + 再発防止テスト | 2026-07-19 00:00 | DONE | #2966 | main | merged: PR #2966 / ad918b2dde8b336c71dd0c5a9b66499e04cb7815 |
| release/ledger-done-2966 | rls-bootstrap-fix の台帳DONE化 | 2026-07-19 | DONE | #2972 | main | 台帳DONE便自身の登録 |
| release/ledger-done-2976 | process-hardening の台帳DONE化 | 2026-07-19 | DONE | #2976 | main | 台帳DONE便自身の登録 |
| release/ledger-done-2988 | deal-removal stage2 の台帳DONE化 | 2026-07-20 | DONE | #2988 | main | 台帳DONE便自身の登録 |
| release/process-hardening-ideal | process-hardening のあるべき姿起票 | 2026-07-19 | DONE | #2976 | main | merged: PR #2976 / 697782d0fed9118ac2014e92bab48f3b151750fb |

---

## 記入例

```
| feature/morimoto/your-feature-name | 受信箱 UI    | 2026-05-26 10:00 | <状態> |     | | タブ1で作業中 |
| feature/morimoto/your-other-feature | スケジュール  | 2026-05-26 11:30 | REVIEW      | 923 | | タブ2で作業中 |
```

## 状態の種類

| 状態 | 意味 |
|------|------|
| `IN_PROGRESS` | 現在作業中（Generator が動いている） |
| `REVIEW` | PR 提出済み・Reviewer/Evaluator 待ち |
| `BLOCKED` | 問題があり停止中（しんごさん確認待ち） |
| `DONE` | PR マージ完了（ログとして永続保持） |
| feature/morimoto/adr-129-backlog-notes | ADR-129 未対応バックログ記録 | 2026-06-11 | DONE | #1921 |  | merged #1921 |
| feature/morimoto/role-badge-color | オーナーロール色 赤→インディゴ（全テナント冪等マイグレーション） | 2026-06-11 | DONE | #1920 |  | merged #1920 |
| docs/morimoto/sa-foundation-recon-audit | SA土台バッチ全体監査レポート（ADR-131/132 実装・監査文書クローズ） | 2026-06-10 | DONE | #1900 |  | merged #1900 |
| feature/morimoto/adr126-error-handling | ADR-126 公開フォームエラーハンドリング（409 already_registered + i18n） | 2026-06-11 | DONE | #1918 |  | merged #1918 |
| feature/morimoto/main-deploy-stamp | main デプロイ成功スタンプ（ADR-116） | 2026-06-07 | DONE | #1712 |  | merged #1712 |
| feature/morimoto/ui-consistency-a | 集計枠 fieldset → Card 統一（SalesPage + CommissionsPage） | 2026-06-10 | DONE | #1919 | | |
| feature/morimoto/datatable-p2-pilot | DataTable標準化フェーズ2 Pilot（SupplierParseStatsTab） | 2026-06-10 | DONE | #1915 | | |
| feature/morimoto/fedex-ship-stage2 | ADR-128 FedEx ラベル発行・集荷予約 Stage 2 実装 | 2026-06-11 | DONE | #1944 |  | merged #1944 |
| feature/morimoto/back-merge-main-for-adr128 | main → develop バックマージ（SA-02 Stage 3 migration 取り込み） | 2026-06-11 | DONE | | | |
| feature/morimoto/fix-develop-migration-order | develop migration 順序修正（SA-02 Stage 3 追加） | 2026-06-11 | DONE | #1954 |  | merged #1954 |
| feature/morimoto/sync-main-to-develop-3 | main → develop フルマージ（SA-02 Stage 3 コード取り込み） | 2026-06-11 | DONE | #1957 |  | merged #1957 |
| feature/morimoto/release-fix | develop → main リリース競合解消（run_all_migrations.sh ADR-128挿入） | 2026-06-11 | DONE | #1958 |  | merged #1958 |
| feature/morimoto/nginx-resolver-adr133 | ADR-133 nginx resolver+proxy_pass変数化 IP固着502恒久解 | 2026-06-11 | DONE | #1970 |  | merged #1970 |
| feature/morimoto/karte-visual-gate | カルテ見た目忠実度ゲート⑤（Phase 5a CSS 寸法是正 + 5b 視覚ゲート） | 2026-06-11 | DONE | #1971 |  | merged #1971 |
| feature/morimoto/fedex-label-validation-wizard | ADR-129 FedEx Label Validation 申請支援ウィザード | 2026-06-12 | DONE | #1993 |  | merged #1993 |
| feature/morimoto/design-site-smoke-autoblock | smoke④ FAIL 時 /design/ 自動遮断（ADR-134 D） | 2026-06-12 | DONE | #2035 |  | merged #2035 |
| feature/morimoto/back-merge-main-for-2032 | main → develop バックマージ（hotfix f2a33605 取り込み・PR #2032 競合解消） | 2026-06-12 | DONE | | | |
| feature/morimoto/adr-135-final-checkboxes | ADR-135 受け入れ条件チェックボックス更新 + 経緯記録 | 2026-06-12 | DONE | #2033 |  | merged #2033 |
| feature/morimoto/adr-135-cleanup-approvers | ADR-135 AUTHORIZED_APPROVERS/AUTHORS 一時追加削除 | 2026-06-12 | DONE | #2034 |  | merged #2034 |
| feature/morimoto/migration-full-dryrun-ci | migration-test.yml 全件ドライランジョブ追加（ADR-135強化） | 2026-06-12 | DONE | #2051 | | |
| feature/morimoto/release-pr-migration-manifest | auto-release-pr.yml migration manifest バナー自動記載 | 2026-06-12 | DONE | #2052 | | |
| feature/morimoto/adr-137-company-stats-ssot | ADR-137 起案 + migration ヘッダ修正（取引額SSOT） | 2026-06-12 | DONE | #2049 | | |
| feature/morimoto/design-301-redirect | nginx /design 301リダイレクト + smoke⑤ | 2026-06-12 | DONE | #2050 | | |
| feature/morimoto/responsive-ux-pr-r1 | レスポンシブ基盤最適化 PR-R1（mobile menu button / 767px 統一） | 2026-06-14 | MERGED | #2156 | | |
| feature/morimoto/hotfix-css-mediaq-safari | Vite 8 cssTarget hotfix — Safari Level 4 media query 非対応バグ修正 | 2026-06-15 | DONE | #2198 |  | merged #2198 |
| feature/morimoto/mobile-shell-pr-r2a | mobile-shell PR-R2-A: NavItemList.tsx + useIsMobile.ts + unit tests | 2026-06-15 | DONE | #2223 |  | merged #2223 |
| docs/morimoto/mobile-shell-pr-r2b-handoff | mobile-shell PR-R2-B 実装ハンドオフ（recon + design docs-only） | 2026-06-15 | DONE | | | |
| feature/morimoto/tenant-deletion-clean | テナント論理削除・物理削除 API | 2026-06-14 | DONE | #2149 | 2026-06-14 | PR #2159 release にて main 反映済み。物理削除APIは未実行・個別PO GO待ち |
| feature/morimoto/tenant-deletion-cache-fix | 論理削除・物理削除後の Redis tenant cache 無効化 | 2026-06-14 | DONE | #2154 | 2026-06-14 | PR #2159 release にて main 反映済み |
| release/develop-to-main-2159 | develop → main release（tenant deletion / ADR-108 B-1 / Discord Auto Setup） | 2026-06-14 | DONE | #2159 | 2026-06-14 | Deploy to VPS run 27486632360 success / migration success |
| docs/morimoto/fedex-etd-stamp-recon | FedEx ETD / Stampステップ失敗原因 recon（docs-only） | 2026-06-15 | DONE | #2234 |  | merged #2234 |
| hotfix/morimoto/reaper-fallback-main | reaper .worktree-id fallback を main に cherry-pick（ADR-114 STEP 0） | 2026-06-18 | DONE | #2334 | main | merged #2334 |
| feature/morimoto/worktree-adr114-pr-c1 | ADR-114 PR-C1: flock追加・起動時reaper plist・docs/ADR更新 | 2026-06-18 | DONE | #2336 |  | merged #2336 |
| feature/morimoto/schedule-8issues-fix | スケジュールページ 8件本番バグ修正 | 2026-06-21 | DONE | #2411 | | merged |
| feature/morimoto/schedule-fix2 | スケジュール #4 calendarLabels i18n追加 / #8 catch setEvents([]) 追加 | 2026-06-21 | DONE | #2413 |  | merged #2413 |
| feature/morimoto/analytics-rls-fix3 | analytics conversion-by-attribute RLS tenant context fix | 2026-06-22 | DONE | | | `test_analytics_conversion_by_attribute_rls.py` の app.tenant_id を set_config で実 tenant に合わせる |
| hotfix/morimoto/page-header-revert-clean | 全PageLayoutページ ヘッダー白帯・1段下ズレ修正（#2432 リグレッション） | 2026-06-23 | DONE | #2486 | main | merged #2486 |
| docs/morimoto/ev-2538-tcg-fk | PR #2538 tcg_type FK 動作確認を evidence-registry に記録（EV-20260624-001） | 2026-06-24 | DONE | #2576 |  | merged #2576 |
| feature/morimoto/products-rls-stage2-force-rls | public.products FORCE-RLS 段階2: FORCE+4ポリシー migration（ADR-145） | 2026-06-26 | DONE | #2616 | develop | merged #2616 |
| release/send-guard-phase-a-main | 送信ガード Phase A（ADR-143: かな検出+スレッド言語トグル+確認ダイアログ）main単独便 | 2026-06-24 | DONE | #2566 |  | merged #2566 |
| release/send-guard-phase-b | 送信ガード Phase B（ADR-143: 多数決自動判定 API + useInboxState 自動注入）main単独便 | 2026-06-24 | DONE | #2579 | main | merged #2579 |
| release/etd-guide-nav-center | ETD ガイド 左ナビ項目ラベル中央揃え リリース | 2026-06-24 | DONE | #2582 | main | merged #2582 |
| release/morimoto/discord-oauth-rls-fix | Discord OAuth callback 監査ログ RLS バグ修正（set_tenant_context 追加・ADR-091）main 単独便 | 2026-06-25 | DONE | #2585 | main | merged #2585 |
| feature/morimoto/migrate-lead-edit-select | LeadEditPage 生select 7個→Select コンポーネント移行（ADR-073） | 2026-06-26 | DONE | #2599 |  | merged #2599 |
| feature/morimoto/products-rls-stage1-operator-context | public.products FORCE-RLS 段階1: 書き込み経路 operator context 付与（ADR-145） | 2026-06-26 | DONE | #2602 | develop | |
| feature/morimoto/common-6roles-stage-a | 共通6ロール化 段階A — DEFAULT_ROLES 6ロール化・migrate スクリプト | 2026-06-26 | DONE | #2619 |  | merged #2619 |
| release/morimoto/i18n-missing-keys-fill | i18n 欠落64キー追加（badges/buddy/goals/leads）翻訳2ファイルのみ | 2026-06-26 | DONE | #2622 | main | main マージ済み・本番デプロイ済み |
| feature/morimoto/resolve-back-merge-2463 | PR #2463 back-merge 手動解消（main→develop コンフリクト9ファイル）PR #2624 | 2026-06-26 | DONE | #2624 |  | merged #2624 |
| docs/product-master-spec-v2 | 商品マスタ あるべき姿 設計書（docs-only）develop起点 v2 | 2026-06-30 | DONE | #2695 |  | merged #2695 |
| release/morimoto/fx-rate-ssot-wt | 為替レート SSOT 実装（自動取得 Celery Beat・super-admin UI） | 2026-06-28 | DONE | | main | migration + Celery task + API + frontend |
| feature/morimoto/wall0-ddl-commit | 壁0+壁2: create_tenant_schema DDL commit + set_config app.tenant_id | 2026-06-29 | DONE | #2690 | develop | PR #2690 クローズ・不採用 |
| release/lessons-guard-enforce | lessons-guard.yml/design.md予約 | 2026-07-21 | DONE | | main | |
| release/server-resource-lessons | lessons.d新設・handoff新設予約 | 2026-07-21 | DONE | | main | |
| release/rls-bootstrap-public-lock | rls_bootstrap 共有部分をグローバルlockで直列化 | 2026-07-21 | DONE | #3024 | main | merged: PR #3024 / 321ab36ca4f6977a7f34af0510f1477af79c8121 |
| release/deal-removal-stage2-r-leadid | deal-removal stage2-R: deal_close_reasons/quotes lead_id参照化 | 2026-07-21 | DONE | #3018 | main | merged: PR #3018 / 0cbd18fb12299680c82eb66198fb37f88e68d507 |
| release/lessons-sec6-dedup | design-partner.md清書予約 | 2026-07-22 | IN_PROGRESS | | main | |
| release/server-resource-final-wrapup | handoff追記予約 | 2026-07-22 | IN_PROGRESS | | main | |
| release/lessons-guard-allpr | lessons-guard.yml/design.md予約 | 2026-07-22 | IN_PROGRESS | | main | |
| release/lessons-guard-scope | lessons-guard.yml/scripts予約 | 2026-07-23 | IN_PROGRESS | | main | |
| release/wall-complete-record | handoff追記予約 | 2026-07-22 | IN_PROGRESS | | main | |
| release/ledger-done-3052 | PR #3052 analytics 修正の台帳DONE化 | 2026-07-22 | DONE | #3052 | main | merged #3052 |
| release/loss-reasons-to-leads | 失注理由の登録をリード側へ移設（recon/design docs） | 2026-07-23 | DONE | #3061 | main | merged: PR #3061 / 0a62655c5efca9ed81892b1a60b7e751b3e28b44 |
| release/loss-reasons-to-leads-ledger-done | release/loss-reasons-to-leads の台帳DONE化 | 2026-07-23 | DONE | #3061 | main | merged: PR #3061 / 0a62655c5efca9ed81892b1a60b7e751b3e28b44 |
| release/session-final-handoff | handoff追記予約 | 2026-07-23 | IN_PROGRESS | | main | |
| release/deal-removal-create-deal | orders.deal_id コード側除去（reservation: dr-orders-dealid） | 2026-07-24 | DONE | #3073 | main | merged: PR #3073 / 6f7242cb72b8241135a8f80e1b81ce18ccc2bae0 |
| release/deal-removal-quotes-dealid | quotes.deal_id コード側除去（reservation: dr-quotes-dealid） | 2026-07-24 | DONE | #3084 | main | merged: PR #3084 / 3c08e50271e1183ae1f61f1797723eb75b9b0fcf |
| release/ledger-orders-dealid-done | PR #3073 マージに伴う台帳DONE記録 | 2026-07-24 | IN_PROGRESS | | main | |
| release/orders-drop-dealid | orders.deal_id 列とFKの削除migration | 2026-07-24 | DONE | #3078 | main | merged: PR #3078 / fa6997cc2f8b535a3c00b00f9bec501eabe8c512 |
| release/ledger-orders-drop-dealid-done | PR #3078 マージに伴う台帳DONE記録 | 2026-07-24 | IN_PROGRESS | | main | |
| release/quotes-drop-dealid | quotes.deal_id 列とFKの本番削除（GO・検算） | 2026-07-24 | DONE | #3088 | main | merged: PR #3088 / ded5e94b78c0f3e25d52d1f1f076f224c3df77aa |
| release/dp-sec0-standard | design-partner.md §0 標準設定追記 | 2026-07-24 | IN_PROGRESS |  | main | 正本先約 design-partner.md / GO=未採番 / 単独便 |
