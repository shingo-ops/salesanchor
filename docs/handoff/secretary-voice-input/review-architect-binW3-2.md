# 審査（architect・第2回）— 便W3 指示書 card-binW3.md

- 審査した物: `origin/release/secretary-voice-w3-ask-pm` の commit 980c2b0cd（`git show 980c2b0cd`）が直した `docs/handoff/secretary-voice-input/design.md` §18-2・§18-4・§18-11 と `docs/handoff/secretary-voice-input/card-binW3.md` §3・§4。第1回は `origin/release/secretary-voice-w3-review1` の `review-architect-binW3-1.md`
- 審査者の手元: 読むだけ。製品のコード・DB・本番・secrets は触っていない。実物の backend/frontend はこの枝と origin/release/secretary-voice-w3-ask-pm で差が無い（`git diff --stat origin/main origin/release/secretary-voice-w3-ask-pm -- backend frontend` が空）

## 判定: APPROVE

1. R1（終わりの時差の印が +09:00 のときだけ比べる）は design §18-4 の 1・card §3・card §4 の試験 1 件の 3 か所に入った。第1回の `TypeError`（500）の道はふさがる。
2. 反映した L1・L3・L5 の文と試験の答えは、実物の順（`backend/app/routers/assistant.py:344-376`・`backend/app/services/secretary_karte.py` の `settle_dates`・`merge_edit`）をたどって矛盾しない。特に card §4 の「カルテ終わり null・はい、終わりを朝5時にして」は本当に `elif` の分かれに入り、`edited` 偽・`edit_dropped` 真になる。
3. 新しく壊れる物は見当たらない。R は無し。軽い指摘は L1〜L3 のみ（直さなくても作れる）。

## 1. 見る点ごとの結果

### (1) R1 が設計・指示書・試験に入ったか — 入った

| 場所 | 入った文 |
|---|---|
| `design.md` §18-4 の 1（始まりを足したあとの箇条） | 「終わりが読めて、終わりの時差の印も +09:00 で、新しい始まりより前なら…印が無い・違う終わりは比べない（…`TypeError`…口の `try` は `HTTPException` しか受けないので 500…審査 R1）」 |
| `card-binW3.md` §3 の 1 つ目の箇条 | 「終わり < 新しい始まりの比べも、終わりの印が +09:00 のときだけ行う」 |
| `card-binW3.md` §4 の `test_secretary_dates.py` | 「明日4時から」・start `…T04:00:00+09:00`・end `…T05:00:00`（印なし）→ 例外が出ず start 16:00・end は元のまま |

- 実物で 500 にならないことの裏: 同じ形が `settle_dates` に来ても `backend/app/services/secretary_karte.py:68` の `except TypeError` で終わりが null になる。印なしの終わりは `afternoon_hours` で触られず、`settle_dates` が落とす（502 や 500 にならない）。

### (2) L1・L3・L5 の文と試験の答えが実物と矛盾しないか — しない

**card §4「カルテ 11/30 15:00・終わり null・『はい、終わりを朝5時にして』・AI の end 05:00 だけ」を実物の順で追った結果**

| 順 | 実物 | この例での値 |
|---|---|---|
| 1 | `assistant.py:327`（の直後に `afternoon_hours`・新設） | 文に「朝」があり止める語に当たるので何も変えない |
| 2 | `assistant.py:344-347` の条件 | `ai_ev.start` が null なので `apply_day` は呼ばれない |
| 3 | `assistant.py:349` `merge_edit(ai_ev, karte)`（`secretary_karte.py` の `merge_edit`） | `ai_end` は読めて、`same_time(05:00, None)` は偽（`a is b` が偽）→ `values["end"]` = 05:00。`values["start"]` はカルテの 15:00。`edit_changed` 真 → `edited` 真 |
| 4 | `assistant.py:364` `settle_dates` | 終わり 05:00 < 始まり 15:00 なので `end_text = None`（`secretary_karte.py` の `settle_dates`） → 結果は 始まり 15:00・終わり null |
| 5 | `assistant.py:370-374` の条件 | `base_ev.start` あり・`final_ev.start` あり（偽）。`base_ev.end` は null（偽）→ **この分かれには入らない** |
| 6 | `assistant.py:375-376` `elif edited and not edit_changed(final_ev, base_ev)` | `edited` 真・`final_ev` と `base_ev` は始まり・終わりとも同じ → `edit_changed` 偽 → **この分かれに入る** |

- 6 で入るので、設計どおり `edited = False` の前に `edit_dropped = True` を置けば、答えは `edited` 偽・`edit_dropped` 真。card §4 の答えと一致する（`elif` の分かれに入ることを、card の括弧書きも正しく言っている）。
- 隣の試験「カルテ 15:00〜16:00・『終わりを朝5時にして』」は 5 で `base_ev.end` あり・`final_ev.end` null の条件に入り（`assistant.py:370-372`）、戻す前の `edited` 真 → `edit_dropped` 真。こちらも一致。
- 「はい、終わりは5時にして」・end 05:00 → `afternoon_hours` で終わりが 17:00 → 15:00〜17:00 で `settle_dates` を通る → `edited` 真・`edit_dropped` 偽。一致。
- この 2 つの分かれは「戻す前の `edited`」が違うだけで、どちらも `edit_dropped = edited` 相当（1 つ目は戻す前に真、2 つ目は条件に `edited` を含む）。設計の「戻す前の `edited` が真なら」と矛盾しない。

**L1（英字の am/pm の前後）**: card §3 と design §18-4 の 1 の文は `(?<![A-Za-z])(?:am|pm)(?![A-Za-z])`。「4pm」は前が数字なので当たり、「PM会議」は後ろが日本語なので当たり、「team」「program」は当たらない。card §4 の試験 2 件（「4時にteamで」→ 16:00・「4pmに」→ 変わらない）の答えと合う。

**L3**: 上の追跡のとおり。

**L5**: design §18-4 の 1 と card §3 にある（印があれば `astimezone`・無ければそのまま）。`KarteIn.start` は文字で、`parse_iso` は印の有無を問わず読める（`secretary_karte.py` の `_read_time`・`merge_edit` が印の有無を別に点検している形と同じ）。実装の迷いは無い。

### (3) 新しく壊れる物 — 無い

- `backend/` と `frontend/` は origin/main と差が無いので、今の試験・口の形は変わっていない。今回の commit は docs 2 ファイルだけ（`git show 980c2b0cd --stat`）。
- 追加の試験 3 件（印なしの終わり・team・4pm）は、card §3 の止める語・比べの文だけで答えが決まる。他の箇条（「素の時刻」の集まり・カルテの朝の点検）と食い違わない。
- 画面側（`edit_dropped` 真なら「はい」で作らない）の文は第1回の確認から変わっていない。

## 2. R（直さないと壊れる）

無し。

## 3. L（軽い指摘・直さなくても作れる）

- L1. design §18-4 の 1 と card §3 の `a.m.`・`p.m.` は「部分一致」と書いてあるが、正規表現の点（`.`）は文字として書く（`a\.m\.`）と実装役に伝えると、「a1m」などに当たらない。文書の言い方だけの話で、当たっても止まる側（今までと同じ答え）なので壊れない。
- L2. card §4 の「カルテ 11/30 15:00・終わり null…end 05:00 だけ」の AI の end は、始まりより前になる日付（`2026-11-30T05:00:00+09:00`）で作る、と 1 語足すと、偽の AI の値の取り違えが無い（今の書き方でも「カルテ 11/30」から読める）。
- L3. L4（`probe_after.py` に Meet の分かれが無く yes_07 の `edited` だけ口と違う）は design §18-11 で「測りの報告に書く」と決めてある。報告の書式に欄を 1 行用意しておくと忘れない。

## 4. 実装役へ渡す順

1. このまま `card-binW3.md` を渡してよい。
2. L1〜L3 は渡す文に口頭で足すか、報告で足りる。
