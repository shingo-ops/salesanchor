# 実装カード SP: 同じ投稿の同じ商品の行（便SP）

設計者: Opus（2026-10-12）。設計: design.md（§3 変更前後・§7 受入条件）。recon: recon.md。
worktree: /Users/tanizawashingo/worktrees/salesanchor/release-v102-same-post-rows（ブランチ release/v102-same-post-rows、origin/main 81f3f5869 起点）。

## 0. 着手前の確認（違えば NEEDS_DECISION で止まる）
0-1. `./scripts/dev/executor-preflight.sh`。`git pull --ff-only origin main` で最新に。
   次の file:line が recon.md と同じであることを確かめる。ずれていたら実物の行を使い、報告に書く。
   - backend/app/services/tcg_analyzer_svc.py:1744-1860
   - backend/app/services/tcg_distribution_svc.py:224-371
0-2. condition_basis の値（例 "R2:状態A-"）がどこで作られるかを file:line で示す。語が状態の規則マスタ（DB の表）から来ることを確かめる。
   - コードに直接書かれた語の一覧から来ているなら、止まる。
0-3. extraction_jobs の id 列の型を確かめる（uuid か）。大小比較で順位を決めてよいかも確かめる。

## 1. is_current（tcg_analyzer_svc.py `_merge_supplier_products` の ranked だけを変える）
- touched_triples・candidates・UPDATE の形は変えない。
- candidates の2つの SELECT（本物の行と仮の行）に、投稿の識別子 `ej.id AS job_id` を足す。仮の行は親の行の投稿。
- ranked を次の考え方に置き換える。
  1. job_rank: 組（product_id, condition_id）と job_id ごとに、received_at と max(computed_at) を出す。
  2. top_job: 組ごとに `DISTINCT ON (product_id, condition_id)` で1つを選ぶ。順は `received_at DESC, max_computed_at DESC, job_id DESC`。
  3. should_be_current = (c.job_id = top_job.job_id)。
- docstring とコメントを「組ごとに最新の投稿を1つ決め、その投稿の組の行をすべて現在の行にする（ADR-158:26）」に直す。
- 旧の `(c.id IS NULL)` の並び鍵は要らなくなる。仮の行は UPDATE の対象外のまま。

## 2. 配信のまとめ方（tcg_distribution_svc.py）
- 配信行を作る SQL を、1つの関数（例 `_output_rows_sql(cond_filter, age_condition) -> str`）にまとめる。
  - `fetch_output_rows` はその SQL の行を、`fetch_preview_data` の output_count はその SQL の行数（`SELECT COUNT(*) FROM (<同じSQL>) x`）を使う。
  - 件数の SQL を別に持たない。今の :354-371 の件数専用の SQL は、この共通の SQL に置き換える。
- SQL の形:
  - base: 今の SELECT（同じ JOIN・同じ WHERE）。今の13列に加えて次を出す。
    - ej.id AS job_id, ar.product_id, ar.condition_id, ar.unit_canonical
    - COALESCE(ar.note_ja,'') AS note_key
    - ar.status AS status_key（COALESCE 前の値でよい）
    - ar.condition_basis
    - ar.price_normalized AS price_num, ar.quantity_normalized AS qty_num
    - `ROW_NUMBER() OVER (ORDER BY {result_order_sql()}) AS ord`
  - grp: base を窓関数で調べる。鍵は (job_id, product_id, condition_id, unit_canonical, note_key, status_key)。次を出す。
    - n = count(*)
    - nb = count(DISTINCT condition_basis)
    - nbn = count(condition_basis)
    - nqn = count(qty_num)
    - mergeable = (n > 1 AND nb = n AND nbn = n AND nqn = n)
  - 出力
    - mergeable の組は1行にする。unit_price は ROUND(MAX(price_num))、quantity は ROUND(SUM(qty_num))。ほかの11列は組で同じ値を使う（min() など、どれを取っても同じ）。並びは min(ord)。
    - mergeable でない行は、今の値のまま1行ずつ出す。並びは ord。
    - 最後に並び順で ORDER BY する。出力の列と順と書式（文字列化）は、今の13列と同じにする。
- ランクの語・状態名をコードに書かない（判定は condition_basis が違うかどうかだけ）。

## 3. テスト
- is_current（既存の _merge_supplier_products のテストに追加。無ければ PostgreSQL のテストの作法で新しく作る）:
  - 同じ投稿の同じ組が2行 → 2行とも TRUE
  - より新しい投稿があれば、古い投稿の2行は FALSE
  - 同じ received_at・computed_at の2投稿 → job id の大きい方が TRUE
  - 2回続けて呼んでも結果が同じ
  - 既存の仮の行（〆）のテストがすべて通る
- 配信（tests/test_tcg_condition_review.py か test_line_analysis_v102_pg.py の PostgreSQL の作法）:
  - N（note 違い）→ 2行
  - R（同じ note・basis 違い）→ 1行。数量が合計・価格が最大
  - S（basis 同じ）→ 2行
  - R でも数量 NULL の行がある → 2行
  - output_count が fetch_output_rows の行数と一致する
  - まとめない行の並び順が今と同じ

## 4. 置き換え試験（マージ前、本番は読み取りだけ）
`bash /tmp/CC報告ファイル/v102-kw-kenpin/runf.sh <sql> <out> ro` で、本番の今のデータに次をかける。
- SQL 内にダブルクォート・$ を使わない。
- 既定で ro。書き込みは禁止。

4-1. 新しい is_current を SELECT で計算する（UPDATE しない）。対象は v102 の全行（pid_resolved かつ product_id あり）。仕入元ごとに組を作る。
   出すもの:
   - 今 FALSE → 新 TRUE の行数
   - 今 TRUE → 新 FALSE の行数と全件。許されるのは、同じ received_at の別の投稿に勝ちが移る場合（重複投稿）だけ。それぞれについて、移った先の行と値が同じかどうかを示す
   - recon §5 の N・R・S の組での出方
4-2. 新しい is_current で、配信の SQL（max_age_hours は本番の設定値。distribution 設定の表から読む）の行数を、今の配信の行数と比べる。差の内訳も出す（増えた行・まとまった組）。
   さらに、投稿 0b32f3e7 の pid 440301、d5af1992 の pid 112 の出力行を示す。
4-3. 相場の確認（v102_unit_price_check_svc.py:62）の中央値が、新しい is_current で変わる組の数と、その組で要確認の判定が変わる行の数を示す。関数を本番の写しの値で呼んで確かめる。
出力: /tmp/CC報告ファイル/same-post-rows/test/。原文は含めない。含む場合は社外秘として手元だけに置く。

## 5. 手順
1. 0 → 実装 → テスト → ruff・pytest（backend の該当テストと tcg_distribution・line_analysis_v102・tcg_condition_review の全部）。frontend は変えない。
2. 4 の置き換え試験。
3. commit（push しない）。このカードと設計書は設計者が置いたもの。必要なら差分を足す。

## 停止条件
- 0 の前提が違う
- 今 TRUE → 新 FALSE に、同じ received_at の重複投稿以外の行がある
- 解析の値の列を変える必要が出た
- テストを書き換えないと既存のテストが通らない

これらに当たったら NEEDS_DECISION で止まる。フックに止められたら、言い換えて再試行せずに止まる。最終行は DONE / BLOCKED: / NEEDS_DECISION: のいずれか。
