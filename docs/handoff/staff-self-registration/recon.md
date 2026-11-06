# スタッフの自己登録 — 現在地（recon）

- 基準: `origin/main` 75c84e176（2026-11-07 fetch 後）。引用は全てこの版のフルパス:行番号。
- 調べた人: Claude Opus（設計担当）。読み取りのみ。

## 1. 既存 ADR の検索結果

- 検索語: スタッフ登録 / 自己登録 / self registration / must_change / invite / 招待 / Discord（`git grep -il docs/adr` と `docs/adr/FEATURE-INDEX.md`）
- 当たったもの:
  - `docs/adr/ADR-1063-tenant-owner-login-approval-and-isolation-guards.md:24`: スタッフ登録の重複の文言は、他社と自社を言い分けない。→ 本件の申込フォームも同じ文言（`EMAIL_UNAVAILABLE_DETAIL`）を使う。
  - `docs/adr/ADR-1063-tenant-owner-login-approval-and-isolation-guards.md:25`: 会社の列があって RLS が無い public の表を、CI で止める（便5 は未実装。`backend/app/ops/` に許可一覧のファイルはまだ無い）。→ 本件で作る表は最初から RLS を付ける。
  - `docs/adr/FEATURE-INDEX.md:50`: ADR-159 では英語名が必須。
- 関連 ADR（本文で参照）:
  - ADR-1013: 自社ログイン。
  - ADR-1008: 人の正本は public.users。ロールの正本は user_roles。
  - ADR-1019: 閲覧者の申込と Discord 受付。本件のひな形。
  - ADR-1055: 新しい機械の許可。
  - ADR-1048: 管理者の2段階確認。Proposed のまま、#4827 で REVIEW 中。
  - ADR-091: Bot の権限。
  - ADR-146: guild からテナントを引く。
  - ADR-1018 / ADR-072: RLS と会社の文脈。
  - ADR-027・ADR-144・ADR-067: 画面の文言・金型・トークン。

## 2. スタッフの作成（今）

- `backend/app/routers/staff.py:596` `create_staff`（POST /staff。権限 staff.create は `backend/app/routers/staff.py:595`）。
  - `backend/app/routers/staff.py:73` `_resolve_user_for_new_staff`: public.users をメールで再利用するか、新しく作る。他社が使っているメールや、もう紐付いているメールは 409（`backend/app/routers/staff.py:65` の文言）。
  - staff を仮コードで INSERT した後、`EMP-%05d` に置き換える。
  - `backend/app/routers/staff.py:640` `assign_single_role(db, tenant_id, current_user, user_id, role_id)`。
    - 付与者の最大 priority 未満のロールしか付けられない（`backend/app/services/role_assignment.py:35` 以降）。
  - `backend/app/routers/staff.py:649`: 新しい利用者のときだけ、`create_invite_token` で招待メールの鍵を作る。
    - 鍵は public.password_reset_tokens の purpose='invite'、72 時間。`backend/app/services/invite.py:16` と `backend/app/services/invite.py:19`。
    - purpose の CHECK は reset と invite だけ（`migrations/20261013_160000_add_self_hosted_auth_tables.sql:56`）。
  - `backend/app/routers/staff.py:653`: commit の後に、自社サーバーのロール合わせ（`schedule_own_staff_sync`）を予約する。
- `backend/app/schemas/staff.py` の StaffCreate。
  - 必須: 姓名（日本語）、姓名（英語）、主メール、role_id。
  - 任意: かな、discord_user_id。status の既定は active、`pending` も使える（StaffStatus）。
- staff.status は、ログインも権限も止めていない。`backend/app/auth/` の中で `'active'` を見ているのは viewer_dependencies.py:86 だけ。
- 画面:
  - `frontend/src/pages/staff/StaffPage.tsx:224` の新規作成の Modal は、管理者が全項目を書く。部品は Modal、Select、TextFieldControl、Button、DataTable。
  - 入力欄は `frontend/src/pages/staff/StaffFormFields.tsx` にある。

## 3. ログインとパスワード

- `backend/app/routers/auth.py` の self_login（/login）は `public.users.password_argon2_hash` で照合する。
  - 一度もログインしていない人の最初の機械は、自動でいつもの機械になる（D5 first_login。enforce のときだけ）。
- `backend/app/routers/auth.py` の /password/change（`@router.post("/password/change")`）では、今のパスワードの照合が要る。
  - 成功すると、更新用トークンを全部失効させて出し直す。
- public.users に password_must_change の列は無い。
  - viewer_accounts には有る（`migrations/20261016_150000_add_viewer_accounts.sql:13`）。
- 閲覧者の「変更するまで止める」型:
  - `backend/app/auth/viewer_dependencies.py:106-108` の require_viewer_password_ok が 403 password_change_required を返す（審査で 27-30 から訂正）。
  - `backend/app/routers/viewer.py:252` で変更が成功したら false に戻す。
  - 画面は `frontend/src/pages/viewer/ViewerApp.tsx:134` で `must_change_password` を見る。
- 本体の共通の入口は `backend/app/auth/dependencies.py:108` の get_current_user。
  - 戻り口は3つ: smoke 用（`backend/app/auth/dependencies.py:159`）、Redis の一時記憶が当たったとき（同ファイルの「② キャッシュ」）、`_authenticate_self_token`（`backend/app/auth/dependencies.py:55`）。設計審査 R6 で2つから訂正。
- 認証アプリ（TOTP）は backend/app に無い。設計だけが #4827 にある（ADR-1048、REVIEW）。

## 4. Discord（閲覧者の受付＝本件のひな形）

- `backend/app/discord_gateway/viewer_trial.py`:
  - 93 行: ボタン `viewer_trial_open` を押すと 66 行の ViewerTrialCodeModal を出す。
  - 252 行: on_code_submit。
  - 266 行: 失敗回数を Redis `viewer_code_fail:{member.id}` に数える（5 回で 3600 秒）。
  - 申込コードを DELETE … RETURNING で使い切る。
  - 130 行: 個室を作る（private_channel.create_private_text_channel）。
  - 333 行: `secrets.token_urlsafe(18)` で仮パスワードを作る。
  - 354/381 行: password_must_change=true にする。
  - 401 行: IntegrityError のとき「もう紐付いています」と返す。
  - 失敗したら個室を消す。
  - 419 行: 持ち主のいない個室を片付ける。
- コードの形は `backend/app/auth/viewer_signup_code.py`:
  - Crockford base32 で 16 文字（80 ビット）。
  - normalize で揃え、sha256 だけを保存する。
  - 画面では 4 文字ずつハイフンで区切る。
- 振り分けは `backend/app/discord_gateway/client.py:256` の on_interaction。
  - 263 行: `viewer_trial_` で始まれば閲覧者の処理へ行く。
  - それ以外は `ticket_open` だけを受け、お客様のチケット（リード作成）にする。
  - 顧客サーバーのテナントは purpose='customer' で引く（client.py `_resolve_tenant_id`）。
- 招待リンク:
  - `backend/app/services/viewer_invite.py:23` の create_viewer_invite が、受付部屋に `POST /channels/{id}/invites` を送る（7 日・1 回限り・unique）。
  - commit の後に呼ぶ決まり。
- Bot の権限:
  - `backend/app/routers/discord_oauth.py:53-79`。
  - 2026-10-17 に Create Instant Invite が追加された（805432407）。
  - 自社サーバーで実際にこの権限が付いているかは、まだ確かめていない（実装前の点検に入れる）。
- 受付ボタンの設置は `backend/app/viewer_discord_cli.py:230` の post-button。stdin の JSON だけを受け取る。

## 5. 自社用サーバー（スタッフのサーバー）

- 自社サーバーの guild は public.tenant_discord_config の purpose='own'（`backend/app/routers/discord_own_server.py` の `_load_own_context`）。
- 設計図 tenant_1.json の中身:
  - roles: everyone、スタッフ。
  - categories: text_cat、voice_cat。
  - channels: general、assign_notice、reply_notice、outside_notice。
  - 反映は plan と apply で、構造だけを作る。
- `backend/app/services/discord_own_staff_sync.py`:
  - staff.discord_user_id がある人にだけ「スタッフ」ロールとアプリの役割ロールを付ける。
  - `schedule_own_staff_sync(tenant_id)` で予約して動く。

## 6. 会社の分け方（RLS）

- public の会社別の表は、`tenant_id = current_setting('app.tenant_id')` の FOR ALL ポリシーと FORCE RLS を使う（`migrations/20261016_010000_add_google_config_rls.sql:2-9`）。
- ログインしていない申込フォームは、表を引く前に会社が分からない。→ 設計で、リンクに会社の番号を入れて解く（design §3-1）。

## 7. 他の作業との関係

- 認証アプリ: 別のセッションが担当（ADR-1048、#4827）。本件の3回目は、それが本番に入ってから始める。
- 最新の ADR 番号:
  - main は ADR-1066 まで。
  - 開いている PR が ADR-1061、ADR-1064、ADR-1067 を使っている。
  - → 本件は ADR-1068 にする。
