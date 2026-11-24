# パスキーの自動の候補 — 設計の審査 1回目（architect）

- 審査対象: origin/release/passkey-autofill-first（ff9e6c0ad）の docs/handoff/passkey-autofill-first/{recon,design,card-bin1,evidence}.md と docs/specs/auth-login/kgi.md
- 照合した実物: origin/main（9019d83e8）の frontend/src/lib/auth/passkey.ts・frontend/src/pages/login/LoginPage.tsx・各 .test.ts(x)・backend の読むだけの箇所、npm 公開版 @simplewebauthn/browser@14.0.0 の esm（npm pack で取得・入れていない）
- 読むだけ。製品のコード・DB・本番・secrets には触れていない。

## 判定: REVISE（直す必要）

1. 部品 14.0.0 の名前・引数は design §4-1 と合う。行番号のずれも軽い（§1）。土台は正しい。
2. ただし design §4-2・§4-3 の「待ち受けの止め方・始め直し・immediate とのぶつかり」に、作ると壊れる穴が3つある（R1 待ち受けの古い呼び出しが生き残る・R2 immediate 中に待ち受けが始まり直す・R3 画面が隠れた後に古い札のまま残る）。実装役はこの穴を自分では塞げない書き方になっている。
3. カード手順2 が merge（クラウドの決まりで禁止）・手順7 が `git add -A`（登録ファイルを巻き込む）・手順8 が `git commit -m`。受入表 §7 の P1 は「持っているパスキーが各機械にあること」の前提が無く、○× で判定できない。

## 直す点（作る前に直す）

### R1 待ち受けの古い呼び出しが、片付けの後・新しい呼び出しの後に生き残る
- 事実:
  - design.md:81-82（§4-2-2）は「片付けで `cancelPasskeyCeremony()` を呼び、以後 setState しない（cancelled の旗）」とだけ書く。待ち受けは §4-1-3（design.md:49）で options → `startAuthentication` → verify を **passkey.ts の1関数**にまとめるので、画面側の旗は関数の途中（options の通信中）に届かない。
  - 部品は `startAuthentication` の呼び出しの時に初めて取り消し用の札を作る（npm 公開版 14.0.0 の `esm/methods/startAuthentication.js:64`）。作る時に前の呼び出しを止める（同 `esm/helpers/webAuthnAbortService.js:10-20`）。`cancelCeremony()` は今ある呼び出しだけを止める（同:21-28）。options の通信中に片付けが走ると止める相手が無く、通信が終わった後に **古い呼び出しが新しく待ち受けを始める**。
  - frontend/src/main.tsx:16 は `React.StrictMode`。開発では useEffect が「始める→片付け→始める」と2回走る。1回目の options が後から返ると、2回目の待ち受けを止めて1回目が残る（止められた側は AbortError で黙って捨てる設計なので、待ち受けが誰もいなくなる／捨てるはずの側が verify まで行ってログインを確定する）。
  - 画面を離れた（片付け済み）後に古い呼び出しが候補を選ばれて成功すると、`adoptAccessToken`（passkey.ts:34 と同じ位置）が画面なしで走る。
- 直し方:
  - design.md §4-1-3 の `startPasskeyAutofill()` を `startPasskeyAutofill(isStale: () => boolean): Promise<void>` に改める。`isStale()` を (a) options の応答の後、`startAuthentication` の前、(b) `startAuthentication` の応答の後、verify の前、の2か所で見て、true なら `Object.assign(new Error("stale"), { name: "AbortError" })` を投げる（verify も `adoptAccessToken` も呼ばない）。
  - design.md §4-2-2 の旗を「世代の番号」に改める。useEffect の中で `const gen = ++genRef.current;` を取り、`isStale = () => genRef.current !== gen || cancelled`。片付けでは `genRef.current++` してから `cancelPasskeyCeremony()`。
  - card-bin1.md §3-1 の「design.md §4-1 の通り」に `startPasskeyAutofill(isStale)` を足す。T3（card-bin1.md:71）に「isStale が options の後で true なら `startAuthentication` を呼ばない」「`startAuthentication` の後で true なら verify を呼ばない」を足す。

### R2 immediate の最中に待ち受けが始め直される
- 事実: design.md:80（240秒の始め直し）と design.md:99（§4-2-5 immediate の失敗・`handlePasskeySignIn` の後の始め直し）は、いつ始め直してはいけないかを書いていない。§4-3（design.md:102-104）の「先に止めて終わるのを待つ」は **押した瞬間の1回**だけを守る。immediate は部品を通らない（recon.md:60）ので、immediate の画面が出ている間に 240 秒のタイマーが来ると、`startAuthentication` が呼ばれて自動の候補が同時に始まる。これは recon.md:76 が「未確認・避ける」とした組み合わせそのもの。同じく `handlePasskeySignIn`（QR の道）の最中に始め直すと、部品の取り消しでユーザーが開いた QR の画面が AbortError で閉じる。
- 直し方:
  - design.md §4-3 に「`busyRef`（押してから終わるまで true）を置く。タイマー・始め直しの鍵（§4-2-5）・visibilitychange は `busyRef.current` が true の間は何もせず、終わった時（finally）に1回だけ始め直す」を足す。useEffect の条件にも `!loading` を足す（design.md:76 の `mode === "signIn" && !approval && !user` に `&& !enrolling && !promptOpen && !loading`）。`enrolling` はパスワード送信の間に true（LoginPage.tsx:200）で、ログイン直後の自動登録（passkey.ts:87 の `startRegistration`）を片付けの `cancelPasskeyCeremony()` が止める事故を避けるために要る。
  - design.md §4-2-3 の「待ち受けの Promise」は、「**絶対に reject しない**（内側で catch して解決する）Promise を `waitRef` に持ち、始め直すたびに新しいものに差し替える。押した時は `cancelPasskeyCeremony(); await waitRef.current;`」と型まで書く。今の「終わり（成功・失敗どちらでも）」は reject の扱いが実装役任せで、`await` が投げて immediate に進めなくなる穴がある。

### R3 画面が隠れた後に古い札のまま待ち受けが残る
- 事実: 札は 300 秒で消える（backend/app/auth/passkeys.py:27）。design.md:80 とカード §3-2（card-bin1.md:63）は「隠れている間は始め直さない」だけで、**見えるようになった時**の扱いが無い。タブを隠したまま 5 分過ぎ、戻って候補を選ぶと、verify は札が無く 401 になり（backend/app/routers/auth.py:1138-1140）、`record_auth_failure(ip)`（同:1135）が走って IP の失敗回数に数えられる（backend/app/cache.py:311-322、10 回で口が止まる）。設計は §6 のリスク表にこれを挙げていない。ブラウザは隠れたタブのタイマーを遅らせるので、240 秒のタイマーは当てにならない。
- 直し方:
  - design.md §4-2-2 の始め直しを「`startedAt` を持ち、(a) タイマーが来た時に見えていれば始め直す、(b) `visibilitychange` で見えるようになった時に `Date.now() - startedAt >= 240_000` なら始め直す。隠れている間のタイマーは何もしない」に書き換える。15 回の上限は「始め直した回数」で数え、(b) も同じ数に入れる。
  - design.md §6 のリスク表に「隠れたタブで札が切れる → 見えた時に始め直す（R3）。切れた札で選ばれた場合は verify の 401 が `authError.passkeyExpired`（authErrorMessage.ts の `challenge_expired` 判定）か `passkeyFailed` で出る」を足す。

### R4 カード手順の違反と抜け（card-bin1.md）
- 手順2（card-bin1.md:101-104）の `git merge --no-ff --no-edit` は、クラウドの決まり（scripts/agent-hooks/cloud/rules.md の「reset・rebase・force・merge・pull は使わない」）に当たる。見張りに止められて実装役が BLOCKED で終わる。
  - 直し方: `cd 作業場所 && git checkout origin/release/passkey-autofill-first -- docs/handoff/passkey-autofill-first docs/specs/auth-login` に替え、確認は `git diff --cached --stat origin/main`（期待: docs の 7 ファイルだけ）にする。
- 手順7（card-bin1.md:123-126）の `git add -A` は、`.claude-pipeline/active-work.d/*.md` を追跡対象にしている（.gitignore:67-71）ので登録ファイルを巻き込む。rules.md は「登録ファイルは commit しない」。
  - 直し方: `git add frontend/src/lib/auth/passkey.ts frontend/src/lib/auth/passkey.test.ts frontend/src/pages/login/LoginPage.tsx frontend/src/pages/login/LoginPage.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/handoff/passkey-autofill-first docs/specs/auth-login` と書く（§2 の表と同じ並び）。
- 手順8（card-bin1.md:128-131）の `git commit -m "..."` は、commit 文を Write でファイルに書いて `git commit -F` にする（文末の共作者の2行を含める）。
- 手順5（card-bin1.md:112-117）に、frontend の決まりの検査を足す: `npm run check:i18n-missing-keys`・`npm run check:error-text-next-action`・`npm run check:jsx-emoji`（frontend/package.json:28 と check:all の並び）。今の手順は vitest・tsc・lint だけで、P7（文字が ja/en）を作る側で確かめられない。
- 手順1 の後に、クラウドの決まり（rules.md）の「push 済みの枝の続きは `git switch -C <枝名> origin/<枝名>`」は不要（新しい枝）なので書かなくてよい。ただし手順1 の前に `./scripts/dev/executor-preflight.sh || exit 1`（AGENTS.md「作業の型」）が無い。card-bin1.md §5 の手順0 として足す。

### R5 試験が最も難しい動きを守っていない
- 事実: T1〜T8（card-bin1.md:68-79・design.md:147）は、待ち受けの始め直し・隠れている間・15 回の上限・片付けの後・immediate 中のタイマーを1本も確かめない。R1〜R3 で足す動きは、試験が無いと次の変更で静かに壊れる（design.md:151 の「守り手」が成り立たない）。
- 直し方（card-bin1.md §3-3 と design.md §7 の「試験」行・§8 の T 番号を合わせて直す）:
  - T9（LoginPage・fake timers）: 待ち受け中に 240 秒進める → `startPasskeyAutofill` が2回目に呼ばれ、`cancelPasskeyCeremony` が先に呼ばれる。15 回呼んだ後は進めても増えない。
  - T10（同）: `document.visibilityState` が hidden の間は 240 秒進めても呼ばれない。visible に戻して `visibilitychange` を出すと、240 秒を超えていれば呼ばれる。
  - T11（同）: immediate の Promise が未解決の間に 240 秒進めても `startPasskeyAutofill` が増えない（R2）。解決後に1回増える。
  - T12（同）: StrictMode で描画 → `startPasskeyAutofill` に渡された `isStale` を、1回目の呼び出しの分は true・2回目の分は false として確かめる（R1）。
  - T3 に R1 の2条件（上記）を足す。

### R6 受入表の判定の前提と書き方（design.md §7・kgi.md）
- P1（design.md:140・kgi.md:36）: 3 台でパスキーの候補を選んでログインするには、3 台それぞれにパスキーがあることが前提。evidence.md:60 は「パスキーの登録: PO 1 件（一度も使っていない）」、evidence.md:41 は端末間の同期が「未確認」。今のままでは P1 が×でも設計の誤りか前提の欠けか区別できない。
  - 直し方: design.md §7 の P1 の検証方法の前に「前提: 反映前に PO が iPhone と Android でもパスワードでログインし、自動登録（passkey.ts:81-99 の `autoRegisterOnce`）か案内でパスキーを作る。登録件数は reader で `webauthn_credentials` の PO の件数が 3 以上（同期で見える場合は 1 でもよいと PO が判断）」を足す。
- P2・P3（design.md:141-142）: 「Chrome 149 以降」の確認が検証方法に無い。P3 はシークレット窓で `getClientCapabilities().immediateGet` が true になるかが未確認（recon.md:70 は「get が NotAllowedError」の事実だけ）。false なら D の道（QR）になり P3 の「画面に出る」が×になる。
  - 直し方: 検証方法に「目視の前に Chrome のバージョン（chrome://version）と、シークレット窓で開発者ツールのコンソールに `await PublicKeyCredential.getClientCapabilities()` を実行した結果の `immediateGet` を記録する」を足し、true でなければ「P3 は判定不能（設計の誤りではない）。シークレット以外の持っていない機械で判定する」と書く。
- P7（design.md:146）: 「`git diff` に色の直値が無い」に命令が無い。直し方: `git diff origin/main -- frontend/src | grep -nE '#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\('` が空、と書く。「CI の i18n と UI ガバナンスの検査」は、UI ガバナンスは .github/workflows/ui-governance-gate.yml があるが、`check-i18n-missing-keys` を呼ぶ workflow は origin/main の .github 配下の検索で見つからなかった（frontend/package.json:28・48 の npm script としては存在）。検証方法は「`cd frontend && npm run check:i18n-missing-keys` が 0 で終わる」と書き、CI の必須チェックかは「未確認」と書く。

## 軽い指摘（直さなくても作れる）

- L1 行番号のずれ（影響なし）: recon.md:26 の `passkey.ts:63-75` は実物 62-74（`conditionalCreateSupported` は 63-74、前の説明コメントが 62）。design.md:21 の「passkey.ts:79-112」は実物 76-112（`getPasskeyPrompt` が 77-79、`autoRegisterOnce` が 81-99、`autoRegisterPasskey` が 102-112）。recon.md:33 の `Callout.tsx:24-31` は実物 25-32。recon.md:32 の `TextField.tsx:43-56` は実物 43-57。
- L2 ほかの recon・design の行番号は origin/main の実物と合う: passkey.ts:22-24・27-35・52-57、LoginPage.tsx:235-250・394-402（autoComplete は 401）・424-437・451-459（reset の autoComplete は 458）、AuthContext.tsx:106-109、ja.json:705-709・765-769、LoginPage.test.tsx:18-20・319-374、passkey.test.ts:11-16、backend/app/routers/auth.py:1106-1116、cache.py:311-325、passkeys.py:27。設計の基準 bef5a7a8b から origin/main 9019d83e8 までに、対象の frontend/src/lib/auth・frontend/src/pages/login・frontend/src/locales・frontend/package.json への変更は無い（`git log bef5a7a8b..origin/main -- <それらのパス>` が空）。
- L3 部品 14.0.0 の名前と引数は design.md §4-1 と一致: `WebAuthnAbortService.cancelCeremony()`（esm/helpers/webAuthnAbortService.js:21-28・d.ts で公開）、`base64URLStringToBuffer(string): ArrayBuffer`・`bufferToBase64URLString(ArrayBuffer): string`、`browserSupportsWebAuthnAutofill(): Promise<boolean>`、`startAuthentication({ optionsJSON, useBrowserAutofill })`（startAuthentication.js:16-23）。`input[autocomplete$='webauthn']` が無ければ投げる（同:50-54）ので、`"email webauthn"`（末尾が webauthn）で条件を満たす。`useBrowserAutofill` は `mediation = 'conditional'` と空の allowCredentials を自分で付ける（同:57-59）。`toAuthenticatorAttachment` は公開されないので design.md:67 のように自前で書くのは正しい。immediate に `uiMode` の扱いが部品に無い（startAuthentication.js 全文）も事実どおり。
- L4 部品に `useBrowserAutofill` を渡した時、`options.allowCredentials` が空配列でも `getOptions.publicKey` に `...optionsJSON` が展開される（同:34-38）。immediate の自前の組み立て（design.md:56-58）は `extensions` と `timeout` の扱いを部品と揃えていない。サーバーの options（backend/app/auth/passkeys.py:84-87 の `authentication_options`）に拡張が入る時は `extensions` を渡す必要がある。今は入っていないので実装に支障は無いが、`o.extensions` があれば渡す1行を足すと将来のずれを防げる。
- L5 `immediateGetSupported()` を「画面を開いたときに1回だけ」調べて state に持つ（design.md:96）時、調べ終わるまでの間は false として扱い（今の道）、押せるようになる前に調べ終わる前提で OK。state の初期値を `false` と書いておくと実装役が迷わない。
- L6 パスキーでログインした時は `clearRecoveryPromptMarksForCurrentUser()` が呼ばれない（AuthContext.tsx:102 の `signIn` だけが呼ぶ）。今の `signInWithPasskey`（同:106-109）と同じで、今回の変更で悪化はしない。自動の候補の道も同じ扱い（lib を直に呼ぶので AuthContext.tsx:106-109 と等価）。意図なら design.md §2 の「対象外」に1行書くと迷いが減る。
- L7 design.md:97 の `Callout variant="info"` は 内側に `TextLink` を入れる。Callout の children は `ReactNode`（components/Callout.tsx:21）なので型は通る。見た目の確認は PO の目視（P3）に任せる。
- L8 `login.passkeyNotOnDevice` と `login.passkeyUseOtherDevice` は ja.json・en.json に現在存在しない（origin/main の `git grep` が空）ので、card-bin1.md:120-121 の `grep -c` が各 2 になる、という期待は成り立つ。locales は ja.json・en.json の 2 ファイルだけ（viewer は別の仕組みで未確認）。
- L9 「この機械にはパスキーがありません」は、画面を閉じた場合にも出る（recon.md:69・design.md:128）。design は「別の機械のパスキーを使う」リンクで逃がしている。PO への完了報告に1行入れる約束（design.md:128）を card-bin1.md には書いていない。カードの報告欄（§6）に「P3 の見え方の注意を完了報告に書く」は Opus 側の作業なので、カードには不要。
- L10 評価の見取り図: card-bin1.md の止まる条件（:86）・行番号のずれは記録して続行（:87）・触るファイル（:37-48）・触らないもの（:48）・T1〜T8 の中身（:68-79）は、実装役が迷わず読める書き方。R1〜R5 を design.md に直した後、カード §3-1・§3-2・§3-3 に同じ変更を写す。

## 確認していない・できなかったこと

- Chrome 149 の `uiMode: 'immediate'` と `getClientCapabilities().immediateGet` の実際の動き（recon.md §5 が出典とする Chrome 公式の文を、本審査では取得していない）。
- 本番の PO の機械での候補の見え方（P1〜P4）。反映後の目視に残る。
- ui-governance-gate.yml と frontend-check.yml の必須チェックの中身（名前の存在のみ確認）。

## 再審査に出す時

- design.md §4-1-3・§4-2・§4-3・§6・§7・§8 と card-bin1.md §3・§5 の修正を同じ枝（release/passkey-autofill-first）に push。R1〜R6 の番号ごとに「どこを直したか」を1行ずつ返すと、2回目の審査が速い。
