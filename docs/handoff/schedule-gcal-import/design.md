# design — Google カレンダー → アプリの取り込み（見せ方はアプリで1件ずつ選ぶ）

状態: KGI PO 承認済み（§12）・便1 実装カード発行済み（§13）。現在地: docs/handoff/schedule-gcal-import/recon.md（以下 recon）。決定記録の案: docs/adr/ADR-1059-google-calendar-import-owner-private.md。
基準: origin/main（2026-11-03 fetch 後）。本番は読み取りだけで確かめた（§2）。

## 0. PO の決定（チャット・2026-11-03）

| 問い | PO の答え |
|---|---|
| 次に何をするか | 「3」= Google からアプリへの向きも作る。受け取る仕組みの設計から |
| 取り込んだ予定を誰に見せるか | 「3が好ましいがSAアプリ側で設定できる？」→ アプリで1件ずつ選ぶ形に決定 |
| 新しく入った予定の最初の見せ方 | 「1」= 最初は「自分だけ」。見せたい予定だけアプリで「社員にも見せる」に切り替える |

## 1. 目的と利用者に見える変化

- 目的: PO が Google カレンダーに入れた予定が、アプリの予定の画面にも出る。個人的な予定は社員に見えない。
- 変化（PO）: Google で予定を足す・直す・消すと、数分以内にアプリの予定の画面に同じ形で出る。取り込んだ予定は最初「自分だけ」。予定を開いて「社員にも見せる」を入れると社員にも出る。
- 変化（社員）: 社員の画面には、PO が「社員にも見せる」にした予定だけが出る。あわせて、今アプリで「個人」として作られた予定（本番に 2 件）は、作った本人以外の画面から消える（§2 の穴をふさぐため。§7 弊害）。

## 2. 現在地（recon の要点を本線と本番で確かめた分）

| 事実 | 根拠 |
|---|---|
| 取り込みを始める方式は 422 で止めている | `backend/app/routers/calendar.py:43-44`（`_ACCEPTED_SYNC_MODES = ("write_only","none")`）、:480-484 |
| 取り込みは「会社の予定」・持ち主なしで入る | `backend/app/services/calendar_service.py:416-447`（`'shared'`、user_id を入れない） |
| `ON CONFLICT (google_event_id)` の受け皿になる一意の索引が無い | migrations/078_create_calendar_events_tenant.sql:77-81（普通の索引）。本番 tenant_004 の索引 5 本・制約 7 本を読み取り、google_event_id の一意は無し（scratchpad 実測。§9） |
| 読み出しは種類を指定しないと全員分を返す | `backend/app/services/calendar_service.py:122-127`、画面は種類なしで呼ぶ `frontend/src/pages/schedule/SchedulePageImpl.tsx:928` |
| 画面の絞りは担当者だけで、「個人」を隠さない | `frontend/src/pages/schedule/SchedulePageImpl.tsx:143-146`（`eventMatchesFilters`） |
| 予定を直すとき「個人／会社」を変える受け口が無い | `backend/app/routers/calendar.py` の `UpdateEventBody`（title・日時・説明・場所・終日だけ）。画面は `calendar_type` と `category` を送るが捨てられる（SchedulePageImpl.tsx:1035-1047） |
| 分類（category）も作成時に捨てられ、本番の予定 9 件はすべて既定の meeting | `CreateEventBody` に category が無い。本番集計: personal/meeting 2 件・shared/meeting 7 件 |
| 人ごとの「共有のしかた」（self/view/edit）は設定画面で保存できるが、表示に効いていない | `backend/app/routers/calendar.py:179,238-244`（読み書きだけ）。`calendar_service.list_events` に share_mode の参照なし |
| 知らせの期限更新の呼び出し元が無い／定期作業が無い | `renew_expiring_webhooks` の呼び出しは試験だけ（git grep）。`backend/app/celery_app.py:67` の beat に calendar 系なし（recon §4） |
| 本番の知らせの登録は 0 件、接続は 1 行（PO・bidirectional） | 本番読み取り（`google_webhook_subscriptions` 0 件。接続 1 行は前回 K2） |
| 予定表を読み書きするのは `backend/app/services/calendar_service.py` と `backend/app/routers/calendar.py` だけ | git grep `calendar_events` origin/main -- backend/app。ほかに AI 用ビュー migrations/20261024_100300_create_ai_cloud_views.sql:338 |

## 3. KGI と KPI（PO が画面で○×を付けられる形）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | PO が Google に予定を1件足すと、5 分以内に PO のアプリの予定の画面に同じ題名・同じ日時で出る | PO が Google で足す→アプリを開き直して目で見る。評価役は本番で予定表の該当行（source=google）と時刻を読み取る |
| K2 | K1 の予定は、社員の画面には出ない | 社員の権限の試験用ログインで同じ日を開き 0 件。試験: 他人の「自分だけ」予定が一覧に返らない |
| K3 | PO がその予定を開いて「社員にも見せる」を入れると社員の画面に出る。外すと消える | 画面操作＋社員ログインで確認 |
| K4 | Google で時刻を変えると、5 分以内にアプリの時刻も変わる。K3 で選んだ見せ方は変わらない | Google で変更→アプリで確認。予定表の calendar_type が変わらないことを読み取り |
| K5 | Google で消すと、5 分以内にアプリからも消える | Google で削除→アプリで確認 |
| K6 | アプリで作って Google に送った予定が、アプリに二重に出ない | アプリで1件作る→5 分後に同じ題名が1件だけ |
| K7 | 知らせが 8 日目以降も届き続ける | 導入 8 日後、知らせの登録の期限が「今より先」で、K1 をもう一度やって合格 |
| K8 | 知らせが落ちても 15 分以内に追いつく | 試験: 知らせなしで定期作業だけ回し、変更が入る。本番は定期作業の実行記録（15 分おき）を読む |
| K9 | 今アプリにある「個人」予定は、作った本人の画面には出たまま | 本番 2 件の持ち主でログイン→出る／ほかの人→出ない |

## 4. 設計（How）

### 便1 — 「自分だけ」を本当に守る（DB の形は変えない）

1. 一覧の読み出しに見せ方の絞りを足す: `calendar_service.list_events` の条件に `(calendar_type = 'shared' OR user_id = :me)` を常に入れる。`type` 指定の分岐は今どおり。
2. 直す・消すの口で、他人の「自分だけ」予定は 404 にする（管理者でも）。持ち主＝`user_id`。`user_id` が空の会社の予定は今どおり（作った人か管理者）。
3. `UpdateEventBody` に `calendar_type`（shared/personal）を足す。変えられるのは予定の持ち主（`user_id`）だけ。持ち主が無い予定を personal にするのは 422。
4. 予定の画面の作成・編集のポップオーバーに「社員にも見せる」の切り替えを1つ足す。`calendar_type` はこの切り替えから決める（今の「分類が個人なら personal」の決め方をやめる）。新規作成の初期値は今と同じ（分類が個人なら切、それ以外は入）。部品は `frontend/src/components/` の既存の切り替え（チェック欄）の金型を使う。名前は実装役が着手前に確かめてカードに書く（直書きの input 禁止・ADR-144）。文言は `t()`、ja/en 同じキー（ADR-027）。
5. 対象外: 分類（category）が保存されない件、人ごとの「共有のしかた」を表示に効かせる件（§8）。

### 便2 — 取り込み本体（migration を含む・危険 PR）

1. migration（足すだけ）:
   - 各テナントの `calendar_events` に `google_event_id` の一意の部分索引（`WHERE google_event_id IS NOT NULL`）を足す。作る前に重複を数え、1 件でもあれば止める（migration 内で RAISE）。古い普通の索引は残す。
   - `public.google_webhook_subscriptions` に `sync_token TEXT`（Google の差分の目印）と `channel_token_hash VARCHAR(64)`（知らせの合言葉の sha256）を足す。
2. 取り込みの書き込み（`upsert_from_google`）:
   - 新規は `calendar_type='personal'`・`user_id = created_by_user_id = 接続の connected_by_user_id`・`source='google'`。
   - 既にある行は、題名・説明・場所・日時・終日だけ上書きする。`calendar_type`・`user_id` は上書きしない（K4）。
   - `ON CONFLICT (google_event_id) WHERE google_event_id IS NOT NULL` に直す（部分索引に合わせる）。
   - 日時は Google の `dateTime`（時差付き）を datetime に直して入れる。終日は Google の終わりの日が「次の日」なので、アプリの終日の形（開始日 00:00〜終了日 23:59・日本時間）に直す。アプリの形の根拠は画面の保存処理 `frontend/src/pages/schedule/SchedulePageImpl.tsx` の saveEvent（`combineDateTime(draft.startDate, "00:00")`・`combineDateTime(draft.endDate, "23:59")`）。列は timestamp with time zone（本番読み取り）。本番に終日の予定は 0 件で、既存の行との食い違いは無い。
   - アプリ起源（`_is_app_origin`）は今どおり飛ばす（K6）。
3. 差分の取り方を Google 公式の形にする（出典 §6）:
   - `sync_token` があれば `events.list(syncToken=…, singleEvents=True, showDeleted は既定)` をページの最後まで読み、最後の `nextSyncToken` を保存する。
   - 無い、または 410 なら、`timeMin = 今 − 30 日`・`singleEvents=True` で全部読み直す。読み直しで現れなかった `source='google'` の行は消す。現れた行の見せ方は残す。
   - 今の「直近 30 分」方式はやめる。
4. 知らせの受け口:
   - 登録時に合言葉を作って `token` に入れ、sha256 だけ保存する。受け口は `X-Goog-Channel-Token` の sha256 が一致しないとき何もしない（200 は返す）。
   - 受け口は取り込み作業を Celery に積むだけにして、すぐ 200 を返す。
5. 定期作業（`backend/app/celery_app.py` の beat に 2 つ）:
   - 15 分おき: 取り込みが有効（sync_mode が bidirectional/read_only）な会社ごとに 3. を回す。登録が無ければ登録する（導入後に自動で始まる）。接続の表 `tenant_google_calendar_config` は RLS が強制（本番読み取り: relrowsecurity・relforcerowsecurity とも t）なので、会社の一覧（public.tenants）を回し、会社ごとに `set_tenant_context` してから読む。終わったら `reset_tenant_context`（ADR-072）。知らせの登録の表 `google_webhook_subscriptions` は RLS 無し（同読み取り: f/f）。
   - 1 日 1 回: 期限が 48 時間以内の知らせを登録し直し、古いチャンネルを `channels.stop`（channel_id と resource_id）で止める。
6. 方式の口: `_ACCEPTED_SYNC_MODES` に bidirectional と read_only を戻す（ADR-1059 で ADR-1057 の取り込み停止を置き換える）。write_only・none にすると知らせを止め、定期作業も回らない＝取り込みの非常停止。
7. 取り込むのは接続の持ち主（PO）の `primary` カレンダーだけ。ほかの人の Google は対象外（ADR-1057 の会社 1 接続のまま）。

### 触らない範囲

Google へ送る側（`create_event`・`update_event`・`delete_event`）、接続・切断の口、OAuth の範囲、秘書（作成の口は同じ）、AI 用ビュー、シフト。

## 5. 代替案と選んだ理由

| 案 | 採否 | 理由 |
|---|---|---|
| 見せ方を Google 側の印で分ける | 不採用 | PO がアプリで選ぶ形を選んだ（§0） |
| 見せ方用の新しい列を作る | 不採用 | 既にある `calendar_type`（shared/personal）が「会社の予定／自分だけ」そのもの。列を増やすと同じ意味が 2 か所になる（SSOT） |
| 取り込み専用の表を別に作る | 不採用 | 予定が 2 か所に分かれ、画面・秘書が両方を読む必要が出る（データ分散の禁止） |
| 知らせだけに頼る（定期作業なし） | 不採用 | Google は知らせの到着を保証しない（`backend/app/services/google_webhook.py:12-13` のコメントと公式の同期ガイド）。期限も 7 日 |
| 定期作業だけ（知らせなし） | 不採用 | K1 の 5 分を 15 分おきでは満たせない |

## 6. 外部・過去事例の参照と我々への応用

- 出典: Google 公式「Synchronize resources efficiently」と events.list の説明（Context7 `/websites/developers_google_workspace_calendar_api`、2026-11-03 取得）。最初に全部読み `nextSyncToken` を保存、以後は `syncToken` で差分だけ、410 なら全部読み直し、ページは最後まで、`syncToken` と `timeMin`・`updatedMin` 等は併用不可、削除は差分に必ず含まれる。
- 出典: 同「Push notifications」（同日取得）。`token` は任意の文字列で、知らせのなりすましを見分けるのに使える（最大 256 文字）。受け口は HTTPS・正規の証明書が要る。
- 数値の導入事例は使わない。今回は Google の決まった手順に合わせる作業で、他社の成果の数字は設計の成否の根拠にならないため。

## 7. 弊害とリスク

| リスク | 対処 |
|---|---|
| 今の「個人」予定 2 件が、作った本人以外の画面から消える | 「個人」の本来の意味どおり。K9 で本人には出ることを確かめる。PO に報告に書く |
| 管理者でも他人の「自分だけ」予定を直せなくなる | 個人的な予定を守るため。会社の予定の権限は今どおり |
| 一意の索引を足すとき重複があると失敗する | migration で先に数えて止める。本番 tenant_004 は google_event_id 付きが 0 件（前回読み取り） |
| 初回の全部読みで件数が多い | 過去 30 日以降に限る。ページを最後まで読む |
| 30 日より前の予定は入らない | 対象外として明記 |
| 接続し直すと別の人が持ち主になる | ADR-1057 の受け入れた点のまま（管理者は PO だけ） |
| 知らせの受け口を誰でも叩ける | 合言葉の照合。叩かれても Google から読み直すだけで、送られた中身は信じない |
| Google からの読み取りが失敗し続ける | 定期作業の失敗を記録に残す。失敗の見張りの置き場は実装カードで決める（既存の Celery 失敗の見張りに乗せる） |

戻し方: 便ごとの PR を revert。migration は足すだけなので残してよい。取り込みだけ止めるときは方式を write_only にする（§4 便2-6）。

## 8. 対象外（別件として記録）

- 予定の分類（category）が作成・更新で保存されない（本番 9 件すべて meeting）。
- 設定画面の「共有のしかた」が表示に効かない。
- 30 日より前の予定の取り込み、PO 以外の人の Google の取り込み、複数カレンダー。

## 9. 確かめた記録

- 本番の索引・制約・知らせの登録件数: /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/a31998c3-b50b-4f1f-9119-370c58e82a8b/scratchpad/gi/prod-idx.txt
- 本番の予定の内訳: 同 scratchpad/gi/prod-cat.txt
- 本番の終日の形・RLS: 同 scratchpad/gi/prod-allday-rls.txt
- 本線のコードの抜き書き: 同 scratchpad/gi/verify.txt・form.txt・readers.txt・sharemode.txt

## 10. 維持の仕組み

- 見せ方の絞りは試験で固定する（他人の personal が一覧に返らない・他人の personal を直すと 404）。
- 取り込みの定期作業は beat に登録し、Celery の未登録点検（project_celery_unregistered_tasks の仕組み）に乗る。
- 知らせの期限は 1 日 1 回の更新で切らさない。K7 を導入 8 日後に確かめる。
- 守り手: backend/tests/test_calendar_service.py, backend/tests/test_calendar_owner_api.py, frontend/src/pages/schedule/SchedulePageImpl.test.tsx

## 11. 設計審査（Architect・同一 AI による自己審査）

判定: APPROVE（設計として。KGI の PO 承認が済むまで実装カードは出さない）。

- 便1: 根拠は本線の行番号で揃い、受入条件 K2・K3・K9 は試験と画面で判定できる。部品の金型名は着手前に実装役が確かめてカードに書く（未確定のままカードを出さない）。
- 便2: 審査中に出た未確認 2 点は本番の読み取りで解消した。①終日の保存の形（§4 便2-2。本番に終日 0 件）②RLS（接続の表は強制あり・知らせの表は無し。§4 便2-5 に会社ごとの文脈の張り方を書いた）。記録: scratchpad/gi/prod-allday-rls.txt。
- `singleEvents=True` と `syncToken` の併用は公式の差分の例に載っている（§6）。
- 未解決: なし。

## 12. PO 承認（チャット・2026-11-03）

- §3 の KGI（K1〜K9）と §7 の弊害（今の「個人」予定 2 件が本人以外から消える）を示し、PO は「1」= この判定で作り始める、を選んだ。便1 から実装に入る承認を含む。
- 便2 は migration を含むため、PR ごとに GO の手順（ADR-136・委任 ADR-1003）を通す。

## 13. 実装カード 便1 — 「自分だけ」を本当に守る

ブランチ: `release/schedule-gcal-import-bin1`（`origin/release/schedule-gcal-import-design` から作る。設計文書も同じ PR に入る）。DB・migrations・deploy.yml・本番 scripts は触らない。

用語: 予定の持ち主 = `COALESCE(user_id, created_by_user_id)`（画面の `ownerUserId` と同じ: `frontend/src/pages/schedule/schedule-utils.ts` の normalizeEvent）。

### 13-1 backend/app/services/calendar_service.py

- `list_events`: 既存の `filters` は後で `ce.` を前に付けて連結している（`where = " AND ".join(f"ce.{f}" for f in filters)`）。かっこ付きの条件をこの配列に入れると `ce.(` になり壊れる。連結の後に、別に `AND (ce.calendar_type = 'shared' OR ce.user_id = :me)` を必ず足す。`user_id` が None なら `AND ce.calendar_type = 'shared'`。`type` の分岐は今どおり残す。docstring も直す。
- `update_event`: `field_map` に `calendar_type` を足す（値は呼び元で検査済み）。payload に `user_id` があれば `user_id = :user_id` も入れる（13-2 で使う）。

### 13-2 backend/app/routers/calendar.py

- `UpdateEventBody` に `calendar_type: Optional[str] = None` を足す。
- `update_event` と `delete_event` の権限確認: SELECT を `created_by_user_id, calendar_type, user_id` にする。
  - `calendar_type == 'personal'` で、持ち主が自分でないなら 404（管理者でも。メッセージは今の「イベントが見つかりません」）。
  - それ以外は今の確認（作った人か tenant admin）のまま。
- `update_event` で payload に `calendar_type` があるとき:
  - 値が shared/personal 以外なら 422。
  - 持ち主が自分でないなら 403「見せ方を変えられるのは予定の持ち主だけです」。
  - personal にするときは payload に `user_id = 自分` を足す（持ち主が空の行は作った人＝自分のときだけここに来る）。

### 13-3 frontend/src/pages/schedule/SchedulePageImpl.tsx

- `ScheduleDraft` に `visibleToStaff: boolean` を足す。`createDraft`: item があれば `item.calendarType === "shared"`、無ければ `true`。
- 分類の SelectControl の onChange: 新規作成（item 無し）のときだけ、`personal` を選んだら `visibleToStaff: false`、ほかを選んだら `true` にする（今の「分類が個人なら個人」の振る舞いを新規作成で保つ）。
- 「終日」の Toggle と同じ形（`schedule-field schedule-field--inline` の div・`Toggle`・`aria-label`）で、「社員にも見せる」の Toggle を終日の直後に1つ足す。金型は既に import 済みの `frontend/src/components/Toggle.tsx`。新しい CSS・色の直書きは足さない。
- 出す条件: 新規作成のときは常に。編集のときは `currentOwnerUserId != null && popover.item.ownerUserId === currentOwnerUserId` のときだけ（両方 null で一致してしまうのを防ぐ）。今のログインの user id は既存の `currentOwnerUserId`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:863-866`。`/calendar/owners` の `isSelf` から取る。編集してよいかの判定 `canEditSelected`（同 :1109-1111）も同じ値を使っている）を `SchedulePopover` に新しい prop で渡す。
  - 訂正（2026-11-03・実装担当の停止報告を受けて Opus が実物で確認）: 初版は `ScheduleRosterState.currentUserId` を渡すと書いた。`ScheduleRosterState` は型の宣言（:80）だけで、値を持つ変数がどこにも無い。新しい取得の口は作らず、上の既存の値を使う。
- `saveEvent`: `calendar_type: draft.visibleToStaff ? "shared" : "personal"` にする（`draft.category === "personal"` からの決め方をやめる）。編集で Toggle を出さない（持ち主でない）ときは `calendar_type` を送らない。

### 13-4 文言（ADR-027）

- `frontend/src/locales/ja.json` と `frontend/src/locales/en.json` の `schedule` に同じキーを1つ足す: `shareWithStaff` = 「社員にも見せる」／「Show to staff」。キー名が既にあれば止めて報告。

### 13-5 試験

- `backend/tests/test_calendar_service.py`: list_events の SQL に `ce.calendar_type = 'shared' OR ce.user_id = :me` が入り、params に me が入る。user_id None なら shared だけ。update_event が calendar_type と user_id を SET する。
- `backend/tests/test_calendar_owner_api.py`（または同じ口の既存試験の置き場）: 他人の personal を PATCH・DELETE → 404（管理者でも）。持ち主以外が calendar_type を送る → 403。持ち主が personal↔shared を切り替え → 200。不正な値 → 422。
- `frontend/src/pages/schedule/SchedulePageImpl.test.tsx`: 新規作成で「社員にも見せる」が出て既定は入。切って保存すると `calendar_type: "personal"`。持ち主でない予定の編集では出ず、`calendar_type` を送らない。

### 13-6 触らない範囲

Google へ送る処理、取り込み（`upsert_from_google`・`backend/app/services/google_webhook.py`）、同期方式の口、分類が保存されない件、設定画面の「共有のしかた」、秘書、migrations。

### 13-7 想定される分岐（止まる条件）

- `SchedulePopover` に今のログインの user id を渡す道が `currentOwnerUserId` 以外にしか無い → 止めて報告（新しい取得の口は作らない）。
- 既存の試験が「他人の personal を返す」前提で書かれていて落ちる → 試験を直さず止めて報告。
- `Toggle` の props が `checked`・`onCheckedChange`・`aria-label` で足りない → 止めて報告。

### 13-8 完了の報告

PR を `--draft` なしで起票（`gh pr create --base main`。本文はテンプレの `### 標準ワークフロー確認` に recon・design・ADR-1059・触るファイル全部）。backend の該当試験と frontend の該当試験の生出力をファイルに残し、パスと PR 番号を報告する。

## 14. 実装カード 便2 — Google の予定を取り込む本体（migration を含む・危険 PR）

ブランチ: `release/schedule-gcal-import-bin2`（この文書と `docs/handoff/schedule-gcal-import/recon-bin2.md` が入っている。同じ PR に実装を足す）。根拠の行番号は `docs/handoff/schedule-gcal-import/recon-bin2.md`（origin/main 0ab7262d6 時点）。着手時に `git fetch origin` し、行番号がずれていたら中身で場所を探す。中身が違えば止めて報告。

Google 公式の決まり（Context7 `/websites/developers_google_workspace_calendar_api`・2026-11-03 確認）:
- `syncToken` と一緒に `timeMin`・`timeMax`・`updatedMin`・`orderBy`・`q` は送れない。ほかの引数（`singleEvents`）は最初の全部読みと同じにする。`syncToken` 付きでは `showDeleted=False` は不可（送らない）。
- `nextSyncToken` は最後のページにだけ付く。期限切れは 410 が返り、全部読み直す。
- 知らせの登録 `events.watch` の `token` は 256 字まで。届く知らせの `X-Goog-Channel-Token` に入る。
- `channels.stop` は `id` と `resourceId` が要る。止められるのは登録した人と同じ OAuth の持ち主だけ。
- 受け口が 500/502/503/504 を返すと Google は送り直す。それ以外の失敗は数えられる。今どおり常に 200 を返す。

### 14-1 migration（新しいファイル・足すだけ・冪等）

`migrations/20261103_200000_add_google_calendar_import_sync.sql` を作る。`scripts/run_all_migrations.sh` の最後の `run_sql migrations/20261103_120000_create_ai_job_assignments.sql`（1213 行付近）の次に、同じ形（1 行のコメント＋`run_sql`）で足す。コメントは「ADR-1059 便2: Google の予定の取り込み（列2つ・一意の部分索引・追加のみ・冪等）」。

```sql
-- ADR-1059 便2: Google の予定の取り込み（足すだけ・冪等）
ALTER TABLE public.google_webhook_subscriptions ADD COLUMN IF NOT EXISTS sync_token TEXT;
ALTER TABLE public.google_webhook_subscriptions ADD COLUMN IF NOT EXISTS channel_token_hash VARCHAR(64);

DO $gcal_import_uniq$
DECLARE
  schema_rec RECORD;
  dup_count INTEGER;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    EXECUTE format(
      'SELECT COUNT(*) FROM (SELECT google_event_id FROM %I.calendar_events'
      ' WHERE google_event_id IS NOT NULL GROUP BY google_event_id HAVING COUNT(*) > 1) d',
      schema_rec.nspname) INTO dup_count;
    IF dup_count > 0 THEN
      RAISE EXCEPTION '%.calendar_events に google_event_id の重複が % 件あります（ADR-1059 便2）',
        schema_rec.nspname, dup_count;
    END IF;
    EXECUTE format(
      'CREATE UNIQUE INDEX IF NOT EXISTS uq_calendar_events_google_event_id'
      ' ON %I.calendar_events (google_event_id) WHERE google_event_id IS NOT NULL',
      schema_rec.nspname);
  END LOOP;
END
$gcal_import_uniq$;
```

- 古い普通の索引 `idx_calendar_events_google_id` は消さない。`CONCURRENTLY` は使わない（DO の中では使えない・表は小さい）。ロック待ちは `scripts/run_all_migrations.sh` の 1 秒＋送り直し（ADR-1037）に任せ、ファイルに `lock_timeout` は書かない。
- 新しいテナントの `calendar_events` は 078 が毎デプロイで作る（`backend/app/services/tenant.py` には無い・recon Q7）。この索引も毎デプロイ同じ DO で付く。`backend/app/services/tenant.py` は触らない。

### 14-2 `backend/app/services/calendar_service.py` の `upsert_from_google`（376-460 付近）

- 引数に `owner_user_id: int` を足す。戻り値は `"upserted" | "deleted" | "skipped"`。最後の `await db.commit()` を消す（呼び元が 1 回だけ commit する。呼び元は `backend/app/services/google_webhook.py` だけ・grep 済み）。
- 取り消し（`status == "cancelled"`）の削除文に `AND source = 'google'` を足す。
- 日時は文字列で渡さず datetime にする（接続は asyncpg・`backend/app/database.py:8`）。同じファイルに `_google_times(start: dict, end: dict) -> tuple[datetime, datetime, bool]` を足す:
  - 終日（`"date" in start`）: 開始 = その日 00:00 日本時間、終了 = `end["date"]` の前の日 23:59 日本時間（Google の終わりの日は次の日のため）。終了が開始より前になったら開始と同じ日の 23:59。
  - 時刻あり: `datetime.fromisoformat(start["dateTime"])`。時差が無いときは `start.get("timeZone")`、無ければ `Asia/Tokyo` の `ZoneInfo` を付ける。end も同じ。
  - 日本時間は `zoneinfo.ZoneInfo("Asia/Tokyo")`。
- INSERT を次の形にする（列と値だけ変える。題名・説明・場所の取り方は今のまま）:
  - 値: `calendar_type='personal'`、`user_id = :owner`、`created_by_user_id = :owner`、`source='google'`、`sync_status='synced'`。
  - 衝突: `ON CONFLICT (google_event_id) WHERE google_event_id IS NOT NULL DO UPDATE SET` 題名・説明・場所・開始・終了・終日・`sync_status='synced'`・`last_synced_at=NOW()`・`updated_at=NOW()`。`calendar_type`・`user_id`・`created_by_user_id` は SET しない（K4）。
  - 最後の条件は `WHERE calendar_events.source = 'google'`（アプリで作った行は上書きしない・K6）。今の `WHERE calendar_events.google_event_id = :gid` はこれに置き換える。
- `_is_app_origin` で飛ばす処理は今のまま。

### 14-3 `backend/app/services/google_webhook.py`

1. `register_webhook`（54-119）:
   - 登録の前に、今の行の `channel_id, resource_id` を読む。
   - `token = secrets.token_urlsafe(32)` を作り、`events().watch` の body に `"token": token` を足す。
   - UPSERT の列と `DO UPDATE SET` に `channel_token_hash = hashlib.sha256(token.encode()).hexdigest()` を足す。`sync_token` は SET しない（差分の目印を残す）。
   - commit と `reset_tenant_context` の後、古い行があり channel_id が変わったら `service.channels().stop(body={"id": 古い channel_id, "resourceId": 古い resource_id})` を `asyncio.to_thread` で呼ぶ。失敗は warning だけ（古い方は 7 日で切れる・`_MAX_TTL_MS`）。docstring の「stop → 新規登録」を「新規登録 → 古いものを stop」に直す。
2. `get_tenant_by_channel`（166-186）を `verify_channel(db, channel_id: str, token: str) -> Optional[int]` に置き換える: `SELECT tenant_id, channel_token_hash FROM public.google_webhook_subscriptions WHERE channel_id = :cid`。行が無い・hash が NULL・`hmac.compare_digest(sha256(token), hash)` が偽なら None。合えば tenant_id。
3. `handle_webhook_notification`（194-259）を消し、`sync_tenant_from_google(db, tenant_id: int) -> dict` を足す。順番:
   1. `SELECT pg_try_advisory_lock(1059, :tid)`。偽なら `{"skipped": "locked"}` を返す（同じ会社の同期が2つ同時に走らない）。以降を try にし、finally で `SELECT pg_advisory_unlock(1059, :tid)`。
   2. `set_tenant_context(db, tenant_id)`。
   3. `SELECT connected_by_user_id, sync_mode FROM tenant_google_calendar_config`。行が無い・`sync_mode` が bidirectional/read_only 以外 → `{"skipped": "off"}`。`connected_by_user_id` が NULL → warning と `{"skipped": "no_owner"}`。
   4. `service = await cal_svc._get_service(db, tenant_id)`。RuntimeError → `{"skipped": "not_connected"}`。`_get_service` は中で commit することがあるので、この後もう一度 `set_tenant_context` する。
   5. `SELECT sync_token FROM google_webhook_subscriptions WHERE tenant_id = :tid`。
   6. 引数: `calendarId="primary"`・`singleEvents=True`・`maxResults=250`。目印があれば `syncToken=目印`、無ければ `timeMin = (今 − 30 日) の UTC の RFC3339`（全部読み）。
   7. `pageToken` を回して最後まで読む。`googleapiclient.errors.HttpError` で `e.resp.status == 410` かつ目印を使っていたら、目印を捨てて 6. の全部読みからやり直す（1 回だけ）。それ以外の失敗はそのまま投げる（Celery の失敗の見張りに数えさせる）。
   8. 各 item を `upsert_from_google(db, tenant_id, item, owner_user_id)`。全部読みのときは cancelled 以外の id を集める。
   9. 全部読みのときだけ、`source = 'google' AND google_event_id IS NOT NULL AND end_datetime >= :time_min AND NOT (google_event_id::text = ANY(CAST(:seen AS text[])))` の行を消す（30 日より前の行は消さない）。
   10. 最後のページの `nextSyncToken` を `UPDATE google_webhook_subscriptions SET sync_token = :t WHERE tenant_id = :tid` で保存する（行が無ければ何もしない）。
   11. `await db.commit()`、`await reset_tenant_context(db, tenant_id)`。戻り値 `{"upserted": n, "deleted": n, "full": bool}`。
4. `renew_expiring_webhooks`（267-292）: 会社ごとに `set_tenant_context(db, tenant_id)` してから `register_webhook` を呼び、finally で `clear_tenant_context(db)`（接続の表は RLS が強制のため。型は `backend/app/tasks/sa02_recon_monitor.py:70,90`）。

### 14-4 受け口 `backend/app/routers/google_calendar.py:386-418`

- `X-Goog-Channel-Token` も読む。`resource_state == "sync"` は何もせず 200。
- `tenant_id = await webhook_svc.verify_channel(db, channel_id, token)`。None なら warning（channel_id だけ記録・token は記録しない）で 200。
- 合えば `sync_google_calendar_tenant.delay(tenant_id)`（14-5）を積んで 200。中で同期を待たない。積む型は `backend/app/routers/meta.py:138` と同じ。
- 例外は今どおり握って 200。docstring を直す。

### 14-5 定期作業 `backend/app/tasks/google_calendar_sync.py`（新しいファイル）

型は `backend/app/tasks/viewer_share_flag_monitor.py:89-95`（同期関数から `asyncio.run`、finally で `engine.dispose()`）。DB は `AsyncSessionLocal`。

- `sync_google_calendar_tenant(tenant_id)`: `sync_tenant_from_google` を 1 回。
- `sync_google_calendar_all()`: `SELECT id FROM public.tenants WHERE is_active = true ORDER BY id` を回す。会社ごとに `set_tenant_context` して `tenant_google_calendar_config` の `sync_mode` を読む。bidirectional/read_only のときだけ、知らせの行が無いか `channel_token_hash` が NULL なら `register_webhook`、その後 `sync_tenant_from_google`。1 社の失敗は記録して次の会社へ進み、最後に失敗が 1 社でもあれば例外を投げる（失敗の見張りに数えさせる）。finally で `clear_tenant_context`。
- `renew_google_calendar_webhooks()`: `renew_expiring_webhooks` を 1 回。
- 名前は `@shared_task(name="app.tasks.google_calendar_sync.<関数名>")`。

`backend/app/celery_app.py`:
- `include=[...]`（21-48）に `"app.tasks.google_calendar_sync"` を足す。
- `beat_schedule`（67-）に 2 つ足す: `"google-calendar-sync-all"` は `"schedule": 900.0`（15 分）、`"google-calendar-renew-webhooks"` は `crontab(hour=4, minute=30)`（毎日 04:30 日本時間）。

### 14-6 方式の口 `backend/app/routers/calendar.py`

- 44 行: `_ACCEPTED_SYNC_MODES = ("bidirectional", "read_only", "write_only", "none")`。43 行のコメントを「ADR-1059 で ADR-1057 の取り込み停止を置き換え」に直す。504 行の 422 は残す（判定は `_VALID_SYNC_MODES` と同じになる）。
- `update_sync_mode`（523-527 付近）: bidirectional/read_only で `register_webhook` が成功したら `sync_google_calendar_tenant.delay(tenant_id)` も積む（最初の全部読みをすぐ始める）。

### 14-7 試験

- `backend/tests/test_calendar_service.py`:
  - `TestUpsertFromGoogle`: 新規の SQL が `'personal'`・`:owner` を入れ、`ON CONFLICT (google_event_id) WHERE google_event_id IS NOT NULL` と `WHERE calendar_events.source = 'google'` を含み、DO UPDATE に `calendar_type`・`user_id` が無い。cancelled の削除文に `source = 'google'`。commit を呼ばない。
  - `_google_times`: 終日 `2026-11-05`〜`2026-11-06` → 11/5 00:00〜11/5 23:59 日本時間。時刻あり `2026-11-05T10:00:00+09:00` → その時刻。時差無し＋`timeZone` → その地域で付く。
  - `sync_tenant_from_google`: 目印ありでは `syncToken` だけ送り `timeMin` を送らない。目印なしでは `timeMin` を送り、現れなかった google の行を消す文を流す。410 で 1 回だけ全部読みに切り替わる。2 ページ目まで読み、最後の `nextSyncToken` を保存する。ロックが取れないと何もしない。`sync_mode` が write_only なら Google を呼ばない。
  - `verify_channel`: 合言葉一致→tenant_id、不一致・hash NULL・行無し→None。
  - `register_webhook`: body に token、保存に hash、古いチャンネルを stop。
  - 今の `TestHandleWebhookNotification`・`TestHandleWebhookNotificationExists`・`TestGetTenantByChannel` は新しい関数の試験に置き換える。
- `backend/tests/test_calendar_owner_api.py:126`: bidirectional/read_only が 200 になり `register_webhook` を呼ぶ試験に書き換える。
- `backend/tests/test_event_loop_nonblocking.py:112`: 対象を `sync_tenant_from_google` に替え、同じことを確かめる。
- 受け口の試験（新規か既存の置き場）: 合言葉が合うと `.delay` が呼ばれ 200、合わないと呼ばれず 200、`sync` は呼ばれず 200。
- `backend/tests/test_celery_beat_registered.py` は書き換えずに通ること（新しい 2 つが登録済み）。

### 14-8 触らない範囲

Google へ送る側（`backend/app/services/google_calendar.py` の create/update/delete_event・`calendar_service` の送る処理）、接続・切断の口、OAuth、秘書、AI 用ビュー、シフト、画面（frontend）、`backend/app/services/tenant.py`、`.github/workflows/deploy.yml`、`monitoring/`。

### 14-9 想定される分岐（止まる条件）

- `upsert_from_google` か `handle_webhook_notification` の呼び元が上に書いた以外にある → 止めて報告。
- `scripts/run_all_migrations.sh` の最後が `migrations/20261103_120000_create_ai_job_assignments.sql` でない（ほかの PR が足した）→ その最後の次に足し、PR 本文に書く。
- `HttpError` の 410 の取り方が今の googleapiclient で `e.resp.status` と違う → 止めて報告。
- 試験の DB が実 PostgreSQL で、`CAST(:seen AS text[])` が通らない → 止めて報告（書き方を変えない）。
- 既存の試験が「取り込みは shared で入る」「受け口が同期を待つ」前提で落ちる → その試験は 14-7 のとおり書き換える。それ以外の理由で落ちる試験は直さず止めて報告。

### 14-10 完了の報告

PR を `--draft` で起票（`gh pr create --base main --draft`。migrations を含むため GO の手順を通す）。本文はテンプレの `### 標準ワークフロー確認` に recon・recon-bin2・design・ADR-1059・触るファイル全部・削除するファイル（中身の行を消したファイル全部）。backend の該当試験の生出力をファイルに残し、パスと PR 番号を報告する。

### 14-11 設計審査（Architect・同一 AI による自己審査・2026-11-03）

判定: APPROVE（実装カードとして）。

- 調べで見つかった今のコードの穴を、カードで全部ふさいだ: ①一意の索引が無いのに `ON CONFLICT (google_event_id)` を使っている（14-1・14-2）②日時を文字列のまま asyncpg に渡している（14-2）③取り込みが shared で入る（14-2）④古いチャンネルを止めていない（14-3-1）⑤期限の更新を呼ぶ定期作業が無い（14-5）⑥合言葉の照合が無い（14-3-2・14-4）⑦更新時に接続の表の会社の文脈を張っていない（14-3-4）。
- 設計 §4 からの細かい足し: 全部読みで消すのは 30 日以内の行だけ（30 日より前を消さない）。同じ会社の同期は DB のロックで 1 本に絞る。持ち主が空の接続では取り込まない。いずれも §4 の目的の中で、PO の判断は要らない。
- Google の決まりは Context7 で確かめた（冒頭）。
- KPI との対応: K1・K4・K5 は 14-3-3＋14-4、K6 は 14-2 の `source = 'google'`、K7 は 14-5 の毎日の更新、K8 は 14-5 の 15 分おき。K2・K3・K9 は便1。
- 未解決: なし。GO は migration を含むため PR ごとに通す（§12）。
