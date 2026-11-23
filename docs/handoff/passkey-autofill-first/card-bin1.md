---
mode: handoff
---
# 実装カード 便1: パスキーの自動の候補と、Chrome のすぐ出す画面

親: [design.md](./design.md) §3・§4・§7（受入条件）／[recon.md](./recon.md)

- 状態: カード作成済み（2026-11-24 Opus）。PO 実装承認: 2026-11-24 チャット（KGI 承認「1」と同じ文で「PRマージ、デプロイまで完走させてくれ」）。マージと本番反映の判断は Opus が行う（担当はしない）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断。
- 区分: B（frontend だけ。migrations・scripts・deploy.yml・backend を触らない）。

## 0. カード発行前チェック

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は Opus が作る（担当は作らない） | ○（§5 手順8 で push まで） |
| 3 | 報告の宛先（最後の返事に生出力の全文） | ○（§6） |
| 4 | 1便1目的（ログイン画面のパスキーの出し方だけ） | ○ |
| 5 | 起点の明示（origin/main から new-worktree.sh） | ○（§5 手順1） |
| 7 | 合格基準を出力まで縛る（差分のファイル一覧） | ○（§5 手順7） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 受領と終端の合図・停止の3点 | ○（§6） |
| 11 | 行番号は目印（ずれたら前後の文で探す） | ○ |
| 13 | sleep 禁止・Write/Edit で書く・フックに止められたら言い換えない | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md（全命令を cd で始める・1手順1命令・待たない・commit と push の後に git log と ls-remote で実在を確かめる）、04-worktree.md（起点は origin/main・`new-worktree.sh` で作る・push は `git push -u origin HEAD`）、05-pr.md（`gh pr create` を直に使わない → PR は Opus が作る）。

基準: 設計の基準 origin/main bef5a7a8b。行番号はこの時点の目印。

## 1. 目的（利用者に見える変化）

- ログイン画面のメール欄を押すと、その機械にパスキーがあれば候補に出る。選ぶと顔・指紋でログインできる。
- Chrome 149 以降では「顔・指紋でログイン」を押すと、選ぶ画面を挟まずに顔・指紋の確認が出る。パスキーが無ければ「この機械にはパスキーがありません」と「スマホなど別の機械のパスキーを使う」が出る。
- Safari・iPhone・古い Chrome では、ボタンは今まで通り。パスワードのログインは変わらない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `frontend/src/lib/auth/passkey.ts` | design.md §4-1 |
| `frontend/src/pages/login/LoginPage.tsx` | design.md §4-2・§4-3 |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | design.md §4-4 のキー2つ |
| `frontend/src/lib/auth/passkey.test.ts` | 試験 T1〜T3 |
| `frontend/src/pages/login/LoginPage.test.tsx` | 試験 T4〜T12 |
| `docs/handoff/passkey-autofill-first/` と `docs/specs/auth-login/` | 手順2 の取り込みで入るだけ。中身は変えない |

触らないもの: backend・migrations・scripts・`.github/`・`AuthContext.tsx`・部品の版（`package.json` と lock）・金型（`frontend/src/components/`）・CSS。新しい部品・新しい CSS・色の直値を作らない。案内は `Callout`（variant="info"）と `TextLink` だけで作る。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. passkey.ts

- design.md §4-1 の通り。`finishPasskeyLogin` を1つ作り、`selfPasskeyLogin`・`startPasskeyAutofill`・`immediatePasskeyLogin` の3つから使う（verify と adoptAccessToken を3か所に書かない）。
- `uiMode` の型は passkey.ts の中だけで足す（`CredentialRequestOptions` を広げる型を1つ書く）。グローバルの型ファイルを作らない。
- `immediatePasskeyLogin` は `allowCredentials` と `password` を渡さない。`o.extensions` があれば渡す。
- `startPasskeyAutofill(isStale: () => boolean)`。`isStale()` を options の後（`startAuthentication` の前）と `startAuthentication` の後（verify の前）の2か所で見て、true なら name が AbortError の誤りを投げる（design.md §4-1-3）。

### 3-2. LoginPage.tsx

- design.md §4-2 の1〜5 と §4-3 の通り。
- `immediateGetSupported()` は画面を開いたときに1回だけ調べて state `immediateOk`（初期値 `false`）に持つ。ボタンを押した後に await しない。
- 待ち受けの useEffect の条件は `mode === "signIn" && !approval && !user && !enrolling && !promptOpen && !loading`。
- 世代の番号 `genRef` と `isStale = () => genRef.current !== gen` を作り `startPasskeyAutofill(isStale)` に渡す。成功の navigate と誤りの表示は `!isStale()` のときだけ。
- 待ち受けの Promise は reject しない形で `waitRef` に持ち、始めるたびに差し替える。
- 自動の候補の待ち受けの失敗は、AbortError と NotAllowedError とブラウザ側の誤りは何も出さない。verify の失敗（`SelfAuthError`）だけ `authErrorMessage(err, t, "passkey")` を出す。
- 始め直し: (a) 240 秒のタイマーで、見えていて `busyRef.current` が false なら始め直す。(b) `visibilitychange` で見えた時に、始めてから 240 秒以上なら始め直す。(a)(b) 合わせて最大15回。始め直しは `genRef.current++` → `cancelPasskeyCeremony()` → 新しく始める。
- 片付けで `genRef.current++` → `cancelPasskeyCeremony()`、タイマーと `visibilitychange` を外す。
- `handlePasskeyButton` と `handlePasskeySignIn` は、始めに `busyRef.current = true`、finally で false。immediate の前に `genRef.current++; cancelPasskeyCeremony(); await Promise.race([waitRef.current, new Promise((r) => setTimeout(r, 1500))]);`（待ちは最大 1.5 秒・審査2 N3）。
- 審査2 で決めた細部（design.md より細かい。こちらに従う）:
  - 条件に `!authLoading` も足す（LoginPage.tsx:66 の `loading: authLoading`）。N7
  - `restarts` と `startedAt` は useEffect の中の `let`（実行ごとに 0 から）。最初の1回に加えて始め直しは最大 15 回＝`startPasskeyAutofill` の呼び出しは1回の実行で計 16 回まで。N1
  - 始め直すたび（(a)(b) どちらでも）に `startedAt = Date.now()` とし、`clearTimeout` してから 240 秒の `setTimeout` を1本だけ張り直す。隠れていて鳴った時は何もせず張り直さない（(b) が引き継ぐ）。N1
  - `startPasskeyAutofill` は入口でも `isStale()` を見て、true なら通信せず AbortError を投げる（確認は計3か所）。N2
  - 片付けの `cancelPasskeyCeremony()` は `busyRef.current` が true の間は呼ばない。N5
  - `immediateGetSupported()` は依存が空の useEffect で1回だけ調べる。L2

### 3-3. 試験（足す）

passkey.test.ts（`@simplewebauthn/browser` の vi.mock に `WebAuthnAbortService`・`base64URLStringToBuffer`・`bufferToBase64URLString`・`browserSupportsWebAuthnAutofill` を足す）:
- T1 `immediateGetSupported`: getClientCapabilities が無い→false／immediateGet true のときだけ true／投げたら false。
- T2 `immediatePasskeyLogin`: options → `navigator.credentials.get` に `uiMode: "immediate"` があり `allowCredentials` と `password` が無い → verify に challenge_id が渡る。get が NotAllowedError を投げたら verify を呼ばず、name が NotAllowedError のまま投げる。
- T3 `startPasskeyAutofill`: `startAuthentication` が `useBrowserAutofill: true` で呼ばれ、その後 verify。`isStale` が options の後で true なら `startAuthentication` を呼ばず AbortError。`startAuthentication` の後で true なら verify を呼ばず AbortError。既存の `selfPasskeyLogin` の試験はそのまま合格。

LoginPage.test.tsx（既存の vi.mock に新しい関数を足す）:
- T4 immediate 対応＋`immediatePasskeyLogin` が NotAllowedError → `login.passkeyNotOnDevice` と `login.passkeyUseOtherDevice` が出る。リンクを押すと今の道（`selfPasskeyLogin`）が1回呼ばれる。
- T5 immediate 非対応 → ボタンで今の道が1回呼ばれ、`immediatePasskeyLogin` は呼ばれない。
- T6 immediate 成功 → 元のページへ進む。今の道は呼ばれない。
- T7 ログインのメール欄の autocomplete が `email webauthn`。再設定のメール欄は `email` のまま。
- T8 自動の候補対応 → 画面を開くと `startPasskeyAutofill` が1回呼ばれる。AbortError で終わっても誤りの文は出ない。画面を閉じると `cancelPasskeyCeremony` が呼ばれる。
- T9（fake timers）待ち受け中に 240 秒進める → `cancelPasskeyCeremony` の後に `startPasskeyAutofill` が2回目に呼ばれる。始め直しを15回した後は進めても増えない。
- T10（fake timers）`document.visibilityState` が hidden の間は 240 秒進めても増えない。visible に戻して `visibilitychange` を出すと、240 秒を超えていれば1回増える。
- T11（fake timers）immediate の Promise が未解決の間に 240 秒進めても `startPasskeyAutofill` が増えない。NotAllowedError で終わった後に1回増える。
- T12 `startPasskeyAutofill` に渡された `isStale` が、片付け（unmount）の後は true を返す。描画し直した後の新しい呼び出しの分は false。もう1本、`<React.StrictMode>` で包んで描画し、1回目の呼び出しの `isStale()` が true・最後の呼び出しの分が false（審査2 N4）。
- 試験の書き方（審査2 N6）: fake timers の下では `waitFor`・`findBy*` を使わず、`await act(async () => { await vi.advanceTimersByTimeAsync(ms); })` で進める。`document.visibilityState` の差し替えは frontend/src/features/tcg-import-workflow/useImportStageDetails.test.tsx の `vi.spyOn(document, "visibilityState", "get")` と `document.dispatchEvent(new Event("visibilitychange"))` の形に倣う。unmount が要る試験は `renderLogin()` が render の戻り値を返すように直してよい。
- 既存の LoginPage の試験はすべてそのまま合格（直してよいのは mock に関数を足すことだけ）。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／金型にない部品が要るとき／design.md と食い違うのに design.md どおりに作れないとき／部品 14.0.0 に design.md §4-1 の名前が無いとき。
- 行番号のずれは記録して続行し、報告に書く。
- 本番 DB・本番サーバーに接続しない。PR を作らない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書く。`cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に、`cd 作業場所` はそのパスに読み替える。1手順1命令。

手順0 作業前の点検
    cd 取り出した場所 && ./scripts/dev/executor-preflight.sh || exit 1
    期待する出力: 0 で終わる。× なら停止して BLOCKED:（生出力の全文）。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/passkey-autofill-impl
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。報告に書く。

手順2 設計の書類を取り込む（Opus が push した枝）
    cd 作業場所 && git checkout origin/release/passkey-autofill-first -- docs/handoff/passkey-autofill-first docs/specs/auth-login
    cd 作業場所 && git diff --cached --stat origin/main
    期待する出力: docs だけ（docs/handoff/passkey-autofill-first と docs/specs/auth-login）。ほかのファイルが出たら停止して NEEDS_DECISION:。merge は使わない（クラウドの決まり）。

手順3 対象ファイルが設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat bef5a7a8b origin/main -- frontend/src/lib/auth/passkey.ts frontend/src/pages/login/LoginPage.tsx frontend/src/lib/auth/passkey.test.ts frontend/src/pages/login/LoginPage.test.tsx
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順4 §3-1 と §3-2 と ja.json・en.json を Write／Edit で直し、§3-3 の試験を書く。

手順5 試験と型と検査を流す
    cd 作業場所/frontend && npm ci
    cd 作業場所/frontend && npx vitest run src/lib/auth src/pages/login
    cd 作業場所/frontend && npx tsc --noEmit -p tsconfig.json
    cd 作業場所/frontend && npm run lint
    cd 作業場所/frontend && npm run check:i18n-missing-keys
    cd 作業場所/frontend && npm run check:error-text-next-action
    cd 作業場所/frontend && npm run check:jsx-emoji
    期待する出力: すべて合格。落ちたら直してからもう一度流す。3回直しても落ちたら停止して BLOCKED:（生出力の全文を付ける）。

手順6 文言の両方そろいを確かめる
    cd 作業場所 && grep -c "passkeyNotOnDevice\|passkeyUseOtherDevice" frontend/src/locales/ja.json frontend/src/locales/en.json
    期待する出力: 両方とも 2。

手順7 差分のファイル一覧を確かめる
    cd 作業場所 && git add frontend/src/lib/auth/passkey.ts frontend/src/lib/auth/passkey.test.ts frontend/src/pages/login/LoginPage.tsx frontend/src/pages/login/LoginPage.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/passkey-autofill-first docs/specs/auth-login
    cd 作業場所 && git diff --cached --stat origin/main
    期待する出力: §2 の表のファイルだけ。deletions がある行は名前を報告に書く。`git add -A` は使わない（登録ファイルを巻き込む）。

手順8 記録して送る
    commit の文を Write で作業場所の外の一時の場所（以下 /tmp/commit-msg.txt と書く）に書く。1行目「feat(login): offer passkeys in email autofill and Chrome immediate mode」、空行、最後の行「Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>」。
    cd 作業場所 && git commit -F /tmp/commit-msg.txt
    cd 作業場所 && git log -2 --oneline
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin refs/heads/release/passkey-autofill-impl
    期待する出力: git log の先頭が手順8 の commit。ls-remote の番号が `git rev-parse HEAD` と同じ。

## 6. 報告

- 受け取ったら最初に「カード 便1 パスキーの自動の候補 を受領」と1行書く（受領確認）。
- 報告は PR コメントにしない。最後の返事に、手順1・2・3・5・6・7・8 の出力の全文を書く。
- 止まったら（停止）、止まった手順・最後のコマンド・理由の原文を書き、最後の行を `BLOCKED:` か `NEEDS_DECISION:` で終える。終えたら最後の行を `DONE: ` と push した HEAD の40桁で終える。

END OF CARD
