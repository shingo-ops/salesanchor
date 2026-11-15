# recon — 秘書チャット 予定の日付の読み方

親: [../design.md](../design.md) ／ 目標: [kgi.md](kgi.md) ／ 設計: [design.md](design.md) ／ 手順書: [card.md](card.md)

すべて origin/main 1eaefbf8c（直し1 のマージ d2f900a33 を含む。本番の HEAD d2f900a33 と、以下のファイルは同じ）で読んだ。

## 1. 本番で起きたこと（観測事実）

- 2026-11-15（日）13:5x〜14:1x JST、直し1 の本番確認で、本番の使い捨ての backend 容器から試しの会話（`docs/handoff/secretary-event-karte/design.md` §8 の T1〜T10。tenant 1・user 1）を流した。
- T3「来週の月曜 13 時から会議」の 1 通目の始まり（AI の読み）:
  - 1 回目の流し: `2026-11-17T13:00:00+09:00`（火曜）
  - 2 回目の流し: `2026-11-16T13:00:00+09:00`（月曜）
  - 3 回目の流し: `2026-11-23T13:00:00+09:00`（次の次の月曜）
- T8「来週の月曜 13 時に佐藤さんと電話の予定」の始まりは流すたびに `2026-11-16T13:00:00+09:00`。
- 時刻（13:00）と時差の印（`+09:00`）は全部の回で正しい。揺れたのは日付だけ。
- ほかの試しの答えの時刻も全部 `+09:00` 付きの ISO 8601（T1〜T10 の全行）。例: T6「11 月 25 日は終日」→ `2026-11-25T00:00:00+09:00`。

## 2. 日付を決めている場所（コード）

- `secretary-agent/compose.mjs:14`: AI への文は `今の日時: ${now}` だけ。`now` は ISO の数字で、曜日の文字は無い。
- `secretary-agent/prompt.txt:7`: 「日時は、文の後ろに付く「今の日時」から計算します。結果は +09:00 を付けた ISO 8601」。何日かの数え方は AI に任せている。
- `secretary-codex/server.mjs:24-25` も同じ `compose.mjs` を使う（:215 で呼ぶ）。本番の担当（`get_ai_assignment(db, "secretary_intent")`）は codex の gpt-5.6-terra。
- `backend/app/routers/assistant.py:175-186` `_agent_payload`: `now` を :181 で `datetime.now(_JST)` から作る（`_JST` は :78）。呼ぶのは :284 だけ（試験からも直接呼ぶ: `backend/tests/test_assistant_karte.py:347`・`backend/tests/test_assistant_rules_router.py:128`）。
- `backend/app/routers/assistant.py:282` `new_path`（karte の鍵がある頼み）。新しい画面の道は :313-326:
  - :316-317 カルテの途中の unknown → カルテだけで予定（`merge_karte(None, karte)`）。AI はこの文で日付を読んでいない。
  - :318-320 予定の答え → `merge_karte(intent.event, karte)`。
  - :321-326 `settle_dates`（`backend/app/services/secretary_karte.py:50-68`）。日時が時刻として読めるかと、終わり < 始まりを見る。日付が正しいかは見ない。
- `backend/app/services/secretary_karte.py:18-36` `merge_karte`: カルテに値があり直前に聞いた欄でなければカルテの値を使う。→ 始まりがカルテ由来のとき、今の文の日付の言い方は始まりの言い方ではない。
- 古い画面の道（karte の鍵が無い頼み）は `backend/app/routers/assistant.py:327-` 以降。`merge_karte`・`settle_dates` を通らない。
- `backend/app/schemas/assistant.py:126-128` `parse_iso` は `datetime.fromisoformat`（`Z` を `+00:00` に替える）。

## 3. 試験

- `backend/tests/test_assistant_karte.py`（348 行）: `_event`・`_unknown`・`_karte`・`meet` の補助と、`tests.test_assistant_router` の `_fixture`・`_mock_agent`・`_respond`・`allowed` を使う。日付の言い方を見る試験は無い。
- `backend/tests/test_assistant_karte.py:324-333` `test_payload_without_karte_is_unchanged`: 古い画面の道の頼みの鍵が `{"text","now","model","rules"}` だけ。
- 「今」を固定する仕組みは試験にも本体にも無い（`datetime.now` を直接呼ぶ）。

## 4. 既存 ADR の検索

- `git grep -il "secretary_karte\|予定のカルテ\|今の日時" docs/adr/` → `docs/adr/ADR-1078-secretary-event-karte.md`・`docs/adr/ADR-1056-secretary-chat.md`（と索引 `docs/adr/README.md`）。
- ADR-1078:24 は「AI に渡すのは利用者が書いた文と日本時間の今の日時だけ（＋途中の予定の日時と直前に聞いた欄）」。本件は AI に渡すものを変えない。backend が AI の答えを検査して直す側の変更で、ADR-1078 の「カルテの判断は backend に置く」の範囲。ADR の変更は不要。

## 5. 未確認

- 本番の AI が `+09:00` 以外の時差の印（`Z` など）で答えた例は観測していない（§1）。その場合は日付を替えない設計にする（design.md §3）。
- 「来週」を日曜にどう数えるかの社内の決まりは、PO の 2026-11-15「1」（週は月〜日）だけ。ほかの文書には無い。
