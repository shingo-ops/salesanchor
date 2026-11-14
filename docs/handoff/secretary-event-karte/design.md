# 設計 — 秘書の「予定のカルテ」（足りない欄だけを順に聞く）

作った人: Opus（Planner）2026-11-14。状態: 設計案（審査前）。PO の実装承認は未。

親: [kgi.md](kgi.md) ／ 現在地: [recon.md](recon.md) ／ ADR: [ADR-1078](../../adr/ADR-1078-secretary-event-karte.md)（Proposed）／ 改める ADR: ADR-1056・ADR-1077（一部）

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
画面（カルテを会話の間だけ持つ）
  └ POST /assistant/messages { text, karte?: {...欄, asked, asked_count} }
backend
  ① 担当を読む ①' 決まりを読む ①'' Meet を付けてよいか（can_add_meet）を読む   ← どれも commit の前
  ② commit
  ③ 容器へ { text, now, model, rules, karte?, asked? }
容器（AI は欄の値を埋めるだけ。次に何を聞くかは決めない）
  └ { kind: "event", event: { title|null, start|null, end|null, is_all_day, location, description, is_meeting, add_meet|null } }
backend
  ④ 日時の検査（終わり < 始まり なら終わりを空に戻す）
  ⑤ 次に聞く欄を決まった順で決める（新しい関数 1 つ。AI に決めさせない）
  └ { kind: "event", draft: {...欄, is_meeting, add_meet, meet_available, ask, ask_count} }
画面
  ask あり → 埋まった欄と質問 1 つを吹き出しに出し、カルテを持ち続ける
  ask なし → 最後の確かめの欄（今の予定の下書き＋Meet の選択）を出し、カルテを捨てる
```

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

- 終日（`is_all_day` が真）で終わりが空のときは、④で終わり＝始まりにしてから呼ぶ（終日の予定は終わりを聞かない）。
- 「聞くのをやめた」後の Meet は、最後の確かめの欄で「付けない」を最初の値にする。

### 4-2. backend の入口と出口（`backend/app/schemas/assistant.py`）

- 前 :15-16 `AssistantMessageIn` は `text` だけ。
- 後: `karte: KarteIn | None = None` を足す。`KarteIn`（extra=forbid）:
  - `title` 200 字まで・`location` 200 字まで・`description` 500 字まで・`start`/`end` は ISO 8601 か null（読めなければ 422）
  - `is_all_day: bool`・`is_meeting: bool`・`add_meet: bool | None`
  - `asked: Literal["title","start","end","add_meet"] | None`・`asked_count: int`（0〜2）
- 前 :40-48 `IntentEvent` は `title: str`・`start: str`。
- 後: `title: str | None`・`start: str | None`・`is_meeting: bool = False`・`add_meet: bool | None = None`。初期値があるので、古い容器の答え（2 欄なし）もそのまま通る。
- 前 :126-133 `EventDraft` は `title`/`start`/`end` が str。
- 後: 3 つとも `str | None`。`is_meeting: bool`・`add_meet: bool | None`・`meet_available: bool`・`ask: Literal[...] | None`・`ask_count: int` を足す。`calendar_type` は "personal" のまま（PO「デフォルトは個人」と同じ）。

### 4-3. backend の流れ（`backend/app/routers/assistant.py`）

- 前 :171-175 `_agent_payload(text, model, rules)`。
- 後: `karte` があるときだけ `"karte"`（欄の値だけ）と `"asked"` を足す。無いときは今と 1 バイトも違わない。
- ①'' 新規: 決まりを読んで大きさを測った後（:260 の後）、commit（:263）の前に `meet_available = await can_add_meet(db, tenant_id, user_id)`。読めなければ `False`（Meet を聞かないだけで、予定は作れる）。判定の式は書かない（`backend/app/services/calendar_service.py:73-80` の 1 か所だけ）。
- 前 :278-289 終わりが無ければ +1 時間（:285）、終わり < 始まりなら 502。
- 後:
  - 始まりがあれば読む。読めなければ今と同じ 502。
  - 終日で終わりが空なら、終わり＝始まり。
  - 終わりがあれば読む。読めなければ 502。終わり < 始まりなら終わりを null に戻す（もう一度聞く）。
  - +1 時間を足す行（:285 の else）と、:325 の同じ足し算を消す。
- 前 :318-330 `EventDraft(...)`。
- 後: `next_ask(ev, meet_available, karte.asked, karte.asked_count)` の結果を `ask`・`ask_count` に入れる。`add_meet` は `meet_available` が偽なら常に null。

### 4-4. 容器（`secretary-agent/`・`secretary-codex/`）

- `secretary-agent/schema.json:31-43`: `title`・`start` を `["string","null"]` にし、`is_meeting`（boolean）・`add_meet`（boolean か null）を足して required に入れる（2 つの容器が同じファイルを使う。`secretary-codex/Dockerfile:12`）。
- `secretary-agent/compose.mjs:7-10`: `compose(prompt, now, text, rules = [], karte = null, asked = null)`。`karte` が null なら今と 1 文字も違わない。あるときだけ「今の日時」の前に次の区画を足す:

```
途中の予定（前の返事までに埋まった欄。利用者の文が変えない限り同じ値を返す）:
{karte の JSON}
直前に聞いた欄: {asked または「なし」}
```

- `readKarte(value)` を足す（無ければ null・オブジェクトならそのまま・それ以外は null を返して呼ぶ側が 400）。
- `secretary-agent/server.mjs:139-152`・`secretary-codex/server.mjs:232-245`: 取り出す欄に `karte`・`asked` を足し、`compose` に渡す。
- `secretary-agent/prompt.txt` の変更:

| 行 | 前 | 後 |
|---|---|---|
| 7 | 終わりが文に無ければ end は null | ＋「終日・一日中なら is_all_day=true」 |
| 10 | 予定の頼みなら kind=event | 予定を入れてほしい頼み、または「途中の予定」への答えなら kind=event。分かった欄だけ入れ、分からない欄は null。予定の頼みは情報が足りなくても unknown にしない |
| 新 | — | title は文に書かれた予定の呼び名（打ち合わせ・棚卸し など）をそのまま使い、無ければ null |
| 新 | — | 打ち合わせ・会議・商談・面談・ミーティング・MTG の予定なら is_meeting=true |
| 新 | — | 直前に聞いた欄が add_meet で、はい・付けて なら true、いいえ・不要 なら false。それ以外は途中の予定の値のまま（無ければ null） |
| 新 | — | 直前に聞いた欄があるとき、短い答え（「11 時に終わる」「MTG テスト」）はその欄の値として読む |
| 新 | — | 「次からは」「これからは」で始まる、やり方を頼む文は予定の頼みではない（試し r2 を unknown のまま保つ） |
| 11 | 請求書でも予定でもない頼み、または情報が足りず作れない頼み → unknown | 請求書でも予定でもない頼み、または情報が足りない請求書の頼み → unknown |

### 4-5. 画面（`frontend/src/features/secretary/`）

- `frontend/src/features/secretary/secretaryApi.ts:37-45` `EventDraftData`: `title`/`start`/`end` を `string | null`、`is_meeting`・`add_meet`・`meet_available`・`ask`・`ask_count` を足す。
- `frontend/src/features/secretary/secretaryApi.ts:52-54` `sendSecretaryMessage(text, karte?)`: カルテがあるときだけ本文に `karte` を載せる。
- `frontend/src/features/secretary/SecretaryChat.tsx`:
  - `useState` でカルテ（`EventDraftData` から欄と `ask`・`ask_count` を取ったもの）を持つ。保存しない。閉じたら消す（:52-57 に 1 行足す）。
  - :75 送るときにカルテを渡す。
  - :76-82 `kind === "event"` で `ask` があれば、新しい吹き出し（埋まった欄の一覧＋`t("secretary.ask." + ask)`）を出し、カルテを入れ替える。`ask` が無ければ今の下書きを出し、カルテを消す。`kind` が invoice・unknown ならカルテを消す。
- 新しい吹き出し frontend/src/features/secretary/SecretaryKarteAsk.tsx（新規）: 埋まった欄は「予定の名前・始まり・終わり」を `secretary.event.*` の既存キーで見出しにし、日時は `pages/schedule/schedule-utils` の既存関数で書く。色・余白はデザイントークンだけ。生の select / input は使わない。
- `frontend/src/features/secretary/SecretaryDraftEvent.tsx`:
  - :33-36 `draft.start`/`draft.end` が null なら欄を空にする。:30 `title` が null なら空。
  - `meet_available` が真のときだけ、:80 の後に `components/Checkbox`（文言は既存キー `schedule.addMeet`）を出す。最初の値は `draft.add_meet === true`。
  - :50-58 送るとき、Meet の選択が入っていて `meet_available` のときだけ `add_meet: true` を足す（予定の画面 `frontend/src/pages/schedule/SchedulePageImpl.tsx:1024-1028` と同じ条件。繰り返しは秘書では作らない）。
  - 場所・内容のメモ（:117-128）と見せる範囲（:129-139・最初は自分だけ）は今のまま。PO の「最後に決定するときに入力欄・プルダウンを見せて」は今の画面で満たしている。
- 翻訳キー（ja / en 同じキー）: `secretary.ask.title`「予定の名前を教えてください。」・`secretary.ask.start`「始まりの日時を教えてください。」・`secretary.ask.end`「終わりの日時を教えてください。一日中の予定なら「終日」と答えてください。」・`secretary.ask.add_meet`「Google Meet のリンクを付けますか？（はい／いいえ）」・吹き出しの見出し `secretary.karte.filled`「ここまでの予定」。

### 4-6. 触らない範囲

- `backend/app/routers/calendar.py`（予定の口）・`backend/app/services/calendar_service.py`（`can_add_meet`）・`/google-calendar/status`・予定の画面・請求書の下書き・決まり帳の口と表・使用量の台帳の書き方。

## 5. 古い版と新しい版が混ざる間（1 便で出せる理由）

- 本番反映の順は backend → secretary-agent → secretary-codex（`.github/workflows/deploy.yml:272`・:704・:739）。
- 新しい backend ＋ 古い容器: 古い容器は `karte`・`asked` を読まずに捨てる（`secretary-agent/server.mjs:139-152`）。答えに 2 欄が無くても初期値で通る（§4-2）。この間は今と同じく、題名か始まりが無いと unknown の聞き返しになる（悪くはならない）。
- 古い backend ＋ 新しい容器: 順番上起きない。容器の作り直しが失敗すると警告だけで古い容器が残る（:717・:752）が、それは上の組み合わせと同じ。
- 画面: 同じ段の中で backend の切り替え（`.github/workflows/deploy.yml:493` blue-green）の後に画面を入れ替える（同 :520）。新しい画面＋古い backend の組み合わせは起きない。開いたままの古い画面＋新しい backend は `karte` を送らないので今と同じ動き。

## 6. 代わりの案と選んだ理由

| 案 | 中身 | 選ばなかった理由 |
|---|---|---|
| A. AI に次の質問も書かせる | 指示文に聞く順を書く | 順と回数を試験で確かめられない。AI の答えが揺れる（C3・C6 を ○ にできない） |
| B. 会話の全文を毎回 AI に送る | 画面が履歴を全部送る | 送る量が増え、決まり帳の 15,000 バイトの上限（`backend/app/routers/assistant.py:73`）に近づく。過去の文のどれが今の値か AI が取り違える |
| C. カルテを DB に置く | 会話の途中を保存する | ADR-1056「会話を残さない」に反する。表が増える |
| **D. 画面がカルテを持ち、backend が次の質問を決める（選んだ）** | 欄の値だけを往復させる | 状態は会話の間だけ・表は増えない・順と回数は関数の試験で 100% |

## 7. 危ない点と手当て

| 危ない点 | 手当て |
|---|---|
| 「予定の頼みは unknown にしない」で、やり方を頼む文（試し r2）が event になる | 指示文に「次からは・これからは」の 1 行（§4-4）。C8 の 69/69 で確かめる |
| 画面が送るカルテは書き換えられる | 字数・型・聞いた回数の上限を backend で守る（§4-2）。カルテは下書きの値だけで、予定は「作成」を押すまで作らない（C7）。書き換えても自分の下書きが変わるだけ |
| 頼みの大きさ（文 1000 字＋決まり 20 件＋カルテ）が 15,000 バイトを超える | 上限いっぱいの日本語で約 15,200 バイト。超えたときは今の 413 の文が出る。全部の欄が上限いっぱいのときだけ起きるので受け入れ、実装の試験で上限いっぱいの大きさを測って記録する |
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
| 古い版の容器でも壊れない | backend の試験で、2 欄の無い答え・`karte` 無しの頼みが今と同じ結果になること |
| カルテ無しの頼みの文が今と同じ | `compose` の試験で、`karte` 無しの出力が今と 1 文字も違わないこと |
| 画面の決まり | i18n の検査（ja/en 同じキー）・金型の検査（ADR-144）・デザイントークンの検査が CI で緑 |

## 10. 外部・過去事例の参照と我々への応用

- Rasa の forms 機能（出典: Rasa 公式文書 https://legacy-docs-oss.rasa.com/docs/rasa/forms ・Context7 `/websites/legacy-docs-oss_rasa_rasa` で 2026-11-14 に確認）
  - 何を: 会話で必須の欄（slot）を集める仕組み。欄ごとに決まった質問 `utter_ask_<欄名>` を持つ。
  - どう: 埋まった欄は飛ばし、空いている欄を順に 1 つずつ聞く。必須の欄がすべて埋まると欄集めを終える。
  - 本件に使ったところ: 「必須の欄の一覧」「決まった質問の文」「埋まった欄は聞かない」「全部埋まったら次へ」の 4 点。質問の文を AI でなく決まった文にした（§3）のもこの形。
  - 数値: 公式文書に成功率などの数は無い。成功の証明には使わず、作りの型としてだけ使う。
  - 適用の限界: Rasa は会話の状態をサーバーに持つ。本件は ADR-1056 の「会話を残さない」のため画面が持つ（§6 の案 D）。

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
