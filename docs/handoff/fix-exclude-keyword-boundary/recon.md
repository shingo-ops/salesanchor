# Recon: 除外ワードの語境界

recon: docs/handoff/fix-exclude-keyword-boundary/recon.md
作業日: 2026-10-14

## 既存 ADR 検索（git grep -i docs/adr/ ・ FEATURE-INDEX）
- 「exclude_keyword／除外キーワード／除外語」で git grep した結果、ADR-093・ADR-100・ADR-1001・ADR-1002・ADR-154・ADR-155 が出た。いずれもマスタの列・移行・名前の登録に関する記述で、除外語の照合規則（語境界）を定めた箇所は無い（ADR-154 は除外語のデータ追加の記述）。ADR と実装の食い違いは見つからなかった。

## 現在地（事実）
- backend/app/services/extraction_judgement_svc.py:57-59 `_needs_boundary`（2文字以下・数字だけの値は語の境界が要る）
- backend/app/services/extraction_judgement_svc.py:61-67 `has_word_boundary`（前後が英字・数字でない、の両側判定）
- backend/app/services/extraction_judgement_svc.py:201-215 `_value_hits`: 検索ワード・品番は `_needs_boundary` のとき両側の境界を条件にする
- backend/app/services/extraction_judgement_svc.py:247-267 `_excluded_keywords`: 品番らしい除外語（strict）以外は、修正前は `normalized in nb` だけ（語境界なし）
- 呼び出し元: backend/app/services/extraction_judgement_svc.py:296（match_product）、backend/app/services/gemini_raw_copy_v102_product_first.py:235（_g2_hits）。いずれも folded を渡す
- 既存テスト backend/tests/test_extraction_judgement_svc.py:770-774 `test_strict_two_char_exclude_keeps_substring`: 除外「SR」が「SRR」に当たる（語頭から始まる部分一致）。これを保つため、右側は条件にしない

## 問題
- 除外「AR」が「25th ANNIVERSARY」の中の ar（直前が s）に当たり、商品が unmatched になる。
