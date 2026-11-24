# 作業指示書（便 W）— 声で予定の下書きを直す

- 設計: `docs/handoff/secretary-voice-input/design.md` §16（必ず全部読む）／ 事実: `recon.md` §9 ／ 目標: `kgi.md` §6 W1〜W6
- 状態: PO の実装承認あり（2026-11-25 チャット「2」= 声で下書きを直す を設計し「PRマージ、デプロイまで完走させてくれ」）
- 実行役: クラウドの Sonnet。枝 `release/secretary-voice-draft-edit`（設計の commit が載った枝。§6）。始める前に `./scripts/dev/executor-preflight.sh || exit 1`。
- 規則: `docs/ai-agents/executor-checklist.md`・ADR-027（文字は `t()`・ja/en 同じ鍵）・ADR-144/ADR-067（新しい部品・色・大きさを作らない）。

## 1. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `backend/app/schemas/assistant.py` | design §16-4 の 1 |
| `backend/app/services/secretary_karte.py` | §16-4 の 2（`merge_edit` を足す。`merge_karte`・`settle_dates`・`next_ask` は変えない） |
| `backend/app/routers/assistant.py` | §16-4 の 3・4（`_agent_payload` は変えない） |
| `frontend/api-contract/openapi.json` | §16-4 の 6（命令で書き出し直す。手で書かない） |
| `backend/tests/test_assistant_karte.py` | §4 |
| `secretary-agent/prompt.txt` | §16-5 の 1 行を `:14` の後に（文は design のとおり一字も変えない） |
| `frontend/src/features/secretary/secretaryApi.ts` | §16-6 の 1 |
| `frontend/src/features/secretary/SecretaryDraftEvent.tsx` | §16-6 の 2 と 3 の `onSaving` |
| `frontend/src/features/secretary/SecretaryChat.tsx` | §16-6 の 3 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx`・`SecretaryDraftEvent.test.tsx`（あれば） | §4 |
| `frontend/src/locales/ja.json`・`en.json` | §16-6 の 4 |

触らない: `secretary-agent/compose.mjs`・`secretaryVoiceAnswer.ts`・`useSecretaryVoice.ts`・`useSecretaryListen.ts`・migrations・deploy.yml・`docs/`（Opus が書く）。

## 2. 実物の点検（始める前に。違ったら止めて `BLOCKED:` で返す）

（１）`frontend/src/features/secretary/SecretaryChat.tsx:186-192` が `} else if (confirm.tries === 0) {` から始まり `askAgain` を読む分かれ道。
（２）同じファイル `:225-245` に `pendingConfirmRef.current = { id: pendingId, tries: 0 };` と `confirmEvent` を読む行がある。
（３）`frontend/src/features/secretary/SecretaryDraftEvent.tsx:31-34` の口は `submitByVoice(): boolean` だけ。`:51` が `useState<"personal" | "shared">(draft.calendar_type)`。
（４）`backend/app/schemas/assistant.py` の `KarteIn` に `extra="forbid"` があり、`asked_count` が最後の欄。
（５）`backend/app/routers/assistant.py:331-348` に `if new_path:` → `merge_karte(None, karte)`・`merge_karte(intent.event, karte)`・`apply_day(...)`・`settle_dates(...)` がある。`:395-411` に `next_ask(...)` と `EventDraft(...)`。
（６）`secretary-agent/prompt.txt` が 18 行で、`:14` が短い答えを直前に聞いた欄として読む決まり。
（７）`askAgain` を使うのは `SecretaryChat.tsx:188` と `SecretaryChat.test.tsx` の T7 だけ（`git grep -n askAgain frontend/src`）。

## 3. 想定される分かれ（迷ったら止めて `NEEDS_DECISION:`）

- 終日の下書きのカルテの始まり・終わりの書き方: 今の backend が終日の下書きで返す start/end の形（`settle_dates`・`apply_day` の実物）に合わせる。合わせ方が分からなければ止める。
- `merge_edit` で長さを保つ計算は `datetime.fromisoformat` で読み、時差の印のあるものどうしだけ計算する。印の無いものが混ざればカルテの終わりのまま。
- `edit` が真なのに `karte` の `asked` が null でない形は来ない（画面が null で送る）。来ても `asked` は無視する。
- 画面で、直した答えが「まだ聞く欄がある」（`ask` が null でない）は直す道では起きない（backend が `ask=None`）。起きたら `edited` が偽と同じに扱う。

## 4. 試験（足す・直す）

backend（`backend/tests/test_assistant_karte.py`・今の試験の書き方に合わせる）:
- `merge_edit`: 説明だけ（AI の description が勝つ・ほかはカルテ・変わった真）／題名を替える（カルテの題名があっても AI が勝つ）／始まりだけ（長さ 1 時間を保つ）／始まりと終わり両方／AI が null だけ（変わった偽）／AI の値が空白だけ（カルテのまま）／終日のカルテで AI が時刻を返す（時刻は替えない）／同じ時刻を別の書き方（変わった偽）／ev が None。
- `merge_edit` に足す: 空白つきの同じ文字（変わった偽）／カルテの終わりが始まりより前（長さを足さない）／時差の印が混ざる始まり（文字で比べる）。
- 口: `edit: true` で AI が**請求書**を返す→ event・`edited` 偽・中身はカルテ・`resolve_names` が呼ばれない／`edit: true` で「終わりを始まりより前に」の答え→ カルテのまま・`edited` 偽。
- 口（審査第 2 回 R1）: `edit: true`・カルテの始まりは明日でない日・文「説明に明日までに資料を持参と入れて」・偽の AI は description と**カルテと同じ start** を返す→ start・end はカルテのまま・description だけ変わる・`edited` 真。逆向き: 偽の AI が start を 3 日後で返し文「来週の月曜にして」→ `apply_day` で来週の月曜になる。
- 口（今の karte 試験と同じ偽の AI の答え）: `edit: true` で AI が description を返す→ event・`edited` 真・`ask` null・ほかの欄はカルテ／AI が unknown を返す→ event・`edited` 偽・中身はカルテ／`edit` を付けない今の試験がそのまま通る／`edit` 無しの答えでは `edited` が null。

frontend:
- T7 を書き直す（`mockResolvedValueOnce` で `edited: false` の返しを 2 回足す）: はい／いいえでない文が 2 回とも直らない（偽の API が `edited: false`）→ 1 回目 `notEdited`、2 回目 `checkScreen`、予定は作られない。
- 足す: 直せた後の新しい下書きで、はい／いいえでない文が直らない → 1 回目は `notEdited`（回数は 0 から数え直し）。
- 足す: 直す頼みの API を保留にしたまま「作る」を押し、作成の API も保留のまま直す答えを返す → 前の吹き出しは替わらない・新しい下書きは出ない（`onSaving`）。
- 足す: 「説明にテストと入れて」→ 偽の API が `edited: true`・description「テスト」の下書き → 前の下書きが `edit.replaced` の文になる・新しい下書きの説明欄が「テスト」・`editedConfirm` を読む → 「はい」で POST /calendar/events の本文の description が「テスト」。
- 足す: 送った本文の `karte` が今の欄の値（手で直した題名を含む）と `edit: true`・`asked: null`・`asked_count: 0`。
- 足す: 画面で「共有」を選んだ下書きを声で直すと、新しい下書きも「共有」のまま。
- 足す: 直す頼みの API を保留にしたまま前の下書きの「作る」を押す → API を返す → 吹き出しは「作りました」のまま・新しい下書きは出ない・POST /calendar/events は 1 回。
- 足す: 直す頼みが失敗（偽の API が 500）→ 失敗の文が出る・前の下書きは残り、ボタンで作れる。

## 5. 確かめ（push の前に全部）

- `cd backend && pytest tests/test_assistant_karte.py tests/test_assistant_router.py -q`（全部緑）
- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` の後の `git diff --stat frontend/api-contract/openapi.json` を結果の行に貼る。差が `KarteIn.edit`・`EventDraft.edited` 以外に及べば止めて `NEEDS_DECISION:`。
- `cd frontend && npx vitest run src/features/secretary`（全部緑）・`npx tsc --noEmit`・`npx eslint src/features/secretary`
- `cd frontend && node scripts/check-i18n-missing-keys.js` と `node scripts/check-error-text-next-action.js`（両方とも合格）。ja と en の鍵が同じ。`askAgain` が両方から消えている（`git grep -n askAgain frontend/src` が 0 件）。
- 生の出力は全部ファイルに残し、最後の返事に結果の行（合格の数・失敗の数）をそのまま書く。

## 6. 進め方

（１）`git fetch origin && bash scripts/new-worktree.sh release/secretary-voice-draft-edit --claude` で作業場所を作る（枝はもう origin にある。無ければ止める）。
（２）§2 の点検 → 実装 → §5 → commit（`feat(secretary): edit event draft by voice (ADR-1082 bin W)`）→ `git push origin release/secretary-voice-draft-edit`。
（３）PR は作らない（Opus が作る）。最後の返事は `DONE:` か `BLOCKED:` か `NEEDS_DECISION:` で始める。
