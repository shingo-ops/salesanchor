# 設計 — 管理者ログインの2段階の確認

> この文書は何か：管理者だけ、パスワードのほかに「指紋・顔」か「認証アプリの6桁の数字」を必須にし、初めての機器からはいつもの機器での承認を必須にする設計です。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)
現状: [recon.md](recon.md)／ADR: [ADR-1048](../../adr/ADR-1048-admin-two-step-login.md)／審査: [review-opus.md](review-opus.md)

**日付**: 2026-10-27
**書いた人**: 設計パートナー（Opus・ccopusgo セッション）
**状態**: 設計案（自己審査 APPROVE）。PO の方向の決定は下の §1 のとおり。実装は未着手。

## 1. PO の決定（2026-10-27 チャット原文）

| 順 | PO の答え | 意味 |
|---|---|---|
| 1 | 「1と2」 | 方式は、パスキー（指紋・顔）と認証アプリの6桁の数字の両方 |
| 2 | 「3」 | 設計を先に見てから、PO の画面作業（メール設定）の時期を決める |
| 3 | 「1」 | 対象は super admin と各会社の owner/admin の両方 |
| 4 | 「3」→「1」 | 使い道の分からない管理者2人を先に止めてから、残りを対象にする（実行済み [deactivate-7-9/README.md](deactivate-7-9/README.md)） |
| 5 | 「生体認証or6桁の認証アプリの番号どちらかで入れるようにしておく」 | 指紋・顔、またはパスワード＋6桁のどちらでも、全部の画面を使える |
| 6 | 「1」（承認の仕組みも入れる） | 初めての機器からは、いつもの機器での承認を必須にする。Gmail のような番号を選ぶ形（PO「gmailみたいに番号を選択するやつは技術的に再現できる？」） |
| 7 | 「1」（画面とメール） | 承認の知らせは、開いている画面に出す＋メール。承認は必ずいつもの機器の画面の中で行う |
| 8 | 「1」 | QR コードを出す金型を新しく登録してよい |

## 2. 目標の数（受け入れ基準）

| 基準 | 基準値（測った日） | 目標値 | 検証方法 |
|---|---|---|---|
| K1 2段階の確認を設定していない有効な管理者の人数 | 3人（2026-10-27 23:20 JST 本番読み取り。パスキー0件・6桁の表なし） | 0人 | 本番 DB の読み取り: 管理者（§3-1 の判定）のうち、webauthn_credentials 0件かつ user_totp の確認済み行なしの人数 |
| K2 管理者に「パスワードだけ」の全権トークンを出した回数 | 0回（自社ログインは未切替のため。2026-10-27） | 0回（切替後も毎週0） | backend ログの `admin_token_issued amr=` を数え、`amr=pwd` 単独が0件 |
| K3 管理者でない人のログインの手順数 | 今の手順数（切替後のログイン画面で数える） | 増えない（同じ数） | 画面で数える（評価者が録画で確認） |
| K4 初めての機器から「パスワード＋6桁」だけで管理者が入れた回数 | 未測定（仕組みが無い） | 0回 | 自動試験: 承認なしの新しい機器で 403。本番ログの `admin_login_pending` のうち承認なしで `issued` になった件数0 |
| K5 使った6桁をもう一度使えた回数 | 未測定 | 0回 | 自動試験: 同じ数字を2回送ると2回目は 401 |
| K6 QR の金型に直書きの色・寸法がある数 | 金型なし | 0か所 | CI（UI ガバナンスの検査）と QrCode.stories.tsx（新設予定） がカタログに出ること |
| K7 承認の画面で、違う番号を選んで通った回数 | 未測定 | 0回 | 自動試験: 違う番号を選ぶと依頼が取り消しになり、新しい機器は入れない |

## 3. 設計

### 3-1. 管理者の判定（正本は1か所のまま）

- 管理者 = `users.is_super_admin = true` か、`get_user_system_keys`（backend/app/auth/dependencies.py:547）が owner / admin を返す人。新しい「管理者」列や名簿は作らない。
- 判定は関数1つ `is_admin_for_2fa(user, db)` に集め、既存の `is_tenant_admin`（backend/app/auth/system_roles.py:17）を呼ぶ。

### 3-2. 入り方と、出すトークン

| 入り方 | 管理者 | 管理者でない人 |
|---|---|---|
| パスキー（指紋・顔） | 全権。amr=["webauthn"]。機器を問わない（理由: パスキーは偽の画面で働かないため、NIST 3.2.5） | 全権（ADR-1013 のまま） |
| パスワード＋6桁・いつもの機器 | 全権。amr=["pwd","otp"] | 6桁は任意（ADR-1013 Decision 7 のまま） |
| パスワード＋6桁・初めての機器 | 承認待ち（§3-5）。承認されたら全権＋その機器を「いつもの機器」に登録 | 該当なし |
| パスワードだけ・2段階が未設定 | 設定だけできるトークン（amr=["pwd"]、scope="enroll"。15分。refresh cookie は出さない） | 全権（今のまま） |
| パスワードだけ・2段階が設定済み | トークンを出さない（6桁かパスキーを求める） | 全権（今のまま） |

- 発行の判定は自社ログインの発行口（backend/app/routers/auth.py:238-310 と refresh の backend/app/auth/self_tokens.py:228 付近）の1か所に置く。refresh でも同じ判定をやり直す（権限が途中で変わっても15分で揃う）。
- 二重の守り: `require_super_admin`（backend/app/auth/dependencies.py:516）と `require_tenant_admin`（:606）でも、トークンの amr が「webauthn」か「pwd＋otp」でなければ 403。scope="enroll" のトークンは設定の口（§3-3・§3-4）以外すべて 403。
- 発行のたびに backend ログへ `admin_token_issued user_id=<id> amr=<...> device=<known|new>` を1行出す（K2・K4 の測り方）。
- Firebase 経路（backend/app/auth/dependencies.py:222-229）は変えない。本件は AUTH_PROVIDER=self（ADR-1013 便4）の後に効く。

### 3-3. 認証アプリの6桁

- 表 `public.user_totp`（1人1行）: user_id INT PK FK users.id ON DELETE CASCADE / secret_encrypted TEXT NOT NULL / confirmed_at TIMESTAMPTZ / last_used_timecode BIGINT / created_at TIMESTAMPTZ NOT NULL DEFAULT now()。RLS なし・salesanchor_app に GRANT（ADR-1013 の表と同じ: migrations/20261013_160000_add_self_hosted_auth_tables.sql:3,95-101）。
- 秘密は既存の `encryption.encrypt`（backend/app/services/encryption.py:100）で暗号化して保存する。新しい鍵・新しい暗号部品は作らない。列名が `_encrypted` で終わるので、読み取りの道で自動で隠れる（backend/app/ops/readonly_query.py:42）。手で入れない（CLAUDE.md ADR-025 常時厳禁）。
- 部品: pyotp 2.10.0。`verify_and_get_timecode`（valid_window=1）で照合し、返った timecode が `last_used_timecode` 以下なら拒否（使い回し防止・K5）。成功時に `last_used_timecode` を更新する（同じ UPDATE の WHERE で古い値を条件にし、同時の2回目を落とす）。
- 失敗回数は既存の `failed_login_count` / `locked_until`（ADR-1013 便1の列）に数える。新しい数え方は作らない。
- 設定の流れ: 秘密を作る → QR を出す（§3-7）→ 6桁を1回打って合っていれば `confirmed_at` を入れる。合うまでは未設定のまま。
- 2段階が設定済みの人が6桁を設定し直す・消すときは、今ある要素（パスキーか今の6桁）で確認し直す（OWASP「要素の変更は既存の要素で再確認」）。

### 3-4. いつもの機器

- 表 `public.user_trusted_devices`: id BIGSERIAL PK / user_id INT FK users.id ON DELETE CASCADE / token_hash BYTEA UNIQUE NOT NULL（cookie の値の SHA-256。値そのものは保存しない）/ label TEXT（ブラウザ名など表示用）/ created_at / last_used_at / revoked_at。
- cookie: 32バイトの乱数、HttpOnly・Secure・SameSite=Strict・有効180日。refresh cookie（backend/app/routers/auth.py:211-221）と同じ書き方にそろえる。
- いつもの機器になる時: (1) 管理者が2段階の設定を終えた機器 (2) パスキーで入った機器 (3) 承認で入れた機器。
- 一覧と取り消し: 管理者は自分の「いつもの機器」を画面で見て消せる。消すとその機器からの次のログインは初めて扱い。
- 判断に場所（IP）は使わない（スマホは移動で変わるため。PO に 2026-10-27 説明済み）。

### 3-5. 初めての機器の承認（番号を選ぶ形）

1. 初めての機器で「パスワード＋6桁」が合ったら、トークンは出さず承認依頼を作る。依頼は Redis に5分・1回限り（パスキーの challenge と同じ置き方: docs/handoff/auth-self-hosted-passkey/design.md:80）。中身は user_id・正しい2けたの番号・候補3つ・依頼の id。
2. 初めての機器の画面に、正しい番号を大きく出して待つ。依頼の id は、初めての機器にだけ渡す乱数（HttpOnly・Secure・SameSite=Strict の cookie、5分）と組にして Redis に置く。承認後のトークンは、この cookie を持つ機器だけが受け取れる（依頼の id を盗み見られても、別の機器では受け取れない）。
3. いつもの機器へ知らせる:
   - 開いている画面: ADR-1016 の SSE 1本（`GET /api/v1/events/stream`）に人単位の宛先 `rt:u:{user_id}` を足す。新しい通り道は作らない。知らせの中身は「承認依頼がある」だけで、番号は載せない。画面は API で依頼を取りに行く。
   - メール: 既存の送信部品（backend/app/services/auth_mail.py:73-93）で「セールスアンカーを開いて承認してください」と送る。メールに承認のボタンやリンクは置かない（偽のメールで承認させられるのを防ぐ）。メール設定が無いときは送らずログだけ（backend/app/services/mail_config.py:28-35 の今の動き）。
4. いつもの機器の画面に Modal で候補の番号3つと「心当たりがない」を出す。全権トークンを持つ、いつもの機器の cookie がある画面だけが見られる。
5. 正しい番号を選ぶ → 依頼が承認になり、初めての機器が待ちの口で全権トークンと「いつもの機器」cookie を受け取る。違う番号か「心当たりがない」→ 依頼を取り消し、初めての機器は入れない。本人にメールで知らせる（K7）。
6. 回数の上限: 1人あたり承認依頼は1時間に3件まで。超えたら1時間は依頼を作らない（通知を何度も送りつける手口を防ぐ）。

### 3-6. すべての機器を失くしたとき

- パスキーが同期型（iCloud キーチェーンなど）なら、新しい機器でパスキーを使えば入れる（§3-2 の1行目。承認は要らない）。
- いつもの機器が1台も無い（cookie を消した等）ときは、承認できないので「パスワード＋6桁」では入れない。パスキーで入るか、次の台本を使う。
- それも使えないときは、本人確認をしたうえで、その人の6桁といつもの機器を消す運用の台本を使う（OWASP「サポートが厳密な手順で本人確認」）。台本は実装の便で docs/handoff/admin-2fa/ に置き、本番データの変更の決まり（PO 同意・DRY-RUN・件数ガード・戻し）に従う。

### 3-7. 画面

- 6桁の入力: 既存の `TextFieldControl`（frontend/src/components/TextField.tsx:43）に inputMode="numeric"・autoComplete="one-time-code"・maxLength=6 を渡す。新しい金型は作らない。
- QR の表示: 新しい金型 frontend/src/components/QrCode.tsx（新設予定）＋QrCode.css（var() のみ）＋QrCode.stories.tsx（新設予定）（PO 許可 2026-10-27「1」、docs/CC_UI_GOVERNANCE.md:13-14）。中身は qrcode.react 4.2.0 の QRCodeSVG。色を CSS 変数で渡せるかは未確認なので、金型を作る便で最初に確かめる。渡せない場合は SVG の path の fill を CSS（var() のみ）で上書きする形にし、どちらも駄目なら止めて相談する。
- QR の隣に、手で打つための英数字も出す（カメラが使えない人のため）。
- 承認の画面: 既存の `Modal`・`Button`。待ちの画面: `Card`・`LoadingBlock`・`Callout`。
- 文字はすべて `t("key")`（ja.json・en.json 同じキー。ADR-027）。

### 3-8. 部品の版

- pyotp 2.10.0（MIT）・qrcode.react 4.2.0（ISC）を本件で足す。
- py_webauthn 2.8.0・@simplewebauthn/browser 14.0.0 は ADR-1013 便5（パスキー）で足す。py_webauthn 3.x は cryptography>=49 が要り、今の 48.0.1（backend/requirements.txt:24）と両立しないため 2.8.0 にする。依存の引き上げは別件。

## 4. 対象と対象外

- 対象: 管理者の2段階の必須化、認証アプリの6桁、いつもの機器、初めての機器の承認、QR の金型、SSE の人単位の宛先、承認の知らせメール。
- 対象外: 管理者でない人への必須化（ADR-1013 Decision 7 のまま任意）、スマホの通知（Web Push。PO 2026-10-27 選ばず）、予備コード（PO の要望なし）、Firebase 経路の MFA（便6 で撤去）、パスキーそのものの実装（ADR-1013 便5）。

## 5. 便の分け方と順番

ADR-1013 の便3（メール・PO の画面作業）→ 便4（切替）→ 便5（パスキー）の後に置く。

| 便 | 中身 | 危ない道 |
|---|---|---|
| 7a | migration: user_totp・user_trusted_devices（構造だけ） | migrations/ → PO GO（ADR-136） |
| 7b | backend: 6桁・いつもの機器・承認・発行の判定・SSE の人単位の宛先・ログ行。設定 `ADMIN_2FA_ENFORCED`（既定 false）。false の間は判定せず記録だけ | なし（deploy.yml を触らないこと） |
| 7c | frontend: 設定画面・待ちの画面・承認の Modal・QrCode 金型 | なし |
| 7d | 3人が設定を終えたことを K1 で確かめてから `ADMIN_2FA_ENFORCED=true` にする | secrets・本番設定 → PO GO |

- 7d の前に K1=0 でなければ切り替えない（PO 本人が閉め出されるのを防ぐ）。

## 6. 代わりの案と選んだ理由

| 案 | 選ばなかった理由 |
|---|---|
| 6桁で入れる範囲を「新しいパスキーの登録だけ」にする | PO が「どちらでも全部使える」を選んだ（2026-10-27）。代わりに初めての機器の承認で偽の画面への弱さを埋める |
| 押すだけの承認（Meta 型） | 何度も送りつけられて押してしまう手口がある。番号を選ぶ形と作る量はほぼ同じ |
| スマホの通知（Web Push） | 部品が0から。iPhone はホーム画面への追加が必要 |
| users に 6桁の列を足す | ADR-1013 Decision 2「ログイン情報は子表」に合わない |
| 新しい暗号部品・新しい鍵 | 既存の encryption.py で足りる |
| 場所（IP）で「いつもと違う」を決める | 本人が移動しても止まる |

## 7. 危険と対処

| 危険 | 対処 |
|---|---|
| PO 本人が閉め出される | 7d の切替は K1=0 を確かめてから。§3-6 の運用台本。戻し: `ADMIN_2FA_ENFORCED=false` |
| 設定前にパスワードを盗まれ、他人に6桁を設定される | 設定だけのトークンは15分・設定の口のみ。設定完了をメールで本人に知らせる。切替前に3人が設定を終える |
| 承認の通知を何度も送られる | 番号を選ぶ形・1時間3件まで・違う番号で取り消し |
| メールがまだ送れない | 画面の知らせだけでも承認できる。メールは便3 の PO 作業後に届く |
| SSE の変更で既存の即時反映が壊れる | 宛先を足すだけ。既存の会社単位・全体の配信の試験を残す |
| 審査用の管理者（tenant-review）が設定できない | 対象に含める（PO 決定）。設定は PO が行う |

## 8. 外部・過去事例の参照と我々への応用

| 出典（日付） | 内容 | 我々への応用 | 適用の限界 |
|---|---|---|---|
| NIST SP 800-63B-4（2025-08-26）3.2.5・付録B | 手で打つ OTP はフィッシングに強いと見なさない。同期型パスキーは AAL2 まで | パスキーは機器を問わず全権、6桁は初めての機器で承認を要る | 連邦向けの基準。管理者に限った要求は本文に無い |
| OWASP MFA Cheat Sheet | 格下げの防止・要素の変更は既存要素で再確認・OTP 1回限り | §3-3 の使い回し防止と再確認 | 数値の基準は無い |
| Google ログイン確認（support.google.com/accounts/answer/7026266） | いつもと違う入り方のときだけ番号を合わせる確認 | §3-5 の形をそのまま採る | Google は自社アプリへの通知。我々は画面＋メール |
| Uber 2022（セキュリティ会社の記事 centrexit.com） | 押すだけの承認を繰り返し送られ、押してしまった | 番号を選ぶ形と回数の上限 | Uber の公式発表は未確認。数値は使わない |

## 9. 維持の仕組み

- 自動試験（backend/tests/ に置く。7b のカードで名前を決める）: K2・K4・K5・K7 を試験で守る。
- UI ガバナンスの CI（docs/CC_UI_GOVERNANCE.md）: K6。
- 毎週の点検: K1 を本番の読み取りで数える（新しく管理者になった人が未設定のままでないか）。
- 守り手: 設計パートナー（Opus）。仕様書の索引 docs/specs/auth-login/README.md に本書を載せる。
