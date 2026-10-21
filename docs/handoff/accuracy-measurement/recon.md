---
mode: handoff
---
# recon: 解析の正答率を正しく測る仕組み（現在地）

親: [LINE解析の調整記録](../../specs/line-analysis-tuning/README.md)

この文書は何か: これまで解析の正しさをどう測ってきたか、何が測れていなかったかを、記録とコードで確かめたものです。

- 調べた日: 2026-10-20（origin/main bb5f03e35 を基準。読み取りだけ）
- 社外秘: 仕入元名・投稿の原文・判定の一覧は書かない。根拠の生データは手元の `~/CC報告ファイル-keep/` にあり、場所だけ示す。
- 生の調査結果: `~/CC報告ファイル-keep/accuracy-method-recon-20261020/recon.md`、`/tmp/CC報告ファイル/accuracy-design/recon-facts.md`

## 0. 既存 ADR の検索

- `git grep -il -e 正答率 -e accuracy -e 正解表 -e gold origin/main -- docs/adr/` → ADR-154 の1件だけ。該当は docs/adr/ADR-154*.md:134「全件正答率は未確立」の記述で、測り方を決めたものではない。
- docs/adr/FEATURE-INDEX.md に正答率・正解表・採点の項目は無い。
- 近いもの:
  - ADR-1025（Proposed）は、誤りの報告→再解析→機械照合の流れ。固定の正解表ではない。
  - ADR-1006（Accepted）は型番だけでの照合。
- 予約の判定（status）と発送日（ship_ja）を決めた専用 ADR は無い。決まりは handoff 文書にある。
  - 予約: docs/handoff/v102-preorder-context/（design.md・card-PO.md・card-PO2.md）
  - 発送日: docs/handoff/v102-ship-note/design.md、v102-ship-column、v102-shipdate-range、v102-heading-ship-review
  - Pre-order という考え方: docs/adr/ADR-093*.md:23, :41
- 結論: 測り方を決めた ADR は無い（grep 済み・該当なし）。

## 1. これまでの測定（10/14・10/16・10/18）

| 測定 | 見本 | 答えを付けた人 | 採点した項目 | 採点していない項目 |
|---|---|---|---|---|
| 10/14 | 現行行から300件（seed 20261014） | AI 3人＋Opus の見直し | 商品が正しいか、の1項目 | 状態・数量・価格・予約・発送日・読み落とし |
| 10/16 | 配信中 948行から300行 | AI 2人が別々に＋Opus の裁定 | 書き写し4項目（行・数量・価格・状態語）、判定4項目（商品・状態・単位・単価） | 予約・発送日 |
| 10/18 | 現行行から300件（seed 20261018） | AI 3人＋Opus の見直し | 商品が正しいか、の1項目 | 10/14 と同じ |

根拠:
- 10/14: `~/CC報告ファイル-keep/accuracy-20261014/method-20261014/JUDGE-RULES.md`（判定欄・出力欄）、RESULT-accuracy-20261014.md
- 10/16: `~/CC報告ファイル-keep/accuracy-overall-20261016/design.md`（判定項目）、final.tsv の1行目
- 10/18: `~/CC報告ファイル-keep/accuracy-20261018/RESULT.md`

【事実】
- 10/18 の見本300件には Pre-order が18件あった（sample300.jsonl を集計）。予約かどうかは採点していない。
- 10/16 の判定ファイルには「予約」「pre-order」の語が0件（grep -c）。項目 A2 は状態（Sealed box など）で、予約かどうかとは別の欄。
- どの回も、答えはその場で AI が原文を読んで付けた。PO が確かめて固定した答えではない。
- 10/16 は、裁定が PO の定義と食い違って2点を訂正した（CORRECTION-20261017.md）。採点する側も間違える、という記録。
- 見本はシステムが出した行から取っている。システムが読み落とした値段の行は見本に入りにくい。
  - 10/16 で、値段の無い記載まで含めて数えると網羅は 312/358 = 87.2%。

## 2. 予約の判定の現状

【事実】
- 予約の判定に「発売日・先の日付・見出し」を足したのは 2026-10-12（git 349947e82, 270ffb043）。
  - それより前は、予約見出しの下の現行281件のうち280件が In Stock だった（docs/handoff/v102-preorder-context/card-PO.md 背景）。
- 予約を決める関数: backend/app/services/v102_status_context.py:120 `context_status`。呼び出し元は backend/app/services/gemini_raw_copy_v101.py:927-934。
- 根拠（status_basis）は4種類。適用順は RELEASE_AHEAD → DATE_AHEAD → HEADING。
  - None（変えない。v102_status_context.py:129, :143）
  - `RELEASE_AHEAD:<発売日>`（:134）
  - `DATE_AHEAD:<日付>`（:139）
  - `HEADING:<見出し行>`（:142）
- 1行目の発送日や範囲日付が在庫ありになる件は、2026-10-19 に直した（docs/handoff/v102-shipdate-range/）。

【未確認】
- いま予約を在庫ありと間違えている行が何件あるか。一度も測っていない。

## 3. 解析の2段と保存先

- 2段の構成: backend/app/services/line_analysis_v102_svc.py:4-7
- Gemini 段（原文から行を書き写す）:
  - `run_v102_extraction`（同 :484）が extraction_items に書く（INSERT :523-531。列は line_start, line_end, raw_price, raw_quantity, source_lines, gemini_index）。
  - 再実行すると DELETE→INSERT（:520）。
- Gemini の応答そのものは extraction_attempts に残る。
  - 列の定義は migrations/20260921_110000_pipeline_tables_public.sql:112-149。response_text, parsed_items, prompt_version, code_version などがある。
  - 定期削除は見つからない（backend の maintenance.py:28-42 の保持日数に無い）。消えるのは親の extraction_jobs が消えたとき（CASCADE、同 migration :116）。
- システム段（商品・状態・予約・発送日を決める）:
  - `_analysis_values`（line_analysis_v102_svc.py:708-744）が analysis_results に UPSERT（:749-772、ON CONFLICT extraction_item_id で上書き）。
  - 列は product_id, pid_basis, unit_*, condition_*, condition_basis, quantity_normalized, price_normalized, status, exclusion, ship_ja, ship_en, price_basis など。
- 段どうしは extraction_item_id でつながる。Gemini とシステムのどちらで間違えたかは、表の上では分けられる。
- 足りないもの:
  - analysis_results は再判定で上書きされ、前の値が残らない。直す前と後の比較は、表からはできない。
  - status_basis は DB に保存されない。migrations・models・schemas に0件。`_analysis_values` にも無い（status は :740）。
  - raw_product_name, raw_state は v102 では書かれない（:523 の INSERT 列に無い）。

## 4. 固定の正解表

- `~/CC報告ファイル-keep/gold-extended-20261007/gold_G3_v3.tsv`
  - 125投稿・2,304件。PO「修正する」2026-10-11 で v3。sha256 b9230904…（README_v3.md:3）。
  - 列は7つ: 投稿、price_line、必須の行、許容する行、price、quantity、根拠（README.md:39-44）。
  - 書き写しの答えだけで、商品・状態・単位・予約・発送日の答えは無い。
- 単位の別表 rand300（10/11）は、手元で見つかっていない（未確認）。

## 5. まとめ（設計への入力）

1. 予約と発送日は、一度も採点していない。前回「予約を予約と捉えていない」ことに気づけなかったのは、採点表に欄が無かったため。
2. 答えは毎回 AI がその場で付けていて、固定されていない。回ごとに比べられない。
3. 見本がシステムの出力から取られていて、読み落としが測りにくい。
4. Gemini 段とシステム段は表の上で分けられる。ただし予約の根拠は保存されず、再判定で前の値が消える。
5. 書き写しの固定の正解表（125投稿・2,304件・PO 承認済み）があり、土台に使える。
