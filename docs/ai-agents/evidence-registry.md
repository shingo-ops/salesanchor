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
id: EV-20260910-LINE-ACCURACY-02
date: 2026-09-10
agent: Codex (design partner)
task: 保存済みLINE解析で実際に別商品となった行を一覧化
scope: docs/handoff/tcg-product-master-growth/recon.md の2026-09-10追加調査
evidence:
  - type: command
    reference: python3 /private/tmp/line-saved-misclassification-audit-20260910.py
    summary: 8/26保存済み解析1,086行と出力1,086行をdataRowで結合し商品ID・抽出名不一致0。原文まで確認した誤商品20行、全行pid_resolved=YES、うちFLAG_SINGLE15行
  - type: file
    reference: /private/tmp/line-confirmed-misclassifications-20260910.json
    summary: 保存行番号、保存商品ID、根拠、対応原文の記録番号と実行番号、入力3ファイルのSHA256を保存。原文の照合先は全20行で1件ずつ。7行は保存SPAN外に商品名があり、実際の原文行番号を別記
  - type: external
    reference: https://www.gundam-gcg.com/jp/products/eb01.html
    summary: Eternal Nexus EB01がガンダムの商品であることを確認
  - type: external
    reference: https://ws-tcg.com/products/nik_bp2/
    summary: NIKKE Vol.2がヴァイスシュヴァルツの商品であることを確認
confidence: high
tradeoff: highは当該バックアップの保存済み誤商品20行について。現本番の残存件数・配信実績・全体の誤り率は未確認。無作為標本ではなく疑わしい表記の抽出確認
decision: 少なくとも20行の誤商品を確認して記録。UA18BTとPC02BTの表記不一致は誤商品確定に含めない
follow_up: 現本番の保存済み判定と最新マスタを認可済み経路で読み取り、過去記録との差を確認
```

```text
id: EV-20260910-LINE-ACCURACY-01
date: 2026-09-10
agent: Codex (design partner, read-only investigation)
task: LINE解析のボトルネックと解決済み行の誤商品条件を確認
scope: docs/handoff/tcg-product-master-growth/recon.md の2026-09-10追記
evidence:
  - type: command
    reference: git ls-remote origin refs/heads/main
    summary: 8206ba2844921c1efb3ca4fd647230e76bb0c5c6 を固定してコードを確認
  - type: command
    reference: /private/tmp/line-accuracy-audit-20260910.json
    summary: 手元マスタ293商品で別商品単独1件。9/8変更値のメモリ適用では0件。末尾数字2付き表記の第1弾単独一致条件は両条件で再現。本番の保存済み誤判定ではない
  - type: command
    reference: /private/tmp/line-accuracy-parser-probes-20260910.json
    summary: 列数不正の部分欠落でもdone、不正SPANの先頭補正、万円・範囲の数値誤変換を合成入力で再現
  - type: command
    reference: gh pr view 3248 --json number,state,headRefOid,title,url
    summary: 人の判定を保護するPRはOPEN、head d074db1ae6d9120f669177810d2ecca153b66879
confidence: medium
tradeoff: 固定コードの挙動は実測済みだが、最新マスタ・AI抽出・保存済み判定を接続した本番監査は未実施。旧バックアップや単独一致率を正解率に読み替えない
decision: 調査暫定。設計審査・PO承認・実装開始・マージは行わない
follow_up: 認可済み読み取り経路で正常完了行を含む原文と判定を突き合わせる
```

```text
id: EV-20260704-001
date: 2026-07-04
agent: Codex
task: 受信箱（inbox）親テーマ一式の新設
scope: docs/specs/inbox/README.md, docs/specs/inbox/ideal-state.md, docs/specs/inbox/kgi.md, docs/specs/inbox/design.md, docs/specs/inbox/layout.svg, docs/specs/README.md, tasks/todo.md, .claude-pipeline/active-work.md
evidence:
  - type: file
    reference: docs/specs/inbox/README.md
    summary: 受信箱親テーマの表紙を新規作成し、範囲・構成・子テーマ一覧・見送り事項を正本化した
  - type: file
    reference: docs/specs/inbox/kgi.md
    summary: 受信箱の見せ方を 8 項目の○× KGI として定義し、Messenger / Instagram / Discord の分母を明記した
  - type: file
    reference: docs/specs/README.md
    summary: dashboard 行の直後に inbox 索引を 1 行追加した
  - type: command
    reference: gh pr view 2773 --json state,mergedAt,mergeCommit,url
    summary: PR #2773 が MERGED、merge commit は 1822d21c9c80b2fc319153d502837eaac37b508c
  - type: command
    reference: git rev-parse origin/main
    summary: origin/main の実測 SHA は 1822d21c9c80b2fc319153d502837eaac37b508c
confidence: high
tradeoff: 仕様文書のみの変更であるため、実装コードや API には影響しないが、索引登録により将来の子テーマ着手時に参照義務が増える
decision: 受信箱親テーマの正本セットを追加し、索引・台帳・active-work の記録を整合させた
follow_up: 子テーマ着手時は inbox 親テーマを先に読む前提で進める

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

## 2026-07-03 PR #2751 便1b 会話ログの背骨必須化

```text
id: EV-20260703-004
date: 2026-07-03
agent: CC
task: 便1b 会話ログの背骨必須化（echo経路のoutbound lead自動作成・遡及lead逆造成1件・NOT NULL）
scope: PR #2751, docs/specs/transaction-flow/README.md, docs/handoff/txn-flow-ben1b/design.md, 本番tenant_004 after検証
evidence:
  - type: command
    reference: "PO Shingo の after検証報告（2026-07-03）"
    summary: "conversation_logs null_convs=0 / [便1b]new_leads=1 / lead_id is_nullable=NO を目視報告済み"
  - type: command
    reference: "dry-run 再実行（2026-07-03）"
    summary: "BEFORE1 → AFTER0 → ROLLBACK。初回はテナント間スキーマ差分でエラー停止したが、最小列方式へ修正後に合格"
  - type: command
    reference: "/tmp/backup_tenant004_ben1b.sql"
    summary: "tenant_004 バックアップを取得済み"
  - type: command
    reference: "tenant_006 の dry-run notice"
    summary: "NULL 3 件のため NOTICE スキップ（DEMO 削除後に再実行で適用）"
confidence: high
tradeoff: 本番 after 検証は読み取り専用で実施し、実データの変更は行っていない
decision: 便1b は本番 tenant_004 の after 検証で成立確認済み
follow_up: 便2 の設計材料整理に進む
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

## 2026-07-03: hooks検証（見張りの生死と阻止力）（EV-20260703-003）
- id: EV-20260703-003
  type: investigation
  reference: "単体試験 exit=0×9（cwd=HOME/本店）／反応試験 2026-07-03 13:42 JST／実戦ログ PR #2748 マージ時 PreToolUse hook error×3→実行継続"
  scope: "~/.claude/settings.json（hooks住所）／~/.claude/scripts/ 5フック／実戦挙動の突合"
  problem: "hook failed頻発報告→『住所化け（/.claude/…）で見張り不在』の仮説が別セッションから提起された。"
  fix: "なし（検証のみ）。仮説は棄却。"
  kgi: "①住所は全件 ~/.claude/ 形式=化け仮説棄却 ②危険入力で danger-hook/scope-guard/worktree-guard が検知 exit=1＋警告文（gh pr merge/push --force/rm -rf/他人PR操作） ③しかし実戦では警告後に gh pr merge が実行完了=阻止力なしの疑い濃厚（表示『BLOCKED』と実効が不一致）。"
  confidence: high（検知の健在）/ medium（阻止力の機序は未修理・未設計）
  human_verification: "Shingo が hooks先行の順序を承認。反応試験の生ログを確認。"
  decision: "対処A（住所修正）は不要でクローズ。阻止力の修理（フックの返し方の見直し・~/.claude/=リポ外につきPO二段構え）は独立対処として次テーマ群へ。"
  lessons: "①転記化けが偽の真因を作る——実測が5分で棄却した。②『BLOCKED表示=阻止』ではない。守りの検証は表示でなく実効（実戦ログとの突合）で判定する。"
  follow_up: "①B+C便: generator.md但し書き（Plannerカード優先）＋応答様式節＋design-partner.mdカード設計規約＋check-freshness main化。②フック阻止力の修理（バックアップ→全文提示→PO承認→適用→阻止の実測）。③dangling-route gate誤検知対策（merge-base化 or docs-onlyスキップ・独立テーマ）。"

## 2026-07-03: 文書体系（ナレッジベース）起票（EV-20260703-005）
- id: EV-20260703-005
  type: review
  reference: "release/doc-estate-theme worktree / git diff --numstat / git diff / bash scripts/check-doc-heading-duplicates.sh"
  scope: "docs/specs/doc-estate/README.md / docs/specs/doc-estate/ideal-state.md / docs/specs/doc-estate/kgi.md / docs/specs/README.md / tasks/todo.md / .claude-pipeline/active-work.md"
  problem: "文書体系（ナレッジベース）の親テーマが specs 索引に無く、3 ファイル標準の正本置き場も未起票だった。"
  fix: "specs の索引へ 1 行追加し、doc-estate 配下に README / ideal-state / kgi の 3 ファイル標準を新設した。worktree と台帳も同時登録した。"
  kgi: "numstat=6件（新規3/追記3）・索引追加1行/削除0・見出し重複検査 PASS（docs/STANDARD-WORKFLOW.md と docs/ai-agents/design-partner.md の2本）"
  confidence: high
  human_verification: "Shingo の GO 待ちで PR 本文へ検算欄転記予定。"
  decision: "文書体系テーマを §1.5 の 3 ファイル標準構成で起票し、specs 索引から辿れる状態にした。"
  lessons: "①新規ファイルは intent-to-add で diff に出してから検算すると見落としが減る。②worktree を手動作成した場合は active-work 登録を忘れない。③索引更新は 1 行差分でも、親テーマが無いと発見性が落ちるため、親テーマの先行登録が有効。"
  follow_up: "GO 後に PR 作成、必要なら merge commit で main へ反映する。"
## 2026-07-03: 便1a 背骨の必須化（lead必須: deal/company・deal必須: order・遡及lead逆造成49件）（EV-20260703-002）
- id: EV-20260703-003
  date: 2026-07-03
  subject: 便1a 背骨の必須化（lead必須: deal/company・deal必須: order・遡及lead逆造成49件）
  pr: "#2743"
  spec: docs/specs/transaction-flow/README.md（K1/K2/K3根拠・KGI承認2026-07-02）
  design: docs/handoff/txn-flow-asis-recon/design.md
  evidence: |
    本番tenant_004 after検証（2026-07-03・読み取り専用）:
    null_companies=0 / total=51, new_leads=49（notes '[便1a]%'）,
    companies.lead_id is_nullable=NO。
    dry-run: BEFORE49→AFTER0→ROLLBACK、バックアップ /tmp/backup_tenant004_ben1a.sql（10,005行）。
    tenant_006: deals 18件/orders 26件 NOTICEスキップ（DEMO削除後に再実行で適用）。
  confirmed: "○（PO Shingo・2026-07-03・after検証3値を目視）"

## 2026-07-03: エージェント完結の設計体制 To-Be 納品前登録（EV-20260703-006）
- id: EV-20260703-006
  date: 2026-07-03
  agent: Codex
  task: エージェント完結の設計体制 To-Be 文書の納品前登録
  scope: docs/specs/agent-complete-design/README.md, docs/specs/agent-complete-design/ideal-state.md, docs/specs/agent-complete-design/kgi.md, docs/specs/README.md, tasks/todo.md
  evidence:
    - type: command
      reference: "date -u +'FRESH-RUN-START %Y-%m-%dT%H:%M:%SZ'"
      summary: "2026-07-03T06:43:00Z に worktree 作業を開始した"
    - type: command
      reference: "git merge --ff-only origin/main"
      summary: "worktree release/agent-complete-design を origin/main 9af6a97a へ fast-forward した"
    - type: file
      reference: docs/specs/agent-complete-design/README.md
      summary: "3ファイル標準の表紙として To-Be 文書を納品する"
    - type: file
      reference: docs/specs/agent-complete-design/ideal-state.md
      summary: "PO自筆のあるべき姿を正本として分離する"
    - type: file
      reference: docs/specs/agent-complete-design/kgi.md
      summary: "KGI と運用を表紙から分離して正本化する"
    - type: file
      reference: docs/specs/README.md
      summary: "索引に agent-complete-design の 1 行を追加する"
    - type: file
      reference: tasks/todo.md
      summary: "新規タスクを進行中として記録した"
confidence: medium
tradeoff: recon 前納品のため、親リンクと §4 は後続便で更新が必要になる
decision: "To-Be 文書をリポジトリに先行納品し、索引と台帳を同時に固定する"
follow_up: "PR 完了後に merge commit で main へ反映し、recon 後に親リンクを確定する"

## 2026-07-03: 便2 受注明細（order_items）新設＋仕入接続の完了登録（EV-20260703-007）
- id: EV-20260703-007
  date: 2026-07-03
  agent: CC
  task: 便2 order_items 新設＋仕入接続（S3・S6）の本番適用完了
  scope: PR #2756, migrations/20260703_030000_order_items_ben2.sql, 本番tenant_004 恒久確認
  evidence:
    - type: command
      reference: "gh run list --workflow=deploy.yml（run 28659581379）"
      summary: "PR #2756 マージ後の Deploy to VPS が completed/success（2026-07-03T12:08:53Z）"
    - type: command
      reference: "本番読み取り専用SELECT（2026-07-03 21:14）"
      summary: "tenant_004 で order_items=1／paid_at・shipping_fee の2行／order_item_id の1行を確認（ROLLBACKなしの恒久状態）"
    - type: command
      reference: "/home/ubuntu/backup_ben2_20260703_172641.dump"
      summary: "適用前バックアップ（pg_dump custom形式・2,409,849 bytes）を取得済み"
    - type: command
      reference: "本番dry-run（2026-07-03 17:41）"
      summary: "BEGIN→migration→検証SELECT3本→ROLLBACK で構造増設のみを事前確認し、PO目視4点が全て○"
  confidence: high
  tradeoff: purchase_orders未作成の旧テナントはto_regclassガードでスキップされるため、該当テナントには仕入列が立たない
  decision: "ガード付きmigration（ab002d76）をdry-run目視4点とGO記録（2026-07-03 17:58, shingo-ops）を経て本番適用し、POが自らマージした"
  follow_up: "便3（段階・成約の自動判定）へ。本セッションのCC違反2件（無断migration修正push・無断PR本文上書き）はB+C便のgenerator.md改定入力として扱う"

## 2026-07-07: B+C便 agent設定整合＋鮮度フックmain基準化（EV-20260707-001）
- id: EV-20260707-001
  date: 2026-07-07
  agent: CC
  task: B+C便 — generator.md/design-partner.md整合（B-1〜B-4）＋check-freshness.sh を origin/develop→origin/main（C）
  scope: PR #2807, .claude/agents/generator.md, docs/ai-agents/design-partner.md, .claude/hooks/check-freshness.sh, docs/handoff/agent-guardrails/recon.md, docs/handoff/agent-guardrails/design.md
  evidence:
    - type: command
      reference: "gh pr view 2807 --json state,mergedAt,mergeCommit"
      summary: "state MERGED / mergedAt 2026-07-07T03:20:12Z / merge commit 277d4443 を確認"
    - type: command
      reference: "git merge-base --is-ancestor 951137ab origin/main"
      summary: "PR先頭 951137ab が origin/main の祖先＝マージ実測（MERGED-CONFIRMED）"
    - type: command
      reference: "git show origin/main:.claude/hooks/check-freshness.sh | grep -c origin/develop"
      summary: "main上フックの develop参照=0・main参照あり（C完了の実測）"
    - type: command
      reference: "git show origin/main:.claude/agents/generator.md | grep -c 'Planner card overrides'"
      summary: "B-1 カード優先ルール=1件 main反映"
    - type: command
      reference: "git show origin/main:docs/ai-agents/design-partner.md | grep -c 'カード設計の規約'"
      summary: "B-4 カード設計規約=1件 main反映"
    - type: command
      reference: "使い捨てクローンで /tmp/hook-main.sh 実行（FRESH-RUN 2026-07-07 13:20:28）"
      summary: "ケースA=古地点で『origin/main より新しい』警告が発火(A-EXIT=0)／ケースB=最新mainで沈黙(B-EXIT=0)。鳴るべき時に鳴り・鳴るべきでない時に黙るを両方実測"
  confidence: high
  tradeoff: "develop上の旧worktreeにmain基準の警告が出るが、developは新規作業禁止（handoff§4）ゆえ望ましい挙動"
  decision: "5点をrelease/agent-guardrails-bcで実装、process-artifacts gate緑通過、GO原文『GO』（shingo-ops 2026-07-05）を経てPOがmerge commitでマージ。C便は使い捨てクローンで動作実測しmain文言発火を確認"
  follow_up: "本店をmainへ戻す片付け／フック阻止力の修理（BLOCKED後も実行継続・EV-20260703-003残課題）／dangling-route gate誤検知対策"

id: EV-20260720-001
date: 2026-07-20
agent: Codex
task: サーバーリソース最適化 ①未使用Dockerイメージの排除(prod1)
scope: prod1 未使用Dockerイメージ19部品の名指し削除（docker rmi・force不使用）
evidence:
  - type: command
    reference: "GO記録（Shingo / 2026-07-20 / GO）"
    summary: "直前1世代3件を保持し、削除対象19件は公開倉庫/GitHubから再入手可能であることを確認した"
  - type: command
    reference: "docker rmi（対象19件を名指し・force不使用）"
    summary: "未使用イメージ19部品を削除し、稼働中・直前1世代・幽霊部品・要判断は除外した。前便の19件中13件を実行し、残り7部品8ラベルを継続便で完了した"
  - type: command
    reference: "docker images --no-trunc --format '{{.ID}}' | sort -u | wc -l"
    summary: "削除後イメージ数=17"
  - type: command
    reference: "docker ps --format '{{.Names}}\\t{{.Status}}'"
    summary: "稼働コンテナ13台がすべてUp、healthy表示対象もhealthyであることを確認した"
  - type: command
    reference: "df -h /; docker system df"
    summary: "ディスク使用量27GB→20GB（7GB回収）、イメージ在庫16.2GB→8.2GBを実測した"
confidence: high
tradeoff: "名指し19部品だけを削除し、volume・コンテナ・prune全種には触れなかったため、型4.4GBと空き箱168個（2GB）は残置した"
decision: "POのGO（Shingo / 2026-07-20 / GO）を根拠に、未使用Dockerイメージ19部品を名指し削除した"
follow_up: "型4.4GB・空き箱168個（2GB）は未処理。③④（掃除係規定拡張＋死活通知）は未実装。prod2の秘密入り.bak散乱は別便。事故なし・サービス無停止"

## EV-20260715-2924 : スコープガードがblock記録した直後にマージが成立（経路未捕捉）

- 事象: PR #2924（inbox/invoice-form-send To-Be design）のマージで、手元ガードがblockを記録したにもかかわらずマージが成立。成立コマンドがエージェントログに残っていない。
- ガード: `~/.claude/scripts/gh-scope-guard.sh`（PreToolUse・exit1=hard block）。理由「PR#2924 は自分のPRではない（許可なし）」で `gh_scope_blocked` を記録。
- blocked記録時刻: `2026-07-15T12:44:10Z` / `2026-07-15T13:05:57Z`（`agent-events.jsonl:40835`, `:40854`。フィールドは `type/session/branch/reason/ts` のみ、`actor/tool/pid` 無し）
- 実マージ（GitHub側メタデータ）: `mergedBy=shingo-cc` / `mergedAt=2026-07-15T12:44:15Z` / `mergeCommit=9bed25ba757a9818a73948fa3cfd6502b3908768`
- 迂回フラグ: 生ログに `--admin` / `--force` / `--no-verify` / `HUSKY=0` / `SKIP=` は未検出。
- 未捕捉: `agent-events.jsonl` に #2924 のマージ成立イベントは無い（blocked 2件のみ）。他ログにも成立記録なし。
- 評価: 実行主体（`shingo-cc`）は正当。問題は仕組み層の2つの穴 - (1)`gh-scope-guard` が `gh pr merge` の一部経路しか止められていない（網羅性）、(2)エージェントログが成立イベントを捕捉していない（監査性）。§6「検問failed後の続行=素通り扱い・結果無事は手順の正当化にならない」に該当。
- 引き継ぎ: 恒久是正は `branch-operations` / ガード層テーマで recon→設計→GO。本子テーマ（invoice-form-send）のスコープ外。

### 追試 EV-20260715-2924b : #2927 で同型再現（常態確認）＋ログ不整合

- 目的: #2924の齟齬が個別か常態かを、記録専用PR #2927 のマージ実行時に実測して切り分け。
- 結果: 再現。ガードは #2927 でも `gh_scope_blocked` を記録（`2026-07-15T15:02:06Z`・理由「PR#2927 は自分のPRではない（許可なし）」）が、マージは成立（`MERGE_RC=0` / `state=MERGED` / `mergedBy=shingo-cc` / `mergedAt=2026-07-15T15:02:12Z` / `mergeCommit=e02b849ba61c563e5c0b4ce7aa2f6878b04134a8`）。`blocked→merged` は約6秒差で #2924 と同型。
- 判定: `gh-scope-guard` の素通りは個別事象でなく常態（#2924・#2927 で2回連続再現）。
- 追加欠陥（ログ信頼性）: マージ前後のログ行数が同一（`LOG_LINES_BEFORE=LOG_LINES_AFTER=40924`）にもかかわらず、`gh_scope_blocked for 2927` の行がログに存在。行数と内容が不整合＝`agent-events.jsonl` を監査の一次証拠に使う前に、記録の整合性自体の検証が必要。
- 引き継ぎ（優先度・ガード層テーマへ）: (1)`gh pr merge` の全経路をガードで捕捉（網羅性）、(2)成立イベントのログ捕捉（監査性）、(3)ログ書き込みの整合性（行数と内容の一致）。本子テーマ（invoice-form-send）のスコープ外。
- EV-20260720-001: new-worktree.sh が「走査行のみ表示して沈黙する」事象の原因を bash -x 実測で確定。原因は内部で呼ぶ reaper-worktree.sh の排他制御(「[reaper] another instance is running; skip.」)で、並行セッション稼働時に出力が途切れる。worktree 作成自体は続行される場合と作成されない場合がある(2026-07-19〜20 に3回再現、うち2回は作成済み・1回は未作成)。worktree数上限(100)は無関係(実測81)。対処: 作成未確認時は bash -x で全記録を取り停止する運用。恒久対処は worktree 運用テーマの延長で道具改修便を起票予定。実測記録は release/local-hooks-ssot-spec 便のカード報告に全文あり。

## 2026-07-22: reaper 配線ズレ修正とK1動作確認（EV-20260722-001）

  reference: "PR #3043 mergeCommit=9a7f2995e8a59c7352e6f6ee81b46f8c796ebf22 ／ 仕様書 PR #3044 mergeCommit=5165d73a3a2d2483bb16ce6b0fac3a462d9519be"
  scope: ".github/workflows/reaper-schedule.yml への REAPER_WORKTREES_DIR 注入（6行追記・削除0）"
  problem: "定期 reaper が self-hosted runner の actions/checkout により _work 配下で実行され、git-common-dir が _work 側を指すため本店の worktree 登録を共有せず、対象0件のまま毎日空振りしていた（2026-07-20 実測: Working directory is /Users/tanizawashingo/actions-runner-shingo/_work/salesanchor/salesanchor ／ 対象 worktree 数: 0 件）。"
  fix: "reaper 実行ステップに REAPER_WORKTREES_DIR=/Users/tanizawashingo/worktrees/salesanchor を env 注入。reaper 本体・checkout 構成は変更していない。"
  kgi: "K1（定期reaperが本店の実worktreeを走査）合格。マージ後の dry-run 実測で 対象 worktree 数 = 91 件（修正前は 0 件）。同 dry-run で main/develop の削除候補混入なし、使用中作業台（release/reaper-scan-dir-fix・release/reaper-auto-cleanup-spec）も候補外、既知の異物3件と main-rls-bootstrap-ordering も候補外を全数確認。"
  note: "採用案は 2026-07-22 に手動 dry-run で有効性を実証済みの最小変更。checkout 廃止案・reaper 本体自衛案は未実測のため不採用。"
  open: "K2〜K10 未達。実削除（K5/K6）は未実測。dry-run 実行中にフォルダ実数が 95→93、削除候補が 2→0 に変動したが、削除主体は未特定（別セッション または ops/launchd/jp.salesanchor.reaper-onlogin.plist の自動起動が候補）。凍結前提が実際には成立していなかった（測定中に origin/main が 9a7f2995 から 058388cf へ前進）。"

## 2026-07-24: lessons-guard 範囲限定化の本番実証 訓練F/G/H（EV-20260724-001）

  reference: "PR #3068（訓練F・CLOSED / mergedAt=null）／ PR #3070（訓練G・CLOSED / mergedAt=null）／ 教訓ポスト PR #3072 mergeCommit=89710660aa893dfd9e24e030af4278aee1dc51f4"
  scope: "本番PRによる動作実証のみ。正本 docs/ai-agents/design-partner.md への恒久変更ゼロ（ダミー行入りPR 2本は未マージでクローズ）。恒久追加は docs/ai-agents/lessons.d/20260724-guard-drill-verification.md（19行）のみ。"
  problem: "範囲限定 #3060（検知を §6開始行〜§7開始行の手前に限定）は手元検証5試験のみで、本番での動作が未実証だった。"
  fix: "対照実験3本を本番PRで実施。F=§6-5 に箇条書き1行 ／ G=§7 に箇条書き1行 ／ H=F のPRに lessons-cleanup ラベル付与。"
  kgi: "F合格: SEC6_START=173 / SEC7_START=329 / SEC6_ADDED=1、warn-direct-lesson-edit=FAILURE、gh pr merge が 'the base branch policy prohibits the merge' で拒否（run 30039245397）。G合格: SEC6_ADDED=0、conclusion=SUCCESS、mergeStateStatus=UNSTABLE（run 30042043713）。H合格: SEC6_ADDED=1 を保ったまま conclusion=SUCCESS、ログに '✅ Lessons Guard: lessons-cleanup ラベルを確認'（新run 30042870942・旧run 30039245397 と別番号を実測）。"
  note: "F と G は process-artifacts gate が赤という条件まで同一で、差はダミー行の位置のみ。ruleset id=15777895 の必須チェック12件に warn-direct-lesson-edit は含まれ process-artifacts gate は含まれないため、マージ拒否はガード単独の効果と確定。PR #3072 の mergedAt=2026-07-23T22:10:30Z は UTC 表記で JST では 2026-07-24 07:10。"
  open: "訓練ブランチ3本のリモート削除は git push origin --delete が手元検問（worktree外／マージ済みブランチ）に拒否され、PO許可のうえ gh api -X DELETE で実施。台帳 .claude-pipeline/active-work.d/ の release-lg-scope-drill-f・-g・release-lessons-drill-fgh は origin/main に未コミットで本店の作業ツリーにのみ存在し、消し込み未実施。範囲限定の恒久維持を機械で保証する仕組みは未設計（本実証は一度きりの人手確認）。"

## 2026-07-28: 作業台滞留の真因と reaper 対策の適用時点（EV-20260728-001）

  reference: "定期run 30216232301（2026-07-26T19:08:45Z・conclusion=success）／対策コミット 9e462249／main合流 d87be6f2（2026-07-26T22:13:16+09:00）／検証時 origin/main=693d654da80d864ec79cfe0681dc78ba8b53f926"
  scope: "reaper 自動掃除テーマの現状把握のみ。コード・ワークフローへの変更ゼロ。読み取り実測のみ。"
  problem: "作業台が95個前後で減らない。原因が片付け忘れか機械側かが未確定だった。"
  fix: "本エントリは実測記録であり変更なし。真因は台帳（.claude-pipeline/）の未コミット差分により reaper のチェック2（未保存保護・scripts/reaper-worktree.sh:154-157）が発動し続けること。対策 9e462249 は main に合流済み（merge-base --is-ancestor 9e462249 693d654d = exit 0）。"
  kgi: "2026-07-27 04:08 JST の定期run 30216232301 は旧 main 1d9ae8cc で実行され、merge-base --is-ancestor 9e462249 1d9ae8cc = exit 1 のため対策未適用だった。同runの内訳は 対象88件／IN_PROGRESS・未マージ23件／未保存50件／未マージ12件／削除対象3件で、実削除は0件（3件とも『既に存在しないか登録解除済み』）。"
  note: "本店 /Users/tanizawashingo/salesanchor の作業コピーは HEAD=d9a73243・origin/main=693d654d で434コミット遅れ、未保存23件。手元 scripts/reaper-worktree.sh は claude-pipeline 出現2件（main版は5件）で対策未反映。ゆえに手元 dry-run は旧版を実行し未保存50件・削除対象0件となった。定期実行は actions/checkout で毎回 origin/main を取り直すため本店の遅れの影響を受けない（run 30216232301 のログに e7a53a24..1d9ae8cc を実測）。"
  open: "①対策適用後の実削除件数は未実測。②台帳を除外した独自集計は both=2／dirty_only=7／unpushed_only=21／clean=57（87 worktree中）だが、reaper の未push判定3経路（scripts/reaper-worktree.sh:147-183）のうち1経路のみで測った値であり reaper と同一物差しではない。③数の三者不一致: git worktree list=97／実フォルダ=94／reaper走査=87＋異物3。K2・K3 未実装の実害。④scripts/dev/executor-preflight.sh:70 は 2>/dev/null || true で失敗理由を破棄し、通信失敗と main 消失を区別せず同一メッセージを出す。疎通検査は api.github.com（25行）、main 存在確認は origin URL の github.com（70行）で宛先が異なる。⑤.claude-pipeline/active-work.md:23 の release/reaper-concurrency-design は IN_PROGRESS だが PR #3066 が 2026-07-23T05:51:08Z に MERGED 済みの残骸。"


```text
id: EV-20260910-LINE-ACCURACY-03
date: 2026-09-10
agent: Codex (design partner)
task: LINE商品取り違えの要因分析
scope: 過去保存20誤商品、固定SHAコード、旧マスタ＋9/8変更値のメモリ再現
evidence:
  - type: file
    reference: docs/handoff/tcg-product-master-growth/recon.md §2026-09-10要因分析
    summary: 区分ID実在、除外入力は商品名のみ、exSARとSARの境界不一致を確認
  - type: command
    reference: /private/tmp/line-factor-analysis-20260910.py / /private/tmp/line-single-filters-20260910.json
    summary: 再現18誤判定中13行は除外語なし。単品11行のSAR/AR/PSA10除外は名のみ1行、仮の名＋状態7行で一致
confidence: medium
tradeoff: 備考の封入説明や否定まで単純除外すると正しいBOXを失う可能性。最新本番と正例で未検証
decision: 区分別共通除外と同一商品行の状態・備考の参照を設計方向の草案に記録。設計合格・PO承認・実装GOではない
follow_up: 現本番マスタ区分と正常BOX実例で誤一致防止・取りこぼしを対に検証
```


```text
id: EV-20260910-LINE-ACCURACY-04
date: 2026-09-10
agent: Codex (Planner then Architect, self-review)
task: 作品抽出・通常版コロ除外の実装準備
scope: 設計文書のみ
evidence:
  - type: file
    reference: docs/handoff/tcg-product-master-growth/design-keyword.md §9
    summary: PO実装依頼受領、作品seedのIP001/IP002/IP006と抽出・保存契約を確認。設計草案とREVISE判定
  - type: command
    reference: /private/tmp/line-coro-exclusion-20260910.json
    summary: 現行関数にコロ除外を追加した局所検算4件。通常名1件維持、限定2種と曖昧名1件を除外
confidence: medium
tradeoff: 現本番マスタ未取得。抽出保存契約と既存ADRの整合確定が必要
decision: 未解決前提を残すため実装カード未発行。製品実装未着手
follow_up: 契約確定、最新マスタ確認、設計整合検査と正式カードチェック
```


```text
id: EV-20260910-LINE-ACCURACY-05
date: 2026-09-10
agent: Codex (design partner)
task: GO受領後の作品抽出契約具体化
scope: 設計文書のみ
evidence:
  - type: file
    reference: docs/handoff/tcg-product-master-growth/design-keyword.md §GO受領後の契約具体化
    summary: 作品9列・保存2カラム・旧7列互換・作品証拠・型番語・訂正保護の境界を具体化。PO発話GOを原文のまま記録
  - type: file
    reference: backend/app/tasks/tcg_extraction.py:163 / backend/app/services/tcg_analyzer_svc.py:1080
    summary: 保存経路と既存判定の上書きを確認。新規行と既存一括再解析を分離
confidence: medium
tradeoff: 現本番マスタの読み取り経路が未提供。migrationの新規TCG経路とADR整合の審査が残る
decision: 実装GO受領済み、設計REVISE継続、カード未発行、製品未変更
follow_up: 最新マスタの読み取り先確認、適用経路の設計、正式カードチェック
```


```text
id: EV-20260910-LINE-ACCURACY-06
date: 2026-09-10
agent: Codex (Planner → Architect self-review)
task: 本番DBの作品・商品照合と実装準備
scope: tenant_004 read-only SELECT、設計・ADR追加案・カードのみ
evidence:
  - type: command
    reference: /private/tmp/line-current-master-20260910.json / /private/tmp/line-current-counts-20260910.json
    summary: transaction_read_only=on。296商品、有効293のwork_id NULL0、11作品、2区分。ガンダム誤判定29中有効原文4、コロちゃお誤判定4中有効0、コロコロ未解決21中有効1
  - type: command
    reference: /private/tmp/line-current-candidate-probes-20260910.json
    summary: 既知のガンダム作品で絞ると29行相当のPM0123誤一致を防止。備考のみ限定版1行も除外入力拡張でNONE。Gemini実測ではない
  - type: file
    reference: docs/handoff/tcg-product-master-growth/design-keyword.md §10
    summary: 実装契約の自己審査APPROVE。文書承認と本番反映は別工程。未登録コロコロ版は自動新規登録しない
  - type: command
    reference: bash scripts/card-lint.sh docs/handoff/tcg-product-master-growth/card-work-matching-v3.md
    summary: exit0、L24長文の非ブロッキング警告7件。task-stateとdiffチェックも成功
confidence: high
tradeoff: 保存行全体と有効原文を区別。GAS一致と正解一致を区別。モデル実測と製品実装・統合試験は未実施
decision: 最新DB未確認の障害は解消。設計・ADR追加案・カードを文書レビューへ出す
follow_up: 文書PR承認後にカードを実装役へ渡す。サブエージェントは起動していない
```

- EV-20260910-GO-FLOW-SCOPE:
  app_form_recon: "実登録画面の項目/権限を読取照合。PEM端末ダウンロードと端末保存禁止案の不整合を発見、鍵発行停止。マージ/デプロイ依頼はGOフロー/L1の対象回答待ち。両head branchのPR検索0件。設計REVISE、外部変更なし。証拠 /tmp/reports/TH-GO-NEXT-SCOPE-RESULT.txt。"
  sandbox_created: "https://github.com/shingo-ops/salesanchor-go-gate-sandbox を承認範囲でブラウザ作成。repo_id 1363676622、Public/main/README.mdのみをshingo-ccのGETで照合。初期HEAD a815d94c535f59fae6415b881296d64ef17bf6c7。App/鍵/設定変更なし、全体REVISE。証拠 /tmp/reports/TH-GO-SANDBOX-CREATED-VERIFY.json。"
  browser_connection: "POの接続/作成依頼に従い利用可能なPlaywright接続でGitHub /new を開き、ログイン画面への遷移を実測。接続成功・POログイン待ち。repo未作成、資格情報読出しなし。証拠 /tmp/reports/TH-GO-BROWSER-CONNECT-RESULT.json。"
  sandbox_creation_approval: "PO原文『進める』を初期READMEのみの公開repo1件作成承認としてREADMEへ記録。Browser必須操作ツール0件、PO画面からの作成未実施。承認不足ではない。資格切替/PO資格のCLI書込み使用なし。報告 /tmp/reports/TH-GO-SANDBOX-CREATE-RESULT.txt。"
  preparation_card: "検証入出力・8失敗注入位置・試験PR10本/成功merge上限7本を具体化。repo初期作成手順/読取カードの限定自己審査APPROVE、全体REVISE。card-lint exit0/構文PASS、4JSON記録を実測。repo/main GET404、空きは未確認、外部作成0件。証拠 /tmp/reports/TH-GO-PREP-CARD-RESULT.txt。"
  validation_plan: "専用repo/App/4保護ルール・権限上限・費用条件・13試験群・担当/停止条件をdesign.mdに保存。GitHub統合試験合格0件、外部作成0件。計画/全体REVISE、検証コード仕様と正式カードは未完了。参照 /tmp/reports/TH-GO-VALIDATION-PLAN-RESULT.txt。"
  revision3: "PR #3394 MERGEDをAPI確認。GO確定JSON・保存先・保存失敗時送信禁止・結果不明時再送禁止を草案化。POの一時認証読取GO後にmain Ruleset例外0件・旧Branch Protectionなしを実測し、例外の不明は解消。通常認証shingo-ccを維持。再実行8状態・保守5項目を追補2に整理。コミット追加時はmain取り込みのみでも再GO、へのPO原文『進める』をREADMEに記録。後続PO原文『GO』で専用App方式とPO管理責任を採択。App作成/設定変更は別承認、実装未着手。状態branch案を追加しローカルGitの競合拒否等6/6確認（GitHub実機ではない）。設計自己審査REVISE。参照: design.md改訂3追補/recon.md調査記録。"
  revision2: "PR #3388 MERGEDをAPI確認。基点87e5748b。専用jobはBranch main限定Environment+App候補。本文の原子的照合はmerge APIにないためGO確定境界A/Bを提案。その後PO原文『合意』によりAの取消期限のみ採択、逐語記録はREADME。App運用や再GO等の方式全体は未採択。自己審査REVISE。詳細はdesign.md改訂2/recon.md追加調査。文書PR https://github.com/shingo-ops/salesanchor/pull/3394 はOPEN/readyで提出、マージ未実施。"
  theme: "GO記録転記・マージ前検査（既存テーマ延長）"
  evidence: "docs/handoff/go-record-transcription/README.md / recon.md / design.md"
  observed: "2026-09-10 PO返答『合意』はGitHub画面・直接CLIのマージ制限まで含む設計範囲への合意。main=60132b058ba52f24afdb50d683a216d88f5fdd59。Rulesetの必須12チェックにprocess-artifacts gateなし。既存GO validatorの純粋関数試験5/5 PASS。"
  publication: "文書公開・PR提出へのPO GOを受領。https://github.com/shingo-ops/salesanchor/pull/3388 をOPEN/ready、base=main、head=release/go-flow-designで確認。マージ未実施。"
  open: "方式は自己審査REVISE。bypass_actorsは現在の権限では非表示。本文競合・専用主体・適用境界は未確定。実装・Ruleset・secrets変更は未承認。文書PRのGO #3388は受領済み、マージ成立は確認前。"

- EV-20260910-PMG-IMPORT-SSOT:
  theme: "インポート・解析・配信の統合 第1段階"
  evidence: "docs/handoff/pmg-import-delivery-ssot/recon.md / docs/handoff/pmg-import-delivery-ssot/design.md / backend/tests/test_tcg_import_progress_pg.py"
  observed: "base=8206ba2844921c1efb3ca4fd647230e76bb0c5c6。仕入元・実際の投稿日時・本文一致のみ再利用する方針にPOが合意。ローカルPostgreSQL 16の専用テストDBで検証。本番実測は引き継ぎ資料によるもので本セッションでは未実施。"
  open: "新PRのマージ・本番適用・実配信は未承認。UI・配信履歴・解析attemptは後続便。最終テスト結果とPR状態はテーマdesign.md参照。"


文書提出の追記（EV-20260910-LINE-ACCURACY-06）:
- PR: https://github.com/shingo-ops/salesanchor/pull/3387 — OPEN、main向け、head=release/line-analysis-accuracy-reconを `gh pr view` で確認。
- 文書7件のみの差分。設計とADR追加案は文書レビュー中。実装役未起動、製品実装・本番DB更新・本番反映なし。
- process-artifactsのローカル検算は合格。初回はローカル証跡パスの表記とADR参照不足を検出し修正した。card-lint exit0（非停止のL24警告7件）、task-state、diffチェックも成功。
- main更新3コミットは文書作業ブランチへ通常のmergeで取り込み、競合した台帳・索引は双方を保存。rebaseはガードで拒否されたため実施せず、許可の自己発行も行っていない。
- GitHub CIは提出時点で実行中。ローカル合格をGitHub CI全通過に読み替えない。


```text
id: EV-20260910-LINE-ACCURACY-07
date: 2026-09-10
agent: Codex (design partner)
task: 実装カードのCI検証経路補正
scope: カード・台帳のみ。製品の仕様と試験基準は維持
evidence:
  - type: command
    reference: 実装役 /root/implement_line_work_matching の停止報告
    summary: preflight成功、worktree release/line-work-matching-v3作成、Docker不存在exit127、製品変更0で停止
  - type: file
    reference: .github/workflows/test.yml:123 / .github/workflows/test.yml:224 / backend/pyproject.toml:54
    summary: 既存CIはPostgreSQL16とRLS_ADMIN_DATABASE_URLを用意してtests全件を実行。設計§10.3でCI経路は許可済み
confidence: high
tradeoff: ローカルpytestは未実施と明示し、CIで実統合試験が実行された証拠を必須にする。Gemini実測不可は本番反映の未完了条件として保持
decision: 一律停止のカード不備を修正し、実装・ローカル静的検査・ready PR・既存CIの順で再開可能とする。追加の実装GOは不要
follow_up: 実装役が再開し、新規統合試験の実行成功と実測未了の区別を報告する
```


## EV-20260910-LINE-ACCURACY-08

- 対象: CARD-LINE-WORK-MATCHING-V3-01の実装・検証準備（Generator）。
- 基点: 6e1335725bb8dfdf390125c4caf5a93f705f4821。設計PR #3387のMERGEDとmergeCommitをghで再確認。
- 実装: v3厳格9列と旧7列パーサ、作品原文2列保存、同一明細の作品根拠検証、作品ID候補制約、作品不明時の型番だけの確定拒否、商品名・状態・備考を独立に除外確認、商品訂正記録のある行スキップ。未一致basisは既存UI互換のNONEを維持。
- migration: 2本を正規runner末尾へ追加。構造は追加専用、PM0200は名称とIP001の検算後にコロを追加、商品登録・再解析は含まない。
- 実行: Python3.12でmake lint-ci exit0（ruff PASS、Bandit High0、mypy警告運用）。初回Python3.14のBandit内部例外はPASSに含めない。task-state PASS、card-lint exit0（長文警告あり）、git diff --check PASS、6 Pythonファイルの構文解析PASS。ローカルpytest未実行。
- PostgreSQL: CIの使い捨てサービス内に試験ごとのDBを作る統合試験を追加。まだ実行前でありPASSとはしない。GITHUB_ACTIONS、localhost、jarvis_test_dbを必須条件とする。
- 安全: テストDB削除命令を含むファイル作成がガード拒否。削除命令を除去し、CIサービス終了に廃棄を委ねる。ガード解除・本番接続なし。
- Gemini: GEMINI_API_KEYの設定有無のみ確認しFalse。6匿名メッセージ・8期待明細をテスト内に準備。live形式失敗／正答／不明／誤分類はすべて未計測。モデル精度改善を実測済みとは扱わない。
- 次: ready PRと既存CI。設計PRのGOを新しい実装PR番号のGOへ流用せず、本番前実測とマージ承認を残条件として区別する。

- PR提出: https://github.com/shingo-ops/salesanchor/pull/3393 （OPEN、ready、初回HEAD 13fae233250d49c434c673450e60772d026293b7）。2026-09-10 01:28 UTC提出。push由来のtask-state/active-work checksは成功、Backend Testsは確認待ち。
- 設計パートナーの読み取り検算報告（Generatorの実DB試験とは別）: 最新有効マスタへ正しいガンダムUUIDを入力した29保存行相当は異作品確定0、未解決29。PM0200コロ追加後、コロちゃお商品名3保存行はPM0285、備考のみ1行は未解決、通常名1件はPM0200。AST抽出関数による局所検算であり、Gemini実測・DBmigration実行結果ではない。

### 2026-09-10 実装受入の実測結果

- PR: https://github.com/shingo-ops/salesanchor/pull/3393 。実装マージ・本番DB更新・既存一括再解析・配信は未実施。
- PostgreSQLと既存回帰: HEAD 6a0de8e39db70fcd523941143d444e099d511fb6、Backend Tests run34425902051 / job102710979427で2424 passed、93 skipped、302 warnings、64.61秒。新規統合6テストはskipなし、CI・ローカル接続先制約をassertし、試験ごとの使い捨てDBで正規SQLを実行した。
- 実DB受入: 作品を付けた過去29保存行相当で異作品確定0・未解決29、作品なし型番29入力で確定0。通常名1→PM0200、コロちゃお名3→PM0285、備考のみ1→NONE/要確認。限定版2種・曖昧コロは通常確定0。ワンピースEB01正常対照→PM0123。商品訂正3項目の再解析・後処理後の変更0。配信候補取得で未解決が除かれることを確認（送信なし）。
- migration: 既存TCG表・表なし・将来作成後・再実行、nullable TEXT2列、PM0200既存5語保持＋コロ1語、名前/作品不一致時の例外停止を実PostgreSQLで検証。テストに定義を手書きした非必須ケースはスキーマ複製検査に拒否され除去し、正規migrationによる必須検証を維持した。
- Gemini実測1: HEAD ff8098eec27dbcdadb60d2d4a02b15e462b2cf42 / run34426151237 / job102711720864。2425 passedだがxdistで集計stdoutを取得できず、正答数の証拠に採用しない。artifact0件。
- Gemini実測2: HEAD 6b489af4d6fbc05f600eacce35bf07a1d849f7bf / run34426443315 / job102712624432。UserWarning集計のstatus=measuredを確認。6匿名メッセージ・期待8明細・抽出8明細、作品特定正答7＋作品不明保持正答1。形式失敗0・API失敗0・欠落0・過剰0・未知化0・誤分類0。既存停止スイッチ・mockキー除外を尊重。最大12メッセージのAPI呼び出し可能性を記録し、初回を正答母数へ合算しない。
- 実測2の生集計: `{"api_failures":0,"correct":8,"excess_items":0,"expected_items":8,"expected_unknown_correct":1,"format_failures":0,"messages":6,"missing_items":0,"observed_items":8,"status":"measured","unknown":0,"wrong":0}`。一般のLINE全件の正答率を示す標本ではない。
- 一時計測の除去SHA: b2700dd0dd04f3ad0e5733d902f3d6980bc8e2ec。匿名標本と単体モックは保持し、今回追加したlive呼び出しを最終ツリーから除去。CI・secrets変更なし。
- 設計パートナー（root）の読み取り確認: v3空出力のヘッダー不足、NONEの既存UI互換、旧7列正常fixtureの指摘修正を確認し、製品差分に追加の阻害所見なし。上記CI生集計もrootがGitHubから直接確認。これは実装差分の読み取り確認であり、同一AIによる設計自己審査を独立した設計第二者レビューとは称さない。
- 最終残条件: 一時計測除去後の最終CIを確認する。process-artifactsは新PR固有のPO GO未受領により失敗（GO記録なし）。設計PR #3387のGOを流用せず、本PRのGOとマージ・本番反映は別判断として待つ。


### 2026-09-10 PR #3393のGO受領

- PO原文: 「GO #3393」。本セッションで受領し、PR本文のGO記録4欄へ原文どおり転記。発話の時分は未取得のため創作しない。
- 対象HEAD: 348d0a6bf6fc906f9866ec8bf36e96a8419e8645。GitHubでOPENを確認。既存の検証記録と本文を保持した。
- バックアップ: docs/B-09_restore_test_procedure.md Step 1の一覧をSSHで要求したが、2026-09-10 11:05 JSTの監視情報だけが返った。バックアップの実在・時刻・整合性は未確認。接続制限の解除や迂回なし。
- 承認受領とバックアップ確認・マージ・本番反映を区別する。承認の再取得は不要。バックアップ未確認と最新main再確認が残条件。本ターンの製品変更・DB更新・マージなし。

### マージ前の適用順不整合を検出（2026-09-10）

PO原文「マージ」を受領。最新main取り込みは文書7件のみで競合なし、製品差分不変。HEAD ceb0d73fをpushし再検査中に、deploy.yml:335のworker起動が:458のSQL適用より先と実物確認。本設計§10.2の順序と不整合のため、マージ前に停止した。先の実装レビューの確認不足として記録する。補正と自己審査は設計§10.2.1、実装役への指示は既存カード末尾。元PRのGO/マージ依頼を取消扱いにせず、先行PRの固有GOを流用・創作しない。新たな製品仕様・本番直接操作・CI変更はない。

### DB先行PR #3398の提出と検証（2026-09-10）

- PR: https://github.com/shingo-ops/salesanchor/pull/3398 、HEAD 8ef86fd09cbd7407c791d9ee6db1cfce9541c604。差分3ファイル54追加・削除0。rootも2SQLのsource ceb0d73fとの逐語一致を検算した。
- SHA256: 構造SQL afdfbf530d075b1beba5d9d91cc2110da1588e94120d8342a041f479a6b72b28、辞書SQL 458857fd40b5dfefd07a0a4b602197f0215ae5a24cf88d582c54bc51deb1c149。
- 先行PR固有CI: Backend job102721200901で2374 passed/93 skipped/82.33秒。migration run34429300255のSQL実DB実行・全件ドライランも成功。rootはGitHubの実出力を確認した。失敗は先行PR固有GO記録欠落（job102721175226）のみ。
- バックアップ参考: 既存deploy run34427083170/job102714500644で2026-09-10 10:51:19 JST salesanchor_db_20260910_105115.sql.gz(4.5M)生成成功を確認。今回反映直前の取得・実物/復元検証とは区別する。先行PRの自動反映もDB変更前に既存のバックアップ工程を実行する。
- 停止位置: 先行PR固有のGO受領前。#3393のGOとマージ依頼は保持し、再取得しない。新規PRへ承認を流用せず、#3398の適用完了確認後に #3393を進める。どちらも本ターン未マージ。

### DB先行反映完了（2026-09-10）

- PO原文「GO #3398」を本セッションで受領（発話の時分は未取得）。公式merge wrapperで #3398 を2026-09-10T02:38:46Zにマージ。merge SHA 760532a9a57c4661672468e26beed8d071b6f6d4。
- 本番自動反映 run34430261411 / job102724106081 は success。rootがGitHub APIとログを直接確認。11:39:26 JSTに salesanchor_db_20260910_113923.sql.gz（4.5M）生成成功。復元試験は未実施。
- 同ログの [222/223] 20260910_160000_tcg_work_evidence.sql と [223/223] 20260910_160100_tcg_normal_deck_coro_exclusion.sql はともに DO、Migrations done（02:41:55Z）。スモーク・最終確認を含むdeploy全体が成功。
- #3393 はこのmainを競合なく取り込み、差分は実装・試験・文書11ファイル。DB先行条件を満たしたため、既存の「GO #3393」「マージ」に基づいて最新HEADの全CI確認後にマージする。既存結果の一括修復・再解析は行わない。

### 新方式の本番保存結果監査（2026-09-10）

POの「進める」に基づきread_only=onのDB接続で確認。固定標本19原文398明細はすべてv3、確定266・未確定132。原文・マスタ・保存根拠に基づく別商品確定を少なくとも5行確認（BASE SHOP系3、151シングル1、複数デッキセット1）。手元の辞書案では5行の誤確定0、うち正しい既存商品3・未確定2。全体正答率や正式設計合格とはしない。詳細・ID・SHA256・未確認はrecon.md「新方式の本番保存結果・初回監査」。追加実装・DB修正・再解析起動は未実施。

### 辞書案の対照検証・自己審査（2026-09-10）

read-onlyでv3全745明細、正規化・単位・区分マスタを取得。反映SHA864ace72の商品判定再現は保存結果との不一致0。初案の検索追加はVol.10/11誤一致を検出しREVISE。3操作限定案は10誤商品→NONE、735明細と正式名称293件の判定不変、合成16/16期待どおり。設計§11の自己審査APPROVE、独立レビュー・PO承認ではない。正式カード・追加実装・本番変更未実施。recon末尾とdesign-keyword.md §11に範囲・受入・停止条件を保存。

### POの実装・本番反映・継続改善承認（2026-09-10）

PO原文「承認する、修正から」「本番反映まで実施してくれ、」を受領。さらに「離席するのでPRマージも事前に承認する、反映後は再解析を行い解析が完了したらスプレッドシートを更新するために配信をする、シートは3シート接続しているが全シートに配信、PDCAを回してほしいので現在の解析精度を向上するためにループで回してほしい、1回のループでの成果を最大化したいのでなるべく検出件数は誤りの沖ない範囲で検出して修正ループを回すこと、合意できるか？」を受領。時分は未取得。3操作修正のマージ・本番反映、完了後の再解析と接続3シートすべてへの配信、原文に基づく改善ループを承認された。旧GO番号の流用・PO文言創作なし。

実施条件: 各周で広く原文・保存結果・マスタを比較し、証拠の揃う修正をまとめて設計・自己審査・実装担当検証後に反映。新商品定義など事業判断が必要な項目は保留し、手動訂正を保持する。再解析完了前に配信しない。実在する接続3シートの宛先・既存配信手順・更新範囲を読み取り確認してから実行する。新規接続先や未知の送信は含まない。実行記録と承認記録は区別する。現時点で新3操作の本番反映・再解析・配信は未実施。


### PR #3400検証と停止位置（2026-09-10）

Backend run34432985860/job102732312951で2459 passed/93 skipped/coverage61.51%、rootが直接確認。SQL/回帰・実DBmigration技術CI成功。read-onlyレビューで3操作と単一トランザクション・timeout・全件原状保持検証を確認。process-artifacts job102732666119だけが番号付きGO原文を要求し拒否。包括的承認は受領済みだがPO原文を創作せず、当該PRのマージ前に停止。新しい状態調査依頼・接続3件・active1386明細・追加商品誤判定15行・開封済み→Sealed box1行・残存running2jobはrecon末尾に根拠付きで保存。再解析・配信は未実施。

### #3400反映・再解析実行と配信停止（2026-09-10）

PO原文「GO #3400」を受領・PR本文へ転記。公式マージ済み（07:24:27Z、d21599c72126dc450a70b7aad2a86b2ef3a412a3）。deploy34449800503/job102782709121成功、反映前DBバックアップ4.7M、今回SQL実行、SA-19 smoke、VPSの同SHA・health200をrootが直接確認。本番辞書は検索1減/除外2増、他の語・順序不変。既存migrationの49UUID再発行を今回単体の保持試験とは区別してreconへ記録。

既存再解析経路で有効原文のdone79job/1425明細を実行、79run完了・1425snapshot・明細ID追加欠落0。設計標本10誤一致は全件NONEへ。別途、旧v2の77行で商品コード変化（型番根拠71行とvol.1の1行がNONE、候補変化5行）。自動確定1011→937は正答率ではない。状態変更0。原文・比較結果はローカル退避、詳細recon末尾。

全3接続のrun_distributionは07:32:05Zに安全装置#8bで書込み前停止、running2件、results=[]。配信未完了。PO追加指示「↳ 不明点は推測で進めることを禁止するので停止して質問してくれ」を受け、不明な終了原因や復旧扱いを創作しない。2件を中断記録し有効1件のみ再実行する復旧案はPO確認待ち、未実装。資料: recon末尾、line-reanalysis-verification.json、line-distribution-attempt.json（/private/tmp）。

### 中断2件復旧案の承認・設計（2026-09-10）

前節の復旧方針にPO原文「進める」、追加原文「› › 次に進む、また離席するのでPRマージとデプロイまで進めてくれ」を受領。07:38:28Zに2件の状態・source対応・items0・有効性を再照合。design-keyword §12に対象固定、事前検証、2件のみerror記録、再投入は有効1件のみ、既存配信停止条件の維持を設計。Architect自己審査APPROVE（同一AI）、実装・機能試験未了。正式card-interrupted-jobs-recovery.mdをcard-lint成功（L24警告のみ）、task-state/diff検査成功の上、既存実装担当1名へ引き継ぐ。追加エージェントなし。

### 中断復旧#3403の実装検証と番号原文待ち（2026-09-10）

HEAD be4bf045a1c5dabc62cfaa5a125b4590e66fb432、Backend run34451813934/job102789066448の実ログで2499 passed/93 skipped/coverage61.60%、新32ケースskipなし。migration run34451813639等の技術CI成功、rootの差分読み取りも追加指摘なし。process-artifacts job102789028541のみ番号付きGO原文を要求して失敗。受領済み原文・事前承認はPRへ保存し、番号は創作せず停止。#3400は反映済みだが、本復旧#3403は未マージ・未反映。

並行調査: 全3シートの674行/12列が完全一致、値と式を退避済み。全1425行の現状再現不一致0、PSA除外2語の案は15誤一致のみNONE、他1410不変・正式名称293件変化0・36対照成功。状態候補5件のうち3件は備考参照の局所比較で既存損傷/開封条件へ変化、2件の伝票/テープ跡の定義は未確認。詳細recon末尾、変更案の本番反映なし。

### #3403復旧後の配信前実測（2026-09-10）

rootが#3403 MERGED/deploy成功、既存retryで有効1jobだけenqueue1、18明細/18解析done・未完了jobs/runs0を直接確認。3接続各674行を値/数式退避、接続ID全件一致。配信予定445行中、今回の18明細にPM0268未サーチ→Searched packとPM0141伝票剥がし跡の備考欠落を検出。前者は実条件CN0007と純関数対照でUnsearched packを確認、後者の分類はPO回答待ち。状態/備考の既存訂正サービスは配信元更新に未対応。配信未実施。詳細と直接検証/他者読取の区別はrecon.md末尾。

## EV-20260910-WORKTREE-PRESERVE

- 対象: 作成時の既存作業場所保持指定の設計草案。
- 根拠: docs/handoff/branch-operations/recon.md / design.md の2026-09-10節。
- base: 6e1335725bb8dfdf390125c4caf5a93f705f4821。
- 文書保存限定の例外として専用worktreeを直接作成。UUID発行・分割台帳登録・既存の開始/所有検査がexit0。回収処理なし。
- 設計自己審査: APPROVE（同一AI）。正式仕様承認・実装担当の作業場所・正式カード検査は未了。製品・運用スクリプト・CIは変更なし。
- 未実施: 保持指定の機能試験、実装、マージ、本番操作。
- 文書検証: git diff --check / bash scripts/check-task-state.sh はexit0。変更は設計・調査・台帳・根拠登録の4ファイル。実装の機能試験ではない。
- 文書提出: https://github.com/shingo-ops/salesanchor/pull/3390 （Draft、base=main、head=release/worktree-preserve-design）。公式register-pr.shで番号登録成功。ローカルprocess-artifacts gateも実diffとPR草案本文を使用してexit0。GitHub CIは別途確認する。

## EV-20260910-GUARDS-DOC — guards文書と実装の対応整理

- 日付: 2026-09-10。実測基点: 6e1335725bb8dfdf390125c4caf5a93f705f4821。
- 依頼1〜3: 作成便と移動便の分離を04-worktree.mdへ記録。元の逸脱はPO引き継ぎであり、本便の実測と区別した。
- scripts/card-lint.sh:169-177のL24（警告のみ）・L25に文書を対応させ、L26同内容2行を1行に整理。
- 同スクリプトにL32の機械実装はない。L32行・L02補足・冒頭説明を人手照合と整合させる。L29は変更しない。
- 検算: 文書のL01〜L33が順に各1行、重複・欠番ゼロ。差分は文書と作業記録のみ。実行時の判定式・製品コード・CI・DBに変更なし。
- 自己審査: 文書変更の受入条件に適合。設計担当と審査担当は同一AIであり独立レビューではない。PR #3389で提出。初回HEAD e2c76412のCIは失敗・実行中なし（成功33件・スキップ9件）。pytest等の内部jobは文書変更のためスキップであり、製品テスト実行済みとは扱わない。最終マージ状態はPR #3389のmergedAt/mergeCommitで確認する。
- 未実施: ガード追加の評価ゲート（依頼4）、商品取り込みサービスのスキーマ検査追加（依頼6）、frontend実装、tenant_001試行とtenant_004の44件取り込み。
- 外部事例: 既存スクリプトとの文書照合で判定できる保守変更のため不要。

PR #3390承認記録（2026-09-10）: PO原文「GO #3390」。文書PRのみのマージ承認。製品実装・本番・後続PRの承認ではない。mainのPR #3389による別テーマの追記を保持して競合解消。


## EV-20260910-TCG-SCHEMA-DESIGN

- 基点: 87e5748b1dab5b062f991a263fa6ac692653877d。設計と根拠: docs/handoff/tcg-product-import/design.md §12、recon.md追補。
- 商品サービス全486行・text6呼び出し・修飾7箇所・動的参照4表を確認。既存2対象は維持。
- 設計資料 schema-test-proposal.py.txt をPython 3.12.8で直接検証し7関数成功。製品側pytest実行・テスト反映ではない。正常/否定試験の範囲と限界は設計に明記。
- 同一AI自己審査APPROVE（限定した静的検査）。PO発話や個別GOは創作しない。実装カード未発行・製品コード未変更。
- 依頼4の評価ゲートは別設計。GOフロー設計PR #3388も自己審査REVISEであり、mainの既存process-artifacts全体を必須化する安全性が確定したとは扱わない。

- 文書提出: https://github.com/shingo-ops/salesanchor/pull/3392。公式wrapperでPR番号登録済み。実装コードは0件。マージ結果はPRのmergedAt/mergeCommitで別途確認する。

## EV-20260910-L1-3404-REGO

POは対象を確認する質問へ「両方とも許可する」と回答。GOフロー修正とL1時刻統一のマージ・デプロイまでを対象として確定した。GOフロー設計全体のREVISE、App鍵受渡し未確定は維持する。

L1は既存実装を確認しPR https://github.com/shingo-ops/salesanchor/pull/3404 を作成。対象はFedEx/SA-02のJST定数参照2ファイル（5行追加・4行削除）。PO原文「GO #3404」をHEAD e4f88d5b7bf2583c43fb3782294a6b61229e9112への承認として受領し、4欄へ転記。必須CI12件とGO転記後process-artifacts gate成功をAPIで確認した。ローカルruff/構文解析/diffチェックは成功。引継ぎのpytest20件成功は他者報告であり、今回のローカル再実行ではない。ローカルBanditはPython3.14の内部エラーがあり全静的検査成功とは扱わない。GitHub上のbackend lint/pytestは成功。

マージ直前にmainがPR #3403で前進しBEHINDとなったため、マージwrapperは実行せず停止。mainを通常取り込み、de9d474aa60886a5c0563a80bd772e89de200517をpushした。差分は同じ2ファイル、5行追加・4行削除。旧GOはPR本文の過去HEAD記録へ移し、現HEADに適用しないと明記した。合意済みの再GO条件に従い、最新CI確認と再GOが必要。L1は実装済み・PR提出済み・旧HEADのみPO承認済み・マージ/本番反映未実施。設計文書はローカル草案であり改訂3のPR未提出。

根拠: /tmp/reports/TH-L1-3404-AFTER-GO.json、TH-L1-3404-MAIN-RULES.json、TH-L1-3404-PRE-MERGE.json、TH-L1-3404-MAIN-ADVANCE.txt、TH-L1-3404-MAIN-SYNC-2.txt、TH-L1-3404-SYNCED.json、TH-L1-3404-PUSH-2.txt、TH-L1-3404-REGO-PENDING-EDIT.txt。マージカードはcard-lintのL31に従い追記出力へ修正後、違反0件（L24警告のみ）。

## EV-20260910-GO-QUEUE-DEFAULT

PO原文「それをデフォルトの設定として実装したい、ガードに追加できる？」を受領。設計保存先 docs/handoff/go-record-transcription/design.md 末尾。preflight成功、基点5386d664、origin/main読取3bdf33d5。既存merge wrapper:93-161はPR単位の追従再試行。origin/mainのguards/12-guard-authoring.mdを読み、実装時の評価契約を確認。自己審査REVISE、ガード本体/CI変更0件。次予約の解放時点をPOへ提示。

## EV-20260910-GO-QUEUE-EVENTS

予約番号とActionsの起動順を分離する設計推論、公式イベント仕様、追加否定試験6件をdocs/handoff/go-record-transcription/design.md末尾へ保存。Context7利用不可・公式資料代替。実機試験0件、自己審査REVISE。L1最新HEAD3e7b28b6の必須CI12/12成功は /tmp/reports/TH-L1-3404-NEXT-CI.json。再GO・マージ未実施。

## EV-20260910-GO-QUEUE-DEPLOY-RELEASE

PO原文「OK」は本番デプロイ成功後の次予約解放への合意。design.md末尾に提示文と原文、DEPLOY_WAIT/DEPLOYED契約、否定/正常6試験を記録。既存deploy.ymlをorigin/mainから読取。全体REVISE・製品/CI未変更。preflight証拠 /tmp/reports/TH-GO-DEPLOY-RELEASE-PREFLIGHT.txt。

## EV-20260910-GO-QUEUE-PRIORITY

POの失敗時返却への「合意」と緊急優先追加依頼をdesign.md現行節へ記録。契約・ガード文案・9試験を具体化、同一AI自己審査REVISE。実装0、外部設定変更0。L1 GO転記済み、main前進でBEHIND。証拠 /tmp/reports/TH-L1-3404-GO2-MSTATE.json。

## EV-20260910-CXASTRAGO-SCOPE

POのcxastrago同条件の委任依頼と、ローカルshell/prompt・PR #3406の草案・既存GO検査の照合をdesign.md末尾へ記録。代理GO未有効、24時間未開始。合成入力2ケースの現状検証は /tmp/reports/TH-CXASTRAGO-VALIDATOR-CHECK.json。役割切替/agent起動/代理GO発行0件。

## EV-20260910-GO-DELEGATION-SCOPE-CONFIRMED

GO制度変更を委任対象へ含むPO意図の確認を受領。原文と現行契約はdocs/handoff/go-record-transcription/design.md冒頭。委任正式有効化/代理GO発行は0件。deploy.ymlの実行時main取得を一次資料で確認し本番SHAの証拠限界を明記。全体自己審査REVISE。


## EV-20260910-PMG-ANALYSIS-RUN

- base: 5d26b70a186479e32e5105ac2e04b92b38eeacec。
- 根拠: docs/handoff/pmg-import-delivery-ssot/recon.md 後続便節（7観点）。
- 成果: 同テーマdesign.mdへ解析履歴・原子的保存・再配達・配信停止の草案を追記。自己審査REVISE。API応答・再試行・heartbeat/tickの配置まで具体化。未決は配信方針のPO判断と稼働接続先/切替確認の2項目。
- PR #3386のMERGEDとmerge SHA 60132b05をGitHubで再確認。画面未完成、本番反映は未確認。
- 今回のPO原文「合意」は削除なしの文書作業場所作成を許可するものとして受領。UUIDと分割台帳を登録し、開始/所有チェックexit0。
- 製品実装、DB変更、実配信、機能試験は未実施。外部事例の改善率は使用しない。

- 文書検証: git diff --check / bash scripts/check-task-state.sh はexit0。製品の故障注入・実DB競合試験は未実施。

- 方針追記: 解析失敗時は同じ解析の再試行が成功するまで全体配信停止。影響説明後のPO原文「進める」を合意として受領。実装/本番GOとは分離。
- 実機確認: 制限付きSSHは監視出力へ置換されDB接続確認は未達。制限解除や人間用鍵へ切替なし。読取診断案はローカル準備済み、未実行。配布順序からmigration先行・追跡未有効配布・排出確認後有効化の分割案を追記。REVISEを維持。

- DB読取診断の後続結果（2026-09-10）: 今回の接続先確認に限る人間用SSH鍵の使用についてPO原文「進める」を受領し、診断exit0。api/worker/beatの診断接続はreadonly=on各3/3、DB識別SHA256一致3/3、tenant_004各3/3、対象4表各4/4。詳細コマンド・出力要約・限界はrecon.md「DB接続先の読取診断結果」。生の認証情報は出力せず、SQLはSHOW/SELECTのみ。
- 現在の残件: 旧実行の排出・切替検査。DB接続設定の一致は確認済みだが既存プロセス接続や全worker個体、配布版、PR #3386本番反映は未確認。REVISE、設計全体承認・実装カード・実装は未着手。

- 文書提出時の停止: 専用worktreeでのgit add/commit要求がPreToolUse hookにより `BLOCKED: create a feature branch before committing.` で拒否。再確認したpwdはrelease-pmg-analysis-run-design作業場所、git statusはrelease/pmg-analysis-run-designで文書4件未ステージ。原因未確定。フックを無効化・迂回していない。文書は保存済み、コミット・PR提出は未実施。git diff --checkとcheck-task-state.shはexit0。

- 文書提出の停止解消: ~/.claude/scripts/worktree-only-guard.shはPWDを既定とし、コマンド先頭cdだけを対象作業場所として解釈する実装だった。先頭cdで専用worktreeを明示して同じフック下でコミット672cf97e成功。フックや権限設定は変更していない。
- 文書提出: https://github.com/shingo-ops/salesanchor/pull/3396 （Draft、base=main、head=release/pmg-analysis-run-design）。register-pr.sh成功、.pr-numberと現行分割台帳へ3396登録。設計REVISEの草案提出であり、実装・マージ・本番GOは未受領。

- 切替設計の更新: deploy.yml:331-335のworker強制削除と共有Celery構成を照合。配布後pausedだけでは初回強制終了を防げないため先行案の保証を撤回し、8段階の検査/停止条件をdesign.mdへ追加。初回一時停止方針は未合意、REVISE維持。本番追加接続・実装なし。PR #3396 HEAD e7da4a85のチェックはpass31/skipping9。

- PO原文「GO」: 初回切替で一時停止を許容する設計方針に対する返答。質問・影響・承認範囲をdesign.mdへ保存。本番停止/実装/PRマージ/追加SSH利用の承認ではない。入口表・初回遮断の制約・6段階の停止/再開案を具体化し、REVISE維持。

- 受付遮断の候補整理: deploy.yml:182-184,360-374の照合から、一時的な追跡設定書換え案を不採択。稼働版/コンテナ/コード指紋だけの読取診断を準備しAST確認成功、本番未実行。ローカルDockerなし（exit127）。追加SSH許可は未受領、REVISE。

- 稼働版/構成読取へのPO原文「許可」を受領し準備済み診断を実行、exit0。Docker29.4.0、3コンテナでCelery5.6.3/Uvicorn0.34.0/SQLAlchemy2.0.38、対象7コード21/21とnginx設定hash一致。recon.md同日結果に記録。ディスク上の対象ファイルの一致であり全プロセス状態/本番反映完了の証明ではない。処理件数・停止・更新・配信は未実施。REVISEの残件を3項目へ整理。

- 切替設計の具体化: ASTでHTTP定義43（GET21/非GET22）を抽出、2ホスト44組を試験仕様化。停止状態をcheckout外に置く案だけではrollback後の遮断維持を保証できないため、停止機構を含む戻し先と初回導入の別審査を必要条件に追加。9つの模擬試験表を保存、未実行。REVISE維持、製品/運用コード変更なし。

- 初回導入案を入口専用7段階へ具体化。API/workerの前後ID不変、通常配布と全体rollbackを呼ばない条件、機構のない版へ戻った際の後続切替禁止を記録。GitHub上の既存Docker試験経路を確認したが本件9試験は未作成/未実行。最新main760532a9を読取照合。REVISE、文書のみ。

- nginx受付判定実測: /tmpの公式nginx1.31.1/PCRE2-10.46をローカルビルドし、架空処理先で151/151成功、exit0。許可なし/あり/取消後の44組とreload/再起動等。ZIP SHA256=e7537c80a7a1b91159ab624e734a493ee992b2f2555aac4d8345fd0bf484fb76。実測範囲と未検証のDocker/TLS/本番処理をdesign/reconへ分離して保存。REVISE維持。製品/運用コード変更なし。

- 復旧試験を9件追加して160/160成功。ZIP SHA256=cb6994733506ebe845244af0f2fc9c182e88adfd556444578a7cb832cadcb973。既存nginx/htpasswd.dの独立サブdirectoryを使う案をcompose/.gitignore/deployと照合し、初回新規mount/再作成を不要にする方向へ改訂。認証ファイル変更・本番接続なし。実機mount/権限とDocker実証は未確認、REVISE。

## EV-20260910-RLS-SCOPE

- 根拠: docs/handoff/rls-bootstrap-txn-fix/recon.md / design.md の2026-09-10追補。
- PR #3397のrun 34429316341で同一failureを2回確認。変更はテスト基盤2ファイルと既存記録4文書に限定。
- 同一AIの設計自己審査APPROVE。実PG検証・PR提出・マージは未実施。POの番号付きGOは創作していない。
- 報告先: /tmp/reports/RLS-SCOPE-PREFLIGHT-20260910.txt、RLS-SCOPE-WORKTREE-01.txt。

- 実装提出: https://github.com/shingo-ops/salesanchor/pull/3399。初回HEAD 8104fd7f。純粋関数正常2例・拒否9例、ruff・書式・台帳検査成功。手元でpytestは未実行。設計のADR-113参照漏れをローカル成果物検査で検出し追補。CI・マージは後続確認。

- CI HEAD 2e4365ad: 2429 passed / 93 skipped / 3 errors（在庫fixtureの旧pokemon code）。テスト1ファイルを対象へ追加し正規pokemon_booster_boxへ照合、空応答防止も追加。設計/recon追補で同一AI自己審査。マージ未実施。

- 最終確認: PR #3399は2026-09-10T03:07:34ZにMERGED、merge 7e3dd6565bc8b239ee09967961326fd096fb72fe。最終HEAD feae3d97、実PGを含む2432 passed / 93 skipped、coverage 61.52%、必須12件成功。worktree回収・台帳DONEを確認。上の未マージ記述はその時点の履歴。

## EV-20260910-TCG-SCHEMA-IMPL

- 設計: PR #3392、docs/handoff/tcg-product-import/design.md §12。recon.md追補を照合。
- 基点: 5386d664f40aa826e7e3d943b87bb65697d49165。TCG-SCHEMA-EDIT-01の正式card-lintと本文確認後に実装。
- 対象: backend/tests/test_tcg_schema_qualification.py。設計資料とSHA-256一致（cb7e8f26eca8cd5e1bb630f6e88b249c411f60fbb41a68949fdbda0e0757c7eb）。
- Python 3.12で7関数の直接実行成功。実ソースの修飾除去7例、動的4表の正常/異常各4例を含む。ruff checkとgit diff --check成功。
- 既存DDL列照合関数を維持。商品サービス・DB・CI・運用スクリプトは変更しない。
- 手元はDockerコマンドなし、Python 3.12にpytest未導入。直接関数実行を正式pytest結果とは扱わない。PRのpytest-run-internalとlint-backend-internalの実行成功が必要。
- ユーザーはこのセッションを実装担当へ切り替え、実装→PR→検証→条件を満たせばマージする確認に「進める」と返答。番号付きGOは創作・転記していない。
- 評価ゲート（依頼4）、商品マスタfrontend、QA試行と44件の本番取り込みは本PR対象外。

- 実装提出: https://github.com/shingo-ops/salesanchor/pull/3397。変更はテスト1件・状態記録3件。公式wrapperで番号登録成功。CIは確認中であり、マージ済みとは扱わない。

- CI停止: 最終HEAD 0c8c643eのrun 34429316341で、test_rls_bootstrap_ordering.pyのtenant_871.leads欠落が初回と再実行で発生。各2377 passed / 1 failed / 93 skipped。同じ実装を含む直前HEAD 780460b2のpytestは成功。差分は文書2件だけ。マージ保留、追加再実行なし。
- 原因の接触面: backend/tests/rls_bootstrap.py:232の全テナントmigrationと、backend/tests/test_tcg_import_progress_pg.py:47のTCG専用一時schema。具体的な並列タイミングは未実測。別件の修正候補は /tmp/reports/TCG-SCHEMA-3397-CI-BLOCKER.md。禁止対象や追加コードには変更していない。

- 別件のDB準備テスト修正をPR #3399へ提出。実DBで判明した在庫fixture旧codeも同PRのテスト内で補正中。現時点で両PRとも未マージ。

- PR #3397へマージ済み#3399を取り込み。商品サービス・設計payloadは変更せず、当該PRの全CIを再確認する。#3397は未マージ。

### PMG解析実行記録の最終保存と承認範囲（2026-09-10）

PO原文「離席するので最後まで進めてくれ、事前にPRマージも承認する」。直前の本件残件調査・文書PR #3396のマージ承認として受領。GO #3396という発話を創作せず、製品実装/本番停止/他PRの承認へ広げない。実機mount/statとプロセスUIDの読取、最新main a0c0eb7fのv3解析/訂正保持を照合して文書へ反映。自己審査REVISE。ローカル160件は成功、Dockerと旧版外部送信の完了照合は未実施。正式実装カードは発行しない。


## EV-20260910-TCG-SCHEMA-MERGED

- PR #3397は2026-09-10T03:14:22ZにMERGED、merge a0c0eb7f36b3d7a6b181d70dc36713ed9a7b7409。
- 最終HEAD a3bc636e、run 34432333829 / pytest job 102730284300: 2436 passed / 93 skipped、coverage61.52%。必須12件成功。手元7関数実行とは分けて確認。
- 商品サービスは変更なし、静的テストは設計payloadとSHA256一致。worktree/ローカルbranch回収・台帳DONEを実在で確認。依頼4は未完了。

## EV-20260910-GUARD-EVAL

- 根拠: docs/handoff/design-partner-card-ops/guard-authoring-recon.md / guard-authoring-design.md。
- 基点a0c0eb7f、試作67/67成功。設置フェーズの同一AI自己審査APPROVE、独立レビューではない。
- 現接続のadmin/maintainはfalse、bypass_actorsは未返却。保護設定は変更していない。GitHubでの実イベント・必須化は未検証。
- 作業場所release/guard-authoring-gate、UUID0452cd58-83fa-4422-9f1c-a538a2cc536c、作成時65件走査・回収0。旧3353台帳は推測で完了化していない。
- /tmp/reports/GUARD-EVAL-PROTOTYPE-04.log、GUARD-EVAL-MAIN-RULESET-BEFORE.json、GUARD-EVAL-WORKTREE-VERIFIED.json。
- この記録は設置PR・マージ・機械強制・POの個別GOを完了扱いにしない。

依頼4の実ファイル配置後検証: 67成功/失敗0/skip0（24.77秒）。証跡 docs/handoff/design-partner-card-ops/guard-evaluations/20260910-install-tests.txt。YAML/設計形式/維持欄/引用先/台帳構造も成功。GitHub CIと実イベント、必須化は未実施。

依頼4の設置PR提出: https://github.com/shingo-ops/salesanchor/pull/3401 。head 3306df2a76368e8ab522cac366b282c824af9cfd、.pr-number一致を直接確認。実Gitの8対象blobと評価JSON照合成功。PR本文ADR表記の不一致を修正し再照合成功。CI確認中・正式GO未受領・未マージ・必須化未実施。

### 依頼4・PR #3401のCI停止（2026-09-10）

- 検証対象head: eb42433b7de5df6bab00fba02e2b15018b5e5fca。新ゲート67成功/0失敗（job102738677559）。
- 全体PG試験job102738726326は2435成功/1失敗/93skip。tests/test_inventory_parser_real_samples.py::test_ac3_2_parse_real_supplier_sample[1]でpublic.suppliers作成時のpg_type_typname_nsp_index重複。ログ: /tmp/reports/GUARD-EVAL-3401-pytest-failure.log。
- 直前head3306df2aの全体PG job102738212532はsuccess。両headとbaseでbackend差分0。断続的な競合が原因候補であり、競合相手と再現条件は未確定。
- 実物: backend/tests/test_inventory_parser_real_samples.py:200 の準備処理はpublic_bootstrap_lockを使っていない。共有ロックはbackend/tests/rls_bootstrap.py:40にある。既存エラーを握り潰さず、同じロックへ参加させる案を別件で検証する。backendファイルは変更していない。
- process-artifacts job102738677035は番号付きGO記録欠落でfailure。PRは未マージ・未必須化。失敗原因未解決のままマージしない。

## EV-20260910-INVENTORY-LOCK

POの追加別PR修正・マージ・デプロイ指示を受領（GO #3401は#3401にのみ転記）。4つの共有DDL経路を既存lockへ参加させる限定修正を自己審査。試作8直接検査成功・修正前4関数拒否。Python3.14、実PG/CIは未実施。設計・調査はdocs/handoff/rls-bootstrap-txn-fix/design.mdとrecon.mdへ追補。実ログ /tmp/reports/INVENTORY-BOOTSTRAP-PROTOTYPE-TESTS-01.txt。

追補（2026-09-10）: PO原文「次に進む、また離席するのでPRマージとデプロイまで進めてくれ」「GO #3401」を受領し#3401本文へ転記。時刻は未提供のため創作していない。追加修正#3402は89ad29ae3a8c3142db36b204e04f48e085803b29で07:46:50Zにマージ。head9a869d8a、実PG job102787311020は2467 passed/93 skipped、coverage61.52%、87.11秒。全CIと必須12成功、worktree回収・台帳DONE。#3401へmain取り込み時の台帳2件の独立追記を両方保持。最終設置CI/デプロイ/実イベント/限定必須化は別途確認する。


```text
id: EV-20260910-FRONTEND-MOLD-01
date: 2026-09-10
agent: Codex (design partner; same-AI self-review)
task: フロントエンド金型化の一次再測定
scope: frontend at 6e1335725bb8dfdf390125c4caf5a93f705f4821; backend/prod excluded
evidence:
  - type: file
    reference: docs/handoff/design-system-recon/recon.md 2026-09-10節
    summary: 117ソースのAST集計。select67/button395/textarea43/table31を別の文字列照合でも検算。違反数ではない
  - type: log
    reference: docs/handoff/design-system-recon/evidence-20260910/checks.json
    summary: 10コマンドexit0、unused-tokensは30候補警告。UI governanceテスト22/22
confidence: high
tradeoff: ソースと指定検査の事実に限定。本番配信SHA・全画面表示・例外全件分類は未確認
decision: 一次測定保存。全体設計REVISE。実装カード発行なし
follow_up: ボタン395箇所を分類し、例外根拠と表示検証を照合する
```


```text
id: EV-20260910-FRONTEND-MOLD-02
date: 2026-09-10
agent: Codex (Planner then same-AI Architect)
task: フロントエンド共通定義の全体設計案
scope: frontend only; observed SHA 6e133572; latest remote 87e5748b with no frontend delta
evidence:
  - type: file
    reference: docs/handoff/design-system-recon/recon.md 追加調査
    summary: 186TSX、toggle-switch8箇所、ボタン構文292/56/32/15。トークン重複候補2件はmedia条件による切替で訂正、無条件root同名重複0
  - type: file
    reference: docs/specs/design-system/design.md 2026-09-10案
    summary: 材料・部品・ページ・見本・検査の責務、段階移行、受入条件を草案化
confidence: high
tradeoff: 数値は構文とCSS定義の事実。実表示と全操作の互換は未検証。完成度100%とは扱わない
decision: 全体案作成済み。自己審査REVISE。PO承認・実装・PRなし
follow_up: 見本確認と個別仕様を確立してから正式カード検査
```


### EV-20260910-FRONTEND-MOLD-03: 静的見本とトグル接続

- 基準: 6e1335725bb8dfdf390125c4caf5a93f705f4821
- 根拠: docs/specs/design-system/design.md §M、docs/handoff/design-system-recon/evidence-20260910/contrast-proposal.json、proposed-controls.svg.png
- 実測: トグル8 JSXの処理照合、指定色5組の計算、資料PNG目視。実画面・操作は未検証。
- 判定: 草案・自己審査REVISE。外観方向のPO確認待ち。hover配色等が未確定。


### EV-20260910-FRONTEND-MOLD-04: CI強制の実設定確認

GitHub main rules APIでUI governance gateの必須登録を確認。workflowの非必須コメントは現状と不一致。最新main 5386d664と調査対象frontend/3 workflows/2検査本体の差分0。既存UI検査テスト22成功/0失敗。根拠: docs/handoff/design-system-recon/evidence-20260910/main-rules-20260910.json、ui-governance-recheck.txt。docs/specs/design-system/design.md §Nに対照試験12組・必須job拡張・取得失敗の扱いを設計。POの続行とCI追加要求を記録。草案・自己審査REVISE、CI未変更・実装未着手。


### EV-20260910-FRONTEND-MOLD-05: 誤合格の再現と第一便設計

異常BASE=ゼロ40桁と正常HEAD同士の2ケースがいずれもexit0。根拠: docs/handoff/design-system-recon/evidence-20260910/ci-invalid-ref-repro.json。docs/specs/design-system/ci-guard-design.mdに取得失敗exit2・2ファイル・16受入IDを確定。同一AIによる自己審査APPROVEは当該第一便のみ。POのCI補強方針合意を記録。全体設計はREVISE、正式カード未発行・実装未着手。


### EV-20260910-FRONTEND-MOLD-06: 事前確認カードと所有元登録仕様

docs/handoff/design-system-recon/CARD-FRONTEND-MOLD-CI-RECON-01.txtは81行・card-lint exit0。読み取り確認用で実装許可ではない。docs/specs/design-system/ci-registry-design.mdへ9候補の所有部品/用途、記録項目、BASEを許可上限にする比較規則を保存。process-artifactsのGO検証関数がPR本文の書式検査であると確認し、本人承認の自動認証と区別。全体自己審査REVISE、第一便設計APPROVE維持、製品実装未着手・別AI未起動。


### EV-20260910-FRONTEND-MOLD-07: 状態別配色と例外承認候補

button-color-matrix.jsonに190組の指定色計算、最小5.064879620284947・4.5未達0を保存。基準CSS6e133572、実画面ではない。docs/specs/design-system/design.md §Pでdark hover・danger・tab選択の候補を修正。ci-registry-design.mdへGitHub reviewの本人ID/状態/HEAD照合案を追補。API仕様を確認したが実運用は未検証でREVISE。製品コード・CI・外部設定未変更、実装未着手。


### EV-20260910-FRONTEND-MOLD-08: Button操作と表構造

基準6e133572。table-structures.json: native table39、spanあり16、footer2、入力/対象イベントあり28（構文上）。focus-color-pairs.json: 指定10背景で輪郭候補の比率最小6.916973995632248。docs/specs/design-system/design.md §Q/RにButton操作・Spinner継承色/装飾表示・表の共通表示部品と5代表の保持契約を設計。実画面/操作試験未実行。全体REVISE、実装未着手。


### EV-20260910-FRONTEND-MOLD-09: 表39件の移行対応

取得main864ace72までfrontend等の対象差分0。table-behaviors.jsonでonSelectを含む全on属性を抽出。migration.mdにTB-01〜39の移行先と保持する操作を保存。design.md §Sで幅・スクロール枠・代表2表のstickyを契約化。既存行構造を維持して共通Tableへ接続する案。39/39の設計対応は実表示39/39の合格ではない。全体REVISE、第一便CI設計のみAPPROVE、実装未着手。


### EV-20260910-FRONTEND-MOLD-10: 表の装飾属性

基準6e133572。table-appearance.jsonに39表の属性を記録。表要素内style180、className59（違反数ではない）。Companies/Contacts各1のrowClassNameも照合。design.md §Tに共通props・状態の優先度・比較レポートの閾値維持を設計。全体REVISE、第一便CI設計APPROVE維持、実装未着手。文書の省略表示名でガード停止後、名前をellipsisへ変更して保存。ガード解除なし。


### EV-20260910-FRONTEND-MOLD-11: 表239属性の移管先

table-appearance-mapping.jsonのTA-001〜239に移管先案を登録、未割当0。直接DataTable参照23個の明示className/style0・rowClassName2を照合。design.md §U、migration.mdへ保存。実装役の事前確認結果は未受領。全体REVISE・第一便CI設計APPROVE、実装未着手。


### EV-20260910-FRONTEND-MOLD-12: 委任した読み取り確認の受領

POの「合意進める」を、直前に提示した読み取りカードの別エージェント委任に限る承認として実行。/root/ci_preflight_readonlyから手順0〜9の結合出力・終了値を受領。本人による設計審査を別AIの独立レビューとは呼ばない。

根拠: docs/handoff/design-system-recon/evidence-20260910/ci-executor-recon-report.json。旧手順2のfetchはFETCH_HEAD書込権限不足でexit255。不要な書込操作をカードから外し、ls-remoteとorigin/main一致を条件に再開。権限拡張・制限解除なし。通常の権限エラーであり自動承認レビューの拒否ではない。

担当報告: リモート/HEAD/origin/mainは7e3dd6565bc8b239ee09967961326fd096fb72feで一致。対象3ファイルの差分0、既存テスト22成功/0失敗。異常BASE・正常対照はいずれも対象0/exit0で設計時の再現と一致。行数398/221/39、対象3ファイルのstatus出力なし。リポジトリ全体がcleanという意味ではない。

設計担当の直接確認: 同じリモートSHAとorigin/mainを照合。設計worktreeでも対象3ファイル対origin/mainのgit diff --exit-codeは空/exit0。担当のテストを本ターンに自分が実行したとは記録しない。

読み取りカードは改訂83行・card-lint合格。第一便CI設計は自己審査APPROVE維持、全体REVISE。次は第一便の具体的な実装カードを確定し、共通部品の実表示・後続ADR・CI登録の承認運用を解決する。今回の委任は製品実装の承認ではない。製品・CI未変更、実装未着手、文書ローカル保存のみ、PR未提出。


### EV-20260910-FRONTEND-MOLD-13: POによる実施順序の変更

PO原文: 「画面統一の全体設計をした後に最終的にCIを設置する方向で進める、先にCIを設置しない」。
全体設計・共通部品の基準と移行設計を先に完成させ、画面統一の実装後にCIの追加・補強を行う。既存CIは維持し、誤合格防止だけを先行実装する計画は中止する。ci-guard-design.mdの設計内容と再現証拠は後続CI便の材料として保持する。

POはPRマージ・デプロイまでの続行も依頼した。依頼受領と成果物の設計合格・画面確認・レビュー合格を区別する。未確認事項を合格済みと扱わない。全体設計はREVISE、製品実装未着手。

最新照合: git ls-remote/ローカルorigin/mainともd21599c72126dc450a70b7aad2a86b2ef3a412a3。設計HEADからorigin/mainまでfrontend・component-standard.md・ADR-144のgit diff --name-only出力0。preflight成功。他者のAGENTS.md変更を保持。


### EV-20260910-FRONTEND-MOLD-14: 委任許可と材料の互換制約

POは「全体設計の完成後、別の実装担当・レビュー担当を起動し、検証を経てマージ・デプロイまで進める委任」に「許可する」と回答。設計担当を維持し、不明点があれば停止する条件を保持。製品実装担当は未起動、読み取り照合担当frontend_definition_auditを起動し完了した。

根拠: docs/handoff/design-system-recon/evidence-20260910/icon-chart-audit.md。CSS/TSのアイコン5値の二重定義とPlatformIconの数値計算を確認。通常アイコン型の説明と実物が不一致。グラフの残量色はページで色文字列を加工している。数値TS生成・CSS用途色へ集約する設計の制約として保存。既存3チェック成功は担当の報告であり、本ターンの設計担当自身のテスト実行ではない。

実表示の確認手段: Browserスキルを再読し、利用可能ツールを再検索。指定されたjs接続ツールは0件、Playwright MCPは存在。スキル指定の操作経路で接続できないため、代替ツールは未使用。画面・テーマ切替を未検証のまま全体APPROVEにしない。別経路でローカル表示検証する可否をPOへ確認する。

全体REVISE、製品・CI未変更、実装未着手。文書はローカル保存、PR未提出。CIを先に実装しない。


### EV-20260910-FRONTEND-MOLD-15: PO目視の移管と既存PRの重複

PO原文: 「画面確認は完了後に私が行うので実装PRマージまで進めてくれ」。完成後の目視はPOが担当。指定ブラウザー不在を理由とする実装前の停止を解除する。自動検証・コードレビューを維持し、目視未実施はPO確認待ちとして記録する。今回の指示の到達点は実装PRマージ。全体設計のその他の不足を目視移管だけでAPPROVEへ変更しない。

実装前の衝突調査で、今回と同じ領域のOPEN PRを7件確認: #2911 色SSOT統合、#2914 色辞書、#2919 色別名、#2889 カレンダー色、#2895 アイコン色、#2668 Select、#2926 色検査。根拠: docs/handoff/design-system-recon/evidence-20260910/overlapping-prs.json。gh pr viewで実状態/ファイル/HEADを取得。各HEADの固定main23413b10f29228ffce7c7bf0813649b1910cf6bbへのancestor判定は1。祖先でないことだけで全変更未反映とは断定しない。

#2668のSelect.tsx/FormField.cssは固定mainとの差分0で、当該部品実装は一致する。一方ページ差分は残り、PR全体が適用済みとは判定しない。#2911のindex.cssはmainにあるaccent-hover #163171をaccent参照へ、link-active-bg #ebeff8もaccent参照へ変更する内容があり、今回の状態別配色案と同値ではない。旧PRを一括マージする根拠はない。古いブランチと現在mainのtree差分にはmain側の後続変更も含むため、その全差分をPR意図と解釈しない。

latest ls-remote mainは3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1feへ進行。上記の比較根拠は固定23413b10。旧台帳のIN_PROGRESSだけでなくGitHub OPENと実ファイルを照合した。今回設計の前段ではOPEN PRの対応確認が不足していたため補完した。

共通のブランチ占有規則（active-work.mdの重複発見時STOP、guards/04-worktree.mdの先約確認）に従い、新しい製品実装の着手を停止。既存PRも今回の整理対象に含め、使える差分を再利用して一本化する可否をPOへ確認する。既存PRの編集・close・merge・他者worktree変更は行っていない。CI追加は最後、製品実装未着手。


### EV-20260910-FRONTEND-MOLD-16: 統合許可と既存PR採否

PO原文: 「今回のフロントエンドのSSOTに関するものはまとめられるものはまとめて良い、ただし不具合発生時に原因が分かるように分離したほうが良いものは分離して順番にマージしてくれ」。重複PRを理由とする停止を解除。migration.mdに7PRの再利用・既反映・不採用を記録。基準main3bdf33d5。#2668の部品3blob一致、5色PRは延べ28/実14ファイルの変更行を担当が実PRdiffで照合。選択背景と文字の同色化・未定義calendar色参照を採らない。CIは最後、PO目視は完成後。新製品実装/PRマージ未着手、まず調査と計画の文書PR化を進める。

## EV-20260910-PMG-CUTOVER-PROBE

PMG切替設計の未確認条件を検証する隔離便。正本: docs/handoff/pmg-import-delivery-ssot/design.md / recon.md / card-cutover-probe.md。
PO実装担当指定「codex terra」、マージ/デプロイ指示と作業場所例外「許可する進める」を区別して記録。製品設計REVISE、試験実装だけ自己審査APPROVE。Terraの旧コルーチン取消試験14/14成功を設計担当が再実行確認。Docker検証は実装/CI待ち。本番状態変更なし。

PMG追補: 17:41 JST、本番読取で既往running2件のID一致・items0を確認。応答worker1台のactive/reserved/scheduled各0。DB更新/配信なし。Terra利用上限停止によりDocker試験は未完成・未提出。詳細は上記recon末尾。

PMG追補: PR #3408 HEAD879aa1f4、Actions run34460419959/job102816671239を直接確認しDocker試験99/99成功・errors0。試験差分審査APPROVE、製品設計REVISE/画面未完成。失敗3段階と修正根拠・版/digest・結果zip hashは上記design/reconのLinux/Docker実測結果節。マージ/自動deployは次の確認対象。

### EV-20260910-FRONTEND-MOLD-17: 文書PRマージと操作契約の補完

GitHub PR #3407は2026-09-10T09:15:15Zにmerge commit d715d998877e899206ba9bb4f82c726fc3175b30でマージ済み。gh pr viewのstate=MERGEDを設計担当が確認。最終HEAD f8c4b19fの文書レビューAPPROVE受領、設計担当が全checksの成功/対象外skipを確認し公式gh-pr-merge-safe.shで実行。これは文書PRの合格で、全体製品設計の合格・製品実装結果ではない。公式cleanupで旧worktree削除と台帳DONEを確認。

新作業場所release/frontend-ssot-contractsは上記main起点。preflight成功、3bdf33d5からfrontend/scripts/.githubの差分0を直接確認。design.md §Zに入力577箇所の全属性、ボタン411箇所の分類と移管案、DOM/ref/送信の保持条件、アイコン生成器の契約を追補。委任担当の読み取り報告はevidence-20260910/*-semantic-audit.md/jsonおよびremaining-components-audit.md/jsonへ保存。UI目視・実装テストの実行結果とは区別する。

全体設計REVISE維持。残件はCard/Badge等の特殊用途と最終CIの所有元・CSS検査契約。製品コード変更0。CI追加は最後、目視は完成後PO。新たなPO決定や番号付きGOを創作していない。


### EV-20260910-FRONTEND-MOLD-18: 全体設計自己審査とAPI矛盾解消

設計担当がPlanner作成後にArchitectとして同一AI自己審査APPROVE。独立した全体設計レビューではない。根拠はdesign.md §AA。限定APIレビューの4指摘（裸本体とアイコン、Select appearance互換、EmptyState内包DOM、Tabsの二重callback）を修正。React.MouseEventを変換しない本文も設計担当が直接確認。

CSS314候補、動的Badge33箇所166状態、動的style172項目、Icon/Spinner属性を追加照合。限定CIの有限propertyと部品寸法除外を確定、受入C01〜C27。調査担当の報告と設計担当の直接差分/文書検査を区別し、未実装テストを実行済みとしない。最新origin/main0be59e5290cab4149aa5451920317f8fa7f7564cと3bdf33d5のfrontend差分0を直接確認。

次は設計文書PRの保存・レビュー・マージと、既存ICON5値を変えない生成便のカード検査。製品実装未着手、CIは最後。ADR-144の追補はProposedで、PO自筆の承認/番号付きGOを代筆しない。

## EV-20260910-PMG-INTEGRATION-DESIGN

2026-09-10、base b36041ed。PO「次を進めるPRマージまで」。既存保持の作成例外と設計文書PRマージの承認として記録。起点main・UUID・担当台帳・preflight/開始/所有検査を確認。製品実装なし。
PR3408のmerge0be59e52、deploy34460726589 successをGitHubから再確認。実nginxと独自試験の差、外部clear/append2呼出しと後置DB記録、40秒stopと通常rollbackを読み取り、design最終節に8受入条件・段階別復旧・旧実行分類を保存。根拠の行番号と公式資料はrecon「入口配布・旧処理照合の再調査」。I1〜I8未実施。自己審査REVISE、実装カード未発行、画面未完成。

## EV-20260910-PMG-BARRIER-CONTRACT

base411df652、2026-09-10。PR3410/deploy34468628611成功確認。rootは配布/監査/ログ設定、Terraは旧配信観測を読取。実装変更なし。既存design:178の過去run非生成に従い、全過去復元を切替前提にする読み方を訂正。配布保留6分類、初期化順序、検問位置を草案化。通常配布も止める影響はPOへ質問中・採用未決。自己審査REVISE、実装カード未発行。根拠はdesign/recon最終節。

### EV-20260910-FRONTEND-MOLD-19: 設計文書マージと数値アイコン実装便

PR #3409は2026-09-10T09:56:27Z、merge commit b36041ed9fa69881886c431d05d586cf09e82f56でMERGED。設計担当がgh pr viewで直接確認。最終HEAD586ba4e3の全CI成功/対象外skipと限定文書レビューAPPROVEを確認し公式mergeスクリプトを実行。全体設計は同一AI自己審査であり、独立した第二者設計審査とは称しない。

同mergeを起点に公式new-worktree.shでrelease/frontend-icon-sourceを作成、preflight成功。CARD-ICON-SOURCE-IMPLEMENT-01をcard-lint exit0で検査してGeneratorへ委任。ICON5値14/16/20/24/48を保つ数値生成だけを本便とし、配色・部品API・画面移行・CI追加は別便。原稿レビューのCLI回帰と途中書込/rename失敗検証の不足を追加試験へ反映。製品検証/PR/マージの結果は完了後追記し、準備段階では合格としない。PO目視は完成後。

EV-20260910-FRONTEND-MOLD-19追補: Generatorの35試験（Node24/22各35成功、失敗0/skip0）、npm ci/check:all/build成功の生ログを設計担当が確認。製品差分第二レビューAPPROVE。詳細とhashはdocs/handoff/design-system-recon/evidence-20260910/icon-source-implementation.md。PR/CI/マージ未完、画面目視は完成後PO。

EV-20260910-FRONTEND-MOLD-19追補: 実装commit40ff3365保存済み。公開repo shingo-ops/salesanchorへの通常pushが自動承認レビューで2回拒否。具体的な製品5/文書9ファイルの公開送信について明示承認不足との判定。詳細は実装検収の末尾。push/PR/実装マージ未実施、POへ公開送信承認を確認する。迂回なし。

公開送信許可の追補: 設計担当が公開リポジトリshingo-ops/salesanchorへの14ファイル（実装5＋設計・検証文書9）送信可否を質問し、PO原文「許可する」を受領した。この許可で公開送信を再開する。番号付きGOやADR承認の代筆には使用しない。

PR #3412 HEAD e739c9f146004c298910e25b1f99e1573bc0cc95のGitHub checksを設計担当が直接確認: SUCCESS37/SKIPPED8/FAILURE1。残る失敗はprocess-artifacts gate（job102847686397）の「GO記録セクションがない」だけ。Frontend lint & custom checks、Storybook、Karte Visual Gateを含む技術チェックは成功。限定第二レビューは同HEADに適用可を確認済み。公開送信許可は受領済みだが、番号付きGO原文を創作せずGO #3412のPO原文を確認する。DB変更なし、バックアップ確認は該当なし。新実装マージ/本番反映未実施。

PO原文「GO #3412」を受領。2026-09-10 20:24 JSTに受領後記録時刻としてPR本文へ転記し、公式validateGORecordのエラー0を確認。バックアップはDB変更なしのため該当なし。最新main追従後のHEADでCIを確認してマージする。承認を実施済みマージと混同しない。


## EV-20260910-GUARD-ENFORCED

2026-09-10、POの管理アカウント利用GO後、shingo-opsのadmin=trueを確認してruleset15777895へguard-authoring/evaluation（GitHub Actions15368）だけ追加。既存12件・strict・適用先・例外0件を保持。設定前後JSONと実イベント証跡は docs/handoff/design-partner-card-ops/guard-evaluations/20260910-runtime.md から参照。未報告BLOCKED、評価欠落0b532e9fは必須FAILURE/BLOCKED、復元fb083494は13必須SUCCESS/CLEAN。試験#3405は未マージ閉鎖。設置#3401は23413b10でマージ・deploy34452331125成功、実配備SHAとHTTP200を確認済み。自己審査APPROVE、独立第二者レビューではない。既往失敗を保持し、製品画面・実データ取り込みの完了とは区別。

## EV-20260910-GO-REV3-PR

設計草案PR #3418提出をAPIと登録ファイルで確認。初回HEAD0546b8b8、文書6ファイルのみ。自己審査REVISE・実装未着手・委任未有効。証拠 /tmp/reports/TH-GO-REV3-PR-CONFIRM.json。

## EV-20260910-PMG-SCREEN-CONNECT

2026-09-10 base4f1c2b81。POは説明後に「承認する…確立したならページ作成まですすめる」と承認（全文はdesign最終節）。本番切替時の一時停止/他の更新待機の方針採用、個別本番停止ではない。
既存progress/items、coverage/NULL契約、ページ/共通APIと権限を実ファイルで確認。検索漏れを訂正。新履歴や切替導入とは独立した既存API接続ページのみ自己審査APPROVE。カードCARD-PMG-SCREEN-CONNECT-01を正式card-lint exit0で検査後Terraへ委任。rootは製品コードを書かない。実装ccc105ad、main4734fe7f統合4619e7a8。root検証build/check:all exit0、unit133件成功、模擬API E2E5件成功・PC/390px英語暗色画像を確認。ページ接続差分APPROVE、親設計REVISE。PR/CI/本番反映は別の状態として記録する。

EV-20260910-PMG-SCREEN-CONNECT追補: PR #3416を提出（https://github.com/shingo-ops/salesanchor/pull/3416）。最新main統合後にrootでbuild/check:all/unit133件とE2E5件を再確認、いずれも成功。根拠台帳の競合は両セッションの全文を保持して解消。画面接続は実装済み・差分確認済み、CI確認中、未マージ・本番未反映。番号付きGO原文未受領。

EV-20260910-PMG-SCREEN-CONNECT GO追補: PO原文「GO #3416」を受領。受領後記録時刻2026-09-10 21:17 JST。対象HEAD ca1dc79bc9a9661a39baae21e0952c890e7522c7の検査は37成功/8対象外skip、唯一の失敗は番号付きGO記録欠落（job102865146997）。承認をPR本文へ転記し、記録文書更新後のHEADで再確認してマージ/通常デプロイを確認する。DB変更なし・バックアップ確認は該当なし。

EV-20260910-PMG-SCREEN-CONNECTリリース完了: PR #3416は最終head6459e7ca・37success/8skip確認後、17ebe93fでMERGED（2026-09-10T12:24:21Z）。deploy34476536034/job102868559798 success、実配備HEAD17ebe93f、公開JS index-i0HIAxuW.jsと新画面コード、health ok/DB・Redis・Celery connectedをrootが直接確認。詳細/限界/実行しなかった試験はdesign/recon末尾。本番の実配信・管理者実データ操作は未実行。ページ接続完了と、未実装の新解析実行記録・全配信履歴/切替設計REVISEを区別する。

## EV-20260910-L1-3404-DEPLOYED

PO原文「GO #3404」をHEAD45b9ae3677153002952bceee77a63972484d47c4へ受領。受領確認21:40 JST、GO4欄へ転記。最新の必須13件とprocess-artifacts gate成功、CLEANを確認して既存gh-pr-merge-safe.shへ --merge --match-head-commit を渡した。GitHub実測: mergedAt2026-09-10T12:42:19Z、mergeCommit df3c2a47ed8a89de86246af834b89329133f86d6。親に承認HEADを含み、差分はFedEx/SA-02の2ファイル+5/-4だけ。

Deploy to VPS run34478228420/job102874182347はsuccess。事前DBバックアップ、既存マイグレーション、SA-19 smoke、FedEx Rates smoke、Finalize、Verify deploymentの成功をActions APIで確認。新しいDB変更を本PRへ追加したわけではない。

今回直接実行した本番読取: prod1の /home/ubuntu/salesanchor のHEADがmergeCommitと一致。稼働astro-webapp-backend-1内の /app/app/services/fedex_rates.py と /app/app/tasks/sa02_recon_monitor.py のSHA256が承認HEAD由来の2値と一致。コンテナState.Statusはrunning。https://api.salesanchor.jp/api/health はstatus ok、database/redis/celery connected。DockerのHealthフィールドが存在せず最初のinspectはexit1となったため、成功扱いせずState.Statusのみの再読取とAPI healthを分離した。本文やログへsecretを出力していない。

承認ファイルhash: fedex_rates.py=1d6c6fc464e553318c15324122aced896d5212ff645caa26d03f795ed6ae7812、sa02_recon_monitor.py=2767f444270a938e53a5ad3496e9454fd7880b2e24b9543919c59429302b4876。

証拠: /tmp/reports/TH-L1-3404-MERGED.json、TH-L1-3404-MERGE-PROOF.json、TH-L1-3404-GO3-CHECK.json、TH-L1-3404-GO3-MERGE.txt、TH-L1-3404-DEPLOY-FINAL-RUN.json、TH-L1-3404-DEPLOY-JOBS.json、TH-L1-3404-PROD-VERIFY.txt、TH-L1-3404-PROD-STATE.txt、TH-L1-3404-API-HEALTH.json、TH-L1-3404-RESULT.json。

L1状態はPO承認済み・マージ済み・本番反映照合済み。wrapperでL1worktree/ローカルbranchを整理、公式ledger-lookupでDONEを確認。GOフロー設計PR #3418は別テーマとして未マージ、全体設計REVISE、ガード/委任経路は未実装のまま。

## EV-20260910-GO-ACTIVATION-IDENTITY

PO/repoの数値IDとworkflow runのactor/triggering_actorを直接照合。根拠 /tmp/reports/TH-GO-PO-IDENTITY.json、TH-GO-REPO-IDENTITY.json、TH-L1-3404-DEPLOY-FINAL-RUN.json。正式委任の開始時本人操作案と再実行/期限境界をdesign.mdへ追記。全体REVISE、代理GO未有効。

## EV-20260910-GO-QUEUE-MODEL

固定3ticketの抽象モデル333状態/639遷移で安全条件違反0。未確定送信を解放する欠落版は5操作で違反を検出。原子的直列化と有効な承認入力を仮定した限定検査で、実CAS/GitHub/本人性/期限/再受付の実装合格ではない。ソース/前提はrecon.md末尾、結果 /tmp/reports/TH-GO-QUEUE-MODEL-RESULT.json。全体REVISE。

### EV-20260910-FRONTEND-MOLD-20: 第1実装便マージと次の同値カラー集約

PR #3412は2026-09-10T11:31:17Z、merge commit6d3e348614d675c533cc46fefddb03544f581e8cでMERGED。設計担当がGitHubのstate/mergedAt/mergeCommitを直接確認。最終HEAD254ab96fはCI38成功/対象外8、第二レビューAPPROVE適用確認。PO原文GO #3412を転記済みで公式merge/cleanup成功、active-work.dはDONE。ICON5値保持とCSS正本からの生成が実装済み。全体の画面統一完了とはしない。

PO原文「離席するのでcxastragoモードと同じ条件で権限委譲するので進めてくれ」を受領。本セッションの対象は引き続きfrontend SSOT。ローカルcxastrago.zshとsalesanchor-astra-go.mdを読み取り、条件は有効化から24時間・不明/失敗/範囲外停止・代理判断の明記、現状はGO委任有効化待ち/期間未開始と確認。PR3406はOPENで委任承認経路未実装。最新main4734fe7fのGO検査もPO表記のみで、代理GO対応を確認できない。委任指示を受領した事実と、機械的有効化を区別し、PO名義GOを創作しない。承認経路の変更は本frontend便で行わない。

既存の実装・レビュー・段階別PRの承認を根拠に、公式release/frontend-color-sourceをorigin/main4734fe7fから作成、preflight成功。旧PR2895/2911/2914/2919の採用差分を既存migrationに従って再測定する。calendar21用途・部品API・新CIは別便。新しい24時間期間を自己設定・再開延長しない。

EV-20260910-FRONTEND-MOLD-20追補: 7製品原稿の限定第二レビューAPPROVE。manifest7件一致、既存9宣言/新16宣言/使用CSS7箇所/mail属性とCSSの対だけと別担当が確認。ブラウザー原稿は静的25ペアと実ソース変換を通過した補助実行後、Chromium1223未導入で起動できなかった。失敗ログを保存し、正式実装便で既存Playwright指定ブラウザーを正規導入して検証する。未実施を成功扱いしない。

EV-20260910-FRONTEND-MOLD-20追補: 7製品を原稿hash一致で反映しrootが全件確認。npm ci成功後、npxのplaywrightが@playwright/test1.59.1へ解決し、比較の直接依存playwright1.60.0とブラウザー版がずれることをrealpath/package version/executablePathで実測。依存設定や期待値を変えず直接依存のCLIでChromium1223を導入するカードへ修正。失敗を保存し、検証結果は再開後に確認する。

同値カラー便の検証完了追補: Generator実行の通常ブラウザー比較は静的25/色50/表示60ペア一致、既存check:all・build・test:coverage（14ファイル121試験）・build-storybookは全exit0。rootが生ログ/JSONと7製品hashを直接確認。詳細はdocs/handoff/design-system-recon/evidence-20260910/color-source-implementation.md。PR/リモートCI/マージ未完、目視は完成後PO、代理GO未有効。

EV-20260910-FRONTEND-MOLD-20提出追補: 実装commit48924bd4を通常push済み。safe-createの自動審査は25ファイル公開承認不足として一度拒否。rootがGitHub APIで同じ25ファイルが既に公開済みであることを確認し、新規ファイル送信を伴わないPR本文作成として正規再審査を受け許可された。公式safe-create/register-pr成功、PR #3420提出済み。main df3c2a47との文書競合はmain全文と本便追補を保持して解消。製品7hash不変、他者の製品変更を保持。代理GOは未有効、番号付きGO未受領。

PR #3420承認ゲート確認: HEAD d168e943のjob102876642463は番号付きGO記録なしでFAILURE。rootがGitHubログを直接確認。代理GO未対応を名前の偽装で通さず、POのGO #3420待ち。残りの技術CIは確認中。マージ/本番反映未実施。

PR #3420 GO追補: PO原文「GO #3420」を受領。2026-09-10 23:30 JSTは受領後記録時刻。HEAD4d73be5fのCI36成功/8対象外skip、残る1失敗は番号付きGO欠落（job102877141141）とrootが確認済み。本人のGOを本文へ転記し、最新HEADのCI確認後に公式手順でマージする。DB変更なし・バックアップ確認該当なし。代理GOは使用しない。

## EV-20260911-GO-SESSION-DELEGATION

PO原文「セッション上で委任した時点でGOを出せる権限を移譲されたと認識して良い」と後続「GO」を受領。追加GitHub有効化案を撤回し、セッション委任成立と検査未対応を分離。design.md最新節に原文・期限非延長・4欄と委任参照・受入条件を保存。同一AI自己審査REVISE、検査実装未着手。元委任の発話時刻は未確認であり、記録時刻で再開しない。証拠 docs/handoff/go-record-transcription/recon.md末尾、/tmp/reports/TH-GO-SESSION-PREFLIGHT.txt。

## EV-20260911-GO-DELEGATION-PROOF

本セッションの元委任user記録2026-09-10T12:11:22.302Zを読取。受信記録基準の24時間は翌12:11:22.302Zまで、再確認で延長しない。生ログ全文ではなく関連3発話と各行hashをreconへ保存。hashは本人認証ではない。委任判定19ケース/重複登録4条件成功、期限比較変異を検出。designに独立した承認処理と本番失敗後の復旧枠を具体化。全体自己審査REVISE、実App/検査実装未実施。証拠 docs/handoff/go-record-transcription/recon.md末尾、/tmp/reports/TH-GO-DELEGATION-SOURCE.json、TH-GO-DELEGATION-MODEL-RESULT.json。

## EV-20260911-GO-BOUNDARY-RECOVERY

制御repo独立起動・Issue転記受付・状態正本への限定書込の案をdesignへ具体化。既存wrapperはActions時exit0、GO/予約照合なし。sandboxはpullのみで実機変更可能とはしない。復旧モデル8状態/9遷移で通常列へ戻る7操作経路を確認、誤解放変異を検出。全体自己審査REVISE・実装/設定変更0件。証拠 docs/handoff/go-record-transcription/recon.md末尾、/tmp/reports/TH-GO-RECOVERY-MODEL-RESULT.json。


## EV-20260911-PMG-VISUAL-HIERARCHY

POの認知負荷軽減依頼に基づく表示改善。根拠: docs/handoff/pmg-import-delivery-ssot/design.md と recon.md の2026-09-11表示節。3つの公開設計指針と実物部品/状態契約を照合、自己審査APPROVEは表示範囲だけ。Terraへの正式カード発行前。実装・視覚/動作試験・PRマージ・本番反映は未完了。

EV-20260911-PMG-VISUAL-HIERARCHY実装検証: 正式カード検査成功後Terraが製品7ファイルを実装。rootがunit143件/E2E8件/build/check:all成功とPC/390px明暗画像を確認。詳細はdesign末尾。表示改善のみコード/視覚レビューAPPROVE。PR/CI/番号付きGOの確認へ、本番未反映。

PR #3424提出済み: https://github.com/shingo-ops/salesanchor/pull/3424 。製品HEAD 0856c66f984e6ddd815168019513d5f4364356b8で40 checks成功・8 skipped、process-artifacts gateのみ失敗（初回の見出し不一致はPR本文修正済み、再実行job103077880628はGO記録未受領だけを報告）。GO #3424未受領のためマージ/本番反映未実施。包括的な事前承認を番号付きGOへ代筆しない。次はGO受領後に最新HEADのCI確認。

### EV-20260910-FRONTEND-MOLD-21: カレンダー実行契約再審査

### 次便の実行条件確認（2026-09-10）

PR #3420はmerge a5e5a250aabe2e244ebf64c24bef40b5db40541c、最終HEADc3f8668eのCI38成功/8対象外、公式merge/cleanup完了を直接確認。次便はこのmain起点。カレンダー21値/20固有色の移管と既存ファイル単位hex増加禁止が衝突し、限定契約を自己審査REVISE。製品未変更。根拠: docs/handoff/design-system-recon/evidence-20260910/calendar-source-audit.md。推奨は色移管保留→共通部品先行、POの順序判断待ち。CIを変更・迂回しない。

### EV-20260911-FRONTEND-MOLD-22: 読み取りやすさと部品先行

POの続行と認知的に理解しやすい表示の要求を受領。design.md§ACへ根拠/基準/測定限界を保存。カレンダーを保留しButton本体の実物再監査へ。実装未着手、CI変更なし、番号付きGOは別途本人原文を確認。

Button契約実装追補: ADの製品3+unit2だけ実装、unit151と既存check/build/Storybook成功。rootが局所browser操作18/表示18/reduced9と最終console.error0を直接確認。初回fixture二重入口警告を保持し実path統一で再測定。詳細はdocs/handoff/design-system-recon/evidence-20260910/button-contract-implementation.md。PR/CI/マージ未完、全体外観・PO理解速度未検証。

Button便PR提出: https://github.com/shingo-ops/salesanchor/pull/3423 をreadyで作成し公式登録完了。実装commit b35807504a87015aed52a99d6791f9774b2f8293、製品5hash一致、限定第二レビューAPPROVE適用をroot確認。stage19/PR全体22ファイル。CI確認中、番号付きGO未受領。過去GO3420を流用せず、全体の形/配色統一とPOによる理解しやすさの評価は未完と区別する。

PR #3423 GO追補: PO原文「GO #3423」を受領。2026-09-11 07:55 JSTは受領後記録時刻。前HEAD3f052a9dはCI37成功/8対象外、1失敗はGO記録欠落。製品5hashは限定第二レビューと一致をroot再確認。本人原文をPRへ転記し、最新HEADの検査後に公式マージする。DB変更なし・バックアップ該当なし。代理GO/過去GOの流用なし。

## EV-20260911-GO-INTAKE-P1-READY

既存sandboxの合成受付workflow準備PRに範囲を限定した設計とカードを作成。actionlint/ローカル13ケース成功。同一AIの限定設計審査APPROVE、実行承認前。全体REVISEを維持。GitHubアプリのrepo書込表示とworkflow API実権限は区別し、403時は停止。成果物 docs/handoff/go-record-transcription/intake-p1-workflow.txt、TH-GO-INTAKE-P1-PR-01.txt。

PR #3424 GO追補: 本セッションでPO原文「GO #3424」を受領。2026-09-11 08:10 JSTは受領確認の記録時刻。PR本文へ本人原文を転記。main76c6dff9の共通Button変更を取り込み、双方の根拠登録を保持して追記競合を解消。DB変更なし・バックアップ該当なし。最新HEADの検証後に公式マージする。


```text
id: EV-20260911-FRONTEND-MOLD-24
date: 2026-09-11
agent: root design partner
task: Icon公開契約便の前提となる既存callback依存不足の分離修正
scope: GoogleCalendarStatusBar依存1行と回帰試験
evidence:
  - type: file
    reference: docs/handoff/design-system-recon/evidence-20260910/calendar-callback-recheck.md
    summary: 対象blob基準と一致、保存前警告1/exit1、専用treeの公式作成確認
  - type: file
    reference: docs/specs/design-system/design.md §AF
    summary: PO続行受領、回帰検証条件/非同期取消は対象外/同一AI自己審査APPROVE
confidence: high
tradeoff: 通知関数変更時は状態再取得とinterval再登録が起きる
decision: Icon外観便とは分離し先行実装検証。新CIなし
follow_up: 赤→緑の回帰試験、保存前lint、既存全検査、第二レビュー、PR。GOは別途
```

EV-20260911-FRONTEND-MOLD-24 実装追補: calendar-callback-implementation.mdへ検収保存。Generator実行の回帰7件中1赤（新通知0回）→依存1行修正→全168緑、対象厳格lint/checkall/build exit0。rootは差分/原稿/ログと2hashを確認。新CI/外観変更なし、番号付きGO/PR/マージ未実施。

EV-20260911-FRONTEND-MOLD-24 PR追補: https://github.com/shingo-ops/salesanchor/pull/3426 ready OPEN、commit218706338a2f6822c269a4fbb5401d6b919ddae4をroot確認。.pr-number/台帳3426一致、12filesの通常push/公式起票登録成功。限定第二レビューAPPROVE、製品2hash一致。CI確認中・番号付きGO未受領・マージ未実施。


PR #3426 GO追補: PO原文「GO #3426」を受領。2026-09-11 10:11 JSTは受領後記録時刻。前HEAD577ecf45のCI37成功/8対象外・残る1失敗はGO記録欠落。製品2hashと限定第二レビュー対象の一致をroot再確認。本人のGOをPR本文へ転記し、最新CI後に公式マージする。DB変更なし・バックアップ該当なし。


```text
id: EV-20260911-FRONTEND-MOLD-23
date: 2026-09-11
agent: root design partner / overlay_contract_audit read-only
task: 通常Icon公開入口の限定
scope: frontend Icon API、唯一styleの同値配置移管
evidence:
  - type: file
    reference: docs/handoff/design-system-recon/evidence-20260910/icon-contract-recheck.md
    summary: main76c6dff9、152 JSX/118実運用分類、style1/color0、Heroicons既定hidden衝突実測
  - type: file
    reference: docs/specs/design-system/design.md §AE
    summary: mode handoff、4ファイル所有、ARIA6属性限定/hidden既定保持、同一AI自己審査APPROVE
confidence: high
tradeoff: className互換は持越し、全体の色/形/認知効果は未検証
decision: 正式カード検査後に既存Generatorへ委任。CI追加は最後
follow_up: 実装、型/DOM/ブラウザー同値比較、第二レビュー、PR。番号付きGOを創作しない
```

EV-20260911-FRONTEND-MOLD-23 実装追補: docs/handoff/design-system-recon/evidence-20260910/icon-contract-implementation.mdへ検収を保存。Generator実行の162試験・既存check/build/Storybook・局所ブラウザー8同値をroot読取確認。rootが型名依存の0件監査を不採用とし、修正版で元152対象欠落0を独立JSON突合。限定第二レビュー対象4hash一致。新PR/番号付きGO/リモートCI/マージは未完。

EV-20260911-FRONTEND-MOLD-23 提出停止追補: pre-commitのmax-warnings=0により既存GoogleCalendarStatusBar依存不足1警告でgit commit exit1。rootが基準76c6dff9本文を同eslint stdinへ入力し同警告/exit1を再現。製品4hash/162試験/8比較の事実とは別に提出条件REVISE。詳細icon-contract-implementation.mdとicon-contract-commit-block.txt。commit/PRなし、既存不備別PR先行のPO判断待ち。


EV-20260911-FRONTEND-MOLD-23 最新基準追補: 前提PR3426 merge5de8afa1を取り込み、通常Icon4製品を再検収。Generator実行の厳格lint/179試験/checkall/build/Storybook全exit0、局所8同値。rootが監査対象152→163欠落0/追加test11/既存属性差分1と4hashを照合。根拠: docs/handoff/design-system-recon/evidence-20260910/icon-contract-implementation.md 最新基準節、icon-contract-resume-evidence.json。旧基準の結果と区別。PR提出前、GO/マージは未完。


PR #3427 提出確認: https://github.com/shingo-ops/salesanchor/pull/3427、ready OPEN、提出HEAD cfb3068b49429672d63dbb84d41be483f40b4bfc、公式.pr-number登録をroot直接確認。製品4/文書24ファイル、保存前検査を迂回せずcommit成功。最新179試験/8表示同値の検収と4hashを維持。番号付きGOは未受領、リモートCI確認が次の一手。マージ/デプロイは未実施。


## EV-20260911-INVENTORY-LITE25

POが在庫補助解析を2.5 Flash-Liteへ変更するよう依頼。理由はPO報告のレガシー精度実績と単価削減。現行精度比較は未実施。既存docs/handoff/llm-model-3-5-flash-lite/design.mdとrecon.mdへ限定契約・自己審査・適用限界を記録。専用release/inventory-lite25、基点eefa9143。

在庫補助解析2.5 Lite変更はcommit be42f18e、PR #3425へ提出済み（https://github.com/shingo-ops/salesanchor/pull/3425）。CI確認中・GO未受領・本番未反映。PR3422のUI変更とは別便。報告/tmp/reports/LITE25-PR-01.txt。


最終検証（2026-09-11）: PR #3425 head e60f555e、backend job103106398328は2543成功/94skip。ただし実API試験がrequested model unavailableとしてskipしたことをwarning生ログで直接確認（404または提供不可文字列の既存判定）。2.5 Liteが現在のCIキーで利用できたとは扱わない。ログ/tmp/reports/LITE25-PYTEST-SKIP-EVIDENCE.log、結果LITE25-FINAL-02.json。実装・理由記録は完了、本番未反映。運用採用はREVISE: 対象プロジェクトでの提供可否解決が必要。旧環境の利用実績は現在のキーでの提供を保証しない。GO未受領。停止記録の文書commitは再CIを避けローカル保存、PR本文にも同内容を保存する。


## 2026-09-11 現在のCI接続の拒否理由を直接確認

PR #3425 head 5fa171b86638e59e433d5c4e6e08a501aaab031f、Backend Tests run34550427274/job103112026495を直接取得。固定ラベル診断は new_users=True / no_longer_available=True / http_404=True / not_found=False / unsupported_method=False / api_v1beta=False。Google呼出しの例外に新規ユーザー向け提供終了の文言が含まれることを確認。従来の一括skip表示からの推測とは区別する。全文は秘密値漏洩防止のため出力していない。

実行結果2543passed・94skipped・303warnings、92.62秒。対象実API試験はskipであり、2.5 Liteによる解析成功や精度合格ではない。本番キーの利用可否・CIキーと本番キーの一致・Googleが新規利用者を判定する具体単位/解除条件は未確認。APIバージョン変更やSDK移行で解決すると断定しない。

Google公式 https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite は安定版IDとStructured outputs対応を掲載。https://ai.google.dev/gemini-api/docs/deprecations は安定版の終了日未発表、preview-09-2025の終了2026-03-31を掲載。確認日2026-09-11。Context7ツールは利用不可、PO起動指示の代替許可により公式資料を直接参照。これらの公開資料は個別キーの利用を保証しない。

診断追加commit2be4c372。CI開始前にmain5de8afa1との根拠台帳追記競合を双方保持して5fa171b8へ統合。本文に残る「停止記録commitはローカル保存」は前時点の記録であり、今回4cf66482もpush済み。製品コード・CI設定・secrets・本番は今回変更なし。診断は実API試験の固定警告のみ、判定と呼出回数は不変。PR未マージ、GO #3425未受領、運用採用REVISE継続。

生ログ /tmp/reports/LITE25-ERROR-DIAGNOSTIC-CI.log、SHA256 0a1c1a6223e8c09f929ada43c8c407a02983974073dfce2e77d48061169b4891。GitHub https://github.com/shingo-ops/salesanchor/actions/runs/34550427274/job/103112026495 。次の確認は本番接続の提供可否と対象プロジェクトの利用条件。レガシー調査は旧利用権の比較材料であり、現接続の診断に必須ではない。キー交換・Google再認証・追加課金は実施していない。


## 2026-09-11 3.1 Flash-Liteとレガシーキーへの変更契約

PO原文「じゃあ3.1に変更して、キーもレガシーに差し替え」。直前の2.5採用契約は本追補で置き換える。2.5はCIキーとPO提供レガシーキーで404・新規ユーザー向け提供終了の文言を実測。3.1 LiteはレガシーキーでHTTP200、JSON期待値一致、入力8/出力9tokenを実測。共有キー利用の3.5 Lite（翻訳）と3.6 Flash（TCG抽出）も各1回HTTP200・非空応答。単純な接続検証であり在庫解析や翻訳精度の合格ではない。報告: /tmp/reports/LITE25-LEGACY-KEY-PROBE-02.json、LITE31-LEGACY-KEY-PROBE-01.json、LITE31-SHARED-KEY-CHECK-01.json。

Why: 利用不可の2.5に代えて利用できた3.1を選ぶ。通常のテキスト入力/出力単価は100万token当たり0.25/1.50USD（Google公式 https://ai.google.dev/gemini-api/docs/pricing 、2026-09-11確認、Context7利用不可のため許可済み公式代替）。3.5の0.30/2.50より同token数なら入力約16.7%・出力40%低い。実請求額・無料/有料契約状態・実在庫精度は未確認。外部導入事例は本選択の証明に不要。

実装: inventory_parser_llm.pyの既定2箇所と関連テストをgemini-3.1-flash-liteへ変更。llm_budget.pyへ3.1のテキスト単価を追加し、入力100万=0.25・出力100万=1.50・合計1.75を既存parser試験で検証する。共有DEFAULT_MODEL、翻訳/TCGのモデル名、prompt、JSON schema、予算上限、DB、CI設定は維持。

キー: ADR-075に従い既存GitHub Actions repository secret GEMINI_API_KEYのみをPO提供値へ更新する。キーは標準入力で渡し値をログ・引数・文書に出さない。更新時刻を読み取り、後続CIの実API試験がskipでなく成功することを確認。deploy.yml:245が同Secretを本番へ展開するため、本番適用は正規デプロイ時に起きる。現キーはGitHubから読み戻せず、旧値への復元材料は本調査では確保していない。旧Googleキー自体を削除・失効させない。更新承認は上記PO原文、PRマージのGO #3425を創作しない。

| 基準 | 検証方法 |
|---|---|
| 在庫既定呼出・返却modelが3.1 Lite | 既存モックとCI実APIテスト |
| 入出力別の費用と合計が正しい | 既存費用連携assert3件 |
| 共有キー利用機能が接続可能 | 3.5 Lite/3.6 Flashへの固定入力各1回HTTP200実測済み |
| 新キーで既存解析経路が成立 | CI実APIテスト、skipを成功に数えない |
| 本番反映の状態を区別 | Secret更新とPRマージとdeploy成功を別記録 |

代替: 3.5継続より単価が低く、2.5は今回拒否されたため不採用。リスクは共有キーの利用量・課金先が変わること、実データ精度/上限が未検証なこと。失敗時に既存ルール解析へ戻る挙動は維持。モデルのロールバックは別PR、キー復元には旧値を安全に再取得する必要がある。新規の秘密管理やCIを追加しない。守り手は既存parser/budget試験と本recon。

同一AIによる自己審査APPROVE（この限定実装契約）。正確な既定値2箇所・料金追加・既存試験・正規Secret更新経路を確認済み。独立レビュー、現行在庫精度の合格、GO #3425、本番反映完了を意味しない。


実装追補: 3.1既定2箇所・単価追加・費用assert3件を反映、対象4Pythonのruffとdiff検査成功。GitHub GEMINI_API_KEY更新操作exit0、updatedAt=2026-09-11T01:45:14Zを直接確認。生報告/tmp/reports/LITE31-KEY-SWAP-01.txt。次回以降のdeployで本番へ展開される経路であり、本番反映は未確認。CIは新キーで検証予定、GO #3425未受領。


## 2026-09-11 3.1変更・新キーのCI検証結果

PR #3425の製品head e606ce4fad444331677d34852b7a61cca06d95f0を検証。Backend Tests run34552094629/job103116973038は2544passed・93skipped・302warnings（91.84秒）。従前2543passed/94skippedに対して成功1増・skip1減で、既存実API試験のモデル不可/認証不可等の固定skip警告は0。モデル/費用・既存全試験のCI成功と、実データ精度の未検証を区別する。生ログ/tmp/reports/LITE31-PYTEST-01.log、SHA256 837725e72484fe4eb4e17bb1123f465a83fce6b98471f3f0669424fc461702ee。

PR全チェック34success/8skipped/1failure。唯一の失敗process-artifacts gate job103116955933はGO記録セクション欠落を明示。コード品質の検査失敗ではない。新たなGO #3425は未受領。GitHub Secret更新完了、製品コードはPR提出済み、本番モデル変更と本番キー反映は未確認。PRマージ・本番デプロイは本便未実施。差分の自己レビュー済み、独立レビューではない。次の一手はPOのGO #3425受領後に正式な記録・最新チェック・マージ/デプロイ確認。

この検証後追記は不要な再API実行を避け文書だけのローカルcommitで保持し、同内容をPR本文にも保存する。GO受領後の次便で文書commitもpushする。現行PR検証結果と未push文書を混同しない。


PR #3425 GO受領: PO原文「GO #3425」。2026-09-11 10:55 JSTは受領後記録時刻。コードhead e606ce4fの34success/8skip/残1failureはGO欠落と実測。既存PRへ本人原文を転記し、文書追補をpush後、最新チェックを確認して公式マージする。Mac一時キーファイルはGitHub登録後に削除し不存在確認。平文一時保存だった点をPOへ明示。VPSの現行.env方式は維持。


PR #3427 GO受領: PO原文「GO #3427」。2026-09-11 12:23 JSTは受領後記録時刻。head2031cfa3のCI37成功/8対象外/残1失敗はGO記録欠落と確認済み。rootが製品4SHA256と検収manifestの一致を再確認。本人原文をPR本文へ転記し、最新CI確認後に公式マージする。DB変更なし、バックアップ該当なし。


## EV-20260910-PRODUCT-UI-TAKEOVER

2026-09-10。商品マスタ画面の既存作業場所をPO承認で引継ぎ。基点a5e5a250。未追跡2ファイルの複製・SHA-256一致とfast-forward後の保持を直接確認。報告 /tmp/reports/PRODUCT-UI-TAKEOVER-BACKUP-01/manifest.json、/tmp/reports/PRODUCT-UI-TAKEOVER-SYNC-01.txt。設計の全件条件とAPIのis_active絞込みが不一致。設計13節の自己審査REVISE。製品編集・build・画面試験・QA/本番投入・実装PRは未実施。委任意思受領と代理GO経路の有効化は別。


## EV-20260911-PRODUCT-UI-IMPLEMENT

商品マスタ全件表示（非表示含む）をPO承認。既存worktree引継ぎ後に一覧/CSV確認登録画面・メニュー/翻訳・一覧SQLを実装。直接検証: frontend単体10件、PlaywrightモックE2E2件、check:all、build、対象ruff成功。詳細はdocs/handoff/tcg-product-import/recon.mdの2026-09-11節。報告/tmp/reports/PRODUCT-UI-FIX-VERIFY-02.txt・PRODUCT-UI-E2E-01.txt・PRODUCT-UI-STATIC-01.txt。Docker不在でローカルPG未実行。PR/CI、本番反映、QA/44件投入は未実施。代理GO承認経路未有効、PO原文の番号付きGOを代筆しない。

EV-20260911-PRODUCT-UI-IMPLEMENT追補: PR #3422 head1fd8a4d0は技術CI40成功/対象外6、承認検査1失敗。backend2545成功/93skip。詳細はrecon末尾と/tmp/reports/PRODUCT-UI-CI-PYTEST-FINAL.log。番号付きGO未受領でマージ/配備未実施。QA/44件登録も未実施。


2026-09-11 最終再検査追補: PR #3422 head e2f1063d（前headから文書3件のみ変更）のCIは38成功/6skip/3失敗。backend job103078793511は2544 passed/93 skipped/1 failed。失敗は既存test_inventory_parser_llm_real_api.py::test_real_gemini_call_returns_structured_itemsで、Gemini APIがHTTP429とYour prepayment credits are depletedを返した。集約pytestも失敗。GO記録欠落も継続。前headの2545成功を最終headの成功と混同しない。ログ/tmp/reports/PRODUCT-UI-CI-PYTEST-REPEAT.log。課金・secrets・CI変更、無意味な再試行、マージ/配備は実行しない。外部サービス復旧と番号付きGOが必要。この追補はローカル文書commitに保存し、再CIを無用に起動しないためpushは保留。PR本文には同じ停止理由を反映する。


2026-09-11 08:06 JST（受領後記録時刻）: PO原文「GO #3422」を受領。PR本文へ本人の承認を転記する。Gemini残高の復旧は未確認で、既存実API試験の失敗は未解消。番号付きGOと全検査成功を区別し、マージ/配備/実登録はまだ行わない。課金やCI設定は変更しない。


2026-09-11 本番反映再開: PO原文「商品マスタの本番反映を実行、離席するので最後まで進めてくれデプロイ反映を完了条件とする」。GO #3422は受領済み。外部API停止は別PR #3425の3.1/キー変更とdeploy成功で対応済み。main4774d774を2a85d3d2へ統合。台帳2件はmain全文と自分の追記を保持、商品画面/APIの承認blob不変、日英両側の変更保持を照合。今回の完了条件はマージ・自動deploy成功・本番応答と配布資産確認。CSV実登録・tenant_001試行・44件本登録は本便対象外。最新CI確認中。


EV-20260911-FRONTEND-MOLD-25: Button外観統一。PO原文GOを次便開始として受領。基準e81dd3ec、使用70/18files、外部class18/raw352。根拠docs/handoff/design-system-recon/evidence-20260910/button-appearance-usage.md、design.md§AG。段階移管の同一AI自己審査APPROVE、実装/新番号付きGO未完。PR3427はmergeb16a4224、最終CI38成功/8対象外をroot直接確認済み。


2026-09-11 Button外観検収追補（EV-20260911-FRONTEND-MOLD-25）: 70利用/外部class0、旧raw352コード不変、配色190・寸法1080・raw440前後同値。検収記録: docs/handoff/design-system-recon/evidence-20260910/button-appearance-implementation.md。補助検収/PRは継続、全画面完了ではない。

## EV-20260911-GO-3418-DOC-MERGE

PO原文「追従してPRマージを実行」を、提示済み#3418の文書保存指示として受領。main追従、文書差分/必要検査後に公式wrapperでマージしAPI確認する。全体設計REVISEを維持し機能完成とはしない。P1は実装承認後のbranch作成API403で停止、branch/workflow/PR未作成を再GET確認済み。証拠 docs/handoff/go-record-transcription/recon.md末尾、/tmp/reports/TH-GO-INTAKE-P1-PR-RESULT.json。


商品マスタメニュー配置追補: PO位置指定を受領。既存設計/reconの2026-09-11メニュー配置節へ保存。DesktopShell既存1行移動、権限/URL維持。新規PR/本番反映は未実施。


商品マスタ配置PR #3429提出済み: https://github.com/shingo-ops/salesanchor/pull/3429 。commit6e289bd9、製品変更はDesktopShell既存1行移動。対象eslint/build/台帳/diff成功、既存4項目と移動先/権限維持を自己レビュー。CI確認中、番号付きGO未受領、本番配置は未反映。生報告/tmp/reports/PRODUCT-MENU-PR-01.txt。


## EV-20260911-PRODUCT-DATE-TABS

2026-09-11。商品一覧の発売日降順と作品タブの依頼を受領。「販売日」は既存「発売日」かの確認へPOは「進める」と回答。基点b6644187、専用release/product-master-date-tabs-design、preflight成功、開始時差分0・mainとの距離0/0。実物根拠はdocs/handoff/tcg-product-import/recon.md同日追補、詳細案はdesign.md §14、親はdocs/specs/product-master/README.md §8。コード順・50件ページ・DATE/UUID・tcg_seriesの定義と共通Tabsを直接照合。Context7利用不可のため公式資料を直接確認した。報告は/tmp/reports/TH-PRODUCT-DATE-TABS-ENTRY.json、TH-PRODUCT-DATE-TABS-DESIGN-PREFLIGHT.txt。製品コード/DB/CI/本番に変更なし。詳細設計はPO確認前の提案で、実装移行承認・カード発行・実装検証とは区別する。

同一AIのArchitect自己審査はAPPROVE（設計品質のみ）。9受入条件、7変更対象、既存試験/CI、親仕様/ADRを照合。文書検査エラー0・task-state成功・diff-check成功。報告 TH-PRODUCT-DATE-TABS-DOC-CHECK.json / TH-PRODUCT-DATE-TABS-TASK-CHECK.txt。PO詳細承認と実装承認は未受領。正式カード未発行、製品テスト未実施。

確認用Draft PR #3431: https://github.com/shingo-ops/salesanchor/pull/3431。head b1bda6297f81860ea98594a37b88d60b05af36c0で作成し、.pr-numberとhead指定のPR一覧の一致を直接確認。5文書のみの167行追加。専用worktreeをコマンドにも明示してガードを通過し、mainへの直接コミットなし。台帳のPR番号を公式register-prが登録済み。未マージ・未実装・PO詳細案確認待ち。

EV-20260911-PRODUCT-DATE-TABS追記: PO原文「GO #3431」を受領。2026-09-11 06:29:55 UTCに受領確認（発話日時の推測ではない）。GitHubでPR #3431 OPEN/Draft、head334a084e、CLEAN、CI失敗0を直接確認。preflight成功・作業場所差分0。設計文書の承認/マージを実行する。正式カード未発行、商品機能の実装/配備は未着手。報告 /tmp/reports/TH-PRODUCT-3431-GO-PR.json。


EV-20260911-FRONTEND-MOLD-26: 共通6部品16ボタンの利用先移行。基準7606ca9a（PR3432マージ済み、CI38成功/8対象外）。広域352を先頭btn-*332/専用20と訂正し、BSA002–006/025–035の原文一致を確認。根拠docs/handoff/design-system-recon/evidence-20260910/raw-shared-raw-audit.md/json、設計design.md§AH。PO原文「次を進める」を受領、設計自己審査済み・実装/新PR未完。新CIは最後。


EV-20260911-FRONTEND-MOLD-27: AH移管で390px発送footerの画面外欠けをroot実測（ja左端-30.140625、en-20.484375、旧24）。AH提出条件REVISE、未検証7ファイルを退避予定。先行AIはModal footer折返し＋見本の2製品に限定。通常footer実運用3/見本2を監査し、局所wrap28条件の左右欠け0を確認。詳細design.md§AIとraw-shared-footer-probe/全利用監査。実装/最終検収/新PR未完。

- EV-20260911-FRONTEND-MOLD-28: AI共通Modal footerの実装検収。560pair/輪郭448/Story4、品質5項目exit0/189unit、限定review APPROVE、2製品hash一致。証拠: docs/handoff/design-system-recon/evidence-20260910/modal-footer-implementation.md。Generatorはbrowser、rootは品質と結果再集計を実行。PR番号付きGO・マージ・PO目視未完。

## EV-20260911-ONEPIECE-COMPLETION

PO原文「全て完了させてくれ」、登録範囲回答「単独販売の商品とセットまで（推奨）」を受領。今回の公開送信制限はPO原文「解析コード・設計文書は社外秘→これは一旦解除」で一時解除。顧客原文・実データ・秘密情報の公開許可には拡張しない。

専用release/onepiece-analysis-completionはorigin/main 7606ca9a起点、preflight成功。設計design-keyword.md §15/改訂1の同一AI自己審査APPROVE、カード形式検査成功。製品3ファイルへ数字境界、末尾単位、単独完売備考、配信除外、商品区分IDに基づくBOX除外を実装。関連110試験成功、先行336試験成功。固定1630の区分参照切替による判定変化0。登録API経由の新規BOXのPSA誤一致を変更前の実DBで1件再現し修正後合格。全体試験実行中、未コミット・PR未提出・未配備。26候補の参照コード静的検査blocking0、残33の確認継続。DB登録・本番再解析・配信は未実施。


PR #3434検証追記（実装HEAD4c5d1893）: GitHub run34577363592で2586成功/95skip、coverage62.41%、必須13検査成功。ローカル初回の読み込み依存1失敗を修正し対象39件成功。全体再試験は試験DBの7.8GBが100%・空き0（DiskFull）で2472成功/25失敗/90errors/94skip。成功扱いせず上記GitHubの新DBで確認した。他者の試験DBを削除せず、このMacの共有試験環境は容量復旧まで使わない。make lint-ci終了0、mypyは既存警告運用で型エラー0ではない。

process-artifacts gateは番号付きGO記録なしで失敗。一般的なマージ指示は受領済みだが、GO #3434の原文を代筆しない。未マージ・未配備。26登録候補は静的検査のみで未投入。書籍区分/冊の回答と33候補の確認は残る。本番再解析・配信未実施。

EV-20260911-PRODUCT-DATE-TABS引継ぎ: PO原文「次を進める」を、直前の実装開始/カード作成・引継ぎ確認への承認として受領。#3431マージa66e9382確認済み。専用実装worktreeは6c55e40d起点、対象7ファイル差分0、preflight成功。TH-PRODUCT-DATE-TABS-IMPL-01.txtを作成。製品変更/依存導入/試験/実装エージェント起動は未実施。Docker socket不存在のためPG実行環境の制約をカードへ明記。承認済み設計の条件を緩めず、正式PG/CI/QA/製品GOを後続条件として維持する。

TH-PRODUCT-DATE-TABS-IMPL-01正式検査: card-lint exit0（L24の長行警告8件のみ）、24手順の連続性、19コマンドのcd先実在、入力フルパス実在、未記入目印0、停止/再開/報告経路、承認済み7製品ファイル境界を同一AIで手動照合。独立レビューではない。証拠 /tmp/reports/TH-PRODUCT-TABS-CARD-LINT.txt / TH-PRODUCT-TABS-CARD-REVIEW.json。task-state/diff成功。カード作成・検査済み、実装役への提示待ち、製品コード未変更。

準備Draft PR #3433: https://github.com/shingo-ops/salesanchor/pull/3433。作成head346f7d72、.pr-numberとhead指定一覧の一致を直接確認。製品ファイル差分0、文書5件のみ。実装役へTH-PRODUCT-DATE-TABS-IMPL-01を提示できる状態。自動起動/実装実行は行っていない。後続実装は同じPRを更新し、実装完了までマージしない。

EV-20260911-PRODUCT-DATE-TABS実装追補: POが実装役1名への委任を承認し、カード範囲の7製品ファイルを実装した。開始時preflight/差分0確認。画面単体14 passed、Chromium E2E5 passed（API/authモック）、対象ruff/厳格eslint/build/diff成功。check:allはexit0（0errors/221warnings、追加試験3警告は修正後に対象eslint/単体成功）。make lint-ciはexit0だがmypy診断153件を警告扱いで保持。正式PG/HTTP試験はDocker不在で未実行、CI/QA実接続/配備も未実施。実測表はrecon同日実装追補、生出力は/tmp/reports/TH-PRODUCT-DATE-TABS-IMPL-01.txt。ローカル実装の記録であり、実装コミットの公開/GO/マージは行っていない。


### 2026-09-11 PR #3433 の公開・マージGO受領

PO原文: 「進めてくれ GO#3433」。受領記録時刻 2026-09-11T08:11:21.255931+00:00（記録時の実測であり発話時刻の推定ではない）。対象はPR #3433の商品マスタ発売日順・作品タブ。ローカル実装12e6b13cを確認し、main 7606ca9a041e315b81040373e8f4ddebbc562133へ追従。競合はtasks/todo.mdの2テーマの行で、本テーマの実装行とmain側の金型化行を保持。製品ファイルの競合なし。公開後の実PG/CI、配備結果とtenant_001実接続確認は、GOの受領と分けて記録する。


PR #3433 CI追補: f09d3659の実DB CI（run34578271232）は2566 passed/95 skipped、process-artifacts成功。試験テーブル独自複製をschema gateが拒否したため、cffe3b2eで両隔離schemaを正式migrationから生成する形へ修正。ルール変更・例外追加なし。対象ruff/正式schema gate成功。mainのPR #3434（2ac5e81a）を追従し、別テーマ証跡の追記を保持。最新統合HEADのCIを再検証する。追従前の成功を最新HEADの合格に流用しない。tenant_001実接続・人の確認は未実施。報告 /tmp/reports/TH-PRODUCT-3433-SCHEMA-FIX.txt、TH-PRODUCT-3433-PG-CI-INITIAL.txt。

EV-20260911-FRONTEND-MOLD-29: AI PR3435 ready提出を.pr-number/head指定一覧/APIで一致確認。main ec173b7e統合3935e17d、2製品hash不変、root統合unit200成功。証拠modal-footer-implementation.md/root-main-verification.json/post-main-unit.log。CI確認中、GO #3435未受領・マージ/PO目視未完。

EV-20260911-FRONTEND-MOLD-30: 2026-09-11 18:01 JST（受領後記録）: PO原文「GO #3435」を受領。対象はPR3435の共通Modal footer修正。製品2hashは検収版と同一。最新CI確認後に正式merge、PO目視/本番確認は未実施。AH16移管はこの前提のマージ後に再開、新CIは最後。 証拠: PR https://github.com/shingo-ops/salesanchor/pull/3435 のGO記録と検収記録。


```text
id: EV-20260911-PRODUCT-CSV-TEMPLATE-DESIGN
date: 2026-09-11
agent: Codex design partner (Planner then Architect; same AI)
task: 空CSVサンプルとUser型不整合の限定修正設計
scope: tcg-product-import既存design/recon・台帳のみ
evidence:
  - type: file
    reference: docs/handoff/tcg-product-import/recon.md 同日再開調査
    summary: adc8bc4d基点、10列/必須5列、User返却とget不一致を照合。前便報告と今回の直接検算を区別
  - type: command
    reference: AST隔離検算（reconに入力・対象関数・assert結果を記載）
    summary: BOM見出し10列を現行parse_rowsへ渡し0行/0エラー。現行endpointでget AttributeError・commit await0回を再現
  - type: external
    reference: https://vite.dev/guide/assets#the-public-directory
    summary: Context7利用不可のため公式資料代替。public資産の配信/build経路を確認
confidence: high
tradeoff: 実HTTP/本物User/実DB成功は未検証。部分登録・履歴空白・digest承認証明の限界を保持
decision: design§15自己審査APPROVE。PO合意はサンプル形式と設計進行のみ。詳細案実装/GOは未承認
follow_up: 詳細案を提示し、実装承認後に正式カード検査・引き継ぎ。44件投入は別段階
```


```text
id: EV-20260912-PRODUCT-CSV-CARD
date: 2026-09-12
agent: Codex design partner
task: PO承認済み商品CSV設計の正式実装カード準備
scope: docs/handoff/tcg-product-import・既存台帳
evidence:
  - type: file
    reference: docs/handoff/tcg-product-import/design.md 2026-09-12承認追記
    summary: 設計承認とカード準備へのPO原文「進める」を記録。GO・自動起動に読み替えない
  - type: command
    reference: bash scripts/card-lint.sh docs/handoff/tcg-product-import/card-template-impl.md
    summary: exit0・違反0・長行警告4件。18手順/実在パス/既存7+新規1ファイル/出力未使用を追加照合
confidence: high
tradeoff: 同一AI自己照合。Docker不在、実DB検証は未実行のため実装後CIに残す
decision: 正式カード準備済み、実装役未起動、製品未変更
follow_up: 実装役の差分と生報告を読み取り確認。公開・実DB検証は後続便
```


```text
id: EV-20260912-PRODUCT-CSV-IMPLEMENT
date: 2026-09-12
agent: csv_card_executor (implementation), Codex design partner (read-only review)
task: 空CSVサンプルとUser型の限定修正
scope: design§15の8製品ファイル、製品未コミット
evidence:
  - type: log
    reference: /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt
    summary: 実装役が単体13/E2E7/build/check:all/lint-ciを実行し成功。親は生出力を確認
  - type: command
    reference: /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02-parent-review.json
    summary: 親が8ファイル差分、BOM/CRLF/10列/0行、日英キー、日英画像を直接確認。Python2ファイルruffは正規権限審査後exit0
confidence: high
tradeoff: frontend警告218/mypy153残存。HTTP回帰/実PG/CI/本番QAは未実行、成功を主張しない
decision: ローカル実装と差分確認済み。公開・マージ・本番操作なし
follow_up: 別便で製品差分を保存・公開し正式CIで追加試験を検証
```


```text
id: EV-20260912-PRODUCT-CSV-PUBLISH
date: 2026-09-12
agent: csv_card_executor (publication), Codex design partner (read-only verification)
task: 空CSVサンプルとUser型修正の製品PR公開・CI確認
scope: PR3438、8製品＋4設計文書
evidence:
  - type: pr
    reference: https://github.com/shingo-ops/salesanchor/pull/3438
    summary: HEAD ff008f180e150be2241ad7d6d2d2f292a439f900、OPEN、12ファイルを親が直接確認
  - type: command
    reference: /tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01-parent-final.json
    summary: CI40成功/6対象外/1失敗。全pytest/PostgreSQL集約は成功。process-artifacts失敗
  - type: command
    reference: /tmp/reports/CARD-PRODUCT-CSV-PUBLISH-01-parent-gate.json
    summary: 手元の設計/維持/引用検査は各エラー0、GO欄欠落を検出。CIログではない
confidence: high
tradeoff: AC5修正前への復元失敗確認未実施。CI個別ログ/総件数/skip件数未取得。全受入完了ではない
decision: 製品PR公開・CI確認済み。GO/マージ/本番反映は未実施
follow_up: 残る回帰確認とCI失敗詳細を確認してからPOへマージ判断を提示
```


```text
id: EV-20260912-PRODUCT-CSV-VERIFY
date: 2026-09-12
agent: csv_card_executor (contrast execution), Codex design partner (evidence review)
task: PR3438の残件検証
scope: HEAD ff008f180e150be2241ad7d6d2d2f292a439f900、製品変更0
evidence:
  - type: log
    reference: /tmp/reports/SA-CSV-REMAINING-GATE-20260912.txt
    summary: 親が正規権限審査でCI実ログ取得。GO記録欄欠落が失敗原因
  - type: log
    reference: /tmp/reports/SA-CSV-BACKEND-CI-20260912.txt:1066
    summary: 全suiteの2601 passed/95 skipped/301 warnings/110.42sを親が直接確認
  - type: command
    reference: /tmp/reports/CARD-PRODUCT-CSV-AC5-CONTRAST-01.json
    summary: 既存HTTP試験関数直接await。旧式3ケースAttributeError、現行3成功。8製品SHA前後一致、通信/DB試行0、復帰assert成功。親はスクリプト/結果を読取確認
confidence: high
tradeoff: 対照検算はpytestではなくDB/監査mock付きASGI内HTTP。実商品登録の証明ではない
decision: AC5とCI失敗原因の残件解消。PO GO未取得、マージ/本番未実施
follow_up: 本番影響と直前確認を提示しPR3438の番号付きGO判断へ
```


```text
id: EV-20260913-PRODUCT-CSV-PRE-RELEASE
date: 2026-09-13
agent: csv_card_executor (main integration), Codex design partner (read-only checks)
task: PR3438本番反映前確認
scope: HEAD2184092c4f7cafcb43188626490c892db5ed82d7、製品変更0
evidence:
  - type: command
    reference: /tmp/reports/SA-CSV-PRE-RELEASE-FINAL-20260913.json
    summary: 親がHEAD/OPEN/MERGEABLE/CI38成功6対象外1失敗確認。全pytest/PG成功、失敗はGO記録不足
  - type: log
    reference: /tmp/reports/SA-CSV-PRE-RELEASE-20260913.txt
    summary: 実装役がmain5b21b3b8統合・製品8SHA不変・12ファイル境界・pushを確認
  - type: log
    reference: /tmp/reports/SA-CSV-LATEST-DEPLOY-20260913.txt:583
    summary: 前回配備の20260912_193916.sql.gz 6.7M生成、main5b21b3b8配備/health成功を実ログ確認。本番HTTP200を別途直接確認
confidence: high
tradeoff: 過去backup生成証拠であり現物存在/復元試験は未確認。今回直前backupは配備時に取得する既存手順
decision: POの番号付きGO判断へ。GO/マージ/本番変更は未実施
follow_up: GO受領後に正式反映カード。配備時backup/HEAD/health/空CSV実資産の検証を完了条件とする
```
