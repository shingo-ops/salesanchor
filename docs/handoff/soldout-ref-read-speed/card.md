# 実装カード — 「売り切れの参照」の 2 つの読み取り SQL を速い形に書き換える

- 設計: docs/handoff/soldout-ref-read-speed/design.md（§3 C1〜C3・§6 K4）・recon.md
- PO 承認: 2026-11-10 PO「1」（設計どおりに実装する）
- 起点: origin/main ecb0fa6fd。作業枝 release/soldout-ref-impl（このカードはこの枝の先頭の commit にある）
- 触るファイル（これ以外は触らない）:
  - backend/app/services/line_analysis_v102_svc.py（`_STOCK_ITEMS_SQL` と `_SOLD_ITEMS_SQL` の 2 つの文字列だけ）
  - backend/tests/test_gemini_raw_copy_v102_soldout_ref.py（足すだけ）
  - backend/tests/test_line_analysis_v102_svc.py（足すだけ）
  - .claude-pipeline/active-work.d/release-soldout-ref-impl.md（台帳。状態の行だけ）
- 読んだ節（docs/handoff/design-partner-card-ops/guards/）と照合:
  - guards/00-common.md: 手順のコマンドは作業台のフルパスへの cd から始める。出力には tail を付ける。push や commit は git log で実在を確かめてから報告する。
  - guards/03-file.md: 書き換えは「変更前の全文」を逐語で目印にして、2 か所を 1 つずつ置き換える。目印が見つからなければ停止する。
  - guards/04-worktree.md: 作業台は scripts/new-worktree.sh で作る。push は git push -u origin HEAD を単独で流す。
- 受領確認: 着手の前に、作業枝の HEAD がクラウドへの依頼文に書いた sha と同じかを確かめ、最初の報告の行に書く。違えば停止して BLOCKED: で報告する。
- 停止の報告: 迷った・目印が無い・想定外の失敗が出たときは、その場で停止し、BLOCKED: か NEEDS_DECISION: で始まる最後の報告に生の出力を貼る。推測で進めない。
- 触らない: `_INHERIT_PRICE_SQL`（同じファイルの :1364 付近にも `j2.source_message_id = ej.source_message_id` があるが、対象外。設計 §2）・`_load_stock_items`・`_load_sold_items`・行を組む関数・migrations/・deploy.yml・scripts/・frontend/・ほかの全部

## 1. backend/app/services/line_analysis_v102_svc.py

origin/main ecb0fa6fd で `_STOCK_ITEMS_SQL` は :1424、`_SOLD_ITEMS_SQL` は :1440 から。行番号でなく下の文を目印にする。

### 1-1. `_STOCK_ITEMS_SQL` を次の全文に置き換える（変わるのは FROM の 1 行目と WHERE の最初の 3 行だけ）

変更前（今の全文）:

```python
_STOCK_ITEMS_SQL = """
    SELECT ej.source_message_id, ei.source_lines, ei.line_start, ei.line_end, ar.product_id, ar.condition_id,
           COALESCE(ar.condition_canonical, '') AS condition_canonical,
           ar.unit_id, COALESCE(ar.unit_canonical, '') AS unit_canonical
    FROM {schema}.extraction_jobs ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ej.source_message_id = ANY(CAST(:ids AS uuid[]))
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
      AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
      AND ar.status IS DISTINCT FROM :sold_out
    ORDER BY ej.source_message_id, ei.line_start NULLS LAST, ei.gemini_index NULLS LAST, ei.id
"""
```

変更後（全文）:

```python
_STOCK_ITEMS_SQL = """
    SELECT ej.source_message_id, ei.source_lines, ei.line_start, ei.line_end, ar.product_id, ar.condition_id,
           COALESCE(ar.condition_canonical, '') AS condition_canonical,
           ar.unit_id, COALESCE(ar.unit_canonical, '') AS unit_canonical
    FROM (SELECT DISTINCT ON (j.source_message_id) j.id, j.source_message_id FROM {schema}.extraction_jobs j
          WHERE j.source_message_id = ANY(CAST(:ids AS uuid[]))
          ORDER BY j.source_message_id, j.created_at DESC, j.id DESC) ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
      AND ar.status IS DISTINCT FROM :sold_out
    ORDER BY ej.source_message_id, ei.line_start NULLS LAST, ei.gemini_index NULLS LAST, ei.id
"""
```

### 1-2. `_SOLD_ITEMS_SQL` を次の全文に置き換える

変更前（今の全文）:

```python
_SOLD_ITEMS_SQL = """
    SELECT ej.source_message_id, ar.product_id, COALESCE(ar.condition_canonical, '') AS condition_canonical
    FROM {schema}.extraction_jobs ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ej.source_message_id = ANY(CAST(:ids AS uuid[]))
      AND ej.id = (SELECT j2.id FROM {schema}.extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id
                   ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)
      AND ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
      AND ar.status = :sold_out
    ORDER BY ej.source_message_id, ei.line_start NULLS LAST, ei.gemini_index NULLS LAST, ei.id
"""
```

変更後（全文）:

```python
_SOLD_ITEMS_SQL = """
    SELECT ej.source_message_id, ar.product_id, COALESCE(ar.condition_canonical, '') AS condition_canonical
    FROM (SELECT DISTINCT ON (j.source_message_id) j.id, j.source_message_id FROM {schema}.extraction_jobs j
          WHERE j.source_message_id = ANY(CAST(:ids AS uuid[]))
          ORDER BY j.source_message_id, j.created_at DESC, j.id DESC) ej
    JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
    JOIN {schema}.analysis_results ar ON ar.extraction_item_id = ei.id
    WHERE ar.pid_resolved = TRUE AND ar.product_id IS NOT NULL AND ar.condition_id IS NOT NULL
      AND ar.status = :sold_out
    ORDER BY ej.source_message_id, ei.line_start NULLS LAST, ei.gemini_index NULLS LAST, ei.id
"""
```

- 「変更前」の全文がファイルの中に 1 か所ずつ文字どおり無いときは、書き換えずに BLOCKED:（見つかった今の文を貼る）。

## 2. backend/tests/test_gemini_raw_copy_v102_soldout_ref.py（足すだけ）

`test_sold_items_and_stock_items_are_read_apart_from_the_latest_job_with_resolved_products` の関数の直後（`def test_unknown_job_returns_empty` の前）に、次の 2 つの試験を足す。同じファイルの `_insert`・`_job`・`_load`・`_add_result`・`seed_products`・`T0`・`SCHEMA`・`pg`・`channel` を使う（今ある試験と同じ準備の形）。

### 2-1. test_same_created_at_jobs_read_only_the_larger_id_job

- `seed_products(pg[0])`。商品を 2 つ（p1, p2。今の試験と同じ `SELECT id FROM public.products ORDER BY id LIMIT 2`）、状態 'Case' と 'Sealed box' の id を取る（今の試験と同じ文）。
- 参照される投稿 post を `_insert(pg[0], channel, "前", T0 - timedelta(hours=2))` で作る。
- job を 2 つ、同じ created_at で作る。id は `small, large = sorted([str(uuid4()), str(uuid4())])`（uuid の文字の順は PostgreSQL の uuid の比べ方と同じ）。INSERT は今の試験と同じ文で、age は 2 つとも `'0 seconds'` ではなく、同じ時刻を確実にするため `created_at` を同じ値にする: `INSERT INTO {SCHEMA}.extraction_jobs(id,source_message_id,status,created_at) VALUES (%s,%s,'done',%s)` に同じ `T0 - timedelta(hours=1)` を渡す。
- small の job に `_add_result(pg[0], small, 0, p2, case, "Case", "Sold out")` と `_add_result(pg[0], small, 1, p2, box, "Sealed box", "In Stock")`。
- large の job に `_add_result(pg[0], large, 0, p1, case, "Case", "Sold out")` と `_add_result(pg[0], large, 1, p1, box, "Sealed box", "In Stock")`。
- `job = _job(pg[0], _insert(pg[0], channel, "今", T0))`、`(loaded,) = _load(pg, job)`。
- 確かめる: `loaded.sold_items == (sr.SoldItem(p1, "Case"),)` と `[(it.product_id, it.condition_canonical) for it in loaded.stock_items] == [(p1, "Sealed box")]`（large だけを読む・stock と sold の両方）。

### 2-2. test_two_reference_posts_each_read_their_own_latest_job_in_post_order

- 準備は 2-1 と同じ（p1, p2, case, box）。
- 参照される投稿を 2 つ: `post_a = _insert(pg[0], channel, "前A", T0 - timedelta(hours=3))`、`post_b = _insert(pg[0], channel, "前B", T0 - timedelta(hours=2))`。
- それぞれに古い job（`now() - '1 hour'`）と最新の job（`now() - '0 seconds'`）を、今の試験と同じ INSERT の文で作る。
- 古い job にはそれぞれ `_add_result(..., 0, p2, box, "Sealed box", "In Stock")`（読まれてはいけない）。
- post_a の最新の job に `_add_result(..., 0, p1, box, "Sealed box", "In Stock")` と `_add_result(..., 1, p1, case, "Case", "Sold out")`。
- post_b の最新の job に `_add_result(..., 0, p2, case, "Case", "In Stock")` と `_add_result(..., 1, p2, box, "Sealed box", "In Stock")`。
- `job = _job(pg[0], _insert(pg[0], channel, "今", T0))`、`loaded = _load(pg, job)`。
- 確かめる:
  - `len(loaded) == 2`。
  - 投稿ごとに（`{p.message_id: p for p in loaded}` で引く。`message_id` の文字は `str(post_a)`・`str(post_b)` と比べる）:
    - post_a: `sold_items == (sr.SoldItem(p1, "Case"),)`、`[(it.product_id, it.condition_canonical) for it in stock_items] == [(p1, "Sealed box")]`。
    - post_b: `sold_items == ()`、`[(it.product_id, it.condition_canonical) for it in stock_items] == [(p2, "Case"), (p2, "Sealed box")]`（行の順 = line_start の順。古い job の行が混ざらない）。
- `_load` が返す投稿の並び順は、この関数の外（sr 側）が決めるので、並び順そのものは確かめない（2 つあることと中身だけ）。

- 名前の確かめ: `SoldoutRefPost` の投稿 id の属性名が `message_id` でない、または `_load` が上の形で使えないときは、書き換えずに NEEDS_DECISION:（今の定義を貼る）。今ある試験 :392-400 付近の `[p.message_id for p in _load(pg, job)]` が目印。

## 3. backend/tests/test_line_analysis_v102_svc.py（足すだけ）

`def test_stock_items_sql_reads_the_unit_columns():` の関数の直後に次を足す（DB は使わない）:

```python
def test_soldout_ref_sqls_pick_the_latest_job_with_distinct_on_not_a_correlated_subquery():
    # 設計 docs/handoff/soldout-ref-read-speed/design.md C3-3：遅い形（投稿ごとの副問い合わせ）に戻すと赤になる
    for sql in (svc._STOCK_ITEMS_SQL, svc._SOLD_ITEMS_SQL):
        assert "j2.source_message_id = ej.source_message_id" not in sql
        assert "DISTINCT ON (j.source_message_id)" in sql
        assert "ORDER BY j.source_message_id, j.created_at DESC, j.id DESC" in sql
```

## 4. 台帳 .claude-pipeline/active-work.d/release-soldout-ref-impl.md

このカードと同じ commit に Opus が作ってある。Sonnet は触らない（PR 番号は Opus が書く）。

## 5. 完了の確かめ（Sonnet が流して生の出力を報告に貼る）

- 依存: `cd backend && /usr/bin/python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`（見つからなければ BLOCKED:）。
- `cd backend && .venv/bin/python -m pytest tests/test_line_analysis_v102_svc.py tests/test_gemini_raw_copy_v102_soldout_ref.py -q --no-cov`
  - 本物の PostgreSQL を使う試験（`pg` を使うもの）は、DB が無い箱では `RLS_ADMIN_DATABASE_URL required` の assert でエラーになる。これは環境のせいなので可。エラーになった試験の名前と最後の行を書く（CI で流す）。それ以外の失敗が残れば NEEDS_DECISION: で生の出力。
- `cd backend && .venv/bin/ruff check app/services/line_analysis_v102_svc.py tests/test_line_analysis_v102_svc.py tests/test_gemini_raw_copy_v102_soldout_ref.py`
- `git diff origin/main --stat` が上の「触るファイル」のうち 3 つのコード・試験と、このカードと台帳だけ。

## 6. 想定の分かれ道

- 「変更前」の全文が見つからない・2 か所ある → BLOCKED:。
- ruff が行の長さを指摘 → SQL の文字列の中は直さない（今の文と同じ長さの行）。指摘が SQL の文字列の外なら ruff のとおりに直す。SQL の中なら NEEDS_DECISION:。
- 試験 2-1・2-2 の準備で、今ある補助の関数の引数の形が違う → 今ある試験の呼び方に合わせる。合わせられなければ NEEDS_DECISION:。
- 完了の報告は DONE / BLOCKED: / NEEDS_DECISION: のどれかで始める。

END OF CARD
