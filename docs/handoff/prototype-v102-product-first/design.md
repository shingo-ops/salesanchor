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

## 追記（商品が決まらない件の理由）
- 件の review に、unmatched は product_not_in_master、ambiguous は product_multiple（候補の id）、matched で boundary_dropped があれば product_boundary（消えた候補の id）を足す。試運転（extraction_shadow_svc.py）の要確認と同じ判定。状態・単位・商品の値は変えない。
- 触るファイル: backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_gemini_raw_copy_v102_product_first.py

## 追記（作品をまたぐ曖昧な商品を前後の商品の作品で決める）
- PO 決定（2026-10-08）：(a) 前後の商品が同じ作品なら決める。(b) 片側だけ・(c) 前後2件ずつの多数決は、落とす候補の作品がその投稿に無いときだけ決める。それ以外は要確認。
- 手がかりは1回目に matched の件だけ（この処理で決めた件は手がかりにしない）。決めた件は match_status=matched_context・product_context（rule・手がかり・落とした候補）を持ち、決めた商品の分類で単位・状態を作り直す。決まらない件は product_multiple に context_reason を足す。product_first なし・v101 の出力は不変。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|試算（手元 sim2.py）と同じ決定|保存済み応答と本番マスタ相当で作り直し、決定・理由が試算と全件一致（r1 51/51・101/101、r2 53/53・100/100、不一致0）|
|対象外の件は変わらない|main と本便のコードで同じ作り直しをして対象外の全欄の差分0件（r1 2,268件・r2 2,266件）|
|既存の出力を壊さない|pytest（新規19件＋既存の v101/v102/prompt_ab 系）|

- 触るファイル: backend/app/services/gemini_raw_copy_v102_context_work.py, backend/app/services/gemini_raw_copy_v101.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_gemini_raw_copy_v102_context_work.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md

## 追記（品番らしい値は原文の書き方のまま前後が区切られているときだけ当たり）
- 規則：match_product に strict_codes（既定 False）を足し、試作版 resolve_product_first だけ True で呼ぶ。True のとき、product_code・mark・検索ワードの各語のうち「fold 後の文字が英数字・区切り文字・記号(P*/S*)だけで、英字を含み、英数字が3文字以上」の値は、値の英数字を順に並べて文字の間に区切り文字（空白・ハイフン類・中黒・下線・ピリオド・アポストロフィ類。改行は除く）を0個以上許す正規表現に当たり、かつ前後が [a-z0-9] でないときだけ当たり。値の中の記号はパターンに入れない。かな・漢字を含む値、数字だけの値、2文字以下の値は今のまま。False のときは1文字も変えない。v6・試運転・tcg_shadow_review は変えない。
- 基準と検証方法：

|基準|検証方法|
|---|---|
|試算と同じ結果|保存済み応答＋本番マスタ相当で、after3 の全件（r1 3,350・r2 3,352）の match_product の候補の変化が strict-sim/v2 の status_changes.tsv と全件一致（Re:ゼロ Vol.4 の候補外しは起きないのが正しい）。結果 6,702/6,702 一致|
|本番・試運転の照合は不変|strict なしの match_product の出力が main と全件同じ（after3 の 6,702件で cmp 一致）＋テスト|
|前後の商品で決める処理と合わせて矛盾なし|response_text から作り直し、matched_context の件数と一覧を main と比較（件数のみ PR に記載）|

- 触るファイル: backend/app/services/extraction_judgement_svc.py, backend/app/services/gemini_raw_copy_v102_product_first.py, backend/tests/test_extraction_judgement_svc.py, docs/handoff/prototype-v102-product-first/design.md, docs/handoff/prototype-v102-product-first/recon.md
