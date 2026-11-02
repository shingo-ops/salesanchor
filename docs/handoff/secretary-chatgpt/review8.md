# 設計審査 8回目（secretary-chatgpt design v8）

- 審査役: Architect（クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 対象: `release/secretary-chatgpt-ai-roster` head 155bbc078 の `docs/handoff/secretary-chatgpt/design.md`（v8）・`recon.md`・`kgi.md`、前回の指摘 `origin/review/secretary-chatgpt-r7` の `review7.md`
- 根拠: `git show origin/main:<path>`（origin/main d828bb269。7回目と同じ commit なので、7回目に照合した行番号はそのまま使える）
- 製品のファイルは変えていない。この枝で足したのはこのファイルだけ
- 試せなかったこと: クラウドの見張りが psql でのファイル実行を止めるため、SQL の動きは手で試していない（試したことにしていない）

## 7回目の6件の確かめ（1件ずつ）

| # | 結果 | 根拠（origin/main） |
|---|---|---|
| Q1 CHECK の作り直し | 直った（細部に軽い点。N3） | design §4-1 は「新しく作る CHECK は表・列を作る文の中で作る」「今ある CHECK を広げる時は `pg_get_constraintdef` を見てから DROP → ADD」の2通りに分けた。前例 `migrations/20261020_110000_line_conditions_value_group_add_supply.sql:15-36` の形（conname で引いて `LIKE '%supply%'` なら何もしない、`:42-45` で二重に確かめてから DROP）と合う。今ある CHECK の名前は `llm_usage_events_purpose_check`・`llm_usage_events_sdk_check`（`20260930_150000_create_llm_usage_events.sql:46-52`）で、`CREATE TABLE IF NOT EXISTS`（`:26`）の中にあるので、元の migration が流れ直しても狭め直さない。後から llm_usage_events を変える migration はほかに無い（`git grep -n llm_usage_events origin/main -- migrations` で、元の表・バックフィル `20260930_160000`・分類表 `20261024_100300` だけ）。バックフィル（`20260930_160000:12-29`）は流れ直しても NOT EXISTS で止まり、入る行も outcome の既定 'ok'・error_code NULL で新しい CHECK を通る。§7 1a に「後の migration が広げた後の流し直し」の試験も入った |
| Q2 v102 の鍵切れの印・鍵なしの行 | 直った（試験の細部に軽い点。N4） | `_get_genai_client()` は try の外（`gemini_raw_copy_v8.py:218`）、API の呼び出しの except は `:228-229` で `RuntimeError(...) from exc`。design §4-2-1 は `__cause__` の鎖を最大5段たどる形、§4-2-3 は `:228` の except で包んだ例外にだけ印 `ledger_api_called` を付け、v102 の輪の except（`line_analysis_v102_svc.py:502-519`）は印がある時だけ書く形にした。`build_prompt_v8`（`gemini_raw_copy_v8.py:202`）も try の外なので印は付かない。送り直しの判定 `_is_transient_http`（`line_analysis_v102_svc.py:468-471`）は包んだ後の文の `(HTTP NNN)` を読むので、印を足しても変わらない |
| Q3 §5-3 の段 | 直った | §7 段3 の中身に「provider→容器の URL の対応表・`SECRETARY_CODEX_URL`・tool_used の読み替え・`AgentEnvelope` の2欄」、合格に「`usage`・`error_events` を含む返事で ValidationError 0件」が入った。今の受け口は `backend/app/schemas/assistant.py:72-76`（extra="forbid"）、読み替えは `assistant.py:103-115` で design の記載と合う |
| Q4 担当を読む回数 | 直った | §4-3 に「1回の仕事の初めに1回だけ読み、引数で下へ渡す」「`call_gemini_raw_copy_v8` に `model` の必須引数」が入った。必須引数を足して壊れる呼び手が無いかを見た: 本体の呼び手は `line_analysis_v102_svc.py:495` と `backend/app/tools/prompt_ab.py:555` の2つで、どちらも design §4-3 の直す一覧にある。試験の差し替えは `*_a, **_k` を受ける関数か MagicMock（`test_line_analysis_v102_pg.py:66`・`test_reextract_v6_with_v102_pg.py:215,236,347,361,408`・`test_api_error_auto_retry.py:40`・`test_prompt_ab.py:49`）。`scripts/accuracy/llm_compare/capture_prompt_ab.py:41-42` の包みは `**kwargs` をそのまま渡すので、model が増えても壊れない |
| Q5 一覧と CHECK の照合 | 直った | §4-3 に「正本は DB の CHECK」、§7 1b に `pg_get_constraintdef` から5つの一覧を取り出して Python 側と比べる試験、段2 に i18n のキーの試験が入った |
| Q6 数で決める合格・K6 の手の主 | 直った（ただし数の決め方に新しい軽い点。N2） | §7 1a の合格に「前日の同じ時刻の1時間の半分以上。前日0行なら確かめない」、§8 K6 に「PO が manual-only 鍵で `!`、GO の原文を記録」が入った |

## 新しい指摘

### N1. 重さ: 中 — §7 段3・§8 K1/K2/K6/K8・§9・§13-5（「試験の担当切替」がどこで行われるか決まっておらず、§9 の「決まるまで切り替えない」と食い違う）
- 根拠:
  - design §7 段3 は「PO がログイン → 試験の担当切替で K1・K2・K6・K8 を測る → 合格なら担当を ChatGPT に」。§8 K6 は「試験の担当で秘書を ChatGPT にする。PO が manual-only 鍵で…ボリュームの auth.json を別名に移す」と本番の VPS の操作を書いている。
  - secretary-codex は本番の VPS にだけ起こす（§5-4 の deploy.yml の段だけ。ほかの環境で起こす手順は design に無い）。§5-2 の一時 VM はログインなしの範囲だけ。したがって K1・K2・K8 を測る「試験の担当切替」は、本番の `ai_job_assignments` の secretary_intent を codex にすることになる。
  - 一方 §9 の最後と §13-5 は「月額契約（ChatGPT の個人の契約）を会社のサーバーでお客さん向けの機能に使ってよいかは PO が決める。決まるまで段3で担当を ChatGPT に切り替えない」。
  - 秘書の API はスーパー管理者だけが呼べる（`backend/app/routers/assistant.py:124` の `Depends(require_super_admin)`）。本番で切り替えても使うのはスーパー管理者だけ、という事実は design に書かれていない。
  - kgi の K6・K9 の測り方は「試験の環境で」と書くが、design はその「試験の環境」がどこかを決めていない。
- 足りない所: 実装カードは「本番で codex に切り替えて K1 を測ってよいか」を決められない。測ること自体が §9 の禁止に当たるように読め、逆に「測るのは切り替えではない」と読むと、PO の判断の前に会社のサーバーで個人の契約を使うことになる。PO のログイン（段3の最初）も同じ問いの中にある。
- 直し方: 次の2つを design に書く。①§13-5 の PO の判断は「段3の PO のログインより前」に取る（判断が「試験だけ可」「不可」の場合の進め方も1行ずつ）。②「試験の担当切替」は本番の `ai_job_assignments` を画面の PUT で codex にすることで、秘書の API はスーパー管理者だけが使える（`assistant.py:124`）ため影響はスーパー管理者だけ。測り終えたら同じ画面で claude に戻し、履歴の2行で確かめる。K9・K5 の「試験の環境」も、本番の画面で行うのか別の環境で行うのかを書く。

### N2. 重さ: 軽・カードで扱える — §7 1a（「前日の同じ時刻の1時間の半分以上」は件数が少なく、正しい時も×になりうる）
- 根拠: recon §2 の本番の集計で line_extraction は直近7日で 675 行＝1時間あたり平均4行ほど。夜の時間は0行の時もありうる（時間ごとの分布は【未確認】）。1時間4行前後だと、普段の揺れで前日の半分を切ることがある。
- 直し方: 窓を広げる（例「反映後24時間の行数が、その前の24時間の行数の半分以上」）か、「反映後に line_extraction の行が1行以上出て、その error が migration 由来でない」に変える。どちらかをカードで決める。

### N3. 重さ: 軽・カードで扱える — §4-1・§4-2-1（CHECK の細部2つ）
- sdk の CHECK は値を2つ足す（codex-cli・claude-code）。前例は1つの値だけを `LIKE` で見ている（`20261020_110000:35`・`:42`）。2つとも入っている時だけ何もしない形にする（片方だけ見ると、もう片方が入らないまま止まる）。
- outcome・error_code の「ok なら NULL、failed なら NOT NULL」は2つの列にまたがる。これを `ADD COLUMN IF NOT EXISTS error_code ... CONSTRAINT ... CHECK (...)` の列の制約として書いた時に PostgreSQL 16 が受け付けるかは【未確認】（クラウドでは SQL を手で流せなかった）。§7 1a の2回流しの試験で確かめる、と1行書く。受け付けない時は、表の制約として名前を付け、`pg_constraint` に無い時だけ足す DO の塊にする。

### N4. 重さ: 軽・カードで扱える — §4-2-3（今の試験の差し替えは印の無い例外を上げる）
- 根拠: 今の試験の差し替えは印の無い例外を上げる（`test_reextract_v6_with_v102_pg.py:215-216` の `RuntimeError("Gemini v8 API 呼び出し失敗: 架空")`・`:347-348`、`test_api_error_auto_retry.py:40` の MagicMock の side_effect）。新しい形では印が無いと failed の行を書かないので、これらの試験は失敗の行が0行のまま緑になる。
- 直し方: 1b の試験では、失敗の行を数える試験の差し替えに印（`ledger_api_called = True`）を付けた例外を使う。印の無い例外で行が0行になる試験も1本足す（鍵なしの道を守る）。
- あわせて: `SoftTimeLimitExceeded` は API の呼び出しの途中でも印の前に上げ直される（`gemini_raw_copy_v8.py:226-227`・`line_analysis_v102_svc.py:500-501`）ので行は出ない。これは「打ち切りは台帳に出さない」と意図として1行書く（書かないとカードで timeout の行を出すか迷う）。

### N5. 重さ: 軽・カードで扱える — §6-1 の PUT（同じ値への切り替え・同時の切り替え）
- 今の担当と同じ choice_id を送った時に履歴を書くか（K9 の「履歴が1行増える」の数え方に関わる）と、2人が同時に PUT した時の old_choice_id の取り方（`SELECT ... FOR UPDATE` で今の行を押さえてから読む）が書かれていない。カードで「同じ値なら書き換えず履歴も書かない・200 で今の行を返す」「今の行を FOR UPDATE で読んでから更新と履歴を同じ取引で書く」と決める。

### N6. 重さ: 軽・カードで扱える — §5-1（auth.json の「中身は読まない」と last_refresh を読むことの言い回し）
- `/health` の last_refresh は auth.json を読んで取り出すので、「中身は読まない」は文字どおりにはできない。「auth.json は JSON として読み、`last_refresh` の1つだけを取り出す。ほかの欄は変数に残さず、ログ・応答・記録に出さない」と書き直す。

## 指摘なしで確かめたこと
- origin/main は 7回目と同じ d828bb269（`git rev-parse --short origin/main`）。
- 移行の流し方: psql は `-v ON_ERROR_STOP=1`（`scripts/run_all_migrations.sh:25`）で、ロックの待ちは1秒・流し直しは合計40回（`:57-60`）。ロックで止まった時は同じファイルを頭から流し直すので、§4-1 の「全部を流れ直しても壊れない形」と合う。
- 分類表の行の数: 足す7列（outcome・error_code・ai_job_choices の job_key・provider・model・ai_job_assignments の job_key・ai_job_assignment_history の job_key）は design の3表の文字の列の数と合う。今の行数 1057 は `backend/tests/ops/test_ai_cloud_views.py:481` のまま。今の分類表の llm_usage_events の行は `20261024_100300_create_ai_cloud_views.sql:142-145`・`:582`。
- 秘書の流れ: try が受けるのは HTTPException だけ（`assistant.py:164`）だが、`_call_agent` は httpx の失敗をすべて HTTPException に直す（`:86-90`）ので、§4-2-3 の「except で failed を1行」で失敗の頼みが漏れない。Claude の容器の `/health` は `{ready}` だけを返す（`secretary-agent/server.mjs:123-125`）ので、§6 の③はそのまま使える。
- 翻訳の道: `_call_gemini`（`message_translator.py:358-394`）の鍵の読み取りは try の外（`:367-369`）、API の except は `:382-384` で `from exc`、空の応答の判定（`:387-388`）は使用量の読み取り（`:390-391`）より前。design §4-2-3 の記載どおり。取り直しの条件は `:505`、取り直しの台帳の行は `:515-519`。
- 翻訳の celery の道（`backend/app/tasks/translation.py:43-56`・`:78-89`）は 7回目の確かめのとおり。

VERDICT: REVISE
