# パスキーの自動の候補 — 設計の審査 2回目（architect）

- 審査対象: origin/release/passkey-autofill-first（7b471136d）の docs/handoff/passkey-autofill-first/{design,card-bin1,review-architect-1,review-architect-1-response}.md
- 照合した実物: origin/main（9019d83e8）の frontend/src/lib/auth/passkey.ts・frontend/src/pages/login/LoginPage.tsx・LoginPage.test.tsx・passkey.test.ts・frontend/src/contexts/AuthContext.tsx・frontend/src/lib/auth/selfAuth.ts・backend/app/routers/auth.py、npm 公開版 @simplewebauthn/browser@14.0.0 の esm（npm pack で取得・入れていない）、scripts/agent-hooks/cloud/rules.md
- 読むだけ。製品のコード・DB・本番・secrets には触れていない。
- 行番号の表記: design.md・card-bin1.md は `git show` を `cat -n` した行（枝の実ファイルの行と同じ）。

## 判定: APPROVE（設計合格）

1. 1回目の R1〜R6 は、response.md の表どおり design.md・card-bin1.md に直っている（下の §1）。L4・L5 も直っている。
2. 直した設計（`!loading` の条件・世代の番号 genRef・busyRef・reject しない waitRef）は、作ると壊れる穴を新しく作っていない（§2）。ただし「始め直しのタイマーの張り直し」「`!authLoading`」「waitRef の待ちの上限」は書かれていないので、軽い指摘（§6 の N1〜N3）に分けた。直さなくても作れるが、カードに1行ずつ足すと実装役が迷わない。
3. T9〜T12 は vitest の fake timers と jsdom で書ける（§3）。カード手順0〜8 はクラウドの決まりに当たらない（§4）。受入表 P1〜P7 は○×か「判定不能」で決められる（§5）。

## §1 R1〜R6・L4・L5 が直ったか

| 番号 | 判定 | 根拠 |
|---|---|---|
| R1 待ち受けの古い呼び出しが生き残る | ○ | design.md:49 `startPasskeyAutofill(isStale: () => boolean)` と、options の後・`startAuthentication` の後の2か所の確認（true なら name が AbortError の誤りを投げ、verify も `adoptAccessToken` も呼ばない）。design.md:79 で世代の番号 `genRef`・`const gen = ++genRef.current`・`isStale = () => genRef.current !== gen`。design.md:86 の片付けは `genRef.current++` の後に `cancelPasskeyCeremony()`。card-bin1.md:57・64・68 に写っている。T3（card-bin1.md:76）に2条件が入っている。部品側の事実と合う: 取り消しの札は `startAuthentication` の中で `createNewAbortSignal()` した時に作られる（esm/methods/startAuthentication.js:64 付近）。`cancelCeremony()` は今ある札だけを止めて `controller = undefined` にする（esm/helpers/webAuthnAbortService.js:21-28）。options の通信中は止める相手が無いので、世代の番号で止める設計は正しい |
| R2 immediate の最中に待ち受けが始め直される | ○ | design.md:77 の条件に `!enrolling && !promptOpen && !loading`。design.md:83-84 のタイマーと `visibilitychange` は `!busyRef.current` が条件。design.md:81 で waitRef は「絶対に reject しない」。design.md:109 で busyRef と `!loading` の関係を書いている。design.md:104 で immediate 失敗後と `handlePasskeySignIn` の後は `loading` が false に戻ると1回だけ始め直る形。`immediateOk` の初期値 false は design.md:91・100。card-bin1.md:63・65・69 に写っている |
| R3 画面が隠れた後に古い札のまま残る | ○ | design.md:82-85 に `startedAt`・`restarts`・(a) タイマーは見えていて busy でない時だけ・(b) `visibilitychange` で見えた時に `Date.now() - startedAt >= 240_000` なら始め直す・(a)(b) 合わせて15回。design.md:139 のリスク表に「隠れたタブで札切れ」、design.md:140 に「StrictMode で古い待ち受け」。札が 300 秒（backend/app/auth/passkeys.py:27）で、切れた札の verify は 401 になり失敗回数に数えられる（backend/app/routers/auth.py:1135-1140）という1回目の根拠はそのまま。T10（card-bin1.md:85）に写っている |
| R4 カード手順の違反と抜け | ○ | card-bin1.md:103-105 手順0 に `./scripts/dev/executor-preflight.sh \|\| exit 1`（scripts/dev/executor-preflight.sh は実在）。手順2（:114-117）は `git checkout origin/release/passkey-autofill-first -- <docs>`（merge をやめた）。手順5（:125-133）に `check:i18n-missing-keys`・`check:error-text-next-action`・`check:jsx-emoji`（frontend/package.json:28・45・19 に3つとも実在）。手順7（:139-142）は明示のパスだけの `git add`（`git add -A` をやめた）。手順8（:144-150）は Write でファイルに書いて `git commit -F`。詳細は §4 |
| R5 試験が最も難しい動きを守っていない | ○（T12 だけ形が違う・N4） | T9 始め直しと15回の上限（card-bin1.md:84）、T10 隠れている間と見えた時（:85）、T11 immediate の最中（:86）、T12 `isStale`（:87）、T3 に R1 の2条件（:76）。design.md:155・159-160 の試験行と守り手も T1〜T12 に合っている。1回目は T12 を StrictMode の描画で確かめる形にしていたが、直しは unmount と描画し直しの形になった。世代の番号の仕組みは同じなので設計の穴ではない（N4 で StrictMode の1本を足す案） |
| R6 受入表の判定の前提と書き方 | ○ | design.md:148 P1 に前提（3 台にパスキーがあること・件数・「判定不能」と書く）。design.md:150-151 P2・P3 に chrome://version と `getClientCapabilities()` の `immediateGet` の記録、true でなければ「P3 は判定不能（設計の誤りではない）」。design.md:154 P7 に `npm run check:i18n-missing-keys` と色の直値の grep の命令。CI の必須かは「未確認」と書いた（正直な書き方） |
| L4 `o.extensions` | ○ | design.md:70 |
| L5 `immediateOk` の初期値 | ○ | design.md:91・100、card-bin1.md:62 |

## §2 直した設計が新しい穴を作っていないか

### 2-1 `!loading` を条件に足した useEffect が、片付け→始め直しを1回だけ起こすか — ○

- useEffect の依存に入る値（mode・approval・user・enrolling・promptOpen・loading）が変わるたびに、React が「前の片付け → 条件が真なら新しく始める」を1回ずつ行う。条件が真→偽（`loading` が true になる）で片付けだけ、偽→真（false に戻る）で始めるだけ。`loading` が true の間は待ち受けもタイマーも `visibilitychange` も無いので、押した後の画面（immediate の画面・QR の画面）を待ち受けが閉じることは無い。
- `loading` を立てるのは `handleSignIn`（frontend/src/pages/login/LoginPage.tsx:197-）・`handlePasskeySignIn`（:235-）・`handleReset`（:253-）。どれも `finally` か失敗の経路で false に戻す。戻った時に1回だけ始め直る。email・password・error は依存に入れないので、入力のたびには走らない。
- 成功の経路は二重に守られている。`adoptAccessToken` が `notify()`（frontend/src/lib/auth/selfAuth.ts:62-65）→ AuthContext の `sync` → `user` が立つ（frontend/src/contexts/AuthContext.tsx:68-93）。`user` が立つと条件が偽になり片付けが走り、`isStale` が true になる。この時に design.md:80 の「成功し、かつ `!isStale()` なら navigate」の確認が先か後かは React の描画の順で変わりうる。ただし既存の自動遷移（LoginPage.tsx:74-78 `!authLoading && user && ...` → `navigate`）が必ず進めるので、ログイン後に画面が止まることは無い（navigate が2回走っても `replace: true` で害は無い）。

### 2-2 `restarts` が描画し直しで0に戻って15回の上限が効かなくならないか — ○（書き方は軽く直す・N1）

- design.md:82 は `startedAt` と `restarts` を「ref に持つ」と書く。ref は描画し直しでは0に戻らない。useEffect の「再実行」（`loading` の切り替え）で0に戻すかどうかは書いていない。
- どちらで作っても上限は効く。再実行のたびに0に戻す形でも、1回の実行の中で15回まで、実行を作るのは利用者の操作（ボタン・送信）だけ。バックグラウンドで無限に始め直す事故は起きない。
- ただし T9 の「15回した後は増えない」の数え方（最初の1回を含めて16回か）が実装役の読み方で変わる。N1 で書き方を決める。

### 2-3 busyRef と `loading` の二重の守りが矛盾しないか — ○

- 矛盾しない。役割が違う。`busyRef` は「押した瞬間から、React が描画して片付けを走らせるまでの隙間」を埋める同期の旗。`loading` は「描画後の定常状態」を決める。`busyRef` が false になるのは `finally` の中で `setLoading(false)` と同じ位置（design.md:98）。
- 唯一の隙間は `handlePasskeySignIn` の中で、片付けの `cancelPasskeyCeremony()` が走る時点と、部品の `startAuthentication` が札を作る時点の前後。押した操作は離散イベントなので、React 18 は `setLoading(true)` の描画と片付けをイベントの終わりに同期で流す。その後に options の通信（selfPasskeyLogin の `postAuth`・selfAuth.ts:95 の `fetch`）が入るので、片付けの取り消しが `startAuthentication` の札を止めることは本番では起きない。試験では selfPasskeyLogin が mock なので起きない。念のための堅くする案は N5。

### 2-4 waitRef が reject しない形で await が必ず終わるか — ○（待ちの上限は N3）

- design.md:81 が「絶対に reject しない（内側で catch して解決する）」と型まで決めている。待ち受けの失敗（AbortError・NotAllowedError・SelfAuthError・ブラウザ側の誤り）はすべて捕まえて解決する。
- 終わる条件: (i) options の通信が返る（stale なら AbortError を投げて終わる）、(ii) `startAuthentication` の待ちは `cancelCeremony()` の abort で AbortError になって終わる。部品の誤りの名前は残る（esm/helpers/identifyAuthenticationError.js:11-18 は `ERROR_CEREMONY_ABORTED` の WebAuthnError に包むが、esm/helpers/webAuthnError.js:28 の `this.name = name ?? cause.name` で name は `AbortError` のまま。NotAllowedError も同:21-26 で cause の name のまま）。design.md:80 の「name が AbortError か NotAllowedError → 何も出さない」は成り立つ。
- 終わらない恐れ: (i) の options の通信に時間切れが無い（frontend/src/lib/auth/selfAuth.ts:95-101 の `fetch` に signal も timeout も無い）。回線が詰まると、押した操作の `await waitRef.current` が通信が返るまで続き、`loading` が true のまま。今のボタン（selfPasskeyLogin の `postAuth`）も同じ待ち方なので悪化はしない。が、押した操作の側の options は別の通信なので、待ち受けの古い通信に引きずられる必要は無い。N3 で「待ちを短く打ち切る」案を書く。

### 2-5 StrictMode の二重描画で isStale が正しく働くか — ○

- StrictMode（frontend/src/main.tsx:16）の開発では「始める → 片付け → 始める」。1回目の実行: `gen = ++genRef.current`（= 1）。片付け: `genRef.current++`（= 2）。2回目の実行: `gen = ++genRef.current`（= 3）。1回目の `isStale()` は `genRef.current(3) !== 1` で true、2回目は false。1回目は options の後で AbortError を投げて終わり、`startAuthentication` も verify も呼ばない。2回目だけが待ち受けを持つ。1回目の `waitRef` は2回目の Promise に差し替わる。
- 注意（軽い）: 1回目も `passkeyAutofillSupported()` の await の後に `startPasskeyAutofill` を呼ぶので、options の通信が1回余分に出る（auth_events の行が1つ増える）。開発（StrictMode）だけの話。本番の `loading` の切り替えでも同じ形で余分な通信が出うる。`isStale()` を options の通信の前にも1回見ると防げる（N2）。

### 2-6 そのほか読んで確かめたこと

- `immediate` の `finally` で `setLoading(false)` → 条件が真に戻り、待ち受けが1回始まる。`navigate(from)` と同じ描画に入れば、LoginPage ごと外れて待ち受けは始まらない。外れなくても片付けで止まる（stale になる）。
- 既存の LoginPage の試験は mock に新しい関数を足すだけで通る見込み: `vi.mock` は `...orig` を広げている（LoginPage.test.tsx:15-23）ので、足さない関数（`passkeyAutofillSupported`・`immediateGetSupported`）は本物が走る。本物は jsdom で `PublicKeyCredential` が無く、例外を捕まえて false を返す設計（design.md:48・51）。待ち受けは始まらず、既存の試験の動きは変わらない。
- 自動の候補の道の「成功→ログイン」は AuthContext.tsx:106-109 の `signInWithPasskey` が `selfPasskeyLogin` を呼ぶだけ（`dev` は別）と等価。lib を直に呼んで差が無い（1回目 L6 を事実で確認）。
- `startAuthentication` に `useBrowserAutofill: true` を渡す時、ログインのメール欄に `input[autocomplete$='webauthn']` が必要（esm/methods/startAuthentication.js:50-54 で無ければ投げる）。`autoComplete="email webauthn"` は末尾が webauthn で条件を満たす。TextFieldControl は `...rest` を `<input>` に渡す（frontend/src/components/TextField.tsx:44・55）ので、属性は届く。待ち受けを始める時点でメール欄は描画済み（useEffect は描画の後）。承認待ちの画面（approval）では欄が消えるので、条件の `!approval` が要る。design は入っている。

## §3 T9〜T12 は vitest の fake timers と jsdom で書けるか — ○（書き方の注意あり）

- 道具: vitest ^4.1.7・jsdom ^29.1.1・@testing-library/react ^16.3.2（frontend/package.json）。fake timers の先例は frontend/src/hooks/useExpiryRefresh.test.tsx:13・useRealtimeRefresh.test.tsx:32 など。
- `document.visibilityState` の差し替えは、この repo に先例がある: `vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility as DocumentVisibilityState)`（frontend/src/features/tcg-import-workflow/useImportStageDetails.test.tsx:8・15）と、`act(() => document.dispatchEvent(new Event("visibilitychange")))`（同:15、useImportWorkflow.test.tsx:15）。T10 はこの形で書ける。
- 時計: vitest の `vi.useFakeTimers()` は既定で `Date` も偽にする（toFake の既定）ので、`Date.now() - startedAt >= 240_000` は `advanceTimersByTime` で進む。T9・T10 で使える。
- 書き方の注意（カードに1行・N6）: fake timers の下で `waitFor`・`findBy*` は使わない（RTL の待ちは jest の偽時計だけを見分けるので、vitest の偽時計では止まる恐れ。未確認だが、止まる形を避けるほうが安全）。待ち受けの Promise の解決は `await act(async () => { await vi.advanceTimersByTimeAsync(240_000); })` の形で流す。T9 の「cancel の後に start」は `mock.cancelPasskeyCeremony.mock.invocationCallOrder` と `mock.startPasskeyAutofill.mock.invocationCallOrder` の比較で書ける。T11 は未解決の Promise（`new Promise(() => {})` か外から解決する形）を immediate の mock に返して書ける。T12 は `mock.startPasskeyAutofill.mock.calls[0][0]` を取り出して呼べばよい。unmount は `render` の戻り値の `unmount()` か `cleanup()`（現在の `renderLogin()` は戻り値を返さないので、返すように直すか `cleanup()` を使う）。
- passkey.test.ts 側: `vi.mock("@simplewebauthn/browser", ...)` は列挙した名前しか返さない（passkey.test.ts:11-15）ので、足す名前を全部足す指示（card-bin1.md:73）が要る。書いてある。`navigator.credentials.get` と `PublicKeyCredential.getClientCapabilities` は `vi.stubGlobal` で足せる。

## §4 カード手順0〜8 がクラウドの決まりに当たらないか — ○

scripts/agent-hooks/cloud/rules.md の決まり（reset・rebase・force・merge・pull を使わない・登録ファイルを commit しない・危険語を実行する命令に入れない・main を取り込まない）と、card-bin1.md:103-150 を照らした。

| 手順 | 命令 | 判定 |
|---|---|---|
| 0 | `./scripts/dev/executor-preflight.sh \|\| exit 1` | ○（禁止語なし・AGENTS.md の作業の型どおり） |
| 1 | `git fetch origin`・`bash scripts/new-worktree.sh release/passkey-autofill-impl`・`git log -1 --format=%H`・`git rev-parse origin/main` | ○（1手順1命令・枝名は `release/<topic>`） |
| 2 | `git checkout origin/release/passkey-autofill-first -- <2つのフォルダ>`・`git diff --cached --stat origin/main` | ○（merge ではない）。注意（取り込む枝は main の少し前の物。docs の2フォルダだけを取るので main の新しいファイルは混ざらない。実測: `git diff --name-status origin/main origin/release/passkey-autofill-first` の D（inbox の docs・components.css 等）は、取り込むパスに入っていない） |
| 3 | `git diff --stat bef5a7a8b origin/main -- <4ファイル>` | ○。実測: bef5a7a8b から origin/main までに frontend/src/lib/auth・pages/login・locales・package.json の変更は無い（`git diff --stat` が空）。期待どおり空になる |
| 5 | `npm ci`・`npx vitest run ...`・`npx tsc --noEmit -p tsconfig.json`・`npm run lint`・`check:i18n-missing-keys`・`check:error-text-next-action`・`check:jsx-emoji` | ○（npm script は3つとも実在・frontend/package.json:15・19・28・45）。`npm ci` がクラウドの外向き通信の許可を通るかは未確認（通らなければ BLOCKED: で報告する設計になっている） |
| 6 | `grep -c ... ja.json en.json` | ○ |
| 7 | 明示のパスだけの `git add`・`git diff --cached --stat origin/main` | ○（`git add -A` をやめた・登録ファイルを巻き込まない） |
| 8 | Write で commit 文 → `git commit -F`・`git log -2 --oneline`・`git push -u origin HEAD`・`git ls-remote origin refs/heads/...` | ○。commit 文の置き場が `/tmp/commit-msg.txt`（例）。この実行環境の決まりは scratchpad を使うことなので、「作業場所の外の一時の場所」と書くとよい（N8・軽い） |

命令の文字列に PostgreSQL の対話ツールの名前・危険語・sleep・`rm -rf`・`reset`・`rebase`・`--force`・`merge`・`pull` は無い（card-bin1.md:103-150 を目で確かめた。§4 の守ること（:92-97）の「sleep しない」「マージしない」は禁止の文言で、命令ではない）。

## §5 受入表 P1〜P7 が○×で判定できるか — ○

| 基準 | 判定 | 根拠・注意 |
|---|---|---|
| P1 3 台で候補が出てログイン | ○ | design.md:148。前提（3 台それぞれにパスキー・reader で `webauthn_credentials` の件数）が先にあり、前提が欠ければ「判定不能」と書く規則がある。「同期で見える場合は 1 でもよいと PO が判断」は PO の判断が入る分岐だが、判断者が決まっているので○×にできる |
| P2 Chrome 149 以降で選ぶ画面なしに確認が出る | ○ | design.md:150。chrome://version と `immediateGet` の記録が先。API 名（`getClientCapabilities().immediateGet`）は Chrome 公式の文を本審査では取得していない（未確認・1回目と同じ）。実機で `immediateGet` が出なければ P2・P3 は「判定不能」で、設計の誤りとは別 |
| P3 持っていなければ案内と QR の道 | ○ | design.md:151。試験 T4 と、true でない時の逃げ（別の機械で判定）あり |
| P4 Safari・iPhone・古い Chrome は今まで通り | ○ | design.md:152。T5＋iPhone で目視 |
| P5 パスワードのログインは変わらない | ○（軽い・N9） | design.md:153。「自動点検の係（user 87）」の user_id の出どころが design.md・recon.md・evidence.md・kgi.md に無い（kgi.md:40 は「自動点検の係」とだけ）。reader で数える時に実装役でなく Opus が確かめる前提なら足りる。出どころを1行足すと迷わない |
| P6 表・列を足さない | ○ | design.md:154。`git diff origin/main --name-only` に migrations・backend が無い、は命令として判定できる |
| P7 文言・金型・トークン | ○ | design.md:155。3つの命令（`npm run check:i18n-missing-keys`・ui-governance-gate・色の直値の grep）。CI の必須かは「未確認」と書いてあり正直 |
| 試験 | ○ | design.md:156。T1〜T12 と、T 番号が card-bin1.md:74-88 と一致している |

## §6 軽い指摘（直さなくても作れる）

実装役が迷いうる順。どれも design.md・card-bin1.md に1〜2行足せば消える。

- N1 始め直しのタイマーの張り直しと、`restarts` の持ち方（design.md:82-85・card-bin1.md:67）。(b)（見えた時の始め直し）で始め直した後、タイマーを張り直すかが書かれていない。(a) が「`setTimeout` を鎖にする」形で、隠れている間に鳴った時に張り直さない作りだと、(b) の後に張り直さない実装が出て、2回目以降が始め直されず、札が切れる（R3 の再発）。案: 「始め直すたび（(a)(b) どちらでも）に `startedAt = Date.now()` とし、`clearTimeout` してから 240 秒の `setTimeout` を1本だけ張り直す。隠れていて鳴った時は何もせず、張り直さない。(b) が引き継ぐ」。`restarts` と `startedAt` は useEffect の中のローカル変数（`let`）でよい（実行ごとに0から。上限は1回の実行の中で最初の1回に加えて 15 回＝呼び出しは計 16 回まで）と1行決めると、T9 の「15回した後」の数え方（card-bin1.md:84）が揺れない。
- N2 `startPasskeyAutofill` の入口でも `isStale()` を1回見る（design.md:49）。今は options の通信の後が最初の確認なので、StrictMode の1回目や、`loading` の切り替えで片付けられた直後の実行が、無駄な options の通信（backend/app/routers/auth.py:1106-1116 で札を1つ作る・auth_events に1行）を出す。入口で `isStale()` が true なら通信せずに AbortError を投げる。T3 に1行足せば守れる。
- N3 押した操作の `await waitRef.current` に上限を付ける（design.md:93・108）。待ち受けが options の通信の途中なら、世代の番号が古くなっているので、待たずに immediate へ進んでも安全（古い呼び出しは `startAuthentication` を呼ばずに AbortError で終わる）。案: `await Promise.race([waitRef.current, new Promise((r) => setTimeout(r, 1500))])`。待つ必要があるのは `startAuthentication` の中の待ちだけで、それは `cancelCeremony()` で即座に終わる。selfAuth.ts:95 の `fetch` に時間切れが無いので、回線が詰まった時に押した操作が止まるのを避けられる。T11 は fake timers なのでこの1500ms の進みも書ける。
- N4 T12 に StrictMode の1本を足す（card-bin1.md:87）。1回目の審査 R5 は StrictMode の描画を求めていた。`<React.StrictMode>` で包んで描画 → `startPasskeyAutofill` の1回目の `isStale()` が true・2回目が false、を1つ書く。
- N5（堅くする案・任意）片付けの `cancelPasskeyCeremony()` を `busyRef.current` が true の間は呼ばない（design.md:86・§2-3）。押した操作の側が自分で必要な取り消しを持っている（immediate は design.md:93 で自分で呼ぶ・QR の道は部品が前の呼び出しを自動で止める・recon.md の事実）ので、片付けの取り消しが押した操作の ceremony を止める隙間が理屈の上でも無くなる。今の設計で本番では起きない（§2-3）。
- N6 試験の書き方の注意をカードに1行（card-bin1.md:84-87）: fake timers の下では `waitFor`・`findBy*` を使わず、`await act(async () => { await vi.advanceTimersByTimeAsync(ms); })` で進める。`document.visibilityState` の差し替えは frontend/src/features/tcg-import-workflow/useImportStageDetails.test.tsx:8・15 の形に倣う。`renderLogin()`（LoginPage.test.tsx:34-44）が `unmount` を返さないので、T12 では戻り値を返すか `cleanup()` を使う。
- N7（待ち受けの開始の条件）`!authLoading` を足す（design.md:77・card-bin1.md:63）。AuthProvider の `loading` は起動時 true（frontend/src/contexts/AuthContext.tsx:58）で、refresh が終わるまで `user` は null。今の条件のままだと、ログイン済みの人が /login を開いた時に、refresh が終わる前に待ち受けが始まって（options の通信が1回）、`user` が立った時に片付けられる。害は小さい（余分な通信・auth_events の1行）が、`!authLoading` を足せば無駄が出ない。LoginPage.tsx:66 で `loading: authLoading` として既に取っている。
- N8 commit 文の置き場（card-bin1.md:145）: 「/tmp/commit-msg.txt（例）」の `/tmp` は例だが、この実行環境の決まりは scratchpad なので「作業場所の外の一時の場所」と書くとよい。
- N9 P5 の「user 87」の出どころを design.md:153 に1行（recon.md か reader の記録のパス）。
- L1（1回目から据え置き）行番号の小さなずれ（recon.md:26・:32・:33・design.md:21）。カードの「行番号は目印」（card-bin1.md:24）で足りる。
- L2 `design.md:100` の「`immediateGetSupported()` を画面を開いた時に1回」は、`mode` を切り替えて戻した時にも再び調べるか不明。1回でよい（`useEffect` の依存を空にする）と書くと実装役が迷わない。

## 確認していない・できなかったこと

- Chrome 149 の `uiMode: 'immediate'` と `getClientCapabilities().immediateGet` の実際の動き（出典は Chrome 公式の文で、本審査では取得していない・1回目と同じ）。反映後の PO の目視（P2・P3）に残る。
- fake timers の下の RTL の `waitFor` の止まり方（§3・N6）。作って試験を流して確かめる。
- クラウドで `npm ci` が通るか（§4 手順5）。通らなければ手順5 の規則で BLOCKED: になる。
- 本番の PO の機械での候補の見え方（P1〜P4）。
- ui-governance-gate.yml と frontend-check.yml の必須チェックの中身。

## 再審査は不要

APPROVE（設計合格）。N1〜N9 は作りながら（実装役が迷った時に）Opus がカードに足せばよい。作る前に直す必要のある点は無い。
