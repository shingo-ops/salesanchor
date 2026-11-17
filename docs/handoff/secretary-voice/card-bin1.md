---
mode: handoff
---
# 実装カード 便1: 秘書の声の保存と読み上げの口（backend と移行 2 本・画面は変えない）

親: [design.md](./design.md) §4-1〜§4-5・§6・§9（V6〜V8・V10〜V12）・§12（便1 の行）

- 状態: カード作成済み（2026-11-17 Opus）・PO 実装承認済み（2026-11-17 チャットで「1」。選択肢「1回目の作業を始めてよい」）。マージと本番への反映の GO は兼ねない。
- 担当: クラウドの Sonnet（実装）。Opus は審査・GO・マージ判断。
- 本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
- 区分: A（`migrations/` と `scripts/` と `frontend/api-contract/` を触るため。ADR-1015）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（`--draft` を付けない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1便1目的（声の保存と読み上げの口。画面・鍵の置き場は便2・便3） | ○ |
| 5 | 起点の明示（新しい枝を origin/main から） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（main との差分に想定外のファイル・削除が無いこと） | ○（§5 手順9） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順9） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の便名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md（全命令を cd で始める・1手順1命令・待たない・commit と push の後に実在を確かめる）、04-worktree.md（起点は origin/main・push は `-u origin HEAD`・作成は `new-worktree.sh`）、05-pr.md（`gh pr create` を直に使わない → PR は Opus が `gh-pr-create-safe.sh` で作る・触るファイル欄は1行カンマ区切り）、07-migration.md（`run_all_migrations.sh` に登録・採番は直近を見てから）、10-executor.md（ヒアドキュメントで書かない）、11-lint.md（L01〜L33 を人手で照合）。

基準: 設計の基準 origin/main 9906651eb。2026-11-17 に origin/main 337ebbd1b と比べ、下の §2 の既存ファイルに差分 0 を確認済み。行番号は 337ebbd1b 時点の目印で、ずれていたら前後の文で探す。

## 1. 目的（便1 で起きること）

- 利用者に見える変化は無い（画面は便2）。backend に口が 3 つ増え、DB に列が 2 つ増える。
- `GET /api/v1/assistant/voice`・`PUT /api/v1/assistant/voice` で、本人の秘書の声（4 つのどれか・未選択は Charon）を読み書きできる。
- `POST /api/v1/assistant/speech` で、本人の声で文を MP3 にして返す。鍵が無い今は 503 を返す（鍵は便3）。
- 読み上げた字数を使用量の台帳に 1 行ずつ書き、月 90 万字で止める。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `migrations/20261117_100000_add_users_secretary_voice.sql`（新規。時刻は §5 手順3 で直近を見て決め直してよい） | `public.users.secretary_voice` を足す（§3-1） |
| `migrations/20261117_100100_add_llm_usage_tts_characters.sql`（新規。同上） | 台帳に列 1 つと値 2 つ（§3-2） |
| `scripts/run_all_migrations.sh` | ファイルの最後の行の後ろに 2 行（説明の注記の行を各 1 行つける） |
| `backend/app/services/secretary_voice.py`（新規） | 声の一覧の正本（design.md §4-1 のコードそのまま）と、読み書きの 2 つの関数（§3-5） |
| `backend/app/services/secretary_tts.py`（新規） | 月の字数・札・Google への頼み・台帳（§3-4） |
| `backend/app/services/llm_budget.py` | 値の一覧に 3 つ・組分けに 1 組・`record_usage_isolated` に `billed_characters`（§3-3） |
| `backend/app/schemas/assistant.py` | 口の入力と出力の型（§3-5） |
| `backend/app/routers/assistant.py` | 口 3 つ（§3-5） |
| `frontend/api-contract/openapi.json` | §5 手順6 の命令で作り直す（手で書かない） |
| `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` | `secretary.voice.name.Aoede` など声ごとの 4 キー（§3-6） |
| `backend/tests/test_llm_usage_isolated.py` | `test_value_sets` の期待の集合に 3 つ足す |
| `backend/tests/test_super_admin_ai_jobs.py` | `test_usage_sdks_belong_to_exactly_one_provider` の組の名前の期待に `google_tts` を足す（1 行だけ） |
| `backend/tests/test_secretary_voice.py`（新規） | V6・V7・V8 と口の単体の試験（§3-7） |
| `backend/tests/test_secretary_voice_pg.py`（新規） | V10・V11・V12（§3-7） |

触らないもの: 画面のコード（`frontend/src/` のうち locales 以外すべて）・`backend/requirements.txt`（新しい部品は足さない。design.md §4-4）・`docker-compose.yml`（便3）・`nginx/`・`.github/`・`deploy.yml`・秘書の容器（`secretary-agent/` など）・秘書の返事の文と AI に渡す文・`staff_ui_preferences`・`backend/app/models.py`（声は生の SQL で読み書きする。言語 `locale` と同じ）・使用量の画面の API（`backend/app/routers/tcg_analysis_dashboard.py`。便2）・ADR と設計の文書。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. 移行 1（users）

- design.md §4-2 の SQL そのまま: 先頭の注記の行と `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS secretary_voice VARCHAR(40);`。CHECK は付けない。
- 列の COMMENT を付ける:「秘書の声（ADR-1080）。NULL は未選択で既定の Charon。値の一覧の正本は backend/app/services/secretary_voice.py」。

### 3-2. 移行 2（台帳）

- `ALTER TABLE public.llm_usage_events ADD COLUMN IF NOT EXISTS billed_characters INTEGER;` と COMMENT（「料金に数える字数。読み上げ（secretary_tts）の行だけ。ほかは NULL」）。
- 使いみちの値の決まり `llm_usage_events_purpose_check` を作り直して `secretary_tts` を足す。形は `migrations/20261113_100000_create_secretary_rules.sql` の 106〜120 行目の DO ブロックと同じ（定義に `secretary_tts` が無いときだけ DROP と ADD。新しい一覧は今の 8 つ＋ `secretary_tts`）。
- sdk の値の決まり `llm_usage_events_sdk_check` も同じ形で作り直して `google-tts-rest` を足す（定義に `google-tts-rest` が無いときだけ。新しい一覧は今の 4 つ＋ `google-tts-rest`。今の 4 つは `migrations/20261103_120000_create_ai_job_assignments.sql` 175 行目付近）。
- 「無いときだけ作り直す」の形にするのは、後の移行が足した値を消さないため（`backend/tests/ops/test_ai_job_assignments_db.py` の `test_c_rerun_keeps_values_added_by_later_migrations` と同じ考え）。
- ダウンの移行は作らない（列を足すだけで、古いコードは列を読まない）。

### 3-3. 台帳の Python 側（`backend/app/services/llm_budget.py`）

- `USAGE_PURPOSES` に `secretary_regression` と `secretary_tts`、`USAGE_SDKS` に `google-tts-rest` を足す（design.md §4-5）。
- `USAGE_SDKS_BY_PROVIDER`（同じファイル 176 行目付近）に 4 つ目の組 `"google_tts": frozenset({"google-tts-rest"})` を足す。Gemini の組には入れない。`backend/tests/test_super_admin_ai_jobs.py` の 281 行目付近 `assert set(USAGE_SDKS_BY_PROVIDER) == {"gemini", "codex", "claude"}` の右辺に `"google_tts"` を足す（その試験のほかの行は変えない）。
- `record_usage_isolated` に引数 `billed_characters: int | None = None` を足し、`_INSERT_USAGE_EVENT_OUTCOME_SQL` の列と値に `billed_characters` を足す。ほかの呼び出し元は変えない（既定の None のまま）。`_INSERT_USAGE_EVENT_SQL` と `record_usage_event`・`record_usage_event_sync` は変えない。

### 3-4. 読み上げ（新規 `backend/app/services/secretary_tts.py`）

design.md §4-4 の 1〜5 のとおり。加えて次を守る:

- 月の字数: `SELECT COALESCE(SUM(billed_characters), 0) FROM public.llm_usage_events WHERE purpose = 'secretary_tts' AND occurred_at >= :start`。`:start` は日本時間の今月 1 日 0 時（`Asia/Tokyo`）。読めなかったら 503 `tts_usage_unreadable`（Google を呼ばない）。合計は口から渡された db で読み、読み終えたら口が取引を閉じる（§3-5）。サービスの中では、Google を待つ間に db を持たない。合計＋今回の字数 ＞ `MONTHLY_CHAR_CAP` なら 429 `tts_monthly_cap_reached`（Google を呼ばない）。
- 鍵: 環境変数 `GOOGLE_TTS_SA_KEY_FILE`。未設定・読めない・鍵として読めないときは 503 `tts_not_configured`（Google を呼ばない・台帳に書かない）。読み方は `backend/app/services/tcg_distribution_svc.py` の 85〜93 行目と同じ `Credentials.from_service_account_file(鍵, scopes=["https://www.googleapis.com/auth/cloud-platform"])`。
- 札: `credentials.refresh(google.auth.transport.requests.Request())` は同期の通信なので `await asyncio.to_thread(...)` の中で呼ぶ。札はモジュールに 1 つ持ち回し、`credentials.valid` が偽のときだけ取り直す。取り直しは `asyncio.Lock` で 1 つにする。札を取れなかったら 502 `tts_upstream_failed`・台帳は `auth_failed`。
- Google への頼み: `httpx.AsyncClient(timeout=10.0)` で `POST https://texttospeech.googleapis.com/v1/text:synthesize`、頭に `Authorization: Bearer` と取った札、中身は design.md §4-4 の 3。返りの `audioContent`（base64）を戻して bytes で返す。
- 台帳（`record_usage_isolated`）: `purpose="secretary_tts"`・`sdk="google-tts-rest"`・`model=google_voice_name(声)`・`counts=UsageCounts()`・`tenant_id=本人の会社`。成功は `outcome="ok"`・`billed_characters=len(文)`。Google の失敗は `outcome="failed"`・`billed_characters=0`・`error_code` は design.md §4-4 の当て方（時間切れ `timeout`・429 `rate_limited`・401/403 `auth_failed`・ほかの HTTP の失敗と届かない `http_error`・音を読めない `unreadable`）。上限・鍵なし・合計を読めないときは書かない。
- 文そのものを台帳にもログにも書かない（ADR-1056）。ログに出すのは利用者の番号・会社・字数・秒・結果の種類だけ。
- 失敗は router の `_fail(状態, code)`（`backend/app/routers/assistant.py` 112 行目付近）と同じ形 `{"detail": {"code": ...}}` で返す。サービスは自分の例外を上げ、router が `_fail` に直す。

### 3-5. 口（`backend/app/routers/assistant.py`・`backend/app/schemas/assistant.py`）

- 3 つとも `dependencies=_SECRETARY_DEPENDENCIES`（同じファイル 87 行目付近）。本人は `get_current_user`、DB は `get_db`。
- 型: `VoiceOut {voices: list[str], default: str, selected: str}`・`VoiceIn {voice: str}`・`SpeechIn {text: str (min_length=1, max_length=300)}`。`VoiceIn` の値の確かめは router で `SECRETARY_VOICES` に無ければ 422（型の中に 4 つを写さない）。`SpeechIn` は空白だけを 422（Pydantic の validator で `text.strip()` が空なら拒む）。
- 読み書きは `secretary_voice.py` に 2 つの関数として置き、口はそれを呼ぶだけにする（PostgreSQL の試験で口と同じ関数を流すため）:
  - `async def read_voice(db, user_id) -> str`: `SELECT secretary_voice FROM public.users WHERE id = :uid`（users の読みは全行可・`migrations/20261016_180000_add_users_write_rls.sql` 10 行目）→ `resolve_voice` の値を返す。
  - `async def save_voice(db, *, user_id, tenant_id, voice) -> None`: 下の PUT の順で書く。行の数が 1 でなければ巻き戻して専用の例外（例 `VoiceNotSaved`）を上げる。
- `GET /assistant/voice`: `read_voice` → `VoiceOut`。
- `PUT /assistant/voice`: `save_voice` を呼ぶ。中の順は design.md §4-3-1（`set_tenant_context(db, current_user.tenant_id)` → `UPDATE public.users SET secretary_voice = :v WHERE id = :uid` → `clear_tenant_context(db)` → `await db.commit()`）。UPDATE の `rowcount` が 1 でなければ、commit せず巻き戻して例外 → 口が 500 `voice_not_saved`、ログに種類を出す。commit の後に db を使わない（`scripts/lint_tenant_schema.py` の Rule C。返す値は書いた値から作る）。
- `POST /assistant/speech`: 声は `read_voice` で DB から読む（画面から受け取らない）→ 月の合計を読む → **Google を呼ぶ前に `await db.rollback()` で読み取りの取引を閉じ、その後この db を使わない**（`backend/app/routers/assistant.py` 6〜7 行目の「DB の取引を開いたまま AI を待たない」・移行は `lock_timeout=1s`）→ 鍵・札・Google → `Response(content=音, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})`。OpenAPI に `audio/mpeg` の 200 を `responses=` で書く。文は POST の中身だけで受け取る。

### 3-6. 翻訳キー（V6 のため。画面はまだ使わない）

- `ja.json` の `secretary` の下に `"voice": {"name": {"Aoede": "アオイデ", "Charon": "カロン", "Erinome": "エリノメ", "Zubenelgenubi": "ズベンエルゲヌビ"}}`。
- `en.json` の同じ場所に `"voice": {"name": {"Aoede": "Aoede", "Charon": "Charon", "Erinome": "Erinome", "Zubenelgenubi": "Zubenelgenubi"}}`。
- ほかのキーは変えない。並びは今のキーの後ろ。

### 3-7. 試験

- `backend/tests/test_secretary_voice.py`（DB なし）:
  - V6: `SECRETARY_VOICES` の全部について、`frontend/src/locales/ja.json` と `en.json` の `secretary.voice.name.` の後ろに声の名前を付けたキーが空でない文字であること。読み方は `backend/tests/test_review_reason_labels_ja_sync.py` の 12〜13 行目と同じ（`Path(__file__).resolve().parents[2]`）。
  - `resolve_voice`: None・空・一覧に無い値 → Charon。4 つはそのまま。`google_voice_name("Charon") == "ja-JP-Chirp3-HD-Charon"`。
  - V7: 月の合計を 899,990 にしたとき 20 字の頼みは 429 `tts_monthly_cap_reached`、Google を呼ぶ関数が 0 回。合計を読む関数が例外のとき 503、Google を呼ばない。
  - 鍵なし（環境変数を消す）で 503 `tts_not_configured`、Google を呼ばない、台帳に書かない。
  - 成功（Google を偽物に差し替え）で 200・`audio/mpeg`・`Cache-Control: no-store`・台帳に `billed_characters=len(文)` の 1 行。Google が 500 を返す・時間切れのとき 502 `tts_upstream_failed` と台帳の `error_code`（`http_error`・`timeout`）。
  - 入力: 301 字・空・空白だけは 422。`PUT` に一覧に無い声は 422。
  - V8: `backend/tests/test_assistant_router.py` の 82〜113 行目付近の 3 つの形（機能なし・super admin でない・権限なし）に、4 つ目として `customers.view` を持たない人の形を足し、新しい 3 つの口すべてで 403 になることとして書く。
  - 声の保存の失敗: `save_voice` が `VoiceNotSaved` を上げたとき PUT が 500 `voice_not_saved` を返す（V11 の口の側）。
  - 読み上げの口で、Google を呼ぶ偽物が呼ばれた時点で、口に渡した db の `rollback` がすでに呼ばれていること（取引を開いたまま待たない）。
  - 単体試験の DB（SQLite）には `users.secretary_voice` の列が無い（ORM から作るため）。GET・PUT・読み上げの単体試験では `read_voice`・`save_voice`・月の合計を読む関数を偽物に差し替える。`models.py` は触らない。
  - 待ちで止めない: `backend/tests/test_event_loop_nonblocking.py` の形で、札の取り直しを 0.3 秒の同期の待ちに差し替えても、読み上げの関数の実行中にループが 10 回以上回ること。
- `backend/tests/test_secretary_voice_pg.py`（CI の使い捨て PostgreSQL・`needs_ci_pg`。形は `backend/tests/test_secretary_rules_tables_pg.py` の 1〜72 行目と同じ）:
  - V10: 移行 2 本を 2 回ずつ流し、列と 2 つの値の決まりの定義が 1 回目と同じ。
  - 準備: `pg` fixture の users は最小の定義で守り（RLS）が無い。`backend/tests/test_users_rls.py` 47〜61 行目と同じく、`_MIGRATIONS` の 2 本（`20261013_160000_add_self_hosted_auth_tables.sql`・`20261016_180000_add_users_write_rls.sql`）と `_GRANT_DDL` を管理者の接続で流してから、移行 1（§3-1）を流す。
  - V11: アプリの役割（salesanchor_app）の非同期の取引（`backend/tests/test_secretary_rules_service_pg.py` の `_engine` と同じ形）で `save_voice(db, user_id=999, tenant_id=999, voice="Aoede")` を流すと、管理者の接続で読んだ値が `Aoede` になる。`tenant_id=998`（別の会社）を渡すと `VoiceNotSaved` になり、値は変わらない（守りが効いている）。
  - V12: `pg_get_constraintdef` で読んだ `llm_usage_events_purpose_check`・`llm_usage_events_sdk_check` の値の集合が、`USAGE_PURPOSES`・`USAGE_SDKS` とそれぞれ同じ（足りない・余る、どちらも落ちる）。
- `backend/tests/test_llm_usage_isolated.py` の `test_value_sets`: 期待の集合に `secretary_regression`・`secretary_tts`・`google-tts-rest` を足す。ほかは変えない。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。
- PR は作らない（§6）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 止まるのは次のときだけ: 本番への接続・DB への書き込み（試験の使い捨ての DB を除く）・マージ・`main` への push・`--force`・ファイルの削除が要るとき／design.md と食い違うのに design.md どおりに作れないとき／新しい部品（`requirements.txt` の変更）が要ると分かったとき／§2 の表に無いファイルを変えないと試験が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 本番 DB・本番サーバー・Google に接続しない（Google への頼みは試験ですべて偽物に差し替える）。鍵ファイルを作らない・探さない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。手順1 で `new-worktree.sh` が作った作業場所のパス（以下「作業場所」）を報告に書き、手順1 の `cd 取り出した場所` はクラウドがこのリポジトリを取り出した最上位の場所に読み替え、手順2 以降の命令は毎回その作業場所へ cd してから流す（下の `cd 作業場所` はそのパスに読み替える）。1手順1命令。

手順1 枝を作る（起点は origin/main）
    cd 取り出した場所 && git fetch origin
    cd 取り出した場所 && bash scripts/new-worktree.sh release/secretary-voice-bin1
    cd 作業場所 && git log -1 --format=%H
    cd 作業場所 && git rev-parse origin/main
    期待する出力: 作業場所のパスと、2つの番号が同じこと。報告に書く。違えば NEEDS_DECISION: で止まる。

手順1.5 Python 3.12 の場所 `/tmp/v312` を作る（以後の `python` はすべて `/tmp/v312/bin/python`）
    cd 作業場所 && python3.12 -m venv /tmp/v312
    無ければ `uv venv --python 3.12 /tmp/v312`。続けて部品を入れる（uv で作ったときは `uv pip install --python /tmp/v312/bin/python` に読み替える）。
    cd 作業場所/backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt

手順2 対象ファイルが設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 337ebbd1b origin/main -- backend/tests/test_super_admin_ai_jobs.py backend/tests/test_users_rls.py backend/app/routers/assistant.py backend/app/schemas/assistant.py backend/app/services/llm_budget.py backend/tests/test_llm_usage_isolated.py frontend/src/locales/ja.json frontend/src/locales/en.json scripts/run_all_migrations.sh
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順3 §3-1・§3-2 の移行 2 本を作り、`scripts/run_all_migrations.sh` のファイルの最後の行の後ろに登録する（今の最後の行は、最後の `run_sql` に付いたロールバックの注記の行。その間に挟まない。説明の注記の行を各 1 行。形は今の最後の数行と同じ）。ファイル名の時刻は、次の命令の出力の最後の名前より後にする。
    cd 作業場所 && git ls-tree --name-only origin/main migrations/ | tail -5

手順4 §3-3〜§3-5 の backend を作り、§3-6 の翻訳キーを足し、§3-7 の試験を書く。

手順5 書いたものを確かめる
    cd 作業場所 && /tmp/v312/bin/python scripts/lint_tenant_schema.py
    期待する出力: 違反 0。違反があれば直して流し直す。

手順6 API の形を作り直す（手で書かない）
    cd 作業場所/backend && ENVIRONMENT=test /tmp/v312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json

手順7 試験を流す
    cd 作業場所/backend && /tmp/v312/bin/python -m pytest tests/test_secretary_voice.py tests/test_secretary_voice_pg.py tests/test_llm_usage_isolated.py tests/test_super_admin_ai_jobs.py tests/test_assistant_router.py tests/test_assistant_rules_router.py tests/test_event_loop_nonblocking.py -q
    期待する出力: 全部 passed。PostgreSQL が無くて skipped になったら、その数と理由を報告に書いて続行する（CI で確かめる）。

手順8 commit
    cd 作業場所 && git add migrations scripts/run_all_migrations.sh backend frontend/api-contract/openapi.json frontend/src/locales/ja.json frontend/src/locales/en.json
    commit 文は Write でファイルに書き（1行目 `feat: secretary voice preference and speech endpoint (bin1)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat
    期待する出力: commit の番号と、§2 の表のファイルだけ。

手順9 差分の点検
    cd 作業場所 && git diff origin/main --numstat
    期待する出力: §2 の表のファイルだけ。削除の数（2列目）が 0 でないファイルは、名前と消えた行の中身を報告に書く（既存の行の書き換えはあってよい）。表に無いファイルがあれば、その名前を報告に書いて止まる。

手順10 push（PR は作らない。PR は Opus が手元で `scripts/gh-pr-create-safe.sh` を使って作る）
    cd 作業場所 && git push -u origin HEAD
    cd 作業場所 && git ls-remote origin release/secretary-voice-bin1
    期待する出力: 手順8 の commit と同じ番号。

## 6. 受入条件（design.md §9 のうち便1 の行）

| 基準 | 検証方法 |
|---|---|
| V6 声の一覧の翻訳キーが ja・en に揃う | `test_secretary_voice.py`（CI） |
| V7 月の上限で止まる（899,990 字＋20 字 → 429・Google 0 回）・合計を読めなければ 503 | `test_secretary_voice.py`（CI） |
| V8 4 つの守りのどれかが欠けた人は 3 つの口すべてで 403 | `test_secretary_voice.py`（CI） |
| V10 移行を 2 回流しても同じ | `test_secretary_voice_pg.py`（CI の PostgreSQL）＋ CI の移行の確かめ |
| V11 声の保存が行ごとの守りの下で効く・書いた行が 1 でなければ 500 | `test_secretary_voice_pg.py`（口と同じ `save_voice` を守りのある DB で）＋`test_secretary_voice.py`（500）（CI） |
| V12 台帳の値の一覧が DB と Python で同じ | `test_secretary_voice_pg.py`（CI の PostgreSQL） |
| 今の動きが変わらない（秘書の返事・決まり帳・使用量の台帳） | 既存の試験が全部緑（CI） |
| 本番で鍵が無い間、読み上げの口は 503 `tts_not_configured` | 出荷後に Opus が本番の読み取りで 1 回確かめる（文は送らない形で） |

PR について（Opus が作る。実装役は作らない）:

- Opus が手元で `scripts/gh-pr-create-safe.sh` を使い、ready（Draft にしない）で作る。本文は `.github/PULL_REQUEST_TEMPLATE.md` を起点にし、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: scripts/run_all_migrations.sh, backend/app/services/secretary_tts.py`（1行・カンマ区切り・実際のファイル名）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- `区分: A`、`PO承認:` に PO の実装承認の言葉と日時、`Opus 審査記録: docs/handoff/secretary-voice/review-opus.md`、`対象ADR: ADR-1080`。
- 移行を含むので、マージは GO（ADR-136 の形。委任の範囲で Opus が発行）まで待つ。

## 7. 報告

- 報告の冒頭に「本報告はカード 便1（秘書の声の保存と読み上げの口）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「カード 便1 を受領」と1行書く。
- 完了報告の本文に、手順1・2・3・5・7・8・9・10 の生出力を全文含める。枝の名前と push した commit の番号を書く。
- 止まったときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
