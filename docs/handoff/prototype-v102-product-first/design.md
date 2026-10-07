# Design: prototype-v102-product-first

## 参照
- recon: docs/handoff/prototype-v102-product-first/recon.md
- ADR-155: docs/adr/ADR-155-product-master-ssot-csv-app.md（判定の言葉はマスタから読む）

## KGI
prompt_ab の v102（recompute を含む）で、1件ごとに商品・商品の分類・単位・状態が「商品先行」の流れで出て、記録（product_id・product_category・match_status・match_candidates・unit_basis・condition_basis）から判断の根拠が追える。v101 以前の出力、本番 v6、試運転は変わらない。

## 設計
- 新規 backend/app/services/gemini_raw_copy_v102_product_first.py（v101 を import しない）
  - 材料: load_product_entries、load_product_kubun_type_map（既存）、line_conditions.unit_id → line_units.canonical、line_unit_ignore_phrases の is_active=true。商品・分類・状態の単位が空なら ValueError。言い回しの表は空でもよい。
  - 単位: 価格の行 → 在庫の行 → 名前の行 → その他の行。価格の行は今の位置の条件、見つからなければ区切りの照合（別名の前後が行の端・空白・記号・数字）。区切りの照合で当たった別名は、(a) 照合で当たった商品の検索ワードの語の範囲、(b) 単位にしない言い回しの範囲（正規化・空白0個以上）の中なら採らない。
  - 状態: 商品が箱系で単位区分が 空・不明・条件つき・複合・数量専用 → 箱系で resolve_condition_v2。商品も単位も不明で単位既定の落ち先（R4:単位既定:単位不明）なら状態「不明」＋理由 condition_unknown。補った区分と適用区分が違う状態の行にも当たる場合は、箱系の結果のまま理由 condition_multiple_candidates と code 一覧を残す（適用区分が空の行・単品の行は対象外）。
  - 状態から単位: 単位なし、または単位区分が「条件つき」で商品が箱系のとき、状態の unit_id の単位を当てる。
  - 区分の値（箱系・不明・条件つき等）は定数 1 か所にまとめ、どのマスタの値かをコメントに書く。
- backend/app/services/gemini_raw_copy_v101.py: V101Context に product_first（既定 None）、extract_v101_items に product_first 引数。v102_fixes=True かつ渡されたときだけ新しい流れ。
- backend/app/tools/prompt_ab.py / prompt_ab_recompute.py: _load_v10_masters(session, product_first=True) で v102 のときだけ読む。
- 触らない: tcg_analyzer_svc.py / extraction_shadow_svc.py / tcg_extraction.py、resolve_condition_v2 / resolve_unit_v2 / match_product / find_unit_alias の中身。

## 基準と検証方法
|基準|検証方法|
|---|---|
|単位なし×箱系・シュリンク付き・難あり×個 が期待の状態と単位|backend/tests/test_gemini_raw_copy_v102_product_first.py|
|カートン（名前の行・価格の行）が Case・Case|同上|
|言い回しの表で除外、空なら採る、数字の後ろは今のまま|同上|
|検索ワードの範囲の別名を採らない|同上|
|商品不明×単位不明が状態「不明」・理由 condition_unknown|同上|
|別区分にも当たる場合 condition_multiple_candidates|同上|
|v101（v102_fixes=False）・v10.2 の出力が不変|test_gemini_raw_copy_v101.py ほか既存テスト failed 0|
|v6・試運転を触っていない|git diff --name-only origin/main...HEAD に 3 ファイルが無い|
|試算の結果|PO 検査 40/40、意図しない変化 0（手元の試算）|

## 外部・過去事例の参照と我々への応用
- 過去事例: 社内の R4c（商品分類既定）が同じ発想（商品の分類で単位区分の不足を補う）。本便は同じ比較を v102 の道具の中で、定数にまとめて行う。
- 外部事例: 商品マスタを先に引いてから属性（単位・状態）を決める「エンティティ解決先行」の抽出手法（商品カタログ照合を属性抽出の前段に置く一般的な設計）。応用: 照合結果と除外理由を記録に残し、人が確認できる形にした。

## 維持の仕組み
- 判定の言葉はマスタから読む（ADR-155）。言い回しは画面（便1）から登録する。
- 区分の値の比較は定数 1 か所。テストが期待値を固定し、CI が常時検査する。
- マスタが空なら黙って続けず止める。

## 触るファイル
触るファイル: backend/app/services/gemini_raw_copy_v101.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/app/tools/prompt_ab.py, backend/app/tools/prompt_ab_recompute.py, backend/tests/test_gemini_raw_copy_v102_product_first.py, backend/tests/test_prompt_ab.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md
