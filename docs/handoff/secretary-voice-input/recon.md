# 秘書に声で話しかける — 現在地（recon）

この文書は何か: 設計の前に、今のコードと本番がどうなっているかを、ファイルの行番号と実測で書いたものです。
基準: `origin/main` 12000ef94（2026-11-19 02:20 ごろ取得）。読んだのは worktree `release/secretary-voice-input`（origin/main と同じ）。

## 1. 既存の ADR

- 検索: `git grep -i -E "秘書|secretary|音声|voice" docs/adr/FEATURE-INDEX.md` → 該当なし（FEATURE-INDEX に秘書の行は無い）
- `ls docs/adr | grep 1080` → `ADR-1080-secretary-voice-tts.md`（秘書の声・読み上げ）。聞き取りは対象外と明記
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

- 今は、予定を作るのは下書きの「作る」ボタンだけ（`SecretaryDraftEvent.tsx:53-74`）
- 「はい／いいえ」を言葉から読み取る仕組みはアプリに無い（`git grep -n -E "YES_WORDS|affirm|はい" backend/app/services backend/app/routers` → 関係する 0 件）。Meet を付けるかの答えは AI がカルテの中で読む（`backend/app/schemas/assistant.py:15` `AskField` に `add_meet`）

## 7. アプリの入れ方

- `frontend/public/manifest.webmanifest` `"display":"standalone"` → スマホではホーム画面に置いたアプリとして開ける

## 8. Google 側（未確認）

- 読み上げ用の鍵（サービスアカウント secretary-tts）で Speech-to-Text が使えるかは **まだ確かめていない**
  - 手元の gcloud はログインが切れている（`gcloud projects get-iam-policy` → `Reauthentication failed`）
  - 本番から 1 回試す台本は用意済み（scratchpad の stt-probe.sh）。自動判定で止められたため、PO の `!` 実行を待つ
