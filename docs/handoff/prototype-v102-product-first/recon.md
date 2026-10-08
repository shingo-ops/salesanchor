# Recon: prototype-v102-product-first（試作版 v102 の商品先行の流れ・便3）

実測時の origin/main: c91559f67b0641463380876b3c208a6d99444e53

## 目的
試作版 v102 だけ、商品を先に特定し、商品の分類をもとに「単位 → 状態 → 状態から単位」を決める。本番 v6・試運転は変えない。

## 既存 ADR 検索
- docs/adr/ADR-155-product-master-ssot-csv-app.md（マスタ値はコードに直書きせず表から読む）
- docs/adr/ADR-027-ui-internationalization.md（本便は UI なし。対象外の確認）

## 現状（実物）
- backend/app/services/gemini_raw_copy_v101.py:696 付近の _extract_one が、単位を _find_unit（価格の行 → 在庫の行 → 別名だけの名前の行）で探し、resolve_condition_v2 に単位の区分だけを渡している。商品は見ていない。
- backend/app/services/tcg_analyzer_svc.py:889 付近の R4c に、商品の分類（箱系）と単位区分（条件つき・複合・数量専用）の比較が既にある。
- backend/app/services/tcg_analyzer_svc.py の load_product_kubun_type_map が、商品 ID → 分類（public.tcg_product_categories.kubun_type）を読む。
- backend/app/services/extraction_shadow_svc.py の load_product_entries が商品リストを読む。
- backend/app/tools/prompt_ab.py の _load_v10_masters が v10・v101・v102 共通のマスタ読み込み。v10・v101 は **masters で展開されるため、キーを足せるのは v102 のときだけ。
- 状態ごとの単位は public.line_conditions.unit_id（migrations/20260925_020000_conditions_add_def_unit_note.sql）。旧名の view（public.conditions）は列が増える前の複製のため、表名 line_conditions / line_units を直接読む。
- 単位にしない言い回しの表: migrations/20261008_100000_create_line_unit_ignore_phrases.sql（便1・PR #4032、main 反映済み）。

## 試算の結果（社外秘の原文は載せない）
- 試算コード（手元）: sim4.py（単位の探し方・区切りの照合・検索ワードの範囲での除外・状態・状態から単位）、sim6.py（言い回しの表での除外）。
- PO 検査: 40/40 が期待どおり。意図しない変化: 0 件。
- 本便の実装は試算の挙動を基準にした。

## 追記（作品をまたぐ曖昧な商品・2026-10-08）
- 曖昧な件は backend/app/services/gemini_raw_copy_v102_product_first.py の resolve_product_first（L312-337）で match_product が ambiguous を返し、_product_reviews（L270-278）が product_multiple を付けるだけで、前後の商品は見ていない（origin/main 87c018f8）。
- 1投稿の items が揃う所は backend/app/services/gemini_raw_copy_v101.py の _extract_v102 のループ後（L925-926）。ProductEntry（backend/app/services/extraction_judgement_svc.py L108-115）に work_id がある。
- 試算（手元・社外秘の原文は載せない）：対象 r1 152件・r2 153件、PO 規則で決定 r1 51件（a46・b5・c0）・r2 53件（a46・b7・c0）。

## 追記（品番らしい値の厳格な照合・2026-10-08）
- 現状（origin/main 8f27d5449）：backend/app/services/extraction_judgement_svc.py の normalize_for_match（L31-44）が空白・改行・記号を消すため、_value_hits（L131-138）は「EX10」が「ex 100@…」に、「RB01」が「PRB-01」に、「ARD」が「CARD」に当たる。_needs_boundary（L57-59）が境界を求めるのは2文字以下・数字だけの値だけ。呼び出し元：backend/app/services/gemini_raw_copy_v102_product_first.py の resolve_product_first（match_product）、backend/app/services/extraction_shadow_svc.py L269（試運転）、backend/app/services/tcg_shadow_review_svc.py L282。
- 既存 ADR 検索：着手前に docs/adr/ を照合の機能キーワードで検索（ADR-155 ほか。照合の規則を変える ADR は無し）。
- 試算：docs 外の手元の strict-sim/v2。誤りと判定した310候補はすべて外れ、候補が複数→1つ 226件（r1）、減るだけ 48件、1つに決まっていた件の悪化 0。
- 実装中に分かったこと：対象の判定を「英数字・区切り文字だけ」にすると `SM5+` のように記号を含む値が既存の規則に落ち、試算と 64 件ずれた。設計者判断で「英数字・区切り文字・記号（P*/S*）だけで英字を含む」に広げた（記号はパターンに入れず、前後の境界で見る）。

## 追記（候補が複数残った件の提案・2026-10-08）
- 現状（origin/main 5da0d5964）：ambiguous は backend/app/services/gemini_raw_copy_v102_product_first.py の _product_reviews が product_multiple（候補 id のみ）を付けるだけ。前後の商品で決める処理は backend/app/services/gemini_raw_copy_v101.py の _extract_v102 内 _apply_context_work。MatchResult は backend/app/services/extraction_judgement_svc.py L118-128 で、当たった品番・記号の情報を持たない。
- 既存 ADR 検索：docs/adr/ を照合・商品特定のキーワードで検索（ADR-155 ほか。この規則を変える ADR は無し）。
- 試算：手元 score-sim/v2（S1+S4）。after7 で r1 148・r2 147 件が決まり、原文で全件確認して誤り0。前後の商品で決めた件と両方決まる27件は全件一致。

## 追記（商品の境目を要確認の理由から外す・2026-10-08）
- 現状（origin/main 0066232b6）：backend/app/services/gemini_raw_copy_v102_product_first.py の _product_reviews が、matched で match.boundary_dropped があると product_boundary の要確認を付ける。戻り dict（resolve_product_first）に boundary_dropped の控えは無い。v101 は backend/app/services/gemini_raw_copy_v101.py の _extract_v102 内 extra で、戻り dict から product_id・product_category・match_status・match_candidates・unit_basis だけを出力の行に移す。
- 既存 ADR 検索：docs/adr/ を照合・商品特定・境界のキーワードで検索（ADR-155 ほか）。この規則を変える ADR は無し。
- 集計（原文は書かない）：手元 boundary-1st/boundary.md。r1 733件・r2 736件。境界で落ちた候補 延べ約2,300 を原文で確かめ、落ちるべきでなかった候補 0。
- 試運転 backend/app/services/extraction_shadow_svc.py:303 の product_boundary は別系統。本便では変えない。

## 追記（除外ワードにも前後が区切られているときだけ当たりを当てる・2026-10-08）
- 現状（origin/main 0066232b6）：backend/app/services/extraction_judgement_svc.py の _excluded_keywords（L228-235）は除外ワードを正規化して部分一致で見る。除外「SAR」が「anniversary」の中で当たり、3rd アニバーサリーセットが除外される。呼び出し元：同ファイル match_product L273、_is_candidate L242（boundary_dropped の控え用、本便では変えない）。
- 既存 ADR 検索：docs/adr/ を照合・除外ワードのキーワードで検索（ADR-155 ほか。この規則を変える ADR は無し）。
- 試算（手元 excl-strict、社外秘のため件数のみ）：after8 の全 7,395 品目で判定が変わる件 0、品番らしい除外ワードが当たっていた延べ 118 回はすべて当たりのまま。
