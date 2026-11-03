# 段C 実装カード（本番での受入の試験を作る・第1版・草案）

- 対象: design.md 第6.1版 §4「段C 本番での受入」・§6 の表（K1〜K9・点検が止まらない・相談係 AI の見え方・場所データの大きさ）。ADR-1055。合格の基準は kgi.md（PO 承認済 2026-11-01）。
- 前提（済み）: 段A・段W・段B は本番に入っている。段B は #5036（merge 8b43e30c2・deploy run 41464085330 が 2026-11-02T14:47:31Z に success）。本番は `AUTH_DEVICE_APPROVAL=enforce`・`AUTH_DEVICE_BOOTSTRAP_CUTOFF=2026-11-02T22:00:00Z`（B4・PO の `!` で確認）。
- 根拠の写し: S=origin/main 5c8b70d82d900d1484c3864d70036efe4bc60678。行番号はすべて S。
- 状態: 草案（Opus 作成）。審査はクラウドの設計審査で行い、§10 に記録する。

## 0. このカードで作るもの・作らないもの

作るもの（3ファイル・新規2・変更1）:

| # | ファイル | 中身 |
|---|---|---|
| C1 | `tests/prod-check/device-accept.spec.ts`（新規） | 本番で K1・K3・K4・K5・K6・K8 と K2 の画面の部分を1本の流れで試す。書き込みを伴う |
| C2 | `tests/prod-check/device-accept.config.ts`（新規） | C1 だけを流す設定。retries 0・workers 1・trace/screenshot/video off |
| C3 | `tests/prod-check/playwright.config.ts`（変更） | `testIgnore` に `device-accept.spec.ts` を足す（毎朝の点検に混ぜない） |
| C4 | `.github/workflows/prod-device-accept.yml`（新規） | 手動だけで動く。C1 を流す。concurrency は毎朝の点検と同じ `prod-ui-check` |

作らないもの: backend・frontend・migrations・deploy.yml には触らない。K2 の web push と K7 は PO の機械が要るので、§5 の PO の手順で行う。K9・相談係 AI・場所データは読むだけの命令（§6）で行う。

## 1. なぜ毎朝の点検と分けるか（実物の根拠）

- 毎朝の点検の設定は `testDir: "."`・`testIgnore: ["page-speed.spec.ts"]`（S tests/prod-check/playwright.config.ts:18-21）。同じ場所に新しい spec を置くと毎朝の点検に混ざる。そこで C3 で外す。
- 毎朝の点検は「見るだけで、書き込みはしない」（S tests/prod-check/playwright.config.ts:4・.github/workflows/prod-ui-check.yml:3）。受入は依頼を作る・合言葉を作り直す・機械を取り消すので、別の入口（C4）にする。
- 毎朝の点検は retries 1（S tests/prod-check/playwright.config.ts:23）。受入でやり直すと依頼の数が増え、1人1時間5件の枠（S backend/app/auth/devices.py:37・:402-411）を超える。そこで C2 は retries 0。

## 2. 決まりごと（Opus 判断）

- D-C1 点検の人（user_id 87・secrets `SMOKE_E2E_EMAIL`/`SMOKE_E2E_PASSWORD`）で行う。いつもの機械は B-0 で作った印（secret `SMOKE_E2E_DEVICE_TOKEN`）。この印は取り消さない。
- D-C2 1回の実行で作る依頼は4件まで（K1/K3 用・K4 用・K6 の正しい合言葉用・K6 の2回目用）。1時間5件の枠の内に収める。K7 の依頼は §5 で別に作る（同じ1時間に重ねない）。
- D-C3 ログインの口は nginx で1分10回の枠（S backend/app/routers/login_approvals.py:3 の説明）。spec は login の呼び出しの間に 7 秒以上あける。
- D-C4 終わりに、spec が作った機械（K3 の機械・K6 の機械）を取り消す。残った pending の依頼は、いつもの機械から reject で閉じる（S backend/app/routers/auth.py:1601-1633）。reject は押した組以外の点検の人の組を全部ログアウトさせるが、点検の人は毎回ログインし直すので害はない。毎朝の点検と重ならないことは C4 の concurrency で守る。
- D-C5 公開リポジトリなので、画面の写し・trace・動画は作らない。合言葉・番号・トークンをログに出さない（console.log しない・expect の失敗文に値を入れない）。
- D-C6 毎朝の点検が動く時間（日本時間 7:00 予定・実際は 1〜3 時間遅れて始まる。S .github/workflows/prod-ui-check.yml:7 と run 41371097056 が 01:10Z 開始）に重ねない。C4 は concurrency で待つので壊れはしないが、実行は日本時間 12:00〜翌 5:00 の間に限る。

## 3. C1 の流れ（順番どおり。1本の test.describe.serial）

ブラウザの文脈（context）を役ごとに分ける。T＝いつもの機械（`sa_device` に SMOKE_E2E_DEVICE_TOKEN を付ける。付け方は S tests/prod-check/login.ts の login() と同じ）。N・B・C・D・E＝印の無い新しい文脈。

| 段 | やること | 合格の判定 | 基準 |
|---|---|---|---|
| 1 | T でログイン | `/api/v1/auth/login` の応答が 200 | K5（許可済みの機械は聞かれない） |
| 2 | N でログイン | 応答が 202・本文に `match_number`・応答の Set-Cookie に `sa_login_pending`。画面に `login.deviceApproval` の待ち画面の文言（ja.json の値と一致）が出る。アクセストークンが無い | K1 |
| 3 | T の画面で許可の小窓が出るまでの秒数を測る（段2 の応答の時刻から、T で `/api/v1/login-approvals/pending` に1件出る・小窓の題が見えるまで） | 60 秒以内 | K2（画面の部分） |
| 4 | N の画面の番号を読み、T の小窓でその番号を押す | N が 15 秒ごとの確認で中へ進む（90 秒以内に URL がログイン画面でなくなる） | K3 |
| 5 | N でログアウトし、もう一度ログイン | 応答が 200（許可待ちが出ない） | K5 |
| 6 | T で `GET /api/v1/auth/devices` | 件数が2以上・N の機械（N で同じ一覧を読んだときの `is_current` の id）が入っている・各行に `created_at`・`label` がある | K8（一覧） |
| 7 | T から N の機械を `DELETE /api/v1/auth/devices/{id}` | 204。そのあと N の次の API 要求が 401 | K8（締め出し） |
| 8 | B を T と同じ印でログイン（200）。C でログイン（202）。T の小窓で「私ではない」 | C の確認が `rejected`。B の次の API 要求が 401。T は入ったまま | K4 |
| 9 | T で `POST /api/v1/auth/recovery-codes` | 10 個返る（値はログに出さない） | K6（作り直し） |
| 10 | D でログイン（202）→ 待ち画面で合言葉の1個目を入れる | 中へ進む | K6（1個で入れる） |
| 11 | E でログイン（202）→ 同じ合言葉を入れる | 入れない（`recovery_code_wrong`） | K6（2回目は使えない） |
| 12 | 後片付け（finally で必ず） | D の機械を取り消す。T の `/login-approvals/pending` が残っていれば reject。T の機械一覧に残るのは B-0 の印だけ | D-C4 |

- 各段は前の段が通らなければ止まる（serial）。段12 は失敗しても必ず走らせる（afterAll）。
- 段11 の失敗で点検の人の失敗回数が1増える（S backend/app/routers/auth.py:1527-1528・:1531-1532）。次の成功したログインで0に戻る（S backend/app/routers/auth.py:1360-1366）。
- 開始時刻（UTC・秒まで）を最初に `GITHUB_STEP_SUMMARY` に書く。§6 の K9 の数えに使う。

## 4. C4 の形

- `on: workflow_dispatch` だけ（schedule は無い）。
- `concurrency: { group: prod-ui-check, cancel-in-progress: false }`（毎朝の点検と同じ。重ならない）。
- 手順は prod-ui-check.yml の「配備中の確認」から「Install system deps」までを写し、最後に `playwright test --config tests/prod-check/device-accept.config.ts`。env は SMOKE_E2E_EMAIL・SMOKE_E2E_PASSWORD・SMOKE_E2E_DEVICE_TOKEN だけ。
- 失敗の知らせは送らない（人が手で流して結果を見るため）。artifact は上げない。
- permissions は `contents: read`・`actions: read`。

## 5. PO の手順（K2 の web push・K7）

- K2 web push: PO のいつもの機械で「通知を許可」を押す → Opus が C4 を流す → PO の機械に知らせが出たかを PO が見る。出なければ K2 の web push だけ「判定待ち」のまま残す（design.md §6 の K2）。
- K7: C4 とは別の時間（1時間以上あける）に行う。Opus が印の無いブラウザで点検の人の依頼を1件作る手順を別に用意し、PO が管理画面「ログインの許可待ち」から理由を書いて許可する。待つ側が入れたかと、記録（`decided_by_user_id`・`auth_events.reason='approved_admin'`）を §6 の読み取りで確かめる。PO のブラウザが使えないときは K7 の本番は「判定待ち」とし、受入を完了とは書かない。

## 6. 読み取りだけの確かめ（PO の `!`・数だけ）

Opus がファイルにして渡す。どれも書き換えない。

- K9: 受入の開始時刻以降の点検の人の `auth_events` を reason 別に数える。`auth_pending`・`device_approval_required`・`approved_device`・`rejected`・`approved_recovery`・`recovery_code_wrong` が出ていること。パスワード・合言葉の文字列がどの列にも無いことは pytest（段A）で見ている。
- 相談係 AI の見え方: `ai_cloud_meta.build_log` の最新行が ok・`column_class` の行数。
- 場所データの大きさ: 本番の MMDB の大きさと backend の使用メモリ（上限 512M）。8割を超えたら PO に報告する。

## 7. 受入（このカードの）

| # | 基準 | 確かめ方 | 誰が |
|---|---|---|---|
| C-a | 毎朝の点検に受入が混ざらない | `playwright test --config tests/prod-check/playwright.config.ts --list` が 8 件のまま（段B の実測と同じ） | 実装役 |
| C-b | 受入の一覧が12段そろう | `--config tests/prod-check/device-accept.config.ts --list` | 実装役 |
| C-c | YAML が読める・schedule が無い | `python3 -c "import yaml…"`・`grep -c schedule` が 0 | 実装役 |
| C-d | 値がログに出ない | spec に console.log が無い・`match_number`/合言葉/トークンを文字列に埋め込む expect が無い（grep） | 実装役・審査役 |
| C-e | 本番で流して全段 pass | C4 の run が success・12段 passed | Opus |
| C-f | 終わった後に点検の人の機械が B-0 の印だけ | §6 の読み取りで有効な機械が1件 | Opus（PO の `!`） |
| C-g | 次の毎朝の点検が緑 | 受入の後の最初の prod-ui-check が success | Opus |

## 8. 戻し方

- 試験だけの追加なので、本番の動きは変わらない。C4 を流さなければ何も起きない。
- 受入で作った機械が残ったときは、点検の人の画面の機械の一覧から取り消す（S backend/app/routers/auth.py:1668-1680）。

## 9. 止まる条件

- 本番で段2 が 202 にならない（enforce が効いていない）→ 止めて PO に報告。
- 1時間5件の枠に当たった（429 too_many_requests）→ 1時間待ってから流し直す。続けて流さない。
- 段12 の後に B-0 の印が取り消されていた → 止めて PO に報告（毎朝の点検が許可待ちで止まるため）。

## 10. 審査記録

（未審査）
