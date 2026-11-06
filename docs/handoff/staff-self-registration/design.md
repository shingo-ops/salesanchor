# スタッフの自己登録 — 設計（design）

| 項目 | 内容 |
|------|------|
| 状態 | 設計案（Opus 作成・自己審査は §9）。PO 実装承認済み（2026-11-07「1」）。クラウドの設計審査の結果は §10 |
| ADR | ADR-1068（Proposed・本 PR の草案） |
| 現在地 | `docs/handoff/staff-self-registration/recon.md` |
| PO 承認 | KGI 1〜13 と3回の分け方に「1」（2026-11-07）、初回ログイン情報＝「2,閲覧用ページと同じ仕組み」（2026-11-07）、実装承認＝「この設計で作り始める」に「1」（2026-11-07） |

## 0. 目的（PO の言葉）

- 「スタッフが初回にアプリに登録してログインするためのフォーム」。
- 流れ:
  1. フォームを送る。送るときに役割を選ぶ。
  2. 新しく採用したスタッフが入力する。
  3. Sales Anchor アプリに自動で登録され、Discord の番号が出る。
  4. スタッフが Discord に参加し、チケットから番号を入れる。
  5. 個別の部屋ができ、アプリ側に Discord ID が自動で登録される。
  6. 個別の部屋に初回のログイン情報を出す。
  7. 初回ログインのあと、生体認証と認証アプリを登録する。
  8. 初回セットアップが自動で終わる。
- メールでは送らない。「URLを発行してくれれば手動で送る」。
- 目的（2回問い直し）:
  - 管理者が人ごとに項目を書く手間と、Discord ID の手入力の誤りをなくしたい。
  - その先で、新しい人が、管理者の手を最小にして安全に働き始められるようにしたい。

## 1. KGI（PO 承認済み）と検証方法（基準は○×で見る）

| # | 基準 | 検証方法 | 回 |
|---|---|---|---|
| 1 | 管理者がスタッフ一覧で役割を選び「招待リンクを作る」を押すと、リンクとコピーボタンが出る | 本番で管理者が押して画面を見る＋API 試験 | 1 |
| 2 | 管理者がリンクを手で送れる（メールは出ない） | 試験で送信関数が呼ばれないこと＋画面のコピー | 1 |
| 3 | 作り直すと新しいリンクが出て、古いリンクは開けない | API 試験（古い鍵で 404）＋本番で古いリンクを開く | 1 |
| 4 | スタッフがリンクを開いて名前などを書ける。リンクは 72 時間で切れる | 画面で入力＋試験（期限超えで 404） | 1 |
| 5 | 送るとアプリに「登録待ち」で出る。画面に登録番号と Discord の参加リンクが出る | 一覧の状態列＋完了画面 | 1 |
| 6 | Discord の受付でスタッフ用ボタンを押し、番号を入れる。5 回まちがえると 1 時間止まる | 本番で押す＋試験（6 回目は拒否） | 2 |
| 7 | 本人と管理者だけが見える個室ができる。二重にできない | 本番で個室の見える人を確認＋試験（2 回目は既に登録済み） | 2 |
| 8 | Discord ID が staff に自動で入る（手入力 0 件） | 一覧の Discord 欄＋DB の値 | 2 |
| 9 | 個室にメールと一度だけのパスワードが出る | 本番の個室の文面 | 2 |
| 10 | 初回ログインでパスワードを変える（変えるまで他の画面は止まる） | 本番でログイン＋試験（403 password_change_required） | 2 |
| 11 | 生体認証と認証アプリの両方を登録するまで、他の画面は止まる | 3回目の設計で詳しく決める | 3 |
| 12 | 両方を終えると「登録待ち」から「有効」へ自動で変わる | 3回目の設計で詳しく決める | 3 |
| 13 | お客様のチケットの動きは変わらない | 既存試験が緑＋本番で顧客サーバーのボタンを押すとリードができる | 1〜3 |

## 外部・過去事例の参照と我々への応用

- 社内の事例（直接の根拠）:
  - 閲覧者の申込（ADR-1019 段4c）は、本件と同じ形でもう動いている。
    - 形: 申込 → コード → Discord の受付ボタン → 個室 → 仮パスワード → 変更を強制。
    - 書き方: `backend/app/discord_gateway/viewer_trial.py`。
  - 本件は、この形を自社サーバー・スタッフ用に写す。新しい仕組みは作らない。
- 外部の事例:
  - 招待リンクで本人に入力させる方式は、一般的な SaaS の招待と同じ形。
  - 本件の成否を外部の数値で示せる直接の根拠は無いため、外部の数値は使わない。
  - 成功は §1 の○×だけで判定する。

## 2. 対象と対象外

- 対象:
  - 招待リンク（作る・作り直す・取り消す）。
  - 申込フォーム（ログイン不要）。
  - 登録待ちの作成。
  - 登録番号。
  - 自社 Discord の受付と個室。
  - Discord ID の自動保存。
  - 仮パスワードと、変えるまで止める仕組み（スタッフ本体＝public.users）。
- 対象外:
  - メール送信。
  - 認証アプリそのもの（別のセッション、ADR-1048）。
  - お客様のチケット。
  - 閲覧者の受付の動き（変えない）。
  - 管理者が全項目を書く今の新規作成（残す）。

## 3. 1回目（KGI 1〜5）

### 3-1. 表（migration・1本）

- `public.staff_join_invites` を新しく作る。
- RLS は最初から付ける。形は `migrations/20261016_010000_add_google_config_rls.sql:2-9` と同じ FOR ALL・FORCE。
- 列:
  - `id BIGSERIAL PK`
  - `tenant_id INTEGER NOT NULL REFERENCES public.tenants(id)`
  - `role_id INTEGER NOT NULL`（会社のスキーマの roles の id。外部キーは付けない。会社ごとのスキーマのため）
  - `created_by INTEGER NOT NULL REFERENCES public.users(id)`
  - `token_hash BYTEA NOT NULL UNIQUE`（32 バイトの CHECK 付き）、`expires_at TIMESTAMPTZ NOT NULL`
  - `status TEXT NOT NULL CHECK (status IN ('open','submitted','linked','revoked'))`
  - `user_id INTEGER NULL REFERENCES public.users(id)`、`staff_id INTEGER NULL`
  - `reg_code_hash BYTEA NULL UNIQUE`（NULL か 32 バイトの CHECK 付き）、`reg_code_expires_at TIMESTAMPTZ NULL`
  - 列名は `hash` で終える。今の鍵の表（`migrations/20261013_160000_add_self_hosted_auth_tables.sql:51` の `token_hash`）と同じ名前の付け方で、AI 用の読み取りビューの拒否リスト（`migrations/20261017_130100_create_ai_ro_views.sql:23` の `hash`）に当たり、ビューから外れる。中身は sha256。
  - `discord_channel_id TEXT NULL`（2回目で使う。二重の個室を防ぐ）
  - `created_at`、`submitted_at`、`linked_at`、`revoked_at`（TIMESTAMPTZ）
- 人の正本は public.users と staff のままにする（ADR-1008）。
  - この表に名前やメールは置かない。置くのは、招待の状態と、それを一人の人へつなぐ番号だけ。
- 鍵と番号は生の値を保存しない。sha256 だけを置く（`backend/app/services/invite.py:28` と同じ）。
- 期限について:
  - リンクは 72 時間（KGI 4、`backend/app/services/invite.py:16` と同じ値）。
  - 登録番号は 7 日。Discord の招待の上限に合わせる（`backend/app/services/viewer_invite.py:19`）。

### 3-2. リンクの形

- 鍵の形は `"{tenant_id}.{secrets.token_urlsafe(32)}"`。URL は `{FRONTEND_BASE_URL}/staff-join#k=<鍵>` にする。
  - フラグメント（`#` の後ろ）を使うと、鍵がアクセスログや Referer に残らない。
- ログインしていない入口は、鍵の先頭の数字で会社の文脈を決める（`set_tenant_context`）。そのうえで RLS のもとで sha256 を引く。
  - 会社の番号を書き換えても、別の会社の行は見えない。sha256 も一致しない。
- 作り直すと `token_hash` と `expires_at` を上書きする。古い鍵の行は残らないので、古い鍵は開けない（KGI 3）。

### 3-3. API

| 道 | 権限 | 中身 |
|---|---|---|
| `POST /staff/join-invites` `{role_id}` | staff.create | 下の (1)〜(3) |
| `GET /staff/join-invites` | staff.view | open・submitted を新しい順に返す（状態・役割名・期限・作った人） |
| `POST /staff/join-invites/{id}/reissue` | staff.create | open だけ。新しい鍵を作り、期限を 72 時間に戻す |
| `POST /staff/join-invites/{id}/revoke` | staff.create | open だけ。revoked にする |
| `GET /public/staff-join/{鍵}` | なし | 会社名・役割名・期限を返す。無効なら 404 1 種類 |
| `POST /public/staff-join/{鍵}` | なし | 下の「申込」 |

- `POST /staff/join-invites` の中身:
  1. 役割の検査は、`assign_single_role` の前半（同じ会社にある・隠す役割でない・自分の最大 priority 未満）を関数に切り出して使う。
     - 切り出し先は `backend/app/services/role_assignment.py`。検査の書き方は1か所に保つ。
  2. 行を作る。
  3. URL を1回だけ返す。
- ログインしていない2本の道（GET と POST の `/public/staff-join/{鍵}`）:
  - `check_auth_rate_limit` で IP の回数を確かめる。
  - 無効な理由（期限切れ・使用済み・取消・存在しない）は区別せず、すべて 404 にする（推測防止）。
- 鍵の読み方（§10 R5）:
  - 形が `^[1-9][0-9]{0,9}\.[A-Za-z0-9_-]{43}$` に合わないときは、DB を引かずに 404。
  - 先頭の会社番号の会社が無い・停止中のときも、同じ 404。
  - 会社の分離は PostgreSQL の試験（CI の pytest PostgreSQL RLS）で示す。SQLite では set_tenant_context が何もしない（`backend/app/auth/dependencies.py:293-294`）ため、SQLite の試験を分離の根拠にしない。
- 申込 `POST /public/staff-join/{鍵}`:
  - 受け取る項目: StaffCreate から役割・状態・user_id・discord_user_id・is_employee・ui_preferences・additional_emails を除いたもの。
    - 姓名（日本語・かな・英語）と主メール。
    - 英語名は必須（ADR-159）。
  - 1 つのトランザクションで、次の (1)〜(6) を行う:
    1. 招待の行を `FOR UPDATE` で取る（open で期限内）。
    2. 人と staff を作る。今の `create_staff` の中身（`backend/app/routers/staff.py:606-648`）を、サービス関数 `create_staff_record` に切り出して、POST /staff と共用する。
       - staff は `status='pending'`。
       - users は `is_active=false` で作る（§10 R1）。ログイン・パスワード再設定の申請（`backend/app/routers/auth.py:602-641`）・トークンの道（`backend/app/auth/dependencies.py:72`）はすべて is_active を見るので、Discord の照合までは入れない。2回目の §4-3 手順6で true にする。
       - 既存の users は使い回さない（§10 R2）。同じメールの users がどこかに1件でもあれば 409（文言は `EMAIL_UNAVAILABLE_DETAIL`）。POST /staff の使い回し（`backend/app/routers/staff.py:86-102`）は今のまま。共用関数は引数 `allow_reuse`（POST /staff は真、申込は偽）と `is_active` を受け取る。
       - 共用関数は `(staff_id, user_id, user_created)` を返す。招待メールの鍵を作る部分（`backend/app/routers/staff.py:649-655`）は POST /staff 側に残す（§10 R4）。
       - 役割の付与者は、招待を作った人（`created_by` の User）。
       - 申込の時点で、招待を作った人を検査し直す（§10 R3）: users.is_active が真、今も staff.create を持つ、役割の検査が通る。どれか1つでも通らなければ 403。画面は「管理者に連絡してください」。
       - 監査ログの user_id も `created_by`。new_data に `"via":"self_registration"` を入れる。
    3. メールの重複は 409。文言は今の `EMAIL_UNAVAILABLE_DETAIL` と同じ（ADR-1063 What 6）。
    4. 登録番号を作る。`generate_signup_code`／`signup_code_sha256` をそのまま使う。
    5. 行を submitted にし、user_id・staff_id・reg_code_hash・reg_code_expires_at を入れる。
    6. commit → `reset_tenant_context` → `invalidate_user_permissions`。
       - ロール合わせ（`schedule_own_staff_sync`）は呼ばない。Discord ID がまだ無いため。
  - 招待メールの鍵（`create_invite_token`）は作らない。メールも送らない。
    - パスワードは2回目で、Discord の個室に出す。
  - commit の後に、自社サーバーの「スタッフ受付」部屋の招待リンクを作る（§3-4）。作れなければ null を返す。
  - 返す値: `{registration_code: "XXXX-XXXX-XXXX-XXXX", discord_invite_url: str | null}`。
    - 番号はこの1回だけ見せる。

### 3-4. Discord の招待リンク（共用化）

- `backend/app/services/viewer_invite.py:23` の Discord 呼び出しの部分を `create_channel_invite(channel_id) -> str | None` として切り出す。閲覧者の関数は、その切り出した関数を呼ぶだけにする（動きは同じ）。
- スタッフ受付部屋の番号は、設計図 tenant_1.json の key `staff_join_reception` から引く。
  - discord_id があればそれを使う。無ければ、名前が一意に1つ当たれば使う。
  - これは `backend/app/services/discord_own_staff_sync.py` の `_find_staff_role_id` と同じ引き方。
- 設計図への追加（1回目に入れる）:
  - カテゴリ `staff_join_rooms`「スタッフ登録」:
    - overwrites は @everyone deny VIEW_CHANNEL、@bot allow VIEW_CHANNEL。
  - 部屋 `staff_join_reception`「スタッフ受付」（カテゴリなし）:
    - @everyone allow VIEW_CHANNEL・deny SEND_MESSAGES。
    - @bot allow VIEW_CHANNEL・SEND_MESSAGES。
  - 反映は、今の自社サーバーの「確認 → 反映」で管理者が行う。新しい道は作らない。
- 実装の前の点検（読み取りのみ）: 自社サーバーで Bot に Create Instant Invite が付いているか。
  - 付いていなければ、リンクは null になる。完了画面は「Discord の参加リンクは管理者から届きます」と出す。
  - 権限を足すかどうかは PO に聞く。

### 3-5. 画面

- スタッフ一覧（`frontend/src/pages/staff/StaffPage.tsx`）:
  - ツールバーに「招待リンクを作る」を置く。
  - Modal の中身:
    - 役割の Select。
    - 作成すると読み取り専用の欄にリンクが出る。
    - コピーボタン。
  - 「招待リンクの一覧」の Modal の中身:
    - DataTable で、状態・役割・期限を並べる。
    - 操作は「作り直す」と「取り消す」。取り消しは ConfirmModal を使う。
  - 登録待ちの人は、今の状態の表示（`staff.status_pending`）で一覧に出る。
- 申込ページ:
  - 新しいファイル frontend/src/pages/staff-join/StaffJoinPage.tsx。
  - `frontend/src/App.tsx` のログイン不要の道（`/reset-password` の並び、`frontend/src/App.tsx:175`）に `/staff-join` を足す。
  - 入力欄は `StaffFormFields` を使う（役割の欄は出さない）。
  - 完了画面に出すもの:
    - 番号（4文字ずつ区切り、コピーボタン付き）。
    - Discord の参加リンク。
    - 次の手順の説明3行。
- 守ること:
  - 部品は components の金型だけを使う（ADR-144）。色はトークン（ADR-067）。文言は全部 `t()`、ja と en は同じキー（ADR-027）。
  - コピーボタン専用の金型は無い（`frontend/src/components/` に copy・clipboard の名前のファイルは 0 件、2026-11-07 点検）。今ある書き方に合わせて、金型の Button（variant secondary・size sm）を押すと `navigator.clipboard.writeText` で写し、2 秒だけ文言を「コピーしました」に変える（`frontend/src/pages/super-admin/ViewerAccountsPage.tsx:292-299`・`:503-508` と同じ）。新しい金型は足さない。
  - 読み取り専用の欄は、今ある TextFieldControl の読み取り専用の指定で出す。指定が無ければ実装を止めて報告する（金型を勝手に足さない。`docs/CC_UI_GOVERNANCE.md:13-15`）。

## 4. 2回目（KGI 6〜10）

### 4-1. 列（migration・1本）

- `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_must_change BOOLEAN NOT NULL DEFAULT false;`
- ORM の User にも同じ列を足す。

### 4-2. 変えるまで止める

- `backend/app/auth/dependencies.py:108` の get_current_user には戻り口が3つある（smoke 用・一時記憶が当たったとき・`_authenticate_self_token` の後。§10 R6）。戻り口ごとに足すと漏れるので、今の関数を内側の関数に改名し、get_current_user はそれを呼んだ後に1か所で次を行う:
  - `user.password_must_change` が真で、道が許可一覧に無ければ、403 `password_change_required`。
- 許可一覧（1か所の定数）: `/api/v1/auth/password/change` だけ（§10 S1 で `/api/v1/me/permissions` を外した。下の変更ページはこれを呼ばない）。
  - `/api/v1/auth/logout` は get_current_user を使わない（`backend/app/routers/auth.py:181-187`）ので、一覧に入れなくても止まらない。
- `/password/change` の成功時の UPDATE に `password_must_change = false` を足す。
- パスワード再設定の確定（`backend/app/routers/auth.py` の再設定の確定。is_active を見る行は `:681`）の UPDATE にも `password_must_change = false` を足す。本人がメールの鍵で自分のパスワードを決めたため（§10 S2 の候補。§4-3 の「再設定へ案内」の道で二重に変更させない）。
- ログインの返事（SelfTokenResponse）に `must_change_password: bool` を足す。
- 画面の動き（§10 S1）:
  - 今の設定画面（`/account/settings`、`frontend/src/App.tsx:298`）はシェルの中にある。シェルは許可一覧に無い道を多く呼ぶ（`frontend/src/components/DesktopShell.tsx:35-40`）。SecuritySection の本体も、表示するとすぐに他の道を呼ぶ（`frontend/src/pages/account-settings/SecuritySection.tsx:39`・`:148`・`:331-334`）。だから、ここへは移さない。
  - 新しい道 `/password-change` を、シェルの無いログイン必須の並び（`frontend/src/App.tsx:180-182`。ProtectedRoute は API を呼ばない）に足す。新しいファイル frontend/src/pages/password-change/PasswordChangePage.tsx。
  - 変更欄（`frontend/src/pages/account-settings/SecuritySection.tsx:284-329` の form（:240 は関数の始まり。3回目の審査 T1 で訂正））を、新しいファイル frontend/src/features/auth/PasswordChangeForm.tsx に切り出す。SecuritySection とこのページの両方がそれを使う（同じ部品を2つ書かない）。SecuritySection の見た目と動きは変えない。
  - ページに出すもの: 変更欄と、ログアウトのボタン（今の useAuth のログアウトを使う）。このページ自身は他の API を呼ばない。
  - シェルの外の UiPrefs・Locale・Theme の3つの Provider は `/staff/me` を呼ぶ（`frontend/src/contexts/UiPrefsContext.tsx:103`・`frontend/src/contexts/LocaleContext.tsx:46`・`frontend/src/contexts/ThemeContext.tsx:76`）。このページでは 403 になるが、catch で既定値に戻って動く（同 `:108`・`:53`・`:83`。Opus が origin/main で照合）。この3つは変えない。移す処理は api.ts の「今の道が /password-change なら移さない」で止まる（3回目の審査 T2）。
  - 変更が成功したら `window.location.assign("/")` でページ全体を読み込み直し、3つの Provider の設定を取り直す（T2）。
  - ログインの返事が真なら、`/password-change` へ移す。
  - `frontend/src/lib/api.ts` の共通の失敗処理で、403 `password_change_required` を受けたら `/password-change` へ移す。今の道が既に `/password-change` なら移さない（同じページへ何度も移すのを防ぐ）。
- 影響: 既存の人は全員 false なので、何も変わらない。

### 4-3. Discord の受付（自社サーバー）

- 新しいファイル backend/app/discord_gateway/staff_join.py。`backend/app/discord_gateway/viewer_trial.py` と同じ順で書く。
  - ボタンの custom_id は `staff_join_open`。前置きは `staff_join_`。
  - 番号の入力欄（Modal）は 16〜19 文字。
  - 失敗回数は Redis の `staff_code_fail:{member.id}` に数える。5 回／3600 秒（KGI 6）。
- 振り分け: `backend/app/discord_gateway/client.py:263` の閲覧者の分岐の直後に、`staff_join_` の分岐を足して `return` する。
  - お客様のチケットの道（`ticket_open`）には入らない。リードは作らない（KGI 13）。
- 会社の決め方: guild の番号から purpose='own' で引く新しい関数（今の `_resolve_tenant_id` は customer 専用のまま）。
- 番号を照合する前に、次を見る（§10 R7）:
  - この Discord ID を、この会社の staff が既に持っていれば「既に登録済み」と返す。失敗には数えない（KGI 7 の試験はこの道で見る）。
  - 管理者のロール（下の手順4）が1つも無ければ、何も変えずに「受付の準備ができていません。管理者に連絡してください」と返す。失敗には数えない。管理者が見られない個室は作らない。
- 番号が合ったとき（1 トランザクション）:
  1. 会社の文脈を付ける。
  2. 行を `FOR UPDATE` で取る（`reg_code_hash` が一致・submitted・期限内）。無ければ失敗に数える。
  3. staff の discord_user_id が既にあるとき、またはこの Discord ID を別の staff が持っているときは、「既に登録済み」と返す。
  4. 個室を作る:
     - カテゴリは `staff_join_rooms`。
     - 見られるのは、本人・Bot・管理者のロール。
     - 管理者のロール＝アプリで `staff.create` を持つ役割のうち、`roles.discord_role_id` がある Discord ロール。正本はアプリの権限。
     - `backend/app/discord_gateway/private_channel.py:50` の `create_private_text_channel` に、既定が空のキーワード引数 `extra_view_role_ids` を足して使う。今の呼び出し元は変わらない。
  5. 仮パスワードは `secrets.token_urlsafe(18)` で作り、`check_password` で検査し、別スレッドで `hash_password` する（`backend/app/discord_gateway/viewer_trial.py:333` と同じ）。
  6. 書き込み:
     - users の `password_argon2_hash`、`password_must_change=true`、`is_active=true`。
     - staff の `discord_user_id`。
     - 招待の行を linked にし、`discord_channel_id` を入れ、`reg_code_hash=NULL` にする。
  7. commit → `reset_tenant_context`。
  8. 個室に出す: メール、仮パスワード、ログインの URL、「最初のログインで変更してください」。
  9. `schedule_own_staff_sync(tenant_id)` を予約する（スタッフのロールと役割のロールが付く）。
  - 失敗したら rollback して、個室を消す（閲覧者と同じ）。
  - commit の後に個室への投稿（手順8）が失敗したとき（§10 R7）: 同じ内容を、本人だけに見える返事（ephemeral の followup）で送る。それも失敗したときは記録に残し、本人には「パスワードを忘れた」から再設定するよう案内する（この時点で is_active は真なので、再設定のメールが届く）。
- 受付ボタンの設置:
  - `backend/app/viewer_discord_cli.py` と同じ型の CLI に action `post-staff-button` を足す。stdin の JSON だけを受け取る。
  - 管理者は、本番の決まった手順で1回だけ置く。
- 持ち主のいない個室の片付けは、閲覧者の `sweep_orphan_rooms` と同じ考え方で、`discord_channel_id` を見る。

### 4-4. 1回目と2回目の間

- 1回目だけが本番に入った間は、受付ボタンがまだ無い。
- 申込で作った人は is_active=false なので、この間はログインもパスワード再設定もできない（§10 R1。運用ではなくコードで止める）。
- 実際のスタッフにリンクを渡すのは2回目が本番に入ってから（PO への案内に書く）。

## 5. 3回目（KGI 11〜12）— 骨組みだけ

- 始める条件: 別のセッションの認証アプリが本番に入ったこと。
- 方針:
  - get_current_user の止め方（§4-2）と同じ場所に、「セットアップ待ち」の止め方を足す。
    - 対象は、staff.status='pending' で自己登録から来た人。
    - 止める条件は、パスキーが 1 件以上、かつ認証アプリが有効、になるまで。
  - 両方がそろった時点の書き込みで、staff を active に変える。
- 詳しい設計は、認証アプリの実物ができてから、その表・関数名で書く。
- 2回目と3回目の間は、登録待ちの人もパスワード変更の後は使える。今の管理者作成の人と同じ扱いで、悪くはならない。

## 6. 弊害・リスクと対処

| リスク | 対処 |
|---|---|
| リンクが漏れると、他人が登録できる | 72 時間・1 回限り・取り消し可。作られる人は is_active=false で、Discord の番号と個室を経ないとログインも再設定もできない。既存の人は使い回さない |
| 仮パスワードが Discord に残る | 閲覧者と同じ（PO 決定）。変えるまで他の画面は止まる |
| 招待を作った人が後で停止された・権限や役割が下がった | 申込の時点で、その人の is_active・staff.create・役割の検査をし直し、どれかが通らなければ 403。画面は「管理者に連絡してください」 |
| 個室を作った後の投稿だけが失敗する | 本人だけに見える返事で同じ内容を送る。それも失敗したら記録し、「パスワードを忘れた」からの再設定を案内する |
| 管理者の Discord ロールが無いまま受付が動く | 番号を照合する前に止め、何も変えずに案内だけ返す（失敗に数えない） |
| 自社サーバーの Bot に招待の権限が無い | リンクは null。完了画面で案内する。権限を足すかは PO に聞く |
| お客様のチケットに混ざる | custom_id の前置きを分け、`ticket_open` の前で `return` する。既存試験と新しい試験で確かめる |
| 会社の取り違え | 表は FORCE RLS。鍵の会社の番号を書き換えても sha256 が一致しない |

## 7. 計画票（PR の単位）

| 回 | PR | 危険パス | GO |
|---|---|---|---|
| 1 | migration（招待の表） | migrations/ | 必要（委任 GO） |
| 1 | バックエンド（API・共用化・設計図の追加） | なし | — |
| 1 | 画面（一覧の Modal・申込ページ） | なし | — |
| 2 | migration（users の列） | migrations/ | 必要（委任 GO） |
| 2 | 止める仕組み＋ログインの返事＋画面 | なし | — |
| 2 | Discord の受付＋CLI | なし | — |
| 3 | 3回目の設計の後に決める | — | — |

- 実装はクラウドの Sonnet が行う。
- 審査は Opus の reviewer が行う。
- マージ・デプロイ・本番確認は Opus が行う（ADR-1003 の委任）。

## 8. 維持の仕組み

- 守り手: 人手で守る
  - 実装の後は、CI の必須の試験が守る。止めない道の一覧は、backend/app/auth/dependencies.py の1つの定数に置く。
- 試験:
  - 招待の作成・作り直し・期限・取消・申込・重複。
  - 申込の後にパスワード再設定を申請しても、鍵が作られずメールも出ない（§10 R1）。
  - 申込のメールが既存の users にあれば、同じ会社でも 409（§10 R2）。POST /staff の使い回しは今のまま（既存試験が緑）。
  - 招待を作った人が停止・staff.create なしなら 403（§10 R3）。
  - 鍵の形が違う・会社が無いときは 404（§10 R5）。
  - password_must_change が真なら、許可一覧以外の道は3つの戻り口（smoke を含む）のどれでも 403（§10 R6）。
  - 既に登録済みの Discord ID は失敗に数えない。管理者ロールが無いときは何も作らない（§10 R7）。
  - 403 で止める仕組み。
  - Discord の照合・回数制限・二重防止。
  - お客様のチケットの振り分けが変わらないこと。
  - これらを CI の必須の試験に入れる。
- 許可一覧（止めない道）は、1 か所の定数にする。
- 設計図の key（`staff_join_reception`、`staff_join_rooms`）は、自社サーバーの「確認」でずれを表示する（今の仕組みのまま）。
- ADR-1068 を Accepted にするのは、1回目と2回目の KGI がすべて○になったとき。

## 9. 設計の審査（Opus 自己審査・同じ AI による審査で、独立した第二者の審査ではない）

- 判定: APPROVE（1回目・2回目）。3回目は骨組みだけのため、対象外。
- 確かめた点:
  - 既存仕様との整合:
    - 人の正本（ADR-1008）。public.users と staff にだけ書く。
    - 役割の正本（user_roles）。`assign_single_role` を共用する。
    - 会社の分け方（ADR-1018、ADR-1063 What 7）。FORCE RLS を付ける。
    - 重複の文言（ADR-1063 What 6）。
    - 閲覧者の型を写し、新しい仕組みは作らない。
  - 根拠: 全部 recon の行番号と照合した。
  - 受入条件は、§1 の表の検証方法で○×が決まる。
  - 実装範囲: 触るファイルと、触らない範囲（お客様のチケット、閲覧者の動き、管理者の新規作成）を書いた。
- 実装カードで実物を確かめる点（設計の前提は変えない）:
  - 自社サーバーの Bot に招待の権限が付いているか（§3-4。無いときの動きは決めてある）。
- この自己審査では、§10 の R1・R2 を見落としていた。

## 10. クラウドの設計審査（Opus・読むだけ）

- 1回目: 2026-11-07、対象 979004eff。判定 REVISE。
- 指摘と直し方:

| # | 重さ | 指摘 | 直した場所 |
|---|---|---|---|
| R1 | 必須 | 申込で作る users が is_active=true だと、パスワード再設定（`backend/app/routers/auth.py:602-641`）で Discord を通らずにログインできる | §3-3（is_active=false で作る）、§4-3 手順6（true にする）、§4-4、§6、§8 |
| R2 | 必須 | `backend/app/routers/staff.py:86-102` が同じ会社の既存 users を使い回すため、申込で他人のアカウントに staff が付き、2回目でパスワードが上書きされうる | §3-3（申込は新規だけ。既存メールは 409） |
| R3 | 必須 | `backend/app/services/role_assignment.py:49-70` は priority しか見ない。招待を作った人が停止・権限を失っても申込が通る | §3-3（申込時に検査し直す）、§6 |
| R4 | 推奨 | 共用関数が `user_created` を返さないと、招待メールの分岐（`backend/app/routers/staff.py:649-655`）が変わる | §3-3 |
| R5 | 推奨 | 鍵の先頭が数字でない・会社が無いときの扱いが無い。SQLite の試験では RLS の分離を示せない | §3-3 |
| R6 | 推奨 | get_current_user の戻り口は3つ（smoke `backend/app/auth/dependencies.py:159`）。自分の情報の道が未特定 | §4-2（1か所で止める。当初は `/api/v1/me/permissions` も許可したが、S1 で外した） |
| R7 | 推奨 | 管理者ロールが無いとき・2回目の照合（KGI 7）・commit 後の投稿失敗の扱いが無い | §4-3 |
| — | 訂正 | recon の viewer_dependencies.py の行番号 | recon §3（106-108 に訂正） |

- 審査の確認で合っていた点: 引用の行番号（上の訂正以外）、NOBYPASSRLS による会社の分離（`backend/app/auth/dependencies.py:280`）、Redis の道でも DB を読み直すこと（`backend/app/auth/dependencies.py:187-192`）、KGI 1〜10 と 13 が○×で判定できること。
- 2回目: 2026-11-07、対象 ee50d2e43。判定 REVISE。R1〜R7 の直しは全部「合う」。新しい指摘:

| # | 重さ | 指摘 | 直した場所 |
|---|---|---|---|
| S1 | 必須 | パスワード変更ページの道と置き場所が決まっていない。今の設定画面とシェルは許可一覧に無い道を呼ぶので、403 が続き、同じページへ何度も移す | §4-2（シェルの無い新しい道、変更欄の切り出し、移す処理の止め、許可一覧から me/permissions を外す） |
| S2 | 推奨 | 審査の返事が記録の上限で途中までしか読めなかった（R7 の「軽い穴」とだけ読めた）。Opus が R7 の道を読み直し、再設定で決めたパスワードの後にもう一度変更させる二重の手間を見つけて直した | §4-2（再設定の確定でも must_change を false にする） |

- 3回目: 2026-11-07、対象 4a15cf7c9。判定 APPROVE（必須の指摘なし）。S1・S2 は「合う」。シェルの無い並びと ProtectedRoute は API を呼ばない。ログアウトは get_current_user を通らない（`backend/app/routers/auth.py:181-187`）。再設定の確定は、1回限り・期限付きの鍵（`:663`）、is_active の確認（`:681`）、全セッションの失効（`:695`）が揃っており、must_change を false にしても危険は無い。推奨2件は次のとおり直した:

| # | 重さ | 指摘 | 直した場所 |
|---|---|---|---|
| T1 | 推奨 | SecuritySection の form の行番号は 284-329 | §4-2 |
| T2 | 推奨 | シェル外の3つの Provider が `/staff/me` を呼ぶ。403 でも既定値で動くことを明記し、成功後に設定を取り直す | §4-2 |

- 状態: 設計審査済み（クラウドの Opus 審査、3回目 APPROVE。推奨は反映済み）。
