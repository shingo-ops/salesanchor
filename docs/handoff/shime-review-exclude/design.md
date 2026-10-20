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
**担当**: Planner（Opus）。改訂2（§12）: 設計審査済み・PO 実装承認済み（2026-10-20「1」）。改訂前の状態: 設計審査済み（2回目 APPROVE）・PO 実装承認済み（2026-10-19「1」）・実装 PR #4535・T3 不合格を受け §4-5 を改訂し再審査 APPROVE（§11-5）・#4535 マージ（2640ae932）・本番反映済み（2026-10-19、G1〜G5 合格、§11-7）  
**ADR-1015 の区分**: A（要確認の判定に新しい規則を足す）。DB の列・migration・本番データの書き換えは無い

---

## 1. 目的と成功条件（KGI、PO 承認済み 2026-10-19）

PO の言葉: 「カードセット〆切 Hironobu Yasukawaさんのこの情報が要確認に回っているのでまだ完全には〆を対応処理できていない」。Opus の KGI 案（直近7日の価格なし〆・完売 45 行のうち 35 行を要確認から外し 10 行を残す。〆と完売は同じ扱い）に PO「y」。

| # | 合格の条件（○×） |
|---|---|
| G1 | 安川さんの〆（item c838f466）が要確認一覧に出ない |
| G2 | 直近7日の価格なし〆・完売のうち、§3 の4条件をすべて満たす行（設計時点 35 行）が要確認から消え、それ以外（設計時点 10 行）は残る |
| G3 | 相手の在庫が無い行（設計時点 8 行。例 f364283f）は残る（§12 改訂2 で置き換え。f364283f は外れる側） |
| G4 | 相手の商品の在庫が在庫表にまだ出ている行（設計時点 2 行。例 044ba439）は残る（§12 改訂2 で置き換え。同じ投稿の別の状態の在庫は数えないので 044ba439・4e713598 は外れる側） |
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

> §12 改訂2 で置き換え。今の正本は 12-3。以下は改訂前の記録。

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

> 改訂前の便の基準。改訂2の基準は 12-6（G3・G4 は H1〜H4 で置き換え）。

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

> 改訂前の記録。②は改訂2で消したので、3行目の対処は古い。改訂2の弊害は 12-7。

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
| 規則の正本 | 本書 12-3（改訂2。コードのコメントから指す） |
| 規則の動き | `backend/tests/test_tcg_condition_review.py`（T1 の12件と、改訂2の (p)〜(t)） |
| 自動で外した〆の正しさ | agent-console の定期実行「〆の自動判定 毎朝点検」（12-8。期限つき。止めた後は人手で守る） |
| fenced の形 | `backend/tests/test_tcg_condition_review_fenced.py` |
| 48 と max_age_hours の一致、include_flag_single | 人手で守る（設定を変える時に本書 §3 の注記と §10 を見る。改訂2でも48と③の数え方は同じ） |

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

## 12. 改訂2 — 〆・完売は値段や前の在庫が無くても要確認から外す（2026-10-20）

状態: 設計審査済み（Reviewer 2回目 APPROVE）・PO 実装承認済み（2026-10-20「1」。選択肢「今の設計を先に作り、残る3つ（カンジンの状態の引き継ぎ・倉田の値段の下の完売・LFスタッフ1の単位）の直しは次の回で設計・審査してから作る」）。承認の前に PO へ示した内容: 外れる11行・残る4行（30th CELEBRATION のカンジン・9種セットの倉田・ピカチュウ30th の LFスタッフ1・肉ルフィの斉藤）とその理由（原本 ~/CC報告ファイル-keep/shime-remaining-20261020/recon8・recon9）。次の回の材料は recon9。

### 12-1. 目的と成功条件（KGI。PO 判断 2026-10-20）

PO の言葉: 「全ての〆、完売商品は要確認に入らずに自動的にシステムが完売と判断して集計リストから消える仕組みになったか？」。§11-7 の後も残った行について、PO は次を決めた。
- 初めて完売と書かれた行（前の在庫が見つからない行）も外す。代わりに、毎朝の定期実行で〆の精度を点検する
- 値段が書かれた完売も、完売の知らせとして扱う
- 在庫表にまだ在庫が出ている商品の〆は残す（「使われている投稿だけを見る」に「合意」）

PO の合意との対応（実装承認で PO に具体の商品名で示して了承を取る。了承が無ければ実装しない）:
- 「使われている投稿だけを見る」を文字どおりに入れる案（12-5 案 E）は採らない。在庫表は差し替えられた古い投稿の在庫も出しているため、案 E では 30th CELEBRATION の〆（5642ad0b）が、在庫表に No shrink box 24,800円 が出ているのに外れてしまう。採用案は「在庫表に出ているかどうか」を在庫表と同じ数え方で見る
- 同じ投稿で〆と別の状態の在庫（例: 箱は〆・Searched pack は在庫あり。044ba439・1d027e6a・4e713598）は〆の対象でないとして外す。この3行は、同じ投稿の Searched pack が在庫表に出たまま、箱の〆が要確認から外れる

| # | 合格の条件（○×） |
|---|---|
| H1 | 直近30日の「Sold out・excluded」の行のうち要確認に出る行が、設計時点で 15 → 4 になる（11 行が外れ、外れていた行が戻るのは 0 行。recon6） |
| H2 | 外れる 11 行は、どれも在庫表（まとめあり・なし）に、同じ窓口・同じ商品で〆と別の投稿の在庫が 0 行（recon6 cross.out） |
| H3 | 在庫表に、同じ窓口・同じ商品で別の投稿の在庫が出ている〆（設計時点 5642ad0b）は残る |
| H4 | ほかの理由（単位不明・状態不明・余白行の疑い等）がある行は残る（設計時点 018e101c・2928ea55・20f9cb54） |
| H5 | 在庫表・配信・GAS の SQL は1文字も変わらない。〆の形でない行の要確認は1行も変わらない |
| H6 | 毎朝の点検が登録され、初回の結果が PO への返答（agent-console の会話）に出る |

件数は時刻で動くため、H1〜H5 は §7 と同じく「同じ読み取りトランザクションで前後を並べる」で確かめる（12-6 T2）。

### 12-2. 現在地（recon。docs/handoff/shime-review-exclude/recon.md「改訂2」。生出力の原本は ~/CC報告ファイル-keep/shime-remaining-20261020/ の recon4・recon5・recon6・review1）

- 【事実】今の式（§3）は price NULL・quantity NULL と ②（前の売り中）を求める。直近30日で要確認に残る〆の形 15 行のうち、①値段つきの完売（8179e1e0）②前の売り中が見つからない行 ③同じ投稿の別の状態（Searched pack）の在庫を③で数えてしまう行（044ba439・1d027e6a・4e713598）が、どれも在庫表と食い違わないのに残っていた（recon4 sim-final-diff.txt・recon5 match.out）。
- 【事実】在庫表は差し替えられた投稿（sm.is_active=FALSE）でも ar.is_current=TRUE の行を出す（`backend/app/services/tcg_distribution_svc.py:316` の source_cte(include_inactive=True)）。2026-10-19 18:42Z の在庫表 1087 行のうち 300 行がそれ（recon5 inactive.out）。
- 【事実】5642ad0b の商品は、差し替え済みの投稿 72c6881d の No shrink box（24,800円）が在庫表に出ている（recon5 kanjin.out）。
- 【事実】在庫表の側は shime=False で定数の lateral になる（`backend/app/services/tcg_condition_review_svc.py:177`。呼び出し `backend/app/services/tcg_distribution_svc.py:366`・:480・:524・`backend/app/services/tcg_import_progress.py:129`）。今回の改訂は shime=True の文字列だけを変える。

### 12-3. 規則の変更（§3 を次で置き換える）

| # | 変更前 | 変更後 |
|---|---|---|
| 形 | sold out・excluded・価格 NULL・数量 NULL・商品と状態あり | sold out・excluded・商品と状態あり（価格・数量は問わない） |
| ① | FLAG でない | 同じ |
| ② | 同じ窓口・商品・状態の、前の売り中がある | 削除 |
| ③ | 同じ窓口・同じ商品の今の在庫（is_current・解決済み・excluded でない・価格あり・48時間以内・FLAG_ でない・売り切れでない）が無い | 同じ。ただし「〆と同じ投稿で、〆と別の状態」の行は数えない |
| ④ | 人の修正が無い | 同じ |

採らなかったこと: ③に cr_sm.is_active IS TRUE を足す案（12-5 案 E）。

外れる理由の言い直し: 「〆と書かれた商品が、在庫表に（別の投稿で）残っていない」なら外す。同じ投稿の別の状態（例: 箱は〆・バラ売りは在庫あり）は〆の対象でないので数えない。

### 12-4. 変更前と変更後（`backend/app/services/tcg_condition_review_svc.py:176-211` の shime_lateral の shime=True 側だけ）

変更前（:183、:187-198、:204-205）
```sql
            AND cr_data.ar->>'price_normalized' IS NULL AND cr_data.ar->>'quantity_normalized' IS NULL
...
        THEN EXISTS (SELECT 1 FROM {schema}.analysis_results cr_pa
                ...（:187-198 の ② の副問い合わせ全体）
                  AND cr_pm.line_posted_at <= sm.line_posted_at)
         AND NOT EXISTS (SELECT 1 FROM {schema}.analysis_results cr_sa
...
                  AND cr_sa.extraction_item_id <> ei.id
                  AND cr_sa.is_current IS TRUE AND cr_sa.pid_resolved IS TRUE AND cr_sa.unit_resolved IS TRUE
```

変更後
```sql
        THEN NOT EXISTS (SELECT 1 FROM {schema}.analysis_results cr_sa
...
                  AND cr_sa.extraction_item_id <> ei.id
                  AND (cr_sa.condition_id = (cr_data.ar->>'condition_id')::integer OR cr_sm.id <> sm.id)
                  AND cr_sa.is_current IS TRUE AND cr_sa.pid_resolved IS TRUE AND cr_sa.unit_resolved IS TRUE
```

- :183 の価格・数量 NULL の行を消す
- :187-197 の `THEN EXISTS (... cr_pa ...)` の副問い合わせ全体を消し、:198 の `         AND NOT EXISTS (SELECT 1 FROM {schema}.analysis_results cr_sa` を `        THEN NOT EXISTS (SELECT 1 FROM {schema}.analysis_results cr_sa` にする
- :204（`AND cr_sa.extraction_item_id <> ei.id`）と :205（`AND cr_sa.is_current ...`）の間に、上の1行を足す
- :179 のコメントの `design.md §3` を `design.md §12-3` にする。同じく `backend/app/services/tcg_condition_review_svc.py:55`（48 の定数のコメント）と `backend/tests/test_tcg_condition_review.py:752`（試験の見出し）の `§3` も `§12-3` にする
- ほかの行（:176-178、:180-182、:184-186、:199-204、:205-211 の中身）は変えない
- 試算に使った SQL は、この形と同じ（recon6 sim-v2.sql。recon4 sim-final.sql から is_active の1行だけを消したもの、sql.diff）
- 波括弧・OFFSET 0・fenced の注意は §4-4 のまま。新しい `) cr_` の閉じ方を作らない（OFFSET 0 の数は素 3・fenced 10 のまま）
- §4-3 の理由の配列は変えない
- 変更前より外れる行が増えるだけで、戻る行は出ない: 形は広くなり、②は無くなり、③の NOT EXISTS は数える行が減る（どの条件も「外れる」側にしか動かない）。実データでも外れる→残る 0（recon6）

### 12-5. 代替案

| 案 | 中身 | 判断 |
|---|---|---|
| D'（採用） | 12-3 のとおり | 在庫表と同じ数え方で「在庫が残っていない〆」を外す。H1〜H5 を実測で満たす |
| E | ③に cr_sm.is_active IS TRUE を足す（差し替えられた投稿の在庫は数えない） | 不採用。在庫表は差し替え済みの投稿の is_current 行を出すので、5642ad0b のように在庫表にまだ在庫が出ているのに〆を外してしまう（recon5 match.out。試算で 12 行外れ、そのうち 1 行が食い違い） |
| F | 〆の形はすべて外す（③も無くす） | 不採用。在庫表に在庫が残っている〆が人の目から消える |
| G | 今のまま | 不採用。PO 判断（12-1）に合わない |

### 12-6. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| T1 試験の書き換え | CI（pg）で `backend/tests/test_tcg_condition_review.py` の次が通る。期待を反転して名前も変える: (b) 相手の在庫なし → 外れる（`test_shime_settled_without_partner_stock`） (g) 別の窓口の在庫だけ → 外れる（`test_shime_settled_when_only_other_channel_has_the_partner`。相手の投稿を 100 → 10 時間前にして、窓口の区別を確かめる形にする） (j) 相手が後の投稿（48時間より古い）→ 外れる（`test_shime_settled_when_partner_was_posted_after_it_but_old`） (k) 相手も Sold out → 外れる（`test_shime_settled_when_partner_is_sold_out_too`）。(a)(c)(d)(e)(f)(h)(i)(l)(m)(n)(o) は変えずに通る |
| T1 試験の追加 | (p) 値段と数量つきの完売（price 7500・quantity 3）で相手の在庫なし → 外れる (q) 〆と同じ投稿で別の状態の在庫（〆の投稿は seed のとおり今の時刻。48時間以内）→ 外れる (r) 〆と同じ投稿で同じ状態の在庫 → 残る (s) 別の投稿で別の状態の在庫（10時間前）→ 残る (t) 差し替え済み（source_messages.is_active=false）の投稿にある is_current の在庫（10時間前）→ 残る（在庫表と同じ数え方。5642ad0b の形）。同じ投稿にするには seed_partner の後に `UPDATE public.extraction_jobs SET source_message_id=<〆の smid> WHERE id=<相手の job>` を使う。`backend/tests/test_tcg_condition_review_fenced.py` の OFFSET 0 の数（:29・:41）は変えずに通る |
| T1 在庫表の固定値 | `backend/tests/test_inventory_distribution_rows.py` の _VIEW_SQL_BEFORE・_GOLDEN を変えずに通る（在庫表は shime=False のため） |
| T2 本番データ（H1〜H5） | §7 T2 と同じ道で、変更前（origin/main）と変更後（PR の HEAD）の review_joins を同じ1つの読み取りトランザクションで並べる。合格: ①前 真→後 偽 の集合 = 同じトランザクションで直接数えた「12-3 の条件を満たし、変更前は needs_review が真で、変更後はほかの理由（price_unresolved・excluded 以外）が無い行」の集合 ②前 偽→後 真 0 行 ③〆の形でない行の変化 0 行 ④前 真→後 偽 の各行で、在庫表（まとめあり・なし）に同じ窓口・同じ商品・別の投稿の行が 0 ⑤在庫表の row_key の集合が前後で同じ。範囲は「sm.is_active かつ直近30日」と7日。設計時点の見込みは30日で 11 行外れる。8〜14 を外れたら止めて理由を調べる |
| T3 速さ | §7 T3 と同じ測り方で、要確認一覧1ページ目の中央値が「変更前 ×1.2 + 100ms」以内（副問い合わせが1つ減るので遅くならない見込み。試算の絞った問い合わせで旧 605〜618ms・新 501〜524ms、recon4 timing.txt） |
| H1〜H4 本番 | デプロイ後、ai_ro で T2 と同じ判定を流し、外れる・残るの行が T2 と同じ（新しい投稿で増えた分は内訳を書く） |
| H6 点検 | 12-8 の定期実行が agent-console の一覧に enabled で出て、初回の回で verdict.md と REPORT.md の1行ができ、返答が前例（1bba6dbe・60ebb886 の返答の手順）と同じ3行の型で来る |

### 12-7. 影響と弊害

| 影響・弊害 | 対処 |
|---|---|
| 解析が商品や状態を取り違えた〆も、在庫表に在庫が無ければ人の目に触れない（PO 判断で受け入れ） | 12-8 の毎朝の点検で、前日に自動で外れた〆を原文と照らす。誤りがあれば PO に返す |
| 〆の行の状態を解析が取り違えた場合（本当に〆なのは同じ投稿の別の状態の方）、(q) の形で〆は外れ、売り切れた方の在庫は在庫表に出たまま残る | 12-8 の (c) 状態の照合で、同じ投稿に別の状態の在庫がある〆は必ず原文と照らす（点検の対象に「同じ投稿の別の状態の在庫あり」の印を付ける） |
| 窓口単位で見るので、同じ仕入元が別の窓口で同じ商品を出していても〆は外れる（(g) の反転）。在庫表の表示は仕入元単位（`backend/app/services/tcg_distribution_svc.py:332`） | 本番で窓口を2つ以上持つ仕入元は 294 のうち 10。外れる 11 行の仕入元3つはどれも窓口1つで、同じ仕入元・別の窓口の在庫表の行は 0（recon7）。T2 で、外れる行ごとに「同じ仕入元・別の窓口の在庫表の行」の数も出し、1以上なら止めて PO に返す |
| 値段つきの完売は、値段の読み違い（実は売り中）でも外れる | status が sold out の行だけが対象。売り中の行は形に当たらない。点検で原文の〆・完売の語を確かめる |
| 初めての〆（前の在庫が無い）も外れる | PO 判断。〆の行は在庫表にもともと出ないので、在庫表は変わらない |
| 旧エンジンの再解析（`backend/app/services/tcg_analyzer_svc.py:1801`）で保存する理由も、新しい規則の値になる | §6 と同じ（意図どおり） |
| 同じ投稿の同じ状態の在庫（r）は残す | 〆と在庫が同じ投稿・同じ状態で並ぶのは解析の食い違いの疑いなので人が見る |

戻し方: この PR を revert する（DB の変更なし）。接触面（§6 の6面）は §6 と同じ（API の件数・画面の行が減るだけ）。

### 12-8. 毎朝の点検（定期実行）

- 名前「〆の自動判定 毎朝点検」。agent-console の定期実行、毎日 10:00 JST、担当 opus-designer。前例 1bba6dbe・60ebb886 と同じ形（本番への書き込み・PR・再解析をしない。読み取りと記録だけ）
- 登録は Opus が `ac-routine.mjs add` で行う（前例どおり createdBy agent）。登録の時点はデプロイと H1〜H4 の確認の後
- 台本: 実装の便で Sonnet が W=~/CC報告ファイル-keep/shime-auto-check/ に daily_check.sh を作る（T2 と同じ道。origin/main の review_joins(shime=True) を Python で組み、表名を ai_ro のビュー名に置き換え、reader 鍵で流す。書き込みなし）。出力は W/daily/<YYYYMMDD_HHMM>/rows.txt（ei 先頭8桁・投稿日時・窓口・商品名・状態名・値段・原文 line_start〜line_end・同じ投稿に別の状態の在庫があるかの印）
- 対象: sm.is_active かつ直近72時間の投稿で、〆の形かつ cr_shime.settled が真の行。W/checked_ids.txt に載っている ei は除く（48時間で相手の在庫が古くなり後から外れた行も、投稿時刻にかかわらず72時間の窓で拾う）。初回は直近72時間すべて
- 判定: Opus が各行を (a) 原文のその行に〆・完売・売切・sold の語がある (b) 商品名が原文の品名と合う (c) 状態が原文と合う（同じ投稿に別の状態の在庫の印がある行は必ず原文で確かめる）の3点で ○×不明 を付け、W/daily/<フォルダ>/verdict.md に表で残し、点検した ei を checked_ids.txt に足す
- 記録: W/REPORT.md の末尾に1行（例「- 2026-10-22 10:00 JST: 点検 n 行・○ m・× k・不明 u」）。× と不明が0の回は W/clean_days.txt の数に1を足し、1つでもあれば0に戻す
- 記録先はリポジトリ外。仕入元の原文は記録ファイルだけに置く
- PO への返答は3行の型。全部○なら「決めることはありません」。×・不明があれば行を記録し、原因を Sonnet に読み取りで調べさせ、直し方の番号選択肢を出して止まる。自分では直さない
- 既知の漏れ: 〆より24時間以上後の投稿の在庫が 48時間で古くなって初めて外れる〆は、外れた時点で72時間の窓を過ぎるので点検に入らない（在庫表への影響はない）
- 止める条件: clean_days.txt が 14 になった回、または 2026-11-10 以降の回で、記録のあと ac-routine.mjs list で id を確かめて disable し、REPORT.md に総括1行（前例 60ebb886 の手順3と同じ）
- 通知は Discord を使わない（前例どおり agent-console の会話に返す）

### 12-9. 別の作業（同じ便に入れない）

肉ルフィ（424590）の商品区分をプロモパック系にする件は本番データの変更なので、この PR と分ける。前例 ~/CC報告ファイル-keep/promo-pack-3items-20261019/ の台本を写して作り（区分が今は空の点・件数1件に合わせる）、確かめ運転のあと PO が `!` で流し、再解析する。20f9cb54 は状態不明・単位不明も持つので、区分を入れただけで要確認から外れるかはまだ確かめていない（再解析の後に見る）。

### 12-10. 計画票

| 順 | 作業 | 担当 | 完了の印 |
|---|---|---|---|
| 1 | 設計審査 | Reviewer（opus） | APPROVE |
| 2 | PO 実装承認 | PO | 番号の返事 |
| 3 | 実装カード・実装・T1 | Opus・Sonnet | PR 起票 |
| 4 | T2・T3 | Sonnet（reader 鍵） | 生出力と合否 |
| 5 | 審査・GO 記録・マージ | Reviewer（opus）・Opus（ADR-1003） | `VERDICT: APPROVE on <HEAD> PR #N`・merge commit |
| 6 | デプロイ確認・H1〜H4 | Opus・Sonnet | deploy success と ai_ro の判定 |
| 7 | 定期実行の登録・H6 | Opus | 一覧に enabled・初回の返答 |
| 8 | 結果の記録 | Opus | 本書に追記 |

ADR: 作らない（§9 と同じ理由。規則の正本は本書 12-3）。外部事例: 使わない（§「外部・過去事例の参照と我々への応用」と同じ理由。社内の前例は定期実行 1bba6dbe・60ebb886）。維持の仕組み: §「維持の仕組み」に、T1 の (p)〜(t) と、点検の定期実行（期限つき）を足す。

### 12-11. 審査

- Opus 自己審査（独立した第二者のレビューではない）: 試算 recon6（外れる 11・戻る 0）、在庫表との突き合わせ（別の投稿 0・同じ仕入元の別の窓口 0、recon6・recon7）を確かめて Reviewer に出した。
- Reviewer（opus）1回目: REVISE（中6・軽4。T2 の比べる相手、行番号、PO の言葉と案 E の説明、G3・G4 の置き換え注記、状態の取り違えの弊害、毎朝点検の手順）。すべて反映。
- Reviewer（opus）2回目: APPROVE（2026-10-20）。12-4 を作業台の写しに当てて組み立て、試算の式と一致、OFFSET 0 は素3・fenced10、shime=False の文字列は1バイトも変わらない。軽5件（recon7 の反映、:332、§3 を指すコメント2か所、(g) の時刻、72時間の漏れ）は本書へ反映済み。生出力 ~/CC報告ファイル-keep/shime-remaining-20261020/review1・review2。
- 未確認: CI（pg）での試験の実行。T2・T3 は実装 PR の HEAD で行う。

### 12-12. 結果（2026-10-20。12-10 順4〜8）

- 実装: PR #4559 を merge（merge commit 6b17ab8ea、2026-10-20 02:52Z）。最後の HEAD 4fd63ef54 で Reviewer（opus）`VERDICT: APPROVE`。GO は ADR-1003 の委任発行（PR 本文 GO記録）
- T2（PR の HEAD 37bf1b0fd・同じ読み取りトランザクション。最後の HEAD 4fd63ef54 との差に判定のコードは含まれない）: ①外れる行 30日10行・7日9行で、条件で直接数えた集合と一致 ②戻る行 0 ③〆の形でない行の変化 0 ④外れる各行で在庫表の同じ窓口・同じ商品・別の投稿の行 0、同じ仕入元・別の窓口・同じ商品の行も 0 ⑤在庫表の row_key の集合は前後で同じ。設計時点の見込み11行との差1行（8179e1e0）は、その投稿が sm.is_active=false になり範囲外になったため。設計時点の 5642ad0b・018e101c が範囲に入らなかったのは投稿が差し替えられたため（差し替え後の投稿も確認済み）
- T3: 要確認一覧1ページ目の中央値 1329 → 1457ms（基準 1694.8ms）で合格。ただし 12-6 の「遅くならない見込み」とは逆に約 10% 遅くなった（原因はまだ確かめていない）
- デプロイ: #4559 の deploy（run 39361249082、02:52〜02:58Z）は、別の migration（20261002_170000）の適用中のデッドロックで失敗し、ai_ro のビューは消えたまま（ログ「views stay dropped」）になった。前後の deploy（02:04Z・02:28Z・03:38Z 開始）は別の便の migration（20261019_100000、line_conditions_value_group の check 制約違反）で失敗していた。別のセッションの修正 #4563（0e911dfca、03:55Z マージ）の後、deploy 39366838514（head 0e911dfca、6b17ab8ea を含む）が 03:55〜04:02Z に success。続く #4562（2cacc774a）も deploy 39368368807 で success。ai_ro は 510 ビュー（04:14Z に確認）
- H1〜H4（04:17Z、ai_ro、origin/main 2cacc774a のコード）:
  - H1: 範囲（sm.is_active かつ直近30日）の「Sold out・excluded」で要確認に残るのは7行。どれも〆の規則以外の理由（未登録の商品・状態不明・単位不明・余白行の疑い）を持つ。〆の規則だけで残る行は 0
  - H2: T2 で外れた10行のうち範囲内の1行（6c4c3bfa）は今も外れ、在庫表の同じ窓口・同じ商品・別の投稿の行は 0。残り9行は sm.is_active=false で範囲外
  - H3: 範囲内に該当行 0 のため本番では観測できず。動きは T1 (t) で守る
  - H4: 2928ea55 は余白行の疑いで要確認のまま（合格）。20f9cb54・018e101c は sm.is_active=false で範囲外
  - 生出力: ~/CC報告ファイル-keep/shime-remaining-20261020/h1/（社外秘。リポジトリに入れない）
- H6: 定期実行「〆の自動判定 毎朝点検」を登録（id f94f9a62、enabled、毎日 10:00 JST、opus-designer）。台本 daily_check.sh の初回手動実行は exit 0・46行（判定は定期実行の初回で行う）。初回の返答は 2026-10-21 10:00 JST
- 残り: 次の便で、①状態の書いていない〆を残りの状態すべてに当てる ②完売の語だけの余白行を余白行の疑いから外す ③参照した在庫の行から単位を写す、の3件を設計・審査する（PO「1」）。肉ルフィの区分の件は 12-9 のまま

## 13. 改訂3 — 〆の残り3件（状態の書いていない〆・完売の語だけの余白行・〆の単位）（2026-10-20）

状態: B・C は Reviewer（opus）APPROVE（ef159c150）。A は PO「2」を受けて §13-10 で設計し直し、Reviewer（opus）第3回 APPROVE（37048d94e）。PO 実装承認済み（2026-10-20「1」、§13-11）。実装は PR #4574 でマージ済み（§13-12）。
材料の原本: ~/CC報告ファイル-keep/shime-next3-20261020/（recon1〜recon4・カード。原文は社外秘のためこの文書に貼らない）。現在地は docs/handoff/shime-review-exclude/recon.md「改訂3」。

### 13-1. 目的と成功条件

PO の言葉（2026-10-20）: 「その投稿者の最新の在庫情報から特定させる仕組みは導入されている？その情報から特定すればいいのでは？」「システムが完売と正しく解析したなら要確認に回す必要は無い、定期実行で確認すれば良い項目だと考えるがどうか？」「これもその提供者の最新の在庫情報から完売にする商品を解く適してほしいが出来るか？」

| 件 | 中身 | 合格の条件（○×） |
|---|---|---|
| A | 状態の書いていない〆を、その仕入元の〆より前の最新の在庫の投稿から決める（§13-10。当初の「全部の状態に当てる」は原文の照合で不採用） | A1 直近60日で段B の相手が変わる〆の集合が {83d61b3d}（Sealed box → Case） A2 〆の確認済み扱いで、参考 40 件のうち偽→真が {0c91e2e0, 5642ad0b}、今の要確認の一覧の〆の形の行で真→偽 0（§13-10-3） |
| B | 値段の行より後ろの「完売しました。」のような完売の語だけの行を、余白行の疑い（possible_footer_line）にしない | B1 直近30日（recon1 の窓。終点 2026-10-20）で possible_footer_line が外れる行の集合が {2928ea55} だけ（In Stock・Pre-order の行で外れるもの 0） B2 その行の status・商品・状態・値段・数量・名前は変わらない |
| C | 〆の行に単位が書かれていないとき、完売の相手（参照した在庫の行）の単位が1種類なら、その単位を写して単位不明（unit_unknown）を外す | C1 直近60日で該当は 39300bc2・018e101c の2行（どちらも参照先は Set）。2行とも、再解析すると unit が Set・unit_resolved が真・review_reasons から unit_unknown が消える C2 相手の単位が2種類以上・相手の単位が無い・〆の行に単位がある・人が判断した、のどれかなら何も変わらない |
| 共通 | 在庫表・配信・GAS の SQL は1文字も変わらない | tcg_distribution_svc.py の diff が 0 行。review_joins は cr_shime（shime=True の側）の相手の条件1か所だけが変わり、shime=False の SQL は1文字も変わらない（`backend/tests/test_inventory_distribution_rows.py` の固定値が変わらずに通る） |

### 13-2. 現在地（recon 改訂3。file:line は origin/main 109503d77）

A（状態の書いていない〆）
- 【事実】段B の規則12e は取り残しの状態が1種類のときだけ相手を決める（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:411-413`）。2種類以上なら相手なし。
- 【事実】直近60日・is_active 不問で、取り残しが2種類以上の〆は 22 行。sm.is_active の範囲では 0 行。22 行とも要確認に出ていない（needs_review 真 0/22。recon1・recon2）。
- 【事実】〆の後7日以内の、同じ商品の次の在庫投稿で再掲されたかを数えた（recon2 SUMMARY.md A）: (a) どの取り残しも再掲なし 3 （「全部に当てる」を支える）／(b) 〆の既定の状態は再掲なし・ほかの取り残しは再掲あり 3 （反する）／(c) 既定の状態も再掲あり 13／(d) 次の在庫投稿なし 3。比較のため今の規則（取り残し1種類、141 行）でも数えると (c) が 77 行あり、再掲の有無は正しさの判定に使えない。判定に使えるのは (a) と (b) だけで、3 対 3。
- 【事実】規則12 の設計（docs/handoff/v102-shime-direct-inherit/design.md）は「前の状態を引き継ぐ」案を、原文の照合で2件の誤り（箱の〆をパックの在庫に当てる・シュリありの〆をシュリなしの在庫に当てる）が出たため採らなかった。

B（完売の語だけの余白行）
- 【事実】余白行の疑いは `backend/app/services/gemini_raw_copy_v101.py:1070-1086` の _apply_f5 が作る。最後の price_line より後ろで役割が名前の行を名前に使わず（ROLE_IGNORED）、footer に足す。呼び出しは :1358 の1か所。理由にするのは :1288（_item_reasons）、件の review に足すのは :1403。
- 【事実】完売の語の行が名前でなく在庫（ROLE_STOCK）になるのは、語と完全に一致するときだけ（:407-412 _is_stock_line）。「完売しました。」は名前の役割になり、余白行の疑いになる。
- 【事実】完売の語は本番の public.tcg_status_master の effect=EXCLUDE・LITERAL の11語（soldout・在庫なし・売り切れ・完売・欠品・sold・売切・SOLD OUT・一旦ストップ・〆・ストップ）。ctx.sold_out_words に入る（:368-372・:383）。
- 【事実】直近30日の possible_footer_line 54 件のうち、余白行が「完売の語＋（しました等）＋句読点」だけなのは 2928ea55 の6行目だけ（recon4 D5）。01c078bb は投稿に値段の行が無く、5行目は「〆」と完全一致で在庫の役割。余白行の疑いは他の行から来ており、product_multiple も持つので B では外れない。In Stock・Pre-order で当たる行は 0（recon2 B）。
- 【事実】2928ea55 は sm.is_active で、理由は possible_footer_line だけ。今も要確認に出ている（§12-12 H4）。

C（〆の行の単位）
- 【事実】単位不明の理由は `backend/app/services/gemini_raw_copy_v101.py:1289-1290`（row["unit"] が none のとき）。保存の列は `backend/app/services/line_analysis_v102_svc.py:720`・:739-740（unit_id・unit_canonical・unit_resolved）。
- 【事実】要確認の一覧は、保存した review_reasons に加えて、unit_resolved が真でなければ unit_unresolved を足す（`backend/app/services/tcg_condition_review_svc.py:261`・:268）。単位を写すときは unit_resolved も真にしないと要確認から外れない。
- 【事実】完売の相手は段A（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:249-267` _targets_of）と段B（:415）が SoldoutTarget で作り、件の soldout_targets に4項目（product_id・condition_id・ref_message_id・ref_line）だけ載せる（`backend/app/services/gemini_raw_copy_v101.py:1215-1217`・:1234-1237）。在庫の行の読み込み（`backend/app/services/line_analysis_v102_svc.py:1350-1362` _STOCK_ITEMS_SQL・:1388-1403）は unit_id を読まない。
- 【事実】保存の時に相手を使うのは `backend/app/services/line_analysis_v102_svc.py:877-898` _apply_soldout_targets（状態を先頭の相手で上書きし、状態の理由だけ外す）。呼び出しは :1129-1132 の1か所。
- 【事実】直近60日の SOLDOUT_REF・SOLDOUT_INHERIT の〆 22 行のうち、unit_unknown は2行（39300bc2・018e101c）。参照先の単位は 22/22 で1種類に決まる。2行の参照先はどれも Set（unit_id 13）（recon2 C・recon4 D6。参照先は保存されていないので近似）。2行とも sm.is_active=FALSE（差し替え済み）。
- 【事実】〆の行の単位は、配信（Sold out・excluded を外す。`backend/app/services/tcg_distribution_svc.py:242-249`・:370・:484）、完売一覧（ei.raw_unit だけ。`backend/app/services/tcg_sold_out_results_svc.py:39`）、〆の確認済み扱い（〆自身の単位を見ない。`backend/app/services/tcg_condition_review_svc.py:186-199`）、付け替えの鍵（(product_id, condition_id)。`backend/app/services/tcg_analyzer_svc.py:2094-2100`）のどれにも使われない（recon2 C）。

### 13-3. 設計

#### A — 不採用を推奨（PO 判断）→ PO「2」により §13-10 で置き換え

- 推奨: 作らない。理由: 裏取りで支える行と反する行が 3 対 3 で、正しさを示せない。今の範囲（sm.is_active）で該当する行は 0 で、要確認に出ている行も 0。規則12 の設計で「前の状態を引き継ぐ」案が原文の照合で誤りを出した前例がある。
- 代わりの守り: §12-8 の毎朝の点検が、自動で外れた〆を原文と照らす。取り残しが2種類以上の〆は今も相手なしで、在庫表の行は人の目と点検に残る。
- PO が採用を選んだ場合: 別の便で設計し直す（全部の状態に当てる・〆の既定の状態だけに当てる、の比較を原文の照合で行う）。この便には入れない。

#### B — 完売の語だけの行を余白行の疑いにしない（`backend/app/services/gemini_raw_copy_v101.py`）

変更前（:1070-1086）
```python
def _apply_f5(
    items: list[dict], roles: list[dict[int, str]],
) -> tuple[list[dict[int, str]], dict[int, list[dict]], list[int]]:
    """F5 最後の price_line より後ろの行で、役割が名前のものは名前に使わない。戻り値の最後は possible_footer_line。"""
    ...
            if n > last_price_line and role_map[n] == ROLE_NAME:
                updated[n] = ROLE_IGNORED
                footer.add(n)
                fixes.setdefault(i, []).append(_fix("F5", n, "最後の price_line より後ろの行を名前に使わない"))
```

変更後
```python
_SOLD_OUT_SENTENCE_TAIL = r"(?:しました|しております|です|となりました|になりました|致しました|いたしました)?[\s。、.,!]*"


def _is_sold_out_sentence(text: str, ctx: V101Context) -> bool:
    """完売の語だけの行（語＋丁寧な言い回し＋句読点。例「完売しました。」）。余白行の疑いにしない（design.md §13-3 B）。"""
    stripped = _nfkc(text).strip().lower()
    return any(w and re.fullmatch(re.escape(_nfkc(w).lower()) + _SOLD_OUT_SENTENCE_TAIL, stripped) for w in ctx.sold_out_words)


def _apply_f5(
    items: list[dict], roles: list[dict[int, str]], lines: list[str], ctx: V101Context,
) -> tuple[list[dict[int, str]], dict[int, list[dict]], list[int]]:
    """F5 最後の price_line より後ろの行で、役割が名前のものは名前に使わない。戻り値の最後は possible_footer_line（完売の語だけの行は除く）。"""
    ...
            if n > last_price_line and role_map[n] == ROLE_NAME:
                updated[n] = ROLE_IGNORED
                if not _is_sold_out_sentence(lines[n - 1], ctx):
                    footer.add(n)
                fixes.setdefault(i, []).append(_fix("F5", n, "最後の price_line より後ろの行を名前に使わない"))
```
- 呼び出し :1358 を `name_roles, f5_fixes, footer_lines = _apply_f5(items, roles, lines, ctx)` にする。ほかに _apply_f5 を呼ぶ所があれば（試験を含む）同じ引数にする。
- NFKC の後なので、全角の「！」「，」「．」は半角になる。句読点の集合は `[\s。、.,!]` で足りる。
- 変えないこと: 行の役割（ROLE_IGNORED のまま。名前に使わない）、F5 の fixes の記録、status の決め方（:926 resolve_status_v2 は件の行全体の文字で決める）、v10.1（v102_fixes=False）の出力。
- この結果、件の review から possible_footer_line が消え、投稿の post_review に孤立した余白行として出ることもなくなる（:1406-1408 は flags の possible_footer_line を使う）。

#### C — 〆の行の単位を完売の相手から写す

1. `backend/app/services/gemini_raw_copy_v102_soldout_ref.py`
   - StockItem（:55-62）に `unit_id: int | None = None` と `unit_canonical: str = ""` を足す（condition_canonical の後ろ。既定値つきなので今の生成箇所は変えずに動く）。
   - SoldoutTarget（:73-81）にも同じ2つを足す（condition_canonical の後ろ）。
   - _targets_of（:256-266）: pairs に it.unit_id・it.unit_canonical を足し、`SoldoutTarget(product_id, condition_id, row.message_id, row.line_no, canonical, unit_id, unit_canonical)` にする。
   - decide_soldout_inherit（:415）: `SoldoutTarget(product_id, stock.condition_id, post.message_id, min(stock.lines, default=0), canonical, stock.unit_id, stock.unit_canonical)` にする。
2. `backend/app/services/line_analysis_v102_svc.py`
   - _STOCK_ITEMS_SQL（:1351-1352）の SELECT に `ar.unit_id, COALESCE(ar.unit_canonical, '') AS unit_canonical` を足す（WHERE・ORDER BY は変えない）。
   - _load_stock_items（:1398-1401）: `StockItem(..., str(r.condition_canonical or ""), int(r.unit_id) if r.unit_id is not None else None, str(r.unit_canonical or ""))`。
3. `backend/app/services/gemini_raw_copy_v101.py`
   - _apply_soldout_inherit（:1215-1217）と _soldout_ref_row（:1234-1237）の相手の dict に `"unit_id": t.unit_id, "unit_canonical": t.unit_canonical`（inherit 側は d.unit_id・d.unit_canonical）を足す。
4. `backend/app/services/line_analysis_v102_svc.py` の _apply_soldout_targets（:877-898）

変更前（:886-889）
```python
    targets = item.get("soldout_targets") or []
    if not targets or _has_human_judgement(decision):
        return values
    condition_id = targets[0]["condition_id"]
```

変更後
```python
    targets = item.get("soldout_targets") or []
    if not targets or _has_human_judgement(decision):
        return values
    values = _with_target_unit(values, targets)
    condition_id = targets[0]["condition_id"]
```
  そして _apply_soldout_targets の直前に足す:
```python
# 単位不明の理由（gemini_raw_copy_v101._REVIEW_UNIT_UNKNOWN と同じ値。前例 v102_buyback_unit_svc.py:42）
REASON_UNIT_UNKNOWN = "unit_unknown"


def _with_target_unit(values: dict, targets: list[dict]) -> dict:
    """〆の件に単位が無く、完売の相手の単位が1種類に決まるとき、その単位を写して unit_unknown を外す（元の values は変えない。design.md §13-3 C）。"""
    units = {(t.get("unit_id"), t.get("unit_canonical") or "") for t in targets}
    if values["unit_id"] is not None or values["unit_canonical"] is not None or len(units) != 1:
        return values
    (unit_id, unit_canonical), = units
    if unit_id is None or not unit_canonical:
        return values
    remaining = [r for r in _split_reasons(values["review_reasons"]) if r != REASON_UNIT_UNKNOWN]
    return {
        **values, "unit_id": int(unit_id), "unit_canonical": unit_canonical, "unit_resolved": True,
        "review_reasons": REASON_SEPARATOR.join(remaining) if remaining else None, "needs_review": bool(remaining),
    }
```
- docstring（:881-885）に「単位が無い件は、相手の単位が1種類なら写す（§13-3 C）」の1文を足し、「状態の名前が引けない件は何も外さない」（:882）を「状態の名前が引けない件は状態の理由を外さない（単位の写しは先に済む）」に、:896 付近のコメント「理由も needs_review も変えない」を「状態の理由も needs_review も変えない（単位の写しの分は済んでいる）」に直す。
- 〆の行に単位の文字があるのに単位の表に無い件（unit_canonical はあるが unit_id が None）は写さない（〆に書いてある単位を上書きしない）。
- 単位を写した後の状態の上書き（:889-898）は、写した後の values の review_reasons から状態の理由を外す（今の式のまま。values を置き換えたので自然にそうなる）。
- 人の判断（商品・状態）がある件は今と同じく何もしない（:887）。人が単位を直した件は apply_value_overrides（`backend/app/services/v102_human_decisions_svc.py:538-543`）で unit_id が入っているので写さない。
- _extra_targets（:901-910）は (product_id, condition_id) だけを比べるので、dict に項目が増えても動きは変わらない。analysis_soldout_extra_targets に書く列も変わらない（:921-935）。
- 変えないこと: 〆の行に単位が書かれている件（12f。unit_id か unit_canonical が入っている）、相手の単位が2種類以上の件、相手が無い件。写した単位は、_apply_soldout_targets（:1129）より前に走る処理（単位と価格の確認 :1125・:958-965、買取の単位、規則13）には見えない（〆の行は Sold out なので、これらの結果は今と同じ）。
- 【事実】_inherit_price（`backend/app/services/line_analysis_v102_svc.py:1302-1347`）は unit_id を読まず、status が Sold out ならすぐ戻る（:1314）。写した単位が値段の引き継ぎを変えることはない（審査で確認）。

### 13-4. 代替案

| 案 | 中身 | 判断 |
|---|---|---|
| A-1（推奨・§13-10 で置き換え） | A は作らない | 3 対 3 で正しさを示せず、今の範囲の該当 0 |
| A-2 | 取り残しの状態すべてに〆を当てる | 不採用。原文の照合で 22 行中 13 行が誤り（§13-10-1） |
| B-1（採用） | F5 で完売の語だけの行を footer に足さない | 理由だけが変わり、役割・値は変わらない |
| B-2 | 完売の語だけの行を在庫の役割（ROLE_STOCK）にする | 不採用。_is_stock_line は名前・状態・数量の取り出し全体に効き、影響が F5 より広い |
| B-3 | 要確認の一覧の側（review_joins）で、〆の確認済み扱いのとき possible_footer_line も外す | 不採用。余白行の疑いは「名前を取り違えたかも」の印で、〆と関係のない行（例「・買取品」）まで外れる |
| C-1（採用） | 相手の単位が1種類なら写す | 保存の値が実物に近づき、unit_unknown と unit_unresolved の両方が正しく消える |
| C-2 | 相手がある〆の行には unit_unknown を付けない（単位は空のまま） | 不採用。unit_resolved が偽のままなので、要確認の一覧で unit_unresolved が残る（`backend/app/services/tcg_condition_review_svc.py:261`） |
| C-3 | 何もしない | 不採用。PO の願い（最新の在庫から決める）に合わない |

### 13-5. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| T1 B の試験 | `backend/tests/test_gemini_raw_copy_v101.py` に足して CI で通る: (u) 「商品A／3BOX@1,000円／完売しました。」で possible_footer_line が []、名前は「商品A」、F5 の fixes は [("F5", 3)]（_STATUS に 完売 がある） (v1) 同じ形で最後の行が「完売です！」なら [] (v2) 同じ形で最後の行が「完売品あり」なら [3] のまま（「〆」だけの行はもともと在庫の役割で疑いにならない。:409） (w) 「・買取品」の既存の試験（:685・:1010）は変えずに通る (x) (u) の status は sold_out のまま（件の行全体で決まる。v101.py:906・:926）で、status・quantity・price・unit・condition は origin/main のコードで同じ入力を流した出力と同じ。_apply_f5 を直接呼ぶ試験があれば新しい引数で通る |
| T1 C の試験 | `backend/tests/test_line_analysis_v102_svc.py` に足して CI で通る: (y) values の unit_id が None・review_reasons が "unit_unknown" で、相手が全て unit_id 13・"Set" → unit_id 13・unit_canonical "Set"・unit_resolved 真・review_reasons None・needs_review 偽 (z) 相手の単位が2種類 → 単位も理由も変わらない (aa) values に単位が入っている（今の _soldout_item の BOX）→ 単位は変わらない (bb) 人の判断がある → 今の試験（:437-445・:556-559）どおり values そのもの (cc) 相手の dict に単位が無い（今の _TARGETS）→ 今の試験が全部変えずに通る（:418-559）。`backend/tests/test_gemini_raw_copy_v102_soldout_ref.py` に: (dd) _targets_of と decide_soldout_inherit が StockItem の unit_id・unit_canonical を SoldoutTarget に運ぶ（:568・:649・:655 の既存の期待は既定値のまま通る）。:669 の soldout_targets の4項目ぴったりの期待は `"unit_id": None, "unit_canonical": ""` を足した6項目に書き換える（test_v102_value_overrides.py:184 は t.get で読むので変えない）。_load_stock_items が unit_id・unit_canonical を読む（pg の試験があれば足す。無ければ SQL の文字列に ar.unit_id が入ることを確かめる） |
| T2 B の本番の当て | 実装の HEAD のコードで、直近30日（B1 と同じ窓）の possible_footer_line の件（sm.is_active 不問）の投稿を、保存済みの Gemini の写しから v102 の取り出しだけやり直し（Gemini は呼ばない・書き込まない）、possible_footer_line が外れる件の集合 = {2928ea55} で、In Stock・Pre-order の件は 0。名前・status・値段・数量の差が 0 |
| T2 C の本番の当て | 同じやり方で 39300bc2・018e101c の job をやり直し（書き込まない）、_apply_soldout_targets の後の values が unit Set・unit_resolved 真・unit_unknown なし。直近60日の SOLDOUT_REF・SOLDOUT_INHERIT の残り 20 行は単位・理由の差が 0 |
| 共通 | `git diff origin/main -- backend/app/services/tcg_distribution_svc.py` が 0 行。`backend/app/services/tcg_condition_review_svc.py` の差は §13-10 A-2 の1か所（cr_shime の相手の条件）だけ。`backend/tests/test_inventory_distribution_rows.py` の固定値が変わらずに通る |
| A | §13-10-3 の T1 A-1・T1 A-2・T2-A1・T2-A2・本番の後 |
| 本番の後 | デプロイ後、2928ea55 の job だけを再解析する（本番の書き込みなので台本と確かめ運転の後に PO が `!` で流す）。その後 ai_ro で、2928ea55 の review_reasons に possible_footer_line が無く、要確認の一覧（review_joins）に出ない。新しい投稿は、毎朝の点検（§12-8）で余白行・単位の写しも原文と照らす |

T2 のやり直しの道が今の再解析の台本（~/CC報告ファイル-keep/nikuluffy-promo-20261020/reanalyze_nikuluffy.py）の MODE=dryrun で足りるかは、実装カードで Sonnet が確かめる。足りなければ、書き込みのない別の台本を作る（本番に書かないことを台本の先頭で確かめる）。

### 13-6. 影響と弊害

| 影響・弊害 | 対処 |
|---|---|
| B: 完売の語だけの行が、実は別の商品の完売の知らせだった場合も、余白行の疑いが付かない | status は今も件の行全体で決まっていて、この変更で変わらない。〆の確認済み扱い（§12-3）と毎朝の点検（§12-8）が〆・完売の行を原文と照らす |
| B: 語のあとに商品名などが続く行（例「完売 ○○」）は今までどおり疑いになる | 意図どおり（完全一致だけを外す） |
| C: 相手の単位が誤っていると、〆の行にも誤った単位が入る | 〆の行の単位は配信・完売一覧・付け替えに使われない（13-2 C）。表示されるのは要確認と解析結果の画面だけ |
| C: 段A の相手が複数で単位が揃うときも写す | 22/22 で1種類に決まっている（recon2）。2種類以上なら写さない |
| A を作らない: 取り残しが2種類以上の〆は相手なしのまま | §13-10 で置き換え（A を作る。影響は §13-10-4） |

戻し方: この PR を revert する（DB の変更なし。写した単位は次の再解析で元に戻る）。

### 13-7. 計画票

| 順 | 作業 | 担当 | 完了の印 |
|---|---|---|---|
| 1 | 設計審査 | Reviewer（opus） | APPROVE |
| 2 | A（§13-10）・B・C まとめての実装承認 | PO | 番号の返事（1回に1件） |
| 3 | 実装カード・実装・T1 | Opus・Sonnet | PR 起票（release/shime-next3-impl） |
| 4 | T2 | Sonnet（reader 鍵・書き込みなし） | 生出力と合否 |
| 5 | 審査・GO 記録・マージ | Reviewer（opus）・Opus（ADR-1003） | `VERDICT: APPROVE on <HEAD> PR #N`・merge commit |
| 6 | デプロイ確認・2928ea55・83d61b3d の再解析（PO `!`）・本番の後の確認 | Opus・Sonnet・PO | deploy success と ai_ro の判定 |
| 7 | 結果の記録 | Opus | 本書に追記 |

ADR: 作らない（§9 と同じ。規則の正本は本書と docs/handoff/v102-shime-direct-inherit/design.md。FEATURE-INDEX.md に該当なし、recon1）。外部事例: 使わない（社内の規則の微修正で、比べる外部の事例が無い。社内の前例は規則12 の設計と §12）。維持の仕組み: T1 の (u)〜(dd) と、§12-8 の毎朝の点検（期限つき）。

### 13-8. 審査

- Opus 自己審査（独立した第二者のレビューではない）: B は 13-2 の当たり 1 行（2928ea55）と In Stock・Pre-order 0 行、C は 2 行・参照先の単位 1 種類を確かめた。C は要確認の一覧が unit_resolved から unit_unresolved を足す（`backend/app/services/tcg_condition_review_svc.py:261`）ので unit_resolved も真にする形にした。A は 3 対 3 のため推奨を不採用にした。
- 未確認: T2 のやり直しの道。CI（pg）での試験の実行。A は §13-10-5。
- Reviewer（opus）審査 第1回（HEAD be51da5fb）: REVISE。指摘 T-1〜T-4（試験の期待2か所の食い違い・(v) の書き方・期間の不揃い）、C-1（docstring とコメント）、C-2（〆に単位の文字がある件を上書きしない守り）、C-3（先に走る処理には見えない旨）、_inherit_price の確かめ結果。すべて本書に反映した。

### 13-9. PO の判断（2026-10-20）

- Opus の問い: 「1. A（0c91e2e0・5642ad0b の窓口の件）は作らず、2件を作る【おすすめ】／2. 3件とも作る方向で、A を設計し直す（投稿の文面と1件ずつ照らす調べ直しが要り、2件の完成も遅れる）／3. 3件とも今は作らない」。
- PO の返事: 「2」。
- これにより: A を、22 行の原文と1件ずつ照らして設計し直す（§13-10 に追記予定）。B・C は §13-3 のまま（審査 APPROVE ef159c150）で、A の再設計の審査が通ってから3件まとめて PO の実装承認を受ける。B・C の実装はまだ始めない。

### 13-10. A の設計し直し（PO「2」を受けて。2026-10-20）

この節は §13-3 A・§13-4 の A-1/A-2 の行・§13-6 の「A を作らない」の行を置き換える（それらは経緯として残す）。材料の原本: ~/CC報告ファイル-keep/shime-next3-20261020/recon5（22 行の原文と Opus の照合 JUDGE.md）・recon6（F1〜F5）・recon7（G1〜G4）。原文と仕入元の名前は社外秘のため、この文書には ei の先頭8文字だけを書く。

#### 13-10-1. 原文の照合でわかったこと（recon5 JUDGE.md・recon6 F4/F5・recon7 G4）

- 【事実】直近60日・is_active 不問の、取り残しが2種類以上の〆 22 行を原文と1件ずつ照らした。「取り残しの状態すべてに当てる」が原文どおりなのは 2 行（615c5371「全数」・cf2dcd2f「どちらも」）、原文に反するのは 13 行、今と結果が同じ 3 行、原文から決められない 4 行。→ 「全部に当てる」は採らない。
- 【事実】「全部・全数・どちらも・ALL」のような語を含む〆は60日で 5 行（F4）。そのうち取り残しが2種類以上なのは 2 行だけ。→ 語で全部に当てる規則も、件数が少なすぎて正しさを示せないので採らない（2 行は今のまま相手なし＝人の目と毎朝の点検に残る。安全側）。
- 【事実】22 行のうち、〆の前の「その商品の在庫を持つ最も新しい1投稿」の状態が1種類なのは 9 行（0c91e2e0・42d8dc23・4759052e・5642ad0b・615c5371・6d2b19b5・72183aa9・7f051447・83d61b3d）。9 行とも、その状態は原文の〆の意味と合う（615c5371 は「全数」で Case も含むため一部だけ合う）。
- 【事実】9 行のうち、保存されている状態と最新の投稿の状態が違うのは 83d61b3d だけ（保存 Sealed box・4分前の投稿は Case のみ）。F5（60日の候補 1256 行）でも、取り残しが2種類以上で保存の状態と最新の投稿の状態が違う行はこの1行（F5_diff.tsv の n_stranded=2 の1行）。42d8dc23・72183aa9 は〆の行に単位語があり、段B の候補にならない（12f）。
- 【事実】要確認の一覧に残っていた〆（0c91e2e0・5642ad0b）が外れない本当の原因は、段B ではなく〆の確認済み扱い（cr_shime）の側にある。同じ窓口・同じ商品の、もっと前の投稿の「シュリなし」の行 a42dcf92（10/18 21:11 の投稿・is_current=真・48時間以内）が「別の投稿の在庫の相手」として数えられ、settled が偽になる（G4 の「今の相手の行数」1）。その後の投稿（〆の直前の最新の在庫の投稿）にはシュリなしは載っていない。is_current は (商品, 状態) ごとに最新の行に付く（`backend/app/services/tcg_analyzer_svc.py:1956`・:2127）ので、後の投稿で書かれなかった状態の古い行は is_current のまま残る。

#### 13-10-2. 設計

A は2か所に分ける。A-1 は段B（〆の相手を決める）、A-2 は要確認の一覧の〆の確認済み扱い（cr_shime）。どちらも「〆の前の、その商品の在庫を持つ最も新しい1投稿」を正にする（PO「その投稿者の最新の在庫情報から特定すればいいのでは？」）。

##### A-1 規則12g — 取り残しが2種類以上なら、最新の在庫の投稿の状態が1種類のときそれに当てる（12d より先に見る。`backend/app/services/gemini_raw_copy_v102_soldout_ref.py`）

【事実】取り残しが2種類以上の〆 22 行は、どれも取り残しに〆の既定の状態（Sealed box）を含み、今の 12d（:406-407）で先に外れる（recon1/qA_all30_ge2.tsv の hit12d=True 22/22・recon1/A.md:42。Reviewer 第1回の R-1）。83d61b3d も取り残しは Case と Sealed box で、4分前の最新の在庫の投稿は Case だけ、原文の照合では Case が正しい（Sealed box は同じ日に再び載っている。recon5 JUDGE.md）。よって 12g は 12d より先に置く。

変更前（:405-415）
```python
        shime = _shime_condition(item)
        if any(it.product_id == product_id and it.condition_canonical == shime for p in posts for it in p.stock_items):
            continue  # 12d
        same_post = frozenset(
            _shime_condition(other) for j, other in enumerate(extracted) if j != i and other.get("product_id") == product_id
        )
        stranded = _stranded_stock(product_id, posts, same_post)
        if len(stranded) != 1:
            continue  # 12e
        (canonical, (post, stock)), = stranded.items()
        decided[i] = SoldoutTarget(product_id, stock.condition_id, post.message_id, min(stock.lines, default=0), canonical)
```

変更後
```python
        shime = _shime_condition(item)
        same_post = frozenset(
            _shime_condition(other) for j, other in enumerate(extracted) if j != i and other.get("product_id") == product_id
        )
        stranded = _stranded_stock(product_id, posts, same_post)
        canonical = _latest_single_state(product_id, posts) if len(stranded) >= 2 else None
        if canonical is None or canonical == shime or canonical not in stranded:  # 12g に当たらなければ今の 12d・12e
            if any(it.product_id == product_id and it.condition_canonical == shime for p in posts for it in p.stock_items):
                continue  # 12d
            if len(stranded) != 1:
                continue  # 12e
            (canonical, _), = stranded.items()
        post, stock = stranded[canonical]
        decided[i] = SoldoutTarget(
            product_id, stock.condition_id, post.message_id, min(stock.lines, default=0), canonical,
            stock.unit_id, stock.unit_canonical,
        )
```
そして _stranded_stock の直後に足す:
```python
def _latest_single_state(product_id: int, posts: Sequence[SoldoutRefPost]) -> str | None:
    """規則12g：その商品の在庫の行がある最も新しい投稿（posts は新しい順）の状態。1種類でなければ None。"""
    for post in posts:
        states = {it.condition_canonical for it in post.stock_items if it.product_id == product_id}
        if states:
            return next(iter(states)) if len(states) == 1 and not next(iter(states)).startswith("FLAG_") else None
    return None
```
- 12g は「取り残しが2種類以上（どれか決められない）」で、「最新の在庫の投稿の状態が1種類」「それが〆の既定の状態と違う」「それが取り残しにある（もっと新しい投稿の完売の行や同じ投稿の他の件で片づいていない）」の3つを満たすときだけ当てる。満たさなければ今の 12d・12e をそのまま通る（取り残し1種類・0種類、最新の状態が〆と同じ、の件は今と同じ結果）。
- 最新の在庫の投稿の状態が〆の既定の状態と同じとき（22 行中 8 行。9 行のうち 83d61b3d 以外）は、今どおり 12d で相手なし（保存の状態＝最新の投稿の状態で、値は変わらない）。
- 相手の行は stranded[canonical]（その状態の最も新しい投稿の、いちばん上の行）で、12e と同じ作り方。単位の2項目は §13-3 C で足すもの（C と同じ PR）。
- docstring（:396-398）の「〆と同じ状態の在庫が前にあれば決めない（12d）。取り残しの状態がちょうど1種類のときだけ決める（12e）。」を「取り残しが2種類以上で、その商品の在庫の行がある最も新しい投稿の状態が1種類・〆の状態と違う・取り残しにあるときは、その状態に決める（12g、12d より先）。それ以外は、〆と同じ状態の在庫が前にあれば決めない（12d）、取り残しの状態がちょうど1種類のときだけ決める（12e）。」に書き換える。
- 変えないこと: 12a〜12c・12f の候補の条件（_is_inherit_candidate）、12g に当たらない件の 12d・12e、段A（_targets_of）、posts の読み込み（load_soldout_ref_posts・`backend/app/services/line_analysis_v102_svc.py:1253-1270`。〆より前・48時間・最新 job・新しい順 :1244-1250）。
- 【事実】F5（60日・is_active 不問の候補 1256 行。12d は入れていない数え方）で、取り残しが2種類以上かつ最新の投稿の状態が1種類で保存の状態と違う行は 83d61b3d の1行だけ（F5_diff.tsv）。ただし F5 の候補は condition_basis が R4:単位既定・R5:パック既定の〆だけで、コードの候補（_is_inherit_candidate。語で決まっていない basis はすべて通す）の上位集合ではない（Reviewer 第2回 R2-1）。F5 の数え方では 1 行。それ以外の basis（〆の状態が空の件など）で当たる行の有無は【未確認】で、T2-A1 で確かめる。

##### A-2 〆の確認済み扱いで、〆より前の投稿の別の状態の相手は「最新の在庫の投稿」の中だけ数える（`backend/app/services/tcg_condition_review_svc.py`）

変更前（:193）
```sql
                  AND (cr_sa.condition_id = (cr_data.ar->>'condition_id')::integer OR cr_sm.id <> sm.id)
```

変更後
```sql
                  AND (cr_sa.condition_id = (cr_data.ar->>'condition_id')::integer
                       -- 別の状態の相手は、〆以後の投稿か、〆より前の最新の在庫の投稿（cr_n1）のものだけ（design.md §13-10 A-2）
                       OR (cr_sm.id <> sm.id AND (sm.line_posted_at IS NULL OR cr_sm.line_posted_at >= sm.line_posted_at OR cr_sm.id = (
                           SELECT cr_n1.id FROM {schema}.source_messages cr_n1
                           WHERE cr_n1.supplier_channel_id = sm.supplier_channel_id
                             AND cr_n1.line_posted_at < sm.line_posted_at
                             AND EXISTS (SELECT 1 FROM {schema}.extraction_jobs cr_n1j
                                 JOIN {schema}.extraction_items cr_n1i ON cr_n1i.extraction_job_id = cr_n1j.id
                                 JOIN {schema}.analysis_results cr_n1a ON cr_n1a.extraction_item_id = cr_n1i.id
                                 WHERE cr_n1j.source_message_id = cr_n1.id
                                   AND cr_n1j.id = (SELECT cr_n1l.id FROM {schema}.extraction_jobs cr_n1l
                                       WHERE cr_n1l.source_message_id = cr_n1.id ORDER BY cr_n1l.created_at DESC, cr_n1l.id DESC LIMIT 1)
                                   AND cr_n1a.product_id = (cr_data.ar->>'product_id')::integer
                                   AND cr_n1a.pid_resolved IS TRUE AND cr_n1a.condition_id IS NOT NULL
                                   AND cr_n1a.status IS DISTINCT FROM 'Sold out')
                           ORDER BY cr_n1.line_posted_at DESC, cr_n1.id DESC LIMIT 1))))
```
- 〆の投稿の line_posted_at が NULL のときは今と同じ条件（別の投稿の別の状態の相手を全部数える。安全側。Reviewer 第1回の軽い指摘）。
- 同じ状態の相手（`cr_sa.condition_id = 〆の condition_id`）は今と同じく、どの投稿のものでも数える（同じ状態が前の投稿で売られていたなら、〆はそれの可能性が高い。安全側）。
- cr_n1 は A-1 の「最新の在庫の投稿」と同じ考え（〆より前・同じ窓口・その商品の Sold out でない行を最新 job に持つ・is_active は見ない）。測定（recon7 G4a・G4_cond.sql）の n1 と同じ条件に、並びの同点を決める `cr_n1.id DESC` を足した（測定には無い。同じ時刻の投稿が2つあると n1 が測定と違いうる。【未確認】該当の有無。T2-A2 で実装の SQL そのものを流して確かめる）。
- shime=False の道（在庫表・配信・取り込みの進み具合。`backend/app/services/tcg_distribution_svc.py` 3か所・`backend/app/services/tcg_import_progress.py` 1か所）は `SELECT FALSE AS settled` の定数のままで、変わらない（`backend/tests/test_tcg_condition_review.py:907-924` が守る）。
- 変えないこと: 48時間の窓（:56 SHIME_STOCK_WINDOW_HOURS）、相手の他の条件（is_current・pid_resolved・unit_resolved・excluded でない・値段あり・FLAG でない・Sold out でない）、settled の使われ方（:262-263・:269-270）、OFFSET 0 の数（コメント1・cr_data 1・cr_shime 1。`backend/tests/test_tcg_condition_review_fenced.py:29`。足す副問い合わせに OFFSET 0 は付けない）。

【事実】測定（recon7 G4。本番 2026-10-20 08:49Z・ai_ro）は「別の状態だけでなく同じ状態の相手も n1 に絞る」形（G4_cond.sql の (i)）で行った。その形で、settled=偽の参考 40 件（差し替え済みの投稿を含む直近4日）のうち真に変わるのは 0c91e2e0・5642ad0b の 2 件だけ、今の要確認の一覧の〆の形 51 行は真→偽・偽→真とも 0。
【推測ではなく包含関係】上の設計は同じ状態の相手を絞らないので、相手の集合は「今」⊇「設計」⊇「(i)」になり、settled の真の集合は「今」⊆「設計」⊆「(i)」。よって設計で真になる〆は {0c91e2e0, 5642ad0b} の部分集合で、一覧の 51 行は変わらない（同じ時刻の投稿で n1 が違う場合を除く）。2 件の〆の状態は Sealed box、相手 a42dcf92 の状態はシュリなしで違う（G4a.out。Reviewer 確認）ので、2 件とも真になる見込み。T2-A2 で実装の SQL を測定と同じ時刻に固定して確かめる。

##### 他に考えた案（A）

| 案 | 中身 | 判断 |
|---|---|---|
| 全部に当てる | 取り残しの状態すべてに〆を当てる | 不採用。原文の照合で 22 行中 13 行が誤り（13-10-1） |
| 語で全部に当てる | 「全部・全数・どちらも」等の語があるときだけ全部に当てる | 不採用。60日で 2 行しか当たらず、正しさを示せない |
| A-1（採用） | 取り残しが2種類以上なら、最新の在庫の投稿の状態が1種類のときだけそれに当てる | 9 行とも原文と合う（1 行は一部）。保存の値が変わるのは 1 行 |
| A-2(i)（採用・同じ状態は絞らない形） | cr_shime で、〆より前の別の状態の相手は最新の在庫の投稿のものだけ数える | 要確認に残っていた 2 件が外れる見込み。一覧の 51 行は変わらない |
| A-2(ii) | (i) の n1 にさらに is_current・unit_resolved・値段あり・excluded でないを足す | 不採用。最新の投稿の行が is_current でないことがあり、0 件しか変わらない（G4） |
| 古い行の is_current を外す | 後の投稿に書かれなかった状態の行を is_current=偽にする | この便では採らない。書かれなかった状態＝売り切れとは限らない（42d8dc23 は傷ありを後で再び載せた）。在庫表・配信に効き影響が広い |

#### 13-10-3. 受け入れ基準（A）

| 基準 | 検証方法 |
|---|---|
| T1 A-1 の試験 | `backend/tests/test_gemini_raw_copy_v102_soldout_ref.py` に足して CI で通る: (ee) 83d61b3d の形: 古い投稿に Sealed box の在庫、新しい投稿に Case の在庫だけ、〆は既定で Sealed box → 相手は Case（新しい投稿の Case の行・unit の2項目も運ぶ。今は 12d で相手なし） (ef) 取り残しが No shrink box・Case（Sealed box の在庫は前に無い）、最新の在庫の投稿は Case だけ → 相手は Case (ff) 最新の在庫の投稿に2種類ある・前に Sealed box の在庫あり → 相手なし（12d） (fg) 最新の在庫の投稿が Sealed box だけ（〆と同じ）・前に Case → 相手なし（12d） (gg) 取り残しが3種類（Case・No shrink box・Searched pack）で、最新の在庫の投稿の状態 Case が〆と同じ投稿の他の件（same_post）の状態 → 12g に当たらず、取り残し2種類のまま 12e で相手なし (hh) 取り残しが3種類で、最新の在庫の投稿の状態 Case が、もっと新しい投稿の完売の行で片づいている（stranded に無い）→ 相手なし (ii) 最新の在庫の投稿の状態が FLAG_ で始まる → 相手なし (jj) 取り残し1種類の既存の試験は全部変えずに通る |
| T1 A-2 の試験 | `backend/tests/test_tcg_condition_review.py` の pg の試験に足して CI で通る: (kk) 0c91e2e0 の形: 〆の前に投稿 P0（別の状態の相手・48時間内・is_current）、その後に投稿 P1（同じ商品で〆と同じ状態・is_current=偽の行だけ。cr_n1 の条件は満たし相手の条件は満たさない）、その後に〆 → settled（price_unresolved・excluded が外れる） (ll) (kk) で P0 の行が〆と同じ状態 → 外れない (mm) 相手が最新の在庫の投稿 P1 の別の状態の行 → 外れない（今の (s) と同じ結果） (nn) 既存の (a)〜(t)・(l)〜(n) が全部変えずに通る |
| T2-A1 本番の当て | 実装の HEAD のコードで、直近60日・is_active 不問の、Sold out・excluded・商品が直接当たった〆を condition_basis を問わずすべて（候補の絞り込みはコードの _is_inherit_candidate に任せる）、保存済みの写しからやり直し（Gemini は呼ばない・書き込まない）、相手が変わる〆の集合 = {83d61b3d}（相手なし → Case）。他の行の相手の差 0。ほかの行が出たら不合格とし、その行を原文と照らして Opus が設計を見直してから進める（PO へ上げる） |
| T2-A2 本番の当て | 実装の review_joins(shime=True) と origin/main の review_joins(shime=True) を ai_ro で流す（daily_check と同じ道）。窓の `NOW()` は両方とも測定の時刻 `TIMESTAMPTZ '2026-10-20 08:49:00+00'` に置き換える（置き換えは T2 の写しの中だけ。製品コードは NOW() のまま）。recon7 の参考 40 件で settled が偽→真に変わる集合 = {0c91e2e0, 5642ad0b}、G4b の一覧の〆の形 51 行で真→偽 0。要確認の一覧の SQL の時間を、同じ時間帯に origin/main の SQL と3回ずつ測り、中央値が 1.2 倍以内 |
| 本番の後 | デプロイ後、83d61b3d の job だけを再解析する（台本と確かめ運転の後に PO が `!` で流す）。ai_ro で 83d61b3d の condition_canonical が Case。0c91e2e0・5642ad0b は投稿が差し替え済みで一覧に出ないので、次に同じ形の〆が来たとき毎朝の点検（§12-8）で確かめる |

#### 13-10-4. 影響と弊害（A）

| 影響・弊害 | 対処 |
|---|---|
| A-1: 最新の在庫の投稿の状態が、〆の意味と違うことがある（例「全数」で Case も含むのに1つに当てる） | 9 行中 1 行（615c5371）が一部だけ合う形。この行は最新の状態が〆の状態と同じなので 12g に当たらず値は変わらない。毎朝の点検が原文と照らす |
| A-1: 12g は 12d より先に見るので、前に〆と同じ状態の在庫があっても、最新の投稿が別の1状態ならそちらに当てる | 取り残しが2種類以上のときだけ。60日で当たるのは 83d61b3d の1行（原文で正しい）。T2-A1 で集合を確かめる |
| A-2: 前の投稿に別の状態の在庫がまだあるのに、最新の投稿に書き忘れていると〆が外れる | 同じ状態の相手は今どおり数えるので、〆と同じ状態の在庫が前にあれば外れない。毎朝の点検の対象 |
| A-2: 相手の副問い合わせで要確認の一覧が遅くなる | 副問い合わせは〆の形の行（CASE WHEN の真の側）だけで走る。T2-A2 で 1.2 倍以内を確かめる |
| 古い行（a42dcf92 の形）は在庫表に 48 時間残る | この便の範囲外（書かれなかった状態＝売り切れとは限らない）。13-10-2 の他の案の表 |

戻し方: この PR を revert する（DB の変更なし。83d61b3d の状態は次の再解析で元に戻る）。

#### 13-10-5. 審査

- Opus 自己審査（独立した第二者のレビューではない）: A-1 は 13-10-1 の 9 行・F5 の差 1 行と同じ条件で書いた。A-2 は測定の (i) より相手を多く数える形にしたので、真になる集合は測定の部分集合（包含関係）で、一覧の行を新たに外すことはない。
- 未確認: 0c91e2e0・5642ad0b が設計の形でも真になること（T2-A2）。要確認の一覧の時間（T2-A2）。同じ時刻の投稿の有無（T2-A2）。
- Reviewer（opus）審査 第3回（HEAD 37048d94e）: APPROVE（R2-1 が直り、新しい問題なし）。
- Reviewer（opus）審査 第2回（HEAD cdbf31492）: REVISE。R2-1（F5 は上位集合ではない）→ 文を直し、T2-A1 の対象を basis を問わない形に明記。
- Reviewer（opus）審査 第1回（HEAD 49119fc22）: REVISE。R-1（A-1 が 12d の後ろで本番の 22 行が 1 行も変わらない）→ 12g を 12d より先に置く形に直した。R-2（T2 が今の時刻に左右される）→ NOW() を測定の時刻に固定。R-3（(gg)(hh)(kk) の組み立て）→ 3種類・is_current=偽で書き直し。R-4（§13-9 の窓口の人名）→ ei に置き換え。軽い指摘（行番号・docstring・同じ時刻・NULL）も反映。

### 13-11. PO の実装承認（2026-10-20）

- Opus の問い: 「1. 3件まとめて作る【おすすめ】／2. A だけ後回しにする／3. 今は作らない」（A は §13-10、B・C は §13-3）。
- PO の返事: 「1,推測無しで〆を正しく認識して完売判定できるようになっている？」。
- これにより: A（§13-10）・B・C（§13-3）を1つの実装 PR（release/shime-next3-impl）で作る。T2-A1 でほかの行が出たら止めて PO へ上げる（§13-10-3）。
- PO の問いへの答え（Opus）: 相手を決めるのは、最新の在庫の投稿の状態が1種類のとき（12g）か、取り残しが1種類のとき（12e）だけで、決めきれないもの（最新の投稿に状態が2つ以上・「全数」等の語・前の在庫なし）は相手を作らず、人の目と毎朝の点検（§12-8）に残す。60日の照合で残るのは、語を含む 2 行・原文から決められない 4 行・「全数」で一部だけ合う 1 行（§13-10-1）。

### 13-12. 実装の記録（PR #4574、マージ 41c244716、2026-10-20 14:18Z）

PO の指示（2026-10-20「推測は禁止して事実確認を怠らずに…確立したなら進める」）を受け、CI の statement timeout は再実行で通さず、原因を測ってから直した。生出力は ~/CC報告ファイル-keep/shime-next3-impl/（ci2・jit3・v4impl・item_path・review3）。

- 【事実】A-2 を §13-10-2 の相関副問い合わせの形で入れた HEAD（51f7da281）では、`backend/tests/test_tcg_result_order.py` の test_larger_result_set が CI で statement timeout になった（2回）。直近 40 回の CI では、この試験の timeout は本ブランチだけ。
- 【事実】同じデータでの EXPLAIN の最上位 cost は main 19,412、51f7da281 18,075,667。cr_n1 の相関副問い合わせの見積もりが、500 行ぶん積まれた（実行は never executed）。PostgreSQL の JIT の閾値は jit_above_cost 100000 で、本番は jit=on・pg_jit_available()=true（ci2/jit_prod2.out）。CI は postgres:16 で jit の上書きなし（`.github/workflows/test.yml:122-123`）。
- 【未確認】CI での JIT の実時間。sandbox-test は既存スクリプトしか回せず、測っていない。timeout の原因が JIT かは確定していない。
- 実装の形（3905188b4）: 〆より前の最新の在庫投稿を、チャネル×商品ごとに先に集める cr_prev（MATERIALIZED CTE、source_cte の先頭。`backend/app/services/tcg_condition_review_svc.py:71-81`）から引く。cr_prev に窓 `line_posted_at >= NOW() - make_interval(hours => {SHIME_STOCK_WINDOW_HOURS})` を置く。
- 窓を足しても意味（§13-10-2）は変わらない理由: 相手の条件は同じ式の窓を持つ（同 :229）。本当の最新が窓の中ならそれが選ばれ、窓の外なら、それより前の投稿もすべて窓の外で、相手が0になる。この点はどちらの形でも同じ。試験 (oo)（60時間前→外れる）・(oo2)（40時間前→残る）・(pp)（窓の式の文字列が一致）・(nn)（cr_n1x の参照は1か所）が守る。在庫表の側（`backend/app/services/tcg_distribution_svc.py` の3か所）は latest_stock=False で、SQL の文字列は変更前と cmp で一致する。
- 【事実】見積もり: CI のデータで 92,139（JIT の閾値未満）、本番で main 508,703／3905188b4 の形 467,584。
- 【事実】本番の読み取り照合（NOW() を 2026-10-20 08:49Z に固定）: 51f7da281 の形との差0（直近4日248行・有効投稿50行）。main との差は 0c91e2e0・5642ad0b の2行だけ（偽→真）。一覧の所要時間は交互7回で main 11.72〜24.56秒、3905188b4 の形 3.23〜6.03秒。
- 【事実】単品の道（context_sql item_only、交互7回の中央値）: 〆の行で main 174ms、3905188b4 203ms。在庫の行で 154ms、155ms。保存1回は4回呼ぶので、〆の行で 696→812ms。基準（1.2倍＋100ms＝935ms）以内。
- 審査: Reviewer（opus）APPROVE on 51f7da281、続いて差分 51f7da281..3905188b4 を再審査して APPROVE on 3905188b4。CI は必須15件が合格。GO は PO の委任に基づき Claude Opus が発行した（ADR-1003。PR #4574 の GO記録）。
- 残り: `backend/app/services/tcg_condition_review_svc.py:224` のコメントは「（cr_n1）」のままで、実体は cr_n1x／cr_prev。動きは変わらないので、次にこのファイルを触る便で直す。
