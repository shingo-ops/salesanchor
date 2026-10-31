# 設計書: 知らない機械からのログインは、いつもの機械で許可するまで入れない

- 状態: 設計案 第5版（Opus 作成）。第1版〜第4版は審査で REVISE（下の「審査記録」）。第2版で指摘21件、第3版で要修正7件・軽微9件・判定の書き方2件、第4版で要修正4件・軽微9件、第5版で要修正3件・軽微10件を反映した
- 対応 ADR: ADR-1055（本 PR で Proposed として起案）。ADR-1013（自社ログイン）の続き。ADR-1048（管理者だけの2段階ログイン・Proposed・未実装）の「機械を覚える」「番号で許可する」部分を全員向けに広げて取り込む。ADR-1016（即時反映）に人単位の宛先を足す改訂の注記を入れる
- 合格の基準: docs/handoff/auth-new-device-approval/kgi.md（K1〜K9・PO 承認済 2026-11-01）
- 事実の出どころ: docs/handoff/auth-new-device-approval/recon.md（基準 7e9155163）。本書で `recon:B` のように節を指す。第2版で足した事実は本書に行番号で書く（基準 7e9155163・作業枝 13ea58557 で読んだ）
- 本番の数: /tmp/CC報告ファイル/new-device-prod-counts-20261101.txt（2026-11-01 00:22 JST・reader 鍵）

## 1. 目的と利用者に見える変化

パスワードが漏れても、知らない機械からは入れないようにする（不正ログイン対策）。

| 場面 | 変更前 | 変更後 |
|---|---|---|
| 初めての機械でパスワードを入れる | そのまま入れる | 「いつもの機械で許可してください」と2けたの番号が出て待つ（K1） |
| いつもの機械 | 何も起きない | 1分以内に「新しい機械からログインしようとしています」の小窓が出る。機械の種類・場所の目安・時刻と、番号3つ・「私ではない」が並ぶ。アプリを閉じていても、通知を許可した機械には通知が出る。メールも届く（リンクなし）（K2） |
| 正しい番号を押す | — | 待っていた機械が入れて、次から聞かれない（K3・K5）。ほかのいつもの機械の小窓も閉じる |
| 「私ではない」を押す | — | 待っていた機械は入れない。押した機械以外は全部ログアウト。パスワード変更を勧める（K4） |
| いつもの機械が無い | — | 予備の合言葉（10個・1回ずつ）で入る（K6）。それも無い人は、しんごさんか担当エンジニアが本人確認のうえ管理画面で許可する（K7） |
| アカウント設定 | パスキーの一覧だけ | 「ログインしている機械」の一覧（日時・場所の目安・機械の種類）。その場でログアウトできる（K8） |
| 記録 | 誰のログインか・理由が残らない（recon:E） | 誰が・成否・理由・初めての機械か が残る。パスワードは残らない（K9） |

## 2. 対象と対象外

- 対象: アプリのログイン（パスワード `backend/app/routers/auth.py:307-366`・パスキー `:901-995`・更新 `:369-401`）。全利用者（super admin・点検専用の人を含む）
- 対象外（理由）
  - 閲覧ページの別ログイン（`backend/app/routers/viewer.py:153`。別の利用者表・別の道。後の便で同じ部品を使う）
  - smoke の固定トークンの道（`backend/app/auth/dependencies.py:147-178`。ログインを通らず、super admin を返さない構造ガードあり）
  - ADR-1048 の6桁コード（認証アプリ）。ADR-1048 に残す
  - 機械の名前付け（後回し・PO 11/1）

## 3. 決めたこと（Opus 判断・大手のやり方に沿う）

| # | 論点 | 決定 | 根拠 |
|---|---|---|---|
| D1 | 許可の形 | 待つ側に2けたの番号、いつもの機械に候補3つ。正しい番号＝許可。違う番号＝その依頼だけ拒否（全ログアウトはしない） | ADR-1048 の審査済み方式。Microsoft Authenticator の番号照合（押し続け攻撃対策）。kgi.md の大手資料 |
| D2 | 機械の印 | Cookie `sa_device`（32バイト乱数・HttpOnly・Secure・SameSite=Strict・path `/api/v1/auth`・180日・ログインのたび延長）。DB は SHA-256 のみ。1つの印を複数の人が使える（`UNIQUE(user_id, token_hash)`） | ADR-1048 の形。login の口にも届くよう path を `/api/v1/auth` に広げる（更新 Cookie と同じ path `auth.py:220-230`）。32バイト乱数なので hash は SHA-256 で足りる |
| D3 | パスキーでのログイン | 知らない機械でも入れて、その機械をいつもの機械に加える。メールで知らせる | パスキー自体が機械に結び付く2つ目の確認（Google はパスキーで2段階確認を省く）。K1 は「パスワードが正しくても」 |
| D4 | 仕組みを入れた日にログイン中の機械 | 更新のとき、組に機械が結び付いておらず、かつ組の作成時刻 `family_created_at` が締切 `AUTH_DEVICE_BOOTSTRAP_CUTOFF` より前なら、その機械をいつもの機械として登録する（`created_via='bootstrap'`）。締切は PR-B に固定値（UTC・PR-B の本番反映を終える予定の時刻＋6時間）で書く。締切より後に作られた組で機械が無いものは、enforce では 401（off では今まで通り）。境界の試験を足す（締切の1秒前は登録・ちょうどは 401） | kgi.md「最初から守ること」。組は最長30日（`self_tokens.py:25`）なので、この扱いは締切から30日で自然に終わる。締切を固定値にするのは、反映が遅れても「後から作られた組」を無条件で通さないため |
| D5 | 一度もログインしていない人の最初のログイン | `users.last_login IS NULL` かつ 機械の登録が0件 のときだけ、その機械を最初のいつもの機械にする（`first_login`）。直後に予備の合言葉を作る小窓を出す。メールで知らせる | Meta は登録時の機械を信頼する。本番で該当5人（counts ファイル）。危険は §7 |
| D6 | 依頼の保存先 | DB の表 `public.auth_login_requests`（Redis にしない）。有効30分 | K7 の管理者許可と記録に要る（5分の Redis では足りない） |
| D7 | 記録（K9） | 既存の `public.auth_events` に列 `user_id`・`reason`・`is_new_device` を足す。口の中で `request.state.auth_audit = {...}` に入れ、既存の middleware（`backend/app/middleware/audit.py:236-254`）が同じ行に書く。202（許可待ち）は `event_type='auth_pending'` で書く（今は 2xx を全部 `auth_success` にしている `audit.py:226-229`）。middleware から口の `request.state` が読めること（starlette 1.3.1 の `request.state` は `scope["state"]` を共有する）を pytest で示す | 記録の置き場を1つに保つ（新しい表を作らない）。202 を成功と数えないため |
| D8 | 全部ログアウト | 共通関数 `revoke_user_sessions(db, user_id, except_family_id=None, device_id=None)` を1つ作り、既存の直書き2か所（`auth.py:524-529`・`:611-616`）もこれに置き換える。アクセストークンに組の id `sid` を入れ、失効した組の id を Redis `auth:fam_revoked:{sid}`（TTL 900秒）に置いて、毎回の確かめで拒否する。Redis が読めないときは、既存のブラックリスト（`backend/app/cache.py:403-418`・読めなければ通す）と同じく通す（危険は §7） | recon:C「専用の関数が無い」「アクセストークンは最長900秒生きる」 |
| D9 | 場所の目安 | DB-IP IP to City Lite（CC BY 4.0・MMDB・毎月）を `maxminddb`（Apache-2.0・3.2.0）で読む。ファイルが無い・読めないときは「不明」。場所を出す画面とメールに「IP Geolocation by DB-IP」のリンクを付ける。IP は判定に使わない | 前段に中継なし＝X-Real-IP が本当の IP（DNS 確認・recon:D）。MaxMind はアカウントが要る |
| D10 | 機械の種類 | User-Agent から自前の小さな関数で「iPhone・Safari」「Mac・Chrome」等を作る（依存を足さない） | 依存を増やさない |
| D11 | 切り替え | 環境変数 `AUTH_DEVICE_APPROVAL=off\|enforce`（既定 off）。**off はログインの止め方が今と同じ**（機械の登録も印の発行もしない。D8 の `sid` と失効の確かめだけは off でも効く）。enforce は PR-B で deploy.yml に入れる。off の間も表は作られ、管理用の命令での印の発行（D12）はできる | D4 の締切と合わせ、off の間に作られた組を「締切前の組」として一度だけ登録するため（審査 軽微1） |
| D12 | 点検専用の人（本番 user87） | 管理用の命令 `python -m app.cli.issue_trusted_device --user-id <id> --label prod-ui-check` で印を1つ発行し、表示せずに GitHub の秘密 `SMOKE_E2E_DEVICE_TOKEN` へ直接流す。点検はログイン前に `sa_device` を付ける | 例外を作らず全員に効かせる |
| D13 | アプリを閉じているときの知らせ | ホーム画面のアプリへの通知（web push）を足す（段W）。iPhone はホーム画面に追加したアプリで iOS 16.4 以降・本人が「通知を許可」を押したときだけ（WebKit 公式・kgi.md:39）。許可していない機械は、画面（SSE）とメールで知らせる | K2「いつものスマホかパソコンに1分以内」を、アプリを閉じていても満たすため（審査で指摘・kgi.md:39 の通知手段） |
| D14 | 予備の合言葉の形 | 1個 = 見出し4文字＋本体10文字（Crockford base32・本体は50ビット）を `ABCD-EFGHJ-KMNPQ` の形で見せる。DB は見出し（その人の中で一意）と本体の argon2（既存 `hash_password`）を置く。照合は見出しで1件に絞ってから argon2 を1回だけ。間違いは依頼の `failed_code_attempts`（5回で依頼を `rejected`）と、口座の失敗回数 `_count_login_failure`（`auth.py:283-304`）の両方に数える | 審査 要修正3。総当たりと照合の重さを抑える。合言葉もパスワードと同じ「推測される鍵」として口座の停止に数える |
| D15 | 同時の操作と本人の確かめ | 決める操作は1行の条件付き更新で1回だけ通す。approve/reject は `UPDATE public.auth_login_requests SET status=... WHERE id=:id AND user_id=:current_user_id AND status='pending' AND expires_at>now() RETURNING id`（**本人の依頼だけ**）。1行も返らなければ、id が無い・他人の依頼・決まり済みのどれでも 404 `not_found`（他人の依頼の有無を漏らさない）。poll の発行は `UPDATE ... SET status='completed' WHERE id=:id AND status='approved' RETURNING` が1行返したときだけ（poll は `sa_login_pending` の hash で依頼を引くので本人の確かめはこの Cookie）。`GET pending` は `WHERE user_id=:current_user_id AND status='pending' AND expires_at>now()`。承認・拒否する側は D16 の `sid` の組に取り消されていない `trusted_device_id` があることを求める（無ければ 403 `device_not_trusted`）。違う番号は 200 `{status:"rejected", reason:"wrong_number"}` | 第1版 要修正4・第2版 要修正1。二重発行・他人の依頼の操作・取り消された機械からの承認を防ぐ |
| D16 | 承認する側の組の取り方 | アクセストークンの `sid`（D8）を唯一の出どころにする。`backend/app/auth/dependencies.py` に本体の関数 `resolve_current_session(request, db, user) -> CurrentSession(user, sid, trusted_device_id, family_created_at)` と、それを包む依存 `get_current_session(request, cred, db: AsyncSession = Depends(get_db))` を足す（`get_current_user` の後に自社トークンの claims を `decode_access_token` で読み直し、`sid` で `auth_refresh_tokens` の組の `trusted_device_id`（取り消されていない最新の行）を引く）。`sid` が無いトークン（本便より前の発行）は 403 `session_upgrade_required`（画面は更新を1回して再試行する）。承認・拒否・機械の一覧の「この機械」・機械の取り消し・購読の登録・**enforce のときのパスワード変更**（A-2）が使う。承認・拒否などの口は引数に `Depends(get_current_session)` を書く。パスワード変更は引数を `get_current_user` のまま変えず、enforce のときだけ本体の中で `resolve_current_session` を呼ぶ（引数に書くと off でも効くため） | 第2版 要修正2。「押した機械以外の全部のログアウト」で残す組を一義にする |

## 4. 変更内容（段ごと）

### 段A（PR-A・migrations を含む＝危険 PR・GO 要）

#### A-1 migration（1本・追加のみ・冪等・全列 COMMENT・public に置き `public.users(id)` にぶら下げる。置き場と登録は recon:J の決まり `scripts/run_all_migrations.sh`・`migration-guard.yml:119`）

- `public.user_trusted_devices`: id BIGSERIAL PK / user_id BIGINT NOT NULL FK CASCADE / token_hash BYTEA NOT NULL / label VARCHAR(100) / user_agent VARCHAR(500) / created_via VARCHAR(20) NOT NULL CHECK IN ('bootstrap','first_login','passkey','device_approval','recovery_code','admin_approval','cli') / created_ip VARCHAR(45) / created_location VARCHAR(200) / created_at TIMESTAMPTZ NOT NULL DEFAULT now() / last_used_at TIMESTAMPTZ / last_ip VARCHAR(45) / last_location VARCHAR(200) / revoked_at TIMESTAMPTZ。UNIQUE(user_id, token_hash)。索引 user_id
- `public.auth_login_requests`: id UUID PK / user_id FK CASCADE / status VARCHAR(20) CHECK IN ('pending','approved','rejected','expired','completed') / match_number CHAR(2) / candidates VARCHAR(8)（例 "47,12,85"） / pending_token_hash BYTEA UNIQUE / device_token_hash BYTEA（待つ機械に既にある印の hash・無ければ NULL） / label VARCHAR(100) / user_agent VARCHAR(500) / ip VARCHAR(45) / location VARCHAR(200) / created_at TIMESTAMPTZ NOT NULL DEFAULT now() / expires_at TIMESTAMPTZ NOT NULL / decided_at TIMESTAMPTZ / decided_via VARCHAR(20) CHECK IN ('device','admin','recovery_code') / decided_by_user_id BIGINT NULL FK SET NULL / decided_device_id BIGINT NULL FK SET NULL / decided_note VARCHAR(200)（管理者の許可のときだけ必須・本人確認の方法） / reject_reason VARCHAR(30) / failed_code_attempts SMALLINT DEFAULT 0。索引 (user_id, created_at DESC)・(status, expires_at)
- `public.user_recovery_codes`: id / user_id FK CASCADE / code_id CHAR(4)（見出し） / code_hash TEXT（本体の argon2） / created_at TIMESTAMPTZ NOT NULL DEFAULT now() / used_at TIMESTAMPTZ / revoked_at TIMESTAMPTZ（作り直しで古い未使用に入れる。行は消さない） / used_request_id UUID NULL。制約ではなく部分索引 `CREATE UNIQUE INDEX IF NOT EXISTS ... ON public.user_recovery_codes (user_id, code_id) WHERE used_at IS NULL AND revoked_at IS NULL`（PostgreSQL の UNIQUE 制約は WHERE を付けられないため）
- `public.auth_refresh_tokens` に `trusted_device_id BIGINT NULL REFERENCES public.user_trusted_devices(id) ON DELETE SET NULL`＋索引
- `public.auth_events` に `user_id BIGINT NULL`・`reason VARCHAR(50) NULL`・`is_new_device BOOLEAN NULL`＋索引 (user_id, created_at DESC)
- RLS と権限（第4版 審査 軽微）: 新しい表（段A の3つ・段W の1つ）には RLS を付けない。ADR-1018 Decision 6 が認証トークン3表に RLS を付けないと決めた理由と同じで、ログイン前・会社が決まる前に、印や依頼の hash の一致で1行を引くため（会社別の RLS を付けるとログインが止まる）。代わりの守りも同じで、生の値は保存せず hash だけを置き、本人の行は `user_id` で絞る。ADR-1055 にこの扱いを書く。権限は前例 `migrations/20261013_160000_add_self_hosted_auth_tables.sql` と同じ形で `salesanchor_app` に表の `SELECT, INSERT, UPDATE, DELETE` と sequence の `USAGE, SELECT` を明示する（作業の最初に前例の GRANT の行を読み、同じ書き方にそろえる）
- 守りの検査に新しい表を登録する
  - `.github/workflows/migration-guard.yml:224` の `PUBLIC_TABLES` に `user_trusted_devices auth_login_requests user_recovery_codes` を足す（段W で `user_push_subscriptions`）
- クラウドの相談係 AI に見せる列の分類（ai_cloud）を、同じ PR で3か所そろえて直す（審査 要修正7）
  - 決まり（実物）: 列名が `_DENY_RE`（`backend/tests/ops/test_ai_cloud_views.py:36`・`migrations/20261024_100000_create_ai_cloud_meta.sql` の deny と同じ）に当たる列は自動で外れるので行を足さない（`token_hash`・`pending_token_hash`・`device_token_hash`・`code_hash`）。`_PASS_TYPES`（:43-46・int・bool・timestamptz・uuid など）の列は、列名が `_NAME_RE`（:37-40・note・name・text など）に当たらなければ行が要らない。それ以外の列は行が要る（新しい列で `_NAME_RE` に当たるのは `decided_note` だけで、これは文字の型なのでどちらにしても行が要る）。1列1行（SQL は表ごとに ARRAY でまとめ、unnest で1列1行になる `20261024_100300:13-14`）
  - 足す行（全部 `mask`・理由は空。allow は使わない）
    | 表 | 列 |
    |---|---|
    | user_trusted_devices | label・user_agent・created_via・created_ip・created_location・last_ip・last_location（7） |
    | auth_login_requests | status・match_number・candidates・label・user_agent・ip・location・decided_via・decided_note・reject_reason（10） |
    | user_recovery_codes | code_id（1） |
    | auth_events | reason（1） |
  - 合計19行。正本 `migrations/20261024_100300_create_ai_cloud_views.sql` の INSERT（:13〜）に表ごとの1行で足し、冒頭の説明（:3）の「1035 行」を「1054 行」に直す
  - 元の表 `docs/handoff/cloud-case-ai/stage1-column-class.tsv`（`auth_events` は :66-70）に同じ19行を足す（列の型の欄は character varying または character）
  - `scripts/migration-guard/reference-allowlist.tsv:7` の sha256 を直した後の値に更新する
  - 試験 `backend/tests/ops/test_ai_cloud_views.py:477` の `1035` を `1054` にする（T10 `:519` が通ること）。`docs/handoff/cloud-case-ai/stage1-column-class.tsv` は1036行→1055行（見出し1行＋1054行）
  - 本便の migration は 20261024_100300 より後に流れ、`scripts/run_all_migrations.sh:233-260` の EXIT trap で見え方が作り直される
- 試験の表定義を4か所そろえる（審査 要修正9）
  - `backend/tests/conftest.py:320-321`（public の名前を外す置き換え）に新しい表3つを足す
  - `backend/tests/conftest.py:1341-1343` の SQLite 版に新しい表3つと `trusted_device_id` 列を足す
  - `backend/tests/rls_bootstrap.py` は**直さない**。理由: この起動の一覧（:14-34）には users・auth_refresh_tokens・auth_events を作る migration が1つも無く、新しい表だけを足すと FK の先が無い。新しい列の分類の漏れは、T10 ではなく `test_ai_cloud_views.py` に足す試験（本便の migration を流した PG で、上の19列に `column_class` の行があることを名前で確かめる）で守る
  - `.github/workflows/migration-test.yml:1338-1352` の auth_events の最小定義に新しい列を足す

#### A-2 backend

- 新しい部品 `backend/app/auth/devices.py`（生 SQL。`self_tokens.py:3-5` と同じ理由で ORM を作らない）
  - `find_trusted_device(db, user_id, raw_cookie) -> row|None`（revoked_at IS NULL かつ last_used_at が180日以内）
  - `register_device(db, user_id, raw_cookie|None, created_via, request) -> (device_id, raw_cookie)`（印が無ければ作る。既にある印は同じ値を使う）
  - `touch_device(db, device_id, request)`（last_used_at・last_ip・last_location）
  - `revoke_device(db, user_id, device_id)` → 結び付いた組を `revoke_user_sessions(device_id=…)` で失効
  - `revoke_user_sessions(...)`（D8）→ 失効した組 id を返し、Redis に `auth:fam_revoked:{sid}` を置く
  - `describe_user_agent(ua) -> str`（D10）
- `backend/app/auth/recovery_codes.py`（D14）: `generate(db, user_id) -> list[str]`・`verify(db, user_id, code) -> id|None`・`remaining(db, user_id)`
- `backend/app/auth/geo.py`: `lookup(ip) -> str|None`。`GEOIP_DB_PATH`（既定 `/geoip/dbip-city-lite.mmdb`）を `maxminddb.open_database(path, maxminddb.Mode.MMAP)` で開き、ファイルの更新時刻が変わったら開き直す。私用の IP・失敗は None。都市・地域・国を「Tokyo, Japan」の形（名前は ja があれば ja、無ければ en）。`backend/requirements.txt` に `maxminddb==3.2.0`
- 場所の元データ（審査 要修正12）: Celery の月次作業 `refresh_geoip_db`（毎月3日）を **celery-worker で動かす**。`https://download.db-ip.com/free/dbip-city-lite-YYYY-MM.mmdb.gz` を名前付き volume `geoip` に落とし、一時ファイル→rename で入れ替える。`docker-compose.yml` で volume `geoip` を celery-worker（:219）には書き込みで、backend には読み取り専用 `:ro` で `/geoip` に付ける。celery-beat（:314）には付けない。起動時にファイルが無ければ worker が1回だけ取りに行く。落とせなくても認証は止めない
- `backend/app/auth/self_tokens.py`（変更前→変更後。呼び出し元は `auth.py:357,381,630,988` と `self_tokens.py:240` の5か所で全部）
  - `create_access_token(user_id, email, amr)` → `create_access_token(user_id, email, amr, sid: str | None = None)`。`sid` があれば claims に入れる（既存の試験 `test_viewer_api.py:183` 等は引数を変えずに通る）
  - `issue_refresh_token(db, user_id, user_agent, family_id=None, family_created_at=None) -> tuple[str, datetime]` → 引数に `trusted_device_id: int | None = None` を足し、INSERT の列に入れる。戻り値の形は変えない。新しい組を作る呼び出し元（`auth.py:357,630,988`）は、先に `family_id = str(uuid.uuid4())` を作って渡し、その値を `sid` に使う
  - `rotate_refresh_token(...) -> tuple[int, str, datetime] | None` → `RotatedRefresh(user_id, raw, expires_at, family_id, family_created_at, trusted_device_id) | None`（NamedTuple）。SELECT と RETURNING に `trusted_device_id` を足し、新しい行へ引き継ぐ。呼び出し元は `auth.py:381` だけ
- `backend/app/routers/auth.py:233` の `_issue_session_tokens(response, raw, expires_at, user_id, email, amr)` → 末尾に `sid: str` を足し（必須）、`create_access_token(..., sid=sid)` に渡す。呼び出し元 `:361,:392,:634,:990` は全部 `sid` を渡す
- `backend/app/auth/dependencies.py`: ブラックリスト確認（①）の直後、キャッシュ（②）より前に、自社トークンなら署名を確かめて `sid` を取り、`auth:fam_revoked:{sid}` があれば 401。`sid` の無い古いトークンは最長900秒で切れるので通す
- `backend/app/routers/auth.py`
  - login（:307-366）: パスワードが正しい後、`last_login` 更新の前に判定。(1) `AUTH_DEVICE_APPROVAL=off` → 今まで通り（機械の登録はしない。`sid` だけは入る）。(2) 印がいつもの機械 → 発行し `trusted_device_id` を付け、印 Cookie を延長。(3) D5 に当たる → 登録して発行。(4) それ以外 → `auth_login_requests` を作り、Cookie `sa_login_pending`（path `/api/v1/auth/login-requests`・30分・HttpOnly・Secure・Strict）を付けて、**`JSONResponse(status_code=202)` を作り、その応答オブジェクト自身に `set_cookie` する**（FastAPI は引数の `response` に付けた Cookie を、JSONResponse を直接返すと捨てる。既存の例は refresh の失敗 `auth.py:382-386` が返す応答に `_clear_refresh_cookie` を付けている）。中身は `{status:"device_approval_required", match_number, expires_in, has_trusted_device, has_recovery_codes}` を返す（`response_model=SelfTokenResponse` は 200 のまま残し、OpenAPI には `responses={202: ...}` で書く）。トークンは出さない。1人1時間に依頼は5件まで（超えたら 429 `too_many_requests`）。知らせ（下）を送る。`last_login` は入れた時だけ更新
  - refresh（:369-401）: 組の機械が取り消されていたら 401。組に機械が無いときは D4（締切前の組なら機械を登録して組に結び付け、**返す応答に `sa_device` の Cookie を付ける**）。あれば `touch_device`
  - passkey verify（:901-995）: enforce のときだけ D3。知らない機械なら `passkey` で登録しメールで知らせる
  - password reset confirm（:524-529）: 直書きを `revoke_user_sessions` に置き換え（動きは同じ。新しい組は出さない）
  - password change（:553-641・取り消しは :611-616）: 直書きを `revoke_user_sessions` に置き換え（動きは同じ）。新しい組の出し方（:629-641 の `is_issuance_enabled()` のとき）を切り替えで分ける
    - off: 今と同じ。新しい組は `trusted_device_id` なしで出し、`sid` だけ入れる。`sid` の無い古いトークンでも通す。機械の登録はしない
    - enforce: D16 の `resolve_current_session` を本体の中で呼んで今の組を引き、その `trusted_device_id` を新しい組に引き継ぐ。`sid` の無いトークンは 403 `session_upgrade_required`（パスワードは変えない＝取り消しより前に確かめる）。今の組に機械が無い場合は、`CurrentSession.family_created_at` が締切より前なら機械を登録して結び付け、返す応答に `sa_device` の Cookie を付ける（refresh で登録したときと同じ付け方）。締切後は、取り消しより前に 403 `device_not_trusted` を返す（パスワードも組も変えない）
    - 試験: off と enforce の両方で、変更後の組の `trusted_device_id` と、403 のときにパスワードが変わっていないことを確かめる
  - logout（:165-190）: 変更なし（印は残す＝次から聞かれない）
  - 新しい口（一覧の取得 `GET /api/v1/login-approvals/pending` だけは `/api/v1/auth/` の外。それ以外は `/api/v1/auth/` 配下＝nginx の login 枠 `nginx/nginx.conf:6,145` の中）
    - `POST /auth/login-requests/poll`（待つ機械・`sa_login_pending`）: pending→`{status:"pending"}`、approved→D15 の条件付き更新で `completed` にできたときだけ、印を登録（`device_approval`/`admin_approval`）し発行。rejected/expired→`{status}` と Cookie 消去。画面は15秒ごと
    - `POST /auth/login-requests/recovery`（待つ機械）`{code}`: D14。合えば合言葉を使用済みにし、印を登録（`recovery_code`）して発行
    - 自分宛ての pending の一覧は、回数の枠の都合で `/api/v1/auth/` の外に置く（下の「回数の枠」）
    - `POST /auth/login-requests/{request_id}/approve` `{number}`（いつもの機械・D16）: D15。正しければ 200 approved、違えば 200 rejected（`wrong_number`）
    - `POST /auth/login-requests/{request_id}/reject`（いつもの機械・D16）: D15。rejected ＋ `revoke_user_sessions(except_family_id=今の組)`
    - `GET /auth/devices`・`DELETE /auth/devices/{device_id}`（K8・本人の機械だけ。他人の id は 404）
    - `GET /auth/recovery-codes/status`（残り数）・`POST /auth/recovery-codes`（10個を作って1回だけ返す。古い未使用は無効に）
  - 状態を変える口（approve・reject・recovery・poll・devices DELETE・recovery-codes POST）は `_require_app_origin`（:215）を通す
  - 閲覧者の隔離の試験（第4版 審査 要修正1）: poll と recovery はトークンを見ずに `sa_login_pending` の Cookie だけで動くので、閲覧者のトークンでも 401 にならない（試験では Origin が無く 403）。`backend/tests/test_viewer_isolation.py` の `_PUBLIC_NO_AUTH_ROUTES` に `("POST", "/api/v1/auth/login-requests/poll")` と `("POST", "/api/v1/auth/login-requests/recovery")` を理由のコメント付きで足す。理由は、既にある `("POST", "/api/v1/auth/login")` と同じく、ログイン前の口でトークンから得られる権限が無いこと。ほかの新しい口は全部 `get_current_user`・`get_current_session`・`require_super_admin` のどれかを通すので 401 になる（その試験はそのまま通る）
  - 許可で入ったときの `last_login`（第4版 審査 軽微）: poll と recovery で発行したときも、login（`auth.py:345`）と同じく `failed_login_count = 0, locked_until = NULL, last_login = :now` を更新する。書き方も login と同じで、users を書く直前だけその人の会社の文脈を張り、書いたら戻す（ADR-1018 便C）
  - 回数の枠（第3版 審査 要修正C）: nginx は `/api/v1/auth/` を送信元ごとに 10回/分・ためられる5回（`nginx/nginx.conf:6,144-146`）で絞り、本番の自動点検はこの枠に合わせて1つの試験で refresh・login を最大3回と決めている（`tests/prod-check/fixtures.ts:20-21`・`tests/prod-check/login.ts:13-15`）。いつもの機械の小窓は画面を開くたび・つなぎ直し・タブに戻るたびに一覧を読むので、この枠の中に置くと点検と普段の画面の両方で 429 が出うる
    - そこで一覧は新しいファイル `backend/app/routers/login_approvals.py` の `GET /api/v1/login-approvals/pending`（`main.py` で `prefix="/api/v1"`）に置く。nginx では `location /api/`（`nginx/nginx.conf:219-221`・30回/秒・ためられる50回）に入り、login の枠を使わない。nginx の設定は変えない
    - 中身は第3版と同じ（`get_current_user`・`WHERE user_id=:current_user_id AND status='pending' AND expires_at>now()`・id・機械の種類・場所・時刻・候補3つ）。GET なので `NO_SIGNAL_ROUTES` には入れない
    - login の枠を使う口は、ログイン画面の login・poll（15秒ごと＝4回/分）・合言葉と、いつもの機械で人が押す approve・reject・機械の一覧と取り消し・合言葉の作り直しだけになる。自動点検は小窓を開いても login の枠を使わない
- 管理者（K7・審査 要修正5）: 新しいファイル `backend/app/routers/super_admin_login_requests.py`。既存の決まり（`backend/app/routers/super_admin_tenants.py:38` の `@router.delete("/super-admin/tenants/{tenant_id}")`、`backend/app/main.py:654` の `prefix="/api/v1", tags=["super-admin"]`）に合わせ、`GET /super-admin/login-requests?status=pending`・`POST /super-admin/login-requests/{request_id}/approve` `{note}`。`require_super_admin`（`dependencies.py:516`）と `_require_app_origin` を通す（`_require_app_origin` は `backend/app/auth/origin.py` に移して auth.py と両方から読む）。自分の依頼は 403。`note`（本人確認の方法・必須・200字まで）を `decided_note` に、許可した人を `decided_by_user_id` に残す。管理者の口は `/api/v1/auth/` の外なので、認証の記録（`audit.py:36` の `_AUTH_PATHS`）には入らない。管理者の操作は既存の `_record_auth_audit`（`auth.py:251-276`。書き先は会社別の `audit_logs`・`record_id` は整数の列）に残す。引数は `tenant_id`＝依頼した人の会社（記録はその人の会社の履歴に入る）、`user_id`＝許可した super admin、`action="update"`、`table_name="auth_login_requests"`、`record_id=None`（依頼の id は UUID で整数の列に入らないため）、`new_data={"event":"login_request_approved_admin", "request_id": "<UUID の文字列>", "target_user_id": <依頼した人の id>}`。note の中身は書かない（第4版 審査 要修正2）。`auth_events` の `reason='approved_admin'` は、待つ機械の poll（`/api/v1/auth/` の下）が発行したときに書く（poll は `decided_via` を見て `approved_device`・`approved_admin` を入れ分ける）。記録の仕組み（`_AUTH_PATHS`）は広げない。本人確認の手順は §9
- 知らせ（K2）
  - 即時（ADR-1016 の SSE に人単位の宛先を足す・審査 要修正6）
    - `backend/app/realtime/topics.py`: `SCOPE_USER = "user"`、話題 `TOPIC_AUTH_LOGIN_REQUEST = "auth.login_request"`、人宛ての話題の表 `USER_TOPICS: dict[str,str] = {TOPIC_AUTH_LOGIN_REQUEST: SCOPE_USER}`
    - `backend/app/realtime/publisher.py:19-22` に `CHANNEL_USER_PREFIX = "rt:u:"` と `user_channel(user_id) -> str`（`tenant_channel` :28 と同じ形）を足し、人宛ての送り口 `publish_user_change(user_id, topic, origin=None)` を足す（`publish_change` :64 と同じ作りで、宛先だけ `user_channel`。中身は `_payload`（:42）のまま topic と origin だけ・依頼の id は入れない）。`_channel_for`（:32-40）は変えない（人宛ては scope で選ばず、この送り口だけが使う）。`CHANNEL_PATTERN = "rt:*"`（:22）のままで `rt:u:` も受け取れる
    - `backend/app/realtime/hub.py:27-31` の `Connection`（`@dataclass(eq=False)`・`queue` に既定値あり）に `user_id: int | None = None` を `queue` より前に足し、`_targets`（:34-46）で `rt:u:` は `conn.user_id` が同じときだけ真（None なら偽）。既存の試験 `backend/tests/test_realtime_middleware.py:164` の `_conn` はそのまま通る
    - `backend/app/routers/realtime_events.py:80` で `Connection(tenant_id=tenant_id, is_super_admin=is_super_admin, user_id=user_id)` を渡す（`user_id` は :73 の変数）
    - 送る時: 依頼を作った時・決まった時（approved/rejected/expired）。決まった時にも送るので、ほかのいつもの機械の小窓も閉じる（審査 軽微5）
    - `USER_TOPICS` を `backend/tests/test_realtime_topics.py:129-133` の一致の確かめと `frontend` の topics.ts に入れる
    - `NO_SIGNAL_ROUTES`（`topics.py:86〜`）には**書き込みの口だけ**を並べる（`backend/tests/test_realtime_topics.py:19` の `_write_routes` は POST/PUT/PATCH/DELETE だけを集め、`:108` が表にある GET を「存在しない道」として落とすため）。理由は「人宛ての合図は口の中で直接送る（書き込みの口の自動合図にしない）」。並べる道は次の全部（段W の3つは PR-W で足す）
      - `("POST", "/api/v1/auth/login-requests/poll")`・`("POST", "/api/v1/auth/login-requests/recovery")`・`("POST", "/api/v1/auth/login-requests/{request_id}/approve")`・`("POST", "/api/v1/auth/login-requests/{request_id}/reject")`
      - `("DELETE", "/api/v1/auth/devices/{device_id}")`・`("POST", "/api/v1/auth/recovery-codes")`
      - `("POST", "/api/v1/super-admin/login-requests/{request_id}/approve")`
      - 段W: `("POST", "/api/v1/auth/push-subscriptions")`・`("DELETE", "/api/v1/auth/push-subscriptions/{subscription_id}")`
      - パスの引数名は上の名前で作る（表とルートの文字列を一致させるため）
    - ADR-1016 に「人単位の宛先 `rt:u:` を足した（ADR-1055）」の改訂の注記を足す
  - メール: `backend/app/services/auth_mail.py` に `send_new_device_mail`（`_send_reset_mail` :97 と同じ SMTP）。時刻（日本時間）・機械の種類・場所の目安・「心当たりがなければ、いつもの機械でアプリを開いて『私ではない』を押し、パスワードを変えてください」。**リンクを入れない**。DB-IP の表示を1行入れる。送信は BackgroundTasks（失敗しても依頼は作る）
- 記録の試験（K9）: 試験の SQLite には `auth_events` が無く、記録は `AsyncSessionLocal` で書いて失敗を飲み込む（`backend/app/middleware/audit.py:32,233`）。そこで pytest では `app.middleware.audit.AsyncSessionLocal` を、受けた SQL と値を覚えるだけの偽物に差し替え、INSERT の値に `user_id`・`reason`・`is_new_device` が入ることを確かめる。列があることは migration-test（実の PostgreSQL）で確かめ、本番は reader 鍵で確かめる
- 記録（K9・D7）: 各口で `request.state.auth_audit = {"user_id", "reason", "is_new_device", "event_type"(任意)}`。`backend/app/middleware/audit.py` の認証の記録（:225-254）で、`request.state.auth_audit` があればその値を INSERT に足し、`event_type` があればそれを使う（202 は `auth_pending`）。reason は `ok`・`bad_password`・`unknown_user`・`inactive`・`locked`・`rate_limited`・`device_approval_required`・`approved_device`・`approved_admin`・`approved_recovery`・`rejected`・`wrong_number`・`expired`・`recovery_code_wrong`・`passkey_new_device`・`first_login`・`bootstrap`。パスワード・合言葉・Cookie の値は書かない
- 片付け: `backend/app/tasks/maintenance.py` に、90日より古い `auth_login_requests` と、取り消し・180日未使用から90日たった機械を消す作業。期限切れの pending を `expired` にする作業（5分ごと）。`celery_app.py:101-110` に登録
- 管理用の命令 `backend/app/cli/issue_trusted_device.py`（`backend/app/cli/` はまだ無いので `backend/app/cli/__init__.py` も新しく作る）: 印の生の値を標準出力に1行だけ出す（ログには出さない）

#### A-3 frontend（金型だけを使う。`docs/CC_UI_GOVERNANCE.md`・ADR-144・ADR-067。全文字は `t()`・ja/en 同じキー）

- `frontend/src/lib/auth/selfAuth.ts`（審査 要修正10）: 今の `postAuth`（:88）と `selfLogin`（:103）は 202 も成功として受け、トークンの無い応答を `adoptAccessToken` に渡してしまう。`selfLogin` の戻り値を `{kind:"ok"} | {kind:"approval_required", matchNumber, expiresIn, hasTrustedDevice, hasRecoveryCodes}` にし、202 を見分ける。呼び出し元は `frontend/src/contexts/AuthContext.tsx:128` の `signIn` だけ（`grep -rn "selfLogin(" frontend/src` で確かめる。試験の `frontend/src/lib/auth/selfAuth.test.ts` にも当たるので、試験も新しい戻り値に直す。それ以外に当たれば止めて報告）。`signIn` を偽物にする試験 `frontend/src/components/AllLegacyButtonOperationMigration.test.tsx`（:12 で `vi.fn()`・:42-50 で中身なしに解決させて `/quotes` へ移るのを確かめる）は上の grep に当たらないので名前で直す対象に入れ、偽物が `{kind:"ok"}` を返すようにする。作業の最初に `grep -rn "signIn" frontend/src --include=*.test.tsx` で他の偽物も挙げ、型が合わなくなるものは同じく直す。`signIn` は戻り値をそのまま返す。型は `AuthContext.tsx:39` の `signIn: (email, password) => Promise<void>` を `Promise<SelfLoginResult>` に、試験用の値 `:183` の `signIn: async () => {}` を `async () => ({kind:"ok"})` に、Firebase の道（:130）は `{kind:"ok"}` を返すように直す。ログイン画面は `approval_required` のとき待ちの表示に切り替える。行番号は `postAuth` が :88、`selfLogin` が :103
- ログイン画面 `frontend/src/pages/login/LoginPage.tsx`: 待ちの表示に切り替える（番号を大きく・残り時間・「予備の合言葉で入る」・「いつもの機械も合言葉も無いとき」の説明）。15秒ごとに poll。poll が 429 を受けたら「少し待ってから続けます」を出し、30秒ごとに下げる（審査 軽微3）。部品は既存の Stack・Button・TextFieldControl・TextLink・Modal
- いつもの機械の小窓 `frontend/src/features/auth/LoginApprovalWatcher.tsx`: **`DesktopShell.tsx:204` と `MobileShell.tsx:198` の両方の RealtimeProvider の内側**に置く（審査 要修正11）。SSE の `auth.login_request`・画面を開いたとき・つなぎ直し・タブに戻ったときに `GET /api/v1/login-approvals/pending`（5秒に1回までにまとめる・login の枠の外）。Modal に機械の種類・場所・時刻、番号ボタン3つ、「私ではない」（danger）。pending が0件になったら閉じる。拒否後はパスワード変更への案内
- アカウント設定 `frontend/src/pages/account-settings/SecuritySection.tsx` の並び: 「ログインしている機械」（DataTable・「この機械」印・ログアウト ConfirmModal）と「予備の合言葉」（残り数・作り直し ConfirmModal・10個を1回だけ表示してコピー）。場所の列の下に DB-IP の表示
- 最初のログイン（D5）と合言葉0個の人: ログイン後に1回、合言葉を作る案内の Modal
- 管理画面 `frontend/src/pages/super-admin/`: 「ログインの許可待ち」一覧（DataTable・許可 ConfirmModal に本人確認の方法の入力欄＝TextFieldControl・必須）
- API の形の検査（第4版 審査 軽微）: 口を足したので、backend を直した後に `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` と `cd frontend && npm run generate:api-types` を流し、変わった `frontend/api-contract/openapi.json` と `frontend/src/api/generated/schema.d.ts` を同じ PR に入れる（入れないと CI の形の検査で落ちる）
- i18n キーは `login.deviceApproval.*`・`accountSettings.devices.*`・`accountSettings.recoveryCodes.*`・`superAdmin.loginRequests.*`（ja.json :674 付近・:3193 付近の並びに合わせる）

### 段W（PR-W・段A の後・段B の前。migration を含む＝危険 PR・GO 要）ホーム画面のアプリへの通知（web push・D13）

- 部品: `pywebpush==2.5.0`（MPL-2.0・2026-08-29 公開・PyPI で確認。Context7 は月の上限で使えず公式を直接確認）
- 鍵: VAPID の鍵の組を1回作り、本番の .env に `WEBPUSH_VAPID_PRIVATE_KEY`（秘密）・`WEBPUSH_VAPID_PUBLIC_KEY`・`WEBPUSH_VAPID_SUBJECT` を置く。GitHub の秘密に `gh secret set` で直接流し（値は表示しない）、deploy.yml の .env 書き出し（`deploy.yml:364-378` の `NAME='${{ secrets.NAME }}'` の形）と古い行の削除（`:318-320`）に3行ずつ足す。未設定なら通知を送らず、画面とメールだけで動く
- migration: `public.user_push_subscriptions`（id / user_id FK CASCADE / trusted_device_id FK CASCADE（いつもの機械にだけ送る） / endpoint TEXT UNIQUE / p256dh TEXT / auth TEXT / created_at / last_success_at / failed_count SMALLINT / revoked_at）。全列 COMMENT。`PUBLIC_TABLES` に足す。ai_cloud の分類3か所と試験の件数を段A と同じやり方で足す（endpoint・p256dh・auth の3行を `mask`・理由は空。件数は 1054→1057、tsv は 1055→1058 行。合わなければ止めて報告）。試験の表定義4か所にも足す
- backend: `POST /auth/push-subscriptions`（いつもの機械のログイン中だけ・今の機械に結び付け）・`DELETE /auth/push-subscriptions/{subscription_id}`（本人の購読だけ・他人の id は 404）・`GET /auth/push-public-key`（`get_current_user` を通す。ログイン中の画面だけが読むため。閲覧者のトークンは 401 になり、閲覧者の隔離の試験はそのまま通る）。依頼の作成時に、その人のいつもの機械（取り消されていない）の購読へ送る。中身は「新しい機械からのログインの許可依頼」と機械の種類・場所・時刻だけ（番号は送らない）。404/410 の返事で購読を取り消す。送信は BackgroundTasks（失敗しても依頼は作る）。書き込みの口（POST と DELETE の2つ）だけを `NO_SIGNAL_ROUTES` に理由付きで足し（GET は足さない）、状態を変える口は `_require_app_origin` を通す
- frontend: `frontend/public/manifest.webmanifest`（name・icons は既存の `apple-touch-icon.png`・`display: standalone`・`start_url: /`）、`frontend/index.html` に manifest の link、`frontend/public/sw.js`（push で通知を出す・通知を押すとアプリを開き、開いた画面は LoginApprovalWatcher が依頼を出す。キャッシュはしない＝今の配信の動きを変えない）。アカウント設定の「ログインしている機械」の上に「この機械に通知を出す」（金型 `frontend/src/components/Toggle.tsx`）。iPhone でホーム画面に追加していないときは、その手順を `t()` の文で出す。ホーム画面のアプリは Safari と Cookie の置き場が別になることがある（【未確認】）。別なら、ホーム画面のアプリは最初に1回だけ「新しい機械」として許可が要る。設計はそのまま動く（新しい機械として扱うだけ）。案内文に「ホーム画面に追加したら、最初に一度だけ許可が要ることがあります」と入れる
- 試験: pytest で依頼1件につき送信関数が購読ごとに1回・410 で取り消し・取り消された機械の購読へは送らない。Vitest で購読の切り替えの表示条件
- API の形の検査（段A と同じ）: 口を足したので `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` と `cd frontend && npm run generate:api-types` を流し、変わった `frontend/api-contract/openapi.json` と `frontend/src/api/generated/schema.d.ts` を同じ PR に入れる
- 本番の確かめ: PO の機械での通知の目視は、PO が「通知を許可」を押した後になる（自動では確かめられない）。自動で確かめるのは送信の記録（last_success_at）

### 段B（PR-B・deploy.yml を含む＝危険 PR・GO 要。段A・段W の本番反映と B-0 の後）

- B-0（本番作業・PR なし）: 本番 backend で管理用の命令を実行し、出力を画面に出さずに `gh secret set SMOKE_E2E_DEVICE_TOKEN` へ流す。値は記録しない。`user_trusted_devices` の user87・`created_via='cli'` の件数（1行）だけ reader 鍵で確かめる
- B-1 `tests/prod-check/login.ts`（ログインの1か所の置き場・審査 要修正13）: `login(page, ...)`（:35）の最初で、`SMOKE_E2E_DEVICE_TOKEN` があれば `page.context().addCookies([{name:"sa_device", value, domain: new URL(BASE_URL).hostname, path:"/api/v1/auth", secure:true, httpOnly:true, sameSite:"Strict"}])` を呼ぶ。`url` では付けない（Playwright 1.60.0 は `url` から path を作るとき最後の `/` までで切るため、`/api/v1/auth` が `/api/v1/` になる。`frontend/node_modules/playwright-core/lib/coreBundle.js:13466`）。`domain` と `path` を直接書くので、Cookie は画面と同じ host（既定 `https://app.salesanchor.jp`・:11）の path `/api/v1/auth` になり、本物の `sa_device` と同じ置き場になる。画面は認証を同じ host の `/api/v1/auth`（`frontend/src/lib/auth/selfAuth.ts:12` の相対パス）に送り、本物の `sa_device` も同じ host・同じ path に付くので一致する。受入で「Cookie を付けたログインが 200」を確かめる。呼び出し元の `tests/prod-check/fixtures.ts`（newContext）と `page-speed.spec.ts:480` の両方がこれを通る。`.github/workflows/prod-ui-check.yml:104-105,153-154` の env に1行ずつ足す
- B-2 `.github/workflows/deploy.yml:371` 付近の .env 書き出しに `AUTH_DEVICE_APPROVAL='enforce'` と `AUTH_DEVICE_BOOTSTRAP_CUTOFF='<固定値 UTC>'`（D4）を足し、`:318-320` の古い行の削除にも足す。docker-compose.yml の backend env の `AUTH_PROVIDER`（:134-136）の並びに `AUTH_DEVICE_APPROVAL=${AUTH_DEVICE_APPROVAL:-off}`・`AUTH_DEVICE_BOOTSTRAP_CUTOFF=${AUTH_DEVICE_BOOTSTRAP_CUTOFF:-}`（段A で入れておく。空なら D4 の登録をしない）
- 反映が締切までに終わらなかったら、締切を直す PR を出し直す（締切を過ぎた状態で enforce を始めない）

### 段C 本番での受入（下の表）

## 5. 変更しない所

ログイン失敗の回数制限の値（`self_tokens.py:29-30`・`cache.py:307-308`）、smoke の道、閲覧ページのログイン、ADR-1048 の6桁、nginx の設定、パスワード再設定メールの文面、`.claude/scripts/review-gate`。

## 6. 受入条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| K1 | pytest: enforce で印なし login → 202・トークン無し・応答の Set-Cookie に `sa_login_pending`（HttpOnly・Secure・SameSite=Strict・path `/api/v1/auth/login-requests`）がある・`auth_events.event_type='auth_pending'`・reason `device_approval_required`。Vitest: `selfLogin` が 202 で `approval_required` を返し、トークンを取り込まない。本番: 受入の自動試験（新しいブラウザで user87 のログイン）→ 202 と画面の文言をスクリーンショット |
| K2 | pytest: 依頼で SSE 宛先 `rt:u:{id}` に1件（別の人の接続には届かない）・メール送信関数が1回（リンクなし・時刻・機械・場所）・購読へ送信関数が1回。本番: 印付きのブラウザで依頼から pending 表示までの秒数を計測（60秒以内）＝○×。web push の「届いて出た」は、PO の機械で「通知を許可」を押してもらった後に1回試す（自動の確かめは送り先が 201 を返し `last_success_at` が依頼の時刻から60秒以内まで）。PO の目視が済むまで web push の部分は「判定待ち」とし、K2 全体の ○ は画面とメールで判定する |
| K3 | pytest: 正しい番号で approve → poll がトークンと印を返す。別の人の依頼 id の approve は 404・状態は変わらない。`sid` の無いトークンは 403。同じ依頼に poll を2回同時に送っても発行は1回。取り消された機械の組からの approve は 403。本番: 受入試験で待つ側が入れる |
| K4 | pytest: 別の人の依頼 id の reject は 404・誰もログアウトしない。reject → poll が rejected、押した組以外の組が全部 revoked、他の組の古いアクセストークンが次の要求で 401。approve と reject を同時に送ると片方だけ通る。本番: 3つ目のブラウザが 401 になる |
| K5 | pytest: 許可済みの印で login → 200。D4 の境界（締切1秒前の組は登録・ちょうどは 401）。本番: K3 のブラウザで再ログインして 200 |
| K6 | pytest: 合言葉で入れる・同じ合言葉2回目は失敗・10個作られる・生の値は DB に無い・間違いで口座の失敗回数が1増える。本番: user87 で作り直し→1個で入る→同じ値で失敗 |
| K7 | pytest: 管理者の口で approve → 待つ側が入れる・`decided_by_user_id`・`decided_note`・操作の記録（`_record_auth_audit` の1行。`tenant_id` が依頼した人の会社・`record_id` が NULL・`new_data` の `request_id` が依頼の id）・待つ側の poll の `auth_events.reason='approved_admin'`・自分の依頼は 403・super admin 以外 403・note 無しは 422・出どころ違いは 403。本番: user87 の依頼を作り、PO のブラウザ（super admin でログイン済みのもの）で管理画面から許可し、reader 鍵で `decided_by_user_id` と `auth_events` を確かめる。PO のブラウザが使えないときは K7 の本番は「判定待ち」とし、受入を完了とは書かない（pytest の ○ と本番の 403 の ○ は別に書く） |
| K8 | pytest: 一覧に日時・場所・種類。DELETE で結び付いた組が revoked、その機械のアクセストークンが 401。本番: 受入試験で一覧の件数と取り消し後の 401 |
| K9 | pytest: 成功・失敗・許可待ちそれぞれで auth_events に user_id・reason・is_new_device。middleware から口の `request.state` が読める。どの列にもパスワード・合言葉の文字列が無い。本番: reader 鍵で受入時刻以降の user87 の行の reason 別件数 |
| 点検が止まらない | PR-B 後の prod-ui-check の手動実行が緑（画面点検と速さの記録の両方） |
| 相談係 AI の見え方 | migration-test の T10 と新しい19列の試験が緑。本番: 反映後の `ai_cloud_meta.build_log` の最新行が ok・`column_class` が1054行（PR-W 後は1057行） |
| 場所データの大きさ | 本番: 取り込んだ MMDB の大きさと、取り込み前後の backend の使用メモリ（上限 512M・`docker-compose.yml:166`）を記録する。使用が上限の8割を超えたら場所の表示を止める（`GEOIP_DB_PATH` を空にする）。大きさは【未確認】 |

## 7. リスクと対処

| リスク | 対処 |
|---|---|
| 締切より前に作られた組（盗まれた更新 Cookie を含む）は D4 で登録される | 今と同じ強さ（悪くはならない）。締切から30日で終わる。K8 の一覧で見つけて取り消せる。段A〜段B の間を短くする（同じ日に B まで） |
| D5: 一度もログインしていない5人のパスワードが漏れていると、攻撃者の機械が最初のいつもの機械になる | 初回パスワードは本人に直接渡したもの（ADR-1013）。登録したことをメールで知らせる。本人が後で K8 の一覧で見つけて取り消せる。5人には最初のログインを早めに済ませてもらう |
| Redis が落ちている間は、失効した組のアクセストークン（最長900秒）が通る | 既存のブラックリストと同じ扱い（`cache.py:403-418`）。更新トークンの失効は DB なので、900秒後には必ず切れる |
| 取り消した後も、開いていた SSE の接続はつながったまま残る | 中身は話題の名前だけで、データは出ない。次のデータ取得が 401 になり、画面はログアウトする |
| 待ちの poll が nginx の login 枠（10回/分・追加5）を使う | 15秒ごと＝4回/分。429 で30秒に下げる |
| いつもの機械の小窓の一覧の取得が login 枠を食い、普段の画面や本番の自動点検（1試験で login 枠3回まで）が 429 になる | 一覧は `/api/v1/login-approvals/pending` に置き login 枠の外（`location /api/`・30回/秒）にする（A-2「回数の枠」）。受入で、本番の自動点検の1回分に 429 が0件であることを確かめる |
| 場所のデータが取れない | 「不明」と出すだけで認証は止めない |
| 全員がいつもの機械を失う | 予備の合言葉、最後は super admin 2人（PO・担当エンジニア）の管理画面 |
| 前にログインしたことがあるのに、切替の日にログイン中の機械が無い人（本番で1人。有効9人－ログイン中3人－一度もログインしていない5人） | D4 にも D5 にも当たらない。次にパスワードで入るときは許可待ちになり、いつもの機械も合言葉も無いので、super admin が本人確認のうえ許可する（K7 の道）。パスキーがあればそのまま入れる。切替の日に reader 鍵でこの人数を数え直し、PO への完了報告で「この人は次のログインで管理者の許可が要る」と伝える |
| off から enforce に戻すとき、締切を新しくしないと off の間にできた組が 401 になる | 戻した後にもう一度 enforce にするときは、締切を新しい固定値にする PR を出す |
| super admin 自身がいつもの機械と合言葉を両方失う | もう1人の super admin が許可する（自分の依頼は自分で許可できない） |
| メールが点検専用の人のアドレスへ飛ぶ | 印付きの点検は依頼を作らないので送られない。受入試験の分だけ |
| 通知を許可していない iPhone は、アプリを閉じていると知らせが出ない | メールで知らせる。設定画面で通知の手順を出す |

戻し方: `AUTH_DEVICE_APPROVAL` を off に戻す（deploy.yml の1行を戻す PR）。off はログインの止め方と機械の登録が今と同じ。違いは1つで、アクセストークンに `sid` が入り、失効した組のアクセストークンも拒まれる（守りが強くなる側）。表と列は残しても害は無い（追加だけ）。web push は VAPID の秘密を消せば送らない。

## 8. 外部事例

| 出どころ | 何を | 適用 |
|---|---|---|
| Meta ヘルプ（kgi.md の一次資料） | 認識していない機械はコードか承認・ブラウザを保存・復旧コード10個・ログインした場所の一覧 | K1〜K8 の形 |
| Google アカウントヘルプ（kgi.md） | 「No, it's not me」でその機械をサインアウトさせ、パスワード変更を勧める | K4・D8 |
| Microsoft Authenticator 番号照合（2023 既定化） | 押し続けて承認させる攻撃への対策 | D1 |
| WebKit「Web Push for Web Apps on iOS and iPadOS」（kgi.md:39） | iOS 16.4 以降・ホーム画面に追加したアプリ・利用者の操作で許可 | D13 |
| DB-IP Lite（db-ip.com・2026-11-01 確認） | CC BY 4.0・MMDB・毎月・アカウント不要・表示必須 | D9 |
| maxminddb 3.2.0・pywebpush 2.5.0（PyPI・2026-11-01 確認・Context7 は月の上限で使えず公式を直接確認） | `open_database(path, Mode.MMAP)`・`get(ip)`／`webpush(subscription_info, data, vapid_private_key, vapid_claims)` | D9・D13 |

数値の成功事例は使わない（直接の根拠になる公開数値が無いため。採用理由は上の仕組みの一致）。

## 9. 維持の仕組み

- 試験: `backend/tests/test_new_device_approval.py`（K1〜K9 の pytest）と `test_web_push.py` を CI の必須の backend 試験に入れる。Vitest は既存の frontend 試験に入る
- 点検: prod-ui-check（毎朝）が印付きでログインできなくなったら Discord に出る（既存の知らせ）
- 片付け: 月次の場所データ更新・日次の古い依頼と機械の削除・5分ごとの期限切れ（Celery beat）
- 管理者が許可するときの本人確認の手順（K7）: 依頼の機械の種類・場所・時刻を、本人に、登録済みの電話番号か対面で読み上げてもらい、一致したときだけ許可する。メッセージアプリの文面だけでは許可しない。確かめた方法を `note` に書く（例「対面で確認」「登録の電話で確認」）
- 置き場: ADR-1055（決定）、本書（設計）、FEATURE-INDEX に「新しい機械の許可」を足す。ADR-1016 に改訂の注記

## 10. 審査記録

### 第1版（13ea58557）: REVISE

- 審査役: 新しく起動した Opus の reviewer（2026-11-01）
- 結果: `VERDICT: REVISE on 13ea58557 design`。重大0・要修正14・軽微7
- 第2版での反映（番号は審査の順）
  - 要修正: 202 の記録（D7）／D4 の締切と境界の試験（D4）／合言葉の形と照合と失敗の数え方（D14）／同時の操作（D15）／管理者の口の置き場と出どころの確かめ（A-2 管理者）／SSE の3か所と話題の表と NO_SIGNAL_ROUTES と ADR-1016 の注記（A-2 知らせ）／ai_cloud の分類3か所と件数（A-1）／PUBLIC_TABLES（A-1）／試験の表定義4か所（A-1）／selfLogin の戻り値と 202 の返し方（A-2 login・A-3）／小窓を両方の外枠に（A-3）／K7 の本番受入（§6）／GeoIP の書き込み役（A-2）／prod-check の Cookie の付け方（B-1）
  - 軽微: off は登録しない（D11）／Redis 停止時（D8・§7）／poll の 429（A-3）／SSE が残る（§7）／ほかの小窓を閉じる（A-2 知らせ）／D5 の危険（§7）／管理者の本人確認の手順（§9）
- 足したもの: アプリを閉じているときの通知（D13・段W）。kgi.md:39 の通知手段に合わせた

### 第2版（4a872fe5d）: REVISE

- 審査役: 新しく起動した Opus の reviewer（2026-11-01）
- 結果: `VERDICT: REVISE on 4a872fe5d design`。重大0・要修正7・軽微9
- 第3版での反映
  - 要修正: 他人の依頼の操作を防ぐ（D15）／承認する側の組の取り方（D16・self_tokens と `_issue_session_tokens` の変更前後）／202 の Cookie の付け方（A-2 login）／NO_SIGNAL_ROUTES は書き込みの口だけ（A-2 知らせ）／rls_bootstrap は直さず別の試験で守る（A-1）／列の分類の19行と件数1054（A-1）／前にログインしたが機械の無い1人（§7）
  - 軽微: Connection の user_id の置き方と既存試験／呼び出し元 AuthContext の signIn／prod-check の Cookie を `page.context()` と `url` で付ける／締切後のパスワード変更／戻した後の締切／off の違い／違う番号の状態番号／iPhone のホーム画面アプリの Cookie（未確認として案内文に）／場所データの大きさ（未確認として受入で測る）
  - 判定の書き方: K2 の web push と K7 の本番を「判定待ち」として分けた

### 第3版（ff2669bd6）: REVISE

- 審査役: 新しく起動した Opus の reviewer（2026-11-01）
- 結果: `VERDICT: REVISE on ff2669bd6 design`。重大0・要修正4・軽微9。前回の要修正7件は反映済みと確認された。件数（1035→1054→1057）と19列の選び方は正しいと確認された
- 第4版での反映
  - 要修正: パスワード変更を off と enforce で分け、D16 の一覧に入れた（A-2）／管理者の許可の記録は既存の操作の記録と、待つ側の poll の `auth_events` に分けて書き、記録の仕組みは広げない（A-2 管理者）／一覧の取得を login 枠の外の `/api/v1/login-approvals/pending` に移した（A-2「回数の枠」・§7）／自動点検の Cookie を `domain` と `path` で付ける（B-1）
  - 軽微: smoke の行番号／`_NAME_RE` の決まり／selfAuth の試験も直す／`signIn` の型と試験用の値と Firebase の道／人宛ての送り口と `rt:u:`（publisher）／K9 の試験の方法（偽の `AsyncSessionLocal`）／合言葉の部分索引と `revoked_at`／refresh で登録したときの Cookie と `get_current_session` の db／列の型

### 第4版（762582b33）: REVISE

- 審査役: 新しく起動した Opus の reviewer（2026-11-01）
- 結果: `VERDICT: REVISE on 762582b33 design`。要修正3・軽微10。前回の要修正4件は反映済みと確認された
- 第5版での反映
  - 要修正: poll と recovery を閲覧者の隔離の試験の「認証なしの口」の表に理由付きで足し、push-public-key は認証ありにした（A-2）／管理者の許可の記録の引数を決め、K7 で確かめる項目に足した（A-2 管理者・§6）／publisher の古い行を消し、人宛ての送り口の1つに絞った（A-2）
  - 軽微: 自動点検の行番号／PR-A と PR-W の API の形の作り直し／`signIn` の偽物の試験／`backend/app/cli/__init__.py`／新しい4表に RLS を付けない理由と GRANT／新しい口の見出しの「すべて」／`family_created_at`／パスワード変更で登録したときの Cookie／D16 を本体の関数と依存に分けた／許可で入ったときの `last_login`

### 第5版

（ここに審査役の VERDICT を追記する）
