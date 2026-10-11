# design: v102 間の行の検知の記録（段1）

- 状態: 設計案（Opus 作成・自己審査済み。独立した第二者レビューではない）
- PO の方針（2026-10-11 原文）:「段階的にgeminiが再抽出してシステムが解析して集計リストに自動で入るまでを実装したい」「トロこぼしを減らせる仕組みなので実現したい」「確立したなら進める」
- 全体の段階（Fable 案を Opus が審査・修正）：段1 記録 → 段2a 見出しで補う（要確認のまま）→ 段2b 補った件の自動配信 → 段3 再抽出の事前試験 → 段4 再抽出の本番導入（要確認のまま）→ 段5 再抽出の件の自動配信。この文書は段1だけを扱う。
- 現在地: [recon.md](recon.md)（docs/handoff/v102-gap-detect-record/recon.md）
- 対象ADR: ADR-154（配信は needs_review=false のみ）、ADR-1007（migration は構造だけ）、ADR-135・ADR-136（migrations を含む PR は PO の「GO #番号」）

## 1. 目的
今は DB に残らない「取りこぼしの疑いの行番号」と「間の行から出る商品の候補」を、投稿ごとに1か所に残す。
- 段2〜5 の効果を、本番の読み取りで数えられるようにする。
- 後で画面に行番号を出すときの、唯一の読み元にする。

この段では、要確認の判定・配信・画面を一切変えない。

## 2. 対象と対象外
- 対象：v102 の投稿すべて（`run_v102_analysis` が書く投稿）。
- 対象外：
  - `analysis_results` の全列
  - `extraction_jobs.review_reasons`
  - `needs_review`
  - 配信（`backend/app/services/tcg_distribution_svc.py`）
  - 画面
  - Gemini の呼び出し
  - 指示書
  - 件（`extraction_items`）

## 3. 変更（2つの PR に分ける。recon.md §2 のデプロイ順のため）

### PR①（migration だけ。ADR-135/136 の危険 PR。PO の「GO #番号」まで main にマージしない）
- 新しいファイル `migrations/20261012_100000_add_extraction_jobs_system_review_detail.sql`：
  ```sql
  -- 構造のみ。値の操作は含めない（ADR-1007）。冪等。
  ALTER TABLE public.extraction_jobs ADD COLUMN IF NOT EXISTS system_review_detail JSONB;
  COMMENT ON COLUMN public.extraction_jobs.system_review_detail IS
      'v102 システムが見つけた要確認の明細（行番号・間の行の商品候補）。解析のたびに上書き。原文は入れない';
  ```
- `scripts/run_all_migrations.sh` の末尾に、コメント1行と `run_sql migrations/20261012_100000_add_extraction_jobs_system_review_detail.sql` の1行を足す。
- 置き場の理由（SSOT）：投稿ごとの明細の置き場を、同じ表の同じ型（`gemini_unsure` JSONB、`migrations/20261009_180000_v102_engine_columns.sql`）にそろえる。新しい表は作らない。

### PR②（コードだけ。PR① の本番反映を確認してからマージ）
1. 新しいファイル backend/app/services/v102_gap_lines.py（新規作成。純粋な関数だけ。DB を読まない）
   - `classify_lines(items, line_count)`
     - 受理された件（rejected を除く）を、最初の行の順に並べる。
     - どの件の lines と price_line にも入らない空でない行を、次の4つに分ける。
       - gap：前の件の最終行より後で、次の件の最初の行より前
       - pre：最初の件より前
       - span：件の範囲内の未使用行
       - trail：最後の件の後
     - 移植元はリポジトリ外の測定スクリプト measure_gap_range.py の 117-132 行。結果が行単位で一致すること（§5-2）。
   - `gap_price_qty_lines(...)`（T1）
     - gap の行（pre は含めない。recon §3：pre は誤報だけだったため）のうち、次の2つを満たす行番号。
       - どの件の price_line でもない
       - 式 F2_price_and_qty に当たる。式は `(_is_price_shaped(行) or has_money(行)) and has_q(行)`。
     - `has_money`・`has_q` の正規表現は、リポジトリ外の測定スクリプト measure_gap_detect_v2.py の 55-87 行から1文字も変えずに写す。`_is_price_shaped` は `backend/app/services/gemini_raw_copy_v101.py:962-966` の本物を import する（写さない）。
   - `gap_name_candidates(items, lines, product_first)`（T2＝規則 H2）
     - gap と pre の行を、連続するまとまりにする。各まとまりの効く範囲は、直後の件から、次のまとまりの直前の件まで。
     - 範囲の件のうち、次の3つをすべて満たす件だけを対象にする。
       - 価格がある（写しが none・空でない）
       - 数量がある（写しが none・空でない）
       - `match_status == "unmatched"`
     - 支えの行
       - まとまりの各行のうち、その行1行だけを `product_match_text(行, "", None)` → `match_text_g2` に通した結果が matched でも ambiguous でもない行。
       - 照合の入口は本番 `backend/app/services/gemini_raw_copy_v102_product_first.py:552-553` と同じ。
     - 候補
       - 支えの行ごとに、`product_match_text("\n".join([支えの行] + 件の各行の原文), "", 件の商品名)` → `match_text_g2` を通す。
       - matched なら product_id を、ambiguous なら candidates を取り、その和集合を候補とする。
       - 移植元はリポジトリ外の測定スクリプト measure_gap_range.py の 140-155 行（method a）と measure_h2.py の 59 行。
2. `backend/app/services/line_analysis_v102_svc.py`
   - `run_v102_pipeline`（:262-300）の成功時の戻り値に `"v102_gap_detail"` を1つ足す。中身は次のとおり。
     - `post_review` のうち `line` を持つ要素の写し
     - T1 の行
     - T2 の結果（件は gemini_index で示す）
   - 例外時（:294-300）は `None`。
   - 既存の `v102_items`・`v102_flags` は1文字も変えない。
   - `_write_results`（:807-844）の `:843` の直後で、新しい `_set_job_review_detail` を呼んで書く。
     - 件は、`_write_results` が既に使っている件と行の対応で、`extraction_item_id` に置き換える。
     - 対応が付かない件は書かない。その数を `"unmapped"` に入れる。
   - 書く値（版 1）：
     ```json
     {"v": 1,
      "post_review": [{"kind": "possible_missing_item", "line": 12}],
      "gap_price_qty": [{"line": 85}],
      "gap_name": [{"extraction_item_id": "…", "gap_lines": [31, 32], "support_lines": [31], "candidates": [440415]}],
      "unmapped": 0}
     ```
     - `candidates` が空のときは「候補なし（要確認＋行番号）」を表す。
     - `gap_lines` はその件に効くまとまりの間の行すべて（支えに使わなかった行も含む）。候補なしでも行番号が残る（PO 2026-10-11「間の行番号を見える状態で」）。
     - 解析が例外で失敗した経路（`run_v102_analysis` の except）では、`system_review_detail` を NULL にする（古い明細を残さない）。
     - `masters` に `product_first` が無いときは `gap_name` を空にし、T1 と `post_review` だけを書く。
     - 原文は入れない（`docs/handoff/v102-no-silent-drop/design.md:31` の決まり）。
3. 触らない範囲
   - `backend/app/services/gemini_raw_copy_v101.py`（変えない。import するだけ）
   - `backend/app/services/gemini_raw_copy_v102_product_first.py`
   - `backend/app/services/tcg_condition_review_svc.py`
   - `backend/app/services/tcg_distribution_svc.py`
   - frontend
   - review_reason_codes
   - 指示書
4. 試験（追加）
   - backend/tests/test_v102_gap_lines.py（新規作成）：分類・T1・T2 を、合成の投稿で確かめる。対象は次の3つ。
     - BASE SHOP 型
     - 見出しだけで当たる型（支えに使わない）
     - 価格の無い在庫一覧（動かない）
   - `backend/tests/test_line_analysis_v102_pg.py`：実 DB で書いて読む1本。
   - 既存の試験は変えない。

## 4. 変更の前後
| | 変更前 | 変更後 |
|---|---|---|
| `extraction_jobs.system_review_detail` | 列なし | 上の JSON（v102 の投稿）／NULL（それ以外・例外時） |
| `review_reasons`・`needs_review`・配信・画面 | — | 変わらない |

## 5. 受入条件と検証
| 基準 | 検証方法 |
|---|---|
| 1. PR①の migration が冪等 | 手元の PostgreSQL 16 で2回流して2回とも成功。列は jsonb・NULL 許容 |
| 2. 計算が測定と一致 | 手元の保存データ（fct2・bs1）を本番の照合関数・本番マスタの写しで計算する。測定 scope-h2 の「L含む」と件数（fct2 動いた480・候補1つ100、bs1 120・20）を比べ、違いは行単位で全部示して原因を説明する。BASE SHOP 3投稿が 440415 であること |
| 3. 既存の結果が不変 | 保存済み応答 1,021 回で、変更前後の `v102_items`・`v102_flags` と `_analysis_values` の結果が完全一致（違いは新しい鍵だけ） |
| 4. 単体・実 DB の試験 | CI の pytest-run-internal が通る |
| 5. 本番反映後 | ①コンテナの該当ファイル sha が main と一致 ②反映後の v102 ジョブが status done、`system_review_detail` が NULL でない ③反映前後で、v102 ジョブの needs_review の件の割合に、説明できない差が無い（読み取り SQL） |

## 6. 代替案
- 画面を開いたときに都度計算する案（Opus の前案）。採らない理由は2つ。
  - 配信の判定と同じ時点の値が残らない。
  - 計算の場所が2つになる（配線の SSOT に反する）。
- `analysis_results` に件ごとの列を足す案。採らない理由は2つ。
  - 投稿ごとの行番号（T1・post_review）は件に属さない。
  - 置き場が2つになる。

## 7. 危険と対処
- 列の追加と書き込みを1つの PR にすると、書き込みが失敗する。→ PR を①と②に分ける。
- JSON が大きくなる。→ 行番号と商品IDだけを入れる。
- 照合の計算が重くなる。→ 動くのは unmatched で価格・数量のある件だけ。測定では 1投稿あたり最大で数件。§5-2 の手元計算で、1投稿あたりの時間を測って記録する。
- 戻し方：PR② を revert する（列は NULL のまま残る）。PR① の列は残置する（DROP しない）。

## 8. 外部・過去事例の参照と我々への応用
該当事例なし。今回は、自社の解析結果の明細を残す変更で、外部の手法を採り入れていない。根拠は自社の測定（recon §3）だけ。

## 9. 維持の仕組み
- 試験 backend/tests/test_v102_gap_lines.py（新規作成）が、分類・T1・T2 の規則を固定する。
- `docs/specs/line-analysis-tuning/README.md` に1行足す。
- 段2a 以降は、この列だけを読む（新しい置き場を作らない）。
- 守り手: backend/tests/test_v102_gap_lines.py（新規作成。CI の pytest-run-internal で毎回走る）

## 10. 未解決
なし。段2以降の未確認は Fable 案 §7（リポジトリ外）にあり、各段の設計で扱う。
