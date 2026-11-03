# 実装報告: アプリ内の鈴（in-app-notice-bell）

## ① 終わり方と理由

終わり方: **BLOCKED**（作りは設計どおり全部入っている。止まった理由は後片付けだけ）。

- 後片付けの命令（試験用の一時ファイルと test-results の削除に使った再帰削除）が、見張り（PreToolUse フック）に「不可逆操作」として止められた。言い換えず、ここで締めた。
- 一時ファイル `frontend/playwright.tmp.config.ts`（事前導入のブラウザを指す仮の設定）が作業場所に未追跡で残っている。**commit していない**。消してよい（`test-results/` は未追跡の生成物）。
- 設計との違い・判断（Opus が確かめる点）:
  1. `git merge origin/main` は**しなかった**。クラウドの決まり（main を取り込まない）を優先した。枝は main より 32 件遅れている。合流は Opus が判断。
  2. 登録先: 設計は `deploy.yml` と書くが、実物は deploy.yml の注記（`deploy.yml:228`）どおり `scripts/run_all_migrations.sh` に追記する形。そこへ 1 行足した（`deploy.yml` は変更していない）。migration-guard は両方を認める。
  3. API のパス: 設計は `/api/notices`、実物の全 router は `/api/v1` 配下のため `/api/v1/notices` に揃えた（設計 §7-1 の「既存の router に揃える」）。画面は `api.get("/notices")`（`/api/v1` は自動で付く）。
  4. `BellOutline` は公開名で export されていなかったため `constants/icons.tsx` に export を 1 行足した。
  5. 鈴を足すとページ右上ボタンが隠れるため、`--page-header-avatar-clearance`（tokens.css）に鈴の分を足した（PC のみ）。**スマホ**は鈴が画面右上の固定で、ページ側の右上ボタンと重なる画面があるかは未確認（目視が要る）。
  6. `migration-test.yml` の最小定義は不要と判断（migration は pg_namespace 走査だけで、ほかの表を参照しない）。AI 閲覧ビューの分類には足していない（設計どおり）。
  7. 新規テナント作成の表の置き場所は `backend/app/services/tenant.py` の `_TENANT_TABLES_SQL`（lead_channels の直後）に足した。

## ② 各コマンドの最後の行

- `pytest tests/test_user_notices.py tests/test_discord_outside_ticket_notice.py tests/test_realtime_topics.py`: `41 passed, 71 warnings in 12.17s`
- `pytest -k "tenant_create or create_tenant or tenant_service or tenant_sql"`: `13 passed, 2 skipped, 14 warnings`
- `pytest -k tenant`（広め）: `229 passed, 57 skipped, 2 errors`（2 件は `test_tcg_work_matching_integration` が「Disposable CI service required」で出る CI 専用 DB の試験。この変更とは無関係）
- `ruff check app tests/test_user_notices.py tests/test_discord_outside_ticket_notice.py`: `All checks passed!`
- `npm ci`: 完了（警告のみ）
- `npm run generate:api-types` の後に `npx tsc --noEmit -p .`: エラー 0（生成前の 4 件は生成物 `api/generated/schema` が無いことが原因で、この変更と無関係）
- `npm run lint`: `✖ 59 problems (0 errors, 59 warnings)`（既存。追加・変更したファイルは `--max-warnings=0` で 0）
- `check:css-fixed-position`: `✅ CSS position:fixed チェック PASSED`
- `check:i18n-missing-keys`: `✅ i18n key check PASSED (all prefixes)`
- `check:css-colors` / `check:dark-parity` / `check:css-var-fallbacks` / `check:css-values` / `check:stylelint` / `check:icon-sync` / `check:page-layout`: すべて PASSED（stylelint は出力なし・終了 0）
- `npx playwright test --list` で notice-bell.spec が vl-mobile-390 / vl-tablet-768 / vl-desktop-1280 の 3 幅に各 4 本（計 12）出る
- 参考: 事前導入のブラウザを指す仮の設定で notice-bell.spec を 3 幅で実行: `12 passed (36.5s)`
- 未実施: `desktop-shell.spec`（既存の回帰）と `vitest`。後片付けの命令と同じコマンド列に入れていて止められたため、流せていない。

## ③ 触ったファイル一覧

backend:
- backend/app/services/user_notices.py（新規: 宛先・Discord id・知らせ作成・合図）
- backend/app/routers/notices.py（新規: GET /api/v1/notices・POST /api/v1/notices/{notice_id}/read）
- backend/app/discord_gateway/outside_ticket_notice.py（順番変更・名前呼び・鈴）
- backend/app/main.py（router 登録）
- backend/app/realtime/topics.py（notices・NO_SIGNAL_ROUTES に既読の口）
- backend/app/services/tenant.py（新規テナントの表）
- backend/tests/test_user_notices.py（新規）
- backend/tests/test_discord_outside_ticket_notice.py（t1 の期待を更新）
- migrations/20261103_150000_create_user_notices.sql（新規）
- scripts/run_all_migrations.sh（登録 1 行）
- docs/adr/ADR-1016-realtime-change-signal-standard.md（改訂 2026-11-03）
- docs/adr/README.md（generate-adr-index.js の生成物）
- frontend/api-contract/openapi.json（export_openapi の生成物）

frontend:
- frontend/src/components/NoticeBell.tsx / NoticeBell.css / NoticeRow.tsx（新規）
- frontend/src/components/DesktopShell.tsx（`.top-right-cluster` に鈴とアバターを並べる）
- frontend/src/components/MobileShell.tsx（右上に鈴）
- frontend/src/constants/icons.tsx（BellOutline の export）
- frontend/src/lib/realtime/topics.ts（notices）
- frontend/src/locales/ja.json / en.json（notices.*）
- frontend/src/tokens.css（鈴の寸法トークン・clearance）
- frontend/tests-e2e/visual-language/notice-bell.spec.ts（新規）
- docs/handoff/in-app-notice-bell/impl-report.md（この報告）

## ④ 止めた所の file:line

- 止まったのは製品コードではなく後片付けの命令。止めた見張り: PreToolUse フック「BLOCKED(cloud): 'rm -rf' は不可逆操作です」。
- 設計に無い判断で止めた所: なし（NEEDS_DECISION 該当なし。MobileShell の右上に既存の固定部品は無かった: `frontend/src/mobile-shell.css` の固定は下端のタブバーと下からのシートだけ）。
- 注意点（確認が要る）: `backend/app/discord_gateway/outside_ticket_notice.py` の `_create_bell` は、失敗時に 1 度だけ立て直して再試行する（設計 §6-7 の「鈴の失敗は外へ出さない」の範囲）。本番の PostgreSQL での実機の確認（K4・K7）は未実施。
