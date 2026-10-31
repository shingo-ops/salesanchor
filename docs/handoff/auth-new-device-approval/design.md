# 設計書: 知らない機械からのログインは、いつもの機械で許可するまで入れない

- 状態: 設計案（Opus 作成）。審査: 下の「審査記録」に追記する
- 対応 ADR: ADR-1055（本 PR で Proposed として起案）。ADR-1013（自社ログイン）の続き。ADR-1048（管理者だけの2段階ログイン・Proposed・未実装）の「機械を覚える」「番号で許可する」部分を全員向けに広げて取り込む
- 合格の基準: docs/handoff/auth-new-device-approval/kgi.md（K1〜K9・PO 承認済 2026-11-01）
- 事実の出どころ: docs/handoff/auth-new-device-approval/recon.md（基準 7e9155163）。本書で `recon:B` のように節を指す
- 本番の数: /tmp/CC報告ファイル/new-device-prod-counts-20261101.txt（2026-11-01 00:22 JST・reader 鍵）

## 1. 目的と利用者に見える変化

パスワードが漏れても、知らない機械からは入れないようにする（不正ログイン対策）。

| 場面 | 変更前 | 変更後 |
|---|---|---|
| 初めての機械でパスワードを入れる | そのまま入れる | 「いつもの機械で許可してください」と2けたの番号が出て待つ（K1） |
| いつもの機械 | 何も起きない | 1分以内に「新しい機械からログインしようとしています」の小窓が出る。機械の種類・場所の目安・時刻と、番号3つ・「私ではない」が並ぶ。メールも届く（リンクなし）（K2） |
| 正しい番号を押す | — | 待っていた機械が入れて、次から聞かれない（K3・K5） |
| 「私ではない」を押す | — | 待っていた機械は入れない。押した機械以外は全部ログアウト。パスワード変更を勧める（K4） |
| いつもの機械が無い | — | 予備の合言葉（10個・1回ずつ）で入る（K6）。それも無い人は、しんごさんか担当エンジニアが管理画面で許可する（K7） |
| アカウント設定 | パスキーの一覧だけ | 「ログインしている機械」の一覧（日時・場所の目安・機械の種類）。その場でログアウトできる（K8） |
| 記録 | 誰のログインか・理由が残らない（recon:E） | 誰が・成否・理由・初めての機械か が残る。パスワードは残らない（K9） |

## 2. 対象と対象外

- 対象: アプリのログイン（パスワード `backend/app/routers/auth.py:307-366`・パスキー `:901-995`・更新 `:369-401`）。全利用者（super admin・点検専用の人を含む）
- 対象外（理由）
  - 閲覧ページの別ログイン（`backend/app/routers/viewer.py:153`。別の利用者表・別の道。後の便で同じ部品を使う）
  - smoke の固定トークンの道（`backend/app/auth/dependencies.py:148-170`。ログインを通らず、super admin を返さない構造ガードあり）
  - ADR-1048 の6桁コード（認証アプリ）。ADR-1048 に残す
  - 機械の名前付け（後回し・PO 11/1）

## 3. 決めたこと（Opus 判断・大手のやり方に沿う）

| # | 論点 | 決定 | 根拠 |
|---|---|---|---|
| D1 | 許可の形 | 待つ側に2けたの番号、いつもの機械に候補3つ。正しい番号＝許可。違う番号＝その依頼だけ拒否（全ログアウトはしない） | ADR-1048 の審査済み方式。Microsoft Authenticator の番号照合（押し続け攻撃対策）。kgi.md の大手資料 |
| D2 | 機械の印 | Cookie `sa_device`（32バイト乱数・HttpOnly・Secure・SameSite=Strict・path `/api/v1/auth`・180日・ログインのたび延長）。DB は SHA-256 のみ。1つの印を複数の人が使える（`UNIQUE(user_id, token_hash)`） | ADR-1048 の形。login の口にも届くよう path を `/api/v1/auth` に広げる（更新 Cookie と同じ path `auth.py:220-230`） |
| D3 | パスキーでのログイン | 知らない機械でも入れて、その機械をいつもの機械に加える。メールで知らせる | パスキー自体が機械に結び付く2つ目の確認（Google はパスキーで2段階確認を省く）。K1 は「パスワードが正しくても」 |
| D4 | 仕組みを入れた日にログイン中の機械 | 機械の印が付いていない更新トークン（＝本便より前に作られた組）が更新されたとき、その機械をいつもの機械として登録する（`created_via='bootstrap'`）。組は最長30日（`self_tokens.py:25`）で切れるので、この扱いは30日で自然に終わる | kgi.md「最初から守ること」 |
| D5 | 一度もログインしていない人の最初のログイン | `users.last_login IS NULL` かつ 機械の登録が0件 のときだけ、その機械を最初のいつもの機械にする（`first_login`）。直後に予備の合言葉を作る小窓を出す。メールで知らせる | Meta は登録時の機械を信頼する。本番で該当5人（counts ファイル） |
| D6 | 依頼の保存先 | DB の表 `public.auth_login_requests`（Redis にしない）。有効30分 | K7 の管理者許可と記録に要る（5分の Redis では足りない） |
| D7 | 記録（K9） | 既存の `public.auth_events` に列 `user_id`・`reason`・`is_new_device` を足す。口の中で `request.state.auth_audit` に入れ、既存の middleware（`backend/app/middleware/audit.py:236-254`）が書く | 記録の置き場を1つに保つ（新しい表を作らない） |
| D8 | 全部ログアウト | 共通関数 `revoke_user_sessions(db, user_id, except_family_id=None, device_id=None)` を1つ作り、既存の直書き2か所（`auth.py:524-529`・`:611-616`）もこれに置き換える。アクセストークンに組の id `sid` を入れ、失効した組の id を Redis `auth:fam_revoked:{sid}`（TTL 900秒）に置いて、毎回の確かめで拒否する | recon:C「専用の関数が無い」「アクセストークンは最長900秒生きる」 |
| D9 | 場所の目安 | DB-IP IP to City Lite（CC BY 4.0・MMDB・毎月）を `maxminddb`（Apache-2.0・3.2.0）で読む。ファイルが無い・読めないときは「不明」。場所を出す画面とメールに「IP Geolocation by DB-IP」のリンクを付ける。IP は判定に使わない | 前段に中継なし＝X-Real-IP が本当の IP（DNS 確認・recon:D）。MaxMind はアカウントが要る |
| D10 | 機械の種類 | User-Agent から自前の小さな関数で「iPhone・Safari」「Mac・Chrome」等を作る（依存を足さない） | 依存を増やさない |
| D11 | 切り替え | 環境変数 `AUTH_DEVICE_APPROVAL=off\|enforce`（既定 off）。off でも機械の登録と印の発行はする（止めないだけ）。enforce は PR-B で deploy.yml に入れる | 点検専用の人の印を先に用意するため |
| D12 | 点検専用の人（本番 user87） | 管理用の命令 `python -m app.cli.issue_trusted_device --user-id <id> --label prod-ui-check` で印を1つ発行し、表示せずに GitHub の秘密 `SMOKE_E2E_DEVICE_TOKEN` へ直接流す。点検はログイン前に `sa_device` を付ける | 例外を作らず全員に効かせる |

## 4. 変更内容（段ごと）

### 段A（PR-A・migrations を含む＝危険 PR・GO 要）

#### A-1 migration（1本・追加のみ・冪等・全列 COMMENT・public に置き `public.users(id)` にぶら下げる。置き場と登録は recon:J の決まり `scripts/run_all_migrations.sh`・`migration-guard.yml:119`・`PUBLIC_TABLES :224`）

- `public.user_trusted_devices`: id BIGSERIAL PK / user_id BIGINT NOT NULL FK CASCADE / token_hash BYTEA NOT NULL / label VARCHAR(100) / user_agent VARCHAR(500) / created_via VARCHAR(20) NOT NULL CHECK IN ('bootstrap','first_login','passkey','device_approval','recovery_code','admin_approval','cli') / created_ip VARCHAR(45) / created_location VARCHAR(200) / created_at / last_used_at / last_ip / last_location / revoked_at。UNIQUE(user_id, token_hash)。索引 user_id
- `public.auth_login_requests`: id UUID PK / user_id FK CASCADE / status VARCHAR(20) CHECK IN ('pending','approved','rejected','expired','completed') / match_number CHAR(2) / candidates VARCHAR(8)（例 "47,12,85"） / pending_token_hash BYTEA UNIQUE / device_token_hash BYTEA（待つ機械に既にある印の hash・無ければ NULL） / label / user_agent / ip / location / created_at / expires_at / decided_at / decided_via VARCHAR(20) CHECK IN ('device','admin','recovery_code') / decided_by_user_id BIGINT NULL FK SET NULL / decided_device_id BIGINT NULL FK SET NULL / reject_reason VARCHAR(30) / failed_code_attempts SMALLINT DEFAULT 0。索引 (user_id, created_at DESC)・(status, expires_at)
- `public.user_recovery_codes`: id / user_id FK CASCADE / code_hash TEXT（argon2・既存 `hash_password`） / created_at / used_at / used_request_id UUID NULL
- `public.auth_refresh_tokens` に `trusted_device_id BIGINT NULL REFERENCES public.user_trusted_devices(id) ON DELETE SET NULL`＋索引
- `public.auth_events` に `user_id BIGINT NULL`・`reason VARCHAR(50) NULL`・`is_new_device BOOLEAN NULL`＋索引 (user_id, created_at DESC)
- ai_ro / ai_cloud の見え方: 新しい表・列は既存の分類の決まり（`migrations/20261024_100300_create_ai_cloud_views.sql:48-50`）に従い、hash・IP・UA を伏せる側に入れる。guard が分類を求める場合は同じ migration で足す
- 試験用の最小定義 `.github/workflows/migration-test.yml:1338-1352` の auth_events にも同じ列を足す

#### A-2 backend

- 新しい部品 `backend/app/auth/devices.py`（生 SQL。`self_tokens.py:3-5` と同じ理由で ORM を作らない）
  - `find_trusted_device(db, user_id, raw_cookie) -> row|None`（revoked_at IS NULL かつ last_used_at が180日以内）
  - `register_device(db, user_id, raw_cookie|None, created_via, request) -> (device_id, raw_cookie)`（印が無ければ作る。既にある印は同じ値を使う）
  - `touch_device(db, device_id, request)`（last_used_at・last_ip・last_location）
  - `revoke_device(db, user_id, device_id)` → 結び付いた組を `revoke_user_sessions(device_id=…)` で失効
  - `revoke_user_sessions(...)`（D8）→ 失効した組 id を返し、Redis に `auth:fam_revoked:{sid}` を置く
  - `describe_user_agent(ua) -> str`（D10）
- `backend/app/auth/geo.py`: `lookup(ip) -> str|None`。`GEOIP_DB_PATH`（既定 `/geoip/dbip-city-lite.mmdb`）を `maxminddb.open_database(path, maxminddb.Mode.MMAP)` で一度だけ開く。私用の IP・失敗は None。都市・地域・国を「Tokyo, Japan」の形（名前は ja があれば ja、無ければ en）。`backend/requirements.txt` に `maxminddb==3.2.0`
- 場所の元データ: Celery の月次作業 `refresh_geoip_db`（毎月3日）で `https://download.db-ip.com/free/dbip-city-lite-YYYY-MM.mmdb.gz` を共有の置き場（docker-compose の名前付き volume `geoip`、backend は読み取り専用で `/geoip`）へ落とし、書き換えは一時ファイル→rename。起動時にファイルが無ければ1回だけ取りに行く。落とせなくても認証は止めない
- `backend/app/auth/self_tokens.py`: `create_access_token` に `sid`（組の id）を足す。`issue_refresh_token` に `trusted_device_id` 引数。`rotate_refresh_token` は組の `trusted_device_id` を引き継ぎ、返り値に入れる
- `backend/app/auth/dependencies.py`: ブラックリスト確認（現 :190 付近 ①）の直後、キャッシュより前に、自社トークンなら署名を確かめて `sid` を取り、`auth:fam_revoked:{sid}` があれば 401。`sid` の無い古いトークンは最長900秒で切れるので通す
- `backend/app/routers/auth.py`
  - login（:307-366）: パスワードが正しい後、`last_login` 更新の前に判定。(1) 印がいつもの機械 → 今まで通り発行し `trusted_device_id` を付け、印 Cookie を延長。(2) D5 に当たる → 登録して発行。(3) `AUTH_DEVICE_APPROVAL=off` → 登録して発行（`bootstrap`）。(4) それ以外 → `auth_login_requests` を作り、Cookie `sa_login_pending`（path `/api/v1/auth/login-requests`・30分・HttpOnly・Secure・Strict）を付けて **202** `{status:"device_approval_required", match_number, expires_in, has_trusted_device, has_recovery_codes}`。トークンは出さない。1人1時間に依頼は5件まで（超えたら 429 `too_many_requests`）。知らせ（下）を送る。`last_login` は入れた時だけ更新
  - refresh（:369-401）: 組の機械が取り消されていたら 401。組に機械が無い（＝本便より前の組）なら D4 で登録して結び付け、印 Cookie を付ける。あれば `touch_device`
  - passkey verify（:901-995）: D3。知らない機械なら `passkey` で登録しメールで知らせる
  - password reset confirm（:524-529）・password change（:611-616）: 直書きを `revoke_user_sessions` に置き換え（動きは同じ）。change の新しい組には今の機械を結び付ける
  - logout（:165-190）: 変更なし（印は残す＝次から聞かれない）
  - 新しい口（すべて `/api/v1/auth/` 配下＝nginx の login 枠 `nginx/nginx.conf:6,145` の中）
    - `POST /auth/login-requests/poll`（待つ機械・`sa_login_pending`）: pending→`{status:"pending"}`、approved→印を登録（`device_approval`/`admin_approval`）し発行して `completed`、rejected/expired→`{status}` と Cookie 消去。画面は15秒ごと
    - `POST /auth/login-requests/recovery`（待つ機械）`{code}`: 合えば合言葉を使用済みにし、印を登録（`recovery_code`）して発行。違えば失敗回数を数え5回で依頼を `rejected`
    - `GET /auth/login-requests/pending`（いつもの機械）: 自分宛ての pending（id・機械の種類・場所・時刻・候補3つ）
    - `POST /auth/login-requests/{id}/approve` `{number}`（いつもの機械）: 正しければ approved、違えば rejected（`wrong_number`）
    - `POST /auth/login-requests/{id}/reject`（いつもの機械）: rejected ＋ `revoke_user_sessions(except_family_id=今の組)`
    - `GET /auth/devices`・`DELETE /auth/devices/{id}`（K8）
    - `GET /auth/recovery-codes/status`（残り数）・`POST /auth/recovery-codes`（10個を作って1回だけ返す。古い未使用は無効に）
  - 承認・拒否・取り消しの口は `_require_app_origin`（:215）を通す
- 管理者（K7）: `GET /admin/login-requests?status=pending`・`POST /admin/login-requests/{id}/approve`（`require_super_admin`。自分の依頼は許可できない）。`decided_by_user_id` に残し、`auth_events` に `reason='admin_approved'`
- 知らせ（K2）
  - 即時: ADR-1016 の SSE に人単位の宛先を足す（`backend/app/realtime/topics.py` に `SCOPE_USER`、`hub.py:34-46` の接続に user_id、宛先 `rt:u:{user_id}`）。種類 `auth.login_request`。中身は id だけ。ADR-1016 の決まりで、書き込む口の一覧（`NO_SIGNAL_ROUTES`）に新しい口を正しく登録する
  - メール: `backend/app/services/auth_mail.py` に `send_new_device_mail`（`_send_reset_mail` :97 と同じ SMTP）。時刻（日本時間）・機械の種類・場所の目安・「心当たりがなければ、いつもの機械でアプリを開いて『私ではない』を押し、パスワードを変えてください」。**リンクを入れない**。DB-IP の表示を1行入れる
- 記録（K9・D7）: 各口で `request.state.auth_audit = {"user_id", "reason", "is_new_device"}`。middleware が同じ行に書く。reason は `ok`・`bad_password`・`unknown_user`・`inactive`・`locked`・`rate_limited`・`device_approval_required`・`approved_device`・`approved_admin`・`approved_recovery`・`rejected`・`wrong_number`・`expired`・`recovery_code_wrong`・`passkey_new_device`・`first_login`・`bootstrap`。パスワード・合言葉・Cookie の値は書かない
- 片付け: `backend/app/tasks/maintenance.py` に、90日より古い `auth_login_requests` と、取り消し・180日未使用から90日たった機械を消す作業。`celery_app.py:101-110` に登録
- 管理用の命令 `backend/app/cli/issue_trusted_device.py`: 印の生の値を標準出力に1行だけ出す（ログには出さない）

#### A-3 frontend（金型だけを使う。`docs/CC_UI_GOVERNANCE.md`・ADR-144・ADR-067。全文字は `t()`・ja/en 同じキー）

- ログイン画面 `frontend/src/pages/login/LoginPage.tsx`: 202 のとき待ちの表示に切り替える（番号を大きく・残り時間・「予備の合言葉で入る」・「いつもの機械も合言葉も無いとき」の説明）。15秒ごとに poll。部品は既存の Stack・Button・TextFieldControl・TextLink・Modal
- いつもの機械の小窓: アプリの外枠に1つ置く部品（`frontend/src/features/auth/LoginApprovalWatcher.tsx`）。SSE の `auth.login_request`・画面を開いたとき・つなぎ直し・タブに戻ったときに `GET pending`（5秒に1回までにまとめる）。Modal に機械の種類・場所・時刻、番号ボタン3つ、「私ではない」（danger）。拒否後はパスワード変更への案内
- アカウント設定 `frontend/src/pages/account-settings/SecuritySection.tsx` の並び: 「ログインしている機械」（DataTable・「この機械」印・ログアウト ConfirmModal）と「予備の合言葉」（残り数・作り直し ConfirmModal・10個を1回だけ表示してコピー）。場所の列の下に DB-IP の表示
- 最初のログイン（D5）と合言葉0個の人: ログイン後に1回、合言葉を作る案内の Modal
- 管理画面 `frontend/src/pages/super-admin/`: 「ログインの許可待ち」一覧（DataTable・許可 ConfirmModal）
- i18n キーは `login.deviceApproval.*`・`accountSettings.devices.*`・`accountSettings.recoveryCodes.*`・`superAdmin.loginRequests.*`（ja.json :674 付近・:3193 付近の並びに合わせる）

### 段B（PR-B・deploy.yml を含む＝危険 PR・GO 要。段A の本番反映と B-0 の後）

- B-0（本番作業・PR なし）: 本番 backend で管理用の命令を実行し、出力を画面に出さずに `gh secret set SMOKE_E2E_DEVICE_TOKEN` へ流す。値は記録しない。件数（1行）だけ確かめる
- B-1 `tests/prod-check` のログイン部分（画面点検と速さの記録の両方）: `SMOKE_E2E_DEVICE_TOKEN` があればログイン前に `sa_device` Cookie を app の host・path `/api/v1/auth` に付ける。`.github/workflows/prod-ui-check.yml:104,153` の env に1行ずつ足す
- B-2 `.github/workflows/deploy.yml:371` 付近の .env 書き出しに `AUTH_DEVICE_APPROVAL='enforce'` を足し、`:318` 付近の古い行の削除にも足す。docker-compose.yml の backend env に `AUTH_DEVICE_APPROVAL=${AUTH_DEVICE_APPROVAL:-off}`（段A で入れておく）

### 段C 本番での受入（下の表）

## 5. 変更しない所

ログイン失敗の回数制限（`self_tokens.py:29-30`・`cache.py:307-308`）、smoke の道、閲覧ページのログイン、ADR-1048 の6桁、nginx の設定、パスワード再設定メールの文面、`.claude/scripts/review-gate`。

## 6. 受入条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| K1 | pytest: enforce で印なし login → 202・トークン無し・`device_approval_required`。本番: 受入の自動試験（新しいブラウザで user87 のログイン）→ 202 と画面の文言をスクリーンショット |
| K2 | pytest: 依頼で SSE 宛先 `rt:u:{id}` に1件・メール送信関数が1回（リンクなし・時刻・機械・場所）。本番: 印付きのブラウザで依頼から pending 表示までの秒数を計測（60秒以内） |
| K3 | pytest: 正しい番号で approve → poll がトークンと印を返す。本番: 受入試験で待つ側が入れる |
| K4 | pytest: reject → poll が rejected、押した組以外の組が全部 revoked、他の組の古いアクセストークンが次の要求で 401。本番: 3つ目のブラウザが 401 になる |
| K5 | pytest: 許可済みの印で login → 200。本番: K3 のブラウザで再ログインして 200 |
| K6 | pytest: 合言葉で入れる・同じ合言葉2回目は失敗・10個作られる・生の値は DB に無い。本番: user87 で作り直し→1個で入る→同じ値で失敗 |
| K7 | pytest: 管理者の口で approve → 待つ側が入れる・`decided_by_user_id` と `auth_events.reason='admin_approved'`・自分の依頼は 403・super admin 以外 403。本番: 管理者でない人の 403 を確認（実際の許可の目視は次に PO が管理画面を開いたとき） |
| K8 | pytest: 一覧に日時・場所・種類。DELETE で結び付いた組が revoked、その機械のアクセストークンが 401。本番: 受入試験で一覧の件数と取り消し後の 401 |
| K9 | pytest: 成功・失敗それぞれで auth_events に user_id・reason・is_new_device。どの列にもパスワード文字列が無い。本番: reader 鍵で受入時刻以降の user87 の行の reason 別件数 |
| 点検が止まらない | PR-B 後の prod-ui-check の手動実行が緑 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 段A〜段B の間（off）にログインした機械は無条件でいつもの機械になる | 今と同じ強さ（悪くはならない）。間を短くする（同じ日に B まで） |
| 本便より前から生きている盗まれた更新 Cookie も D4 で登録される | 今と同じ強さ。30日で終わる。K8 の一覧で見つけて取り消せる |
| 待ちの poll が nginx の login 枠（10回/分・追加5）を使う | 15秒ごと＝4回/分。一覧の取得は5秒に1回までにまとめる |
| 場所のデータが取れない | 「不明」と出すだけで認証は止めない |
| 全員がいつもの機械を失う | 予備の合言葉、最後は super admin 2人（PO・担当エンジニア）の管理画面 |
| メールが点検専用の人のアドレスへ飛ぶ | 印付きの点検は依頼を作らないので送られない。受入試験の分だけ |

戻し方: `AUTH_DEVICE_APPROVAL` を off に戻す（deploy.yml の1行を戻す PR）。表と列は残しても害は無い（追加だけ）。

## 8. 外部事例

| 出どころ | 何を | 適用 |
|---|---|---|
| Meta ヘルプ（kgi.md の一次資料） | 認識していない機械はコードか承認・ブラウザを保存・復旧コード10個・ログインした場所の一覧 | K1〜K8 の形 |
| Google アカウントヘルプ（kgi.md） | 「No, it's not me」でその機械をサインアウトさせ、パスワード変更を勧める | K4・D8 |
| Microsoft Authenticator 番号照合（2023 既定化） | 押し続けて承認させる攻撃への対策 | D1 |
| DB-IP Lite（db-ip.com・2026-11-01 確認） | CC BY 4.0・MMDB・毎月・アカウント不要・表示必須 | D9 |
| maxminddb 3.2.0（PyPI・2026-11-01 確認・Context7 は月の上限で使えず公式を直接確認） | `open_database(path, Mode.MMAP)`・`get(ip)` | D9 |

数値の成功事例は使わない（直接の根拠になる公開数値が無いため。採用理由は上の仕組みの一致）。

## 9. 維持の仕組み

- 試験: `backend/tests/test_new_device_approval.py`（K1〜K9 の pytest）を CI の必須の backend 試験に入れる
- 点検: prod-ui-check（毎朝）が印付きでログインできなくなったら Discord に出る（既存の知らせ）
- 片付け: 月次の場所データ更新・日次の古い依頼と機械の削除（Celery beat）
- 置き場: ADR-1055（決定）、本書（設計）、FEATURE-INDEX に「新しい機械の許可」を足す

## 10. 審査記録

（ここに審査役の VERDICT を追記する）
