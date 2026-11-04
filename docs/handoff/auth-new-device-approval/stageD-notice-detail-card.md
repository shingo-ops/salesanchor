# ADR-1055 段D: ログインの依頼をお知らせの一覧に出し、押すと詳しい画面で許可する（実装カード v1）

- 状態: 設計案作成済み・Opus 自己審査（§11。同一AIの審査で、独立した第二者の審査ではない）・PO 実装承認済み（2026-11-05 PO「1」＝小窓をやめて、お知らせだけにして作り始める）
- 担当: 実装はクラウドの Sonnet。マージ前に手元の審査役（reviewer・opus）の審査を受ける。GO・マージは PO の委任に基づき Claude Opus（frontend と本番の受入試験と文書だけ・DB・secrets・deploy.yml・migrations は触らない）
- 前の段: 段C（場所の目安の直し・本番反映済み）。`stageC-geoip-open-mode-card.md`

## 1. 目的（PO に見える変化）
PO の言葉（2026-11-04〜05）:
- 「アプリ内の通知にも表示されるようにして」
- 「通知は通知なのでそこにボタンを置かない、通知をクリックしたら詳細ページが開いて情報を表示して許可するか拒否するか選択が表示される仕様にできる？インスタと同じ仕様を想定している」
- 「私です」を押した後の動き: 選択肢「1. 『私です』を押したら、3つの番号から待っている機械に出ている番号を選んで許可する」に「全員これ」（2026-11-05）

変化:
- 新しい機械からのログインの依頼が来ると、いつもの機械の右上の鈴（スマホは下のタブの「お知らせ」）の一覧に1件出る。行にボタンは置かない
- その行を押すと、アプリの中の詳しい画面が開く。機械・場所の目安・時刻が並び、下に「私ではありません」「私です」がある
- 「私です」を押すと、3つの番号が出る。待っている機械に出ている番号を選ぶと許可される（今の守りと同じ）
- 依頼が来たとき勝手に開く小窓は無くなる（鈴の一覧と詳しい画面に置き換える）

## 2. 観測した事実（2026-11-05・origin/main で確かめた）
手本の画面（Claude in Chrome で PO のブラウザから見た・ボタンは押していない）:
- メタ社のアカウント設定「ログインの場所」→「デバイスを確認」→「認識できないログイン」。1件ごとに「アカウント名・機械（iPhone/Mac/Android）・町（国・県）・日時」と「私ではありません」「私です」の2つのボタン。写真 `/tmp/CC報告ファイル/stagec/insta/meta-review-login.png`（手元のみ・社外に出さない）
- スマホのインスタアプリに届く通知の文面は見られていない（未確認）。本カードの文言は手本に頼らず決める

今の仕組み:
- 小窓 `frontend/src/features/auth/LoginApprovalWatcher.tsx:219-357`。`GET /login-approvals/pending` を読み、依頼があると `Modal` を開く（`:316-356`）。中身は機械・場所・時刻の `dl`（`:332-339`）、番号の3つのボタン（`:340-352`）、足元に「私ではない」（`:323-327`）。拒否の後は別の小窓（`:297-314`）。取得は SSE `TOPICS.authLoginRequest`（`:268`）・画面を開いたとき・タブに戻ったとき・5秒に1回まで（`:217`・`:239-250`）
- 小窓の置き場所: `frontend/src/components/DesktopShell.tsx:209`（import `:39`）、`frontend/src/components/MobileShell.tsx:211`（import `:44`）
- 待ち一覧の口: `backend/app/routers/login_approvals.py:46-75`。本人の `pending` で期限内の行だけ。返す項目は `id・label・location・created_at・expires_at・candidates`（`:25-31`）。正本は `public.auth_login_requests`
- 許可の口: `backend/app/routers/auth.py` の `POST /login-requests/{id}/approve`（本文 `{number}`。正しい番号で approved、違えば rejected・wrong_number）、拒否 `POST /login-requests/{id}/reject`（押した機械以外を全部ログアウト）。どちらも本人の依頼だけ・いつもの機械の組だけ（`device_not_trusted` は 403）
- 鈴: `frontend/src/components/NoticeBell.tsx:49-153`。`GET /notices`（各社の `user_notices`・`backend/app/routers/notices.py:228-255`）を読み、行は `NoticeRow`（`frontend/src/components/NoticeRow.tsx:171-185`・文字を持たない部品）。行を押すと Discord のリンクだけ新しいタブで開き既読にする（`:76-90`）。SSE `TOPICS.notices` で読み直す（`:69`）。会社の無い人は `/notices` が空（`notices.py:234-235`）
- 鈴の置き場所: `DesktopShell.tsx:413`（PC）、`MobileShell.tsx:332`（`variant="tab"`）
- 文言: `frontend/src/locales/ja.json:706-718` `login.deviceApproval.watcher.*`、`:5869-5876` `notices.*`（en.json に同じキー）
- 画面の金型: `frontend/src/components/PageLayout.tsx`（詳細系は `titleText`）、`Button`・`Stack`・`EmptyState` が既にある
- 本番の受入試験が小窓を使っている: `tests/prod-check/device-accept.spec.ts:89-94`（小窓の題名）・`:230-244`（K2: 小窓が60秒以内に出る・`dd` を読む）・`:246-252`（K3: 小窓の番号を押す）・`:292-305`（K4: 「私ではない」）
- 小窓の試験: `frontend/src/features/auth/LoginApprovalWatcher.test.tsx`（79行）。shell の試験は小窓を空に差し替えている（`DesktopShell.test.tsx:11`・`MobileShell.test.tsx:36`）

## 3. 決めたこと（Opus 判断・PO の言葉の範囲）
- D1 正本は `public.auth_login_requests` 1か所。鈴は `GET /login-approvals/pending` を読んで行を足す。`user_notices` に写さない（同じ依頼を2か所に持たない・許可や期限切れで写しが古くなるのを防ぐ）。backend は変えない
- D2 鈴の一覧の行は、許可待ちの依頼を上に、その下に今までの知らせ。依頼の行はいつも未読の見た目。許可・拒否・期限切れで一覧から消える（既読の印は付けない）
- D3 鈴の数字 = 今までの未読の数 + 許可待ちの依頼の数
- D4 詳しい画面は新しい道 `/account/login-requests/:id`。中身は `GET /login-approvals/pending` から id で探す（新しい口は作らない）。見つからなければ「この依頼は終わっています」と出す
- D5 勝手に開く小窓 `LoginApprovalWatcher` はやめる（PO の「通知をクリックしたら詳細ページ」）。メールの知らせは今のまま
- D6 守りは今のまま: 「私です」の後に3つの番号から選ぶ（PO「全員これ」）。backend の許可・拒否の口・回数の枠は変えない
- D7 拒否のボタンの文言を手本に合わせて「私ではありません」にする（`watcher.notMe` の値を変える。キーは変えない）

## 4. 変更
実装前に、下の「今の行」を実物で読む。違えば止める。

### 4-1. 新しい画面 `frontend/src/features/auth/LoginRequestDetailPage.tsx`
- `PageLayout`（`titleText={t("login.deviceApproval.detail.title")}`）の中に作る
- 読み込み: `api.get<{ items: PendingLoginRequest[] }>("/login-approvals/pending")` から `useParams().id` の行を探す。型 `PendingLoginRequest` は今の `LoginApprovalWatcher.tsx:203-210` のものを新しい画面のファイルへ移して export する
- SSE `TOPICS.authLoginRequest` で読み直す（`useRealtimeRefresh`・今の小窓と同じ書き方）
- 状態と表示:
  - 読み込み中: 何も押せない（`Button` の `loading` か本文なし）
  - 見つかった（step=`ask`）: 説明 `watcher.body`、`dl` に機械 `watcher.device`・場所の目安 `watcher.location`・時刻 `watcher.time`（値が無ければ `watcher.unknown`。時刻の書き方は今の `formatTime` `:294-295` と同じ）。下に `Button variant="danger"`「私ではありません」(`watcher.notMe`) と `Button variant="primary"`「私です」(`detail.itsMe`)
  - 「私です」を押した（step=`pick`）: `watcher.pickNumber` と番号の3つの `Button variant="secondary"`（今の `:340-352` と同じ）。「戻る」(`common.back`・ja「戻る」が既にある) で step=`ask` に戻る
  - 番号を押す: `POST /auth/login-requests/{id}/approve` `{number}`。返事 `approved` → `detail.approvedTitle`/`detail.approvedBody`。`rejected`（違う番号）→ `detail.wrongNumberBody`
  - 「私ではありません」: `POST /auth/login-requests/{id}/reject` `{}` → `watcher.rejectedTitle`・`watcher.rejectedBody` と `/account/settings` へのリンク（`watcher.changePassword`）
  - 見つからない（許可済み・拒否済み・期限切れ・他人）: `EmptyState` か本文で `detail.closed`、鈴に戻る説明は不要
  - 失敗（通信など）: 一覧を読み直し、まだあれば step=`ask` のまま
- 押している間はボタンを止める（今の `busy` と同じ）
- 色・余白は金型とトークンだけ。新しい CSS を作るなら CSS 変数だけ使う。生の `select`・`input`・色の直値は使わない（ADR-067・ADR-144）

### 4-2. 道を足す `frontend/src/App.tsx`
- `/account/settings` の行（今 `:297` 付近）の次に `<Route path="/account/login-requests/:id" element={<LoginRequestDetailPage />} />`。同じ囲み（ログイン後の shell の中）に置く

### 4-3. 鈴 `frontend/src/components/NoticeBell.tsx`
- `load` で `/notices` と `/login-approvals/pending` を両方読む。片方が失敗しても、もう片方は出す
- 依頼の行を一覧の上に出す。`NoticeRow` を使い、`title = t("notices.kind.login_request", { device: label ?? t("login.deviceApproval.watcher.unknown") })`、`meta = relativeTime(created_at, ...)`、`unread = true`
- 依頼の行を押す: `useNavigate()` で `/account/login-requests/{id}` へ行き、`setOpen(false)` で一覧を閉じる。`/notices/{id}/read` は呼ばない
- 数字 `unread` = `/notices` の `unread_count` + 依頼の件数。`label` と `formatUnreadCount` はその合計を使う
- 読み直しの合図に `TOPICS.authLoginRequest` を足す（`useRealtimeRefresh([TOPICS.notices, TOPICS.authLoginRequest], ...)`）
- 一覧が空の判定は、知らせと依頼の両方が0件のとき
- 今の Discord の行の動き（`:76-90`）は変えない

### 4-4. 小窓をやめる
- `DesktopShell.tsx:209` と `MobileShell.tsx:211` の `<LoginApprovalWatcher />`、import（`:39`・`:44`）を消す
- `frontend/src/features/auth/LoginApprovalWatcher.tsx` と `LoginApprovalWatcher.test.tsx` を消す
- `DesktopShell.test.tsx:11`・`MobileShell.test.tsx:36` の差し替えの行を消す
- 消す前に `git grep -n LoginApprovalWatcher` で他に使う所が無いか確かめる。あれば止める

### 4-5. 文言（ja.json と en.json に同じキー・ADR-027）
- `notices.kind.login_request`: ja「新しい機械（{{device}}）からログインの依頼があります」/ en「Login request from a new device ({{device}})」
- `login.deviceApproval.detail.title`: ja「新しい機械からのログイン」/ en「Login from a new device」
- `login.deviceApproval.detail.itsMe`: ja「私です」/ en「This was me」
- `login.deviceApproval.detail.approvedTitle`: ja「ログインを許可しました」/ en「Login approved」
- `login.deviceApproval.detail.approvedBody`: ja「新しい機械はこのまま使えます。」/ en「The new device can now be used.」
- `login.deviceApproval.detail.wrongNumberBody`: ja「番号が違ったため、この依頼を取り消しました。もう一度ログインしてください。」/ en「The number did not match, so this request was cancelled. Please sign in again.」
- `login.deviceApproval.detail.closed`: ja「この依頼は終わっています。」/ en「This request has already ended.」
- 値を変える: `login.deviceApproval.watcher.notMe` ja「私ではありません」/ en「This wasn't me」
- 値を変える: `login.deviceApproval.body`（待つ機械の画面の説明）ja「この機械は初めてのログインです。いつもの機械のお知らせから依頼を開き、下の番号を選んでください。」/ en は同じ意味に直す（今の「小窓」が無くなるため）
- 使わなくなるキーは消さない（他から使われていないか `git grep` で確かめ、使われていなければ消してよい。迷えば残す）

### 4-6. 試験
- 新: `frontend/src/features/auth/LoginRequestDetailPage.test.tsx`
  - 依頼があると機械・場所・時刻と「私ではありません」「私です」が出る。番号のボタンはまだ出ない
  - 「私です」で番号が3つ出る。番号を押すと `/auth/login-requests/{id}/approve` に `{number}` を送り、approved で `detail.approvedTitle` が出る
  - 違う番号の返事（rejected・wrong_number）で `detail.wrongNumberBody` が出る
  - 「私ではありません」で `/reject` を送り、`watcher.rejectedTitle` が出る
  - id が一覧に無いと `detail.closed` が出る
- 鈴の試験 `frontend/src/components/NoticeBell.test.tsx` を新しく作る（今は鈴の試験のファイルが無い）
  - 依頼1件と未読の知らせ2件で、数字が3、依頼の行が一番上
  - 依頼の行を押すと `/account/login-requests/{id}` へ行き、`/notices/{id}/read` を呼ばない
  - `/login-approvals/pending` が失敗しても知らせは出る
- 本番の受入試験 `tests/prod-check/device-accept.spec.ts`
  - `watcherTitle()`（`:89-94`）を、鈴の依頼の行の文言と詳しい画面の題名を読む形に変える（ja.json から読む今のやり方を保つ）
  - K2（`:230-244`）: いつもの機械の画面で鈴を開き、依頼の行が60秒以内に出る → 押して詳しい画面の `dd` を読む（今と同じ確かめ）
  - K3（`:246-252`）: 「私です」→ 番号を押す → 新しい機械が入れる（今の確かめを保つ）
  - K4（`:292-305`）: 「私ではありません」を押す
  - 他の段（K1・K5〜K8・K6）は変えない
- 本番の受入試験 K7（`tests/prod-check/device-k7.spec.ts`・管理者の許可の道）は変えない

### 触らない
- backend のすべて（`auth.py`・`login_approvals.py`・`notices.py`・`user_notices.py`）、DB・migrations、`deploy.yml`、`scripts/`、secrets、compose
- 待つ機械の画面（`LoginPage.tsx`）の作り。文言 `login.deviceApproval.body` の値だけ変える
- 管理者の許可の画面（`/super-admin/login-requests`）
- メールの文面

## 5. 選んだ理由と退けた案
- 採用: 鈴が許可待ちの依頼を正本から読んで行を足す。backend を変えず、写しを作らない
- 退けた案1: 依頼のたびに `user_notices` に1行入れる → 依頼の状態（許可・期限切れ）と知らせの行が別々に残り、片方だけ古くなる。会社の無い人（super admin）は `user_notices` を持たず出ない
- 退けた案2: 鈴の行に許可・拒否のボタンを置く → PO「通知は通知なのでそこにボタンを置かない」
- 退けた案3: 小窓も残す → PO の形（通知 → 詳しい画面）と2つの入口ができ、同じ依頼を2か所で押せる。メールと鈴の数字で気づける
- 退けた案4: 「私です」だけで許可 → PO「全員これ」（番号を選ぶ形）

## 6. 守りへの影響
- 許可の条件は変わらない（いつもの機械の組・本人の依頼・正しい番号・期限内・1回だけ）。backend を変えないので、口の守りは今の試験がそのまま守る
- 詳しい画面の道の id は URL に出るが、本人の一覧から探すだけで、他人の id では「終わっています」になる（口も他人の依頼は 404）
- 小窓が無くなるので、気づくのは鈴の数字・メール。依頼の期限（30分）は変えない

## 7. 受入条件
| 基準 | 検証方法 |
|---|---|
| D-a 鈴に依頼が出る | 新しい試験: 依頼1件で行が一番上・数字に足される。本番: K2 の新しい形が緑 |
| D-b 行にボタンが無い | 鈴の試験で、依頼の行の中に button が行そのもの1つだけ |
| D-c 押すと詳しい画面 | 鈴の試験で `/account/login-requests/{id}` に行く。PO が本番で目視（行を押すと機械・場所・時刻と2つのボタン） |
| D-d 「私です」→ 番号 → 許可 | 詳しい画面の試験・本番 K3 の新しい形が緑 |
| D-e 「私ではありません」→ 拒否 | 詳しい画面の試験・本番 K4 の新しい形が緑 |
| D-f 小窓が出ない | `git grep -n LoginApprovalWatcher origin/main` が0件。本番で依頼が来ても小窓が開かない（PO 目視） |
| D-g 文言は t() 経由・ja/en 同じキー | CI の i18n の確かめが緑。直書きの日本語なし |
| D-h 金型とトークン | CI の UI governance gate・Lint & Dark Mode Check が緑 |
| D-i CI | PR の必須の確かめがすべて緑 |

## 8. 戻し方
この PR を revert する PR を main に入れる。小窓の形に戻る。backend・DB は変えていないので、それ以外は戻すものが無い。

## 9. 止まる条件
- §2 の行番号の中身が実物と違う → 止めて報告
- `LoginApprovalWatcher` を他でも使っている → 止めて報告
- backend を変えたくなった → 止めて報告
- 金型に無い見た目が要る（新しい部品が要る）→ 止めて報告
- 本番の受入試験を手元やクラウドで本番に向けて流さない（流すのは合流後に Opus が GitHub の操作で）
- CI が赤 → 直さず報告

## 10. 外部事例
- メタ社（インスタ）の「認識できないログイン」の画面（2026-11-05・PO のブラウザで目視・§2）。1件ごとに機械・場所・日時と「私ではありません」「私です」。本設計は同じ並びと文言を使い、「私です」の後に番号を選ぶ所だけ違う（ADR-1048 Why の「押すだけの承認は通知を何度も送られて押してしまう手口に弱い」による。PO「全員これ」）
- 数値の事例は使わない（見た目と流れの手本で、効果の証明には使わない）

## 11. 自己審査（Opus・同一AI）
- 既存の ADR-1055（What 1・3）・ADR-1048（What 3・4）と整合: 許可は番号で、いつもの機械の画面の中だけ。メールに許可のボタンを置かない。変えるのは知らせの出し方と画面の入口だけ
- 正本: 依頼は `public.auth_login_requests` だけ。鈴は読むだけ（D1）
- 未確認で設計が依存する所: なし（インスタアプリの通知の文面は使っていない）
- 判定: APPROVE（実装範囲は frontend と本番の受入試験と文書。backend・DB を含まない）

## 12. 維持の仕組み
- 鈴と詳しい画面の試験が、依頼の行・番号の手順・拒否を CI で守る
- 本番の受入試験 K2〜K4 が、本番で鈴 → 詳しい画面 → 許可の流れを確かめる
