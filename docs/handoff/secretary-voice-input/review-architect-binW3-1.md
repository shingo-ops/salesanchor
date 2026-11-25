# 審査（architect・第1回）— 便W3 指示書 card-binW3.md

- 審査した物: `origin/release/secretary-voice-w3-ask-pm` の `docs/handoff/secretary-voice-input/design.md` §18・`card-binW3.md`・`kgi.md` §8・`recon.md` §11・`binW3/`。実物は同じ枝の backend・frontend（この枝の backend/frontend は origin/main と差が無い。`git diff --stat origin/main origin/release/secretary-voice-w3-ask-pm -- backend frontend` が空）
- 審査者の手元: 読むだけ。製品のコード・DB・本番・secrets は触っていない。§18-4 の 1 の文を写した試作を scratchpad で流した（製品には置いていない。pydantic が手元に無いため標準ライブラリだけの写し）

## 判定: REVISE

1. 設計 §18-4 の 1 の文のとおりに `afternoon_hours` を書くと、始まりが +09:00・終わりが時差の印なしの答えで、終わりと新しい始まりを比べる所が `TypeError`（500）になる。口の `try` は `HTTPException` しか受けないので画面に 500 が出る（試作で再現。R1）。
2. 行番号・変更前の形・試験の表・画面の分かれ・openapi の差・`probe_after.py` の順は実物と合う。直す必要があるのは R1 の 1 点だけ。
3. 軽い指摘は L1〜L5（直さなくても作れる・壊れない）。R1 は指示書の §3 に 1 行足せば済む。

## 1. 見る点ごとの結果

### (1) card §2 の行番号と変更前の形 — 合う（全部）

| card の言い方 | 実物 | 結果 |
|---|---|---|
| `assistant.py:327` が `intent = envelope.intent` | `backend/app/routers/assistant.py:327` | 合う |
| `:334-335` が `edited = False`・`meet_refused = False` | `backend/app/routers/assistant.py:334-335` | 合う |
| `:370-376` が「直した結果が日時を失ったら」の分かれ（`final_ev, edited = base_ev, False`） | `backend/app/routers/assistant.py:370-376`（374 が `final_ev, edited = base_ev, False`・375 が `elif edited and not edit_changed`・376 が `edited = False`） | 合う |
| `:442` が `meet_refused=meet_refused if edit_mode else None,` | `backend/app/routers/assistant.py:442` | 合う |
| `:57` が `from app.services.secretary_dates import apply_day, same_day` | `backend/app/routers/assistant.py:57` | 合う |
| `secretary_dates.py:14`・`:17`・`:207` | `backend/app/services/secretary_dates.py:14`（import）・`:17`（`_JST_OFFSET`）・`:207`（`def apply_day(`） | 合う |
| `schemas/assistant.py:178` が `meet_refused` | `backend/app/schemas/assistant.py:178` | 合う |
| `secretaryApi.ts:57` | `frontend/src/features/secretary/secretaryApi.ts:57` | 合う |
| `SecretaryChat.tsx:233` が `} else if (yesFallback) {` | `frontend/src/features/secretary/SecretaryChat.tsx:233` | 合う |
| 試験 `:541` の「4時に変えて 説明 明日」 | `backend/tests/test_assistant_karte.py:541` | 合う |

- 触るファイルの組は、便W2 が `meet_refused` を足したときの組と同じ（`grep -rln meet_refused` が schemas・router・secretaryApi.ts・SecretaryChat.tsx・同 test・openapi.json・test_assistant_karte.py）。足し漏れは無い。

### (2) `afternoon_hours` の決まりと card §4 の表 — R1 の 1 点を除き全部その通り

設計 §18-4 の 1 の文を写した試作（`/tmp/claude-0/-home-user-salesanchor/65f36be1-8a1e-52b0-9bcc-828c8fd4971a/scratchpad/proto_afternoon.py`）の出力。

| 文 | AI の値 | 試作の答え | card の期待 |
|---|---|---|---|
| 明日4時に打ち合わせ | 04:00/05:00 | 16:00/17:00 | 同じ |
| 明日1時から2時 | 01:00/02:00 | 13:00/14:00 | 同じ |
| あさって4時半 | 04:30 | 16:30 | 同じ（終わり 05:30 でも 17:30） |
| 4時から1時間 | 04:00・end null | 16:00・null | 同じ |
| 4時から1時間 | 04:00/05:00 | 16:00/17:00 | 同じ（終わり < 新しい始まりで足す） |
| 午前4時・朝6時・夜1時・深夜2時・4am・午後4時 | 04:00 等 | 変わらない | 同じ |
| 10時・12時・7時 | 10:00・12:00・07:00 | 変わらない | 同じ |
| 1時間にして | end 04:00 | 変わらない | 同じ |
| 終日・時差の印なし `2026-11-26T04:00:00`・既に 16:00 | — | 変わらない | 同じ |
| カルテ始まり 05:00・終わりは6時 | end 06:00 | 変わらない | 同じ |
| カルテ始まり 15:00・終わりは5時 | end 05:00 | 17:00 | 同じ |
| 明日４時（全角） | 04:00 | 16:00 | 同じ |

穴の探し（card に無い言い方）:

| 文 | AI の値 | 試作の答え | 見立て |
|---|---|---|---|
| 9時から5時 | 09:00/05:00 | 09:00/17:00 | よい（終わりだけ直る） |
| 10時から4時間 | 10:00/14:00 | 変わらない | よい（「4時間」は当たらない） |
| 明日2時から4時間 | 02:00/06:00 | 14:00/18:00 | よい（終わり < 始まりで足す） |
| 明日4時から | start +09:00・end 時差の印なし | **`TypeError`** | **R1** |
| 明日4時にPM打ち合わせ・team meeting | 04:00 | 変わらない | L1（`pm`・`am` が英単語の中でも止まる。今までと同じ答えで悪くはならない） |
| 明日4:30に | 04:30 | 変わらない | L2（「時」の字が無い書き方は当てない。声の文字起こしは「4時半」が主なので影響は小さい） |
| 明日4時に・値が `…T04:00:00Z` | — | 変わらない | よい（+09:00 以外は触らない） |

- 「10時」「12時」「11時」「16時」は `(?<![0-9])` で前の数字に止められ、当たらない。「1時間」「4時間」は `(?!間)` で当たらない（試作で確認）。
- 10時・12時・7時・「1時間」で穴は無い。

### (3) `intent.model_copy` を置く位置 — 矛盾しない・今の試験は壊れない

- 置く位置は `backend/app/routers/assistant.py:327` の直後。その後に `final_ev = intent.event`（:332）・直す道の `ai_ev = intent.event`（:340）・`merge_karte(intent.event, karte)`（:357）・古い画面の `ev = intent.event`（:378）がすべて直した `intent` から読むので、新しい画面・直す道・古い画面の 3 つの道ですべて「直した後の値」が通る。
- `same_time`・`same_day`（`:344-348` の条件）は、直した値で比べる。「4時に変えて」で AI が 04:00・カルテが 16:00 のとき、前は別の時刻として扱われ、後は同じ時刻（`edited` 偽）になる。これは正しい向き（言われた時刻がカルテと同じなので直すところが無い）。
- `apply_day` の `_with_day`（`backend/app/services/secretary_dates.py:187`）は日付の文字だけ替えて `value[10:]`（時刻・時差の印）を残す。`afternoon_hours` の出力も `isoformat(timespec="seconds")` で同じ形（`T16:00:00+09:00`）なので食い違わない。
- `merge_edit`（`backend/app/services/secretary_karte.py:127`）の「終わりが無ければ始まり＋カルテの長さ」は、直した始まりを使う。長さを保つ動きは変わらない。
- `Intent`（`backend/app/schemas/assistant.py:86`）の `model_validator` は kind と欄の組を見るだけで、`model_copy` では走らない。event の型は変えないので問題無い（card §3 の心配は当たらない）。
- 今の試験: `backend/tests/test_assistant_karte.py:541`（「4時に変えて 説明 明日」・AI は 16:00）は、時が 16 で集まり {4} に入らず変わらない → そのまま通る。1〜6時が文に出る今の試験はこの 1 件だけ（`grep -nP "(?<![0-9])[1-6]\s*時(?!間)"` で `tests/test_assistant_*.py`・`tests/test_secretary*.py`・`app/assistant_regression` を見た）。`T0[1-6]:` の値を AI が返す今の試験は `test_assistant_karte.py:406` と `:527` で、前者は `merge_edit` を直接呼ぶ・後者は文に時刻の語が無い（「説明に明日と入れて」）ので当たらない。決まり帳 23 件も 1〜6時の語が 0 件（recon §11-4）。

### (4) `edit_dropped` の立て方と画面の分かれ — 立て方は合う。1 つ漏れ（L3）

- 「戻す前の `edited` が真のときだけ」（`:374` の手前で `edit_dropped = edited`）で、card §4 の 4 件の答えになる。
  - 「はい、終わりは5時にして」・AI end 05:00・カルテ 15:00〜16:00 → 規則で 17:00 → `edited` 真・`edit_dropped` 偽。
  - 「終わりを朝5時にして」→ 「朝」で当たらず 05:00 → `settle_dates`（`backend/app/services/secretary_karte.py:52`）が終わりを空に → `:370-374` の分かれに入る → 戻す前の `edited` は真 → `edit_dropped` 真。
  - AI が unknown → `merge_edit(None, karte)` で `edited` 偽 → `edit_dropped` 偽。
  - `edit` が偽 → `edit_dropped if edit_mode else None` で null。
- 画面: `SecretaryChat.tsx:233` の条件を `yesFallback && !(reply.kind === "event" && reply.draft.edit_dropped === true)` にすると、
  - 「はい、お願いします」（AI は直しなし）→ `edited` 偽・`edit_dropped` 偽 → 今のまま `yesFallback` で作る。
  - 直せなかった（`edit_dropped` 真）→ 下の else（`:243` 付近の `notEdited`・`confirm.tries === 0` なら確かめ待ちを `tries: 1` で続け、2 回目は `checkScreen`）。`pendingConfirmRef` は `:200` で一度 null にしてあり else の中で戻すので、「続けて『はい』で POST 1 回」の試験（card §4）が成り立つ。
  - `meet_refused` 真の枝（`:225`）は `yesFallback` の枝より前にあるので、両方真でも作られない（今のまま）。
- 漏れ（L3）: 直した結果が日時を失う分かれは 2 つある。`:370-374`（カルテに始まり・終わりがあるのに結果が空）と、`:375-376` の `elif edited and not edit_changed(final_ev, base_ev)`。後者に入るのは、`merge_edit` が「変わった」と読んだ値を `settle_dates` が落として結果がカルテと同じになったとき（例: カルテの終わりが空・「はい、終わりを朝5時にして」→ 終わり 05:00 が始まりより前で落ちる）。設計は前者だけで `edit_dropped` を立てるので、後者では `edited` 偽・`edit_dropped` 偽 → 画面は「はい」で前の下書きを作る（recon §11-3（２）と同じ形の黙った作成）。カルテの終わりが空になるのは「終わりを聞く回数を使い切った」ときだけで、まれ。

### (5) openapi の差 — 1 欄で済む

- 便W2 の `meet_refused` は `frontend/api-contract/openapi.json:11430-11440` の 1 欄（`anyOf` で boolean と null・`title`）。`edit_dropped` も同じ形（既定値ありで `required` に入らない）で、欄は名前順に並ぶので `edited` の近くに 1 欄入るだけ。差が `EventDraft.edit_dropped` 以外に及ぶ理由は見当たらない（`backend/tools/export_openapi.py` は存在する）。ただし、実際の書き出しは実装役が流して差を貼ること（card §5 のとおり）。審査者は流していない（実装がまだ無い）。

### (6) `binW3/probe_after.py` が本番の口と同じ順か — 同じ（L4 の 1 点を除く）

- 新しい頼み（karte 無し）: 直した値 → `apply_day(…, None)` → `settle_dates`（`probe_after.py:44-47`）。口は `final_ev = intent.event`（:332）→ `apply_day`（:362）→ `settle_dates`（:364）で同じ順。
- 直す頼み: `afternoon_hours` → `same_time/same_day` の条件 → `apply_day` → `merge_edit` → `settle_dates` → 日時を失えば `base`・`dropped = edited`・`edited = False` → 変化なしなら偽（`probe_after.py:44, 50-60`）。口の `:340-376` と同じ順。
- 差（L4）: 口にある「Meet を付けられない人なら `add_meet` を落として `meet_refused`」（`assistant.py:341-342`）が probe には無い。「はい、Meetも付けて」（yes_07）だけ、probe では `edited` 真・口では `edited` 偽・`meet_refused` 真になる。Y4 の数え方（直す頼みの読み落とし 0 回）では「AI が add_meet を返したか」を見れば足りるので、数字は変わらない。

## 2. R（直さないと壊れる）

### R1. `afternoon_hours` の「終わり < 新しい始まり」の比べで時差の印の混在を守る（`TypeError` → 500）

- 直す文書: `docs/handoff/secretary-voice-input/design.md` §18-4 の 1 の最後の箇条（「始まりを足したあと、終わりが読めて新しい始まりより前なら、終わりにも 12 時間足す」）と `docs/handoff/secretary-voice-input/card-binW3.md` §3 と §4（試験 1 件）。
- 直し方: 「終わりが読めて」を「終わりが読めて、時差の印が +09:00（`_JST_OFFSET` と等しい）で」に替える。印の無い・違う終わりは比べず触らない。card §3 の 1 行目「時差の印が +09:00 でない・無い値は触らない」の後ろに「終わり < 始まりの比べも、終わりの印が +09:00 のときだけ行う（印が混ざると `datetime` の比べが `TypeError` になる）」と足す。card §4 の `test_secretary_dates.py` に 1 件足す: 「明日4時から」・start `2026-11-26T04:00:00+09:00`・end `2026-11-26T05:00:00`（印なし）→ 例外が出ず、start 16:00・end は元のまま。
- 理由（事実）: `backend/app/routers/assistant.py:327` の後の `afternoon_hours` 呼び出しは、`:319` からの `try`（`except HTTPException` は `:390` だけ）の中にある。`TypeError` は捕まらず FastAPI の 500 になる。試作で、start が +09:00・end が印なしの答えで `TypeError: can't compare offset-naive and offset-aware datetimes` を再現した。`IntentEvent` は時刻を文字のまま受ける（`backend/app/schemas/assistant.py:77-78`）ので AI の答えで起こりうる。同じ形は `settle_dates` が `except TypeError`（`backend/app/services/secretary_karte.py:68`）、`merge_edit` が印の有無を点検（`:165-167`）、`backend/tests/test_secretary_dates.py:329` が印なしの始まりを試験に入れているとおり、この製品では既知の形。

## 3. L（軽い指摘・直さなくても作れる）

- L1. 止める語の `AM|PM|am|pm|a.m.|p.m.`（`design.md` §18-4 の 1）を文の中の部分一致で見ると、「PM会議」「team」「program」の英字の中でも止まる（試作で確認。PM は「PM-00001」の商品マスタの語でもある）。止まったときは今までと同じ答え（悪くはならない）。直すなら、英字は前後が英字でないときだけ（`(?<![A-Za-z])(?:am|pm)(?![A-Za-z])`・「4pm」は前が数字なので当たる）。
- L2. 「4:30」のように「時」の字が無い書き方は当たらない。声の文字起こしの主な形（「4時半」）は当たるので影響は小さい。対象外として `design.md` §18-2 に 1 行書くと、後で迷わない。
- L3. `edit_dropped` を、`assistant.py:375-376` の `elif edited and not edit_changed(final_ev, base_ev)` の中でも `edit_dropped = True` にする（`edited = False` の前に）。そこに入るのは `settle_dates` が AI の値を落としたときだけ（`edit_changed` を満たさなくなる原因は他に無い）。card §4 の backend 試験に 1 件: カルテ終わり null・「はい、終わりを朝5時にして」・end 05:00 → `edited` 偽・`edit_dropped` 真。
- L4. `probe_after.py` に Meet の分かれが無い（上の (6)）。Y4 の数字は変わらないが、`final` に出る `edited` が口と違う行が 1 種（yes_07）ある。報告に一言書くとよい。
- L5. カルテの始まりの朝の点検（0〜6時）は「日本時間で」とある。時差の印が +09:00 以外のカルテは `astimezone` で日本時間に直してから時を見る、印の無いカルテは時をそのまま見る、と card §3 に書くと実装役が迷わない（`KarteIn.start` は読めるが印の有無は問わない。`backend/app/schemas/assistant.py:36-41`）。

## 4. 実装役へ渡す前に直す順

1. `design.md` §18-4 の 1 と `card-binW3.md` §3・§4 に R1 を反映する。
2. 余力があれば L3（1 行と試験 1 件）を反映する。L1・L2・L4・L5 は報告で足りる。
3. 直したら第 2 回の審査で、R1 の文が直っているかだけ確かめる。
