# 作業指示書（便 V2）— 秘書の画面が外れた後にマイクを開かない（後片付け）

- 設計: `docs/handoff/secretary-voice-input/design.md` §15-13 ／ 目標: `docs/handoff/secretary-voice-input/kgi.md` §5 V2（秘書の声が欄に入るのは 0 回）
- 状態: PO の実装承認あり（2026-11-25 チャット「残っていることを進める、2と1を順番に進める」の「2」= この直し）
- 実行役: クラウドの Sonnet。作業場所は既存の枝 `release/secretary-voice-unmount-cleanup`（手順は §6）。始める前に `./scripts/dev/executor-preflight.sh || exit 1`。
- 規則: `docs/ai-agents/executor-checklist.md`。この便は画面の文字・部品・色を足さない（ADR-027・ADR-144・ADR-067 に当たる変更なし）。

## 1. 触るファイル（これ以外は触らない）

| ファイル | 変えること |
|---|---|
| `frontend/src/features/secretary/SecretaryChat.tsx` | §3 |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | §4 |

触らない: `useSecretaryListen.ts`・`useSecretaryVoice.ts`・`SecretaryDraftEvent.tsx`・`secretaryVoiceAnswer.ts`・`ja.json`・`en.json`・backend・migrations・deploy.yml・`docs/`（Opus が書く）。

## 2. 実物の点検（始める前に。違ったら止めて `BLOCKED:` で返す）

（１）`frontend/src/features/secretary/SecretaryChat.tsx:10` が `import { Fragment, useEffect, useRef, useState } from "react";`。
（２）同じファイルの `:91` に `const voiceOnRef = useRef(false);`、`:94` に `const turnRef = useRef(0);` がある。
（３）同じファイルの `speakThenListen`（`:134-145`）の最後の行が `if (voiceOnRef.current && turn === turnRef.current) listen.start();`。
（４）`frontend/src/features/secretary/useSecretaryVoice.ts:107` が `useEffect(() => disable, [disable]);`、`frontend/src/features/secretary/useSecretaryListen.ts:200` が `useEffect(() => abort, [abort]);`（どちらも変えない）。
（５）`frontend/src/features/secretary/SecretaryChat.test.tsx` の `describe("SecretaryChat voice conversation"` の最後の試験が `T13`（`:1082` 付近）で、`holdNextSpeech`・`hear`・`startCount`・`flush`・`SLOW`・`TOGGLE`・`FAB` が使える。

## 3. SecretaryChat.tsx

`const eventRefs = useRef(new Map<number, SecretaryDraftEventHandle>());`（今の `:97`）の**すぐ後**に、次の 8 行を足す。ほかは変えない。

```tsx
  // 画面が外れたら、読み上げの途中の終わりでマイクを開かない（声と聞き取りの部品は自分で片付ける）
  useEffect(
    () => () => {
      voiceOnRef.current = false;
      turnRef.current += 1;
    },
    [],
  );
```

- なぜ: 画面が外れると `useSecretaryVoice` の片付け（`disable`）が読み上げの回数を進め、途中の `speak` は `"ok"` を返す（`useSecretaryVoice.ts:84`・`:96`）。そのとき `speakThenListen` の最後の行は `voiceOnRef.current` も `turn === turnRef.current` も真のままなので、外れた後に `listen.start()` を呼ぶ。聞き取りの部品の片付け（`useSecretaryListen.ts:200`）はもう済んでいるので、開いたマイクは誰も閉じない。
- 書き方の検査 `react-hooks/exhaustive-deps` の警告 0 件（ref だけを使うので依存は `[]`）。

## 4. SecretaryChat.test.tsx

`describe("SecretaryChat voice conversation"` の中、`T13` の試験の後に 1 つ足す。

```tsx
  it("T14: unmounting during a reading does not open the mic afterwards", async () => {
    mock.postWithTimeout.mockResolvedValueOnce(unknownReply("Hello there."));
    const { unmount } = renderChat();
    fireEvent.click(screen.getByRole("button", { name: FAB }));
    fireEvent.click(await screen.findByRole("switch", { name: TOGGLE }));
    expect(startCount()).toBe(1);
    const release = holdNextSpeech();
    hear("hi");
    await waitFor(() => expect(mock.speech).toHaveBeenCalledTimes(1), { timeout: 4000 });
    unmount();
    release();
    await flush();
    expect(startCount()).toBe(1);
  }, SLOW);
```

- 直す前のコードでこの試験が**落ちる**ことを先に確かめる（§3 を入れる前に 1 回流し、`startCount()` が 2 で落ちる記録を残す）。落ちなければ止めて `BLOCKED:` で返す（試験が直しを測れていない）。
- 名前・文は英語のまま（ほかの試験と同じ）。

## 5. 確かめ（全部の生の出力をファイルに残す）

（１）`cd frontend && npx vitest run src/features/secretary` → 全件合格（前は 105 件。今回 +1 件）。
（２）`cd frontend && npx eslint src/features/secretary --max-warnings=0` → rc=0。
（３）`cd frontend && npx tsc --noEmit -p .` → rc=0。
（４）`git diff --name-only origin/main...HEAD` に、この紙の §1 の 2 ファイル以外のコードが無い（Opus の docs は除く）。

## 6. 作業場所・commit・push

（１）写しの最上位で `git fetch origin` → `bash scripts/new-worktree.sh release/secretary-voice-unmount-cleanup-impl`（出た場所へ cd）→ `git merge --no-edit origin/release/secretary-voice-unmount-cleanup`（ぶつかれば `BLOCKED:`）。
（２）commit 文は Write でファイルに書いて `git commit -F <file>` で流す。git は 1 命令ずつ流す。Bash に psql の語を書かない。
（３）`git push origin HEAD:release/secretary-voice-unmount-cleanup`（同じ枝へ。PR は Opus が作る）。force push はしない。
（４）返事は `DONE` / `BLOCKED: <理由>` / `NEEDS_DECISION: <問い>` のどれか 1 つで始める。1 つの発言は 600 文字以内・番号付きの発言に分ける。
