---
mode: handoff
---
# recon: 解析の誤りの原因を切り分ける（回帰分析）

親: [kgi-regression.md](./kgi-regression.md)／[design-regression.md](./design-regression.md)。2026-10-31 Opus（origin/main 67ae676b3 起点の枝 release/accuracy-regression-design で確認）。

この文書は何か: 誤りの原因を計算で切り分ける前に、今ある道具と記録で何ができて何が足りないかを、ファイルの行と本番の件数で確かめた記録です。

## 既存 ADR の検索
- `git grep -i -E "回帰分析|regression analysis|logistic" docs/adr/` → 該当 2 件（ADR-1001・ADR-1002）はどちらも表名 `products_logistics` の一致で、無関係。回帰分析の ADR は 0 件。
- 関係する ADR: `docs/adr/ADR-1024-ai-readonly-db-path.md`（本番を読むだけの道）、`docs/adr/ADR-1042-cloud-read-window.md`（クラウドから読むだけの窓口）、`docs/adr/ADR-1043-accuracy-gold-in-db.md`（正解表を本番 DB に置く）。
- 設計仕様書: `docs/specs/line-analysis-tuning/README.md`（親 design.md と同じ）。

## 今の姿（事実）

### 採点の道具
- `scripts/accuracy/score_v102.py:181-282` `score()` は正解表の全行を採点する。`除外` が `ALL` の行は飛ばす（:206-207・:212-213）。
- 判定は項目ごとに ok / ng / na / skip（:161-178 `judge()`）。読み落としは `c1` に数える（:208-210・:215-217）。
- 出力は集計（`result.tsv`、:285-300 `result_rows()`）と、違った件だけの一覧（`errors.tsv`、:352-353）。**正しかった件を含む行ごとの判定は出力しない。**
- `docs/handoff/accuracy-measurement/card-by-group-bin1.md:14` は「後の score_v102 も、この形（1件×1項目＝1行の判定表）に直してから渡す」と書くが、直す道具は本線に無い（`scripts/accuracy/` の一覧に該当なし）。
- `scripts/accuracy/by_group.py`（169 行）は判定表 `key 項目 判定` を受けて仕入元ごとの正答率と Wilson の幅を出す（`scripts/accuracy/README.md:32`）。回帰の計算は無い。
- 道具はどれも標準ライブラリだけで書かれている（`scripts/accuracy/README.md:3`）。

### 本番の件数（2026-10-31 JST・ADR-1024 の道・読むだけ）
生の出力: `/tmp/CC報告ファイル/regression-sa/counts/`（counts.txt・join.txt・versions.txt・columns.txt）
- 正解表 gold_v1: 1,494 行・100 投稿・仕入元の窓口 46。
- 100 投稿すべてに読み取りの記録が 1 回ずつある。
- 指示書の版・モデル: 100 投稿すべて `v102:raw_copy_v101_f_ct:fe50593fa362`・`gemini-3.1-flash-lite` の1種類。
- 画面からの誤り報告: 0 件。

### 窓口から読める列（ai_ro）
- `public__source_messages`: id, supplier_channel_id, raw_text, line_posted_at ほか
- `public__extraction_attempts`: input_bytes, item_count, started_at, response_received_at, finished_at, validation_result, error_code ほか
- `public__supplier_channels`: id, supplier_id ほか

### 計算の道具（公式の説明書・2026-10-31）
- Context7 は月の上限に達して使えなかった（応答 "Monthly quota exceeded"）。起動指示に従い公式の説明書を直接読んだ。
- statsmodels 0.15.0 `RegressionResults.get_robustcov_results`: `cov_type='cluster'` は「clustered covariance estimator (CRV1)」。`groups` は群の番号、`use_correction` は小標本の補正の有無、`df_correction` は群の数−1 を自由度に使う（https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html）。
- GLM の補正の式は説明書に無い。**未確認**（design §10 で扱う）。

## 未確認
- 1,494 行の中の誤りの数（採点を通していない）。
- 正解表の A2（状態）・A3（単位）の値の種類（中身は社外秘。数は実装段で数える）。
