# 段A 実装カード（知らない機械からのログインを止める・第2版）

- 対象: docs/handoff/auth-new-device-approval/design.md 第6.1版 §3（D1〜D16）・§4 段A（A-1・A-2・A-3）・§6・§7。ADR-1055（Proposed）。合格の基準は kgi.md の K1〜K9（PO 承認済 2026-11-01）。
- 中身の正本: 何をどう作るかは design.md §4 段A の文のとおりに作る。このカードは「順番・先に確かめること・止まる条件・受入」を足す。design.md とこのカードが食い違うときは止まって Opus へ返す（自分で選ばない）。
- 根拠の写し: S=origin/main bf3ad441638ed1084c50c5528a435a294b01469f。design.md の行番号は基準 7e9155163 で読んだもので、S までに本線が進んでいる。実装の前に §3(a) で行を合わせ直す。§0 V-2 の行は origin/main dc99a062e でも同じだった（第1版の審査）。
- 前提: このカードと design.md・kgi.md・ADR-1055 は、設計書だけの PR で本線に入れてから流す。手順1 の後に origin/main に docs/handoff/auth-new-device-approval/design.md が無ければ、停止して BLOCKED: で返す。
- 読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md・guards/07-migration.md・guards/10-executor.md・scripts/agent-hooks/cloud/rules.md。実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。.pr-number・gh-pr-create-safe.sh・gh-pr-merge-safe.sh はクラウドでは使わない。PR は設計担当（Opus）が手元で scripts/gh-pr-create-safe.sh で作る。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第2版（Opus 作成）。第1版の審査 REVISE（要修正3・軽微5）を直した。
- 受領確認: 実装役は着手の最初の報告に「段A カード 第2版 前半（または後半）を受け取った・S=bf3ad4416」と書く。

## 0. 設計からの直し（V）
- V-1 2回に分けて流す（変更は一度に1つ・1回の作業の量を抑える）。同じ枝 release/new-device-approval-stage-a に積む。PR は後半の push の後に1つだけ作る（design.md の「PR-A」は1つのまま）。
  - 前半: A-1（migration・試験の表定義・ai_cloud の分類・守りの登録）と A-2（backend 全部と pytest）。
  - 後半: A-3（frontend 全部と Vitest）と API の形（openapi.json）。
- V-2 本線が進んだことで、すでに分かっている行のずれ（S で確かめた）:
  - S .github/workflows/migration-test.yml の auth_events の最小定義は :1395-1409（design.md の :1338-1352 から動いた）。
  - S backend/app/realtime/publisher.py は :19-22 の CHANNEL_*・:28 tenant_channel・:32 _channel_for・:42 _payload・:64 publish_change・:78 publish_change_sync（design.md と同じ）。
  - S backend/app/realtime/hub.py:28-31 の Connection・S backend/app/routers/realtime_events.py:80 の Connection(...)（design.md と同じ）。S backend/app/realtime/topics.py:86 の NO_SIGNAL_ROUTES（同じ）。
  - S migrations/20261024_100300_create_ai_cloud_views.sql:3 の「1035 行」・S backend/tests/ops/test_ai_cloud_views.py:477 の 1035・S docs/handoff/cloud-case-ai/stage1-column-class.tsv は 1036 行（design.md と同じ）。本番の ai_cloud_meta.column_class は 1035 行（2026-11-01 01:49 JST・reader 鍵）。
  - S scripts/run_all_migrations.sh の一覧の最後の登録は :1205 の 20261031_210000_create_ops_case.sql。
  - S docker-compose.yml は celery-worker が :222・celery-beat が :317・一番外の volumes: が :562・networks: が :567（design.md の :219・:314 から動いた）。geoip の volume は一番外の volumes: にも足す。
  - S の検査の台本の置き場: scripts/check-migration-value-writes.py・scripts/lint_tenant_schema.py・scripts/check-migration-registration-exists.sh。
  - ADR-1016 の改訂の注記（ADR-1055）は設計の PR で既に足してある。
- V-3 本番の事実（reader 鍵・2026-11-01 01:49 JST・/tmp/CC報告ファイル/nd-card-prod-owner.txt の続き）:
  - public.auth_events・auth_refresh_tokens・users の持ち主は3つとも jarvis（migration を流す役と同じ）。ALTER TABLE ... ADD COLUMN IF NOT EXISTS は通る。
  - public.auth_events の今の列は id・event_type・path・method・status_code・client_ip・user_agent・duration_ms・created_at。user_id・reason・is_new_device はまだ無い。

## 1. 触るファイル（変更前→変更後。中身は design.md の該当の文）
| # | ファイル | 変更前（S） | 変更後 | 回 |
|---|---|---|---|---|
| 1 | 新 migrations/20261101_120000_add_new_device_approval.sql | 無い | A-1 の3表・2つの列の追加・索引・全列 COMMENT・GRANT（S migrations/20261013_160000_add_self_hosted_auth_tables.sql の GRANT と同じ書き方）。冪等（IF NOT EXISTS）。RLS は付けない | 前半 |
| 2 | scripts/run_all_migrations.sh | :1205 が最後の登録 | :1205 の後に #1 を run_sql で1行足す（同じ書き方の説明の行を1行付ける） | 前半 |
| 3 | .github/workflows/migration-guard.yml | :224 PUBLIC_TABLES | 末尾に user_trusted_devices auth_login_requests user_recovery_codes | 前半 |
| 4 | migrations/20261024_100300_create_ai_cloud_views.sql | :3 が 1035 行・:13〜 INSERT | A-1 の表の19行を表ごとに1行で足す・:3 を 1054 行に | 前半 |
| 5 | docs/handoff/cloud-case-ai/stage1-column-class.tsv | 1036 行 | 同じ19行を足して 1055 行 | 前半 |
| 6 | scripts/migration-guard/reference-allowlist.tsv | :7 の sha256 | #4 を直した後の sha256。4列目の末尾に「 / ADR-1055 design §4 A-1（19行追加）」を足す | 前半 |
| 7 | backend/tests/ops/test_ai_cloud_views.py | :477 が 1035 | 1054。新しい19列に column_class の行があることを名前で確かめる試験を1つ足す | 前半 |
| 8 | backend/tests/conftest.py | :320-321・:1341-1343 | A-1 の「試験の表定義」のとおり | 前半 |
| 9 | .github/workflows/migration-test.yml | :1395-1409 の auth_events | 新しい3列を足す | 前半 |
| 10 | 新 backend/app/auth/devices.py・recovery_codes.py・geo.py・origin.py | 無い | A-2 のとおり | 前半 |
| 11 | backend/app/auth/self_tokens.py・dependencies.py | — | A-2 のとおり（create_access_token の sid・issue_refresh_token の trusted_device_id・RotatedRefresh・sid の失効の確かめ・resolve_current_session と get_current_session） | 前半 |
| 12 | backend/app/routers/auth.py | — | A-2 のとおり（login・refresh・passkey verify・password reset confirm・password change・新しい口・_require_app_origin を origin.py へ移して読む） | 前半 |
| 13 | 新 backend/app/routers/login_approvals.py・super_admin_login_requests.py | 無い | A-2 のとおり。backend/app/main.py に2つの include_router を足す | 前半 |
| 14 | backend/app/realtime/topics.py・publisher.py・hub.py・backend/app/routers/realtime_events.py | — | A-2「知らせ」のとおり | 前半 |
| 15 | backend/app/services/auth_mail.py | — | send_new_device_mail を足す | 前半 |
| 16 | backend/app/middleware/audit.py | — | A-2「記録」のとおり | 前半 |
| 17 | backend/app/tasks/maintenance.py・celery_app.py | — | 片付け・期限切れ・refresh_geoip_db の作業と登録 | 前半 |
| 18 | 新 backend/app/cli/__init__.py・issue_trusted_device.py | 無い | A-2 のとおり | 前半 |
| 19 | backend/requirements.txt | — | maxminddb==3.2.0 | 前半 |
| 20 | docker-compose.yml | — | backend の environment に GEOIP_DB_PATH・AUTH_DEVICE_APPROVAL・AUTH_DEVICE_BOOTSTRAP_CUTOFF（design.md A-2・B-2 の形）。volume geoip を celery-worker に書き込みで・backend に :ro で /geoip。celery-beat には付けない。一番外の volumes:（:562）に geoip: を足す | 前半 |
| 21 | 新 backend/tests/test_new_device_approval.py | 無い | design.md §6 の pytest の列を全部 | 前半 |
| 22 | backend/tests/test_viewer_isolation.py・test_realtime_topics.py | — | A-2 のとおり（_PUBLIC_NO_AUTH_ROUTES に2つ・:24 の本数・USER_TOPICS の一致） | 前半 |
| 23 | docs/adr/ADR-1016-realtime-change-signal-standard.md・docs/adr/README.md | 注記は設計の PR で入っている | ADR-1016 は直さない（注記が無ければ停止）。node scripts/generate-adr-index.js を流し、README.md が変わったときだけ入れる | 前半 |
| 24 | frontend/src/lib/auth/selfAuth.ts・selfAuth.test.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/components/AllLegacyButtonOperationMigration.test.tsx | — | A-3 のとおり | 後半 |
| 25 | frontend/src/pages/login/LoginPage.tsx | — | 待ちの表示 | 後半 |
| 26 | 新 frontend/src/features/auth/LoginApprovalWatcher.tsx（と試験） | 無い | A-3 のとおり | 後半 |
| 26a | frontend/src/components/DesktopShell.tsx | :204 RealtimeProvider・:197-198 管理の案内の並び | :204 の内側に #26 と #26b を置く。:198 の後に { to: "/super-admin/login-requests", labelKey: "nav.superAdminLoginRequests" } を足す | 後半 |
| 26b | 新 frontend/src/features/auth/RecoveryCodePrompt.tsx（と試験） | 無い | design.md:158 の案内。ログイン後に GET /auth/recovery-codes/status の残りが0のとき Modal を1回出す（「作る」で POST /auth/recovery-codes・10個を1回だけ表示してコピー／「あとで」で閉じる）。閉じたことはそのタブの sessionStorage に覚え、同じタブでは出し直さない（読み書きは try/catch） | 後半 |
| 26c | frontend/src/components/MobileShell.tsx | :198 RealtimeProvider・:187 管理の案内の並び | :198 の内側に #26 と #26b を置く。:187 の並びに nav.superAdminLoginRequests を同じ形で足す | 後半 |
| 27 | frontend/src/pages/account-settings/SecuritySection.tsx | — | 機械の一覧と予備の合言葉 | 後半 |
| 28 | 新 frontend/src/pages/super-admin/LoginRequestsPage.tsx（と試験） | 無い | 許可待ちの一覧。見出しは t("nav.superAdminLoginRequests")（check:nav-sync） | 後半 |
| 28a | frontend/src/App.tsx | :89-103 の super-admin の import・:302 の /super-admin/fx-rate の Route | 同じ並びに import と /super-admin/login-requests の Route を足す（fx-rate の Route と同じ守りで包む） | 後半 |
| 29 | frontend/src/lib/realtime/topics.ts | — | USER_TOPICS の話題を足す | 後半 |
| 30 | frontend/src/locales/ja.json・en.json | — | A-3 の i18n キー（同じキーを両方に） | 後半 |
| 31 | frontend/api-contract/openapi.json | — | backend の口を足した後に書き出す。schema.d.ts は入れない | 後半 |

## 2. 触らない範囲
- design.md §5 の全部（回数制限の値・smoke の道・閲覧ページのログイン・ADR-1048 の6桁・nginx の設定・パスワード再設定メールの文面・.claude/scripts/review-gate）。
- .github/workflows/deploy.yml と tests/prod-check（段B）。web push（段W）。
- backend/tests/rls_bootstrap.py（design.md A-1 の理由で直さない）。
- 既存の migration の中身（#4 の INSERT の行の追加と :3 の数だけは例外）。
- 本番 DB・本番の .env・GitHub の秘密。クラウドでは本番に繋がない。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 行の合わせ直し: design.md §4 段A に出てくる「ファイル:行」を、作業場所で grep か sed -n で1つずつ読む。中身が同じで行だけ動いたものは、動いた後の行を報告に書いて進む。中身が違う（関数名・引数・文の意味が違う）ものがあれば、その箇所で停止して BLOCKED: で Opus へ返す。
- (b) selfLogin の呼び出し元: `grep -rn "selfLogin(" frontend/src` と `grep -rn "signIn" frontend/src --include=*.test.tsx` の結果が、design.md A-3 に名前が出ているファイル以外に当たれば、型が合わなくなるものは同じ形で直し、報告に名前を書く。本体（試験でないファイル）に当たれば停止する。
- (c) 呼び出し元の全部: create_access_token・issue_refresh_token・rotate_refresh_token・_issue_session_tokens を grep し、design.md A-2 に挙げた呼び出し元（auth.py の4か所と self_tokens.py の1か所、試験を除く）以外に本体の呼び出しがあれば停止する。
- (d) celery-worker の外への通信: docker-compose.yml の celery-worker の networks が外へ出られない網（internal: true）だけなら、refresh_geoip_db は DB-IP に届かない。そのときは作業を作るが失敗しても認証は止めない作りのまま進め、報告に「celery-worker から外へ出られない」と書く（止まらない）。
- (e) starlette の request.state: design.md D7 の「middleware から口の request.state が読める」を pytest で示す。読めなければ停止する（記録の作り方を変える必要があるため）。
- (f) 新しい表の名前が既にある: S の migrations と backend に user_trusted_devices・auth_login_requests・user_recovery_codes・trusted_device_id の語が無いことを grep で確かめる。有れば停止する。
- (g) migration の登録検査: bash scripts/check-migration-registration-exists.sh と scripts/check-migration-value-writes.py が通ること（commit の後に check-before-submit がまとめて流す）。通らなければ、出力を付けて停止する。
- (h) lint_tenant_schema: 新しい表は public に置き tenant に置かない。scripts/lint_tenant_schema.py の strict（check-before-submit が流す）が落ちたら停止する。
- (k) 画面の置き場: #26a・#26c・#28a の行が S と違い、同じ形の並びが見つからないときは停止する。管理の案内の並びに足す形が fx-rate の行と違う形（icon 等が要る）なら、その形に合わせ、報告に書く。
- (i) PostgreSQL: pytest の PG の試験（ops/test_ai_cloud_views.py など）は、クラウドの中で自分が立てた localhost の PostgreSQL でだけ流す。立てられなければ SQLite の試験だけ流し、報告に「PG の試験は CI で確かめる」と書く（止まらない）。
- (j) 依存: pip install -r backend/requirements.txt で maxminddb==3.2.0 が入ること。入らなければ停止する。

## 4. 実装役の手順（1手順1命令。<W> は手順1 で作られた作業場所の絶対パス）

### 4-1. 前半
手順1. クラウドの決まりどおり作業場所を作る。前半は新しい枝なので main のまま始める。
  cd "$(git rev-parse --show-toplevel)" && git fetch origin main
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/new-device-approval-stage-a
  cd <W> && git rev-parse HEAD origin/main
  （2行が同じことを確かめ、sha を報告に書く。違えば停止して BLOCKED:）
手順2. design.md とこのカードを読み、§3 の (a)(c)(f) を確かめる。
  cd <W> && sed -n 1,245p docs/handoff/auth-new-device-approval/design.md
  cd <W> && grep -rn "user_trusted_devices\|auth_login_requests\|user_recovery_codes\|trusted_device_id" migrations backend | head -20
  cd <W> && grep -rn "create_access_token(\|issue_refresh_token(\|rotate_refresh_token(\|_issue_session_tokens(" backend/app | head -30
手順3. 依存を入れる。
  cd <W>/backend && pip install -r requirements.txt > /tmp/stageA-pip.txt 2>&1
  cd <W>/backend && tail -5 /tmp/stageA-pip.txt
手順4. §1 の #1〜#9 を作る（A-1）。#6 の sha256 は #4 を直した後に計算する。
  cd <W> && shasum -a 256 migrations/20261024_100300_create_ai_cloud_views.sql
  cd <W> && wc -l docs/handoff/cloud-case-ai/stage1-column-class.tsv
  （tsv が 1055 行でなければ停止する。）
手順5. §1 の #10〜#23 を作る（A-2）。ADR の目次を作り直す。
  cd <W> && node scripts/generate-adr-index.js
手順6. backend の試験を流す（出力は /tmp に置き、作業場所に残さない）。
  cd <W>/backend && ENVIRONMENT=test python -m pytest tests/test_new_device_approval.py tests/test_viewer_isolation.py tests/test_realtime_topics.py tests/test_realtime_middleware.py -q > /tmp/stageA-pytest-1.txt 2>&1
  cd <W>/backend && tail -30 /tmp/stageA-pytest-1.txt
  cd <W>/backend && ENVIRONMENT=test python -m pytest tests -q -x --ignore=tests/sandbox > /tmp/stageA-pytest-all.txt 2>&1
  cd <W>/backend && tail -30 /tmp/stageA-pytest-all.txt
  （PG が要る試験は §3(i) に従う。落ちた試験があれば直す。本便と関係ない理由で落ちるものは、名前と最後の行を報告に書く。）
手順7. 変わったファイルを確かめる。
  cd <W> && git status --short | head -80
  （§1 の前半の行以外のファイルが出ていたら add しない。試験の途中にできたファイル・.claude-pipeline/active-work.d/ は add しない。）
手順8. §1 の前半のファイルを名前で add して commit する（フォルダごとの add はしない）。
  cd <W> && git add migrations/20261101_120000_add_new_device_approval.sql migrations/20261024_100300_create_ai_cloud_views.sql scripts/run_all_migrations.sh scripts/migration-guard/reference-allowlist.tsv
  cd <W> && git add .github/workflows/migration-guard.yml .github/workflows/migration-test.yml docs/handoff/cloud-case-ai/stage1-column-class.tsv docker-compose.yml backend/requirements.txt
  cd <W> && git add backend/app/auth backend/app/cli backend/app/routers/auth.py backend/app/routers/login_approvals.py backend/app/routers/super_admin_login_requests.py backend/app/main.py
  cd <W> && git add backend/app/realtime backend/app/routers/realtime_events.py backend/app/services/auth_mail.py backend/app/middleware/audit.py backend/app/tasks/maintenance.py backend/app/celery_app.py
  cd <W> && git add backend/tests/test_new_device_approval.py backend/tests/test_viewer_isolation.py backend/tests/test_realtime_topics.py backend/tests/ops/test_ai_cloud_views.py backend/tests/conftest.py
  cd <W> && git status --short | head -80
  （celery_app.py の場所が backend/app/celery_app.py でなければ実物の場所で add する。README.md は generate-adr-index.js で変わったときだけ git add docs/adr/README.md。add した後に §1 に無いファイルが入っていれば git restore --staged で外す。）
  cd <W> && git commit -m "feat: 知らない機械からのログインを止める仕組みの土台（段A前半・既定は止めない）"
手順9. commit が在ることを確かめ、提出前の入口を流してから push する（入口は未保存の変更があると止まるので、commit の後に流す。--no-verify は使わない。× なら直して commit し直してから push）。
  cd <W> && git log -3 --oneline
  cd <W> && bash scripts/dev/check-before-submit.sh > /tmp/stageA-cbs-1.txt 2>&1
  cd <W> && tail -25 /tmp/stageA-cbs-1.txt
  cd <W> && git push -u origin release/new-device-approval-stage-a
手順10. 報告を返す。PR は作らない。報告の1つの発言は600文字以内にして番号付きの発言に分け、最後を DONE: か BLOCKED: で始める。

### 4-2. 後半（前半の push の後に、別の回で流す）
手順11. 作業場所を作り、push 済みの枝の先頭に合わせる。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/new-device-approval-stage-a
  cd <W> && git fetch origin release/new-device-approval-stage-a
  cd <W> && git switch -C release/new-device-approval-stage-a origin/release/new-device-approval-stage-a
  cd <W> && git rev-parse HEAD origin/release/new-device-approval-stage-a
  （2行が同じことを確かめる。違えば停止して BLOCKED:。main は取り込まない。reset・rebase・force・merge・pull は使わない。）
手順12. §3(b) を確かめる。
  cd <W> && grep -rn "selfLogin(" frontend/src | head -20
  cd <W> && grep -rln "signIn" frontend/src --include=*.test.tsx | head -30
手順13. frontend の依存を入れる。
  cd <W>/frontend && npm ci > /tmp/stageA-npm.txt 2>&1
  cd <W>/frontend && tail -5 /tmp/stageA-npm.txt
手順14. §1 の #24〜#30 を作る（A-3）。金型だけを使う（docs/CC_UI_GOVERNANCE.md）。文字は全部 t()。生の select・input・自作のタブ・色の直値を使わない。
手順15. API の形を書き出す。
  cd <W>/backend && pip install -r requirements.txt > /tmp/stageA-pip2.txt 2>&1
  cd <W>/backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json
  cd <W>/frontend && npm run generate:api-types
手順16. frontend の検査と試験を流す。
  cd <W>/frontend && npx tsc --noEmit > /tmp/stageA-tsc.txt 2>&1
  cd <W>/frontend && tail -20 /tmp/stageA-tsc.txt
  cd <W>/frontend && npm run lint > /tmp/stageA-lint.txt 2>&1
  cd <W>/frontend && tail -20 /tmp/stageA-lint.txt
  cd <W>/frontend && npm run check:i18n-missing-keys > /tmp/stageA-i18n.txt 2>&1
  cd <W>/frontend && tail -10 /tmp/stageA-i18n.txt
  cd <W>/frontend && npm run test:unit > /tmp/stageA-vitest.txt 2>&1
  cd <W>/frontend && tail -30 /tmp/stageA-vitest.txt
  cd <W>/frontend && npm run check:all > /tmp/stageA-checkall.txt 2>&1
  cd <W>/frontend && tail -30 /tmp/stageA-checkall.txt
手順17. 変わったファイルを確かめる。
  cd <W> && git status --short | head -80
  （frontend/src/api/generated/schema.d.ts は .gitignore の対象なので出ない。出たら add しない。§1 の後半の行以外のファイルは add しない。）
手順18. §1 の後半のファイルを名前で add して commit する。
  cd <W> && git add frontend/src/lib/auth/selfAuth.ts frontend/src/lib/auth/selfAuth.test.ts frontend/src/contexts/AuthContext.tsx frontend/src/components/AllLegacyButtonOperationMigration.test.tsx
  cd <W> && git add frontend/src/pages/login/LoginPage.tsx frontend/src/features/auth frontend/src/components/DesktopShell.tsx frontend/src/components/MobileShell.tsx frontend/src/App.tsx
  cd <W> && git add frontend/src/pages/account-settings/SecuritySection.tsx frontend/src/pages/super-admin/LoginRequestsPage.tsx frontend/src/locales/ja.json frontend/src/locales/en.json frontend/api-contract/openapi.json
  cd <W> && git status --short | head -80
  （frontend/src/lib/realtime/topics.ts（#29）・§3(b) で直した試験・新しい試験のファイルは、実物の名前で同じく add する。§1 に無いファイルが入っていれば git restore --staged で外す。）
  cd <W> && git commit -m "feat: ログイン画面の待ち表示・いつもの機械の許可の小窓・機械の一覧（段A後半）"
手順19. commit が在ることを確かめ、提出前の入口を流してから push する。
  cd <W> && git log -3 --oneline
  cd <W> && bash scripts/dev/check-before-submit.sh > /tmp/stageA-cbs-2.txt 2>&1
  cd <W> && tail -25 /tmp/stageA-cbs-2.txt
  cd <W> && git push -u origin release/new-device-approval-stage-a
手順20. 報告を返す（手順10 と同じ形）。PR は作らない。

## 4b. GO と承認・PO の操作
- PO の承認: K1〜K9 と「全員に最初から効かせる」「入れた日にログイン中の機械はいつもの機械」（2026-11-01 PO 承認）。PO の依頼「PRマージ、デプロイまで完走させてくれ」（2026-11-01）。設計は第6版で審査 APPROVE。
- #1・#2・#4・#20 は危険パス（migrations・本番 scripts・docker-compose）→ ADR-136 の委任 GO（POの委任に基づくClaude Opus発行）。新しく起動した opus の審査役の APPROVE の後に、PR 本文へ GO記録を書いてからマージする。
- 段A のマージと本番反映の後も、AUTH_DEVICE_APPROVAL は off のまま（ログインの止め方は今と同じ）。enforce は段B。
- PO が操作することはない。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| A1 | design.md §6 の pytest の列（K1〜K9）が全部ある・緑 | CI の pytest（SQLite と PostgreSQL RLS）・手順6 の tail |
| A2 | off のときログインの止め方が今と同じ | test_new_device_approval.py の off の試験（印なし login が 200・トークンあり・機械の行が増えない） |
| A3 | CI の必須の点検が全部緑 | gh pr checks（設計担当） |
| A4 | 変わったファイルが §1 の行の範囲だけ（試験のファイルと §3(b) で名前を報告したものを含む） | gh pr diff --name-only（設計担当） |
| A5 | 本番反映後、新しい3表と2つの列ができている | reader 鍵で pg_attribute と to_regclass（設計担当） |
| A6 | 本番反映後、ai_cloud_meta.column_class が 1054 行・build_log の最新行が ok | reader 鍵（設計担当） |
| A7 | 本番反映後、今のログインと更新が通る | prod-ui-check の手動実行が緑（設計担当） |
| A8 | 本番反映後、auth_events に user_id・reason が入り始める | reader 鍵で反映時刻以降の行の reason 別件数（設計担当） |

## 6. 戻し方
- マージの commit を git revert する PR を1つ出す。AUTH_DEVICE_APPROVAL は off のままなので、ログインの止め方は戻す前も後も同じ。
- 表と列は追加だけなので、残しても害は無い（design.md §7 の戻し方）。消すのは PO の判断。
- 場所のデータは GEOIP_DB_PATH を .env で空にすれば読まない。

## 停止と報告
- §3 で「停止」とした時、§2 の触らない範囲を変えないと進めない時、design.md とこのカードが食い違う時、試験が直せない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果（動いた行の一覧を含む）、手順6（後半は手順16）の tail、push した sha を書く。

END OF CARD
