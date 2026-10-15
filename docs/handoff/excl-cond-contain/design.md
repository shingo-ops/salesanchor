<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。 -->
# Phase 3 設計 — excl-cond-contain（除外語の一致が状態の合図の語に収まるときだけ無視する）

この文書は何か: 商品の除外語（例: AR）が「ARパック」という状態の合図の語の一部としてだけ出てくるときに、その除外を無視して商品を落とさないようにする設計書です。
親（設計仕様書）: [docs/specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)／recon: [recon.md](recon.md)

**対象ADR**: ADR-154（関連：商品除外語の扱い。v102 の除外語判定そのものを定める ADR は無い。recon.md §1）  
**recon**: docs/handoff/excl-cond-contain/recon.md  
**日付**: 2026-10-16  
**PO承認**: 2026-10-16（Opus 経由で y）

## KGI
POが次を出力で○×判定できる: 除外語「AR」の商品について、本文「アビスアイ ARパック」「アビスアイ ＡＲ　パック」では除外されず、「アビスアイ AR 1枚」では除外される。v102 の全 7,963 行の再計算で商品決定が変わる行は 5 行（試算値）。

## 仕様
- 無視する条件: 除外語の一致箇所が、状態マスタ（public.conditions）の合図の語の一致箇所に完全に収まり、かつ合図の語の正規化後の長さが除外語より長いとき、その一致だけを無視する。無視されない一致が1つでも残れば除外のまま。
- 合図の語: `masters["cond_entries"]` のうち match_type が KEYWORD / LITERAL の search_kw（カンマ区切り）。照合と同じ正規化（`normalize_for_match`）。一度だけ作り、G2Index に持たせる。
- 空のとき（cond_terms 既定）は変更前と同一動作。
- v6（`backend/app/services/tcg_analyzer_svc.py`）は変えない。新しい表・列・設定値は作らない（SSOT は conditions）。

## 変更（file と内容）
- `backend/app/services/extraction_judgement_svc.py`
  - `build_cond_terms(cond_entries)`: 合図の語のタプルを作る（長い順・重複なし）
  - `_mask_contained`: 除外語の一致箇所のうち、より長い合図の語の一致箇所に収まるものを同じ長さの空白にする（nb は文字位置、folded は記号・空白を許す位置）
  - `_exclude_hit`: 変更前の1語判定をそのまま切り出したもの
  - `_excluded_keywords(..., cond_terms=())`: 変更前の判定で当たった語だけを、空白にした文で本番の判定（境界判定・品番らしい語の判定を含む）に再度かける。まだ当たれば除外
  - `_is_candidate` / `match_product` に cond_terms を通す
- `backend/app/services/gemini_raw_copy_v102_product_first.py`: `G2Index.cond_terms`（既定 ()）、`with_cond_terms`、`_g2_hits` と `match_product_g2` が索引の cond_terms を渡す
- `backend/app/services/line_analysis_v102_svc.py`: `load_v102_masters` で cond_entries から一度だけ作り、masters["product_first"] に持たせる
- `backend/tests/test_extraction_judgement_cond_terms.py`: 新規テスト

触らない範囲: v6、試作版ツール `backend/app/tools/prompt_ab.py`、DB スキーマ、migrations、deploy.yml。

## 外部・過去事例の参照と我々への応用
- 該当なし：社内の照合規則（除外語の境界判定）の局所的な例外追加であり、外部事例の参照は不要と判断。代わりに社内の過去事例として、一律に合図の語を取り除く案（strip 版）を試算し、「SARパック」の AR 部分まで消えて SAR 除外語が外れる副作用が出たため、包含ルール版に変更した（既存調査 §6 の既知の限界 → 本設計で解消）。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 除外語 AR・合図の語 ARパック で「アビスアイ ARパック」は除外されない | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_ar_inside_arpack_is_ignored` |
| 全角「ＡＲ　パック」も除外されない | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_fullwidth_spaced_arpack_is_ignored` |
| 「アビスアイ AR 1枚」は除外される | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_standalone_ar_still_excluded` |
| 除外語 SAR・「SARパック」は除外される | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_sar_not_contained_by_arpack` |
| 除外語 PSA10・合図の語 psa（短い）は除外される | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_shorter_cue_does_not_ignore` |
| 除外語 CHR・合図の語 CHR（同じ長さ）は除外される | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_same_length_cue_does_not_ignore` |
| 除外語 FUTURISTIC・合図の語 ur は除外される | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_longer_exclude_than_cue_is_kept` |
| 1行に「ARパック」と単独の AR があれば除外される | `backend/tests/test_extraction_judgement_cond_terms.py::TestContain::test_both_arpack_and_standalone_ar_in_one_line` |
| cond_terms が空なら変更前と同じ結果 | `backend/tests/test_extraction_judgement_cond_terms.py::test_empty_cond_terms_matches_legacy_call_signature` と既存 `backend/tests/test_extraction_judgement_svc.py` の全件 |
| 合図の語は KEYWORD/LITERAL のみ・正規化・長い順 | `backend/tests/test_extraction_judgement_cond_terms.py::test_build_cond_terms_filters_type_normalizes_and_orders` |
| 商品照合（G2）と base に同じ合図の語が届く | `backend/tests/test_extraction_judgement_cond_terms.py::test_g2_uses_index_cond_terms` ほか |
| 既存の v102 / 照合系テストが変わらない | CI の pytest（変更前 949 passed → 変更後 973 passed＝新規 24 件のみ増。DB 必須の 79 件はローカルで同じ理由でエラー、CI で実行） |
| lint が通る | CI の ruff（`ruff check app/`） |

## 技術 How・KPI
- 方式: 「当たった除外語だけ」を、収まる一致箇所を空白にした文で本番の判定に再度かける。境界判定・品番らしい語の判定を新しく書き直さないため、判定の食い違いが出にくい。
- KPI: 全 7,963 行の再計算で決定が変わる行 = 5 行（試算）。再計算は PO が実施（この PR では本番に触れない）。

## 弊害・トレードオフ
- 合図の語が短い（2文字以下）だと広く収まる → 除外語より長い合図の語に限るので、同じ長さ・短い語では無視されない。
- 除外語が連続して重なる特殊な文字列（例: 除外語 aa・本文 aaa）では、収まる一致箇所だけを空白にするため、周辺の一致が変わる可能性がある → 実データの除外語は短い略称が多く、試算の差分 5 行で確認済み。
- v6 は同じ不具合が残る → 対象外（PO 承認済み）。

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 実装・テスト・PR 作成 | Sonnet |
| 2 | CI 確認・レビュー | Opus |
| 3 | main マージ後の本番反映・再計算 | PO / Opus（この PR の範囲外） |

## 継続
- 完了後の監視: 反映後に再計算し、変わった行が試算の 5 行と一致するかを PO が確認。
- 戻し方: この PR を revert する（スキーマ・データの変更なし）。

## 維持の仕組み
- 守り手: `backend/tests/test_extraction_judgement_cond_terms.py`
- 対象: 除外語が合図の語の一部としてだけ出る場合の無視、および同じ長さ・短い合図の語・単独の除外語では無視されないこと。cond_terms が空なら従来どおりであること。
- 関所なしの場合: テストは CI の pytest が毎 PR で実行する。合図の語の本番データの変更（conditions）は人手で見る（過剰な無視が出ていないかを再計算で確認）。
