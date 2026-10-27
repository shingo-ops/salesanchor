# 設計 — 管理者ログインの2段階の確認

> この文書は何か：管理者だけ、パスワードのほかに「指紋・顔」か「認証アプリの6桁の数字」を必須にし、初めての機器からはいつもの機器での承認を必須にする設計です。

親: [docs/specs/auth-login/README.md](../../specs/auth-login/README.md)
現状: [recon.md](recon.md)／ADR: [ADR-1048](../../adr/ADR-1048-admin-two-step-login.md)／審査: [review-opus.md](review-opus.md)

**日付**: 2026-10-27（第2版 2026-10-28: Opus 審査役の REQUEST_CHANGES 指摘1〜12 を反映。第3版 同日: 2回目の審査の必須7・任意7 を反映。review-opus.md §6）
**書いた人**: 設計パートナー（Opus・ccopusgo セッション）
**状態**: 設計案（第3版。再審査待ち）。PO の方向の決定は下の §1 のとおり。実装は未着手。
**行番号の基準**: origin/main（2026-10-28 fetch 後。backend/app と frontend/src/pages/login は本ブランチとの差 0）

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
| K2 管理者に「パスワードだけ」の全権トークンを出した回数 | 0回（自社ログインは未切替のため。2026-10-27） | 0回（切替後も毎週0） | backend ログの `admin_token_issued` 行（§3-2）のうち `scope=full` かつ `amr=pwd`（pwd だけ）の件数が0。自動試験でも同じ条件を確かめる |
| K3 管理者でない人のログインの操作数 | 3操作（1画面でメール入力・パスワード入力・「ログイン」ボタン。frontend/src/pages/login/LoginPage.tsx:91-125。2026-10-28 origin/main） | 3操作のまま（6桁を設定していない人） | 7c の評価者が録画で数える |
| K4 初めての機器から承認なしで管理者が全権を得た回数 | 未測定（仕組みが無い） | 0回 | 自動試験: 承認なしの新しい機器は全権トークンを受け取れない。本番ログ: `admin_token_issued` 行のうち `amr=pwd+otp` かつ `device=new` で、`request_id` が `admin_login_approved` 行の `request_id` に無い件数0（§3-2・§3-5 のログ行）。パスキーで入った行は `device=-` なので数えない（パスキーは機器を問わず全権。PO 決定5） |
| K5 使った6桁をもう一度使えた回数 | 未測定 | 0回 | 自動試験: 同じ数字を2回送ると2回目は 401 |
| K6 QR の金型に直書きの色・寸法がある数 | 金型なし | 0か所 | CI（UI ガバナンスの検査）と QrCode.stories.tsx（新設予定） がカタログに出ること |
| K7 承認の画面で、違う番号を選んで通った回数 | 未測定 | 0回 | 自動試験: 違う番号を選ぶと依頼が取り消しになり、新しい機器は入れない |

## 3. 設計

### 3-1. 管理者の判定（正本は1か所のまま）

- 管理者 = `users.is_super_admin = true` か、`get_user_system_keys`（backend/app/auth/dependencies.py:547）が owner / admin を返す人。新しい「管理者」列や名簿は作らない。
- 判定は関数1つ `is_admin_for_2fa(user, db)` に集め、既存の `is_tenant_admin`（backend/app/auth/system_roles.py:17）を呼ぶ。中身の順番は次のとおり。
  1. `user.is_super_admin` が true なら、DB を引かずに管理者とする。
  2. `set_tenant_context(db, user.tenant_id)`（dependencies.py:330）で会社の文脈を設定する。`get_user_system_keys` は search_path の設定が前提で（:547-552 の説明）、user_roles は会社ごとのスキーマにしか無い。get_current_user（:124-260）の中では search_path は設定されていない（設定は get_current_tenant の :300-302）。生の `SET search_path` は書かない（:337 の決まり）。
  3. `get_user_system_keys` を呼び、`is_tenant_admin` で判定する。
  4. `clear_tenant_context(db)`（:414）で文脈を戻す。後で get_current_tenant が改めて設定する。
- この関数を呼ぶのは2か所だけ: 自社のトークンを出す口（§3-2）と、必須化の間の Firebase の道（§3-2）。
- 判定が例外で失敗したとき（DB の障害など）は、トランザクションを rollback し、管理者として扱う（閉じる側に倒す）。上の 2 で文脈を必ず設定するので、設定漏れによる「毎回の失敗」は起きない。失敗は DB 障害のときだけで、そのときは今も要求は通らない。

### 3-2. 入り方と、出すトークン

| 入り方 | 管理者 | 管理者でない人 |
|---|---|---|
| パスキー（指紋・顔） | 全権。amr=["webauthn"]。機器を問わない（理由: パスキーは偽の画面で働かないため、NIST 3.2.5） | 全権（ADR-1013 のまま） |
| パスワード＋6桁・いつもの機器 | 全権。amr=["pwd","otp"] | 本件では6桁の設定の口を出さない（ADR-1013 Decision 7 の任意設定は別件） |
| パスワード＋6桁・初めての機器 | 承認待ち（§3-5）。承認されたら全権＋その機器を「いつもの機器」に登録 | 該当なし |
| パスワードだけ・2段階が未設定 | 必須化の後: 設定だけできるトークン（amr=["pwd"]、scope="enroll"。15分。refresh cookie は出さない）。必須化の前: 全権（記録だけ） | 全権（今のまま） |
| パスワードだけ・2段階が設定済み | 必須化の前後どちらでも、トークンを出さない（6桁かパスキーを求める。§3-3 の券） | 該当なし（設定の口が無い） |

- **必須化の設定 `ADMIN_2FA_ENFORCED` が変えるもの**: 2段階を設定していない管理者に、全権を出すか設定用だけを出すか。もう1つは、管理者の Firebase トークンを拒むか。2段階を設定済みの管理者は、設定の値に関係なく2段階と承認を求める。これは、7d の前に3人が実際に使って確かめられるようにするためである。
- **トークンの形**: 自社アクセストークンに `scope`（"full" か "enroll"）を足す。amr は今の `create_access_token(user_id, email, amr)`（backend/app/auth/self_tokens.py:86-98。今は1つの文字列を `[amr]` にする）を、複数の要素を渡せる形に広げる。
- **トークンを出す口（必ず全部が同じ関数を通る）**: 次の5つ。どの口も、§3-1 の判定・トークンの作成・refresh の組への amr の記録・ログ行を、共通の関数1つで行う。口ごとに書き分けない。
  1. パスワード: login（backend/app/routers/auth.py:238-316）
  2. 6桁: §3-3 の6桁の口
  3. 承認待ち: §3-5 の、初めての機器が承認後にトークンを受け取る口
  4. パスキー: ADR-1013 便5 の login/verify（docs/handoff/auth-self-hosted-passkey/design.md:80「login と同じ発行処理」）
  5. refresh（auth.py:319-347）
- **refresh で強さを引き継ぐ**: 今の refresh は `create_access_token(user_id, email, None)`（auth.py:344）で amr を捨てる。refresh の表 `auth_refresh_tokens`（migrations/20261013_160000_add_self_hosted_auth_tables.sql:68-81）に amr の列は無い。そこで 7a で同じ表に `amr TEXT[]`（NULL 可）を足し、組（family）を作る口（上の 1〜4）で必ず入れる。refresh の入れ替え（self_tokens.rotate_refresh_token）は新しい行へ同じ値を写す。refresh は写した amr でトークンを作り直し、そのうえで判定をやり直す。管理者で amr が「webauthn」か「pwd＋otp」でない組は、全権を出さず 401（ログインし直し）にする。amr が NULL の組（7a より前に作られた組）は「pwd だけ」と見なす。refresh では機器を見直さない。
- **自社トークンはキャッシュに入れない**: 今は自社トークンも Firebase と同じキャッシュ（300秒、backend/app/cache.py:15）に書かれ（dependencies.py:108）、キャッシュの確認（:190-198）は自社トークンの振り分け（:207-209）より前にある。このままでは2回目以降の要求が `_authenticate_self_token` を通らず、scope と amr の確認が飛ぶ。そこで 7b で次のように並べ替える。
  - 自社トークンの振り分けを、ログアウト済みの確認（:180-185）の直後、キャッシュの確認（:190）の前へ移す。
  - `_authenticate_self_token` の中のキャッシュへの書き込み（:108）を消す。自社トークンは毎回、手元で署名を確かめ、users を1回引く（今のキャッシュに当たらない時と同じ量）。
  - IP の制限の確認（:200-205）は、今と同じく Firebase の道だけに置く。自社トークンは外部に問い合わせず手元で確かめる。偽のトークンは今と同じく `_reject_self_token`（:74-79）が IP の失敗に数える。
  - この結果、キャッシュに当たる道を通るのは Firebase のトークンだけになる。
- **自社トークンの確認で scope と amr を読む**: `_authenticate_self_token`（dependencies.py:82）が claims から amr と scope を読む。`get_current_user`（:124、request を受け取る）は、それを `request.state.auth_amr` と `request.state.auth_scope` に載せる。scope="enroll" のトークンは、`_authenticate_self_token` の中で「設定の口の一覧」以外の道なら 403 にする。一覧は §3-3・§3-4 の口で、backend の定数1か所に置く。一覧の数は試験で固定する。
- **二重の守り**: `require_super_admin`（dependencies.py:516）と `require_tenant_admin`（:606）は、自社トークンのとき `request.state.auth_amr` が「webauthn」か「pwd＋otp」でなければ 403。Firebase のトークンのとき（必須化の前だけ通る）は今のまま。主な守りはトークンを出す口のほうである。`require_permission` 系（owner/admin に全権限キーを足す :597-600）はこの二重の守りの対象外で、出す口の判定だけで守る。
- **Firebase の道**: 今は issuer が salesanchor でないトークンは Firebase の確認に回る（dependencies.py:207-213。AUTH_PROVIDER は見ない）。キャッシュに当たったトークンは、Firebase の確認と MFA の確認（:222-229）を通らずに利用者を返す（:190-198）。そこで `ADMIN_2FA_ENFORCED=true` の間は、Firebase の道で見つかった利用者が管理者（§3-1）なら 401 にする。置く場所は、キャッシュに当たった道（:198 の return の前）と、当たらない道（:258 でキャッシュに書く前）の両方。上の並べ替えにより、ここを通るのは Firebase のトークンだけである。管理者は自社ログイン（便4 で開く）だけで入る。管理者でない人は通す。キャッシュに当たった道でも毎回 §3-1 の判定を行う（super admin でない人は user_roles を1回引く）。この負荷は必須化の間だけで、便6 で Firebase の道ごと無くなる。
- **ログ行**: 管理者（§3-1）にトークンを出すたびに、backend ログへ次の1行を出す。管理者でない人には出さない。値は id と短い語だけで、メールアドレス・番号・秘密は載せない。
  `admin_token_issued user_id=<id> scope=<full|enroll> amr=<webauthn|pwd+otp|pwd> device=<known|new|-> via=<login|otp|approval|passkey|refresh> request_id=<承認の依頼の id か ->`
  - device は、6桁の口と承認待ちの口でだけ known か new を書く。パスキーと refresh とパスワードだけの口は `-`。

### 3-3. 認証アプリの6桁

- 表 `public.user_totp`（1人1行）: user_id INT PK FK users.id ON DELETE CASCADE / secret_encrypted TEXT NOT NULL / confirmed_at TIMESTAMPTZ / last_used_timecode BIGINT / created_at TIMESTAMPTZ NOT NULL DEFAULT now()。RLS なし・salesanchor_app に GRANT（ADR-1013 の表と同じ: migrations/20261013_160000_add_self_hosted_auth_tables.sql:3,95-101）。
- 秘密は既存の `encryption.encrypt`（backend/app/services/encryption.py:100）で暗号化して保存する。新しい鍵・新しい暗号部品は作らない。列名が `_encrypted` で終わるので、読み取りの道で自動で隠れる（backend/app/ops/readonly_query.py:42）。手で入れない（CLAUDE.md ADR-025 常時厳禁）。
- 部品: pyotp 2.10.0。`verify_and_get_timecode`（valid_window=1）で照合し、返った timecode が `last_used_timecode` 以下なら拒否（使い回し防止・K5）。成功時に `last_used_timecode` を更新する（同じ UPDATE の WHERE で古い値を条件にし、同時の2回目を落とす）。pyotp の関数名と引数は 7b のカードを書く前に公式の資料で確かめる（Context7 か PyPI の公式ページ）。
- **パスワードと6桁の間の引き継ぎ（指摘4）**: 2段階を設定済みの人のパスワードが合ったら、トークンは出さず「6桁待ちの券」を作る。券は Redis に5分・1回限りで、中身は user_id と残りの試行回数（3回）。券の id は HttpOnly・Secure・SameSite=Strict の cookie で渡す（path は §3-4 の表）。1人に有効な券は1枚だけにする。新しい券を作るときは、その人の古い券を消す。6桁の口は券と6桁を受け取り、合えば券を消して §3-2 の判定へ進む。3回外れたら券を消し、パスワードからやり直させる。
- **失敗の数え方（指摘4）**: 今の login はパスワードが合うと `failed_login_count` を0に戻す（backend/app/routers/auth.py:293-299）。このままでは「パスワード→6桁を3回外す」を繰り返すと、6桁の失敗に上限が無い。そこで、2段階を設定済みの人は、パスワードが合っても `failed_login_count` を戻さない。戻すのは2段階目まで通ったときだけにする。6桁の外れも同じ `failed_login_count` に1足し、10回で15分止める（:280-285 の今の動き。新しい数え方・新しい列は作らない）。6桁が外れたら `record_auth_failure(ip)` も呼ぶ（パスワードの外れと同じ。auth.py:289）。
- **止まっている人は6桁の口でも拒む**: 今の login は止まっているかを入口でだけ見る（auth.py:264）。6桁の口でも、券の user_id の `locked_until` が今より後なら、券を消して拒む。これで、止まる前に作った券で試し続けることはできない。1人1枚の券と合わせると、6桁を試せる回数は「15分ごとに10回まで」になる。
- 設定の流れ: 秘密を作る → QR を出す（§3-7）→ 6桁を1回打って合っていれば `confirmed_at` を入れる。合うまでは未設定のまま。
- 2段階が設定済みの人が6桁を設定し直す・消すときは、今ある要素（パスキーか今の6桁）で確認し直す（OWASP「要素の変更は既存の要素で再確認」）。

### 3-4. いつもの機器

- 表 `public.user_trusted_devices`: id BIGSERIAL PK / user_id INT FK users.id ON DELETE CASCADE / token_hash BYTEA UNIQUE NOT NULL（cookie の値の SHA-256。値そのものは保存しない）/ label TEXT（ブラウザ名など表示用）/ created_at / last_used_at / revoked_at。
- cookie: 32バイトの乱数、HttpOnly・Secure・SameSite=Strict・有効180日。書き方は refresh cookie（backend/app/routers/auth.py:211-221）にそろえる。名前は refresh cookie（`sa_refresh`、self_tokens.py:25）と別にする。
- **2段階の口と cookie の置き場所**: 2段階の口はすべて `/api/v1/auth/2fa/` の下に置く。cookie の path は前方一致で効くので、下の表のとおりにする。refresh の cookie（path `/api/v1/auth`、self_tokens.py:26）は2段階の口にも届くが、2段階の口は読まない。cookie を立てる応答はどの口でもよい（パスキーの口がいつもの機器の cookie を立てる場合も同じ）。

| cookie | 中身 | path | 読む口 |
|---|---|---|---|
| いつもの機器 | 32バイトの乱数（DB には SHA-256 だけ） | `/api/v1/auth/2fa` | 6桁の口（known か new を決める）・承認の一覧と回答の口・機器の一覧と取り消しの口 |
| 6桁待ちの券 | 券の id | `/api/v1/auth/2fa/otp` | 6桁の口だけ |
| 承認待ち | 依頼と組にした乱数 | `/api/v1/auth/2fa/pending` | 承認待ちの口だけ |

- refresh は機器を見直さない（§3-2。ログは `device=-`）。
- いつもの機器になる時: (1) 管理者が2段階の設定を終えた機器 (2) パスキーで入った機器 (3) 承認で入れた機器。
- 一覧と取り消し: 管理者は自分の「いつもの機器」を画面で見て消せる。消すとその機器からの次のログインは初めて扱い。
- 判断に場所（IP）は使わない（スマホは移動で変わるため。PO に 2026-10-27 説明済み）。

### 3-5. 初めての機器の承認（番号を選ぶ形）

1. 初めての機器で「パスワード＋6桁」が合ったら、トークンは出さず承認依頼を作る。依頼は Redis に5分・1回限り（パスキーの challenge と同じ置き方: docs/handoff/auth-self-hosted-passkey/design.md:80）。中身は user_id・正しい2けたの番号・候補3つ・依頼の id・依頼した機器のブラウザ名（User-Agent から作る短い表示名）と時刻。依頼を作ったら backend ログへ `admin_login_pending user_id=<id> request_id=<依頼の id>` を1行出す（K4）。
2. 初めての機器の画面に、正しい番号を大きく出して待つ。依頼の id は、初めての機器にだけ渡す乱数（HttpOnly・Secure・SameSite=Strict の cookie、5分）と組にして Redis に置く。承認後のトークンは、この cookie を持つ機器だけが受け取れる（依頼の id を盗み見られても、別の機器では受け取れない）。
3. いつもの機器へ知らせる:
   - 開いている画面: ADR-1016 の SSE 1本（`GET /api/v1/events/stream`）に人単位の宛先 `rt:u:{user_id}` を足す。新しい通り道は作らない。知らせの中身は「承認依頼がある」という topic の名前だけで、番号は載せない。画面は API で依頼を取りに行く。必要な変更は §3-9。
   - メール: 承認の知らせを送る。今の送信部品 `_send_reset_mail`（backend/app/services/auth_mail.py:73-93）は再設定のメール専用（本文に reset_url を差し込む）なので、7b で「件名と本文を受け取って送る」共通の関数に分け、再設定と承認の両方から呼ぶ（指摘12）。メールは「セールスアンカーを開いて承認してください」と依頼した機器のブラウザ名・時刻だけを書く。承認のボタンやリンクは置かない（偽のメールで承認させられるのを防ぐ）。メール設定が無いときは送らずログだけ（backend/app/services/mail_config.py:28-35 の今の動き）。
4. いつもの機器の画面に Modal で、依頼した機器のブラウザ名と時刻、候補の番号3つ、「心当たりがない」を出す（指摘9）。全権トークンを持ち、いつもの機器の cookie がある画面だけが見られる。
5. 正しい番号を選ぶ → 依頼が承認になり、backend ログへ `admin_login_approved user_id=<id> request_id=<依頼の id>` を出す。初めての機器が待ちの口で全権トークンと「いつもの機器」cookie を受け取る。違う番号か「心当たりがない」→ 依頼を取り消し、`admin_login_rejected user_id=<id> request_id=<依頼の id>` を出す。初めての機器は入れない。本人にメールで知らせる（K7）。
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

### 3-9. 即時反映（ADR-1016）への追加（指摘5）

ADR-1016 は topic の範囲を tenant と global に決め（決定3）、宛先を `rt:t:{tenant_id}` と `rt:global` に決めた（決定6。ADR-1016:23-24）。改訂 2026-10-18 で `rt:shared` が足されている（:37）。人単位の宛先はどこにも無い。本件で次を足す。

- topics.py に範囲 `SCOPE_USER` を足し、承認の知らせの topic をこの範囲で1つ置く。
- 宛先 `rt:u:{user_id}` を足す。publisher はこの範囲の topic を、この宛先にだけ出す。
- hub の接続（backend/app/realtime/hub.py:28-31 の Connection。今は tenant_id と is_super_admin だけ）に user_id を足し、配る先を決める処理（hub.py:34-45）で、同じ user_id の接続にだけ配る。
- 承認の知らせは、承認依頼を作る処理の中で明示的に publish する。middleware（ADR-1016 決定4）は書き込みの経路から宛先の人を知れないため使わない。これは決定5（裏の処理は明示的に publish）と同じ扱いにする。
- 本件で足す書き込みの経路（`/api/v1/auth/2fa/` の下の POST・DELETE）は、`NO_SIGNAL_ROUTES`（backend/app/realtime/topics.py:86）に理由付きで載せる。載せないと決定8の CI が赤になる。既存の login・refresh も同じ表に載っている（topics.py:100・:124）。
- ADR-1016 の本文には、今までの改訂と同じ形の「改訂」の節を 7b の PR で足す（ADR-1048 が Accepted になってから）。本書の段階では ADR-1016 を書き換えない。

## 4. 対象と対象外

- 対象: 管理者の2段階の必須化、認証アプリの6桁、いつもの機器、初めての機器の承認、QR の金型、SSE の人単位の宛先と ADR-1016 の改訂（§3-9）、承認の知らせメールと送信部品の共通化、refresh の表への amr 列、管理者の Firebase トークンの拒否。
- 対象外: 管理者でない人への必須化（ADR-1013 Decision 7 のまま任意）、スマホの通知（Web Push。PO 2026-10-27 選ばず）、予備コード（PO の要望なし）、管理者でない人の Firebase 経路の MFA（便6 で撤去）、パスキーそのものの実装（ADR-1013 便5）。

## 5. 便の分け方と順番

ADR-1013 の便3（メール・PO の画面作業）→ 便4（切替）→ 便5（パスキー）の後に置く。7d は便4 の後なら、便6（Firebase の撤去）を待たずに切り替えてよい。理由は、§3-2 で管理者の Firebase トークンを拒むため。

| 便 | 中身 | 危ない道 |
|---|---|---|
| 7a | migration: user_totp・user_trusted_devices（構造だけ）、auth_refresh_tokens に amr 列 | migrations/ → PO GO（ADR-136） |
| 7b | backend: 6桁・6桁待ちの券・いつもの機器・承認・発行の判定（login と refresh）・scope の確認・管理者の Firebase トークンの拒否・SSE の人単位の宛先と ADR-1016 の改訂・メール部品の共通化・ログ行。設定 `ADMIN_2FA_ENFORCED`（既定 false）。false の間は判定せず記録だけ | なし（deploy.yml を触らないこと） |
| 7c | frontend: 設定画面・6桁の画面・待ちの画面・承認の Modal・QrCode 金型 | なし |
| 7d | 3人が設定を終えたことを K1 で確かめる。管理者の今の refresh の組を全部失効させる。そのあと `ADMIN_2FA_ENFORCED=true` にする | secrets・本番設定・本番データ → PO GO |

- 7d の前に K1=0 でなければ切り替えない（PO 本人が閉め出されるのを防ぐ）。
- 7d の前に、試験の自動ログインに使う利用者（qa-admin）が §3-1 の判定で管理者に当たらないことを、本番の読み取りで確かめる。当たる場合は切り替えずに止めて相談する（切り替えると試験の自動ログインが6桁で止まるため）。
- 7d の組の失効は、amr 列（7a）だけでも強さは守られる。それでも、切替の前に出た組を残さないために行う（二重の守り）。失効の台本は本番データの変更の決まり（DRY-RUN・件数ガード・戻し）に従う。失効させる組の持ち主は §3-1 の判定（super admin、または会社の権限キーで管理者）で選ぶ。users の role 列では選ばない。

## 6. 代わりの案と選んだ理由

| 案 | 選ばなかった理由 |
|---|---|
| 6桁で入れる範囲を「新しいパスキーの登録だけ」にする | PO が「どちらでも全部使える」を選んだ（2026-10-27）。代わりに初めての機器の承認で偽の画面への弱さを小さくする（埋めきれない分は §7） |
| 押すだけの承認（Meta 型） | 何度も送りつけられて押してしまう手口がある。番号を選ぶ形と作る量はほぼ同じ |
| スマホの通知（Web Push） | 部品が0から。iPhone はホーム画面への追加が必要 |
| users に 6桁の列を足す | ADR-1013 Decision 2「ログイン情報は子表」に合わない |
| 新しい暗号部品・新しい鍵 | 既存の encryption.py で足りる |
| 場所（IP）で「いつもと違う」を決める | 本人が移動しても止まる |
| refresh で amr を持たず、7d で管理者の組を失効させるだけにする | 切替の後に「pwd だけ」で作られた組が残らないことを、毎回の refresh で確かめられない。列を足す方が確かめやすい |
| 7d を便6（Firebase の撤去）の後に置く | 便6 は PO の画面作業が要り時期が読めない。管理者の Firebase トークンを拒めば足りる |
| パスワードと6桁を1回の要求で同時に送る | 6桁を設定していない人と画面を分けにくい。券の形でも失敗の上限は §3-3 で守れる |

## 7. 危険と対処

| 危険 | 対処 |
|---|---|
| PO 本人が閉め出される | 7d の切替は K1=0 を確かめてから。§3-6 の運用台本。戻し: `ADMIN_2FA_ENFORCED=false` |
| 設定前にパスワードを盗まれ、他人に6桁を設定される | 設定だけのトークンは15分・設定の口のみ。設定完了をメールで本人に知らせる。切替前に3人が設定を終える |
| 承認の通知を何度も送られる | 番号を選ぶ形・1時間3件まで・違う番号で取り消し |
| **残る危険**: 偽のログイン画面にパスワードと6桁を打たせ、偽の画面が本物の番号を中継して、本人に承認させる | 承認の Modal に依頼した機器のブラウザ名と時刻を出し、本人が気づける形にする。完全には防げない。完全に防げるのはパスキーだけ（NIST 3.2.5）。PO の決定5（どちらでも全部使える）を守る代わりに残る危険として記録する |
| 管理者の判定が失敗する | 管理者として扱う（§3-1。閉じる側） |
| 切替の前に作られた refresh の組で、弱いまま全権が続く | amr 列で毎回確かめる。7d で管理者の組を失効させる |
| メールがまだ送れない | 画面の知らせだけでも承認できる。メールは便3 の PO 作業後に届く |
| SSE の変更で既存の即時反映が壊れる | 宛先を足すだけ。既存の会社単位・全体・共通の配信の試験を残す |
| 審査用の管理者（tenant-review）が設定できない | 対象に含める（PO 決定）。設定は PO が行う |

## 8. 外部・過去事例の参照と我々への応用

| 出典（日付） | 内容 | 我々への応用 | 適用の限界 |
|---|---|---|---|
| NIST SP 800-63B-4（2025-08-26）3.2.5・付録B | 手で打つ OTP はフィッシングに強いと見なさない。同期型パスキーは AAL2 まで | パスキーは機器を問わず全権、6桁は初めての機器で承認を要る | 連邦向けの基準。管理者に限った要求は本文に無い |
| OWASP MFA Cheat Sheet | 格下げの防止・要素の変更は既存要素で再確認・OTP 1回限り・回数制限 | §3-3 の使い回し防止・失敗の数え方・再確認 | 数値の基準は無い |
| Google ログイン確認（support.google.com/accounts/answer/7026266） | いつもと違う入り方のときだけ番号を合わせる確認 | §3-5 の形をそのまま採る | Google は自社アプリへの通知。我々は画面＋メール |
| Uber 2022（セキュリティ会社の記事 centrexit.com） | 押すだけの承認を繰り返し送られ、押してしまった | 番号を選ぶ形と回数の上限 | Uber の公式発表は未確認。数値は使わない |

## 9. 維持の仕組み

- 自動試験（backend/tests/ に置く。7b のカードで名前を決める）: K2・K4・K5・K7 を試験で守る。あわせて、refresh で amr が引き継がれること、amr が NULL の組で管理者に全権が出ないこと、scope="enroll" で設定の口以外が 403 になること、管理者の Firebase トークンがキャッシュの有無どちらでも 401 になること、6桁の外れが `failed_login_count` に数えられパスワード成功で戻らないこと、を試験で守る。さらに次も試験で守る: scope="enroll" のトークンは2回目の要求（キャッシュの後）でも 403、自社トークンの管理者は2回目の要求でも通る、パスキーの組を refresh しても全権が続く、Firebase の道で管理者の判定が失敗したら管理者として 401、止められた後は6桁の券が使えない、新しい券を作ると古い券は使えない（1人1枚）。
- UI ガバナンスの CI（docs/CC_UI_GOVERNANCE.md）: K6。
- 毎週の点検: K1 を本番の読み取りで数える（新しく管理者になった人が未設定のままでないか）。K2・K4 を本番ログで数える。
- 守り手: 設計パートナー（Opus）。仕様書の索引 docs/specs/auth-login/README.md に本書を載せる。
