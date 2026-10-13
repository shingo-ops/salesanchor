# 要確認一覧の読み込みを速くする（作業2）設計 — 2026-10-13 Opus

状態: 設計案（Opus 作成）→ Fable 審査待ち。PO の依頼「データテーブルの読み込みが遅い → 理由と改善」（2026-10-13）。

## 1. KGI（PO が○×で判定できる形）
- KGI-1: 要確認タブの最初の20件の取得（GET /api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW&limit=20 の中の SQL 合計）が **本番で 3.0 秒以下**（変更前 7.7〜7.9 秒・3周）
- KGI-2: 一覧に出る中身が **1文字も変わらない**（同じ条件で変更前後の戻り値の sha256 が一致）

## 2. 現在地（recon の要約。全文は recon.md）
- 遅い場所: backend/app/services/tcg_condition_review_svc.py:129 `CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar) cr_data` を PostgreSQL が展開（subquery pull-up）し、:130 の `cr_product.id::text = cr_data.ar->>'product_id'` などの比較のたびに to_jsonb(ar) を作り直している。EXPLAIN（measure-out-explain-raw.txt:372-378）で当該ノード actual time 約3,750ms。変更後も除去行数は同程度（candidateA:491 Rows Removed 240,081）で、減るのは1比較あたりの費用（to_jsonb を行ごとに1回だけ作る）。同ノードは約140ms（candidateA:486-494）。
- 本番の列型: products.id integer・analysis_results.product_id integer（speed-measure-candidateA.txt:25-28、pg_attribute）。
- この部品 review_joins を使う経路（全走査 speed-recon-2.md §4、Fable 審査で `git grep` 再確認）: 要確認一覧 API（tcg_analysis_review_svc.py:47 _BASE_FROM → :180/:186/:197/:244）・CSV 出力（tcg_review_csv_svc.py:75）・シート出力（tcg_review_sheet_svc.py:108）・配信（tcg_distribution_svc.py:292/364/407）・取り込み進捗（tcg_import_progress.py:129）・状態保存と再解析（context_sql 経由 tcg_condition_review_svc.py:205-225、:283-325）。
- 関連 ADR（`git grep -il "analysis_results\|要確認" origin/main -- docs/adr`）: ADR-1002（:70 analysis_results.product_id を INTEGER 化。列型の根拠）・ADR-1001（:93 tcg_condition_review_svc.py をスキーマ参照変更の対象に列挙）・ADR-158（:58 source_cte の is_current。今回は触らない範囲の根拠）。docs/adr/FEATURE-INDEX.md に該当項目なし。本変更は SQL の意味を変えないため、どの ADR とも食い違わない。

## 3. 直し方（1か所・1語）
tcg_condition_review_svc.py:129 を次に変える:
```
変更前: CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar) cr_data
変更後: CROSS JOIN LATERAL (SELECT {analysis_expression} AS ar OFFSET 0) cr_data
```
直前にコメント1行: 「OFFSET 0 は PostgreSQL の展開（pull-up）を止め、to_jsonb(ar) を行ごとに1回だけ作るため。外すと要確認一覧が約3倍遅くなる（docs/handoff/review-speed/design.md）」
- 根拠（公式）: PostgreSQL REL_16_STABLE src/backend/optimizer/prep/prepjointree.c is_simple_subquery「Can't pull up a subquery involving grouping, aggregation, SRFs, sorting, limiting, or WITH」と `subquery->limitOffset ||` の条件。Context7 は月間上限で使えなかったため、起動指示の代替として公式ソースを直接確認。
- 1行のサブクエリに OFFSET 0 を付けても返る行は変わらない（SQL の意味は同じ。実行の順番だけが変わる）。

触らない範囲: review_joins の他の行、_BASE_FROM、source_cte、件数・提供者の SQL の共有化（「変更は一度に1つ」。この変更の効果を測ってから次を決める）、フロント。

### 代替案と選ばなかった理由
- B: 結合を `cr_product.id = (cr_data.ar->>'product_id')::integer` にする → 再解析の候補（candidate の JSON）で product_id が整数でない文字のとき型変換エラーで落ちる恐れ。意味が変わり得るので不採用。
- C: 件数・提供者・本体を1本の SQL にまとめる → 変更が大きく、CSV・シートにも波及。A の効果測定後に必要なら別便。

## 4. 実測（本番・読み取りのみ・2026-10-13 10:03 UTC・別コンテナ・READ ONLY）生出力 speed-measure-candidateA.txt
| 条件 | 変更前 合計ms（3周） | 変更後 合計ms（3周） | sha256 |
|---|---|---|---|
| NEEDS_REVIEW 20件 | 7915 / 7734 / 7770 | 2388 / 2451 / 2419 | 一致 |
| NEEDS_REVIEW 500件 | 40398 / 40254 / 41373 | 5465 / 5414 / 5397 | 一致 |
| ALL 500件 0〜 | 15965 / 15835 / 15591 | 3437 / 3465 / 3428 | 一致 |
| ALL 500件 500〜 | 5351 / 5351 / 5350 | 4294 / 4186 / 4170 | 一致 |
| NORMAL_COMPLETED 500件 | 10881 / 10837 / 10867 | 6286 / 6244 / 6305 | 一致 |
| 配信 fetch_output_rows | 24873 | 23144 | 一致 |
| 配信 fetch_preview_data | 10743 | 8758 | 一致 |
| 取り込み進捗 2job×2関数 | — | — | 一致（as_of の時刻欄を除く） |

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| KGI-1 本番で NEEDS_REVIEW 20件の SQL 合計 ≤3.0秒 | デプロイ後、同じ測定スクリプト（x.py）を別コンテナ・READ ONLY で3周 |
| KGI-2 戻り値が変わらない | デプロイ前に取った sha256（変更前コード）と、デプロイ後の sha256 を比べる。データ更新があり得るため、デプロイ後は「旧コードの文字列を再現した版」と同時に測って一致を見る（今回と同じ方式） |
| 既存試験が通る | CI の pytest（test_tcg_condition_review.py:323-343 の実 PG 試験・test_tcg_result_order.py・CSV/シート試験） |
| 展開止めが外されない | 新しい単体試験（backend/tests/test_tcg_condition_review.py 末尾・pg fixture なし＝DB 不要で常時走る）: (a) review_joins() に `AS ar OFFSET 0) cr_data` を含み `AS ar) cr_data` を含まない (b) context_sql(analysis_expression="to_jsonb(ar) \|\| CAST(:candidate AS jsonb)") でも同様 (c) tcg_analysis_review_svc._BASE_FROM に `AS ar OFFSET 0) cr_data` がちょうど1回 |

## 6. 弊害とリスク
- PostgreSQL の版上げで最適化の方法が変わる可能性 → 単体試験で文字列を固定し、効果は本設計の測定スクリプトで再測できる。
- ALL 500件 500〜 は短縮が小さい（5.35→4.2秒）。主因は別の場所（並び替え）であり今回の対象外。

## 7. 維持の仕組み
- 守り手: CI の pytest（backend/tests/test_tcg_condition_review.py::test_review_joins_keeps_offset_zero_pullup_barrier。DB 不要で毎回走る）。速さの測り直しは設計担当（Opus）が本書 §5 の方法で行う。
- 単体試験（文字列の固定）＋ コードコメントで理由と本設計へのリンク。
- 測定スクリプト: repo 外の ~/CC報告ファイル-keep/review-page-20261013/x.py（再測用・本番データの中身を出さず件数と sha256 だけ出す）。repo には測り方（別コンテナ・READ ONLY・OLD/NEW 文字列を差し替えて同時に測る）を本書に記すに留める。

## 審査
- 2026-10-13 Fable（設計審査）: APPROVE。指摘（行番号・文言・ADR 参照・試験の置き場所・recon の未確認解消）は本版で反映済み。

## 8. 外部・過去事例の参照と我々への応用
- PostgreSQL 公式ソース（上記 §3）。OFFSET 0 で展開を止めるのは PostgreSQL 開発者の文書に基づく方法で、本件の効果は本番の実測（§4）で確認した。他社事例の数値は使わない（本件の判断は自社本番の実測だけで足りるため）。

## 9. 戻し方
- `OFFSET 0` を外す1行の revert。DB 変更なし。
