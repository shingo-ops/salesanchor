# 秘書に声で話しかける — 設計（design）

状態: **聞き取りのやり方は A（ブラウザの聞き取り・無料）に決定（PO 2026-11-19「1」）。まず試しの便（§14）で iPhone のホーム画面のアプリで聞き取れるかを確かめる。§5 の B 用の backend・migration・月の上限（§7）は作らない**
目標: [kgi.md](kgi.md)（K1〜K6・PO 承認 2026-11-19「1」）／ 現在地: [recon.md](recon.md) ／ 調べ: [research.md](research.md)
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
- B の前に、本番から 1 回試して事実をそろえる（`stt-probe.sh`: 今の鍵で使えるか・K2 の文がそのまま取れるか・速さ）
- 以下 §5 以降は B で書く。A になった場合は §5-1・§5-2・§7 が無くなり、§5-4 の録音がブラウザの聞き取りに置き換わる

## 5. 変更するファイル（B の場合）

### 5-1 backend

- `migrations/20261119_xxxxxx_add_llm_usage_stt_seconds.sql`（新規・冪等）
  - `ALTER TABLE public.llm_usage_events ADD COLUMN IF NOT EXISTS billed_seconds INTEGER;`
  - 使いみちの CHECK に `secretary_stt`、sdk の CHECK に `google-stt-rest`、provider の CHECK に `google_stt` を足す（読み上げの migration `migrations/20261117_100100_add_llm_usage_tts_characters.sql` と同じ形）
- `backend/app/services/llm_budget.py:159-185` 一覧に同じ 3 つを足す（DB の CHECK と試験で一致を見る仕組みはそのまま）。:400-419 `billed_seconds` を書けるようにする
- `backend/app/services/secretary_stt.py`（新規）`secretary_tts.py` と同じ形
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
- `frontend/src/features/secretary/secretaryVoiceAnswer.ts`（新規）`judgeYesNo()`。はい・いいえの言葉の一覧はここ 1 か所
- `frontend/src/features/secretary/SecretaryVoiceMode.tsx`（新規）音声モードの中身（状態の文字・✕）。色・寸法は var() だけ
- `frontend/src/features/secretary/SecretaryChat.tsx`
  - `send()`（:97-147）を「文を受け取って送る」形に分け、ボタン・音声モードの両方から呼ぶ
  - `Textarea`（:239-247）に `onKeyDown`・`onKeyUp` でスペース長押し（§3-1）
  - スマホ（`isMobile`）のときだけ欄の右にマイクの `IconToggleButton`
- `frontend/src/locales/ja.json`・`en.json` に同じ鍵（聞いています・考えています・話しています・マイクが使えない・入れますか？ など）
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:640-662` の下に聞き取りの今月の分数

### 5-4 録音と区切り（`useSecretaryListen`）

- `navigator.mediaDevices.getUserMedia({ audio: true })` → `MediaRecorder`（形はブラウザに任せる: Chrome は webm、Safari は mp4）
- 音の大きさは `AnalyserNode` で 50 ミリ秒ごと。話し始め＝一定より大きい音が 150 ミリ秒続く。区切り＝話し始めの後 1.2 秒静か。1 回の最長 30 秒（Google の 1 分の上限より短く）
- 止めるときは `MediaStreamTrack.stop()` を全部呼ぶ（K5: 聞いていない間はマイクが閉じている）

## 6. 1 か所にすること（SSOT）

- 使いみち・sdk・provider の一覧: `llm_budget.py` と DB の CHECK（今の仕組み）
- Google の鍵と札: `secretary_tts.py` の 1 か所（聞き取りもそれを使う）
- 予定の中身の組み立て: `buildEventPayload()` の 1 か所
- はい・いいえの言葉: `secretaryVoiceAnswer.ts` の 1 か所
- 画面の文字: `ja.json`・`en.json`

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

## 12. 外部事例

research.md §3（ChatGPT の音声モード・2023-09-25 公開。形の見本としてだけ使う）

## 13. 維持の仕組み

- 一覧と CHECK の一致は既存の試験が見張る
- 聞き取りの月の分数は使用量の画面で毎月見える

## 補足: 次のテーマ（会話の相棒）への備え（2026-11-19）

- PO 決定（11/19「1」）: 声の機能を先に仕上げ、秘書を会話の相棒にする作り直しは次のテーマにする
- 聞き取りの部品（`useSecretaryListen.ts`・§5-4）は「声 → 文字」だけを返し、秘書の指示・会話の扱いを持たない
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

（６）`frontend/src/locales/ja.json`・`en.json` の `secretary` の下に `listen` を足す（同じ鍵）
- ja: `start` 話して入力する ／ `stop` 聞くのをやめる ／ `listening` 聞いています… ／ `error.unsupported` この画面では声の聞き取りが使えません ／ `error.notAllowed` マイクが許可されていません。端末の設定でマイクを許可してください ／ `error.serviceNotAllowed` この端末では声の聞き取りが許されていません ／ `error.noSpeech` 声が聞こえませんでした。もう一度押して話してください ／ `error.audioCapture` マイクが使えませんでした ／ `error.network` 聞き取りの通信に失敗しました。もう一度お試しください ／ `error.language` 日本語の聞き取りに対応していません ／ `error.other` 聞き取れませんでした。もう一度お試しください
- en: 同じ意味の英語

（７）試験
- `frontend/src/features/secretary/useSecretaryListen.test.ts`（新規）: 対応表（8 つ）・部品が無いと `unsupported`・`start` で `lang` などの設定・途中の文・確定で `onText` 1 回・空の確定で呼ばない・画面から消えると `abort`・続けて 2 回 `start()` しても部品は 1 つ・前の失敗の後に `start()` すると `error` が `null` に戻る・`start()` の直後に `listening` が `true`・`rec.start()` が投げると `error` が `other` になり、次の `start()` で部品が作られる・`error` の後に `end` が来ても `error` が残る・`abort()` の直後に次の `start()` で新しい部品が作られ、古い部品の `end` が来ても `listening` は `true` のまま・`abort()` の後に古い部品から `result`・`error` が来ても `onText` は呼ばれず `error` も変わらない・`stop()` の後の `end` で `listening` が `false` になる
- `frontend/src/features/secretary/SecretaryChat.test.tsx` に足す: `isMobile=false` で印が無い・`isMobile=true` で印が有る・押すと「聞いています」・確定の文が欄に入り送られない（送る口が呼ばれない）・部品が無いと「使えません」・窓を閉じると `abort`
- 試験の中に日本語の文字を直接書かない（`useSecretaryVoice.test.ts:4-6` と同じ書き方）

### 14-3 触らないもの

- backend・migrations・deploy.yml・`nginx/nginx.conf:323`・読み上げ（`useSecretaryVoice.ts`）・下書きの部品
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
