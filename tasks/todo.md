# Tasks

タスク台帳の正本。セッション開始時に必ず読むこと（`AGENTS.md §引き継ぎルール` 参照）。

---

## 進行中

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|---------|-----|------|
| Android LINE専用API・Termux送信 | Codex | PR #3445本番deploy34676818835成功。端末登録・2件受付済み、各39名確認待ち。配信接続CLI実装中 | 管理接続CI・PR番号GO後に本番inspect。未登録名と配信先を確定し解析・配信を検証 | PR #3445 / Issue #3437 / docs/handoff/line-import-delivery/recon.md | 2026-09-12 |
| 商品マスタの発売日順・作品タブ（実装） | Agent | ローカル実装12e6b13c、画面単体14件/E2E5件成功。PO原文GO#3433受領、最新main追従済み | PR #3433へ公開、実PG skip0・CI確認後にマージ/配備。tenant_001実接続と人の確認は未実施 | docs/handoff/tcg-product-import/recon.md 同日GO追補 / EV-20260911-PRODUCT-DATE-TABS / PR #3433 | 2026-09-11 |
| フロントエンド金型化・再測定 | Agent | PR3432マージ済み。AI共通footer2製品の実装・検収済み、PR #3435提出（560比較/輪郭448/統合unit200）、AH16移管案は退避して保留 | PO原文GO #3435受領済み。最新CI確認後にマージ。AHは最新mainで再開、新CIは最後。PO目視未実施 | docs/specs/design-system/design.md §AI / docs/handoff/design-system-recon/evidence-20260910/modal-footer-implementation.md | 2026-09-11 |
| PMG解析実行記録（後続設計） | 設計担当 | PR #3396文書マージ確認済み。製品設計REVISE。隔離試験PR #3408のDocker99件成功、ページ接続PR #3416は本番反映済み | PR #3408マージ/自動deploy成功確認済み。入口配布・旧処理照合の具体手段を確定して設計再審査 | docs/handoff/pmg-import-delivery-ssot/design.md 最終確認節 / EV-20260910-PMG-ANALYSIS-RUN / PR #3396 | 2026-09-10 |
| 商品取り込みのスキーマ修飾検査（依頼6） | 実装担当 | PR #3397マージ済み（a0c0eb7f）。実PGを含む2436成功・93スキップ、必須12件成功 | 依頼4の評価ゲートを別PRで設置・検証する | backend/tests/test_tcg_schema_qualification.py / EV-20260910-TCG-SCHEMA-IMPL | 2026-09-10 |
| worktree作成時の既存保持指定（設計） | Agent | PR #3390にPO GO受領。文書4件のみ、mainの別テーマ追記を保持して競合解消。実装未着手 | 最新HEADのCI確認後に文書PRをマージ。最終状態はPR #3390参照。実装担当の作業場所と正式カードは別途 | docs/handoff/branch-operations/design.md 同日節 / EV-20260910-WORKTREE-PRESERVE | 2026-09-10 |
| LINE解析精度・正常完了の誤商品調査 | Agent | #3403マージ/本番反映、有効1件18明細/18解析完了。未完了0。3接続退避済み、445行配信予定。新たに状態/備考2件の問題を確認、配信未実施 | POがCase維持/NOTE_JA記載を確定。設計§13限定2件修正を実装・実DB再解析試験、反映後3シート配信と照合 | recon.md「#3403復旧後の抽出完了と配信前確認」 / EV-20260910-LINE-ACCURACY-08 / PR #3403 / Deploy34456746721 | 2026-09-10 |
| Sales Anchor アプリ全体（親）起票 | Agent | `release/sales-anchor-app-theme` worktree で `docs/specs/sales-anchor-app/README.md` / `ideal-state.md` / `kgi.md` を最新 origin/main から新設し、`docs/specs/README.md` に 1 行追記した | PR #2768 マージ済み・KGI承認済（PR起票中）。次は子テーマの着手順序決め | `docs/specs/sales-anchor-app/README.md` / `docs/specs/sales-anchor-app/ideal-state.md` / `docs/specs/sales-anchor-app/kgi.md` / `docs/specs/README.md` | 2026-07-04 |
| LINE改善の期限付きGO委任（GOフロー子テーマ） | 設計担当 | PR #3406にPO原文GO #3406を記録。未保存の9月10日委任受領記録を統合し、文書書式を補正。委任経路は未有効、方式はREVISE | 最新HEADのCI確認後、承認済み文書PRをマージ。方式の再審査・実装・有効化は別工程 | docs/handoff/go-record-transcription/line-delegation.md / EV-20260910-LINE-GO-DELEGATION / PR #3406 | 2026-09-12 |
| GOフロー統一（既存GO転記テーマの延長） | 設計担当 | PR #3418は草案保存としてPOが追従・マージ指示。全体REVISEを維持。L1 #3404本番反映完了 | 文書PRのマージをAPI確認。P1は承認後のbranch作成403で停止、接続権限解消後に同じカード手順3から再開 | PR #3418、EV-20260911-GO-3418-DOC-MERGE、TH-GO-INTAKE-P1-PR-RESULT.json | 2026-09-11 |
| 文書体系（ナレッジベース）起票 | Agent | `release/doc-estate-theme` worktree で `docs/specs/doc-estate/README.md` / `ideal-state.md` / `kgi.md` を origin/main b4a1ced から新規作成し、`docs/specs/README.md` に 1 行追記済み | `git diff --numstat` と `bash scripts/check-doc-heading-duplicates.sh` で検算し、PR 本文の検算欄へ転記する | `docs/specs/doc-estate/README.md` / `docs/specs/doc-estate/ideal-state.md` / `docs/specs/doc-estate/kgi.md` / `docs/specs/README.md` | 2026-07-03 |
| Chromatic 完全撤去 | Agent | npm依存・プラグイン・コメント除去済み（PR #chromatic-full-removal）。完了定義: `git grep -i chromatic -- ':!docs/' 0件 + ビルド成功` | PR GO待ち | `docs/handoff/chromatic-full-removal/` | 2026-06-24 |
| Foundation F1 国台帳 `public.countries` 新設 | Agent | `backend/app/routers/countries.py` / `backend/app/schemas/countries.py` / `backend/tests/test_countries_master.py` を追加し、`frontend/src/constants/countries.ts` を seed source とする migration `20260621_010000_create_countries_master.sql` を生成済み。SQLite 互換の `public.countries` rewrite も `backend/tests/conftest.py` に追加した | lint/test を回し、必要なら migration / docs / line ref を微調整して PR 化へ進める | `backend/app/routers/countries.py` / `backend/app/schemas/countries.py` / `backend/tests/test_countries_master.py` / `backend/tests/conftest.py` / `migrations/20260621_010000_create_countries_master.sql` / `docs/handoff/foundation-f1-countries-master/recon.md` / `docs/handoff/foundation-f1-countries-master/design.md` | 2026-06-21 |
| Foundation F3 流入元の統制 | Agent | `backend/app/services/channel_masters.py` / `backend/app/routers/leads.py` / `backend/app/routers/conv_logs.py` / `backend/app/services/tenant.py` / `backend/tests/test_channel_type_control.py` / `frontend/src/components/ChannelTypeCombobox.tsx` / `frontend/src/pages/leads/LeadEditPage.tsx` / `frontend/src/pages/leads/LeadsPage.tsx` / `frontend/tests-e2e/lead-channel-control.spec.ts` を追加・更新中 | pytest / Playwright / lint を回し、backfill report を確認して PR 化へ進める | `backend/app/services/channel_masters.py` / `backend/app/routers/leads.py` / `backend/app/routers/conv_logs.py` / `backend/app/services/tenant.py` / `backend/tests/conftest.py` / `backend/tests/test_channel_type_control.py` / `frontend/src/components/ChannelTypeCombobox.tsx` / `frontend/src/pages/leads/LeadEditPage.tsx` / `frontend/src/pages/leads/LeadsPage.tsx` / `frontend/tests-e2e/lead-channel-control.spec.ts` / `scripts/migrate_20260621_030000_backfill_lead_channel_type.py` / `docs/handoff/foundation-f3-channel-control/recon.md` / `docs/handoff/foundation-f3-channel-control/design.md` | 2026-06-21 |
| PR-E 人の確認/承認の必須化（process-artifacts gate 拡張） | Agent | `scripts/check-process-artifacts.js` に user-impacting change の Shingo GO 必須化を追加し、対象に `backend/app/auth/` / `backend/app/tasks/` / `backend/app/discord_gateway/` と **PR-C の外部API検出で見つかる変更**も含めるよう修正。`node scripts/tests/test-process-artifacts.js` で 72 PASS / 0 FAIL を確認し、feature/morimoto/pr-e-human-go-gate を更新 push 済み | Shingo GO を受領後、PR 本文へ `### GO記録` を反映し、CI 実機確認を経て merge 可否を判断する | `scripts/check-process-artifacts.js` / `scripts/tests/test-process-artifacts.js` / `docs/STANDARD-WORKFLOW.md` / `docs/handoff/incident-paypal-invoicing-false-complete/design.md` / PR #2410 | 2026-06-21 |
| PR-F 本番デプロイ安全化の決定記録（事前リハーサルはローンチ後） | Agent | `deploy.yml` に Pre-deploy DB backup / backend health check / auto-rollback / blue-green が既に実装済みで、PR-F の deploy 後 health + auto-rollback は既達と整理した。残件の事前リハーサルは staging 前提のバックログに分離した | ステージング環境構築後に PR-F の事前リハーサルと外部 health の auto-rollback 連動可否を再設計する | `docs/handoff/incident-paypal-invoicing-false-complete/design.md` / `docs/adr/ADR-1000-external-api-smoke-mandatory.md` / `.github/workflows/deploy.yml` / `.github/workflows/qa-smoke.yml` / `tests/qa-smoke/utils/db-assert.ts` | 2026-06-21 |
| Select 本体分離 + InvoicesPage パイロット | Agent | `frontend/src/components/Select.tsx` で `SelectControl` を分離し、`frontend/src/pages/invoices/InvoicesPage.tsx` の filter-bar 1か所だけを新本体へ差し替えた。既存フォーム用 `Select` は wrapper のまま維持 | Storybook / build / lint / stylelint の結果と前後スクショを整理して報告する | `frontend/src/components/Select.tsx` / `frontend/src/components/FormField.css` / `frontend/src/components/Select.stories.tsx` / `frontend/src/pages/invoices/InvoicesPage.tsx` / `/tmp/select-body-before.png` / `/tmp/select-body-after.png` / `/tmp/select-story-labeled.png` / `/tmp/select-story-bare.png` | 2026-06-28 |
| QA Smoke Suite #2346 psql 経路自己探索化 | 追跡 issue #2422 で Layer A を分離中 | `scripts/qa/reset-tenant.sh` を backend postgres コンテナ `astro-webapp-postgres-1` へ寄せる修正を入れ、`tests/qa-smoke/utils/db-assert.ts` と同じ実 DB への docker exec 経路に揃えた。Layer B は `tests/qa-smoke/utils/db-assert.ts` に `app.tenant_id=6` / `search_path=tenant_006,public` を付与して tenant RLS を backend と同文脈に揃えた。scene-05/06/08/09 は `test.skip` で #2346 を着地させ、認証ユーザー解決/データ可視性の根因を issue #2422 で追跡する | 再 smoke を流して backend 実 DB に `qa-admin` が入るかと `gh pr checks 2346` の failed=0 を確認し、merge 可否を判断する。Layer A は issue #2422 で別途修正 | `.github/workflows/qa-smoke.yml` / `scripts/qa/reset-tenant.sh` / `tests/qa-smoke/utils/db-assert.ts` / `tests/qa-smoke/utils/real-backend.ts` / `backend/app/auth/dependencies.py` / `backend/app/routers/staff.py` / `gh issue 2422` | 2026-06-21 |
| Advisor Phase 1 PR-5 W-1c フォロー追加 UI | Agent | `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx` に [フォロー追加] インライン composer を追加し、`/analytics/weekly-advisor-defensive` の `lead_id` から `PATCH /leads/{id}` まで繋ぐ実装を進めた。backend は `lead_id` 追加済み、`npm run build` と backend の `weekly_advisor_defensive` pytest は green。Playwright は mac の Chromium bootstrap 制約でローカル実行不可 | `scene1-dashboard.spec.ts` の追加 E2E は CI で確認し、required checks が緑なら PR 化して merge へ進める | `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx` / `frontend/src/pages/dashboard/WeeklyAdvisorSection.css` / `frontend/src/api/funnel.ts` / `backend/app/routers/analytics.py` / `backend/tests/test_analytics.py` / `frontend/tests-e2e/scene1-dashboard.spec.ts` | 2026-06-21 |
| W-2① PR-3 フロント（優先見込み客を「今やること」に表示） | Agent | `frontend/src/pages/dashboard/DashboardPage.tsx` に `PriorityProspectsSection` を追加し、`frontend/src/pages/dashboard/PriorityProspectsSection.tsx` / `frontend/src/api/funnel.ts` / `frontend/src/mocks/funnelFixtures.ts` / `frontend/tests-e2e/scene1-dashboard.spec.ts` / `frontend/src/pages/dashboard/DashboardPage.stories.tsx` / `docs/handoff/w2-pr3-frontend/*` を更新済み。scene1-dashboard Playwright 6/6 green、`npm run build` green | process-artifacts の最終確認を添えて PR 化へ進める | `frontend/src/pages/dashboard/DashboardPage.tsx` / `frontend/src/pages/dashboard/PriorityProspectsSection.tsx` / `frontend/src/api/funnel.ts` / `frontend/src/mocks/funnelFixtures.ts` / `frontend/tests-e2e/scene1-dashboard.spec.ts` / `frontend/src/pages/dashboard/DashboardPage.stories.tsx` / `docs/handoff/w2-pr3-frontend/recon.md` / `docs/handoff/w2-pr3-frontend/design.md` / `E2E_NO_WEBSERVER=1 npx playwright test tests-e2e/scene1-dashboard.spec.ts --project chromium --workers=1 --reporter=line` / `npm run build` | 2026-06-22 |
| Schedule Google Calendar UI follow-up | Agent | `frontend/src/pages/schedule/SchedulePage.tsx` の他メンバー表示トグルを `onClick` で確実に更新し、`frontend/src/pages/schedule/ScheduleSettingsPage.tsx` / `frontend/src/pages/schedule.css` の余白を正本寄せで調整済み。`backend/app/routers/calendar.py` の他担当予定取得ガードは `staff.view` のまま確認した | 実機で `/schedule` と `/schedule/settings` を開き、レビューアカウントのチェック切替と 2 カラム/タイトル余白をスクリーンショットで突合する | `frontend/src/pages/schedule/SchedulePage.tsx` / `frontend/src/pages/schedule/ScheduleSettingsPage.tsx` / `frontend/src/pages/schedule.css` / `backend/app/routers/calendar.py` / `backend/tests/test_calendar_events_rbac.py` / `docs/ai-agents/evidence-registry.md` | 2026-06-22 |
| Supply Chain PR-1/2/3 condition正典地盤 | Agent | `backend/app/services/condition_vocab.py` を新設し、parser / LLM parser / ParseReviewPage / ja.json / en.json を正典マスタに寄せた。`scripts/check-condition-vocab.js` と `.github/workflows/condition-vocab-check.yml` を追加し、temp copy での意図的違反で CI 赤、実体で CI 緑を確認した。`recon_ro` は prod1 側で後始末済み、`migrations/20260622_020000_add_inventory_raw_condition.sql` と `scripts/run_all_migrations.sh` への登録で raw_condition の段階1 migration も runner に載せた | design / recon / migration runner / gate / tests の証跡を揃えたので、段階1 ハンドオフに進める。危険変更は本番 GO 待ちとして維持する | `backend/app/services/condition_vocab.py` / `backend/app/services/inventory_parser.py:107-108,223-237,511-518,577-672,1097-1111` / `backend/app/services/inventory_parser_llm.py:64-81,102-125,159-180,299-317` / `frontend/src/pages/super-admin/ParseReviewPage.tsx:125-131,585-602` / `frontend/src/locales/ja.json:2233-2243` / `frontend/src/locales/en.json:2233-2243` / `scripts/check-condition-vocab.js:8-116` / `.github/workflows/condition-vocab-check.yml:1-21` / `migrations/20260622_020000_add_inventory_raw_condition.sql:1-6` / `scripts/run_all_migrations.sh:165-173` / `pytest -q --no-cov backend/tests/test_inventory_parser_rule.py backend/tests/test_inventory_parser_llm.py` / `node scripts/check-condition-vocab.js` | 2026-06-22 |
| Schedule Google Calendar UI PR2 カレンダー本体 | Agent | `frontend/src/pages/schedule/SchedulePage.tsx` をベースに、左パネルをカテゴリ→担当者へ切り替え、`/schedule/settings` を担当者管理画面へ拡張し、`staff.view` を manager gate にした担当者ベース表示を接続中。backend は owner roster API / owner settings migration まで実装し、backend 45 passed / frontend build green を確認済み。PR #2442 を develop、release PR #2443 を main へ反映済み | 完了 | `backend/app/routers/calendar.py` / `backend/app/services/calendar_service.py` / `backend/tests/test_calendar_owner_api.py` / `backend/tests/test_calendar_service.py` / `frontend/src/pages/schedule/SchedulePageImpl.tsx` / `frontend/src/pages/schedule/ScheduleSettingsPage.tsx` / `frontend/src/pages/schedule/schedule-utils.ts` / `migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql` / `PR #2442` / `PR #2443` | 2026-06-22 |
| PR-C 外部API変更の自動検出 | Agent | `scripts/detect-external-api-change.js` の Discord / Google 誤判定を是正し、`scripts/tests/test-detect-external-api-change.js` を完全一致期待値へ更新して 12/12 pass を確認済み | GitHub Actions 実機で detector / workflow の挙動確認へ進む | `scripts/detect-external-api-change.js` / `scripts/tests/test-detect-external-api-change.js` / `node scripts/tests/test-detect-external-api-change.js` | 2026-06-20 |
| Advisor Phase 1 PR-2 新規/既存セグメント別 売上サマリーAPI | Agent | `backend/app/routers/analytics.py` に `/analytics/revenue-segments` を追加し、`new / repeat` の売上・件数・平均単価・顧客数・構成比を返す read-only 集計 API を実装中 | `backend/tests/test_analytics.py` に team / mine / boundary の pytest を追加し、`docs/handoff/advisor-phase1/` の recon/design を PR-2 用に更新して branch → push → CI へ進める | `backend/app/routers/analytics.py:97-464` / `backend/tests/test_analytics.py:519-664` / `docs/handoff/advisor-phase1/recon.md` / `docs/handoff/advisor-phase1/design.md` | 2026-06-20 |
| W-2① 属性別成約率集計 API | Agent | `backend/app/routers/analytics.py` に `/analytics/conversion-by-attribute` を追加し、RLS 実走の syntax 修正を含めて develop→main まで反映済み。SQLite 契約テスト / PG-RLS 実走 / release PR の merge は green | 完了 | `backend/app/routers/analytics.py` / `backend/tests/test_analytics.py` / `backend/tests/test_analytics_conversion_by_attribute_rls.py` / PR #2457 / PR #2458 / `gh pr checks 2446` | 2026-06-22 |
| PayPal Sandbox smoke の coverage 閾値除去 | Agent | `/private/tmp/paypal-sandbox/.github/workflows/external-api-smoke.yml` に `--no-cov` を追加済み | `test_paypal_sandbox.py` が PASS し、`process-artifacts gate` を含む workflow 全体が green であることを確認済み（run 27833818674 / 27833818677） | `/private/tmp/paypal-sandbox/.github/workflows/external-api-smoke.yml` / `gh run watch 27833818677` / `gh pr checks 2354` | 2026-06-20 |
| Discord ticket gateway visibility + lead紐付け修正 | Agent | PR #2360 反映後、private ticket channel の bot 可視性不足と未作成 lead を実機で再現し、`ticket_channel_creator.py` の修正着手中 | `backend/app/discord_gateway/ticket_channel_creator.py` の bot overwrite / lead upsert をテストで固め、CI 確認へ進む | PR #2360 / VPS ログ `Missing Access` / `tenant_004.leads` 空確認済み | 2026-06-19 |
| Claude Code KPI / Grafana 基盤 | Agent | backend の同時処理中リクエスト数 / SSE 接続数を `/metrics` と Grafana `backend-api-metrics` に追加し、さらに `monitoring-main` を総合通知 → 部門サマリー → 機能別詳細の階層ポータルへ再設計、色基準（緑=OK / 黄=注意 / 赤=異常）と repo反映 vs 実機反映の区別も明文化済み | Prometheus alert の warning line を実測値に合わせて微調整し、KPI 正本 `docs/ai-agents/kpi.md` の collector 設計へ反映する | `backend/app/metrics.py` / `backend/app/services/sse_pubsub.py` / `monitoring/grafana/provisioning/dashboards/json/backend-metrics.json` / `monitoring/grafana/provisioning/dashboards/json/monitoring-main.json` / `monitoring/prometheus/alert_rules.yml` / `docs/INCIDENT_RESPONSE.md` / `docs/runbooks/monitoring-vps-migration.md` 確認済み | 2026-06-17 |
| 監視VPS移行 M8（ADR-080） | PO待ち | M7完了・M8未着手。ADR-081 で監視VPS 受信経路と backend worker 方針を最終確定済み | PO確認の上、Sakura パケットフィルタ反映 → app VPS から 3000/3001/9090 疎通確認 → 1週間運用確認後にアプリVPSの旧監視Dockerボリューム削除（prometheus_data/grafana_data/loki_data） | docs/runbooks/monitoring-vps-migration.md / docs/adr/ADR-081-monitoring-vps-final-operational-design.md | 2026-06-17 |
| VPS runner登録（ADR-078） | PO待ち | 2026-06-15予定日到来も未実行。現在 qa-smoke 未稼働のまま | PO GOを待って `docs/runbooks/vps-runner-setup.md` に従い実行 | memory/project_vps_runner_plan.md / ADR-078 | 2026-06-17 |
| Meta App Review 申請 | PO待ち | ドキュメント整備済み・動画未撮影 | PO が申請動画を撮影 → Agent がレビュー申請書類を提出 | memory/project_meta_app_review_progress.md | 2026-06-17 |
| discord-gateway live受信の LLM 解析 env 注入（Issue #1154） | PO待ち | gateway は idle(bot token未設定)・DATABASE_URL/GEMINI_API_KEY 未注入を docker inspect で確認。live化した瞬間に DB接続失敗+LLM不発 | PO が live化判断 → compose の discord-gateway に DATABASE_URL/GEMINI_API_KEY 追加 + bot token 設定 + 実機確認 | Issue #1154 / docker-compose.yml | 2026-06-17 |
| (follow-up) ParseReviewPage の Phase A 在庫スキップ警告コードの撤去検討 | Agent | Option Z で Discord 承認が在庫を触らなくなり phaseAWarning が発火しない dead code 化。害は無いが整理候補 | 低優先。次の在庫系PRに同梱可 | frontend ParseReviewPage.tsx (phaseWarning) | 2026-06-17 |

---

## 完了（直近）

| タスク | 完了日 | PR |
|------|------|---|
| 受注管理(業務画面)テーマの器作成（3ファイル+索引登録） | 2026-07-04 | #2771 |
| 受信箱（inbox）親テーマ一式の新設 | 2026-07-04 | #2773 |
| エージェント完結の設計体制（To-Be 3ファイル標準） | 2026-07-03 | #2757 |
| 教訓便（起因ラベル・#2761記帳・5W2H-002） | 2026-07-03 | #2764 |
| Advisor Phase 1 PR-1 顧客別受注履歴API | 2026-06-20 | #2377 |
| Foundation F2 国の統制（lead.country を台帳から選ぶ） | 2026-06-21 | #2428 |
| サイドバークリック時の自動折りたたみ + hover 抑止修正 | 2026-06-20 | #2375 / #2376 |
| loading / feedback 共用部品の追加と main 反映 | 2026-06-19 | #2363 / #2348 / #2361 |
| 受信二言語化 第1便（中央受信パイプライン第一歩） | 2026-06-21 | #2423 / #2420 |
| 複数エージェント並行開発の標準化（ADR-086） | 2026-06-17 | #1254 |
| Generator executor フォールバック（ADR-082） | 2026-06-17 | #1232 |
| 解析レビュー明細テーブルのヘッダー sticky 固定 | 2026-06-17 | #1192 |
| QAチェックシート GitHub Pages 自動公開 + bootstrap publish（/qa/ 最新化） | 2026-05-30 | #1190 |
| release develop → main（AEON operation guide / ADR index sync / main back-merge 反映） | 2026-05-30 | #1178 |
| 在庫表「追加」(廃番トグル誤表記)ボタン撤去 + 誤archive3商品復元 | 2026-05-30 | #1187 |
| QAチェックシート I-03(AND/OR) を見積検索Fセクションへ移動 + 全URL監査(古いリンク0) | 2026-05-30 | #1188 |
| QAチェックシート更新（在庫新仕様反映: Option Z/18h失効/単位/F11-10,11追加） | 2026-05-30 | #1180 |
| 在庫オファー lifecycle（単位 unit 永続化 migration084 + 18時間自動失効 Celery purge） | 2026-05-30 | #1179 |
| 解析レビュー表 QA修正（メモ来歴削除/単価整数/差分数量列削除/単位列追加/列幅+承認Option Z） | 2026-05-30 | #1177 |
| AEON operation guide canonicalization | 2026-05-30 | docs/ai-agents/aeon-operation.md |
| AEON ディスパッチャ smoke validation | 2026-05-30 | /tmp/aeon-delivery-20260530-052601.log |
| リリース develop → main | 2026-05-29 | #1135 |
| 監視VPS移行 M1〜M7（ADR-080） | 2026-05-29 | #1146 #1148 #1150 |
| Agent pipeline redefinition / runtime sync | 2026-05-29 | #1158 |
| stale active-work クリーンアップ | 2026-05-29 | #1134 |
| Discord Webhook 分離 | 2026-05-29 | #1132 |
| PR固有 smoke テスト削除 | 2026-05-29 | #1133 |
| QA修正バッチ(Discord取込原文化/SM-4解析行/在庫0行濃淡/GEMINI passthrough) | 2026-05-29 | #1152 |
| check:new-tokens を release PR(develop→main)で skip | 2026-05-29 | #1159 |
| QA修正(#1152)の本番反映 (release develop→main → deploy success → backend に GEMINI_API_KEY 到達を docker inspect で確認) | 2026-05-29 | #1135 |

---

## フォーマットルール

- `担当`: `Agent` / `PO待ち` / `CI待ち` / `Agent+PO` のいずれか
- `現在地`: コマンド・ファイル・PR で確認した事実。「〜のはず」は禁止
- `次の一手`: 具体的なアクション（「進める」は不可）
- `根拠`: ファイルパス / PR番号 / ADR番号 / コマンド結果
- `更新日`: YYYY-MM-DD 形式

完了したタスクは「完了（直近）」テーブルに移動する。30日超過行は削除可。

## PMG インポート関連・進捗（2026-09-10）

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|------|------|------|
| ワンピース商品追加・解析対策 | 設計・実装担当 | PR #3434提出、GitHub2586成功/95skip、必須13成功。登録26候補静的検査成功 | 番号付きGO記録で手順検査を解消しマージ/配備。書籍区分など33候補の確認継続 | docs/handoff/tcg-product-master-growth/design-keyword.md §15 | 2026-09-11 |
| TCG 人確認後配信の検証記録 | 設計担当 | 実コードの人工192条件・修正関数7ケース照合済み。文書自己レビューAPPROVE、製品設計REVISE | 文書PRチェック後に条件付き許可の範囲で保存。共通判定/全項目確認/配信接続の正式設計は未完了 | docs/handoff/tcg-product-master-growth/recon.md「人の確認完了と配信を接続するための検証記録」/EV-20260912-HUMAN-REVIEW-DELIVERY-VERIFIED | 2026-09-12 |
| guards文書の手順・採番整合（依頼1〜3） | Agent | PR #3389マージ済み（c3eaa3d5）。worktree分便・L32人手照合・採番整合を反映 | 評価ゲートの設置・必須化結果は下記とEV-20260910-GUARD-ENFORCEDを参照 | docs/handoff/design-partner-card-ops/guards/04-worktree.md / docs/handoff/design-partner-card-ops/guards/11-lint.md / EV-20260910-GUARDS-DOC | 2026-09-10 |
| インポート関連・進捗 第1段階 | Agent | PR #3386マージをGitHubで再確認。画面未完成、本番反映未確認 | 解析記録・配信履歴・画面統合の後続設計 | docs/handoff/pmg-import-delivery-ssot/design.md / docs/handoff/pmg-import-delivery-ssot/recon.md | 2026-09-10 |
| PMG切替の隔離検証 | Terra / 設計担当 | 旧処理取消14件・Docker99件成功。PR #3408マージ済み。running2件復旧は別セッション担当 | PR #3408マージ/自動deploy成功。次は実設定・実配布経路の統合検証設計 | EV-20260910-PMG-CUTOVER-PROBE / docs/handoff/pmg-import-delivery-ssot/recon.md | 2026-09-10 |
| PMG入口配布・旧処理照合設計 | 設計担当 | PR #3410文書マージ/自動deploy成功。過去全件復元を必須にしない訂正と配布保留契約を草案化、自己審査REVISE | 本番切替時の保留方針をPO承認済み。複数SSHの所有制御と切替境界の観測手段を確定 | EV-20260910-PMG-BARRIER-CONTRACT / docs/handoff/pmg-import-delivery-ssot/design.md | 2026-09-10 |
| PMG総合ページ接続 | root / Codex Terra | PR #3416マージ17ebe93f・deploy34476536034成功。unit133件/E2E5件、公開JSとhealth確認済み | 対象取込91投稿の未解決5名をPO承認で新規登録、残件0を本番照会。次は取込確定・抽出開始。解析実行/永続配信履歴/本番切替の設計REVISEは継続 | EV-20260910-PMG-SCREEN-CONNECT / docs/handoff/pmg-import-delivery-ssot/card-screen-connect.md | 2026-09-10 |
| PMG進捗画面の見やすさ改善 | root / Codex Terra | PR #3424提出済み。unit143/E2E8/build/check:all成功、初回HEADのCIは承認記録以外成功 | GO #3424受領済み。最新main統合後のテスト/CIを確認してマージ。本番未反映 | EV-20260911-PMG-VISUAL-HIERARCHY / docs/handoff/pmg-import-delivery-ssot/design.md | 2026-09-11 |



## DB準備テストの領域分離（2026-09-10）

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|------|------|------|
| RLS bootstrapの他領域干渉解消 | Codex | PR #3399マージ済み（7e3dd656）。最終実PG2432成功・93スキップ、必須12件成功 | PR #3397マージ済み（a0c0eb7f）。以後は既存テストで維持 | docs/handoff/rls-bootstrap-txn-fix/design.md / EV-20260910-RLS-SCOPE | 2026-09-10 |


## ガード評価ゲート（依頼4、2026-09-10）

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|------|------|------|
| guards変更の必読・弊害・トレードオフ評価 | Codex | #3401マージ/配備済み。限定必須化済み。評価欠落BLOCKED、復元後13必須成功/CLEAN。試行#3405閉鎖 | 本文書PRで実測結果を正式保存。以後はガード変更時の評価と版照合を維持 | docs/handoff/design-partner-card-ops/guard-authoring-design.md / EV-20260910-GUARD-EVAL | 2026-09-10 |

## Inventory共有テーブル準備（2026-09-10）

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|------|------|------|
| inventory準備の共通ロック参加 | Codex | PR #3402マージ済み（89ad29ae）。実PG2467成功/93skip・全CI成功 | deploy34451686912成功、#3401へ取込み・設置済み。追加変更なし | docs/handoff/rls-bootstrap-txn-fix/design.md / EV-20260910-INVENTORY-LOCK | 2026-09-10 |


## 在庫補助解析モデル変更

| テーマ | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|---|---|---|---|---|---|
| 在庫補助解析3.1 Flash-Lite | Agent | 3.1へ実装更新・対象ruff成功。GitHub GEMINI_API_KEYをPO提供キーへ更新済み（01:45:14Z） | PR #3425 head e606ce4f: CI2544成功/93skip、唯一の失敗はGO未記録。GO #3425受領済み。最新CI後に正式マージ/デプロイ確認。本番反映未確認 | EV-20260911-INVENTORY-LITE25 / docs/handoff/llm-model-3-5-flash-lite/recon.md | 2026-09-11 |


## 商品マスタ画面の引継ぎ（2026-09-10）

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|------|------|------|
| 商品マスタ一覧・CSV画面 | Agent | PR #3422はdd9d3abfマージ・deploy34558334380成功、公開資産の2ルート/health確認済み。PO指定で既存サイドメニューを解析精度管理直下へ移動 | 配置変更PR #3429提出、eslint/build成功。最新CIと番号付きGOを確認して本番反映。CSV試行/44件登録は別便 | docs/handoff/tcg-product-import/recon.md / EV-20260911-PRODUCT-UI-IMPLEMENT | 2026-09-11 |
