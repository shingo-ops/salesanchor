# recon — 「売り切れの参照」の読み取りが 1 投稿あたり約 1 秒かかる件

- 調べた日: 2026-11-10（JST）。行番号は origin/main 11838e9d0。
- 調べた人: Claude Opus（設計担当）。本番は読むだけ（prod1 の別の箱で、取引を READ ONLY にした Python から SELECT と EXPLAIN だけ）。
- きっかけ: docs/handoff/replay-tx-release/design.md の P4 で K2（1 投稿の読み取りの最長が 1 秒未満）が ×（最大 1129 ms、1000 ms 以上が 5 件）。PO が「2」（この読み取りを速くする設計）を選んだ。
- 生出力（手元の写し）: scratchpad/replay-tx/p5/p5.json・p5_jit.json・p5_rewrite.json・p5_inherit.json・各 stdout/stderr。prod1 の /home/ubuntu/fhd-test/replaytx/p5/ に同じ物。

## 0. 既存 ADR・設計の検索

- `git grep -il "jit" origin/main -- docs/adr` と `git grep -il "source_message_id" origin/main -- docs/adr migrations` で、JIT の設定・この 2 つの索引を決めた ADR と移行は見つからなかった。
- 関係する決まり: ADR-1037（移行の鍵待ち 1 秒）・ADR-1070（接続の返却時の後始末）・docs/handoff/replay-tx-release/design.md（試しの道具の取引）。どれもこの SQL の形は扱っていない。
- `git show origin/main:docs/adr/FEATURE-INDEX.md | grep -i "〆\|soldout\|LINE解析\|line_analysis"` は 0 件。〆の参照の規則（規則 11・12）はコードの説明（:1463・:1481 の docstring）にある。この設計は読む行の中身を変えない（§3 で一致を確かめた）。
- 既存の索引の移行は extraction_attempts など別の表だけ（`git grep -n "ix_extraction\|idx_extraction" origin/main -- migrations`）。extraction_items・extraction_jobs への索引の移行は無い。

## 1. どこが遅いか（事実・本番の実測）

### 1-1. 1 投稿の読み取りの内訳（p5.json・20 投稿）

- `load_soldout_ref_posts` だけが遅い: 参照する投稿が 1 件以上ある 15 投稿すべてで 913〜2297 ms。ほかの段はどれも 70 ms 以下。参照が 0 件の 5 投稿は合計 18〜71 ms。
- 中の 3 つの SQL: `_SOLDOUT_REF_POSTS_SQL` 0.7 ms／`_STOCK_ITEMS_SQL` 1098 ms（296 行）／`_SOLD_ITEMS_SQL` 1009 ms（0 行）（最初の遅い投稿の例）。

### 1-2. 場所（行番号）

- `backend/app/services/line_analysis_v102_svc.py:1327-1345` load_soldout_ref_posts。:1341 で `_load_stock_items` と `_load_sold_items` を呼ぶ。
- `backend/app/services/line_analysis_v102_svc.py:1424-1437` `_STOCK_ITEMS_SQL`、`:1440-1451` `_SOLD_ITEMS_SQL`。どちらも :1432-1433・:1446-1447 に「その投稿の最新の job」を選ぶ相関副問い合わせ:
  `AND ej.id = (SELECT j2.id FROM extraction_jobs j2 WHERE j2.source_message_id = ej.source_message_id ORDER BY j2.created_at DESC, j2.id DESC LIMIT 1)`
- `backend/app/services/line_analysis_v102_svc.py:1463-1478` `_load_stock_items`、`:1481-1491` `_load_sold_items`（SQL を流して行を組むだけ）。

### 1-3. 呼び出し元（全部）

- 本番の解析: `backend/app/services/line_analysis_v102_svc.py:1567`（run_v102_analysis の中。:1539 で投稿ごとの鍵 pg_advisory_xact_lock を取った同じ取引の中。:1572 で commit）。
- 試しの道具: `backend/app/tools/v102_replay_diff.py`（replay_post）・`backend/app/tools/prompt_ab_recompute.py`。
- 〆の参照の本体: `backend/app/services/gemini_raw_copy_v102_soldout_ref.py`（読んだ結果を使うだけ。SQL は持たない）。
- `git grep -n "_STOCK_ITEMS_SQL\|_SOLD_ITEMS_SQL\|_load_stock_items\|_load_sold_items" origin/main -- backend` の結果は上の場所と試験 2 か所（§5）だけ。

### 1-4. なぜ遅いか（EXPLAIN (ANALYZE, BUFFERS)・p5.json と p5_jit.json）

- 今の形の見積もりの費用は 1,219,003。PostgreSQL 16.13 の設定は jit=on・jit_above_cost=100000・jit_inline_above_cost=500000・jit_optimize_above_cost=500000（pg_settings、既定のまま）。見積もりが 3 つの境目を全部越えるので、JIT（問い合わせごとの機械語への翻訳）・inline・最適化が全部走る。
- JIT ありの 1 回: 実行 875.966 ms のうち JIT が 759.593 ms（Inlining 64・Optimization 411・Emission 281）。
- 見積もりが大きい理由: 相関副問い合わせが extraction_jobs（5,229 行）を毎回 Seq Scan する見積もり（1 回 316）で、それが外側の行の数だけ掛かる。実際に回るのは 10 回（loops=10）だけ。
- 索引: extraction_items は主キーだけ（extraction_job_id の索引なし）。extraction_jobs も主キーだけ（source_message_id の索引なし）。行数は analysis_results 92,259・extraction_items 93,210・extraction_jobs 5,229・source_messages 5,229。

## 2. JIT を止めると速くなるか（p5_jit.json・15 投稿×2 つの SQL×3 回ずつ）

| SQL | JIT あり（今） | `SET LOCAL jit = off` | 行の一致 |
|---|---|---|---|
| 在庫の行（stock） | 374.7〜531.1 ms | 42.7〜62.2 ms | 15 投稿とも 6 回の結果が全部同じ（計 999 行） |
| 売り切れの行（sold） | 415.3〜562.1 ms | 53.3〜101.4 ms | 同上（計 174 行） |

- JIT なしの計画（最初の投稿）: 実行 69.936 ms。残りの時間の大半は extraction_items 93,210 行の Seq Scan と、その行ごとの Memoize（ヒット 88,364・ミス 4,846）。

## 3. 問い合わせの形を直すと速くなるか（p5_rewrite.json・15 投稿×2 つの SQL×3 回ずつ）

書き換え案: 相関副問い合わせをやめ、FROM の extraction_jobs を「:ids の投稿ごとに最新の job を 1 つだけ選ぶ」副問い合わせに置き換える。

```sql
FROM (SELECT DISTINCT ON (j.source_message_id) j.id, j.source_message_id FROM {schema}.extraction_jobs j
      WHERE j.source_message_id = ANY(CAST(:ids AS uuid[]))
      ORDER BY j.source_message_id, j.created_at DESC, j.id DESC) ej
JOIN {schema}.extraction_items ei ON ei.extraction_job_id = ej.id
```

| SQL | 今の形（JIT あり） | 書き換え（設定はそのまま） | 行と順番の一致 | 書き換えの計画に JIT |
|---|---|---|---|---|
| stock | 387.8〜1106.7 ms | 14.9〜84.8 ms | 15 投稿とも 6 回が全部同じ（計 999 行・順番も） | 0 / 15 |
| sold | 433.3〜1378.3 ms | 15.3〜79.8 ms | 同上（計 174 行・順番も） | 0 / 15 |

- 書き換えの見積もりの費用は 3,318〜3,412（境目 100,000 の 1/29 以下）なので JIT は走らない。
- 今の形の時間は §2 の回（374〜562 ms）と §3 の回（387〜1378 ms）で違う。同じ SQL・同じ投稿でも回によって 2 倍ほど振れる。振れの原因は確かめていない（§6）。書き換えはどちらの回でも 85 ms 以下。
- 同じ意味になる理由（紙の上の確かめ）: 今の形は「:ids の投稿の job のうち、その投稿の job を created_at の新しい順・id の大きい順に並べた先頭と同じ id のもの」。書き換えは「:ids の投稿ごとに、同じ並べ方の先頭 1 つ」。並べ方（created_at DESC, id DESC）が同じで、id は主キーなので同点が無い。created_at が NULL の行の扱い（DESC で先頭）も同じ式なので同じ。外側の ORDER BY（:1436・:1450）は変えない。

## 4. 同じ形のほかの SQL（p5_inherit.json）

- `_INHERIT_PRICE_SQL`（`backend/app/services/line_analysis_v102_svc.py:1350-1367`、前の価格の引き継ぎ）にも同じ相関副問い合わせ（:1364-1365）がある。本番の解析で、価格なし・数ありの件ごとに呼ばれる（:1376 から `_inherit_price`）。
- 20 投稿それぞれの最初の決まった件の値で流すと 1.3〜2337.9 ms。JIT が付いたのは 14 / 20。JIT なしでも 300 ms を超える回がある（f74bc117 329.9 ms・6cfb2f5a 387.0 ms）。
- 本番の解析で 1 投稿あたり何回呼ばれているかは確かめていない（数える SELECT を本番で流そうとして、見張り psql-write-guard に止められた。言い換えて流し直していない）。→ この設計では扱わず、次の段で測ってから設計する（design §2・§9）。

## 5. 今ある試験

- `backend/tests/test_line_analysis_v102_svc.py:1044-1046` `_STOCK_ITEMS_SQL` に単位の列があること（文字列の確かめ）。
- `backend/tests/test_line_analysis_v102_svc.py:1049-1063` `_load_stock_items` が行を組むこと（DB を使わない偽物）。
- `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py:389-464` CI の使い捨て PostgreSQL で load_soldout_ref_posts を流す試験。:438 は「古い job と最新の job があるとき、最新の job の結果だけを読む」ことを確かめている（created_at を 1 時間ずらす）。created_at が同じで id だけ違う場合の試験は無い。

## 6. 未確認

- 今の形の時間が回によって約 2 倍振れる原因（同じ時間帯に動いていた本番の作業との重なりか）。書き換え後はどちらの回でも 85 ms 以下なので、この設計の成否には効かない。
- `_INHERIT_PRICE_SQL` の本番での呼ばれる回数（§4）。
- 書き換えで一致を確かめたのは 15 投稿（行 1,173）。全投稿での一致は実装後の P3（design §5・§6 K3）で 20 投稿の結果の比べで確かめる。
