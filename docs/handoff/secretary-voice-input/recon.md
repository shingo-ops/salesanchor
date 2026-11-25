# 秘書に声で話しかける — 現在地（recon）

この文書は何か: 設計の前に、今のコードと本番がどうなっているかを、ファイルの行番号と実測で書いたものです。
基準: `origin/main` 12000ef94（2026-11-19 02:20 ごろ取得）。読んだのは worktree `release/secretary-voice-input`（origin/main と同じ）。

## 1. 既存の ADR

- 検索: `git grep -i -E "秘書|secretary|音声|voice" docs/adr/FEATURE-INDEX.md` → 該当なし（FEATURE-INDEX に秘書の行は無い）
- `ls docs/adr | grep 1080` → `docs/adr/ADR-1080-secretary-voice-tts.md`（秘書の声・読み上げ）。聞き取りは対象外と明記
  - `docs/handoff/secretary-voice/design.md:16` 「対象外: 声で話しかける（聞き取り）」
  - `docs/handoff/secretary-voice/kgi.md:26` 同じ
- 関係する ADR: ADR-1056（秘書チャット）・ADR-1078（予定のカルテ）・ADR-1080（読み上げ）・ADR-027（i18n）・ADR-067（デザイントークン）・ADR-144（UI 金型）・ADR-136（危険 PR の GO）

## 2. 本番の画面はマイクを禁止している（事実）

- `/Users/tanizawashingo/worktrees/salesanchor/release-secretary-voice-input/nginx/nginx.conf:100` `add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;`（app.salesanchor.jp の server 枠）
- 同 `nginx/nginx.conf:323` 同じ値（/grafana/ の枠）
- 実測: `curl -sI https://app.salesanchor.jp/` → `permissions-policy: camera=(), microphone=(), geolocation=()`（2026-11-19 02:25 ごろ）
- 意味: このままでは、どのやり方でもブラウザはマイクを使わせない。聞き取りには `microphone=(self)` への変更が要る
- `scripts/security_check.sh:61` `check_header "Permissions-Policy" ""` は「見出しがあるか」だけを見る（値は見ない）

## 3. 秘書の窓（画面）

- `frontend/src/features/secretary/SecretaryChat.tsx`（268 行）
  - :50-63 窓の状態（open・messages・text・sending・karte・voiceOn・voiceNote・voice・voiceOnRef・session）
  - :65-76 `close()` 閉じると会話・カルテ・声を全部消す
  - :78-87 「声で返事」の切り替え。:80 `voice.enable()` はクリックの中で AudioContext を起こす
  - :97-147 `send()` 送る処理（文を吹き出しに出す→ `sendSecretaryMessage` → 返事の種類で分ける → 声が入なら読み上げ）
  - :114-118 予定でまだ聞く欄があるとき（ask）。:118 質問を読み上げる
  - :124-125 予定の最後の下書き（event）。読み上げは無い
  - :149-152 `markCreated()` 作った後に「作りました」を読み上げる
  - :229-255 `Drawer` の footer に「声で返事」・`Textarea`・送るボタン
  - :239-247 `Textarea` に `onKeyDown` は無い（Enter で送る処理は今は無い。送るのはボタンだけ）
- `frontend/src/features/secretary/useSecretaryVoice.ts`（110 行）読み上げ。AudioContext だけで鳴らす（:2-3 `<audio>` と blob: を使わない理由＝画面の安全設定を広げない）
  - :62-105 `speak()` は鳴り終わるまで待つ Promise を返す（音声モードで「鳴り終わったらまた聞く」に使える）
- `frontend/src/features/secretary/secretaryApi.ts`（149 行）
  - :91-93 `sendSecretaryMessage(text, karte)`
  - :113-115 `fetchSecretarySpeech()` は `api.postBlob`
  - :124-149 失敗の種類分け
- `frontend/src/features/secretary/SecretaryDraftEvent.tsx`
  - :53-74 予定を作る `submit()`。`POST /calendar/events` の中身をこの中で組み立てている（:58-68）
  - 意味: 音声モードで「はい」と答えたときに同じ中身で作るには、この組み立てを 1 か所の関数に出す必要がある（同じ式を 2 か所に書かないため）
- `frontend/src/features/secretary/SecretaryChat.css`（110 行）色・寸法はトークンだけ

## 4. 部品（金型）

- `frontend/src/components/Drawer.css:121-123` 767px 以下では窓の幅 100%、:29 高さ 100dvh → スマホでは秘書の窓がもう画面いっぱい。音声モードは窓の中身を差し替えれば「画面いっぱい」になる（新しい金型は要らない）
- `frontend/src/components/Sheet.css:35` 下から出る板は高さ 80dvh まで（画面いっぱいにはならない）
- `frontend/src/components/IconToggleButton.tsx` 絵柄だけのボタンの金型（aria-label 必須）
- `frontend/src/constants/icons.tsx` 絵柄の一覧。マイクの絵柄は無い（`grep -n Microphone frontend/src` → 0 件）。元は `@heroicons/react` ^2.2.0（`frontend/package.json:79`）
- `frontend/src/components/Textarea.tsx` 入力欄の金型（標準の textarea の属性をそのまま通す → `onKeyDown`・`ref` を渡せる）

## 5. 読み上げの口と使用量（聞き取りの手本）

- `backend/app/routers/assistant.py:98-103` `_SECRETARY_DEPENDENCIES`（feature・super admin・customers.view・invoices.create）
- `backend/app/routers/assistant.py:613-634` `POST /assistant/speech`。:622-627 Google を待つ前に読み取りの取引を閉じる
- `backend/app/services/secretary_tts.py:27-29` Google の宛先と範囲。:69-102 鍵（`GOOGLE_TTS_SA_KEY_FILE`）から札を作る。:110-120 使用量の記録
- `backend/app/services/llm_budget.py:159-185` 使いみち・sdk・provider の一覧（DB の CHECK と試験で一致を見る）。:317-323・:400-419 `billed_characters` を書く
- `migrations/20261117_100100_add_llm_usage_tts_characters.sql` 読み上げのときに足した列と CHECK
- `backend/app/routers/tcg_analysis_dashboard.py:694`・:939-940・:1050 使用量の画面に今月の読み上げ字数を返す
- `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:146`・:640-662 その表示

## 6. 予定の「はい／いいえ」

- 今は、予定を作るのは下書きの「作る」ボタンだけ（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:53-74`）
- 「はい／いいえ」を言葉から読み取る仕組みはアプリに無い（`git grep -n -E "YES_WORDS|affirm|はい" backend/app/services backend/app/routers` → 関係する 0 件）。Meet を付けるかの答えは AI がカルテの中で読む（`backend/app/schemas/assistant.py:15` `AskField` に `add_meet`）

## 7. アプリの入れ方

- `frontend/public/manifest.webmanifest` `"display":"standalone"` → スマホではホーム画面に置いたアプリとして開ける

## 8. Google 側（未確認）

- 読み上げ用の鍵（サービスアカウント secretary-tts）で Speech-to-Text が使えるかは **まだ確かめていない**
  - 手元の gcloud はログインが切れている（`gcloud projects get-iam-policy` → `Reauthentication failed`）
  - 本番から 1 回試す台本は用意済み（scratchpad の stt-probe.sh）。自動判定で止められたため、PO の `!` 実行を待つ

## 9. 声で下書きを直す（便W・2026-11-25 調べ・origin/main 48a5fdb1d）

### 9-1 起きたこと（PO の試し 2026-11-25）

- PO は予定の下書きが出た後に「説明にテスト 消していい って入力して」と 2 回話した。秘書は「はい、か、いいえで答えてください」→「画面で確かめて…」と返し、説明は入らなかった。予定は作られていない。
- 今の動きどおり。確かめ待ちの間は、はい／いいえ以外の文を AI に送らない（`frontend/src/features/secretary/SecretaryChat.tsx:167-193`）。1 回目は問い直し（:186-188）、2 回目は「画面で確かめて」で確かめ待ちを終える（:189-191）。その後の「OK」は新しい頼みとして AI に送られた（:195-206）。

### 9-2 下書きと AI の間（実物）

- 下書きの欄は、出た時の値で 1 回だけ作る（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:41-53` の `useState` の初期値）。同じ部品に新しい下書きを渡しても欄は変わらない。替えるには部品を作り直す（React の key を替える）。
- 親が下書きに触る口は `submitByVoice` だけ（`frontend/src/features/secretary/SecretaryDraftEvent.tsx:31-34`）。今の欄の値を読む口は無い。
- 下書きの「公開の範囲」（`calendar_type`）は画面では personal と shared を選べる（:51・:170-179）。秘書の返事の型は personal だけ（`frontend/src/features/secretary/secretaryApi.ts:47`・`backend/app/schemas/assistant.py:167`）。
- 画面は会話の途中の予定（カルテ）を全部の欄で送る（`frontend/src/features/secretary/secretaryApi.ts:56-67`）。backend は AI に日時の 3 欄と直前に聞いた欄だけを送る（`backend/app/routers/assistant.py:190-207`。題名・場所・メモを送らないのは大きさの上限のため・`docs/handoff/secretary-event-karte/design.md:118`）。
- AI の答えとカルテを合わせるとき、カルテに値がある欄はカルテが勝つ（`backend/app/services/secretary_karte.py:18-36`）。今のままでは、題名・時刻のように埋まった欄は声で変えられない。
- カルテの形は知らない鍵を 422 で断る（`backend/app/schemas/assistant.py:18-32` の `extra="forbid"`）。直す頼みの印を足すには、この形に欄を足す必要がある。
- 指示文に「埋まった予定の欄を直す頼み」の決まりは無い（`secretary-agent/prompt.txt:3-18`・見出し 1 行と決まり 15 項目）。
- はい／いいえの判定は、いいえの語が文のどこかにあれば「いいえ」（`frontend/src/features/secretary/secretaryVoiceAnswer.ts:60-65`・語の一覧は `frontend/src/locales/ja.json` の `secretary.voiceMode.noWords`）。「違う、4 時にして」は「いいえ」になり、下書きは取り消される（作られはしない）。

### 9-3 本物の AI に直す言い方を読ませた結果（2026-11-25 03:06 JST・Opus が実施）

- 道: 本番の backend の image の使い捨て容器から `http://secretary-codex:8090/intent` を直接呼んだ（ADR-1077 便0 と同じ道・制限のない鍵・PO の 2026-11-25 の許可「必要な権限は全て…使用して良い」）。使用の記録に行は入らない。
- 条件: カルテ＝始まり 2026-11-26 15:00・終わり 16:00・終日でない・直前に聞いた欄なし。担当 AI は `gpt-5.6-terra`（本番の使用の記録の model 列で確かめた）。6 つの言い方を 2 回ずつ（計 12 回・全部 HTTP 200）。
- 台本: `docs/handoff/secretary-voice-input/binW/probe_edit.py`。生の結果: `docs/handoff/secretary-voice-input/binW/probe-before-20261125.jsonl`。

| 言い方 | 1 回目 | 2 回目 | 読めた数 |
|---|---|---|---|
| p1 説明にテスト 消していい って入力して | unknown | event・description「テスト」 | 1/2 |
| p2 場所は渋谷の事務所にして | event・location | event・location | 2/2 |
| p3 メモに資料を持っていくと書いて | unknown | unknown | 0/2 |
| p4 時間を4時に変えて | event・start 16:00・end null | 同じ | 2/2 |
| p5 タイトルを定例会議に変えて | event・title | event・title | 2/2 |
| p6 Meetも付けて | event・add_meet true | event・add_meet true | 2/2 |

- 読み取れること（事実）: 場所・時刻・題名・Meet は今の指示文のままで 8/8 読めた。説明・メモは 1/4。時刻だけ変える頼みでは終わりが null で返る（2/2）。
- 未確認: 回数が 2 回ずつで少ない。指示文を足した後の数は便W の測り（kgi.md §6 W1・W2）で数える。

## 10. 声で直す便の気をつける点 3 つ（便W2・2026-11-25 調べ・origin/main ea800930e）

### 10-1 実物

- 「はい」の判定は、いいえの語が無く、文の頭が はい の語なら、後ろに何が続いても「はい」（`frontend/src/features/secretary/secretaryVoiceAnswer.ts:60-65`）。「はい」なら前の下書きをそのまま作る（`frontend/src/features/secretary/SecretaryChat.tsx:276-280`）。はい の語は `はい|うん|お願い|入れて|作って|オッケー|ok`（`frontend/src/locales/ja.json` の `secretary.voiceMode.yesWords`）。
- 直す道で日付の表（`apply_day`）を当てるのは、AI の始まりがカルテと時刻として違うとき（`backend/app/routers/assistant.py:340-341`）。時刻だけ違っても当たる。表が文の中に日付の言い方を 1 つだけ見つけると、始まりの日をその日に替える（`backend/app/services/secretary_dates.py:201-228`）。
- 手元で表を試した結果（Opus・2026-11-25・`backend/app/services/secretary_dates.py` を直接呼ぶ）: 「4時に変えて、説明に明日と入れて」など、読点や「して」でつながる 7 つの言い方は表が日付を見つけず（None）、日付は動かない。「4時に変えて 説明 明日」のように空白で区切ると表が「明日」を見つけ、カルテが明日でない日なら始まりの日が明日に動く。
- Meet を付けられるかは `can_add_meet`（`backend/app/services/calendar_service.py:74-81`・Google をつないだ本人だけ真）。直す道は AI の add_meet をそのまま合わせ（`backend/app/services/secretary_karte.py` の `merge_edit`）、変わった＝真になる。返す下書きは付けられない人では add_meet を null にする（`backend/app/routers/assistant.py:430`）ので、画面は何も変わらないのに「直しました」と読む。

### 10-2 本物の AI の答え（2026-11-25 09:14 JST・Opus が実施）

- 道は §9-3 と同じ（本番の backend の image の使い捨て容器から秘書の容器を直接呼ぶ・記録に行は入らない）。カルテ＝題名「打ち合わせ」・始まり 2026-11-30 15:00・終わり 16:00（明日でない日）。今日＝2026-11-25。9 つの言い方を 3 回ずつ（計 27 回・全部 HTTP 200）。
- 台本: `docs/handoff/secretary-voice-input/binW2/probe_followup.py`。生の結果: `docs/handoff/secretary-voice-input/binW2/probe-before-20261125.jsonl`。

| 言い方 | 3 回の答え | 数 |
|---|---|---|
| d1 4時に変えて、説明に明日と入れて | 3 回とも start 11/30 16:00・description「明日」 | 日付を変えない 3/3 |
| d2 16時にして、メモは明日の資料 | 3 回とも start 11/30 16:00・description「明日の資料」 | 3/3 |
| d3 説明に今日の議事録と入れて4時にして | 3 回とも start 11/30 16:00・description「今日の議事録」 | 3/3 |
| d4 時間を4時にしてメモに明日持参 | 3 回とも start 11/30 16:00・description「明日持参」 | 3/3 |
| d5 4時に変えて | 3 回とも start 11/30 16:00 | 3/3 |
| y1 はい、場所は渋谷にして | 3 回とも event・location「渋谷」 | 直す欄を返した 3/3 |
| y2 オッケー、説明に資料と入れて | 3 回とも event・description「資料」 | 3/3 |
| y3 はい、お願いします | 3 回とも unknown | 直す欄なし 3/3 |
| y4 うん、それで | unknown 2 回・event で全部の欄 null 1 回 | 直す欄なし 3/3 |

- 読み取れること（事実）: AI は時刻だけの直しで日付を 15/15 変えなかった。日付が動く道は表（`apply_day`）だけ。「はい」の後ろの直しは 6/6 読めた。後ろに直しが無い「はい」は 6/6 直す欄を返さなかった（`merge_edit` で変わった＝偽になる形）。
- 未確認: 3 回ずつで少ない。反映後に kgi.md §7 X1〜X3 で同じ台本をもう一度流す。

## 11. 「はい、〜にして」で前の下書きが作られる件・「あさって4時」が朝4時になる件（便W3・2026-11-25 調べ・origin/main 88c3fccd1）

調べの台本と生の結果: `docs/handoff/secretary-voice-input/binW3/`（`docs/handoff/secretary-voice-input/binW3/probe_before.py`・`probe-before-20261125.jsonl` 118 行・`probe-before-20261125-table.txt`・`docs/handoff/secretary-voice-input/binW3/hours_count.py`・`hours-20261125.txt`）。本物の AI（`http://secretary-codex:8090/intent`・gpt-5.6-terra）に 1 件ずつ順に流した（同時に流すと 117/118 が 429 busy になった。AI は同時に 1 件だけ受ける）。118/118 が 200。

### 11-1 何時を朝と読むか（AI の答え・最終の値）

| 言い方 | 新しい頼み「明日N時に打ち合わせ」（今 20:00 と 09:00・2 回ずつ） | 「あさってN時にして」（直す・カルテ 11/30 15:00） | 「N時に変えて」（直す） |
|---|---|---|---|
| 1時 | 01:00 が 4/4 | 13:00 が 2/2 | 13:00 が 2/2 |
| 2時 | 14:00 が 3/4・02:00 が 1/4 | 14:00 が 2/2 | 14:00 が 2/2 |
| 3時 | 15:00 が 4/4 | 15:00 が 2/2 | 15:00 が 2/2 |
| 4時 | 16:00 が 3/4・04:00 が 1/4 | 16:00 が 2/2 | 16:00 が 2/2 |
| 5時 | 17:00 が 4/4 | 17:00 が 1/2・05:00 が 1/2 | 17:00 が 2/2 |
| 6時 | 06:00 が 4/4 | 06:00 が 2/2 | 18:00 が 2/2 |
| 7〜11時 | すべて朝（07:00〜11:00）20/20 | 10/10 | 10/10 |

- 1〜6時を朝と読んだ数は 36 回中 13 回。同じ言い方でも回によって朝と午後が入れ替わる（2時・4時・5時）。
- 指示文（`secretary-agent/prompt.txt` 19 行）に午前・午後の決まりは無い。日付は「今の日時から数える」（`:7`）だけ。
- backend は日付の部分だけを決まりの表で替える（`backend/app/services/secretary_dates.py:201` `apply_day`）。時刻は AI の読んだまま。

### 11-2 本番の予定の始まりの時刻（日本時間・5 社の表・読むだけ）

`hours-20261125.txt`: 予定 35 件（終日 0 件）。アプリで作った予定は 5時 1・7時 4・10時 2・11時 1・14時 1・17時 1・21時 4・22時 1・23時 1。Google 側は 9〜22時だけ。0〜6時に始まる予定は 1 件（5時・題名「カレンダー動作テスト(Google側で修正した)」・PO の試し）。7時の 4 件は作った時刻が始まりより後の試し。→ 実際の使い方で、1〜6時に始まる予定は 0 件。

### 11-3 「はい、〜」の答え（カルテ 11/30 15:00〜16:00・2 回ずつ）

- 直す頼み 8 種 × 2 = 16 回: 14 回が `edited` 真（言われた欄だけが変わった）。残り 2 回は「はい、3時からにして」でカルテが既に 15:00（変わらないので偽が正しい）。読み落としは 0/16（便W2 の 6/6 と合わせて 0/22）。
- 「はい、お願いします」など 7 種 × 2 = 14 回: すべて `edited` 偽（AI は unknown か、空か、同じ値を返した）→ 前の下書きで作られる（設計どおり）。
- 前の下書きで黙って作られる道は、今の作り（`frontend/src/features/secretary/SecretaryChat.tsx:235-240` の `yesFallback`）で 2 つある。
  （１）AI が直しを返さなかった（上の 0/22）。
  （２）AI は直しを返したが、合わせた結果が日時を失い、backend がカルテのまま・`edited` 偽に戻した（`backend/app/routers/assistant.py` の「直した結果が日時を失ったら」の分かれ）。例: 始まり 15:00 で「はい、終わりは5時にして」を AI が 05:00 と読むと、終わり < 始まりで終わりが空になり（`backend/app/services/secretary_karte.py:52-70` `settle_dates`）、前のままに戻る。画面は「はい」として前の下書きを作る。11-1 のとおり 5時を朝と読む回がある。
- 直す道では聞き返しは出ない（`backend/app/routers/assistant.py` の `if edit_mode: ask, ask_count = None, 0`）。画面の `!reply.draft.ask` の条件は直す道では常に真。
- 作った後に読む文は「予定を作りました。」だけ（`frontend/src/features/secretary/SecretaryChat.tsx:381-388` `markCreated`・`frontend/src/locales/ja.json` `secretary.created.event`）。

### 11-4 今までの試し 23 件（`backend/app/assistant_regression/cases.json`）

時刻の言い方は 15時・16時・10時・13時・17時半・9時・14時と「1 時間」「2 時間」（長さ）だけ。素の 1〜6時は 0 件。→ 11-1 の決まりを足しても 23 件の答えは変わらない。
