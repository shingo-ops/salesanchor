# recon: 旧解析 v6 の投稿を新解析 v102 でやり直す

基準: origin/main b6435490b（2026-10-16）。本番の読み取りは 2026-10-16 01:43Z〜。生出力は /tmp/CC報告ファイル/v6-to-v102/（q*.out）と /tmp/CC報告ファイル/v6-to-v102/recon/（out_*.txt。読んだソースの写しは src/）。調査は Sonnet、確認は Opus。

## 0. PO の依頼と承認（原文）
- 「新しい解析システムで全て再解析できる？」
- 範囲の問い「やり直すのは旧版（v6）の 1,010投稿だけにしますか（y/n）」に続き、「Gemini で行いますか（y/n）」に PO「y」（2026-10-16）。y の中身は「v6 の 1,010投稿のやり直し（約7.5ドル・約2時間）を Gemini で進める」。

## 1. ADR 検索
- `git grep -i` で docs/adr を「再抽出」「retry-extraction」「8b」で検索。直接の ADR は無い。
- 関係する ADR: /Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/docs/adr/ADR-158-product-level-supersession.md（is_current の付け直し）、/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/docs/adr/ADR-1004-llm-usage-ledger.md（Gemini 使用量の台帳）。
- v102 本番切替の設計: /Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/docs/handoff/v102-prod-switch/design.md。

## 2. 本番の件数（q3.out / q5.out / q7.out / recon/out_counts.txt）
| 版 | job 数 | 投稿日時 |
|---|---|---|
| v102 | 457（done 439 / empty 18） | 2026-10-09 23:02Z〜 |
| raw-extraction-v6-rawcode-p1 | 1010（done 963 / empty 41 / error 3 / filtered 3） | 2026-09-09〜2026-10-09 15:10Z |
| v5 / v4 / v3 | 911 / 220 / 218 | 08-28〜09-25 |

- v6 job に紐づく行: extraction_items 17106 / analysis_results 16994（is_current 約2695）/ extraction_attempts 1204 / item_corrections 0。
- 1つの投稿（source_message）に job は1つ。v6 と v102 の両方がある投稿は0件。
- 48時間の配信窓に入る v6 の行は0（v6 の最新投稿は 10/9 15:10Z）。

## 3. やり直しに使える経路
- 既存の再解析 reanalyze_v102_job（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/tasks/tcg_extraction.py:706）は、v6 job には何もしない（:710-713）。
- 抽出 _run_extraction（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/tasks/tcg_extraction.py:333）は、status='pending' の job だけを処理する（:337-347）。
  - 本番の LINE_ANALYSIS_ENGINE は v102。この場合 _run_v102_extraction（:438）→ run_v102_extraction（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/services/line_analysis_v102_svc.py:462）を通る。
  - その中で、:497 で extraction_items を消し（analysis_results も一緒に消える）、:498-510 で新しく入れ直し、:515-527 で prompt_version を v102: に書き換える。
  - TCG_AUTO_ANALYZE=1 なら run_v102_analysis（:1260）、TCG_AUTO_DISTRIBUTE=1 なら _enqueue_auto_distribute（tcg_extraction.py:455-457）。
- done/empty の job を pending に戻す既存の道は無い。アプリが pending に戻すのは、error を戻す tcg_diagnostics_svc.py:232 と、停滞回収の :93 だけ。
- extraction_jobs には、CHECK 制約・トリガー・RLS のいずれも無い（recon/out_ej_cons.txt, out_trg.txt, out_ej_rls.txt）。

## 4. 危険の事実
- 配信の待ち合わせ #8b（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/services/tcg_distribution_svc.py:894-920）
  - pending/running/extracted の job が1件でもあれば、全配信を中止する。
  - やり直し中は常に1件が running なので、そのままでは新しい投稿の配信が約2時間止まる。
- 自動配信の予約
  - 1件ごとに配信タスクが1つ積まれる（TCG_AUTO_DISTRIBUTE=1、recon/out_prod_env.txt）。
  - 1010回、シート全体の書き直しが走る（tcg_distribution_svc.py:789-807, :1000-1049）。
- 停滞回収（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/tasks/tcg_extraction_recovery.py:125-130）
  - created_at が15分より古く、直近の試行も15分より古い pending を、10分ごとに最大50件投入する。
  - pending を一度に多く作ると、自動で投入される。
- キュー
  - task_routes は無い。celery-worker は1台で --concurrency=2（docker-compose.yml:209）。
  - Celery に積むと、新しい投稿の解析がその後ろに並ぶ。
- Gemini が失敗した場合
  - recorder.fail が status='error'、prompt_version=v102 にするが、古い items は残る（DELETE は応答の後）。
  - 既存の retry-extraction（error のみ対象。items を先に消す、tcg_diagnostics_svc.py:223-229）で直せる。
- 相場の点検 unit_price_mismatch
  - v102 の現行行を、期間を区切らずに使う（v102_unit_price_check_svc.py:4,62）。
  - やり直すと、v6 由来の現行行（約2695）が相場の母数に加わる。
- 要確認タブ
  - 窓が無く、sm.is_active=TRUE が条件（tcg_analysis_review_svc.py:57）。
  - v6 で is_active の投稿は30件（そのうち要確認の現行行は22、recon/out_v6_active_review.txt）。
- 控え（バックアップ）
  - 毎日3:00の全 DB dump がある（scripts/backup.sh:27-29、保持10件）。
  - 再実行すると古い控えが消えるので、手動では使わない。
- 費用・時間の実測（q10.out / q12.out）
  - v102 は1件平均 $0.007424・14.5秒（p95 26.0秒）。
  - 失敗は 6/463。
  - 予想: 1007件で約 $7.5、直列で約4時間、2並列で約2時間。

## 5. r1 審査を受けた実測（2026-10-16。生出力 /tmp/CC報告ファイル/v6-to-v102/recon2/）
1. is_current の順位
   - 順位は `received_at DESC, max_computed_at DESC, job_id DESC`（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/services/tcg_analyzer_svc.py:1987-1992）。NULLS の指定は無い。
   - 本番の source_messages 2890件で、received_at が NULL のものは 0（out_q2a〜c）。
   - 窓内の現行の組は 1013。そのうち 665組に v6 の行がある（現行の v6 行は 0）。
   - v6 の received_at が窓内以上の組は 0。v6 の received_at が NULL の組も 0（out_q3a/out_q3b）。
2. 原文と事前フィルタ
   - 原文が空の v6 対象は 0。
   - いまの事前フィルタに当たるものは done の1件（ej 443987d7-db92-4a8c-a5eb-ca42b3ef6e85、message_exclude_no_digit「個別」）。全角数字の扱いは再現していない（out_q4a〜e）。
3. run_v102_extraction の recorder
   - recorder は省略できる（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/services/line_analysis_v102_svc.py:462）。
   - recorder が無いときは、次のとおり動く。
     - claim をしない。
     - extraction_attempts を書かない。
     - 失敗では例外をそのまま送出する（:455）。
     - llm_usage_events は書く（extraction_attempt_id は NULL、:418-427）。
     - status を条件にしない。
     - :496 で DELETE し、:515-527 で status と prompt_version を更新する。
   - claim は、status='pending' でないと CLAIM_CONFLICT になる（tcg_extraction_record_svc.py:69-）。
4. Gemini の時間切れと、本番の資源
   - Gemini の時間切れは指定が無い（gemini_extraction_svc.py:248-276）。google-genai は 2.8.0 で、HttpOptions に timeout がある。
   - celery-worker のメモリは上限 768M に対し 490MiB を使っている。prod1 の available は 941MB（out_q8_free）。
5. 即時通知
   - _publish_review_changed（/Users/tanizawashingo/worktrees/salesanchor/release-reextract-v6-with-v102/backend/app/tasks/tcg_extraction.py:696-703）は Redis の rt:global に publish する。
   - run_v102_analysis は、これを呼ばない。
6. job 5d71f040-d9ae-496a-9c89-7708ec073d88 は prompt_version raw-extraction-v6-rawcode-p1（/tmp/CC報告ファイル/carton-case/q5_job.txt）。
