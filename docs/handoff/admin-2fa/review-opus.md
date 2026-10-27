# 設計審査 — 管理者ログインの2段階の確認

> この文書は何か：設計書が実装に渡せる形になっているかを、設計者と同じ AI（Opus）が Architect の立場で確かめた記録です。独立した第二者の審査ではありません。

親: [design.md](design.md)

**日付**: 2026-10-27
**審査した人**: 設計パートナー（Opus・Architect 役。設計者と同一 AI）
**判定**: 第1版 APPROVE（自己審査）→ 別に起動した Opus の審査役が REQUEST_CHANGES（2026-10-28）→ 第2版で全12点に対処し、再審査待ち（§5）。どの判定も PO の実装承認・GO を兼ねない。

## 1. 照合した事実（origin/main・2026-10-27 fetch 後）

| 設計の記述 | 照合先 | 結果 |
|---|---|---|
| 管理者の判定の正本 | backend/app/auth/dependencies.py:516（require_super_admin）、:547（get_user_system_keys）、:606（require_tenant_admin）、backend/app/auth/system_roles.py:17 | 一致 |
| ログイン情報は子表 | docs/adr/ADR-1013-self-hosted-auth-and-passkey.md:23（Decision 2） | 一致。user_totp・user_trusted_devices は子表 |
| 6桁は範囲外・任意 | ADR-1013:30（Decision 7） | 管理者についてだけ広げる。ADR-1048 に関係を明記 |
| refresh cookie の書き方 | backend/app/routers/auth.py:211-221（HttpOnly・Secure・SameSite strict） | いつもの機器の cookie を同じ書き方にそろえる |
| refresh で止めた人を拒否 | backend/app/auth/self_tokens.py:227-228、発行は backend/app/routers/auth.py:319-347 | 一致。ただし :344 で amr を引き継がない（第2版で対処。§3） |
| Redis に5分・1回限り | docs/handoff/auth-self-hosted-passkey/design.md:80 | 同じ置き方 |
| 暗号部品 | backend/app/services/encryption.py:100 | 一致 |
| 子表の GRANT・RLS なし | migrations/20261013_160000_add_self_hosted_auth_tables.sql:3,95-101 | 同じ形にする |
| メールが送れないときはログだけ | backend/app/services/mail_config.py:28-35 | 一致 |
| 6桁の入力枠 | frontend/src/components/TextField.tsx:43（InputHTMLAttributes を受ける :37） | 新しい金型は不要 |
| 金型の作法 | docs/CC_UI_GOVERNANCE.md:13-15 | QrCode は PO 許可済み（2026-10-27「1」） |
| cryptography の版 | backend/requirements.txt:24（48.0.1） | py_webauthn 2.8.0 で両立 |

照合の生出力: 手元の控え /tmp/CC報告ファイル/auth-2fa/design-linecheck.txt（134行）。

## 2. 観点ごとの判定

| 観点 | 判定 | 根拠 |
|---|---|---|
| データと配線を分散させない | 合格 | 管理者の判定は既存の関数、置き場は users の子表、知らせは既存 SSE 1本とメール部品、暗号は既存部品。新しい名簿・通り道・鍵なし |
| 金型とトークン | 合格 | 6桁は TextFieldControl、承認は Modal・Button。新設は QrCode だけで PO 許可済み・var() のみ・stories あり |
| 目標が数で測れる | 合格 | K1〜K7 に基準値（未測定はその旨）と測り方。K1 は本番読み取り、K2・K4 はログ行、K4・K5・K7 は自動試験、K6 は CI |
| 範囲がはっきりしている | 合格 | 対象と対象外（§4）、便 7a〜7d と危ない道（§5） |
| 閉め出しの防止 | 合格 | 既定 false の設定で入れ、K1=0 を数えてから PO の GO で切り替え。戻しは false |
| 外部の根拠 | 合格 | NIST・OWASP・Google は公式本文を 2026-10-27 に直接読んだ。Uber の件は記事のみで公式未確認と明記し、数値に使わない |

## 3. 審査で直した点

- 承認後のトークンを、依頼を出した機器だけが受け取れるようにした（依頼の id と機器の cookie を組にする。design.md §3-5 の2）。
- 設定だけのトークンには refresh cookie を出さないことを明記した（§3-2）。
- いつもの機器が1台も無い人は「パスワード＋6桁」で入れないことと、その時の道を明記した（§3-6）。

## 4. 未解決と、実装の便で最初に確かめること

| 事項 | 扱い |
|---|---|
| qrcode.react 4.2.0 に CSS 変数の色を渡せるか | 未確認。便7c の最初に確かめる。だめなら CSS で上書き、それも無理なら止めて相談（design.md §3-7） |
| メールが本番で送れるか | ADR-1013 便3 の PO の画面作業待ち。送れない間も画面の知らせで承認できる |
| 自動試験のファイル名 | 便7b の実装カードで決める |
| 全部を失くしたときの運用台本 | 便7b と同時に作る。本番データ変更の決まりに従う |
| 管理者の last_login が全員空の理由 | 未確認。本件の判定には使わないので設計に影響なし |

いずれも設計の芯（何を・どこに・どう測る）を変えない。実装に入るには、ADR-1013 便5（パスキー）の本番反映、PO の実装承認、便ごとの実装カードが要る。

## 5. 第2版（2026-10-28）— 別に起動した Opus の審査役の指摘と対処

第1版の自己審査は、下の 1〜8 を見落としていた。どれも実物（origin/main）で指摘どおりであることを確かめてから直した。

| # | 指摘 | 実物の確認 | 対処（design.md） |
|---|---|---|---|
| 1 | refresh で amr を引き継げない | backend/app/routers/auth.py:344 が amr に None を渡す。auth_refresh_tokens に amr 列なし（migrations/20261013_160000:68-81） | §3-2: 7a で amr 列を足し、組に記録して写す。NULL は pwd だけと見なす。7d で管理者の組を失効 |
| 2 | Firebase の道が残る | backend/app/auth/dependencies.py:207-213 は AUTH_PROVIDER を見ない。キャッシュに当たると :190-198 で MFA 確認なしに返る | §3-2: 必須化の間は管理者の Firebase トークンを、キャッシュの有無どちらでも 401 |
| 3 | scope=enroll をどこで確かめるか | _authenticate_self_token（:82）は request を受け取らない。get_current_user（:124）は受け取る | §3-2: _authenticate_self_token で道の一覧と照らし、amr・scope を request.state に載せる |
| 4 | パスワードと6桁の間の引き継ぎと失敗の上限 | パスワード成功で failed_login_count を0に戻す（auth.py:293-299） | §3-3: Redis の券（5分・3回）。2段階を設定済みの人は2段目まで通るまで数を戻さない |
| 5 | ADR-1016 への追加が対象に無い | hub.py:28-31 の Connection に user_id なし。宛先は rt:t・rt:global・rt:shared だけ | §3-9 を新設。§4・7b に入れる。ADR-1016 の改訂の節は 7b の PR で足す |
| 6 | K2 に scope が無い | — | §2 K2・§3-2 のログ行に scope |
| 7 | K3 の基準値が数で無い | frontend/src/pages/login/LoginPage.tsx:91-125 は1画面・3操作 | §2 K3 を「3操作」 |
| 8 | K4 のログ行が定義されていない | — | §3-5 に pending・approved・rejected の行と request_id |
| 9 | 偽の画面に番号を中継される | — | §3-5 の4: 依頼した機器のブラウザ名と時刻を出す。§7 に残る危険。ADR-1048 の「埋める」を直した |
| 10 | 判定に失敗したとき | — | §3-1: 管理者として扱う |
| 11 | いつもの機器の cookie の path | refresh は /api/v1/auth（self_tokens.REFRESH_COOKIE_PATH） | §3-4: path と名前を分ける |
| 12 | メール部品の一般化 | auth_mail.py:73-93 は reset_url 専用 | §3-5 の3: 7b で共通の関数に分ける |

引用の直し: recon.md の ADR-1016 の引用（:23-24 と rt:shared の :37）、手元の絶対パスを repo からの相対に、role 列の書き方（DB の列は未確認と明記）、mail_config の行を :28-35 にそろえた。

