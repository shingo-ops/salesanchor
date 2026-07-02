# Evidence Registry

AI Agent の判断根拠を残すための台帳。ADR、仕様、テスト結果、ログ、コード参照など一次情報を優先する。

## Entry Template

```text
id: EV-YYYYMMDD-001
date:
agent:
task:
scope:
evidence:
  - type: file | adr | command | log | external
    reference:
    summary:
confidence: high | medium | low
tradeoff:
decision:
follow_up:
```

## Current Entries

```text
id: EV-20260622-009
date: 2026-06-22
agent: Codex
task: W-2① PR-3 frontend priority prospects display
scope: frontend/src/pages/dashboard/DashboardPage.tsx, frontend/src/pages/dashboard/PriorityProspectsSection.tsx, frontend/src/api/funnel.ts, frontend/src/mocks/funnelFixtures.ts, frontend/tests-e2e/scene1-dashboard.spec.ts, frontend/src/pages/dashboard/DashboardPage.stories.tsx, frontend/src/contexts/AuthContext.tsx, frontend/src/lib/firebase.ts, frontend/src/lib/firebase-auth.ts, frontend/tests-e2e/utils/api-mock.ts, tasks/todo.md
evidence:
  - type: file
    reference: frontend/src/pages/dashboard/PriorityProspectsSection.tsx
    summary: 攻めセクションを追加し、priority_prospect を rank_score 降順・しやすさ%・見込み金額・サンプル少・フォロー追加付きで表示する UI を実装した
  - type: file
    reference: frontend/src/api/funnel.ts
    summary: /analytics/priority-prospects?scope=mine を取得する型と client を追加した
  - type: file
    reference: frontend/tests-e2e/scene1-dashboard.spec.ts
    summary: priority prospects の表示と follow-up 保存を scene1-dashboard Playwright で検証するよう更新した
  - type: file
    reference: frontend/tests-e2e/utils/api-mock.ts
    summary: plain object fixture 内の status 文字列をレスポンスメタと誤認しないよう、数値 status のみ response detail と見なすよう修正した
  - type: command
    reference: E2E_NO_WEBSERVER=1 npx playwright test tests-e2e/scene1-dashboard.spec.ts --project chromium --workers=1 --reporter=line
    summary: scene1-dashboard の 6 テストが通過した
  - type: command
    reference: npm run build
    summary: frontend の production build が通過した
confidence: high
tradeoff: 既存 scene1 の nav 期待は現行 DOM に合わせてテスト側を更新したため、今後 nav 文言が変わる場合は同じ箇所の再調整が必要
decision: Dashboard の「今やること」へ攻め/守りの 2 セクションを追加し、E2E は dev-mode fake auth で安定実行する
follow_up: Chromatic baseline は未実施のため、UI baseline を Shingo 承認後に取得する
```

```text
id: EV-20260622-001
date: 2026-06-22
agent: Codex
task: W-2① 属性別成約率集計 API
scope: backend/app/routers/analytics.py, backend/tests/test_analytics.py, backend/tests/test_analytics_conversion_by_attribute_rls.py, tasks/todo.md
evidence:
  - type: file
    reference: backend/app/routers/analytics.py
    summary: /analytics/conversion-by-attribute を追加し、channel_type / country / sales_form / temperature / response_speed の 5 軸を all-time 集計、k=10 shrink、overall_rate 付きで返す read-only endpoint を実装した
  - type: file
    reference: backend/tests/test_analytics.py
    summary: SQLite 契約テストで empty / team / mine / shrink / n 返却を検証した
  - type: file
    reference: backend/tests/test_analytics_conversion_by_attribute_rls.py
    summary: tenant_006 を用いた PG/RLS 実走テストを追加し、RLS 接続変数未設定時は skip になる形で実装した
  - type: file
    reference: tasks/todo.md
    summary: W-2① を進行中タスクとして記録した
  - type: command
    reference: ruff check backend/app/routers/analytics.py backend/tests/test_analytics.py backend/tests/test_analytics_conversion_by_attribute_rls.py
    summary: touched analytics files の静的チェックが通過した
  - type: command
    reference: pytest -q backend/tests/test_analytics.py -k conversion_by_attribute --no-cov
    summary: SQLite 契約テスト 2 件が通過した
  - type: command
    reference: pytest -q backend/tests/test_analytics_conversion_by_attribute_rls.py --no-cov
    summary: PG/RLS 実走テストは接続変数未設定のため 1 件 skip になった
confidence: medium
tradeoff: 0-1 スケールの率で返すため、フロント側の表示時に必要ならパーセント換算が要る
decision: 既存 channels の scope 実装を踏襲しつつ、属性別集計は all-time の read-only endpoint として段階導入する
follow_up: RLS 接続先を設定した実環境で tenant_006 の実走を再確認し、PR 化する
```

```text
id: EV-20260622-002
date: 2026-06-22
agent: Codex
task: Schedule Google Calendar UI follow-up fix
scope: frontend/src/pages/schedule/SchedulePage.tsx, frontend/src/pages/schedule/ScheduleSettingsPage.tsx, frontend/src/pages/schedule.css, backend/app/routers/calendar.py, backend/tests/test_calendar_events_rbac.py, tasks/todo.md
evidence:
  - type: file
    reference: frontend/src/pages/schedule/SchedulePage.tsx
    summary: 他メンバーの表示トグルを label の onClick で確実に反映し、権限ゲートは staff.view であることを明示した
  - type: file
    reference: frontend/src/pages/schedule/ScheduleSettingsPage.tsx
    summary: /schedule/settings の 4 セクション + 右ペインヘッダー構造は維持しつつ、正本寄せの余白調整を CSS 側に委譲した
  - type: file
    reference: frontend/src/pages/schedule.css
    summary: settings shell / header / nav / content の top padding と列幅を調整し、右ペインの食い込みを防ぐ方向へ寄せた
  - type: file
    reference: backend/app/routers/calendar.py
    summary: 他担当の予定取得は staff.view のみ許可する既存ガードを確認し、manager 用の閲覧権限判定を維持した
  - type: file
    reference: backend/tests/test_calendar_events_rbac.py
    summary: 他担当予定の 403 / 200 の両パスを確認する RBAC テストが存在する
  - type: command
    reference: cd frontend && npm run build
    summary: TypeScript build と Vite bundle が成功した
  - type: command
    reference: cd frontend && npx eslint src/pages/schedule/SchedulePage.tsx src/pages/schedule/ScheduleSettingsPage.tsx
    summary: touched frontend files に対する lint が通過した
  - type: command
    reference: cd backend && python3 -m pytest tests/test_calendar_events_rbac.py -q -o addopts=''
    summary: 他担当予定の RBAC テスト 2 件が通過した
confidence: high
tradeoff: フロントの schedule 画面は見た目の余白を正本に寄せたが、実機スクリーンショットの最終突合は未実施
decision: トグル配線と settings レイアウトを壊さずに、最小限の UI/権限修正で正本へ寄せる
follow_up: 実機で /schedule と /schedule/settings を開き、レビューアカウントでチェック状態と 2 カラムをスクリーンショット突合する
```

```text
id: EV-20260620-006
date: 2026-06-20
agent: Codex
task: Schedule Google Calendar UI PR4 backend category expansion
scope: backend/app/services/calendar_service.py, backend/app/routers/calendar.py, backend/tests/test_calendar_service.py, frontend/src/pages/schedule/schedule-utils.ts, migrations/079_add_calendar_category.sql
evidence:
  - type: file
    reference: backend/app/services/calendar_service.py
    summary: calendar_events.category を作成・更新・Google webhook upsert・一覧レスポンスに反映し、NULL 時は 7種別へフォールバックするロジックを追加した
  - type: file
    reference: backend/app/routers/calendar.py
    summary: /calendar/events の create / patch payload に category を追加した
  - type: file
    reference: frontend/src/pages/schedule/schedule-utils.ts
    summary: schedule-utils の正規化を API category 優先、無い場合のみ derived fallback に切り替えた
  - type: file
    reference: migrations/079_add_calendar_category.sql
    summary: tenant_* schema の calendar_events に category カラムとチェック制約を追加する migration を作成した
  - type: command
    reference: cd backend && pytest -q tests/test_calendar_service.py --no-cov
    summary: calendar_service の 42 テストが通過した
  - type: command
    reference: cd backend && ruff check app/services/calendar_service.py app/routers/calendar.py tests/test_calendar_service.py
    summary: backend の touched files に対する ruff check が通過した
  - type: command
    reference: cd frontend && npm run build
    summary: frontend の production build が成功した
confidence: high
tradeoff: API/DB への category 追加でフロントのアダプタを解消できる一方、既存データの NULL category は読み取り時フォールバックで吸収する
decision: Persist category server-side and let the frontend prefer API values so PR2 の adapter を本番データに切り替えられるようにする
follow_up: 必要なら backlog 既存行の category backfill を次のメンテで追加する
```

```text
id: EV-20260620-008
date: 2026-06-20
agent: Codex
task: Schedule Google Calendar category conservative backfill migration
scope: backend/app/services/calendar_category_utils.py, scripts/migrate_20260620_080000_calendar_category_backfill.py, scripts/run_all_migrations.sh, backend/tests/test_calendar_category_utils.py
evidence:
  - type: file
    reference: backend/app/services/calendar_category_utils.py
    summary: category が NULL の既存行にだけ適用する保守的 backfill 判定を切り出し、personal と app 起点の明確な shipping / billing / purchase のみ返すようにした
  - type: file
    reference: scripts/migrate_20260620_080000_calendar_category_backfill.py
    summary: public.tenants の active テナントを巡回し、category IS NULL の rows のみを backfill して、曖昧な行は据え置く 080 データ migration を追加した
  - type: file
    reference: scripts/run_all_migrations.sh
    summary: 079 の直後に backfill migration を差し込み、080_phase_b_migration より前に実行されるようにした
  - type: file
    reference: backend/tests/test_calendar_category_utils.py
    summary: personal / 明示値不変 / source ガード / shipping-billing-purchase の判定と、backfill_schema が NULL 行だけ更新することをテストした
  - type: command
    reference: cd backend && ruff check app/services/calendar_category_utils.py tests/test_calendar_category_utils.py ../scripts/migrate_20260620_080000_calendar_category_backfill.py
    summary: touched Python files に対する ruff check が通過した
  - type: command
    reference: cd backend && pytest -q tests/test_calendar_category_utils.py tests/test_calendar_service.py --no-cov
    summary: calendar category backfill 関連テストと既存 calendar_service テストが 50 passed で通過した
confidence: high
tradeoff: live DB の NULL 件数確認はこの環境ではできないため、保守的ルールと unit test で安全性を担保した
decision: 既存データの曖昧な category は埋めず、後続の読み取りフォールバックに依存しない方向へ段階的に揃える
follow_up: 本番 PR では 080 データ migration を含めてレビューに回す
```


```text
id: EV-20260620-007
date: 2026-06-20
agent: Codex
task: PR-C 外部API変更の自動検出 実機確認とスコープ整理
scope: PR #2387, PR #2388, gh pr checks 2387, gh pr checks 2388, gh run view 27854430001 --log, gh run view 27854453163 --log
evidence:
  - type: file
    reference: scripts/detect-external-api-change.js
    summary: detector self-ignore を入れて自身の変更を外部API判定から除外し、discord / firebase のみを検出する状態に戻した
  - type: command
    reference: gh pr checks 2387
    summary: PR #2387 の External API gate が SUCCESS になり、PayPal Sandbox smoke は発火せず外部API未整備警告のみになった
  - type: command
    reference: gh pr checks 2388
    summary: docs-only PR #2388 で external API gate は skip / sandbox smoke は素通りした
  - type: command
    reference: HOME=/private/tmp XDG_CACHE_HOME=/private/tmp GH_TOKEN=$(gh auth token) gh run view 27854430001 --log
    summary: External API gate ログで discord / firebase を検出し、実環境スモーク未整備の出力を確認した
  - type: command
    reference: HOME=/private/tmp XDG_CACHE_HOME=/private/tmp GH_TOKEN=$(gh auth token) gh run view 27854453163 --log
    summary: docs-only PR の PayPal Sandbox smoke workflow が No sandbox smoke changes detected で終了することを確認した
confidence: high
tradeoff: 外部API検出の実機確認は検証用差分入りで行ったが、検証後は本番コードに残さないよう削除した
decision: PR-C の検出ロジックは本体のみで維持し、検証痕跡は別 PR への影響がない形で証跡化する
follow_up: PR #2387 をレビューしてマージし、PR #2388 は閉じる
```

```text
id: EV-20260620-005
date: 2026-06-20
agent: Codex
task: Schedule Google Calendar UI PR3 settings page
scope: frontend/src/pages/schedule/ScheduleSettingsPage.tsx, frontend/src/pages/schedule.css, frontend/src/constants/icons.tsx, frontend/src/locales/ja.json, frontend/src/locales/en.json, tasks/todo.md, .claude-pipeline/active-work.md
evidence:
  - type: file
    reference: frontend/src/pages/schedule/ScheduleSettingsPage.tsx
    summary: /schedule/settings を表示/同期/カレンダー管理/業務連動・通知の4セクション + カレンダー編集ダイアログ付きの設定画面として実装した
  - type: file
    reference: frontend/src/pages/schedule.css
    summary: settings shell / nav / save bar / dialog / toggle sizing を既存トークンのみで整え、CSS 値チェックに通る形へ調整した
  - type: file
    reference: frontend/src/locales/ja.json
    summary: settings page 用の i18n キーを追加した
  - type: file
    reference: frontend/src/locales/en.json
    summary: settings page 用の i18n キーを追加した
  - type: file
    reference: frontend/src/constants/icons.tsx
    summary: settings page 用の back / display / sync / calendar / automation / close アイコン定義を追加した
  - type: command
    reference: cd frontend && npm run build
    summary: TypeScript build と Vite bundle が成功した
  - type: command
    reference: cd frontend && npm run lint
    summary: lint は warnings のみで完了し、今回の schedule/settings 差分に error は残らなかった
  - type: command
    reference: cd frontend && npm run check:stylelint
    summary: 追加した CSS が stylelint を通過した
  - type: command
    reference: cd frontend && npm run check:css-values
    summary: 追加した CSS が数値ハードコードチェックを通過した
  - type: command
    reference: rg -n \"#[0-9a-fA-F]{3,8}\" frontend/src/pages/schedule.css frontend/src/pages/schedule/ScheduleSettingsPage.tsx frontend/src/constants/icons.tsx frontend/src/locales/ja.json frontend/src/locales/en.json
    summary: 今回の変更対象ファイルに hex の直書きがないことを確認した
confidence: high
tradeoff: The settings screen is now fully scaffolded on the frontend, but save API wiring is still deferred to the backend PR
decision: Finish PR3 as a frontend-only settings screen first so the backend category/API work can stay isolated in PR4
follow_up: Wire save persistence and any backend payload changes in PR4
```

```text
id: EV-20260620-004
date: 2026-06-20
agent: Codex
task: Schedule Google Calendar UI PR2 calendar shell
scope: frontend/src/pages/schedule/SchedulePage.tsx, frontend/src/pages/schedule/ScheduleSettingsPage.tsx, frontend/src/pages/schedule.css, frontend/src/pages/schedule/schedule-utils.ts, frontend/src/locales/ja.json, frontend/src/locales/en.json, frontend/src/App.tsx
evidence:
  - type: file
    reference: frontend/src/pages/schedule/SchedulePage.tsx
    summary: FullCalendar 依存を外し、左パネル・週/日/月ビュー・空状態・読み込み中・詳細/編集ポップオーバーを備えた内製グリッドへ置換した
  - type: file
    reference: frontend/src/pages/schedule/ScheduleSettingsPage.tsx
    summary: /schedule/settings ルートの scaffold を追加し、PR3 で実装差し替えできる土台を用意した
  - type: command
    reference: cd frontend && npm run build
    summary: TypeScript build と Vite bundle が成功した
  - type: command
    reference: cd frontend && npm run lint
    summary: lint は warnings のみで完了し、今回の schedule 差分に error は残らなかった
  - type: command
    reference: rg -n \"#[0-9a-fA-F]{3,8}\" frontend/src/pages/schedule.css frontend/src/pages/schedule/SchedulePage.tsx frontend/src/pages/schedule/ScheduleSettingsPage.tsx frontend/src/pages/schedule/schedule-utils.ts frontend/src/pages/schedule/Schedule.stories.tsx
    summary: 今回の schedule 実装ファイルに hex の直書きがないことを確認した
confidence: high
tradeoff: The runtime shell is now aligned with the new schedule design, but PR3 still needs the real settings controls and save API wiring
decision: Land the interactive calendar shell first so the settings work can reuse the same SSOT and layout primitives
follow_up: Implement PR3 settings wiring and then PR4 backend category expansion
```

```text
id: EV-20260620-003
date: 2026-06-20
agent: Codex
task: Schedule Google Calendar UI PR2 prebuilt states handoff sync
scope: docs/handoff/schedule-gcal/design.md, docs/handoff/schedule-gcal/recon.md
evidence:
  - type: file
    reference: docs/handoff/schedule-gcal/design.md
    summary: PR2-ready empty/loading/detail/edit states and screenshot set were documented for the schedule bundle
  - type: file
    reference: docs/handoff/schedule-gcal/recon.md
    summary: PR2 prebuilt states were appended to the recon notes so the later calendar implementation can consume them directly
confidence: high
tradeoff: The repo now carries a richer schedule handoff, but the actual runtime UI still remains to be implemented in PR2
decision: Preserve the design states in repo docs so PR2 can start from the same surface area as the updated bundle
follow_up: Implement the runtime adapter and the new calendar shell against these documented states
```

```text
id: EV-20260620-002
date: 2026-06-20
agent: Codex
task: Schedule Google Calendar UI PR1 token integration
scope: frontend/src/tokens.css, frontend/src/index.css, frontend/src/features/schedule/calendars.config.ts, docs/handoff/schedule-gcal/recon.md
evidence:
  - type: file
    reference: frontend/src/tokens.css
    summary: `--cal-*` / `--schedule-*` tokens were added to the central token file, with dark-mode overrides for the category palette
  - type: file
    reference: frontend/src/index.css
    summary: `--accent-bright` was added as the shared bright-accent alias used by schedule today styling
  - type: file
    reference: frontend/src/features/schedule/calendars.config.ts
    summary: schedule category SSOT was introduced as a standalone calendar definition module
  - type: file
    reference: docs/handoff/schedule-gcal/recon.md
    summary: token/component correspondence table and staged-deprecation notes were recorded for PR1
confidence: high
tradeoff: The schedule palette is now centralized before the main calendar rewrite, but the existing FullCalendar screen still needs adapter work in later PRs
decision: Freeze the schedule token surface now so PR2/PR3 can consume a stable SSOT
follow_up: Use the same `calendars.config.ts` module when the frontend adapter and settings page are implemented
```

```text
id: EV-20260620-001
date: 2026-06-20
agent: Codex
task: PR-C 外部API変更の自動検出
scope: scripts/detect-external-api-change.js, scripts/tests/test-detect-external-api-change.js, .github/workflows/external-api-smoke.yml, backend/tests/sandbox/test_paypal_sandbox.py, backend/pyproject.toml, docs/handoff/incident-paypal-invoicing-false-complete/design.md, docs/handoff/incident-paypal-invoicing-false-complete/recon.md
evidence:
  - type: file
    reference: scripts/detect-external-api-change.js
    summary: diff 行ベースで外部 API を分類し、GitHub Actions outputs へ PayPal/未整備 API の結果を渡す detector を追加した
  - type: file
    reference: scripts/tests/test-detect-external-api-change.js
    summary: 既知の外部呼び出しファイル群と無関係 UI ファイルの両方を検証する unit test を追加した
  - type: file
    reference: .github/workflows/external-api-smoke.yml
    summary: detector の結果に応じて PayPal Sandbox smoke / 未整備ログ / スキップを分岐する workflow を追加した
  - type: file
    reference: backend/tests/sandbox/test_paypal_sandbox.py
    summary: 実 PayPal Sandbox を叩く smoke test を root 側にも配置した
  - type: file
    reference: backend/pyproject.toml
    summary: sandbox を通常 pytest の探索対象から外し、専用 smoke marker を追加した
confidence: high
tradeoff: 既存の固定パス gate を残しつつ、コード内容ベースの detector を並走させるため、初期はログ量が増える
decision: PayPal の実スモークは維持し、その他の外部 API は未整備可視化で逃さない gate に移行する
follow_up: 新しい外部 API を追加するたび `scripts/tests/test-detect-external-api-change.js` に反映する
```

```text
id: EV-20260531-002
date: 2026-05-31
agent: Codex
task: 複数エージェント並行開発の標準化レビュー通過
scope: docs/PARALLEL_TERMINAL_GUIDE.md, docs/ai-agents/evidence-registry.md, docs/adr/ADR-086-parallel-development-standardization.md
evidence:
  - type: command
    reference: bash scripts/aeon-dispatch.sh reviewer "Re-review the branch feature/morimoto/parallel-dev-standard after the latest fixes..."
    summary: external PR review returned APPROVED / no findings after stale branch-first flow removal and evidence registry reinforcement
  - type: command
    reference: bash scripts/check-task-state.sh
    summary: task/runbook format checks passed after the doc updates
  - type: command
    reference: bash scripts/check-active-work-format.sh
    summary: active-work.md 6列 format checks passed after the doc updates
confidence: high
tradeoff: The standard is now validated by a reviewer run, but PR/merge evidence is still the next step if this needs to be promoted to mainline history.
decision: The parallel-development standard is repeatable by another session and the documentation changes are approved for PR submission.
follow_up: Create the PR and capture PR number / CI / merge SHA if the goal is mainline promotion.
```

```text
id: EV-20260531-001
date: 2026-05-31
agent: Codex
task: 複数エージェント並行開発の標準化
scope: docs/adr/ADR-086-parallel-development-standardization.md, docs/ai-agents/aeon-operation.md, tasks/todo.md, .claude-pipeline/active-work.md
evidence:
  - type: file
    reference: docs/adr/ADR-086-parallel-development-standardization.md
    summary: worktree / active-work / tasks / evidence / delivery-release / governance review を1枚に統合した標準 ADR を作成した
  - type: file
    reference: docs/ai-agents/aeon-operation.md
    summary: 実行手順の正本に ADR-086 への参照を追加した
  - type: file
    reference: tasks/todo.md
    summary: 今回の標準化タスクを進行中として登録した
  - type: file
    reference: .claude-pipeline/active-work.md
    summary: worktree 占有状況に本ブランチを登録した
  - type: command
    reference: node scripts/generate-adr-index.js
    summary: ADR-086 を含む ADR index を再生成した
  - type: command
    reference: bash scripts/check-task-state.sh
    summary: tasks/todo.md と関連 runbook の形式チェックが通過した
  - type: command
    reference: bash scripts/check-active-work-format.sh
    summary: active-work.md の 6 列フォーマットが通過した
  - type: file
    reference: /Users/tanizawashingo/worktrees/salesanchor/feature-morimoto-parallel-dev-standard
    summary: worktree path は feature/morimoto/parallel-dev-standard で分離されている
confidence: medium
tradeoff: 正本を1枚にまとめるぶん文書量は増えるが、同じ説明を各セッションで繰り返す無駄を減らせる
decision: 既存の worktree / AEON / evidence / release の仕組みを、並行開発の標準 ADR として正式化する
follow_up: Reviewer / CI / PR 番号 / merge SHA を追加して、ADR-086 を Accepted に更新する
```

```text
id: EV-20260530-001
date: 2026-05-30
agent: Claude Code (orchestrator)
task: Codex の役割を Research・Planning に拡張し、非対話 exec ラッパーを整備
scope: AGENTS.md, memory/project_codex_adoption.md, scripts/codex-research.sh
evidence:
  - type: command
    reference: codex --help
    summary: codex exec サブコマンドが実装済みであることを確認（v0.134.0）
  - type: command
    reference: ls scripts/
    summary: codex-generator.sh（TUI対話型）は存在するが codex exec 用の非対話ラッパーは存在しなかった
  - type: file
    reference: scripts/codex-generator.sh
    summary: 既存ラッパーは Generator（対話型TUI）専用であり Research/Planning 用の exec ラッパーは未作成
  - type: file
    reference: .claude/agents/research.md
    summary: develop ブランチでは既に存在していた（ギャップ③は既解消）
  - type: file
    reference: AGENTS.md
    summary: 役割分担テーブル（Codex: Research/Planning/Generator、Claude Code: Review）を追加済み
confidence: high
tradeoff: codex exec はサンドボックス制限あり（sandbox_permissions = disk-full-read-access）。書き込みが必要なタスクは codex-generator.sh（対話型）を使い続ける必要がある
decision: scripts/codex-research.sh を新設。--plan フラグで Planner モード切替可能。既存の codex-generator.sh は Generator 専用として温存
follow_up: 実運用 30 日後に Research/Planning exec モードの採用率を Governance が確認する
```

```text
id: EV-20260529-004
date: 2026-05-29
agent: Codex
task: Agent pipeline redefinition and runtime definition sync
scope: .claude/agents, docs/agents, AGENTS.md, CLAUDE.md, docs/onboarding/claude-code.md, docs/ai-agents/agent-roles.md
evidence:
  - type: file
    reference: .claude/agents/planner.md
    summary: Planner runtime prompt was rewritten to the Research -> Planner -> Architect -> PO Approval pipeline
  - type: file
    reference: .claude/agents/generator.md
    summary: Generator now requires Architect APPROVE and explicit PO Approval before implementation
  - type: file
    reference: docs/ai-agents/agent-roles.md
    summary: Runtime canonical source was moved to `.claude/agents/` and Architect was added to the role index
  - type: file
    reference: AGENTS.md
    summary: Project rules now document the new runtime pipeline and source-of-truth split
confidence: medium
tradeoff: Keeping both `.claude/agents/` and `docs/agents/` in sync adds maintenance overhead, but it preserves a short runtime prompt and a detailed reference layer
decision: Standardize the new Research -> Planner -> Architect -> PO Approval -> Generator -> Reviewer -> Evaluator -> GitHub CI pipeline with `.claude/agents/` as runtime source of truth
follow_up: Add a lightweight sync check or maintainers' review note if divergence between `.claude/agents/` and `docs/agents/` appears again
```

```text
id: EV-20260530-011
date: 2026-05-30
agent: Codex
task: AEON delivery runner startup confirmed with non-recursive smoke prompt
scope: scripts/aeon-delivery.sh, /tmp/aeon-delivery-20260530-051503.log, tasks/todo.md
evidence:
  - type: log
    reference: /tmp/aeon-delivery-20260530-051503.log
    summary: delivery flow started normally with research stage and read-only Codex wrapper invocation, confirming the same-terminal entry path works
  - type: file
    reference: tasks/todo.md
    summary: task row updated to reflect that delivery startup was confirmed but full smoke completion remains pending
confidence: high
tradeoff: the smoke prompt can confirm startup and stage wiring without proving a full end-to-end completion; completion needs a longer run or a bounded no-op task
decision: AEON delivery startup is working, but the smoke run is still incomplete
follow_up: run a bounded, non-recursive no-op smoke task to let the stage sequence complete
```

```text
id: EV-20260530-010
date: 2026-05-30
agent: Codex
task: AEON delivery smoke run interrupted by recursive prompt
scope: scripts/aeon-delivery.sh, /tmp/aeon-delivery-20260530-051337.log, tasks/todo.md
evidence:
  - type: log
    reference: /tmp/aeon-delivery-20260530-051337.log
    summary: smoke prompt triggered Research to invoke aeon-delivery.sh recursively, so the run was interrupted before the delivery stages completed
  - type: file
    reference: tasks/todo.md
    summary: task row updated to reflect that the first smoke run was interrupted by prompt recursion
confidence: high
tradeoff: a naive smoke prompt can recurse into the same AEON delivery entry point, so smoke prompts must explicitly forbid re-entry
decision: the first smoke run is not a valid success signal because it did not reach the intended stage sequence
follow_up: rerun delivery with a non-recursive smoke prompt
```

```text
id: EV-20260530-009
date: 2026-05-30
agent: Codex
task: AEON release runner and delivery/release split
scope: scripts/aeon-release.sh, docs/ai-agents/aeon-release.md, docs/ai-agents/aeon-delivery.md, docs/ai-agents/aeon-routing.md, docs/ai-agents/agent-roles.md, docs/onboarding/claude-code.md, .claude/settings.json
evidence:
  - type: file
    reference: scripts/aeon-release.sh
    summary: main 向け PR を worktree ownership と baseRefName の両方で確認してから merge commit する release runner を追加した
  - type: file
    reference: docs/ai-agents/aeon-release.md
    summary: delivery と release を分離した canonical 手順を追加した
  - type: file
    reference: docs/ai-agents/aeon-routing.md
    summary: AEON の observed sequence に release step を追加し、main 反映までの経路を明文化した
  - type: file
    reference: .claude/settings.json
    summary: Claude Code から release runner を実行できる allow list を追加した
confidence: high
tradeoff: delivery と release を分離すると安全性は上がる一方、運用ステップは 1 つ増える
decision: AEON の main 昇格は `scripts/aeon-release.sh` を別ステップとして扱う
follow_up: dummy PR で release runner の smoke check を実行する
```

```text
id: EV-20260530-008
date: 2026-05-30
agent: Codex
task: Evaluator contract alignment for AEON delivery runner
scope: scripts/codex-exec.sh, docs/agents/evaluator.md, .claude/agents/evaluator.md
evidence:
  - type: file
    reference: docs/agents/evaluator.md
    summary: Evaluator pipeline position and inputs were updated to run after Generator and before Reviewer
  - type: file
    reference: .claude/agents/evaluator.md
    summary: runtime evaluator definition was kept aligned with the same post-generator/pre-reviewer flow
  - type: file
    reference: scripts/codex-exec.sh
    summary: Codex exec evaluator prompt now matches the post-generator evaluation flow
confidence: high
tradeoff: evaluator no longer depends on Reviewer approval up front, which matches the new delivery runner but requires a disciplined handoff to Reviewer afterward
decision: AEON delivery flow evaluates immediately after Generator completion and before Reviewer PR handling
follow_up: smoke run the delivery runner on a small task to verify evaluator log flow
```

```text
id: EV-20260530-007
date: 2026-05-30
agent: Codex
task: AEON end-to-end delivery runner
scope: scripts/aeon-delivery.sh, docs/ai-agents/aeon-delivery.md, docs/ai-agents/aeon-routing.md, docs/onboarding/claude-code.md, .claude/settings.json
evidence:
  - type: file
    reference: scripts/aeon-delivery.sh
    summary: same-terminal で research → planner → architect → generator → evaluator → reviewer を連結する delivery flow を追加した
  - type: file
    reference: docs/ai-agents/aeon-delivery.md
    summary: delivery flow の canonical documentation を追加した
  - type: file
    reference: .claude/settings.json
    summary: Claude Code から delivery runner を実行できる allow list を追加した
confidence: high
tradeoff: delivery runner で一気通貫化すると運用は楽になるが、失敗時の切り戻しは各 stage の report に依存する
decision: AEON の end-to-end delivery は `scripts/aeon-delivery.sh` を canonical runner とする
follow_up: 実行結果を見て、必要なら stage 別ログの保存先を固定する
```

```text
id: EV-20260530-006
date: 2026-05-30
agent: Codex
task: Claude Code permission allowlist for AEON dispatcher
scope: .claude/settings.json, docs/onboarding/claude-code.md, scripts/aeon-dispatch.sh
evidence:
  - type: file
    reference: .claude/settings.json
    summary: project settings の allow list に aeon-dispatch / codex-* wrapper を追加した
  - type: file
    reference: docs/onboarding/claude-code.md
    summary: 同一 terminal session から AEON dispatcher を呼ぶ操作導線を追記した
  - type: file
    reference: scripts/aeon-dispatch.sh
    summary: dispatcher 自体は同一ターミナルから AEON roles を起動できる状態にあった
confidence: high
tradeoff: allow list を広げることで使いやすさは上がる一方、実行可能コマンドが増えるため運用ルールの周知が必要になる
decision: Claude Code の project settings に AEON dispatcher を許可し、オンボーディングに標準コマンドを追加する
follow_up: 実運用で不要な entry があれば、最小限まで allow list を絞る
```

```text
id: EV-20260530-005
date: 2026-05-30
agent: Codex
task: AEON routing index and same-terminal execution guide
scope: docs/ai-agents/aeon-routing.md, docs/ai-agents/agent-roles.md, scripts/aeon-dispatch.sh
evidence:
  - type: file
    reference: docs/ai-agents/aeon-routing.md
    summary: Claude Code から同一端末で AEON roles を起動する canonical routing を明文化した
  - type: file
    reference: docs/ai-agents/agent-roles.md
    summary: Role index に AEON runtime entry を追加して導線を揃えた
  - type: file
    reference: scripts/aeon-dispatch.sh
    summary: generator / research / planner / architect / reviewer / evaluator の role routing を持つ入口を整備した
confidence: high
tradeoff: ルーティングの正本を docs/ai-agents に足したことで説明責任は上がるが、更新時に index と routing doc の同期が必要になる
decision: Claude Code からの AEON 起動手順は `scripts/aeon-dispatch.sh` + `docs/ai-agents/aeon-routing.md` を正本とする
follow_up: 将来 role が増えたら `aeon-routing.md` の表を先に更新し、dispatcher を追随させる
```

```text
id: EV-20260530-004
date: 2026-05-30
agent: Codex
task: AEON mainline delivery KGI definition
scope: docs/ai-agents/kpi.md, docs/agents/governance.md, scripts/aeon-dispatch.sh
evidence:
  - type: file
    reference: scripts/aeon-dispatch.sh
    summary: Claude Code から同一ターミナルで Codex 担当ロールを呼び出す入口を定義済み
  - type: file
    reference: docs/agents/governance.md
    summary: Governance は KGI / KPI review を責務に持ち、AEON の最上位指標を参照できる位置にある
  - type: file
    reference: docs/ai-agents/kpi.md
    summary: GitHub / Claude telemetry / manual mapping の正本として KPI を集約していた
confidence: high
tradeoff: KGI を 1 本に絞ることで評価軸は明快になる一方、補助 KPI を併記しないと途中課題の切り分けが難しくなる
decision: AEON の最上位 KGI を `AEON Mainline Delivery Completion Rate` とし、Claude Code → Codex → PR → main の完了率で測る
follow_up: 30 日 or 10 deliveries の観測後に target 値を Governance で再評価する
```

```text
id: EV-20260530-003
date: 2026-05-30
agent: Codex
task: AEON dispatcher for same-terminal Codex invocation from Claude Code
scope: scripts/aeon-dispatch.sh, scripts/codex-generator.sh, scripts/codex-exec.sh, .claude/agent-config.sh
evidence:
  - type: file
    reference: scripts/codex-generator.sh
    summary: Generator 入口は既に存在し、Claude Code から同一端末で呼び出す前提を持っていた
  - type: file
    reference: scripts/codex-exec.sh
    summary: Research / Planner / Architect / Reviewer / Evaluator の non-interactive Codex 入口が既に揃っていた
  - type: file
    reference: .claude/agent-config.sh
    summary: worktree / branch / active-work の共通設定値が SSoT 化されていた
confidence: high
tradeoff: 1 本の dispatcher で入口を揃えることで運用は単純になる一方、ロール判定とパスの増加に応じて保守範囲が広がる
decision: Claude Code 側からは `scripts/aeon-dispatch.sh` を単一入口にし、Codex 担当ロールを同一端末で起動する
follow_up: 将来 role mapping が増えたら `.claude/agent-config.sh` から role table を読み込む方式を検討する
```

```text
id: EV-20260530-002
date: 2026-05-30
agent: Codex
task: Codex exec runtime extension for reviewer and evaluator
scope: scripts/codex-exec.sh, scripts/codex-reviewer.sh, scripts/codex-evaluator.sh, docs/agents/reviewer.md, docs/agents/evaluator.md, .claude/agents/reviewer.md, .claude/agents/evaluator.md
evidence:
  - type: file
    reference: docs/agents/reviewer.md
    summary: Reviewer agent の責務と sprint review / external PR review の2モードが既に詳細定義されていた
  - type: file
    reference: docs/agents/evaluator.md
    summary: Evaluator agent の責務と Playwright ベースの評価フローが既に詳細定義されていた
  - type: file
    reference: .claude/agents/reviewer.md
    summary: runtime 定義は Reviewer を別ロールとして公開していた
  - type: file
    reference: .claude/agents/evaluator.md
    summary: runtime 定義は Evaluator を別ロールとして公開していた
  - type: command
    reference: bash -n scripts/codex-exec.sh
    summary: 既存の role dispatcher に新規 role を追加しても構文上は問題ないことを確認済み
confidence: high
tradeoff: reviewer / evaluator も同一ディスパッチ基盤に載せることで運用は揃う一方、各 role のプロンプトが増えるほど dispatcher が長くなる
decision: codex exec の runtime wrapper を reviewer / evaluator まで拡張し、role-specific entrypoint を用意する
follow_up: 役割が増えたら `scripts/codex-*.sh` の共通化を検討する
```

```text
id: EV-20260530-001
date: 2026-05-30
agent: Codex
task: Codex exec non-interactive runtime sync
scope: .claude/agents, scripts/codex-exec.sh, scripts/codex-research.sh, scripts/codex-planner.sh, scripts/codex-architect.sh, docs/agents/research.md, docs/agents/architect.md
evidence:
  - type: file
    reference: docs/agents/research.md
    summary: Research agent の責務と出力先が既に詳細定義として存在していた
  - type: file
    reference: docs/agents/architect.md
    summary: Architect agent の責務と出力先が既に詳細定義として存在していた
  - type: file
    reference: .claude/agents/
    summary: runtime 定義に research / architect が欠けていた
  - type: file
    reference: scripts/codex-generator.sh
    summary: 既存の Codex ラッパーは対話型 Generator 専用で、非対話 exec ラッパーは存在しなかった
  - type: command
    reference: codex exec --help
    summary: Codex CLI は `exec` サブコマンドで非対話実行し、`--sandbox workspace-write` と `--cd` が使えることを確認した
confidence: high
tradeoff: research/planner/architect の役割を個別スクリプトに分けることで呼び出しは明示的になる一方、将来の役割追加時には薄い wrapper が増える
decision: non-interactive Codex は `codex exec` を正にして role-specific wrapper を追加し、runtime 定義も `.claude/agents` 側に同期する
follow_up: 将来必要なら Evaluator / Reviewer 向けの `codex exec` ラッパーも同じ方式で追加する
```

```text
id: EV-20260529-003
date: 2026-05-29
agent: Claude Code (orchestrator)
task: Forget-proof working memory implementation
scope: AGENTS.md, docs/ai-agents/task-template.md, tasks/todo.md, docs/runbooks/monitoring-vps-migration.md, docs/PARALLEL_TERMINAL_GUIDE.md, scripts/check-task-state.sh, .github/workflows/task-state-check.yml
evidence:
  - type: file
    reference: tasks/todo.md
    summary: 既存の台帳は「なし」のみで状態管理が存在しなかった → 生きたタスクテーブルに置き換え
  - type: file
    reference: .claude-pipeline/active-work.md
    summary: ブランチ占有管理は存在するが進捗状態（現在地/次の一手）は持っていない
  - type: file
    reference: docs/ai-agents/evidence-registry.md
    summary: Evidence Registry は存在するがタスク台帳との連携ルールが未定義だった
  - type: file
    reference: docs/runbooks/monitoring-vps-migration.md
    summary: スプリント状態テーブルが存在せず、会話メモリに依存していた
  - type: command
    reference: rg -n "現在地|次の一手|スプリント状態" tasks docs AGENTS.md
    summary: 実装前は該当するフィールドがどのファイルにも存在しなかった
confidence: high
tradeoff: tasks/todo.md を正本にすることで更新漏れリスクが残る。CI lint（check-task-state.sh）で構造違反を検出することで緩和する
decision: tasks/todo.md をタスク台帳正本とし、runbook にスプリント状態テーブルを追加。AGENTS.md に引き継ぎ必須ルールを明記。CI で構造チェックを自動実行
follow_up: 30日後に運用実態を確認し、更新漏れが多ければ ADR 化を検討
```

```text
id: EV-20260529-002
date: 2026-05-29
agent: Governance
task: Agent Operating System architecture setup
scope: AGENTS.md, docs/agents, docs/schemas, docs/ai-agents, .github/workflows inventory
evidence:
  - type: file
    reference: AGENTS.md
    summary: Runtime Prompt を短文参照方式へ変更
  - type: file
    reference: docs/agents/
    summary: 6 Agent の詳細定義を責務固定で作成
  - type: file
    reference: docs/schemas/
    summary: Research / Planner / Review / Evaluation / Governance の schema を作成
  - type: command
    reference: rg -n "design-review-gate|design review gate|Design Review Gate|design_review_gate|design-review" .github/workflows docs AGENTS.md CLAUDE.md .codex/config.toml
    summary: design-review-gate は既存 workflow/job として見つからなかった
confidence: medium
tradeoff: GitHub Ruleset の実登録状態は GitHub UI/API 確認が必要。workflow は今回変更しない
decision: Governance を runtime pipeline 外へ分離する移行案を docs/agents/governance.md に記録し、既存 workflow は温存
follow_up: 別 PR で governance job 分離と design-review-gate 追加要否を判断
```

```text
id: EV-20260529-001
date: 2026-05-29
agent: Governance
task: Codex AI Agent operating standard setup
scope: ~/.codex/config.toml, AGENTS.md, .codex/config.toml, docs/ai-agents
evidence:
  - type: file
    reference: AGENTS.md
    summary: 既存のプロジェクト共通ルール、不可逆操作、i18n、ADR 参照方針を確認
  - type: file
    reference: CLAUDE.md
    summary: Claude 側の役割分離、ADR-012、ADR-076、SSoT 索引を確認
  - type: file
    reference: .codex/config.toml
    summary: 既存設定は disk-full-read-access のみだったため、安全デフォルトへ更新
  - type: command
    reference: rg -n "<禁止モデル名>|gpt-5\\.5|gpt-5" ~/.codex/config.toml AGENTS.md CLAUDE.md .codex/config.toml README.md docs
    summary: 禁止モデル名は設定値・起動プロファイルから除去し、文書上は使用禁止ルールとしてのみ記載
confidence: medium
tradeoff: repo 全体探索を避けたため、指定範囲外に同種設定が残っている可能性は未確認
decision: Agent 役割、読取範囲、Evidence 必須化、repo 全体探索禁止を標準化
follow_up: 実運用後に ADR 化が必要か Governance が判断する
```

```text
id: EV-20260529-004
date: 2026-05-29
agent: Governance
task: Claude Code KPI / Grafana observability design
scope: AGENTS.md, docs/ai-agents/kpi.md, docs/agents/governance.md, monitoring/prometheus/prometheus.yml, monitoring/grafana/provisioning/dashboards/json/monitoring-main.json, docs/schemas/evaluation-package-v1.yaml
evidence:
  - type: file
    reference: AGENTS.md
    summary: KPI の正本を 1 ファイルに固定する方針を追記
  - type: file
    reference: docs/agents/governance.md
    summary: Governance の metric 定義を docs/ai-agents/kpi.md 参照に分離
  - type: file
    reference: monitoring/prometheus/prometheus.yml
    summary: 既存の Prometheus 収集基盤があり、追加 exporter を載せる土台がある
  - type: file
    reference: docs/schemas/evaluation-package-v1.yaml
    summary: Evaluator の合否と evidence 形式が既に schema 化されている
  - type: external
    reference: https://docs.anthropic.com/en/docs/claude-code/monitoring-usage
    summary: Claude Code telemetry で session / token / cost 系メトリクスが観測可能
  - type: external
    reference: https://docs.anthropic.com/en/api/data-usage-cost-api
    summary: Anthropic Admin API は個人アカウントでは利用不可
confidence: high
tradeoff: 個人 Pro Max では公式請求原本は取れないため、token/cost は telemetry proxy と manual mapping に分離する必要がある
decision: docs/ai-agents/kpi.md を KPI 正本とし、GitHub direct metrics / Claude telemetry / manual mapping / unavailable metrics を分離して設計する
follow_up: GitHub collector と Claude telemetry collector の実装計画を別 PR で具体化する
```

```text
id: EV-20260530-012
date: 2026-05-30
agent: Agent
task: AEON dispatcher smoke validation
scope: scripts/aeon-delivery.sh, scripts/aeon-dispatch.sh, scripts/codex-generator.sh, docs/ai-agents/evidence-registry.md, tasks/todo.md
evidence:
  - type: command
    reference: bash scripts/aeon-delivery.sh --smoke "AEON smoke validation: start all stages and return no-op reports only. Do not modify files. Do not inspect beyond what is needed to confirm the runner path. Stop after the stage sequence completes or the first blocker is found."
    summary: research -> planner -> architect -> generator -> evaluator -> reviewer の smoke ルートが同一ターミナルから完走し、generator は no-op、reviewer は REQUEST_CHANGES の smoke 応答を返した
  - type: file
    reference: /tmp/aeon-delivery-20260530-052601.log
    summary: delivery run の complete log が保存されている
  - type: file
    reference: tasks/todo.md
    summary: AEON ディスパッチャ行を完了側へ移動した
confidence: high
tradeoff: smoke validation はレビュー判定の実体ではなく、起動経路と run loop の到達性確認に限定される
decision: AEON delivery/release runner は smoke 完走まで確認でき、同一ターミナルからの Codex 呼び出し経路は実用可能と判断する
follow_up: live PR がある場合のみ `scripts/aeon-release.sh <PR番号>` で release 実行に進める
```

```text
id: EV-20260530-013
date: 2026-05-30
agent: Agent
task: AEON operation guide canonicalization
scope: docs/ai-agents/aeon-operation.md, docs/ai-agents/aeon-routing.md, docs/ai-agents/aeon-delivery.md, docs/ai-agents/aeon-release.md, docs/onboarding/claude-code.md, docs/ai-agents/agent-roles.md, tasks/todo.md
evidence:
  - type: file
    reference: docs/ai-agents/aeon-operation.md
    summary: delivery と release を 1 枚にまとめた canonical operating procedure を追加
  - type: file
    reference: docs/ai-agents/aeon-routing.md
    summary: routing index から canonical operation guide へ誘導した
  - type: file
    reference: docs/onboarding/claude-code.md
    summary: onboarding から canonical operation guide を参照するよう更新した
confidence: high
tradeoff: 既存の aeon-* ドキュメントは軽量索引として残し、重複説明は参照誘導に寄せた
decision: AEON の運用手順は `docs/ai-agents/aeon-operation.md` を正本とし、delivery / release / onboarding はそこへ集約する
follow_up: 新しい AEON 変更はまず operation guide と evidence-registry を更新してから関連索引へ反映する
```

```

```text
id: EV-20260530-001
date: 2026-05-30
agent: Claude Code (Hikky-dev)
task: Generator executor 選択 + Codex→Claude Code 自動フォールバック実装
scope: .github/workflows/claude-pipeline.yml / AGENTS.md / docs/adr/ADR-082
evidence:
  - type: adr
    reference: docs/adr/ADR-082-generator-executor-codex-fallback.md
    summary: generator_executor input (auto/codex/claude) の設計根拠・AC・トレードオフを記録
  - type: file
    reference: .github/workflows/claude-pipeline.yml
    summary: claude-worker L335-389 / regenerate L1035-1078 にフォールバックロジック実装。GENERATOR_FALLBACK env で Discord 通知を制御
  - type: file
    reference: AGENTS.md
    summary: 役割分担テーブルの「ジェネレーター」行に自動フォールバックを明記。§Generator Executor 切り替え を追加
  - type: command
    reference: governance agent 実行（2026-05-30）
    summary: MONITOR 判定。ADR 未記録・AGENTS.md 未反映・evidence-registry 未記録の3ギャップを特定 → 本エントリで解消
confidence: high
tradeoff: auto モードでは実際の executor をログで確認する必要がある。Codex が安定したら codex 専用モードへの移行を検討
decision: generator_executor=auto をデフォルトとし、Codex 不在・失敗時は自動で Claude Code にフォールバックする
follow_up: Codex フォールバック Discord 通知が頻発する場合は self-hosted runner の codex CLI インストールを確認する
```text
id: EV-20260530-014
date: 2026-05-30
agent: Agent
task: release develop → main completion for AEON sync
scope: PR #1178, gh pr checks 1178, gh pr merge 1178 --merge --delete-branch, tasks/todo.md, docs/ai-agents/evidence-registry.md
evidence:
  - type: command
    reference: gh pr checks 1178
    summary: Playwright E2E (chromium) と pytest-run-internal が pass し、release PR の必須チェックが揃った
  - type: command
    reference: gh pr merge 1178 --merge --delete-branch
    summary: GitHub 上で PR #1178 が MERGED になり、merge commit 341c399a505e3150a54612de6055fdbabbacc56a が生成された
  - type: command
    reference: gh pr view 1178 --json state,mergedAt,mergeCommit,url,mergeStateStatus
    summary: state=MERGED, mergedAt=2026-05-29T21:24:21Z, mergeCommit=341c399a505e3150a54612de6055fdbabbacc56a を確認した
confidence: high
tradeoff: local `gh pr merge` は worktree の branch checkout 制約で delete-branch に失敗したが、GitHub 側の merge 自体は完了した
decision: AEON 関連の develop → main release は PR #1178 で完了したとみなし、次の release 系作業では main 側の差分だけを別途確認する
follow_up: `tasks/todo.md` の完了欄と release 関連 runbook を必要に応じて参照更新する
```

## 2026-06-24 PR #2538 products tcg_type FK 動作確認

```text
id: EV-20260624-001
date: 2026-06-24
agent: Shingo（本番DB read-only SELECT）
task: PR #2538 products tcg_type FK 動作確認（STEP6検証）
scope: 本番DB pg_constraint, migration 20260623_030000_add_products_tcg_type_fk.sql
evidence:
  - type: command
    reference: "ssh prod1 docker compose exec -T postgres psql -U jarvis -d jarvis_db -c \"SELECT conname, conrelid::regclass AS tbl, confrelid::regclass AS references FROM pg_constraint WHERE conname = 'fk_products_tcg_type';\""
    summary: "1行返却 — fk_products_tcg_type | products | tcg_type_master。FK が本番DBに実在することを確認。"
  - type: review
    reference: migrations/20260623_030000_add_products_tcg_type_fk.sql
    summary: "pre-flight付き・データ非破壊（制約追加のみ）・冪等設計。deploy.yml run 28080592231 = success（2026-06-24T06:47:53Z）。"
  - type: review
    reference: PR #2538 mergeCommit 0abd9b6a / baseRefName main
    summary: "main に直接マージ済み。バックアップ salesanchor_db_20260624_082535.sql.gz はマージ後採取のため前後差分比較は実行不可。migration がデータ非破壊設計のため代替判定とする。"
confidence: high
tradeoff: バックアップ基準がマージ後のため「前後差分0」の数値比較は実施不可。pre-flightが違反0を保証しFKのみ追加する冪等設計を根拠に完了判定。
decision: "#2538 完了（正本の完了定義①〜④を満たす）。FK実在・deploy success・データ非破壊を本番DBで直接確認済み。"
follow_up: public.inventory / message_translations の行数前後差分はバックアップ逆転のため省略。次回のリリースPRでバックアップ採取タイミングをマージ前に統一すること。
```

## 2026-06-28 リリースB(#2646)デプロイOOM障害対応・サーバ容量回復・#2665デプロイ完走

```text
id: EV-20260628-001
date: 2026-06-28
agent: CC（Hikky-dev）+ Shingo（GO発行・本番画面確認）+ Claude（Planner）
task: リリースB(#2646)反映デプロイのOOM失敗 → サーバ容量回復（Docker掃除＋dockerd再起動）→ 本番無害立証 → #2665デプロイ完走
scope: 本番VPS(prod1)のディスク/メモリ/スワップ・Docker(キャッシュ/コンテナ/イメージ)・全コンテナ稼働・本番DB主要テーブル行数・app_fx_rates migration適用
evidence:
  - type: command
    reference: "ssh prod1: docker system df （掃除前）"
    summary: "Build Cache 15.07GB(RECLAIMABLE 14.96GB) / Images RECLAIMABLE 13.16GB / Volumes 1.978GB — 回収可能ゴミ総量を特定。volume/imageは今回対象外と判断"
  - type: command
    reference: "ssh prod1: docker builder prune -f → df -h / && docker system df"
    summary: "ビルドキャッシュ削除でディスク 40G(85%)→27G(56%)、13GB回収。Build Cache 15.07GB→117.8MB。イメージ・コンテナ・ボリュームには未接触"
  - type: command
    reference: "ssh prod1: docker rm astro-webapp-backend-green （停止コンテナのみ・名前指定）"
    summary: "deploy残存の停止コンテナ(Exited 0)1本のみ削除。稼働中(Up)コンテナには未接触"
  - type: command
    reference: "ssh prod1: ps aux --sort=-%mem （dockerd肥大の特定）"
    summary: "dockerd RSS 1.0GB(全体51.6%)を占有。本番アプリ各コンテナは軽量(backend-1 115MiB等)。逼迫の主因はdockerdのヒープ抱え込みと判定"
  - type: command
    reference: "ssh prod1: sudo systemctl restart docker → sleep 30 → docker ps （低利用時間帯に実施）"
    summary: "dockerd再起動。スワップ 1.1Gi→70Mi、dockerd RSS 1.0GB→323MB(677MB解放)、RAM available 310Mi→522Mi。全コンテナ復帰"
  - type: command
    reference: "ssh prod1: docker ps --format '{{.Names}}\\t{{.Status}}' | sort （復帰確認）"
    summary: "本番11本すべてUp、うち4本(frontend/nginx/postgres/redis)healthy。Exited残留0件。Stage0顔ぶれと一致。※backend-1は自動復帰せずExited(0)→手動起動で復帰（落とし穴・要調査）"
  - type: command
    reference: "ssh prod1: psql -d jarvis_db: 主要テーブル行数 + テナント別 leads/companies"
    summary: "suppliers47/tenants5/users10/inventory92/products1305 不変。本番tenant_004 leads6・companies51 / tenant_006 leads37・companies30 無傷。データ消失なし"
  - type: command
    reference: "ssh prod1: psql -d jarvis_db: SELECT to_regclass('public.app_fx_rates')"
    summary: "掃除前null→#2665デプロイ後 app_fx_rates 存在(0行・空テーブル正常追加)。migration正常適用・既存データ非破壊"
  - type: review
    reference: "deploy run 28322515797(#2665) 全ステップ✓: Pre-deploy DB backup / Deploy to VPS(OOM突破) / Run migrations / Post-deploy smoke tests / success"
    summary: "メモリ回復後の再デプロイが緑完走。前回OOMで停止した箇所を突破。スモーク緑＝本番正常応答。GO: Shingo 2026-06-28"
confidence: high
tradeoff: 掃除＋dockerd再起動の無害性立証と#2665デプロイ成功が同一deployで同時発生したため厳密分離は不可。ただし「処置後に本番が正常稼働・データ無傷」の事実は独立に成立。dockerd再起動は全コンテナ一時停止(数十秒〜数分)を伴う。
decision: "dockerd再起動＋Dockerキャッシュ掃除＋停止コンテナ削除は、本番を壊さずメモリ回復する有効手段として確立。再現手順=①docker builder prune -f ②停止コンテナrm(名前確認) ③低利用帯にsudo systemctl restart docker。禁止=volume prune(データ消失)/image prune -a(別セッション使用イメージ確認要)。症状トリガー=deploy blue-green healthタイムアウト＋スワップ枯渇＋dockerd RSS肥大。"
follow_up: "(1)dockerd再起動後backend-1が自動復帰しない件＝無人再起動時の本番停止リスク・要調査 (2)残骸再発防止＝定期自動掃除＋容量早期警報の設計 (3)根本RAM不足＝増設要否は今後のdeploy安定度で判断 (4)未使用イメージ13GB削除は森本さん確認後"
```

## 2026-06-27 PR #2630 public.products FORCE-RLS 本番反映・KGI①②③ 実証

```text
id: EV-20260627-001
date: 2026-06-27
agent: CC（Hikky-dev）+ Shingo（本番DB確認・GO発行）
task: PR #2630 release/products-rls-2540-resolve → main マージ後 KGI①②③ 本番実証
scope: 本番DB public.products RLS状態・4ポリシー・inventory.condition・バックエンドログ・ROLLBACK保証プローブ
evidence:
  - type: command
    reference: "ssh prod1: psql -U jarvis -d jarvis_db -c \"SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='products' AND relnamespace='public'::regnamespace;\""
    summary: "relrowsecurity=t / relforcerowsecurity=t — KGI① FORCE-RLS 本番で有効"
  - type: command
    reference: "ssh prod1: psql -U jarvis -d jarvis_db -c \"SELECT policyname FROM pg_policies WHERE schemaname='public' AND tablename='products';\""
    summary: "products_select / products_insert / products_update / products_delete — 4ポリシー全件存在"
  - type: command
    reference: "ssh prod1: psql -U jarvis -d jarvis_db -c \"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='inventory' AND column_name='condition';\""
    summary: "0 rows — D-1 migration（20260624_140000_converge_inventory_v2.sql）は本番で no-op（列存在せず＝影響なし）"
  - type: command
    reference: "ssh prod1: docker logs astro-webapp-backend-1 --since=2h 2>&1 | grep -E '42501|row.level.security|permission denied|RLS|InsufficientPrivilege'"
    summary: "(no output) — 本番反映後2時間、42501/permission denied ログ一切なし"
  - type: command
    reference: "ROLLBACK保証プローブ（BEGIN; SET LOCAL SESSION AUTHORIZATION salesanchor_app; SET LOCAL app.is_operator='true'; INSERT public.products '__postdeploy_probe__'; SELECT count(*); SET LOCAL app.tenant_id='6'; SELECT count(*) WHERE tenant_id IS NULL; ROLLBACK;）"
    summary: "operator_insert_ok=1（運営INSERT通過）/ tenant_read_ok=1306（テナントSELECT通過）/ ROLLBACK完了 — KGI② 本番実証"
  - type: command
    reference: "ROLLBACK後確認: SELECT count(*) AS probes FROM public.products WHERE name='__postdeploy_probe__'; SELECT relforcerowsecurity FROM pg_class WHERE relname='products';"
    summary: "probes=0（プローブ行残存なし）/ relforcerowsecurity=t（本番 FORCE-RLS 不変）— データ非残存・本番無変更を確認"
  - type: review
    reference: "PR #2630 merge commit e3a13731 / deploy run 28270188291 / main branch"
    summary: "migration [168/168] 完走・Green backend healthy 18s・deploy success。develop 不動（32800137）。GO: Shingo 2026-06-27。"
confidence: high
tradeoff: ROLLBACK保証プローブのため本番に実商品データは残していない。実トラフィックではなくプローブによる経路確認。
decision: "KGI①②③ 全達成。①FORCE-RLS+4ポリシー本番確認済み。②運営INSERT/テナントSELECT ROLLBACK保証プローブで実証・42501なし。③inventory.condition 0rows=他社漏洩リスクなし。PR #2540 GitHub自動MERGED（develop全コミットがmainに取り込まれたため）。"
follow_up: 実商品マスタ/在庫整備は別タスク。KGI③「固有行が他社から見えない」の実データによる確認は商品マスタ整備後に実施。
```

## Review Rules

- `confidence: high` は一次情報が複数あり、再現可能な検証がある場合に限る
- `confidence: medium` は一次情報はあるが範囲制限や未検証リスクが残る場合
- `confidence: low` は仮説、未検証、外部依存が強い場合
- Evidence なしのルール追加は禁止


## 2026-06-30: 標準フローに Phase 1.5「設計仕様書（あるべき姿）の確認・作成」を必須化 + 索引新設
- PR: #2698（base=develop・docs-only・5ファイル/44行 挿入のみ）/ merged 2026-06-30T06:40:51Z
- GO記録: GO発行者 Shingo / 日時 2026-06-30 / GO原文 GO #2698 / バックアップ確認 なし（docs-only）
- CI: process-artifacts gate ほか全 pass（fail ゼロ）
- 人の目視確認（develop反映後・Shingo）:
  - KGI#1 SOP表に「1.5」段が見える: ○
  - KGI#2 §1.5に「先に読む/無ければ作る」「理想優先」: ○
  - KGI#3 §1.5に「対象/対象外」の線引き: ○
  - KGI#4 docs/specs/README.md から product-master/README.md へリンク到達（blob 7dd60b1 実在）: ○
  - KGI#5 PRテンプレに「設計仕様書（あるべき姿）」欄: ○
  - KGI#6 PR #2698 develop マージ済み: ○
- 確認者: Shingo

## 2026-07-01: 文書の親子構造 標準ルール化テーマ KGI 5/5 達成（EV-20260701-001）
- id: EV-20260701-001
  type: review
  reference: "PR #2703 merge commit 365a5eec / PR #2704 merge commit 51db94b8 / main branch"
  summary: "文書の親子構造 標準ルール化テーマ KGI 5/5 達成。型見本(#2703)＋KGI③⑤(#2704)を main 反映。人の目視合格を確認。"
  confidence: high
  human_verification: "Shingo が GitHub 上で目視確認。図2枚(親子構造・関所と維持)が表示・親子リンクが双方向に到達・各文書冒頭に素人向け1行説明を確認。合格。"
  decision: "KGI①②④ 既達成 / ③ 子文書1行説明 4/4 / ⑤ 正本§1.6 明文化 1/1。達成KGI数 5/5。GO: Shingo 2026-07-01(#2704)。"
  lessons: "①マージ方式はリポ設定に合わせる(squash禁止→merge commit)。②GO発行者は英字表記(Shingo/shingo-ops)、ひらがな不可。③正本等の危険ファイル変更PRは『触るファイル:』『削除するファイル:』欄を平打ち(行頭空白・ダッシュなし)で必須。④マージ直後にMERGEDを実測してから台帳DONE・片付け(成否未確認で進むと未完なのにDONEの記録齟齬が発生)。"
  follow_up: "「設計に維持の仕組み欄を必須化し関所で守らせる」新テーマを引き継ぎ済み(第1弾:文章ルール＋守り手関所の名指し / 第2弾:記入と名指し実在の機械強制・案A / 適用は猶予＋warningで段階的)。"

## 2026-07-01: reaper 誤検出修正（専用棚一致で push 済み扱い）（EV-20260701-002）
- id: EV-20260701-002
  type: review
  reference: "PR #2705 merge commit a6050cfffe7cad4e557d956100646a922427a89c / main branch"
  scope: "scripts/reaper-worktree.sh / scripts/tests/test-reaper-safety.sh"
  problem: "reaper チェック2 bブロックの未push判定が @{u}..HEAD を使用。@{u} が共用側(origin/main・origin/develop)を指す設定漏れの worktree で、きれい・push済みの完了机を『未保存』と誤検出し永久保護＝堆積させていた。"
  fix: "HEAD == origin/<branch>（専用棚一致）なら push 済みとみなす救済を b に追加。a（未コミット確認）・c（upstream未設定分岐）・チェック3（完了確認）は不変。"
  kpi: "既存14テスト緑（回帰なし）＋再現テスト15追加。修正を stash 退避すると test15 が FAIL、復元で 15/15 PASS（テストがバグを捕捉することを立証）。"
  confidence: high
  human_verification: "Shingo が KPI ○A○B○C を確認。GO #2705 を自筆で発行。CI 全緑・process-artifacts gate pass を実測後マージ。"
  decision: "reaper 未push誤検出を修正し main 反映。完了机の自動回収が想定どおり効く状態にした。"
  lessons: "①CC が別worktree・本店へ勝手に台帳/GO を書き込む逸脱を複数回。生ログ照合と名指し1ファイル撤去で対処。②GO記録はしんご自筆のみ・代筆厳禁を再確認。③main宛PRのブランチ名は release/ または hotfix/ が必須（fix/ は関所で弾かれる）。"
  follow_up: "第1便で reaper 214/229行（②完了確認の develop→main 付替）を別途実施。カード⑥は本PRマージ後の最新 main で撮り直してから作成する。"

## 2026-07-02: develop廃止 第1便 動線をmainへ付替（EV-20260702-001）
- id: EV-20260702-001
  type: review
  reference: "PR #2715 merge commit 1df552b363160f5ebccb64913a1634395c9fb1be / main branch"
  scope: "書換8: gh-pr-create-safe.sh / pr-base-check.yml / executor-preflight.sh / new-worktree.sh / backfill-active-work-done.sh / reaper-worktree.sh / validate-pr-ownership.sh / validate-worktree-start.sh ＋修正1: workflow-lint.yml ／ 削除3: auto-back-merge.yml / auto-release-pr.yml / claude-pipeline.yml"
  problem: "PR動線・worktree土台・完了判定・各種ガードが develop 前提のままで、develop廃止（main一本化）に移行できない。"
  fix: "既定base・土台・判定・案内文を main/release に付替（develop残存0件×8を検算）。役目消滅の自動化3件を削除。workflow-lint の検査名簿から削除済み claude-pipeline.yml の項目を除去。"
  kgi: "KGI 5/5 達成（①既定base=main実測 ②削除3不在MISSING×3 ③develop残存0×8 ④MERGED+必須CI全pass+Shingo自筆GO #2715 ⑤develop存続=中止可能の担保 1b9a93b7）。"
  confidence: high
  human_verification: "Shingo が GO #2715 を自筆発行。必須チェック10件全pass・MERGED実測後に台帳DONE。"
  decision: "第1便完了。develop は未撤去（撤去は第3便・別途自筆GO）。CI設定整合性チェックの赤1件は workflow-lint.yml 変更時にPO確認を強制する仕様の警報であり、GO #2715 で確認済み＝想定どおりの赤（必須チェック外・マージ阻害なし）。"
  lessons: "①カードの禁止条項は便をまたいで残存し矛盾を生む→全カード冒頭に上書き宣言を必須化。②切れた表示から件数を推測しない（名簿9→8と誤予告、実物は10→9）。③絵文字直後の空白数など不可視差分はアンカー不一致の主因→hexdumpで実物確認。④行末バックスラッシュはアンカーに含めない。"
  follow_up: "第1.5便（守りの移設：main ruleset へ UI governance gate 等）→ しんご実地確認 → 第2便。第4便へ申し送り: runner-label-lint.yml 削除（検査対象消滅の死骸）／test-manifest-generation.sh:2,197 等の残コメント掃除／『絶対に緑にならない警報』の設計改善検討（索引で類似確認のうえ）。"



## 2026-07-02: 維持の仕組み欄の必須化（正本§1.7＋関所検査A/B）KGI 6/6 達成（EV-20260702-002）
- id: EV-20260702-002
  type: review
  reference: "PR #2717 merge commit 7cd89dd0 / 進捗記録 PR #2722 / main branch"
  scope: "docs/STANDARD-WORKFLOW.md §1.7新設 / scripts/check-process-artifacts.js validateMaintenanceSection / scripts/tests/test-process-artifacts.js 9本追加 / docs/handoff/design-partner-loop-maintenance-gate/"
  summary: "全designに維持の仕組み欄を必須化。関所が『欄と守り手の非空＋守り手パス実在』を検査（warn初期・MAINTENANCE_ENFORCE=failで引き上げ・PR2600未満は猶予）。design-partner-loop構想§5の予告便を実装。"
  kgi: "KGI 6/6（①正本§1.7明文 1/1 ②書式3点 3/3 ③design.md実例 3/3 ④空欄検知 1/1 ⑤架空パス検知 1/1 ⑥誤検知0・猶予巻き込み0）。テスト99本全緑。本番CI実機でもPR #2717自身と#2722の2回、警告ゼロ・pass を実測。"
  confidence: high
  human_verification: "Shingo が 2026-07-02 14時台にブラウザで3点を目視確認: ①main正本に§1.7が表示 ②PR #2717 がMerged＋全チェック緑 ③親README§5に済(#2717)記載。GO #2717 は自筆発行済み。"
  decision: "第1弾（文章ルール）＋第2弾（機械検査・warnモード）を main 反映。failへの引き上げは運用を見てPO判断（ワークフローにMAINTENANCE_ENFORCE=fail 1行のPR）。"
  lessons: "①CCが赤テストを無断で自己修正しコミットまで進める逸脱（修正内容は事後diff検証で採用可だったが手順違反）。②カードの停止条件は肯定形で一義に書く（『〜以外なら停止』は読み違いを誘発、2回停止）。③pushを飛ばしたPR作成は Head sha blank で失敗する。④机は AGENT_WORKTREE_BASE(~/worktrees)配下が必須、worktree move で中身ごと移設可能。"
  follow_up: "①warn→fail引き上げの時期判断（PO）。②修正md積み重ね（複数design）の関所対応は次便。③design-partner.md §6への教訓還流は別docs便で提案。"

## 2026-07-02: develop廃止 第1.5便 守りの移設（EV-20260702-003）
- id: EV-20260702-003
  type: review
  reference: "PR #2724 merge commit 257812ef01a8f88dc8cdeaf5b3a4529b787c2e49 / main ruleset 15777895（10→12件・PO自身がGitHub画面で実施）"
  scope: ".github/workflows/worktree-integrity-check.yml（発火先にmain追加）／main branch protection ルールセット（UI governance gate・dangling-route gate を必須追加）"
  problem: "develop撤去（第3便）後、develop側ルールセットの守り（鍵2・worktree検問）が誰にも掛からなくなる。"
  fix: "worktree検問の発火先を [main, develop] に拡張（#2724）。main必須チェックに2ゲートを追加（10→12件）。"
  kgi: "KGI 5/5（①UI governance gate=main必須11番目 ②dangling-route gate=同12番目 ③発火設定[main, develop]×2実測・実発火は次のactive-work.md変更PRで追認 ④既存10件無傷・12件ちょうど ⑤残差=Playwright E2E (chromium) 1件のみ・意図的除外を承認済み）。"
  confidence: high
  human_verification: "Shingo が GO #2724 を自筆発行・12件一覧を目視しPUT承認・404後はGitHub画面で自ら追加。MERGED実測後に完了承認。"
  decision: "第1.5便完了。E2E必須化は見送り（1人開発＋recon運用では必須化コスト＞利益。装置は必須外で存置し警報として活用）。"
  lessons: "①ルールセット変更はCC権限では404（権限不足は404で返る）＝管理者POの物理操作の領分。②関所の設計パス欄名は『設計:』（『設計doc:』は正規表現に掛からない）。③recon.mdの引用は後続便の削除で宙に浮く——世界を変えたら過去reconの引用整合も便に含める。④採番は毎回実測（002は別テーマが使用済み・2回連続で衝突を実測が防いだ）。"
  follow_up: "①KGI-3実発火の追認（次にactive-work.mdを触るPRで自然に確認）。②E2E必須化はskip時判定検証込みの独立テーマ（索引確認のうえ）。③巻き戻し控え=~/ruleset-main-before-batch1-5.json。④次は しんご実地確認 → 第2便（developの鍵外し）→ 第3便（撤去・自筆GO）→ 第4便（後片付け: runner-label-lint.yml削除・残コメント掃除）。"

## 2026-07-03: develop廃止・現在地スナップショット（複数セッションの誤報告防止）（EV-20260703-001）
- id: EV-20260703-001
  type: snapshot
  reference: "origin/main SHA 1e8d1a6e239975ece1ec5f05d6bb50a0ea4322f5（2026-07-03 01:04 JST 実測）"
  scope: "develop廃止計画の進捗に関する全争点の一括実測。別セッションからの『未完』報告2件（worktree検問main未発火・完了記録なし・new-worktree.sh develop起点）が古いmainを見た誤判定だったため、照合基準を1枚に固定する。"
  problem: "並行セッションが各自の時点のmainで検証し、解決済みの問題を『未完』と報告する事象が2件発生（鮮度未検証の古い写真問題）。"
  fix: "本記録なし（コード変更なし）。以下の実測値を照合基準として登録する。"
  kgi: "6争点すべて実測PASS: ①new-worktree.sh L80=BASE_BRANCH origin/main固定（#2715） ②claude-pipeline/auto-back-merge/auto-release-pr=MISSING×3（#2715） ③worktree-integrity-check.yml L5,L8=[main, develop]（#2724） ④main必須チェック12件 ⑤develop−main残差=Playwright E2E (chromium) 1件のみ（意図的除外・EV-20260702-003） ⑥EV-20260702-001/002/003各2箇所実在・develop存続 1b9a93b7（中止可能の担保）。"
  confidence: high
  human_verification: "Shingo がエビデンス確立を指示。実測生ログは設計パートナーセッションで全争点確認。"
  decision: "第1便・第1.5便は完了済みが正。develop未撤去は意図的（第3便まで残置）。別セッションは検証前に git rev-parse origin/main を取り、本記録のSHA以降のmainと突合すること。"
  lessons: "①並行セッションの検証は必ず実測時のmain SHAを併記する（SHAなしの『未完』報告は鮮度不明として扱う）。②解決済み事項の再報告はSHA突合で1手で棄却できる——スナップショット記録が構造的な防波堤になる。"
  follow_up: "残作業は変わらず: しんご実地確認 → 第2便（develop鍵外し）→ 第3便（撤去・自筆GO）→ 第4便（後片付け: runner-label-lint.yml削除・deploy.yml stamp・残コメント）。§3-2への守り正本リスト化は別セッション分担（衝突なし）。"

## 2026-07-03: develop廃止 第1.7便 エージェント案内書のRAG整合（EV-20260703-002）
- id: EV-20260703-002
  type: review
  reference: "PR #2745 merge commit 0de95d9c0b408df4c2b6efe195d32e0aa7ae1358（3コミット構成）"
  scope: "CLAUDE.md / AGENTS.md / docs/onboarding/claude-code-partner-prompt.md / docs/PARALLEL_TERMINAL_GUIDE.md（4枚をmain一本化へ整合）＋ docs/ai-agents/design-partner.md（接触面分析欄・作法3行・教訓1項目）"
  problem: "エージェントが読む案内書がdevelop前提のままで、並行セッションが古い世界観で動く（誤報告2件の真因・EV-20260703-001）。"
  fix: "4分類ルール（削除済み装置参照=撤去／develop起点手順=main書換／残置注記=意味更新して存置／禁止対象のdevelop=存置）で4枚更新。正本に接触面分析欄（6面走査・空欄不可）と作法3行を追加。"
  kgi: "5条件中○4＋条件つき○1: ①接触面分析欄=1 ②作法3行=各1 ③教訓1項目=1 ④案内書10/12（残置注記はSSOT原則でCLAUDE/AGENTSの2枚に集約・onboardingは45行で正本読了を誘導済み＝意図的） ⑤MERGED+CI緑+PO GO。"
  confidence: high
  human_verification: "Shingo がGOをPRコメントで発行しCCにマージを直接指示（本文GO記録欄は空欄のまま・事後承認で確定）。"
  decision: "第1.7便完了。Planner知識のRAG化＝学びを正本・案内書・記録層に外部化し全セッションに届く構造が成立。"
  lessons: "①正規表現の広域削除は巻き込み事故を起こす（AGENTS.md事業情報6行を誤削除→diff検出→HEAD~1から機械復元。消す範囲もアンカー完全一致で）。②検算に赤が残ったままコミットへ進む事故＝停止条件は肯定形で『④が全緑の場合のみ⑤実行』と書く。③GO転記とマージ実行の経路は1本に固定（本文4欄→一言GO→カード。コメントGO＋直接マージ指示は記録が割れる）。④KGIの粒度過剰もPlanner責任（注記×4はSSOTと矛盾・2枚集約が正）。"
  follow_up: "①次セッション冒頭の要点宣言に接触面分析が含まれるかでRAG動作を追認。②案内書lint（実在しないファイル名参照の機械検出）は索引確認のうえ独立テーマ。③しんご実地確認 → 第2便へ（変わらず）。"



