# recon: 自社ログイン中も、サーバーが Firebase のログイン札を受け付ける

- 書いた日: 2026-11-04（Opus・コードの読み取り）
- 基準: origin/main `b6b999d01`（worktree `release/block-firebase-token-in-self`）。本番では試していない。
- 既存 ADR の検索: `docs/adr/ADR-1013-self-hosted-auth-and-passkey.md`（自社ログイン）、ADR-127（認証の順序）、ADR-1017（smoke の最小権限）、ADR-1055（知らない機械の承認・D8 組の失効）。新しい ADR は要らない（ADR-1013 の Decision 6「切替はスイッチ AUTH_PROVIDER で行う」を、サーバーの受け付けにも効かせる直し）。

## 1. 事実（コード）

| # | 事実 | 根拠 |
|---|---|---|
| R1 | 全 API の認証の出口は `get_current_user` 1 つ | `backend/app/auth/dependencies.py:137-283` |
| R2 | 自社の札（`iss=salesanchor`）だけを自社の確かめに回す | `backend/app/auth/dependencies.py:230-232` |
| R3 | それ以外の札は Firebase で確かめる。この前に `AUTH_PROVIDER` を見る分かれ道は無い | `backend/app/auth/dependencies.py:234-242` |
| R4 | 二段階の確認は `MFA_REQUIRED` のときだけ。本番は false | `backend/app/auth/dependencies.py:245-252`・ADR-1013 Context（本番は MFA_REQUIRED=false） |
| R5 | Firebase で通った札は email で利用者を引き、結果を 300 秒の一時記憶に入れる | `backend/app/auth/dependencies.py:254-281`・`backend/app/cache.py:15`（`JWT_CACHE_TTL = 300`）・`:72-81` |
| R6 | 一時記憶に当たった札は、種類を見ずに通る（②） | `backend/app/auth/dependencies.py:213-221` |
| R7 | Firebase の札を確かめる所は、サーバー全体でここ 1 か所だけ | `git grep -n verify_id_token backend/app` の結果が `backend/app/auth/dependencies.py:236` の 1 行だけ |
| R8 | スイッチの読み方: `auth_provider()` は環境変数 `AUTH_PROVIDER`（既定 `firebase`）を毎回読む | `backend/app/auth/self_tokens.py:21`・`:39-40` |
| R9 | 札の発行元の読み方: `peek_issuer()` は署名を見ずに `iss` を読む。読めなければ None | `backend/app/auth/self_tokens.py:111-117` |
| R10 | 本番は `AUTH_PROVIDER=self`、画面も `VITE_AUTH_PROVIDER=self` | `.github/workflows/deploy.yml:378`・`:380` |
| R11 | 画面は自社ログインのとき自社の札だけを API に付ける | `frontend/src/lib/auth/selfAuth.ts:223-232`（`isSelfAuth()` なら `ensureSelfToken()`） |
| R12 | sid（今のログインの組）を求めるのは機械の承認・拒否・一覧・取り消しの API だけ。他の API は `get_current_user` だけで通る | `backend/app/auth/dependencies.py` の `resolve_current_session`・`backend/app/routers/auth.py:768` |
| R13 | 移行の設計は「API の受け付けは便2〜便5 の間、両方の札を受ける」と決めていた | `docs/handoff/auth-self-hosted-passkey/design.md:120` |
| R14 | Firebase の利用者と元のパスワードは便6 まで消さない（移行時にパスワードを持ち出していない） | ADR-1013 Decision 4・6、`docs/handoff/auth-self-hosted-passkey/design.md:158`・`:160` |
| R15 | 戻し方は「`AUTH_PROVIDER` と `VITE_AUTH_PROVIDER` を `firebase` に変える前進 PR」 | `docs/handoff/auth-self-hosted-passkey/design.md:158`（便4b の戻し方の欄） |
| R16 | 試験の環境は既定で `AUTH_PROVIDER` を置かない（＝firebase）。自社ログインの試験だけ self にする | `backend/tests/test_self_auth.py:36-42`・conftest に `AUTH_PROVIDER` の行は無い（`grep -rn AUTH_PROVIDER backend/tests/conftest.py` が 0 行） |
| R17 | smoke の札は①より前で返るので、この直しの影響を受けない | `backend/app/auth/dependencies.py:164-191` |
| R18 | IP の回数確認（③）は一時記憶に外れたときだけ、Firebase の確かめの前で動く。既存の試験は「回数超え→429」を期待している | `backend/app/auth/dependencies.py:224-228`・`backend/tests/test_security_hardening.py:170-181` |

## 2. 意味

本番は自社ログインに切り替わっている（R10）。それでもサーバーは Firebase の札を確かめて通す（R3）。二段階の確認も無い（R4）。Firebase に昔のパスワードが残っている（R14）。そのため、昔のパスワードを知っている人は、自社のログインも、顔・指紋の確認も、知らない機械の承認（ADR-1055）も通らずに API を使える。

R13 のとおり、両方の札を受けるのは計画どおりだった。ただし本番の画面は自社の札しか送らない（R11）。そのため、今 Firebase の札を受け付けても、正規の利用者には何の役にも立たない。

## 3. 未確認

- Firebase に今いる利用者の数と、そのパスワードが今も使えるか（Firebase の画面でしか見えない）。
- 本番で Firebase の札が実際に通るか（試すには本物のパスワードが要る。試していない）。
- 今日までに Firebase の札で API が使われたか（本番の記録の読み方を決めていない）。
