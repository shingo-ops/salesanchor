# 作業指示書（便 W3）— 素の 1〜6時を午後に・直せなかったときは「はい」付きでも作らない

- 設計: `docs/handoff/secretary-voice-input/design.md` §18（必ず全部読む。§17 は前の便）／ 事実: `docs/handoff/secretary-voice-input/recon.md` §11 ／ 目標: `docs/handoff/secretary-voice-input/kgi.md` §8 Y1〜Y6
- 状態: PO の実装承認あり（2026-11-25 チャット「どちらも直す」。前の指示「PRマージ、デプロイまで完走させてくれ」）
- 実行役: クラウドの Sonnet。枝 `release/secretary-voice-w3-ask-pm`（設計の commit が載った枝）。始める前に `./scripts/dev/executor-preflight.sh || exit 1`。
- 規則: `docs/ai-agents/executor-checklist.md`・ADR-027（文字は `t()`・ja/en 同じ鍵。今回は鍵を足さない）・ADR-144/ADR-067（新しい部品・色・大きさを作らない）。

## 1. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `backend/app/services/secretary_dates.py` | design §18-4 の 1（`afternoon_hours` を足すだけ） |
| `backend/app/routers/assistant.py` | §18-4 の 2・4 |
| `backend/app/schemas/assistant.py` | §18-4 の 3 |
| `frontend/api-contract/openapi.json` | §18-4 の 5（命令で書き出し直す。手で書かない） |
| `backend/tests/test_secretary_dates.py` | §4 |
| `backend/tests/test_assistant_karte.py` | §4 |
| `frontend/src/features/secretary/secretaryApi.ts` | §18-5 の 1 |
| `frontend/src/features/secretary/SecretaryChat.tsx` | §18-5 の 2 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | §4 |

触らない: `secretary-agent/` の全部・`backend/app/services/secretary_karte.py`・`frontend/src/features/secretary/SecretaryDraftEvent.tsx`・`frontend/src/locales/`・migrations・deploy.yml・`docs/`（Opus が書く）。

## 2. 実物の点検（始める前に。違ったら止めて `BLOCKED:` で返す）

（１）`backend/app/routers/assistant.py:327` が `intent = envelope.intent`。`:334-335` が `edited = False`・`meet_refused = False`。`:370-376` が「直した結果が日時を失ったら」の分かれ（`final_ev, edited = base_ev, False`）。`:442` が `meet_refused=meet_refused if edit_mode else None,`。`:57` が `from app.services.secretary_dates import apply_day, same_day`。
（２）`backend/app/services/secretary_dates.py:14` が `from app.schemas.assistant import IntentEvent, KarteIn, parse_iso`、`:17` が `_JST_OFFSET = timedelta(hours=9)`、`:207` が `def apply_day(`。
（３）`backend/app/schemas/assistant.py:178` が `meet_refused: bool | None = None`（`EventDraft` の最後の欄）。
（４）`frontend/src/features/secretary/secretaryApi.ts:57` が `meet_refused?: boolean | null;`。
（５）`frontend/src/features/secretary/SecretaryChat.tsx:233` が `} else if (yesFallback) {`。

## 3. 想定される分かれ（迷ったら止めて `NEEDS_DECISION:`）

- 時刻の値の 12 時間足しは `parse_iso` で読んだ `datetime` に `timedelta(hours=12)` を足し `isoformat(timespec="seconds")`。時差の印が +09:00 でない・無い値は触らない（`_JST_OFFSET` と比べる）。
- 「素の時刻」の数の集まりと、値の時（日本時間）を比べる。分は見ない（「4時半」→ 04:30 → 16:30）。
- 止める語は design §18-4 の 1 の一覧どおり。NFKC の後、大文字小文字を区別せずに文の中の部分一致で見る。
- `intent.model_copy(update={"event": ...})` で `Intent` の検査が飛ぶことが問題になれば止める（`Intent` に model_validator があれば、event の型を変えないので通るはず。違えば `NEEDS_DECISION:`）。
- 今の試験が `afternoon_hours` で落ちたら、試験は直さず止めて `NEEDS_DECISION:`（落ちた試験名と生の出力を付ける）。

## 4. 試験（足す）

backend `backend/tests/test_secretary_dates.py`（今の書き方に合わせる・`afternoon_hours` の表）:
- 「明日4時に打ち合わせ」・start `2026-11-26T04:00:00+09:00`・end `2026-11-26T05:00:00+09:00` → 16:00・17:00。
- 「明日1時から2時」・01:00/02:00 → 13:00/14:00。
- 「あさって4時半」・04:30 → 16:30。
- 「4時から1時間」・start 04:00・end null → start 16:00・end null。
- 「4時から1時間」・start 04:00・end 05:00 → 16:00・17:00（5 は集まりに無いが、終わり < 新しい始まりで足す）。
- そのまま（変わらない）: 「午前4時」「朝6時」「夜1時」「深夜2時」「4am」「午後4時」で AI が 04:00 等 → 変わらない。「10時」10:00・「12時」12:00・「7時」07:00 → 変わらない。「1時間にして」で end 04:00 → 変わらない。終日 → 変わらない。時差の印なし `2026-11-26T04:00:00` → 変わらない。「4時」で AI が既に 16:00 → 変わらない。
- カルテの始まりが `2026-11-30T05:00:00+09:00` で「終わりは6時」・end 06:00 → 変わらない。カルテの始まりが 15:00 で「終わりは5時」・end 05:00 → 17:00。
- 全角「４時」→ 16:00。

backend `backend/tests/test_assistant_karte.py`（今の口の試験の書き方に合わせる・偽の AI）:
- 新しい頼み（karte null）・文「明日4時に打ち合わせ」・偽の AI が start 04:00・end 05:00（+09:00）→ 下書きの start 16:00・end 17:00。
- 直す道・カルテ 11/30 15:00〜16:00（+09:00）・文「はい、終わりは5時にして」・偽の AI が end `2026-11-30T05:00:00+09:00` だけ → end 17:00・`edited` 真・`edit_dropped` 偽。
- 直す道・カルテ 11/30 15:00〜16:00・文「終わりを朝5時にして」・偽の AI が end 05:00 → 決まりは当たらず、終わり < 始まりで戻る → start/end はカルテのまま・`edited` 偽・`edit_dropped` 真。
- 直す道・偽の AI が unknown → `edited` 偽・`edit_dropped` 偽。
- カルテがあって `edit` が偽 → `edit_dropped` null。
- 古い画面の道（karte の鍵なし）・文「明日4時に打ち合わせ」・偽の AI 04:00 → start 16:00。
- 今の `test_assistant_karte.py` の試験（`:541` の「4時に変えて 説明 明日」を含む）がそのまま通る。

frontend `frontend/src/features/secretary/SecretaryChat.test.tsx`（今の書き方に合わせる）:
- 「はい、終わりは5時にして」→ 偽の API が `edited: false`・`edit_dropped: true` → POST /calendar/events は呼ばれない・`notEdited` を読む・続けて「はい」で POST が 1 回（確かめ待ちが続いている）。
- 「はい、お願いします」→ 偽の API が `edited: false`・`edit_dropped: false` → 前の下書きで POST が 1 回（今の試験がそのまま通ればよい）。
- 直す頼み（はい なし）で `edit_dropped: true` → 今の else と同じ（`notEdited`）。

## 5. 確かめ（push の前に全部）

- `cd backend && pytest tests/test_secretary_dates.py tests/test_assistant_karte.py tests/test_assistant_router.py -q`（全部緑）
- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` の後の `git diff --stat frontend/api-contract/openapi.json` と `git diff frontend/api-contract/openapi.json` を結果に貼る。差が `EventDraft.edit_dropped` 以外に及べば止めて `NEEDS_DECISION:`。
- `cd frontend && npx vitest run src/features/secretary`（全部緑）・`npx tsc --noEmit`・`npx eslint src/features/secretary`
- `cd frontend && node scripts/check-i18n-missing-keys.js`（合格）
- 生の出力は全部ファイルに残し、最後の返事に結果の行（合格の数・失敗の数）をそのまま書く。

## 6. 進め方

（１）`git fetch origin && bash scripts/new-worktree.sh release/secretary-voice-w3-ask-pm --claude` で作業場所を作る（枝はもう origin にある。無ければ止める）。
（２）§2 の点検 → 試験を先に足して落ちることを確かめる → 実装 → §5 → commit（`fix(secretary): afternoon for bare 1-6 o'clock and no create on dropped edit (ADR-1082 bin W3)`）→ `git push origin release/secretary-voice-w3-ask-pm`。
（３）PR は作らない（Opus が作る）。最後の返事は `DONE:` か `BLOCKED:` か `NEEDS_DECISION:` で始める。
