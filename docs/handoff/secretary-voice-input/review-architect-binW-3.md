# 設計審査（architect）— 便W「声で予定の下書きを直す」第 3 回

- 審査対象: `origin/release/secretary-voice-draft-edit` の `docs/handoff/secretary-voice-input/design.md` §16・`card-binW.md`と、同じ枝の実物
- 第 2 回: `origin/release/secretary-voice-draft-edit-review2` の `docs/handoff/secretary-voice-input/review-architect-binW-2.md`
- 審査日: 2026-11-24（スケジュール実行）／ 読むだけ。製品のコード・DB・本番・secrets には触れていない
- 表記: 「B:」は `origin/release/secretary-voice-draft-edit` の中のパス。実物のコードは設計の commit だけが載っていて、まだ未変更（今の形）。行番号は B: の `git show` で読んだもの

## 判定: APPROVE（R は 0 件・L は 5 件）

1. 第 2 回の R1（直す道の `apply_day` は AI の始まりがカルテと時刻として違うときだけ・試験 2 件）は、B:docs/handoff/secretary-voice-input/design.md:469 と B:docs/handoff/secretary-voice-input/card-binW.md §4「口（審査第 2 回 R1）」に直った。実物 `apply_day`・`_guard_ok` と突き合わせて、2 件の試験の文が期待どおりに動くことを確かめた。
2. 取り込んだ L1〜L6（`onSaving`・戻した値を `settle_dates` に通さない・assert・回数の数え直しの試験・自前の try/finally・props の型）は、設計書と実物の行が食い違わない。直しで出た新しい矛盾・穴は、実装を止めるものは無い。
3. 残るのは軽い指摘 L1〜L5 だけ（失敗時に外す口の名前・`edited` の数え直し・声が切れた後の確かめ待ちの戻し・文に日付語が混ざる場合・使わない型の 1 文）。直さなくても作れる。

---

## 1. 第 2 回の R1 の突き合わせ（実物の行）

直し方の文（B:design.md:469）:「`ai_ev.start` が null でなく、かつカルテの始まりと時刻として違うときだけ `apply_day(ai_ev, body.text, now.date(), None)`」。

- 実物の門: `karte is not None and karte.start is not None and karte.asked != "start"` は B:backend/app/services/secretary_dates.py:217-218。直す道は `karte` に None を渡すので、この門は通らない。だから「AI が同じ値で返したときは呼ばない」を呼ぶ側（B:backend/app/routers/assistant.py の `edit_mode` の枝）で作るのは正しい。`apply_day` 自体は変えなくてよい。
- 試験 1（「説明に明日までに資料を持参と入れて」・AI はカルテと同じ start）:
  - `_resolve`（B:secretary_dates.py:117-154）は、`_OTHER_DATE_WORDS`・`_DATE_MODIFIERS`・`_CLAUSE_LINK` のどれにも当たらず（文に「次・前・後・末・ので・ため」などが無い）、「明日」が `_RELATIVE_RE` で 1 つ見つかる（:145-148）。直前の字は「に」で `_BEFORE_OK`（:59）にあり、後ろは「まで」で `_AFTER_OK`（:63-66）に合う。つまり文は「明日」と読まれる＝**この試験は修正前なら本当に落ちる**（日付が動く）。
  - 修正後は始まりが同じなので `apply_day` を呼ばず、`merge_edit` が description だけ AI を採る。設計・カードの期待（start・end はカルテのまま・description だけ変わる・`edited` 真）と合う。
- 試験 2（AI が start を 3 日後で返し文「来週の月曜にして」）:
  - `_WEEKDAY`（B:secretary_dates.py:48）が「来週の月曜」に当たる。`_DATE_MODIFIERS`（:30-34）に「来週」は無い（`_OTHER_DATE_WORDS` にあるのは「翌週・先週」で「来週」ではない）。後ろは「にして」で `[にで](?![はもを])`（:64）に合う。`_LEFTOVER` にも当たらない。守りは `week_word` があるので None（:140）。`_guard_ok` は `guard is None` で真（:191-192）。日付は来週の月曜になる。
  - `_with_day`（:176-181）は AI の始まりが時差の印なし、または +09:00 のときだけ替える（:171）。偽の AI の答えに +09:00 か印なしで書けば試験は通る。実際の AI は +09:00 で返す（B:secretary-agent/prompt.txt:7）。
- 結論: R1 は直った。残る穴は、設計が自分で認める「AI が言われていない始まりを違う値で返す」場合だけ（その値が勝つのは設計の約束どおり）。

## 2. 取り込んだ L の突き合わせ

| 第 2 回の L | 設計・カードの書き | 実物との突き合わせ | 判定 |
|---|---|---|---|
| L1 作る押下の途中の窓（`onSaving`・失敗時に外す） | B:design.md:490。`onSaving?: () => void` を `setSaving(true)` の直後に呼ぶ。失敗したら外す。カード §1 の表と §4 の試験（作成も保留のまま直す答えを返す） | B:frontend/src/features/secretary/SecretaryDraftEvent.tsx:66（`setSaving(true)`）・:80（`onCreated()`）・:81-85（失敗の枝）。下の L1 の補足あり | 直った（口の名前だけ L1） |
| L2 戻した値は `settle_dates` を再度通さない | B:design.md:471「`merge_edit(None, karte)` の値そのまま」 | B:backend/app/services/secretary_karte.py:50-68 は終わり<始まりで終わりを null にする。通さないと決まっているので迷わない | 直った |
| L3 `assert karte is not None` | B:design.md:469 の枝の先頭に書いた | 既存の `assert intent.event is not None` は B:backend/app/routers/assistant.py:339。同じ書き | 直った |
| L4 回数の数え直しの試験 | B:card-binW.md §4 frontend「足す: 直せた後の新しい下書きで…回数は 0 から数え直し」 | `startConfirm` が `tries: 0` で始める（B:SecretaryChat.tsx:243 の形）。合う | 直った |
| L5 自前の `setSending` と try/finally | B:design.md:491 | 今の `finally`（B:SecretaryChat.tsx:268-270）は確かめ待ちの道の `return`（:193）の後ろなので、自前が要る。合う。`send` の先頭の `sending` 門（:160）と `useEffect` の自動送信の門（:277）が効く | 直った |
| L6 `calendarType` の型 | B:design.md:486 に「`EventDraftData.calendar_type` は `"personal"` だけ…別に持つ」 | B:frontend/src/features/secretary/secretaryApi.ts:47（`calendar_type: "personal"`）・B:SecretaryDraftEvent.tsx:51（`useState<"personal" | "shared">(draft.calendar_type)`）。矛盾なし | 直った |

## 3. 実物と食い違う箇所の探索（見る点 (2)(3)）

- `edit_mode` の置き場: `if new_path:`（B:assistant.py:333）の前、`final_kind`（:330）・`final_ev`（:331）の隣に置く。`try` の中で作るので、後ろの `:376`・`:391` は同じ `try` を抜けた後に読む。`try` は `HTTPException` 以外の例外を握らない（:363）ので、変数が未作成のまま読まれる道は無い。
- `:376` を `final_kind` に直すのは安全: 直す道以外では `final_kind` は `intent.kind` で始まり、`unknown`＋カルテの枝（:334-337）で event に替わるだけ。請求書の枝は今と同じ。
- `:391` の `elif final_kind == "event" and new_path:` の中で `edit_mode` を使い、`next_ask` を呼ばず `ask=None`・`ask_count=0`・`edited=…` にする、という書きは、`EventDraft` の欄（B:schemas/assistant.py の `EventDraft`）に `edited` を足す設計と合う。openapi.json の差は `KarteIn.edit`・`EventDraft.edited` の 2 欄だけという確かめもカード §5 にある。
- `KarteIn` は `extra="forbid"`（B:backend/app/schemas/assistant.py:21）。`edit` を足さないと画面の `edit: true` は 422 になる。設計・カードとも足すと書いてあり、配備途中の組み合わせは B:design.md §16-8 に書いてある。
- 画面の送る文: `sendSecretaryMessage(text, karte)`（B:secretaryApi.ts:91-93）の `karte` は `EventKarte` 型。`edit?: boolean` を足す（設計 §16-6(1)）ので型は通る。`karteFromDraft`（:70-83）は `edit` を作らないので、聞く道には影響しない。
- 確かめ待ちの道は `pendingConfirmRef` を `null` にした後に API を呼ぶ。待つ間に「作る」ボタン→ `markCreated` が `pendingConfirmRef.current = null`（B:SecretaryChat.tsx:285）にするだけで安全。答えが届いたとき ref の集合で止める設計（B:design.md:492）で足りる。

## 4. R（直さないと作れない・壊れる）

なし。

## 5. L（軽い指摘・直さなくても作れる）

- **L1. 作成の失敗で id を集合から外す「口」の名前を 1 語書く**: B:design.md:490 は「作成が失敗したら `onSaving` で入れた id を集合から外す」と書くが、どの口で外すかは書いていない。実物は失敗のとき既に `onVoiceFailed?.()` を呼ぶ（B:SecretaryDraftEvent.tsx:84。ボタン・声のどちらで押しても呼ぶ）。親の呼び先は B:SecretaryChat.tsx:344-347。ここに `createdOrCancelledRef.current.delete(m.id)` を足す、と 1 文書くと迷わない（新しい props は要らない）。あわせてカード §4 に 1 件: 「作る」を押す→作成の API が 500 → 直す答えが届く → 新しい下書きが出る（外れている）、を足すと、外し忘れ（作れない下書きが残る）を CI が拾う。
- **L2. `edited` を `settle_dates` の後に数え直す**: B:design.md:471 は「土台の始まり・終わりが埋まっていたのに null になったら」だけカルテに戻す。土台の終わりが null（欄が空）で、AI が始まりより前の終わりだけ返すと、`merge_edit` は「変わった＝真」を出す（B:design.md:462 の規則）が、`settle_dates` が終わりを null に戻す（B:secretary_karte.py:63-67）ので、返す下書きはカルテと同じ。`edited` は真のまま、声は「直しました」と読む前に `!d.end` で `checkScreen` に落ちる（B:SecretaryChat.tsx:227 と同じ形）ので壊れはしない。`settle_dates` の後に「最終の値が土台と同じなら `edited` を偽」と 1 文足すと、より正確になる。
- **L3. 確かめ待ちを戻す書きは声が続いているときだけ**: B:design.md:494 の「回数が 0 なら確かめ待ちを回数 1 で前の下書きに戻す」は、同 §16-6(3) の最後の行（`voiceOnRef.current && sentIn === session.current` のときだけ）の中に入る、と 1 語足すと迷わない。待つ間に声をやめた（`onVoiceChange(false)` が `pendingConfirmRef.current = null`・B:SecretaryChat.tsx:135）あとで戻すと、後で声をまた入れたときに古い確かめ待ちが生き返る。
- **L4. 文に日付語が混ざる頼み**: 「4 時に変えて、説明に明日と入れて」のように、時刻の頼みと日付語を含む説明の頼みが 1 文に入ると、AI の始まりが違う（時刻だけ）ので `apply_day` が当たり、「明日」で日付が動きうる。`_resolve` は日付語が 1 つのとき表で決める（B:secretary_dates.py:149-151）。この場合も設計 §16-7 の「はい」の前に画面で下書きを見せる手当てで防げる。対象外の欄（§16-2）に 1 行書くか、PO に知らせるだけでよい。
- **L5. カルテの始まりが日本時間でない画面**: `toKarteTime` はブラウザの時差の印を付ける（B:design.md:484）。日本以外のブラウザだと、AI が +09:00 で返した同じ時刻が「違う」と数えられ（文字で比べる分かれ道・B:design.md:469）、`apply_day` が当たりうる。また `_day_of`（B:secretary_dates.py:171）は +09:00 以外の印を読まないので、そのときは日付は替わらず安全な側。実害は小さい。日本のブラウザだけが対象、とカードに 1 文あると迷わない。

## 6. 見る点ごとの結果

- (1) 第 2 回の R1: 直った（§1。実物の `apply_day`・`_guard_ok`・`_resolve` の行で 2 件の試験が期待どおりに動くことを確認）。
- (2) 取り込んだ L1〜L6: 実物と食い違わない（§2・§3）。
- (3) 直しで新しく出た矛盾・穴: 作れない・壊れるものは無い。L1〜L5。
- (4) 実装者が迷わず作れるか: 作れる。L1（失敗時に外す口）だけは 1 文あると迷わない。

## 7. 次

- design.md §16-12 の「第 3 回」の行に結果（APPROVE・R 0 件・L1〜L5）を書く。L は設計担当が直すかどうかを決めてよい（L1・L3 は 1 文ずつで済む）。
- そのあと PO の実装承認（card-binW.md の状態の行にある）のとおり、実行役（クラウドの Sonnet）へ card-binW.md を渡してよい。
