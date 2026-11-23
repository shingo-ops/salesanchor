# パスキーの自動の候補 — 設計（design）

- KGI: docs/specs/auth-login/kgi.md「KGI 追加 — パスキーの自動の候補」P1〜P7・KPI（PO 承認 2026-11-24 チャット「1」）
- PO の言葉: docs/specs/auth-login/ideal-state.md「PO の言葉（2026-11-23〜24 …）」
- 現在地: docs/handoff/passkey-autofill-first/recon.md
- 正本の ADR: ADR-1013（パスキー・RP ID）／ADR-1055 What 5（パスキーは機械の承認なし）／ADR-027（文言は t()）／ADR-144（金型）
- 状態: 設計案作成済み（Opus・2026-11-24）。審査はクラウドで行う。

## §1 目的（PO の言葉で）

ログインのとき、パスキーを持っている人には、パスワードより先にパスキーが出るようにする。ブラウザに任せ、新しいデータは作らない（PO「1」=ア）。

## §2 対象と対象外

| 対象 | 対象外（触らない） |
|---|---|
| frontend/src/lib/auth/passkey.ts（関数を足す・共通の verify を1つにまとめる） | backend 全部（口・回数止め・札の5分・audit） |
| frontend/src/pages/login/LoginPage.tsx（メール欄の autoComplete・待ち受けの開始と停止・ボタンの道の分岐・案内の表示） | DB・migrations・deploy.yml・scripts |
| frontend/src/locales/ja.json・en.json（login の下にキー2つ） | 再設定画面のメール欄（LoginPage.tsx:458） |
| 試験 2 本（passkey.test.ts・LoginPage.test.tsx） | AuthContext.tsx（signInWithPasskey はそのまま） |
| | パスワードでログインした後の自動登録（passkey.ts:79-112） |

## §3 変更前→変更後

| # | 変更前 | 変更後 |
|---|---|---|
| A | メール欄 `autoComplete="email"`（LoginPage.tsx:401） | `autoComplete="email webauthn"` |
| B | 画面を開いても何もしない | ログイン画面（mode=signIn・承認待ちでない・`passkeySupported()`・ブラウザが自動の候補に対応）を開いたら、自動の候補の待ち受けを始める。候補を選んで顔・指紋が通れば verify → ログイン → 元のページへ |
| C | ボタン → `signInWithPasskey()`（部品の画面・別の機械の QR を含む） | `immediateGet` が true（Chrome 149 以降）なら、まず immediate で呼ぶ。通れば verify → ログイン。NotAllowedError なら案内「この機械にはパスキーがありません」と「別の機械のパスキーを使う」リンクを出す。リンク → 今までの `handlePasskeySignIn()`（QR の道） |
| D | — | `immediateGet` が false（Safari・iPhone・Chrome 148 以前）なら、ボタンは今までどおり `handlePasskeySignIn()` |

新しい ADR は作らない。理由: RP ID・サーバー・表・保存の場所が変わらず、ADR-1013 Decision 1・5b の範囲の画面の工夫だから。

## §4 作り方（file:line と前後のコード）

### §4-1 passkey.ts

1. import に `WebAuthnAbortService`・`base64URLStringToBuffer`・`bufferToBase64URLString`・`browserSupportsWebAuthnAutofill`・型 `AuthenticationResponseJSON` を足す（どれも 14.0.0 の index で公開・recon §4）。
2. 共通の後半を1つにする（重複させない）:
   ```ts
   async function finishPasskeyLogin(challengeId: string, credential: AuthenticationResponseJSON): Promise<void> {
     const token = await postAuth<TokenResponse>("/passkey/login/verify", { challenge_id: challengeId, credential });
     adoptAccessToken(token.access_token, token.expires_in);
   }
   ```
   `selfPasskeyLogin()` は options → `startAuthentication({ optionsJSON })` → `finishPasskeyLogin` に書き換える（動きは同じ）。
3. 足す関数:
   - `passkeyAutofillSupported(): Promise<boolean>` = `passkeySupported() && await browserSupportsWebAuthnAutofill()`（例外は false）。
   - `startPasskeyAutofill(isStale: () => boolean): Promise<void>` = options → `startAuthentication({ optionsJSON: res.options, useBrowserAutofill: true })` → `finishPasskeyLogin`。`isStale()` を (a) options の応答の後・`startAuthentication` の前、(b) `startAuthentication` の応答の後・verify の前、の2か所で見て、true なら `Object.assign(new Error("stale"), { name: "AbortError" })` を投げる（verify も `adoptAccessToken` も呼ばない）。理由: 部品の取り消しの札は `startAuthentication` を呼んだ時に初めて作られるので、options の通信中の片付けは部品では止められない（審査1 R1）。
   - `cancelPasskeyCeremony(): void` = `WebAuthnAbortService.cancelCeremony()`。
   - `immediateGetSupported(): Promise<boolean>` = `conditionalCreateSupported()` と同じ型で `caps.immediateGet === true`。
   - `immediatePasskeyLogin(): Promise<void>`:
     ```ts
     const res = await postAuth<Challenge<PublicKeyCredentialRequestOptionsJSON>>("/passkey/login/options");
     const o = res.options;
     const cred = (await navigator.credentials.get({
       publicKey: { challenge: base64URLStringToBuffer(o.challenge), rpId: o.rpId, timeout: o.timeout, userVerification: o.userVerification },
       uiMode: "immediate",
     } as CredentialRequestOptions)) as PublicKeyCredential | null;
     if (!cred) throw new Error("Authentication was not completed");
     const r = cred.response as AuthenticatorAssertionResponse;
     await finishPasskeyLogin(res.challenge_id, {
       id: cred.id, rawId: bufferToBase64URLString(cred.rawId), type: "public-key",
       response: { authenticatorData: bufferToBase64URLString(r.authenticatorData), clientDataJSON: bufferToBase64URLString(r.clientDataJSON),
                   signature: bufferToBase64URLString(r.signature), userHandle: r.userHandle ? bufferToBase64URLString(r.userHandle) : undefined },
       clientExtensionResults: cred.getClientExtensionResults(),
       authenticatorAttachment: cred.authenticatorAttachment === "platform" || cred.authenticatorAttachment === "cross-platform" ? cred.authenticatorAttachment : undefined,
     });
     ```
     `o.extensions` があれば `publicKey.extensions` に渡す（今のサーバーは入れないが、将来のずれを防ぐ・審査1 L4）。
     `allowCredentials` と `password: true` は渡さない（recon §5: 空でない allow は失敗・パスワードの候補は出さない）。navigator の誤りはそのまま投げる（name が NotAllowedError のまま届く）。
     `as CredentialRequestOptions` は TypeScript の DOM 型に `uiMode` がまだ無いため。型の拡張は passkey.ts の中だけに書く。

### §4-2 LoginPage.tsx

1. A: :401 の `autoComplete="email"` を `"email webauthn"` に（:458 は変えない）。
2. B: 待ち受けの useEffect を足す。条件 `mode === "signIn" && !approval && !user && !enrolling && !promptOpen && !loading`（`enrolling` はパスワード送信の間 true・LoginPage.tsx:200。ログイン直後の自動登録 passkey.ts:87 を片付けの取り消しで止めないため。審査1 R2）。
   - `passkeyAutofillSupported()` が false なら何もしない。
   - 世代の番号: `genRef = useRef(0)`。始めるたびに `const gen = ++genRef.current;`、`isStale = () => genRef.current !== gen` を作り、`startPasskeyAutofill(isStale)` を呼ぶ。成功し、かつ `!isStale()` なら `navigate(from, { replace: true })`。
   - 失敗の扱い: name が AbortError か NotAllowedError → 何も出さない（止めた・閉じた・古い）。それ以外で **verify まで進んだ失敗**（SelfAuthError）かつ `!isStale()` → `authErrorMessage(err, t, "passkey")` を error に出す。それ以外のブラウザ側の誤り → 何も出さない。
   - 待ち受けの Promise: **絶対に reject しない**（内側で catch して解決する）Promise を `waitRef` に持ち、始めるたびに新しいものに差し替える（§4-3 で `await waitRef.current` に使う）。
   - 始め直し（札は 5 分で消える・recon §3）: `startedAt`（始めた時刻）と `restarts`（始め直した回数）を ref に持つ。
     - (a) 240 秒のタイマーが来た時、`document.visibilityState === "visible"` かつ `!busyRef.current` なら始め直す。隠れている間・busy の間のタイマーは何もしない。
     - (b) `visibilitychange` で見えるようになった時、`Date.now() - startedAt >= 240_000` かつ `!busyRef.current` なら始め直す（ブラウザは隠れたタブのタイマーを遅らせるため。審査1 R3）。
     - 始め直しは「`genRef.current++` → `cancelPasskeyCeremony()` → 新しく始める」の順。`restarts` は (a)(b) 合わせて数え、15 回に達したら以後始め直さない（1 時間）。
   - 片付け（画面を離れる・条件が外れる）: `genRef.current++` してから `cancelPasskeyCeremony()`。タイマーと `visibilitychange` の登録を外す。
3. C/D: ボタンの onClick を `handlePasskeyButton` に替える。
   ```
   setError(""); setPasskeyMissing(false);
   if (!immediateOk) return handlePasskeySignIn();   // D: 今まで通り（immediateOk は state・初期値 false）
   busyRef.current = true; setLoading(true);
   try {
     genRef.current++; cancelPasskeyCeremony(); await waitRef.current;   // §4-3（waitRef は reject しない）
     await immediatePasskeyLogin(); navigate(from, { replace: true });
   } catch (err) {
     if (err is NotAllowedError) setPasskeyMissing(true);
     else setError(authErrorMessage(err, t, "passkey"));
   } finally { busyRef.current = false; setLoading(false); }
   ```
   注意: 押した直後に `await immediateGetSupported()` を挟むと押す操作の有効時間を食うため、`immediateGetSupported()` は画面を開いたときに1回だけ調べて state `immediateOk`（初期値 `false`＝今の道）に持つ。ボタンの中では state を読むだけにする（審査1 L5）。
   `handlePasskeySignIn` も同じく、始めに `busyRef.current = true`、finally で false にする。
4. `passkeyMissing` が true の間、ボタンの下に `Callout variant="info" title={t("login.passkeyNotOnDevice")}` を出し、中に `TextLink` で `t("login.passkeyUseOtherDevice")` → `handlePasskeySignIn()`（今の道・QR）。メール欄・パスワードはそのまま使える。
5. immediate の失敗の後と、`handlePasskeySignIn` の終わり（成功以外）の後は、待ち受けを始め直す。やり方: `loading` が false に戻ると B の useEffect の条件が再び true になり、1 回だけ始め直る（`!loading` を条件に入れたため。別の鍵の数字は作らない）。busy の間（`loading` が true）は useEffect の片付けが走り、待ち受けもタイマーも止まっている。

### §4-3 ぶつかりを避ける

- 待ち受け中に、部品の `startAuthentication`（D の道・リンクの道）を呼ぶと、部品が前の呼び出しを自動で止める（recon §4）。止められた待ち受けは AbortError で終わり、§4-2-2 で黙って捨てる。
- immediate は部品を通らないので、先に `genRef.current++` と `cancelPasskeyCeremony()` を呼び、`await waitRef.current`（reject しない Promise）で待ち受けが終わるのを待ってから navigator を呼ぶ（recon §6 の未確認を避ける）。
- `busyRef`（押してから終わるまで true）を置く。タイマー・`visibilitychange` は `busyRef.current` が true の間は何もしない。さらに `!loading` を useEffect の条件に入れるので、busy の間は待ち受け自体が片付けられている。終わって `loading` が false に戻った時に1回だけ始め直る（審査1 R2）。immediate の画面や QR の画面が出ている間に、待ち受けが始まり直してその画面を閉じることは無い。
- パスワードの送信中（`enrolling` が true）は条件が外れて待ち受けを止める。ログイン後の自動登録（passkey.ts:81-99）は待ち受けが止まった後に始まるので、片付けの取り消しで自動登録を止めることは無い。

### §4-4 文言（ADR-027）

| キー | ja | en |
|---|---|---|
| login.passkeyNotOnDevice | この機械にはパスキーがありません | No passkey on this device |
| login.passkeyUseOtherDevice | スマホなど別の機械のパスキーを使う | Use a passkey from another device, like your phone |

ja.json と en.json の login の中、`signInWithPasskey` の次に足す。ほかのキーは変えない。

### §4-5 審査2の軽い指摘の取り込み

審査2（review-architect-2.md・APPROVE）の N1〜N7・L2 は card-bin1.md §3-2・§3-3 に細部として書いた（!authLoading・restarts の数え方とタイマーの張り直し・入口の isStale・待ちの上限 1.5 秒・StrictMode の試験・busy 中は片付けで取り消さない）。食い違う時はカードの細部に従う。

## §5 代替案と選んだ理由

| 案 | 採否 | 理由 |
|---|---|---|
| 自動の候補だけ（ボタンは今まで通り） | 不採用 | PO「33」=3 は immediate を含む |
| 画面を開いたら immediate を自動で呼ぶ | 不採用 | 押す操作が必須（recon §5）。呼べない |
| 部品を 14 より新しい版へ上げる | 不採用 | 14.0.0 に uiMode が無いことは確かめたが、新しい版にあるかは確かめていない。版上げは影響が広い（登録の道も変わる） |
| サーバーに「この人はパスキーを持つ」を覚えさせる | 不採用 | PO「1」=ア（新しいデータを作らない） |

## §6 リスクと対処

| リスク | 対処 |
|---|---|
| 「閉じた」でも「パスキーがありません」と出る（recon §5 で区別できない） | 案内の下に「別の機械のパスキーを使う」リンクを必ず出す。メール・パスワード欄はそのまま。PO への完了報告で、この見え方を伝える |
| 待ち受けがパスワードのログインを邪魔する | 待ち受けは欄の候補に出るだけ。P5（自動点検の係のログインが 14 日すべて成功）で見る。最初の朝の点検で失敗なら戻す |
| 画面を開くたびに auth_events が 1 行増える | 既存の表・既存の種類。新しい表・列は作らない（P6）。増える数は auth_events のパス別件数で見る |
| 回数止めの IP（10 回失敗）では options が 429 | 待ち受けは黙って始めない。ログイン自体も止まっている状態で、今と同じ |
| 押す操作の有効時間が options の通信で切れる | NotAllowedError → 案内とリンク（壊れない）。P2 で PO の Chrome で確かめる |
| 隠れたタブで札が 5 分で切れる（ブラウザは隠れたタブのタイマーを遅らせる） | 見えるようになった時に 240 秒を過ぎていれば始め直す（§4-2-2 (b)）。それでも切れた札で選ばれた場合は verify が 401 になり、`authError.passkeyExpired`（authErrorMessage.ts:36 の `challenge_expired` 判定）か `passkeyFailed` が出る。その 1 回は IP の失敗回数に数えられる（backend/app/routers/auth.py:1135・10 回で止まる）（審査1 R3） |
| 開発時の二重描画（main.tsx:16 の StrictMode）で古い待ち受けが残る | 世代の番号と `isStale` で、古い呼び出しは options の後と候補の後で止まり、verify もログインもしない（§4-1-3・§4-2-2・審査1 R1） |

戻し方: この PR を戻す（revert）だけ。サーバー・DB は変わらないので、データの戻しは要らない。

## §7 受入条件

| 基準 | 検証方法 |
|---|---|
| P1 3 台で欄に候補が出て、顔・指紋でログインできる | 前提: 反映前に PO が iPhone と Android でもパスワードでログインし、自動登録（passkey.ts:81-99 の `autoRegisterOnce`）か案内でパスキーを作る。reader で `webauthn_credentials` の PO の件数が 3 以上（同期で見える場合は 1 でもよいと PO が判断）。前提が欠けた時の×は「判定不能」と書き、設計の誤りと区別する（審査1 R6）。その上で反映後、PO の目視（Mac Chrome・iPhone Safari・Android Chrome）＋ reader で auth_events の /api/v1/auth/passkey/login/verify 成功（PO の user_id・user_agent 3 種） |
| P2 Chrome 149 以降で持っていれば、ボタンで選ぶ画面なしに顔・指紋 | 目視の前に Chrome のバージョン（chrome://version が 149 以上）と、開発者ツールのコンソールで `await PublicKeyCredential.getClientCapabilities()` の `immediateGet` を記録する。true の時に PO の Mac Chrome で目視 |
| P3 持っていなければ「この機械にはパスキーがありません」と QR の道 | 同じくシークレット窓で `immediateGet` を記録する。true なら Mac Chrome のシークレット窓で目視（常に NotAllowedError）＋ 試験 T4。true でなければ「P3 は判定不能（設計の誤りではない）」とし、パスキーの無い別の Chrome 149 以上の機械で判定する |
| P4 Safari・iPhone・Chrome 148 以前は今まで通り | 試験 T5（immediateGet false → 今の道）＋ iPhone で目視 |
| P5 パスワードのログインは変わらない | 試験（既存の LoginPage 試験すべて合格）＋ 反映後 14 日、自動点検の係（user 87）のログイン成功が毎日ある（reader） |
| P6 表・列を足さない | `git diff origin/main --name-only` に migrations・backend が無い |
| P7 文言は ja/en・金型・トークンだけ | `cd frontend && npm run check:i18n-missing-keys` が 0 で終わる（CI の必須チェックかは未確認）・ui-governance-gate が緑・`git diff origin/main -- frontend/src \| grep -nE '#[0-9a-fA-F]{3,8}\b\|rgb\(\|hsl\('` が空 |
| 試験 | passkey.test.ts に T1〜T3、LoginPage.test.tsx に T4〜T12（カード §3-3）が足され、frontend の試験がすべて合格 |

## §8 維持の仕組み

- 守り手: frontend/src/pages/login/LoginPage.test.tsx（T4〜T12）と frontend/src/lib/auth/passkey.test.ts（T1〜T3）。CI の frontend の試験で毎回走る。
- 試験（T1〜T12。始め直し・隠れている間・15 回の上限・busy 中・古い呼び出しを含む）が CI の frontend の試験に入り、今後の変更で壊れたら赤になる。
- KPI（PO のログインのうちパスキーの割合・目標 80%）は反映から 30 日後に reader で数える（Opus が予約する）。
- 仕様の正本は docs/specs/auth-login（README の子リンクに本フォルダを追加済み）。

## §9 外部・過去事例の参照と我々への応用

docs/handoff/passkey-autofill-first/evidence.md（2026-11-23〜24 取得の出典つき）に置く。要点:
- 業界団体（FIDO Alliance・2026-10 公表・15 社）: パスキーを先に出さない画面が 10 社中 8 社の「持っているのに使われない」の原因。1 社はパスキーを先に出せば利用が約 2 倍と見積もり。
- Dashlane（2023-10・ウェブ）: 自動の候補からの成功 92%（パスワード自動入力 54%）。
- adidas（2026-04）: 自動の候補＋自動登録で成功率 99% 超、「パスキーが無い」誤り 0.3% 未満。
- 適用の限界: どれも大きな一般向けサービスの数字。このアプリは使う人が十数人で、同じ割合になる根拠は無い。だから KPI は本番の実数で測る。
