# 設計審査 7回目（secretary-chatgpt design v7）

- 審査役: Architect（クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 対象: `release/secretary-chatgpt-ai-roster` head b15612e21 の `docs/handoff/secretary-chatgpt/design.md`（v7）・`recon.md`・`kgi.md`、前回の指摘 `origin/review/secretary-chatgpt-r6` の `review6.md`
- 根拠: `git show origin/main:<path>`（origin/main d828bb269）。design が照合に使った 44098dc31 との差分を、`scripts/run_all_migrations.sh`・`migrations`・`backend/tests/rls_bootstrap.py`・`backend/tests/ops/test_ai_cloud_views.py`・`backend/app/services`・`backend/app/routers/assistant.py`・`backend/app/tasks`・`.github/workflows/deploy.yml`・`secretary-agent` で取って0件（`git diff --stat 44098dc31 origin/main -- ...` の出力が空）
- 製品のファイルは変えていない。この枝で足したのはこのファイルだけ

## 6回目の5件の確かめ（1件ずつ）

| # | 結果 | 根拠（origin/main） |
|---|---|---|
| P1 流れ直し | 直った（ただし CHECK の作り直しの形に新しい穴。Q1） | `run_sql`（`scripts/run_all_migrations.sh:110-118`）は毎回 psql に流すだけ。design §4-1 に `IF NOT EXISTS`・`ON CONFLICT DO NOTHING`・`CREATE OR REPLACE TRIGGER`・CHECK の名前付けが入り、§7 1a に「2回流して画面で変えた担当が残る」試験が入った。CI 側も変えた SQL を2回流す（`.github/workflows/migration-test.yml:1236`・`:1319`）ので形が合う。補足: migration の段は migration の変更がある便でだけ動く（`deploy.yml:770` の `steps.gate.outputs.migrations`）。「deploy のたびに」は「migration を含む deploy のたびに」が正確だが、流れ直す前提は同じ |
| P2 分類の試験の流す順番 | 直った | `20260930_150000:40` が `public.extraction_attempts` を参照し、`20260921_110000_pipeline_tables_public.sql:112` がそれを作る。`:16` が参照する suppliers は `056_...:45`、`:237` の products は `062_...:30` で、どちらも bootstrap の一覧（`backend/tests/rls_bootstrap.py:14-34`）にある。units・conditions は bootstrap で作られず（`rls_bootstrap.py` に作る行が無い）、`20260921_110000:183-` の FK なしの側を通る。外部の参照はほかに無い（`git show ...:20260921_110000 \| grep REFERENCES` の結果）。実際に流れるかは【未確認】だが、design は「流れなければ実装を止めて設計に戻す」と書いており足りる。前例として `backend/tests/test_llm_usage_events_migration_pg.py:16-17` が同じ `20260921_110000` を先に流して `20260930_150000` を流している |
| P3 v102 の2行の見方 | 直った | `AttemptRecorder.id` は1つの recorder に1つの uuid（`tcg_extraction_record_svc.py:56`）。v102 の台帳の行は `extraction_attempt_id=recorder.id`（`line_analysis_v102_svc.py:551`）。その場の送り直しは最大2回（`:464`）なので、1つの attempt の failed は最大3行。§7 1b が extraction_attempt_id で数える形になった |
| P4 秘書の担当が読めない時 | 直った | §5-3 に「`_log(..., "not_ready", None)` を出して `_fail(503, "not_ready")`、台帳は書かない」が入った。`_log` の引数（`assistant.py:66`）と合う。読み取りが DB の失敗で終わっても、HTTPException が `get_db` の except で rollback される（`database.py:46-55`）。言い回しの細部: `_fail` は例外を返す関数（`assistant.py:60-63`）なので「返す」ではなく `raise _fail(...)`（軽・カードで扱える） |
| P5 TRUNCATE と GRANT | 直った | §4-1 に `BEFORE TRUNCATE ... FOR EACH STATEMENT`、GRANT は前例 `20261101_130000_add_new_device_approval.sql:126-132` と同じ形が入った。§7 1a のトリガーの試験に TRUNCATE も入った。試験の DB を丸ごと空にする共通の道具が public の表を TRUNCATE するかを見たが、当たったのは tenant の表だけ（`backend/tests/test_lead_merge_pg.py:344`）で、トリガーがほかの試験を壊す所は見当たらない |

## 新しい指摘

### Q1. 重さ: 中 — §4-1（CHECK を毎回「DROP → ADD」で作り直す形は、前に deploy を落とした形）
- 根拠（origin/main）: `migrations/20261020_110000_line_conditions_value_group_add_supply.sql:5-6`・`:12-13`。「run_all_migrations.sh は毎回全 migration を流すため、後の migration が広げた制約を狭め直さないよう、今の制約の定義を見て、すでに目的の値を含むなら何もしない（deploy 39356908634・39359118758 の失敗の復旧）」と書かれ、`:15-36` で `pg_get_constraintdef(c.oid) LIKE '%supply%'` を見てから DROP → ADD している。`20261019_100000_...promo_single.sql`・`20261020_100000_...booklet.sql` も同じ形（`git grep -l pg_get_constraintdef origin/main -- migrations`）。ロックの待ち時間は1秒で、最大40回まで流し直す（`run_all_migrations.sh:57-58`・`:63`）。
- 足りない所: design §4-1 は「CHECK は名前を付け、`DROP CONSTRAINT IF EXISTS` → `ADD` の順にする」とだけ書いており、条件なしで毎回作り直す形になっている。
  - 後の migration が同じ CHECK をさらに広げる（例: ADR-1057 のあとで purpose・sdk・error_code・provider・job_key を足す）と、その値の行がある状態で本便の migration が流れ直して狭い CHECK を付け直し、violated by some row で deploy が落ちる。上の前例と同じ壊れ方。
  - 条件なしの DROP → ADD は、流れ直すたびに llm_usage_events（解析で毎分書かれる表）に ACCESS EXCLUSIVE のロックを取り、表全体を読み直す。psql は文ごとに commit するので、DROP の後 ADD がロックの待ちで止まり40回流し直しても取れないと、CHECK が外れたまま残る。
- 直し方: §4-1 の CHECK の行を次のように直す。「CHECK の作り直しは前例 `20261020_110000_line_conditions_value_group_add_supply.sql:15-36` の形にする。DO の塊の中で `pg_get_constraintdef` を見て、本便で足す値（purpose の `secretary_intent`、sdk の `codex-cli`）がすでに入っていれば何もしない。入っていない時だけ DROP → ADD する。outcome・error_code の CHECK と、新しい3表の provider・job_key の CHECK は、それぞれの列・表を作る時に一緒に作る（`ADD COLUMN IF NOT EXISTS ... CHECK` か `CREATE TABLE IF NOT EXISTS` の中）ので、作り直しをしない」。§7 1a の流れ直しの試験に「後の migration を真似て purpose の CHECK に別の値を足し、その値の行を入れた後でも、本便の migration を流し直して通る」を1本足す。

### Q2. 重さ: 中 — §4-2-1・§4-2-3（v102 の道では例外が包み直され、鍵切れの印が消える。API を呼ぶ前の失敗にも行が出る）
- 根拠（origin/main）:
  - v102 の API の呼び出しは `gemini_raw_copy_v8.py:220-229` で、例外を `RuntimeError(f"Gemini v8 API 呼び出し失敗: {_gem._safe_error_message(exc)}") from exc` に包み直す。
  - `_safe_error_message`（`gemini_extraction_svc.py:197-208`）は、文の中に 4xx・5xx の数があると「理由 (HTTP NNN)」だけを返し、残りの文（`API_KEY_INVALID`・`PERMISSION_DENIED` などの状態名）を捨てる。
  - v102 の送り直しの輪の except（`line_analysis_v102_svc.py:502-519`）が受けるのは、この包み直された RuntimeError。
  - `_get_genai_client()`（`gemini_raw_copy_v8.py:218`、本体 `gemini_extraction_svc.py:248-266`）は鍵が無い時に RuntimeError を上げ、これは try（`:220`）の外で起きる。それでも、v102 の輪の except（`line_analysis_v102_svc.py:502`）は `call_gemini_raw_copy_v8` 全体を囲んでいるので、この例外も受ける。
  - 翻訳の道は `LLMParseError(f"... {exc}") from exc`（`message_translator.py:382-384`）で元の文を残す。旧エンジンの道は元の例外のまま受ける（`gemini_extraction_svc.py:436-440`）。違うのは v102 の道だけ。
- 足りない所:
  - ① design §4-2-1 の `gemini_ledger_error_code(exc)` の①は「HTTP の 401・403、または例外の中の状態名」で auth_failed にする。しかし v102 の道で渡る例外は包み直された物で、状態名が消えている。状態名が 401・403 以外の番号と一緒に来ると（Google の鍵の誤りが返す HTTP の番号は【未確認】）http_error になり、画面のログイン×（§6 の①）が出ない。4回目の③で直したはずの穴が、解析の主な道（v102）で残る。
  - ② design §4-2-3 の v102 の行は「`_call_gemini` の送り直しの輪の except で、失敗した呼び出しごとに1回」。この except は鍵が無い時の RuntimeError も受けるので、API を呼んでいないのに failed（other）の行が出る。翻訳の道の「印の無い例外（`_ensure_api_key` 等）は API を呼んでいないので行を書かない」（§4-2-3 の③）と食い違う。
- 直し方: §4-2-1 に「`gemini_ledger_error_code` は `exc` とその `__cause__` の鎖をたどって、元の例外で①を判定する（v102 は `gemini_raw_copy_v8.py:229` で `from exc` を付けて包み直しているため）」と書く。試験を1本足す: 「`API_KEY_INVALID` を含む例外を `call_gemini_raw_copy_v8` の中で起こすと、v102 の failed の行の error_code が auth_failed になる」。§4-2-3 の v102 の行に「`__cause__` の無い RuntimeError（`_get_genai_client` の鍵なし・SDK なし）は API を呼んでいないので行を書かない」と書く。またはこの2つを見分ける印を `call_gemini_raw_copy_v8` の中で付ける形にする（翻訳の道の印と同じ考え方）。

### Q3. 重さ: 軽・カードで扱える — §7（§5-3 の backend の直しが、どの段に入るか書かれていない）
- 根拠: design §7 の段1b は「秘書の model を担当表から渡す・秘書の台帳の行（claude-code）」だけ、段3は「secretary-codex 容器＋codex の選択肢3行の migration」だけを挙げる。§5-3 の provider→容器の URL の対応表・`SECRETARY_CODEX_URL`・`tool_used` の読み替え（今は `assistant.py:103-115` で unreadable になる）・`AgentEnvelope` に `usage`・`error_events` を足す直し（`backend/app/schemas/assistant.py:72-76` の `extra="forbid"`）は、どの段にも載っていない。
- 直し方: §7 の段3の中身に「§5-3 の backend の直し（宛先の対応表・`SECRETARY_CODEX_URL`・tool_used・`AgentEnvelope` の2欄）」を足す。段3の合格の見方に「codex の容器が返した `usage` と `error_events` を含む返事で ValidationError が0件」を足す。

### Q4. 重さ: 軽・カードで扱える — §4-3（1回の呼び出しの中で担当を何回読むかが決まっていない）
- 根拠: v102 の1回の呼び出しで、モデルの名前は `line_analysis_v102_svc.py:480`（試行の記録）・`gemini_raw_copy_v8.py:219-222`（実際の呼び出し）・`line_analysis_v102_svc.py:453`（台帳）の3か所で使われる。`call_gemini_raw_copy_v8` は DB の session を受け取らない（`gemini_raw_copy_v8.py:182-193`）。翻訳も `message_translator.py:485`・`:505`・`:644` で複数回読む。
- 足りない所: 各所が `get_ai_assignment` を別々に呼ぶと、その間に画面で切り替えた時、試行の記録・実際の呼び出し・台帳の model がずれる。K9 の「次の1回の ledger の model が新しい値」の確かめも、どの読み取りの値かがぶれる。
- 直し方: §4-3 に「1回の仕事（1つの extraction_job・1回の翻訳の頼み・1回の秘書の頼み）の初めに1回だけ読み、その値を引数で下へ渡す。`call_gemini_raw_copy_v8` には `model` の必須引数を足す（DB を読ませない）」と書く。

### Q5. 重さ: 軽・カードで扱える — §4-2-1・§4-1（同じ一覧が5か所に分かれ、DB と照らす試験が無い）
- 根拠: purpose・sdk の一覧は CHECK（`20260930_150000_create_llm_usage_events.sql:46-52`）・`USAGE_PURPOSES`・`USAGE_SDKS`（`llm_budget.py:159-171`）・`KNOWN_PURPOSES`（`LlmUsageSection.tsx:151-158`）・i18n に分かれている。今、`USAGE_PURPOSES`・`USAGE_SDKS` を CHECK と照らす試験は無い（`git grep -n "USAGE_PURPOSES\|USAGE_SDKS" origin/main -- backend/tests` が0件）。本便でさらに error_code の9つ・job_key の5つ・provider の3つが CHECK と Python と i18n に分かれる。
- 直し方: §7 1b に試験を1本足す。「本物の migration を流した DB で `pg_get_constraintdef` から purpose・sdk・error_code・provider・job_key の値を取り出し、Python 側の一覧（`USAGE_PURPOSES`・`USAGE_SDKS`・error_code の一覧・provider→sdk の対応表）と同じ集合であること」。i18n のキーは段2で「error_code の9つ・job_key の5つすべてに日本語と英語のキーがある」を試験にする。正本は CHECK、と §4-3 に1行書く。

### Q6. 重さ: 軽・カードで扱える — §7・§8（○×で決められない合格の見方・本番で行う確かめの手の主）
- 根拠: §7 1a の合格に「直近1時間の line_extraction の行数が前日の同じ時刻と同程度」とあり、数の幅が無い。§8 の K6 は「ボリュームの auth.json を退けて1回呼ぶ」だが、secretary-codex は本番の VPS にしか無い（§5-4）。VPS で変更を伴う作業は作業ごとに PO の GO が要る（`AGENTS.md`「VPS 直作業禁止」）。
- 直し方: 1a の合格を「直近1時間の line_extraction の行数が、前日の同じ時刻の1時間の半分以上（前日が0なら確かめない）」のように数で書く。K6 は「PO が manual-only 鍵で `!` を使い、auth.json を別名に移す→画面で×→戻す→○。手順の行は §5-4 の後に書き、GO の原文を記録する」と書く。

## そのほかに確かめたこと（指摘なし）
- K5 の検査の型で今当たる所は、6回目と同じ4か所だけ（`gemini_extraction_svc.py:283`・`llm_budget.py:57-89`・`message_translator.py:10-12,49-50`・`server.mjs:70`。`git grep -nE` を origin/main の `backend/app`・`secretary-agent` に当てた結果）。
- 新しい表の権限の前例（`20261101_130000:126-132`・`20261102_090000_add_user_push_subscriptions.sql:33-39`）と、`20260605_030000` の既定の権限（`:21-24`）は design の書き方と合う。
- deploy.yml の順番: アプリの反映（`:235`）→秘書の容器の段（`:670`）→役の用意（`:703`）→migration（`:768`）。段3で容器と codex の選択肢の migration を同じ便で出しても、選択肢の行が入る前に容器が起きるだけで、画面で codex を選べるのは migration の後になる。design §4-1 の意図と合う。
- 秘書の容器の compose は本体と別の project で起こす（`docker-compose.secretary-agent.yml:7-8`）。design §5-4 の `-p astro-webapp-secretary-codex` も別の project で、deploy の `--remove-orphans` に消されない。deploy の後片付けは `docker image prune -f`・`docker builder prune`（`deploy.yml:1007`・`:1013`）だけで、名前付きボリュームは消さない。
- 翻訳の celery の道（`backend/app/tasks/translation.py:44-56`）は `asyncio.run` の中で `AsyncSessionLocal` を使い、終わりに `engine.dispose()` をする。§4-2-3 の `record_usage_isolated` が同じ輪の中で `AsyncSessionLocal()` を開いても、輪の違いの問題は起きない。
- 画面の部品: `BadgeVariant` に success・danger がある（`Badge.tsx:16`）。`DashboardTab`（`AnalysisDashboardPanel.tsx:55`）と tabItems（`:470-476`）は design のとおり。即時反映の表の前例 `topics.py:368` も合う。

VERDICT: REVISE
