# recon — 除外語の一致が状態の合図の語に収まるときだけ無視する（excl-cond-contain）

この文書は何か: 商品の除外語（例: AR）が、状態マスタの合図の語（例: ARパック）の一部として書かれているだけのときに誤って商品を落としている現状を、実コードの行番号つきで記録した調査です。
親（設計仕様書）: [docs/specs/line-analysis-tuning/README.md](../../specs/line-analysis-tuning/README.md)／子: [design.md](design.md)

基準: origin/main = 63046732eec987c192376ca956a901742dbd6a48（git fetch 後に実測）。パスは省略せず書く。
社外秘: 仕入元の投稿本文・job_id・item_id は載せない。載せるのは集計値のみ。

## 1. 既存 ADR 検索（着手前・必須）
実行したコマンドと結果:
- `git grep -n -i -E "除外語|exclude_kw|excluded|状態マスタ|conditions" -- docs/adr/` → 7件
  - docs/adr/ADR-050-release-pr-workflow-standardization.md:74（GitHub ruleset の conditions。無関係）
  - docs/adr/ADR-109-leads-status-ssot-immutable-codes.md:49（FOLLOWUP_EXCLUDED。無関係）
  - docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:49,101,116（CSV 取込時の商品の検索語・除外語。照合ロジック `_excluded_keywords` の仕様ではない）
  - docs/adr/ADR-156-product-classification-tree-and-master-separation.md:42（conditions への FK 追加 migration。照合に無関係）
  - docs/adr/ADR-159-staff-identity-on-discord.md:41（Excluded は別の意味。無関係）
- `docs/adr/FEATURE-INDEX.md` を 除外／exclude／状態マスタ／conditions／状態 で grep → 照合に関する行は無し（hit は :61 の expand-contract のみ。無関係）
- 結論: v102 の除外語判定の仕様を定める ADR は無い（grep 済み）。最も近い関連は ADR-154（商品除外語の扱い。CSV 取込・name-first 側）で、本変更はそれと矛盾しない。ADR と食い違う実装は無いので「ADR 優先」の調整は発生しない。
- 生出力: /tmp/CC報告ファイル/excl-cond-contain/adr_grep2.txt, adr_featindex.txt（作業環境の一時ファイル）

## 2. 除外語の判定（変更前）
- `backend/app/services/extraction_judgement_svc.py:247-268` `_excluded_keywords(product, nb, folded=None, strict_codes=False)`
  - :256-261 strict_codes かつ folded あり → `_strict_code_hits`（:190-198）。None なら下へ
  - :262-264 `normalized = _normalize_value(keyword)`。空 or `normalized not in nb` → 外れ
  - :265-266 `_needs_boundary(normalized)`（:57-59 = 2文字以下 or 数字のみ）かつ folded あり → `has_left_word_boundary(folded, keyword)` が偽なら外れ
- `backend/app/services/extraction_judgement_svc.py:70-75` `has_left_word_boundary`: 直前が英数字でない出現が1つでもあれば真。右側は見ない。このため「ARパック」の AR は右が日本語なので当たる（不具合の原因）
- `backend/app/services/extraction_judgement_svc.py:22-28` `fold_for_match`（空白・記号が残る）／:31-44 `normalize_for_match`（空白・記号 P*/S* を除去）
- 呼び出し元（変更前）:
  - `backend/app/services/gemini_raw_copy_v102_product_first.py:235` `_g2_hits` → `_excluded_keywords(entry, nb, folded, True)`
  - `backend/app/services/extraction_judgement_svc.py:306` `match_product` → `_excluded_keywords(product, nb, folded, strict_codes)`
  - `backend/app/services/extraction_judgement_svc.py:275` `_is_candidate` → `_excluded_keywords(product, nb)`（folded なし）。:295 の boundary_dropped 用

## 3. 呼び出し元は v102 の経路から呼ばれるか（事実）
- `_g2_hits`: `match_product_g2`（`backend/app/services/gemini_raw_copy_v102_product_first.py:260`）→ `match_text_g2`（:281-284）から呼ばれる。`match_text_g2` の呼び手は次の3つで、いずれも v102。
  - `backend/app/services/gemini_raw_copy_v102_product_first.py:637-638` `resolve_product_first`（変更前の行番号）
  - `backend/app/services/gemini_raw_copy_v102_followup.py:48`
  - `backend/app/services/gemini_raw_copy_v102_soldout_ref.py:169`
  - `backend/app/services/v102_gap_lines.py:175,202`
  - 4つとも `ProductFirstMasters`（masters["product_first"]）を受け取り `match_text_g2` に渡す。索引（G2Index）に持たせた合図の語は全部に届く。
- `match_product`: `match_product_g2`（:261）が `base = match_product(block, index.base_entries, strict_codes=True)` で呼ぶ。最終候補は G2 側（:260）で決まり、base は matched_keywords / excluded_by / boundary_dropped などの記録の欄用。v102 の経路から呼ばれるので、同じ合図の語を渡す（記録と候補の食い違いを避けるため）。
- `_is_candidate`: `match_product`（:295）からのみ呼ばれる。同じく v102 の経路。同じ合図の語を渡す。
- `match_product` を v102 以外から呼ぶ場所: backend/app 内の grep（`grep -rn "match_product\b" backend --include='*.py'`）で、本体以外の呼び手は `match_product_g2` のみ（テストを除く）。
- 試作版ツール `backend/app/tools/prompt_ab.py`（:247） は `load_product_first_masters(session)` を直接呼んで masters["product_first"] を作り直す。ここは合図の語を持たない（既定の空＝従来どおり）。今回の対象外（本番の v102 は `load_v102_masters` を通る）。

## 4. 状態マスタ（合図の語）
- テーブル: `public.conditions`。読む関数 `backend/app/services/tcg_analyzer_svc.py:651-729` `load_condition_entries`
  - 有効条件: `is_active = TRUE AND priority IS NOT NULL AND priority > 0`（:667-673）
  - search_kw はカンマ区切りの1文字列、match_type 既定 KEYWORD（:710）。REGEX の search_kw は正規表現文字列なので語として扱えない（:792-805 `_entry_hit`）
- v102 が既に読んでいる: `backend/app/services/line_analysis_v102_svc.py:196` `cond_entries = analyzer.load_condition_entries(session)`、:199-200 で `masters["cond_entries"]`（`load_v102_masters` :191-206）、:202 で `"product_first": load_product_first_masters(session)`
- 「状態マスタ」は public.conditions と解釈した（備考 `load_note_master`・ステータス `load_status_master` は対象外）。

## 5. v6 経路（変更しない）
- `backend/app/services/tcg_analyzer_svc.py:304-342` `match_keyword`、:555-587 `match_pid_with_work` は別実装。`extraction_judgement_svc._excluded_keywords` を import していない。v102 の変更は v6 に波及しない。

## 6. 試算（既存調査より。数値のみ）
- 母集団: v102 の全 extraction_items × analysis_results の 7,963 行（is_current の真偽を問わない）。
- 包含ルール版の試算で、7,963 行中 5 行の商品決定が変わる（PO 承認済みの数値）。本文・ID は載せない。
- 既存調査の実行結果の原本は作業者の手元（リポジトリ外）。CN0013「ARパック」の search_kw・match_type・priority の本番の値は、この PR では未確認（DB 未接続）。

## 7. 未確認
- conditions.search_kw の本番データの全語（件数・長さ分布）。実装は語を実行時に読むので、実装の正しさには影響しない。
- `backend/app/tools/prompt_ab.py` 経由の試作版ツールの結果は、今回の変更では変わらない（意図）。
