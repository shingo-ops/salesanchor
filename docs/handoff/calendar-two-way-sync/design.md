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
- 実物との照合: card-bin2.md §0 の 3 か所（`calendar_service.py:31`・`:1416`・`:1460-1464`、試験 `:685-698`）を origin/main 2560f963f で一字一句確かめた。書き込みの文は `changes` の列だけを `col = :col` で並べる（`:1468`）ので、`color_key = None` は `color_key = NULL` になる。
- 既存の試験との整合: `test_color_only_when_label_matches` の「名札なし・{"L1":"#0000ff"}・行の色 "red"」は、"red" が 24 色に無く `EVENT_COLORS.get` が None になるので今までどおり触らない。
- 決めごととの整合: ADR-1081 What 4（アプリで作った予定の色は取り込まない）は ADR-1059 改訂 2026-11-20 で既に置き換わっている。今回はその上の「無い」の読み方だけ。
- 未解決: なし。
