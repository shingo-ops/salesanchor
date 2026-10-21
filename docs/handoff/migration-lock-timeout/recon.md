<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ。リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 2 現在地 — アプリ入れ替え中に在庫表が止まる件

**日付**: 2026-10-21  
**担当**: Planner（Opus）。調査は Sonnet、基準は fetch 後の origin/main（22f083083）。

## 0. PO の依頼と承認済みの成功条件（原文）
- 問い: 「SAアプリは1秒以内になった？」→ 再測定 → 遅い時間帯の原因調査 → 「入れ替え中に在庫表が止まらないように直す」を PO が「1」で選択（2026-10-21）。
- 承認済み KGI（PO「1」2026-10-21）:
  - アプリの入れ替え中に在庫表を開いても、1回の表示が2秒を超えない（作り替えの作業がほかを待たせるのは最大1秒まで）。
  - 待たせ合いで入れ替えが失敗する回数を0にする（今は週4回）。
  - 確かめ方: 試験用の DB で再現して確かめ、本番は次の数回の入れ替えの記録で確かめる。

## 1. 既存 ADR の検索結果
- `git grep -il "lock_timeout\|run_all_migrations" origin/main -- docs/adr/` と `docs/adr/FEATURE-INDEX.md` を確認。
- ADR-1005（`docs/adr/ADR-1005-migration-run-once-ledger.md`）: :17 毎回全件実行・実行記録なし。:27-29 段階0/1/2（段階2=未実行のものだけ1回流す）。:5 Accepted（方向性）、各段階の GO は別。→ 今回の「全件を毎回流す」はこの ADR の領域で、今回は変えない。
- ADR-1003（`docs/adr/ADR-1003-go-delegation-to-opus.md`）:35 DROP TABLE / DROP COLUMN を含む migration は委任 GO の対象外。
- ADR-135 / ADR-136: scripts/ は危険パス。GO 記録が要る。
- FEATURE-INDEX.md:62: migration は blue-green の切替より前に流れる（古い backend が読みを返している間に DDL が走る）。
- lock_timeout を決めた ADR は無い（0件）。

## 2. 移行処理の流れ（事実）
- `.github/workflows/deploy.yml:563-581` 「Run database migrations」。`appleboy/ssh-action@v1`（:565）。:576 `cd /home/ubuntu/salesanchor`、:577 `bash scripts/run_all_migrations.sh`。deploy.yml に timeout-minutes / command_timeout の指定は0件。
- ssh-action v1 の command_timeout 既定は 10m（`gh api 'repos/appleboy/ssh-action/contents/action.yml?ref=v1'` の :28-30 `default: "10m"`）。→ 移行ステップは10分で打ち切られる。
- 移行ステップの所要は通常 73〜138秒、詰まった回は 430秒・436秒（直近300回の deploy から。生出力: /tmp/CC報告ファイル/migration-lock-timeout/recon2/notes.md）。
- `scripts/run_all_migrations.sh`（1038行）:
  - :25 `PSQL="psql -U jarvis -d jarvis_db -v ON_ERROR_STOP=1"`。lock_timeout 指定なし。
  - :47 TOTAL は `^run_(sql|py)` 行を数える。
  - :49-59 run_py（backend コンテナで python。asyncpg）。
  - :62-87 run_sql。`docker exec -i "${POSTGRES}" ${PSQL} < file`。"deadlock detected" のときだけ最大3回・5秒あけて流し直す（c072445cf、10/20）。lock timeout は再試行しない。
  - :108-127 EXIT trap（ai_ro ビュー作成。失敗してもデプロイは続行）。
- DB・ロール・compose・アプリ接続（`backend/app/database.py:13-31`）のどこにも lock_timeout / statement_timeout は無い。例外は ai_reader ロール（`migrations/20261017_130000_create_ai_reader_role.sql:26-27`）と、SET LOCAL を持つ 8 ファイル（§5）。
- migrations の冪等性: CI `.github/workflows/migration-test.yml:1828-1839` が `scripts/migration-dryrun-report.py run --rounds 2` で全件を2周流す（2周目＝再実行が通ることの確認）。同 :1759-1826 は run_sql 関数を使わず独自ループで psql -f。

## 3. 遅くなった時間帯と原因（事実）
- 在庫表 GET（Prometheus `http_request_duration_seconds`, handler="/api/v1/inventory"）: 10/18 22:42Z〜10/21 07:21Z で約221件、1秒以内 68.3%、平均 1.64秒、10秒超 約6件。生出力: /tmp/CC報告ファイル/inventory-speed/remeasure-1021/out.txt
- 遅い時間帯A: 10/19 02:16〜02:22Z。run 39187571868（#4526 attempt 2）の移行ステップ 02:14:03〜02:21:19 と重なる。平均 1.7〜13.5秒。02:19:26Z に DROP と deadlock し、在庫表の SQL が負けて 500。attempt 1 でも 02:08:20Z に同じ DROP が `SELECT id FROM public.products WHERE is_active = TRUE` と deadlock。生出力: /tmp/CC報告ファイル/inventory-speed/slow-cause-1021/
- 遅い時間帯B: 10/19 18:38〜18:51Z、再解析（80投稿）実行中。平均 1.2〜1.6秒。原因は【未確認】（今回の対象外）。
- 直近300回の deploy の失敗8回のうち移行ステップが7回（deadlock 3回・CHECK 違反4回）。deadlock は計4件（attempt 1 で落ち再実行で通った1件を含む）。うち3件が `DROP TABLE IF EXISTS public.parse_logs`、1件が `migrations/20261017_120000_line_conditions_value_rank.sql` の CREATE OR REPLACE VIEW public.conditions。4件とも run_sql 経由。
- parse_logs は毎回作られて毎回消される: `migrations/20260604_120000_create_parse_logs.sql`（products 等へ FK）→ 約300本後の `migrations/20261002_170000_drop_discord_inventory_tables.sql:26-29`（`scripts/run_all_migrations.sh:924`）。

## 4. 試験用 DB での再現（事実）
- 試験: `tests/sandbox/lock-timeout-repro.sh`（7314c23f7）。GitHub sandbox-test run 39570551782（success）。生ログ: /tmp/CC報告ファイル/migration-lock-timeout/repro/run-log.txt
- 基準: 読み取り C は 78〜80ms。
- 試験1（今の形）: A が products を読んでいる間、B（本物の DROP の migration ファイル）は **products** の AccessExclusiveLock を待ち 11084ms。後から来た C は 8912ms 待たされた。→ parse_logs を消すと FK 先の products に最強のロックを取りに行き、待っている間は後続の読み取りも全部止まる。
- 試験2（`docker exec -e PGOPTIONS='-c lock_timeout=1s'`）: B は 1085ms で `ERROR:  canceling statement due to lock timeout`（rc 3）、parse_logs は残る。C は 78ms（ただし B が諦めた後に測った。B が待っている1秒の間の C は未測定）。
- 試験3: A が終わった後に B を流し直すと 84ms で成功し parse_logs は消えた。
- PostgreSQL 16 公式文書（Context7 は月間上限で使えず、公式を直接確認）: lock_timeout はロック取得を待つ時間の上限で、超えた文を中止する。postgresql.conf 全体での設定は非推奨で、セッション・ロール・トランザクション単位が推奨。PGOPTIONS は接続パラメータ options と同じ働き。

## 5. 範囲の判断に要る事実
- run_py 26本のうち 20本は SQL ファイルを読んで asyncpg で流す。Python 内で直接 DDL を書くのは `scripts/migrate_074_rename_english_name_to_nickname.py:87` のみ。観測した deadlock 4件はすべて run_sql 側（§3）。生出力: /tmp/CC報告ファイル/migration-lock-timeout/recon3/notes.md
- `SET LOCAL lock_timeout = '5s'` を持つ 8 ファイル（すべて BEGIN〜COMMIT 内）:
  `migrations/20260910_180000_tcg_interrupted_jobs_recovery_t004.sql:3`、`migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:3`、`migrations/20260913_150000_tcg_empty_box_condition.sql:3`、`migrations/20260913_200000_tcg_cardset_exclusion.sql:5`、`migrations/20260913_210000_tcg_cardset_bundle_registration.sql:5`、`migrations/20260914_010000_tcg_extraction_attempts.sql:3`、`migrations/20260915_010000_drop_tcg_products_phase2c.sql:4`（:86 に DROP TABLE）、`migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:9`（:98/:193/:299 に DROP COLUMN）。
- deadlock_timeout の設定は0件（既定1秒）。
- sandbox-test: `.github/workflows/sandbox-test.yml`、`gh workflow run sandbox-test.yml --ref <ブランチ> -f test=<名前>`（`tests/sandbox/README.md:9`）。60分・使い捨て・secrets/本番データ禁止。
