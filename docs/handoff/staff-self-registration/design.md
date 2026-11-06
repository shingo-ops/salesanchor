# スタッフの自己登録 — 設計（design）

| 項目 | 内容 |
|------|------|
| 状態 | 設計案（Opus 作成・自己審査は §9）。実装は PO の実装承認の後 |
| ADR | ADR-1068（Proposed・本 PR の草案） |
| 現在地 | `docs/handoff/staff-self-registration/recon.md` |
| PO 承認 | KGI 1〜13 と3回の分け方に「1」（2026-11-07）、初回ログイン情報＝「2,閲覧用ページと同じ仕組み」（2026-11-07） |

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

## 1. KGI（PO 承認済み）と検証方法

| # | 基準（○×で見る） | 検証方法 | 回 |
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
  - `token_sha256 BYTEA NOT NULL UNIQUE`、`expires_at TIMESTAMPTZ NOT NULL`
  - `status TEXT NOT NULL CHECK (status IN ('open','submitted','linked','revoked'))`
  - `user_id INTEGER NULL REFERENCES public.users(id)`、`staff_id INTEGER NULL`
  - `reg_code_sha256 BYTEA NULL UNIQUE`、`reg_code_expires_at TIMESTAMPTZ NULL`
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
- 作り直すと `token_sha256` と `expires_at` を上書きする。古い鍵の行は残らないので、古い鍵は開けない（KGI 3）。

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
- 申込 `POST /public/staff-join/{鍵}`:
  - 受け取る項目: StaffCreate から役割・状態・user_id・discord_user_id・is_employee・ui_preferences・additional_emails を除いたもの。
    - 姓名（日本語・かな・英語）と主メール。
    - 英語名は必須（ADR-159）。
  - 1 つのトランザクションで、次の (1)〜(6) を行う:
    1. 招待の行を `FOR UPDATE` で取る（open で期限内）。
    2. 人と staff を作る。今の `create_staff` の中身（`backend/app/routers/staff.py:606-648`）を、サービス関数 `create_staff_record` に切り出して、POST /staff と共用する。
       - staff は `status='pending'`。
       - 役割の付与者は、招待を作った人（`created_by` の User）。
       - 監査ログの user_id も `created_by`。new_data に `"via":"self_registration"` を入れる。
    3. メールの重複は 409。文言は今の `EMAIL_UNAVAILABLE_DETAIL` と同じ（ADR-1063 What 6）。
    4. 登録番号を作る。`generate_signup_code`／`signup_code_sha256` をそのまま使う。
    5. 行を submitted にし、user_id・staff_id・reg_code を入れる。
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
  - 新しいファイル `frontend/src/pages/staff-join/StaffJoinPage.tsx`。
  - `App.tsx` のログイン不要の道（`/reset-password` の並び、`frontend/src/App.tsx:175`）に `/staff-join` を足す。
  - 入力欄は `StaffFormFields` を使う（役割の欄は出さない）。
  - 完了画面に出すもの:
    - 番号（4文字ずつ区切り、コピーボタン付き）。
    - Discord の参加リンク。
    - 次の手順の説明3行。
- 守ること:
  - 部品は components の金型だけを使う（ADR-144）。色はトークン（ADR-067）。文言は全部 `t()`、ja と en は同じキー（ADR-027）。
  - コピーボタンと読み取り専用の欄に既存の金型が無い場合は、金型を足してから使う。直書きはしない（実装カードで実物を点検して決める）。

## 4. 2回目（KGI 6〜10）

### 4-1. 列（migration・1本）

- `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_must_change BOOLEAN NOT NULL DEFAULT false;`
- ORM の User にも同じ列を足す。

### 4-2. 変えるまで止める

- `backend/app/auth/dependencies.py:108` の get_current_user には戻り口が2つある（一時記憶が当たったときと、`_authenticate_self_token` の後）。両方で次を行う:
  - `user.password_must_change` が真で、道が許可一覧に無ければ、403 `password_change_required`。
- 許可一覧（1か所の定数）: `/api/v1/auth/password/change`、`/api/v1/auth/logout`。
  - 実装カードで、画面が最初に読む「自分の情報」の道を実物で特定して足す。
- `/password/change` の成功時の UPDATE に `password_must_change = false` を足す。
- ログインの返事（SelfTokenResponse）に `must_change_password: bool` を足す。
- 画面の動き:
  - 返事が真なら、パスワード変更の画面へ移す。
  - `frontend/src/lib/api.ts` の共通の失敗処理で、403 `password_change_required` を受けたら同じ画面へ移す。
  - 変更の部品は `frontend/src/pages/account-settings/SecuritySection.tsx` の変更欄を使う（同じ部品を2つ書かない）。
- 影響: 既存の人は全員 false なので、何も変わらない。

### 4-3. Discord の受付（自社サーバー）

- 新しいファイル `backend/app/discord_gateway/staff_join.py`。`viewer_trial.py` と同じ順で書く。
  - ボタンの custom_id は `staff_join_open`。前置きは `staff_join_`。
  - 番号の入力欄（Modal）は 16〜19 文字。
  - 失敗回数は Redis の `staff_code_fail:{member.id}` に数える。5 回／3600 秒（KGI 6）。
- 振り分け: `backend/app/discord_gateway/client.py:263` の閲覧者の分岐の直後に、`staff_join_` の分岐を足して `return` する。
  - お客様のチケットの道（`ticket_open`）には入らない。リードは作らない（KGI 13）。
- 会社の決め方: guild の番号から purpose='own' で引く新しい関数（今の `_resolve_tenant_id` は customer 専用のまま）。
- 番号が合ったとき（1 トランザクション）:
  1. 会社の文脈を付ける。
  2. 行を `FOR UPDATE` で取る（`reg_code_sha256` が一致・submitted・期限内）。無ければ失敗に数える。
  3. staff の discord_user_id が既にあるとき、またはこの Discord ID を別の staff が持っているときは、「既に登録済み」と返す。
  4. 個室を作る:
     - カテゴリは `staff_join_rooms`。
     - 見られるのは、本人・Bot・管理者のロール。
     - 管理者のロール＝アプリで `staff.create` を持つ役割のうち、`roles.discord_role_id` がある Discord ロール。正本はアプリの権限。
     - `backend/app/discord_gateway/private_channel.py:50` の `create_private_text_channel` に、既定が空のキーワード引数 `extra_view_role_ids` を足して使う。今の呼び出し元は変わらない。
  5. 仮パスワードは `secrets.token_urlsafe(18)` で作り、`check_password` で検査し、別スレッドで `hash_password` する（`viewer_trial.py:333` と同じ）。
  6. 書き込み:
     - users の `password_argon2_hash` と `password_must_change=true`。
     - staff の `discord_user_id`。
     - 招待の行を linked にし、`discord_channel_id` を入れ、`reg_code_sha256=NULL` にする。
  7. commit → `reset_tenant_context`。
  8. 個室に出す: メール、仮パスワード、ログインの URL、「最初のログインで変更してください」。
  9. `schedule_own_staff_sync(tenant_id)` を予約する（スタッフのロールと役割のロールが付く）。
  - 失敗したら rollback して、個室を消す（閲覧者と同じ）。
- 受付ボタンの設置:
  - `backend/app/viewer_discord_cli.py` と同じ型の CLI に action `post-staff-button` を足す。stdin の JSON だけを受け取る。
  - 管理者は、本番の決まった手順で1回だけ置く。
- 持ち主のいない個室の片付けは、閲覧者の `sweep_orphan_rooms` と同じ考え方で、`discord_channel_id` を見る。

### 4-4. 1回目と2回目の間

- 1回目だけが本番に入った間は、受付ボタンがまだ無い。
- そのため、実際のスタッフにリンクを渡すのは2回目が本番に入ってから（PO への案内に書く）。

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
| リンクが漏れると、他人が登録できる | 72 時間・1 回限り・取り消し可。作られるのは「登録待ち」で、Discord の番号と個室を経ないとパスワードが無い |
| 仮パスワードが Discord に残る | 閲覧者と同じ（PO 決定）。変えるまで他の画面は止まる |
| 招待を作った人の役割が後で下がった | 申込の時点で役割の検査をし直し、通らなければ 403。画面は「管理者に連絡してください」 |
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

- 試験:
  - 招待の作成・作り直し・期限・取消・申込・重複。
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
  - 画面が最初に読む「自分の情報」の道の名前（§4-2 の許可一覧）。
  - コピーボタンの金型があるか（§3-5）。
  - 自社サーバーの Bot に招待の権限が付いているか（§3-4。無いときの動きは決めてある）。
