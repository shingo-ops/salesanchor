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
（２）`useSecretaryListen` が `listening`・`interim`・`start`・`stop`・`abort` を返す（`frontend/src/features/secretary/useSecretaryListen.ts:89-97` の型・start/stop/abort は `:94-96`）。
（３）`useSecretaryVoice().speak` が `"ok" | "failed" | "cap"` を返し、読み終わってから解決する。
（４）`ja.json`/`en.json` の 6325 行に `secretary.voiceToggle` がある。
（５）`frontend/src/pages/schedule/schedule-utils.ts:119` に `formatDraftDateLine`、`:161` に `formatDateInput`、`:177` に `formatTimeInput` がある。

## 3. SecretaryChat.tsx

（１）定数 `const VOICE_SEND_SILENCE_MS = 1000;` を部品の外に 1 つ置く（ほかで同じ数を書かない）。
（２）`onVoiceChange(true)` のとき、今の `voice.enable()` のあとで `listen.start()` を呼ぶ（同じ押した処理の中）。`false` のときは今の処理に `listen.abort()` と `pendingConfirm` を外す処理を足す。
（３）自動で送る: `heardRef = useRef(false)` を足し、聞き取りの callback（今の 67-79 行）で文を足したら `true`、`send()` の頭と `onVoiceChange` で `false` にする。`sendRef = useRef(send); sendRef.current = send;` を毎回の描画で入れる。`useEffect` で、`voiceOn && listen.listening && heardRef.current && text.trim() !== "" && listen.interim === "" && !sending` のときだけ `setTimeout(() => void sendRef.current(), VOICE_SEND_SILENCE_MS)` を張る。依存は `[voiceOn, listen.listening, listen.interim, text, sending]`（`sendRef` を使うので `send` は依存に入れない。書き方の検査 `react-hooks/exhaustive-deps` の警告 0 件にする）。片付けで `clearTimeout`。声で会話が切れているときは何もしない（今と同じ）。
（４）回数の印 `turnRef = useRef(0)` を足す。`send()` の頭・`onVoiceChange`・`close()` で 1 進める。`speakThenListen(id, spoken)` を作る: **最初に `listen.abort()` を呼び、`heardRef.current = false` にする**（マイクが開いたままボタンで作ったときなどに、秘書の声を拾わないため・審査 N1・`frontend/src/features/secretary/useSecretaryListen.ts:173` はすでに聞いているときの `start()` で何もしない）。次に `const turn = ++turnRef.current` で印を 1 つ進めて覚える（読み上げの途中で別の読み上げ（作るボタンの知らせ等）が始まったとき、古い方の終わりでマイクを開かないため・審査 N2。`frontend/src/features/secretary/useSecretaryVoice.ts:64` の `speak` は頭で前の読み上げを止め、前の方は `"ok"` を返す）。`const r = await voice.speak(spoken)`。`r !== "ok"` なら今の `setVoiceNote({id, kind: r})` と、声で会話を切る（`onVoiceChange(false)` と同じ処理）。`r === "ok"` かつ `voiceOnRef.current` かつ `turn === turnRef.current` なら `listen.start()`（読み上げを途中で止めても `speak` は "ok" を返すため・`frontend/src/features/secretary/useSecretaryVoice.ts:84`・`:96`・`:100`。印が違えばマイクを開かない）。
（５）`send()` の中の読み上げを、声で会話の間は `speakThenListen` に替える。読む文は §15-6 の表のとおり:
- 聞き返し: `reply.draft.reply`（今のまま）。
- `ask` あり: `t(\`secretary.ask.${ask}\`)`（今のまま）。
- 予定の最後の下書き: `draft.title`・`draft.start`・`draft.end` のどれかが空なら、確かめ待ちにせず `checkScreen` を読む。空でなければ `t("secretary.voiceMode.confirmEvent", { title: draft.title, when })` を読み、`pendingConfirm = { id: pendingId, tries: 0 }`。`when` は `formatDraftDateLine({ startDate: formatDateInput(s), startTime: formatTimeInput(s), endDate: formatDateInput(e), endTime: formatTimeInput(e), allDay: draft.is_all_day }, t, i18n.language)`（`s = new Date(draft.start)`・`e = new Date(draft.end)`）。`i18n` は `frontend/src/features/secretary/SecretaryChat.tsx:51` の `useTranslation()` から `const { t, i18n }` で取り出す。新しい書式は作らない。
- 請求書: `t("secretary.voiceMode.invoiceReady")` だけ。会社名・金額・品名を文に入れない。
- 失敗（catch の中・`forbidden` 以外）: 声で会話の間だけ `t(\`secretary.error.${kind}\`)` を読む。
（６）確かめ待ちの答え: `send()` の中で、今の `voice.stop()`・`listen.abort()`（123-124 行）の**後に**置き、声で会話かつ `pendingConfirm` があるときは、`sendSecretaryMessage` を呼ばない。利用者の吹き出しは今と同じに足し、`judgeYesNo(trimmed, yesWords, noWords)`（§5）で分ける。動き・読む文・また聞くかは design.md §15-5 の表のとおり。**表の読む文はすべて `speakThenListen` で読む**（読み終わるとまた聞く）。「はい」は `eventRefs.current.get(pendingConfirm.id)?.submitByVoice()` を呼び、`false` か部品が無いときは確かめ待ちを外して `checkScreen` を読む。考え中の吹き出しは出さない。
（７）`markCreated`・`markCancelled` の中で `pendingConfirm` を外す。`close()` でも外す。`markCreated` の読み上げは、声で会話の間は `speakThenListen` にする（作った後も会話を続けるため）。`<SecretaryDraftEvent` に `onVoiceFailed={() => { 確かめ待ちを外す; 声で会話なら speakThenListen(m.id, t("secretary.voiceMode.checkScreen")) }}` を渡す。
（８）`eventRefs = useRef(new Map<number, SecretaryDraftEventHandle>())`。221 行の `<SecretaryDraftEvent` に `ref={(h) => { if (h) eventRefs.current.set(m.id, h); else eventRefs.current.delete(m.id); }}` を渡す。
（９）変えない: 送るボタンの `disabled`（304 行）・マイクの印・欄の `maxLength`・`close()` のほかの処理・声で会話が切れているときの `markCreated` の読み上げ（今の `speakFor`）。

## 4. SecretaryDraftEvent.tsx

（１）`export interface SecretaryDraftEventHandle { submitByVoice(): boolean }` を足す。
（２）部品を `forwardRef<SecretaryDraftEventHandle, Props>` にする。`submitRef = useRef(submit); submitRef.current = submit;`・`canRef`（`canCreate && !saving`）も同じく毎回入れる。`useImperativeHandle(ref, () => ({ submitByVoice: () => { if (!canRef.current) return false; void submitRef.current(); return true; } }), [])`。`submit` は今の 1 つだけを使う（写しを作らない）。書き方の検査の警告 0 件。
（２-２）Props に `onVoiceFailed?: () => void` を足す。今の `submit()` の失敗の処理（70-72 行）の中で、今の表示はそのままにして `onVoiceFailed?.()` を呼ぶ。
（３）見た目・ボタン・`submit()` の中身は変えない。

## 5. secretaryVoiceAnswer.ts（新）

```ts
export type YesNo = "yes" | "no" | "unknown";
/** 否定を先に見る。語の一覧は翻訳キー secretary.voiceMode.yesWords / noWords（| 区切り）から渡す */
export function judgeYesNo(text: string, yesWords: string[], noWords: string[]): YesNo
```
- 比べる前に `text` と語を NFKC にし、英字は小文字にし、句読点・空白を除く形も作る。
- `noWords` のどれかに当たれば `"no"`（否定を先に見る）。当たらず、文の頭が `yesWords` のどれかで始まれば `"yes"`。どちらでもなければ `"unknown"`。空の語は無視する。
- 英字だけの語（yes・no・ok 等）は、句読点と空白を除く前の形（NFKC・小文字だけにした形）で単語の区切りで比べる（`/\b語\b/`）。"yes please" は yes、"look"・"know" には当てない。日本語の語は句読点と空白を除いた形で比べる。
- 日本語の直書きを書かない（語は呼ぶ側が `t()` で読んで `split("|")` して渡す）。

## 6. 翻訳（ja と en で同じキー・同じ数）

| キー | ja | en |
|---|---|---|
| `secretary.voiceToggle`（変える） | 声で会話 | Voice conversation |
| `secretary.voiceMode.confirmEvent` | {{title}}を{{when}}に入れますか？ | Add {{title}} on {{when}}? |
| `secretary.voiceMode.invoiceReady` | 請求書の下書きを出しました。画面で中身を確かめて、作るボタンを押してください。 | The invoice draft is ready. Check it on screen and press the create button. |
| `secretary.voiceMode.notCreated` | 入れませんでした。 | I did not add it. |
| `secretary.voiceMode.askAgain` | はい、か、いいえで答えてください。 | Please answer yes or no. |
| `secretary.voiceMode.checkScreen` | 画面で確かめて、作るボタンを押してください。 | Please check the screen and press the create button. |
| `secretary.voiceMode.yesWords` | はい\|うん\|お願い\|入れて\|作って\|オッケー\|ok | yes\|yeah\|ok\|okay\|sure\|please |
| `secretary.voiceMode.noWords` | いいえ\|いや\|違う\|やめ\|キャンセル\|入れないで\|作らないで\|だめ\|ダメ | no\|nope\|cancel\|stop\|don't |

- 差し込みは `{{ }}`（今の ja.json と同じ形・審査で確かめた）。

## 7. 試験（CI で回す。Mac では回さない）

`secretaryVoiceAnswer.test.ts`（日本語は今の試験と同じく `String.fromCharCode` か翻訳の値から作る）:
- 「はい」→yes・「いいえ」→no・「はい、いや違う」→no・「えーと」→unknown・「ええと」→unknown・「ＯＫ」（全角）→yes・"let me look"→unknown・"I know"→unknown・"Yes, please."→yes・空の語は無視。

`SecretaryChat.test.tsx`（今の偽物は 2 つの組に分かれている: 偽の AudioContext は「voice reply」の組（501-528 行付近）、偽の聞き取り FakeRec は「listen mark」の組（642-676 行付近）。T1〜T12 は両方を入れた新しい組で書く。試験は英語の画面で回るので、切り替えの名 `TOGGLE` は "Voice conversation" に直し、答えは en の語（yes・no）で言わせる）:
- T1 声で会話を入れると `start` が 1 回呼ばれる。
- T2 声で会話の間、聞き取った文があり途中の文字が空のまま 1000ms で送られる（偽の時計）。999ms では送られない。途中の文字があると送られない。手で打った文だけのときは送られない。
- T3 声で会話が切れているときは、1000ms たっても送られない。
- T4 返事を読み終わる（`speak` が ok）と `start` がもう 1 回呼ばれる。`failed` のときは呼ばれず、知らせが出て、声で会話が切れる。
- T5 予定の最後の下書きで `confirmEvent` を読む。次に「はい」で POST `/calendar/events` が 1 回。`sendSecretaryMessage` は 2 回目を呼ばない。
- T6 「いいえ」で POST 0 回・`notCreated` を読む。
- T7 分からない 2 回で POST 0 回・`askAgain` → `checkScreen` の順に読む。`askAgain` を読み終わると `start` がもう 1 回呼ばれる。
- T8 請求書の下書きで `invoiceReady` を読む。「はい」と言っても請求書の POST は 0 回（確かめ待ちにならない）。読んだ文に会社名・金額が入っていない。
- T9 窓を閉じると確かめ待ちが外れる（もう一度開いて「はい」でも POST 0 回）。
- T10 読み上げの途中で手で送ると、前の読み上げが終わっても `start` は呼ばれない（回数の印）。
- T11 声で会話の間、マイクが開いた状態で予定の「作る」ボタンを押すと、作った知らせを読み始める前に `abort` が呼ばれ、読み上げの間に聞き取りの文が来ても送りは 0 回。
- T12 声で会話の間、確かめの文を読んでいる途中で予定の「作る」ボタンを押すと、前の読み上げが終わっても `start` は呼ばれず、作った知らせを読み終わったときに 1 回だけ呼ばれる。送りは 0 回。
- 予定を作った知らせ（声で会話の間）を読み終わると `start` が呼ばれる（T5 の中で確かめる）。

## 8. 合格（PR を出す前に自分で確かめる）

- 上の試験が CI で全部通る。書き方の検査（eslint `--max-warnings=0`）の警告 0 件。`ja.json`/`en.json` のキー数が同じ。`local/no-japanese-literal` の違反 0 件。
- `git diff origin/main --name-only` が §1 の 7 ファイルだけ。
- PR は `--base main`・本文に `### 標準ワークフロー確認`。変更規模は大。

## 9. 想定の分かれ道（起きたら止めて返す）

- `formatDraftDateLine` の形が §2（５）と違う → NEEDS_DECISION:（新しく作らない）。
- `forwardRef` にすると今の試験が落ちる → 原因の生出力をつけて BLOCKED:。
- 1000ms で試験が不安定 → 偽の時計の使い方を直す。定数は変えない。

## 10. 戻し方

この PR の merge commit を revert する。DB・設定の変更なし。
