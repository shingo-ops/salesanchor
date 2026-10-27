# 設計審査 — 管理者ログインの2段階の確認

> この文書は何か：設計書が実装に渡せる形になっているかを、設計者と同じ AI（Opus）が Architect の立場で確かめた記録です。独立した第二者の審査ではありません。

親: [design.md](design.md)

**日付**: 2026-10-27
**審査した人**: 設計パートナー（Opus・Architect 役。設計者と同一 AI）
**判定**: 第1版 APPROVE（自己審査）→ 別に起動した Opus の審査役が REQUEST_CHANGES（2026-10-28）→ 第2版で全12点に対処（§5）→ 再審査も REQUEST_CHANGES（必須7・任意7）→ 第3版で対処（§6）→ 3回目の審査も REQUEST_CHANGES（必須5・任意9）→ 第4版で対処し、再審査待ち（§7）。どの判定も PO の実装承認・GO を兼ねない。

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

引用の直し: recon.md の ADR-1016 の引用（:23-24 と rt:shared の :37）、手元の絶対パスを repo からの相対に、role 列の書き方（第3版で「本番に列はある・判定には使わない」に直した）、mail_config の行を :28-35 にそろえた。

## 6. 第3版（2026-10-28）— 2回目の審査役の指摘と対処

指摘は、どれも origin/main の実物で確かめてから直した。行番号の食い違いは0件、公開してはいけない情報は0件という報告だった。

| # | 区分 | 指摘 | 実物の確認 | 対処 |
|---|---|---|---|---|
| 1 | 必須 | 自社トークンがキャッシュを通り、2回目から scope と amr を見ない | dependencies.py:108 が自社トークンも cache_jwt_result に書く。当たると :190-198 で返る | design §3-2: 自社トークンの振り分けを :180-185 の直後・:190 より前へ。:108 の書き込みを消す。IP の制限は Firebase の道だけ |
| 2 | 必須 | Firebase の道で会社の権限を引けない | search_path を立てるのは get_current_tenant（:300-302）だけ。get_user_system_keys（:547-552）はそれが前提 | design §3-1: set_tenant_context → get_user_system_keys → clear_tenant_context。super admin は DB を引かない。例外なら管理者扱い |
| 3 | 必須 | トークンを出す口が漏れている | login（auth.py:238-316）・refresh（:319-347）のほかに、本件で6桁・承認待ち・パスキーの口が増える | design §3-2: 口を5つ書き、全部が共通の関数を通る。ログ行に via |
| 4 | 必須 | cookie の path が決まっていない | refresh の cookie は /api/v1/auth（self_tokens.py:26） | design §3-4: 口を /api/v1/auth/2fa/ の下に置き、cookie 3種の path と読む口を表にした |
| 5 | 必須 | 6桁の試行の上限に穴がある | 止まっているかは入口だけで見る（auth.py:264）。外れで record_auth_failure を呼ぶのはパスワードだけ（:266・:289。:249 は check_auth_rate_limit。第4版で直した） | design §3-3: 券は1人1枚、6桁の口でも locked_until を見る、外れで record_auth_failure(ip) |
| 6 | 必須 | K4 の数え方がパスキーも数えてしまう | — | design §2 K4: amr=pwd+otp かつ device=new に絞る。パスキーは device=- |
| 7 | 必須 | 止めた2人の台本の sha256 が記録と合わない | 今の版 69f3ebf0…、実行した版 58983715…（差は2行目の注記） | deactivate-7-9/README.md に両方を書いた |
| 任1 | 任意 | role 列を未確認と書いている | run-log.txt:4 の列名に role がある | recon.md:22 を直した |
| 任2 | 任意 | ログ行を管理者以外にも出す | — | design §3-2: 管理者だけ |
| 任3 | 任意 | 知らせの出し方と CI の表 | ADR-1016 決定4・5・8、topics.py:86 | design §3-9: 明示の publish、新しい口を NO_SIGNAL_ROUTES に |
| 任4 | 任意 | 管理者でない人の6桁 | — | design §3-2: 本件では出さない |
| 任5 | 任意 | 履歴に表示名が残る | 第1版のコミットに残る | マージは squash で行う |
| 任6 | 任意 | require_permission が対象外か | — | design §3-2: 対象外と明記 |
| 任7 | 任意 | 試験用の自動ログインの利用者 | — | design §5: 7d の前に qa-admin が管理者に当たらないことを読み取りで確かめる。失効の対象は §3-1 の判定で選ぶ |

あわせて §9 に試験6つを足した（enroll は2回目も 403、自社トークンの管理者は2回目も通る、パスキーの組の refresh、Firebase で判定失敗なら 401、止めた後の券、券は1人1枚）。

## 7. 第4版（2026-10-28）— 3回目の審査役の指摘と対処

指摘は origin/main の実物で確かめてから直した。行番号の食い違いは2件（下の任意4・任意9）、公開してはいけない情報は0件という報告だった。

| # | 区分 | 指摘 | 実物の確認 | 対処 |
|---|---|---|---|---|
| 1 | 必須 | 必須化の設定が変えるものが、表・refresh・二重の守り・7b の行で食い違う | design の表と refresh の 401・二重の守りの 403・7b の「判定せず記録だけ」が合わない | design §3-2: refresh は表と同じ共通の判定。二重の守りは必須化の後だけ。§5 の 7b: false の間も判定とログを行う。ADR の守り方も合わせた |
| 2 | 必須 | IP の制限を「今と同じ」と誤って書いた | dependencies.py:201 はキャッシュに当たらない自社トークンも通る。振り分けは :207-209 | design §3-2: 意図した動きの変更として理由3つを書き、§9 に試験 |
| 3 | 必須 | 出す口で判定が例外のとき、rollback で使い回し防止や組の入れ替えが消える | rotate_refresh_token は self_tokens.py:195-236 で書き込む | design §3-1: 出す口では書き込みの前に判定し、例外なら 503 でトークンを出さない。Firebase の道は 401 |
| 4 | 必須 | 同時に送ると6桁を3回より多く試せる | 試行回数の減らし方が決まっていない | design §3-3: 照合の前に Redis の DECR で減らす。1人1枚は「今の券の id」1つで照合 |
| 5 | 必須 | 待ちの画面の問い合わせが nginx の回数制限に当たる | nginx/nginx.conf:6（IP ごとに1分10回）・:144-146・:406-408（burst=5） | design §3-5 の7: 15秒ごと、いつもの機器は知らせを受けたときだけ。2台で1分8回。nginx は変えない |
| 任1 | 任意 | パスキーの口にいつもの機器の cookie が届かない | path が /api/v1/auth/2fa | design §3-4: パスキーの後に画面が「この機器を登録」の口を1回呼ぶ |
| 任2 | 任意 | require_super_admin を直接呼ぶ所がある | backend/app/routers/realtime_events.py:31 | design §3-2 と §5 の 7b に入れた |
| 任3 | 任意 | users を引く回数 | dependencies.py:93-98 と :105 の2回 | design §3-2 を直した |
| 任4 | 任意 | record_auth_failure の行番号 | auth.py:249 は check_auth_rate_limit。record_auth_failure は :266・:289 | 本書 §6 の表を直した |
| 任5 | 任意 | 6桁の口の入口の IP の確認と、再確認の口の上限 | — | design §3-3 に書いた |
| 任6 | 任意 | enroll の照合のしかたと request の渡し方 | :82 は request を受け取らない | design §3-2: ルートのひな形で照合、get_current_user から渡す |
| 任7 | 任意 | K2 の「切替」がどれか | — | design §2 K2: 7d の後は毎週0。7d の前は設定済みの管理者について0 |
| 任8 | 任意 | Firebase の道でキャッシュに当たったときの負荷 | :330・:414 の中の SET | design §3-2 に書き足した |
| 任9 | 任意 | 金型の作り方の行の範囲 | CC_UI_GOVERNANCE.md:15 が作り方 | design §3-7 を :13-15 に |
