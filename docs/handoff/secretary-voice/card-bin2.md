---
mode: handoff
---
# 実装カード 便2: 声を選ぶ欄・「声で返事」の切り替えと再生・今月の字数の欄

親: [design.md](./design.md) §3・§4-6〜§4-8・§6・§9（V3・V5 の画面・V9）・§12（便2 の行）

- 状態: カード作成済み（2026-11-17 Opus）。PO 実装承認: 2026-11-17、便1 の完了報告で「残り 2回目：設定画面に、声を選ぶ欄を作ります」と伝えた後の PO の言葉「PRマージ、デプロイまで完走させてくれ」。便3（本番の鍵）の GO は兼ねない。
- 担当: クラウドの Sonnet（実装）。Opus は審査・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: B（画面と backend の読み取りの口。`migrations/`・`deploy.yml`・本番 `scripts/` を触らない。`frontend/api-contract/` は §5 手順6 の命令で作り直すだけ）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（声を選んで聞けるようにする画面。鍵は便3） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に想定外のファイル・削除が無いこと） | ○（§5 手順9） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順9） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md（全命令を cd で始める・1手順1命令・待たない・commit と push の後に実在を確かめる）、04-worktree.md（起点は origin/main・push は `-u origin HEAD`・作成は `new-worktree.sh`）、05-pr.md（PR は Opus が `gh-pr-create-safe.sh` で作る・触るファイル欄は1行カンマ区切り）、10-executor.md（ヒアドキュメントで書かない）、11-lint.md（L01〜L33 を `scripts/card-lint.sh` で照合）。

基準: origin/main fc84e2a4b（2026-11-17・便1 #5568 合流後）。行番号はこの時点の目印で、ずれていたら前後の文で探す。

## 1. 目的（便2 で起きること）

- 設定の「表示の好み」に「秘書の声」の欄が出る（秘書の窓が出る人だけ）。4 つの声から選べ、未選択の人はカロンが選ばれて見える。
- 秘書の窓の入力欄の上に「声で返事」の切り替えが出る。最初は切れ。入れると、その後の返事を選んだ声で読み上げる。
- 使用量の画面に「秘書の読み上げ（今月）」の欄が 1 枚増える。
- 本番には鍵がまだ無い（便3）。切り替えを入れた人には「声を出せませんでした…」の 1 行が出るだけで、文の返事は今まで通り。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `backend/app/services/secretary_voice.py` | `FREE_MONTHLY_CHARS = 1_000_000` を `MONTHLY_CHAR_CAP` の上に 1 行足す（無料枠の正本。§3-5） |
| `backend/app/routers/tcg_analysis_dashboard.py` | 使用量の口に今月の読み上げの字数を足す（§3-5） |
| `backend/tests/test_tcg_analysis_dashboard_llm_usage.py` | §3-5 の試験を足す |
| `frontend/api-contract/openapi.json` | §5 手順6 の命令で作り直す（手で書かない） |
| `frontend/src/lib/api.ts` | `postBlob` を足す（§3-1） |
| `frontend/src/features/secretary/useSecretaryAccess.ts`（新規） | 秘書の窓を出す条件の 1 か所（§3-2） |
| `frontend/src/features/secretary/useSecretaryVoice.ts`（新規） | 文の分け方・順に取る・順に鳴らす・止める（§3-3） |
| `frontend/src/features/secretary/useSecretaryVoice.test.ts`（新規） | §3-7 |
| `frontend/src/features/secretary/SecretaryChat.tsx` | 条件を §3-2 に置き換え・切り替えと読み上げ（§3-4） |
| `frontend/src/features/secretary/SecretaryChat.test.tsx` | V3 の試験を足す（§3-7） |
| `frontend/src/features/secretary/SecretaryChat.css` | 切り替えの行の並び 1 つ（§3-4。値はトークンだけ） |
| `frontend/src/features/secretary/secretaryApi.ts` | 声の口の呼び出しと型（§3-1） |
| `frontend/src/pages/account-settings/PreferencesSection.tsx` | 「秘書の声」の欄（§3-6） |
| `frontend/src/pages/account-settings/PreferencesSection.test.tsx`（新規） | §3-7 |
| `frontend/src/pages/super-admin/components/LlmUsageSection.tsx` | 今月の字数の欄（§3-5） |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | §3-8 のキー（同じキーを両方に） |

触らないもの: `migrations/`・`scripts/`・`.github/`・`deploy.yml`・`docker-compose.yml`（便3）・`nginx/`（画面の安全設定は変えない）・`backend/app/routers/assistant.py`・`backend/app/services/secretary_tts.py`（`read_month_total` を呼ぶだけで中は変えない）・`backend/app/realtime/topics.py`・秘書の返事の文と AI に渡す文・`staff_ui_preferences`・新しい部品（`package.json`・`requirements.txt` を変えない）・`frontend/src/components/`（金型は使うだけ）・ADR と設計の文書。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. 通信（`frontend/src/lib/api.ts`・`frontend/src/features/secretary/secretaryApi.ts`）

- `api.ts` の `api` の並びに `postBlob: (path: string, data: unknown, timeoutMs: number) => requestBlobPost(path, data, timeoutMs)` を足す。`requestBlobPost` は `requestForm` の近くに新しく書く:
  - 送る: `getAuthHeaders()` の札（`Content-Type: application/json` のまま）・`method: "POST"`・`body: JSON.stringify(data)`・`AbortController` で `timeoutMs` 後に打ち切る・`fetchWithReauth` を使う（`requestForm` と同じ）。
  - 繰り返さない（429 と 503 を何度も頼まないため。`requestBlob` の繰り返しの仕組みは使わない）。
  - `!res.ok` のとき: `requestForm` と同じく `res.json()` の `detail` を読み、`throw new ApiError(errorMessageFromDetail(detail, res.status), res.status, detail)`。
  - 成功は `res.blob()` を返す。
  - 今ある `getBlob` と `requestBlob` は変えない。
- `secretaryApi.ts` に足す:
  - `export const SPEECH_TIMEOUT_MS = 15_000;` `export const SPEECH_MAX_CHARS = 300;`（口の `SpeechIn` の `max_length=300` と同じ数。`backend/app/schemas/assistant.py:198`）
  - `export interface VoiceSettings { voices: string[]; default: string; selected: string }`
  - `getSecretaryVoice()` → `api.get<VoiceSettings>("/assistant/voice")`
  - `saveSecretaryVoice(voice: string)` → `api.put<VoiceSettings>("/assistant/voice", { voice })`
  - `fetchSecretarySpeech(text: string)` → `api.postBlob("/assistant/speech", { text }, SPEECH_TIMEOUT_MS)`
  - `export function isSpeechCapError(err: unknown): boolean` — `err instanceof ApiError` かつ `responseDetail` の `code === "tts_monthly_cap_reached"` のとき true。

### 3-2. 窓を出す条件の 1 か所（新規 `useSecretaryAccess.ts`）

- `export function useSecretaryAccess(): { ready: boolean; allowed: boolean }`。中身は今の `SecretaryChat.tsx:216`〜`SecretaryChat.tsx:223` の式をそのまま移す（`forbidden` だけは除く。`forbidden` は窓の中の状態なので `SecretaryChat` に残す）。
  - `ready = !features.loading && !superAdmin.loading && !permissions.loading`
  - `allowed = ready && features.isEnabled("secretary_chat") && superAdmin.isSuperAdmin && permissions.hasPermission("customers.view") && permissions.hasPermission("invoices.create")`
- `SecretaryChat` は `const { allowed } = useSecretaryAccess(); const visible = allowed && !forbidden;` に置き換える。条件の式を 2 か所に書かない。

### 3-3. 読み上げの部品（新規 `useSecretaryVoice.ts`）

- `export function splitForSpeech(text: string): string[]` — 純粋な関数:
  1. 「。」「！」「？」「!」「?」の直後と改行で区切る（区切りの記号は前の文に残す）。
  2. 前後の空白を除き、空の片は捨てる。
  3. 1 片が `SPEECH_MAX_CHARS`（300）字を超えるときは 300 字ごとに切る（`Array.from` で数え、1 字を途中で割らない）。
- `export function useSecretaryVoice(): { enable: () => void; disable: () => void; speak: (text: string) => Promise<"ok" | "failed" | "cap"> ; stop: () => void }`
  - `enable()` は切り替えを入れた操作の中で呼ぶ。`AudioContext` が無ければ作り、`resume()` する（Chrome に止められないため・design.md §3 の 1）。`window.AudioContext` が無い環境では何もしない（`speak` は `"failed"` を返す）。
  - `disable()` は `stop()` してから `AudioContext.close()` し、持っている参照を捨てる。
  - `stop()`: 鳴っている `AudioBufferSourceNode` を `stop()`、まだ鳴らしていない片を捨て、今の読み上げの番号（世代）を 1 進める。古い世代の結果は鳴らさない。
  - `speak(text)`: 最初に `stop()` してから始める（前の返事の残りを捨てる）。`splitForSpeech` の片を順に処理する。片 i を鳴らしている間に片 i+1 を `fetchSecretarySpeech` で取りに行く（先取りは 1 つだけ）。受け取った `Blob` を `arrayBuffer()` → `decodeAudioData` → `AudioBufferSourceNode` を `destination` につないで `start()`、`onended` で次へ。
  - 失敗: どれかの片で例外が出たら残りを捨てて止め、`isSpeechCapError` なら `"cap"`、それ以外は `"failed"` を返す。世代が変わって打ち切られたときは `"ok"` を返す（失敗の行を出さない）。
  - 鳴らし方は `AudioContext` だけ。`<audio>`・`new Audio()`・`URL.createObjectURL` を使わない（design.md §4-8。画面の安全設定を広げないため）。
  - 部品が消えるとき（`useEffect` の後片付け）に `disable()` する。

### 3-4. チャットの画面（`SecretaryChat.tsx`・`SecretaryChat.css`）

- `SecretaryChatInner` に `const [voiceOn, setVoiceOn] = useState(false);` と `const voice = useSecretaryVoice();`、失敗の行の状態 `const [voiceNote, setVoiceNote] = useState<{ id: number; kind: "failed" | "cap" } | null>(null);` を足す。保存しない（K3）。
- 切り替え: `footer` の `secretary-chat__composer` の一番上に行を 1 つ足す:
  - `<div className="secretary-chat__voice-row">` の中に `<label htmlFor="secretary-voice-toggle">{t("secretary.voiceToggle")}</label>` と `<Toggle id="secretary-voice-toggle" checked={voiceOn} onCheckedChange={onVoiceChange} />`（金型 `frontend/src/components/Toggle.tsx`）。
  - `onVoiceChange(next)`: `next` なら `voice.enable()`、違えば `voice.disable()` と `setVoiceNote(null)`。その後 `setVoiceOn(next)`。
  - `.secretary-chat__voice-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); }` を足す（値はトークンだけ）。
- `close()`: 今の 4 行に加え `voice.disable()`・`setVoiceOn(false)`・`setVoiceNote(null)`。
- `send()`: 最初（`trimmed` を確かめた後）に `voice.stop()` と `setVoiceNote(null)`。
- 読み上げる文（design.md §3 の 3）。返事の吹き出しを `replaceMessage` で入れた直後に、`voiceOn` のときだけ次の文で `void speakFor(pendingId, 文)` を呼ぶ:
  - `text`（AI の文の返事・`reply.draft.reply`）: その文の全部。
  - `ask`: `t(\`secretary.ask.${reply.draft.ask}\`)` の 1 行だけ。
  - `invoice`・`event`: 読まない。
  - 失敗（`catch` の側の `status: "error"` の吹き出し）: 読まない。
  - `created`（`markCreated`）: `voiceOn` のとき `t(target === "invoice" ? "secretary.created.invoice" : "secretary.created.event")` を読む。リンクの文字は読まない。
  - 取り消し（`markCancelled`）: 読まない。
- `speakFor(id, text)`: `const r = await voice.speak(text); if (r !== "ok") setVoiceNote({ id, kind: r });`
- 失敗の行: `renderMessage` の返す吹き出しの後ろに、`voiceNote?.id === m.id` のとき `<p className="secretary-draft__error" role="status">{t(voiceNote.kind === "cap" ? "secretary.voiceCapReached" : "secretary.voiceFailed")}</p>` を出す（今ある見た目の印を使う。新しい色を足さない）。`renderMessage` が `key` を持つ要素を返している作りを崩さないよう、`<Fragment key={m.id}>` で包む。
- `voiceOn` が切れている間は `fetchSecretarySpeech` を 1 回も呼ばない（V3）。

### 3-5. 今月の字数（backend の使用量の口と画面）

- `secretary_voice.py`: `MONTHLY_CHAR_CAP` の上に `FREE_MONTHLY_CHARS = 1_000_000  # Google の無料枠（毎月 100 万字・design.md §1）` を足す。`MONTHLY_CHAR_CAP` の注記は変えない。
- `tcg_analysis_dashboard.py`:
  - 新しい型 `class SecretaryTtsMonth(BaseModel): characters: int | None; free_limit: int; cap: int` を `LlmUsageResponse` の上に置き、`LlmUsageResponse` の最後に `secretary_tts_month: SecretaryTtsMonth` を足す。
  - `get_llm_usage` の中で、今の集計の後に `secretary_tts.read_month_total(db)` を呼ぶ（字数の数え方の正本はこの関数 1 つ。SQL を写さない）。`secretary_tts.TtsError` のときは `characters=None`（読めなかった。0 に丸めない）。`free_limit=FREE_MONTHLY_CHARS`・`cap=MONTHLY_CHAR_CAP`。
  - 期間（`days`）とは関係なく、日本時間の今月 1 日からの合計（`read_month_total` のとおり）。
- `LlmUsageSection.tsx`:
  - 型 `LlmUsageResponse` に `secretary_tts_month: { characters: number | null; free_limit: number; cap: number }` を足す。
  - 今のサマリーの `Card`（`className="llm-usage-summary"`）の直後に、同じ金型と同じクラスで `Card` を 1 枚足す: 大きな文字の欄（`llm-usage-summary__hero`）に見出し `t("analysisRules.dashboard.usage.tts.label")` と値 `t("analysisRules.dashboard.usage.tts.value", { used, limit, percent })`、小さな欄（`llm-usage-summary__stat`）に見出し `t("analysisRules.dashboard.usage.tts.capLabel")` と値 `t("analysisRules.dashboard.usage.tts.chars", { count: cap })`。`data-testid="llm-usage-tts-month"` を付ける。
  - 数は `toLocaleString()`。`percent` は `characters / free_limit * 100` を小数 1 桁。`characters` が `null` のときは値の場所に今ある `formatNumber(null, t)` と同じ「未報告」の表示を使う。
  - 新しい CSS・新しい部品を足さない。

### 3-6. 設定の欄（`PreferencesSection.tsx`）

- `useSecretaryAccess()` の `allowed` が true のときだけ、言語の行の後ろに行を 1 つ足す（同じ `account-settings-pref-row`・同じ `label` の形）。
- `allowed` になったら `getSecretaryVoice()` を 1 回呼ぶ。読めるまでは行を出さない。読めなければ行の代わりに `<div className="error-message">{t("accountSettings.secretaryVoiceLoadFailed")}</div>`。
- 部品は言語と同じ `<SelectControl size="sm" id="secretary-voice-select" ...>`（金型）。選択肢は返ってきた `voices` の順に `<option value={v}>{t(\`secretary.voice.name.${v}\`)}</option>`。`value` は `selected`。
- 変えたら `saveSecretaryVoice(next)`。返ってきた `selected` を表示に使う。失敗したら前の値に戻し、`<div className="error-message">{t("accountSettings.secretaryVoiceSaveFailed")}</div>` を出す。保存中は `disabled`。
- 「試しに聞く」は置かない（design.md §4-7）。

### 3-7. 試験

- `useSecretaryVoice.test.ts`（純粋な関数だけ）: `splitForSpeech` が (1)「こんにちは。明日は？」→ 2 片 (2) 改行で区切る (3) 650 字の 1 文 → 300・300・50 (4) 空白だけ → 0 片。
- `SecretaryChat.test.tsx` に足す（今の作りのまねで、`fetchSecretarySpeech` を `vi.mock` で数える。`window.AudioContext` は偽物を置く: `resume`・`close`・`decodeAudioData`・`createBufferSource` が `start` と `connect` を持つ物を返す）:
  - V3-a: 窓を開いた直後、切り替えは切れ（`checked` が false）。
  - V3-b: 切れのまま文の返事を受けても `fetchSecretarySpeech` は 0 回。
  - V3-c: 入れてから文の返事を受けると、最初の片の文で 1 回以上呼ばれる。
  - V3-d: 入れた状態で `fetchSecretarySpeech` が `ApiError(…, 503, { code: "tts_not_configured" })` を投げると、`secretary.voiceFailed` の文が出て、返事の文も出ている。
  - V3-e: 窓を閉じて開き直すと切り替えは切れに戻る。
- `PreferencesSection.test.tsx`（新規）: (1) 条件を満たさない人には欄が無い (2) 満たす人に選択肢が 4 つ・`selected` が選ばれている (3) 変えると `saveSecretaryVoice` が新しい値で 1 回呼ばれる。通信は `vi.mock` で差し替える。
- `test_tcg_analysis_dashboard_llm_usage.py` に足す: (1) 返す中身に `secretary_tts_month` があり `free_limit == 1_000_000`・`cap == 900_000` (2) `read_month_total` が `TtsError` を投げると `characters is None` で 200。今のこのファイルの作り（偽物の DB の差し替え方）に合わせる。

### 3-8. 翻訳キー（ja と en に同じキー。ADR-027）

| キー | ja | en |
|---|---|---|
| `secretary.voiceToggle` | 声で返事 | Read replies aloud |
| `secretary.voiceFailed` | 声を出せませんでした。文はそのまま読めます。もう一度送ると試します | Could not play the voice. You can still read the text. Send again to retry |
| `secretary.voiceCapReached` | 今月の読み上げの上限に達しました。文はそのまま読めます。来月 1 日から使えます | This month's read-aloud limit has been reached. You can still read the text. It resets on the 1st |
| `accountSettings.secretaryVoiceLabel` | 秘書の声 | Secretary voice |
| `accountSettings.secretaryVoiceLoadFailed` | 秘書の声を読み込めませんでした。画面を開き直してください | Could not load the secretary voice. Please reopen this page |
| `accountSettings.secretaryVoiceSaveFailed` | 秘書の声を保存できませんでした。もう一度選んでください | Could not save the secretary voice. Please choose again |
| `analysisRules.dashboard.usage.tts.label` | 秘書の読み上げ（今月） | Secretary read-aloud (this month) |
| `analysisRules.dashboard.usage.tts.value` | {{used}} 字 / {{limit}} 字（{{percent}}%） | {{used}} / {{limit}} chars ({{percent}}%) |
| `analysisRules.dashboard.usage.tts.capLabel` | 止める上限 | Stop limit |
| `analysisRules.dashboard.usage.tts.chars` | {{count}} 字 | {{count}} chars |

`secretary.voice.name.*`（便1 で足し済み）は変えない。失敗の文は「起きたこと＋次にすること」の形（ADR-1071・`npm run check:error-text-next-action`）。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- PR は作らない（§6）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除が要るとき／design.md と食い違うのに design.md どおりに作れないとき／新しい部品（`package.json`・`requirements.txt` の変更）が要ると分かったとき／§2 の表に無いファイルを変えないと試験・確かめが通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 画面の文字はすべて `t()`。色・寸法は CSS 変数（トークン）だけ。生の `<select>`・`<input type="checkbox">` を書かない（ADR-144・ADR-067・ADR-027）。
- 本番・Google に接続しない。鍵ファイルを作らない・探さない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、手順1 の `cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降の命令は毎回その作業場所へ cd してから流す。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/secretary-voice-bin2
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。違えば NEEDS_DECISION: で止まる。
    cd 作業場所 && git merge --ff-only origin/release/secretary-voice-bin2-card
    期待する出力: このカード（`docs/handoff/secretary-voice/card-bin2.md`）を足す commit 1 つが早送りで入る。早送りにならなければ NEEDS_DECISION: で止まる。このカードのファイルは §2 の表に含めて扱う（中身は変えない）。

手順1.5 部品を入れる
    cd 作業場所 && python3.12 -m venv /tmp/v312
    無ければ `uv venv --python 3.12 /tmp/v312`（以後 pip は `uv pip install --python /tmp/v312/bin/python` に読み替える）。
    cd 作業場所/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt
    cd 作業場所/frontend && npm ci

手順2 対象ファイルが基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat fc84e2a4b origin/main -- backend/app/services/secretary_voice.py backend/app/routers/tcg_analysis_dashboard.py frontend/src/lib/api.ts frontend/src/features/secretary frontend/src/pages/account-settings/PreferencesSection.tsx frontend/src/pages/super-admin/components/LlmUsageSection.tsx frontend/src/locales/ja.json frontend/src/locales/en.json
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順3 §3-1〜§3-8 を作る。

手順4 画面の確かめ
    cd 作業場所/frontend && npx tsc --noEmit -p tsconfig.json
    cd 作業場所/frontend && npm run check:all
    期待する出力: どちらも失敗 0。失敗は直して流し直す。

手順5 画面の試験
    cd 作業場所/frontend && npx vitest run src/features/secretary src/pages/account-settings src/pages/super-admin/components
    期待する出力: 全部 passed。

手順6 API の形を作り直す（手で書かない）
    cd 作業場所/backend && ENVIRONMENT=test /tmp/v312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json

手順7 backend の試験
    cd 作業場所/backend && /tmp/v312/bin/python -m pytest tests/test_tcg_analysis_dashboard_llm_usage.py tests/test_secretary_voice.py tests/test_tcg_analysis_dashboard_cost_summary.py -q
    期待する出力: 全部 passed（PostgreSQL が無くて skipped になったら数と理由を書いて続行）。

手順8 commit
    cd 作業場所 && git add backend frontend/api-contract/openapi.json frontend/src
    commit 文は Write でファイルに書き（1行目 `feat: secretary voice picker, read-aloud toggle and monthly chars (bin2)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat
    期待する出力: §2 の表のファイルだけ。

手順9 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表のファイルだけ。削除の数が 0 でないファイルは名前と消えた行の中身を報告に書く。表に無いファイルがあれば名前を書いて止まる。

手順10 push（PR は作らない）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/secretary-voice-bin2
    期待する出力: 手順8 の commit と同じ番号。

## 6. 受入条件（design.md §9 のうち便2 の行）と PR

| 基準 | 検証方法 |
|---|---|
| V1 の画面側: 設定に選択肢が 4 つ・未選択の人はカロンが選ばれて見える | `PreferencesSection.test.tsx`（CI）。本番は便3 で PO のアカウントで数える |
| V3 「声で返事」は最初は切れ・切れの間の読み上げの頼み 0 回・閉じたら切れに戻る | `SecretaryChat.test.tsx` V3-a〜e（CI） |
| V5 の画面側: 今月の字数の欄が出る・読めなければ 0 でなく「未報告」 | `test_tcg_analysis_dashboard_llm_usage.py`（CI）と画面の確かめ |
| 鍵が無い間は失敗の 1 行だけで文の返事は出る | V3-d（CI） |
| 文字は `t()`・ja/en 同じキー・金型とトークンだけ | `npm run check:all`・lint（CI） |
| `<audio>`・`createObjectURL` を使わない | Opus が差分を grep で 0 件と確かめる |
| 今の動きが変わらない | 既存の試験が全部緑（CI） |

PR は Opus が手元で `scripts/gh-pr-create-safe.sh` を使い ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。欄の良い例: `触るファイル: frontend/src/lib/api.ts, frontend/src/features/secretary/useSecretaryVoice.ts`（1行・カンマ区切り）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。`区分: B`・`対象ADR: ADR-1080`・`Opus 審査記録: docs/handoff/secretary-voice/review-opus.md`。

## 7. 報告

- 冒頭に「本報告はカード 便2（声を選ぶ欄と読み上げの画面）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「カード 便2 を受領」と1行書く。
- 完了報告の本文に、手順1・2・4・5・7・8・9・10 の生出力を全文含める（長い出力は失敗の行と最後の要約の行を必ず含める）。枝の名前と push した commit の番号を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
