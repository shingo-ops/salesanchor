# 設計 — 秘書の「予定のカルテ」（足りない欄だけを順に聞く）

作った人: Opus（Planner）2026-11-14。状態: 設計案 第3版（第2版への設計の審査（クラウド・同じ AI）の「直す点あり」6 件を直した。再審査前）。PO の実装承認は未。

親: [kgi.md](kgi.md) ／ 現在地: [recon.md](recon.md)（docs/handoff/secretary-event-karte/recon.md）／ ADR: [ADR-1078](../../adr/ADR-1078-secretary-event-karte.md)（Proposed）／ 改める ADR: ADR-1056（一部）。ADR-1077 とは指示文と答えの形を共有する（改めない）

根拠の行番号はすべて origin/main = 73bf937a8 のもの。

## 1. 目的と PO の決定

- 目的（PO の言葉は kgi.md に転記）: 「予定を入れて」と頼まれたら秘書は予定の登録だと決め、分かった欄を埋めたまま、空いている必須の欄だけを 1 つずつ聞く。
- カルテの欄（PO 2026-11-14・原文は kgi.md）:

| 欄 | 必須 | いつ決めるか |
|---|---|---|
| 予定の名前 | 必須 | 1 番目に聞く |
| 始まりの日時 | 必須 | 2 番目に聞く |
| 終わりの日時（終日かどうかもここで決める） | 必須 | 3 番目に聞く |
| Google Meet を付けるか | 打ち合わせのときだけ | 4 番目に聞く |
| 場所・内容のメモ | 任意 | 聞かない。最後の確かめの欄に入力欄を出す |
| 見せる範囲（全員／自分だけ） | 任意・最初は自分だけ | 聞かない。最後の確かめの欄に選択を出す |

- 「予定の種類」の欄は作らない。予定を作る口（`backend/app/routers/calendar.py:114-123`）に種類の欄が無いため。種類は「打ち合わせかどうか」（Meet を聞くかの判定）にだけ使う。

## 2. 対象と対象外

- 対象: 予定の頼みの往復（画面 → backend → 容器 → backend → 画面）、容器の指示文と答えの形、予定の下書きの欄（Meet の選択を足す）。
- 対象外: 請求書のカルテ、繰り返しの予定、会話の保存、予定の種類の欄、予定の口（`POST /calendar/events`）の形の変更、Google カレンダーの同期のしかた、決まり帳（ADR-1077）の便3 の中身。

## 3. 作りの全体（1 往復の流れ）

```
画面（カルテを会話の間だけ持つ。新しい画面は 1 通目から必ず karte の鍵を送る。1 通目は null）
  └ POST /assistant/messages { text, karte: null | {...欄, asked, asked_count} }
backend
  ① 担当を読む ①' 決まりを読む ①'' Meet を付けてよいか（can_add_meet）を読む   ← どれも commit の前
  ② commit
  ③ 容器へ { text, now, model, rules, karte?: {start, end, is_all_day}, asked? }   ← 題名・場所・メモは送らない（§4-3）
容器（AI は欄の値を埋めるだけ。次に何を聞くかは決めない）
  └ { kind: "event", event: { title|null, start|null, end|null, is_all_day, location, description, is_meeting, add_meet|null } }
backend
  ④ 合わせる: AI が null で返した欄はカルテの値を使う（埋まった欄を AI が落としても消えない）
     カルテの途中で AI が unknown を返したら、カルテの値で予定のまま続け、同じ欄をもう一度聞く
  ⑤ 日時の検査（終わり < 始まり なら終わりを空に戻す）
  ⑥ 次に聞く欄を決まった順で決める（新しい関数 1 つ。AI に決めさせない）
  └ { kind: "event", draft: {...欄, is_meeting, add_meet, meet_available, ask, ask_count} }
画面
  ask あり → 埋まった欄と質問 1 つを吹き出しに出し、draft から次のカルテを作って持ち続ける
  ask なし → 最後の確かめの欄（今の予定の下書き＋Meet の選択）を出し、カルテを捨てる
```

- karte の鍵が無い頼み（開いたままの古い画面）は、今と同じ動きのまま（§4-3「古い画面の道」・§5）。

### 3-1. 欄の名前の対応表（この表が正。各節はこの名前で書く）

| 欄 | 画面 → backend（`karte`） | backend → 容器（`karte`） | 容器 → backend（`event`） | backend → 画面（`draft`） |
|---|---|---|---|---|
| 予定の名前 | `title`（1000 字まで） | 送らない | `title`（1000 字まで・null 可） | `title`（null 可） |
| 始まり | `start`（ISO 8601 か null） | `start` | `start`（null 可） | `start`（null 可） |
| 終わり | `end`（ISO 8601 か null） | `end` | `end`（null 可） | `end`（null 可） |
| 終日 | `is_all_day` | `is_all_day` | `is_all_day` | `is_all_day` |
| 場所 | `location`（1000 字まで） | 送らない | `location`（1000 字まで） | `location` |
| 内容のメモ | `description`（1000 字まで） | 送らない | `description`（1000 字まで） | `description` |
| 打ち合わせか | `is_meeting` | 送らない | `is_meeting` | `is_meeting` |
| Meet を付けるか | `add_meet`（true/false/null） | 送らない | `add_meet` | `add_meet`（`meet_available` が偽なら常に null） |
| Meet を付けられるか | 送らない | 送らない | — | `meet_available` |
| 直前に聞いた欄 | `asked` | 頼みの外側の `asked` | — | `ask`（次に聞く欄） |
| その欄を聞いた回数 | `asked_count`（0〜2） | 送らない | — | `ask_count` |

- 画面は返ってきた `draft` から次のカルテを作る: 欄は `draft` の同じ名前の値、`asked` ← `draft.ask`、`asked_count` ← `draft.ask_count`。

- 次に聞く欄を AI でなく backend の関数で決める理由: 聞く順・同じ質問の回数（C3・C6）を試験で 100% 確かめられるため。AI の役目は今の「文を決まった形に書き換えるだけ」（`secretary-agent/prompt.txt:1`）のまま変えない。
- 質問の文は画面の翻訳キー（`secretary.ask.*`）で出す。AI に質問の文を書かせない。

## 4. 変更の中身（ファイルごとの前と後）

### 4-1. 次に聞く欄を決める関数（新規 backend/app/services/secretary_karte.py）

```python
ASK_ORDER = ("title", "start", "end", "add_meet")
MAX_ASKS_PER_FIELD = 2

def next_ask(ev, meet_available: bool, asked: str | None, asked_count: int) -> tuple[str | None, int]:
    """空いている欄を決まった順で 1 つ返す。同じ欄を 2 回聞いても埋まらなければ None（最後の確かめの欄を出す）。"""
    missing = [f for f in ("title", "start", "end") if getattr(ev, f) is None]
    if ev.is_meeting and meet_available and ev.add_meet is None:
        missing.append("add_meet")
    if not missing:
        return None, 0
    field = missing[0]
    if field == asked:
        if asked_count >= MAX_ASKS_PER_FIELD:
            return None, asked_count
        return field, asked_count + 1
    return field, 1
```

- 終日（`is_all_day` が真）で終わりが空のときは、⑤で終わり＝始まりにしてから呼ぶ（終日の予定は終わりを聞かない）。
- `ev` は④で合わせた後の値（AI の値が null の欄はカルテの値）。
- 「聞くのをやめた」後の Meet は、最後の確かめの欄で「付けない」を最初の値にする。

### 4-2. backend の入口と出口（`backend/app/schemas/assistant.py`）

- 前 :15-16 `AssistantMessageIn` は `text` だけ。
- 後: `karte: KarteIn | None = None` を足す。鍵が送られたかは `body.model_fields_set` に `"karte"` があるかで見る（pydantic v2。null を送った頼みと、鍵の無い頼みを分ける）。`KarteIn`（extra=forbid）:
  - `title`・`location`・`description` はどれも 1000 字まで（AI の答えの上限と同じにする。小さいと、AI が長く書いた下書きを次の頼みで送ったときに 422 になるため）・`start`/`end` は ISO 8601 か null で 40 字まで（`max_length=40`。超えるか読めなければ 422。上限が無いと小数の桁が長い時刻で送る量が膨らみ、原因と合わない 413 になるため）
  - `is_all_day: bool`・`is_meeting: bool`・`add_meet: bool | None`
  - `asked: Literal["title","start","end","add_meet"] | None`・`asked_count: int`（0〜2）
- 前 :40-48 `IntentEvent` は `title: str`・`start: str`、字数の上限が無い。
- 後: `title: str | None`・`start: str | None`・`is_meeting: bool = False`・`add_meet: bool | None = None`。`title`・`location`・`description` に `max_length=1000` を足す（超えたら形の検査で 502 unreadable。今の :269-272 と同じ道）。初期値があるので、古い容器の答え（2 欄なし）もそのまま通る。
- 前 :126-133 `EventDraft` は `title`/`start`/`end` が str。
- 後: 3 つとも `str | None`。`is_meeting: bool`・`add_meet: bool | None`・`meet_available: bool`・`ask: Literal[...] | None`・`ask_count: int` を足す。`calendar_type` は "personal" のまま（PO「デフォルトは個人」と同じ）。

### 4-3. backend の流れ（`backend/app/routers/assistant.py`）

- 前 :171-175 `_agent_payload(text, model, rules)`。
- 後: カルテが null でないときだけ `"karte": {"start", "end", "is_all_day"}` と `"asked"` を足す。題名・場所・メモ・打ち合わせか・Meet は送らない（④で backend が合わせるので AI に要らない。送る量を増やさないため）。カルテが無いときは今と 1 バイトも違わない。
- 大きさ（実測の計算・`json.dumps(ensure_ascii=False, separators=(",",":"))` で数えた値）: 今の上限いっぱい（文 1000 字＋決まり 150 字×20 件）が 12,143 バイト。カルテ（始まり・終わり・終日）と `asked` を足して 12,261 バイト。上限 15,000（:73）より 2,739 バイト小さい。題名・場所・メモ（各 1000 字）まで送ると 21,303 バイトで超えるため、送らない。
- ①'' 新規: 決まりを読んで大きさを測った後（:260 の後）、commit（:263）の前に `meet_available = await can_add_meet(db, tenant_id, user_id)`。この呼び出しは `async with db.begin_nested():` の中で行う。読めなければ `False`（Meet を聞かないだけで、予定は作れる）。入れ子の取引にするのは、PostgreSQL で失敗した文が外の取引を中断のまま残し、その後の commit と会社の文脈の張り直しを壊さないため（試験は SQLite なので、失敗を起こす試験で入れ子の巻き戻しを確かめる）。判定の式は書かない（`backend/app/services/calendar_service.py:73-80` の 1 か所だけ）。
- 前 :278-289 終わりが無ければ +1 時間（:285）、終わり < 始まりなら 502。
- 後（新しい画面の道 = 頼みに karte の鍵がある）:
  - ④ 合わせる（新しい関数 `merge_karte(ev, karte)` を backend/app/services/secretary_karte.py（新規・§4-1 と同じファイル）に置く）: `title`・`start`・`end`・`location`・`description`・`add_meet` の各欄は次の順で決める。(1) カルテに値があり、その欄が直前に聞いた欄（`karte.asked`）でなければ、カルテの値を使う（AI は題名・場所・メモを見ていないので、AI の値で上書きさせない）。(2) それ以外は、AI の値が null でなければ AI の値、null ならカルテの値。`is_meeting` は AI かカルテのどちらかが真なら真。`is_all_day` は AI かカルテのどちらかが真なら真。聞いていない欄を会話の途中で言い直した値は取り込まない。最後の確かめの欄で手で直す。
  - ④' カルテが null でなく、AI が unknown を返したとき: カルテの値だけで予定として続ける（`kind` は event・欄はカルテのまま）。`next_ask` に渡すと、直前と同じ欄が空のままなので同じ欄を聞き、回数が 1 増える（3 回目は聞かない）。AI が invoice を返したときは、話が変わったとして今と同じ請求書の下書きを返す（画面はカルテを捨てる）。
  - ⑤ 始まりがあれば読む。読めなければ今と同じ 502。終日で終わりが空なら、終わり＝始まり。終わりがあれば読む。読めなければ 502。終わり < 始まりなら終わりを null に戻す（もう一度聞く）。+1 時間は足さない。
- 後（古い画面の道 = 頼みに karte の鍵が無い）: 今の動きを 1 つも変えない。題名か始まりが null なら 502 unreadable（今の形の検査で止まるのと同じ結果）。終わりが無ければ +1 時間（:285・:325 はこの道にだけ残す）。終わり < 始まりなら 502。`ask` は null・`ask_count` は 0・`add_meet` は null で返す。
- 前 :318-330 `EventDraft(...)`。
- 後: 新しい画面の道では `next_ask(ev, meet_available, karte.asked, karte.asked_count)` の結果を `ask`・`ask_count` に入れる（カルテが null なら `asked=None`・`asked_count=0`）。`add_meet` は `meet_available` が偽なら常に null。
- 今の試験はそのまま通る: `backend/tests/test_assistant_router.py:151-159`（終わりに +1 時間）と :239-241（終わり < 始まりで 502）は karte の鍵を送らないので古い画面の道を通り、同じ結果になる。新しい道の試験は別に足す（§9）。

### 4-4. 容器（`secretary-agent/`・`secretary-codex/`）

- `secretary-agent/schema.json:31-43`: `title`・`start` を `["string","null"]` にし、`is_meeting`（boolean）・`add_meet`（boolean か null）を足して required に入れる（2 つの容器が同じファイルを使う。`secretary-codex/Dockerfile:12`）。
- `secretary-agent/compose.mjs:7-10`: `compose(prompt, now, text, rules = [], karte = null, asked = null)`。`karte` が null なら今と 1 文字も違わない。あるときだけ「今の日時」の前に次の区画を足す:

```
途中の予定（前の返事までに埋まった日時。利用者の文で分かった欄だけを入れ、分からない欄は null で返してよい）:
{karte の JSON（start・end・is_all_day だけ）}
直前に聞いた欄: {asked または「なし」}
```

- 日時だけを渡す理由: 「11 時に終わる」のような短い答えを、始まりの日付に合わせて読ませるため。題名などは backend が④で合わせるので渡さない（§4-3 の大きさ）。

- `readKarte(value)` を足す（無ければ null・オブジェクトならそのまま・それ以外は null を返して呼ぶ側が 400）。
- `secretary-agent/server.mjs:139-152`・`secretary-codex/server.mjs:232-245`: 取り出す欄に `karte`・`asked` を足し、次の関数に渡す。
- `secretary-agent/server.mjs:54` `runClaude(text, now, model, rules)` と `secretary-codex/server.mjs:128` `runCodex(...)`: 引数に `karte`・`asked` を足す。`compose` を呼ぶ `secretary-agent/server.mjs:122` と `secretary-codex/server.mjs:215` で、それを `compose` に渡す。
- `secretary-agent/prompt.txt` の変更:

| 行 | 前 | 後 |
|---|---|---|
| 7 | 終わりが文に無ければ end は null | ＋「終日・一日中なら is_all_day=true」 |
| 10 | 予定の頼みなら kind=event | 予定を入れてほしい頼み、または「途中の予定」への答えなら kind=event。分かった欄だけ入れ、分からない欄は null。予定の頼みは情報が足りなくても unknown にしない |
| 新 | — | title は文に書かれた予定の呼び名（打ち合わせ・棚卸し など）をそのまま使い、無ければ null |
| 新 | — | 打ち合わせ・会議・商談・面談・ミーティング・MTG の予定なら is_meeting=true |
| 新 | — | 直前に聞いた欄が add_meet で、はい・付けて なら true、いいえ・不要 なら false。それ以外は null |
| 新 | — | 直前に聞いた欄があるとき、短い答え（「11 時に終わる」「MTG テスト」）はその欄の値として読む |
| 新 | — | 「次からは」「これからは」で始まる、やり方を頼む文は予定の頼みではない（試し r2 を unknown のまま保つ） |
| 11 | 請求書でも予定でもない頼み、または情報が足りず作れない頼み → unknown | 請求書でも予定でもない頼み、または情報が足りない請求書の頼み → unknown |

### 4-5. 画面（`frontend/src/features/secretary/`）

- `frontend/src/features/secretary/secretaryApi.ts:37-45` `EventDraftData`: `title`/`start`/`end` を `string | null`、`is_meeting`・`add_meet`・`meet_available`・`ask`・`ask_count` を足す。
- `frontend/src/features/secretary/secretaryApi.ts:52-54` `sendSecretaryMessage(text, karte)`: 本文に `karte`（無ければ null）を必ず載せる。
- `frontend/src/features/secretary/SecretaryChat.tsx`:
  - `useState` でカルテ（`EventDraftData` から欄と `ask`・`ask_count` を取ったもの）を持つ。保存しない。閉じたら消す（:52-57 に 1 行足す）。
  - :75 送るときにカルテを渡す。
  - :75 送るときは必ず `karte` の鍵を載せる（カルテが無ければ `karte: null`）。backend はこの鍵の有無で新しい道か古い道かを分ける（§4-3）。
  - :76-82 `kind === "event"` で `ask` があれば、新しい吹き出し（埋まった欄の一覧＋`t("secretary.ask." + ask)`）を出し、§3-1 の対応表のとおり `draft` から次のカルテを作る。`ask` が無ければ今の下書きを出し、カルテを消す。`kind` が invoice・unknown ならカルテを消す。
- 新しい吹き出し frontend/src/features/secretary/SecretaryKarteAsk.tsx（新規）: 埋まった欄は「予定の名前・始まり・終わり」を `secretary.event.*` の既存キーで見出しにし、日時は `pages/schedule/schedule-utils` の既存関数で書く。色・余白はデザイントークンだけ。生の select / input は使わない。
- `frontend/src/features/secretary/SecretaryDraftEvent.tsx`:
  - :33-36 `draft.start`/`draft.end` が null なら欄を空にする（`new Date(null)` を呼ばない。1970 年になるため）。:30 `title` が null なら空。
  - :43 `canCreate`: 終日でないときは、日付に加えて始まりと終わりの時刻も空でないことを条件に足す（今は日付だけを見ていて、時刻が空でも「作成」を押せる）。
  - `meet_available` が真のときだけ、:80 の後に `components/Checkbox`（文言は既存キー `schedule.addMeet`）を出す。最初の値は `draft.add_meet === true`。
  - :50-58 送るとき、Meet の選択が入っていて `meet_available` のときだけ `add_meet: true` を足す（予定の画面 `frontend/src/pages/schedule/SchedulePageImpl.tsx:1024-1028` と同じ条件。繰り返しは秘書では作らない）。
  - 場所・内容のメモ（:117-128）と見せる範囲（:129-139・最初は自分だけ）は今のまま。PO の「最後に決定するときに入力欄・プルダウンを見せて」は今の画面で満たしている。
- 翻訳キー（ja / en 同じキー）: `secretary.ask.title`「予定の名前を教えてください。」・`secretary.ask.start`「始まりの日時を教えてください。」・`secretary.ask.end`「終わりの日時を教えてください。一日中の予定なら「終日」と答えてください。」・`secretary.ask.add_meet`「Google Meet のリンクを付けますか？（はい／いいえ）」・吹き出しの見出し `secretary.karte.filled`「ここまでの予定」。

### 4-6. 試しの台本（`docs/handoff/secretary-rulebook/bin0/run_baseline.py`）

- 前 :78-87: event なら `parse_iso(ev.start)` を必ず呼ぶ。新しい答えで始まりが null だと `AttributeError` が出て、捕まえる例外（ValueError・TypeError・AssertionError）に入らず台本が止まる。
- 後: 始まりが null なら日時の検査をとばし、種類だけで判定する。始まりがあるときは今と同じ検査（終わりが無ければ +1 時間で比べる）。C8 は種類の一致（69/69）だけを見るので、判定の基準は変わらない。

### 4-7. 触らない範囲

- `backend/app/routers/calendar.py`（予定の口）・`backend/app/services/calendar_service.py`（`can_add_meet`）・`/google-calendar/status`・予定の画面・請求書の下書き・決まり帳の口と表・使用量の台帳の書き方。

## 5. 古い版と新しい版が混ざる間（1 便で出せる理由）

- 本番反映の順は backend → secretary-agent → secretary-codex（`.github/workflows/deploy.yml:272`・:704・:739）。
- 新しい backend ＋ 古い容器: 古い容器は `karte`・`asked` を読まずに捨てる（`secretary-agent/server.mjs:139-152`）。答えに 2 欄が無くても初期値で通る（§4-2）。この間は今と同じく、題名か始まりが無いと unknown の聞き返しになる。カルテの途中で unknown が返っても、④' で同じ欄を聞き直すだけで、埋まった欄は消えない。
- 古い backend ＋ 新しい容器: 順番上起きない。容器の作り直しが失敗すると警告だけで古い容器が残る（:717・:752）が、それは上の組み合わせと同じ。
- 新しい画面＋古い backend: 同じ段の中で backend の切り替え（`.github/workflows/deploy.yml:493` blue-green）の後に画面を入れ替える（同 :520）ので起きない。
- 開いたままの古い画面＋新しい backend: 古い画面は `karte` の鍵を送らない。backend は古い画面の道（§4-3）を通り、題名・始まりが null の答えは 502、終わりが無ければ +1 時間で、今の画面が読める形（題名・始まり・終わりが必ず文字）だけを返す。古い画面が `title.trim()` や `new Date(null)` で壊れることは無い。新しい容器は情報が足りない予定を unknown でなく null 入りの event で返すため、古い画面ではこの頼みが今の「読めなかった」ときの失敗の文になる。再読み込みまでの間だけで、予定が間違って作られることは無い。

## 6. 代わりの案と選んだ理由

| 案 | 中身 | 選ばなかった理由 |
|---|---|---|
| A. AI に次の質問も書かせる | 指示文に聞く順を書く | 順と回数を試験で確かめられない。AI の答えが揺れる（C3・C6 を ○ にできない） |
| B. 会話の全文を毎回 AI に送る | 画面が履歴を全部送る | 送る量が増え、決まり帳の 15,000 バイトの上限（`backend/app/routers/assistant.py:73`）に近づく。過去の文のどれが今の値か AI が取り違える |
| C. カルテを DB に置く | 会話の途中を保存する | カルテは保存しないという約束（docs/handoff/secretary-event-karte/kgi.md「変えない約束」。PO の承認待ちの目標に置く）に反する。表が増える |
| **D. 画面がカルテを持ち、backend が次の質問を決める（選んだ）** | 欄の値だけを往復させる | 状態は会話の間だけ・表は増えない・順と回数は関数の試験で 100% |

## 7. 危ない点と手当て

| 危ない点 | 手当て |
|---|---|
| 「予定の頼みは unknown にしない」で、やり方を頼む文（試し r2）が event になる | 指示文に「次からは・これからは」の 1 行（§4-4）。C8 の 69/69 で確かめる |
| 画面が送るカルテは書き換えられる | 字数・型・聞いた回数の上限を backend で守る（§4-2）。カルテは下書きの値だけで、予定は「作成」を押すまで作らない（C7）。書き換えても自分の下書きが変わるだけ |
| 頼みの大きさ（文 1000 字＋決まり 20 件＋カルテ）が 15,000 バイトを超える | 容器には日時の 3 欄と `asked` だけを送る（§4-3）。上限いっぱいで 12,261 バイト。実装の試験で上限いっぱいの頼みを作り、15,000 以下であることを確かめる |
| AI が埋まった欄を null で返して、もう一度聞いてしまう | ④で backend が「null ならカルテの値」に合わせる（AI に頼らない）。`merge_karte` の試験で確かめる |
| カルテの途中で AI が unknown を返し、カルテが消える | ④' で予定のまま同じ欄を聞き直す。3 回目は聞かない（C6） |
| AI が長い題名・メモを書き、次の頼みが 422 になる | AI の答えの 3 欄に 1000 字の上限（超えたら 502）・カルテの上限も同じ 1000 字（§4-2） |
| Meet を付けられない人に聞いてしまう | 聞く条件に `can_add_meet` の値を使う（1 か所）。予定の口でも 422 で止まる（`backend/app/routers/calendar.py:425-434`） |
| 決まり帳の便3 と同じファイル（指示文・答えの形・画面の型）を触る | 本件を先に出す。便3 の手順書は本件の合流後の origin/main から作り直す（`docs/handoff/secretary-rulebook/design.md` に注記を足す） |

## 8. 試しの会話 10 本（C2・C3・C4・C6 の判定表）

PO のアカウントが Google をつないだ本人（`meet_available` 真）のときの期待。偽なら Meet を聞く回数は全部 0 が期待（recon.md §7 の未確認を試す前に確かめる）。

| # | 1 通目 | 期待する聞き方の並び | Meet を聞くか |
|---|---|---|---|
| T1 | 明日の10時に打ち合わせを入れて | 終わり →（11 時に終わる）→ Meet →（はい）→ 確かめの欄（Meet に印） | 聞く |
| T2 | あさって 9 時、北風商会の山田さんと商談。1 時間 | Meet →（いいえ）→ 確かめの欄 | 聞く |
| T3 | 来週の月曜 13 時から会議 | 終わり →（14時）→ Meet →（付けて）→ 確かめの欄 | 聞く |
| T4 | 面談を入れたい | 始まり →（明日 15 時）→ 終わり →（16 時）→ Meet →（不要）→ 確かめの欄 | 聞く |
| T5 | 今日の 17 時半から在庫の棚卸し 2 時間 | すぐ確かめの欄 | 聞かない |
| T6 | 11 月 25 日は終日 展示会に出る予定を入れて | すぐ確かめの欄（終日） | 聞かない |
| T7 | 予定を入れて | 名前 →（歯医者）→ 始まり →（金曜 10 時）→ 終わり →（11 時）→ 確かめの欄 | 聞かない |
| T8 | 来週の月曜 13 時に佐藤さんと電話の予定 | 終わり →（13時半）→ 確かめの欄 | 聞かない |
| T9 | 金曜の 14 時から 12 時まで 仕入れ | 終わり（後ろが前より早いので）→（15 時）→ 確かめの欄 | 聞かない |
| T10 | 明日 10 時から棚卸し | 終わり →（うーん）→ 終わり →（わからない）→ 確かめの欄（終わりは空） | 聞かない |

- C2: 各返事で聞いた欄が、その時点で埋まっていないこと（埋まった欄を聞いたら ×）。
- C3: 並びが表のとおり。1 回の返事で質問は 1 つ。
- C6: T10 で「終わり」を聞いた回数が 2 回で止まる。
- backend の試験でも、`next_ask` の全部の分かれ道（順・終日・Meet の 4 条件・同じ欄 3 回目）を確かめる。

## 9. 受け入れの条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| C1 1 回目で名前と始まりが埋まって見え、終わりだけを聞く | 本番で PO が「明日の10時に打ち合わせを入れて」を 1 回。吹き出しを目視 |
| C2 埋まった欄を聞き直す回数 0 | §8 の 10 本を本番で流し、返事ごとに記録して照合 |
| C3 1 回 1 欄・決まった順 | §8 の 10 本の並び ＋ `next_ask` の試験（全部の分かれ道） |
| C4 Meet は打ち合わせ×つないだ本人のときだけ。「はい」でリンクが付く | §8 の 4 本／6 本。T1 の予定を予定の画面で開き Meet のリンクを目視 |
| C5 確かめの欄に場所・内容・見せる範囲（最初は自分だけ） | 画面を目視 1 回 ＋ 画面の試験 |
| C6 同じ質問の 3 回目 0 | T10 ＋ `next_ask` の試験 |
| C7 「作成」まで予定は増えない | §8 の前後で予定の件数を読み取り鍵で数えて照合 |
| C8 試し 23 件の種類 69/69 | 本番反映後に `docs/handoff/secretary-rulebook/bin0/run_baseline.py` を 1 回 |
| 古い版の容器でも壊れない | backend の試験で、2 欄の無い答えが初期値で通ること |
| 古い画面でも壊れない | backend の試験で、karte の鍵の無い頼みが今と同じ結果になること（今の試験 `backend/tests/test_assistant_router.py:151-159`・:239-241 がそのまま緑。題名か始まりが null の答えは 502） |
| 埋まった欄は AI が落としても上書きしても消えない | `merge_karte` の試験（AI が null・カルテに値 → カルテの値。聞いた欄で AI に値 → AI の値。聞いていない欄でカルテに値・AI に別の値 → カルテの値（題名・メモを上書きしない）。is_meeting は一度真なら真） |
| Meet を読めなくても頼みが壊れない | backend の試験: `can_add_meet` が例外を出したとき、`meet_available` は偽で 200 が返り、その後の名前探しも動く（入れ子の取引の巻き戻し） |
| カルテの時刻の長さ | backend の試験: 41 字以上の `start` は 422 |
| 画面の今の試験の書き直し | `frontend/src/features/secretary/SecretaryChat.test.tsx:137` は送る本文を `{ text: "make something" }` ちょうどで確かめている。`{ text: "make something", karte: null }` に書き直す |
| カルテの途中の unknown | backend の試験: カルテあり＋unknown の答え → event・同じ欄・回数＋1。回数 2 のとき → ask は null |
| 時刻が空なら「作成」を押せない | 画面の試験: 終日でなく時刻が空のとき、作成のボタンが押せない |
| 送る量 | backend の試験: 文 1000 字・決まり 150 字×20 件・カルテありの頼みが 15,000 バイト以下 |
| 試しの台本が null の始まりで止まらない | `docs/handoff/secretary-rulebook/bin0/run_baseline.py` を、始まりが null の event も種類だけで判定するよう直す（§4-6）。手元で null 入りの答えを 1 つ読ませて止まらないこと |
| カルテ無しの頼みの文が今と同じ | `compose` の試験で、`karte` 無しの出力が今と 1 文字も違わないこと |
| 画面の決まり | i18n の検査（ja/en 同じキー）・金型の検査（ADR-144）・デザイントークンの検査が CI で緑 |

## 10. 外部・過去事例の参照と我々への応用

- Rasa の forms 機能（出典: Rasa 公式文書 https://legacy-docs-oss.rasa.com/docs/rasa/forms ・Context7 `/websites/legacy-docs-oss_rasa_rasa` で 2026-11-14 に確認）
  - 何を: 会話で必須の欄（slot）を集める仕組み。欄ごとに決まった質問 `utter_ask_<欄名>` を持つ。
  - どう: 埋まった欄は飛ばし、空いている欄を順に 1 つずつ聞く。必須の欄がすべて埋まると欄集めを終える。
  - 本件に使ったところ: 「必須の欄の一覧」「決まった質問の文」「埋まった欄は聞かない」「全部埋まったら次へ」の 4 点。質問の文を AI でなく決まった文にした（§3）のもこの形。
  - 数値: 公式文書に成功率などの数は無い。成功の証明には使わず、作りの型としてだけ使う。
  - 適用の限界: Rasa は会話の状態をサーバーに持つ。本件はカルテを保存しない約束（docs/handoff/secretary-event-karte/kgi.md「変えない約束」）のため画面が持つ（§6 の案 D）。

## 11. 維持の仕組み

- 守り手: backend の試験（next_ask の全部の分かれ道）・容器の試験（compose のカルテ無しの出力が今と同じ）・画面の試験が .github/workflows/test.yml で PR ごとに走る。指示文は決まり帳の試し 23 件。
- 聞く順と回数: `next_ask` の試験（backend）が CI で毎回走る。順を変えるにはこの試験と ADR-1078 を同時に変える必要がある。
- 欄の一覧の正本: 予定の口（`CreateEventBody`）。秘書の欄を足すときは ADR-1078 の表を改める。
- 指示文: 決まり帳の試し 23 件（`backend/app/assistant_regression/cases.json`）を、指示文を変える PR のたびに流す（ADR-1077 便0 の手順）。
- 持ち主: 設計は Opus、実装はクラウドの Sonnet、合格の判定は PO の目視（C1・C4・C5）。

## 12. 進め方（1 便）

1. この設計の審査（クラウド）→ PO に KGI と設計の承認を 1 回で聞く。
2. 承認後、実装の手順書（card.md）を書き、手順書の点検 → クラウドの Sonnet に実装を頼む。
3. マージ前の審査役（opus）→ マージ → 本番反映 → §8・§9 の確かめ → PO の目視。
4. 決まり帳の便3 は、この合流の後の origin/main から手順書を作る。
