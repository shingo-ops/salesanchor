# ADR-1060: 予定に Google Meet を付ける。付けられるのは Google をつないだ本人の予定だけで、URL は calendar_events.meet_url の 1 か所に置く

| 項目 | 内容 |
|---|---|
| ステータス | Accepted（2026-11-05・PO の「GO #5135」（ADR-135・ADR-136）で採用。記録の発行は POの委任に基づくClaude Opus発行） |
| 起案日 | 2026-11-04 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1057（送るのは本人の予定だけ）、ADR-1059（Google→アプリの取り込み）、ADR-027（i18n）、ADR-067・ADR-144（金型とデザイントークン）、ADR-135・ADR-136（migration を含む PR の GO） |
| 設計 | docs/handoff/schedule-gcal-alignment/design.md（§5-7・§11-3） |

---

## What（何を決めたか）

1. Meet の URL の置き場所は `calendar_events.meet_url`（TEXT・NULL 可）の 1 か所だけ。`description` など別の欄には写さない。
2. Meet を付けられるのは、Google をつないだ本人の予定だけ。作るときも直すときも、付けてよいかの判定は `calendar_service.can_add_meet` の 1 か所（送る方式 `bidirectional`／`write_only` で、つないだ本人）。満たさなければ 422 で止め、表にも Google にも何も残さない。直すときは、Google に送ってある予定で、持ち主が本人であることも要る。判定は口の `try` の前で行う（`try` の中で出すと `except Exception` が 500 に変えてしまうため）。
3. ADR-1057 の線の内側で行う。直す道が持ち主を見ずに Google へ送る受け入れ点（ADR-1057）は、Meet には広げない。
4. Google 側で付いた Meet の取り込みは、ADR-1059 の取り込みが動く `bidirectional` のときだけ。取り込みは `hangoutLink` を `meet_url` に入れる（直すのは `source='google'` の行だけ）。
5. アプリから作った予定の Meet は、アプリから付ける。Google 側で後から足した Meet は、取り込みがアプリ起源の行を上書きしないため入らない。
6. 付け方は Google Calendar API の `conferenceData.createRequest`（`hangoutsMeet`）。`requestId` は毎回新しい値にする。作成が `pending` で `hangoutLink` が無いときは、1 秒おきに 2 回まで読み直す。それでも取れなければ `meet_url` は空のまま、予定は保存済みで、画面に「Google Meet を付けられませんでした」を出す。もう一度付けるときは新しい `requestId` で頼み直す。
7. 作る・直す口の返事は `{"id", "meet_url"}`。接続状態の口（`GET /google-calendar/status`）は `meet_available`（`can_add_meet` の答え）を返す。画面はこの値が真のときだけ「Google Meet を付ける」を出す。
8. 付けるだけで、付けた Meet を外す操作は作らない。

## Why（なぜ）

- 接続は会社で 1 つ（ADR-1057）。他人の予定に Meet を付けると、つないだ人の Google の予定として作られてしまう。PO はまず自分の予定だけで確かめると決めた。
- 判定の式を口と画面と状態の口に散らすと、片方だけ直して穴ができる。式を 1 か所に置き、他は呼ぶだけにする。
- Meet の URL を説明の文に書くと、Google から取り込んだ説明で上書きされ、置き場所が 2 つになる。

## 受け入れた点

- 他の人の予定と、Google に送っていない予定には Meet を付けられない。
- Meet だけが Google 側で失敗しても、予定そのものは残る（アプリの表には残り、画面に知らせを出す）。
- Workspace の管理者が Meet を止めているとき、Meet 付きの作成が予定ごと断られるかどうかは未確認。予定ごと断られた場合、アプリの表には残り Google には入らず `sync_status='failed'` になる。
- これから作る会社の `calendar_events` に表そのものが無い点は今からある抜けで、この ADR の範囲外（残件）。

## 戻し方

- 実装 PR を revert する。移行は列を足すだけ（`ADD COLUMN IF NOT EXISTS`）なので、列は残してよい。
- 画面から Meet を出さないだけなら、状態の口の `meet_available` を偽にすればよい。

## 見直す条件

- PO 以外の人が自分の Google をつなぎ、人ごとの接続になったとき（段2）。
- Meet を外す操作や、Google 側で後から付けた Meet の取り込みが要るとき。
