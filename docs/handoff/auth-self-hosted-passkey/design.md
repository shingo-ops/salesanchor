---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — auth-self-hosted-passkey

> この文書は何か：ログインの判定を Firebase から自社サーバーへ移し、顔・指紋（パスキー）でもログインできるようにするための作り方です。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)

**対象ADR**: ADR-1013（本テーマ・起案中。ADR-138 を覆す）、ADR-1008（人の正本＝public.users.id・不変）、ADR-1007（migration は構造のみ・1回実行）、ADR-127（認証失敗ロックの順序・維持）、ADR-136（危険PRのGO・不変）、ADR-144（UIガバナンス・不変）  
**recon**: [docs/handoff/auth-self-hosted-passkey/recon.md](recon.md)  
**KGI**: [docs/specs/auth-login/kgi.md](../../specs/auth-login/kgi.md)  
**日付**: 2026-10-13  
**担当**: 設計パートナー（Opus）。設計相談は Fable（§10）  
**状態**: 設計審査済み（Fable 審査 2：REVISE 限定 → 指摘を全て反映・再審査不要の判定）。PO 承認済み（2026-10-13 チャット「y」）。実装未着手（便1 以降は実装カードと PO の実装承認を経る）

---

## 1. 全体像（変更前 → 変更後）

**変更前**（recon）:

```
ブラウザ ──メール＋パスワード──▶ Firebase（Google）
   │  Firebase の ID トークン（1時間）
   ▼
API（get_current_user）── Firebase で署名を確認 ── email で public.users を引く
パスワード再設定メール: Firebase が送る
```

**変更後**:

```
ブラウザ ──メール＋パスワード／パスキー──▶ 自社 API /api/v1/auth/*
   │  ① アクセストークン（自社署名の JWT・15分・画面のメモリだけに保持）
   │  ② 更新用トークン（ランダム値・httpOnly Cookie・30日・DB にはハッシュだけ）
   ▼
API（get_current_user）── 自社の鍵で署名を確認 ── sub（users.id）で public.users を引く
パスワード再設定メール: 自社サーバーが salesanchor.jp のアドレスから送る
ログイン情報の置き場: public.users（パスワードの暗号化データ）と、users.id にぶら下がる表だけ
```

- 画面と API は同じ場所（`https://app.salesanchor.jp/api/v1`。recon P10）なので、Cookie は同一サイトで済む（別ドメインへの Cookie 送信は起きない）。
- 移行の切替日まで、Firebase のログインは今のまま動く（§6 便4 で切替）。

## 2. データ（SSOT：人の正本 public.users.id にだけぶら下げる）

migration は構造のみ・1回実行（ADR-1007）。値の投入は migration で行わない。

| 置き場 | 列／表 | 内容 | 理由 |
|---|---|---|---|
| public.users（列追加） | `password_argon2_hash` TEXT NULL | Argon2id の文字列（`$argon2id$v=19$m=19456,t=2,p=1$...`） | OWASP 第一選択（recon 公式仕様）。NULL＝パスワード未設定 |
| 同 | `password_changed_at` TIMESTAMPTZ NULL | 最後に変えた時刻 | 変更後に古い更新用トークンを無効にする基準 |
| 同 | `failed_login_count` INT NOT NULL DEFAULT 0・`locked_until` TIMESTAMPTZ NULL | 口座単位の失敗回数と停止期限 | OWASP「IP でなく口座単位」。NIST「100 回以下で止める」 |
| public.webauthn_credentials（新表） | `id` BIGSERIAL PK、`user_id` FK users.id ON DELETE CASCADE、`credential_id` BYTEA UNIQUE（≤1023）、`public_key` BYTEA、`sign_count` BIGINT、`transports` TEXT[]、`backup_eligible` BOOL、`backup_state` BOOL、`aaguid` UUID、`label` TEXT、`created_at`、`last_used_at` | パスキー（公開鍵だけ。顔・指紋そのものは端末から出ない） | W3C の保存すべき値（recon 公式仕様） |
| public.password_reset_tokens（新表） | `id`、`user_id` FK、`purpose` TEXT（`reset`＝再設定・期限 30 分／`invite`＝新規ユーザーの初回設定・期限 72 時間）、`token_hash` BYTEA UNIQUE（sha256）、`expires_at`、`used_at`、`created_at` | 再設定リンクと初回設定リンクの使い捨て鍵（ハッシュだけ保存。1 つの表で両方を扱い、表を増やさない） | OWASP Forgot Password |
| public.auth_refresh_tokens（新表） | `id`、`user_id` FK、`token_hash` BYTEA UNIQUE、`family_id` UUID、`family_created_at` TIMESTAMPTZ、`expires_at`、`revoked_at`、`created_at`、`last_used_at`、`user_agent_hash` | 更新用トークン（使うたびに入れ替え、使い回しを検知したら同じ family を全部失効）。期限は family の作成から**絶対 30 日**（入れ替えても延びない）。`user_agent_hash` は記録と検知だけに使い、拒否には使わない | OWASP Session Management（絶対期限） |

- 列名を password_hash にしない理由（2026-10-13 便1 調査で判明）: `scripts/run_all_migrations.sh` は毎デプロイ登録済み migration を全件やり直し、409 行目で `migrations/20260612_150000_drop_password_hash.sql`（DROP COLUMN IF EXISTS password_hash）が毎回走る。同じ名前の列は毎デプロイ消えるため、password_argon2_hash を使う。
- 人の名簿は増やさない。上の新表はすべて `users.id` の子で、メールアドレスも持たない（メールは users.email の 1 か所）。
- `staff.firebase_uid` は本テーマでは触らない（ADR-1008 の P4 で削除予定）。
- Firebase にだけいる 3 人（recon P12）は移行しない（users に行が無いため）。便6 の Firebase 片付けで消える。

## 3. API（すべて /api/v1/auth/ 配下・認証前の口はレート制限つき）

**共通の守り（審査 HIGH-1）**: `backend/app/main.py:208` の CORS は `https://salesanchor.jp`（LP）と `https://jarvis-claude.uk` も credentials 付きで許可している。SameSite=Strict は同じ登録可能ドメイン（salesanchor.jp）からの呼び出しを止めない。そのため、/api/v1/auth/ の POST はすべて `Origin` ヘッダが `AUTH_RP_ORIGIN`（本番 `https://app.salesanchor.jp`）と一致しなければ 403 にする。auth API は `nginx/nginx.conf` の api.salesanchor.jp 側からも届くが、更新用 Cookie は app.salesanchor.jp に限られ api 側には送られないため、refresh は成立しない。

| 口 | 入力 | 動き | 守ること |
|---|---|---|---|
| POST `login` | email・password | email を小文字にして users を引く → `is_active` → `locked_until` → Argon2id 照合。成功でアクセストークン（本文）＋更新用 Cookie、`failed_login_count` を 0 に、`last_login` を更新。失敗で `failed_login_count`+1、10 回で 15 分停止 | 失敗理由は区別しない 1 つの文言。存在しない email・停止中・`is_active=false` でも、ダミーのハッシュ照合を必ず通して同じ時間にする |
| POST `refresh` | 更新用 Cookie | ハッシュで照合 → 入れ替え（古いものは失効。新しいものの期限は family の絶対期限を引き継ぐ）。失効済みが使われたら同じ family を全部失効 | Cookie は `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth`。Origin 照合 |
| POST `logout` | Cookie＋Bearer | 更新用を失効、アクセストークンは既存のブラックリスト（`backend/app/cache.py:155`）へ | 既存の仕組みを流用。Origin 照合 |
| POST `password-reset/request` | email | 使用中のユーザーなら使い捨て鍵（purpose=reset）を作り、メール送信は裏で行う（FastAPI の BackgroundTasks。応答を待たせない）。いつも同じ応答「届いていればメールを確認してください」 | OWASP。回数制限は「email の小文字のハッシュ単位・1 時間 3 回」を、ユーザーの有無に関係なく同じに数える（429 の有無で存在が分からないように） |
| POST `password-reset/confirm` | 鍵・新パスワード | 鍵のハッシュ照合・期限・未使用 → パスワード更新・`password_changed_at`・`used_at`・その人の更新用トークンを全失効・停止解除。自動ログインはしない | OWASP。purpose=invite の鍵もこの口で使う |
| POST `password/change` | 今のパスワード・新パスワード（ログイン中） | 照合して更新・`password_changed_at`・他の端末の更新用トークンを失効 | 画面 `frontend/src/pages/account-settings/SecuritySection.tsx` の置き換え先 |
| POST `passkey/register/options`・`passkey/register/verify` | ログイン中 | py_webauthn で登録。`userVerification=required`、`residentKey=required`。user handle（`user.id`）は users.id を 8 バイトの固定長にしたもの（メール等の個人情報は入れない） | 顔・指紋の確認を必須にする |
| POST `passkey/login/options`・`passkey/login/verify` | なし（端末が候補を出す） | options は challenge と、それを引くための使い捨て ID を返す（challenge は Redis に 5 分・1 回限り、鍵はその ID）。verify は ID で challenge を取り出して消し、`userVerification=required` で照合。成功でアクセストークン＋更新用 Cookie（login と同じ発行処理） | `sign_count`: 保存値と新値がどちらも 0 なら許可（同期型パスキーは 0 のまま）。保存値が 0 より大きく、新値が保存値以下なら拒否し、監査記録に残す（複製の疑い） |
| GET/DELETE `passkeys` | ログイン中 | 自分のパスキーの一覧・削除 | 他人のものは触れない |
| POST `register`（既存 `backend/app/routers/auth.py:43` を置き換え・super admin 専用のまま） | email・氏名・テナント・ロール | users を `password_argon2_hash` NULL で作り、purpose=invite の鍵を作って「初回設定メール」を送る（`AUTH_PROVIDER=self` のときだけ。firebase の間は users の行だけ作り、鍵もメールも作らない）。メールのリンクは再設定ページと同じ。担当者の追加（`POST /api/v1/staff`）で新しく利用者ができたときも同じ初回設定メールを送る（既存の利用者を足したときは送らない） | 審査 HIGH-2。Firebase 撤去後に新しい人を作る経路。表は増やさない |

### パスキーの RP ID（登録したパスキーが結びつくドメイン）
- **RP ID = app.salesanchor.jp、確認するオリジン = https://app.salesanchor.jp**（PO 2026-10-13「y」・審査 HIGH-4）。ログインする場所はアプリの画面だけなので範囲を最小にする。後から変えると、登録済みのパスキーが全部使えなくなる。
- 値は環境変数 `AUTH_RP_ID`・`AUTH_RP_ORIGIN` で持つ。ローカル開発は AUTH_RP_ID=localhost・AUTH_RP_ORIGIN=http://localhost:5173（ポートは実際の開発サーバーに合わせる）。Cookie の Secure 属性は環境変数 `AUTH_COOKIE_SECURE`（既定 true。ローカル開発だけ false）で切り替える。

### パスワードの決まり（NIST SP 800-63B-4・recon 公式仕様）
- 長さ 15 文字以上・64 文字以下（今回はパスワード単独でもログインできるため、単独要素の基準 15 文字を使う）。文字の種類の混在は求めない。定期変更は求めない。
- よく使われる・漏れたパスワードの一覧に載っているものは拒否する（大文字小文字を区別しない）。外部サービスへは問い合わせない。一覧の実体（審査 2 MEDIUM-C）:
  - 出典: SecLists の Passwords/Common-Credentials/100k-most-used-passwords-NCSC.txt（https://github.com/danielmiessler/SecLists ・MIT ライセンス・2026-10-13 に公開元で確認）
  - 件数: 約 10 万件（ファイル名どおり。実数は取り込み時に `wc -l` で記録）
  - 置き場: backend/app/auth/data/common-passwords.txt（新設）。同じフォルダの README.md に、出典 URL・取り込んだコミット SHA・件数・ライセンスを書く
  - 大きさの上限: 2 MB（超えたら取り込まず設計者へ戻す）
  - 読み込み: 起動時に 1 回、小文字の集合としてメモリに置く
  - 更新: 自動更新しない。更新するときは同じ手順で取り込み、PR で差し替える
- 発行するパスワードは、ランダム 20 文字（英大小・数字。見間違えやすい文字を除く）。

### トークン
- アクセストークン: JWS（HS256・`python-jose`）。中身は `iss=salesanchor`・`sub=users.id`・`email`・`jti`・`iat`・`exp`（15 分）・`amr`（`pwd` か `webauthn`）。ヘッダに `kid`。
- 鍵の入れ替え（審査 MEDIUM-4）: 本番 .env に `AUTH_JWT_SECRET`（今の鍵）と `AUTH_JWT_SECRET_PREVIOUS`（前の鍵・入れ替え後 15 分だけ置く）。署名は今の鍵だけで行い、確認は `kid` で両方を受ける。手順: 新しい鍵を `AUTH_JWT_SECRET` に、古い鍵を `_PREVIOUS` に入れてデプロイ → 15 分後に `_PREVIOUS` を空にしてデプロイ。
- 秘密が未設定のとき（審査 HIGH-3）: `AUTH_PROVIDER=firebase` なら自社の発行経路を無効にして通常どおり起動する。`AUTH_PROVIDER=self` なのに秘密が無ければ起動を止める（設定漏れを本番で気づかずに動かさない）。
- 無効にする「発行経路」は、`login`・`refresh`・`passkey/login/*` の 3 系統だけ（審査 2 MEDIUM-B）。`password-reset/*`・`register`・`password/change` は、`AUTH_PROVIDER` と秘密の有無に関係なく動く（便3 で再設定メールを本番で試すため）。
- `email` を入れるのは、署名を確かめずに中身を読む 3 か所（`backend/app/middleware/audit.py:50`・`backend/app/middleware/rate_limit.py:39`・`backend/app/middleware/session_guard.py:45`）を今のまま動かすため。この 3 か所の作り直しは本テーマの外（ADR-127 の「別件」のまま）。既知の弱点（偽の JWT で rate_limit の「認証済み」枠に入れる・session_guard の追跡がトークン 15 分ごとに切れる）も、そのまま引き継ぐ。
- 既存の JWT キャッシュ・ブラックリスト・IP ロックは `sha256(token)` が鍵なので、そのまま使う（recon `backend/app/cache.py:14`）。
- パスワードの変更・再設定の後（審査 MEDIUM-5）: §4 ④ で `iat` が `password_changed_at` より前のトークンを拒否する。ただし JWT キャッシュ（300 秒）に載っている間は ④ を通らないため、**古い端末のアクセストークンは最大 5 分生きる**。これを受け入れ基準に明記する。

## 4. `get_current_user` の変更（全 API の出口・`backend/app/auth/dependencies.py:72`）

順序は今のまま（ADR-127）。変えるのは ④ だけ:

1. SMOKE_SERVICE_TOKEN（:99-113）— **先頭のまま変えない**（FedEx smoke が使う）
2. ブラックリスト（:116）・3. JWT キャッシュ（:125。キャッシュに当たったときは今どおり `cached["email"]` で users を引く）・IP ロック（:136）— 変えない
4. 署名確認: トークンの `iss` を見て振り分ける
   - `iss=salesanchor` → 自社の鍵で確認 → `sub`（users.id）で users を引き、`is_active` を確認し、トークンの `email` と users.email が一致することも確かめる（一致しなければ 401＝メールアドレスが変わったら再ログイン）。`iat` < `password_changed_at` なら 401
   - それ以外 → 今の Firebase 確認（:144 以降）。**便6 で削除**
5. MFA 判定（:153-160）— 自社トークンでは使わない（本番は `MFA_REQUIRED=false`・recon P1）。二段階認証は次のテーマ（PO 2026-10-13「二段階認証は次の便で…任意で設定する項目」）
6. テナント決定（:194）— 変えない（DB の user.tenant_id）

切替スイッチ: 環境変数 `AUTH_PROVIDER`（`firebase`／`self`。既定 `firebase`）。画面側は同名のビルド変数 `VITE_AUTH_PROVIDER`。API の受け付けは便2〜便5 の間、両方のトークンを受ける。

## 5. 画面（金型・デザイントークン・i18n。生の部品と色の直書きは禁止）

| 画面 | 変更 | 使う金型 |
|---|---|---|
| ログイン（`frontend/src/pages/login/LoginPage.tsx`） | Firebase 呼び出しを自社 API に。「顔・指紋でログイン」ボタンを追加（端末が対応しているときだけ表示）。生 `<button>`（:115「パスワードを忘れた」・:154「ログインへ戻る」）を文字リンクの金型 `TextLink` に置き換える（login-round-inputs/design.md） | `Button`・`TextFieldControl`（既存）。`frontend/src/components/buttonAppearance.ts:1` に文字リンク風の種類は無いため、文字リンクは TextLink を使う（login-round-inputs/design.md） |
| パスワード再設定（新ページ `/reset-password?token=`） | 新パスワード 2 回入力 → confirm | `Button`・`TextFieldControl`・`Callout`（結果表示） |
| アカウント設定 セキュリティ（`frontend/src/pages/account-settings/SecuritySection.tsx`） | パスワード変更を自社 API に。パスキー一覧（名前・登録日・最後に使った日）・追加・削除 | `Button`・`TextFieldControl`・`DataTable`（`frontend/src/components/DataTable.tsx`）・`ConfirmModal`（削除確認） |
| 認証の土台（`frontend/src/contexts/AuthContext.tsx`・`frontend/src/lib/api.ts`・`frontend/src/hooks/useSSE.ts`・`frontend/src/components/ShippingDetailPanel.tsx`） | `getIdToken()` を「メモリのアクセストークン（切れていたら refresh）」に置き換え。Bearer 方式は変えない。起動時の手順: ページを開く → メモリにトークンが無い → refresh を 1 回だけ呼ぶ → 401 ならログイン画面へ。401 のときの自動 refresh は 1 回まで（`nginx/nginx.conf` の `/api/v1/auth/` は 10 回/分・burst 5 の制限があり、繰り返すとすぐ 429 になるため） | — |
| e2e の試験用の迂回（`frontend/src/lib/firebase-auth.ts` の開発時の偽ユーザーと `frontend/tests-e2e/utils/auth.ts`） | 便4 で、自社方式でも同じように迂回できる形に移す（開発ビルドのときだけ有効。本番ビルドには入らない） | — |
| 誤りの文言（`frontend/src/lib/firebaseErrorMessage.ts`） | 自社 API の誤りコード用に `frontend/src/lib/auth/authErrorMessage.ts` を新設して置き換える（firebaseErrorMessage.ts は便6 まで残す） | — |

- 新しい文言はすべて `t("key")`。ja.json と en.json に同じキー（ADR-027）。キー名は既存の `login.*`・`accountSettings.*` の下に足す。
- 上の表に無い部品が必要になったら、作らずに設計者へ戻す（金型を先に登録する判断は設計者と PO）。

## 5.5 接触面分析（6 面）

| 面 | 接触 | 対処 |
|---|---|---|
| 人 | 使用中の人（便4b の試し実行の件数。recon P3・P12 の時点は 10 人）。切替日に全員のパスワードが変わる | 発行ファイルを PO が配る（§6 便4）。切替日を事前に告知。審査用（id=10）も含む |
| エージェント | 設計・実装・確認は Sonnet／Fable。本番の書き込みは危険便の GO 後だけ | 発行スクリプトは PO の端末から実行し、平文はサーバーに残さない |
| 機械 | CI: 多数のテストは `get_current_user` を差し替えて迂回（影響小。数え方で 38〜54 ファイル。差し替えの本体は `backend/tests/conftest.py`）。`.github/workflows/qa-smoke.yml`（本番 Firebase 実ログイン・直近 5 回失敗 recon P11）と `.github/workflows/rotate-qa-firebase.yml` | 便6 で自社ログイン版に置き換え・削除 |
| データ | public.users に 4 列、新 3 表。人の名簿は増やさない | 構造だけの migration（便1）。値はアプリと発行スクリプトだけが書く |
| 本番 | backend（`docker run` の入れ替え・`scripts/blue-green-cutover.sh:80`）、nginx の CSP（`nginx/nginx.conf:82`）、.env に秘密 2 種（`AUTH_JWT_SECRET`・SMTP 資格情報）追加 | 秘密の追加は危険便で PO の GO。CSP は Firebase 撤去と同じ便で外す |
| 外部 | Firebase（便6 まで並存）、さくらのメール（SMTP 送信・送信用アドレス）、DNS（DMARC 追加・DKIM） | 外部 GUI 操作は PO（CLAUDE.md の不可逆操作リスト）。手順書を便3 のカードに付ける |

## 6. 便割り（1 便 1 テーマ・それぞれ別 PR）

危険便＝`migrations/`・`.github/workflows/deploy.yml`・`docker-compose.yml`・`nginx/`・本番 `scripts/`・`backend/scripts/`（本番コンテナに入る運用スクリプト）・secrets を含む便。ADR-136 のとおり、「GO #PR番号」が要る（GO 委任中は「POの委任に基づくClaude Opus発行」で記録）。

| 便 | テーマ | 危険 | 戻し方 | 測り方 |
|---|---|---|---|---|
| 便0 | 本設計一式・ADR-1013（docs のみ） | 無 | revert | ADR 索引の CI 緑・関所 `node scripts/check-process-artifacts.js` 緑 |
| 便1 | migration: §2 の列と表（構造のみ） | **危険** | 列と表は残してコードが使わない（削除は別便・PO GO） | 本番で `\d public.users` と新 3 表が §2 と一致。今のログインに影響なし（ログイン成功数が前日と同程度） |
| 便2 | backend: パスワード照合・トークン発行／更新／失効・口座ロック・§4 の振り分け・`AUTH_PROVIDER` スイッチ（既定 firebase）。依存追加 `argon2-cffi` | 無（コードのみ）。認証のためセキュリティ審査必須 | revert | 単体・結合テスト緑。本番では既定 firebase のため挙動不変（ログイン成功数が前日と同程度） |
| 便3 | メール: SMTP を backend に渡す（`docker-compose.yml`・`.github/workflows/deploy.yml`）、再設定 API、メール文面（ja/en）。**便3 の間は、再設定の口は環境変数 `AUTH_PASSWORD_RESET_ALLOWLIST`（試験用アドレスだけ）に載った email にしか送らない**（審査 MEDIUM-6。切替前に実ユーザーへメールが届いて混乱しないように）。画面は Firebase のままなので、K5 は試験用アドレスに対して API を直接呼んで送る。試験用アドレスは、使用中の 10 人とは別に、試験用テナント（tenant 6 `tenant-review`）に試験ユーザーとして 1 人作る（email は便3 のカードに明記。この人は K1 の対象外）。PO の GUI: さくらで送信用アドレス作成・DKIM 有効化、DNS に DMARC 追加 | **危険**（compose・deploy・secrets） | 環境変数を外せば送信停止（`backend/app/services/email_sender.py:40` が送らずログだけになる） | K5: Gmail 試験アカウントの受信箱に届き、ヘッダの SPF・DKIM・DMARC が pass |
| 便4a | 画面と API の残り（初期値は Firebase のまま・本番のログインは変わらない）: `POST /api/v1/auth/password/change`、`register` を §3 の形に置き換え、担当者の追加（`POST /api/v1/staff`）で新しく利用者ができたときも、`AUTH_PROVIDER=self` なら初回設定メールを送る（既存の利用者を足したときは送らない）、画面の自社ログイン層（ビルド変数 `VITE_AUTH_PROVIDER` が `self` のときだけ自社 API。未設定・`firebase` は今と同じ動き）、再設定ページ `/reset-password`、ログイン画面の金型化、アカウント設定のパスワード変更、誤りの文言 `frontend/src/lib/auth/authErrorMessage.ts` | 無（コードのみ）。認証のためセキュリティ審査必須 | revert（初期値が firebase なので利用者への影響は無い） | K0: マージ・deploy 後も本番のログインは今と同じ（login は 404・PO が今のパスワードでログインできる）。見た目の変化はログイン画面の 2 つのボタンが枠付きの補助ボタンになることだけ |
| 便4b | 切替: `AUTH_JWT_SECRET` を GitHub の secret に追加し、`.github/workflows/deploy.yml` と `docker-compose.yml` で backend に渡す（審査 HIGH-3）。`AUTH_PROVIDER=self`、画面は `VITE_AUTH_PROVIDER=self`（ビルド変数なので `frontend/Dockerfile` の ARG・`docker-compose.yml` の build args・`.github/workflows/deploy.yml` に追加）、`AUTH_PASSWORD_RESET_ALLOWLIST` を外す、**初回パスワード発行スクリプト backend/scripts/issue_initial_passwords.py（新設）**（審査 HIGH-5。`backend/Dockerfile` は backend/ 配下だけをイメージに入れるため、リポジトリ直下の scripts/ には置かない。id 2 も発行の対象） | **危険**（backend/scripts・deploy・compose・secrets） | 便4b は revert しない（`.env` の `AUTH_PROVIDER=self` が残り、backend が self のままになるため）。heredoc の `AUTH_PROVIDER` と `VITE_AUTH_PROVIDER` を `firebase` に変える前進 PR をマージして deploy する（消す一覧は残す。画面もビルドし直される）。Firebase のユーザーと元のパスワードは便6 まで残るので、元どおりログインできる。ただし便4b の後に新しく登録した人は Firebase にいないため、戻した状態ではログインできない（戻す前に人数を確かめる） | K1: 発行ファイルの行数＝便4b の試し実行の件数・使用中の人の last_login が切替後に更新。K4: 試験ユーザーで再設定を実演 |
| 便5 | パスキー: 登録・ログイン・一覧・削除（backend＋画面）。依存追加 `webauthn`（py_webauthn）・`@simplewebauthn/browser`。ボタンは端末がパスキーに対応しているときだけ表示（環境変数のスイッチは作らない＝compose・deploy を触らない） | 無（migration は便1 で済。compose・deploy も触らない） | revert（登録済みのパスキーの行は残るが使われない） | K2: PO の端末で顔か指紋だけでログイン（画面録画）・`webauthn_credentials` に 1 行 |
| 便6 | Firebase 撤去: `firebase-admin` と Firebase SDK の除去、§4 の Firebase 分岐削除、`backend/app/auth/utils.py`（カスタムクレーム）と `backend/app/schemas/auth.py` の `firebase_uid` の除去（審査 HIGH-2）、`nginx/nginx.conf:82` の CSP から Firebase 用の許可を外す、credentials のマウント除去（`docker-compose.yml:69` ほか）、運用スクリプト・CI・監視の置き換え（`scripts/setup_review_tenant.py`・`.github/workflows/qa-smoke.yml`・`.github/workflows/rotate-qa-firebase.yml`・`scripts/snapshot/firebase.sh`・`scripts/smoke/external-firebase.sh`・`docs/external-state-contract.yml`）、`bcrypt` の除去（`backend/requirements.txt:10`）、**Firebase の登録ユーザー削除** | **危険・不可逆**（外部 GUI／secrets） | 削除前に PO の Mac で Firebase の書き出しを暗号化して保管（便6 カードに手順） | K3: Firebase の書き出しで総数 0。ADR-032 を Superseded に |
| 次のテーマ | 二段階認証（認証アプリ）を任意設定で追加 | — | — | PO 2026-10-13 の言葉どおり別テーマで設計 |

### 便4 初回パスワード発行の手順（平文をサーバーにもリポジトリにも残さない）
1. PO の Mac で `umask 077` の後、`ssh prod1 "docker exec astro-webapp-backend-1 python -m scripts.issue_initial_passwords --apply"`（コンテナ内の作業場所は /app ＝ backend/ なので、新設する backend/scripts/issue_initial_passwords.py がこの名前で呼べる）の標準出力を、PO の Mac のファイル（例: ~/Documents/salesanchor-initial-passwords-YYYYMMDD.tsv・権限 600）へ直接書き出す。
2. スクリプトは「`is_active=true` かつ `password_argon2_hash` が NULL」の全員（PO 2026-10-13「y」・recon P3 の時点で 10 人。実際の対象者数は便4b の試し実行の件数。便3 の試験ユーザーは便3 で password_argon2_hash が入るため自然に外れる）に、ランダム 20 文字を作り Argon2id で `password_argon2_hash` に保存し、`users.id`・メール・パスワードの 3 列を標準出力に出す。サーバー側のファイル・ログには平文を書かない（ログは件数だけ）。
3. 既に `password_argon2_hash` がある人は飛ばす（2 回実行しても上書きしない）。`--apply` なしは件数だけ表示する試し実行。
4. PO が各人に伝え終えたら、ファイルを削除する（Mac の記憶装置では「上書きして完全に消す」ことは約束できないため、手順書には「削除」と「ゴミ箱に残っていないことの確認」だけを書く）。
5. 発行対象のうち id=2（テスト用アドレス）と id=10（審査用）は実在の利用者ではないため、K1 の「ログインできる」の確認は PO が発行ファイルの値で行う。

## 7. 代替案と選んだ理由（Fable の比較 §10 を要約）

| 案 | 長所 | 短所 | 判断 |
|---|---|---|---|
| A. 自社で完全に持つ（本設計） | ログイン情報が 1 か所（K3）。自社からメール（K5）。パスキーを自由に足せる | パスワード保管・メール・ロックを自前で守る責任が増える | **採用**（PO 2026-10-13） |
| B. Firebase を残し、パスキーだけ自社で確認 | 変更が小さい | パスワードは Firebase、パスキーは自社の 2 か所に分かれる＝PO の「データの分散禁止」に反する。K3・K5 を満たせない | 不採用 |
| C. Firebase のパスキー対応を待つ | 作らなくてよい | 公式の提供時期なし（recon: private preview） | 不採用 |
| D. 既存パスワードを Firebase から持ち出して移す（scrypt 互換） | 全員がパスワードを変えずに済む | Firebase の署名鍵を本番に置く必要・検証ライブラリが非公式（2023 年 1 回の公開） | 不採用（PO 2026-10-13 「y,新規パスワードを発行する」） |

## 外部・過去事例の参照と我々への応用

- 事例1: FIDO Alliance「Passkey Index」2025 年 10 月（Amazon・Google・Microsoft など 9 社の自己申告）。ログイン成功率 93%（パスキー）対 63%（その他）、ログイン時間 8.5 秒対 31.2 秒。→ 応用: 便5 の KPI の目安。ただし大企業の自己申告で、10 人規模の我々の成功の証明には使わない
- 事例2: OWASP Password Storage・Forgot Password・Session Management の各 Cheat Sheet（2026-10-13 確認・出典は recon）→ 応用: §2・§3 の Argon2id の値、再設定の使い捨て鍵、更新用トークンの入れ替え
- 事例3: NIST SP 800-63B-4（2025-07-31 Final）→ 応用: §3 の長さ 15 文字・漏洩一覧照合・定期変更なし。パスキーは単独で多要素相当（次のテーマの二段階認証を任意にする根拠の 1 つ）
- 事例4（社内の過去）: ADR-138（2026-06-12）で「使われないパスワードの保管は攻撃面を増やすだけ」と判断して削除した → 応用: 今回は照合に使うので保管する理由がある。ADR-1013 で Supersedes と明記し、保管は Argon2id とし、平文は発行時の PO の Mac だけに置く
- Firebase から自社認証へ移した、規模と数値のある公開事例は見つけていない（recon 外部調査）。成否は本テーマの KGI の実測だけで判定する

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| K1: 発行ファイルの行数＝対象者数（便4 の試し実行で表示される「is_active=true かつ password_argon2_hash が NULL」の件数。2026-10-13 時点 10 人。実際の件数は便4b の試し実行の値・便3 の試験ユーザーは含まない）、対象者全員が新パスワードでログインできる | 便4 実施後、ファイル行数（`wc -l`、値は見ない）と、`public.users.last_login` が切替時刻より後の is_active 利用者の数（login API が成功時に last_login を更新する。`backend/app/routers/auth.py` の login が更新済み） |
| K2: パスワードを打たずに顔か指紋だけでログインできる | PO の端末で実演し画面録画。`webauthn_credentials` に PO の users.id の行が 1 行以上（件数のみ読み取り） |
| K3: Firebase の登録ユーザー 0、ログイン情報は §2 の置き場だけ | 便6 後に Firebase の書き出しで総数 0。`git grep -i firebase` が許可した例外（ADR・過去の handoff）以外 0 |
| K4: 再設定メールのリンクで新パスワードを設定してログインできる。リンクは 1 回で無効・30 分で無効 | 試験ユーザーで実演＋結合テスト（使用済み・期限切れ・別人の鍵を拒否） |
| K5: 再設定メールが Gmail の受信箱に届き、SPF・DKIM・DMARC が pass | Gmail 試験アカウントの「メッセージのソースを表示」 |
| 口座ロック: 10 回失敗で 15 分止まり、正しいパスワードでも入れない。存在しない email でも応答が同じ | 結合テスト |
| auth API の POST は Origin が `https://app.salesanchor.jp` 以外なら 403（LP `https://salesanchor.jp` からの refresh も 403） | 結合テスト（審査 HIGH-1） |
| 再設定の申込みは、ユーザーの有無で状態コード・応答本文・回数制限が同じ。メール送信は応答の後に裏で行う | 結合テスト（審査 MEDIUM-1） |
| パスワード変更後、古い端末のアクセストークンは最大 5 分で拒否され、更新用トークンは即時に失効する | 結合テスト（審査 MEDIUM-5） |
| パスキー: 新値が保存値以下（保存値 > 0）の sign_count は拒否、challenge は 1 回で消える | 単体テスト（審査 MEDIUM-3） |
| 新規ユーザー登録で初回設定メールが届き、リンクでパスワードを設定してログインできる | 試験ユーザーで実演（審査 HIGH-2） |
| 更新用トークンの使い回し検知で同じ family が全部失効 | 結合テスト |
| SMOKE_SERVICE_TOKEN の経路が今のまま動く | 既存の FedEx smoke（`scripts/smoke/external-fedex.sh`）が緑 |
| 画面に生の `<button>`・`<input>`・色の直書きが無い。文言はすべて `t()`・ja/en 同一キー | 変更した画面ファイルに `grep -nE "<button|<input|#[0-9a-fA-F]{3,6}\b|rgb\("` で 0 件（`ui-allow:` の例外コメント付きを除く）、ja/en のキー差分 0、既存の lint・CI 緑 |
| 「パスワードを忘れた」「ログインへ戻る」は文字リンク風から枠付きの補助ボタンに見た目が変わる（金型に文字リンク風の種類が無いため） | Evaluator の画面写真で PO が確認 |
| 署名を確かめず中身を読む 3 か所が自社トークンでも email を取れる | 単体テスト（自社トークンで rate_limit が「認証済み 300 回/分」側に入る） |
| 発行スクリプトがサーバーに平文を残さない | 実行後に本番の /tmp とアプリのログに平文が無いことを件数で確認（PO の端末の読み取りスクリプト） |
| 人の確認の記録 | 上の実測を `docs/ai-agents/evidence-registry.md` に記録 |

## 技術 How・KPI

- KPI-1: ログイン成功率（成功÷試行・週次。切替後 4 週）
- KPI-2: 口座ロックの件数（週次。急増したら攻撃か使い勝手の問題として調べる）
- KPI-3: パスキー登録者数／使用中ユーザー数（便5 後 4 週）
- KPI-4: 再設定メールの送信数と、そのうちリンクが使われた数

## 弊害・トレードオフ

- パスワードの暗号化データを自社で持つ（ADR-138 で減らした攻撃面が戻る）→ Argon2id・口座ロック・漏洩一覧照合で守る。DB のバックアップにも含まれる点は既存のバックアップ保護に従う
- 切替日に全員のパスワードが変わる → 事前告知と、PO による配布。困った人は再設定メールで自分で直せる（便3 が便4 より先）
- 秘密が 2 種増える（`AUTH_JWT_SECRET`・SMTP）→ 危険便（便3・便4）で PO の GO。鍵の入れ替え手順は §3「トークン」
- メールが届かないと再設定できない → 便3 で K5 を満たしてから便4 に進む
- 戻し方: 便4 までは `AUTH_PROVIDER=firebase` に戻せば元どおり。便6（Firebase 削除）だけは戻せないので最後に置き、PO の GO を取る

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| T0 | 本設計一式と ADR-1013 を docs PR で main へ（便0）。`node scripts/generate-adr-index.js` | 設計パートナー |
| T1〜T6 | 便1〜便6。各便の前に実装カードを作り、カードチェック → Sonnet が実装 → Fable がコード審査 → CI 緑 → 危険便は GO | 設計パートナー（カード・GO 確認）・Sonnet（実装）・Fable（審査） |
| PO の手作業 | 便3: さくらで送信用アドレス作成と DKIM、DNS に DMARC。便4: 発行ファイルの配布。便6: Firebase のユーザー削除の GO | PO |

## 継続

- 切替後 4 週、KPI-1〜4 を週 1 回まとめる
- 次のテーマ: 二段階認証（認証アプリ・任意設定）を設計する

## 維持の仕組み

- 守り手: 人手で守る（ログインの安全に関わる検査は、便2・便5 で作るテストが守る。ファイルはまだ無いため、各便のカードで、テストのパスをこの欄に追記する）
- 対象: ① ログイン情報が §2 の置き場以外に増えない ② 発行したパスワードの平文がサーバー・リポジトリに残らない ③ 画面の部品が金型だけ ④ SMOKE_SERVICE_TOKEN の順序が先頭のまま

---

## 10. 設計相談と審査の記録

| 回 | 相手 | 判定 | 要点 |
|---|---|---|---|
| 相談 1 | Fable（architect・同一セッションから起動した別モデル。2026-10-13） | 推奨 A（PO 希望と同じ方向）を段階化 | B は SSOT 違反、C は時期不明。dual-accept で段階移行、Firebase 削除は最後。未確認 12 項目 → PO の端末で読み取り確認し recon P1〜P13 に反映。①は scrypt 移行か初回発行かを PO 判断 → PO「新規パスワードを発行」 |
| 審査 1 | Fable（architect・同一セッションから起動した別モデル。2026-10-13） | REVISE（CRITICAL 0・HIGH 5・MEDIUM 6・LOW 多数） | HIGH-1 兄弟オリジンから refresh 可 → §3 共通の Origin 照合と基準行。HIGH-2 Firebase 撤去後の新規登録経路なし → §3 `register`（purpose=invite の鍵で初回設定メール・表は増やさない）、便6 に除去対象。HIGH-3 `AUTH_JWT_SECRET` の便が未割当 → 便4、未設定時の起動の扱いを §3。HIGH-4 RP ID 未記載 → §3 に候補と PO 判断待ちを明記。HIGH-5 発行スクリプトがイメージに入らない → `backend/scripts/`、危険便の定義に追加。MEDIUM: 列挙対策（回数制限・裏送信）、絶対期限、パスキーの UV・user handle・challenge の鍵・sign_count、鍵の入れ替え、変更後の旧トークン（最大 5 分）、便3 の送信先を試験アドレスに限定 → すべて §2・§3・便3・受け入れ基準に反映。LOW: ダミー照合の範囲・失敗回数のリセット・email の小文字化・削除の書き方・戻し方の具体化・起動時の refresh・e2e の迂回・生ボタンの grep → 反映 |
| 審査 2 | Fable（同上・2026-10-13） | REVISE（限定。審査 1 の HIGH-1〜5・MEDIUM-1〜6 は全て反映済みと判定。「示した文どおりに直せば再審査不要」） | HIGH-A 便3 の試験ユーザーで K1 の人数が崩れる → 発行対象を「is_active かつ password_hash が NULL」、試験ユーザーは別に作り K1 の対象外（kgi.md も）。MEDIUM-A 便5 のビルド変数スイッチは compose・deploy を触る → スイッチをやめ revert で戻す。便4 に frontend/Dockerfile の ARG を明記。MEDIUM-B 無効にする口を 3 系統に限定。MEDIUM-C 漏洩一覧の実体（SecLists NCSC 10 万件・MIT・置き場・上限・更新）。LOW-1 DataTable に確定。LOW-2 ローカルの RP_ORIGIN と AUTH_COOKIE_SECURE。LOW-3 api 側は Cookie が送られない、に訂正。LOW-4・5 戻し方を revert PR に固定し、便4 後の新規登録者は戻すとログイン不可と明記 → すべて反映 |
