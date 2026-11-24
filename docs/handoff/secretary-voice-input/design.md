# 秘書に声で話しかける — 設計（design）

状態（2026-11-24 追記）: **音声モード（交代で話す型）は §15 が正**（目標は kgi.md §5・PO 承認 2026-11-24「1」）。§3-2・§5-4 の録音の流れは B 用の古い記録。
状態: **聞き取りのやり方は A（ブラウザの聞き取り・無料）に決定（PO 2026-11-19「1」）。まず試しの便（§14）で iPhone のホーム画面のアプリで聞き取れるかを確かめる。§5 の B 用の backend・migration・月の上限（§7）は作らない**
目標: [kgi.md](kgi.md)（K1〜K6・PO 承認 2026-11-19「1」）／ 現在地: [docs/handoff/secretary-voice-input/recon.md](recon.md) ／ 調べ: [research.md](research.md)
関係 ADR: ADR-1056・ADR-1078・ADR-1080・ADR-027・ADR-067・ADR-144・ADR-136。新しい ADR: ADR-1082（聞き取り。ADR-1081 は別の件で使用済み）

## 1. 目的

手を使わずに秘書に用事を頼めるようにする。PC は「スペース長押しで欄に文字が入る」、スマホは「音声モードで話す→声で返る→また聞く」。

## 2. 対象と対象外

- 対象: 秘書の窓（`SecretaryChat`）の入力。聞き取りの口（backend）。使用量の表示。本番の画面のマイク許可（nginx）
- 対象外: kgi.md §3（請求書を音声だけで作る・秘書以外の画面・録音の保存）

## 3. 動きの流れ

### 3-1 PC（K1・K2・K5）

（１）入力欄が空で、スペースを押す → 既定の動き（空白を入れる）を止め、押し始めの時刻を覚える
（２）300 ミリ秒より前に離した → 空白を 1 つ入れる（普通の空白と同じ結果）
（３）300 ミリ秒押し続けた → マイクを開いて録音を始め、欄の上に「聞いています」を出す
（４）離した → 録音を止め、マイクを閉じる（線を全部止める）→ 聞き取りに送る → 文を欄に入れる（送らない）
（５）欄に文字があるときのスペース・キーの繰り返し（`e.repeat`）・日本語変換中（`e.isComposing`）は何もしない（普通の空白）

### 3-2 スマホ（K3・K4・K5・K6）

（１）入力欄の右のマイクの絵柄を押す → 音声モード。窓の中身を音声モードの画面に差し替える（スマホでは窓が画面いっぱい: recon §4）
（２）押したその場で、読み上げの AudioContext を起こし、マイクを開く（iPhone は押した中でしか音を出せないため）
（３）聞く → 話し始めを見つけ、1.2 秒静かなら区切る（§5-4）→ マイクを閉じる → 聞き取り → 吹き出しに出して、今の `send()` と同じ処理で秘書に送る
（４）返事を読み上げる（音声モードでは「声で返事」の切り替えに関係なく読む）。読み上げの間はマイクを閉じている（自分の声を拾わない・K5）
（５）読み終わったら（１）の状態に戻ってまた聞く
（６）✕ で抜ける → マイクを閉じ、読み上げも止める。会話は窓に残る
（７）8 秒話さなければ「聞いています」のまま待ち続ける。60 秒話さなければ音声モードを抜ける（マイクの開けっ放しを防ぐ）

### 3-3 予定の確かめ（K6）

- 音声モードで、予定の最後の下書き（`kind: "event"` かつ `ask` が無い）が来たら、「{用件}を{日付}{時刻}に入れますか？」と読み上げて聞く
- 答えを 1 か所の関数 `judgeYesNo(text)` で 3 つに分ける: はい／いいえ／分からない
  - はい → 下書きの「作る」と同じ処理で作る（§5-3 で 1 か所に出した関数）→「作りました」を読み上げ
  - いいえ → 作らない →「入れませんでした」
  - 分からない → もう 1 回だけ聞く。2 回目も分からなければ作らずに「画面で確かめてください」と言い、音声モードは続ける
- 「はい」が無い限り作らない（聞き違いで勝手に入れない）

## 4. 聞き取りのやり方（PO 決定: A・2026-11-19「1」。下の表は比べた記録として残す）

| 比べること | A. ブラウザの聞き取り | B. Google の聞き取り（おすすめ） |
|---|---|---|
| 費用 | 0 円 | 1 分 約 2.6 円。見込み 月 約 320 円（research §1） |
| 音の送り先 | ブラウザ会社の一般向けサービス（会社の契約の外） | 読み上げと同じ Google Cloud の契約 |
| iPhone のホーム画面のアプリ | 動くか**まだ確かめていない** | 録音は標準の仕組みで、送るのは自分の口 |
| 使用量を画面で見る | できない | できる（読み上げと同じ） |
| 準備 | 無し | Google 側で聞き取りを使えるようにする（PO の操作が要るかもしれない） |
| 作る量 | 小 | 中（口・DB の列・使用量の表示） |

- おすすめは B。理由: PC とスマホで同じ仕組みになる。読み上げと同じ契約に音を閉じ込められる。使用量を見られる（KGI の条件）
- B の前に、本番から 1 回試して事実をそろえる（stt-probe.sh: 今の鍵で使えるか・K2 の文がそのまま取れるか・速さ）
- 以下 §5 以降は B で書く。A になった場合は §5-1・§5-2・§7 が無くなり、§5-4 の録音がブラウザの聞き取りに置き換わる

## 5. 変更するファイル（B の場合）

### 5-1 backend

- migrations/20261119_xxxxxx_add_llm_usage_stt_seconds.sql（新規・冪等）
  - `ALTER TABLE public.llm_usage_events ADD COLUMN IF NOT EXISTS billed_seconds INTEGER;`
  - 使いみちの CHECK に `secretary_stt`、sdk の CHECK に `google-stt-rest`、provider の CHECK に `google_stt` を足す（読み上げの migration `migrations/20261117_100100_add_llm_usage_tts_characters.sql` と同じ形）
- `backend/app/services/llm_budget.py:159-185` 一覧に同じ 3 つを足す（DB の CHECK と試験で一致を見る仕組みはそのまま）。:400-419 `billed_seconds` を書けるようにする
- backend/app/services/secretary_stt.py（新規）`backend/app/services/secretary_tts.py` と同じ形
  - 鍵は読み上げと同じ `GOOGLE_TTS_SA_KEY_FILE`（新しい鍵は置かない）。札を作る関数は `secretary_tts._bearer_token` を共通に使う（同じ式を 2 か所に書かない）
  - 宛先・モデル・場所は probe で 200 になった組み合わせ 1 つを定数で持つ
  - `read_month_seconds(db)`・`check_monthly_cap()`・`transcribe(audio, mime, user_id, tenant_id)`
  - 使用量は `record_usage_isolated` で `purpose="secretary_stt"`・`sdk="google-stt-rest"`・`billed_seconds=` Google が返す `metadata.totalBilledDuration`
- `backend/app/routers/assistant.py` に `POST /assistant/transcription`（守りは `_SECRETARY_DEPENDENCIES`）
  - 本文は音そのもの。受ける形は `audio/webm`・`audio/mp4` だけ。1 MB を超えたら 413
  - 月の秒数を読んだら、Google を待つ前に取引を閉じる（`:622-627` と同じ）
  - 返す: `{ "text": "..." }`。音は保存しない・記録にも残さない
- `backend/app/routers/tcg_analysis_dashboard.py:694`・:939・:1050 に今月の聞き取りの分数と上限を足す
- 試験: 口の守り・形・大きさ・上限・Google の失敗・使用量の記録・一覧と CHECK の一致

### 5-2 本番の画面のマイク許可

- `nginx/nginx.conf:100` `microphone=()` → `microphone=(self)`（自分の画面だけ許す。他の画面に埋め込まれたときは許さない）
- `nginx/nginx.conf:323`（/grafana/）は変えない

### 5-3 frontend

- `frontend/src/constants/icons.tsx` にマイクの絵柄を登録（`@heroicons/react` の Microphone。金型の一覧に足す）
- `frontend/src/features/secretary/secretaryApi.ts` に `transcribeSecretaryAudio(blob)` を足す
- `frontend/src/features/secretary/useSecretaryListen.ts`（新規）マイクを開く・録音・区切り・閉じる。§5-4
- `frontend/src/features/secretary/SecretaryDraftEvent.tsx:58-68` の中身の組み立てを `buildEventPayload()` に出し、下書きの「作る」と音声モードの「はい」の両方がこれを使う
- frontend/src/features/secretary/secretaryVoiceAnswer.ts（新規）`judgeYesNo()`。はい・いいえの言葉の一覧はここ 1 か所
- frontend/src/features/secretary/SecretaryVoiceMode.tsx（新規）音声モードの中身（状態の文字・✕）。色・寸法は var() だけ
- `frontend/src/features/secretary/SecretaryChat.tsx`
  - `send()`（:97-147）を「文を受け取って送る」形に分け、ボタン・音声モードの両方から呼ぶ
  - `Textarea`（:239-247）に `onKeyDown`・`onKeyUp` でスペース長押し（§3-1）
  - スマホ（`isMobile`）のときだけ欄の右にマイクの `IconToggleButton`
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じ鍵（聞いています・考えています・話しています・マイクが使えない・入れますか？ など）
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:640-662` の下に聞き取りの今月の分数

### 5-4 録音と区切り（`useSecretaryListen`）

- `navigator.mediaDevices.getUserMedia({ audio: true })` → `MediaRecorder`（形はブラウザに任せる: Chrome は webm、Safari は mp4）
- 音の大きさは `AnalyserNode` で 50 ミリ秒ごと。話し始め＝一定より大きい音が 150 ミリ秒続く。区切り＝話し始めの後 1.2 秒静か。1 回の最長 30 秒（Google の 1 分の上限より短く）
- 止めるときは `MediaStreamTrack.stop()` を全部呼ぶ（K5: 聞いていない間はマイクが閉じている）

## 6. 1 か所にすること（SSOT）

- 使いみち・sdk・provider の一覧: `backend/app/services/llm_budget.py` と DB の CHECK（今の仕組み）
- Google の鍵と札: `backend/app/services/secretary_tts.py` の 1 か所（聞き取りもそれを使う）
- 予定の中身の組み立て: `buildEventPayload()` の 1 か所
- はい・いいえの言葉: secretaryVoiceAnswer.ts の 1 か所
- 画面の文字: `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`

## 7. 月の上限（B の場合・PO の判断待ち）

- 案: 月 600 分（約 9.6 ドル・約 1,530 円）で止める。止まったら「今月の聞き取りの上限に達しました」と出す

## 8. 測り方（受入）

| 基準 | 検証方法 |
|---|---|
| K1 | 本番の PC（Chrome）で長押し 10 回・文の途中のスペース 10 回。欄と「聞いています」を見る |
| K2 | 本番の PC で決まった文を 10 回。欄の文・話し終わりから欄に出るまでの秒（画面の記録の時刻）・送られていないこと |
| K3 | PO のスマホで 5 回。触らずに 3 往復 |
| K4 | PO のスマホで 10 回。区切った時刻から声が出始める時刻まで（画面の記録） |
| K5 | 本番でマイクの使用中の印（ブラウザの表示）と `getUserMedia` の線の数。閉じた後 0 |
| K6 | PO のスマホで予定を 5 回頼む。毎回「入れますか？」が先に出る。「いいえ」で入らない |
| 使用量 | 使用量の画面の分数と、Google の返した秒の合計を 10 回分照らす |

## 9. 便の分け方

- 便0: 本番から 1 回試す（PO の `!` 実行）→ やり方と上限を PO が決める → ADR-1081 起案
- 便1（危険 PR: migrations を含む・ADR-136 の GO 記録）: §5-1 backend ＋ §5-2 nginx
- 便2: §5-3 frontend（便1 が本番に入ってから）
- 便3: 本番で K1〜K6 を測る

## 10. 危ないことと対処

- iPhone で、マイクを開いている間は音が小さい受話口から出ることがある → 読み上げの間はマイクを閉じる設計（§3-2（４））。K3 で確かめる
- 聞き違いで予定が入る → 「はい」が無い限り作らない（§3-3）
- マイクの開けっ放し → 60 秒で抜ける・閉じるときに線を全部止める（§3-2（７）・§5-4）
- 費用が増える → 月の上限（§7）と使用量の画面

## 11. 戻し方

- 画面: 便2 の PR を戻す（マイクの絵柄とスペース長押しが消えるだけ）
- 口: 便1 の PR を戻す。足した列と CHECK の値は残しても害が無い（読み上げのときと同じ扱い）
- マイク許可: `nginx/nginx.conf:100` を `microphone=()` に戻す

## 12. 外部・過去事例の参照と我々への応用

research.md §3（ChatGPT の音声モード・2023-09-25 公開。形の見本としてだけ使う）

## 13. 維持の仕組み

- 守り手: 秘書の窓の試験（`frontend/src/features/secretary/useSecretaryListen.test.ts`・`frontend/src/features/secretary/SecretaryChat.test.tsx`）を CI の必須の確かめが毎回流す。マイクの許可は `nginx/nginx.conf` の app の枠 1 か所だけ（ADR-1082 What 2）
- A を選んだので、聞き取りは使用量の台帳に書かない（費用 0 円）。下の 2 行は B を選んだときのもの
- 一覧と CHECK の一致は既存の試験が見張る
- 聞き取りの月の分数は使用量の画面で毎月見える
- 声で会話（§15）: 試験 T1〜T13（`frontend/src/features/secretary/SecretaryChat.test.tsx`）と、はい・いいえの判定の試験（新しいファイル secretaryVoiceAnswer.test.ts）を CI の必須の確かめが毎回流す。V3 は T5〜T7、V4 は T8、V2 の「秘書の声を拾わない」は T4・T10〜T13 で守る（§15-12 の表）

## 補足: 次のテーマ（会話の相棒）への備え（2026-11-19）

- PO 決定（11/19「1」）: 声の機能を先に仕上げ、秘書を会話の相棒にする作り直しは次のテーマにする
- 聞き取りの部品（`frontend/src/features/secretary/useSecretaryListen.ts`・§5-4）は「声 → 文字」だけを返し、秘書の指示・会話の扱いを持たない
- 秘書へ送る処理は今の `send()` を「文を受け取って送る」形にした 1 か所だけ（§5 の :94）。次のテーマで会話の扱いを変えても、聞き取りの部品は変えずに済む

## 14. 試しの便（便T・A を選んだ後の最初の便）

### 14-1 なぜこの形か

- 確かめたいこと: iPhone のホーム画面に置いたアプリ（standalone）の中で、ブラウザの聞き取りが動くか（research §1・§6）
- 別の試しのページにしない理由: ホーム画面のアプリには住所の欄が無く、新しいページへ行くにはメニューの追加が要る。秘書の窓は今でも開ける（`frontend/src/features/secretary/SecretaryChat.tsx:223-228`）。秘書の窓を使えるのは super admin だけ（同 :4・:260-267）＝ PO だけが見る
- 作るものは本番の機能の一部としてそのまま使う（聞き取りの部品・マイクの印）。試しのためだけの捨てるコードは作らない

### 14-2 変えるファイル（変更前 → 変更後）

（１）`nginx/nginx.conf:100`
- 前: `add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;`
- 後: `add_header Permissions-Policy "camera=(), microphone=(self), geolocation=()" always;`
- `nginx/nginx.conf:323`（/grafana/）は変えない
- 本番への届き方: nginx の設定が変わった配備では nginx の入れ物を作り直す（`.github/workflows/deploy.yml:564-584`）。作り直しの間 2〜3 秒、画面が開けない（同 :574 の注記）。作り直しの前に `nginx -t` を通し、だめなら作り直さない。後の確認がだめなら前の設定に自動で戻す（同 :578-579・:670）

（２）`frontend/src/constants/icons.tsx`
- :32-53 の solid の import に `MicrophoneIcon` を足す（`@heroicons/react` 2.2.0 に有る: `node_modules/@heroicons/react/24/solid/MicrophoneIcon.js`）
- 末尾の `LeadChatIcon` の前に `export const SECRETARY_ICONS = { listen: hi(MicrophoneIcon) } satisfies Record<string, Icon>;` を足す（包み方は :95-99 と同じ `hi()`）

（３）`frontend/src/features/secretary/useSecretaryListen.ts`（新規）
- 声 → 文字だけを受け持つ。秘書への送り・会話の扱いは持たない（§補足）
- `getSpeechRecognition()`: `window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null`（MDN「Using the Web Speech API」の書き方）。型は同じファイルに最小の interface を書く
- `classifyListenError(code: string): ListenError | null`（1 か所の対応表。`null` は「何も出さない」）
  - `not-allowed` → `notAllowed` ／ `service-not-allowed` → `serviceNotAllowed` ／ `no-speech` → `noSpeech` ／ `audio-capture` → `audioCapture` ／ `network` → `network` ／ `language-not-supported` → `language` ／ `aborted` → `null`（自分で止めたとき・何も出さない）／ それ以外 → `other`
  - 値の一覧の出典: MDN `SpeechRecognitionErrorEvent.error`（Context7 `/mdn/content`）
- `useSecretaryListen(onText: (text: string) => void)` が返すもの: `supported`・`listening`・`interim`・`error`（`ListenError | "unsupported" | null`）・`start()`・`stop()`・`abort()`
  - 持っている部品は `useRef` に 1 つだけ置く（`recRef`）。`listening` は state で持つ
  - `onText` も `useRef` に入れ、描くたびに最新に入れ替える（受け口はいつも最新の `onText` を呼ぶ）
  - `start()`: 押したその場で呼ぶ。次の順に行う
    1. `recRef.current` が有れば何もせず終わる（二重に起こさない。二度押しでも部品は 1 つ）
    2. `error=null`・`interim=""` に戻す（前の知らせを消す）
    3. 部品が無ければ `error="unsupported"` にして終わる
    4. 作って `recRef.current` に入れ、`lang="ja-JP"`・`interimResults=true`・`continuous=false`・`maxAlternatives=1` を付け、`result`・`error`・`end` の受け口を付ける
    5. `rec.start()` を呼び、続けて `listening=true` にする（`start` の受け口を待たない。押した直後から「聞いています」を出し、印を押された形にする）
    6. `rec.start()` が投げたら `recRef.current=null`・`listening=false`・`error="other"`
  - `result`: 途中の文は `interim` に入れる。確定した文（`isFinal`）は前後の空白を落として、空でなければ `onText` を 1 回呼ぶ
  - 受け口（`result`・`error`・`end`）はどれも、まず `recRef.current` が自分（その受け口を付けた部品）かを見る。違えば何もしない（止めた古い部品の知らせで今の状態を変えない）
  - `error`: `classifyListenError` の結果が `null` でなければ `error` に入れる
  - `end`: `listening=false`・`interim=""`・`recRef.current=null`（`error` は消さない。知らせは次に押すまで残す）
  - `stop()`: `recRef.current?.stop()` だけ呼ぶ。確定の文を受け取るため、片付けは `end` に任せる
  - `abort()`: `recRef.current?.abort()` を呼び、`end` を待たずにその場で `recRef.current=null`・`listening=false`・`interim=""` にする（窓を閉じる・送る・画面から消えるとき。止めた部品の後の知らせは上の「自分か」の確かめで捨てる）
  - 画面から消えるとき（useEffect の後始末）に `abort()`

（４）`frontend/src/features/secretary/SecretaryChat.tsx`
- `const listen = useSecretaryListen((heard) => setText((prev) => (prev + heard).slice(0, SECRETARY_MAX_TEXT)));`
- `close()`（:65-76）の先頭で `listen.abort()`
- `send()`（:97-100）の `voice.stop()` の隣で `listen.abort()`
- 入力欄（:239-247）と同じ行に、`isMobile` のときだけ `IconToggleButton`（`frontend/src/components/IconToggleButton.tsx`）を置く
  - `pressed={listen.listening}`・`iconOff`/`iconOn` は `SECRETARY_ICONS.listen`・`size="md"`・`disabled={sending}`
  - `onClick`: 聞いていれば `listen.stop()`、いなければ `listen.start()`
  - `aria-label`: 聞いていれば `t("secretary.listen.stop")`、いなければ `t("secretary.listen.start")`
  - 部品が無い端末でも印は出す（押すと「使えません」と出る。試しの便で端末ごとの結果を見るため）
- 入力欄の下に `<p className="secretary-chat__listen-status" role="status">`: 聞いている間は `t("secretary.listen.listening")` と途中の文、`error` があれば `t(\`secretary.listen.error.${error}\`)`。どちらも無ければ出さない
- 送るのは今までどおりボタンだけ（聞き取った文を勝手に送らない・K2）

（５）`frontend/src/features/secretary/SecretaryChat.css`
- `.secretary-chat__input-row { display: flex; align-items: flex-end; gap: var(--space-2); }`（`Textarea` は `fullWidth` のまま）
- `.secretary-chat__listen-status { margin: 0; font-size: var(--font-sm); color: var(--text-secondary); }`（同じファイルの `.secretary-draft__hint` と同じトークン）

（６）`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` の `secretary` の下に `listen` を足す（同じ鍵）
- ja: `start` 話して入力する ／ `stop` 聞くのをやめる ／ `listening` 聞いています… ／ `error.unsupported` この画面では声の聞き取りが使えません ／ `error.notAllowed` マイクが許可されていません。端末の設定でマイクを許可してください ／ `error.serviceNotAllowed` この端末では声の聞き取りが許されていません ／ `error.noSpeech` 声が聞こえませんでした。もう一度押して話してください ／ `error.audioCapture` マイクが使えませんでした ／ `error.network` 聞き取りの通信に失敗しました。もう一度お試しください ／ `error.language` 日本語の聞き取りに対応していません ／ `error.other` 聞き取れませんでした。もう一度お試しください
- en: 同じ意味の英語

（７）試験
- `frontend/src/features/secretary/useSecretaryListen.test.ts`（新規）: 対応表（8 つ）・部品が無いと `unsupported`・`start` で `lang` などの設定・途中の文・確定で `onText` 1 回・空の確定で呼ばない・画面から消えると `abort`・続けて 2 回 `start()` しても部品は 1 つ・前の失敗の後に `start()` すると `error` が `null` に戻る・`start()` の直後に `listening` が `true`・`rec.start()` が投げると `error` が `other` になり、次の `start()` で部品が作られる・`error` の後に `end` が来ても `error` が残る・`abort()` の直後に次の `start()` で新しい部品が作られ、古い部品の `end` が来ても `listening` は `true` のまま・`abort()` の後に古い部品から `result`・`error` が来ても `onText` は呼ばれず `error` も変わらない・`stop()` の後の `end` で `listening` が `false` になる
- `frontend/src/features/secretary/SecretaryChat.test.tsx` に足す: `isMobile=false` で印が無い・`isMobile=true` で印が有る・押すと「聞いています」・確定の文が欄に入り送られない（送る口が呼ばれない）・部品が無いと「使えません」・窓を閉じると `abort`
- 試験の中に日本語の文字を直接書かない（`frontend/src/features/secretary/useSecretaryVoice.test.ts:4-6` と同じ書き方）

### 14-3 触らないもの

- backend・migrations・deploy.yml・`nginx/nginx.conf:323`・読み上げ（`frontend/src/features/secretary/useSecretaryVoice.ts`）・下書きの部品
- PC のスペース長押し・音声モード・「入れますか？」（K1〜K6 の本体は次の便）

### 14-4 試しの合格（PO がスマホで見る）

| 基準 | 検証方法 |
|---|---|
| T1 印が出る | ホーム画面のアプリで秘書の窓を開き、入力欄の右にマイクの印が有る（○×） |
| T2 聞き取れる | 印を押し「明日10時から打ち合わせの予定を入れて」と言う。欄に文が入り、送られない。5 回のうち何回できたか・出た文・出た知らせ |
| T3 マイクが閉じる | 止まった後、iPhone の画面の上のマイクの印（橙の点）が消える（○×） |
| T4 比べ | 同じことを Safari で開いた画面でも 1 回。欄に文が入れば○、入らなければ×と出た知らせ（ホーム画面のアプリと違うかを見るための記録。合否には使わない） |

- T3 が×（止めた後もマイクの印が消えない）なら、T2 の回数に関わらず止めて PO に知らせる（K5 に反するため）
- それ以外の進み方は T2 の回数だけで決める（1 回でも出た知らせはすべて記録する）
  - 5 回中 4〜5 回: A のまま次の便（PC のスペース長押し・音声モード・K6）の設計へ進む
  - 5 回中 0〜3 回: どの知らせが出たかに関わらず止める。出た知らせと T4 の結果を PO に見せ、「Safari で使う」「B（有料）に変える」「もう一度 5 回試す」のどれにするかを聞く

### 14-5 戻し方

- この便の PR を戻す。印が消え、マイクの許可は `microphone=()` に戻る

### 14-6 音の送り先（事実と未確認）

- MDN: 一部のブラウザでは音がウェブのサービスに送られて聞き取られる（research §1-A）
- iPhone で音がどこに送られるかは **まだ確かめていない**（PO への 11/19 の説明で「Google」と書いたのは、iPhone については根拠が無かった）

### 14-7 審査の記録

- 1 回目（クラウドの Opus・2026-11-19 13:08 UTC）: REVISE。必須 3 件（二重 start・知らせが消えない・T2/T4 の判定が一つに決まらない）。file:line は 15 件すべて一致。→ §14-2（３）・（７）と §14-4 を直した
- 1 回目で「未確認」とされた `MicrophoneIcon`: 手元の `frontend/node_modules/@heroicons/react/24/solid/MicrophoneIcon.js` が有る（2.2.0）
- 2 回目（クラウドの Opus・2026-11-19 13:13 UTC）: REVISE。1 回目の必須 3 件は直った。新しい必須 1 件（カードの作業場所の作り方がクラウドの決まり `scripts/agent-hooks/cloud/rules.md:15` と違う）→ カードを `git switch -C` に直した。推奨 1〜5（abort 後の片付け・試験 3 件・戻りの型・T3 が×なら止める・印の置き場所）も直した。推奨 6（preflight）はカードに書いた
- 3 回目（クラウドの Opus・2026-11-19 13:17 UTC）: **APPROVE**。新しい必須なし。新しい推奨 3 件（試験 2 件・カードの作業場所の場所の明記・`onText` を ref に持つ）も直した
- 実装 1 回目（クラウドの Sonnet・2026-11-19 13:20 UTC）: カード手順 4 の `scripts/dev/executor-preflight.sh` がクラウドで落ちて BLOCKED（gh 認証と api.github.com への道が無い）。ファイルは変えていない。カード手順 4 を「`origin/main` があるかだけ見る」に直した

## 15. 音声モード（交代で話す型）— ブラウザの聞き取りで作る（2026-11-24 版）

- 状態: 設計案作成済み（Claude Opus 2026-11-24）・設計審査は §15-12・PO の目標承認済み（kgi.md §5）・実装未着手（実装は PO の実装承認とカード `docs/handoff/secretary-voice-input/card-binV.md` が揃ってから）
- §3-2・§5-4 は B（録音して Google で聞き取る）を前提に書いた古い流れ。A（ブラウザの聞き取り）に決まった今は、この §15 が正。§3-3（予定の確かめ）は §15-5 で今のコードに合わせて書き直した。

### 15-1 目的と、利用者に見える変化（PO 2026-11-24）

- PO の言葉: 「これが成功したら横展開していろいろなことを音声で依頼できるように拡張したい」「まずは予定と請求書で小さく進める」
- 奥の目的: 手を使わずに、秘書に用事を頼めるようにする（kgi.md §1 のまま）。

| | 今（origin/main） | 後 |
|---|---|---|
| 切り替え | 「声で返事」: 返事を読み上げるだけ（`frontend/src/features/secretary/SecretaryChat.tsx:59`・`:261-262`） | 「声で会話」: 入れると、すぐ聞き始める。話し終わると自動で送る。返事を読み上げる。読み終わるとまた聞く |
| 話し終わり | 送るのは人がボタンを押す（同 `:304`） | 話し終わってから 1.0 秒、新しい文字が来なければ自動で送る（声で会話の間だけ） |
| 予定の最後の下書き | 読み上げない（同 `:149-150`） | 「{用件}を{日時}に入れますか？」と読み上げる。「はい」で作る。「いいえ」で作らない |
| 請求書の下書き | 読み上げない（同 `:147-148`） | 決まった文「請求書の下書きを出しました。画面で中身を確かめて、作るボタンを押してください」だけを読む。会社名・金額は読まない |
| 声の「はい」で請求書 | 作れない | 作れないまま（PO 2026-11-23「1」・kgi.md §5 V4） |
| 声で会話を切る | — | 今の「声で返事」を切るのと同じ（読み上げを止め、マイクも止める） |

### 15-2 対象と対象外

- 対象: `frontend/src/features/secretary/` の 4 ファイル（`frontend/src/features/secretary/SecretaryChat.tsx`・`frontend/src/features/secretary/SecretaryDraftEvent.tsx`・新しいファイル secretaryVoiceAnswer.ts・試験）と翻訳 2 ファイル。
- 対象外: backend・DB・migration・nginx・deploy.yml・容器（`secretary-codex`）・AI への指示文（secretary-codex の指示文と返事の形）・聞き取りの部品 `frontend/src/features/secretary/useSecretaryListen.ts`・読み上げの部品 `frontend/src/features/secretary/useSecretaryVoice.ts`。**ChatGPT の無料分と Google の読み上げの無料枠の中だけで動く（新しい有料のサービス 0 件）**。
- 対象外（次のテーマ）: 予定と請求書以外の用事（横展開）。見積もりを作る機能。請求書を声だけで作ること。

### 15-3 事実（根拠つき）

| # | 事実 | 根拠 |
|---|---|---|
| E1 | 秘書の考える部分は ChatGPT（codex / gpt-5.6-terra） | 本番 DB `ai_job_assignments`（reader 鍵 2026-11-24 10:41 JST） |
| E2 | ChatGPT の呼び出しは 11/11〜11/22 の 135 回のうち 134 回成功・1 回失敗（`unreadable`）。回数の制限で失敗した記録は 0 件 | 本番台帳 `ai_ro.public__llm_usage_events`（purpose `secretary_intent`・sdk `codex-cli`）2026-11-24 19:23 JST の読み取り |
| E3 | 11 月の読み上げは 33 回・520 字。止める線は 90 万字 | 同じ台帳（purpose `secretary_tts`）・`backend/app/services/secretary_voice.py:22` |
| E4 | 聞き取りは話している間ずっと聞く形で本番に出ている。PO が PC で動くのを確かめた（2026-11-24「1,PCで問題なく動作した」） | `frontend/src/features/secretary/useSecretaryListen.ts:118-121` |
| E5 | 聞き取りがブラウザの都合で終わると、画面は人の操作なしで聞き直す（最大 5 回） | 同 `:147-155`・`:87` |
| E6 | 規格では、聞き取りを始める `start()` が投げる失敗は「画面が動いていない」「もう始まっている」の 2 つだけ。人の操作の中で呼ぶ決まりは無い | Web Speech API の規格（Context7 `/webaudio/web-speech-api`・index.bs:657・:660） |
| E7 | 読み上げの音の準備（AudioContext）は、切り替えを押した処理の中で作る | `frontend/src/features/secretary/useSecretaryVoice.ts:48-53`・`frontend/src/features/secretary/SecretaryChat.tsx:101-110` |
| E8 | 予定の「作る」は下書きの部品の中の `submit()` 1 か所。作れる条件は `canCreate` | `frontend/src/features/secretary/SecretaryDraftEvent.tsx:46-51`・`:53-74` |
| E9 | 送るときは今も読み上げを止め、聞き取りを捨てる（自分の声を拾わない） | `frontend/src/features/secretary/SecretaryChat.tsx:123-124` |
| E10 | 秘書が会社のデータを読むのは backend の検索だけ。AI に会社のデータは渡していない | ADR-1056・`backend/app/routers/assistant.py:192-205`（送る本文は文・今・決まり・カルテだけ） |

### 15-4 流れ（声で会話の 1 往復）

（１）「声で会話」を入れる → その処理の中で読み上げの音の準備をし（E7）、聞き取りを始める（`listen.start()`）。
（２）話す → 文字が欄に出る（今のまま）。
（３）この回に聞き取った文字が欄にあり（手で打った文だけのときは送らない）、途中の文字が空で、聞いている状態のまま 1.0 秒（定数 `VOICE_SEND_SILENCE_MS = 1000`）新しい文字が来ない → 今の `send()` を呼ぶ。`send()` は今のまま聞き取りを捨て、読み上げを止めてから送る（E9）。
（４）返事が来る → 種類ごとに読む文を 1 つ決めて読む（§15-6 の表）。
（５）読み終わった（`speak` が `"ok"`）、かつ声で会話のまま、かつ窓が同じ会話のまま、かつ**読み始めた後に新しい送りも新しい読み上げも無い**（回数の印 `turnRef` が読み始めたときと同じ。読み上げはどれも、始める前にマイクを止め、印を 1 つ進める）→ 聞き取りを始める（`listen.start()`）→（２）に戻る。
（６）読み上げが `"failed"` か `"cap"` → 今と同じ知らせを出し、声で会話を切る（マイクも止める）。文字のチャットは使える。
（７）聞き取りが 5 回続けて何も聞き取れずに止まった（E5）→ 今と同じ「声が聞き取れませんでした」。声で会話は入ったまま。マイクの印を押すと再開する。
（８）窓を閉じる・切り替えを切る → 今の `close()`・`onVoiceChange(false)` のまま全部止める。

- 自動で送るのは「声で会話」が入っている間だけ。切れているときは今のまま人が送る（ADR-1082 What 4「勝手に送らない」は、切れているときの決まりとして残す。入れたときに自動で送ることは PO 2026-11-24「1」で承認）。
- 聞いている間は送るボタンを押せない今の決まり（`:304`）はそのまま。自動で送るのはタイマーだけ。
- 読み上げの前には必ずマイクを止める（審査 N1）: 読み上げはどれも、始める前に聞き取りを止め、この回に聞き取った印を外す。ボタンで作ったときの知らせや失敗の知らせも同じ。ADR-1082 What 5 の「読み上げている間はマイクを止める」に合わせる。
- 回数の印が要る理由（審査 B2）: 読み上げを途中で止めても `speak` は `"ok"` を返す（`frontend/src/features/secretary/useSecretaryVoice.ts:84`・`:96`・`:100`）。読み上げ中に手で送ると、前の読み上げの終わりでマイクが開き、次の返事の声を拾う。送るたび・切り替えのたび・閉じるたびに印を 1 つ進め、古い読み上げの終わりではマイクを開かない。

### 15-5 予定の確かめ（声の「はい」）

- 予定の最後の下書き（`kind: "event"` かつ `ask` が無い）が来たら、確かめ待ちの印 `pendingConfirm = { id, tries: 0 }` を持つ。
- 確かめ待ちの間に送られた文は、ChatGPT に送らない。新しい 1 か所の関数 `judgeYesNo(text, yesWords, noWords)`（新しいファイル frontend/src/features/secretary/secretaryVoiceAnswer.ts）で 3 つに分ける。語の一覧は翻訳キー `secretary.voiceMode.yesWords`・`noWords` の 1 か所（§15-10）。

| 答え | 動き | 読む文 | 読んだ後にまた聞くか |
|---|---|---|---|
| はい | 下書きの部品の `submit()` を呼ぶ（部品に `ref` で口を 1 つ出す。中身は今の `submit()` と同じ 1 か所・E8）。作れたら今の `markCreated` | 「予定を作りました」（今の `secretary.created.event`） | 聞く（声で会話の間） |
| はい だが `canCreate` が偽・保存中 | 作らない。確かめ待ちを外す | 「画面で確かめて、作るボタンを押してください」 | 聞く |
| はい で作るのに失敗（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:70-72`） | 下書きの部品の今の失敗の表示のまま。確かめ待ちを外す（部品に失敗を知らせる口 `onVoiceFailed` を 1 つ足す） | 「画面で確かめて、作るボタンを押してください」 | 聞く |
| いいえ | 作らない。今の `markCancelled` | 「入れませんでした」 | 聞く |
| 分からない（1 回目） | 作らない。もう 1 回だけ聞く | 「はい、か、いいえで答えてください」 | 聞く（答えを受けるため） |
| 分からない（2 回目） | 作らない。確かめ待ちを外す | 「画面で確かめて、作るボタンを押してください」 | 聞く |

- 下書きの用件・始まり・終わりのどれかが空（`EventDraftData` の `title`・`start`・`end` は `string | null`・`frontend/src/features/secretary/secretaryApi.ts:41-43`）のときは、確かめ待ちにせず「画面で確かめて、作るボタンを押してください」を読む。
- `judgeYesNo` の決まり: 文を NFKC にして英字を小文字にする。日本語の語は句読点と空白を除いた形で、英語の語は除く前の形で比べる。否定の語が 1 つでもあれば「いいえ」（**否定を先に見る**。「はい、いや違う」は「いいえ」）。否定が無く、**文の頭が肯定の語で始まる**とき「はい」（「ええと」は「ええ」で始まるので、肯定の語から「ええ」を外す）。英語は単語の区切りで比べる（"look" を "ok"、"know" を "no" と見ない）。どちらでもなければ「分からない」。
- 確かめ待ちの間に人が画面の「作る」「やめる」を押したら、確かめ待ちを外す（今の `markCreated`・`markCancelled` の中で外す）。
- 確かめ待ちは、声で会話が切れているときは作らない（文字のチャットの動きは変えない）。

### 15-6 返事ごとに読む文

| 返事 | 読む文 | 今との差 |
|---|---|---|
| 聞き返し（`kind: "unknown"`） | AI の `reply`（今のまま `:152-153`） | なし |
| 予定のまだ聞く欄（`ask` あり） | 今のまま `secretary.ask.*`（`:143`） | なし |
| 予定の最後の下書き | 「{用件}を{日時}に入れますか？」（新しい翻訳キー。日時は今の作る小窓と同じ `formatDraftDateLine`（`frontend/src/pages/schedule/schedule-utils.ts:119`）で組む。例「11月10日(火) 午前10時～午前11時」） | 新しく読む |
| 請求書の下書き | 決まった文（新しい翻訳キー）。会社名・金額・品名は読まない | 新しく読む |
| 失敗の文（`secretary.error.*`） | その文 | 新しく読む（声で会話の間だけ） |
| 作った知らせ | 今のまま（`:176`） | なし |

- 請求書で会社名を読まない理由: 読み上げは backend の口から Google に文を送る（ADR-1080 What 1・What 3）。会社名・金額を Google に送る道を新しく作らない。
- 予定の用件は、PO が話した言葉を ChatGPT が書き直したもの。今も「声で返事」のとき聞き返しの文は Google に送っている。新しい種類のデータを送る道ではない。
- 請求書の下書きを読んだ後もマイクは開く。そこで「はい」と言っても、普通の文として ChatGPT に送られるだけで、請求書は作られない（請求書を作る POST はボタンからだけ・`frontend/src/features/secretary/SecretaryDraftInvoice.tsx:124`・`:283`）。無料プランの回数を 1 回使う。

### 15-7 画面（金型・翻訳）

- 部品は今のものだけ（`Toggle`・`IconToggleButton`・`Textarea`・`Button`・`ChatBubble`）。新しい金型・色・寸法は無い（ADR-067・ADR-144）。
- 翻訳キー（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー）: `secretary.voiceToggle` の文を「声で会話」に変える。新しいキー: `secretary.voiceMode.confirmEvent`・`secretary.voiceMode.invoiceReady`・`secretary.voiceMode.notCreated`・`secretary.voiceMode.askAgain`・`secretary.voiceMode.checkScreen`・`secretary.voiceMode.yesWords`・`secretary.voiceMode.noWords`。
- 日本語の直書きは CI の `local/no-japanese-literal` が止める（`frontend/eslint.config.js` の秘書の窓の override・ADR-1087）。`judgeYesNo` の語の一覧は翻訳キーに置く（§15-10 で決定）。

### 15-8 危ない点と手当て

| 危ない点 | 手当て | 確かめ |
|---|---|---|
| 秘書の声をマイクが拾い、自分の声を送る | 送る前に聞き取りを捨てる（E9）。読み上げの間は聞き取りを始めない（読み終わってから始める・§15-4（５）） | V2 で 3 往復して、秘書の声が欄に入らない |
| 聞き違いで予定が入る | 「はい」が無い限り作らない。否定を先に見る。肯定は文の頭だけ・英語は単語の区切り（§15-5） | V3「いいえ」5 回で 0 件・試験で「ええと」「let me look」が「はい」にならない |
| 読み上げを途中で止めた後にマイクが開き、次の返事の声を拾う（審査 B2） | 回数の印（§15-4（５）） | 試験 T10・V2 |
| マイクが開いたままボタンで作り、作った知らせの読み上げを拾って勝手に送る（審査 N1） | 読み上げる前に必ずマイクを止め、聞き取った印を外す（§15-4（５）） | 試験 T11・V2 |
| 秘書の読み上げの途中で「作る」ボタンを押し、前の読み上げの終わりでマイクが開き、次の知らせを拾う（審査 N2） | 読み上げのたびに回数の印を 1 つ進め、古い読み上げの終わりではマイクを開かない（§15-4（５）） | 試験 T12・V2 |
| 英語の画面で「yes」と話しても、聞き取りは日本語に固定（`frontend/src/features/secretary/useSecretaryListen.ts:118`）なので「イエス」になる | 今回は日本語だけで使う。英語の語は試験のためだけ | 対象外（英語の聞き取りは別テーマ） |
| 声で会話を入れたとき、手で打った文が勝手に送られる | この回に聞き取った文字があるときだけ送る（§15-4（３）） | 試験 T2 |
| 話の途中の間（ま）で送られる | 1.0 秒待つ。途中の文字があれば送らない | V1 で 10 回。送られた文が話した文と同じか |
| iPhone で、読み終わった後に人の操作なしで聞き始められない【未確認】 | 規格には禁止は無い（E6）。動かなければ、マイクの印を 1 回押せば続く（§15-4（７）と同じ）。**それでも予定と請求書は頼める** | V6。iPhone の結果で「1 回押す型」に決めるかを PO に聞く |
| iPhone で、マイクを使った後の読み上げが小さい受話口から出る【未確認】（§10 の報告） | 読み上げの前に聞き取りを捨てる（E9）。直らなければ PO に知らせる | V6 |
| ChatGPT の無料分の回数の制限【未確認・公式の数は確かめていない】 | 制限で失敗したら、今の失敗の文を読み、声で会話は続く | E2（今まで 0 件）・V5 の間の台帳の失敗の数 |
| 返事までの秒数【未確認・本番で測った値なし】 | 待つ間は今の考え中の吹き出し（`secretary.thinking`） | kgi.md K4（10 秒以内 9/10）を V の測りと一緒に測る |

### 15-9 戻し方

- この便の PR の merge commit を revert する。DB・設定の変更は無い。切り替えは「声で返事」に戻る。

### 15-10 実装の前にカードで決めること（設計の残り 0 件にするため）

- `judgeYesNo` の語の一覧の持ち方（日本語の直書きの検査に当たらない形）: 翻訳キー `secretary.voiceMode.yesWords`・`noWords`（`|` 区切り）に置き、`t()` で読んで渡す。ja と en で同じキー。英語の画面では英語の語（yes・no 等）。→ 決定。
- 日時の読み方: `formatDraftDateLine` を使う（新しい書式を作らない）→ 決定。「(火)」を読み上げが「かようび」と読むかは【未確認】。V3 の目視で見る。
- 書き方の検査（`react-hooks/exhaustive-deps`・`frontend/eslint.config.js:35`・`--max-warnings=0`）に当たらない形: 自動で送る処理は `sendRef.current = send` で持って呼ぶ。下書きの部品の口は `submitRef.current = submit` で持って呼ぶ → 決定。
- 下書きの部品の口: `SecretaryDraftEvent` を `forwardRef` にし、`useImperativeHandle` で `submitByVoice(): boolean`（`canCreate` が偽か保存中なら何もせず false）を出す。ボタンの `submit()` と同じ関数を呼ぶ。作るのに失敗したら props の `onVoiceFailed` を呼ぶ。

### 15-11 外部・過去事例の参照と我々への応用

- ChatGPT の音声モード（2023-09-25 公開・research.md §3）: 「話す→黙る→声で答える→また聞く」の形の見本としてだけ使う。速さ・成功の数の証拠には使わない（数を出した公開の資料は見つけていない）。
- 我々への応用: 形だけまねて、作りは今の部品（聞き取り・読み上げ・秘書の送り）をつなぐだけにする。新しい外のサービスは使わない。

### 15-12 審査の記録

| 回 | 審査 | 結論 | 直したこと |
|---|---|---|---|
| 1 | マージ前の審査役（Claude Opus・2026-11-24・PR #5728 の HEAD 85156a5e2） | REVISE（止める指摘 5 件・止めない指摘 9 件） | B1 ADR-1082 What 4・5 に声で会話の追記／B2 回数の印（§15-4（５））／B3 確かめの後もまた聞く・作るのに失敗したとき（§15-5 の表）／B4 書き方の検査に当たらない形（§15-10）／B5 日時は `formatDraftDateLine`・空のとき（§15-5・§15-6）。止めない指摘: 行番号・試験の英語の切り替えの名・偽物 2 つ・はい/いいえの誤判定・§15-5 と §15-10 のずれ・ADR-1080 の番号・手で打った文の自動送り・請求書の後の「はい」・維持の仕組み（§13）を直した |
| 2 | マージ前の審査役（Claude Opus・2026-11-24・HEAD ecc13d6a6） | REVISE（B1〜B5 は全部直っていた。新しい止める指摘 1 件 N1） | N1 読み上げの前に必ずマイクを止める（§15-4・カード §3（４）・試験 T11）／止めない指摘: 確かめ待ちの分かれ道は今のマイクを止める処理の後／英語は句読点を除く前の形で比べる／終わりの時刻が空も確かめない／`i18n` の取り出し／聞き取りは日本語に固定（§15-8） |
| 3 | マージ前の審査役（Claude Opus・2026-11-24・HEAD 33bb0bf8e） | REVISE（N1 は直っていた。新しい止める指摘 1 件 N2） | N2 読み上げのたびに回数の印を進める（§15-4（５）・カード §3（４）・試験 T12）／止めない指摘: 英語は句読点を除く前の形で比べると §15-5 にも書いた・§15-4（５）に止める決まりを書いた |
| 4 | マージ前の審査役（Claude Opus・2026-11-24・HEAD f3ab86098） | APPROVE（止める指摘 0 件） | 止めない指摘 N3（読み上げの途中にマイクの印を押すと秘書の声を拾う）と、窓を閉じた後の確かめ待ちを、カード §3（８-２）（８-３）・試験 T13 に入れた |

- 受け入れの基準と確かめ方の対応:

| 基準 | 確かめ方 |
|---|---|
| V1 | 本番の PC で録画して 10 回数える（kgi.md §5）・試験 T2（1000ms で送る・999ms で送らない） |
| V2 | 本番の PC で 5 回・試験 T4・T10〜T14（T14 は §15-13） |
| V3 | 本番の PC で 5 回ずつ・試験 T5〜T7 |
| V4 | 本番の PC で 5 回・試験 T8 |
| V5 | 本番の台帳の読み上げの字数・新しい有料のサービスの数 |
| V6 | PO の Android と iPhone で各 1 回 |

### 15-13 画面が外れた後にマイクを開かない（便 V2・2026-11-25）

- 起き方（事実・コードで確かめた）: 秘書の画面（`SecretaryChatInner`）が読み上げの途中で外れると、読み上げの部品の片付け `frontend/src/features/secretary/useSecretaryVoice.ts:107` が回数を進め、途中の `speak` は `"ok"` を返す（`:84`・`:96`）。`frontend/src/features/secretary/SecretaryChat.tsx:144` は `voiceOnRef` も回数の印 `turnRef` も変わっていないので `listen.start()` を呼ぶ。聞き取りの部品の片付け `frontend/src/features/secretary/useSecretaryListen.ts:200` はもう済んでいるので、開いたマイクを閉じる者がいない。PR #5738 の審査役の止めない指摘 1 件。
- 外れる場面: 秘書を使う権利が無くなったとき（`frontend/src/features/secretary/SecretaryChat.tsx:436-443` の `visible` が偽）・秘書の窓を含む画面ごと消えたとき。窓を閉じるボタンは `close()` が印を進めるので今も起きない。
- 直し方: `SecretaryChatInner` に、外れるときだけ動く片付けを 1 つ足し、`voiceOnRef` を偽にして `turnRef` を 1 進める（カード `docs/handoff/secretary-voice-input/card-binV2.md` §3）。声と聞き取りの部品は変えない（片付けは今のまま各自が行う）。
- 代わりの案と選ばなかった理由: (a) `useSecretaryListen` に「外れた後は start を無視」を足す → ほかの使い道（声の入力の印）にも効き、範囲が広がる。(b) `speakThenListen` で毎回「まだ付いているか」を別の印で見る → 印が 2 つになり、回数の印と役目が重なる。今の回数の印を進めるだけの直しが最も小さい。
- 確かめ方: 試験 T14（直す前は落ち、直した後は通る）。基準は kgi.md §5 V2「秘書の声が欄に入るのは 0 回」の守り。
- 戻し方: この便の PR の merge commit を revert する。DB・設定の変更なし。
- 審査の記録: 下の表に足す。

| 回 | 審査 | 結論 | 直したこと |
|---|---|---|---|
| V2-1 | マージ前の審査役（Claude Opus・2026-11-25） | APPROVE on 040b039e3（止める指摘 0。差分はカード §3・§4 と一字ずつ一致。片付けの順番に頼らない・StrictMode の害なしを実物で確認） | 止めない指摘のうち、PR 本文の GO原文を「GO #5739」の形に直した。作業中の札に PR 番号を書いた |

## 16. 声で下書きを直す（便W・2026-11-25）

### 16-1 目的と、利用者に見える変化

- 目的: 予定の下書きが出た後、手を使わずに中身を直して、そのまま「はい」で作れるようにする（kgi.md §6）。
- 前: 「入れますか？」の後は、はい／いいえしか聞かない。「説明に〇〇と入れて」は 2 回で「画面で確かめて」になり、直せない（recon.md §9-1）。
- 後: はい／いいえ以外の文は「直す頼み」として秘書に送る。直った下書きが下に出て、前の下書きは「下の直した下書きに替えました」の一文になる。秘書は「直しました。〇〇を〇〇に入れますか？」と読む。直し方が読めなければ「直すところが分かりませんでした…」と読み、2 回続けば今と同じ「画面で確かめて」で終わる。

### 16-2 対象と対象外

- 対象: 予定の下書きの、題名・始まり・終わり・場所・説明・Meet。声で会話が入っていて、「入れますか？」の確かめ待ちの間だけ。
- 対象外: 請求書の下書き（声では作らない約束のまま・§15-5）。終日の切り替え（終日の下書きでは時刻の頼みを使わない）。公開の範囲（画面で選んだ値を引き継ぐだけ）。手で打った文での直し（声で会話が切れているときは今のまま）。説明に「足す」（直すときは置き換え）。

### 16-3 選んだ形と、選ばなかった形

- A（画面だけで直す・AI と backend は今のまま）: カルテは値のある欄が勝つ（recon.md §9-2）ので、空の欄しか埋まらない。しかも PO の試した説明の言い方は AI が 1/2・メモは 0/2 しか読めない（recon.md §9-3）。PO の困りごとが直らないので選ばない。
- B（題名・場所・説明も AI に送り、AI に全部の欄を返させる）: 大きさの上限 15,000 バイトを超える（`docs/handoff/secretary-event-karte/design.md:118`）。選ばない。
- C（選ぶ形）: 画面は今の欄の値に「直す頼み」の印を付けて送る。backend は直す頼みのときだけ「AI が値を返した欄は AI、返さなかった欄はカルテ」で合わせる。AI に送る中身は今と同じ（日時の 3 欄だけ）。指示文に「直す頼み」の決まりを 1 行足し、説明・メモを読めるようにする。

### 16-4 backend（変更前 → 変更後）

1. `backend/app/schemas/assistant.py:18-32` `KarteIn`: 欄 `edit: bool = False` を `asked_count` の後に足す。`:159-172` `EventDraft`: 欄 `edited: bool | None = None` を `ask_count` の後に足す（直す頼みの答えのときだけ真偽、ほかは null）。
2. `backend/app/services/secretary_karte.py` に `merge_edit(ev: IntentEvent | None, karte: KarteIn) -> tuple[IntentEvent, bool]` を足す（`merge_karte` は変えない）。
   - 土台はカルテの値（題名・始まり・終わり・終日・場所・説明・会議・Meet）。`ev` が None なら土台のまま、変わった＝偽。
   - 題名・場所・説明: AI の値が null でなく、前後の空白を除いて空でなければ AI の値。
   - Meet: AI の値が null でなければ AI の値。会議: カルテか AI のどちらかが真なら真。終日: カルテの値のまま。
   - 始まり・終わり（カルテが終日でないときだけ）: AI の始まりが時刻として読めればそれを使う。AI の終わりが読めればそれを使う。AI の終わりが無く始まりだけ変わったときは、カルテの長さ（終わり − 始まり）を新しい始まりに足す（時差の印つき ISO・秒まで）。長さを計算できない（カルテに片方が無い・時差の印の有無が混ざる）ときは、カルテの終わりのまま。
   - 変わった: 題名・始まり・終わり・場所・説明・Meet のどれかが土台と違えば真。始まり・終わりは時刻として比べる（同じ時刻で書き方だけ違うものは変わっていない）。
3. `backend/app/routers/assistant.py:331-348` 新しい画面の道: カルテがあり `karte.edit` が真のときは、今の `merge_karte` の分かれ道より先に次を行う。AI が event で始まりを返したら、その答えに `apply_day(ev, body.text, now.date(), None)`（日付の決まりの表を当てる）。続けて `merge_edit` → `settle_dates`。最終の種類は event（AI が unknown や請求書を返しても、下書きはカルテのまま・変わった＝偽）。
4. `backend/app/routers/assistant.py:392-411` 下書きを作るところ: 直す頼みのときは `next_ask` を呼ばず `ask=None`・`ask_count=0`・`edited=<変わったか>`。
5. AI に送る中身（`_agent_payload`・`:190-207`）は変えない。直す頼みでも日時の 3 欄と `asked`（null）だけ。大きさは今と同じ。

### 16-5 指示文（`secretary-agent/prompt.txt`）

- `:14` の後に 1 行足す（2 つの容器が同じファイルを読む・`docs/handoff/secretary-event-karte/design.md` §4-4）:
  `- 「途中の予定」があり、利用者の文がその予定の欄を直す頼み（「説明にテストと入れて」「メモに資料を持参と書いて」「場所は渋谷にして」「4 時に変えて」「題名を定例会議にして」など）なら kind=event にし、言われた欄だけに値を入れ、言われていない欄は null にします。説明・メモ・備考・詳細は description に、場所は location に、題名・タイトル・件名は title に、言われた文字のとおりに入れます。`
- カルテが無い頼みには「途中の予定」の見出しが付かない（`secretary-agent/compose.mjs:11-14`）ので、この行は今までの頼みに当たらない。確かめは W4（23 件）。

### 16-6 frontend（変更前 → 変更後）

1. `frontend/src/features/secretary/secretaryApi.ts:56-67` `EventKarte` に `edit?: boolean`、`:40-53` `EventDraftData` に `edited?: boolean | null` を足す。時差の印つきの時刻の文字を作る関数 `toKarteTime(date: string, time: string): string`（`combineDateTime` で作った時刻を、ブラウザの時差の印つき `YYYY-MM-DDTHH:mm:00+09:00` の形で書く）をここに足す。
2. `frontend/src/features/secretary/SecretaryDraftEvent.tsx:31-34` の口に `currentValues(): { karte: EventKarte; calendarType: "personal" | "shared" }` を足す。今の欄の値から作る（題名・場所・説明は前後の空白を除き、空なら null。始まり・終わりは日付が空、または終日でなく時刻が空なら null。終日なら始まり 00:00・終わり 23:59。Meet は付けてよい人なら印の値、そうでなければ下書きの値。asked は null・asked_count は 0・edit は true）。props に `initialCalendarType?: "personal" | "shared"` を足し、`:51` の最初の値に使う。
3. `frontend/src/features/secretary/SecretaryChat.tsx`:
   - `:43` 予定の吹き出しに `calendarType?: "personal" | "shared"` を足し、`SecretaryDraftEvent` の `initialCalendarType` に渡す。
   - `:225-245` の「下書きの中身を読んで確かめを始める」部分を関数 `startConfirm(id, draft, key)` に出し、今の道（key＝confirmEvent）と直した後（key＝editedConfirm）の両方から呼ぶ（同じ処理を 2 か所に書かない）。
   - `:186-192`（はい／いいえ以外）を「直す頼み」に替える。下書きの口が無ければ今の `checkScreen` で終える。あれば `currentValues()` を読み、考え中の吹き出しを出して `sendSecretaryMessage(文, karte)` を送る。待つ間は確かめ待ちを外す（送り中は自動で送らない・:277）。
     - 答えが event で `edited` が真: 前の下書きの吹き出しを文 `secretary.edit.replaced` に替え、考え中の吹き出しを新しい下書き（公開の範囲は前の値）に替え、`startConfirm(新しい id, 下書き, "editedConfirm")`。
     - それ以外（変わらない・unknown）: 考え中の吹き出しを `secretary.voiceMode.notEdited` に替える。回数が 0 なら確かめ待ちを回数 1 で前の下書きに戻して `notEdited` を読む。1 なら確かめ待ちを外して `checkScreen` を読む。
     - 失敗: 今の `send` の失敗と同じ（権限なしは `onForbidden`・ほかは失敗の文を出して読む）。確かめ待ちは外したまま（前の下書きのボタンで作れる）。
     - 窓を閉じた後に届いた答えでは、確かめ待ちを付けない（`session` の値が違えば何もしない）。
4. 文言（`frontend/src/locales/ja.json`・`en.json` の `secretary`）: 足す `voiceMode.editedConfirm`「直しました。{{title}}を{{when}}に入れますか？」/「Updated. Add {{title}} on {{when}}?」、`voiceMode.notEdited`「直すところが分かりませんでした。はい、か、いいえ、か、直したいところを言ってください。」/「I could not tell what to change. Say yes, no, or what to change.」、`edit.replaced`「この下書きは、下の直した下書きに替えました。」/「This draft was replaced by the updated one below.」。使われなくなる `voiceMode.askAgain` は両方から消す。
5. 新しい部品・色・大きさは作らない（今の `ChatBubble`・`SecretaryDraftEvent` だけ）。

### 16-7 危ない点と手当て

| 危ない点 | 手当て |
|---|---|
| AI が言われていない欄に値を入れ、勝手に変わる | 直した下書きは必ず画面に出し、「入れますか？」に「はい」と言うまで作らない。下調べでは言われていない欄に値が入ったのは 0/12（p6 の 1 回目の始まり・終わりはカルテと同じ値で、変わっていない）。W2 で数える |
| 指示文を変えると今までの読み方が変わる | 足す行はカルテのある頼みだけに当たる。反映後に 23 件（W4）。23/23 でなければ PR を戻す |
| 「違う、4 時にして」は「いいえ」と判定され取り消される | 作られることは無い（安全な側）。判定は変えない。PO の目視で困るなら次の便で考える |
| 直すたびに AI を 1 回呼ぶ | 秘書の 1 日の回数に数える（今の道と同じ）。新しい費用は無い（W6） |
| 本番の容器の作り直しが失敗する | 配備は警告だけで前の容器が残る（`.github/workflows/deploy.yml:771-800`）。その間は説明・メモが読みにくいだけで、ほかは動く。反映後の 23 件と W1 の測りで気づく |

### 16-8 戻し方

- 便W の PR を戻す。画面・backend・指示文が一緒に戻る。古い画面は `edit` を送らないので、新しい backend・古い画面の組み合わせでも今と同じ動き。

### 16-9 測り方

- kgi.md §6 の W1〜W6。W1・W2・W4 は反映後に Opus が recon.md §9-3 と同じ道で流す。台本の結果は `docs/handoff/secretary-voice-input/binW/` に置く。

| 基準 | 検証方法 |
|---|---|
| 直す頼みで AI の値が勝ち、時刻だけなら長さを保つ | backend の試験（`merge_edit` の分かれ道すべて・口の直す道）が CI で緑 |
| はい／いいえ以外で直す頼みを送り、2 回読めなければ終える | 画面の試験（T7 を書き直す・直った下書きに「はい」で作る）が CI で緑 |
| 説明・メモが読める | W1: 6 回中 5 回以上 |
| ほかの欄が読める | W2: 12 回中 11 回以上 |
| 今までの読み方 | W4: 23/23 |

### 16-10 外部・過去事例の参照と我々への応用

- Rasa の forms（`docs/handoff/secretary-event-karte/design.md` §10 で 2026-11-14 に確認済み）: 欄を集める会話の型。今回は「埋まった欄を言い直しで替える」ので、同じ型の延長として、言われた欄だけを替えて他は残す形を使う。数値は無く、成功の証明には使わない。
- 今回の根拠は本番の AI の実測（recon.md §9-3・12 回）。外部の数は使わない。

### 16-11 維持の仕組み

- 合わせ方の正本は `backend/app/services/secretary_karte.py` の 1 か所（聞く道は `merge_karte`、直す道は `merge_edit`）。試験が CI（`.github/workflows/test.yml`）で毎回走る。
- 指示文を変える PR のたびに 23 件を流す決まり（`docs/handoff/secretary-event-karte/design.md` §11）はそのまま。
- 持ち主: 設計は Opus、実装はクラウドの Sonnet、合格の判定は Opus の実測と PO の目視（W5）。

### 16-12 審査の記録

- （設計の審査の結果をここに書く）
