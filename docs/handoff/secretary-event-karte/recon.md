# 現在地の調べ — 秘書の「予定のカルテ」

調べた人: Opus（2026-11-14）。根拠はすべて `git show origin/main:<path>`（origin/main = 73bf937a8・2026-11-14 00:58 JST）と本番のログの読み取り。推測は書かない。分からないことは「未確認」と書く。

親: [kgi.md](kgi.md) ／ 設計: [design.md](design.md)

## 0. 既存 ADR の検索

- `git grep -l -i "secretary\|秘書" origin/main -- docs/adr` → ADR-1056（秘書の作り）・ADR-1057（Google カレンダーは本人だけ同期）・ADR-1058（AI の担当表）・ADR-1077（決まり帳）。
- 予定の欄を AI が 1 つずつ聞く・会話の途中の状態を持つ、を決めた ADR は無い。ADR-1056:16 は「AI に渡すのは利用者が書いた文と日本時間の今の日時だけ」、ADR-1077 §What が「＋承認済みの決まり」に改めた。

## 1. 起きたこと（本番・2026-11-13 PO の試し）

- PO の文と秘書の返事（PO がチャットに貼った写し）: 「明日の10時に打ち合わせを入れて」→「打ち合わせのタイトルを教えてください。」→「MTG テスト」→「予定の日時を教えてください。」→「明日の10時」→「予定の内容を教えてください。」
- 本番の backend のログ: `POST /api/v1/assistant/messages 200 OK` が 3 件。`rules_unreadable` は 0 件（生の記録 /tmp/CC報告ファイル/secbin2b/po-try-full.txt・po-try2.txt）。

## 2. なぜそう動くか（事実）

### 2-1. 画面は最新の 1 文だけを送る（前の頼みを持たない）
- `frontend/src/features/secretary/secretaryApi.ts:52-54` `sendSecretaryMessage(text)` は `{ text }` だけを POST する。
- `frontend/src/features/secretary/SecretaryChat.tsx:75` `const reply = await sendSecretaryMessage(trimmed);`。会話は `useState` だけ（同 :47・:52-57 閉じたら消す）。
- `backend/app/schemas/assistant.py:15-16` `AssistantMessageIn` は `text` だけ。
- `backend/app/routers/assistant.py:171-175` 容器へは `{"text","now","model","rules"}` だけ。

### 2-2. 足りないと「予定」と決めずに聞き返す
- `secretary-agent/prompt.txt:11`「請求書でも予定でもない頼み、または情報が足りず作れない頼みは、kind=unknown にして reply に短い聞き返しを日本語で書きます（invoice と event は null）。」
- `secretary-agent/schema.json:34-38` 予定の `title`・`start` は文字列のみ（null 不可）。題名か始まりが無いと予定の形を作れない。
- `backend/app/schemas/assistant.py:40-48` `IntentEvent` も `title: str`・`start: str`。
- 結果: 1 回目は「題名が無い」で unknown、2 回目「MTG テスト」は前の文を持たないので日時が無く unknown、3 回目「明日の10時」も題名が無く unknown。

### 2-3. 終わりが無いと backend が 1 時間を足す
- `secretary-agent/prompt.txt:7`「終わりが文に無ければ end は null にします。」
- `backend/app/routers/assistant.py:285` `event_end = parse_iso(ev.end) if ev.end is not None else event_start + timedelta(hours=1)`、同 :325 で下書きの end に入れる。

## 3. 予定の口と今の下書きの欄

- 予定を作る口 `backend/app/routers/calendar.py:114-123` `CreateEventBody`: `title`・`start_datetime`・`end_datetime`（3 つとも必須）・`calendar_type="shared"`・`description`・`location`・`is_all_day`・`add_meet=False`・`recurrence="none"`。「予定の種類」の欄は無い。
- 秘書の下書き `frontend/src/features/secretary/SecretaryDraftEvent.tsx`:
  - :30-39 名前・終日・始まり日時・終わり日時・場所・内容・見せる範囲を全部欄に出す。見せる範囲は下書きの `calendar_type`（:39）。
  - :43 `canCreate` は 名前・始まり日付・終わり日付が空でないとき。
  - :50-58 `POST /calendar/events` に送る。`add_meet` は送らない。
  - :33-36 `new Date(draft.start)`・`new Date(draft.end)` で欄に入れる（null は想定していない）。
- 下書きの見せる範囲の初期値: `backend/app/schemas/assistant.py:133` `calendar_type: Literal["personal"] = "personal"`、`backend/app/routers/assistant.py:329`、`frontend/src/features/secretary/secretaryApi.ts:44`。PO の「デフォルトは個人」と今の値は同じ。

## 4. Google Meet

- 付けてよいかの判定は 1 か所: `backend/app/services/calendar_service.py:73-80` `can_add_meet`（送る方式が bidirectional / write_only で、Google をつないだ本人だけ真）。
- 予定の口の守り: `backend/app/routers/calendar.py:425-434`（繰り返しと Meet の両方は不可・`can_add_meet` が偽なら 422）。
- 画面への出し方: `backend/app/routers/google_calendar.py:266-267` `/google-calendar/status` の `meet_available` が `can_add_meet` を呼ぶ。予定の画面は `frontend/src/pages/schedule/SchedulePageImpl.tsx:822-825` で読み、:1024-1028 で「つないだ本人で、入っていて、Meet が無く、繰り返さない」ときだけ `add_meet: true` を送る。
- 文言の翻訳キー `schedule.addMeet`（`frontend/src/locales/ja.json:3372`「Google Meet のビデオ会議を追加」）。

## 5. 容器（2 つ）と配り方

- 2 つの容器は同じ `secretary-agent/prompt.txt`・`schema.json`・`compose.mjs` を使う: `secretary-agent/Dockerfile:6`、`secretary-codex/Dockerfile:12`。
- AI に渡す文の組み立て `secretary-agent/compose.mjs:7-10`。決まりが無いときは前と 1 文字も違わない（:6 の注記）。
- 容器は頼みの本文のうち `text`・`now`・`model`・`rules` だけを取り出す（`secretary-agent/server.mjs:139-152`、`secretary-codex/server.mjs:232-245`）。ほかの欄は読まずに捨てる。
- 本番反映の順: `.github/workflows/deploy.yml:272`（backend を含む本体）→ :704（secretary-agent）→ :739（secretary-codex）。容器の作り直しが失敗しても警告だけ（:717・:752）。

## 6. 決まり帳（ADR-1077）との関係

- 決まり帳の便3 は `secretary-agent/prompt.txt`・`schema.json`・画面の型を変える予定（`docs/handoff/secretary-rulebook/design.md:177`）。便3 は設計済み・手順書未作成・実装未着手。
- 試しの 23 件 `backend/app/assistant_regression/cases.json`: 予定 8 件のうち終わりの無いもの e3「来週の月曜 13 時に佐藤さんと電話の予定」・e7「金曜の 14 時からオンラインで仕入れの相談、場所は Zoom」。今は種類 event で合格（`docs/handoff/secretary-rulebook/baseline.md` §2・69/69）。試しは種類だけを見る。

## 7. 未確認

- 本番で PO のアカウントの `can_add_meet` が真か（Google をつないだ本人か）は、まだ確かめていない。C4 の「はい」の試しの前に `/google-calendar/status` の `meet_available` を見る。
