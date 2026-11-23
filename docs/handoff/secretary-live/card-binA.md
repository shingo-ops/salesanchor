# 実装カード 便 A: マイクの印を PC にも出し、話している間の文字を欄に出す

正本: docs/handoff/secretary-live/design.md §7・§9・§10・§11。ADR-1087（Proposed）。KGI: kgi.md L2・L3（L13 の「文の長さ」の 1 件も）。
PO の承認: KGI L1〜L13 は 2026-11-23「1」。実装からマージ・配備までの完走は 2026-11-24「1,…PRマージ、デプロイまで完走させてくれ」。
ブランチ: `release/secretary-mic-live-text`（origin/main から新しく作る）。行番号は origin/main bef5a7a8b の値。
0 円の便。backend・migration・台帳は触らない（ADR-1082 What 1 のまま）。

## 作業場所の作り方（クラウド）

1. `git fetch origin` の後、`bash scripts/new-worktree.sh release/secretary-mic-live-text` で作り、その中へ cd する。
2. `git rev-parse origin/main` が通ることを確かめる。通らなければ BLOCKED:
3. 以後の作業はすべてこの worktree の中で行う。clone のまま commit しない。reset・rebase・force・merge・pull は使わない。

## 触るファイル（これ以外は触らない）

1. `frontend/src/features/secretary/useSecretaryListen.ts`
2. `frontend/src/features/secretary/useSecretaryListen.test.ts`
3. `frontend/src/features/secretary/SecretaryChat.tsx`
4. `frontend/src/features/secretary/SecretaryChat.test.tsx`（`describe("SecretaryChat listen mark"` の塊 :633-729 だけ）
5. `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（`secretary.listen` の塊 :6324 の中だけ）
6. `frontend/eslint.config.js`（override を 1 つ足すだけ）

触らない: backend・migrations・.github・useSecretaryVoice.ts・「声で返事」のトグル（便 C で消す）・下書きの部品・CSS・icons.tsx・design.md・ADR 本文。

## 変更 1: useSecretaryListen.ts（聞き続ける・自分で終わったら聞き直す）

今（:104-153）: `continuous = false`。`onend` で必ず止まる。

変えた後:

- 定数 `export const LISTEN_MAX_IDLE_RESTARTS = 5;` を足す（何も聞き取れないまま聞き直す回数の上限）。
- `useRef` を 2 つ足す: `wantRef`（利用者が聞いてほしい間 true）・`idleRestartsRef`（続けて何も取れなかった聞き直しの回数）。
- 部品を作って始める処理を、内側の関数 `begin()` に分ける。`start()` は「`recRef.current` があれば何もしない → `wantRef=true`・`idleRestartsRef=0`・`setError(null)`・`setInterim("")` → 部品が無ければ今と同じく `unsupported` → `begin()`」。
- `begin()` の設定: `lang="ja-JP"`・`interimResults=true`・**`continuous=true`**・`maxAlternatives=1`。
- `onresult`: 今と同じ（決まった文は `onTextRef.current(...)` を 1 回、途中の文は `setInterim`）。加えて、決まった文が空でなければ `idleRestartsRef=0`。
- `onerror`: `classifyListenError` で分ける。`noSpeech` は**表に出さず**、そのまま `onend` の聞き直しに任せる。`null`（aborted）は今と同じく何もしない。それ以外（notAllowed・serviceNotAllowed・audioCapture・network・language・other）は `wantRef=false` にして `setError(kind)`。
- `onend`（自分の部品のときだけ）: `recRef.current=null`・`setInterim("")`。続けて
  - `wantRef` が true で `idleRestartsRef < LISTEN_MAX_IDLE_RESTARTS` なら、`idleRestartsRef += 1` して `begin()`（`listening` は true のまま）。
  - そうでなければ `wantRef=false`・`setListening(false)`。上限に届いて止まったときだけ `setError("noSpeech")`。
- `begin()` の中の `rec.start()` が投げたら: `recRef.current=null`・`wantRef=false`・`setListening(false)`・`setError("other")`（今と同じ）。
- `stop()`: `wantRef=false` にしてから今と同じく `recRef.current?.stop()`。
- `abort()`: 先頭で `wantRef=false`。残りは今と同じ。

決まった文が二重に足されないこと: 決まった文は `onresult` の `isFinal` のときだけ `onText` に渡し、途中の文は `interim` にだけ持つ（今の分け方のまま）。聞き直した部品は新しい部品なので、前の部品の結果を二度渡さない。

## 変更 2: SecretaryChat.tsx（PC にも出す・欄に途中の文字・1,000 字）

1. :255 の `{isMobile && (` と対の `)}` を外し、マイクの印を PC にも出す。聞き取りの無いブラウザでは、今と同じく印は出て、押すと `secretary.listen.error.unsupported` の文が出る（今の試験 `SecretaryChat.test.tsx:716` の動き）。
2. 欄（:246 の `Textarea`）:
   - `value={listen.listening ? text + listen.interim : text}`
   - `readOnly={listen.listening}`（聞いている間は打てない。止めた後に直せる）
3. 下の案内（:268-273）: 聞いている間は `t("secretary.listen.listening")` だけを出す（途中の文字は欄に出すので、ここには出さない）。
4. 送るボタン（:274）: `disabled={sending || listen.listening || text.trim() === ""}`（聞いている間は送れない。勝手に送らない）。
5. 1,000 字（`SECRETARY_MAX_TEXT`・:63）:
   - `useState` で `tooLong`（boolean）を足す。
   - :63 の受け口を、足した後の長さが `SECRETARY_MAX_TEXT` 以上になったら、先頭の `SECRETARY_MAX_TEXT` 字だけ残し、`setTooLong(true)` と `listen.stop()` を呼ぶ形に変える。`listen` を受け口の中で使うため、`useRef` に `listen.stop` を持って呼ぶ（受け口の作り直しで聞き取りを作り直さない）。
   - 今の text は `useRef` で持ち、受け口の中では `setText` の更新関数（`prev`）を使わず `ref + heard` で長さを決め、`setText` には値を渡す。`setTooLong`・`stop` は更新関数の外で呼ぶ（更新関数は純粋でなければならず、開発時に 2 回呼ばれるため・審査 4 回目 N4）。
   - 案内の段に、`tooLong` のとき `t("secretary.listen.tooLong", { max: SECRETARY_MAX_TEXT })` を出す（聞き取りの誤りの文より先）。
   - `tooLong` は、欄を手で直したとき（`onChange`）・送ったとき・窓を閉じたとき・次に印を押したときに false に戻す。

## 変更 3: 翻訳（ja.json・en.json の `secretary.listen` の中）

- `"tooLong"` を足す。
  - ja: `"{{max}} 字に達したので聞くのをやめました。この画面で一度に送れるのは {{max}} 字までです。いったん送ってから続きを話してください"`
  - en: `"Stopped listening at {{max}} characters. This box can send up to {{max}} characters at once. Send this part, then speak the rest."`
- ほかの鍵は変えない。

## 変更 4: eslint.config.js（日本語の直書きを秘書の窓だけ機械で止める）

最後の `...storybook.configs["flat/recommended"]` の前に、次の 1 塊を足す（前例: 同じファイルの `src/pages/design-preview/**` の塊）。

```js
// ADR-1087: 秘書の窓は日本語の直書きを CI で止める（全体は warn のまま）
{
  files: ['src/features/secretary/**/*.{ts,tsx}'],
  ignores: ['src/features/secretary/**/*.test.{ts,tsx}'],
  rules: {
    'local/no-japanese-literal': 'error',
  },
},
```

origin/main bef5a7a8b の `features/secretary/` は、日本語が注釈の中にしかない（Opus が `git show` で全 12 ファイルを確かめた）。足した後に error が出たら直さず BLOCKED:

## 変更 5: なし（審査 4 回目 N1 の直しで、索引の秘書の行への ADR-1087 は設計の PR で足した。`docs/adr/FEATURE-INDEX.md` は触らない）

## 試験（期待を足す・変える）

useSecretaryListen.test.ts:
- 今の `expect(rec.continuous).toBe(false)` を `toBe(true)` に変える。
- 足す: (a) 聞いている間に `emitEnd()` が来ると、新しい部品で聞き直し `listening` が true のまま (b) `stop()` の後の `emitEnd()` では聞き直さない (c) `abort()` の後は聞き直さない (d) 何も取れないまま `LISTEN_MAX_IDLE_RESTARTS` 回聞き直したら止まり `error` が `noSpeech` (e) 決まった文が来ると数え直しが 0 に戻り、その後も聞き直す (f) `notAllowed` の後の `emitEnd()` では聞き直さず `error` が残る (g) `noSpeech` の誤りは表に出ず聞き直す (h) 聞き直しの前後で決まった文が二重に `onText` に渡らない。
- 今の試験「clears the previous error on the next start」「keeps the error after an end event that follows it」は、(d)(f) の動きに合わせて期待を直す。直す必要が無ければ触らない。

SecretaryChat.test.tsx の listen mark の塊:
- 「has no listen mark when isMobile is false」を「has a listen mark when isMobile is false」に変え、PC でも印があることを確かめる。
- 足す: (i) 途中の文が欄に出る・その間は欄が readOnly・送るボタンが押せない (ii) 決まった文を足して 1,000 字を超えると欄が 1,000 字で止まり `tooLong` の文が出て部品の `stop` が呼ばれる (iii) 欄を手で直すと `tooLong` の文が消える。
- 日本語の文字は今と同じく `String.fromCharCode` で作る。

## 確かめ（commit の前に全部流し、最後の 10 行を報告に貼る）

1. `cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/features/secretary`
2. `cd frontend && npx tsc --noEmit -p .`
3. `cd frontend && npx eslint src/features/secretary`（error 0・warn 0）
4. `cd frontend && node scripts/check-i18n-missing-keys.js`
5. `git diff --stat origin/main` で触ったファイルが上の 6 種（7 ファイル）だけであること

## 想定される分岐（当たったらその場で止める）

- `ignores` を足した塊で eslint が設定の誤りを出す → BLOCKED:（書き方を変えない）
- 今の試験が、このカードに書いていない理由で落ちる → 期待を書き換えず BLOCKED:
- `Textarea` が `readOnly` を受けない → BLOCKED:
- 見張り・フックに止められた → 言い換えず原文を書いて BLOCKED:

## commit と push

- commit は 1 つ。文は Write でファイルに書いて `git commit -F` で流す。末尾は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- `git push -u origin release/secretary-mic-live-text`（--no-verify・force を付けない）
- PR は作らない（Opus が作る）。最後の返事は 1 行で `DONE: <sha>` か `BLOCKED: <理由>`。

## 本番の確かめ（Opus・PO）

- 配備の後、本番の PC の Chrome で秘書の窓を開き、マイクの印が出ること・話している間に欄に文字が出ることを Opus が確かめる（L2 の 1 回目）。
- L2（4 つの組み合わせで各 10 回）と L3（各 5 回）は、kgi.md の測り方で PO と行う。結果は `docs/handoff/secretary-live/results.md` に書く。
