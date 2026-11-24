# 設計審査（architect）— 便W「声で予定の下書きを直す」第 2 回

- 審査対象: `origin/release/secretary-voice-draft-edit`（6d422df2e）の design.md §16・card-binW.md と、同じ枝の実物
- 第 1 回: `origin/release/secretary-voice-draft-edit-review1` の `docs/handoff/secretary-voice-input/review-architect-binW-1.md`
- 審査日: 2026-11-24（スケジュール実行）／ 読むだけ。製品のコード・DB・本番には触れていない
- 表記: 「B:」は `origin/release/secretary-voice-draft-edit` の中のパス。実物のコードは設計の commit だけが載っていて、まだ未変更（今の形）

## 判定: REVISE（直す必要あり・R は 1 件）

1. 第 1 回の R1（openapi.json）・R2（口の分かれ道）・R3（待つ間の作成・取り消し）は、設計書・カードに直った。実物の行と突き合わせて矛盾は無い。取り込んだ L1・L2・L4・L5・L6・L8・L9 も実物と食い違わない。
2. ただし R2 の直し方（直す道で `apply_day(…, None)` を当てる）が、新しい穴を作っている。カルテの「始まりがあれば替えない」門（B:backend/app/services/secretary_dates.py:217-218）を外すので、AI が言われていない始まりをカルテと同じ値で返す（設計 §16-7 が認めている）と、説明に「明日」と入れる頼みで予定の日付が明日に動く（下の R1）。
3. R1 は設計書 §16-4(3) とカード §4 の書き足しだけで直る。

---

## 1. 第 1 回の R1〜R3 の突き合わせ

| 第 1 回 | 直った場所 | 実物との突き合わせ | 判定 |
|---|---|---|---|
| R1 openapi.json の書き出し | B:design.md:475（§16-4 項目 6）・B:card-binW.md:15（§1 表）・:62（§5）。§5 に `git diff --stat` を貼り、差が 2 欄以外なら止める | CI は B:.github/workflows/api-contract-check.yml:38 で書き出し、:55 の `git diff --exit-code -- frontend/api-contract/` で落とす。命令の書きも同じ | 直った |
| R2 口の分かれ道 | B:design.md:468-473（§16-4(3)(4)）。`edit_mode` を `if new_path:` の前で 1 回・if 連鎖の先頭・`apply_day` の二重を止める・`:376` を `final_kind`・`settle_dates` の後に null なら戻す・請求書の試験（B:card-binW.md §4 口） | 下の §2 で行ごとに確認 | 直った（ただし新しい穴 R1 あり） |
| R3 待つ間の作成・取り消し | B:design.md:490（ref の集合）と、同 §16-6(3) の「答えが届いたら最初に」の枝・B:card-binW.md §4 frontend の試験 | 下の §2 で確認 | 直った（残る狭い窓は L1） |

## 2. 実物の行との確認（直した分）

R2:
- `:333` の `if new_path:` の前に `edit_mode` を作る置き場がある（B:backend/app/routers/assistant.py:330-333。`final_kind = intent.kind` は :330、`new_path` は :301、`karte` は :302）。
- if 連鎖は今 `if karte is not None and intent.kind == "unknown":`（:334）→ `elif … "event":`（:338）。先頭に `if edit_mode:` を足せば、unknown の枝に先に入らない。
- `:343` `if intent.kind == "event":` の中の `apply_day(final_ev, body.text, now.date(), karte)`（:345）に `not edit_mode` を足せば二重にならない。`settle_dates` は :346-349 の try の中で、直す道でも通る。
- `:376` は今 `if intent.kind == "invoice":`。`final_kind` に直せば、直す道で AI が請求書を返しても入らない。`elif final_kind == "event" and new_path:`（:391）に落ちる。`next_ask` は :397。`kind=final_kind`（:432）なので返す種類は event になる。
- `settle_dates`（B:backend/app/services/secretary_karte.py:50-68）は、終わり < 始まりなら終わりを null にする（:63-67）。設計の「土台が埋まっていたのに null になったら戻す」は、この動きに対する手当てとして成り立つ。

R3:
- `markCreated`・`markCancelled`（B:frontend/src/features/secretary/SecretaryChat.tsx:284-294）は id を受け取る形で、そこに集合の 1 行を足せる。
- 下書きの吹き出しの id と確かめ待ちの id（`pendingConfirmRef.current = { id: pendingId, … }`・:243）は同じ。直した答えの新しい下書きも `pendingId` で出るので、`startConfirm(新しい id, …)` に合う。

取り込んだ L:
- L1（空白・時差の印の混在・負の長さ・settle 後の戻し）は B:design.md §16-4(2)(3) にある。
- L2（`voiceOnRef.current && sentIn === session.current` の両方）は B:design.md §16-6(3) の最後の行にあり、今の道（B:SecretaryChat.tsx:211・:220・:249・:265）と同じ書き。
- L4（`is_meeting` は下書きの値・`toKarteTime` の時差の印・1000 字で切る）は §16-6(1)(2) にある。B:backend/app/schemas/assistant.py:27-28（`max_length=1000`）と合う。
- L5・L6 は §16-2 の対象外に載った。L8 は §16-8 に載った。L9 は B:card-binW.md §4 に載った。

## 3. R（直さないと作れない・壊れる）

### R1. 直す道の `apply_day` は、AI が始まりを「カルテと同じ値」で返したときに日付を動かしてしまう

- 事実:
  - B:design.md:469 は、直す道で `ai_ev.start` が null でなければ `apply_day(ai_ev, body.text, now.date(), None)` を当てると書く。
  - `apply_day` の「カルテの始まりが埋まっていれば替えない」門は `karte is not None and karte.start is not None and karte.asked != "start"`（B:backend/app/services/secretary_dates.py:217-218）。直す道は `karte` に None を渡すので、この門を通らない。
  - 「明日」「今日」「あさって」などの相対語は `_guard_ok` の `guard` が None（B:backend/app/services/secretary_dates.py:140 は曜日だけ guard を付ける・:191 `if guard is None: return True`）なので、AI の値が何であっても日付が替わる。
  - AI が言われていない欄に、カルテと同じ値を入れて返すことは設計自身が認めている（B:design.md:504。p6 の 1 回目の始まり・終わりはカルテと同じ値）。つまり `ai_ev.start` が null でなく、カルテと同じ値のことがある。
- 壊れ方: 「説明に明日までに資料を持参と入れて」と頼む→ AI が description と、カルテと同じ start を返す→ `ai_ev.start` が null でないので `apply_day` が当たり、文の「明日」で **始まりの日が明日に動く**（終わりも同じ日なら一緒に動く）→ `merge_edit` はこの値を「AI の値が勝つ」で採る→ 直した下書きは日付が変わり、`edited` 真・説明も入る。声は「直しました。…を〇月〇日に入れますか？」と読むが、頼んだのは説明だけで、日付が変わったことに気づけないと予定が違う日にできる。設計の約束「言われていない欄は変わらない」（B:design.md:504）が破れる。
- 直し方（B:design.md §16-4(3) の 2 つ目の `if edit_mode:` の枝の文を次に直す。B:card-binW.md §4 に試験を 1 件足す）:
  1. 枝の中の `apply_day` は、「AI の始まりがカルテの始まりと**時刻として違う**ときだけ」当てる、と書く（`ai_ev.start` が null でなく、カルテの始まりが null か、`parse_iso` で比べて違うとき。比べられなければ文字で比べる＝L1 の `merge_edit` の比べと同じ書き）。同じ値で返ってきたら、その始まりは「言われていない欄」なので `apply_day` を当てない。
  2. 一方、「来週の月曜にして」のように AI が日付を替えて返した場合は、カルテの始まりと違うので `apply_day` が当たり、日付の揺れ（AI の数え間違い）を表で直せる。設計の意図（B:design.md:469）はそのまま残る。
  3. カード §4 の「口」に 1 件足す: `edit: true`・カルテの始まりが明日以外・文は「説明に明日までに資料を持参と入れて」・偽の AI は description と **カルテと同じ start** を返す→ 返る下書きの start・end はカルテのまま・description だけ変わる・`edited` 真。
  4. 逆向きも 1 件: 偽の AI が start を 3 日後で返し文が「来週の月曜にして」→ `apply_day` で来週の月曜になる（表が効く）。

---

## 4. L（軽い指摘・直さなくても作れる）

- **L1. R3 の窓が一部残る（作る押下の途中）**: B:design.md:490 の集合に id が入るのは `markCreated`（作成の API が成功した後）。「作る」を押して `saving` の間（B:frontend/src/features/secretary/SecretaryDraftEvent.tsx:66 の `setSaving(true)` から :80 の `onCreated()` まで）に直した答えが届くと、集合が空のまま前の吹き出しが `edit.replaced` に替わり、新しい下書きが出る。その後 `markCreated(前の id)` が `replaceMessage` で前の吹き出しを「作りました」に戻し、新しい下書きも画面に残る＝同じ予定を 2 件作れる。窓は作成 API の往復の間だけで狭いので直さなくても作れる。直すなら `SecretaryDraftEvent` の `onCreated` の前の「作り始めた」を親に知らせる props（例 `onSaving`）を足し、そこでも集合に入れる。新しい部品は要らない。
- **L2. settle 後の「カルテに戻す」で再度 `settle_dates` を通すか**: B:design.md:471 は「下書きはカルテのまま」と書く。カルテ自身の終わりが始まりより前（画面で手で作れる）だと、戻した値をそのまま返すのか、`settle_dates` をもう一度通して終わりを null にするのかが読み取れない。前者（返す値は `merge_edit(None, karte)` そのまま・`settle_dates` は通さない）と 1 文書く。
- **L3. 型検査のための 1 行**: `edit_mode = karte is not None and karte.edit` は、枝の中の `karte` を型検査（mypy）が non-None と見ない。枝の先頭に `assert karte is not None`（既存の `assert intent.event is not None`＝B:backend/app/routers/assistant.py:339 と同じ書き）と書くと迷わない。
- **L4. 直した答えを読み上げる間の「読み取れなかった」の回数**: B:design.md:494 の「回数が 0 なら…1 なら…」は、直った答えが 1 回出たら新しい下書きの tries が 0 に戻る（`startConfirm` が 0 で始める）形。「直せない→直せた→直せない」は 1 回目の `notEdited` から数え直しになる。意図どおりだが、T7 に「直せた後の回数は 0 に戻る」の 1 件があると迷わない。
- **L5. `setSending` の書き**: B:design.md の §16-6(3) は「送り中は自動で送らない（:277）」と書くが、`setSending(true)` と `finally { setSending(false) }` を直す道の中に書く、と明示したほうがよい。今の `send` の `finally`（B:SecretaryChat.tsx:268-270）は確かめ待ちの道の `return`（:193）の後ろにあるので、直す道は自前の try/finally が要る。
- **L6. `calendarType` の型**: B:frontend/src/features/secretary/secretaryApi.ts:40-53 の `EventDraftData.calendar_type` は `"personal"` だけ。B:design.md の `initialCalendarType?: "personal" | "shared"` は SecretaryDraftEvent の props で別の型なので矛盾はしないが、`calendar_type` の `"personal"` と props の型が違うことをカードに 1 文書くと迷わない。

---

## 5. 見る点ごとの結果

- (1) 第 1 回の R1〜R3: 3 件とも直った（§1・§2）。
- (2) 取り込んだ L1・L2・L4・L5・L6・L8・L9: 実物と食い違わない（§2）。
- (3) 直しで新しく出た穴: R1（`apply_day` の門が外れる）。ほかは L1〜L6。
- (4) 実装者が迷わず作れるか: R1 を直せば作れる。L2・L3・L5 は書いてあるほうが迷わない。

## 6. 次

R1 を design.md §16-4(3)・card-binW.md §4 に直し、§16-12 の「第 2 回」の行に結果を書いてから第 3 回に出す。L は直すかどうかを設計担当が決めてよい。
