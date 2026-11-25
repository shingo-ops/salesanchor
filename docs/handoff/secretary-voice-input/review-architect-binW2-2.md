# 設計の審査（architect）第2回 — 便W2「声で直す便の気をつける点 3 つ」

- 審査した物: 枝 `origin/release/secretary-voice-edit-followup`（先頭 ef5a7ed3e）の `docs/handoff/secretary-voice-input/design.md` §17・`docs/handoff/secretary-voice-input/card-binW2.md`。直した所は `git diff 482820832 ef5a7ed3e`（2 ファイル・+8/-5）で確認。実物は同じ枝の `backend/app/routers/assistant.py`・`backend/app/services/secretary_dates.py`・`backend/app/services/secretary_karte.py`・`frontend/src/features/secretary/secretaryVoiceAnswer.ts`・`SecretaryChat.tsx`・`backend/tests/test_assistant_karte.py`。
- 第1回: `docs/handoff/secretary-voice-input/review-architect-binW2-1.md`（REVISE・R1 と L1〜L5）。
- 手元で動かせた物: なし（読むだけ。pytest・vitest は流していない）。以下は実物を読んでの手計算。

## 判定: APPROVE

1. 第1回の R1（日付の表の条件を `same_time` と `same_day` の両方にする・import を残す・+01:00 の試験 1 本）が design §17-4 の 3・card §3・§4 に直り、実物（`backend/app/routers/assistant.py:340`・`backend/app/services/secretary_dates.py:163-173`・`backend/app/services/secretary_karte.py:96-103`）と食い違わない。
2. L1〜L5 の直しも実物と食い違わず、直しで新しく出た矛盾・穴は無い（下の (3)）。
3. 直さないと作れない・壊れる物は無い。残りは軽い指摘 L1〜L2 だけ（実装者への注意で足りる）。

## R（直さないと壊れる物）

なし。

## 点検の結果

### (1) R1 の取り込み

- design §17-4 の 3「後」の 2 つ目の箇条は「`ai_ev.start` が null でなく、かつ（カルテの始まりが null か、`not same_time(...)` かつ `not same_day(...)`）」になった。実物の今の条件は `backend/app/routers/assistant.py:340`（`karte.start is None or not same_time(ai_ev.start, karte.start)`）。`same_day` を足すと「同じ時刻でも同じ日でもないときだけ表」になり、今の `same_time` の守りは残る。
- import: `backend/app/routers/assistant.py:58` が `same_time` を import している。口で使い続けるので残す、と design §17-4 の 3 と card §3 が一致した（第1回の「消さない／外す」の同居は消えた）。
- 手計算（R1 の試験）: カルテ始まり `2026-11-10T02:00:00+01:00`・AI の始まり `2026-11-10T10:00:00+09:00`（同じ瞬間 = UTC 01:00）。
  - `same_time` は `parse_iso(a) == parse_iso(b)`（`backend/app/services/secretary_karte.py:96-103`）で真 → 表を当てない。
  - 直しの合わせ（`backend/app/services/secretary_karte.py:153-170` あたりの `merge_edit`）: `not same_time(ev.start, karte.start)` が偽なので start は替わらない。`values["start"] == ev.start` は文字が違い偽 → end の計算もしない。description だけ入り `edited` 真。期待「日付が動かない」と合う。
  - `same_day` だけの条件だと `_day_of` が +01:00 で None（`secretary_dates.py:171-172`）→ 偽 → 表が当たり「明日」で 2026-11-02 に動く → 試験は先に落ちる（card §6 の「試験を先に足して落ちることを確かめる」と合う）。
- 既存の 2 試験: `test_edit_same_start_does_not_move_date_by_description_words`・`test_edit_changed_start_gets_day_table`（`backend/tests/test_assistant_karte.py:483-500`）は新しい条件でも結果が変わらない（前者は `same_time` 真で表なし・後者は両方偽で表が当たる）。
- 時差の印が混ざる場合（カルテが印なし・AI が +09:00）: `same_time` は比べられず `TypeError` → 文字比べで偽。`same_day` は両方読めて日が同じなら真 → 表は当たらない（日が違えば当たる）。壊れない。

### (2) L1〜L5 と実物

| 直し | 実物との突き合わせ | 合う |
|---|---|---|
| L1 取り除く語は `squash(fold(語))`・空になる語は飛ばす・取るのは `matchesAtStart` が通った後 | `secretaryVoiceAnswer.ts` に `fold`・`squash` があり同じ名前で呼べる。今の `matchesAtStart` も `w !== ""` で空の語を飛ばす（同ファイル `matchesAtStart`）。`judgeYesNo` は no を先に見て、次に yes の頭の判定（同ファイル末尾）。手順どおりに足せる | ✓ |
| L2 import の文 | 上の (1) のとおり | ✓ |
| L3 §17-3 (1) の言い切りを「AI が答えたときは」に | §17-6 の「直す道で失敗」の行と一致。`SecretaryChat.tsx` の `sendEdit` の catch は失敗の文だけで作らない | ✓ |
| L4 反映後の測りに「あさって4時にして」3 回 | design §17-8 に足された。目標には入れない書き方で kgi の数を変えない | ✓ |
| L5 「はい、Meet も付けて」の試験 | card §4 に足された。設計の分かれ（２）が（３）より先なので、`yesFallback` 真でも `meet_refused` 真なら作らない。試験の期待（POST は呼ばれない・`meetUnavailable`）と合う | ✓ |

- 取り除きの手計算（第1回の表を再確認・変わらず）: 「はい」「はいはい」「yes please」「ok ok」→ 残り空 → yes。「はい、お願いします」→ 残り「します」→ yesMore。「yesterday」は文の頭の判定（`(?![a-z0-9'])`）で偽 → unknown のまま。取った後に残りがある限り yesMore なので、「取りすぎて空になって誤って yes」になる形は見つからない（語の一覧の語だけを頭から取るため）。

### (3) 新しい矛盾・穴

- design §17-8 の基準の表（「時刻だけの直しで日付が動かない」）は、新しい試験（4 時に変えて）と R1 の試験の両方で守られる。矛盾なし。
- design §17-3 (2)「AI の始まりの日付がカルテの日付と違うときだけ」は、時差の印が +09:00 でない端末では「同じ瞬間なら表なし・違う瞬間かつ日が読めないなら表あり」になり、今の動きと同じ。文と実装は食い違わない（設計の文は日本の端末を前提にした言い方だが、害はない）。
- card §2 の点検（１）の「`:336-343`」は、実装前の今の物に対する点検で正しい。実装後の行は動くが点検は実装前に流すので問題なし。
- 新しい試験が先に落ちる順（card §6 の（２））: 「4 時に変えて 説明 明日」は今の条件で `not same_time` が真 → `apply_day` が「明日」を見つけて日が動き落ちる。R1 の試験は設計どおり `same_day` だけにすると落ちる。どちらも「先に書いて落ちる」の作業に合う。
- openapi の差が `EventDraft.meet_refused` の 1 欄で済むかは第1回のまま**未確認**（この環境で fastapi が動かなかったため）。card §5 の止める条件が保険になっている。

### (4) 実装者が迷わず作れるか

- 迷わない。順番（試験を先 → 実装 → 確かめ → push）・触るファイル・止める条件（`BLOCKED:`・`NEEDS_DECISION:`）が揃っている。

## L（軽い指摘・直さなくても作れる）

- L1 `docs/handoff/secretary-voice-input/card-binW2.md` §4 の「4時に変えて 説明 明日」の試験: 期待の end 17:00 を出すには、カルテの始まり・終わりが両方「+09:00 の印つき」で終わりが 16:00（長さ 1 時間）である必要がある（`secretary_karte.py` の `merge_edit` が終わりを足すのは 3 つの時刻すべてに時差の印があるときだけ）。card は「2026-11-30 15:00」と書いているだけで印・終わりが無い。実装者は既存の試験の書き方（`start, end = "2026-11-10T10:00:00+09:00", "2026-11-10T11:00:00+09:00"`・`backend/tests/test_assistant_karte.py:485` あたり）に合わせれば作れる。card に「始まり・終わりとも +09:00 の印つき・終わりは 16:00」と 1 行足すと確実。
- L2 同じ試験の `_event(...)`（`backend/tests/test_assistant_karte.py:28` あたりの偽の AI の答えを作る関数）に渡す値は `start=`・`description=` の指定で足りる。card の文のとおりでよい（指摘ではなく確認）。

## 審査の結果の使い方

- Opus は L1 を card に 1 行足すだけで実装役へ渡せる（足さなくても作れる）。再審査は不要。
