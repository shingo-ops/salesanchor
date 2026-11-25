# design: 予定の中身を Google とアプリの両方向でそろえる

- 現在地: `docs/handoff/calendar-two-way-sync/recon.md`
- 対象 ADR: ADR-1059（取り込み）に改訂を足す・ADR-1016（即時反映）に改訂の注記を足す。関連 ADR-1075（繰り返し）・ADR-1081（色）・ADR-1057（送るのは本人の予定だけ）
- PO の決定: 2026-11-20「1,」=「予定の中身を全部、両方向にそろえる → 題名・時間・場所・色を、どちらで直してももう片方にそろえます。画面も開き直さずに変わります。」。同日、合流と本番反映まで進める指示（自律の委任）。

## 1. 目的と利用者に見える変化

- 前: アプリで作った予定を Google で直しても、アプリには入らない（recon §2 `backend/app/services/calendar_service.py:1408`）。Google で作った予定を Google で直したときも、予定の画面は開き直すまで古い（recon §2 合図なし・§4 画面が受けていない）。
- 後: アプリで作った予定を Google で直すと、題名・説明・時間・終日・場所・色がアプリに入る。予定の画面を開いたままなら、取り込みの後に開き直さずに変わる。アプリで直した予定が Google へ行く道は今のまま。

## 2. 受け入れの基準（KGI / KPI）

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | アプリで作った予定（1 回だけの予定）の題名を Google で変える → 本番の DB のその行の題名が Google と同じになる | 本番反映後、PO が Google で直す。読み取り専用の鍵で行の `title`・`last_synced_at` を読む。15 分以内に変われば ○ |
| K2 | 同じく時間・場所・色（名札のある色）を Google で変える → DB の `start_datetime`/`end_datetime`・`location`・`color_key` が Google と同じになる | K1 と同じ読み方 |
| K3 | 予定の画面を開いたまま Google で直す → 開き直さずに画面の箱が変わる | PO が本番で目視 |
| K4 | アプリで直した予定が Google に行く（今の動きが壊れていない） | PO が本番で目視（アプリで題名を変え、Google で見る） |
| K5 | 取り込みは Google へ 1 回も書かない（行ったり来たりの繰り返しが起きない） | 試験: 取り込み中に Google の書き込み関数が呼ばれたら落ちる |
| K6 | アプリで直して Google へ送る途中（`sync_status` が `synced` でない）の行は、取り込みで上書きしない | 試験 |
| K7 | 取り込みで、アプリで作った予定の見せ方・持ち主・起源（`calendar_type`・`user_id`・`created_by_user_id`・`source`・`sync_origin_id`）と Meet の URL は変わらない | 試験（UPDATE の SET に入らないことを SQL の文で確かめる） |
| K8 | 中身が同じなら書かない（自分の送った値が戻ってきただけのときは「直した」と数えない） | 試験 |
| K9 | アプリで作った繰り返しの回は今と同じく飛ばす。Google で消したアプリの予定は今と同じく消さない | 試験（既存 `test_instance_of_app_origin_is_skipped` が通り、消す試験を足す） |
| K10 | Google で作った予定の取り込みは今と同じ | 既存の試験が全部通る |
| K11 | 取り込みで 1 件でも書いたら、その会社に合図 `calendar.events` を 1 回出す。0 件なら出さない | 試験 |
| K12 | 予定の画面は合図 `calendar.events` を受けたら予定を読み直す | 画面の試験 |

## 3. 変更（実装カード card-bin1.md が正）

### 3-1. 取り込み（`backend/app/services/calendar_service.py` `upsert_from_google`）

- `:1412` の繰り返しの判定（アプリ起源の回は飛ばす）を、`:1408` の判定より**前**へ移す。中身は変えない。
- `:1408` でアプリ起源と分かったら、飛ばす代わりに新しい関数 `_update_app_origin_from_google(db, tenant_id, google_event, label_colors)` を呼んで、その戻り値を返す。
- `_update_app_origin_from_google` の動き:
  1. `status == "cancelled"` なら `"skipped"`（消さない。今と同じ）。
  2. 始まり・終わりが無ければ `"skipped"`（今の Google 起源と同じ判定）。時刻は今と同じ `_google_times` で読む。
  3. その行を 1 件読む（`google_event_id = :gid` かつ `sync_origin_id LIKE 'app:{tenant_id}:%'` かつ `sync_status = 'synced'` かつ繰り返しの元でも回でもない）。無ければ `"skipped"`。
  4. Python で列ごとに比べ、違う列だけを集める（再審査の指摘 B3・B4）:
     - 題名・説明・場所: 題名が無いときは `""`。説明と場所は空と NULL を同じとし、改行は `\n` にそろえて比べる。
     - 時間: 終日は「アプリが Google へ送る日付の形」（`_to_google_event_body`）で比べる。違うときだけ `_google_times` の形で `start_datetime`・`end_datetime`・`is_all_day` を書く。時刻ありは時差をそろえて比べる。
     - 色: `eventLabelId` → `key_for_hex`（Google 起源と同じ読み方）で、名札がアプリの色に当たるときだけ比べる。名札が無い・表に無い・表が読めないときは触らない（アプリは色を変えたときだけ送るので、名札の無いアプリの予定がある）。
  5. 違う列が無ければ `"skipped"`。あれば `UPDATE ... SET <違う列>, last_synced_at = NOW() WHERE id = :id AND sync_status = 'synced'` を流し、書いた行数が 1 以上なら `"upserted"`。列の名前は固定の 7 つだけから作る。詳しい形は card §1(2)。

### 3-2. 合図（`backend/app/services/google_webhook.py` `sync_tenant_from_google`）

- `:372` の `reset_tenant_context` の後、`upserted + deleted > 0` のときだけ `await publish_change(TOPIC_CALENDAR_EVENTS, SCOPE_TENANT, tenant_id)` を 1 回呼ぶ。合図の失敗は取り込みを止めない（`publish_change` は例外を出さない・recon §4）。

### 3-3. 合図の名前（ADR-1016 の表）

- `backend/app/realtime/topics.py`: `TOPIC_CALENDAR_EVENTS = "calendar.events"` と、会社の分かる裏の処理用の表 `TENANT_TASK_TOPICS: dict[str, str] = {TOPIC_CALENDAR_EVENTS: SCOPE_TENANT}` を足す。今の `TASK_TOPICS`（会社の分からない裏の処理用）には入れない。
- `backend/tests/test_realtime_topics.py`: `:132` の集合に `TENANT_TASK_TOPICS` を足す。`TENANT_TASK_TOPICS` の範囲は tenant だけ、という試験を足す。
- `frontend/src/lib/realtime/topics.ts`: `calendarEvents: "calendar.events"` を足す。

### 3-4. 予定の画面（`frontend/src/pages/schedule/SchedulePageImpl.tsx`）

- `:908` の `invalidate` の後に `useRealtimeRefresh([TOPICS.calendarEvents], () => { void invalidate(["calendar", "events"]); });` を 1 行足す。読み直しの頭は保存後と同じ `["calendar", "events"]`（写しの置き場を 1 つのまま使う）。

### 3-5. 触らない範囲

- アプリ → Google の送り方（`update_event`・`create_event`・`delete_event`・`backend/app/services/google_calendar.py`）。ただし 1 か所だけ直す: `_to_google_event_body`（`backend/app/services/calendar_service.py:1558-1561`）は説明・場所が空だと送らないので、アプリで消しても Google に古い値が残る。取り込みを入れるとその古い値がアプリに戻ってしまう（設計審査の指摘 A）。値が None でなければ空 `""` でも送るようにする（card §1(3)）。
- Google 起源の取り込みの SQL（`:1491` 以下）。消す処理（`:1420`）。全部読み直しの消す処理（`backend/app/services/google_webhook.py`）。
- 予定の書き込みの口の合図（`NO_SIGNAL_ROUTES` の `_PENDING` のまま）。DB の形（migration なし）。画面の見た目（新しい部品・色・文字なし）。

## 4. なぜこの形か（代替案）

| 案 | 中身 | 選ばない理由 |
|---|---|---|
| A（採用） | アプリ起源の行は、同期済みで中身が違うときだけ、中身の列だけを UPDATE | 取り込みは DB だけに書くので Google へ戻らない（K5）。送る途中の行は守れる（K6） |
| B | 起源の印を外し、Google 起源と同じ INSERT ON CONFLICT に混ぜる | `source` で消す・上書きする所（`:1420`・`:1491`・全部読み直し）にアプリの予定が入り、Google で消すとアプリからも消える。PO の決めていない動きになる |
| C | Google の `updated` の時刻とアプリの `updated_at` を比べて新しい方を残す | 2 つの時計のずれに頼る。`sync_status` で同じことがより確かに分かる |
| D | 予定の画面を数十秒おきに読み直す | 取り込みが 1 件も無くても読み続ける。ADR-1016（合図で読み直す）と食い違う |

## 5. リスクと対処

- Google の知らせが遅い・来ない: 15 分おきの取り込みで拾う（ADR-1059）。K1 の基準は 15 分以内。
- アプリで直した直後に Google の古い値が戻る: 送る途中は `pending` なので書かない（K6）。送り終えた後の取り込みは Google の最新の値（= アプリが送った値）を読むので、中身が同じで書かない（K8）。
- Google への送信が失敗した行（`failed`）: Google の直しは入らない。次にアプリで直して送れたら戻る。本番の今の `failed` は 0 件（recon §5）。
- 合図で読み直しが増える: 取り込み 1 回で最大 1 回。画面側は 1.5 秒まとめる（ADR-1016）。
- アプリで説明・場所を消したとき: 上の直しで Google も消える。Google は空の説明・場所を返さないので、取り込みは空と NULL を同じに扱い、書き戻さない（K8）。改行の違い（`\r\n` と `\n`）も同じに扱う。
- 予定の画面は、保存でも動かしたときでも、時間を必ず時刻つき（`toISOString()`）で送る（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1023-1024`・`:1313-1314`）。終日の「日付だけ」の送り方は画面からは使われない（三審の指摘 C1 を実物で確かめた）。
- 今の画面は説明・場所を空にすると送らない（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1027-1028` の `|| undefined`、口は `backend/app/routers/calendar.py:489` の `exclude_none`）。だから今はアプリで説明・場所を消せず、DB にも Google にも前の値が残る。値どうしは同じなので、取り込みで戻ることも無い。消せるようにするのは別の件（§6）。
- 終日の予定: アプリが日付だけで持つ行と時刻つきで持つ行で、Google へ送る終わりの日の作り方が違う（`backend/app/services/calendar_service.py:1527-1533`）。だから DB の値どうしではなく「送る日付の形」で比べる。同じなら書かない（K8）。Google で日付を変えたときだけ `_google_times` の形（終了日 23:59・日本時間）で書く。
- 色: アプリは色を変えたときだけ Google へ送る（ADR-1081）。名札の無いアプリの予定で色を消さないよう、名札が当たるときだけ入れる。Google で色を「なし」に戻した場合はアプリに入らない（受け入れる・§6）。
- アプリで直したのに Google へ送らなかった行（同期方式が送らない設定のとき・`backend/app/services/calendar_service.py:537` で `pending` にし `:556` で送らない）: `pending` のまま残るので、取り込みはその行を上書きしない（アプリで直した中身を守る）。送る設定に戻して次にアプリで直せば `synced` に戻る。本番の今の `pending` は 0 件（recon §5）（再審査の指摘 B5）。

## 6. 決めていないこと（PO の判断が要る・今回は今の動きのまま）

- Google でアプリの予定を消したとき、アプリからも消すか（今は消さない）。
- アプリで作った繰り返しの予定を Google で直したとき（今は取り込まない）。
- ~~Google でアプリの予定の色を「なし」に戻したとき、アプリの色も消すか~~ → PO 2026-11-22「1」で「消す」に決定（§10）。
- アプリの画面で説明・場所を空にして消せるようにするか（今は消せない・§5）。
- アプリで直したことを、同じ会社のほかの人の画面にもすぐ出すか（予定の書き込みの口の合図）。

## 7. 外部・過去事例の参照と我々への応用

- Google 公式の同期の手順（syncToken・知らせは届く保証なし）は ADR-1059 が根拠として採用済み。今回はその上の「同じ予定を 2 か所で直す」決め方だけで、数値で比べられる外部事例は見つけていない。成功の証明には使わず、K1〜K4 の本番の観測で判定する。

## 8. 維持の仕組み

- 守り手: backend/tests/test_calendar_service.py
- K5〜K11 の試験（`backend/tests/test_calendar_service.py`）と合図の名前の照合（`backend/tests/test_realtime_topics.py`）が CI の必須チェックで毎回走る。
- 取り込みの件数は今の記録（「Google 取り込み完了 (tenant=…, upserted=…)」）で本番でも見える。

## 9. 戻し方

- 実装 PR を revert する。DB の形は変えないので、戻しても残る物は無い。

## 10. 便2: Google で色を「なし」に戻したらアプリの色も外す（PO 2026-11-22「1」）

### 10-1. 目的と変化
- 前: アプリで作った予定を Google で色「なし」に戻しても、アプリは前の色のまま（§5 の色の行・本番で観測した動き）。
- 後: 同じ操作で、アプリの色も外れて持ち主の色に戻る。画面は便1の合図で開き直さずに変わる。

### 10-2. 現在地（origin/main 2560f963f で読んだ実物）
- 取り込みの色の比べ方: `backend/app/services/calendar_service.py:1460-1464`。名札が当たるときだけ `color_key` を入れ、名札が無いときは触らない。
- アプリから送る色: `backend/app/services/google_calendar.py:414-442` `_apply_event_label`。色ありは名札の id、色なしは `eventLabelId=""`。名札の表に色が無いときも `eventLabelId=""` で送り、記録 `event_label_missing` を出す（`:437`）。
- 名札の表: `backend/app/services/google_calendar.py:405-411`。色の値は小文字にそろえて持つ。アプリの 24 色の値も小文字（`backend/app/services/event_colors.py:8-17`）。
- Google 起源の予定は、名札が無ければ既に NULL にする（`backend/app/services/calendar_service.py:1558-1563`）。今回はアプリ起源をそれにそろえる。
- 画面: 色が無ければ持ち主の色で塗る（`frontend/src/pages/schedule/eventColors.ts:29-30`）。色の変化は塗り直す（ADR-1081 K8・本番合格済み）。画面の直しは要らない。
- 本番の記録（2026-11-22 に Grafana Loki で直近 7 日を数えた。残っていた記録は 2026-11-19 02:43〜11-21 21:56 UTC）: 取り込み 481 回すべてで「名札なし・古い色の番号あり」の予定は 0 件（`event_color_legacy_colorid count=0` が 481 回）。`event_label_missing` は 0 件。

### 10-3. 変更（card-bin2.md が正）
- `_update_app_origin_from_google` の色の比べ方に 1 つ足す。外すのは次の全部がそろうとき:
  1. `label_colors` が None でない（名札の表が読めた）
  2. Google の予定に `eventLabelId` が無い（空も無いと同じ）
  3. Google の予定に `colorId` も無い
  4. アプリの行の `color_key` が NULL でない
  5. その色の値が名札の表の値にある（`EVENT_COLORS.get(r_color) in label_colors.values()`）
- 名札が表に無い id のとき・表が読めないとき・アプリの色が表に無いときは、今のまま触らない。
- 触らない範囲: Google へ送る処理・Google 起源の取り込み・画面・DB の形（migration なし）・合図。

### 10-4. なぜこの形か
- 案A（名札が無ければ必ず外す）は採らない。アプリの色が Google の名札の表に無いと、アプリは `eventLabelId=""` で送る。すると Google から戻った自分の書き込みで、選んだ色がすぐ消える。
- 条件 5 で「Google でも表せた色なのに、Google に色が無い」ときだけ外す。これは Google 側で外した、と読める。
- 条件 3 で古い色の番号だけの予定を外さない（本番 7 日で 0 件だが、消さない側に倒す）。

### 10-5. 受け入れの基準
| 基準 | 検証方法 |
|---|---|
| K12 アプリで色を付けた予定を Google で色「なし」にすると、アプリの色が外れて持ち主の色になる（画面を開き直さない） | PO が本番で目で見る |
| K13 同じ操作で DB の `color_key` が NULL になり、取り込みの記録に upserted=1 が出る | 本番の記録（Loki の `sync_google_calendar_tenant … upserted`）で時刻を合わせて読む |
| K14 条件 1〜5 のどれかが欠けるときは `color_key` に触らない（6 通り） | `backend/tests/test_calendar_service.py` の新しい試験（CI） |
| K15 今までの色の試験（`test_color_only_when_label_matches` ほか）がそのまま通る | CI |

### 10-6. リスクと対処
- アプリで色を付けた直後、名札の表が読めずに名札を送れなかった行（`_apply_event_label` の `table is None`）は、次の取り込みで表が読めると外れることがある。表が読めない回は本番 7 日で記録 0 件（記録の文 `event_label_colors_unavailable`・`backend/app/services/google_calendar.py:402`・Loki で 2026-11-22 に数えた）。起きても色を付け直せば戻る。
- 戻し方: 実装 PR を revert する。DB の形は変えない。

### 10-7. 外部事例
- Google 公式の名札（eventLabelId）の扱いは ADR-1081 で確かめ済み。今回は同じ欄の「無い」の読み方だけで、数で比べられる外部事例は要らない。判定は K12〜K15 で行う。

### 10-8. 設計審査（同じ AI による自己審査・2026-11-22）
- 判定: APPROVE。
- 実物との照合: card-bin2.md §0 の 3 か所（`backend/app/services/calendar_service.py:31`・`:1416`・`:1460-1464`、試験 `backend/tests/test_calendar_service.py:685-698`）を origin/main 2560f963f で一字一句確かめた。書き込みの文は `changes` の列だけを `col = :col` で並べる（`:1468`）ので、`color_key = None` は `color_key = NULL` になる。
- 既存の試験との整合: `test_color_only_when_label_matches` の「名札なし・{"L1":"#0000ff"}・行の色 "red"」は、"red" が 24 色に無く `EVENT_COLORS.get` が None になるので今までどおり触らない。
- 決めごととの整合: ADR-1081 What 4（アプリで作った予定の色は取り込まない）は ADR-1059 改訂 2026-11-20 で既に置き換わっている。今回はその上の「無い」の読み方だけ。
- 未解決: なし。

## 11. 便3: アプリで説明・場所を空にしたら Google でも消す（PO 2026-11-23「1」）

### 11-1. 目的と変化
- 前: 予定を直す画面で説明や場所を全部消して保存しても、前の文が残る。アプリにも Google にも残る（§5 の 82 行目に書いた「今は消せない」）。
- 後: 同じ操作で、アプリの説明・場所が空になる。Google の予定の説明・場所も空になる。

### 11-2. 現在地（origin/main 3763e55c7 で読んだ実物）
- 画面の保存: `frontend/src/pages/schedule/SchedulePageImpl.tsx:1033-1034` が `description: draft.description || undefined`・`location: draft.location || undefined`。空の文字は undefined になり、送る中身から落ちる。直す画面の値は元の予定から `?? ""` で作る（`:160-161`）。
- 口: `backend/app/routers/calendar.py:489` の `body.model_dump(exclude_none=True)` は None だけを落とす。空の文字 `""` は残る。
- 書き込み: `backend/app/services/calendar_service.py:502-531` は送られた列だけを `UPDATE` する。`""` もそのまま入る。繰り返しの予定の直し（`:1056`・`:1124-1125`・`:1224`）も `"description" in payload` で読むので `""` が入る。
- Google へ: `backend/app/services/calendar_service.py:1649-1653` が「空 `""` でも送る。None は送らない」（ADR-1059 改訂 2026-11-20）。繰り返しの予定は表の行から本文を作る（`:170-187`）ので、行の `""` が送られる。Google の `events.patch` は送った欄だけを書き換える。
- Google から戻る取り込み: `_norm_text`（`:1382-1384`）が空と NULL を同じに扱う。`""` を送った後に Google が欄を返さなくても、書き戻しは起きない。
- 画面の表示: 説明・場所は中身があるときだけ出す（`frontend/src/pages/schedule/SchedulePageImpl.tsx:390-391`）。`""` と NULL は同じ見え方。
- 動かす・長さを変える操作（`:1320-1321`）は説明・場所を変えないので、今の送り方のままでよい。

### 11-3. 変更（card-bin3.md が正）
- 画面の保存だけを直す。直すとき（`editing` があるとき）に、元の予定に説明（場所）があり、画面で空にしたなら、`description: ""`（`location: ""`）を送る。
- 作るときは今のまま（空なら送らない）。元から空の予定は今のまま送らない（NULL を `""` に書き換えない）。
- 触らない範囲: 裏側のコード全部・DB の形（migration なし）・Google へ送る処理・取り込み・動かす操作。

### 11-4. なぜこの形か
- 裏側は既に `""` を受けて DB と Google を空にできる（11-2）。止めているのは画面の `|| undefined` だけ。直す所を 1 か所にする。
- 案B（裏側で `""` を NULL に直して入れる）は採らない。`_to_google_event_body` は None を送らないので、Google に古い文が残る。送り方の決め（ADR-1059 改訂 2026-11-20）も変えることになり、範囲が広がる。
- DB に `""` と NULL の 2 通りが入る。どちらも「空」と決めてある（§3 の 40 行目・`_norm_text`・画面の表示）。`""` を入れるのは「中身があった予定を空にした」ときだけで、元から空の予定は NULL のまま。

### 11-5. 受け入れの基準
| 基準 | 検証方法 |
|---|---|
| K16 アプリで予定の説明と場所を消して保存すると、アプリの予定の説明・場所が空になる | PO が本番で目で見る |
| K17 同じ予定の Google 側の説明・場所も空になる | PO が本番の Google カレンダーで目で見る |
| K18 直すとき、元にあった説明・場所を空にしたら `""` を送る | `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` の新しい試験（CI） |
| K19 元から空の予定を直すときと、作るときは、説明・場所を送らない | 同じ試験ファイルの新しい試験（CI） |
| K20 今までの予定の画面の試験がそのまま通る | CI |

### 11-6. リスクと対処
- 空にした直後、Google の知らせで取り込みが走っても、空と NULL を同じに扱うので書き戻さない（`_norm_text`）。
- 戻し方: 実装 PR を revert する。DB の形は変えない。消した文は戻らない（PO が自分で消したもの）。

### 11-7. 外部事例
- Google の `events.patch` が「送った欄だけ書き換える」ことは ADR-1059 改訂 2026-11-20 の時点で確かめ済み。今回は画面から `""` を送るかどうかだけで、数で比べられる外部事例は要らない。判定は K16〜K20 で行う。

### 11-8. 設計審査（同じ AI による自己審査・2026-11-23）
- 判定: APPROVE。
- 実物との照合: 11-2 の行を origin/main 3763e55c7 で読んで確かめた。`exclude_none` が `""` を落とさないこと、裏側の 3 つの直しの道（単発・この回・これ以降）がどれも `""` を DB に入れ Google に送ることを、コードで追った。
- 既存の試験との整合: 直す画面の試験（`frontend/src/pages/schedule/SchedulePageImpl.test.tsx:192-203` ほか）は `apiEvent` の説明・場所が null なので、新しい分岐に入らず今までどおり。
- 決めごととの整合: ADR-1059 改訂 2026-11-20 の「空 `""` でも送る」をそのまま使う。DB の「空と NULL は同じ」（§3）も変えない。
- 未解決: なし。

## 12. 便4: Google で消したとき・繰り返しの 1 回だけを直した・消したとき（2026-11-25）

### 12-1. 目的と変化
- PO の決定: 2026-11-25「３」（残っていた 2 つ、Google で消したときと、繰り返しの 1 回だけを直した・消したときを、両方そろえる案）。続けて「1」（会社の予定も、アプリのみんなの画面から消す）。
- 変化 a: アプリで作った予定を Google で消すと、アプリの予定の画面からも消える。自分だけの予定も、会社の予定も同じ。アプリで消すときと同じく行を消す（12-10 で改めた）。Google のごみ箱から戻すと、つないだ本人の「自分だけ」の予定として戻る。
- 変化 b: アプリで作った繰り返しの予定の 1 回だけを Google で直す・消すと、アプリでもその 1 回だけが変わる・消える。
- 変えない所: Google で繰り返しの「これ以降」「すべて」を直した・消したときは、アプリは今のまま。取り込みは DB にだけ書き、Google へは書かない。

### 12-2. 現在地（origin/main 88c3fccd1）
- 単発の予定の取り込み: `backend/app/services/calendar_service.py:1405-1485` の `_update_app_origin_from_google`。`:1420-1421` で消した知らせ（`cancelled`）は何もしない。`:1429-1441` は送り終えた・繰り返しでない行だけを読む。`:1445-1474` で中身の違う列を作り、`:1478-1485` で送り終えた行だけを直す。
- 入口: `backend/app/services/calendar_service.py:1488-1531` の `upsert_from_google`。`:1511-1514` がアプリで作った繰り返しの回を全部飛ばす（ADR-1075 決定6）。`:1517-1520` がアプリで作った予定を上の関数へ回す。`:1523-1531` は Google で作った予定（`source='google'`）だけを消す。
- 取り込みの回し方: `backend/app/services/google_webhook.py:333-343`。1 回の取り込みで名札の表を 1 回読み（`:335`）、文脈を張り直し（`:337`）、1 件ずつ `upsert_from_google` を呼ぶ（`:339-341`）。差分の取り込みは `singleEvents: True`（`:299`）。
- 画面へ返す一覧: `backend/app/services/calendar_service.py:247` が消した印の行を返さない。繰り返しは例外の行（消した印も）がある回を外す（`:337-366`）。
- アプリで消すとき: 単発は行を消してから Google を消す（`:648-683`）。Google から戻る知らせは、もう行が無いので `:1523-1531` に落ち、何も変わらない。繰り返しの「この予定」を消すと、消した印の例外の行を作るか印を付ける（`:1263-1305`）。作った行は送り中（`pending`）のまま。
- アプリで「この予定」を直すとき: 例外の行を作る・直す。Google に送れたら回の id を持たせて送り終えた印を付ける（`:1050-1095`、`_mark_synced` は `:883-899`）。
- 例外の行の作り: `_insert_row`（`:948-966`、いつも `source='app'`・`pending`）・`_row_values`（`:969-988`、持ち主・見せ方・色は元の行から写す）。
- Google の予定を 1 件読む: `backend/app/services/google_calendar.py:401-411` の `get_event`。鍵が古いと更新して commit し、文脈を張り直す（`:316-318`）。
- 本番の数と Google の資料: recon.md「便4」。

### 12-3. 変更（card-bin4.md が正）
- a（単発）: `_update_app_origin_from_google` で `cancelled` が届いたら、送り終えた・繰り返しでない行を消して "deleted" を返す（画面が読み直す）。消した印は付けない（12-10）。
- b（繰り返しの回）: `:1511-1514` の「全部飛ばす」を、新しい `_apply_app_instance_from_google` に替える。順に:
  1. 送り終えた繰り返しの元の行（Google の id が `recurringEventId`）を読む。無ければ飛ばす。
  2. Google の元の予定を `get_event` で読む。1 回の取り込みで同じ元は 1 回だけ読む（取り込みから渡す入れ物 `series_cache`）。読めない・消えている・決まり（RRULE の行。EXDATE・RDATE の行は見ない・並びの違いは見ない）や題名・説明・場所・始まりと終わりがアプリの元の行と違うときは、「これ以降」「すべて」の直し・消しとみなして飛ばす。
  3. 回を `originalStartTime` で決める。アプリの決まりの回でなければ飛ばす（アプリで「これ以降」を切った後の回など）。
  4. その回の例外の行を読む。あっても送り中・送れなかった行なら飛ばす。
  5. 消した回: 例外の行に消した印を付ける。無ければ消した印の例外の行を作る（Google の回の id を持たせ、送り終えた印）。もう印があれば飛ばす。
  6. 直した回: 期待する中身（例外の行、無ければ元の行の中身をその回の時間にしたもの）と題名・説明・場所・時間を比べ、違うときだけ書く。無ければ例外の行を作る。消した印の例外の行が Google で戻っていたら印を外す。色は入れない。
- 中身の比べ方（題名・説明・場所・時間）は `_update_app_origin_from_google` から `_content_changes` に切り出して a と b で同じものを使う。単発の動き（色の扱いを含む）は変えない。
- 取り込み（`backend/app/services/google_webhook.py:339-341`）は、1 回の取り込みに 1 つの `series_cache` を作って渡す。
- 触らない範囲: DB の形（migration なし）・アプリから Google へ送る処理・Google で作った予定の取り込み・画面・文言・全部読みの片付け（`source='google'` だけ）。

### 12-4. なぜこの形か
- 単発は行を消す（案B）。最初は行を残して印を付ける案A を選んだが、DB の決まりで書けない（12-10）。案B はアプリで消すとき（`delete_event` `:648-683`）と同じ消し方で、DB の形を変えずに済む。
- 案A（行を残して印）は採らない: `calendar_events_cancelled_exception_check` が単発の行に印を許さない。決まりを緩めるには DB の形を変える移行が要り、危ない変更（ADR-135/136）になる。PO の決定（みんなの画面から消す）は案B で満たせる。
- 案B で失うもの: Google のごみ箱から戻した予定は、Google で作った予定と同じく本人の「自分だけ」で戻る。別のカレンダーへ移した予定も消える（つないだカレンダーから無くなったのと同じ形）。
- 案C（消す前に Google に 1 件ずつ聞き直して移動か確かめる）は採らない: 公式の資料で「元のカレンダーからは消した形」と決まっており、聞き直しても見分けられない。
- 元の予定を読み比べる（b の 2）: `singleEvents=true` の取り込みでは、Google で「すべて」を直すと回が全部届く。回だけを見ると 1 回ずつの直しと区別できず、例外の行が回の数だけできる。公式も回ごとの直しで「すべて」を表すと例外が大量にできると注意している。元の予定が変わったかを見れば区別できる。読むのは 1 回の取り込みで元 1 つにつき 1 回。
- 期待する中身と同じなら書かない（b の 6）: アプリで繰り返しを作ると、Google は回を全部知らせてくる。同じ中身なら何も書かないので、作っただけで例外の行は増えない。
- 色を回では入れない: Google で「すべて」の色だけを変えたとき、元の予定の色の比べ方は名札の表に頼るため、取り違えると例外の行が回の数だけできる。1 回だけの色の直しは今回の範囲の外にする。

### 12-5. 受け入れの基準
| 基準 | 検証方法 |
|---|---|
| K-a1 アプリで作った単発の予定（自分だけ・会社のどちらも）を Google で消すと、15 分以内にアプリの予定の画面から消える | 本番でテスト予定を作り、Chrome で Google から消して画面を見る（同意票を出してから） |
| K-a2 その予定の行が表から消え、取り込みの記録に失敗が出ない | 本番を読むだけの鍵でその行を数える（0 行）。取り込みの記録で deleted=1・失敗 0 件 |
| K-a3 取り込みの書き込みが DB の決まりに通る（単発の消し・回の消し・回の直し） | 本物の PostgreSQL の試験 `backend/tests/test_calendar_sync_tenant_reset_pg.py`（CI） |
| K-b1 アプリで作った繰り返しの 1 回だけを Google で直すと、アプリでもその 1 回だけが変わる | 本番でテストの繰り返しを作り、Chrome で 1 回だけ直して画面を見る |
| K-b2 1 回だけを Google で消すと、アプリでもその 1 回だけが消える | 同じテストの繰り返しで見る |
| K-b3 Google で「これ以降」「すべて」を直す・消すと、アプリは変わらない | 同じテストの繰り返しで見る。例外の行が増えていないことを読むだけの鍵で数える |
| K-b4 アプリで繰り返しを作っただけでは、例外の行は 0 行のまま | 作った直後の取り込みの後に、読むだけの鍵で例外の行を数える |
| K-c1 取り込みは Google へ書かない。送り中・送れなかった行に触らない。アプリで消したときの知らせで何も変わらない | `backend/tests/test_calendar_service.py` の試験（CI） |
| K-c2 今までの取り込み・繰り返し・予定の試験がそのまま通る | CI |

### 12-6. リスクと対処
- 別のカレンダーへ移した予定もアプリから消える。Google のごみ箱から戻すと本人の「自分だけ」で戻る。PO に伝える。
- 取り込みは 1 件ずつの失敗を受け止めない（`backend/app/services/google_webhook.py:339-347` に try が無い）。DB の決まりに外れる書き込みが 1 つでもあると、その会社の取り込み全体が止まり、続きの印（sync_token）も進まないので毎回同じ所で止まる。だから書き込みは本物の PostgreSQL の試験で確かめる（K-a3）。
- 取り込みの途中で鍵の更新の commit が入る（`get_event` が鍵を更新するとき）: それまでに書いた分が先に確定するだけで、件ごとに独立しているので問題は無い。鍵は取り込みの頭で名札の表を読むときに更新されるので、途中で起きることは少ない。
- Google が決まりの文字を書き換えて返す（UNTIL の形など）: 違うと読めば「これ以降・すべて」として飛ばすので、アプリが壊れる向きには倒れない。K-b1 が本番で × なら、決まりの比べ方を直す。
- 作った直後の取り込みが、元の行の送り終えた印より先に走る: 元の行が送り中なので飛ばす（今と同じ）。
- 回ごとの問い合わせが増える: 回 1 件につき読み 3 回（見分け・元の行・例外の行）と、元 1 つにつき Google への読み 1 回。本番の繰り返しは 0 件で、作ったときだけ回がまとめて届く。
- 戻し方: 実装 PR を revert する。DB の形は変えない。消えた単発の行は戻らない（Google で消した予定なので、Google に合わせた結果）。回の例外の行は残り、revert 後も今の画面の動きのまま。

### 12-7. 外部事例
- Google Calendar API の公式の資料（Context7 `/websites/developers_google_workspace_calendar_api`・2026-11-25 に読んだ）: 消した予定の形、別のカレンダーへ移したときの形、`originalStartTime`、回ごとの直しの注意（recon.md 便4）。これが作り方の根拠。
- 数で比べられる外部の導入事例は使わない。同じ API の決まりに合わせる作業で、判定は K-a1〜K-c2 で行う。

### 12-8. 維持の仕組み
- 動きは `backend/tests/test_calendar_service.py` の試験で CI が毎回確かめる。
- 決めは ADR-1059 改訂 2026-11-25 と ADR-1075 改訂 2026-11-25 に残す。

### 12-9. 設計審査（同じ AI による自己審査・2026-11-25）
- 判定: APPROVE。
- 実物との照合: 12-2 の行を origin/main 88c3fccd1 で読んで確かめた。一覧が消した印を隠すこと（`:247`・`:337-366`）、アプリで消したときの知らせが便4 の新しい道に入らないこと（行が先に消えるので `_is_app_origin` が偽）、アプリで「この予定」を消した例外の行は、新しく作った行なら送り中のまま（`:1263-1305`）で、便4 は触らないことを追った（前から送り終えている例外の行を消す場合は 12-11 の①）。
- 既存の試験との整合: `test_cancelled_touches_nothing`（`backend/tests/test_calendar_service.py:650`）と `test_instance_of_app_origin_is_skipped`（`:2133`）は今回の決めで動きが変わるので、カードで新しい試験に置き換える。ほかの取り込みの試験はそのまま通る形にした（行を読む列を 1 つ足すので、試験の道具 `_app_origin_db` で 8 列の行に「印なし」を足す）。
- 決めごととの整合: ADR-1059 の「取り込みは Google へ書かない」「送り終えた行だけ」を守る。ADR-1075 決定6 の「二重に入らない」（Why）も、例外の行を作るのは中身が違う回だけなので守られる。
- 未解決: なし（「すべて」を消したときの届き方は、どちらの形でもアプリは今のままになるように作った）。
- 見落とし: この審査は DB の決まり（CHECK・UNIQUE）と書き込みを照らさなかった。マージ前の審査役（Opus）が、単発の行に消した印を付ける書き込みが `calendar_events_cancelled_exception_check` に外れると見つけた。12-10 で改めた。

### 12-10. 改め（2026-11-25・DB の決まりと全部の書き込みを照らした）
- 照らした決まり（`backend/app/services/tenant.py:1579-1604`、本番は `docs/handoff/migration-runner-redesign/recon-5-0b/prod003/constraints.tsv:8` と同じ）: category・color_key・calendar_type・source・sync_status の値の決まり、cancelled_exception（消した印は例外の行だけ）、exception_pair（例外の行は回の始まりも持つ）、recurrence_role（例外の行は決まりを持たない）、recurrence_rule の形、recurring_event_id の参照（元の行が消えると例外も消える）、例外の行の重なり禁止（元の行と回の始まりの組）、Google の id の重なり禁止。
- 照らした書き込み（実装コミット 70451bf3c）:

| 書き込み | 結果 | 根拠 |
|---|---|---|
| 単発の消し（消した印を付ける UPDATE） | × 必ず失敗 | 単発の行は recurring_event_id が空。cancelled_exception に外れる |
| 単発の戻し（印を外す UPDATE） | 届かない道 | 単発の行には印が付けられないので、通る行が無い |
| 回の消し・直しで例外の行を作る（`_insert_row`＋`_adopt_google_instance`） | ○ 値の決まりはすべて通る | recurring_event_id＝元の行・original_start_datetime＝回・recurrence_rule＝空・source='app'・sync_status は pending→synced・見せ方と区分と色は元の行から写す |
| 同じ | △ Google の id の重なりで失敗しうる | 回の Google の id を持つ行が、元の行と回の組では見つからない形で既にあると、重なり禁止に外れる。今の道では起きにくいが、起きると取り込み全体が止まる |
| 例外の行に消した印を付ける・外す・中身を直す UPDATE | ○ | 例外の行なので cancelled_exception を満たす。ほかの列は変えない |

- 直し方: ①単発の消しは行を消す（アプリで消すときと同じ・12-4）。②単発の戻しの道を取る（届かない道なので）。③例外の行を作る前に、回の Google の id を持つ行が既にあるかを読み、あれば記録を 1 行残して飛ばす。④①〜③と例外の行の作り・消しを、本物の PostgreSQL の試験で確かめる（K-a3）。
- 審査（同じ AI による自己審査）: APPROVE。DB の形は変えない。PO の決定（みんなの画面から消す）を満たす。失うもの（ごみ箱から戻すと本人だけの予定で戻る）は 12-4・12-6 と ADR-1059 改訂 2026-11-25 に書いた。カードは card-bin4.md「6. 改め」。

### 12-11. マージ前の審査（Opus）の指摘と決め（2026-11-25・実装 055749b18）
- 判定: APPROVE。DB の決まりに外れる書き込みの道は見つからなかった。CI の pytest-run-internal は 10076 passed・失敗 0 件（本物の PostgreSQL の接続先あり）。
- ①（中）前から送り終えている例外の行を、アプリで「この予定」で消すと、`backend/app/services/calendar_service.py:1266-1268` は消した印だけを付け、送り終えた印は残す。Google への取り消しが失敗すると警告だけ（`:1303-1304`）。その後の取り込みでその回が「消していない」形で届くと、`:1706-1707` が印を外し、アプリでもその回が戻る。
  - 決め: この便では直さない。起きるのは Google への送りが失敗したときか、送る前後のごく短い間だけ。Google へ書き戻さないので行ったり来たりは続かない。送りが成功すれば、次の取り込みで消した印がまた付く（`:1652-1680` の消した回の道、印を付けるのは `:1674`）。
  - 失うもの: Google への送りが失敗したとき、アプリで消した回が Google に合わせて戻る。
  - 次の候補: アプリの道で、送り終えるまで送り中にする（`:1267`）。アプリの道の変更なので別の便にする。
- ②（低）元の予定を読むカレンダーは会社の設定（`backend/app/services/google_calendar.py:404`）、取り込みは `"primary"`（`backend/app/services/google_webhook.py:299`）。送る道（`google_calendar.py:477`・`:499`・`:515`）も会社の設定を使う。本番の読むだけの鍵で `tenant_google_calendar_config` を読み、設定のある 2 社とも `primary` だった（2026-11-25 13:20 JST、2 行）。本番では食い違わない。
- ③（低）「Google で消した回 × 送り中の例外の行」を直接試す試験は無い。コードは `:1649` で消す道・直す道より先に止める。この便では足さない。
- ④（低）題名 500 字の決まり（`backend/app/services/tenant.py:1556`）は、前からある道と同じ種類の危なさ。この便では変えない。
