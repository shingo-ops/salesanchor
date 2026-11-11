# ADR-1075: 予定の繰り返しは元の予定 1 行に決まり（RRULE）1 つで持ち、表示のときに広げる（回を作り置かない・例外は元を指す行）

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（設計案・審査1・2 の REVISE を直し済み・審査3 待ち・成功条件は PO の決定待ち） |
| 備考 | PO 2026-11-12 選択「1」（繰り返しを付ける）・「1、」（Google の決まった選び方 6 つと、直す・消すときの 3 択。自由に決める選び方（Google の 7 番目）は後で）。 |
| 起案日 | 2026-11-12 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1057（送るのはつないだ本人の予定だけ）、ADR-1059（取り込み）、ADR-1060（Meet）、ADR-1074（編集画面の金型）、ADR-144・ADR-067・ADR-027、ADR-135・ADR-136（移行を含む PR の GO）、ADR-1037（ロック待ち 1 秒）。設計: `docs/handoff/schedule-gcal-clone/design.md` §12・根拠 `docs/handoff/schedule-gcal-clone/recon.md` §9 |

---

## What（何を決めたか）

1. 繰り返しの決まりは、各会社の `calendar_events` の元の行の `recurrence_rule`（RFC 5545 の RRULE）1 か所だけに持つ。回の行を作り置かない。
2. 1 回だけ直した・消した回は、元の行を指す例外の行（`recurring_event_id`・`original_start_datetime`・消した印 `is_cancelled`）で持つ。同じ回の例外は 1 行だけ。例外の行の持ち主・共有の別はいつも元の行と同じ。
3. 一覧では頼まれた期間の中だけを日本時間で広げて返す。1 つの元から返す回は 1000 まで。探す結果では広げず元の行を 1 件返す。
4. 受け口は「どの選び方か」（繰り返さない・毎日・毎週・毎月 第 N・毎月 最終・毎年・平日。Google は開始日が月の最後の同じ曜日のとき「毎月 最終○曜日」も出すため、PO の言う 6 つの「毎月」を 2 つの値に分けた・2026-11-12 実測）だけを受け、決まりの文字はサーバーが開始日から作る。直す・消すは「この予定／これ以降／すべて」の scope と回の始まりを受ける。元の行に scope が無い送信は 422。
5. 「これ以降」は元の決まりに UNTIL を付けて切り、新しい元の行を作る。「すべて」は元の行を直す。1 回ずつを直して実現しない。
6. Google とつないだ本人の予定は `recurrence` 付きで送る。1 回だけの直しは Google の回（instance）の id を例外の行に持つ。取り込みでは、アプリ起源の元の予定の回（`recurringEventId` が一致）を飛ばす。Google で作った繰り返しは今と同じ 1 回ずつの取り込み。

## Why（なぜ）

- データを分散させない（PO の指示・SSOT）。回を作り置くと同じ予定が何百行にも分かれ、直すたびに全部を直すことになり、終わりの無い繰り返しも表せない。
- Google Calendar API の持ち方（元の予定の `recurrence`・回の `recurringEventId`・`originalStartTime`、「これ以降」は UNTIL で切る）に揃えると、送る・取り込むときに形を変換しなくて済む（recon §9.2・Context7 2026-11-12）。
- アプリで作った繰り返しを Google に送ると、取り込みでは元と別の id の回が返る。今のアプリ起源の見分けは id の完全一致なので、何もしないと二重に入る（recon §9.3）。

## 影響

- 移行 1 本（欄 4 つ・CHECK・部分 UNIQUE・会社ごとに回す）。分類表に 1 行。`python-dateutil==2.9.0.post0` を明示。
- 一覧・直す・消す・取り込み・Google への送り（`backend/app/services/calendar_service.py`・`backend/app/routers/calendar.py`・`backend/app/services/google_calendar.py`）。
- 予定の画面（選ぶ欄・詳しくの行・3 択の小窓・回の id）。
