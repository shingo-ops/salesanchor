# 設計 — 秘書の返事を、選んだ声で読み上げる

状態: 設計審査合格（審査役 3 回目）・PO 実装承認済み（2026-11-17 チャットで「1」。選択肢「1回目の作業を始めてよい」＝便1）。便2・便3 の承認と本番の鍵の GO は兼ねない。基準: `origin/main` 9906651eb（便1 のカードは 337ebbd1b で照合）。
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
3. 読み上げる文は返事の種類ごとに決める（`frontend/src/features/secretary/SecretaryChat.tsx:129`〜`frontend/src/features/secretary/SecretaryChat.tsx:171` の 5 種類）:
   - 文の返事（`text`）: 吹き出しの文の全部。
   - 聞き返し（`ask`）: 最後の問いの 1 行（`t("secretary.ask.<欄>")`）だけ。「ここまでの予定」と埋まった欄の一覧は読まない。
   - 作った知らせ（`created`）: 知らせの文だけ。リンクの文字は読まない。
   - 請求書と予定の下書き（`invoice`・`event`）: 読まない。中身は直して押す入力欄の集まりで、文ではないため。
   画面はこの文を、文の区切り（。！？と改行）で分ける。区切った 1 つが 300 字を超えるときは、さらに 300 字ごとに切る（AI が自由に書く「わからない」の返事は長さの決まりが無いため・recon.md §2）。最初の 1 文から順に `POST /api/v1/assistant/speech` に文を送る。
4. backend は、本人の声を DB から読み（画面は声を送らない）、今月の字数が上限の手前かを台帳で確かめ、Google に文を送って MP3 を受け取り、台帳に字数を 1 行書いて、MP3 を返す。
5. 画面は受け取った音を `decodeAudioData` で音に直し、順に鳴らす。1 文目を鳴らしている間に 2 文目を取りに行く。
6. 切り替えを切る・窓を閉じる・次の頼みを送ると、鳴っている音を止め、残りを捨てる。

## 4. 変更の中身（ファイルごとの前と後）

### 4-1. 声の一覧の正本（新規 backend/app/services/secretary_voice.py）

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
| `PUT /assistant/voice` | `{voice: str}`（`SECRETARY_VOICES` に無い値は 422。型の中に 4 つを写さない） | 同上 | 本人の `users.secretary_voice` だけを書く。書き方は §4-3-1 |
| `POST /assistant/speech` | `{text: str}`（1〜300 字・空白だけは 422） | `audio/mpeg` の中身・`Cache-Control: no-store` | §4-4 |

- 文は必ず POST の中身で送る（URL に載せない）。

#### 4-3-1. `public.users` への書き方（行ごとの守り）

- `public.users` の書き換えは、行ごとの守り（RLS）で「今の会社の文脈が行の会社と同じ」か「運営者の印」が要る（`migrations/20261016_180000_add_users_write_rls.sql:20`〜`migrations/20261016_180000_add_users_write_rls.sql:28`）。文脈を付けずに書くと、0 行に当たって黙って何も変わらない（K2 が壊れる）。
- よって言語の書き方（`backend/app/routers/staff.py:225`〜`backend/app/routers/staff.py:231`）と同じく、`set_tenant_context(db, current_user.tenant_id)` → `UPDATE public.users SET secretary_voice = :v WHERE id = :uid` → `clear_tenant_context(db)` → commit の順にする。
- 書いた行の数が 1 でなければ 500 を返し、ログに種類を出す（黙って成功にしない）。
- 読みと書きは `backend/app/services/secretary_voice.py` の 2 つの関数 `read_voice(db, user_id)`・`save_voice(db, *, user_id, tenant_id, voice)` に置き、口はそれを呼ぶだけにする（PostgreSQL の試験で口と同じ関数を流すため）。
- 試験: RLS が効いた PostgreSQL（users の書込の守りの移行を流した DB）で、アプリの役割の取引から `save_voice` を流し、行の値が変わること。別の会社の番号を渡すと 0 行で失敗になること（V11）。
- 声は画面から受け取らない。backend が本人の値を読む。PC とスマホで同じ声になる（K2）。

### 4-4. 読み上げの口の中身（新規 backend/app/services/secretary_tts.py）

1. 今月（日本時間の月初から）の `purpose='secretary_tts'` の `billed_characters` の合計を数える。合計＋今回の字数 ＞ `MONTHLY_CHAR_CAP` なら 429（`tts_monthly_cap_reached`）を返し、Google には送らない。合計を読めなかったとき（DB の失敗）は 503 を返し、Google には送らない（数えられないときは止める側に倒す）。
   - 同時の頼みが同じ合計を読んで一緒に通ることは受け入れる。1 人の画面で同時に出るのは 2 文（鳴らし中＋次の 1 文）で、窓を複数開いても超える分は「同時の数 × 300 字」。止める上限 90 万字と無料枠 100 万字の間の 10 万字に収まる（§6）。
   - 合計と声を読んだら、Google を呼ぶ前に読み取りの取引を閉じる（`await db.rollback()`）。閉じたあとはその db を使わない。同じファイルの決まり「DB の取引を開いたまま AI を待たない」（`backend/app/routers/assistant.py:6`〜`backend/app/routers/assistant.py:7`）に従う。台帳は自分の取引で書く `record_usage_isolated` を使う。
2. 鍵ファイル `GOOGLE_TTS_SA_KEY_FILE` が未設定・読めないなら 503（`tts_not_configured`）。起動は止めない（今の Google の鍵 `TCG_SHEETS_SA_KEY_FILE` と同じ扱い・recon.md §6）。
3. `google-auth` のサービスアカウントの鍵で札を取り、`httpx` で `POST https://texttospeech.googleapis.com/v1/text:synthesize` に `{input:{text}, voice:{languageCode:"ja-JP", name: google_voice_name(voice)}, audioConfig:{audioEncoding:"MP3"}}` を送る。待つのは 10 秒まで。
4. 成功したら台帳に 1 行書く（§4-5）。返ってきた音（base64）を戻して返す。
5. Google の失敗・時間切れは 502（`tts_upstream_failed`）。台帳には `outcome` を失敗で 1 行書く（字数は 0 として数える・料金は成功分だけ）。
- 部品: 新しい部品は足さない。`google-auth` は今の部品（`backend/requirements.txt` の `google-auth-oauthlib`・`google-auth-httplib2`）に付いて入っており、同じ使い方がすでにある（鍵の読み方 `backend/app/services/tcg_distribution_svc.py:85`〜`backend/app/services/tcg_distribution_svc.py:93`・札の取り直し `backend/app/services/google_calendar.py:267`）。札の取り方は Context7（google-auth-library-python）で確かめた: `service_account.Credentials.from_service_account_file(鍵, scopes=["https://www.googleapis.com/auth/cloud-platform"])` → `credentials.refresh(google.auth.transport.requests.Request())` → `credentials.token` を `Authorization: Bearer` に使う。範囲 `cloud-platform` は Google の読み上げの公式の書き方の例と同じ。
- 待ちでアプリを止めない: `refresh` は同期の通信なので `asyncio.to_thread` の中で呼ぶ。札はプロセスの中で 1 つ持ち回し、`credentials.valid` が偽のときだけ取り直す（同時の取り直しは `asyncio.Lock` で 1 つにする）。Google への頼みは `httpx.AsyncClient`（秘書の容器を呼ぶ `_call_agent` と同じ形・`backend/app/routers/assistant.py:210`）。
- 台帳の失敗の種類は今の 9 つ（`backend/app/services/llm_budget.py` の `USAGE_ERROR_CODES`）に当てる: 時間切れ → `timeout`、Google の 429 → `rate_limited`、401・403 → `auth_failed`、ほかの HTTP の失敗と届かない → `http_error`、音を読めない → `unreadable`、札を取れない → `auth_failed`。新しい種類は足さない。

### 4-5. 使用量の台帳（`public.llm_usage_events`・ADR-1004 を改める）

- 前: 1 行 = Gemini の応答 1 回。字数の列は無い。`sdk` は 4 つ（`migrations/20261103_120000_create_ai_job_assignments.sql:175`）、`purpose` は 8 つ（`migrations/20261113_100000_create_secretary_rules.sql:120`）。
- 後（移行 1 本・どれも「無いときだけ」）:
  - 列 `billed_characters INTEGER NULL` を足す（Google が料金に数える字数。空白・改行を含む送った文の全字数。読み上げ以外の行は NULL）。
  - `purpose` に `secretary_tts` を足す（作り直しの形は `migrations/20261113_100000_create_secretary_rules.sql:106`〜`migrations/20261113_100000_create_secretary_rules.sql:120` と同じ）。
  - `sdk` に `google-tts-rest` を足す（作り直しの形は `migrations/20261103_120000_create_ai_job_assignments.sql:169`〜`migrations/20261103_120000_create_ai_job_assignments.sql:175` と同じ）。
- Python 側の値の一覧も同じ便で足す。`backend/app/services/llm_budget.py:159`〜`backend/app/services/llm_budget.py:172` の `USAGE_PURPOSES` に `secretary_tts`、`USAGE_SDKS` に `google-tts-rest`。あわせて `USAGE_SDKS_BY_PROVIDER`（`backend/app/services/llm_budget.py:176`）に 4 つ目の組 `"google_tts": frozenset({"google-tts-rest"})` を足し、`backend/tests/test_super_admin_ai_jobs.py:281` の組の名前の期待に `google_tts` を足す（どの sdk もちょうど 1 つの組に属する決まり・同じファイル 275〜281 行目）。Gemini の組には入れない（読み上げは Gemini ではない）。この組を引くのは担当表の画面と秘書の口だけで、担当の提供元に `google_tts` は無いので画面の数は変わらない。一覧に無い値は `backend/app/services/llm_budget.py:250`〜`backend/app/services/llm_budget.py:254` で例外になり、`record_usage_isolated` はその例外をログに出して飲み込む（`backend/app/services/llm_budget.py:419`〜`backend/app/services/llm_budget.py:420`）。足し忘れると行が 1 行も書かれず、月の上限が常に 0 字と数えて効かなくなる。
- 今すでに DB と Python の一覧はずれている（観測: DB の `purpose` は `secretary_regression` を含む 8 つ・Python の `USAGE_PURPOSES` は 7 つ）。この便で `secretary_regression` も Python に足し、「DB の値の決まりの一覧と Python の一覧が同じ」ことを確かめる試験を足す（V12）。今後のずれも CI で落ちる。
- 書き方: `record_usage_isolated` に `billed_characters` を渡せるようにし、書く SQL（`_INSERT_USAGE_EVENT_OUTCOME_SQL`）にも列を足す。`model` は `ja-JP-Chirp3-HD-<声>`、トークンの列は NULL。`cost_usd` は NULL になる（単価表に無いモデルと、トークンが全部空のときは NULL を返す作り・`backend/app/services/llm_budget.py:227`〜`backend/app/services/llm_budget.py:231`）。料金は字数で見る（§4-6）。
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
- 読み上げの部品は新しいファイル useSecretaryVoice.ts（新規） 1 つにまとめる（文の分け方・順に取る・順に鳴らす・止める）。
- 通信は `frontend/src/lib/api.ts` に POST で中身を受け取る口 `postBlob` を足して使う（今は GET の `getBlob` だけ・`frontend/src/lib/api.ts:280`）。通信の部品を別に作らない。
- 鳴らし方は `AudioContext.decodeAudioData` と `AudioBufferSourceNode`。`<audio>` と `blob:` の URL は使わない。理由: 画面の安全設定（`nginx/nginx.conf:96`）に `media-src` が無く `default-src 'self'` に落ちるため、`<audio>` に `blob:` を渡すと止められる（research.md T6）。音の中身は同じ場所の `/api/v1` から取るので `connect-src 'self'` で通る。安全設定は変えない。
- 失敗したら、返事の文の下に `t("secretary.voiceFailed")`（「声を出せませんでした。文はそのまま読めます。もう一度送ると試します」の形・ADR-1071）を 1 行出す。上限に達したら `t("secretary.voiceCapReached")`。文の返事は今まで通り出る。
- 新しい文字はすべて `t()`。`frontend/src/locales/ja.json` と `frontend/src/locales/en.json` に同じキーを足す（ADR-027）。

### 4-9. 鍵の置き場（`docker-compose.yml`）

- `backend` の環境に `GOOGLE_TTS_SA_KEY_FILE=${GOOGLE_TTS_SA_KEY_FILE:-}` と、同じ場所を読み取り専用でつなぐ行を足す（形は `docker-compose.yml:127`・`docker-compose.yml:162` と同じ）。
- 鍵そのものを本番に置くのは鍵の変更にあたる。便3 の直前に PO 本人へもう一度確かめる（kgi.md §3）。Google 側で鍵に付ける権限の名前は未確認（recon.md §8）。便3 の前に公式資料で確かめ、確かめられなければ止めて PO に聞く。
- **追補（2026-11-18 Opus・便3a）**: 上の「形は `:127`・`:162` と同じ」をやめる。その形を写すと、鍵が 2 つとも未設定の環境で backend に `/dev/null:/dev/null:ro` が 2 本並び、つなぐ先が重なる（重なったときの Docker の動きは未確認）。代わりに、つなぐ先をコンテナの中の固定の場所（/run/google-tts-sa.json）にし、環境の値は `GOOGLE_TTS_SA_KEY_FILE=${GOOGLE_TTS_SA_KEY_FILE:+/run/google-tts-sa.json}`、つなぐ行は `${GOOGLE_TTS_SA_KEY_FILE:-/dev/null}:/run/google-tts-sa.json:ro` とする。`${VAR:+replacement}` は値があるときだけ replacement、無ければ空（Docker 公式の Compose の説明「Interpolation」の節・2026-11-18 Context7 で確認）。値が空なら `backend/app/services/secretary_tts.py` の `_credentials()` が 503 `tts_not_configured` を返す（今と同じ）。
- **追補（2026-11-18 Opus・権限の名前）**: Google 公式の権限の一覧（`https://docs.cloud.google.com/iam/docs/roles-permissions`）に Text-to-Speech 専用の役のページは無い（`speech` は Speech-to-Text）。公式の始め方（`text-to-speech/docs/get-started`）にも役を付ける手順は無い。決め方: 鍵を置いた直後に本番から 1 回読み上げを頼み、200 なら足りている・403 なら権限が足りないと判断する（便3b の最初の確かめ）。
- 便の分け方: **便3a** = compose の 2 行（鍵が無くても今と同じ動き・委任 GO）。**便3b** = PO が鍵を作り、VPS に置き `.env` に場所を書く（PO 本人の GO）。
- **追補（2026-11-18 Opus・便3a-2）**: 便3a の反映後、本番の backend の箱に `GOOGLE_TTS_SA_KEY_FILE` も /run/google-tts-sa.json のつなぎも無いことを読み取りで確かめた。本番の backend は compose ではなく `scripts/blue-green-cutover.sh` の `docker run`（`.env` のキーを名前だけで渡し、つなぎは 1 本ずつ手書き）で作られるため（`.github/workflows/deploy.yml` の Step 3b）。設計の入れ忘れ（compose だけを見た）。そこで **便3a-2** として、入れ替え手順に compose と同じ形のつなぎを足す（`.env` に場所があり、ファイルが在るときだけ。無ければつながず警告して入れ替えは続ける。`GOOGLE_TTS_SA_KEY_FILE` は名前で渡す一覧から外す）。あわせて、compose の鍵ファイルを固定の場所につなぐ行と `${X:+...}` で値を置き換える環境の行を入れ替え手順に入れ忘れると落ちる試験を足す（今の `backend/tests/test_bg_cutover_volume_parity.py` は名前つきの置き場だけを見ていた。2026-11-04 の geoip と同じ種類の 2 回目）。作業カード: [card-bin3a2.md](./card-bin3a2.md)。PO 実装承認: 2026-11-18「1」。
- 代わりの案と選ばなかった理由（便3a-2）: (a) `.env` に箱の中の場所 /run/google-tts-sa.json を書き、つなぎだけ足す → `.env` の 1 つの値が compose では VPS 上の場所・入れ替え手順では箱の中の場所と意味が分かれ、`docker compose` で backend を起こす戻しの道（deploy.yml の Finalize）で壊れる。(b) 入れ替え手順をやめて compose で起こす → 無停止の入れ替え（docs/handoff/zero-downtime-deploy/design.md）を捨てることになり、範囲が大きすぎる。(c) ファイルが無いとき入れ替えを止める → 読み上げ 1 つのために反映全体が止まる。警告だけにし、便3b の最初の確かめ（本番から 1 回読み上げて 200）で見つける。
- 便3b への申し送り（2026-11-18 Opus が本番で読み取りだけで確かめた）: 本番の backend の箱は `uid=100(appuser)` で動く。今ある鍵ファイル tcg-sheets-sa.json は `644 ubuntu:ubuntu`。読み上げの鍵ファイルも箱の利用者が読める権限（同じ 644 か、それに相当する持ち主の設定）で置かないと、`_credentials()` が読めず 503 になる。置き方は便3b で PO に示す。
- **追補（2026-11-18 Opus・便3b 手順書）**: PO の選択「1」（鍵の作り方と置き方を手順書にして渡す）により、手順書 [card-bin3b.md](./card-bin3b.md) を作った。反映（`.github/workflows/deploy.yml` Step 2）は決まった名前の行だけを書き直すため、手で足した `GOOGLE_TTS_SA_KEY_FILE` の行は消えないことを確かめた。鍵は新しいサービスアカウント `secretary-tts` で作る（表計算用の鍵と別に止められるように）。

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
| 費用が膨らむ | 月 90 万字で止める（429）。上限の判定は backend だけ。合計を読めなければ止める（503）。同時の頼みで超える分（同時の数 × 300 字）は 10 万字の余白で受ける | 上限の試験（§9 の V7）・値の一覧の一致の試験（V12） |
| 台帳に書けず上限が数えられない | Python と DB の値の一覧を同じ便で足し、一致を試験する（§4-5） | V12 |
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
- 短い返事（20 字以下）10 回・長い返事（30 字以上）10 回。それぞれ 9 回以上が 1.5 秒・3 秒以内で合格。
- 長い返事の線は 30 字（PO 2026-11-17「1」）。決まった返事の最長は 44 字で、60 字以上は 0 個だったため（`frontend/src/locales/ja.json` の `secretary.*` 52 個を数えた）。
- 測る返事（決まった返事なので毎回同じ文で測れる）:
  - 長い: `secretary.ask.end`（36 字）を 5 回・`secretary.ask.add_meet`（31 字）を 5 回。
    - end が出る条件: 題と始まりの日時があり、終日でなく、終わりを言わない予定の頼み（終日なら終わりは始まりで埋まり、聞かれない）。
    - add_meet が出る条件: 題・始まり・終わりがそろった打ち合わせの頼みで、Meet に触れない。測るのは Google の予定をつないだ本人（PO）。測る前に、同期の向きが「両方向」か「アプリから Google だけ」であることを読み取りで確かめる。
    - どちらかの条件がそろわないときは、10 回とも end で測る。
  - 短い: 20 字以下の決まった返事が出る頼み。どの頼みを使うかは便3 の前にこの節へ書き足し、審査役に見せる。

## 9. 受け入れの条件と確かめ方

| 基準 | 検証方法 |
|---|---|
| V1（K1）設定の「秘書の声」に選択肢が 4 つ・未選択の人はカロン | 本番の画面で選択肢を数える。`GET /assistant/voice` の `selected` を見る。backend の試験で NULL→Charon・一覧に無い値→Charon。未選択に戻す口は作らないので、本番の確かめは V2 より先に行う。使うのは PO のアカウント（便3 の時点で `secretary_voice` が NULL であることを読み取りで確かめてから） |
| V2（K2）PC で選んだ声がスマホでも同じ | 本番で PC で選び、スマホで欄と読み上げの台帳の `model` を見る |
| V3（K3）「声で返事」は最初は切れ・切れている間の読み上げ 0 回 | 画面の試験（最初の状態が切れ・切れの間 `postBlob` が 0 回）。本番で窓を開き直して見る |
| V4（K4）声が出始めるまで 短い 1.5 秒以内 9/10・長い 3 秒以内 9/10 | §8 の本番測定 |
| V5（K5）今月の字数が画面に出る・字数の一致 10/10 | 使用量の画面を見る。10 回読み上げ、送った文の字数と台帳の `billed_characters` を照らす。毎日の数: 台帳の行は時刻つきなので、日ごとの合計を読み取りで出して画面の今月の合計と合うかを見る。注: この照らしはアプリが書いた数どうしの一致で、Google の請求の数との一致は §11 の月 1 回の照合でしか確かめられない |
| V6 声の一覧の翻訳キーが ja・en に揃う | 試験: `SECRETARY_VOICES` の全部に `secretary.voice.name.<声>` が両方の言語にあること（足し忘れで CI が落ちる） |
| V7 月の上限で止まる | 試験: 今月の合計が 899,990 字のとき 20 字の頼みは 429・Google を呼ばない |
| V8 守りが秘書と同じ | 試験: 4 つの守りのどれかが欠けた人は 3 つの口すべてで拒まれる |
| V9 画面の安全設定の違反 0 件 | 本番で読み上げ中にブラウザのコンソールを見る（CSP の違反の行 0 件） |
| V10 移行を 2 回流しても同じ | 移行の試験（CI の migration-test）で 2 回流して差分 0 |
| V11 声の保存が行ごとの守りの下で効く | 試験: RLS が効いた PostgreSQL で、口と同じ `save_voice` を流すと行の値が変わる・別の会社の番号では 0 行で失敗・口は書いた行が 1 でなければ 500 |
| V12 台帳の値の一覧が DB と Python で同じ | 試験: `llm_usage_events` の `purpose`・`sdk` の値の決まりの一覧と `USAGE_PURPOSES`・`USAGE_SDKS` が同じ（ずれたら CI が落ちる） |

## 10. 外部・過去事例の参照と我々への応用

詳しくは [research.md](research.md)（5W2H・数値・出典つき）。要点:

- 成功の要因: 自然な声（S4: 同じ Chirp 3: HD を新聞社が 4 声で採用）・使う人が選べる（S2: 再生を押した人は 5%）・待たせない（T3: 1 秒未満が滑らか）。→ 4 声を PO が選んだ・押した人だけ・1 文ずつ。
- 失敗の要因: 声の権利（F2: OpenAI の声の取り下げ）・使いみちが無い（F3: 39%）。→ 既製の声だけ・目的を PO の言葉に結び、読み上げだけに絞る。F1（Amazon の機器部門で 250 億ドル超の損失）は機器の安売りという商売の形の失敗で、API の使いすぎとは別物。月の上限の根拠にはしない（上限の根拠は無料枠と料金表・research.md T4）。
- 限界: 数値の多くは売る側の発表。日本の業務アプリでの数値つきの事例は見つからなかった。成否は K1〜K5 を本番で測って決める。

## 11. 維持の仕組み

守り手: 設計担当の Opus（月 1 回の請求の照合と 30 日後の利用の数えを週次点検の項目に足す）。機械の見張りは下の表の CI と DB の決まり。

| 何を守るか | 仕組み（機械か手か） | 置き場所 |
|---|---|---|
| 設計書の形（目標・基準表・事例・この節） | 機械: PR の確かめ「process-artifacts-gate」 | `.github/workflows/process-artifacts-gate.yml`・`scripts/check-process-artifacts.js` |
| ADR の一覧が最新 | 機械: 「ADR index is up to date」 | `.github/workflows/adr-index-check.yml` |
| 文書がたどれる | 機械: doc-index-reachability | `.github/workflows/doc-index-reachability.yml` |
| 使いみちと SDK の値が決まった一覧の中 | 機械: DB の値の決まり（CHECK）と V12 の一致の試験 | §4-5 の移行・`backend/tests/` |
| 声の一覧の翻訳の足し忘れ | 機械: V6 の試験（便1・便2 で足す） | `backend/tests/` |
| 月の上限 | 機械: V7 の試験と backend の判定 | backend/app/services/secretary_tts.py |
| 「声で返事」は最初は切れ | 機械: V3 の画面の試験 | `frontend/src/features/secretary/` |
| 画面の文字は `t()` | 機械: 今ある lint（`local/no-japanese-literal`）と ja/en の同じキーの確かめ | 既存 |
| 部品の金型と色の印 | 機械: 今ある UI ガバナンスの確かめ（ADR-144・ADR-067） | 既存 |
| 台帳と Google の請求の字数が合う | **手**: 毎月 1 日に照合（機械にしない理由: Google の請求の数は請求の画面か請求の書き出しでしか読めず、今は請求の書き出しを持っていない）。担当: 設計担当の Opus が週次点検の項目に足す | 週次点検 |
| 使われているか | **手**: 便3 から 30 日後に `secretary_tts` の行の数を見る | この設計の §12 |

## 12. 進め方（3 便）

| 便 | 中身 | 合流の条件 |
|---|---|---|
| 便1 | 移行（§4-2・§4-5）・backend の 3 つの口・声の一覧・字数の記録・Python の使いみちの一覧への `secretary_regression` の追加・試験 V6〜V8・V10〜V12・声の表示名の翻訳キー（V6 のため） | CI 緑・審査役の合格。移行を含むので GO 記録（委任の範囲で Opus が発行） |
| 便2 | 設定の欄・チャットの切り替えと再生・`postBlob`・使用量の画面の欄・ja/en・試験 V3 | CI 緑・審査役の合格・評価する係の画面の確かめ |
| 便3 | 鍵の置き場（compose）と本番の鍵 | **PO 本人の GO**（鍵の変更）。その後 K1〜K5 を本番で測る |

## 13. 接触面分析（6 つの面）

| 面 | 何が変わるか | 確かめ |
|---|---|---|
| 人 | super admin が設定で声を選び、チャットで切り替えを入れると声が出る。入れなければ何も変わらない | K1〜K3 |
| エージェント | 秘書の AI（容器）には何も渡さない・何も変えない | §4-10 |
| 機械 | backend に口 3 つ（新しい部品は足さない）。CI に試験が足される | V6〜V8・V10〜V12 |
| データ | `public.users` に列 1 つ・台帳に列 1 つと値 2 つ。文そのものは保存しない | §4-2・§4-5 |
| 本番 | 移行 2 本（列を足すだけ・「無いときだけ」）。鍵の置き場 | 便1 の GO 記録・便3 の PO GO |
| 外部 | Google Cloud Text-to-Speech に返事の文を送る（月 90 万字まで） | §6・§11 の月 1 回の照合 |

## 14. 未確認（便の中で確かめる。確かめるまで次の便に進まない）

- 本番サーバーから Google までの時間（便3 の K4 測定で確かめる）。
- 鍵に要る Google 側の権限の名前（便3 の前）。
- ~~`google-auth` の札の取り方~~ → 2026-11-17 Context7 で確かめた（§4-4）。
