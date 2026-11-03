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
