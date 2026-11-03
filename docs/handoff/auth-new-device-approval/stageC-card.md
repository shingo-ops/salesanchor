# 段C 実装カード（本番での受入の試験を作る・第3版・草案）

- 対象: design.md 第6.1版 §4「段C 本番での受入」・§6 の表（K1〜K9・点検が止まらない・相談係 AI の見え方・場所データの大きさ）。ADR-1055。合格の基準は kgi.md（PO 承認済 2026-11-01）。
- 前提（済み）: 段A・段W・段B は本番に入っている。段B は #5036（merge 8b43e30c2・deploy run 41464085330 が 2026-11-02T14:47:31Z に success）。本番は `AUTH_DEVICE_APPROVAL=enforce`・`AUTH_DEVICE_BOOTSTRAP_CUTOFF=2026-11-02T22:00:00Z`（B4・PO の `!` で確認）。
- 根拠の写し: S=origin/main 5c8b70d82d900d1484c3864d70036efe4bc60678。行番号はすべて S。
- 状態: 草案（Opus 作成）。審査はクラウドの設計審査で行い、§10 に記録する。

## 0. このカードで作るもの・作らないもの

作るもの（4ファイル・新規3・変更1）:

| # | ファイル | 中身 |
|---|---|---|
| C1 | `tests/prod-check/device-accept.spec.ts`（新規） | 本番で K1・K3・K4・K5・K6・K8 と K2 の画面の部分を1本の流れで試す。書き込みを伴う |
| C2 | `tests/prod-check/device-accept.config.ts`（新規） | C1 だけを流す設定。retries 0・workers 1・trace/screenshot/video off |
| C3 | `tests/prod-check/playwright.config.ts`（変更） | `testIgnore` に `device-accept.spec.ts` を足す（毎朝の点検に混ぜない） |
| C4 | `.github/workflows/prod-device-accept.yml`（新規） | 手動だけで動く。C1 を流す。concurrency は毎朝の点検と同じ `prod-ui-check` |

作らないもの: backend・frontend・migrations・deploy.yml には触らない。K2 の web push とメールと K7 は PO の機械と受信箱が要るので、§5 の PO の手順で行う。K9・相談係 AI・場所データは読むだけの命令（§6）で行う。

design.md §6 との違い（第3版で明記）:
- K1 の画面の写しは作らない（D-C5・公開リポジトリのため）。代わりに待ち画面の文言を、ja.json の値と一致するかの真偽だけで見る。
- K8 の一覧は画面ではなく API（`GET /api/v1/auth/devices`）で見る。画面の表示は §5 の PO の手順の中で PO が目で見る。

## 1. なぜ毎朝の点検と分けるか（実物の根拠）

- 毎朝の点検の設定は `testDir: "."`・`testIgnore: ["page-speed.spec.ts"]`（S tests/prod-check/playwright.config.ts:18-21）。同じ場所に新しい spec を置くと毎朝の点検に混ざる。そこで C3 で外す。
- 毎朝の点検は「見るだけで、書き込みはしない」（S tests/prod-check/playwright.config.ts:4・.github/workflows/prod-ui-check.yml:3）。受入は依頼を作る・合言葉を作り直す・機械を取り消すので、別の入口（C4）にする。
- 毎朝の点検は retries 1（S tests/prod-check/playwright.config.ts:23）。受入でやり直すと依頼の数が増え、1人1時間5件の枠（S backend/app/auth/devices.py:37・:402-411）を超える。そこで C2 は retries 0。

## 2. 決まりごと（Opus 判断）

- D-C1 点検の人（user_id 87・secrets `SMOKE_E2E_EMAIL`/`SMOKE_E2E_PASSWORD`）で行う。いつもの機械は B-0 で作った印（secret `SMOKE_E2E_DEVICE_TOKEN`）。この印は取り消さない。
- D-C2 1回の実行で作る依頼は4件まで（N・C・D・E）。1時間5件の枠（状態を問わず数える。S backend/app/auth/devices.py:402-411）の内に収める。K7 の依頼は §5 で別に作る（同じ1時間に重ねない）。途中で落ちたら、流し直しは1時間あける。
- D-C3 入口（nginx）は `/api/v1/auth/` の全部を1つの IP で1分10回・まとめて5回に絞る（S nginx/nginx.conf:6・:156-158）。T〜E は同じ runner の IP。そこで次の3つを守る。
  - spec から送る `/api/v1/auth/` の呼び出し（`context.request`）は、1回ごとに S tests/prod-check/login.ts:20-24 の `authPace()`（8秒あける）を先に呼ぶ。画面が自分で呼ぶ分（起動時の refresh＝S frontend/src/contexts/AuthContext.tsx:111-112、小窓のボタンの approve・reject）は1回ごとには挟めないので、`goto` とボタンを押す前に `authPace()` を呼び、起動時の refresh はまとめ枠（5回）で吸収する。呼び出しの見込みは §3 の表の右端の列（合計 約26回・最短 約210秒）。
  - 画面（page）を使うのは T と、K1 の文言を見る N の最初だけ。N の画面は待ち画面の文言を確かめたら、15秒ごとの確認（S frontend/src/pages/login/LoginPage.tsx:32）が走る前に閉じる。そのあとの N・B・C・D・E は、その文脈の `context.request`（Cookie を共有する）で API を直接呼ぶ。
  - 締め出し（401）の確かめは `/api/v1/auth/` の外の `GET /api/v1/login-approvals/pending`（S backend/app/routers/login_approvals.py:3・nginx の `/api/` 30回/秒）で行う。組の失効は次の要求で 401 になる（S backend/app/auth/dependencies.py:201-204）。
- D-C4 終わりに、spec が作った機械（N の機械は段7で取り消し済み・D の機械）を取り消す。残った pending の依頼（E）は T から reject で閉じる（S backend/app/routers/auth.py:1601-1633）。reject は押した組（T）以外の点検の人の組を失効させるだけで、機械の行には触らない（S backend/app/auth/devices.py:297-321・auth.py:1628）。B-0 の印は残る。
- D-C5 公開リポジトリなので、画面の写し・trace・動画は作らない。合言葉・番号・トークンをログに出さない。
  - トークン・番号・合言葉は変数に持つだけにし、console.log しない。test.step の題や expect の失敗文に値を入れない。
  - 値を使う操作（番号のボタンを押す・合言葉を送る）は try/catch で包み、失敗したら値を含まない決まった文で投げ直す（Playwright の失敗文は locator ごと出るため）。
  - 応答本文を丸ごと expect しない。比べるのは状態番号と、真偽にした結果だけ。
- D-C6 API の呼び出しの持ち方: login・poll・recovery の応答の `access_token` を変数に持ち、`Authorization: Bearer` を付けて呼ぶ。アクセストークンは画面のメモリにしかないので（S frontend/src/lib/auth/selfAuth.ts:40・:58）、T の API も同じく T の login の応答から受ける。どの文脈も `Origin: BASE_URL` を付ける（取り消し・拒否・合言葉の作り直しは Origin を確かめる。S backend/app/routers/auth.py:1617・:1676・:1804）。
- D-C7 毎朝の点検が動く時間（日本時間 7:00 予定・実際は 1〜3 時間遅れて始まる。S .github/workflows/prod-ui-check.yml:7 と run 41371097056 が 01:10Z 開始）に重ねない。C4 は concurrency で待つので壊れはしないが、実行は日本時間 12:00〜翌 5:00 の間に限る。

## 3. C1 の流れ（順番どおり。1本の test.describe.serial）

文脈（context）を役ごとに分ける。T＝いつもの機械（S tests/prod-check/login.ts:35-67 の `login()` をそのまま使う。印・パスキー無し扱い・合言葉の小窓止めが入る）。N・B・C・D・E＝新しい文脈。B だけは T と同じ印の Cookie を付ける。N の画面には login.ts:51-58 と同じ init script と route を掛ける。

| 段 | やること | 合格の判定 | 基準 | auth の呼び出し |
|---|---|---|---|---|
| 1 | T の画面で `login()`。続けて T で `GET /api/v1/auth/devices` | login の応答が 200・`/` に着く。応答の `access_token` を変数に持つ。一覧の id の集まりを「始めの集まり」として変数に持つ（値は出さない） | K5（許可済みの機械は聞かれない） | 4（login の実数は2・上限で3と数える） |
| 2 | N の画面でログイン（メール・パスワード・ボタン） | 応答が 202・本文に `match_number` がある（変数に持つ）・文脈の Cookie に `sa_login_pending` がある。画面に待ち画面の文言（ja.json の `login.deviceApproval` の値と一致）が出る。`access_token` が無い。確かめたら N の画面を閉じる（文脈は残す） | K1 | 2 |
| 3 | T の画面で許可の小窓が出るまでの秒数を測る（段2 の応答を受けた時刻から、小窓の題が見えるまで） | 60 秒以内。小窓の「機械」「場所」「時刻」の3つの欄（S frontend/src/features/auth/LoginApprovalWatcher.tsx:146-151）が空でない（真偽だけ見る。場所は「不明」の文言でも可） | K2（画面の部分・知らせの中身） | 0 |
| 4 | T の小窓で、段2 の番号のボタンを押す。N は `context.request` で poll を1回 | 小窓が閉じる。N の poll が 200 で `access_token` を返す | K3 | 2 |
| 5 | N で API の logout → API の login | login が 200（許可待ちにならない） | K5 | 2 |
| 6 | T と N で `GET /api/v1/auth/devices` | T の一覧に N の一覧の `is_current` の id が入っている・各行に `created_at`・`label`・`location` の項目がある（`location` は null でも可。画面では「不明」と出る。S backend/app/routers/auth.py:1655-1660） | K8（一覧） | 2 |
| 7 | T から N の機械を `DELETE /api/v1/auth/devices/{id}` | 204。そのあと N の `GET /api/v1/login-approvals/pending` が 401 | K8（締め出し） | 1 |
| 8 | B で API の login（200・トークンを持つ）。C で API の login（202）。T の小窓で「私ではない」。C で poll | C の poll が `rejected`。B の `GET /api/v1/login-approvals/pending` が 401。T の同じ要求は 200 | K4 | 4 |
| 9 | T で `POST /api/v1/auth/recovery-codes` | 200・10 個返る（数だけ見る） | K6（作り直し） | 1 |
| 10 | D で API の login（202）→ `POST /api/v1/auth/login-requests/recovery` に1個目 | 200・`access_token` が返る | K6（1個で入れる） | 2 |
| 11 | E で API の login（202）→ 同じ合言葉を送る | 400・`detail` が `recovery_code_wrong` | K6（2回目は使えない） | 2 |
| 12 | 後片付け（afterAll で必ず） | D の一覧の `is_current` の id を T から取り消す。T の `/login-approvals/pending` に残りがあれば T から reject（API）。最後に T の一覧の id の集まりが段1 の「始めの集まり」と同じ（B-0 の印が入っていることも見る） | D-C4 | 約4 |

- 各段は前の段が通らなければ止まる（serial）。段12 は失敗しても必ず走らせる。段12 で取り消す相手の id は、その段までに取れた分だけにする（取れていない機械は §8 で手で消す）。
- test の時間の上限は 15 分（auth 約26回 × 8 秒 ＋ 小窓待ち 60 秒 ＋ 余裕）。
- 段11 の失敗で点検の人の失敗回数が1増える（S backend/app/routers/auth.py:1527-1528・:1531-1532）。口座が止まる回数には届かない。次の成功したログインで0に戻る（S backend/app/routers/auth.py:1360-1366）。
- 開始時刻（UTC・秒まで）を最初に `GITHUB_STEP_SUMMARY` に書く。§6 の K9 の数えに使う。

## 4. C4 の形

- `on: workflow_dispatch` だけ（schedule は無い）。
- `concurrency: { group: prod-ui-check, cancel-in-progress: false }`（毎朝の点検と同じ。重ならない）。
- 手順は prod-ui-check.yml の「配備中の確認」から「Install system deps」までを写し、最後に `playwright test --config tests/prod-check/device-accept.config.ts`。env は SMOKE_E2E_EMAIL・SMOKE_E2E_PASSWORD・SMOKE_E2E_DEVICE_TOKEN だけ。
- 失敗の知らせは送らない（人が手で流して結果を見るため）。artifact は上げない。
- permissions は `contents: read`・`actions: read`。

## 5. PO の手順（K2 の web push・K7）

知らせ（web push・メール）は、依頼を出した本人の購読と本人のメールにだけ送られる（S backend/app/routers/auth.py:340-366・:450）。C4 の依頼は点検の人のものなので、PO の機械にも受信箱にも届かない。そこで K2 の知らせは PO 自身のアカウントで試す。

- K2 web push とメール（PO 自身のアカウント・C4 とは別の時間）:
  1. PO のいつもの機械（パソコン）で、アプリの「通知を許可」を押しておく。
  2. PO が、一度もログインしたことの無いブラウザ（スマホのプライベート画面など）で自分のアカウントにログインする → 待ち画面に番号が出る。
  3. 60 秒以内に、いつもの機械に知らせ（web push）が出るか。PO の受信箱にメールが届き、時刻・機械の種類・場所の目安が書いてあり、押して許可するリンクが無いか。PO が見て○×を言う。
  4. いつもの機械の小窓で同じ番号を押す → 新しいブラウザが入れる。
  5. 後片付け: いつもの機械の「ログインしている機械」の一覧で、日時・場所の目安・機械の種類が出ていることを見てから（K8 の画面の部分）、今入れたブラウザを取り消す。
  - 自動の確かめ: 試した時刻以降の PO の購読の `last_success_at` が 60 秒以内に更新されたか（design.md §6 K2）を、§6 の読み取りで見る。
  - 知らせもメールも出ないときは K2 を「判定待ち」とし、受入を完了とは書かない。
- K7: C4 とも K2 とも別の時間（C4 から1時間以上あける）に行う。Opus が印の無いブラウザで点検の人の依頼を1件作る小さな台本を別に用意する（login → 202 → 待つ）。PO が管理画面「ログインの許可待ち」から理由を書いて許可する。台本は poll で入れたら（`access_token` を受けたら）、そのトークンで自分の機械（一覧の `is_current`）を `DELETE /api/v1/auth/devices/{id}` で取り消して終わる。管理者の許可で入ると `admin_approval` の機械が登録されるため（S backend/app/routers/auth.py:1446-1452）。記録（`decided_by_user_id`・`auth_events.reason='approved_admin'`）と、取り消した後に点検の人の有効な機械が B-0 の印だけになったことを §6 の読み取りで確かめる。PO のブラウザが使えないときは K7 の本番は「判定待ち」とし、受入を完了とは書かない。

## 6. 読み取りだけの確かめ（PO の `!`・数だけ）

Opus がファイルにして渡す。どれも書き換えない。

- K9: 受入の開始時刻以降の点検の人の `auth_events` を `event_type`・`reason`・`is_new_device` の組で数える（S backend/app/middleware/audit.py:248-257）。出ていること: `event_type='auth_pending'` かつ `reason='device_approval_required'` かつ `is_new_device=true`（S backend/app/routers/auth.py:461-467）・`approved_device`（is_new_device=true）・`rejected`・`approved_recovery`・`recovery_code_wrong`・許可済みの機械のログインの `reason='ok'`（S backend/app/routers/auth.py:420・:497）。パスワード・合言葉の文字列がどの列にも無いことは pytest（段A）で見ている。
- K2 の自動の確かめ: §5 の K2 を試した時刻以降に、PO の購読の `last_success_at` が更新された件数。
- C-g の 429: 受入の後の最初の prod-ui-check の実行記録で、429 の出た回数（`gh run view --log` を数える。0 が合格）。
- 相談係 AI の見え方: `ai_cloud_meta.build_log` の最新行が ok・`column_class` の行数。
- 場所データの大きさ: 本番の MMDB の大きさと backend の使用メモリ（上限 512M）。8割を超えたら PO に報告する。

## 7. 受入（このカードの）

| # | 基準 | 確かめ方 | 誰が |
|---|---|---|---|
| C-a | 毎朝の点検に受入が混ざらない | `playwright test --config tests/prod-check/playwright.config.ts --list` が 8 件のまま（段B の実測と同じ） | 実装役 |
| C-b | 受入の一覧が12段そろう | `--config tests/prod-check/device-accept.config.ts --list` | 実装役 |
| C-c | YAML が読める・schedule が無い | `python3 -c "import yaml…"`・`grep -c schedule` が 0 | 実装役 |
| C-d | 値がログに出ない | spec に console.log が無い・test.step の題と expect に値の変数が無い・値を使う操作が try/catch で決まった文に投げ直している（grep と目視） | 実装役・審査役 |
| C-e | 本番で流して全段 pass | C4 の run が success・12段 passed | Opus |
| C-f | 終わった後に点検の人の機械が受入の前と同じ（B-0 の印を含む） | 段12 の集まりの比べが pass・§6 の読み取りで有効な機械の件数が受入の前と同じ | Opus（PO の `!`） |
| C-g | 次の毎朝の点検が緑で、429 が0件 | 受入の後の最初の prod-ui-check が success、かつ実行記録の 429 が0件（§6） | Opus |

## 8. 戻し方

- 試験だけの追加なので、本番の動きは変わらない。C4 を流さなければ何も起きない。
- 受入で作った機械が残ったときは、点検の人の画面の機械の一覧から取り消す（S backend/app/routers/auth.py:1668-1680）。K2 で PO が入れたブラウザは、PO のいつもの機械の一覧から取り消す。

## 9. 止まる条件

- 本番で段2 が 202 にならない（enforce が効いていない）→ 止めて PO に報告。
- backend の 429（`detail` が `too_many_requests`＝1時間5件の枠）→ 1時間待ってから流し直す。続けて流さない。
- nginx の 429（本文が nginx の画面・`detail` が無い）→ D-C3 の間隔が守られていない。流し直さず spec を直す。
- 段12 の後に B-0 の印が取り消されていた → 止めて PO に報告（毎朝の点検が許可待ちで止まるため）。
- K2 で知らせもメールも出ない → K2 を判定待ちにして PO に報告。原因を調べる前に流し直さない。

## 10. 審査記録

- 第1版（863c99c）: クラウドの設計審査（Opus・run cse_01W47tdhM1a3acEb92UP7wme・2026-11-03T00:28Z）→ REVISE（要修正6・軽微2）。指摘1 nginx の枠は auth 全体にかかる → D-C3・§3 右端の列。指摘2 印の無い文脈の準備 → N だけ画面を使い init script を掛ける。指摘3 トークンの持ち方 → D-C6。指摘4 値がログに出る道 → D-C5・C-d。指摘5〜8 は実行記録が途中で切れて読めなかったため、第2版の審査で改めて挙げてもらう。合っていた点: 12段の順・reject で B-0 の印が残る・依頼4件・concurrency。
- 第2版（d701d7e）: クラウドの設計審査（Opus・run cse_01W47tdeXn9MBEDgNYDcvCdx・2026-11-03T00:36Z）→ REVISE（要修正6・軽微3）。指摘1 知らせは依頼した本人にだけ届く → §5 の K2 を PO 自身のアカウントで試す形にした。指摘2 知らせの中身 → 段3 で3つの欄を見る。指摘3 メール → §5 の K2 の 3。指摘4 K8 の場所 → 段6 に `location`・§0 に画面でなく API と明記。指摘5 K9 の組 → §6。指摘6 K7 の後に残る機械 → §5 の K7 の台本で自分の機械を取り消す。指摘7 「1件だけ」の決め打ち → 段1 の集まりと段12 で比べる（呼び出し +1）。指摘8 D-C3 の書き方 → 画面が自分で呼ぶ分の扱いを足した。指摘9 §0 の数・写しを作らない違い・429 の数え → §0・§6・C-g。合っていた点: §3 の呼び出しの数（約25回）は実物どおり。
