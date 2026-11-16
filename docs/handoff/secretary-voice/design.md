# 設計 — 秘書の返事を、選んだ声で読み上げる

状態: 設計案（PO の実装承認前）。基準: `origin/main` 9906651eb。
目標: [kgi.md](kgi.md)（K1〜K5・PO 承認 2026-11-17）。現状: `docs/handoff/secretary-voice/recon.md`。事例: [research.md](research.md)。
決まりの記録: `docs/adr/ADR-1080-secretary-voice-tts.md`（Proposed）。関係: ADR-1056（秘書）・ADR-1004（使用量台帳）・ADR-1077・ADR-027・ADR-067・ADR-144・ADR-1071。

## 1. 目的と PO の決定

- 秘書のチャットの返事を、一人ひとりが選んだ声で読み上げる。ChatGPT のように一人ひとりに合わせた秘書にする最初の一歩（kgi.md §1）。
- 声は 4 つ: Aoede・Charon・Erinome・Zubenelgenubi（PO が 30 の声から聞き比べて選んだ）。まだ選んでいない人は Charon。
- 声の仕組みは Google Cloud Text-to-Speech の Chirp 3: HD（`ja-JP-Chirp3-HD-<声>`）。毎月 100 万字までは無料（recon.md §9）。

## 2. 対象と対象外

- 対象: 声の選択欄（アカウント設定「表示の好み」）・声の保存・読み上げの口（backend）・チャットの「声で返事」の切り替えと再生・字数の記録と使用量の画面の表示・月の上限。
- 対象外: 声で話しかける（聞き取り）・返事の文の言い回し・声の複製や有名人に似せた声・秘書以外の画面での読み上げ。

## 3. 作りの全体（1 往復の流れ）

1. 利用者が「声で返事」を入れる（このとき画面が音の部品 `AudioContext` を起こす。押した操作の中で起こすので Chrome に止められない・research.md T1）。
2. 秘書の返事（文）が画面に出る。今まで通り。
3. 画面が返事の文を、文の区切り（。！？と改行）で分ける。最初の 1 文から順に `POST /api/v1/assistant/speech` に文を送る。
4. backend は、本人の声を DB から読み（画面は声を送らない）、今月の字数が上限の手前かを台帳で確かめ、Google に文を送って MP3 を受け取り、台帳に字数を 1 行書いて、MP3 を返す。
5. 画面は受け取った音を `decodeAudioData` で音に直し、順に鳴らす。1 文目を鳴らしている間に 2 文目を取りに行く。
6. 切り替えを切る・窓を閉じる・次の頼みを送ると、鳴っている音を止め、残りを捨てる。

## 4. 変更の中身（ファイルごとの前と後）

### 4-1. 声の一覧の正本（新規 `backend/app/services/secretary_voice.py`）

- 前: 無い。
- 後: 声の一覧と既定はこのファイル 1 か所だけに書く。

```python
SECRETARY_VOICES: tuple[str, ...] = ("Aoede", "Charon", "Erinome", "Zubenelgenubi")
DEFAULT_SECRETARY_VOICE = "Charon"
TTS_LANGUAGE_CODE = "ja-JP"
MONTHLY_CHAR_CAP = 900_000          # 無料枠 100 万字の 9 割で止める
MAX_CHARS_PER_REQUEST = 300

def resolve_voice(stored: str | None) -> str:
    """DB の値が一覧に無い・空なら既定を返す。"""
    return stored if stored in SECRETARY_VOICES else DEFAULT_SECRETARY_VOICE

def google_voice_name(voice: str) -> str:
    return f"{TTS_LANGUAGE_CODE}-Chirp3-HD-{voice}"
```

- 画面は声の一覧を自分で持たない。`GET /api/v1/assistant/voice` が返す一覧を使う（§4-3）。声の表示名だけ翻訳キー `secretary.voice.name.<声>`（ja・en 両方）で出す。

### 4-2. 保存の場所（新しい移行 1 本・`public.users` に列 1 つ）

- 前: 声を置く列は無い。一人ずつの言語は `public.users.locale`（`migrations/053_add_users_locale.sql:5`）、画面の色は `public.users.theme`（`migrations/054_add_users_theme.sql:5`）に置かれ、`PATCH /staff/me/locale`・`PATCH /staff/me/theme`（`backend/app/routers/staff.py:212`・`backend/app/routers/staff.py:235`）で本人が書く。
- 後: 同じ形で `public.users.secretary_voice VARCHAR(40) NULL` を足す。NULL は「まだ選んでいない＝ Charon」。

```sql
-- ADR-1080: 秘書の声（一人ずつ）。NULL は未選択で既定の Charon。値の一覧の正本は backend/app/services/secretary_voice.py
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS secretary_voice VARCHAR(40);
```

- `staff_ui_preferences`（会社ごとの表）を選ばない理由: (1) 秘書を使う super admin は会社の staff 行に紐づかないことがある（`frontend/src/contexts/UiPrefsContext.tsx` の既定値の注記「staff に紐づかない admin」）。(2) 好みの書き込み `backend/app/services/staff_create.py:83`（`upsert_ui_prefs`）は全列を上書きするため、列を足すと管理者がスタッフ編集画面で保存したときに声が消える恐れがある。(3) 全テナントを回す移行が要る。`public.users` なら 3 つとも起きない。
- 値の決まり（DB の CHECK）は付けない。一覧の正本を Python 1 か所にするため（DB と 2 か所にしない）。書く口は一覧に無い値を 422 で拒む。読むときは `resolve_voice` で既定に倒す。
- 相談係の伏せたビュー（ADR-1052）: 分類の無い文字の列は伏せられる（`backend/tests/ops/test_ai_cloud_views.py:310`）。足す登録は要らない。

### 4-3. backend の口（`backend/app/routers/assistant.py`・`backend/app/schemas/assistant.py`）

守りはすべて秘書と同じ `_SECRETARY_DEPENDENCIES`（`backend/app/routers/assistant.py:88`〜`backend/app/routers/assistant.py:91`）。

| 口 | 入力 | 出力 | 中身 |
|---|---|---|---|
| `GET /assistant/voice` | なし | `{voices: [...4], default: "Charon", selected: "Charon"}` | `selected` は `resolve_voice(users.secretary_voice)` |
| `PUT /assistant/voice` | `{voice: "Aoede"}`（`Literal` で 4 つに限る） | 同上 | 本人の `users.secretary_voice` だけを書く |
| `POST /assistant/speech` | `{text: str}`（1〜300 字・空白だけは 422） | `audio/mpeg` の中身・`Cache-Control: no-store` | §4-4 |

- 文は必ず POST の中身で送る（URL に載せない）。
- 声は画面から受け取らない。backend が本人の値を読む。PC とスマホで同じ声になる（K2）。

### 4-4. 読み上げの口の中身（新規 `backend/app/services/secretary_tts.py`）

1. 今月（日本時間の月初から）の `purpose='secretary_tts'` の `billed_characters` の合計を数える。合計＋今回の字数 ＞ `MONTHLY_CHAR_CAP` なら 429（`tts_monthly_cap_reached`）を返し、Google には送らない。
2. 鍵ファイル `GOOGLE_TTS_SA_KEY_FILE` が未設定・読めないなら 503（`tts_not_configured`）。起動は止めない（今の Google の鍵 `TCG_SHEETS_SA_KEY_FILE` と同じ扱い・recon.md §6）。
3. `google-auth` のサービスアカウントの鍵で札を取り、`httpx` で `POST https://texttospeech.googleapis.com/v1/text:synthesize` に `{input:{text}, voice:{languageCode:"ja-JP", name: google_voice_name(voice)}, audioConfig:{audioEncoding:"MP3"}}` を送る。待つのは 10 秒まで。
4. 成功したら台帳に 1 行書く（§4-5）。返ってきた音（base64）を戻して返す。
5. Google の失敗・時間切れは 502（`tts_upstream_failed`）。台帳には `outcome` を失敗で 1 行書く（字数は 0 として数える・料金は成功分だけ）。
- 部品: `google-auth` を `backend/requirements.txt` に足す（読み上げ専用の大きな部品は入れない）。使い方は便1 で Context7 か公式資料で確かめる。

### 4-5. 使用量の台帳（`public.llm_usage_events`・ADR-1004 を改める）

- 前: 1 行 = Gemini の応答 1 回。字数の列は無い。`sdk` は 4 つ（`migrations/20261103_120000_create_ai_job_assignments.sql:175`）、`purpose` は 8 つ（`migrations/20261113_100000_create_secretary_rules.sql:154`）。
- 後（移行 1 本・どれも「無いときだけ」）:
  - 列 `billed_characters INTEGER NULL` を足す（Google が料金に数える字数。空白・改行を含む送った文の全字数。読み上げ以外の行は NULL）。
  - `purpose` に `secretary_tts` を足す（作り直しの形は `migrations/20261113_100000_create_secretary_rules.sql:141`〜`migrations/20261113_100000_create_secretary_rules.sql:156` と同じ）。
  - `sdk` に `google-tts-rest` を足す（作り直しの形は `migrations/20261103_120000_create_ai_job_assignments.sql:169`〜`migrations/20261103_120000_create_ai_job_assignments.sql:175` と同じ）。
- 書き方: `record_usage_isolated`（`backend/app/services/llm_budget.py`）に `billed_characters` を渡せるようにする。`model` は `ja-JP-Chirp3-HD-<声>`、`cost_usd` は無料枠の中なので 0、トークンの列は NULL。
- 1 行に書くのは字数・声・成否だけ。文そのものは書かない（会話を保存しない約束・ADR-1056）。

### 4-6. 使用量の画面（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx`）

- 前: トークンと料金だけ。
- 後: 「秘書の読み上げ（今月）」の小さな欄を 1 つ足す。表示は「◯◯字 / 1,000,000 字（◯%）」と「止める上限 900,000 字」。値は今の API（`backend/app/routers/tcg_analysis_dashboard.py:746`）に今月の字数の合計を足して返す。新しい部品は作らず、今ある部品の金型と色の印（デザイントークン）だけを使う。

### 4-7. 設定の画面（`frontend/src/pages/account-settings/PreferencesSection.tsx`）

- 前: 画面の色（`Toggle`）と言語（`SelectControl`）。
- 後: 「秘書の声」の欄を足す。部品は言語と同じ `SelectControl size="sm"`。選択肢は `GET /assistant/voice` の一覧で、表示名は `t("secretary.voice.name.<声>")`。変えたら `PUT /assistant/voice`。
- 欄が出るのは、秘書の窓が出る人だけ（`frontend/src/features/secretary/SecretaryChat.tsx:220`〜`frontend/src/features/secretary/SecretaryChat.tsx:223` と同じ条件を 1 つの関数にまとめて両方から呼ぶ。条件を 2 か所に写さない）。
- 欄の横に「試しに聞く」は置かない（字数を使うため。必要になれば別の便）。

### 4-8. チャットの画面（`frontend/src/features/secretary/`）

- 入力欄の並び（`frontend/src/features/secretary/SecretaryChat.tsx:188`）に `Toggle`（金型）で「声で返事」を置く。最初は切れている。状態は画面の中だけで持ち、保存しない（窓を閉じたら切れに戻る）。K3。
- 読み上げの部品は新しいファイル `useSecretaryVoice.ts` 1 つにまとめる（文の分け方・順に取る・順に鳴らす・止める）。
- 通信は `frontend/src/lib/api.ts` に POST で中身を受け取る口 `postBlob` を足して使う（今は GET の `getBlob` だけ・`frontend/src/lib/api.ts:280`）。通信の部品を別に作らない。
- 鳴らし方は `AudioContext.decodeAudioData` と `AudioBufferSourceNode`。`<audio>` と `blob:` の URL は使わない。理由: 画面の安全設定（`nginx/nginx.conf:96`）に `media-src` が無く `default-src 'self'` に落ちるため、`<audio>` に `blob:` を渡すと止められる（research.md T6）。音の中身は同じ場所の `/api/v1` から取るので `connect-src 'self'` で通る。安全設定は変えない。
- 失敗したら、返事の文の下に `t("secretary.voiceFailed")`（「声を出せませんでした。文はそのまま読めます。もう一度送ると試します」の形・ADR-1071）を 1 行出す。上限に達したら `t("secretary.voiceCapReached")`。文の返事は今まで通り出る。
- 新しい文字はすべて `t()`。`ja.json` と `en.json` に同じキーを足す（ADR-027）。

### 4-9. 鍵の置き場（`docker-compose.yml`）

- `backend` の環境に `GOOGLE_TTS_SA_KEY_FILE=${GOOGLE_TTS_SA_KEY_FILE:-}` と、同じ場所を読み取り専用でつなぐ行を足す（形は `docker-compose.yml:127`・`docker-compose.yml:162` と同じ）。
- 鍵そのものを本番に置くのは鍵の変更にあたる。便3 の直前に PO 本人へもう一度確かめる（kgi.md §3）。Google 側で鍵に付ける権限の名前は未確認（recon.md §8）。便3 の前に公式資料で確かめ、確かめられなければ止めて PO に聞く。

### 4-10. 触らない範囲

- 秘書の返事の文・AI に渡す文（ADR-1056・ADR-1077）・会話を保存しない作り・画面の安全設定（`nginx/nginx.conf`）・`staff_ui_preferences`・ほかの Google の鍵。

## 5. 代わりの案と選んだ理由

| 案 | 選ばない理由 |
|---|---|
| 声を `staff_ui_preferences` に置く | §4-2 の 3 つの理由 |
| 声を画面（ブラウザ）にだけ覚える | PC とスマホで同じにならない（K2 に反する） |
| ブラウザ内蔵の読み上げ（`speechSynthesis`） | PO が選んだ 4 つの声が使えない。機械ごとに声が変わる |
| Google の流しながら返す方式（双方向の通信） | 出力が MP3 でなく、画面で鳴らす作りが重くなる。1 文ずつ頼めば K4 の目安に届く見込み（Mac での実測 9 字 0.50〜0.75 秒・recon.md §7）。本番で K4 が届かなければ次の手として検討する |
| `<audio>` で鳴らし、安全設定に `media-src blob:` を足す | 安全設定を広げずに済む方法がある（§4-8） |
| 字数を台帳でなくログだけに書く（ADR-1056 の第 1 段の形） | K5（画面で今月の字数を見る）と月の上限が作れない |

## 6. 危ない点と手当て（弊害）

| 危ない点 | 手当て | 見張り |
|---|---|---|
| 費用が膨らむ | 月 90 万字で止める（429）。上限の判定は backend だけ | 上限の試験（§9 の V7） |
| 無料枠は請求先の口座ごとで、見本づくりの 4,634 字のように台帳に載らない使い方もある | 毎月 1 回、Google の請求画面の字数と台帳の字数を照らす（手作業・§10） | 月 1 回の照合の記録 |
| 長い返事で待たせる | 1 文ずつ頼み、1 文目から鳴らす | K4 の本番測定 |
| Google が止まる | 文の返事はそのまま出る。声だけ 1 行の失敗表示 | 失敗の行の数（台帳の `outcome`） |
| 返事の文を Google に送る | Google は読み上げの文と音を記録しない（recon.md §9）。会社のデータは返事の文に載る分だけで、新しく送る中身は増えない | — |
| 押す前に鳴らすと止められる | 切り替えを押した操作の中で音の部品を起こす | 画面の試験（V5） |
| 声の権利（research.md F2） | Google の既製の声だけ | — |
| 使われない（research.md F3・S2 は再生 5%） | 押した人だけに鳴らす。使われた回数を台帳で数える | 30 日後に行の数を見る（§11） |

## 7. 古い版と新しい版が混ざる間

- 便1（backend）を先に出す。画面がまだ古いので、新しい口は呼ばれない。列が足されるだけで、今の動きは変わらない。
- 便2（画面）は便1 の後。鍵が無い間は読み上げの口が 503 を返し、画面は失敗の 1 行を出す（切り替えを入れた人にだけ）。

## 8. K4 の測り方

- 評価する係（evaluator）が本番で Playwright を使う。製品のコードに測るための仕掛けは入れない。
- 測る仕掛けは、Playwright がページを開く前に差し込む台本（init script）だけ: (1) 返事の吹き出しが出た時刻を `MutationObserver` で記録 (2) `AudioBufferSourceNode.prototype.start` を包んで最初に鳴らし始めた時刻を記録。差を秒で出す。
- 短い返事（20 字以下）10 回・長い返事（60 字以上）10 回。それぞれ 9 回以上が 1.5 秒・3 秒以内で合格。

## 9. 受け入れの条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| V1（K1）設定の「秘書の声」に選択肢が 4 つ・未選択の人はカロン | 本番の画面で選択肢を数える。`GET /assistant/voice` の `selected` を見る。backend の試験で NULL→Charon・一覧に無い値→Charon |
| V2（K2）PC で選んだ声がスマホでも同じ | 本番で PC で選び、スマホで欄と読み上げの台帳の `model` を見る |
| V3（K3）「声で返事」は最初は切れ・切れている間の読み上げ 0 回 | 画面の試験（最初の状態が切れ・切れの間 `postBlob` が 0 回）。本番で窓を開き直して見る |
| V4（K4）声が出始めるまで 短い 1.5 秒以内 9/10・長い 3 秒以内 9/10 | §8 の本番測定 |
| V5（K5）今月の字数が画面に出る・字数の一致 10/10 | 使用量の画面を見る。10 回読み上げ、送った文の字数と台帳の `billed_characters` を照らす |
| V6 声の一覧の翻訳キーが ja・en に揃う | 試験: `SECRETARY_VOICES` の全部に `secretary.voice.name.<声>` が両方の言語にあること（足し忘れで CI が落ちる） |
| V7 月の上限で止まる | 試験: 今月の合計が 899,990 字のとき 20 字の頼みは 429・Google を呼ばない |
| V8 守りが秘書と同じ | 試験: 4 つの守りのどれかが欠けた人は 3 つの口すべてで拒まれる |
| V9 画面の安全設定の違反 0 件 | 本番で読み上げ中にブラウザのコンソールを見る（CSP の違反の行 0 件） |
| V10 移行を 2 回流しても同じ | 移行の試験（CI の migration-test）で 2 回流して差分 0 |

## 10. 外部・過去事例の参照と我々への応用

詳しくは [research.md](research.md)（5W2H・数値・出典つき）。要点:

- 成功の要因: 自然な声（S4: 同じ Chirp 3: HD を新聞社が 4 声で採用）・使う人が選べる（S2: 再生を押した人は 5%）・待たせない（T3: 1 秒未満が滑らか）。→ 4 声を PO が選んだ・押した人だけ・1 文ずつ。
- 失敗の要因: 費用の膨張（F1: Amazon の機器部門で 250 億ドル超の損失）・声の権利（F2: OpenAI の声の取り下げ）・使いみちが無い（F3: 39%）。→ 月の上限・既製の声だけ・目的を PO の言葉に結び、読み上げだけに絞る。
- 限界: 数値の多くは売る側の発表。日本の業務アプリでの数値つきの事例は見つからなかった。成否は K1〜K5 を本番で測って決める。

## 11. 維持の仕組み

| 何を守るか | 仕組み（機械か手か） | 置き場所 |
|---|---|---|
| 設計書の形（目標・基準表・事例・この節） | 機械: PR の確かめ「process-artifacts-gate」 | `.github/workflows/process-artifacts-gate.yml`・`scripts/check-process-artifacts.js` |
| ADR の一覧が最新 | 機械: 「ADR index is up to date」 | `.github/workflows/adr-index-check.yml` |
| 文書がたどれる | 機械: doc-index-reachability | `.github/workflows/doc-index-reachability.yml` |
| 使いみちと SDK の値が決まった一覧の中 | 機械: DB の値の決まり（CHECK） | §4-5 の移行 |
| 声の一覧の翻訳の足し忘れ | 機械: V6 の試験（便1・便2 で足す） | `backend/tests/` |
| 月の上限 | 機械: V7 の試験と backend の判定 | `backend/app/services/secretary_tts.py` |
| 「声で返事」は最初は切れ | 機械: V3 の画面の試験 | `frontend/src/features/secretary/` |
| 画面の文字は `t()` | 機械: 今ある lint（`local/no-japanese-literal`）と ja/en の同じキーの確かめ | 既存 |
| 部品の金型と色の印 | 機械: 今ある UI ガバナンスの確かめ（ADR-144・ADR-067） | 既存 |
| 台帳と Google の請求の字数が合う | **手**: 毎月 1 日に照合（機械にしない理由: Google の請求の数は請求の画面か請求の書き出しでしか読めず、今は請求の書き出しを持っていない）。担当: 設計担当の Opus が週次点検の項目に足す | 週次点検 |
| 使われているか | **手**: 便3 から 30 日後に `secretary_tts` の行の数を見る | この設計の §12 |

## 12. 進め方（3 便）

| 便 | 中身 | 合流の条件 |
|---|---|---|
| 便1 | 移行（§4-2・§4-5）・backend の 3 つの口・声の一覧・字数の記録・試験 V6〜V8・V10・`google-auth` | CI 緑・審査役の合格。移行を含むので GO 記録（委任の範囲で Opus が発行） |
| 便2 | 設定の欄・チャットの切り替えと再生・`postBlob`・使用量の画面の欄・ja/en・試験 V3 | CI 緑・審査役の合格・評価する係の画面の確かめ |
| 便3 | 鍵の置き場（compose）と本番の鍵 | **PO 本人の GO**（鍵の変更）。その後 K1〜K5 を本番で測る |

## 13. 接触面分析（6 つの面）

| 面 | 何が変わるか | 確かめ |
|---|---|---|
| 人 | super admin が設定で声を選び、チャットで切り替えを入れると声が出る。入れなければ何も変わらない | K1〜K3 |
| エージェント | 秘書の AI（容器）には何も渡さない・何も変えない | §4-10 |
| 機械 | backend に口 3 つ・部品 `google-auth`。CI に試験が足される | V6〜V8・V10 |
| データ | `public.users` に列 1 つ・台帳に列 1 つと値 2 つ。文そのものは保存しない | §4-2・§4-5 |
| 本番 | 移行 2 本（列を足すだけ・「無いときだけ」）。鍵の置き場 | 便1 の GO 記録・便3 の PO GO |
| 外部 | Google Cloud Text-to-Speech に返事の文を送る（月 90 万字まで） | §6・§11 の月 1 回の照合 |

## 14. 未確認（便の中で確かめる。確かめるまで次の便に進まない）

- 本番サーバーから Google までの時間（便3 の K4 測定で確かめる）。
- 鍵に要る Google 側の権限の名前（便3 の前）。
- `google-auth` の札の取り方（便1 の実装の前に公式資料で）。
