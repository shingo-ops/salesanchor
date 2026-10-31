# 現状調査 — 知らない機械からのログインを止める仕組みの土台

調べた日: 2026-10-31
基準の sha（`git rev-parse origin/main`）: 7e91551634a8a6e06a11b5387b6d0a70a0e29f5b
作業枝: release/new-device-approval-design（origin/main との差は docs/handoff/auth-new-device-approval/ の文書だけ。製品コードは origin/main と同じ）
合格の基準: docs/handoff/auth-new-device-approval/kgi.md（K1〜K9）

読むだけの調査。提案・設計は書かない。本番には接続していない。secrets・.env は読んでいない。鍵・パスワード・メールアドレス・IP の実際の値は書かない。
行番号はすべて上の sha 時点。パスは /home/user/salesanchor からの相対（フルパス表記は省略せず docs/ や backend/ から書く）。

---

## A. 既存 ADR

### 【事実】
- 探した語（docs/adr/ を `git grep -il`）: passkey / device / session / refresh / 2fa / totp / mfa / recovery / audit / notification / push / realtime。
- 今回に直接関係する ADR は3本。
  - ADR-1013（自社ログインとパスキー）— 状態 **Accepted**。docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:5。
    - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:22 パスワード照合・トークンの発行と失効・再設定メール・パスキーを自社サーバーで持つ。
    - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:23 ログイン情報は public.users.id にだけぶら下げる（users の4列と子表 webauthn_credentials・password_reset_tokens・auth_refresh_tokens）。
    - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:24 パスワードは Argon2id、長さ15〜64、口座単位で10回失敗すると15分止める。
    - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:28 ログイン関連 API は app.salesanchor.jp 以外のオリジンから呼ばれたら拒否。パスキーの RP ID は app.salesanchor.jp。
    - docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:30 二段階認証（認証アプリ）は本 ADR の範囲外（次の便で任意設定）。
  - ADR-1048（管理者のログインは2段階の確認を必須にし、初めての機器からはいつもの機器で番号を選んで承認する）— 状態 **Proposed**（2026-10-27）。docs/adr/ADR-1048-admin-two-step-login.md:5。docs/adr/README.md:228 も Proposed。
    - 対象は super admin と各会社の owner/admin。docs/adr/ADR-1048-admin-two-step-login.md:6, :16。
    - docs/adr/ADR-1048-admin-two-step-login.md:18 初めての機器は、いつもの機器の画面で2けたの番号を3候補から選ぶ承認。
    - docs/adr/ADR-1048-admin-two-step-login.md:19 承認の知らせは SSE（人単位の宛先 `rt:u:{user_id}` を足す）とメール。メールに承認ボタン・リンクは置かない。
    - docs/adr/ADR-1048-admin-two-step-login.md:20 新しい子表 `public.user_totp`・`public.user_trusted_devices`（cookie の値のハッシュだけ）。承認の依頼は Redis に5分・1回限り。
    - 設計書は docs/handoff/admin-2fa/design.md、現状調査は docs/handoff/admin-2fa/recon.md、審査は docs/handoff/admin-2fa/review-opus.md。
    - 実装の有無: `user_totp`・`user_trusted_devices`・`trusted_device` を backend・frontend/src・migrations・scripts で grep → 0件（実装は無い）。
  - ADR-1016（即時反映の標準）— 状態 **Accepted**。docs/adr/ADR-1016-realtime-change-signal-standard.md:5。
    - docs/adr/ADR-1016-realtime-change-signal-standard.md:15 通り道は SSE 1本 `GET /api/v1/events/stream`。ページごとの通り道は禁止。
    - docs/adr/ADR-1016-realtime-change-signal-standard.md:16 合図は topic と origin だけ。中身は送らない。
    - docs/adr/ADR-1016-realtime-change-signal-standard.md:23 チャンネルは rt:t:{tenant_id} と rt:global。docs/adr/ADR-1016-realtime-change-signal-standard.md:37 に rt:shared を追加（改訂 2026-10-18）。
    - docs/adr/ADR-1016-realtime-change-signal-standard.md:60 WebSocket は比較した代替案の1つ（比較表は design.md §5 とある）。
    - docs/adr/ADR-1016-realtime-change-signal-standard.md:64 backend/app/auth/ の変更は A 区分（ADR-1015）。docs/adr/ADR-1016-realtime-change-signal-standard.md:65 nginx を含む PR は危険 PR で PO の GO が要る。
- その他の関連 ADR（名前だけ）: ADR-138（password_hash 列廃止。docs/adr/ADR-138-remove-password-hash.md）、ADR-1017（smoke の最小権限認証。docs/adr/ADR-1017-smoke-auth-least-privilege.md）、ADR-1019（閲覧ページの別アカウント。docs/adr/ADR-1019-inventory-viewer-separate-accounts.md）、ADR-1018（public の機微表の RLS。docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md）、ADR-128・ADR-129（audit_logs の網羅）、ADR-144（UI ガバナンス）、ADR-072（schema 修飾）。
- docs/adr/FEATURE-INDEX.md:33 ログイン/パスキー → ADR-1013、docs/adr/FEATURE-INDEX.md:34 管理者の2段階・新しい機器の承認 → ADR-1048。FEATURE-INDEX に SSE/通知/リアルタイムの行は無い（`grep -n -i "sse|websocket|realtime|push|通知"` で通知は ADR-056 の行 docs/adr/FEATURE-INDEX.md:43 のみ。これは開発運用の通知で、利用者向けではない）。
- ADR-069（Uptime Kuma）の 2FA/TOTP は監視ツールの設定で、アプリの認証とは別。docs/adr/ADR-069-uptime-kuma-activation.md:45, :61。

### 【未確認】
- 「新しい機械の許可」を利用者全員に広げる ADR は見つからない（ADR-1048 は管理者のみ。docs/adr/ADR-1048-admin-two-step-login.md:23 で非管理者は対象外）。探した所: docs/adr/ 全体の grep、FEATURE-INDEX.md。
- ADR-1048 の Proposed がその後 Accepted になったかは、docs/adr/ADR-1048-admin-two-step-login.md:5 と docs/adr/README.md:228 の時点では Proposed。会話上の承認は未確認。
- ADR-1016 の design.md（docs/handoff/realtime-standard/design.md）の中身は今回読んでいない。

---

## B. ログインの道（backend/app/routers/auth.py）

### 【事実】
- 共通部品
  - 更新トークンの Cookie を付けてアクセストークンを返す: backend/app/routers/auth.py:233（`_issue_session_tokens`）。password login・passkey login・refresh・password change が使う。
  - Cookie を付ける: backend/app/routers/auth.py:220-230（`_set_refresh_cookie`）。名前 `sa_refresh`（backend/app/auth/self_tokens.py:26）、`httponly=True`、`secure`=環境変数 AUTH_COOKIE_SECURE（既定 true。backend/app/auth/self_tokens.py:59）、`samesite="strict"`、`path=/api/v1/auth`（backend/app/auth/self_tokens.py:27）、`max_age`=期限までの秒数。
  - Cookie を消す: backend/app/routers/auth.py:241-248（`_clear_refresh_cookie`）。
  - アクセストークン: backend/app/auth/self_tokens.py:92-104（`create_access_token`）。HS256、有効 900 秒（backend/app/auth/self_tokens.py:24）、クレームは iss・sub（user_id）・email・jti・iat・exp、amr は 1要素の配列（None なら入らない）。本文で返す（`SelfTokenResponse`: access_token / token_type / expires_in。backend/app/routers/auth.py:199-202）。
  - 更新トークン: `secrets.token_urlsafe(32)` を生成し、sha256 を表に保存（backend/app/auth/self_tokens.py:162-191）。絶対 30 日（backend/app/auth/self_tokens.py:25）。
  - 入口の検査: 自社発行が有効か backend/app/routers/auth.py:210-212、画面のオリジンか backend/app/routers/auth.py:215-217。
- パスワードのログイン: `POST /auth/login` backend/app/routers/auth.py:307-366
  - IP 単位の失敗上限の確認 backend/app/routers/auth.py:318、口座の存在・有効・停止期限の確認 backend/app/routers/auth.py:335-339、照合 backend/app/routers/auth.py:341、成功で失敗数リセットと last_login 更新 backend/app/routers/auth.py:345-347、更新トークン発行 backend/app/routers/auth.py:357-359、アクセストークン発行（amr="pwd"）backend/app/routers/auth.py:361。パスワード変更成功時の再発行も amr="pwd"（backend/app/routers/auth.py:634）。
  - 失敗の理由は区別せず `invalid_credentials` 1種類（backend/app/routers/auth.py:279-280）。
- パスキーのログイン
  - 選択肢: `POST /auth/passkey/login/options` backend/app/routers/auth.py:888-898。
  - 検証: `POST /auth/passkey/login/verify` backend/app/routers/auth.py:901-995。更新トークン backend/app/routers/auth.py:988、アクセストークン（amr="webauthn"）backend/app/routers/auth.py:990。
  - sign_count の巻き戻り検知時に監査記録 backend/app/routers/auth.py:957-970。
- 更新（refresh）: `POST /auth/refresh` backend/app/routers/auth.py:369-401
  - Cookie から取り、入れ替え backend/app/routers/auth.py:381。失敗時は 401 と Cookie 削除 backend/app/routers/auth.py:382-386。成功時のアクセストークンは amr=None（backend/app/routers/auth.py:392）＝更新で amr は引き継がれない。
- ログアウト: `POST /auth/logout` backend/app/routers/auth.py:165-190
  - アクセストークンを Redis のブラックリストに載せる（TTL 3600 秒。backend/app/routers/auth.py:178、実体 backend/app/cache.py:160）。Redis が使えないと 503。
  - Cookie の更新トークンがあれば失効させ Cookie を消す backend/app/routers/auth.py:185-189。
- その他のトークン発行口: パスワード変更 backend/app/routers/auth.py:553（backend/app/routers/auth.py:630 で新しい更新トークン）。パスワード再設定確認 backend/app/routers/auth.py:473-550（トークンは出さず全失効だけ）。
- フロントの受け口: frontend/src/lib/auth/selfAuth.ts（getAccessToken・hasSession・adoptAccessToken を他ファイルが import。例: frontend/src/hooks/useSSE.ts:6, frontend/src/pages/account-settings/SecuritySection.tsx:12）。

### 【未確認】
- パスキー検証 backend/app/routers/auth.py:901-995 の全行は読んでいない（`_issue_session_tokens` 呼び出しは grep で :990 と確認）。
- 認証後の API が `get_current_user` で自社トークンをどう検証するか（backend/app/auth/dependencies.py:82 `_authenticate_self_token`）の中身は今回読んでいない。

---

## C. 更新トークンの保存

### 【事実】
- 表: `public.auth_refresh_tokens`。作成 migrations/20261013_160000_add_self_hosted_auth_tables.sql:68-81。登録 scripts/run_all_migrations.sh:1132。
- 列: id（BIGSERIAL）・user_id（public.users(id) 参照、ON DELETE CASCADE）・token_hash（BYTEA、32バイト固定）・family_id（UUID）・family_created_at・expires_at・revoked_at（NULL=有効）・created_at・last_used_at・user_agent_hash（BYTEA、sha256。「記録と検知だけに使い拒否には使わない」と COMMENT）。migrations/20261013_160000_add_self_hosted_auth_tables.sql:68-93。索引は user_id と family_id。migrations/20261013_160000_add_self_hosted_auth_tables.sql:82-83。
- ORM モデルは無い（生 SQL）。理由は backend/app/auth/self_tokens.py:3-5（migration-guard チェック1を避けるため）。
- 作る所: backend/app/auth/self_tokens.py:162-191（INSERT は backend/app/auth/self_tokens.py:177）。呼び出し元: backend/app/routers/auth.py:357（login）、backend/app/routers/auth.py:630（password change）、backend/app/routers/auth.py:988（passkey login）、backend/app/auth/self_tokens.py:240 付近（rotate 内）。
- 入れ替え: backend/app/auth/self_tokens.py:194-243。古い行を1文で失効→取り出し（backend/app/auth/self_tokens.py:203）。失効済みの再利用を検知すると同じ family_id を全部失効（backend/app/auth/self_tokens.py:217-224）。ユーザーが無効、または password_changed_at が発行より新しい場合は拒否（backend/app/auth/self_tokens.py:230-236）。
- 取り消す所
  - 1本: backend/app/auth/self_tokens.py:246-253（`revoke_refresh_token`、logout が呼ぶ）。
  - その人の全部: 次の2か所に、同じ UPDATE（`WHERE user_id = :uid AND revoked_at IS NULL`）がある。パスワード再設定の確定 backend/app/routers/auth.py:524-529、パスワード変更 backend/app/routers/auth.py:611-616。
  - 管理者が他人の分を取り消す口: 見つからない（下の未確認）。
- 消す（行の削除）処理: 見つからない。revoked や期限切れの行を消すジョブは grep していない範囲に無い（下の未確認）。
- 「ある人の全部の機械をログアウトさせる」専用の関数: 無い。上の2か所がその場で UPDATE を書いている。ただし更新トークンを失効させても、発行済みのアクセストークン（最長900秒）は生きる。アクセストークンの失効手段は logout の Redis ブラックリスト（トークン単位）のみ（backend/app/cache.py:160）。人単位の失効の仕組みは未確認。
- スタッフの無効化/削除と更新トークン: backend/app/routers/staff.py に `revoke` の語は無い（`grep -n "revoke|is_active" backend/app/routers/staff.py` は backend/app/routers/staff.py:103 の INSERT のみ）。更新時に is_active を見て拒否する側は backend/app/auth/self_tokens.py:230-232。

### 【未確認】
- auth_refresh_tokens の期限切れ行の定期削除: backend/app/tasks/maintenance.py と backend/app/celery_app.py:101-110 を見た範囲では auth_events・data_access_events の削除のみ。他のタスクファイルは全件読んでいない。
- 機械ごとの一覧を出す口（この人の有効な更新トークンの一覧）: backend/app/routers/auth.py の `@router` 一覧に無い。

---

## D. 機械の見分け

### 【事実】
- 機械ごとの印（クッキー・ID）を作っている所: **無い**。更新トークン用 Cookie `sa_refresh` は「ログイン1回ごと」に作る（機械を覚えるものではない。ログインのたびに新しい family_id）。frontend 側のタブ識別子 `getClientId`（frontend/src/lib/realtime/clientId.ts）は即時反映の origin 用で、認証には使っていない（用途は frontend/src/lib/realtime/RealtimeProvider.tsx:10 の import と ADR-1016 :16）。`device` を含む migration は migrations/20260912_160000_line_import_devices.sql と migrations/20260923_040000_update_device_tcg_schema.sql だけで、いずれも認証と無関係（LINE 取り込み・TCG）。
- user_agent の受け取り: ログイン系は `request.headers.get("user-agent")` を更新トークン発行に渡すだけ（backend/app/routers/auth.py:358, :381, :631, :988）。保存先は sha256 化して `auth_refresh_tokens.user_agent_hash`（backend/app/auth/self_tokens.py:171, :182）。元の文字列は残らない（この表には）。
- IP の受け取り: 関数 `get_client_ip` が唯一の入口（backend/app/client_ip.py:12-21）。`X-Real-IP` の値が IP として正しければそれを使い、なければ接続元。`X-Forwarded-For` は読まない（backend/app/client_ip.py:3-6 の説明）。呼び出し元: backend/app/routers/auth.py:317, :481, :568, :893, :911、backend/app/auth/dependencies.py:145、backend/app/middleware/audit.py（`get_client_ip(request)`）。
- IP の残し方
  - Redis のカウンタ: キーは IP の sha256 先頭16文字（backend/app/cache.py:317, :333）。
  - public.auth_events.client_ip（VARCHAR(45)）と user_agent（先頭500文字）に生で残る（migrations/001_create_auth_events.sql:12-13、書き込み backend/app/middleware/audit.py:236-254）。
  - 閲覧者の public.viewer_login_events（migrations/20261016_150000_add_viewer_accounts.sql:58）に IP・UA を残す関数 `_record_event`（backend/app/routers/viewer.py:105）。列の詳細は未読。
- nginx が渡す見出し: `proxy_set_header X-Real-IP $remote_addr;`。app.salesanchor.jp 側 nginx/nginx.conf:105, :120, :135, :150, :163, :183, :203（各 location）。api.salesanchor.jp 側も同形（nginx/nginx.conf:362 以降の location）。`X-Forwarded-For $proxy_add_x_forwarded_for` も付くが backend は読まない。`real_ip` 系の設定は nginx/nginx.conf に無い（`grep -n -i real_ip` 0件）。
- 認証 API の nginx 側の制限: `limit_req_zone ... zone=login rate=10r/m`（nginx/nginx.conf:6）。`location /api/v1/auth/` に `limit_req zone=login burst=5 nodelay;`（nginx/nginx.conf:145）。
- 場所の目安（国・市）を出す部品（GeoIP など）: backend/requirements*.txt・backend/app を `geoip|maxmind` で探していない（下の未確認）。

### 【未確認】
- nginx の前に Cloudflare 等の別の中継があるか: nginx/nginx.conf に `real_ip_header`・`set_real_ip_from`・CF- ヘッダの記述は無い。ただし DNS・Cloudflare 側の設定は GUI で、リポジトリからは見えない。もし中継があれば `$remote_addr` は中継の IP になる。確かめた所: nginx/nginx.conf、.github/workflows/setup-pgw.yml:62, .github/workflows/setup-pushgateway-once.yml:102（これは別サービス）。
- GeoIP ライブラリ・データの有無（未探索）。
- viewer_login_events の列（migrations/20261016_150000_add_viewer_accounts.sql:58-69 の途中以降は読んでいない）。

---

## E. 認証の記録

### 【事実】
- ai_ro / ai_cloud から見える auth_events
  - 元の表は `public.auth_events`。作成 migrations/001_create_auth_events.sql:6-16。
  - 列（全部）: id BIGSERIAL PK、event_type VARCHAR(50) NOT NULL（auth_success / auth_failure / auth_request）、path VARCHAR(500) NOT NULL、method VARCHAR(10) NOT NULL、status_code INTEGER NOT NULL、client_ip VARCHAR(45)、user_agent VARCHAR(500)、duration_ms INTEGER、created_at TIMESTAMPTZ DEFAULT NOW()。migrations/001_create_auth_events.sql:7-15。
  - 索引: (event_type, created_at DESC) migrations/001_create_auth_events.sql:19-20、(client_ip, created_at DESC) migrations/001_create_auth_events.sql:22-23、created_at 単独 migrations/072_add_retention_indexes.sql:10-11。
  - ALTER で列を足した migration: `grep -i auth_events migrations/*.sql | grep -i -E "alter|add column"` → 0件。
  - **利用者を表す列（user_id・email・tenant_id）は無い**（上の列の一覧に無く、後から足した migration も無い）。
  - ai_cloud の伏せ方: migrations/20261024_100300_create_ai_cloud_views.sql:48-50 で client_ip・event_type・method・path・user_agent を `mask`（伏せる）に分類。
  - ai_ro ビューの作成: migrations/20261017_130100_create_ai_ro_views.sql。同ファイルで `auth_events` を grep しても0件（作り方が表の一覧でなく自動の可能性。未確認）。
  - ORM モデル: `class AuthEvent` は backend/app に無い（`grep` 0件）。生 SQL で書く。
  - テスト用 DB の最小定義: .github/workflows/migration-test.yml:1338-1352。
- 書く所: backend/app/middleware/audit.py の `AuditMiddleware._record_auth_event`。INSERT は backend/app/middleware/audit.py:236-254。
  - 対象: パスが `/api/v1/auth/` で始まる全リクエスト（backend/app/middleware/audit.py:37, :184）、または応答が 401・403（backend/app/middleware/audit.py:40, :185）。
  - event_type の決め方: 401/403 → auth_failure（backend/app/middleware/audit.py:226-227）、auth パスで 2xx → auth_success、それ以外 → auth_request。
  - 失敗の理由（パスワード違い・停止中・未登録）は記録されない。誰のログインかも記録されない。「初めての機械か」も無い。
  - 除外パス: /health /metrics /docs /openapi /static（backend/app/middleware/audit.py:46）。
  - 注意書き: 「パスワード・トークン等の機密情報は記録しない」backend/app/middleware/audit.py:20-21。
- 別の記録: `_record_auth_audit`（backend/app/routers/auth.py:251-276）は auth_events ではなく、会社別の `tenant_NNN.audit_logs` に書く（呼ぶ先 backend/app/services/audit.py:277、INSERT は backend/app/services/audit.py:313）。列: tenant_id・user_id・action・table_name・record_id・old_data・new_data（backend/app/services/audit.py:313-318 の INSERT 列）。呼び出し元: register backend/app/routers/auth.py:121、パスワード再設定確定 backend/app/routers/auth.py:531、パスワード変更 backend/app/routers/auth.py:618、パスキー登録 backend/app/routers/auth.py:875、パスキー sign_count 異常 backend/app/routers/auth.py:958、パスキー削除 backend/app/routers/auth.py:1041。**パスワードログインの成功・失敗はここに書かれない**（backend/app/routers/auth.py:307-366 に `_record_auth_audit` 呼び出しが無い）。
- 90日で消す処理
  - `purge_auth_events`: backend/app/tasks/maintenance.py:171-189。保持日数は環境変数 `AUTH_EVENT_RETENTION_DAYS` 既定90（backend/app/tasks/maintenance.py:30）。
  - 毎日 5:30 の定期実行登録: backend/app/celery_app.py:101-110。
  - 別の古い手段: scripts/archive_audit_logs.sh:55-72（auth_events の古い行を CSV 圧縮して DELETE）。どこから呼ばれるかは未確認。
- 試験: backend/tests/test_data_deletion_helpers.py:522-534（purge_auth_events）、backend/tests/test_auth_audit_helper.py、backend/tests/test_rls_auth_audit.py。

### 【未確認】
- ai_ro 側で auth_events が実際に見えるか（ai_ro ビューの生成スクリプトを今回特定していない。migrations/20261017_130100_create_ai_ro_views.sql に auth_events の語は無い。ai_cloud の分類表には載っている）。探した所: migrations/、scripts/run_all_migrations.sh:217-222。
- 本番の auth_events の実データ・件数（本番に接続しないため）。

---

## F. 利用者と権限

### 【事実】
- 利用者の表: `public.users`（ORM backend/app/models.py:22-37）。列（ORM）: id・tenant_id（tenants 参照）・username・email（unique）・full_name・is_super_admin（default false）・created_at・updated_at・is_active・last_login。自社ログインで足した列（生 SQL。ORM に無い）: password_argon2_hash・password_changed_at・failed_login_count・locked_until（migrations/20261013_160000_add_self_hosted_auth_tables.sql:6-9）。
- テナント: `public.tenants`（backend/app/models.py:8-20）。列: id・tenant_name・tenant_code・created_at・updated_at・is_active・settings（JSON）。テナントごとのデータは `tenant_NNN` スキーマ（backend/AGENTS.md の「本番テナント tenant_004」等。audit_logs のスキーマ名は backend/app/services/audit.py:303 で `tenant_{tenant_id:03d}` と組む）。ログイン時はテナントが決まる前に引くため users に RLS は付けない（migrations/20261013_160000_add_self_hosted_auth_tables.sql:3）。
- super admin の見分け方: 列 `users.is_super_admin`。関数 `require_super_admin`（backend/app/auth/dependencies.py:516-543）が `getattr(current_user, "is_super_admin", False)` を見る。SSE 側も同じ判定を呼ぶ（backend/app/routers/realtime_events.py:25-31）。
- 会社の管理者の見分け方: `is_tenant_admin(system_keys)`。`get_user_system_keys`（backend/app/auth/dependencies.py:547）が user_roles→roles の system_key 集合を返し、`require_tenant_admin`（backend/app/auth/dependencies.py:606）が owner か admin を通す。「判定の正本は user_roles。users.role は見ない」（同関数の docstring）。
- 現在の利用者を取る入口: `get_current_user`（backend/app/auth/dependencies.py:124）。自社トークンは `_authenticate_self_token` へ振り分け（backend/app/auth/dependencies.py:209）。smoke 用の固定トークン経路あり（backend/app/auth/dependencies.py:148-170、super admin は拒否）。
- 管理画面で利用者を一覧・操作している所
  - スタッフ画面: frontend/src/App.tsx:253（`/staff`→StaffPage）、frontend/src/App.tsx:254（`/staff/:id/edit`）、frontend/src/App.tsx:378（`staff`、別ルート群）。ファイル: frontend/src/pages/staff/StaffPage.tsx・StaffEditPage.tsx・StaffFormFields.tsx。
  - 口: backend/app/routers/staff.py:532 `GET /staff`（権限 staff.view）、:568 `GET /staff/{id}`、:588 `POST /staff`（作成。INSERT INTO public.users は :103）、:671 `PATCH /staff/{id}`、:747 `DELETE /staff/{id}`（権限 staff.delete）。自分用: :251 `GET /staff/me`、:299 locale、:322 theme、:352 profile、:455 avatar。
  - ロール画面: frontend/src/pages/roles/RolesPage.tsx、口は backend/app/routers/roles.py（:175, :203, :259, :332, :373, :403, :486, :520）。
  - super admin の画面群: frontend/src/pages/super-admin/（マスタ編集・閲覧者アカウント frontend/src/pages/super-admin/ViewerAccountsPage.tsx など。ルート frontend/src/App.tsx:348）。テナント削除の口: backend/app/routers/super_admin_tenants.py:38, :104。super admin が「他人の利用者（users）を一覧・ログアウト・許可する」画面・口は見つからない。
  - 自分が super admin かを画面で知る: frontend/src/hooks/useSuperAdmin.ts:19-35（`GET /me/permissions` の is_super_admin。口は backend/app/routers/roles.py:132）。
- 本番の管理者の数（参考。記録からの引用で、今回は本番に接続していない）: docs/handoff/admin-2fa/recon.md の §4（2026-10-27 時点）に有効な管理者3人・パスキー0件とある。

### 【未確認】
- 非管理者を含む「利用者全員の一覧」を出す専用の管理画面（super admin 用）。探した所: frontend/src/pages/super-admin/、backend/app/routers/super_admin_*.py の名前一覧。
- 新しく招待された人が最初にログインする流れ（初回設定メール `send_invite_email` backend/app/services/auth_mail.py:125 の後、パスワード設定→ログイン）の詳細。backend/app/routers/auth.py:473-550（確定）は読んだが、新規ユーザーが「いつもの機械が無い」状態をどう扱うかはコードに存在しない（機械の概念自体が無い）。

---

## G. 知らせの道

### 【事実】
- (1) 即時に画面へ届ける仕組み: **SSE**（WebSocket ではない）。
  - 口: `GET /api/v1/events/stream`、backend/app/routers/realtime_events.py:59（`stream_change_signals`）〜 :112 付近。認証は `get_current_user`・`get_current_tenant`・super admin 判定を短い DB セッションで行う（backend/app/routers/realtime_events.py:68-73 付近）。1人あたり同時5本まで（backend/app/routers/realtime_events.py:24, :75）。30秒ごとに ping（backend/app/routers/realtime_events.py:23, :92 付近）。送る形は `event: change` + JSON（backend/app/routers/realtime_events.py:90）。
  - 配る側: backend/app/realtime/hub.py（プロセスにつき1本、Redis `psubscribe("rt:*")`。backend/app/realtime/hub.py:1, :85）。宛先判定 `_targets` は rt:shared・rt:global・rt:t:{tenant_id} のみ（backend/app/realtime/hub.py:34-46）。**人単位の宛先は無い**。
  - 送る側: backend/app/realtime/publisher.py（チャンネル定数 backend/app/realtime/publisher.py:19-22、`publish_change` :64、同期版 :78）。topic の対応表: backend/app/realtime/topics.py。
  - nginx: `location = /api/v1/events/stream`（nginx/nginx.conf:200 と :462）。バッファ無効・read timeout 3600s。
  - frontend の受け手: frontend/src/lib/realtime/RealtimeProvider.tsx:11（ENDPOINT）。`fetch` + ReadableStream（EventSource は Authorization ヘッダーを付けられないため。frontend/src/hooks/useSSE.ts:3）。購読は frontend/src/hooks/useRealtimeRefresh.ts:15（`useRealtimeRefresh(topics, reload)`、まとめ時間 1500ms。:13）。topic 定数 frontend/src/lib/realtime/topics.ts。
  - 古い通り道（別 SSE）: `/api/v1/conversations/stream`（frontend/src/components/DesktopShell.tsx:138, frontend/src/components/MobileShell.tsx:108）、`/api/v1/leads/stream`（frontend/src/pages/leads/LeadsPage.tsx:185）。
  - 合図は topic と origin だけでデータを持たない（docs/adr/ADR-1016-realtime-change-signal-standard.md:16）。
  - /auth/ 配下は SSE の書き込み合図の対象外か: viewer のログインは対象外の理由が明記（backend/app/realtime/topics.py:103）。/api/v1/auth/ の各 POST の扱いは backend/app/realtime/topics.py を全部読んでいないため未確認。
- (2) メールを送る仕組み
  - ログイン関連: backend/app/services/auth_mail.py（`smtplib` + STARTTLS。backend/app/services/auth_mail.py:110）。関数: `send_password_reset_email` :120、`send_invite_email` :125、`send_viewer_password_reset_email` :130。送信部 `_send_reset_mail`（backend/app/services/auth_mail.py:97）。同期関数で BackgroundTasks から呼ぶ（backend/app/routers/auth.py:160 に invite の例）。例外は握りつぶしてログに型名だけ出す（backend/app/services/auth_mail.py:115-116）。宛先は `t***@domain` のように伏せてログへ（`_mask_addr` backend/app/services/auth_mail.py:89）。
  - 設定の読み口: backend/app/services/mail_config.py（SMTP_* と MAIL_FROM。`smtp_settings()` は未設定なら None を返し送信を飛ばす。backend/app/services/auth_mail.py:100-102）。
  - 他のメール: backend/app/services/email_sender.py:58（データ削除の通知）、backend/app/services/po_mailer.py、ops_mail_notifier.py、review_mail_notifier.py。
  - メール本文は日本語・英語の併記（backend/app/services/auth_mail.py:19-35）。
- (3) service worker・manifest・web push
  - `git ls-files` を `service-?worker|sw\.(js|ts)|manifest|workbox|vite-plugin-pwa|webpush|web_push` で検索 → frontend/ 配下に該当なし（docs 配下の証拠 JSON のみ）。
  - frontend/package.json・backend/requirements*.txt を `pwa|workbox|web-push|pywebpush` で grep → 0件。
  - frontend/index.html は `apple-touch-icon` のみ（frontend/index.html:6）。manifest 参照・serviceWorker 登録なし（frontend/src/main.tsx も grep 0件）。frontend/vite.config.ts:19 の「manifest」はビルドの manifest で PWA ではない。
  - frontend/public/: apple-touch-icon.png・brand-icons・favicon.png・favicon.svg・images・logo.png・og-image.png・templates のみ。
  - docs/handoff/admin-2fa/recon.md §6 にも「serviceWorker・pywebpush・VAPID・PushManager・webmanifest の grep 0件」とある（過去の調査の引用）。
- 画面に出る小さな知らせの部品: frontend/src/components/loading/Toast.tsx、frontend/src/components/AppUpdateNotice.tsx、frontend/src/components/Callout.tsx。
- 利用者単位の知らせを置く DB: frontend/src/pages/notifications/ と backend/app/routers/notifications.py があるが、中身は今回読んでいない（下の未確認）。

### 【未確認】
- backend/app/routers/notifications.py と frontend/src/pages/notifications/ が何を扱うか（受信箱用の通知か、利用者向けのお知らせか）。ファイル名の存在のみ確認。
- SSE の接続がログイン後いつ開くか（RealtimeProvider をどこでマウントしているか）。frontend/src/lib/realtime/RealtimeProvider.tsx の本体のみ冒頭40行を読んだ。ログイン待ちの画面（まだトークンが無い状態）で SSE が張れないのは `hasSession`/`getAccessToken` を使う構造から明らかだが、確認の試験はしていない。

---

## H. 画面の部品

### 【事実】
- ログイン画面: frontend/src/pages/login/LoginPage.tsx（290行）。
  - 状態: email・password・error・loading・mode（"signIn" か reset）・resetSent・enrolling・promptOpen・promptBusy（frontend/src/pages/login/LoginPage.tsx:34-43）。`useAuth()` から signIn・signInWithPasskey・sendPasswordReset・user・loading（:44）。
  - ログイン後の自動遷移: `user` が入ると navigate（:54, :56）。パスキー登録の勧め（Modal）を挟む流れ（:57-100）。パスキーのログイン `handlePasskeySignIn` :129-141。
  - 金型: Button・Modal・Stack・TextFieldControl・PasswordFieldControl・TextLink（frontend/src/pages/login/LoginPage.tsx:18-23）。パスワード用 `<form onSubmit={handleSignIn}>` :189、パスキーのボタン :222-233、再設定の form :246、パスキー勧めの Modal :273-286。
  - エラー文言: `authErrorMessage`（frontend/src/lib/auth/authErrorMessage.ts）。
  - テスト: frontend/src/pages/login/LoginPage.test.tsx。
- アカウント設定: frontend/src/pages/account-settings/。ルート frontend/src/App.tsx:284（`/account/settings`）。
  - AccountSettingsPage.tsx（17行）が ProfileSection・PreferencesSection・SecuritySection を縦に並べる（frontend/src/pages/account-settings/AccountSettingsPage.tsx:11-13）。外枠 PageLayout（:1）。
  - SecuritySection.tsx（142行）: パスワード変更フォーム（`api.post("/auth/password/change")` :46）。末尾付近で PasskeySection を読む（import :18）。
  - PasskeySection.tsx（175行）: 一覧は `DataTable`（import :11）、取得 `api.get("/auth/passkeys")` :35、削除 `api.delete("/auth/passkeys/" + id)` :75、削除ボタンは `Button variant="danger" size="sm"` :109、確認の小窓は `ConfirmModal` :163、名前入力は `TextFieldControl`。
  - ログインした場所・機械の一覧、セッションの一覧、「ほかをログアウト」に当たる画面・口: 無い。
  - 試験: frontend/src/pages/account-settings/SecuritySection.test.tsx・PasskeySection.test.tsx。
  - Storybook: frontend/src/pages/account-settings/AccountSettings.stories.tsx。
- 部品（frontend/src/components/ 直下。`.tsx` の金型）: Button.tsx・ButtonLink.tsx・Modal.tsx・ConfirmModal.tsx・DataTable.tsx・Drawer.tsx・Sheet.tsx・Callout.tsx・Card.tsx・Badge.tsx・EmptyState.tsx・ListRow.tsx・TextField.tsx・PasswordField.tsx・Textarea.tsx・Select.tsx・Toggle.tsx・Checkbox.tsx・Radio.tsx・ChoiceCardGroup.tsx・Tabs.tsx・Stack.tsx・TextLink.tsx・Tooltip.tsx・Popover.tsx・PageLayout.tsx。小さな表示: frontend/src/components/loading/ に LoadingBlock・Toast・Spinner・Skeleton・SaveIndicator・ProgressBar など。
  - 無いもの: QR コード、数字を選ぶ部品、6桁入力欄（`ls frontend/src/components/*Qr*` はヒットなし。他は名前を確認）。ADR-1048 は QR 金型の新設に PO 許可済みと書く（docs/adr/ADR-1048-admin-two-step-login.md:6）。
- UI ガバナンス（docs/CC_UI_GOVERNANCE.md、64行）の要点
  - 部品を作る前に frontend/src/components/ に金型があるか確認し、あれば必ず使う。無ければ作らず止めて報告（PO 許可を得てから金型を登録）。docs/CC_UI_GOVERNANCE.md:9-17。金型の作法は `Xxx.tsx` + `Xxx.css`（var() のみ）+ `Xxx.stories.tsx`。
  - 禁止（CI が赤）: 生 select／生 input（text・checkbox・radio）／読み込み中の文字だけの表示（LoadingBlock を使う）／ボタンの言葉を保存中に入れ替える（Button の loading を使う）／自作タブ／色の直値／生 px のインラインスタイル。docs/CC_UI_GOVERNANCE.md:21-33。
  - どうしても必要なら `{/* ui-allow: <理由> (#<課題番号>) */}`。新規 ui-allow は人間のレビュー必須。docs/CC_UI_GOVERNANCE.md:35-52。
  - CI: scripts/check-ui-governance.js、.github/workflows/ui-governance-gate.yml。
  - 本文: docs/adr/ADR-144-ui-component-governance.md。
- i18n（ADR-027）
  - 設定: frontend/src/i18n.ts。ファイル: frontend/src/locales/ja.json・frontend/src/locales/en.json（閲覧ページ用は frontend/src/locales/viewer/ja.json・en.json で別）。
  - auth 関係のキーの並び（ja.json、en.json とも同じ行番号に先頭がある）
    - `login`（frontend/src/locales/ja.json:674、en.json:674）: email・password・signIn・forgotPassword・resetPassword・sendResetEmail・resetEmailSent・backToLogin・signInWithPasskey・passkeyPromptTitle・passkeyPromptBody・passkeyPromptRegister・passkeyPromptSkip。
    - `authError`（frontend/src/locales/ja.json:689、en.json:689）: invalidCredentials・forbiddenOrigin・unavailable・tooManyAttempts・resetLinkInvalid・currentPasswordWrong・passwordTooShort・passwordTooLong・passwordTooCommon・validation・default・passkeyFailed・passkeyExpired・passkeyCancelled・passkeyExists・passkeyLimit。
    - `accountSettings`（frontend/src/locales/ja.json:3193、en.json:3193）: subtitle・sectionProfile・sectionSecurity・…・changePassword 系・passkey 系（passkeyTitle・passkeyDescription・passkeyLabel・passkeyAdd・passkeyAdded・passkeyCol*・passkeyUnnamed・passkeyNeverUsed・passkeyEmpty・passkeyDelete*・passkeyUnsupported）・sectionPreferences・avatar 系。
  - バックエンドのエラーは `detail` に英語の記号（`invalid_credentials` など）を返し、画面が `authError.*` に対応づける（backend/app/routers/auth.py:276-280, :318-319 と frontend/src/lib/auth/authErrorMessage.ts）。

### 【未確認】
- DataTable・ConfirmModal・Modal の props の細部（今回は import と使い方の行だけ確認）。
- en.json の auth 系キーが ja.json と完全に同じ並びか（行番号の先頭が一致することのみ確認）。
- frontend/src/lib/auth/authErrorMessage.ts の中身（呼び出しは確認、本体は未読）。

---

## I. 守りの今

### 【事実】
- ログイン失敗の回数制限は2種類ある。
  - 口座単位: `users.failed_login_count`、上限 10 回（`LOGIN_FAIL_LIMIT` backend/app/auth/self_tokens.py:29）、停止 15 分（`LOGIN_LOCK_DURATION` backend/app/auth/self_tokens.py:30）。数える関数 `_count_login_failure` backend/app/routers/auth.py:283-304。ログインの冒頭で停止期限を確認 backend/app/routers/auth.py:335-339。
  - IP 単位（Redis）: 失敗 10 回で 15 分ロック（`AUTH_FAIL_MAX=10`・`AUTH_FAIL_LOCKOUT_TTL=900` backend/app/cache.py:307-308）。確認 `check_auth_rate_limit` backend/app/cache.py:311、記録 `record_auth_failure` backend/app/cache.py:328。Redis が使えないと fail-open（backend/app/cache.py:315-316, :323-325）。使う所: backend/app/routers/auth.py:318, :482, :569, :894, :912、backend/app/auth/dependencies.py:145 付近。
  - nginx 側: 認証 API は 1IP あたり毎分10回・burst 5（nginx/nginx.conf:6, :145）。閲覧者のログイン等にも同じ制限（nginx/nginx.conf:100, :115, :130）。
- パスワード変更の口: `POST /auth/password/change`（backend/app/routers/auth.py:553-680）。失敗を数える `_count_login_failure` を共用（コメント backend/app/routers/auth.py:283）。成功でその人の更新トークンを全部失効し、今の端末にだけ新しい更新トークンを出す（backend/app/routers/auth.py:611-616, :630）。照合失敗は 400（401 ではない）。
- パスワード再設定: `POST /auth/password-reset/request` backend/app/routers/auth.py:431、`/confirm` :473。確認で更新トークンを全部失効 backend/app/routers/auth.py:524-529。
- viewer（閲覧ページ）の別ログイン
  - 別の道。`POST /api/v1/viewer/login`（backend/app/routers/viewer.py:153）。別のトークン `create_viewer_access_token`（backend/app/auth/viewer_tokens.py:35、有効 12 時間 :16）。受け側 `get_current_viewer`（backend/app/auth/viewer_dependencies.py:59）。表は viewer_accounts・viewer_login_events（migrations/20261016_150000_add_viewer_accounts.sql）。
  - **自社ログインの更新トークン表・Cookie・`_issue_session_tokens` は使わない**（backend/app/routers/viewer.py の import は auth_refresh_tokens を含まない。viewer_dependencies.py は viewer_tokens と cache だけ）。
  - 同じ部品を使う所: IP 単位の失敗制限（`check_auth_rate_limit`・`record_auth_failure` backend/app/routers/viewer.py:41-45, :163, :213）、メール単位の制限（backend/app/routers/viewer.py:99-140）、パスワード方針 `check_password`（backend/app/routers/viewer.py:24）、ログアウトのブラックリスト（backend/app/auth/viewer_dependencies.py:20, :65）。
  - nginx は別の location（nginx/nginx.conf:99, :114, :129）。viewer のログインは SSE 合図の対象外（backend/app/realtime/topics.py:103）。
  - 自社の `/api/v1/auth/` に viewer のログインが入ってくるか: 入らない（パスが `/api/v1/viewer/`）。ただし audit ミドルウェアの `_AUTH_PATHS` は `/api/v1/auth/` だけなので、viewer のログインは 401/403 のときだけ auth_events に載り、成功は載らない（backend/app/middleware/audit.py:37, :184-185 から読み取り。実データでは未確認）。

### 【未確認】
- viewer の「ほかの機械をログアウト」などの有無（今回は viewer.py の `@router` 一覧と import のみ）。
- Redis 不通時の fail-open が本番でどう働くか（本番に接続しないため）。

---

## J. DB の変え方

### 【事実】
- migration の置き場: リポジトリ直下 migrations/。命名 `migrations/YYYYMMDD_HHMMSS_description.sql`（backend/AGENTS.md「Migration 適用経路」。連番は禁止で CI が強制）。例: migrations/20261013_160000_add_self_hosted_auth_tables.sql。
- 登録の決まり（2か所に書かれていて食い違いがある）
  - backend/AGENTS.md は「`.github/workflows/deploy.yml` の『新しいマイグレーションはここに追加』コメント直前に psql 実行ステップを追記」と書く。
  - 実際の deploy.yml は `.github/workflows/deploy.yml:228` で「新マイグレーション追加時は deploy.yml ではなく run_all_migrations.sh に追記する」と書き、`.github/workflows/deploy.yml:232` のステップ2は scripts/run_all_migrations.sh を呼ぶだけ。
  - 現行の登録の仕方: `scripts/run_all_migrations.sh` の末尾側に `run_sql migrations/<ファイル名>` を追記。例 scripts/run_all_migrations.sh:1131-1132（自社ログインの表）。`run_sql` の定義 scripts/run_all_migrations.sh:110。lock_timeout とリトライの仕組みあり（scripts/run_all_migrations.sh:118-135）。
  - CI の検査: `.github/workflows/migration-guard.yml:119` が、deploy.yml または run_all_migrations.sh のどちらかに登録されているか確かめる（:131-135）。未登録なら PR が止まる。同ファイルのチェック4（`REFERENCES public.X` の許可リスト）の PUBLIC_TABLES 一覧は .github/workflows/migration-guard.yml:224（新しい public 表を足すときはここも更新する、とコメントがある。.github/workflows/migration-guard.yml:218-221）。auth_events はこの一覧に入っている。auth_refresh_tokens・webauthn_credentials・password_reset_tokens がこの一覧にあるかは目視していない。
  - migrations/ を含む PR は PO の「GO #PR番号」まで main にマージしない（AGENTS.md「ブランチと作業場所」）。
  - deploy.yml は migrations/** や scripts/run_all_migrations.sh が変わったときだけ DB 移行を走らせる（.github/workflows/deploy.yml:57-61 のフィルタ）。
- 追加専用の決まり: カラム削除・表削除・型変更は原則禁止（backend/AGENTS.md「Migration は additive-only」）。新テーブルは全列に `COMMENT ON COLUMN`（backend/AGENTS.md「書き方の決まり」）。`{schema}` プレースホルダ禁止（backend/AGENTS.md）。全テナントへ足すときは `DO $$ ... pg_namespace` 走査形式（参考 migrations/090_add_lead_contact_links.sql）。
- 毎デプロイで全 migration をやり直す: ADR-1013 の記述 docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:25（`scripts/run_all_migrations.sh` は登録済み migration を全件やり直す）。冪等（IF NOT EXISTS）で書く必要がある。
- テナントの表か public の表かの決まり
  - ADR-072（docs/adr/ADR-072-tenant-schema-prefix-enforcement.md、状態 Proposed v2。docs/adr/ADR-072-tenant-schema-prefix-enforcement.md:4）は「テナントのスキーマ内の表を書く方法（schema 修飾か `reset_tenant_context()`）」の決まりで、**表を tenant にするか public にするかを決める ADR ではない**。要点: 既定は案B＝書き込み後 `await db.commit()` の直後に `reset_tenant_context()`（docs/adr/ADR-072-tenant-schema-prefix-enforcement.md:87）、tenant と public を同一クエリで JOIN するなら案A＝schema 修飾（docs/adr/ADR-072-tenant-schema-prefix-enforcement.md:88）。CI の検査（docs/adr/ADR-072-tenant-schema-prefix-enforcement.md:105-106）。backend/AGENTS.md の「ADR-072 write endpoint」も同じ。
  - 認証系の表は public に置き、人の正本 public.users.id にぶら下げる決まり: docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:23。ADR-1048 も新しい子表を public に置く（docs/adr/ADR-1048-admin-two-step-login.md:20）。人の正本は public.users: docs/adr/ADR-1008-person-ssot-users-id.md（名前のみ確認）。
  - public の機微表への RLS: ADR-1018 の対象に認証系が入る（docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:15）。docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:26-27「段階③: 認証系5表。案C＝書込・削除だけ DB で止め、読取は全行可のまま」。自社ログイン表は RLS を付けない（migrations/20261013_160000_add_self_hosted_auth_tables.sql:3）。
  - アプリ用ロールへの GRANT: migrations/20261013_160000_add_self_hosted_auth_tables.sql:95-98（`salesanchor_app` ロールが存在すれば付与）。
  - 会社別の audit_logs は tenant スキーマ（`tenant_{id:03d}.audit_logs`。backend/app/services/audit.py:303, :313）、auth_events は public（migrations/001_create_auth_events.sql:6）。
- ORM に載せない理由: 新しい public 表を models.py に載せると migration-guard チェック1が走り deploy.yml/run_all への追記を求める（backend/app/auth/self_tokens.py:3-5 のコメント、.github/workflows/migration-guard.yml:9, :17）。

### 【未確認】
- migration-guard の PUBLIC_TABLES 一覧（.github/workflows/migration-guard.yml:224）に auth_refresh_tokens 等が含まれるか（auth_events は含まれると読めた。他は目視していない）。

---

## K. 試験（backend/tests の認証関係）

### 【事実】
- 自社ログイン・トークン: backend/tests/test_self_auth.py、backend/tests/test_password_reset.py、backend/tests/test_password_policy.py、backend/tests/test_password_gen.py、backend/tests/test_issue_initial_passwords.py。
- パスキー: backend/tests/test_passkeys.py、backend/tests/test_passkey_login_enroll.py、backend/tests/test_rls_passkey_enroll_skips.py。
- 監査・記録: backend/tests/test_auth_audit_helper.py、backend/tests/test_rls_auth_audit.py、backend/tests/test_get_access_audit.py、backend/tests/test_audit_medium.py、backend/tests/test_audit_goals_carrier.py、backend/tests/test_audit_subtable_diff.py、backend/tests/test_data_deletion_helpers.py（purge_auth_events: 522-534）。
- 認証のその他: backend/tests/test_smoke_auth_least_privilege.py、backend/tests/test_meta_inbox_auth.py。
- 閲覧ページ: backend/tests/test_viewer_api.py、test_viewer_signup.py、test_viewer_password.py、test_viewer_tokens.py、test_viewer_isolation.py、test_super_admin_viewers.py ほか test_viewer_*.py。
- 即時反映: backend/tests/test_realtime_events.py、test_realtime_middleware.py、test_realtime_state_share.py、test_realtime_topics.py。
- メール: backend/tests/test_mail_config.py、test_email_tasks.py、test_po_mailer.py、test_ops_mail_notifier.py、test_review_mail_notifier.py。
- 試験用 DB: backend/tests/conftest.py は SQLite。`public.auth_refresh_tokens` を SQLite 用に書き換える処理が backend/tests/conftest.py:320-321、表の定義が :1341-1343。
- frontend 側の関連試験: frontend/src/pages/login/LoginPage.test.tsx、frontend/src/pages/account-settings/SecuritySection.test.tsx・PasskeySection.test.tsx、frontend/src/lib/realtime/RealtimeProvider.test.tsx、frontend/src/hooks/useRealtimeRefresh.test.tsx。

### 【未確認】
- 上のファイルが現在 CI で通っているか（実行していない）。
- `auth` を名前に含まない認証関連の試験が他にあるか（`ls backend/tests | grep -i -E "auth|passkey|token|login|password|webauthn|viewer|session|rate|audit|realtime|mail"` に出たものを列挙。それ以外は探していない）。

---

## 補足: 数えると要点になる事実（解釈は書かない）

- 機械を表す印は、今のコードのどこにも作られていない（D）。
- ログイン成功・失敗を「誰が」付きで残す表は、自社のパスワードログインについては無い。auth_events は利用者の列を持たず（E）、`_record_auth_audit` はパスワードログインから呼ばれていない（E）。
- 更新トークンの全失効は2か所に UPDATE が直書きされ、関数として切り出されていない。アクセストークンは人単位では失効できない（C）。
- 人単位の SSE 宛先・web push・service worker・manifest は無い。メールは SMTP で送る部品がある（G）。
- ADR-1048（管理者の2段階と新しい機器の承認）は Proposed で、実装は無い（A）。
