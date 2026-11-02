# 設計審査 9回目（secretary-chatgpt design v9）

- 審査役: Architect（クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 対象: `release/secretary-chatgpt-ai-roster` head 6ce9947bd の `docs/handoff/secretary-chatgpt/design.md`（v9）・`recon.md`・`kgi.md`、前回の指摘 `origin/review/secretary-chatgpt-r8` の `review8.md`
- 根拠: `git show origin/main:<path>`（origin/main c758ea8。8回目の d828bb269 からの差分は `scripts/agent-hooks/mac-test-guard/` の4ファイルだけで、design が引く製品のファイルには差分なし。`git diff --name-only d828bb269 origin/main` で確かめた。よって8回目までに照合した行番号はそのまま使える）
- 製品のファイルは変えていない。この枝で足したのはこのファイルだけ
- 試せなかったこと: SQL の動き（2列にまたがる列の CHECK を PostgreSQL 16 が受け付けるか等）は手で流していない（試したことにしていない）

## 8回目の6件の確かめ（1件ずつ）

| # | 結果 | 根拠（origin/main） |
|---|---|---|
| N1 「試験の担当切替」の場所と PO の判断の順番 | 直った（言い回しに軽い点。R1・R2） | design §7「どこで測るか」（`design.md:190-193`）に ①K5・K9 の試験の環境は CI（本物の PostgreSQL に migration を流した DB）、本番の解析と翻訳の担当は試すために切り替えない ②段3の K1・K2・K6・K8 は本番で測り、「試験の担当切替」は本番の画面の PUT で secretary_intent を codex にすること、測り終えたら claude に戻し履歴の2行で確かめる ③§13-5 の PO の判断は段3の PO のログインより前、答え3通り（使ってよい／スーパー管理者の試験だけ可／不可）ごとの進め方、が入った。§9（`design.md:217`）・§13-5（`:241`）も同じ向きに直った。秘書の API がスーパー管理者だけという根拠は実物と合う: `backend/app/routers/assistant.py:119-128` の `@router.post("/assistant/messages", dependencies=[..., Depends(require_super_admin), ...])`（`:124`）、`require_super_admin` は `is_super_admin` が真でなければ 403（`backend/app/auth/dependencies.py:539-566`）。担当表は tenant_id なし（§4-1）なので、切り替えはどの会社のスーパー管理者の頼みにも効くが、呼べるのはスーパー管理者だけ、で筋は通る |
| N2 1時間の比べ方 | 直った | §7 1a の合格（`design.md:181`）が「反映後24時間の line_extraction の行数が、その前の24時間の半分以上。前の24時間が0行なら確かめない」に変わり、1時間で比べない理由（直近7日 675 行、recon §2）も書かれた |
| N3 CHECK の細部2つ | 直った | §4-1（`design.md:39`）: sdk は `codex-cli` と `claude-code` の両方が定義に入っている時だけ何もしない。前例 `migrations/20261020_110000_line_conditions_value_group_add_supply.sql:15-36` は1つの値を `LIKE` で見る形で、design はそれを2つの値の AND に広げると明記した。§4-1（`:40`）: 2列にまたがる CHECK は【未確認】のまま §7 1a の2回流しの試験で確かめ、受け付けない時は名前付きの表の制約を `pg_constraint` に無い時だけ足す DO の塊にする、と代わりの形も決まった |
| N4 試験の差し替えの印・打ち切り | 直った | §7 1b（`design.md:183`）に「失敗の行を数える試験の差し替えは印（`ledger_api_called = True`）を付けた例外を使う」「印の無い例外で行が0行になる試験を1本」が入った。引いた差し替えは実物と合う: `backend/tests/test_reextract_v6_with_v102_pg.py:215-216`（`RuntimeError("Gemini v8 API 呼び出し失敗: 架空")`）・`:347-348`（`RuntimeError("架空")`）、`backend/tests/test_api_error_auto_retry.py:39-40` は `call_gemini_raw_copy_v8` を `MagicMock(side_effect=...)` で差し替え（`:46`）。§4-2-3 の v102 の行（`design.md:76`）に「打ち切りは台帳に出さないのが意図」が入った。根拠の行も合う: `backend/app/services/gemini_raw_copy_v8.py:226-227`（`except SoftTimeLimitExceeded: raise`）・`:228-229`（`RuntimeError(...) from exc`）、`line_analysis_v102_svc.py:500-501` |
| N5 同じ値・同時の切り替え | 直った | §6-1 の PUT（`design.md:174`）に「今の行を `SELECT ... FOR UPDATE` で押さえて old_choice_id にする」「同じ choice_id なら書き換えず履歴も書かず 200 で今の行を返す」が入った。§7 の本番の確かめ（claude→codex・codex→claude の2行）とも合う |
| N6 auth.json の読み方 | 直った | §5-1（`design.md:118`）が「JSON として読み、`last_refresh` の1つだけを取り出す。ほかの欄は変数に残さず、ログ・応答・記録に出さない。ファイルがあるかどうかも見る」に変わった。`/health` の返す物（`:120`）とも合う |

## 新しい指摘

### R1. 重さ: 軽・カードで扱える — §7「どこで測るか」と §9（PO の判断を取る時点の言い回しが2通り）
- 根拠: §7（`design.md:193`）と §13-5（`:241`）は「段3の PO のログインより前に取る」、§9（`:217`）は「決まるまで段3に入らない」。段3の中身はログインの前に V1〜V5・secretary-codex の容器・codex の選択肢3行の migration を含む（`:185`）。一方「不可」の時は「codex の容器も選択肢の3行も出さない」（`:193`）。ログインの直前に「不可」と答えが出ると、容器と3行はすでに本番に出ている。
- 直し方: 判断を取る時点を「段3に入る前（V1〜V5 の前）」にそろえる。§9 の書き方がそのまま使えるので、§7・§13-5 の「ログインより前」を「段3に入る前」に直すだけで足りる。実装カードの順番で守れる。

### R2. 重さ: 軽・カードで扱える — §7（「影響はスーパー管理者（PO と担当エンジニア）だけ」の人の範囲は【未確認】）
- 根拠: 秘書の API がスーパー管理者だけなのは実物で確かめた（上の N1）。ただ本番で `is_super_admin` が真の利用者が誰か・何人かは recon にも design にも測った記録が無い【未確認】。
- 直し方: 段3の切り替えの前に、読み取りの道で `public.users` の `is_super_admin = true` の件数（名前・メールは出さず、id と件数だけ）を数えて §7 に書く。想定外の人がいれば切り替えの前に PO に知らせる。

### R3. 重さ: 軽・カードで扱える — 段3（VPS のログインと手元のログインの打ち消し合いが確かめる項目に無い）
- 根拠: recon §5-3 は「VPS 用に別にログインしたとき、手元のログインと打ち消し合うか」を【未確認】に挙げている。design §5-1（`design.md:119`）は「手元の Mac のログインとは別に持つ」と書くが、段3の合格（`:185`）・§8 K6 にこれを確かめる項目が無い。打ち消し合う場合、PO の手元の Codex を使うたびに秘書の行が×になり、K6 の○×が手元の操作で揺れる。
- 直し方: 段3の PO のログインの後に「VPS でログイン→手元の `codex exec` を1回→秘書を1回呼ぶ→両方とも成功」を1行足す。打ち消し合うと分かったら段3を止めて PO に戻す。

## 指摘なしで確かめたこと
- origin/main は c758ea8。d828bb269 からの差分は `scripts/agent-hooks/mac-test-guard/` の4ファイルだけ（`git diff --stat d828bb269 origin/main`）。design が引く assistant.py・llm_budget.py・gemini_*・line_analysis_v102_svc.py・message_translator.py・tcg_*・deploy.yml・run_all_migrations.sh・ai_cloud_views・secretary-agent・画面の部品・試験には差分なし。
- 今の llm_usage_events の列（`migrations/20260930_150000_create_llm_usage_events.sql:26-53`）: tenant_id・cost_usd・使用量の列はすべて NULL 可、model・sdk・purpose は NOT NULL。design §5-1 の「codex の行は cost_usd NULL・tool_use_prompt_tokens と total_tokens NULL」、claude-code の行の「使用量の列すべて NULL」、秘書の行の source_ref NULL（§4-2-3）はこの列の決まりで書ける。CHECK の名前は `llm_usage_events_purpose_check`・`llm_usage_events_sdk_check`（`:46-52`）で、§4-1 の広げる形の対象と合う。
- 前例の DO の塊（`20261020_110000:15-36`）は DROP と ADD が1つの DO の文の中なので、その形で書けば途中で CHECK が外れたまま残ることは無い。§4-1 の「条件なしで毎回 DROP → ADD すると…外れたまま残る」は DO の外で2文に分けた時の話として読める。
- v102 の送り直しの輪（`line_analysis_v102_svc.py:493-519`）の except は `_is_transient_http` の後に `recorder.record_error_detail` と `RecordError("API_ERROR")` へ進む形で、§4-2-3 の「送り直す前・最後に投げる前の両方で、印がある時だけ1行」と差し込める場所が実物にある。
- §7 の答え「スーパー管理者の試験だけ可」の時に claude に戻す流れは、§6-1 の PUT（同じ値なら履歴を書かない）と矛盾しない。戻すと履歴は claude→codex・codex→claude の2行になる。

VERDICT: APPROVE
