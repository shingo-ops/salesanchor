# 設計審査記録: v6 の投稿を v102 で解析し直す（reextract-v6-with-v102）

- 審査日: 2026-10-16
- 審査役: Architect（Opus）
- 対象: `docs/handoff/reextract-v6-with-v102/design.md` / `recon.md`、生出力 `/tmp/CC報告ファイル/v6-to-v102/`（recon/ 含む）
- コード基準: worktree `release-reextract-v6-with-v102`（origin/main b6435490b）。以下の file:line は `backend/` 起点
- 本番 DB への問い合わせ: していない（数値は recon の生出力のみ参照）

## 判定: **REVISE**

狙い（v6 の結果を v102 で置き換え、配信の途中状態を出さない）と、引数追加先・自動配信の止め方の大筋は実コードと一致する。
ただし D3（is_current の付け直しを前提に窓外は配信不変とする主張）の前提が未検証で、処理の並び順・早期分岐・ADR-1019 との衝突・Celery 外のタイムアウト・K2/K4/K5 の観測方法に、直さないと正しく測れない／途中状態や二重実行を起こし得る点がある。

---

## 照合できた設計主張（事実）

| 主張 | 根拠 |
|---|---|
| 引数追加先 `_run_extraction` / `_run_recorded_extraction` / `_run_v102_extraction` | app/tasks/tcg_extraction.py:333, :469（:418 から呼出）, :438 |
| 自動配信の分岐と投入 | app/tasks/tcg_extraction.py:455-457, :606-608, :628 |
| v102 解析は Gemini 応答後に DELETE→INSERT→prompt_version 書換 | app/services/line_analysis_v102_svc.py:462-529（DELETE :497、prompt_version :515-527, :168-171） |
| v102 分析は advisory xact lock 下で実行 | app/services/line_analysis_v102_svc.py:1271 |
| 配信行は ej.status を見ず is_current と窓で絞る | app/services/tcg_distribution_svc.py:319-343 |
| #8 / #8b の待ち合わせ | app/services/tcg_distribution_svc.py:865-892, :894-920 |
| 既存試験 #8 は settings を patch しない | tests/test_tcg_distribution.py:193-302 |

---

## 指摘

### M（必須）

**M1. is_current 付け直しで窓内の行が FALSE になり得る（D3 の前提が未検証）**
- 根拠: 現行行の選び方は `MAX(received_at) DESC → computed_at → job_id`（app/services/tcg_analyzer_svc.py:1982-1995）。PostgreSQL の `DESC` は既定で NULLS FIRST。`received_at` は取込時の解析失敗で NULL になり得る（app/services/tcg_line_import_svc.py:445-460）。
- 影響: received_at が NULL の古い v6 投稿、または received_at が窓内の投稿より新しい v6 投稿を v102 でやり直すと、同じ組（商品×…）について窓内の行が `is_current=FALSE` にされ、主タブから消える。「窓外のやり直しは配信に出ない」という D3 の主張が崩れる。
- 窓の基準は `sm.line_posted_at`（tcg_distribution_svc.py:216-226）で、順位の基準は `received_at`。両者のずれは recon で未測定。
- 直し方: 実行前に (a) 対象 v6 投稿の received_at NULL 件数、(b) 対象 v6 投稿で received_at ≥ 窓内最古 received_at の件数を recon に追加。該当があれば対象から外すか、順位の扱いを設計で決める。K5 もこの観点で測る（M6）。

**M2. 処理の並び順が「新しい順」だと、未処理の v6 結果を参照して解析される**
- 根拠: 〆参照 `load_soldout_ref_posts`（app/services/tcg_analyzer_svc.py:1060-1088）と価格引継ぎ `_INHERIT_PRICE_SQL`（:1094-1111）は過去48h の投稿の保存済み結果を読む（`_load_stock_items` :1201）。
- 影響: 設計の `line_posted_at DESC` では、各投稿の解析時点で「それより古い投稿」はまだ v6 のまま → v6 結果を参照して v102 結果が作られる。窓内（10/14〜）は v6（≤10/9）を参照しないので配信中の行は安全だが、やり直し結果自体の品質が v102 単独と一致しない。
- 直し方: `line_posted_at ASC`（古い順）にする。

**M3. 原文空・事前フィルタ一致の分岐で v6 のまま残る／v6 の行が残る**
- 根拠: `_run_extraction` は raw_text 空なら status='empty' にして prompt_version を変えない（app/tasks/tcg_extraction.py:372-388）。事前フィルタ一致なら 'filtered' にし、items/analysis_results を消さず prompt_version も変えない（:392-414）。schema 未準備は pending のまま（:361-363）。
- 影響: (a) v6 の empty 41 件に原文空が含まれれば prompt_version が v6 のまま残り K1 未達、しかも道具の再実行で毎回再選択される。(b) v6 の done が今のフィルタで filtered になると v6 の is_current 行が残る。要確認タブは ej.status を見ない（app/services/tcg_analysis_review_svc.py:52-63）ので出続ける。
- 直し方: recon に「原文空の件数」「今のフィルタで一致する件数」を追加。K1 の分母からの除外条件と、filtered 化した job の v6 行の扱い（残す／is_current を落とす）を設計で決める。

**M4. ADR-1019 の順序規定と衝突、並行作業と同じ関数を触る**
- 根拠: ADR-1019（Accepted 2026-10-16）`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:25` が `build_distribution_rows` の順序「#8・#8b、設定の読み込み、fetch_output_rows」を明記。`docs/handoff/gas-viewer-fresh-fast/design.md:120-134` も #8b を hold として使う予定。
- 影響: D3 の「設定読込を #8b の前に移す／#8b を窓で絞る」は ADR と食い違う（CLAUDE.md: ADR 優先）。並行設計とも同じ関数で衝突する。
- 直し方: design の ADR 検索欄に ADR-1019 を追加し、ADR-1019 の改訂を伴う変更として起案するか、#8b を変えずに済む方式（M6 の観測案と合わせて）を選ぶ。gas-viewer-fresh-fast 側との順番を決める。

**M5. Celery 外で走らせるとタイムアウトが無く、ハング時に二重実行・二重課金になる**
- 根拠: Celery 側には SoftTimeLimit(300s) がある（app/tasks/tcg_extraction.py:783-784）が、道具プロセスには無い。`genai.Client` にタイムアウト指定なし（app/services/gemini_extraction_svc.py:262-276）。running 停滞回収は 15 分（app/tasks/tcg_extraction_recovery.py:37-38, :64-101）で Celery に再投入する。
- 影響: Gemini 呼び出しがハングすると 15 分後に停滞回収が同じ job を Celery で実行 → 二重呼び出し・二重課金。道具は止まったまま。
- 直し方: 道具側で 1 件あたりの上限（`signal.alarm` 等、300s 相当）を設け、超過時は fail() で error に倒す。

**M6. K2・K4・K5 が観測できない／数値が合わない**
- K2: #8b のログ内訳は status 別件数のみで job id が無い（app/services/tcg_distribution_svc.py:894-920）→「やり直しの job が待ち合わせに入っていない」は観測不可。→ 実行中の #8b 発生回数と `last_distributed_at` の進みで測る、または #8b が窓内件数だけを数えることを試験で担保する形に書き直す。
- K4: 「created_at が 10/9 15:10Z 以前」は v6 の created_at 最大 2026-10-09 15:11:21（out_v6colstat.txt）を取りこぼす。→ 実行前に控えた job id 一覧（控え CSV）で判定する。
- K5: 窓内件数の前後比較は通常の投稿流入と区別できない。→「やり直し job の付け直しで窓内の行が is_current=FALSE になった件数 = 0」を測る形にする（M1 と一体）。

### m（軽微）

- m1. 自動配信は呼出時に `os.environ` を読む（app/tasks/tcg_extraction.py:455, :606）。道具プロセスで `TCG_AUTO_DISTRIBUTE=0` にすれば D2 のコード変更なしで止められる（代替案として検討）。
- m2. pending 停滞回収の条件（app/tasks/tcg_extraction_recovery.py:113-137）は created_at と最新 attempt が 15 分超 → v6 job を pending に戻した瞬間に成立し、Celery と取り合う。片方は CLAIM_CONFLICT（app/services/tcg_extraction_record_svc.py:78-86）。道具は CLAIM_CONFLICT を連続失敗に数えず、DB を読み直して判定すること。pending に戻すのは処理直前の 1 件ずつにする。
- m3. claim 前の例外では job が pending のまま残り、停滞回収が Celery に投入する（tcg_extraction_record_svc.py:224-270 の `_owned` 条件）。道具の停止手順にこの扱いを書く。
- m4. `_publish_review_changed` はタスク側のみ（app/tasks/tcg_extraction.py:794）→ 道具実行では要確認画面の即時反映が起きない。完了後に一度通知するか、仕様として明記。
- m5. 要確認タブは窓なし（app/services/tcg_review_sheet_svc.py:106-109 → tcg_analysis_review_svc.py:105-108）。「窓外は待っても出力不変」は主タブのみ真。配信テスト対象（has_review=t）は途中状態を書き得る。
- m6. 在庫表 API は #8b を持たない（app/api/inventory_offers.py:356-380）→ is_current の変化が即時に見える。`line_import_admin.py:84`（ready_for_delivery は import 単位）・`:117`（窓なし fetch_output_rows）も同様。影響範囲表に追加。
- m7. ダッシュボードの stale running（created_at < 10 分前、app/services/tcg_analysis_dashboard_svc.py:39-50）に道具実行中の job が 1 件出る。v6 job は created_at が古いため。運用者向けに周知。
- m8. K3: `llm_usage_events` を purpose だけで集計すると通常投稿分も含む。`source_ref='extraction_job:<id>'`（形式は tcg_extraction.py:422 付近）と控えの job id で絞る。`cost_usd` NULL は SUM で無視される点も注記。
- m9. `--max-cost-usd` と K3 の上限が同じ値だと、判定が 1 件処理後のため 1 件分超過し得る。道具の上限は K3 より 1 件分（平均 $0.007424、q10）以上小さくする。
- m10. 本番実行・`\copy` による控えは VPS 直作業で無制限鍵を要する → PO 許可が要ることを計画に明記。戻し手順（控えからの復元 SQL）を実行前に書く。
- m11. celery-worker コンテナ内で 3 本目のプロセスを動かす（docker-compose.yml:206-208、concurrency=2）とメモリを取り合う。別コンテナ（`run --rm`）案を比較する。
- m12. recon の is_current 件数が 2696（out_counts）と 2695（out_v6_current_rows）で 1 件ずれる。測った時刻差か条件差かを注記。

---

## 未解決事項（実測・確認が要るもの）

1. 対象 v6 投稿の received_at NULL 件数、received_at と line_posted_at のずれ（M1）
2. 原文空の件数、今の事前フィルタに一致する件数（M3）
3. K6 の job `5d71f040` が v6 か（未確認）
4. Gemini の 1 日あたり上限（shadow で 12 日 4367 回の実績のみ、q9。上限値は未確認）
5. 本番実行の実行者と無制限鍵の許可（PO）
6. ADR-1019 を改訂するか、#8b を変えない方式にするかの判断（M4）

---

## r2 審査（2026-10-16 12:26 JST）

- 審査役: Architect（Opus）。読み取りのみ。本番 DB には問い合わせていない（数値は recon §5 と /tmp/CC報告ファイル/v6-to-v102/recon2/ の生出力のみ）。
- コード基準: worktree release-reextract-v6-with-v102（b6435490b）。file:line は `backend/` 起点、migrations と workflow はリポジトリ起点。

### 判定: **REVISE**

r1 の M1〜M6 への答え（status を変えない方式・ASC・フィルタ件の除外・#8b 不変）は筋が通っており、実コードとも合う。
ただし「recorder なしで2関数を直接呼ぶ」方式で、失敗の見え方と is_current の付け直しが Celery 経路と変わる点を設計が拾えていない。
また、デプロイで別コンテナが消される事実と食い違う記述がある。下の M1〜M6 を直せば APPROVE できる見込み。

### 確認できた事実（問い 1〜8）

| # | 問い | 事実（根拠） |
|---|---|---|
| 1a | status を条件にしない | 正しい。run_v102_extraction は load_extraction_context → 指示書 → Gemini → DELETE/INSERT → UPDATE で、status を読まない（app/services/line_analysis_v102_svc.py:462-529） |
| 1b | 失敗は DELETE の前で例外か | Gemini 呼び出しの例外は、recorder=None ならそのまま送出（:452-456）。DELETE は :496 なので、その前で止まる。**ただし応答が JSON でない場合は例外にならず**、`items=None → rows=[]` で DELETE（:496）→ status='empty'・review_reasons='response_unreadable' で commit（:492-493, :511-528） |
| 1c | commit の位置 | 関数の中で3回 commit する: Gemini の前（:446）、台帳を書いた直後（:424）、最後（:528）。道具が rollback で戻せるのは「:446 から :528 までの間」の DELETE/INSERT/UPDATE だけ。:528 の後に時間切れ等で例外が出ると、DB は v102 で確定しているのに道具は失敗と数える |
| 1d | source_ref の形式 | `extraction_job:<job_id>`（:93, :421）。台帳の時刻列は **occurred_at**（migrations/20260930_150000_create_llm_usage_events.sql:28）。created_at ではない。cost_usd は NULL になり得る（app/services/llm_budget.py:259） |
| 2a | run_v102_analysis は単独で呼べるか | 呼べる。status の前提は無い。件が無く response_unreadable のときは早期 return（:1286-1287） |
| 2b | lock・is_current | pg_advisory_xact_lock（:1271）は :1302 の commit で外れる。is_current の付け直し `_merge_supplier_products`（:1310）は **lock の外**で走り、変更が1件以上のときだけ commit（app/services/tcg_analyzer_svc.py:2016-2018） |
| 2c | 失敗の扱い | 解析の例外は **送出しない**。rollback して review_reasons に extract_exception を書き、空の stats を返す（:1303-1309）。送出するのはマスタの読み込み（:1288、try の外）と ctx が無いときだけ |
| 2d | 配信予約 | 内部で積まない・_publish_review_changed も呼ばない（:1260-1312）。積むのは呼び出し元（app/tasks/tcg_extraction.py:448-457, :713-722） |
| 3 | 道具から呼べるか | `load_extraction_context(session, job_id)`（app/tasks/tcg_extraction.py:318-330）は読み取りのみ。`_apply_pre_extraction_filter(session, raw_text)`（:172-224）も読み取りのみ。ただし knowledge_rules が読めないと `session.rollback()` して None（=フィルタしない）を返す（:200-203） |
| 4 | Gemini の作り | 同期の `client.models.generate_content`（app/services/gemini_raw_copy_v8.py:218-227）。例外は RuntimeError に包む（:226-227）。Client に timeout 指定なし（app/services/gemini_extraction_svc.py:248-276）。google-genai の HttpOptions.timeout は「ミリ秒」（手元 2.20.0 の model_fields で確認。本番 2.8.0 では未確認） |
| 5 | extraction_attempts を読む所 | app/routers/tcg_analysis_dashboard.py:474,490,508（費用サマリ。attempts 起点の LEFT JOIN）, :865,877（日別リクエスト・成功率）, :1077-1108（失敗の対応一覧）, app/services/tcg_analysis_dashboard_svc.py:116（最新エンジン）, app/routers/tcg_diagnostics.py:114（job の試行一覧）, app/tasks/tcg_extraction_recovery.py:71,120（停滞回収）。v102 の解析・要確認・配信は読まない |
| 6 | compose run | celery-worker は backnet・環境変数・768M 上限・/tmp tmpfs 64M（docker-compose.yml:207-286）。`run` は同じ service 定義から作られる。**デプロイは名前の部分一致で `astro-webapp-celery-worker*` を `docker rm -f` する**（.github/workflows/deploy.yml:411、戻し時 :674-676） |
| 8 | FK の向き | extraction_jobs ←(CASCADE) extraction_items（migrations/20260921_110000_pipeline_tables_public.sql:95）←(CASCADE) analysis_results（同 :216/:251）←(CASCADE) analysis_soldout_extra_targets（migrations/20261010_120000_create_analysis_soldout_extra_targets.sql:4）。extra_targets を書くのは v102 だけ（app/services/line_analysis_v102_svc.py:869）なので v6 job には無い。item_corrections は FK なし（migrations/20260903_170000_item_corrections_t004.sql:6） |

### 指摘

#### M（必須）

**M1. Gemini の応答が読めないとき、v6 の結果を消して「empty」で確定し、どの K にも失敗として出ない**
- 根拠: app/services/line_analysis_v102_svc.py:392-401（JSON でなければ items=None）, :492-496（rows=[] でも DELETE）, :511-528（status='empty'・prompt_version=v102・review_reasons='response_unreadable' で commit）。続く run_v102_analysis は早期 return（:1286-1287）。
- 影響: v6 の件（平均 17件/投稿）が消え、prompt_version が v102 になるので D3 で二度と選ばれない。K1・K4 は通る。
- 直し方: D4 の結果区分に `unreadable` を足す（戻り値 `review_reasons == 'response_unreadable'` で判定）。連続失敗に数える。K4 に「処理した job で review_reasons に response_unreadable を含む件 = 0（あれば一覧にして、控えから戻すか再実行）」を足す。

**M2. 抽出の commit と解析の間で止まった件が、「v102 だが解析結果が無い」まま取り残される**
- 根拠: 抽出は :528 で確定し、items の DELETE で v6 の analysis_results も CASCADE で消える（migrations/20260921_110000_pipeline_tables_public.sql:216）。解析の失敗は例外にならず extract_exception を書いて返る（:1303-1309）。D3 は prompt_version=v6 だけを選ぶので、この件は流し直しで拾われない。
- 起きる場面: (a) :528 の直後に時間切れ（signal）が来る、(b) 解析の pipeline 失敗、(c) マスタ読込の例外、(d) デプロイでコンテナが消える（M4）。
- 影響: その投稿の行が要確認・相場点検・在庫表から消える。D4-3 の「例外のときは解析失敗と数える」では (b) を数えられない。
- 直し方: (1) 失敗・例外のあとは、session を捨てて新しい session で job の prompt_version・review_reasons を読み直して区分を決める。(2) 解析後に review_reasons に extract_exception を含むかで `analysis_error` と判定する。(3) 道具に「直し」モード（`--repair`）を足す。対象は、控えの job id のうち v102 で、items>0 かつ analysis_results=0、または extract_exception を持つ件。これらに run_v102_analysis と M3 の付け直しをかける。(4) K に「控えの job id のうち v102 で items>0 かつ analysis_results=0 の件 = 0」を足す。

**M3. v6 だけが持っていた組の is_current が付け直されない**
- 根拠: run_v102_analysis は付け直しの「前の組」を `_load_resolved_pairs`（:1000-1017）で読む。しかしそれは :1296 で呼ばれ、抽出の DELETE（:496）で v6 の analysis_results が CASCADE で消えた後なので、常に空になる。`_merge_supplier_products` は、この job の新しい組と extra_pairs だけを付け直す（app/services/tcg_analyzer_svc.py:1912-1950）。
- 影響: v6 投稿 P が組 X の現行だったのに v102 で X を出さなかった場合、X の現行が無くなる。同じ仕入元の一つ前の投稿の X 行は FALSE のまま残る。窓なしで読むところ（要確認タブ app/services/tcg_analysis_review_svc.py:57、相場点検 app/services/v102_unit_price_check_svc.py:62、line_import_admin の fetch_output_rows）から、その組が消える。主タブ（窓内）には v6 の現行行が無い（recon §5-1）ので、K5 では見えない。
- 直し方: 道具が抽出の **前** に `_load_resolved_pairs(session, job_id)` で v6 の組を控える（読み取りのみ）。解析の後に `analyzer._merge_supplier_products(session, job_id, analyzer.TCG_SCHEMA, extra_pairs=v6_pairs)` を呼んで commit する（冪等）。控えた組は1行の記録にも出す（M2 の --repair でも使う）。試験に「v102 が出さない組で、一つ前の投稿の行が現行に戻る」を足す。

**M4. 「デプロイでは止まらない」は誤り。別コンテナはデプロイで強制削除される**
- 根拠: .github/workflows/deploy.yml:411 `docker ps -a --filter "name=astro-webapp-celery-worker" ... | xargs -r docker rm -f`。name フィルタは部分一致なので、`docker compose run` の既定名 `astro-webapp-celery-worker-run-<id>` も当たる。失敗時の戻し（:674-676）も同じ。
- 影響: 約2〜4時間の実行中に main へのマージ→デプロイがあると、途中で SIGKILL される。DB の取引は PG 側で rollback されるが、M2 の (d) の取り残しが起きる。
- 直し方: (1) `--name reextract-v6-<日付>` を付けて、名前を `astro-webapp-celery-worker` で始めない。(2) 実行中は main のマージを止めることを計画 §6 に書く（PO・他セッションへの周知を含む）。(3) §4 の行を事実に合わせて書き直す。

**M5. K2・K6 の判定が一義でない。K3 の列名が違う**
- K2「0 か通常の新着だけ」「ふだんと変わらない」は○×が決まらない。→「控えの job id のうち status が pending/running/extracted の件 = 0（実行中に3回読む）」と「実行中の #8b のログ件数 = 0、または新着 job の id だけで説明できる」と「配信の last_distributed_at が実行中に1回以上進む」にする。
- K3 は `created_at` ではなく `occurred_at`（migrations/20260930_150000_create_llm_usage_events.sql:28）。`cost_usd IS NULL` の件数も同時に出す（NULL が1件でもあれば、上限が効いていないので止める）。
- K6「PO に見せる」には合格の条件が無い。→「job 5d71f040 の prompt_version が `v102:` で始まる」かつ「その items に紐づく analysis_results が1件以上」かつ「カートンの行の product_id・condition_id・数量・単価を一覧で出し、PO が y/n で判定」にする。
- K1 は「4件以下」ではなく、dry-run が出した除外の一覧（filtered 3・フィルタの件・item_corrections の件）と **一致** で判定する。

**M6. 戻し方の手順 4「窓内の組を再解析で付け直す」は、v6 では動かない**
- 根拠: 既存の再解析 reanalyze_v102_job は、v102 でない job では何もしない（app/tasks/tcg_extraction.py:706-713）。CSV の is_current は控えた時点の値なので、その後に新しい投稿が同じ組を取っていると、現行が2つになる。
- 直し方: 戻しの手順は次のとおりにする。
  1. 控えの job id の extraction_items を DELETE する（v102 の analysis_results・extra_targets も CASCADE で消える）。
  2. items → analysis_results の順に CSV から INSERT する（id はそのまま）。
  3. extraction_jobs を CSV の全列で UPDATE する（status, extracted_at, prompt_version, error_message, gemini_unsure, review_reasons, system_review_detail を含む）。
  4. 戻した job ごとに `_merge_supplier_products(..., extra_pairs=<v102 が出していた組>)` を呼ぶ。v102 が出していた組は、手順 1 の前に `_load_resolved_pairs` で控える。
  5. 道具に `--rollback-from <dir>` を持たせるか、戻しの SQL とスクリプトを実行前に PR に入れる。手順 4 は SQL だけでは書けない（Python の関数呼び出しが要る）。
- CASCADE の向き（job → items → results → extra_targets）なので、items を消して入れ直す形は成り立つ。

#### m（軽微）

- m1. 時間切れの作り。`signal.alarm` のハンドラで TimeoutError（OSError の子）を投げると、httpx/httpcore が通信の失敗に読み替えて、SDK が再試行する恐れがある【未確認】。また `_record_usage` の `except Exception`（app/services/line_analysis_v102_svc.py:425）に当たると、時間切れが黙って消える。→ 主は、道具の中だけで `_gem._get_genai_client` を包み、`HttpOptions(timeout=300_000)` を足す（既存ファイルは変えない）。alarm は予備にとどめ、BaseException の子の独自例外を投げる。run_v102_extraction が戻ったら、すぐ `signal.alarm(0)` にする（解析・lock の最中に鳴らさない）。DB の途中で鳴った場合は、psycopg2（libpq）が EINTR を再試行するので、C の呼び出しが終わってから Python で例外が出る【推測：CPython の signal の仕様による。実測なし】。そのため、どの場合も M2 の「新しい session で読み直す」で区分を決める。
- m2. 時間切れで切った呼び出しも、Gemini 側では課金され得るが、台帳には残らない（:417-427 は応答を受けたときだけ）。K3 にこの差を注記する。
- m3. attempts を書かないことの影響を §4 に足す。費用サマリ（app/routers/tcg_analysis_dashboard.py:465-510）は attempts 起点なので、やり直しの約 $7.5 が「日別・仕入元別・合計」に出ない。台帳起点の月別（:746 以降）とは数字が合わなくなる。日別リクエスト・成功率（:857-883）にも 1007回が出ない。診断の試行一覧（app/routers/tcg_diagnostics.py:114）は、v102 の job に v6 時代の試行だけを表示する。停滞回収（app/tasks/tcg_extraction_recovery.py:71,120）は status を変えないので影響しない。→ 周知と、PO への報告文に注記する。
- m4. 付け直し（app/services/line_analysis_v102_svc.py:1310）は advisory lock の外で走る。§3 D4-3 の「lock・付け直しは関数の中」は半分だけ正しい。人の直しの再解析タスクと交差し得るので、M3 の追加の付け直しの直前にも item_corrections を読み直し、行があれば飛ばす。
- m5. D3 の SQL は、スキーマを付けて `public.item_corrections`・`public.extraction_jobs` と書く（コードの TCG_SCHEMA は "public"、app/services/tcg_analyzer_svc.py:58）。除外の判定は選ぶ時だけでなく、1件ごとの処理の直前にも行う（実行は数時間かかる）。
- m6. `docker compose run` は nohup で流すため `-T` を付ける。ホストの compose プロジェクトのディレクトリ（.env がある所）で実行する。768M の上限と restart の方針が run のコンテナにも効くかは、`docker inspect` の HostConfig.Memory・RestartPolicy で実測する【未確認】。
- m7. `_apply_pre_extraction_filter` は knowledge_rules が読めないとき「フィルタしない」を返す（app/tasks/tcg_extraction.py:200-203）。D2 の確かめに「knowledge_rules の message_exclude 系の件数が 1以上」を足す（読めずに素通りさせない）。
- m8. 原文の組み立ては、run_v102_extraction の中でもう一度行われる（:471）。道具側の ctx は判定にだけ使う、と実装カードに書く。

### 実装カードに書くべき注意点
1. 1件ごとの順番は次のとおり。
   1. 新しい session を作る。
   2. item_corrections を読み直す。
   3. ctx を作り、フィルタを判定する。
   4. `_load_resolved_pairs` で v6 の組を控える。
   5. 時間切れ付きで run_v102_extraction を呼ぶ（戻ったらすぐ `alarm(0)`）。
   6. 戻り値の review_reasons を見る（unreadable かどうか）。
   7. run_v102_analysis を呼ぶ。
   8. 読み直して extract_exception があるかを見る。
   9. `_merge_supplier_products(extra_pairs=v6 の組)` を呼んで commit する。
   10. 費用を読み直す（occurred_at・NULL も見る）。
   11. 1行を記録する。
2. 例外のあとは、session を捨てる。新しい session で job を読み直してから、区分を決める（失敗と数えるのは、DB が v6 のままのときだけ）。
3. `--repair` で取り残し（v102・items>0・results=0／extract_exception／unreadable）を直す。
4. 本番は `docker compose run --rm --no-deps -T --name reextract-v6-YYYYMMDD celery-worker ...` で流す。実行中は main のマージを止める。
5. 控えには extraction_jobs の全列・items・analysis_results・処理順の job id 一覧を入れる。戻しのスクリプトは PR に入れる。
6. 試験に足すもの
   - 応答が読めない件が unreadable と数えられる。
   - 解析の pipeline の失敗が analysis_error と数えられる。
   - 抽出の確定後に例外が出た件が、読み直しで正しく区分され、--repair で直る。
   - v6 だけの組が、一つ前の投稿へ現行として戻る。
   - `--name` を付けたコンテナ名が `astro-webapp-celery-worker` で始まらない（コマンドの組み立てを試験する）。

---

## r3 審査（2026-10-16 12:31 JST）

- 審査役: Architect（Opus）。読み取りのみ。本番 DB には問い合わせていない。
- 対象: design.md r3（§0-2・§1〜§7）。コード基準は r2 と同じ（b6435490b）。

### 判定: **REVISE**（残りは2点。設計の文言を足せば APPROVE できる）

r2 の M1〜M6・m1〜m8 には、すべて答えがある。D4 の順番（再判定 → 組の控え → 抽出 → 読み直し → 解析 → 読み直し → 付け直し → 費用）は、コードの commit 位置（app/services/line_analysis_v102_svc.py:424, :446, :528, :1302, app/services/tcg_analyzer_svc.py:2016-2018）と合う。
残るのは、(1) 控えのファイルを置く場所が、コンテナと一緒に消えること、(2) 「解析の確定 → 付け直し」の間で止まった件を、--repair も K も見つけられないこと。

### 問い1: M4 の扱い（マージを止めない）は十分か
- 名前を外す（deploy.yml:409-411 の部分一致から外れる）＋ホストの繰り返し＋--repair、という方針で十分。マージを止める必要は無い。
- `docker compose stop celery-worker`（.github/workflows/deploy.yml:407）と `up --remove-orphans`（:412）が run のコンテナに効くかは、【未確認】のままでも合否に影響しない。
  - どの時点で止まっても、ちょうど1件が途中になるだけ。取引の途中なら、PG が rollback する。
  - したがって条件は「途中のどの位置で止まっても、--repair が直せること」の1つだけ。下の M2 を直せば、この条件を満たす。
  - stop の場合は SIGTERM のあと 60秒で止まる（docker-compose.yml:265-270）。道具は SIGTERM で今の1件を切り上げるだけでよく、特別な扱いは要らない。

### 指摘

#### M（必須）

**M1. 控え（pairs/・処理順の一覧・除外一覧・CSV）を置く場所が、コンテナの中にしかない**
- 根拠: celery-worker の volumes は、資格情報2つの読み取り専用だけ（docker-compose.yml:256-258）。/tmp は tmpfs 64M（:282-283）。`--rm` で消える。/app は root の持ち物で、実行ユーザーは appuser（backend/Dockerfile:27-28）。
- 影響: D4-3 の pairs/<job>.json は、コンテナが消えると無くなる。そのため、--repair の付け直しも、--rollback-from も動かない。ホストの `\copy` で取る CSV も、コンテナからは読めない。
- 直し方
  - D6 のコマンドに `-v /home/ubuntu/reextract-v6:/work`（書き込み可）を足す。`--out-dir /work/...` と `--rollback-from /work/backups/...` を使う。
  - ホストのディレクトリは、appuser の uid が書けるようにする（実行前に `id appuser` で uid を実測する）。
  - pairs/<job>.json は、書いて fsync してから、D4-4 の抽出に進む。書けなければ、その件は抽出しない。

**M2. 解析の確定（:1302）と付け直し（D4-8）の間で止まった件を、--repair も K も見つけられない**
- 根拠: K7 は「items>0 かつ results=0」と extract_exception だけを見る。解析が確定していれば、どちらにも当たらない。--repair の対象は、K4(b) と K7 だけ（D1）。
- 影響: v6 だけの組の現行が無いまま残る（r2 の M3 と同じ害）。D4-8 で item_corrections があり、付け直しを飛ばした件も同じ。
- 直し方（どちらか、または両方）
  - (a) --repair は、一覧のうち v102 で pairs ファイルがある件の **すべて** に、付け直し（`_merge_supplier_products(extra_pairs=pairs)`）をかける。冪等で、Gemini も呼ばない。
  - (b) K8 を足す。pairs/ の組（仕入元チャネル・product_id・condition_id）のうち、「その組の行はあるのに is_current=TRUE が0行」の件 = 0。--repair の判定にも使う。
  - D4-8 で飛ばした件は、区分 `skip_merge` と記録する。

#### m（軽微）
- m1. unreadable が毎回出る投稿は、繰り返し（最大10回）のたびに --repair で Gemini を呼び直す。→ --repair でのやり直しは1件あたり N回まで（例: 2）とする。超えたら `--rollback-from --job-id` でその件だけ v6 に戻す。そのため、戻しは job 単位で選べるようにする。
- m2. 費用の上限は、1回のプロセスの中の累計ではなく、「一覧の job の source_ref・最初の開始時刻（out-dir に保存）以降」で台帳から毎回数える。そうしないと、繰り返し10回で上限が外れる。
- m3. K1・K4(a) の「除外一覧」には、D4-2 の再判定で後から飛ばした件（実行記録の skip_*）も含める。そうしないと差が出る。
- m4. K2(b) は、実行中に新しい投稿の job が1件以上できたときだけ判定する（新着が無ければ、last_distributed_at は進まない）。
- m5. 戻しの前に、v102 の items に紐づく item_corrections（確認済み・直し）を数える。1件以上ある job は戻さずに報告する（items を消すと人の判断が宙に浮く。FK なし、migrations/20260903_170000_item_corrections_t004.sql:6）。analysis_results の INSERT が FK（products 等）で失敗した job は、job 単位で rollback して報告する。
- m6. D6 の `--name ...-N` の N は、繰り返しの回の番号にする。前の回のコンテナが残っていたら（名前がぶつかったら）、`docker rm` してから次へ進む。

### 実装カードに足す注意点
1. D6 のコマンドは次のとおり。
   ```
   docker compose run --rm --no-deps -T --name reextract-v6-YYYYMMDD-<回> -v /home/ubuntu/reextract-v6:/work celery-worker python -m app.tools.reextract_v6_with_v102 --out-dir /work/run ...
   ```
2. pairs ファイルは、書いて fsync してから抽出に進む。
3. --repair は、すべての v102 の件に付け直しをかける（冪等）。
4. K8 を足す。
5. 費用は、台帳の全期間の累計で数える。
6. 試験に「解析の確定後・付け直しの前に止まった件が、--repair で付け直される」を足す。

---

## r4 審査（2026-10-16）

### 判定: **REVISE**（文言だけ。直せば、差分を見るだけで APPROVE する）
r3 の M1・M2・m1〜m6 は、§0-3 にすべて答えがある。中身は妥当。
ただし本文（§1・D1・§5・§6・§7）に反映されていない所がある。Generator は本文を読むので、このままでは抜ける。1点は、戻しが動かない。

### 指摘
- **M1. 控えの CSV が、コンテナから見えない場所にある**
  - §5 は、控えを /home/ubuntu/backups/reextract-v6/ に置く。D6 で載せるのは /home/ubuntu/reextract-v6 だけ（design.md:179）。
  - そのため `--rollback-from` が CSV を読めない。
  - 直し方: 控えを /home/ubuntu/reextract-v6/backups/ に置くか、`-v` をもう1つ足す。
- m1. D1 の `--repair` が、まだ「K4(b)・K7 に当たる件」のまま。§0-3 の M2「v102 の件すべてに付け直し」と、m1「2回まで（repair_counts.json）」を本文に入れる。
- m2. §5 の戻しに、次を本文として入れる。
  - `--job-id` で job を選べること。
  - 戻す前に item_corrections を数え、1件以上なら戻さないこと（m5）。
  - job 単位で rollback すること。
- m3. §1 の表の K1（除外一覧に skip_* を含める）と K2(b)（新着があるときだけ判定）を、§0-3 の m3・m4 に合わせて書き直す。
- m4. §6-5 の「K1〜K7」を「K1〜K8」にする。§6-3・6-4 の確かめにも K8 を足す。表の並び（K8 が K7 の前）を直す。
- m5. §7 の試験に、次を足す。
  - 解析の確定後・付け直しの前に止まった件が、`--repair` で付け直される。
  - unreadable のやり直しが2回で止まる。
  - 戻しが、item_corrections のある job を飛ばす。
  - started_at.txt からの費用の累計で止まる。
  - pairs が書けないとき、抽出しない。

---

## r5 審査（2026-10-16）

### 判定: **APPROVE**
r4 の M1・m1〜m5 は、本文に入っている。
- 控えは /home/ubuntu/reextract-v6/backups/ に置き、コンテナからは /work/backups で読める（design.md:217, :221、D6 の -v と一致）。
- D1 の --repair・--rollback-from、§1 の K1・K2(b)・K7→K8 の並び、§6 の K8、§7 の5つの試験も反映済み。
- 重大な指摘は残っていない。

### 実装カードへの注意（審査の条件ではない）
- 戻しの手順5 `_merge_supplier_products` は、変更が1件以上のときだけ、関数の中で commit する（app/services/tcg_analyzer_svc.py:2016-2018）。
  - 変更が0件なら commit しないので、道具は手順5の後に必ず自分で commit する。
  - 手順0〜4 が確定するのは、この commit の時点。
  - --repair の付け直しも同じ扱いにする。
- pairs/ の置き場所を1つに決めて、カードに書く。
  - 実行時の out-dir（/work/pairs）と、§5 の控え（backups/pairs）が別になっている。
  - --repair と --rollback-from が、同じ pairs を読むようにする。
