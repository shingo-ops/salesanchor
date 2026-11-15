# recon — 予定のカルテ 直し1（時刻として読めない答え）

親: [../design.md](../design.md) ／ 設計: [design.md](design.md) ／ 手順書: [card.md](card.md)

すべて origin/main 65a2bb376（本番の HEAD と同じ。#5514 のマージ 5f24dda83 を含む）で読んだ。

## 1. 本番で起きたこと（観測事実）

- 2026-11-15 10:4x JST、本番の使い捨ての backend 容器で試しの会話 10 本（`../design.md` §8）を流した。T1〜T9 は表のとおり。T10 の 3 通目（カルテ: 題名「棚卸し」・始まりあり・終わり空・`asked=end`・`asked_count=2`、文「わからない」）が `HTTPException 502 {'code': 'unreadable'}` になった。期待は「確かめの欄（終わりは空）」。
- 同じカルテと文で容器（secretary-codex・担当 gpt-5.6-terra）を直接 3 回呼んだ。容器はどれも 200。AI の答え（intent.event）は次のとおり:
  - 1 回目・2 回目: `start` だけ値・`end` は null → 合わせると確かめの欄になる（正しく動く）
  - 3 回目: `"end": "わからない"`（文字をそのまま終わりの欄に入れた）。答えの形の検査（AgentEnvelope）は通る
- 試しの前後で予定の件数は変わっていない（tenant_001 3 件・tenant_004 25 件。最新の作成時刻も同じ）。予定が勝手にできる害は無い。

## 2. 失敗の道（コード）

- `backend/app/services/secretary_karte.py:28-30`: 直前に聞いた欄（`asked`）は、AI の値が null でなければ AI の値を使う。→ `end = "わからない"`。
- `backend/app/services/secretary_karte.py:39-54` `settle_dates`: 始まりがあれば `parse_iso(ev.start)`（:48）、終わりがあれば `parse_iso(end_text)`（:52）。読めないと `ValueError` をそのまま出す（:46 は始まりが空のときの終わり）。
- `backend/app/schemas/assistant.py:126-128` `parse_iso` は `datetime.fromisoformat`。読めなければ `ValueError`。片方だけ時差の印（+09:00 など）が無い 2 つを `<` で比べると `TypeError`（Python の datetime の決まり）。
- `backend/app/routers/assistant.py:324-326`: 新しい画面の道で `settle_dates` が `ValueError`/`TypeError` を出すと 502 unreadable。:343 で使用の記録は failed。
- AI の答えの形 `IntentEvent` の `start`/`end` は文字か null で、時刻として読めるかは見ない（`backend/app/schemas/assistant.py:70-81`、`start`/`end` は :75-76）。カルテ（`KarteIn`）の `start`/`end` は読めなければ 422 なので、読めない値は AI の答えからだけ来る。読めるかは `settle_dates` だけが見る。

## 3. この扱いを決めた設計と試験

- `../design.md:124` ⑤「始まりがあれば読む。読めなければ今と同じ 502。…終わりがあれば読む。読めなければ 502」。AI が欄に文字を入れる場面を想定していなかった（入れ忘れ）。
- `backend/tests/test_assistant_karte.py:105-106`: `settle_dates(start="あした")` が `ValueError`。
- `backend/tests/test_assistant_karte.py:222-227` `test_unreadable_start_on_new_path_is_502`: 新しい道で始まり「あした」→ 502。
- 古い画面の道（karte の鍵が無い頼み）は `backend/app/routers/assistant.py:328-339` で別に読む。`settle_dates` を通らない。古い道の試験 `backend/tests/test_assistant_router.py` は karte の鍵を送らない。

## 4. 既存 ADR の検索

- `git grep -il "secretary_karte\|予定のカルテ" docs/adr/` → `docs/adr/ADR-1078-secretary-event-karte.md` だけ。ADR は 502 の扱いを書いていない（決めているのはカルテを保存しない・聞く順・回数の上限）。ADR の変更は不要。
- 親の目標 `../kgi.md` C6「同じ欄を 2 回聞いても埋まらないときは 3 回目を聞かず、最後の確かめの欄を出して手で入れられる」。今の動きはこれに反する。

## 5. 未確認

- 本番で、AI が時差の印の無い時刻を返したことがあるか（`TypeError` の道）は観測していない。同じ「時刻として扱えない値」なので一緒に塞ぐ（design.md §3）。
