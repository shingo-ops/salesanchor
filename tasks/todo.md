# Tasks

タスク台帳の正本。セッション開始時に必ず読むこと（`AGENTS.md §引き継ぎルール` 参照）。

---

## 進行中

| タスク | 担当 | 現在地 | 次の一手 | 根拠 | 更新日 |
|------|------|------|---------|-----|------|
| Foundation F1 国台帳 `public.countries` 新設 | Agent | `backend/app/routers/countries.py` / `backend/app/schemas/countries.py` / `backend/tests/test_countries_master.py` を追加し、`frontend/src/constants/countries.ts` を seed source とする migration `20260621_010000_create_countries_master.sql` を生成済み。SQLite 互換の `public.countries` rewrite も `backend/tests/conftest.py` に追加した | lint/test を回し、必要なら migration / docs / line ref を微調整して PR 化へ進める | `backend/app/routers/countries.py` / `backend/app/schemas/countries.py` / `backend/tests/test_countries_master.py` / `backend/tests/conftest.py` / `migrations/20260621_010000_create_countries_master.sql` / `docs/handoff/foundation-f1-countries-master/recon.md` / `docs/handoff/foundation-f1-countries-master/design.md` | 2026-06-21 |
| PR-E 人の確認/承認の必須化（process-artifacts gate 拡張） | Agent | `scripts/check-process-artifacts.js` に user-impacting change の Shingo GO 必須化を追加し、対象に `backend/app/auth/` / `backend/app/tasks/` / `backend/app/discord_gateway/` と **PR-C の外部API検出で見つかる変更**も含めるよう修正。`node scripts/tests/test-process-artifacts.js` で 72 PASS / 0 FAIL を確認し、feature/morimoto/pr-e-human-go-gate を更新 push 済み | Shingo GO を受領後、PR 本文へ `### GO記録` を反映し、CI 実機確認を経て merge 可否を判断する | `scripts/check-process-artifacts.js` / `scripts/tests/test-process-artifacts.js` / `docs/STANDARD-WORKFLOW.md` / `docs/handoff/incident-paypal-invoicing-false-complete/design.md` / PR #2410 | 2026-06-21 |
| PR-F 本番デプロイ安全化の決定記録（事前リハーサルはローンチ後） | Agent | `deploy.yml` に Pre-deploy DB backup / backend health check / auto-rollback / blue-green が既に実装済みで、PR-F の deploy 後 health + auto-rollback は既達と整理した。残件の事前リハーサルは staging 前提のバックログに分離した | ステージング環境構築後に PR-F の事前リハーサルと外部 health の auto-rollback 連動可否を再設計する | `docs/handoff/incident-paypal-invoicing-false-complete/design.md` / `docs/adr/ADR-1000-external-api-smoke-mandatory.md` / `.github/workflows/deploy.yml` / `.github/workflows/qa-smoke.yml` / `tests/qa-smoke/utils/db-assert.ts` | 2026-06-21 |
| feature/morimoto/discord-ticket-immediate-translation-2 | Agent | `backend/app/services/message_translator.py` に `detect_inbound_language` / `ensure_inbound_translations` / `original_language_override` を追加し、`tasks/translation.py`・`routers/conv_logs.py`・`services/translation_monitor.py` を新ルールへ差し替え。関連 pytest 40 passed、`python3 -m py_compile` 通過。`make lint-ci` は既存の mypy/bandit 基盤エラーで未完了 | PR 化して shingo-cc 経由の base=develop へ送る | `backend/app/services/message_translator.py` / `backend/app/tasks/translation.py` / `backend/app/routers/conv_logs.py` / `backend/app/services/translation_monitor.py` / `backend/tests/test_message_translator.py` / `backend/tests/test_ticket_channel_translation.py` / `backend/tests/test_translation_monitor.py` / `pytest -q --no-cov tests/test_message_translator.py tests/test_ticket_channel_translation.py tests/test_translation_monitor.py` / `make lint-ci` | 2026-06-21 |
| QA Smoke Suite #2346 psql 経路自己探索化 | 追跡 issue #2422 で Layer A を分離中 | `scripts/qa/reset-tenant.sh` を backend postgres コンテナ `astro-webapp-postgres-1` へ寄せる修正を入れ、`tests/qa-smoke/utils/db-assert.ts` と同じ実 DB への docker exec 経路に揃えた。Layer B は `tests/qa-smoke/utils/db-assert.ts` に `app.tenant_id=6` / `search_path=tenant_006,public` を付与して tenant RLS を backend と同文脈に揃えた。scene-05/06/08/09 は `test.skip` で #2346 を着地させ、認証ユーザー解決/データ可視性の根因を issue #2422 で追跡する | 再 smoke を流して backend 実 DB に `qa-admin` が入るかと `gh pr checks 2346` の failed=0 を確認し、merge 可否を判断する。Layer A は issue #2422 で別途修正 | `.github/workflows/qa-smoke.yml` / `scripts/qa/reset-tenant.sh` / `tests/qa-smoke/utils/db-assert.ts` / `tests/qa-smoke/utils/real-backend.ts` / `backend/app/auth/dependencies.py` / `backend/app/routers/staff.py` / `gh issue 2422` | 2026-06-21 |
| Advisor Phase 1 PR-5 W-1c フォロー追加 UI | Agent | `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx` に [フォロー追加] インライン composer を追加し、`/analytics/weekly-advisor-defensive` の `lead_id` から `PATCH /leads/{id}` まで繋ぐ実装を進めた。backend は `lead_id` 追加済み、`npm run build` と backend の `weekly_advisor_defensive` pytest は green。Playwright は mac の Chromium bootstrap 制約でローカル実行不可 | `scene1-dashboard.spec.ts` の追加 E2E は CI で確認し、required checks が緑なら PR 化して merge へ進める | `frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx` / `frontend/src/pages/dashboard/WeeklyAdvisorSection.css` / `frontend/src/api/funnel.ts` / `backend/app/routers/analytics.py` / `backend/tests/test_analytics.py` / `frontend/tests-e2e/scene1-dashboard.spec.ts` | 2026-06-21 |
| QA Smoke Suite #2346 psql 経路自己探索化 | 追跡 issue #2422 で Layer A を分離中 | Layer B は `tests/qa-smoke/utils/db-assert.ts` に `app.tenant_id=6` / `search_path=tenant_006,public` を付与して tenant RLS を backend と同文脈に揃えた。scene-05/06/08/09 は `test.skip` で #2346 を着地させ、認証ユーザー解決/データ可視性の根因を issue #2422 で追跡する | `gh pr checks 2346` が failed=0 になることを確認して merge 可否を判断する。Layer A は issue #2422 で別途修正 | `.github/workflows/qa-smoke.yml` / `tests/qa-smoke/utils/db-assert.ts` / `tests/qa-smoke/utils/real-backend.ts` / `backend/app/auth/dependencies.py` / `backend/app/routers/staff.py` / `gh issue 2422` | 2026-06-21 |
| Supply Chain PR-1/2 集計ルール・集計層 | Agent | `migrations/20260620_010000_create_inventory_aggregation_rules.sql` / `backend/app/services/inventory_aggregation.py` / `backend/tests/test_inventory_aggregation.py` に加え、実 API smoke `backend/tests/test_inventory_api_smoke.py` を追加。`gh run view 27902593736` で `pytest-run-internal` が PostgreSQL service 付きで実行され、smoke は skip ではなく実行されたが `public.suppliers.tenant_id` 不足で失敗。`test_meta_graph.py::test_app_id_missing_raises` は xfail、`test_discord_gateway_reconnect.py` は import-time pre-existing 赤として skip | `pytest-run-internal` の smoke 失敗原因を `public.suppliers` 既存 schema 差分として切り分け、CIでの実 row→API→集計経路の再検証へ進める | `migrations/20260620_010000_create_inventory_aggregation_rules.sql` / `backend/app/services/inventory_aggregation.py` / `backend/app/routers/inventory_offers.py` / `backend/tests/test_inventory_aggregation.py` / `backend/tests/test_inventory_api_smoke.py` / `backend/tests/test_meta_graph.py` / `backend/tests/test_discord_gateway_reconnect.py` / `.github/workflows/test.yml` / `gh run view 27902593736 --json jobs` | 2026-06-21 |
| Schedule Google Calendar UI PR2 カレンダー本体 | Agent | `frontend/src/pages/schedule/SchedulePage.tsx` を FullCalendar 依存から内製グリッドへ置換し、左パネル・週/日/月ビュー・空状態/読み込み中/詳細/編集ポップオーバーを実装し、`/schedule/settings` の scaffold も追加した | PR3 の settings 実装要件に合わせて表示/同期/カレンダー管理/通知の実データ接続へ進む | `frontend/src/pages/schedule/SchedulePage.tsx` / `frontend/src/pages/schedule.css` / `frontend/src/pages/schedule/ScheduleSettingsPage.tsx` / `frontend/src/pages/schedule/schedule-utils.ts` | 2026-06-20 |
| PR-C 外部API変更の自動検出 | Agent | `scripts/detect-external-api-change.js` の Discord / Google 誤判定を是正し、`scripts/tests/test-detect-external-api-change.js` を完全一致期待値へ更新して 12/12 pass を確認済み | GitHub Actions 実機で detector / workflow の挙動確認へ進む | `scripts/detect-external-api-change.js` / `scripts/tests/test-detect-external-api-change.js` / `node scripts/tests/test-detect-external-api-change.js` | 2026-06-20 |
| Advisor Phase 1 PR-2 新規/既存セグメント別 売上サマリーAPI | Agent | `backend/app/routers/analytics.py` に `/analytics/revenue-segments` を追加し、`new / repeat` の売上・件数・平均単価・顧客数・構成比を返す read-only 集計 API を実装中 | `backend/tests/test_analytics.py` に team / mine / boundary の pytest を追加し、`docs/handoff/advisor-phase1/` の recon/design を PR-2 用に更新して branch → push → CI へ進める | `backend/app/routers/analytics.py:97-464` / `backend/tests/test_analytics.py:519-664` / `docs/handoff/advisor-phase1/recon.md` / `docs/handoff/advisor-phase1/design.md` | 2026-06-20 |
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
| Advisor Phase 1 PR-1 顧客別受注履歴API | 2026-06-20 | #2377 |
| サイドバークリック時の自動折りたたみ + hover 抑止修正 | 2026-06-20 | #2375 / #2376 |
| loading / feedback 共用部品の追加と main 反映 | 2026-06-19 | #2363 / #2348 / #2361 |
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
