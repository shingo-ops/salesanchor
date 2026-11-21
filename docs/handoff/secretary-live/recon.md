# 秘書チャット「マイク（A）」「LIVE（B）」の前の調べ（現在地・読むだけ）

- 調べた場所: `origin/main` の `2560f963f`（Merge pull request #5677）。作業場所 `release/secretary-live-recon`
- 目的: 秘書チャットに (A) マイクの印（話すと文字が欄に出る・秘書は文字で答える）と (B) LIVE（声どうしの会話・割り込み可・双方の発言が画面に文字で残る・LIVE 中も予定や請求書の下書きを作れる）を足す設計の前の事実集め。今の「声で返事」のチェックは最後に消す予定。
- 決まり: 事実には `パス:行` を付ける。読んでいないもの・動かしていないものは「未確認」と書く。製品のコード・DB・本番・secrets は触っていない（読んだだけ）。
- 以下のパスは特に書かない限り `/home/user/salesanchor` 相当のリポジトリ直下からの相対（実際に読んだのは作業場所 `/root/worktrees/salesanchor/release-secretary-live-recon/` の同じパス）。

---

## 1. 画面 `frontend/src/features/secretary/`（12 ファイル・2,363 行）

| ファイル | 行数 | 役割 |
|---|---|---|
| `SecretaryChat.tsx` | 294 | 窓の本体。右下の印→`Drawer`。会話は `useState` だけ（`:1-8` の冒頭の説明・保存しない）。`SecretaryChat`（外側・`:286-294`）が `useSecretaryAccess` で出す条件を見て、`SecretaryChatInner`（`:50`）に `isMobile` を渡す |
| `useSecretaryVoice.ts` | 110 | 返事の読み上げ。`splitForSpeech`（`:10`・。！？と改行で分け 300 字で切る）→ `fetchSecretarySpeech`（`:72`）→ `ctx.decodeAudioData`（`:73`）→ `createBufferSource`（`:86`）。鳴らし方は `AudioContext` だけ（`:2-3`）。先取りは 1 つ（`:80-82`）。`enable`（`:48`）/`disable`（`:55`）/`speak`（`:62`）/`stop`（`:35`） |
| `useSecretaryListen.ts` | 175 | 声→文字。ブラウザの Web Speech API。`getSpeechRecognition`（`:58`）・`classifyListenError`（`:65`）・`useSecretaryListen`（`:96`）。設定は `lang="ja-JP"`（`:115`）・`interimResults=true`（`:116`）・`continuous=false`（`:117`）。部品は `recRef` に 1 つ（`:114`）。確定した文を `onText` に渡す（勝手に送らない。冒頭 `:3-4`） |
| `secretaryApi.ts` | 149 | 口の呼び出しと型。`sendSecretaryMessage`（`:91`・`POST /assistant/messages`・100 秒 `:9`）・`fetchSecretarySpeech`（`:113`・15 秒 `:96`・300 字 `:97`）・`getSecretaryVoice`/`saveSecretaryVoice`（`:105`/`:109`）・`isSpeechCapError`（`:118`・`tts_monthly_cap_reached`）・`classifySecretaryError`（`:137`）・予定のカルテの型 `EventKarte`（`:56`）と `karteFromDraft`（`:70`）。入力の上限 `SECRETARY_MAX_TEXT = 1000`（`:10`） |
| `useSecretaryAccess.ts` | 23 | 出す条件 1 か所。`secretary_chat` の feature・super admin・`customers.view`・`invoices.create`（ファイル内の `isEnabled("secretary_chat")` 以下）。設定の「秘書の声」欄（`frontend/src/pages/account-settings/PreferencesSection.tsx:9-16`）も同じ条件を使う |
| `SecretaryDraftEvent.tsx` | 169 | 予定の下書きの吹き出しの中身。「作る」は `POST /calendar/events` を本人のログインで呼ぶ（冒頭 `:1-5`） |
| `SecretaryDraftInvoice.tsx` | 289 | 請求書の下書き。「作る」は `POST /invoices`。通貨・支払方法・送料なしの確認など |
| `SecretaryKarteAsk.tsx` | 53 | 予定のカルテの途中の吹き出し（埋まった欄＋次の質問。質問文は翻訳キー `secretary.ask.*`・冒頭 `:1-4`） |
| `SecretaryChat.css` | 122 | 並びだけ。色・寸法はトークン（`:1`）。`.secretary-chat__composer`（`:8`）・`__input-row`（`:15`）・`__listen-status`（`:21`）・`__voice-row`（`:27`）ほか |
| `SecretaryChat.test.tsx` | 729 | 見える条件（`:133`）・送る（`:165`）・請求書（`:243`・`:339`）・予定（`:417`）・声で返事（`:501`〜`:631`・V3-a〜g）・聞き取りの印（`:633`〜`:729`。`isMobile={false}` に印なし `:685`、`isMobile={true}` に印あり `:692`） |
| `useSecretaryListen.test.ts` | 221 | 聞き取り部品の試験（`:61` `classifyListenError`・`:76` 以降の動き） |
| `useSecretaryVoice.test.ts` | 29 | `splitForSpeech` の試験だけ（`:8`）。`speak`/`enable` 自体の試験は未確認（このファイルには無い） |

### 1-1 `SecretaryChat.tsx` の主要な行

- 型 `ChatMessage`（`:37-43`）: 利用者の文・AI の文（`status?: "sending" | "error"`）・`invoice`・`event`・`ask`・`created` の 6 種。
- 状態（`:52-67`）: `open`・`messages`・`text`・`sending`・`karte`（`:57`）・**`voiceOn`（`:59`）**・`voiceNote`（`:60`）・`voice = useSecretaryVoice()`（`:61`）・`listen = useSecretaryListen(...)`（`:63`・確定文を欄の末尾に足し `SECRETARY_MAX_TEXT` で切る）・`voiceOnRef`（`:66`・返事が届いた時点の値で決める）・`session`（`:67`）。
- `close()`（`:69-81`）: 聞き取りを `abort`・会話・欄・カルテを消し、声を `disable`、`voiceOn` を false に戻す。
- **声で返事の切り替え**: `onVoiceChange`（`:83-92`）が `voice.enable()`/`voice.disable()` と `voiceOnRef`/`voiceOn` を更新。`speakFor`（`:94-97`）。返事が来たとき `voiceOnRef.current` なら読む（聞き返し `:124`・普通の文の返事 `:134`・作成後の「作りました」`:157`）。トグルの描画は `:241-244`（`<label htmlFor="secretary-voice-toggle">{t("secretary.voiceToggle")}</label>` と `<Toggle id="secretary-voice-toggle" checked={voiceOn} onCheckedChange={onVoiceChange} />`）。
- **マイクの印が `isMobile` のときだけ出る行**: `:255-265`（`{isMobile && ( <IconToggleButton pressed={listen.listening} iconOff/iconOn={SECRETARY_ICONS.listen} size="md" disabled={sending} onClick={() => (listen.listening ? listen.stop() : listen.start())} aria-label={t(listen.listening ? "secretary.listen.stop" : "secretary.listen.start")} /> )}`）。`isMobile` は `App.tsx:154` の `useIsMobile()`（`frontend/src/hooks/useIsMobile.ts:18`・`matchMedia (max-width: MOBILE_MAX)`）を `App.tsx:158` で渡している。聞いている間の表示は `:267-273`（`role="status"`・途中の文 `listen.interim`・失敗は `secretary.listen.error.*`）。
- 送る `send()`（`:102-153`）: 読み上げと聞き取りを止め（`:105-106`）→ 利用者の吹き出しと「考えています」の吹き出しを足し（`:110-114`）→ `sendSecretaryMessage(trimmed, karte)`（`:119`）→ 返事の種類で分岐（`:120-136`）。失敗は `classifySecretaryError`（`:138`）。`forbidden` は印ごと消す（`:139-142`）。
- 吹き出しの描画 `renderBubble`（`:173-225`）。窓は `Drawer`（`:235-281`・`footer` に composer）。右下の印は `FloatingActionButton`（`:229-234`・`aboveTabbar={isMobile}`）。

### 1-2 使っている金型（`frontend/src/components/`）

| 金型 | 使い方（行） | 金型側の約束 |
|---|---|---|
| `Drawer` | 窓。`open`・`onClose`・`title`・`footer`（`SecretaryChat.tsx:235-281`） | `components/Drawer.tsx:28-46`（props）・フッタ描画 `:195-197`・閉じる/戻る/全画面ボタンが標準で付く（`:150-185`） |
| `FloatingActionButton` | 右下の印（`:229-234`） | `components/FloatingActionButton.tsx:15-24`。`icon`・`label`・`aboveTabbar`。金型 `Button` は使えない理由が冒頭に書いてある（`:3-6`） |
| `ChatBubble` | 吹き出し（`layout="panel"`・`direction="inbound"/"outbound"`・`pending`・`failed`・`wide`） | `components/ChatBubble.tsx:22-34` |
| `Textarea` | 入力欄（`fullWidth`・`maxLength`・`disabled={sending}`） | `components/Textarea.tsx:37-62`。`variant` に `"composer"` あり（`:32`）。ref を渡せるのは `TextareaControl`（`:45`）で、`Textarea`（`:62`）の ref の扱いは未確認 |
| `Button` | 「送る」（`loading`・`disabled`） | 本文未読（使い方は `:274-276`） |
| `IconToggleButton` | マイクの印 | `components/IconToggleButton.tsx:21-37`。`pressed`・`iconOff`/`iconOn`・`size: 'sm'|'md'`・`variant: 'default'|'badge'`・`aria-label` 必須・`count`。`pressed` で `iconOn`・危険色系（`:4`） |
| `Toggle` | 声で返事（`:243`） | `components/Toggle.tsx:12-19`（`checked`・`onCheckedChange`・`id`・`aria-label`）。中身は `role="switch"` の checkbox |
| `Select`・`TextField`・`Checkbox` | 予定の下書き（`SecretaryDraftEvent.tsx:8-12`） | — |

**LIVE 画面に使えそうな既存の金型（存在を確かめたもの）**:
- 発言を文字で残す: `ChatBubble`（今の窓と同じ。`layout="panel"`）。聞き取りの途中の文を出す欄は今 `<p className="secretary-chat__listen-status">`（`:268`）。
- 押している/いない・LIVE 中の状態を示す丸い押しボタン: `IconToggleButton`（上記）。`variant: 'badge'` は常に危険色（`IconToggleButton.tsx:8`・`:32`）。
- 2〜3 択の切替: `SegmentedToggle`（`components/SegmentedToggle.tsx:2`。「アイコンボタンから 1 つを選ぶ」）。
- ほか `Callout`・`Sheet`・`Stack`・`ChatComposer`（`ChatComposer.tsx:34-42`。`leading`・`input`・`attach`・`trailing`・`send`。受信箱の入力欄の金型）が `components/` にあるが、**中身（props の意味・秘書の窓に合うか）は読んでいない＝未確認**。
- 金型が無い見た目（例: LIVE の大きな波形・通話の終了ボタン）は、`docs/CC_UI_GOVERNANCE.md:13-15`・`docs/adr/ADR-144-ui-component-governance.md:59-64` により「実装を止め PO に報告→PO 許可→`components/` に `Xxx.tsx`＋`Xxx.css`（`var()` のみ）＋`Xxx.stories.tsx` で新設」。

### 1-3 絵柄 `frontend/src/constants/icons.tsx`

- 秘書の絵柄: `SECRETARY_ICONS = { listen: hi(MicrophoneIcon) }`（`:416`）。1 つだけ。`MicrophoneIcon` の import は `:53`。
- 右下の印: `LeadChatIcon`（`:419-421`・`ChatBubbleOvalLeftOutlineIcon`）。
- 既にある別の絵柄（LIVE に流用できるかは未確認）: `Phone = hi(PhoneIcon)`（`:129`）・`XOutline = hi(XMarkOutlineIcon)`（`:155`・`close` として `:377`）・`Target = hi(SignalIcon)`（`:104`）。
- 読み上げ・停止・スピーカー系の絵柄（SpeakerWave・Stop 等）は `icons.tsx` に**見つからなかった**（`Speaker`/`StopIcon`/`StopCircle`/`PhoneXMark` を検索して 0 件。外部の heroicons 側にあるかは未確認）。
- 大きさ: `frontend/src/constants/iconSizes.ts:5-11`（`sm 14・md 16・base 20・lg 24・xl 48`。`tokens.css` から生成・手で直さない `:2-3`）。

### 1-4 翻訳 `frontend/src/locales/ja.json`・`en.json`

`secretary` は `ja.json:6269`〜`:6361` 付近（`en.json` も同じ `:6269` 始まり）。鍵:
`open`・`title`・`placeholder`・`send`・`create`・`cancel`・`thinking`・**`voiceToggle`（`:6277`・ja「声で返事」/ en「Read replies aloud」）**・`listen.start`（話して入力する）/`listen.stop`/`listen.listening`/`listen.error.{unsupported,notAllowed,serviceNotAllowed,noSpeech,audioCapture,network,language,other}`・`voiceFailed`・`voiceCapReached`・`cancelled`・`priceRequired`・`priceDecimals`・`error.{notReady,busy,timeout,unreadable,generic,authFailed,agentFailed,rulesTooLong}`・`invoice.*`・`event.*`・`ask.{title,start,end,add_meet}`・`karte.filled`・`created.{invoice,event}`・`link.{invoice,event}`・`voice.name.{Aoede,Charon,Erinome,Zubenelgenubi}`。
LIVE 用の鍵（開始・終了・つなぎ中・話してください 等）は**まだ無い**。足すなら ja・en の両方（ADR-027）。

### 1-5 UI の決まり（要点）

- **ADR-144**（`docs/adr/ADR-144-ui-component-governance.md`）: `pages/` の UI は原則 `components/` の金型。生の `<select>`・`<input type="text"|"search"|省略>`・自作タブ・色直値/生 px のインラインスタイルの**新規追加は CI で赤**（`:29-39`）。ゲート本体 `scripts/check-ui-governance.js`（`:41-48`）。検査対象は PR の変更ファイル中 `frontend/src/pages/**/*.tsx`（`:43`）で、`features/`・`components/` は検査しない旨の追記あり（`:134`）。ただし `docs/CC_UI_GOVERNANCE.md:7-15` は「金型があるか先に確認→あれば必ず使う→無ければ止めて報告」を CC の遵守事項にしている。`ui-allow` 例外コメントは理由と課題番号の両方が必須（`:47-48`）。生 checkbox・生 radio も禁止種別に追加済み（`:130-148`）。`docs/CC_UI_GOVERNANCE.md:27-28`: 読み込み中の文字だけの表示は `LoadingBlock`、ボタンの言葉の入れ替えは禁止（`Button` の `loading`）。2026-09-10 改訂案は Proposed で全件検査へ（`:108-128`）。
- **ADR-067**（`docs/adr/ADR-067-design-token-enforcement.md`）: 色・余白・寸法は `var(--…)` のトークンだけ。インラインの色直値・生 px・opacity/zIndex の数値・width/height 等の数値は ESLint（`eslint.config.js`）と `check-css-hardcoded-colors.js`/`check-css-hardcoded-values.js`/`check-dark-parity.js` が止める（`:25-34`）。金型専用のトークンは `tokens.css` に足す（`:38` 以降の表）。
- **ADR-027**（`docs/adr/ADR-027-ui-internationalization.md`）: 画面の言葉は ja/en 両方（`:13`）。固有名詞も `t()` を通す・新しい英語の直書きは `check-ui-governance.js` の `englishUiLiteral` が差分で止める（`:84-88`）。

---

## 2. 裏側と配線

### 2-1 `backend/app/routers/assistant.py`（634 行）の口

守りは 4 つ `_SECRETARY_DEPENDENCIES`（`:98-103`・`secretary_chat` feature・super admin・`customers.view`・`invoices.create`）。口一覧:

| 口 | 行 | 中身 |
|---|---|---|
| `POST /assistant/messages` | `:266-440` | 文＋カルテ→担当表の provider の容器へ→下書き（請求書/予定/聞き返し）。何も作らない |
| `GET /assistant/rules`・`POST /assistant/rules`・`…/feedback`・`…/approve`・`…/reject`・`DELETE`（remove） | `:447`〜`:555` 付近 | 決まり帳（ADR-1077） |
| `GET /assistant/voice` / `PUT /assistant/voice` | `:581` / `:589` | 本人の声（4 つから選ぶ・既定 Charon） |
| `POST /assistant/speech` | `:608-634` | 文（1〜300 字・`schemas/assistant.py:197-198` `SpeechIn`）→MP3。`Cache-Control: no-store`（`:633`） |

- **WebSocket・ストリーム・音声の入力の口は `assistant.py` に無い**（口は上の表で全部）。`speech` は 1 文ずつの一括取得（`useSecretaryVoice.ts:62-105`）。
- 順番（`:1-9` の冒頭の説明）: ①守り・担当表と決まりを読む・頼みの大きさを測る・Meet 可否を読む ②`db.commit()`（`:~326`）③容器を呼ぶ ④会社の文脈を張り直す ⑤名前探し ⑥返す。AI を待つ間 DB の取引を開けない。
- 担当を読む: `get_ai_assignment(db, "secretary_intent")`（`assistant.py:~282`・`services/ai_assignment.py:10-15` の SQL は `ai_job_assignments` JOIN `ai_job_choices`）。行が無いと `AiAssignmentMissing`→`503 not_ready`。

### 2-2 秘書の頼みを AI の容器へ送る道（ADR-1058）

- 宛先は `agent_url(provider)`（`assistant.py:106-112`）: `{"claude": SECRETARY_AGENT_URL, "codex": SECRETARY_CODEX_URL}`（既定 `http://secretary-agent:8090` / `http://secretary-codex:8090`・`:85-86`）。それ以外の provider は `None`→`not_ready`。
- 送る本文 `_agent_payload`（`:192-205`）: `text`・`now`・`model`・`rules`（承認済みの決まり）＋カルテがあれば日時 3 欄と `asked`。上限 15,000 バイト（`AGENT_BODY_MAX_BYTES` `:89`）＜容器の `MAX_BODY = 16 * 1024`（`secretary-agent/server.mjs:15`）。
- 呼び出し `_call_agent`（`:221-263`）: `POST {url}/intent`・タイムアウト 85 秒（`:87`）。容器の失敗は 504 timeout/503 not_ready・auth_failed/429 busy/502 agent_failed・unreadable に直す。同時 1 本・80 秒（ADR-1056 What `docs/adr/ADR-1056-secretary-chat.md:19`）。
- 容器の置き場: `secretary-agent/`（Dockerfile・server.mjs・`schema.json`・`prompt.txt`）と `secretary-codex/`。deploy.yml の起こす段は `Start secretary-agent (ADR-1056)`（`.github/workflows/deploy.yml:735`）・`Start secretary-codex (ADR-1058)`（`:771`）。容器は backnet に入れず frontnet だけ（ADR-1056 `:19`）。
- 担当表の job_key の値は DB の CHECK で 5 つに閉じている: `migrations/20261103_120000_create_ai_job_assignments.sql:32`・`:44`・`:56`（`line_extraction`・`translation_inbound`・`translation_inbound_escalation`・`translation_outbound`・`secretary_intent`）。初期値は `('secretary_intent','claude','sonnet')`（同 `:105`）。選択肢は migration でだけ足す（ADR-1058 `:18`）。
- **既存の AI の道は「文→決まった JSON」の一括呼び出し**（`secretary-agent/server.mjs:131` `POST /intent`）。声の連続した入出力・割り込みを流す口は**無い**（上の口一覧と容器の口 `/intent` のみを確認）。

### 2-3 読み上げの鍵の渡し方（名前だけ・値は見ていない）

- 鍵の名前: **`GOOGLE_TTS_SA_KEY_FILE`**（`.env` に「VPS 上の鍵ファイルの場所」を置く）。コードは `backend/app/services/secretary_tts.py:30`（`KEY_FILE_ENV`）・`:69-84`（`_credentials`。未設定・読めない→`503 tts_not_configured`）。
- compose: `docker-compose.yml:159-160`（環境 `GOOGLE_TTS_SA_KEY_FILE=${GOOGLE_TTS_SA_KEY_FILE:+/run/google-tts-sa.json}`）・`:165`（ボリューム `${GOOGLE_TTS_SA_KEY_FILE:-/dev/null}:/run/google-tts-sa.json:ro`）。
- 入れ替え `scripts/blue-green-cutover.sh`: `.env` のキー名を名前だけで渡す（`:78-88`）が、`GOOGLE_TTS_SA_KEY_FILE` は名前で渡さず飛ばす（`:86`）。代わりに `TTS_ARGS`（`:93-95`）で鍵ファイルを `/run/google-tts-sa.json` に読み取り専用でつなぎ、環境値を箱の中の場所に置き換える。ファイルが無いときはつながない（`:96-101`・読み上げは 503 のまま・入れ替えは続ける）。
- `.github/workflows/deploy.yml` には `GOOGLE_TTS` は**出てこない**（`TTS|google-tts` を検索して 0 件。`GOOGLE_CALENDAR_*`・`GOOGLE_DRIVE_*` は出る `:352-359`・`:414-419`）。鍵ファイルは VPS 上に置く方式で GitHub の secrets には入れていない（置くのは PO 本人・ADR-1080 `:42`）。
- 新しい外の AI（LIVE 用）の鍵をどう渡すかは**まだ決まっていない**（この調べの範囲では該当の記述なし）。ADR-1056 `:20` は「月額契約のログイン情報は専用ファイル（chmod 600）・`.env` に書かない（`.env` は backend に全部渡るため）」。

### 2-4 `nginx/nginx.conf` の Permissions-Policy と CSP

- **app.salesanchor.jp の枠**（`server_name` `:83`）:
  - CSP `:96`: `default-src 'self'; script-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:`。
    - **`media-src` は無い**＝`default-src 'self'` に落ちる。`blob:` が許されているのは `img-src` だけ → 読み上げが `<audio>`/blob: を使わず `AudioContext` で鳴らす理由（`useSecretaryVoice.ts:2-3`・ADR-1080 `:18`）。
    - `connect-src 'self'`: 同じ origin だけ。外部の AI の WebSocket/HTTPS に画面から直接つなぐには広げる必要がある（別 origin 宛の `wss:` は今は許されない）。同じ origin の `ws:`/`wss:` を `'self'` が含むかはブラウザ依存で**未確認**。
  - **Permissions-Policy `:100`: `camera=(), microphone=(self), geolocation=()`**。つまり**マイクは既に自分の画面に許されている**（ADR-1082 `:16` の決定どおり `main` に入っている）。LIVE のためのマイク許可の変更は今は要らない。
  - 参考: `/grafana/` の枠は `microphone=()`（`:323`）・`connect-src 'self' ws: wss:`（`:320`）で別枠。
- **`/api/` の枠**（`:294-307`）: `limit_req zone=api burst=50`・`proxy_pass http://$backend:8000`・`proxy_read_timeout 120s`。**`Upgrade`/`Connection` のヘッダ・`proxy_http_version 1.1` は無い**＝この枠は WebSocket をそのまま通す形にはなっていない。長い接続用の枠は SSE 3 つだけ: `/api/v1/conversations/stream`（`:235-253`）・`/api/v1/leads/stream`（`:255`）・`/api/v1/events/stream`（`:275`）。`proxy_buffering off`・`proxy_read_timeout 3600s`・`proxy_http_version 1.1`・`chunked_transfer_encoding on`（`:244-251`）。`Upgrade` を付けているのは `/grafana/`（`:316-317`）・`/status/`（`:333-334`）・`monitor` の枠（`:865-866`）だけ。
- nginx を変える配備は nginx を作り直し 2〜3 秒画面が開けない（`.github/workflows/deploy.yml:570-575`・ADR-1082 `:41`）。
- フロントの API は同じ origin の `/api/v1`（`frontend/src/lib/api.ts:32`）。`api.salesanchor.jp` の枠（`:397`〜）の CSP は `default-src 'none'; frame-ancestors 'none'`（`:426`）で、画面の origin は `app.salesanchor.jp`。

### 2-5 台帳 `llm_usage_events` と月の上限

- **purpose の集合**（コード側の写し）: `backend/app/services/llm_budget.py:158-171` `USAGE_PURPOSES` = `line_extraction`・`line_extraction_shadow`・`inventory_parse_fallback`・`translation_inbound`・`translation_inbound_escalation`・`translation_outbound`・`secretary_intent`・`secretary_regression`・`secretary_tts`。
- **sdk の集合**: `llm_budget.py:174-176` `USAGE_SDKS` = `google-genai`・`google-generativeai`・`codex-cli`・`claude-code`・`google-tts-rest`。担当表の provider→sdk の対応 `USAGE_SDKS_BY_PROVIDER`（`:180-185`）: `gemini`→google-genai/google-generativeai、`codex`→codex-cli、`claude`→claude-code、`google_tts`→google-tts-rest。1 つに決まらない provider は `_sdk_for`（`assistant.py:115-119`）が `None`→`not_ready`。
- **CHECK の場所（正本は DB）**: 作成 `migrations/20260930_150000_create_llm_usage_events.sql:46-52`（`llm_usage_events_purpose_check`・`llm_usage_events_sdk_check`）。その後の作り直し: `migrations/20261103_120000_create_ai_job_assignments.sql:159-163`（`secretary_intent`・codex-cli・claude-code を許す）・`migrations/20261117_100100_add_llm_usage_tts_characters.sql:1-38`（`billed_characters` 列・`secretary_tts`・`google-tts-rest` を許す。「定義に値が無いときだけ作り直す」＝冪等 `:6`・`:24`）。**新しい purpose・sdk を足すには、この形の migration が要る**（`record_usage_event` は集合に無い purpose を `ValueError`: `llm_budget.py:256-257`）。migration を含む PR は PO の「GO #PR番号」まで main にマージしない（`AGENTS.md`「ブランチと作業場所」）。
- 書き方: 秘書の AI 呼び出しは 1 回 1 行（purpose `secretary_intent`・`assistant.py:167-184` `_record_ledger`・`record_usage_isolated`）。月額契約なので `cost_usd` は NULL（ADR-1058 `:24`）。読み上げは `secretary_tts`・`sdk=google-tts-rest`・`billed_characters`（`secretary_tts.py:110-120`）。
- **月の上限**: 読み上げだけにある。`MONTHLY_CHAR_CAP = 900_000`（`backend/app/services/secretary_voice.py:22`・無料枠 `FREE_MONTHLY_CHARS = 1_000_000` `:21`・1 回 300 字 `:23`）。`read_month_total`（`secretary_tts.py:48-61`・日本時間の今月 1 日 0 時から `billed_characters` を合計）→`check_monthly_cap`（`:64-66`・超えると `429 tts_monthly_cap_reached`）。字数を読めなければ 503 で Google を呼ばない。画面は `isSpeechCapError`（`secretaryApi.ts:118`）→「今月の読み上げの上限に達しました」（`secretary.voiceCapReached`）。**`secretary_intent` には月の上限の仕組みは見つからなかった**（台帳に書くだけ。月額契約のため金額上限なし。`tenant_llm_budgets`/`check_budget` は `llm_budget.py` にあるが秘書から呼ばれているかは未確認）。
- 料金の事実（調べ済みの記録）: Chirp 3: HD は毎月 100 万字まで無料・超過は 100 万字 30 ドル（`docs/handoff/secretary-voice/research.md:35`）。毎月 Google の請求の字数と台帳を手で照らす（ADR-1080 `:43`）。

### 2-6 外の有料 AI を新しく使うことに関わる決まり（原文引用）

**ADR-1056**（`docs/adr/ADR-1056-secretary-chat.md`）
- `:15`「本番サーバーに専用の容器 `secretary-agent` を 1 つ置き、中で Claude Code を月額契約のログイン（`CLAUDE_CODE_OAUTH_TOKEN`）で `-p` 実行する。道具は全部切る（`--tools ""`・`--disallowedTools "mcp__*"`・`--strict-mcp-config`）。」
- `:16`「AI に渡すのは利用者が書いた文と日本時間の今の日時だけ。AI が返すのは決まった形の JSON（請求書・予定・わからない、のどれか）だけ。会社のデータは渡さない。」
- `:18`「作成は、利用者が下書きを確かめて「作る」を押したときに、画面が今の `POST /invoices`・`POST /calendar/events` を利用者本人のログインで呼ぶ。AI の側に書き込みの道は無い。請求書・予定の写しを持たない。」
- `:20`「月額契約のログイン情報は VPS の専用ファイル（chmod 600）にだけ置き、容器にだけ渡す。`.env` には書かない（`.env` は backend に全部渡るため）。置くのは PO 本人で、AI は値を見ない。」
- `:34`（リスク）「月額契約の約束に反していて契約を止められるおそれがある（約束の調査は PO が禁止）。止められてもチャットが「準備ができていません」になるだけで、請求書・予定の機能は今のまま動く。使い方をごまかす作りはしない。」
- `:35`「利用者が書いた文は AI 会社へ送られる。会社のデータは送らない。」
- `:43`（Excluded）「請求書・予定そのものの作りの変更、今あるデータを直す頼み（第2段）、Codex・Grok（第1段の合格後に 1 つずつ）、使う人を広げる権限キー、`llm_usage_events` の変更」
- `:5` のステータス欄は「Accepted」。

**ADR-1080**（`docs/adr/ADR-1080-secretary-voice-tts.md`・ステータス Proposed `:5`）
- `:15`「秘書の声は Google Cloud Text-to-Speech の Chirp 3: HD の 4 つ（Aoede・Charon・Erinome・Zubenelgenubi）。既定は Charon。」
- `:17`「読み上げは backend の口 `POST /api/v1/assistant/speech` だけが行う。声は backend が本人の値を読む。守りは秘書と同じ 4 つ。」
- `:18`「チャットの「声で返事」は最初は切れていて、保存しない。音は同じ場所の API から取り、`AudioContext` で鳴らす。画面の安全設定は変えない。」
- `:19`「読み上げた字数を使用量台帳 `public.llm_usage_events` に 1 回 1 行で書く（列 `billed_characters`・使いみち `secretary_tts`・`sdk` は `google-tts-rest`）。文そのものは書かない。」
- `:20`「今月の字数が 90 万字（無料枠 100 万字の 9 割）に届いたら backend が読み上げを止める。」
- `:33`「月の上限の根拠は料金表（research.md T4・無料枠は月 100 万字）。上限を backend に置けば、画面の不具合でも止まる。」
- `:37`（代わりの案・選ばなかった）「…ブラウザ内蔵の読み上げ・Google の流しながら返す方式・`<audio>` と安全設定の緩和・ログだけに書く。」
- `:42`「本番に Google の読み上げ用の鍵を置く（便3・PO 本人の GO）。」

**ADR-1082**（`docs/adr/ADR-1082-secretary-voice-input.md`・ステータス Proposed `:5`）
- `:15`「声を文字にするのは、ブラウザが元から持つ聞き取り（Web Speech API の `SpeechRecognition`）。backend に聞き取りの口は作らない。費用は 0 円で、使用量台帳には書かない。」
- `:16`「本番の画面の安全設定 `Permissions-Policy` のうち、`microphone` だけを `()` から `(self)` にする（`nginx/nginx.conf` の app の枠 1 か所）。他の画面に埋め込まれたときは許さない。camera・geolocation は今のまま禁止。」
- `:18`「聞き取った文は入力欄に入れるだけで、勝手に送らない（K2）。音声モードで予定を作るのは「はい」と答えたときだけ（K6・次の便）。」
- `:19`「マイクを使うのは、押している間・音声モードの間だけ。窓を閉じる・送る・画面から消えるときは止める（K5）。」
- `:34`（代わりの案）「Google Cloud の有料の聞き取り（design.md §4 の B）: 使用量を画面で見られ、音が会社の契約の中に閉じる。月 約 320 円の見込み。PO が無料を選んだため選ばない。試しの便で iPhone で動かなければ、もう一度 PO に聞く。」
- `:42`「音の送り先: ブラウザの会社のサービスに送られることがある（MDN）。iPhone での送り先は未確認（design.md §14-6）。」

**ADR-1058**（`docs/adr/ADR-1058-ai-job-assignments.md`・関連の決まり。LIVE が AI の担当を増やすなら必読）
- `:17` 読むのは関数 `get_ai_assignment(job_key)` だけ・行が無ければ止まる（既定値に逃げない）。
- `:18`「選択肢は migration でだけ足す。画面と API に選択肢を足す道は作らない。」
- `:38`（リスク）「月額契約（ChatGPT の個人の契約）を会社のサーバーで使ってよいかは使い方の約束の判断で、PO が決める。決まるまで ChatGPT の容器は本番に出さない。答えが「不可」なら秘書は Claude のまま。」

**ADR-1004**（台帳）: Decision 1「1 行 = Gemini の応答 1 回」は ADR-1080 が読み上げに広げて改めた（`docs/adr/ADR-1004-llm-usage-ledger.md:5`・`:25`・ADR-1080 `:23`）。

### 2-7 `docs/adr/FEATURE-INDEX.md` の声・秘書の行

- `docs/adr/FEATURE-INDEX.md:77`: 「アプリ内チャット秘書 / 決まり帳 / 予定のカルテ / 声 / 音声入力 / TTS」→ **ADR-1056 ／ ADR-1077 ／ ADR-1078 ／ ADR-1080 ／ ADR-1082**・仕様 `docs/specs/secretary-chat/README.md`・主なファイル `backend/app/services/secretary_*.py`・`backend/app/routers/assistant.py`。
- 声・秘書に関わるのにこの行には出ていない ADR（本文で参照を確認したもの）: **ADR-1058**（AI の担当）・**ADR-1004**（LLM 使用量台帳）・ADR-1016（変わった合図・即時反映）・ADR-1071（失敗の文）・ADR-1054（画面のデータの取り方）・ADR-027・ADR-067・ADR-144。`FEATURE-INDEX.md` で `声|秘書|音声|voice|tts|speech` を引いて出る行は :77 の 1 行だけ。
- 関係の設計・調べ: `docs/handoff/secretary-voice/`（読み上げ）・`docs/handoff/secretary-voice-input/`（聞き取り。`design.md:28-34` に PC のスペース長押し・スマホの「音声モード」の設計があるが、ADR-1082 `:20` で「最初の便は試しの便」とされ**次の便は未着手と読める**。コードに `SecretaryVoiceMode`・スペース長押しは無い＝ `features/secretary/` のファイル一覧に無い）・`docs/handoff/secretary-chatgpt/`・`docs/handoff/secretary-event-karte/`・`docs/handoff/secretary-rulebook/`・`docs/handoff/secretary-chat/`。

---

## 3. LIVE を作るとき触る場所の一覧

「事実」の列は上で確かめたもの。「決める必要があること」は推測ではなく、確かめた事実から出る未決の点。

| 場所 | なぜ触るか（確かめた事実） |
|---|---|
| `frontend/src/features/secretary/SecretaryChat.tsx` | マイクの印は `isMobile` のときだけ（`:255-265`）。(A) を PC にも出すならここの条件。LIVE の入口の印・LIVE 画面への差し替え・`close()`（`:69-81`）での LIVE 後片付け・`voiceOn` 関連の削除（`:59`・`:66`・`:83-97`・`:124`・`:134`・`:157`・`:241-244`）。`send()`（`:102-153`）は LIVE 中の発話を同じ処理に流すなら「文を受け取って送る」形に分ける必要がある（ADR-1082 設計 `design.md:94` も同じ案） |
| `frontend/src/features/secretary/useSecretaryListen.ts` | (A) の部品。今は 1 回区切り（`continuous=false` `:117`）・日本語固定（`:115`）。LIVE が同じ部品を使うか別の部品かは未決 |
| `frontend/src/features/secretary/useSecretaryVoice.ts` | 一括取得→順に鳴らす方式（`:62-105`）。割り込み可（話し始めたら止める）は `stop()`（`:35-46`）があるが、LIVE の声が別方式（流し）になるなら別の部品。`声で返事` を消すとき `enable`/`disable` の呼び手（`SecretaryChat.tsx:76`・`:85`・`:87`）も消える |
| `frontend/src/features/secretary/secretaryApi.ts` | LIVE の口の呼び出し・型。`SECRETARY_MAX_TEXT = 1000`（`:10`）の扱い |
| 新規 `frontend/src/features/secretary/` 内の LIVE 画面・部品 | 発言を文字で残す（`ChatBubble` を使えば今の会話と同じ並びに出せる）。金型が無い見た目は ADR-144 の手順（PO 許可→金型新設） |
| `SecretaryDraftEvent.tsx` / `SecretaryDraftInvoice.tsx` / `SecretaryKarteAsk.tsx` | LIVE 中の下書きを同じ吹き出しで出すなら変更不要の可能性が高い（`ChatMessage` の種類は `SecretaryChat.tsx:37-43`）。ただし LIVE が `/assistant/messages` 経由で下書きを作る前提かは未決 |
| `frontend/src/constants/icons.tsx` | `SECRETARY_ICONS`（`:416`）に LIVE 用の絵柄を足す（今は `listen` の 1 つだけ）。終了・スピーカー系は未登録 |
| `frontend/src/components/`（金型） | 必要なら新設（ADR-144）。`IconToggleButton`・`ChatBubble`・`SegmentedToggle` は流用候補（2 節 1-2） |
| `frontend/src/locales/ja.json`・`en.json`（`:6269` 付近 `secretary`） | LIVE の開始・終了・状態・失敗の文（両言語・ADR-027）。`voiceToggle`（`:6277`）等は最後に消す |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | 声で返事の試験 `:501-631`（V3-a〜g）は `voiceToggle` を消すとき同時に消す。聞き取りの印の試験 `:633-729`（特に `:685` の「isMobile が false では印が無い」）は (A) を PC にも出すなら書き換わる |
| `frontend/src/pages/account-settings/PreferencesSection.tsx` | 設定の「秘書の声」欄（`:9-16`）。LIVE の声を同じ 4 声から選ぶなら関係する |
| `backend/app/routers/assistant.py` | LIVE の口（今は `messages`・`speech` のみ）。守りの `_SECRETARY_DEPENDENCIES`（`:98-103`）を使い回すのが既存の形 |
| `backend/app/services/secretary_tts.py`・`secretary_voice.py` | 月の字数の上限（`MONTHLY_CHAR_CAP` `secretary_voice.py:22`）。LIVE が同じ Google の読み上げを使うなら字数の数え方・300 字/回の制限（`:23`）に合わせる必要。外の別の声の AI を使うなら台帳の purpose/sdk と上限の仕組みが新規 |
| `backend/app/services/llm_budget.py`（`:158-185`）＋新しい `migrations/*.sql` | 新しい外の AI を使うなら `USAGE_PURPOSES`・`USAGE_SDKS`・`USAGE_SDKS_BY_PROVIDER` の写しと、DB の CHECK を作り直す migration（`20261117_100100_add_llm_usage_tts_characters.sql` が型）。migration 入りの PR は PO の GO まで main に入れない |
| `backend/app/services/ai_assignment.py`・`migrations/20261103_120000_…:32,44,56` | LIVE の AI を担当表で選ばせるなら job_key の追加（CHECK の作り直し）。ADR-1058 `:18` のとおり migration でだけ |
| `secretary-agent/`・`secretary-codex/`・`.github/workflows/deploy.yml:735`・`:771` | LIVE の AI が既存の容器（文→JSON の一括 `POST /intent`）で足りるか、別の道が要るか。現状の容器は流れる声を扱う口を持たない（`secretary-agent/server.mjs:131`） |
| `nginx/nginx.conf`（app の枠 `:83`〜・CSP `:96`・Permissions-Policy `:100`・`/api/` `:294`） | `microphone=(self)` は既にある（`:100`）。画面から外へ直接つなぐなら `connect-src`（`:96`）の広げ方、WebSocket を backend 経由にするなら `/api/` の枠か専用の枠に `Upgrade`・`proxy_http_version 1.1`（SSE の枠 `:235-253` が型）。nginx を変える配備は 2〜3 秒画面が止まる（`deploy.yml:570-575`） |
| `docker-compose.yml:159-165`・`scripts/blue-green-cutover.sh:78-101` | 新しい鍵ファイル・環境値を backend に渡す場合の配線の型（`GOOGLE_TTS_SA_KEY_FILE` が前例） |
| `docs/adr/`（新規 ADR）・`docs/adr/FEATURE-INDEX.md:77`・`docs/adr/README.md`（`node scripts/generate-adr-index.js`） | ADR-1056 を改める点（AI に渡すのは文と今だけ、道具を渡さない、作成は「作る」を押したとき）に LIVE がどう触れるか。ADR-1080 What 4（画面の安全設定は変えない）・ADR-1082 What 1（聞き取りは台帳に書かない）の改め |

## 4. 確かめられなかったこと

- **LIVE に使う外の AI・声の方式は何か**（この調べの対象外。リポジトリ内に LIVE の設計・選定の文書は見つからなかった）。リアルタイムの音声 API の料金・契約（月額契約の個人利用の可否を含む）・日本語の質・割り込みの仕様は**調べていない**。
- `connect-src 'self'` が同一 origin の WebSocket（`wss:`）を許すかどうか、Safari/iOS の差（ブラウザの挙動・本番でも動かしていない）。
- `/api/` の枠で WebSocket が通るか（`Upgrade` ヘッダが無いことは確認。実際に通らないかは試していない）。
- iPhone のホーム画面アプリでの聞き取り・マイク許可の挙動（ADR-1082 `:30`・`:42` が未確認と明記。本番の確かめ結果は見つからなかった）。
- Web Speech API の聞き取りで「割り込み（読み上げ中に話し始めたら止める）」ができるか、読み上げの音を聞き取りが拾う問題（ADR-1082 設計の `design.md:31` は「読み上げの間はマイクを閉じる」としている）。動かして確かめていない。
- `Textarea`（`components/Textarea.tsx:62`）が ref を受けるか・`Callout`/`Sheet`/`Stack`/`ChatComposer`/`SegmentedToggle`/`Button` の props の意味（存在とファイル名だけ確認）。
- heroicons 側に話者・停止・波形の絵柄があるか（`icons.tsx` に登録は無い）。
- `tenant_llm_budgets`・`check_budget`（`llm_budget.py`）が秘書の AI 呼び出しから使われているか（`assistant.py` からの呼び出しは見つからなかった。別の経路は未確認）。
- ADR-1080 と ADR-1082 のステータスは Proposed のまま（`:5`）。本番での K1〜K5/K1〜K6 の確かめが済んだかは記録を見つけていない。
- `docs/handoff/secretary-voice-input/design.md` の「音声モード」「スペース長押し」が実装されたか: `features/secretary/` のファイルに該当は無い（上の一覧）。それ以外の場所（`frontend/src` 全体）は `AudioContext|getUserMedia|WebSocket|EventSource` の検索で `useSSE.ts` と `useSecretaryVoice.ts` だけが出た（`getUserMedia` は 0 件）。
- 本番の状態（`secretary_chat` の行・鍵ファイルの有無・容器の稼働・台帳の中身・今月の字数）は本番に触れない決まりのため**一切見ていない**。
- `docs/specs/secretary-chat/README.md` の本文は読んでいない（目次の行とファイル名だけ）。`docs/STANDARD-WORKFLOW.md`・`docs/ai-agents/executor-checklist.md`・`ai-agents/lessons.d/` は今回開いていない（調べ役の読むだけの作業のため）。
