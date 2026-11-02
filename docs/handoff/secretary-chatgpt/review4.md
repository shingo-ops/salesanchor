# 設計審査 4回目（secretary-chatgpt design v4）

- 審査役: Architect（クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 対象: `release/secretary-chatgpt-ai-roster` head 837a6493c の `docs/handoff/secretary-chatgpt/design.md`（v4）・`recon.md`・`kgi.md`
- 根拠: `git show origin/main:<path>`（origin/main 90ee0c1。design の照合基準 b88ff157b はこれの祖先）の行番号
- 製品のファイルは変えていない。この枝はこのファイルだけ

## 確認できた所（直っている）
- 3回目①: 旧エンジンの fail は「API の例外の印がある かつ 応答なし」の時だけ書く形。v102 は `gemini_extraction_svc.py:436-440` を通らないため印が付かず二重にならない（`line_analysis_v102_svc.py:474-522`、`tcg_extraction.py:432,497-499`）。
- 3回目②: 秘書の行は別取引ですぐ commit（`assistant.py:139` の後は commit されない、`database.py:46-61`）。
- 3回目③: `AgentEnvelope` の `extra="forbid"`（`backend/app/schemas/assistant.py:72-76`）に usage・error_events を足す形。
- 3回目④: 経路ごとの ok/failed の表がある。§4-2-2 の集計（`tcg_analysis_dashboard.py:475,495,509,678,705`）・`prompt_ab.py:130-134`・`reextract_v6_with_v102.py:316-321` の行番号は合っている。
- §5-4: `deploy.yml:666-699` の段の中身（if・continue-on-error・command_timeout・df・build・probe・compose）は実物どおり。
- 画面の引用（`AnalysisDashboardPanel.tsx:55,470-475,590`・`Modal.tsx:26-33,73-79`・`Select.tsx:20-27`・`ConfirmModal.tsx:37`・`Badge.tsx:16`・`topics.py:5,368`）は合っている。ADR-1057 の番号は main で空いている。

## 指摘

### 1. 重さ: 中 — §4-2-3（解析 旧エンジンの行）
- origin/main: `backend/app/services/tcg_extraction_record_svc.py:226-265`、`backend/app/tasks/tcg_extraction.py:432`
- 足りない所: 失敗の行を「fail の今の取引の中」で書き、書く関数は「自分の失敗はログに出して飲み込む」（§4-2-3 書く関数の段）とある。PostgreSQL では INSERT が失敗すると取引全体が使えなくなるので、例外を飲み込んでも後ろの `UPDATE extraction_jobs SET status='error'`（`:262-264`）と `s.commit()`（`:265`）が失敗し、`:268-270` の except で全部巻き戻る。台帳の1行の失敗で、仕事が error にならず残る。
- 直し方: 失敗の行の INSERT を `session.begin_nested()`（SAVEPOINT）で囲み、失敗したら SAVEPOINT だけ戻す、と書く。または `:265` の commit の後に別の commit で書く。どちらかを §4-2-3 の表の「取引」の列に明記し、「台帳の INSERT を失敗させても extraction_jobs が error になる」試験を1本足す。

### 2. 重さ: 中 — §4-2-1・§4-2-3（翻訳の行）
- origin/main: `backend/app/services/message_translator.py:367-369,382-391,492,499,513,520,646,654`
- 足りない所:
  - 空の応答は「ok＋使用量」とするが、今のコードは `:387-388` で例外を上げ、使用量は `:390-391` で初めて読む。「印を付けて上げるだけ」では使用量が手に入らない。
  - `_ensure_api_key()`・`_get_genai_module()`（`:367-369`）は try の外。鍵が無い時の例外に印が無く、行を書くのか書かないのかが決まっていない。
  - except で囲む範囲が書かれていない。`_parse_translation_response`（`:499`・`:520`・`:654`）の例外まで囲むと、ok の行（呼び出し元の取引・巻き戻る）に加え、印なしの例外の扱いが曖昧になる。
- 直し方: `_call_gemini` の中で使用量を `:387` より前に読み、例外に `outcome`・`error_code`・`usage_counts` を持たせる、と書く。except は `_call_gemini(...)` の1行だけを囲み、印の無い例外（鍵なし等）は行を書かない（K3 は ② の鍵の有無で見る）と明記する。

### 3. 重さ: 中 — §4-2-1・§6（Gemini の行のログイン ○×）
- origin/main: `backend/app/services/gemini_extraction_svc.py:213-222`
- 足りない所: ○× の①は「最後の呼び出しが auth_failed」だが、Gemini の失敗は `_classify_error` の写しなので 401・403（鍵の無効・取り消し）は `gemini_http_error`→`http_error` になり、auth_failed は Gemini では1行も書かれない。鍵が無効でも環境に値があれば4行とも ○ のまま（K3「ログインできているか」が Gemini の4行で測れない）。また「その AI の最後の呼び出し」が job_key ごとか provider ごとか、担当を変えた後に前の provider の行を見ないか、が決まっていない。
- 直し方: 台帳に入れる時の読み替えに「HTTP 401/403、または API_KEY_INVALID・PERMISSION_DENIED を含む → auth_failed」を `_classify_error` より先に足す（既存の分類の値は変えない）。①の読み方を「purpose = job_key かつ sdk が今の担当の provider のもの、の最新1行」と §6-1 に書く。

### 4. 重さ: 中 — §7・§4-3・§5-3（段の中身の割り当て）
- origin/main: `secretary-agent/server.mjs:70,134-142`、`backend/app/routers/assistant.py:77-85`、`.github/workflows/deploy.yml:670-699`
- 足りない所: 段1b の合格に「K5 の試験が緑」があり、検査の範囲に `secretary-agent/` を含む（§4-3）。`server.mjs:70` の `"sonnet"` を消すには、容器が model を受け取り（`:136` は text・now だけ読む）、`assistant.py` が担当を読んで送る（§5-3）必要があるが、§7 の 1b にはそれも、秘書の ok/failed の台帳の行（§5-3 最後）も入っていない。§5-3 は段3の中身として読める。1b は自分の合格の条件を満たせない。
- 直し方: どちらかに決めて §7 に書く。(a) 1b に「assistant.py が `get_ai_assignment("secretary_intent")` を読み model を送る・秘書の台帳の行（claude-code）を書く・server.mjs が model を受け取り無ければ 400」を入れる。旧い容器は余分な欄を無視する（`:136`）ので backend が先に切り替わっても壊れない、と順番を書く。(b) K5 の範囲から `secretary-agent/` を段3まで外す。

### 5. 重さ: 中 — §5-1 と §5-4（容器の作り方の食い違い）
- origin/main: `secretary-agent/Dockerfile:6`、`.github/workflows/deploy.yml:682`、`docker-compose.secretary-agent.yml:14`
- 足りない所: §5-1 は「指示文と答えの形のファイルを写しを作らず両方の容器に入れる。build context はカードで決める」、§5-4 は `docker build -t astro-webapp-secretary-codex ./secretary-codex` と context を `./secretary-codex` に決めている。この context では `../secretary-agent/prompt.txt` を COPY できない（今の Dockerfile も context 内の4ファイルだけを COPY、`:6`）。カードで決める余地が無く、§5-4 のまま作ると写しを作るしかない。
- 直し方: 今決める。例: context をリポジトリの根にして `docker build -f secretary-codex/Dockerfile .`、compose も `build: {context: ., dockerfile: secretary-codex/Dockerfile}` にし、§5-4 の命令を合わせる。

### 6. 重さ: 中 — §7 段1a（AI 用の読み取りビューの分類表）
- origin/main: `migrations/20261024_100300_create_ai_cloud_views.sql:1-7,142-145`、`backend/tests/ops/test_ai_cloud_views.py:481,486-520,523-570`、`scripts/run_all_migrations.sh:1059`
- 足りない所: 新しい文字の列（llm_usage_events の outcome・error_code、ai_job_choices の job_key・provider・model、ai_job_assignments の job_key、ai_job_assignment_history の job_key）は分類表 `ai_cloud_meta.column_class` に行が無いと T10 の試験（`_classification_gaps`、`:510-515` の「分類なし」）が赤になる。分類表の正本は `20261024_100300` の SQL で、行数の検査 `:481`（1057）も変わる。§7 1a にこの作業が無い。新しい migration を `run_all_migrations.sh` の一覧（`:1059` の形）に載せることも書かれていない。
- 直し方: 1a に「分類表の SQL に7列の行を足す（outcome・error_code・provider・job_key は CHECK で値が限られるので allow と理由、model は今の `:142` と同じく mask）・`:481` の数を直す・run_all_migrations.sh に載せる」を足す。

### 7. 重さ: 中 — §10（段1b の戻し方）
- origin/main: `backend/app/routers/tcg_analysis_dashboard.py:475,485,495,504,509,678,705`
- 足りない所: 「コードを前の版に戻せば元どおり」とあるが、1b の後は失敗の行が表に残る。前の版のコードには `outcome = 'ok'` の条件が無いので、使用量画面と解析ダッシュボードの数（LEFT JOIN の `COUNT(*)`、v102 の送り直しは同じ extraction_attempt_id の行が増える）が戻した後にずれる。
- 直し方: 集計の `outcome = 'ok'` の条件だけを、失敗の行を書くコードより前の別の PR（1a の後・1b の前）で出す、と §7 に書く。そうすれば 1b を戻しても条件は残る。または §10 に影響と対処を書く。

### 8. 重さ: 軽 — §4-2-3・§5-3（秘書の ok の行の位置）
- origin/main: `backend/app/routers/assistant.py:163-175,205`
- 足りない所: ok の行は `:163` の後・`:169` の前に書くが、`_log(..., "ok")` は `:205`。`reset_tenant_context`（`:169`）や `resolve_names`（`:175`）が例外を出すと、台帳は ok・ログは行なしになる。「ログと台帳の数が一致する」（§4-2-3）は成り立たない。tenant_id・source_ref に何を入れるかも書かれていない。
- 直し方: 台帳の ok は「AI の呼び出しが成功した」の意味だと書き、一致の文を消す（または `:205` で書く）。tenant_id は `tenant_id`、source_ref は NULL と書く。

### 9. 重さ: 軽 — §6・§6-1（GET の中身）
- origin/main: `secretary-agent/server.mjs:123-125`
- 足りない所: GET `/ai-jobs` が毎回容器の `/health` を呼ぶが、待つ時間の上限が無い（届かない時に画面が止まる）。`count_24h` が ok だけか失敗も含むかが決まっていない。
- 直し方: `/health` は2秒で打ち切り、届かなければ `login_reason="not_ready"`。`count_24h` は ok の数と書く（失敗の数も出すなら別の欄）。

### 10. 重さ: 軽 — §4-1（履歴の表）
- origin/main: `migrations/20260605_030000_create_salesanchor_app_role.sql:21-23`、`backend/app/models.py:26`
- 足りない所: 「書き換え・消しはしない」が決まりだけで、アプリのロールには既定の権限で UPDATE・DELETE が付く。changed_by の外部キーが利用者の削除（テナントの削除で消える）の時にどうなるかも未定。
- 直し方: 履歴の表から salesanchor_app の UPDATE・DELETE を外す（REVOKE）。changed_by は ON DELETE SET NULL とし、画面は「ID 不明」を出す。

### 11. 重さ: 軽 — §8 K8
- origin/main: `docker-compose.secretary-agent.yml:26`（mem_limit 512m。§5-1 で同じ値）
- 足りない所: K8 の①「減った量が 512MB 以下」は容器の上限が 512m なので常に通り、測りにならない。kgi の K8 は基準値と下限を設計の最初に測って決めるとあるが、recon §5-3 で未確認のまま。
- 直し方: 読み取りの道で prod1 の MemAvailable を今測って基準値と下限（数値）を design に書く。①は K1 の10本を流す間の docker stats の最大値に替える。

### 12. 重さ: 軽 — §5-1（容器の細部）
- origin/main: `secretary-agent/server.mjs:74-83,133`
- 足りない所: codex に渡す環境変数（今は PATH 等の決まった物だけ、`:74-81`）、頼みの文の渡し方（今は標準入力、`:117`）、auth.json が無い時に `/intent` が codex を呼ばずに 503 not_ready を返すか（今の `:133` に当たる物）、が書かれていない。標準エラーは今は捨てている（`:83`）が、codex では auth_failed の判定に読む（記録はしない）ことも明記が要る。
- 直し方: §5-1 に4点を1行ずつ書く（環境は PATH・CODEX_HOME・HOME だけ）。

### 13. 重さ: 軽 — §2・§4-1（使いみち inventory_parse_fallback）
- origin/main: `migrations/20260930_150000_create_llm_usage_events.sql:48`、`backend/app/services/llm_budget.py:163`、`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:154`
- 足りない所: 台帳の purpose に inventory_parse_fallback があるが、`backend/app` に書き手が無い。「5つの仕事」に入れない理由が書かれていない（K3 の5行の数え方で迷う）。
- 直し方: §2 に「inventory_parse_fallback は今は書き手が無いので仕事に入れない」と1行足す。

VERDICT: REVISE
