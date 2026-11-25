# 設計の審査（architect）第1回 — 便W2「声で直す便の気をつける点 3 つ」

- 審査した物: 枝 `origin/release/secretary-voice-edit-followup`（先頭 4828208320227302afa770ebc47e48effb18faee）の `docs/handoff/secretary-voice-input/design.md` §17・`card-binW2.md`・`kgi.md` §7・`recon.md` §10・`docs/adr/ADR-1082-secretary-voice-input.md` の 2026-11-25 追記。実物は同じ枝の backend・frontend。
- 手元で動かせた物: なし（読むだけ）。`python -m tools.export_openapi` は fastapi が入っておらず動かなかった → openapi の差が 1 欄で済むかは**未確認**（設計の構造からの読みだけ・下の (5)）。

## 判定: REVISE

1. §17 の 3 つの直し（はいと直し・日付の表の条件・Meet の断り）は、行番号・変更前の形・既存試験との関係が実物と合う。作れる設計。
2. 1 点だけ、新しい条件が今の守りを弱める所がある（R1）。時差の印が +09:00 でない画面（外国の端末）で、「説明に明日と入れて」のように始まりが変わらない直しで日付が動く。1 行で直る。
3. 残りは軽い指摘（L1〜L5）。R1 を直せば APPROVE 相当。

## R（直さないと壊れる物）

### R1 日付の表を当てる条件は `same_day` 単独にせず、今の `same_time` の守りを残す

- 場所: `docs/handoff/secretary-voice-input/design.md` §17-4 の 3 の「後」の 2 つ目の箇条（`apply_day` の条件）と、`docs/handoff/secretary-voice-input/card-binW2.md` §3 の 2 つ目の箇条（`same_time` の import を外す指示）。実装先は `backend/app/routers/assistant.py:340-342`。
- 事実:
  - 今の条件は `ai_ev.start is not None and (karte.start is None or not same_time(ai_ev.start, karte.start))`（`backend/app/routers/assistant.py:340`）。
  - 設計の新しい条件は `not same_day(...)` だけ。`same_day` は `_day_of` を使い、時差の印が +09:00 でないと None を返す（`backend/app/services/secretary_dates.py:163-173` の `_day_of`。`if parsed.tzinfo is not None and parsed.utcoffset() != _JST_OFFSET: return None`）。card §4 も「時差の印が +09:00 でない→偽」を試験に入れている。
  - 画面が送るカルテの始まりは、ブラウザの時間帯の時差の印つき（`frontend/src/features/secretary/secretaryApi.ts:91-101` の `toKarteTime` が `getTimezoneOffset()` で印を作る）。日本以外の端末では +09:00 にならない。英語の画面（`frontend/src/locales/en.json`）もある。
- 壊れる場面: 日本以外の端末で、カルテの始まりが `2026-11-10T02:00:00+01:00`。「説明に明日までに資料と入れて」で AI が始まりを同じ瞬間（`2026-11-10T10:00:00+09:00`）で返す。今は `same_time` が真なので表を当てない。設計どおりだと `same_day` が両方 None で偽 → `apply_day` が「明日」を見つけて始まりの日が動く。`test_edit_same_start_does_not_move_date_by_description_words`（`backend/tests/test_assistant_karte.py:483-490`）が守っている動きが、+09:00 以外では守られなくなる。
- 直し方: 条件を「`ai_ev.start` が null でなく、かつ（カルテの始まりが null か、`not same_time(ai_ev.start, karte.start)` かつ `not same_day(ai_ev.start, karte.start)`）」にする（同じ時刻でも同じ日でもないときだけ表を当てる）。
  - これで §17-4 の 3 の「`same_time` の import は…消さない。口で使わなくなれば…外す」の食い違いも消える（口で使い続けるので import は残す。card §3 の 2 つ目の箇条は削る）。
  - card §4 の backend 試験に 1 本足す: カルテの始まりが `+01:00`・AI の始まりが同じ瞬間の `+09:00`・説明「明日」→ 日付が動かない。
  - 既存の `test_edit_changed_start_gets_day_table`（カルテ 11/10・AI 11/04）は `same_time` も `same_day` も偽 → 表が当たり通る。`test_edit_same_start_does_not_move_date_by_description_words` は `same_time` 真で通る。

## 点検の結果（見る点 1〜6）

### (1) §17-4・§17-5 の行番号と変更前の形（card §2 の点検を自分で流した）

| card §2 | 実物 | 合う |
|---|---|---|
| （１）`backend/app/routers/assistant.py:336-343` | `:336` が `if edit_mode:`・`:339` が `ai_ev = intent.event if intent.kind == "event" else None`・`:340` が `same_time` の条件・`:341` が `apply_day(ai_ev, body.text, now.date(), None)`・`:342` が `merge_edit(ai_ev, karte)`・`:343` が `final_kind = "event"` | 合う |
| `:334` が `edited = False` | `:334` | 合う |
| `:434` が `edited=edited if edit_mode else None,` | `:434`（`:430-435` が `EventDraft(...)`、`add_meet=ev.add_meet if meet_available else None` は `:430`） | 合う |
| （２）`backend/app/services/secretary_dates.py:163-173` に `_day_of`、`:201` に `apply_day` | `:163` `def _day_of`・`:201` `def apply_day` | 合う |
| （３）`frontend/src/features/secretary/secretaryVoiceAnswer.ts:60-66` の `judgeYesNo` が no → yes → unknown | `:60-66`。`:63` が no・`:64` が yes・`:65` が unknown | 合う |
| （４）`frontend/src/features/secretary/SecretaryChat.tsx:169` の `key` が `"confirmEvent" \| "editedConfirm"` | `:169` | 合う |
| `:192` が `const sendEdit = async (confirm: { id: number; tries: number }, trimmed: string) => {` | `:192` | 合う |
| `:276-286` が yes / no / それ以外 | `:276` yes・`:281` no・`:283-285` が `else { await sendEdit(confirm, trimmed); }` | 合う（終わりは `:285`・`:286` は `return;` の手前の `}`） |
| （５）`judgeYesNo` を呼ぶのは `SecretaryChat.tsx` だけ | `git grep -n judgeYesNo` は `secretaryVoiceAnswer.ts:60`・`secretaryVoiceAnswer.test.ts`・`SecretaryChat.tsx:25,271` だけ | 合う |

- 設計 §17-5 の「今の `:215-234`」は実物では `:215` から `:235` あたり（`else` の閉じまで）。±1 で実装者は迷わない。
- 既存の型: `frontend/src/features/secretary/secretaryApi.ts:55` が `edited?: boolean | null;`（`meet_refused` はこの次に足す形で合う）。`backend/app/schemas/assistant.py:159-172` の `EventDraft` は `edited` が最後の欄（`:172` あたり）で、`meet_refused` はその次に足せる。
- `backend/app/schemas/assistant.py:18-32` の `KarteIn` は設計 §16 の `edit` が入っていて、W2 では触らない（設計どおり）。

### (2) yesMore の取り除き方（今の語の一覧と `prepare`・`matchesAtStart` の動きで手計算）

- 前提（実物）: ja の語は `はい|うん|お願い|入れて|作って|オッケー|ok`（`frontend/src/locales/ja.json:6337`）、en は `yes|yeah|ok|okay|sure|please`（`frontend/src/locales/en.json:6337`）。いいえの語を先に見る（`secretaryVoiceAnswer.ts:63`）。文の頭の判定は `matchesAtStart`（日本語の語は句読点・空白を除いた形の頭、英字の語は `leading` に対する単語の境界つき）。
- 設計の手順（句読点・空白を除いた形の頭から、長い語から順に、取れなくなるまで取る。残りが空なら yes・あれば yesMore。取る前に文の頭の判定が通っているのが前提）で手計算した結果:

| 入力 | 句読点・空白を除いた形 | 取った後の残り | 判定 | 期待 |
|---|---|---|---|---|
| 「はい」 | はい | （空） | yes | yes ✓ |
| 「はい、入れて」 | はい入れて | はい→入れて→（空） | yes | yes ✓ |
| 「はいはい」 | はいはい | （空） | yes | yes ✓ |
| 「yes please」 | yesplease | yes→please→（空） | yes | yes ✓ |
| 「Yes, please.」 | （小文字にして）yesplease | （空） | yes | yes ✓ |
| 「ok ok」 | okok | （空） | yes | yes ✓ |
| 「はい、場所は渋谷にして」 | はい場所は渋谷にして | 場所は渋谷にして | yesMore | yesMore ✓ |
| 「はい、お願いします」 | はいお願いします | はい→お願い→します | yesMore | yesMore ✓ |
| 「yes, at four」 | yesatfour | atfour | yesMore | yesMore ✓ |
| 「オッケー、説明に資料と入れて」 | オッケー説明に資料と入れて | 説明に資料と入れて | yesMore | yesMore ✓（kgi X1） |
| 「yesterday I…」 | — | 取る前の文の頭の判定で偽（`(?![a-z0-9'])`） | unknown | 今のまま ✓ |

- card §3 の「英字の語も句読点・空白を除いた形で取り除いてよい」は、上の手計算で問題なし。英字の境界は取る前の文の頭の判定が守る。取った後の「okay」は長い語から取るので「ok」＋「ay」にならない（en の一覧は `okay` が `ok` より長い）。
- 今の `secretaryVoiceAnswer.test.ts:25-51` の既存試験（`HAI`→yes・`IIE`→no・`はい、いや違う`→no・`ETO`→unknown・`FULL_OK`→yes・`Yes, please.`→yes・`yes please don't`→no・空の語の一覧→unknown・`yes` と `["", "yes"]`→yes）は、すべて同じ結果（取り除いた残りが空 → yes）で通る。ただし `FULL_OK` の中身は未確認（試験の定数の定義を全部は読んでいない）。実装者は流して確かめる。

### (3) `same_day` で日付の表を当てる条件にしたとき

- `test_edit_changed_start_gets_day_table`（`backend/tests/test_assistant_karte.py:493-500`）: カルテ 11/10・AI 11/04 → 日が違う → `apply_day` が当たり 11/02 になる → 通る。
- `test_edit_same_start_does_not_move_date_by_description_words`（`:483-490`）: 同じ始まり → `same_day` 真 → 表を当てない → 通る。
- card §4 の新しい試験「4時に変えて 説明 明日」（カルテ 2026-11-30 15:00・AI 16:00）: 今の条件では `not same_time` が真で `apply_day` が「明日」（今日 2026-11-01 固定・`backend/tests/test_assistant_karte.py:74-77`）を見つけ日が動く → 先に書くと落ちる（card §6 の「試験を先に足して落ちることを確かめる」と合う）。新しい条件では日が同じ → 動かず 16:00・終わりはカルテの長さ 1 時間で 17:00 ✓（`merge_edit` の `secretary_karte.py:153-170`）。
- ほかに壊れる試験: `backend/tests/` に直す道（`edit` が真）を使う試験は `test_assistant_karte.py` だけ（`git grep` で `edit=True` はここだけ）。`merge_edit` の単体試験（`:369-430`）は `merge_edit` を変えないので影響なし。`EventDraft` の全欄を比べる試験は見つからない（`d["edited"]` など欄ごとの比べだけ）ので、`meet_refused` の追加で壊れる試験は無い。
- 壊れる道: R1（+09:00 以外）。もう 1 つ、設計 §17-6 の最後の行どおり「日付を言った頼みで AI が同じ日を返す」ときは、今まで（時刻も変えた頼み）は表が直せたが、これからは直せない（L3）。

### (4) `meet_refused` の流れ

- add_meet を捨てる位置: 設計の「`ai_ev` を作った次・`apply_day` の前」で、後の `merge_edit`（`secretary_karte.py:127` の `ev.add_meet is not None` で AI の値を取る箇所）と `edit_changed`（`:106-115` の `ev.add_meet != base.add_meet`）に add_meet が届かない。Meet だけの頼み → AI の欄が全部 null → `edited` 偽・`meet_refused` 真 ✓。場所＋Meet → `edited` 真（場所）・`meet_refused` 真 ✓。
- `meet_available` 真: 条件の外なので今のまま ✓。偽の AI が `add_meet: false`（要らない）を返したときも `None` に替わり、`meet_refused` は偽（`add_meet is True` のときだけ真）。今まで `karte.add_meet` が null で AI が false だと「変わった」になっていた不具合も一緒に消える（良い方向）。
- settle 後にカルテへ戻す場合（`assistant.py:361-368` あたりの `final_ev, edited = base_ev, False`）: `meet_refused` は別の変数なのでそのまま返る（設計のとおり）。画面は `edited` 偽・`meet_refused` 真で `meetUnavailable` を読む。日時を失った直しと Meet を断る文が両方真の稀な場合だけ「直せなかった」より「Meet の断り」が先に読まれるが、害は無い。
- 画面の 4 つの分かれ（設計 §17-5 の 3）: （１）`edited` 真かつ `ask` 無し（Meet 断りも真なら `editedMeetUnavailable`）→（２）`meet_refused` 真（`edited` 偽）→（３）`yesFallback` 真 →（４）今と同じ。順番の抜けは無い。edit 道では backend が `ask` を必ず null にする（`assistant.py:418` の `ask, ask_count = None, 0`）ので（１）の `!ask` は常に真。
- tries を増やさない: `sendEdit` は先頭で `pendingConfirmRef.current = null`（`SecretaryChat.tsx:200` あたり）にするので、（２）で `{ id: confirm.id, tries: confirm.tries }` に戻す指示は必要で正しい。card §4 の「Meet の後に直らない文 2 回 → 1 回目 `notEdited`・2 回目 `checkScreen`」で検査できる。
- `yesFallback` で作らない: （２）が（３）より先なので、「はい、Meet も付けて」は作られない ✓。（１）も（３）より先なので、直った下書きの聞き直しも作られない ✓。
- 抜け: 無し（L2 の言葉の修正のみ）。

### (5) openapi の差が 1 欄で済むか — 未確認（読みの結果）

- 動かせなかったため差は**未確認**。構造からの読み: `EventDraft` のプロパティは名前順で書き出されている（`frontend/api-contract/openapi.json:11375-11395` の `description` → `edited` → `end`）。`meet_refused` は `meet_available` と `start` の間に 1 ブロックだけ入る見込み。`KarteIn` は変えないので `edit` の欄は動かない。`frontend` 側に `edited` を手で書いた生成物は `secretaryApi.ts` だけ（`git grep -n '"edited"\|edited?:'` で openapi.json と `secretaryApi.ts` だけ）で、openapi から作る型ファイルは無い。
- card §5 の「差が `EventDraft.meet_refused` 以外に及べば止めて `NEEDS_DECISION:`」は、今の openapi が main の backend と食い違っていた場合の保険として正しい。実装者はそのまま守ればよい。

### (6) 実装者が迷わず作れるか

- R1 を直せば迷わない。迷いそうな所は L1・L2・L4。

## L（軽い指摘）

- L1 `docs/handoff/secretary-voice-input/design.md` §17-5 の 1「取り除く」: 取り除く語を `squash(fold(語))` の形にし、取り除く語が空になる語（例: 記号だけの語）は飛ばす、と 1 行足す。足さないと、語の一覧に記号だけの語が入った場合に「取り除けなくなるまで繰り返す」が止まらなくなる（今の `matchesAtStart` は `w !== ""` で守っている・`secretaryVoiceAnswer.ts:50` あたり）。取り除く前に文の頭の判定が通っていること（今の `matchesAtStart`）が前提、とも書くと英字の境界（`yesterday`）の守りが明確になる。
- L2 `docs/handoff/secretary-voice-input/design.md` §17-4 の 3 の `same_time` の注の文は「消さない」と「外す」が同居している。R1 を取り込めば「口で使い続けるので残す」の 1 文になる。`docs/handoff/secretary-voice-input/card-binW2.md` §3 も同じ直し。
- L3 設計 §17-3 (1) の「今より悪くなる形が無い（直せなかったときは今と同じく作る）」は、AI の呼び出しが失敗したとき（1 日の回数の上限・容器の停止・通信切れ）には当てはまらない。「はい、お願いします」と言ったのに失敗の文が出て作られない（前の下書きはボタンで作れる）。§17-6 の表の「直す道で失敗」の行に既に書いてあるので、§17-3 の言い切りを「AI が答えたときは」に直すとよい。
- L4 §17-6 の最後の行と、(3) で見た「日付を言った頼みで AI が同じ日を返すと今までは表が直せたが、これからは直せない」は同じ話。kgi X3 は「日付が動かない」だけを測るので、日付を替える頼み（「あさって 4 時」）で AI が日付を落とす数は測られない。反映後の probe_followup.py に「あさって4時にして」を 3 回足すと穴が見える（任意）。
- L5 card §4 の `SecretaryChat.test.tsx` に「`yesFallback` が真で `meet_refused` が真」（「はい、Meet も付けて」）の 1 本があると、（２）が（３）より先であることが試験で守られる（任意）。

## 審査の結果の使い方

- Opus は R1 を design.md §17-4 の 3・card-binW2.md §3・card-binW2.md §4 に取り込み、L1・L2・L3 を直してから実装役へ渡す。再審査は R1 の取り込みの確認だけでよい（第 2 回）。
