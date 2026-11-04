# 実装報告 2: アプリ内の鈴 — 宛先の改訂（design.md §4-改訂1・§4-改訂2）

## ① 終わり方

**完了**（BLOCKED・NEEDS_DECISION なし）。設計 §4-改訂1・§4-改訂2 のとおり、宛先の関数・設定の表・API・画面の区画・試験を入れた。PR は作っていない。

## ② merge の結果

- `git fetch origin` → 作業場所を `scripts/new-worktree.sh release/in-app-notice-bell` で作成 → `git switch -C release/in-app-notice-bell origin/release/in-app-notice-bell`（HEAD と origin が同じことを確認）→ `git merge origin/main`（rebase・force・reset は不使用）。
- 衝突は 2 件。どちらも機械的に解けた。
  1. `scripts/run_all_migrations.sh`: 末尾に両側が 1 行ずつ足した形。両方残した（`20261103_150000_create_user_notices.sql` → `20261103_200000_add_google_calendar_import_sync.sql` の日時順）。
  2. `docs/adr/README.md`: 自動生成物。main 側を取り、`node scripts/generate-adr-index.js` で作り直した（218 件）。
- merge commit: `31a469ccd`。注: クラウドの決まりには「main を取り込まない」とあるが、この依頼の 1/5 が merge を明示しているため依頼に従った。PR の必須の点検が「main の新しいファイルをこの枝で足したもの」と数えて落ちる場合は、Opus が判断してほしい。

## ③ 変えたファイル

backend:
- `backend/app/services/user_notices.py` — 宛先を改訂。担当者 1 人以上 → 担当者だけ（別々なら全員）。0 人 → `notice_fallback_recipients` の有効な人。0 件か有効 0 人 → `system_key='owner'` の有効な人全員。admin は足さない。Discord の名前呼びは同じ `resolve_notice_recipients` を使うので同じ宛先。
- `backend/app/routers/notice_fallback_recipients.py`（新規 router 1 つ）— `GET` / `PUT /api/v1/notice-fallback-recipients`。両方 `require_permission("notifications.manage")`。GET は `selected`・`defaulted_to_owner`・`candidates[{user_id,name}]`（name は `COALESCE(NULLIF(u.full_name,''),u.username)`。Discord id・メールは返さない）。PUT は全置換、別会社・無効・存在しない id が 1 つでもあれば 422。表はスキーマ名つき（`tenant_table_ref`）、commit のあと `reset_tenant_context`（ADR-072）。
- `backend/app/main.py` — router 登録（import 順は ruff で整列）。
- `backend/app/services/tenant.py` — `_TENANT_TABLES_SQL` に `notice_fallback_recipients` を追加。
- `backend/app/realtime/topics.py` — **設計の「触ってよい範囲」に書かれていないが、1 行だけ触った**。`PUT /api/v1/notice-fallback-recipients` を `NO_SIGNAL_ROUTES` に載せた（`test_every_write_route_is_in_exactly_one_table` が、どちらの表にも無い書き込み口で落ちるため。既存の `POST /notices/{id}/read` と同じ扱い）。範囲外なので Opus が確認してほしい。
- `migrations/20261103_150000_create_user_notices.sql` — 同じ `DO $$` 走査に `notice_fallback_recipients(user_id INTEGER PRIMARY KEY, updated_by INTEGER, updated_at TIMESTAMPTZ DEFAULT now())` を追加（追加のみ・冪等）。`run_all_migrations.sh` の行は既にあるので変更なし。
- `backend/tests/test_user_notices.py` — 宛先の試験を改訂分に差し替え、設定 API の試験を追加。
- `frontend/api-contract/openapi.json` — `export_openapi` で作り直した（作り直して差分が無いことも確認）。

frontend:
- `frontend/src/pages/notifications/NoticeFallbackSection.tsx` / `.css`（新規）— 区画「担当者がいないときに受け取る人」。部品は既存の `MultiSelect`（layout="popover"）と `Button` だけ。色・余白・角はトークンのみ。
- `frontend/src/pages/notifications/NotificationsPage.tsx` — `hasPermission("notifications.manage")` のときだけ区画を出す。**表より上に置いた**（下に置くと、スマホで選択の一覧が下のタブバーに隠れて 2 件目以降が押せなかったため。e2e で確認）。
- `frontend/src/locales/ja.json` / `en.json` — `notices.fallback.title / help / defaultOwner / clear / count / saved`（同じキー）。
- `frontend/tests-e2e/visual-language/notice-fallback.spec.ts`（新規）— 「権限があると区画が出る・選んで保存できる（PUT の中身も確認）」「権限が無いと出ない」。
- `npm run generate:api-types` は実行した（`src/api/generated/schema.d.ts` は git 管理外のため commit には出ない）。

docs: `docs/handoff/in-app-notice-bell/impl-report-2.md`（この報告）、merge に伴う `docs/adr/README.md`・`scripts/run_all_migrations.sh`。

## ④ 流した命令と結果

| 命令 | 通過 | 失敗 |
|---|---|---|
| `pytest tests/test_user_notices.py tests/test_discord_outside_ticket_notice.py tests/test_realtime_topics.py`（`--no-cov`） | 49 | 0 |
| `pytest -k "tenant_create or create_tenant or tenant_service or tenant_sql or migration or openapi or adr072 or adr_072"`（`--no-cov`） | 94（skip 38） | 0（error 12 は下の「流せなかった物」） |
| `ruff check app tests/test_user_notices.py tests/test_discord_outside_ticket_notice.py` | All checks passed | 0 |
| `npx tsc --noEmit -p .`（generate:api-types 後） | エラー 0 | 0 |
| `npm run lint` | エラー 0（警告 59 は既存・今回のファイルは警告 0） | 0 |
| `check:i18n-missing-keys` | PASSED | — |
| `check:css-colors / css-values / css-var-fallbacks / dark-parity / stylelint / css-fixed-position / page-layout / new-tokens / page-size / icon-sync / claude-size / jsx-emoji / nav-sync / content-toolbar / page-folder / breakpoint-sync / mobile-responsive-structure2 / color-token-sync / css-class-naming / status-direct-writes` | すべて PASSED（exit 0） | 0 |
| `vitest run`（MultiSelect・Popover・batch3dPages・FormActionButtonMigration・lib/realtime の 5 ファイル） | 69 | 0 |
| Playwright `notice-bell.spec.ts`（3 幅 × 4 本） | 12 | 0 |
| Playwright `notice-fallback.spec.ts`（3 幅 × 2 本） | 6 | 0 |
| Playwright `desktop-shell.spec.ts` | 6 | 0 |

試験で確かめた内容（backend）: 担当者あり→担当者だけ（owner・admin は入らない）／同じ人が複数 lead でも 1 回／別々の担当者→全員／なし・設定なし→オーナー全員（admin は入らない）／担当者が無効・別会社・不在→オーナー／設定あり→設定の人／担当者がいれば設定は使わない／設定の人が全員無効・別会社・不在→オーナー／一部無効→有効な人だけ／権限なし 403（GET・PUT とも。表は変わらない）／別会社・無効・不在 id は 422（表は変わらない）／candidates に Discord id とメールが無い／保存後の次の宛先決定が設定の人になる／通知の流れ（Discord の名前呼び・鈴の行・合図）が担当者だけになる。

## ⑤ 流せなかった物・残っている物

- **`npm run check:stories` が失敗**（`NoticeBell.tsx`・`NoticeRow.tsx` に `.stories.tsx` が無い）。これは前回（impl-report.md）の作りが原因で、今回の変更の前から落ちている（変更を退けた状態でも同じ失敗を確認）。`.stories.tsx` の追加は今回の設計の範囲外なので手を付けていない。CI に `check:stories` が入っていれば PR で落ちる。Opus が判断してほしい。
- **PostgreSQL が要る試験は流せていない**: `-k migration` などで出た `ERROR` 12 件（`test_llm_usage_events_migration_pg` など）は、使い捨ての DB サービスが無いため（この変更とは無関係の既存の試験）。新しい migration の SQL（`DO $$` ＋ `notice_fallback_recipients`）自体は PostgreSQL で流していない。構文は既存の `user_notices` と同じ形で書いただけで、実際の適用確認は未実施。
- `_TENANT_TABLES_SQL` の新テナント作成経路は PostgreSQL で流していない（文字列の追加のみ。`pytest -k tenant` 系の既存試験は上の表のとおり通過）。
- スマホ幅で区画の見た目は e2e の機能確認のみ。目視は PO の確認が要る。
- 一時ファイル（`frontend/playwright.tmp.config.ts`・`test-results/`・`playwright-report/`）は commit していない（config は削除済み、残りは git 管理外）。
