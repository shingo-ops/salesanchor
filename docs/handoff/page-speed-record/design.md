<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# 設計 — 本番の全画面の速さを毎日記録する（判定なし）

この文書は何か: 毎朝の本番の画面点検のついでに、アプリの全画面を 1 つずつ開いて「開き終わるまで何秒かかったか」を測り、遅い順の表として残す仕組みの設計です。

**対象ADR**: ADR-1053（`docs/adr/ADR-1053-prod-page-speed-record.md`）
**recon**: `docs/handoff/page-speed-record/recon.md`
**日付**: 2026-10-31
**担当**: Planner／Architect（Claude Opus。同じ AI の自己審査であり、独立した第二者の審査ではない）
**状態**: 設計案作成済み。KGI は PO の言葉から起こした（下記 1）。秒数の合格ラインは PO が決める（この設計では決めない）

---

## 1. あるべき姿（PO の言葉のまま）

- 「データ（商品・投稿）が増えても、お客さんが遅いと感じる前に機械で気づけるようにする」
- 「どの画面を何秒以内にするかの基準を、私と数で決めるところから」
- 「全ページを対象にしたい、ボトルネックを特定するために遅い順に対応するべき、現状把握を推測は禁止して…精度が高いエビデンスを確立して安全に」
- PO 選択「1」（2026-10-31）: まず本番の全画面の今の速さを測る。次にテスト環境でデータを 1 倍・3 倍・10 倍にして測る

この設計は 2 便に分ける（1 便 = 1 つの変更。前の便を測ってから次へ）。

- 便0: 今の毎朝の点検が、ログイン後の 4 項目で毎回失敗している不具合を直す（2026-10-31 の試し実行で判明・recon §4 追記）。直さないと毎朝 Discord に誤った知らせが届き、便1 の「今の点検の合否を変えない」も確かめられない
- 便1: 全画面の速さの記録を足す

便1 が受け持つのは「本番の全画面の今の速さを、機械が毎日測って遅い順に残す」まで。秒数の合格ライン（何秒を超えたら知らせるか）は、記録が貯まってから PO が数で決める。データを増やした試験は別の便。

## 2. KGI（○×で測る）

| # | 合格条件 | 測り方 | 合格ライン |
|---|---|---|---|
| G0（便0） | 毎朝の点検 S1〜S8 が、点検用の人で最後まで動いて合格する | 作業ブランチで手動実行 1 回、実行記録の `passed`・`failed`・`skipped` の数 | 0 failed。8 passed、または S6 だけが「会社 0 件」で skip の 7 passed・1 skipped（2026-10-31 設計再審査 should 1） |
| G1 | 毎朝の点検の実行記録に「画面の速さ（遅い順）」の表が出る | 手動実行 1 回の実行記録の要約を開く | 表が在る=1 |
| G2 | 表に載る画面の数（測れた＋測れなかった理由つき） | 表の行数を数える | 135/135 |
| G3 | 測るあいだに本番へ送った書き込み（ログインとその続き以外） | 表の下の「止めた送信」と、Prometheus の同じ時間帯の POST/PATCH/PUT/DELETE の回数 | 0 件 |
| G4 | 表に会社・人・商品などの中身（名前・番号・金額）が出ない | 表の全行を目で見て、道すじは `:id` の形だけ | 0 件 |
| G5 | 遅い・測れない画面があっても、今の点検の合否と Discord の知らせは変わらない | 速さの記録だけが失敗する回で、仕事全体の結論と知らせの有無を見る | 合否が変わらない=1 |
| G6 | 毎朝の点検の終わる時間 | 実行記録の所要時間 | 50 分以内 |

## 3. KPI

- 達成 KGI 数 ◯/6（初回の手動実行で数える）

## 4. recon（要点。全文は `docs/handoff/page-speed-record/recon.md`）

- 画面ごとの速さの警報は無い。今ある `BackendHighLatency` は全操作まとめての割合で、使われる回数が少ない画面の遅さは埋もれる（recon §1・§2）
- 30 日で 198 種の操作のうち 162 種は 20 回未満。サーバーの記録だけでは大半の画面を判定できない（recon §2）
- 画面は 135 件（recon §3）。入口の守りはログインだけで、権限が足りない画面も開いて中の API が 403 を返す（`frontend/src/components/ProtectedRoute.tsx`）
- 点検用の人は見るだけの役割（recon §4）。会社・人・商品の中身の多い画面は 403 になる見込み → 測れたかどうかを行ごとに出す
- 開くだけで書き込む GET が 2 本ある（recon §5）。ずっと開いている通信が 1 本ある（recon §6）

## 5. design（技術 How）

### 5-0. 便0: 今の点検の待ち方を直す

> 2026-10-31 追記: 同じ不具合を別の担当が PR #4923 で先に直し、本線へ入った（`tests/prod-check/fixtures.ts` で worker ごとに 1 回ログイン・test の間を 20 秒あける）。本書の PR は `tests/prod-check/prod-ui.spec.ts` を #4923 の版のままにし、5-0・5-0b のうち prod-ui.spec.ts の書き換えは取り下げた。残るのは `tests/prod-check/settle.ts`（速さの記録が使う）と `tests/prod-check/login.ts` の `authPace`・`BASE_URL` と `tests/prod-check/playwright.config.ts` の `BASE_URL` の読み込み。以下の 5-0・5-0b は経緯として残す。

事実（recon §4-2）:
- 2026-10-31 03:00 JST の手動実行（run 41103098245・41103007617）で S3〜S6 が 2 回とも失敗。8 件の失敗はすべて `page.waitForLoadState("networkidle")` の行（`tests/prod-check/prod-ui.spec.ts:40,57,72,84`）で 30 秒切れ。その手前の「画面に出たか」の確かめ（検索欄が見える等）は全部通っている
- ログイン後はアプリが開いたままの通信を `fetch` で最大 3 本持つ（2026-10-31 設計審査の指摘 M1 で 1 本から訂正）: `/api/v1/events/stream`（`frontend/src/lib/realtime/RealtimeProvider.tsx:77-84`）、`/api/v1/conversations/stream`（全画面の枠 `frontend/src/components/DesktopShell.tsx:138`・`frontend/src/components/MobileShell.tsx:108`）、`/api/v1/leads/stream`（`frontend/src/pages/leads/LeadsPage.tsx:185`）。後ろの 2 本は `frontend/src/hooks/useSSE.ts:45-51` 経由。3 本とも頭書き `Accept: text/event-stream` を付ける（`frontend/src/hooks/useSSE.ts:48`・`frontend/src/lib/realtime/RealtimeProvider.tsx:80`。`git grep -n "text/event-stream" origin/main -- frontend/src` でこの 2 か所だけ）。`networkidle` は「通信が 500 ミリ秒 0 件」を待つので、開いたままの通信があると成り立たない
- 権限の無い開いたままの通信は 403 で切れ、2 秒・4 秒…の間隔でつなぎ直す（`frontend/src/hooks/useSSE.ts:57-59`）。これも同じ頭書きなので数えない
- それまでの合格（run 41006073342）は秘密が未登録で S2〜S8 を飛ばしていただけ（`6 skipped`）
- 確かめ方: 直した後の手動実行で S1〜S8 が合格すれば、原因がこの待ち方だったことの確認にもなる（G0）

直し方:
- 新しいファイル `tests/prod-check/settle.ts` に「開き終わった」の決め方を 1 か所だけ置く（便1 もこれを使う。決め方を 2 か所に書かない）
  - `STREAM_ACCEPT = "text/event-stream"`（開いたままの通信の見分け方。道すじの一覧は持たない。新しい開いたままの通信が増えても、アプリが同じ頭書きを付ける限り直さなくてよい）
  - `LOADING_SELECTOR = '.sa-loading-block, .sa-skeleton, .loading-screen, .loading-indicator, [aria-busy="true"]'`
  - `trackApi(page)`: その page の `request`・`requestfinished`・`requestfailed` を見て、道すじが `/api/` で始まり、頭書き `accept`（`request.headers()` の小文字の名前）に `STREAM_ACCEPT` を含まない通信の「終わっていない数」と「最後に始まった・終わった時刻」を持つ
  - `waitSettled(page, tracker, opts?)`: 5-3 の 3 条件（既定 `minMs: 500`・`quietMs: 1000`・`capMs: 30000`）が揃うまで 100 ミリ秒ごとに確かめる。揃えば `{ settled: true, elapsedMs, inFlight, loading }`、上限なら `{ settled: false, elapsedMs, inFlight, loading }` を返す（`inFlight` = 終わっていない `/api/` の通信の数、`loading` = 見えている読み込み中の印の数。どちらも数だけで、道すじや中身は持たない）
  - `expectSettled(page, tracker)`: `waitSettled` を呼び、開き終わらなければ「画面が 30 秒で開き終わらない（終わっていない通信 N 件・読み込み中の印 M 件）」の文で失敗させる（2026-10-31 設計再審査 should 3。打ち切りの原因を数で見分けるため）
- `tests/prod-check/prod-ui.spec.ts` の `await page.waitForLoadState("networkidle");` 5 か所（:40,:57,:72,:84,:89）を、`await expectSettled(page, api);` に置き換える。`api` は各 test の最初（`login()` より前）に `const api = trackApi(page);` で作る
- それ以外の行・`tests/prod-check/login.ts`・ワークフローは便0 では触らない
- 見込みの危険（設計審査 M2）: S3 は `console` の error を全部数える（`tests/prod-check/prod-ui.spec.ts:31-34,41`）。全画面の枠が未読の会話の一覧と会話の開いたままの通信を呼び（`frontend/src/components/DesktopShell.tsx:128-138`）、どちらも `messaging.view` が要る（`backend/app/routers/meta_inbox.py:866-867`）。点検用の人がこの権限を持たなければ 403 の読み込み失敗が error として数えられ、待ちを直した後に S3 が別の理由で落ちうる。点検用の人の権限は未確認（recon §8 U4）。対処: 便0 の手動実行で S3 の失敗文（件数と文の種類だけ。中身の番号は出ない）を見てから決める。待ち方の直しと S3 の数え方の直しは 1 つずつ行い、混ぜない
- S3 が 403 の error で落ちたときの扱い（2026-10-31 設計再審査 should 2）: 待ち方の直しだけではマージしない（毎朝の誤った知らせが S3 の 1 件として残るため）。同じ PR に、S3 の数え方の直しを別の commit として足し、もう 1 回手動実行して G0 を数えてからマージする。数え方を直す前に、手動実行の記録で error の件数と文の種類を確かめる。数え方の直しでは、公開の実行記録には件数だけを出し、error の文そのもの（道すじの番号を含みうる）は出さない

### 5-0b. 便0 の続き: ログインの回数制限に当たらないようにする

事実（便0 の手動実行 run 41113702544・HEAD fdf0e4798・2026-10-30 19:15〜19:18 UTC。recon §4-3）:
- 待ち方の直しは効いた。S4 が合格し、30 秒切れ（networkidle）は 0 件になった
- 残りの失敗は 3 種類: S3 の console error 1 件（`Failed to load resource: ... status of 401 ()`）、S3 の再試行と S8 の 1 回目でログイン後の画面に 30 秒で着かない（`tests/prod-check/login.ts:23`）、S5・S6 で検索欄が 10 秒で見えない
- 本番の入口の記録（Loki `{job="containerlogs"}`、点検の機械の IP だけ）で、この 3 分間に `/api/v1/auth/` への通信が 31 件あった。うち 429（多すぎる）が 7 件: ログイン 2 件（19:16:18・19:17:48）と、会社一覧での読み直し（`/api/v1/auth/refresh`）5 件（19:16:56〜19:17:34。参照元 `/crm/companies`）
- 429 は入口（nginx）の制限: `/api/v1/auth/` は 1 つの IP から 1 分 10 件、まとめて 5 件まで（`nginx/nginx.conf:6`・`nginx/nginx.conf:144-146`（もう 1 つの入口 `nginx/nginx.conf:406-408` も同じ））
- 新しい画面を読み込むたびに、アプリは `/api/v1/auth/refresh` を 1 回呼ぶ。ログイン画面では、まだ入っていないので 401 が返る。これは毎回起きる正常な動き（記録の 401 はすべてこの形。19:16:10 から 19:18:21 まで、参照元 `/login` の refresh は毎回 401）
- 今の点検は test ごとにログインし直す（`tests/prod-check/prod-ui.spec.ts` S3〜S6・S8 の `login()`）。1 回のログインで `/api/v1/auth/` を 2 件使う（`/login` を開いたときの refresh 401 と POST login。ログイン直後は読み込み直しが無く refresh を呼ばない: `frontend/src/lib/auth/selfAuth.ts:103-106`・`frontend/src/pages/login/LoginPage.tsx:50`。設計審査 5-0b の項目 1）。`page.goto` 1 回でさらに 1 件使う（`frontend/src/contexts/AuthContext.tsx:104-108`）。このため 1 分 10 件を超える
- つながり: 会社一覧の読み直しが 429 になる → アプリはログイン画面に戻る → 検索欄が出ない（S5・S6）。ログインが 429 になる → ログイン後の画面に着かない（S3 の再試行・S8）。S3 の 401 は、ログイン画面で出る正常な 401 を、S3 が `login()` より前から数えていたため
- 同じ時間帯に 403 は 0 件（設計審査 M2 の心配は起きていない。recon §8 U4 は「403 は出ていない」まで確認）
- Playwright の公式文書（https://playwright.dev/docs/test-retries 2026-10-31 確認。Context7 は月の上限で使えず、直接確認）: `test.describe.configure({ mode: 'serial' })` では 1 つ落ちると残りは飛ばし、再試行はまとめて最初からやり直す。1 つの page を `beforeAll` で作って test の間で使い回す書き方が載っている

直し方（入口の制限は本番を守る仕組みなので変えない。点検の側を制限の内側に収める）:
- `tests/prod-check/login.ts` に `authPace()` を足す。前回の呼び出しから 8 秒たつまで待つ。最初の呼び出しも、ファイルを読み込んだ時刻から 8 秒待つ（再試行は別の作業者で最初からなので、その分も数える）。8 秒の根拠は `nginx/nginx.conf:6` の 1 分 10 件（6 秒に 1 件）より遅くするため、と注に書く
- ログイン後の点検（S2〜S6・S8）を 1 つの `test.describe` にまとめ、`mode: 'serial'` にする。page は `beforeAll` で 1 つ作り、`api = trackApi(page)` もそこで 1 回だけ作る。ログインは S2 の 1 回だけにする（S3〜S6・S8 の `login()` を消す）
- 秘密情報が無いときは、まとめ全体を飛ばす（設計審査 5-0b の must）。まとめの本体の最初に `test.skip(!creds(), SKIP_REASON);` を 1 行置き、S2 の中の `test.skip` は消す。`beforeAll` の最初にも `if (!creds()) return;` を置き、page を作らない。`afterAll` は `await context?.close();`。S2 は `const { email, password } = creds()!;` で読む（ADR-1051 の「秘密情報が未登録なら skip」を保つ）
- page の作り方: `beforeAll(async ({ browser }) => { context = await browser.newContext({ ...devices["Desktop Chrome"], baseURL: BASE_URL }); context.setDefaultTimeout(15_000); context.setDefaultNavigationTimeout(30_000); page = await context.newPage(); api = trackApi(page); })`。手で作る context に config の `use` が引き継がれるかは公式文書（https://playwright.dev/docs/api/class-browser 2026-10-31 確認）に書いていないため、引き継ぎに頼らず値を渡す。`BASE_URL` は `tests/prod-check/login.ts` に `export const BASE_URL = process.env.PROD_CHECK_BASE_URL || "https://app.salesanchor.jp";` として置き、`tests/prod-check/playwright.config.ts:16` もこれを読む形に替える（値を 2 か所に書かない）。trace・スクリーンショット・動画は手で作る context では既定で作られない（ADR-1051 を保つ）
- `page.goto(...)` と `login()` と `signOut()` の前に `await authPace();` を置く（`/api/v1/auth/` を使う操作の前だけ）
- S3 の console error は、S3 の始めに数え始める（S2 のログインが済んだ後）。数え方はそのまま全部数える
- S1 と S7 は、まとめの外に置いたまま（ログインしていない page で動く）。S7 は S8 の後に動かす（ファイルの並び順を S8 の後へ移す）。S1・S7 の `page.goto` の前にも `await authPace();` を置く
- 1 回の点検で `/api/v1/auth/` を使う数の見込み（設計審査 5-0b がコードから数えた値）: S1 1・S2 2・S3 1・S4 2・S5 1・S6 1・S8 1（logout だけ。ログアウト後は読み込み直しが無い）・S7 2 = 11 件。authPace を通る操作は 9〜10 回でおよそ 80 秒
- 制限に当たらない理由: 入口は 6 秒に 1 件ずつ枠が戻り、まとめて使えるのは 5 件まで（`nginx/nginx.conf:6`・`nginx/nginx.conf:145`）。点検は 1 件を使う操作を 8 秒おき（6 秒に 1 件より遅い）に動かすので、その分は枠を減らさない。2 件を使う操作は S2 と S7 の 2 回だけで、その 1 件ずつの超過は 5 件のまとめ枠が吸収する（設計再審査 5-0b の should 1）。再試行でもう 1 回まわっても同じ間隔なので同じ
- S9（通知の試験。`PROD_CHECK_FORCE_FAIL=1` のときだけ足す）は、まとめの外で S7 の後に置き、`page.goto` の前に `await authPace();` を置く（設計再審査 5-0b の should 2）
- 触らない: `nginx/nginx.conf`・`tests/prod-check/settle.ts`・ワークフロー・backend・frontend
- 便1 への影響: 便1 は 1 回のログインのあと、読み込み直しなしで画面を切り替える（5-1）。このため refresh を使わず、135 画面でも制限に当たらない。便1 のカードに「`page.goto` は最初の 1 回だけ」と書く

確かめ方: 手動実行 1 回で 0 failed（S6 の「会社 0 件」の skip は可）。あわせて同じ時間帯の入口の記録で、点検の IP からの 429 が 0 件であることを数える（G0 の補足）

### 5-1. 全体の流れ（便1）

1. 今の点検（S1〜S8）はそのまま先に動く。合否と Discord の知らせもそのまま
2. その後に新しい段「画面の速さを記録（判定なし）」が動く
   - 点検用の人で 1 回ログインする（`tests/prod-check/login.ts` の `login()` をそのまま使う）
   - 135 画面を、アプリの中の画面切り替え（読み込み直しなし）で 1 つずつ開き、開き終わるまでの時間を測る
   - 結果を遅い順の表にして、実行記録の要約（job summary）に書く
3. この段が失敗しても仕事全体は失敗にしない（`continue-on-error: true`）。知らせも送らない

### 5-2. 変えるファイル（これ以外は触らない）

| ファイル | 変更 |
|---|---|
| `tests/prod-check/settle.ts` | 便0 で新規（5-0）。便1 で戻り値に時刻を 2 つ足す |
| `tests/prod-check/prod-ui.spec.ts` | 触らない（PR #4923 の版のまま。5-0 の追記） |
| tests/prod-check/page-speed-targets.ts | 新規。測る画面 135 件の表（5-4） |
| tests/prod-check/page-speed.spec.ts | 新規。測る本体（5-3・5-5・5-6） |
| tests/prod-check/page-speed.config.ts | 新規。この段だけの Playwright 設定 |
| `tests/prod-check/playwright.config.ts` | 1 行追加: `testIgnore: ["page-speed.spec.ts"],`（今の点検にこの段が混ざらないように） |
| `.github/workflows/prod-ui-check.yml` | `timeout-minutes: 20` → `60`。「不合格を Discord に知らせる」の後ろに段を 1 つ足す（5-7） |
| `docs/adr/ADR-1053-prod-page-speed-record.md`・`docs/adr/README.md` | 新規 ADR と索引の作り直し（`node scripts/generate-adr-index.js`） |

触らない: `tests/prod-check/login.ts`・backend・frontend・migrations・deploy.yml・監視の設定。

### 5-3. 「開き終わった」の決め方（`tests/prod-check/settle.ts` が正本）

- 便1 は便0 の `trackApi`・`waitSettled` をそのまま使い、上限だけ `capMs: 45000` を渡す。速さの記録に要る「最後の応答が終わった時刻」「読み込み中の印が消えた時刻」は `waitSettled` の戻り値に足す（便1 で settle.ts に追加）
- 画面切り替えの命令を出した時刻を 0 とする
- 次の 3 つが同時に成り立った時点で「開き終わった」とみなす
  - 0 から 500 ミリ秒以上たった
  - 読み込み中の印（`.sa-loading-block`・`.sa-skeleton`・`.loading-screen`・`.loading-indicator`・`[aria-busy="true"]`）が画面に 1 つも見えない
  - `/api/` への通信のうち終わっていないものが 0 件の状態が 1000 ミリ秒続いた。ただし頭書き `Accept: text/event-stream` の通信（ずっと開いている通信 3 本と、そのつなぎ直し）は数えない
- 記録する秒数 = 「最後の `/api/` 通信の応答が終わった時刻」と「読み込み中の印が消えた時刻」の遅い方 − 0
- 45 秒たっても開き終わらなければ打ち切り、「時間切れ」と記録する
- 段の全体が 40 分を超えたら、残りの画面は測らずに「時間切れで未測定」と記録して表を出す

### 5-4. 測る画面の表（tests/prod-check/page-speed-targets.ts）

- 中身は recon の 135 件（/tmp/CC報告ファイル/speed-check/measure/targets.tsv を実装者に渡す。リポジトリには ts の表として入れる）
- 1 行の形: `{ route: "/crm/leads", kind: "" }`。番号つきの画面は `{ route: "/crm/leads/:id/edit", kind: "needs-id", listPage: "/crm/leads", listApi: "/api/v1/leads" }`
- 番号つき 10 種の拾い元（一覧画面と、その画面が呼ぶ一覧 API）:

| 画面 | 一覧画面 | 一覧 API | 根拠 |
|---|---|---|---|
| `/crm/leads/:id/edit` | `/crm/leads` | `/api/v1/leads` | `frontend/src/pages/leads/LeadsPage.tsx:153` |
| `/contacts/:id/edit` | `/crm/contacts` | `/api/v1/contacts` | `frontend/src/pages/contacts/ContactsPage.tsx:137` |
| `/crm/companies/:id` | `/crm/companies` | `/api/v1/companies` | `frontend/src/pages/companies/CompaniesPage.tsx:211` |
| `/admin/products/:id/edit` | `/admin/products` | `/api/v1/products` | `frontend/src/pages/products/ProductsPage.tsx:144` |
| `/quotes/:id` | `/quotes` | `/api/v1/quotes` | `frontend/src/pages/quotes/QuotesPage.tsx:59` |
| `/invoices/:id` | `/invoices` | `/api/v1/invoices` | `frontend/src/pages/invoices/InvoicesPage.tsx:55` |
| `/staff/:id/edit` | `/staff` | `/api/v1/staff` | `frontend/src/pages/staff/StaffPage.tsx:131` |
| `/bots/:id/edit` | `/bots` | `/api/v1/bots` | `frontend/src/pages/bots/BotsPage.tsx:108` |
| `/teams/:id/edit` | `/teams` | `/api/v1/teams` | `frontend/src/pages/teams/TeamsPage.tsx:76` |
| `/suppliers/:id/edit` | `/suppliers` | `/api/v1/suppliers` | `frontend/src/pages/suppliers/SuppliersPage.tsx:67` |

- 番号の拾い方: 一覧画面を開いたときの一覧 API の応答（道すじが一覧 API と一致し、問い合わせ文字は問わない GET・状態 200）が配列で 1 件以上なら、先頭の `id` を使う。番号はメモリの中だけで使い、表にも記録にも出さない。拾えなければ「番号を拾えず（一覧が 0 件か権限なし）」と記録する
- 一覧画面を番号拾いのために開いた分は、表の行にしない（一覧画面そのものは別の行で測る）

### 5-5. 本番を守る（書き込みを止める）

段の最初に、ブラウザの全部の通信に関所を置く（`context.route("**/*", ...)`）。ログインより先に置く。

| 通信 | 扱い |
|---|---|
| `GET` で道すじに `/attachment-url` を含む | 止める（開くだけで UPDATE する・recon §5） |
| `GET /api/v1/tenant-commission-settings` | 止める（行が無い会社で INSERT する・recon §5） |
| `GET`・`HEAD`・`OPTIONS`（上の 2 つ以外） | 通す |
| `POST /api/v1/auth/login`・`POST /api/v1/auth/refresh` | 通す（ログインとその続き） |
| それ以外（POST・PATCH・PUT・DELETE など） | 止める |

- 止めた送信は「方式＋道すじの形（番号は `:id`）」ごとの件数だけを表の下に出す
- サインアウトはしない（サインアウトは送信なので止まる。今の点検 S8 がサインアウトを確かめている）
- service worker は止める（`serviceWorkers: "block"`。アプリは登録していないが、関所をすり抜けないように）

### 5-6. 表の中身（公開されるので中身を出さない）

実行記録の要約は公開リポジトリで誰でも見られる。出すのは次だけ。

- 見出し: 「画面の速さ（判定なし・遅い順）」、測った日時（日本時間）、測った画面の数
- 1 行 = 1 画面: 道すじの形（`:id` の形）／開き終わるまでの秒（小数 1 桁）／状態（測れた・時間切れ・番号を拾えず・別の画面へ移った・エラー）／API の数／403 の数／5xx の数／いちばん遅い API の道すじの形とその秒
- 並び: 状態「測れた」で 403 が 0 件の画面を秒の遅い順 → 403 が 1 件以上の画面（権限が無く中身が出ていない）を遅い順 → 測れなかった画面
- 道すじの形: 数字だけ・UUID の形・16 文字以上の英数字の区切りは `:id` に置き換える。問い合わせ文字は名前だけ残し、値は出さない
- 出さない: 画面の文字・API の応答の中身・番号・メール・利用者名・件数
- 同じ表を tests/prod-check/page-speed.md に書き、ワークフローがそれを要約に足す。artifact には上げない（ADR-1051）

### 5-7. ワークフローに足す段

```yaml
      - name: 画面の速さを記録（判定なし）
        if: always() && steps.gate.outputs.skip != 'true'
        continue-on-error: true
        env:
          CI: "true"
          NODE_PATH: ${{ github.workspace }}/frontend/node_modules
          SMOKE_E2E_EMAIL: ${{ secrets.SMOKE_E2E_EMAIL }}
          SMOKE_E2E_PASSWORD: ${{ secrets.SMOKE_E2E_PASSWORD }}
        run: |
          ./frontend/node_modules/.bin/playwright test --config tests/prod-check/page-speed.config.ts || status=$?
          if [ -f tests/prod-check/page-speed.md ]; then cat tests/prod-check/page-speed.md >> "$GITHUB_STEP_SUMMARY"; fi
          exit "${status:-0}"
```

- 「不合格を Discord に知らせる」（`if: failure()`）より後ろに置く。この段の失敗は知らせに入らない
- page-speed.config.ts: `testMatch: "page-speed.spec.ts"`、`retries: 0`、`workers: 1`、`timeout: 45 * 60 * 1000`、`reporter: [["list"]]`、`trace`・`screenshot`・`video` は `off`、ブラウザは今の設定と同じ Desktop Chrome、`baseURL` は今と同じ決め方（`PROD_CHECK_BASE_URL` か本番）
- 秘密が未登録のときは、今の点検と同じく test.skip（理由「点検用の人の秘密情報が未登録」）

## 6. 弊害・トレードオフ

| 弊害 | 対処 |
|---|---|
| 点検用の人は見るだけの役割なので、多くの画面は 403 で中身が出ず、本当の重さは測れない | 403 の画面を別の並びに分けて「測れた」と混ぜない。どこまで測れたかを初回の記録で数え、PO に見せて次の手（権限を広げるか・テスト環境で測るか）を決めてもらう |
| 点検用の人の会社はデータが少ない。データが増えたときの遅さはこの記録では分からない | 「データを 1・3・10 倍にした試験」は別の便（PO 選択「1」の後半） |
| 毎朝 135 画面ぶんの読み取りがサーバーの記録（Prometheus）に混ざる。毎朝 JST 07:00 台の数字が少し速く見える | 時刻が決まっているので、サーバーの記録を見るときにその時間帯を外せる。読み取りだけで書き込みは無い |
| 段が壊れて記録が出なくなっても知らせが来ない | 今回は「記録だけ」なので知らせを付けない。秒数の合格ラインを決める便で、知らせ方も一緒に決める。それまでは実行一覧のこの段の注意の印で分かる |
| 仕事の時間が延びる（今 数分 → 最大 50 分） | 時間上限を 60 分に上げ、段の中でも 40 分で打ち切る。GitHub 提供の機械は公開リポジトリでは無料 |
| 画面切り替えで開いた時間は、初めて URL を開いたときより短い（部品の読み込みが最初の 1 回だけ） | 同じ決め方で毎日測るので、日ごとの比べには使える。最初に開く画面だけ部品の読み込みが入ることを表の注記に書く |

## 7. 外部・過去事例

- 事例1: Playwright 公式文書「Network」（https://playwright.dev/docs/network 、2026-10-31 確認。Context7 の月の上限に達したため公式を直接読んだ）。`context.route` はその context の全ページの通信を止められる。service worker 経由の通信は止められないので `serviceWorkers: "block"` を使う → 応用: 5-5 の関所
- 事例2: Playwright 公式文書 `Request.timing()`（https://playwright.dev/docs/api/class-request#request-timing 、同日確認）。`startTime` は時刻（ミリ秒）、他は `startTime` からの差。`responseEnd` は応答が終わった後に値が入る → 応用: 5-3 の「最後の応答が終わった時刻」
- 事例3（社内の過去事例）: 2026-10-15 に `BackendHighLatency` を P99 から割合に変えた。`/api/health` が毎回遅く、14 日で 393 回鳴っていたため（`docs/runbooks/alerts.md` の BackendHighLatency）→ 応用: 合格ラインを記録より先に決めると、鳴りすぎて誰も見なくなる。今回は記録だけにして、ラインは記録を見てから決める
- 外部の導入の成功・失敗の数値の事例は使っていない。この便は「測って残す」だけで、成功の証明に外部の数字を使わないため

## 8. 受入基準

| 基準 | 検証方法 |
|---|---|
| G1 表が出る | 作業ブランチで `gh workflow run prod-ui-check.yml --ref release/page-speed-record` を 1 回動かし、`gh run view <id>` の要約に見出し「画面の速さ」が在る |
| G2 135 行 | 同じ実行の表の行数を数える（tests/prod-check/page-speed.md と同じ中身） |
| G3 書き込み 0 | 表の下の「止めた送信」の件数と、同じ時間帯の Prometheus `sum(increase(http_requests_total{job="backend",method=~"POST|PATCH|PUT|DELETE"}[<段の時間>]))` から `/api/v1/auth/*` を除いた数が 0 |
| G4 中身が出ない | 表の全行を設計担当が目で見る。`grep -E '[0-9]{3,}'` で道すじに 3 桁以上の数字が無い |
| G5 合否が変わらない | 実行の結論が S1〜S8 の結果どおり（速さの段の失敗で failure にならない） |
| G6 50 分以内 | 実行の所要時間 |
| 今の点検に混ざらない | `./frontend/node_modules/.bin/playwright test --config tests/prod-check/playwright.config.ts --list` に page-speed が出ない |
| 書き込みの道が無い | tests/prod-check/page-speed.spec.ts に SQL・DB 接続の文字が無い（`grep -n -i -E 'select |insert |update |delete |psql|DATABASE_URL'` が 0 件） |
| 型が通る | 実装者の手元で `npx tsc --noEmit -p` 相当の確認、または `--list` が型エラー無しで動く |

## 9. 維持の仕組み

- 守り手: `.github/workflows/prod-ui-check.yml`（毎日動かす）
- 守り手: tests/prod-check/page-speed.config.ts（今の点検と分ける）
- 守り手: 人手で守る — 秒数の合格ラインと知らせ方は PO が決める。決まるまでは、設計担当が週に 1 回、表の遅い順の上位を見る（理由: ラインが無いので機械では判定できない）
- 画面を足した・消したときは、tests/prod-check/page-speed-targets.ts を直す。直し忘れは表の「別の画面へ移った」で見える

## 10. 接触面分析（6 面）

逆参照: `prod-ui-check`・`tests/prod-check`・`SMOKE_E2E` を拡張子を問わず検索（`git grep -n`）。出てきたのは ADR-1051・qa-smoke-rebuild の設計と recon・ワークフロー本体・点検の 3 ファイル・登録簿。

| 面 | 影響 |
|---|---|
| ① 人 | PO: 毎朝の実行記録に表が増える。知らせは増えない。点検用の人の権限は変えない |
| ② エージェント | 設計担当が表を読んで報告する。ADR-1053 と本書を読めば決まりが分かる。並行セッションへは登録簿で知らせる |
| ③ 機械 | prod-ui-check の時間が延びる。今の点検の合否・知らせは変わらない（G5）。必須チェックには入れない |
| ④ データ | 本番 DB に書かない（5-5 で止める）。SQL・DB 接続を持たない。新しい表・新しい保存先を作らない（記録は GitHub の実行記録の要約だけ。保存は 90 日前後で消える・recon U2）。tenant_004 には触れない（点検用の人は tenant_001 か tenant_002） |
| ⑤ 本番 | 配備・VPS・監視の設定は変えない。毎朝 135 画面ぶんの読み取りが増える（6 の表） |
| ⑥ 外部 | お客さんの画面・外部 API には影響なし。読み取りが外部 API を呼ぶ画面は、読み取りの範囲で今の利用者と同じ動き |

## 11. 計画票

| ステップ | 内容 | 担当 |
|---|---|---|
| 1 | 本書・recon・ADR-1053 を作り審査 | Opus（審査はクラウド） |
| 2 | 便0 の実装カードで settle.ts と待ち方の置き換え → push | クラウドの Sonnet |
| 3 | 便0 の作業ブランチで手動実行 1 回、G0 を数える → マージ前の審査 → CI 緑 → マージ（本書・ADR も同じ PR） | Opus |
| 4 | 便1 の実装カードで 5-2 の残りのファイル → push | クラウドの Sonnet |
| 5 | 便1 の作業ブランチで手動実行 1 回、G1〜G6 を数える → 審査 → CI 緑 → マージ | Opus |
| 6 | main で手動実行 1 回、表を PO に遅い順で報告し、秒数の合格ラインを決めてもらう | Opus → PO |

## 12. 未決（PO が決めること）

- D1: 何秒を超えたら知らせるか（画面ごとか、全部同じか）。記録を見てから決める
- D2: 403 で測れない画面をどう測るか（点検用の人の見る権限を広げる／テスト環境で測る）
