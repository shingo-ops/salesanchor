# 作業指示書（便 W2）— 声で直す便の気をつける点 3 つ

- 設計: `docs/handoff/secretary-voice-input/design.md` §17（必ず全部読む。§16 は前の便）／ 事実: `docs/handoff/secretary-voice-input/recon.md` §10 ／ 目標: `docs/handoff/secretary-voice-input/kgi.md` §7 X1〜X6
- 状態: PO の実装承認あり（2026-11-25 チャット「3」= 目視 2 つと、気をつける点 3 つを直す設計を両方。前の指示「PRマージ、デプロイまで完走させてくれ」）
- 実行役: クラウドの Sonnet。枝 `release/secretary-voice-edit-followup`（設計の commit が載った枝）。始める前に `./scripts/dev/executor-preflight.sh || exit 1`。
- 規則: `docs/ai-agents/executor-checklist.md`・ADR-027（文字は `t()`・ja/en 同じ鍵）・ADR-144/ADR-067（新しい部品・色・大きさを作らない）。

## 1. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `backend/app/schemas/assistant.py` | design §17-4 の 1 |
| `backend/app/services/secretary_dates.py` | §17-4 の 2（`same_day` を足すだけ） |
| `backend/app/routers/assistant.py` | §17-4 の 3 |
| `frontend/api-contract/openapi.json` | §17-4 の 4（命令で書き出し直す。手で書かない） |
| `backend/tests/test_assistant_karte.py` | §4 |
| `frontend/src/features/secretary/secretaryVoiceAnswer.ts` | §17-5 の 1 |
| `frontend/src/features/secretary/secretaryVoiceAnswer.test.ts` | §4 |
| `frontend/src/features/secretary/secretaryApi.ts` | §17-5 の 2 |
| `frontend/src/features/secretary/SecretaryChat.tsx` | §17-5 の 3 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | §4 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | §17-5 の 4 |

触らない: `secretary-agent/` の全部・`backend/app/services/secretary_karte.py`・`frontend/src/features/secretary/SecretaryDraftEvent.tsx`・migrations・deploy.yml・`docs/`（Opus が書く）。

## 2. 実物の点検（始める前に。違ったら止めて `BLOCKED:` で返す）

（１）`backend/app/routers/assistant.py:336-343` が `if edit_mode:` → `ai_ev = intent.event if intent.kind == "event" else None` → `same_time(ai_ev.start, karte.start)` の条件で `apply_day(ai_ev, body.text, now.date(), None)` → `merge_edit(ai_ev, karte)`。`:334` が `edited = False`。`:434` が `edited=edited if edit_mode else None,`。
（２）`backend/app/services/secretary_dates.py:163-173` に `_day_of`、`:201` に `apply_day`。
（３）`frontend/src/features/secretary/secretaryVoiceAnswer.ts:60-66` の `judgeYesNo` が no → yes（文の頭）→ unknown の順。
（４）`frontend/src/features/secretary/SecretaryChat.tsx:169` の `startConfirm` の `key` が `"confirmEvent" | "editedConfirm"`。`:192` が `const sendEdit = async (confirm: { id: number; tries: number }, trimmed: string) => {`。`:276-286` が yes / no / それ以外の分かれ。
（５）`judgeYesNo` を呼ぶのは `SecretaryChat.tsx` だけ（`git grep -n judgeYesNo frontend/src` が `secretaryVoiceAnswer.ts`・その試験・`SecretaryChat.tsx` だけ）。

## 3. 想定される分かれ（迷ったら止めて `NEEDS_DECISION:`）

- はい の語を取り除くとき、英字の語も句読点・空白を除いた形で取り除いてよい（文の頭の判定は今の `matchesAtStart` のまま。取り除くのは判定が yes になった後だけ）。
- 日付の表の条件は `same_time` と `same_day` の両方（design §17-4 の 3）。`same_time` の import は残す。
- `meet_refused` と `edited` が両方真のとき（場所と Meet を一緒に言った）は §17-5 3（１）の `editedMeetUnavailable`。
- 試験の中の日本語の文は、今の `secretaryVoiceAnswer.test.ts` と同じく `String.fromCharCode` か ja.json から作る（試験に日本語を直書きしてよいかは今の試験ファイルの書き方に合わせる。`SecretaryChat.test.tsx` が直書きしていればそれに合わせる）。

## 4. 試験（足す・直す）

backend（`backend/tests/test_assistant_karte.py`・今の試験の書き方に合わせる）:
- `same_day`: 同じ日の別の時刻→真／違う日→偽／片方 null→偽／時差の印が +09:00 でない→偽。
- 口: `edit: true`・カルテの始まり `2026-11-10T02:00:00+01:00`・偽の AI は同じ瞬間の `2026-11-10T10:00:00+09:00` と description「明日」を返す・文「説明に明日と入れて」→ start は カルテのまま（日付が動かない）（審査 R1）。
- 口: `edit: true`・カルテの始まり 2026-11-30 15:00・文「4時に変えて 説明 明日」・偽の AI は start 2026-11-30 16:00 と description「明日」を返す → start は 11/30 16:00・end 11/30 17:00（日付が動かない）・`edited` 真。
- 口: `meet_available` 偽で `edit: true`・偽の AI が add_meet true だけを返す → `edited` 偽・`meet_refused` 真・add_meet null。
- 口: `meet_available` 偽で、偽の AI が location と add_meet true を返す → `edited` 真・`meet_refused` 真・location が入る。
- 口: `meet_available` 真で、偽の AI が add_meet true を返す → `edited` 真・`meet_refused` 偽・add_meet 真。
- 口: カルテがあって `edit` が偽（付けない）→ `edited` null・`meet_refused` null（便W の審査役の指摘）。
- 今の `test_edit_same_start_does_not_move_date_by_description_words`・`test_edit_changed_start_gets_day_table` がそのまま通る。

frontend `secretaryVoiceAnswer.test.ts`:
- 「はい」「はい、入れて」「はいはい」「Yes, please.」「ok ok」→ yes。「はい、場所は渋谷にして」「はい、お願いします」「yes, at four」→ yesMore。今の試験はそのまま通る。

frontend `SecretaryChat.test.tsx`:
- 「はい、場所は渋谷にして」→ 偽の API が `edited: true`・location「渋谷」→ POST /calendar/events は呼ばれない・`editedConfirm` を読む → 「はい」で POST の本文の location が「渋谷」・POST は 1 回。
- 「はい、お願いします」→ 偽の API が `edited: false` → 前の下書きで POST が 1 回。
- 「はい」だけ → 秘書の API は呼ばれない・POST が 1 回（今の T5 がそのまま通ればよい）。
- `meet_refused: true`・`edited: false` → `meetUnavailable` を読む・POST は呼ばれない・続けて「はい」で POST が 1 回（確かめ待ちが続いている）。
- `meet_refused: true`・`edited: false` の後に、直らない文 2 回 → 1 回目 `notEdited`・2 回目 `checkScreen`（Meet の答えで回数が増えていない）。
- `meet_refused: true`・`edited: true` → `editedMeetUnavailable` を読む。
- 「はい、Meet も付けて」→ 偽の API が `meet_refused: true`・`edited: false` → POST は呼ばれない・`meetUnavailable` を読む（はいと直しでも作らない）。
- 「はい、お願いします」で偽の API が 500 → 失敗の文・POST は呼ばれない・前の下書きはボタンで作れる。

## 5. 確かめ（push の前に全部）

- `cd backend && pytest tests/test_assistant_karte.py tests/test_assistant_router.py -q`（全部緑）
- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` の後の `git diff --stat frontend/api-contract/openapi.json` を結果の行に貼る。差が `EventDraft.meet_refused` 以外に及べば止めて `NEEDS_DECISION:`。
- `cd frontend && npx vitest run src/features/secretary`（全部緑）・`npx tsc --noEmit`・`npx eslint src/features/secretary`
- `cd frontend && node scripts/check-i18n-missing-keys.js` と `node scripts/check-error-text-next-action.js`（両方とも合格）。ja と en の鍵が同じ。
- 生の出力は全部ファイルに残し、最後の返事に結果の行（合格の数・失敗の数）をそのまま書く。

## 6. 進め方

（１）`git fetch origin && bash scripts/new-worktree.sh release/secretary-voice-edit-followup --claude` で作業場所を作る（枝はもう origin にある。無ければ止める）。
（２）§2 の点検 → 試験を先に足して落ちることを確かめる → 実装 → §5 → commit（`fix(secretary): voice edit follow-ups (ADR-1082 bin W2)`）→ `git push origin release/secretary-voice-edit-followup`。
（３）PR は作らない（Opus が作る）。最後の返事は `DONE:` か `BLOCKED:` か `NEEDS_DECISION:` で始める。
