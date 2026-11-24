# 設計審査（architect）— 便W「声で予定の下書きを直す」第 1 回

- 審査対象: `origin/release/secretary-voice-draft-edit` の design.md §16・card-binW.md・recon.md §9・kgi.md §6・ADR-1082 What 7 と、同じ枝の実物
- 審査日: 2026-11-24（スケジュール実行）／ 読むだけ。製品のコード・DB・本番には触れていない
- 表記: 「B:」は `origin/release/secretary-voice-draft-edit` の中のパス（`git show` で読んだ）

## 判定: REVISE（直す必要あり）

1. 方向（AI の値が勝つ合わせ方・日時 3 欄だけ送る・指示文 1 行）は実物と合い、ADR-027・ADR-144・ADR-067 と check-error-text-next-action.js にも反しない。
2. ただし R1〜R3 を直さないと、CI の `API Contract Check` が赤になる（R1）／直す頼みに AI が請求書を返すと請求書の下書きが出る（R2）／待つ間に作成を押すと二重に予定ができうる（R3）。
3. R1〜R3 は設計書とカードの書き足しだけで直る。直った版は、この第 2 回で見る。

---

## 1. 点検の結果（(1) カード §2 と design §16 の行番号・変更前の文）

実物と 1 件ずつ突き合わせた。「合う」以外だけ備考を付ける。

| # | 設計・カードの言い分 | 実物 | 判定 |
|---|---|---|---|
| 1 | カード§2(1) `SecretaryChat.tsx:186-192` が `} else if (confirm.tries === 0) {` から `askAgain` | B:frontend/src/features/secretary/SecretaryChat.tsx:186-192 | 合う |
| 2 | (2) `:225-245` に `pendingConfirmRef.current = { id: pendingId, tries: 0 }` と `confirmEvent` | 同:243・:244（`if` の頭は :225） | 合う |
| 3 | (3) `SecretaryDraftEvent.tsx:31-34` の口は `submitByVoice(): boolean` だけ・`:51` が `useState<"personal" \| "shared">(draft.calendar_type)` | B:frontend/src/features/secretary/SecretaryDraftEvent.tsx:31-34・:51 | 合う |
| 4 | (4) `KarteIn` が `extra="forbid"`・`asked_count` が最後 | B:backend/app/schemas/assistant.py:21・:32 | 合う |
| 5 | (5) `:331-348` に `merge_karte`・`apply_day`・`settle_dates`、`:395-411` に `next_ask` と `EventDraft` | B:backend/app/routers/assistant.py:333-349（`if new_path:`は :333）・:397・:398-411 | 合う（始まりの行が 2 行ずれるだけ） |
| 6 | (6) prompt.txt 18 行・`:14` が短い答えの決まり | B:secretary-agent/prompt.txt:14・全 18 行 | 合う |
| 7 | (7) `askAgain` の使用は `SecretaryChat.tsx:188` と T7 だけ | `git grep -n askAgain` → B:SecretaryChat.tsx:188・B:SecretaryChat.test.tsx:988〜998（T7）・ja.json:6330・en.json:6330 | 合う（鍵そのものは ja/en の 2 か所。設計 §16-6-4 が「両方から消す」と書いてあり矛盾しない） |
| 8 | design §16-4(1) `KarteIn :18-32`・`EventDraft :159-172` | B:backend/app/schemas/assistant.py:18-32・:159-172 | 合う |
| 9 | §16-4(3) `:331-348`・(4) `:392-411` | B:backend/app/routers/assistant.py:331-349・:391-411 | 合う |
| 10 | §16-4(5) `_agent_payload :190-207` | B:backend/app/routers/assistant.py:192-205（下の 2 行は :192 から） | 合う（範囲が広いだけ） |
| 11 | §16-5 `compose.mjs:11-14`（カルテが無い頼みに見出しが付かない） | B:secretary-agent/compose.mjs:11-14（:13 `karte === null ? ""`） | 合う |
| 12 | §16-6(1) `secretaryApi.ts:56-67`・`:40-53` | B:frontend/src/features/secretary/secretaryApi.ts:56-67（EventKarte）・:40-53（EventDraftData） | 合う |
| 13 | §16-6(3) `:43`・`:277`（送り中は自動で送らない） | B:SecretaryChat.tsx:43・:277（`sending` を見る） | 合う |
| 14 | recon §9-2 `prompt.txt:3-18 の 15 行` | B:secretary-agent/prompt.txt:3-18 は 16 行（`決め:` の見出し＋15 項目） | 数え違い（L7） |
| 15 | recon §9-3 p4「時刻だけ変えると end は null」 | B:docs/handoff/secretary-voice-input/binW/probe-before-20261125.jsonl の p4 は 2 回とも start `2026-11-26T16:00:00+09:00`・end null（カルテの日付のまま） | 合う（日付が今日にずれる心配は、この 2 回では出ていない） |

## 2. R（直さないと作れない・壊れる）

### R1. `frontend/api-contract/openapi.json` を触る物に入れる（CI が赤になる）

- 事実: `KarteIn` に `edit`、`EventDraft` に `edited` を足すと API の形が変わる。`.github/workflows/api-contract-check.yml:38`（`python -m tools.export_openapi ../frontend/api-contract/openapi.json`）で書き出し、`:55` の `git diff --exit-code -- frontend/api-contract/` で差があれば落ちる。openapi.json には今 `KarteIn`（B:frontend/api-contract/openapi.json:16377）と `EventDraft`（:11330）がある。
- 食い違い: B:docs/handoff/secretary-voice-input/card-binW.md:8-23 の「触るファイル（これ以外は触らない）」と §5 の確かめに openapi.json が無い。実装者は表のとおり触らず push し、PR で赤になる。前の便（ADR-1078）は同じ理由で openapi.json を変更に入れていた（B:docs/handoff/secretary-event-karte/card.md:1633）。
- 直し方:
  - card-binW.md §1 の表に 1 行足す: `frontend/api-contract/openapi.json` ｜ `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で書き出し直す（手で書かない。差は `KarteIn.edit` と `EventDraft.edited` だけのはず）。
  - card-binW.md §5 に足す: 書き出し直した後の `git diff --stat frontend/api-contract/openapi.json` を結果の行に貼る。差が 2 欄以外にも及べば止めて `NEEDS_DECISION:`。
  - design.md §16-4 に項目 6 を足す: 「`frontend/api-contract/openapi.json` を書き出し直す（`.github/workflows/api-contract-check.yml`）」。

### R2. 直す頼みの口の分かれ道を、実物の形に合わせて書き直す（請求書・二重の日付直し）

事実（B:backend/app/routers/assistant.py）:
- `:376` の `if intent.kind == "invoice":` は **AI の答えの種類**（`intent.kind`）で請求書の下書きを作る。`final_kind` は見ていない。
- design §16-4(3) は「AI が unknown や請求書を返しても、最終の種類は event・下書きはカルテのまま」と書くが、AI が請求書を返すと、`:376` が先に当たり、`InvoiceDraft` を返す。画面は請求書の下書きを出し、確かめ待ちは付かない（`SecretaryChat.tsx:217-222`）。前の予定の下書きは残るが、直す頼みが請求書として返る。設計の文と実物がぶつかる。
- 同じ道の `:341-345` は `final_kind == "event"` かつ `intent.kind == "event"` で `apply_day(final_ev, body.text, now.date(), karte)` を呼ぶ。直す道は design の文どおり「merge の前の AI の答えに `apply_day(ev, text, today, None)`」を当てるので、そのまま通すと日付の表が 2 回当たる。2 回目は `apply_day` の `:217-218`（カルテの始まりが埋まっていれば替えない）が止めるが、カルテの始まりが null の下書き（画面で手で消した）では 2 回目も当たる。偶然に頼る形で、実装者が迷う。

直し方（design.md §16-4(3)(4) を次の形に書き直す。カードの §1 の `assistant.py` 行は「design §16-4 の 1・3・4・6」に）:
1. `:330-331` の後ろ（`if new_path:` の中の最初）に、`karte is not None and karte.edit` の枝を足し、既存の `if karte is not None and intent.kind == "unknown": … elif … "event":`（`:334-340`）の **前** に置く（同じ if 連鎖の先頭の枝にする）。その枝の中で: `ai_ev = intent.event if intent.kind == "event" else None`／`ai_ev` があり `ai_ev.start` が null でなければ `ai_ev = apply_day(ai_ev, body.text, now.date(), None)`／`final_ev, edited = merge_edit(ai_ev, karte)`／`final_kind = "event"`。
2. `:341-349` の `if intent.kind == "event": final_ev = apply_day(...)` は、直す道では呼ばない（枝の条件に `not edit_mode` を足す。`edit_mode = karte is not None and karte.edit` を `:333` の前で 1 回だけ作り、`:376`・`:397` でも同じ名前を使う）。`settle_dates` は直す道でも呼ぶ（`:346-349` のまま）。
3. `:376` を `if final_kind == "invoice":` に直す（`final_kind` は `:330` で `intent.kind` に初期化されるので、直す道以外では今と同じ）。直す道だけ `final_kind` が event に替わるので、AI が請求書を返しても請求書の枝に入らない。
4. `:391-411` の枝では `edit_mode` のとき `ask, ask_count = None, 0`・`edited=edited`、それ以外は今の `next_ask`・`edited=None`。
5. 試験（card-binW.md §4 の「口」）に 1 件足す: `edit: true` で AI が **請求書** を返す→ kind は event・`edited` 偽・中身はカルテのまま・請求書の候補検索（`resolve_names`）が呼ばれない。

### R3. 待つ間に前の下書きが「作成済み／取り消し」になったときの答えの扱い

- 事実: 直す頼みを送っている間、前の下書きの吹き出しは生きている（`SecretaryChat.tsx:333-349` が描く `SecretaryDraftEvent`。「作る」ボタンは `saving` 以外で押せる＝B:SecretaryDraftEvent.tsx:191）。design §16-6(3) は「待つ間は確かめ待ちを外す」としか書かず、答えが届いたとき前の吹き出しを無条件に `edit.replaced` に替える形に読める。
- 壊れ方: 利用者が待つ間にボタンで「作る」を押す→ `markCreated`（:284-290）が前の吹き出しを「作りました」に替える→ そのあとに直した答えが届く→ 前の吹き出しが `edit.replaced` の文に上書きされ、新しい下書きが出る。画面には「作りました」が消えて「直した下書き」が残り、もう一度「はい」と言うか押すと **同じ予定が 2 件** できる。「いいえ・取り消し」でも同様に、取り消した下書きが新しい下書きで復活する。
- 直し方（design §16-6(3) の「答えが event で edited が真」の枝の頭に足す）: 答えが届いたとき、前の下書きの id（`confirm.id`）が「作成済み・取り消し済み」の印の集合に入っていれば、直した答えを捨てる（考え中の吹き出しを消すか、`edit.replaced` を使わず何もしない）。印は `markCreated`・`markCancelled`（:284-294）が `useRef(new Set<number>())` に id を入れて作る（state ではなく ref。同じ関数に 1 行ずつ足すだけ）。窓を閉じた後の捨て方（`session` の値が違えば何もしない）と同じ書き方で 1 か所にまとめる。
- 試験を 1 件足す（card-binW.md §4 の frontend）: 直す頼みの API を保留にしたまま前の下書きの「作る」を押す→ API を返す→ 吹き出しは「作りました」のまま・新しい下書きは出ない・POST /calendar/events は 1 回。

---

## 3. L（軽い指摘・直さなくても作れる）

- **L1. `merge_edit` の決まりの抜け（設計 §16-4(2)）**: (a) 前後の空白を除いたあとの値を使うのか、元の値のままかが書かれていない（「テスト」と「テスト 」で `edited` が揺れる）。除いた値を使い、同じく除いた値で比べる、と 1 文足す。(b) 「時刻として比べる」で、片方だけ時差の印が無いと `datetime` の比べが `TypeError` になる。長さの計算（印が混ざればカルテの終わりのまま）と同じく、比べられなければ文字の比べにする、と足す。(c) カルテの終わり < 始まり（画面で手で作れる）のときの長さが負になる。負なら終わりはカルテのまま。(d) `edited` を `settle_dates` の前で数えるので、「終わりを 9 時に」（始まり 10 時）のように終わり < 始まりになると、`settle_dates`（B:backend/app/services/secretary_karte.py:63-67）が終わりを null にし、`edited` 真・終わりが空の下書きが出て前の下書きが替わる。声は「画面で確かめて」になる。作れはするが、前の下書きを失う。`settle_dates` の後で、土台の始まり・終わりが埋まっていたのに null になったら「変わらない」（カルテのまま・`edited` 偽）に戻す、が安全。
- **L2. 窓を閉じた後の条件（設計 §16-6(3) 最後の行）**: `session` の値だけ見ると書かれているが、今の道（B:SecretaryChat.tsx:211・:220・:225・:249・:265）は `voiceOnRef.current && sentIn === session.current` の両方を見る。待つ間に声の切り替えを切った場合に `speakThenListen` が声が無効のまま呼ばれ、「声が使えません」の注記が出る。`startConfirm` と失敗の読み上げも同じ両方の条件にする、と書く。
- **L3. 「はい、4 時にして」は作る側に判定される**: `judgeYesNo`（B:frontend/src/features/secretary/secretaryVoiceAnswer.ts:63-64）は、いいえの語が文のどこかにあれば no、無ければ文の頭が肯定の語なら yes。「はい、場所は渋谷にして」「オッケー、説明にテストと入れて」は yes になり、**直さずに前の下書きで予定ができる**。§16-7 の表は「違う、4 時にして」（取り消し）だけ載せ、この向きが無い。判定は変えない決め（§16-7）なので、表に 1 行足して PO に知らせる。
- **L4. `currentValues` の書き**: (a) `is_meeting` を何から作るかが無い（`draft.is_meeting` を渡す、と書く。次を聞かないので結果は変わらない）。(b) `toKarteTime` の時差の印の作り方が決まっていない（例の `+09:00` は固定に読める）。ブラウザの時差から `±HH:mm` を作る、と書く（`toISOString()` の `Z` 付きでも backend は読める＝B:backend/app/schemas/assistant.py:126-128 で `Z` を許す）。(c) 説明が 1000 字を超える下書き（手で貼る）だと `KarteIn`（:27-28 `max_length=1000`）で 422 になり、「失敗」の文が出る。1000 字で切る、と書くか、対象外に書く。
- **L5. 終日の下書きの日付の頼み**: 設計 §16-2 は「終日の切り替え・終日では時刻の頼みを使わない」としか書かないが、§16-4(2) は終日のとき始まり・終わりをカルテのままにするので、「来週の月曜にして」も捨てられ、`edited` 偽（notEdited）になる。終日の下書きの形（今の道は `settle_dates` が終わり＝始まりにする＝B:secretary_karte.py:60-61。画面は `currentValues` で 00:00〜23:59 を送る）とは矛盾しない。§16-2 の対象外に「終日の下書きの日付の頼み」も足す、と書く。
- **L6. 説明・題名の消し込み**: AI が null を返すと「言われていない欄」と区別できず、「説明を消して」は直せない（`edited` 偽）。§16-2 の対象外に 1 行足す。
- **L7. recon §9-2 の数**: `prompt.txt:3-18 の 15 行` は 16 行（項目は 15 個）。直さなくても誤読しない。
- **L8. 配備の順**: 画面だけ先に新しくなると、古い backend が `edit` を 422 で断り（`extra="forbid"`・B:schemas/assistant.py:21）、直す頼みが「失敗」の文になる。§16-8 の戻し方は「新 backend・古い画面」だけ書いている。ほぼ同時の配備なので実害は短い時間に限るが、§16-8 に 1 文足す。
- **L9. T7 の書き直し**: 既存の T7（B:SecretaryChat.test.tsx:988-1003）は `mock.postWithTimeout` を 1 回だけ返す。書き直しの案どおりなら 2 回目・3 回目の API 返しを足す必要がある（`edited: false` の返しを 2 回）。カードに「`mockResolvedValueOnce` を 2 回足す」と書くと迷わない。

---

## 4. 見る点ごとの結果（まとめ）

- (1) 行番号・変更前の文: 実物と合う（§1 の表）。
- (2) `merge_edit` の決まりと口の分かれ道: 「AI の値が勝つ・時刻だけなら長さを保つ・終日は時刻を替えない」は `settle_dates`（B:secretary_karte.py:50-68）・`apply_day`（B:secretary_dates.py:201-228）と食い違わない。`apply_day(…, None)` は B:secretary_dates.py:217 のカルテの門を通らず、始まりへ当たる（設計の意図どおり）。終日の下書きの形: 今の道は終わり＝始まり（B:secretary_karte.py:60-61）、画面が送る終日は 00:00〜23:59（設計 §16-6(2)）。どちらも `settle_dates` を通る。食い違いは R2（`:376` の請求書の枝・日付の表の二重）と L1。
- (3) 画面: `currentValues` の時刻は `YYYY-MM-DDTHH:mm:00+09:00`（25 字）で `KarteIn` の ISO・40 字の検査（B:schemas/assistant.py:24-25・:34-40）を通る。部品を作り直す（新しい id）流れ・確かめ待ちの回数（0→1→外す）は筋が通る。穴は R3（待つ間の作成・取り消し）と L2。
- (4) 指示文の 1 行: B:secretary-agent/compose.mjs:11-14 は、カルテが無い頼みでは見出し（`途中の予定`）を出さないので、新しい行は今までの頼みに当たらない。`secretary-agent/server.test.mjs:310-313`・`:353-357`・`secretary-codex/server.test.mjs:300-303`・`:396-401`・`:439-445` は prompt.txt を読んで期待を作るので、1 行足しても壊れない。確かめは W4（23 件）で、今の設計の道のまま。
- (5) 決まり: ADR-027（文字は `t()`・ja/en 同じ鍵）— §16-6(4) は両方に足し、`askAgain` を両方から消す。ADR-144・ADR-067（新しい部品・色・大きさを作らない）— §16-6(5) と一致。check-error-text-next-action.js（B:frontend/scripts/check-error-text-next-action.js:28-29）— 新しい 3 文は「失敗・エラー・できません」を含まないので数えに入らず、`notEdited` は「ください」も含む。通る。ただし R1 の openapi.json は別の CI の道。
- (6) 実装者が迷わず作れるか: R1〜R3 を直せば作れる。L1・L2・L4・L9 は、書いてあるほうが迷わない。

## 5. 次

R1〜R3 を design.md §16・card-binW.md に直してから、第 2 回の審査（`review-architect-binW-2.md`）を出す。L は直すかどうかを設計担当が決めてよい。
