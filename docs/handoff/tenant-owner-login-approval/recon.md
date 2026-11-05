<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — 会社の持ち主が自社の社員のログインを許可する／会社の分け方の見張り

**仕事名**: tenant-owner-login-approval  
**日付**: 2026-11-05  
**対象ADR**: ADR-1063（新規）、ADR-1055（改訂）  
**担当**: Claude Opus（設計担当・PO の委任に基づく）  
**基準**: origin/main f72f2dc5f（2026-11-05 fetch 後）。生出力は /tmp/CC報告ファイル/owner-approval/ と /tmp/CC報告ファイル/tenant-isolation/report.md

---

## 既存 ADR の検索結果

`git grep -i -E 'owner|login_request|rls|tenant_id' docs/adr/` と `docs/adr/FEATURE-INDEX.md` で探した。関係するもの:

| ADR | 関係 |
|---|---|
| ADR-1055 | 新しい機械のログイン許可。許可できるのは本人のいつもの機械・運営（super admin）・控えの番号の3つ。本件で「会社のオーナー」を4つ目に足す（改訂） |
| ADR-1018 | public の機微な表に RLS を段階導入。接続役は salesanchor_app（NOBYPASSRLS） |
| ADR-072 | 会社ごとのスキーマ分離と lint（strict） |
| ADR-036 | DB のポカよけ（migration-guard） |
| ADR-1013 | 自社ログイン。認証系の表に RLS を付けない判断 |
| ADR-027 / ADR-144 / ADR-067 | i18n・UI 部品の金型・デザイントークン |
| ADR-136 | 危険 PR（migrations/ 等）の GO 手順 |

オーナー専用の依存関数は無い: `git grep -n -E 'def (require_tenant_owner|require_owner|is_tenant_owner)' backend/app` → 0 件。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20261101_130000_add_new_device_approval.sql:41` | public.auth_login_requests の作成。tenant_id 列なし・RLS なし |
| `migrations/20261101_130000_add_new_device_approval.sql:63` | status は pending/approved/rejected/expired/completed のみ |
| `migrations/20261101_130000_add_new_device_approval.sql:64` | decided_via は device/admin/recovery_code のみ（'admin' を再利用すれば制約の変更は不要） |
| `migrations/20261101_130000_add_new_device_approval.sql:129` | salesanchor_app に SELECT/INSERT/UPDATE/DELETE を付与済み |
| `migrations/20261024_100000_create_ai_cloud_meta.sql:124` | timestamptz の列は ai_ro の見せ方で素通し（分類の追加は不要） |
| `backend/tests/ops/test_ai_cloud_views.py:622` | auth_login_requests を新しい表として見せ方の試験に含む。列を足したらこの試験の期待を確かめる |
| `backend/app/auth/system_roles.py:8` | `ROLE_KEY_OWNER = "owner"` |
| `backend/app/auth/system_roles.py:14` | admin は会社から隠す運営用の役（`TENANT_HIDDEN_SYSTEM_KEYS`） |
| `backend/app/auth/system_roles.py:19` | `is_tenant_admin` は owner と admin の両方で真 → オーナーだけの判定には使えない |
| `backend/app/auth/dependencies.py:494` | `get_user_system_keys(db, user_id)` で役の鍵の集合を得る |
| `backend/app/auth/dependencies.py:553` | `require_tenant_admin` は owner/admin を通す。オーナー専用の依存関数を新設する |
| `backend/app/auth/dependencies.py:210` | `get_current_tenant` が search_path・app.tenant_id を張る |
| `backend/app/services/user_notices.py:73` | `_owner_user_ids` が既に「オーナーの人だけ」を取る（再利用する） |
| `backend/app/routers/roles.py:145` | /me/permissions が役の鍵から is_tenant_admin を返す。is_tenant_owner を足す場所 |
| `backend/app/routers/super_admin_login_requests.py:70` | 運営の許可待ち一覧（public.auth_login_requests を public.users と JOIN） |
| `backend/app/routers/super_admin_login_requests.py:107` | 運営の許可。自分の依頼は 403、条件つき UPDATE、監査、commit、publish_user_change |
| `backend/app/routers/login_approvals.py:45` | 本人のいつもの機械が見る許可待ち（鈴が生で取りに行く） |
| `backend/app/routers/auth.py:273` | `_record_auth_audit`（会社文脈を張って audit_logs に書き、外す） |
| `backend/app/routers/auth.py:339` | `_notify_new_request` は依頼した本人にだけ知らせる |
| `backend/app/routers/auth.py:1318` | `_load_login_request` が待ち中 Cookie から依頼を引く（ボタンの認証に使う） |
| `backend/app/routers/auth.py:1378` | poll。decided_via='admin' で許可された依頼は機械を登録して入れる |
| `backend/app/services/auth_mail.py:192` | `send_new_device_mail`（リンク・番号を入れないメールの手本） |
| `backend/app/routers/staff.py:78` | スタッフ登録で全社の users をメールで引く |
| `backend/app/routers/staff.py:86` | 他社なら 409「他の会社で使われています」（漏れ） |
| `backend/tests/test_staff_create_users.py:115` | 漏れの文言を期待する試験（直す対象） |
| `frontend/src/pages/login/LoginPage.tsx:300` | いつもの機械も控えの番号も無いとき、文だけ出す（ボタンなし） |
| `frontend/src/pages/management-center/ManagementCenterPage.tsx:28` | 管理センターのメニューを権限から組み立てる |
| `frontend/src/App.tsx:393` | 管理センターの入れ子の道筋 |
| `frontend/src/components/NoticeBell.tsx:1` | 鈴。許可待ちを表から生で取って数える（写しを作らない） |
| `frontend/src/hooks/usePermissions.ts:1` | isTenantAdmin を出す。isTenantOwner を足す場所 |
| `frontend/src/pages/super-admin/LoginRequestsPage.tsx:1` | 運営の許可待ち画面（ConfirmModal と本人確認のメモ欄の手本） |
| `backend/app/tasks/master_required_fields_monitor.py:1` | 管理者用 Discord に定期で送る作業の手本 |
| `backend/app/celery_app.py:21` | 作業の登録（include）。足し忘れると未登録になる |
| `backend/app/celery_app.py:69` | 定期の時間割（beat_schedule） |
| `.github/workflows/migration-test.yml:40` | paths-filter（migration 関係のファイルが変わった PR だけで job が動く） |
| `.github/workflows/migration-test.yml:1352` | job「マイグレーション全件ドライラン（実DB）」の始まり。Python 3.12 と backend の依存を入れる |
| `.github/workflows/migration-test.yml:2002` | 1周目。2026-06 までの migration しか流さない（新しい表は入らない） |
| `.github/workflows/migration-test.yml:2071` | 全件ドライラン。登録された全 migration − 除外一覧を報告用 DB jarvis_report に流す（便5 はこの後に置く） |
| `.github/workflows/migration-test.yml:2087` | まとめの job＝必須チェック「マイグレーションSQL 実行テスト（実DB）」 |
| `migrations/003_add_phase1_tenant_tables.sql:176` | 会社の roles・user_roles は RLS で app.tenant_id を見る（文脈なしでは読めない） |
| `.github/workflows/process-artifacts-gate.yml:8` | 起動は pull_request → 設定もスクリプトも PR 側のものが動く |
| `.github/workflows/process-artifacts-gate.yml:27` | checkout は既定（PR のマージ用の写し） |
| `scripts/check-process-artifacts.js:51` | PO だけが変えてよいファイルの一覧（今は workflow-lint.yml だけ） |
| `.github/workflows/workflow-lint.yml:1` | 自分自身の改ざん検知。必須チェックではない |
| `docs/specs/tenant-rls/README.md:1` | 会社の分け方の仕様書の表紙（見張りの表を足す場所） |
| `docs/ai-agents/executor-checklist.md:1` | 実装役の点検表（見張りの表へのリンクを足す場所） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 本番の接続役が salesanchor_app か | deploy の job log 1238・3166 行（report.md 追記） | ✅ 解消済み（salesanchor_app） |
| 2 | 必須チェックの一覧 | `gh api` で ruleset 15777895 を取得（rulesets.json） | ✅ 解消済み。workflow-lint は必須でない |
| 3 | 見張りのゲートは PR 側のコードで動くか | process-artifacts-gate.yml:8・27 と GitHub 公式文書（events-that-trigger-workflows: pull_request は PR のマージ用の写し、pull_request_target は基のブランチで動く） | ✅ 解消済み。PR 側で動く → PR が自分で見張りを外せる。K10 は pull_request_target で基のブランチの定義を動かす |
| 4 | 本番で BYPASSRLS を持つ役の一覧 | ai_ro にカタログの見せ方が無く読めない | ⏳ 便5 の初回実行で読み、PO 報告のうえ許可一覧に固定（設計で手順化） |
| 5 | public の tenant_id 付きで RLS の無い表の今の数 | CI の実 DB で数える | ⏳ 便4 の最初の実行（記録だけの形）で数え、理由つきの許可一覧にする（設計で手順化） |
| 6 | お客さまの会社のオーナーの人数 | お客さまの会社には触らない決まり | 対象外。オーナーがいなければ画面で「運営に連絡」と出す設計で吸収 |
| 7 | Context7 での GitHub Actions 仕様の確認 | 月の上限で使えず（2026-11-05） | ✅ 公式文書を直接確認で代替（起動指示の許可） |

**未解決ゼロ確認**: 設計の判断に要る不明点はゼロ。#4・#5 は「実装の最初の実行で測って固定する」手順として設計に入れた（推測の値は入れない）。

---

## 補足

- 依頼の表に tenant_id は無い。会社の絞り込みは `public.users u ON u.id = r.user_id` で `u.tenant_id = get_current_tenant の会社` とする（運営の一覧と同じ JOIN）。
- 運営の許可（super_admin_login_requests.py:107）と同じ UPDATE をオーナー用に書き写すと二重管理になる → 共通の関数に1か所化する。
- メールは全社で1つ（public.users）のため、スタッフ登録で「失敗か成功か」から他社在籍を推測される余地は消せない。文言の区別を無くすところまでが本件の範囲。
