# 作業指示書（便 V）— 秘書チャットの「声で会話」（交代で話す型）

- 設計: `docs/handoff/secretary-voice-input/design.md` §15 ／ 目標: `docs/handoff/secretary-voice-input/kgi.md` §5（V1〜V6・PO 承認 2026-11-24「1」）
- 状態: 作業指示書の案（実装は PO の実装承認があってから。この紙だけで始めない）
- 実行役: クラウドの Sonnet。作業場所は `bash scripts/new-worktree.sh release/secretary-voice-mode --claude`。始める前に `./scripts/dev/executor-preflight.sh || exit 1`。
- 規則: `docs/ai-agents/executor-checklist.md`。UI の文字は全部 `t()`（ADR-027）・金型だけ（ADR-144）・色や寸法の直値なし（ADR-067）。

## 1. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `frontend/src/features/secretary/SecretaryChat.tsx` | §3 |
| `frontend/src/features/secretary/SecretaryDraftEvent.tsx` | §4 |
| `frontend/src/features/secretary/secretaryVoiceAnswer.ts`（新） | §5 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | §6 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | §7 |
| `frontend/src/features/secretary/secretaryVoiceAnswer.test.ts`（新） | §7 |

触らない: `useSecretaryListen.ts`・`useSecretaryVoice.ts`・`secretaryApi.ts`・`SecretaryDraftInvoice.tsx`・backend・migrations・deploy.yml・`secretary-codex/`・`secretary-agent/`・`frontend/eslint.config.js`。

## 2. 実物の点検（始める前に。違ったら止めて BLOCKED: で返す）

（１）`SecretaryChat.tsx` の `onVoiceChange`（今は 101-110 行）・`send`（120-172 行）・`markCreated`/`markCancelled`（174-179 行）・`<SecretaryDraftEvent`（221 行）が、この紙の説明どおりにある。
（２）`useSecretaryListen` が `listening`・`interim`・`start`・`stop`・`abort` を返す（`useSecretaryListen.ts` 91-93 行の型）。
（３）`useSecretaryVoice().speak` が `"ok" | "failed" | "cap"` を返し、読み終わってから解決する。
（４）`ja.json`/`en.json` の 6325 行に `secretary.voiceToggle` がある。

## 3. SecretaryChat.tsx

（１）定数 `const VOICE_SEND_SILENCE_MS = 1000;` を部品の外に 1 つ置く（ほかで同じ数を書かない）。
（２）`onVoiceChange(true)` のとき、今の `voice.enable()` のあとで `listen.start()` を呼ぶ（同じ押した処理の中）。`false` のときは今の処理に `listen.abort()` と `pendingConfirm` を外す処理を足す。
（３）自動で送る: `useEffect` で、`voiceOn && listen.listening && text.trim() !== "" && listen.interim === "" && !sending` のときだけ `setTimeout(() => void send(), VOICE_SEND_SILENCE_MS)` を張る。依存は `[voiceOn, listen.listening, listen.interim, text, sending]`。片付けで `clearTimeout`。声で会話が切れているときは何もしない（今と同じ）。
（４）`speakThenListen(id, spoken, sentIn)` を作る: `const r = await voice.speak(spoken)`。`r !== "ok"` なら今の `setVoiceNote({id, kind: r})` と、声で会話を切る（`onVoiceChange(false)` と同じ処理）。`r === "ok"` かつ `voiceOnRef.current` かつ `sentIn === session.current` なら `listen.start()`。
（５）`send()` の中の読み上げを、声で会話の間は `speakThenListen` に替える。読む文は §15-6 の表のとおり:
- 聞き返し: `reply.draft.reply`（今のまま）。
- `ask` あり: `t(\`secretary.ask.${ask}\`)`（今のまま）。
- 予定の最後の下書き: `t("secretary.voiceMode.confirmEvent", { title, when })`。`when` は `draft.is_all_day` なら `t("secretary.voiceMode.whenAllDay", { date })`、違えば `t("secretary.voiceMode.when", { date, time })`。`date`・`time` は `draft.start` から、画面で今使っている日付の書式の関数で作る（新しい書式を作らない。見つからなければ止めて NEEDS_DECISION:）。あわせて `pendingConfirm = { id: pendingId, tries: 0 }`。
- 請求書: `t("secretary.voiceMode.invoiceReady")` だけ。会社名・金額・品名を文に入れない。
- 失敗（catch の中・`forbidden` 以外）: 声で会話の間だけ `t(\`secretary.error.${kind}\`)` を読む。
（６）確かめ待ちの答え: `send()` の頭で、声で会話かつ `pendingConfirm` があるときは、`sendSecretaryMessage` を呼ばない。利用者の吹き出しは今と同じに足し、`judgeYesNo(trimmed, yesWords, noWords)`（§5）で分ける。動きと読む文は design.md §15-5 の表のとおり。「はい」は `eventRefs.current.get(pendingConfirm.id)?.submitByVoice()` を呼び、`false` が返ったら `checkScreen` を読む。考え中の吹き出しは出さない。
（７）`markCreated`・`markCancelled` の中で `pendingConfirm` を外す。`close()` でも外す。
（８）`eventRefs = useRef(new Map<number, SecretaryDraftEventHandle>())`。221 行の `<SecretaryDraftEvent` に `ref={(h) => { if (h) eventRefs.current.set(m.id, h); else eventRefs.current.delete(m.id); }}` を渡す。
（９）変えない: 送るボタンの `disabled`（304 行）・マイクの印・欄の `maxLength`・`close()` のほかの処理・`markCreated` の今の読み上げ。

## 4. SecretaryDraftEvent.tsx

（１）`export interface SecretaryDraftEventHandle { submitByVoice(): boolean }` を足す。
（２）部品を `forwardRef<SecretaryDraftEventHandle, Props>` にする。`useImperativeHandle(ref, () => ({ submitByVoice: () => { if (!canCreate || saving) return false; void submit(); return true; } }), [canCreate, saving, submit])`。`submit` は今の 1 つだけを使う（写しを作らない）。
（３）見た目・ボタン・`submit()` の中身は変えない。

## 5. secretaryVoiceAnswer.ts（新）

```ts
export type YesNo = "yes" | "no" | "unknown";
/** 否定を先に見る。語の一覧は翻訳キー secretary.voiceMode.yesWords / noWords（| 区切り）から渡す */
export function judgeYesNo(text: string, yesWords: string[], noWords: string[]): YesNo
```
- 比べる前に `text` を NFKC にし、英字は小文字にする。語も同じにする。
- `noWords` のどれかを含めば `"no"`。含まず `yesWords` のどれかを含めば `"yes"`。どちらも無ければ `"unknown"`。空の語は無視する。
- 日本語の直書きを書かない（語は呼ぶ側が `t()` で読んで `split("|")` して渡す）。

## 6. 翻訳（ja と en で同じキー・同じ数）

| キー | ja | en |
|---|---|---|
| `secretary.voiceToggle`（変える） | 声で会話 | Voice conversation |
| `secretary.voiceMode.confirmEvent` | {{title}}を{{when}}に入れますか？ | Add {{title}} on {{when}}? |
| `secretary.voiceMode.when` | {{date}} {{time}} | {{date}} at {{time}} |
| `secretary.voiceMode.whenAllDay` | {{date}}の終日 | {{date}}, all day |
| `secretary.voiceMode.invoiceReady` | 請求書の下書きを出しました。画面で中身を確かめて、作るボタンを押してください。 | The invoice draft is ready. Check it on screen and press the create button. |
| `secretary.voiceMode.notCreated` | 入れませんでした。 | I did not add it. |
| `secretary.voiceMode.askAgain` | はい、か、いいえで答えてください。 | Please answer yes or no. |
| `secretary.voiceMode.checkScreen` | 画面で確かめて、作るボタンを押してください。 | Please check the screen and press the create button. |
| `secretary.voiceMode.yesWords` | はい\|うん\|ええ\|お願い\|入れて\|作って\|オッケー\|ok | yes\|yeah\|ok\|okay\|sure\|please |
| `secretary.voiceMode.noWords` | いいえ\|いや\|違う\|やめ\|キャンセル\|入れないで\|作らないで\|だめ\|ダメ | no\|nope\|cancel\|stop\|don't |

- 差し込みの書き方は、今の ja.json の別のキーで使っている形に合わせる（`{{ }}` でなければ今の形にする）。

## 7. 試験（CI で回す。Mac では回さない）

`secretaryVoiceAnswer.test.ts`（日本語は今の試験と同じく `String.fromCharCode` か翻訳の値から作る）:
- 「はい」→yes・「いいえ」→no・「はい、いや違う」→no・「えーと」→unknown・「ＯＫ」（全角）→yes・空の語は無視。

`SecretaryChat.test.tsx`（今の試験の聞き取り・読み上げの偽物を使う）:
- T1 声で会話を入れると `start` が 1 回呼ばれる。
- T2 声で会話の間、確定した文があり途中の文字が空のまま 1000ms で送られる（偽の時計）。999ms では送られない。途中の文字があると送られない。
- T3 声で会話が切れているときは、1000ms たっても送られない。
- T4 返事を読み終わる（`speak` が ok）と `start` がもう 1 回呼ばれる。`failed` のときは呼ばれず、知らせが出て、声で会話が切れる。
- T5 予定の最後の下書きで `confirmEvent` を読む。次に「はい」で POST `/calendar/events` が 1 回。`sendSecretaryMessage` は 2 回目を呼ばない。
- T6 「いいえ」で POST 0 回・`notCreated` を読む。
- T7 分からない 2 回で POST 0 回・`askAgain` → `checkScreen` の順に読む。
- T8 請求書の下書きで `invoiceReady` を読む。「はい」と言っても請求書の POST は 0 回（確かめ待ちにならない）。読んだ文に会社名・金額が入っていない。
- T9 窓を閉じると確かめ待ちが外れる（もう一度開いて「はい」でも POST 0 回）。

## 8. 合格（PR を出す前に自分で確かめる）

- 上の試験が CI で全部通る。`ja.json`/`en.json` のキー数が同じ。`local/no-japanese-literal` の違反 0 件。
- `git diff origin/main --name-only` が §1 の 7 ファイルだけ。
- PR は `--base main`・本文に `### 標準ワークフロー確認`。変更規模は大。

## 9. 想定の分かれ道（起きたら止めて返す）

- 日付の書式の関数が見つからない → NEEDS_DECISION:（新しく作らない）。
- `forwardRef` にすると今の試験が落ちる → 原因の生出力をつけて BLOCKED:。
- 差し込みの書き方が `{{ }}` と違う → 今の形に合わせて進める（止めない）。
- 1000ms で試験が不安定 → 偽の時計の使い方を直す。定数は変えない。

## 10. 戻し方

この PR の merge commit を revert する。DB・設定の変更なし。
