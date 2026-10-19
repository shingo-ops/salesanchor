---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 価格のない〆・完売の行を要確認に出さない

> この文書は何か: 相手の在庫が既に在庫表から消えている「価格のない〆・完売」の行を、要確認一覧から外す設計書。取り違えが疑われる行は残す。
> 親: docs/handoff/v102-shime-same-post-stock/design.md（規則13。〆を在庫の件に効かせる側）

**対象ADR**: ADR-158（関連・変更しない。要確認の理由を定める ADR は無い。recon §0。§9）  
**recon**: docs/handoff/shime-review-exclude/recon.md  
**日付**: 2026-10-19  
**担当**: Planner（Opus）。状態: 設計審査済み（2回目 APPROVE）・PO 実装承認済み（2026-10-19「1」）・実装 PR #4535・T3 不合格を受け §4-5 を改訂し再審査 APPROVE（§11-5）・#4535 マージ（2640ae932）・本番反映済み（2026-10-19、G1〜G5 合格、§11-7）  
**ADR-1015 の区分**: A（要確認の判定に新しい規則を足す）。DB の列・migration・本番データの書き換えは無い

---

## 1. 目的と成功条件（KGI、PO 承認済み 2026-10-19）

PO の言葉: 「カードセット〆切 Hironobu Yasukawaさんのこの情報が要確認に回っているのでまだ完全には〆を対応処理できていない」。Opus の KGI 案（直近7日の価格なし〆・完売 45 行のうち 35 行を要確認から外し 10 行を残す。〆と完売は同じ扱い）に PO「y」。

| # | 合格の条件（○×） |
|---|---|
| G1 | 安川さんの〆（item c838f466）が要確認一覧に出ない |
| G2 | 直近7日の価格なし〆・完売のうち、§3 の4条件をすべて満たす行（設計時点 35 行）が要確認から消え、それ以外（設計時点 10 行）は残る |
| G3 | 相手の在庫が無い行（設計時点 8 行。例 f364283f）は残る |
| G4 | 相手の商品の在庫が在庫表にまだ出ている行（設計時点 2 行。例 044ba439）は残る |
| G5 | 価格のある行・ほかの理由のある行の要確認は1行も変わらない。在庫表（配信行）は1行も変わらない |

件数は時刻で動く（48 時間が過ぎると丙が甲になる、新しい投稿が入る）。そのため G2〜G5 は「同じ時刻に変更前と変更後の判定を並べて比べる」方法で確かめる（§7）。

## 2. 対象と対象外

対象
- `backend/app/services/tcg_condition_review_svc.py` の review_joins に「〆の確認済み扱い」(cr_shime) を1つ足し、それが真の行では price_unresolved と excluded を理由に入れない
- 試験の追加（`backend/tests/test_tcg_condition_review.py`）
- fenced の文字列検査の期待数（`backend/tests/test_tcg_condition_review_fenced.py:29` の 2→3、:41 の 2+5+2→3+5+2）。cr_shime に OFFSET 0 を足すため

対象外（触らない）
- 在庫表・GAS・配信プレビューの WHERE（§4-5 の review_joins の呼び出しに shime=False を足す3か所を除く。`backend/app/services/tcg_distribution_svc.py:367-375`・:481-489）。〆の行は価格 NULL・excluded・Sold out なので、要確認かどうかに関係なく在庫表に出ない（同:370、:372、:375）
- 解析（v102）の保存値・ar.needs_review・ar.review_reasons。ダッシュボードの件数（ar.needs_review を数える）は v102 の行では変わらない。例外として、旧エンジンの再解析（`backend/app/services/tcg_analyzer_svc.py:1801`）が甲に当たる行を再解析した場合だけ、保存値の needs_review・review_reasons が新しい規則の値になる（§6）
- 「このままで良い」(review_ack) の仕組み
- 価格のある行、保存済みの理由がある行（20f9cb54 のような状態不明は残る）
- 画面（frontend）。行が一覧から消えるだけ

## 3. 規則（新規）：〆の確認済み扱い

価格のない〆・完売の行は、次をすべて満たすとき「確認済み扱い」とし、理由 price_unresolved と excluded を付けない。

| # | 条件 | SQL での形 |
|---|---|---|
| 形 | status が sold out、exclusion が excluded、価格と数量が NULL、商品と状態が決まっている | `lower(btrim(COALESCE(status,''))) IN ('sold out','soldout')`・`exclusion = 'excluded'`・`price_normalized IS NULL`・`quantity_normalized IS NULL`・`product_id`・`condition_id` が NULL でない |
| ① | 状態が FLAG でない | condition_canonical・condition_basis に FLAG を含まない |
| ② | 同じ仕入れ窓口に、同じ商品・同じ状態の過去の在庫がある | 別の行で、同じ sm.supplier_channel_id・同じ product_id・同じ condition_id・価格あり・売り切れでない・投稿が自分以前 |
| ③ | その商品の在庫が在庫表に今は残っていない（近似） | 同じ窓口・同じ product_id の別の行で、is_current・pid/unit 解決・excluded でない・価格あり・投稿が 48 時間以内・condition_canonical が FLAG_ でない・売り切れでない、が1行も無い |
| ④ | 人の修正が無い | その行の item_corrections が1件も無い（cr_latest.id IS NULL） |

適用範囲: 新しい規則は prompt_version を見ないので、v102 以外（旧エンジン）の〆の形の行にも効く。意図した範囲（人の修正が無く相手の在庫が消えた〆は、どちらのエンジンでも確認が要らない）。直近7日の画面の範囲では v102 以外の該当は 0 行（再審査 a1.out）なので KGI には影響しない。

「形」と①④を先に見て、満たすときだけ②③の副問い合わせを走らせる（CASE で囲む）。

③が近似である点: 在庫表の本当の条件（`backend/app/services/tcg_distribution_svc.py:367-375`）は cr.needs_review と cr.effect（Error 等）も見るが、review_joins の中で自分自身を呼べないため、保存済みの列で代える。近似は「在庫が残っているとみなす」側に倒れる（要確認・Error の行も残りとして数える）ので、外しすぎにはならない。48 は本番の max_age_hours（recon §3）と同じ値の定数。include_flag_single=true にしたときは FLAG_SINGLE の在庫を見落とす（§10）。

③の FLAG の見方: 在庫表は判定後の cr.canonical（`backend/app/services/tcg_distribution_svc.py:238`）で FLAG_ を落とすが、③は保存値の ar.condition_canonical で見る。人の状態判断などで cr.canonical だけ FLAG_ になる行は、③では「在庫が残っている」と数えるので要確認に残る側に倒れる（外しすぎない）。逆に ar.condition_canonical が FLAG_ で cr.canonical が FLAG_ でない行（人が FLAG を直した行）は③で数えず、外しすぎる側になる。この行は在庫表には出ているので、T2 ①（甲の集合との一致）と T2 ③で差が出ないことを確かめる

## 4. 変更前と変更後

### 4-1. 定数（`backend/app/services/tcg_condition_review_svc.py:53` の _HEX_PATTERN の下に足す）

```python
# 〆の確認済み扱いで「在庫表にまだ在庫がある」とみなす投稿の新しさ（時間）。
# 本番の tcg_distribution_settings.max_age_hours（48）と同じ値。設定を変えたらここも変える（docs/handoff/shime-review-exclude/design.md §3）
SHIME_STOCK_WINDOW_HOURS = 48
```

### 4-2. review_joins（`backend/app/services/tcg_condition_review_svc.py:227` の `) cr_valid` の直後、:228 の `CROSS JOIN LATERAL (SELECT` の前に足す）

変更前（:227-229）
```sql
        AND (NOT cr_input.mentions OR cr_input.master_valid), FALSE) AS valid_ack) cr_valid
    CROSS JOIN LATERAL (SELECT
        ARRAY(SELECT DISTINCT reason FROM unnest(
```

変更後
```sql
        AND (NOT cr_input.mentions OR cr_input.master_valid), FALSE) AS valid_ack) cr_valid
    CROSS JOIN LATERAL (SELECT
        -- 〆の確認済み扱い（docs/handoff/shime-review-exclude/design.md §3）。真なら price_unresolved と excluded を付けない
        CASE WHEN
            lower(btrim(COALESCE(cr_data.ar->>'status', ''))) IN ('sold out', 'soldout')
            AND cr_data.ar->>'exclusion' = 'excluded'
            AND cr_data.ar->>'price_normalized' IS NULL AND cr_data.ar->>'quantity_normalized' IS NULL
            AND cr_data.ar->>'product_id' IS NOT NULL AND cr_data.ar->>'condition_id' IS NOT NULL
            AND strpos(COALESCE(cr_data.ar->>'condition_canonical', '') || COALESCE(cr_data.ar->>'condition_basis', ''), 'FLAG') = 0
            AND cr_latest.id IS NULL
        THEN EXISTS (SELECT 1 FROM {schema}.analysis_results cr_pa
                JOIN {schema}.extraction_items cr_pi ON cr_pi.id = cr_pa.extraction_item_id
                JOIN {schema}.extraction_jobs cr_pj ON cr_pj.id = cr_pi.extraction_job_id
                JOIN {schema}.source_messages cr_pm ON cr_pm.id = cr_pj.source_message_id
                WHERE cr_pm.supplier_channel_id = sm.supplier_channel_id
                  AND cr_pa.product_id = (cr_data.ar->>'product_id')::integer
                  AND cr_pa.condition_id = (cr_data.ar->>'condition_id')::integer
                  AND cr_pa.extraction_item_id <> ei.id
                  AND cr_pa.price_normalized IS NOT NULL
                  AND lower(btrim(COALESCE(cr_pa.status, ''))) NOT IN ('sold out', 'soldout')
                  AND cr_pm.line_posted_at <= sm.line_posted_at)
         AND NOT EXISTS (SELECT 1 FROM {schema}.analysis_results cr_sa
                JOIN {schema}.extraction_items cr_si ON cr_si.id = cr_sa.extraction_item_id
                JOIN {schema}.extraction_jobs cr_sj ON cr_sj.id = cr_si.extraction_job_id
                JOIN {schema}.source_messages cr_sm ON cr_sm.id = cr_sj.source_message_id
                WHERE cr_sm.supplier_channel_id = sm.supplier_channel_id
                  AND cr_sa.product_id = (cr_data.ar->>'product_id')::integer
                  AND cr_sa.extraction_item_id <> ei.id
                  AND cr_sa.is_current IS TRUE AND cr_sa.pid_resolved IS TRUE AND cr_sa.unit_resolved IS TRUE
                  AND cr_sa.exclusion IS DISTINCT FROM 'excluded'
                  AND cr_sa.price_normalized IS NOT NULL
                  AND cr_sm.line_posted_at >= NOW() - make_interval(hours => {SHIME_STOCK_WINDOW_HOURS})
                  AND COALESCE(cr_sa.condition_canonical, '') NOT LIKE 'FLAG_%'
                  AND lower(btrim(COALESCE(cr_sa.status, ''))) NOT IN ('sold out', 'soldout'))
        ELSE FALSE END AS settled OFFSET 0) cr_shime
    CROSS JOIN LATERAL (SELECT
        ARRAY(SELECT DISTINCT reason FROM unnest(
```

### 4-3. 理由の配列（`backend/app/services/tcg_condition_review_svc.py:233-234`・:240-241）

変更前
```sql
                CASE WHEN cr_data.ar->>'price_normalized' IS NULL THEN 'price_unresolved' END,
                CASE WHEN cr_data.ar->>'exclusion' IS NOT NULL AND NOT cr_review_ack.excluded_acked THEN 'excluded' END
...
                AND NOT (reason = 'price_unresolved' AND cr_data.ar->>'price_normalized' IS NOT NULL)
                AND NOT (reason = 'excluded' AND (cr_data.ar->>'exclusion' IS NULL OR cr_review_ack.excluded_acked)) ORDER BY reason) AS other_reasons,
```

変更後
```sql
                CASE WHEN cr_data.ar->>'price_normalized' IS NULL AND NOT cr_shime.settled THEN 'price_unresolved' END,
                CASE WHEN cr_data.ar->>'exclusion' IS NOT NULL AND NOT cr_review_ack.excluded_acked AND NOT cr_shime.settled THEN 'excluded' END
...
                AND NOT (reason = 'price_unresolved' AND (cr_data.ar->>'price_normalized' IS NOT NULL OR cr_shime.settled))
                AND NOT (reason = 'excluded' AND (cr_data.ar->>'exclusion' IS NULL OR cr_review_ack.excluded_acked OR cr_shime.settled)) ORDER BY reason) AS other_reasons,
```

:240-241 も変えるのは、保存済みの review_reasons に同じ名前の理由が入っている行（v102 の埋め直しで付く price_unresolved。recon 原本 1-2 B）でも外すため。ほかの理由（unit_unresolved、condition_unknown 等）は残るので、その行は要確認に残る。

### 4-4. 実装上の注意（Sonnet 向け）

- f-string の中なので `{schema}` と `{SHIME_STOCK_WINDOW_HOURS}` 以外の波括弧を書かない。`'FLAG_%'` はそのまま書く（在庫表 `backend/app/services/tcg_distribution_svc.py:238` と同じ書き方）
- **`) cr_valid` と次の `CROSS JOIN LATERAL` の間に SQL のコメント行を置かない。** _fence_review_joins の正規表現（`backend/app/services/tcg_condition_review_svc.py:117`）は `) cr_valid` の直後に空白と CROSS/LEFT/JOIN が続くことを見るので、間にコメントがあると当たらず「expected=5 got=4」の例外で在庫表（dist_base）が落ちる。コメントは §4-2 のとおり `SELECT` の内側に置く
- 新しい別名 `cr_shime` は `OFFSET 0) cr_shime` で閉じるので、正規表現の `) cr_...` に当たらない（`cr_shime` は候補の名前に無く、`) cr` の後に `_shime` が続くため `cr` にも当たらない）。fenced の変換数 5 は変わらない。`to_jsonb(` を新しく書かない
- cr_shime の `OFFSET 0` は、PostgreSQL が lateral を理由の配列の参照先ごとに展開して副問い合わせを何回も走らせるのを防ぐ（審査の合成データ実測: 付けない 186.2 秒・付ける 14.5 秒・変更前 16.3 秒）。これで素の review_joins の OFFSET 0 は 2→3、fenced は 9→10 になる（§2）
- 比較は `cr_pa.product_id = (cr_data.ar->>'product_id')::integer` の形にし、列の側を型変換しない（索引を使うため）。本番の型は product_id・condition_id とも integer（r3-types.out）
- 副問い合わせの中で `ei`・`sm` を外側の別名として参照する（review_joins の前提 `backend/app/services/tcg_condition_review_svc.py:140`）
- `cr_pa.extraction_item_id <> ei.id` で自分を除く（context_sql の候補値 `to_jsonb(ar) || candidate` でも ei は同じ）

### 4-5. 在庫表の側では cr_shime を作らない（T3 不合格を受けた改訂、2026-10-19）

T3（本番の実測）で在庫表の SQL が 約1.2 秒 → 14〜16 秒に遅くなった（verify/REPORT.md）。在庫表の行は〆の形を WHERE（`backend/app/services/tcg_distribution_svc.py:367-375`）で必ず落とすので、在庫表の側で cr_shime を計算する意味が無い。そこで review_joins に引数を1つ足し、在庫表の3か所では副問い合わせを作らない。

```python
def review_joins(*, analysis_expression: str = "to_jsonb(ar)", selected_expression: str | None = None,
                 schema: str | None = None, fenced: bool = False, shime: bool = True) -> str:
```

- `shime=True`（既定）: §4-2 の cr_shime をそのまま入れる（要確認一覧・取り込み進捗・context_sql）
- `shime=False`: cr_shime の lateral を `CROSS JOIN LATERAL (SELECT FALSE AS settled OFFSET 0) cr_shime` に置き換える。§4-3 の理由の配列は同じ文字列のまま（settled が常に偽なので変更前と同じ判定）。OFFSET 0 の数は shime の値で変わらない（素 3・fenced 10）
- 書き方: §4-2 の cr_shime の lateral の文字列を Python の変数に分け、shime=False のときは `CROSS JOIN LATERAL (SELECT FALSE AS settled OFFSET 0) cr_shime` に差し替えて f-string に埋める（波括弧は §4-4 のとおり）
- 呼び出し元の変更（4か所）:
  - :366 `review_joins(schema=TCG_SCHEMA, fenced=True)` → `review_joins(schema=TCG_SCHEMA, fenced=True, shime=False)`
  - :480 `review_joins(schema=TCG_SCHEMA)` → `review_joins(schema=TCG_SCHEMA, shime=False)`
  - :524 `review_joins(schema=TCG_SCHEMA)` → `review_joins(schema=TCG_SCHEMA, shime=False)`
  - `backend/app/services/tcg_import_progress.py:129` `review_joins(schema=TCG_SCHEMA)` → `review_joins(schema=TCG_SCHEMA, shime=False)`。取り込み進捗は要確認の数を保存値で数え、review_joins は並び順（cr.canonical）にだけ使うので、cr_shime は要らない（再審査の指摘。取り込み1件の全行にかかるので速さの危険を残さない）
- これで在庫表・配信プレビュー・除外内訳の SQL は、変更前と比べて「`CROSS JOIN LATERAL (SELECT FALSE AS settled OFFSET 0) cr_shime` の1つと、理由の配列の `cr_shime.settled` 参照」だけが違う形になり、判定は変更前と同じになる
- 遅くなった原因は未確認（ai_ro で EXPLAIN が使えない）。この改訂は副問い合わせそのものを在庫表の SQL から無くすので、原因が何であっても在庫表の側には及ばない

試験の追加（T1）: (m) `review_joins(fenced=True, shime=False)` と `review_joins(shime=False)` の両方の文字列に `cr_pa`・`cr_sa` が無く、`SELECT FALSE AS settled OFFSET 0) cr_shime` が1回ある (n) 在庫表の SQL（distribution_rows_sql、まとめあり・なしの両方）に `cr_pa` が無い (o) `backend/app/services/tcg_distribution_svc.py` のソースに `shime=False` がちょうど3回、`backend/app/services/tcg_import_progress.py` に1回ある（付け忘れで遅い SQL が戻るのを防ぐ） (l) は shime=False の在庫表で〆の行が出ず例外が無いことを見る形にそろえる。

## 5. 代替案と選んだ理由

| 案 | 中身 | 判断 |
|---|---|---|
| A（採用） | 一覧の判定 review_joins で、条件を満たす〆の行に2つの理由を付けない | 判定の唯一の場所（`backend/app/services/tcg_condition_review_svc.py:3`「Every read gate uses review_joins」）。相手の在庫が後から消えた場合も、次の表示で自動で外れる |
| B | 解析の保存時（v102）に「確認済み」の印を書く | 2つの理由は保存値でなく一覧 SQL が毎回付ける（:233-234）ので、保存しても消えない。③（在庫表に今残っているか）は時間で変わるのに保存時点で固定される |
| C | 自動で review_ack（このままで良い）を書く | ack は excluded しか外さない（:240）。人の判断の記録に機械の判断を混ぜることになる。本番の前例も無い（recon §1） |
| D | 価格のない〆はすべて要確認から外す | 取り違えが疑われる 10 行も消える。PO 承認の KGI（10 行は残す）に反する |

## 6. 影響範囲（review_joins の呼び出し元の全走査、recon §2・a2_callers_grep.txt）

| 呼び出し元 | 変わること |
|---|---|
| 要確認一覧 `backend/app/services/tcg_analysis_review_svc.py:76` | 甲の行が一覧と total から消える（目的） |
| 在庫表 dist_base `backend/app/services/tcg_distribution_svc.py:366` | 変わらない。shime=False で cr_shime は常に偽（§4-5）。〆の行は :370・:372・:375 で落ちる |
| 配信プレビュー件数 `backend/app/services/tcg_distribution_svc.py:480` | 変わらない（shime=False・同じ WHERE） |
| 除外内訳 `backend/app/services/tcg_distribution_svc.py:524` | 変わらない（shime=False。needs_review・reasons を使わない） |
| 取り込み進捗 `backend/app/services/tcg_import_progress.py:129` | 変わらない（shime=False、§4-5）。要確認の数は保存値の ar.needs_review で数え、review_joins は並び順にだけ使う |
| 状態の判断の保存 context_sql `backend/app/services/tcg_condition_review_svc.py:322`（設計時点は :275。実装で行が増えた） | 甲の行は needs_review が偽になる。状態の判断の保存は今と同じに通る |
| 旧エンジンの再解析 `backend/app/services/tcg_analyzer_svc.py:1592`・:1801 | :1592 は商品の修正がある行だけを通る道（:1586-1592）なので④で settled は偽になり、変わらない。:1801 で甲に当たる行を再解析すると、保存する review_reasons から2つの理由が抜ける（新しい規則と同じ値）。:1801 の候補値は status・exclusion を持たないので、古い保存値で「形」を判定する |
| 試験 `backend/tests/test_tcg_analysis_review.py:220`・`backend/tests/test_inventory_distribution_rows_pg.py:99`・`backend/tests/test_v102_human_decisions_pg.py:283`・:445・`backend/tests/test_tcg_condition_review.py:159`・`backend/tests/test_tcg_distribution_pg.py`・`backend/tests/test_tcg_import_progress_pg.py`・`backend/tests/test_line_analysis_v102_pg.py`・`backend/tests/test_tcg_work_matching_integration.py`・`backend/tests/test_review_gemini_summary_pg.py` | review_joins を通るので追従する。期待値の変更は不要の見込み（〆の形の試験データが無い）。CI で確かめる |
| 試験 `backend/tests/test_tcg_condition_review_fenced.py:29`・:41 | OFFSET 0 の数の期待を 2→3・9→10 に直す（§2） |
| 試験 `backend/tests/test_inventory_distribution_rows.py:119`（_VIEW_SQL_BEFORE）・:269（_GOLDEN） | 在庫表の SQL の長さと SHA-256 の固定値。shime=False でも cr_reasons が cr_shime.settled を参照するので、定数の lateral（`CROSS JOIN LATERAL (SELECT FALSE AS settled OFFSET 0) cr_shime`）と参照の分だけ SQL が変わる（CI で6件とも +159 文字、§11-6）。差がこの部分だけであることを新旧 SQL の diff で確かめてから固定値を更新し、各定数の上のコメントに1行足す（過去の便と同じやり方、commit 9a2af2049） |

### 接触面分析（6面）

| 面 | 影響 |
|---|---|
| DB | 書き込みなし。読み取りの副問い合わせが増える（速さは §7 T3） |
| API | GET /api/v1/tcg/analysis-results の件数と行が甲の分減る |
| 画面 | 要確認タブから甲の行が消える |
| GAS・在庫表 | 変わらない（T2） |
| 定期処理 | なし |
| 権限・secrets | なし |

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| T1 試験 | CI（pg）で新しい試験 12 件が通る: (a) 甲の形 → needs_review 偽・理由に2つ無し (b) 相手の在庫なし → 2つの理由が残る (c) 相手の商品の在庫が 48 時間以内にある → 残る (d) その在庫が 48 時間より古い → 外れる (e) 状態が FLAG → 残る (f) item_corrections あり → 残る (g) 別の窓口の相手だけ → 残る (h) 保存済みの理由（unit_unresolved 等）あり → 2つは消えるが needs_review は真 (i) 相手の在庫が 48 時間以内だが is_current が偽（ADR-158 でまとめ済み。G1 の形）→ 外れる (j) 相手の投稿が自分より後 → 残る (k) 相手に価格はあるが Sold out → 残る (l) review_joins(fenced=True) の在庫表（dist_base）に〆の行を入れても例外が出ず、行は変わらない。既存の `backend/tests/test_tcg_condition_review_fenced.py`・`backend/tests/test_tcg_condition_review.py:681` も通る |
| T2 マージ前・本番データ（G2〜G5） | 本番 ai_ro に対し、変更前（origin/main）と変更後（PR の HEAD）の review_joins で作った要確認の判定と在庫表の行を、同じ1つの読み取りトランザクションで並べる。合格: ①要確認で「変更前 真・変更後 偽」になった行の集合 = 同じトランザクションで §3 の4条件を直接数えた甲の集合 ②「変更前 偽・変更後 真」は 0 行 ③甲以外で判定が変わった行 0 ④在庫表（distribution_rows_sql、まとめあり・なし）の row_key の集合が前後で同じ。比べる範囲は recon §3 と同じ「sm.is_active かつ直近7日」。設計時点の見込みは甲 35・乙 8・丙 2。甲が 30〜40 を外れたら止めて理由を調べる（この基準は上の範囲にだけ使う）。範囲外（7日より古い・無効な投稿）で判定が変わった行は件数を別に記録する |
| T3 速さ | T2 と同じ場で、要確認一覧の1ページ目の SQL と在庫表の SQL（まとめあり・なし）の実行時間を前後で各3回（ばらつきで判定が際どいときは捨て運転1回＋各5回。§11-6）測り、中央値が「変更前 ×1.2 + 100ms」以内。ai_ro では EXPLAIN ANALYZE・\\timing が使えないため、読み取りの道が出す AUDIT 行の ms を、前後を交互に流して比べる（絶対値でなく前後の比の根拠として使う。Opus 判断 2026-10-19） |
| G1 本番 | デプロイ後、ai_ro で T2 と同じ判定を流し c838f466 が偽。PO は要確認一覧に安川さんの「カードセット〆切」が出ないことを画面で見られる |
| G3・G4 本番 | デプロイ後の同じ判定で f364283f・044ba439 が真のまま（044ba439 は相手の在庫が 48 時間以内に残っている間） |

T2・T3 の本番の読み方: SQL は Python で review_joins から作り、表の名前を ai_ro のビュー名（public.x → ai_ro.public__x）に置き換えて reader 鍵で流す（書き込みなし。前便 docs/handoff/v102-shime-same-post-stock/design.md §7 T2 と同じ道）。生出力は /tmp/CC報告ファイル/shime-review-exclude-20261019/verify/ に置く。

## 8. 計画票

| 順 | 作業 | 担当 | 完了の印 |
|---|---|---|---|
| 1 | PO 実装承認 | PO | 「y」 |
| 2 | 実装カード発行 | Opus | 実装カード（§4 の前後コード・T1 の試験） |
| 3 | 実装・T1（手元で DB を使わない試験・ruff） | Sonnet | PR 起票（draft でない。危険パスなし） |
| 4 | T2・T3 の本番読み取り比較 | Sonnet（reader 鍵） | verify/ の生出力と合否 |
| 5 | 審査 | Reviewer（opus） | `VERDICT: APPROVE on <HEAD> PR #N` |
| 6 | GO 記録・マージ | Opus（委任 GO、ADR-1003） | merge commit |
| 7 | デプロイ確認・G1/G3/G4 | Opus・Sonnet | deploy success と ai_ro の判定 |
| 8 | 結果の記録 | Opus | 本書 §7 に結果を追記 |

## 9. ADR を作らない理由

要確認の理由（excluded・price_unresolved）自体を定める ADR が無く（recon §0）、今回は理由の付け方に1つ例外を足すだけで、技術の選択や他の機能との約束を変えない。規則の正本は本書 §3 とし、コードのコメントから本書を指す。

## 外部・過去事例の参照と我々への応用

外部事例は使わない。理由: 社内の SQL の判定に1条件を足す変更で、比べる価値のある外部の数値が無い。社内の前例として、v102 の〆の引き継ぎ（`backend/app/services/line_analysis_v102_svc.py:871` _apply_soldout_targets、人の判断があれば機械が上書きしない）と note_unmatched の純メモ除外（`backend/app/services/tcg_condition_review_svc.py:237`、一覧 SQL で理由を外す）を手本にした。④（人の修正があれば触らない）と、一覧 SQL で理由を外す形はこの2つと同じ。

## 10. 弊害・トレードオフ

| 弊害 | 対処 |
|---|---|
| ③の 48 は定数。在庫表の設定を変えるとずれる | 定数のコメントで本書と設定名を指す。ずれても「在庫が残っているとみなす期間」が変わるだけで、在庫表には影響しない |
| include_flag_single=true のとき、FLAG_SINGLE の在庫を③で見落とし、外しすぎる | 本番は false（recon §3）。true に変える時は本書 §3 を見直す（継続） |
| 取り違えた商品の〆でも、たまたま同じ商品の過去の在庫があり今は残っていなければ外れる | ②で同じ窓口・同じ状態まで揃うことを求める。誤りは在庫表に影響しない（〆の行はもともと在庫表に出ない）。見落としの影響は「確認の手間が1件減る代わりに、誤った〆に気づかない」にとどまる |
| 副問い合わせで一覧が遅くなる | 〆の形の行だけ走らせる。T3 で測り、基準を超えたら止める |
| ③の FLAG を保存値（ar）で見るため、在庫表（cr）とずれる行がある | §3 の注記。T2 ①③で差 0 を確かめ、差が出たら止める |
| 丙の行は 48 時間後に自動で外れる | 意図どおり（相手の在庫が在庫表から消えた時点で③が満たされる）。G4 は「残っている間」の確認 |

戻し方: この PR を revert する（DB の変更が無いので revert だけで元に戻る）。

## 維持の仕組み

守り手: backend/tests/test_tcg_condition_review.py（規則の動きを CI の pg 試験で守る。48 と max_age_hours の一致は人手で守る）

| 守るもの | 守り手 |
|---|---|
| 規則の正本 | 本書 §3（コードのコメントから指す） |
| 規則の動き | `backend/tests/test_tcg_condition_review.py`（T1 の12件） |
| fenced の形 | `backend/tests/test_tcg_condition_review_fenced.py` |
| 48 と max_age_hours の一致、include_flag_single | 人手で守る（設定を変える時に本書 §10 を見る） |

## 11. 審査

### 11-1. Opus による自己審査（独立した第二者のレビューではない）

判定: **APPROVE（設計合格。実装承認ではない）**

| 観点 | 結果 |
|---|---|
| KGI との一致 | §3 の4条件は PO 承認の KGI の文言（FLAG でない・同じ仕入元の同じ商品・同じ状態の過去の在庫・在庫表に今残っていない（dist_base 近似・48h）・人の判断なし・〆と完売は同じ）と一対一。「同じ仕入元」は仕分けの実測と同じ supplier_channel 単位にした（recon §3） |
| 実物との整合 | 理由を作る場所は review_joins だけ（:228-241）。在庫表は〆の行を価格・除外・完売の3条件で別に落とすので、判定の変化が配信に漏れない（`backend/app/services/tcg_distribution_svc.py:370`・:372・:375）。T2 ④で実データでも確かめる |
| 根拠 | 45 行の内訳・設定値・保存済みの理由を本番 ai_ro で実測（r1-reasons.out・r2-settings.out・split2.out） |
| 検証可能性 | G1〜G5 を集合の一致で判定。時刻の影響は「同じトランザクションで前後を並べる」で除いた |
| 実装範囲 | 1ファイルの SQL の前後と試験12件・fenced の期待数2か所。触らない範囲を §2 に列挙 |
| 未解決 | U1（速さ）は T3 で止める条件付き。U2・U3 は結論に影響しない |

指摘して直したこと: 仕分けの SQL（split2）は相手の status が NULL の行を数えていなかったが、在庫表（`backend/app/services/tcg_distribution_svc.py:248`）は COALESCE で NULL を売り切れでない側に入れる。§4-2 は在庫表に合わせて COALESCE にした。差が出るかは T2 ①で見る（甲が 35 から動いたら内訳を確かめる）。

### 11-2. Reviewer（opus）1回目: REVISE（2026-10-19）

| # | 指摘 | 直したところ |
|---|---|---|
| 1 | `) cr_valid` の直後のコメント行で fenced の正規表現が外れ、dist_base が例外で落ちる（致命） | §4-2 コメントを SELECT の内側へ・§4-4 に禁止を明記・T1 (l) |
| 2 | `::text` で列側を変換すると索引が使えない | §4-2 を `= (...)::integer` に。型は本番で integer（r3-types.out） |
| 3 | cr_shime に OFFSET 0 が無いと副問い合わせが展開され約11倍遅い | §4-2 `OFFSET 0) cr_shime`・§2/§6 に fenced 試験の期待数 2→3・9→10 |
| 4 | 取り込み進捗は保存値で数えるので変わらない | §6 を訂正 |
| 5 | review_joins を通る試験の列挙漏れ | §6 に追記 |
| 6 | 試験 (i)〜(l) の不足 | §7 T1 に追加（12件） |
| 7 | ③の FLAG が ar と cr でずれる | §3 注記・§10 |
| 8 | 旧エンジンの再解析で保存値が変わる点が §2 と矛盾 | §2 を訂正 |

### 11-3. Reviewer（opus）2回目: APPROVE（2026-10-19）

前回の8件はすべて解消。review_joins の写しに §4-1〜§4-3 を当てはめて組み立て、fenced の置換数 5（例外なし）、OFFSET 0 の数 素 3・fenced 10、`_c3(base)==fenced`、波括弧の書き残し 0 を確かめた。軽微3件は本書へ反映済み: ① T2 の比べる範囲を「sm.is_active かつ直近7日」に固定 ② 旧エンジンの影響は :1801 だけ（:1592 は④で外れない） ③ 新しい規則は v102 以外にも効く旨を §3 に明記。fenced 試験の行番号を :30→:29 に訂正。
未確認（CI と T3 で確かめる）: 実際の PostgreSQL での構文検査・実行計画、analysis_results.product_id の索引の有無（U1）。

### 11-4. T2・T3 の1回目（PR #4535 の HEAD fddb84805、2026-10-19 08:03Z、verify/REPORT.md）

- T2: ①〜④ 合格（前 真→後 偽 35 行 = 甲 35 行、前 偽→後 真 0、甲以外の変化 0、在庫表の row_key 差 0）。〆の形 46・甲 35・乙 8・丙 3（設計時点から丙 +1、理由は次回 T2 で特定）。範囲外（7日より古い）で真→偽 3 行（0fcc5a27・f24b28fa・e7a170d8。e7a170d8 は v102 以外）。§3 は全期間・全エンジンに効く設計（§3 適用範囲）なので意図どおりかを次回 T2 で4条件と突き合わせる。
- T3: 要確認一覧 932→1154 ms（基準 1218、合格）。在庫表 まとめなし 1206→14092 ms・まとめあり 1352→16260 ms（不合格）。→ §4-5 で在庫表の側から cr_shime を外す改訂。

### 11-5. Reviewer（opus）3回目（§4-5 の改訂）: APPROVE（2026-10-19）

shime=False の文字列から定数の lateral と settled の参照4か所を除くと origin/main と完全一致（素・fenced とも）。置換数5、OFFSET 0 は素3・fenced10、cr_pa・cr_sa 0。:480 は WHERE が価格ありに限るため、:524 は cr.canonical・cr.effect しか使わないため、数字は変わらない。T3 の AUDIT ms は前後の比としてのみ根拠にする（変更前のばらつき 1159〜1337ms より基準が広く、12倍はばらつきを大きく超える）。軽微な指摘を反映: 取り込み進捗も shime=False に、試験 (m) を fenced なしにも広げ (n) をまとめあり・なしに (o) を追加、lateral の文字列を変数に分ける書き方を明記。マージ前に main の取り込みを CI で確かめる。

### 11-6. T3 の測り直しと CI の失敗（HEAD 060a07cbe、2026-10-19、verify3/REPORT.md・ci-fail/）

- T3 要確認一覧1ページ目: 前後交互に各5回（捨て運転各1回）。変更前の中央値 947ms、変更後の中央値 1205ms、基準 1236.4ms で合格。2回目の 0.2ms 超えは、変更前1回目の外れ値 1848ms によるもの。
- CI ①: pytest-run-internal で6件失敗。`backend/tests/test_inventory_distribution_rows.py:107`・:283 の固定値と比べて、4通りとも +159 文字。§4-5 の定数の lateral の分。固定値の更新を §6 に追加した。shime=False で lateral を出さない形は、cr_reasons が settled を参照するため採らない。
- CI ②: pytest (SQLite + PostgreSQL RLS) は ① の集約で、① に連動して落ちただけ。
- CI ③: process-artifacts gate は「### GO記録」が無いため。services を変更する PR の手続きで、GO の後に本文へ足す。

### 11-7. マージと本番反映（2026-10-19）

- Reviewer（opus）4回目 APPROVE（247dd1df8）。main（ADR-1032 の docs 3ファイル）を取り込んだ 326ba74c6 で再 APPROVE。PR の差分は 247dd1df8 と1バイトも違わない。CI は必須チェック 38 件が緑。GO は「POの委任に基づくClaude Opus発行（ADR-1003）」で、PR 本文の ### GO記録 に残した。
- マージ 2640ae932（10:02:52Z）。Deploy run 39234592360 success（10:06Z）。Checkout の log に 2640ae932529368998f5eab61528abfe2b7e67a8。
- 本番の照合は ai_ro・sm.is_active かつ直近7日、10:09〜10:10Z。生出力は /tmp/CC報告ファイル/shime-review-exclude-20261019/post/。
  - G1 合格: c838f466 は要確認から外れた。
  - G2: 〆の形は 47 行。外れたのは 36 行（甲）、残ったのは 11 行（乙 8・丙 3）。KGI 承認時（06:24Z）の 45 行・35/10 から、直近7日の窓に入る行が2行増えた。止める範囲（30〜40）の内側。
  - G3 合格: f364283f ほか乙 8 行は残った。
  - G4 合格: 044ba439・4e713598・5642ad0b は残った。
  - G5 合格: 〆の形でない 1141 行で needs_review が真の行は、変更前 145・変更後 145。needs_review か理由が違う行は 0。
- 要確認一覧1ページ目の AUDIT は 1206ms（参考、1回）。
- 未確認: VPS 上のコンテナ内のコードの SHA（読み取り鍵では見られない）。PO の画面目視。
