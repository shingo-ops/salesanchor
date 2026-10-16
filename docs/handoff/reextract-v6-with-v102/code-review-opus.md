# コード審査: v6→v102 やり直しの道具（コミット 62aa26bca）

- 審査役: Opus（読み取りのみ。コード変更・push・本番接続はしていない）
- 対象: backend/app/tools/reextract_v6_with_v102.py / backend/tests/test_reextract_v6_with_v102_pg.py / scripts/ops/reextract-v6-loop.sh
- 照合先: design.md（r5）・card.md・review-opus.md（r2「実装カードに書くべき注意点」・r3「足す注意点」）
- 基準のコード: 62aa26bca。origin/main（e882207ca）との差分のうち、道具が呼ぶファイル（line_analysis_v102_svc.py / tcg_analyzer_svc.py / tcg_extraction.py / gemini_extraction_svc.py / gemini_raw_copy_v8.py / 試験の fixture / test.yml / pyproject.toml）の変更は 0（`git diff --stat 62aa26bca origin/main -- …` の結果は migrations 2本だけ）
- CI ログの控え: /tmp/CC報告ファイル/v6-to-v102/code-review/ci_log_38848795489.txt

## 判定: **REVISE**（M1 を1点直せば APPROVE。m は任意か、本番手順で補えばよい）

---

## 指摘

### M1. v6 に戻した job を、次の `--execute` がまた選んでやり直す（v6 の結果がまた消える。K1 も合わなくなる）
- 【事実】`--rollback-from` は extraction_jobs を控えの全列で UPDATE する。prompt_version は v6、status は done に戻る（reextract_v6_with_v102.py:637-642, :668）。
- 【事実】`--execute` の対象は「prompt_version が v6 で、status が done/empty/error、received_at あり、item_corrections なし」だけで決まる（reextract_v6_with_v102.py:224-261）。戻した job を外す条件は無い。repair_counts.json も見ない（:482-500）。
- 【事実】design D1 は「unreadable の再抽出が2回を超えた件は `--rollback-from --job-id` で v6 に戻す」としている（design.md:122-123）。一方で、gemini_error の残りは `--execute` を流し直すほかに拾う道が無い（`--repair` は v102 の件しか直さない。reextract_v6_with_v102.py:538-539）。
- 起きること: 上限の件を戻した後に、残りの gemini_error を拾うために `--execute` を流すと、戻した件が再び抽出される。応答がまた読めなければ v6 の items・results が消え、`--repair` は repair_exhausted で止まる（:544-545）。費用も掛かる。K1（v6 で残る job ＝ 除外一覧＋skip_*）にも、戻した件が入らない。
- 直し方（どれか1つ）:
  - rollback が `rolled_back` にした job id を out-dir の `rolled_back.txt` に追記する。`classify_v6_jobs`／`process_job` の再判定で、その id を `skip_rolled_back` として飛ばす（記録に残るので K1 にも入る）。
  - あるいは、`process_job` の再判定で repair_counts.json の回数が上限の job を `skip_repair_exhausted` として飛ばす。
- 試験に1本足す: 「unreadable→2回やり直し→rollback→`--execute` しても Gemini を呼ばず skip_* になる」。

### m1. `--job-id` だけの実行が最初に走ると、order.txt が1件になり、費用の上限と `--repair` の範囲が狭まる
- 【事実】order.txt は、無いときだけ書かれ、中身は `--job-id` で絞った後の対象（reextract_v6_with_v102.py:264-273, :488-493）。費用の集計は order.txt の job だけを数える（:444-453, :288-298）。ループの `--repair` も order.txt を読む（reextract-v6-loop.sh:67）。
- design §6 の順（全件の dry-run → `--job-id` 1件）を守れば問題は出ない。順を違えたときに、上限が黙って効かなくなる。
- 直し方: `only_job` があるときは order.txt を書かない。`_Budget.job_ids` に、その回の targets の id も足す（`execute` の :494-496 の後で `|= {j for j, _ in targets}`）。

### m2. 失敗が残っていても、`--execute` と `--repair` が 0 で終わり、ループが「完了」で抜ける
- 【事実】`execute` が 3 を返すのは、費用の上限か連続の失敗の上限のときだけ（reextract_v6_with_v102.py:503-519）。gemini_error が4件ずつ散って残っても 0 になる。`repair` も repair_exhausted が残っても 0（:592-597）。ループは repair の 0 で `exit 0`（reextract-v6-loop.sh:73-75）。
- design D5 は「全部済んだら 0」（design.md:176-177）。実装の 0 は「最後まで回った」の意味。
- 直し方（どちらか）: 終わりに「v6 のまま残る対象（skip_* 以外）」または「unreadable・analysis_error の残り」が1件以上なら、別の終了コード（例: 4）を返す。もしくは本番手順で、ループの後に必ず K4・K7 を確かめることを PO 報告の前提にする（いまの §6-5 で拾える）。

### m3. 空の応答（items 0・unreadable でない）で、抽出の後・解析の前に止まった件を `--repair` が解析しない
- 【事実】本番の流れでは、items 0 の job も run_v102_analysis が review_reasons に `no_items` を書く（tests/test_line_analysis_v102_pg.py:131-136）。
- 【事実】`--repair` が解析をかけるのは「items>0 かつ results=0」か extract_exception のときだけ（reextract_v6_with_v102.py:553-554）。K7 も items>0 だけを見る（design.md:97）。
- 起きること: その位置で止まった件は、`no_items` が付かないまま残る。データは消えない。
- 直し方: `need_analysis` に「status='empty' かつ review_reasons が NULL」を足す（run_v102_analysis は冪等・Gemini を呼ばない。line_analysis_v102_svc.py:1260-1264）。

### m4. `--rollback-from --execute` で失敗した job があっても、終了コードは 0
- 【事実】`rollback` は常に EXIT_OK（reextract_v6_with_v102.py:708）。rollback_error は records.jsonl と集計の出力にだけ出る（:703-705）。
- 直し方: `counter["rollback_error"]` が1以上なら 1 などを返す。

### m5. 後から流した dry-run が excluded.tsv を上書きする
- 【事実】order.txt は started_at.txt があれば order.dryrun.txt に逃がす（:271-273）が、excluded.tsv は毎回同じ名前で書く（:274）。
- K1 の「dry-run の除外一覧」が、最初の一覧ではなくなる。order.txt と同じく、started_at.txt があれば excluded.dryrun.tsv に書く。

### m6. 控え CSV で、値がちょうど `\N` の文字列だと NULL に読まれる
- 【事実】COPY の CSV は、NULL の文字列と同じ値を引用符で囲んで区別するが、Python の csv は引用符を外すので、`_read_csv` では区別できない（reextract_v6_with_v102.py:605-611）。
- 本番の対象の列に `\N` という値がある見込みは低い。直すなら csv.reader で「引用符なしの `\N`」だけを NULL にする（または戻しの dry-run で、`\N` を含む値の件数を出す）。

### m7. 人の直しが Gemini の呼び出し中に入ると、その直しは孤立する（設計 §4 の残りの穴）
- 【事実】直前の再判定（reextract_v6_with_v102.py:408-412）から、run_v102_extraction の DELETE（line_analysis_v102_svc.py:500）までの間に、Gemini の呼び出し（最大 300〜330 秒）が入る。item_corrections の作成文に extraction_items への FK は無い（migrations/20260921_110000_pipeline_tables_public.sql:321-323）ので、直しは消えずに、指す items が無くなる。
- 既存ファイルを変えない方針では塞げない。本番手順で「実行中は要確認画面での直しを控える」を PO 報告に1行入れること。K 判定には、実行後に `item_corrections` のうち extraction_item_id が存在しない行の件数（実行前と比べる）を足すとよい。

### m8. 試験の1行が常に真になる書き方
- tests/test_reextract_v6_with_v102_pg.py:175 は `A or categories(env)[hit] == "skip_prefilter"` で、前半の誤りを見逃す。`assert categories(env) == {ok: "done", hit: "skip_prefilter"}` にする（次の行で中身は確かめているので、実害は無い）。

---

## 観点ごとの確認結果

### 1. 設計との一致
| 項目 | 結果 | 根拠 |
|---|---|---|
| D4 の順番（再判定→組の控え→抽出→読み直し→解析→読み直し→付け直し→費用→記録） | 一致 | reextract_v6_with_v102.py:405-434（2〜5）, :351-376（6〜8）, :508-515（9〜10） |
| 例外の後の session | 一致。抽出の session は rollback して close（:390-395）。区分は新しい session の読み直しで決める（:399-402, :306-332）。v6 のままなら gemini_error、v102 なら確定後として先へ | review-opus.md:187 |
| 解析の失敗 | 例外と extract_exception の両方で analysis_error（:361-370）。run_v102_analysis は自分で失敗を commit する（line_analysis_v102_svc.py:1302-1310） | — |
| 付け直し | item_corrections を読み直してから `_merge_supplier_products(extra_pairs=v6 の組)` → 自分で commit（:335-348）。関数は変更0件だと commit しない（tcg_analyzer_svc.py:2016-2018）ので、明示の commit は正しい | — |
| --repair | unreadable は2回まで再抽出（回数は抽出の前に fsync して保存。:544-547）。取り残しは再解析。v102 の件すべてに付け直し（:553-554）。ただし m3 | design.md:120-127 |
| --rollback-from | 既定は書かない（:661-663）。item_corrections を数えて1件以上なら飛ばす（:651-660）。手順1〜5を1つの取引で行い、失敗はその job だけ rollback（:664-675）。ただし M1・m4 | design.md:221-228 |
| 費用の上限 | started_at.txt からの台帳で毎回数える。NULL があれば止める。処理の前後で確かめる（:444-464, :503-519） | design.md:167, :78 |
| 時間切れ | 主: HttpOptions(timeout=ミリ秒)。予備: alarm(timeout+30)、例外は BaseException の子（:63-64）、finally で alarm(0) と元の handler に戻す（:72-85） | design.md:55-57 |
| D2 確かめ | エンジン・指示書・knowledge_rules 除外系 ≥1。失敗で 2（:187-216） | design.md:131-134 |
| D5 通知 | 1件以上で `_publish_review_changed()` を1回（:520-522）。`_enqueue_auto_distribute` は呼ばない（試験 :53-56 で禁止） | design.md:173-175 |

報告の「設計と違えた点」1〜6 の評価:
1. TCG_SCHEMA を実行時に読む: 妥当。試験は analyzer.TCG_SCHEMA を tenant_901 に差し替える（tests/test_tcg_work_matching_integration.py:366-367）ため、この形でないと試験できない。本番の値は下の 2-4。
2. unreadable にも付け直し: 妥当。D4-8 は区分によらず付け直す設計で、v6 の組の現行を戻す（K8）ために要る。
3. 区分の追加（pairs_error・skip_not_v6・skip_no_context・repair_*・would_rollback・rolled_back・rollback_error）: 妥当。pairs_error は連続の失敗に数える（:59）。
4. order.dryrun.txt: 妥当。ただし excluded.tsv も同じ扱いにする（m5）。
5. --limit で 0: 単発の実行としては妥当。m2 の「0 の意味」と合わせて扱う。
6. CSV の NULL は `\N`・戻しは v102 の組をその場で読む: 後者は design §5-1 のとおり。前者は m6。

### 2. 本番データを壊す道筋
- dry-run は書かない: 【事実】呼ぶのは preflight（SELECT のみ。:187-210）、classify_v6_jobs（SELECT・load_extraction_context・_apply_pre_extraction_filter。どれも SELECT だけ。tcg_extraction.py:172-215, :318-330）、最後に rollback（:270）。試験も表4つの件数が変わらないことを見ている（tests/…_pg.py:150-152）。
- 戻しの CSV の往復: 列の型は pg_attribute から取り、`CAST(:p AS <型>)` で入れる（:614-642）。生成列は除く。試験は items・results・job の全列を jsonb で比べて一致（tests/…_pg.py:511-527）。配列（source_lines INTEGER[]）・真偽・時刻・JSONB を含む。【事実】analysis_results・extraction_items に identity 列は無い（migrations を `GENERATED` で検索して該当 0）。残りは m6 だけ。
- job 単位の rollback: 試験で、FK で失敗する job だけが元のまま、他の job は戻ることを確かめている（tests/…_pg.py:530-563）。手順5の `_merge_supplier_products` が中で commit しても、それは最後の手順なので、取引の途中で確定する件は無い。
- TCG_SCHEMA は本番で public: 【事実】`TCG_SCHEMA = "public"` の直書き（tcg_analyzer_svc.py:58）。環境変数は読まない（環境変数を読む app/tcg_config.py:20 は、この経路では import されない）。knowledge_rules・llm_usage_events は `public.` 直書き（:201, :294）で、design m5 と合う。
- 残る道筋: M1（戻した件の再処理）と m7（直しの孤立）。

### 3. Gemini の時間切れの差し替え
- 外へ漏れるか: 【事実】差し替えは `main()` の --execute/--repair でだけ行う（:744, :748）。本番では、道具だけが動く別コンテナのプロセスなので、celery-worker の Gemini 呼び出しには届かない。試験は execute()/repair() を直接呼び、差し替えの試験は monkeypatch で元に戻す（tests/…_pg.py:471-478）。xdist の他の試験にも漏れない。
- 効く経路: 【事実】v102 の Gemini 呼び出しは `_gem._get_genai_client()`（属性経由。gemini_raw_copy_v8.py:17, :218）。モジュールの属性の差し替えで効く。
- google-genai 2.8.0 で有効か: 【事実】手元の 2.8.0 で確認（`python3 -c "import google.genai as g; print(g.__version__)"` → 2.8.0、実装担当が置いた wheel /tmp/CC報告ファイル/v6-to-v102/impl/g28/x/）。HttpOptions.timeout はミリ秒で、秒に直して httpx の timeout に渡す（_api_client.py:223-233, :1310-1322）。X-Server-Timeout ヘッダも付く（:181-186）。retry_options が無いときは1回で打ち切る（:521-532）。【未確認】本番コンテナの版が 2.8.0 であること（requirements.txt:29 は `>=1.0.0`）。本番の1件目の前に `docker compose run … python -c "import google.genai as g; print(g.__version__)"` で確かめること。
- alarm: 道具は `python -m` の主スレッドで動くので signal は使える。コンテナの PID 1 でも、自前の handler なら届く。

### 4. 試験と CI
- 印・fixture: 既存の PG 試験と同じ。pg・v102 の fixture を import し（tests/…_pg.py:27-30）、pg は GITHUB_ACTIONS と使い捨て DB を必須にして、試験ごとに DB を作って消す（tests/test_tcg_work_matching_integration.py:342-379）。prohibit_live_gemini（autouse）も import で効いている。専用の marker は既存でも使っていない。
- 時間: 【事実】CI の pytest-run は `timeout-minutes: 15`（.github/workflows/test.yml:118）、`-n auto --dist=loadfile`（backend/pyproject.toml:65。2 vCPU なので2並列、ファイル単位で1つの worker）。直近の成功は全体で `6160 passed … in 280.68s`（CI ログ:2265）、ジョブ全体で約5分半。既存で pg を使う試験は 269本あり、それが 2並列 280秒の中に収まっているので、CI での pg 試験1本は平均2秒強以下。新しい試験の pg 試験は 26本なので、CI では1分前後の増えと見積もる（手元の 400秒は Mac の値）。15分の上限には余裕がある。【未確認】実測は、この PR の CI の pytest の行（`… in Ns`）を 280秒と比べて確かめること。
- signal.alarm を使う試験は、xdist の worker の主スレッドで動く（手元でも addopts の -n で通っている）。

### 5. scripts/ops/reextract-v6-loop.sh
- 終了コード: 3・2 で止まる。0 のときは repair へ進み、repair が 0 で完了。それ以外（137 等）は次の回へ進む（:56-76）。最大回数で 1（:79-80）。m2 のとおり「0＝失敗が残っていない」ではない。
- コンテナ名: `reextract-v6-${DATE_TAG}-${round}`（:38）。デプロイが消す名前は `astro-webapp-celery-worker` の部分一致（.github/workflows/deploy.yml:409-411）で、当たらない。ぶつかったら `docker rm -f`（:26-33）。試験あり（tests/…_pg.py:610-626）。
- `-v`・`-T`・`--no-deps`・`--rm`: すべて付いている（:40, :48）。
- /work の書込確認: appuser のまま `--entrypoint sh` で touch と rm（:46-52）。書けなければ 2 で止まる。
- 秘密情報: スクリプトが出すのは日付・回・終了コードだけ。道具の出力も、例外は型名か、戻しの失敗時の DB のメッセージ先頭200字（:675）だけで、API キーや接続文字列は出さない。
- 置き場所: ホストの compose のディレクトリには scripts/ がある（deploy.yml:405 が `bash scripts/deploy/…` を呼ぶ）。マージ・デプロイの後なら scripts/ops/ も届く。

---

## APPROVE の条件
- M1 を直し、試験を1本足す。
- m1〜m8 は任意。直さない m2・m7 は、本番手順（ループの後の K4・K7、実行中の直しを控える旨）を PO 報告に入れること。

---

## r2（直しのコミット 6cc4a99c3。差分は 62aa26bca から）

- 読んだもの: `git diff 62aa26bca 6cc4a99c3`（控え: /tmp/CC報告ファイル/v6-to-v102/code-review/r2_diff.txt）、試験の結果 /tmp/CC報告ファイル/v6-to-v102/impl/pytest2.txt（`39 passed, 2 warnings in 36.77s`）
- 判定: **APPROVE**（下の r2-m1 は push 前に必ず行う。r2-m2〜m4 は任意）

### r1 の指摘の直り具合
| 指摘 | 結果 | 根拠 |
|---|---|---|
| M1 戻した job のやり直し | 直った。rollback が成功した job を rolled_back.txt に fsync して追記し（reextract_v6_with_v102.py:775-776）、process_job が skip_not_v6 の確認の後でその job を `skip_rolled_back` にして飛ばす（:423-425）。区分が記録に残るので K1 にも入る | 試験 test_rolled_back_job_is_skipped_by_the_next_execute（Gemini の呼び出し回数が増えず、v6 のまま） |
| m1 order.txt と費用の範囲 | 直った。order.txt を作るのは絞らない実行だけ（:504-507）。どの実行でも、処理する job を処理の前に order.txt に足し、budget.job_ids にも足す（:515-517）。--limit で止まる件は足さない（:513-514 の後） | test_narrowed_runs_keep_order_txt_and_append_processed_jobs（費用の集計が3件すべてを数える） |
| m2 終了コード 4 とループ | 直った。下の「終了コード 4 とループの抜け方」を参照 | test_exit_4_when_failures_remain_in_execute_and_repair / test_loop_continues_on_exit_4_and_ends_with_4_at_the_max_rounds |
| m3 空の応答で解析前に止まった件 | 直った。判定の根拠も正しい。下を参照 | test_repair_analyzes_an_empty_job_stopped_before_the_analysis |
| m4 戻しの失敗の終了コード | 直った。rollback_error が1件以上なら 1（:781）。失敗した job は rolled_back.txt に入らない | test_rollback_error_gives_exit_1 |
| m5 excluded.tsv の上書き | 直った。excluded.tsv があれば excluded.dryrun.tsv に書く（:283-284） | test_later_dry_run_does_not_overwrite_the_first_lists |
| m6 CSV の `\N` | 直った。下の「CSV の往復」を参照 | test_csv_distinguishes_null_empty_and_backslash_n |
| m7 直しの孤立 | 設計に注記された（design.md:212。実行の後で、開始より後に作られた item_corrections を数えて PO に報告する）。**ただし design.md の変更は未コミット**（r2-m1） | `git status`: ` M docs/handoff/reextract-v6-with-v102/design.md` |
| m8 試験の弱い主張 | 直った（tests/test_reextract_v6_with_v102_pg.py:175 が辞書の完全一致になった） | — |

### 終了コード 4 とループの抜け方
- 【事実】execute と repair は、上限で止まらずに最後まで回り、その回の区分に gemini_error・analysis_error・unreadable・repair_exhausted・pairs_error のどれかがあれば 4 を返す（:56-58, :538-539, :619-620）。skip_* と rolled_back は入らない。
- 【事実】ループは、execute が 0 か 4 のときに repair へ進み、execute も repair も 0 のときだけ「完了」で 0 を返す（reextract-v6-loop.sh:61-79）。どちらかが 4 なら次の回へ進み、最大回数に達したら 4 で終わる（:80-88。residual は :55）。3・2 は今までどおりすぐ止まる。137 等は repair を飛ばして次の回へ進む（今までどおり）。
- 回の進み方（確認）: unreadable の件は v102 になるので、次の回の execute は選ばない。repair が回ごとに1回ずつ再抽出し、2回で repair_exhausted になる。その後は Gemini を呼ばずに 4 を返し続けるので、ループは最大回数まで回って 4 で終わる（費用は増えない）。その件を rollback すると、repair は v102 の件しか見ないので（:538-539 付近）残りに数えず、execute は skip_rolled_back にする。gemini_error の件は v6 のままなので、回ごとの execute がやり直す（費用の上限の内）。
- 【事実】EXIT_ROLLBACK_ERROR=1 はループの「最大回数で 1」と同じ値だが、ループは rollback を呼ばないので混ざらない。

### m3 の判定の根拠
- 【事実】run_v102_extraction は、応答が読めたとき review_reasons を NULL にして commit する（line_analysis_v102_svc.py:513-514, :516-527）。
- 【事実】run_v102_analysis は、items 0 でも（unreadable のときを除き。:1286-1287）パイプラインを通す。_post_review_reasons は件数 0 なら必ず `no_items` を付け（gemini_raw_copy_v101.py:1322-1324）、それを _job_review_reasons 経由で review_reasons に書く（line_analysis_v102_svc.py:770-771, :976）。例外のときは extract_exception を書く（:1302-1306）。
- 【事実】本番の流れも、items 0 のときに解析を走らせる（tcg_extraction.py:446）。
- よって、「v102・status=empty・items 0・review_reasons が NULL」なのは、解析が走っていない件だけ。判定（reextract_v6_with_v102.py:572）は正しい。repair は v102 の件しか見ないので、v6 の empty（NULL）が拾われることもない。コードのコメントには、no_items の出どころとして gemini_raw_copy_v101.py:1324 も書くとよい（任意）。

### CSV の往復
- 【事実】自前のパーサ（reextract_v6_with_v102.py:629-672）は「引用符なしの空 = NULL」「引用符つき = その文字列（空も `\N` も文字列）」と読む。`""` のエスケープと、引用符の中の改行（\n・\r\n）にも対応する。列数が合わない行は `zip(strict=True)` で例外になり、黙って進まない。
- 【事実】PostgreSQL の COPY の CSV は、NULL を引用符なしの空で出す（NULL の既定は空）。FORCE_QUOTE * なら、NULL でない値はすべて引用符で囲まれる。試験は、本物の COPY（FORCE_QUOTE *）の出力で NULL・空・`\N`・改行と引用符を含む値を往復させて一致を見ている（tests/…_pg.py:723-733）。rollback の往復の試験（dump_csv も FORCE_QUOTE *）も通っている。
- 【事実】FORCE_QUOTE を付けない既定の CSV でも、PostgreSQL は空の文字列を `""` と引用して NULL と区別するので、このパーサで正しく読める。逆に `NULL '\N'` を付けて控えを取ると、NULL が文字列 `\N` として戻る（r2-m3）。

### 残りの指摘（いずれも軽微）
- **r2-m1（push 前に必ず）**: m7 の注記を入れた design.md が未コミット（`git status` で ` M`）。コミットに入れること。
- r2-m2: 道具の冒頭の説明の終了コードの行（reextract_v6_with_v102.py:24）に、4（失敗が残った）と 1（戻しの失敗）が書かれていない。`--help` と本番手順を読む人のために足す。
- r2-m3: 控えの取り方を書いた design.md:219 は「`\copy` で CSV にする」だけで、オプションを指定していない。道具の説明（:22）と同じ `(FORMAT csv, HEADER true, FORCE_QUOTE *)` を design §5 か本番手順に書くこと。特に `NULL '\N'` は使わないこと（NULL が文字列 `\N` として戻り、NOT NULL でない列で値が化ける）。
- r2-m4: 絞った実行の後に全件の --execute を流すと、order.txt が既にあるので excluded.tsv が書かれない（:504-507。試験もそれを確かめている: tests/…_pg.py:667）。design §6 の順（最初に全件の dry-run）を守れば dry-run の excluded.tsv があるので問題は出ない。気になるなら、excluded.tsv が無いときだけ execute でも書く。
- 新しい穴: 上のほかには見つからなかった。append_line_durable は1件ごとに fsync するが、件数は数千なので所要は問題にならない（見積もり）。
