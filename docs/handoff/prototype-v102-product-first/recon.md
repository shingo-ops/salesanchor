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
