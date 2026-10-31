# 設計 — ログイン直後のパスキー登録（ADR-1013 便6）

現在地: [recon-login-enroll.md](recon-login-enroll.md)（docs/handoff/auth-self-hosted-passkey/recon-login-enroll.md）。対象 ADR: ADR-1013（自社ログイン・パスキー）。守る ADR: ADR-027（i18n）・ADR-144（UI 金型）・ADR-025（手動 INSERT 禁止）・ADR-135/136（migration を含む PR の GO）。

## 1. 目的（PO の言葉）

- PO（2026-10-31）「他のアプリだとログインしたときに生体認証登録しますか？みたいな表示が出て登録できるようになってるのが通常だけどSAでも同じ仕組みに出来る？」
- PO 決定「1」: 案A を採る。パスワードでログインした直後に、裏でパスキーを自動で用意する。それができない端末では、SA の画面で「登録しますか」と聞き、「今はスキップ」も押せる。
- PO 決定「1」: 6 か月で 3 回スキップした人には、もう聞かない（adidas と同じ）。

## 2. 対象と対象外

| 対象 | 対象外 |
|---|---|
| 社内の利用者のパスワードでのログイン直後（`frontend/src/pages/login/LoginPage.tsx` `handleSignIn`） | パスキーでのログイン、更新用トークンでの復帰、閲覧ページ（viewer）のログイン、Firebase のログイン |
| 自動作成の登録の受け付け（サーバー） | 設定画面の登録の決まり（今のまま UP・UV 必須） |
| スキップの記録（新しい表 1 つ） | 管理者の 2 段階の確認（ADR-1048。別の便） |

## 3. 変更前と変更後

| 場面 | 変更前 | 変更後 |
|---|---|---|
| パスワードでログイン（パスワード管理にパスワードを保存した Chrome・Safari） | すぐ元の画面へ | 裏でパスキーが作られ、OS の小さな知らせが出る。そのまま元の画面へ |
| パスワードでログイン（自動で作れない端末。パスキー 0 個） | すぐ元の画面へ | 「顔・指紋でログインできるようにしますか」の画面。「登録する」で OS の画面→登録。「今はスキップ」で元の画面へ |
| 同上（6 か月以内に 3 回スキップ済み、またはパスキーを持っている） | すぐ元の画面へ | すぐ元の画面へ（聞かない） |
| パスキーでログイン | すぐ元の画面へ | 変わらない |

## 4. 外部・過去事例の参照と我々への応用

調べた日 2026-10-31。一次資料を Opus が直接読んだ（クラウドの調べ役は外へ通信できない）。原文で確かめられない数値は根拠に数えない。

| 区分 | Who | When | What / How | How much | 要因 | 出典 |
|---|---|---|---|---|---|---|
| 成功 | adidas | 2026-03 | パスワードでログインした直後に裏で自動作成。条件外（NotAllowedError）は手動登録の画面へ。6 か月で 3 回スキップした人には出さない | 自動作成で登録数 +8%（基準は未記載）。登録率 47%（スマホ 52%・PC 34%）。開始したログインの成功率 99% 超（パスワードは 70%） | 自動作成と手動案内の 2 段構え。失敗を利用者に見せない | https://web.dev/case-studies/adidas-passkeys |
| 成功 | Yahoo! JAPAN | 2023-10 | ログイン・登録の直後に案内。設定画面からも登録可。出す回数に上限 | 登録の 97% が案内経由（ログイン後 91%・新規登録後 6%）、設定画面は 3%。問い合わせ 25% 減。認証 2.6 倍速い | ログイン直後に出す。端末に合わせた言葉 | https://web.dev/case-studies/yahoo-japan-passkeys |
| 成功 | Microsoft | 2024-12-12 | 別の方法でログインした直後に案内。断るボタンは「今はスキップ」。永久に断る選択肢は出さない | 登録の 99% が案内経由、設定画面は 1% 未満。案内を見た人の約 25% が反応。始めた人の 99% が完了。ログイン成功率 98%（パスワード 32%） | 出す場所（ログイン直後）と「速さ」を前に出した文言 | https://www.microsoft.com/en-us/security/blog/2024/12/12/convincing-a-billion-users-to-love-passkeys-ux-design-insights-from-microsoft-to-boost-adoption-and-security/ |
| 限界 | Google（Chrome 公式） | 2025-05 公開・2025-12 更新 | 自動作成の条件: 既定のパスワード管理に保存されたパスワードで最近入ったこと。作られなくても画面に何も出ない | 数値なし | パスワード管理を使わない人には効かない → SA の案内画面が必須 | https://developer.chrome.com/docs/identity/webauthn-conditional-create |
| 限界 | Chrome 公式の実装手引き | 2026-07 | 呼ぶのは「パスワードでの完全なログインの直後」だけ | 数値なし | 対応外の端末向けの案内は自前で要る | https://developer.chrome.com/docs/modern-web-guidance/guides/security/passkey-conditional-create |
| 失敗 | Microsoft（同上） | 2024-12 | 1 回の案内での反応は約 25% | — | 1 回だけでは足りない → 再び聞く決まりが要る | 同上 |
| 失敗 | Yahoo! JAPAN（同上） | 2019→2022 | 端末に縛られたパスキーの継続 38% | 62% が SMS などに戻った | 機種変更で消える。今は同期されるパスキー（iCloud・Google）が主 | 同上 |
| 過去（SA） | SA | 2026-10-31 | 便5 の設定画面での登録が本番で 500 | PO 端末で発見 | 試験で記録部品を代役にし、本番の行の制限が試されなかった → 本便は PostgreSQL の試験を必須にする（§8 K-1） | #4942 |

当てはめ: 4 社とも「ログイン直後に聞く」と「設定画面だけ」で登録の数が大きく違う（Microsoft 99% 対 1% 未満、Yahoo! JAPAN 97% 対 3%）。SA は十数名の社内利用なので数の大きさはそのまま使わない。向きだけを使う。

道具の仕様の確認: Context7 は月の上限で使えなかった。代わりに公式配布物を直接確認した（@simplewebauthn/browser 14.0.0 の startRegistration.js、py_webauthn v2.8.0 の verify_registration_response.py、Chrome 公式の 2 ページ。recon §2・§3）。

## 5. 技術 How

### 5-1. サーバー（`backend/app/routers/auth.py`・`backend/app/auth/passkeys.py`）

(1) 「パスワードでログインした直後か」の判定 `_is_fresh_password_login(request, user) -> bool` を auth.py に足す。
- `Authorization: Bearer` の値を取り、`self_tokens.peek_issuer(token) == self_tokens.ISSUER` でなければ False
- `self_tokens.decode_access_token(token)` を呼ぶ（`get_current_user` が先に同じ値を検証済み。ここは `amr`・`iat` を読むためだけ）。例外は False
- `claims["sub"] == str(user.id)` かつ `claims.get("amr") == ["pwd"]` かつ `now - claims["iat"] <= FRESH_LOGIN_SECONDS`（passkeys.py に `FRESH_LOGIN_SECONDS = 300`）なら True
- 理由: 更新用トークンで作り直した合図には `amr` が無い（`backend/app/routers/auth.py:391`）。パスキーのログインは `["webauthn"]`。パスワード変更（`backend/app/routers/auth.py:633`）も `["pwd"]` で、パスワードを打った直後なので含めてよい

(2) 新しい口 `GET /api/v1/auth/passkey/prompt`（`get_current_user`・`_require_app_origin`）。返り値 `{"can_auto": bool, "show_prompt": bool}`。
- `fresh = _is_fresh_password_login(...)`、`count` = 本人のパスキー数、`skips` = 直近 `PROMPT_SKIP_WINDOW_DAYS = 180` 日のスキップ数
- `can_auto = fresh and count < MAX_PASSKEYS_PER_USER`
- `show_prompt = fresh and count == 0 and skips < PROMPT_SKIP_LIMIT`（`PROMPT_SKIP_LIMIT = 3`）
- 「0 個の人だけ聞く」理由: ブラウザはこの端末にパスキーがあるかを教えない。持っている人に聞くと重複の誤りになりうる。持っている人にも自動作成は試す。設定画面からはいつでも足せる

(3) 新しい口 `POST /api/v1/auth/passkey/prompt/skip`（同じ依存）。`fresh` でなければ 403 `{"detail": "auto_not_allowed"}`。`public.passkey_enroll_prompt_skips` に 1 行足し 204。監査記録は付けない（ログインの安全に関わらない表示の記録のため）

(4) `POST /passkey/register/options` に本文 `{"auto": bool}`（既定 false・今の呼び方 `{}` はそのまま通る）。今の口は本文を受けていない（`backend/app/routers/auth.py:688-693`）ので、`PasskeyRegisterOptionsRequest(BaseModel): auto: bool = False` を足し、引数 `data: PasskeyRegisterOptionsRequest | None = None` で受ける。
- `auto` が true で `fresh` でなければ 403 `auto_not_allowed`
- challenge は `store_challenge("reg_auto" if auto else "reg", ...)`

(5) `POST /passkey/register/verify`: まず `take_challenge("reg", ...)`、無ければ `take_challenge("reg_auto", ...)`。
- `reg_auto` のときだけ `verify_registration_response(..., require_user_presence=False, require_user_verification=False)`。`reg` は今のまま `require_user_verification=True`
- 監査記録の `new_data` に `"auto": true/false` を足す（`_record_auth_audit` 経由。#4942 の形を守る）
- それ以外（INSERT・409・上限）は変えない

### 5-2. DB（migration 1 本）

`migrations/20261031_200000_add_passkey_enroll_prompt_skips.sql`（`migrations/20261013_160000_add_self_hosted_auth_tables.sql` と同じ形）

```sql
CREATE TABLE IF NOT EXISTS public.passkey_enroll_prompt_skips (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    skipped_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_passkey_enroll_prompt_skips_user_at
    ON public.passkey_enroll_prompt_skips (user_id, skipped_at);
-- COMMENT ON TABLE / COLUMN（日本語で用途）
-- RLS なし: public.webauthn_credentials と同じ理由（テナントが決まる前に引く）
-- DO ブロックで salesanchor_app に SELECT, INSERT と sequence の USAGE を GRANT（既存ファイル :96-101 と同じ形）
```

- 置き場の理由: 人ごとの設定の表は無い（recon §4）。`public.users` に列を足すと「6 か月で 3 回」を数えられない。1 か所（この表）だけに置き、ほかへ写さない
- 試験用の SQLite 版を `backend/tests/conftest.py` の `webauthn_credentials` の隣に足す（`public.` を外す置換 `backend/tests/conftest.py:324-325` にも足す）
- `scripts/run_all_migrations.sh` の末尾（今の最後は `run_sql migrations/20261024_100100_create_ai_reader_cloud_role.sql`）に `run_sql` で登録する（guards/07-migration.md「置くだけだと MIGRATION GUARD が落ちる」）
- 相談係用の伏せたビュー（ADR-1052）: 新しい表に文字の列は無い（id・user_id・skipped_at）。分類の無い文字の列は自動で伏せる決まり（`backend/tests/ops/test_ai_cloud_views.py:301`）なので、分類表 `migrations/20261024_100300_create_ai_cloud_views.sql` は変えない

### 5-3. 画面（`frontend/src/lib/auth/passkey.ts`・`frontend/src/pages/login/LoginPage.tsx`）

(1) passkey.ts に足す
- `conditionalCreateSupported(): Promise<boolean>`: `PublicKeyCredential.getClientCapabilities?.()` の `conditionalCreate === true`。無い・例外なら false
- `getPasskeyPrompt(): Promise<{ can_auto: boolean; show_prompt: boolean }>`
- `autoRegisterPasskey(): Promise<"created" | "exists" | "not_allowed" | "failed">`: options を `{ auto: true }` で取り、`startRegistration({ optionsJSON, useAutoRegister: true })`。10 秒で打ち切り（`failed`）。InvalidStateError→`exists`、NotAllowedError→`not_allowed`、そのほか→`failed`
- `skipPasskeyPrompt(): Promise<void>`
- `registerPasskey(label)` は変えない（案内の「登録する」から `registerPasskey("")` で呼ぶ。空の名前は今も「名前なし」表示）

(2) LoginPage.tsx `handleSignIn` の `await signIn(...)` と `navigate(...)` の間に、次を足す。どこで失敗しても必ず `navigate` する（ログインを止めない）
1. `passkeySupported()` でなければ navigate
2. `getPasskeyPrompt()`。失敗なら navigate
3. `can_auto` かつ `conditionalCreateSupported()` なら `autoRegisterPasskey()`。`not_allowed` 以外の結果（作れた・既にある・失敗）は navigate
4. （自動作成を試さなかった、または `not_allowed`）`show_prompt` なら案内を開く。でなければ navigate
- 案内は金型 `Modal`（`size="sm"`）＋ `Button` 2 つ。「登録する」→ `registerPasskey("")`→ 結果に関わらず navigate（キャンセルは黙って続ける）。「今はスキップ」と閉じる操作 → `skipPasskeyPrompt()` → navigate
- 新しい文言は `login.passkeyPromptTitle`・`login.passkeyPromptBody`・`login.passkeyPromptRegister`・`login.passkeyPromptSkip` を `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の両方に（ADR-027）。文言は Microsoft の「速さ」を前に出す（例: 「次からは顔や指紋だけで、すぐにログインできます」）
- 色・大きさの直書きはしない（ADR-144）

## 6. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| A1 パスワードでログインした直後だけ、自動作成の options が 200。更新用トークン・パスキーのログイン・5 分超の合図では 403 | pytest（合図を `create_access_token(..., amr)` で作り分け、`iat` は時刻を進めて試す） |
| A2 自動作成の verify は UP・UV の印が無くても通り、設定画面の verify は UV の印が無いと 400 のまま | pytest（`verify_registration_response` の呼び出し引数を確かめる試験＋既存の試験が全通過） |
| A3 `show_prompt` は 0 個かつ 180 日で 2 回以下のときだけ true。3 回目のスキップの後は false。181 日前のスキップは数えない | pytest |
| A4 スキップの記録と監査記録の書き込みが PostgreSQL の本物の表で通る（代役にしない） | `backend/tests/` の PostgreSQL 専用試験（CI の RLS 試験の枠） |
| A5 画面: 自動作成が `not_allowed` で `show_prompt` true のとき案内が出る。スキップで元の画面へ移り skip が 1 回呼ばれる。どの失敗でもログイン後の画面へ移る | vitest（`LoginPage` の分岐 5 通り: 対応外・作れた・not_allowed＋案内・not_allowed＋案内なし・prompt 取得失敗） |
| A6 ja/en のキーが揃い、直書きの文字・色が無い | 既存の CI（i18n・UI ガバナンス） |
| A7 本番: PO の PC かスマホで、パスキーを消した状態でパスワードログイン → 自動作成の知らせか案内が出て、登録後にパスキーでログインできる | PO 目視＋本番 DB の読み取り（パスキーの行が増え、監査の `auto` が記録される） |
| A8 本番: 反映後 10 分の backend の記録に、このページ由来の 500 が 0 件 | 本番 backend の記録を読む |

## 7. KPI（測り方と基準値）

- 基準値（2026-10-31 18:27 JST・本番読み取り）: パスキーを持つ人 1 人 / パスワードでログインできる有効な人 9 人。直近 14 日にログインした人 4 人
- 目標: 反映から 14 日後、直近 14 日にログインした人のうちパスキーを持つ人の割合が 4 人中 3 人以上（Microsoft・Yahoo! JAPAN の「案内経由が 97〜99%」の向きと、SA の人数の少なさから。1 人はスキップを続けうる）
- 測り方: 本番 DB の読み取り（`webauthn_credentials` の人数・`audit_logs` の `passkey_registered` の `auto` の内訳・`passkey_enroll_prompt_skips` の件数）。14 日後に記録する

## 8. 弊害・トレードオフと対処

| 弊害 | 対処 |
|---|---|
| 自動作成の道だけ UP・UV の印を求めない（設定画面より弱い） | 使えるのは「パスワードを打って 5 分以内の合図」と「その合図で取った reg_auto の challenge（5 分で失効・1 回きり）」の両方がそろう時だけ。Chrome 公式の決まりと同じ。ログインに使うときは今のまま UV を求める（`backend/app/auth/passkeys.py` の認証側は変えない） |
| 合図を盗まれると、盗んだ人の端末のパスキーを足されうる | 合図そのものが既に全操作の鍵で、新しく増える危険ではない。5 分の窓で狭める。登録は監査記録に `auto` 付きで残る |
| ログインが遅くなる | 自動作成は 10 秒で打ち切り。どの失敗でも先へ進む |
| K-1（同じ種類のミスを通さない）: 便5 は記録部品を代役にして本番の 500 を見逃した | A4 の PostgreSQL 試験を必須にし、カードの「本物と同じ形で試す試験」欄に書く |
| migration を含む | ADR-135/136 の手順: バックアップの確認と GO 記録をマージ前に残す |

戻し方: PR の revert（画面は案内が消え元の動きへ。サーバーは `auto` を受けなくなる）。表は残っても害が無い（読まれないだけ）ので、表の削除はしない。

## 9. 計画票

| 段 | 中身 | 担当 |
|---|---|---|
| 1 | 本設計の審査・カード作成・`scripts/card-lint.sh` | Opus |
| 2 | 実装（§5 全部を 1 つの PR。migration を含む） | Sonnet（クラウド） |
| 3 | マージ前審査（reviewer opus）・必須 CI | Opus |
| 4 | バックアップ確認・GO 記録・マージ・反映確認（A8） | Opus |
| 5 | PO 目視（A7）・14 日後の KPI 記録 | PO・Opus |

## 10. 継続・維持の仕組み

- 自動作成の道の守り: A1・A2 の pytest が CI で毎回走る（UV を外す範囲が広がったら赤）
- スキップの決まりの数（300 秒・180 日・3 回）は passkeys.py の定数 1 か所だけに置く
- 14 日後の KPI を ADR-1013 の記録に残す
- 守り手: Claude Opus（ADR-1013 の担当。14 日後の KPI 記録と、試験が赤になったときの直し）。見張りの試験: backend/tests/test_passkey_login_enroll.py・backend/tests/test_origin_check_not_on_get.py。見張りの試験: backend/tests/test_passkey_login_enroll.py・backend/tests/test_origin_check_not_on_get.py

## 11. 設計相談と審査の記録

- 2026-10-31 PO: 案A と 6 か月 3 回を決定（「1」を 2 回）
- 2026-10-31 Opus 審査（同じ AI による自己審査。独立した第二者の審査ではない）: 下の「審査」に記す

### 審査（2026-10-31・Opus 自己審査）

判定: **APPROVE**（設計合格。PO 承認・実装開始・マージの承認は兼ねない。実装と本番反映は PO の 2026-10-31「完走させてくれ」と「1」の範囲）

確かめたこと（`git show origin/main:` で実物照合）:
- 合図の `amr` は配列 `["pwd"]`（`backend/app/auth/self_tokens.py:92-104`）。有効期間 900 秒（同 :24）なので 300 秒の窓はその内側
- challenge の置き場の鍵に kind が入る（`backend/app/auth/passkeys.py:48` `_key(kind, owner, challenge_id)`）→ `reg` と `reg_auto` は混ざらず、`reg` で取れなければ `reg_auto` を試す順で取り違えない。`store_challenge` の説明文「kind は reg か login」に `reg_auto` を書き足す
- 今の options の口は本文を受けない（`backend/app/routers/auth.py:688-693`）→ §5-1 (4) で既定 false の本文を足す。設定画面の呼び方（`frontend/src/pages/account-settings/PasskeySection.tsx:58` → `registerPasskey(label)`）は変わらない
- verify は空の名前を「名前なし」に直す（`backend/app/routers/auth.py:738` `... or None`）→ 案内からの `registerPasskey("")` は通る
- 設定画面の verify の UV 必須（`backend/app/routers/auth.py:727-733`）は変えない

残る事項（設計合格を妨げない）:
- 案内を 5 分より長く開いたままスキップすると 403 になり、スキップが数えられない。画面は失敗を無視して先へ進む。次回も案内が出るだけで害は無い
- 社員がブラウザにパスワードを保存しているかは未確認。保存していない人には自動作成が効かず、案内の画面で登録する（どちらでも合格の基準 A7 は判定できる）
- `getClientCapabilities` が無いブラウザ（古い Safari 等）は自動作成を試さず案内へ回る
