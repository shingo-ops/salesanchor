-- rollback.sql: snapshot.txt の値へ戻す + unit_aliases 2行を削除（文書として保管。実行は PO 合意と permit-danger 手順が必要）
BEGIN;
DO $do$
DECLARE c int; n int := 0; a int := 0;
BEGIN
-- SP-00004 伊石侑生
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00004' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00005 カンジン
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00005' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00006 貞弘昂平
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00006' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00007 倉田 和博
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00007' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00011 星野 良介
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00011' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00018 SAMURAI-T
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00018' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00020 矢ヶ嵜裕史
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00020' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00029 JUN OKUBAYASHI
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00029' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00031 Yasu Kishi
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00031' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00033 T
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00033' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00034 かあ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00034' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00036 末吉宏成
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00036' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00037 株式会社モノウリ ハタナカ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00037' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00042 平田光希
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00042' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00043 武
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00043' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00044 miki
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00044' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00053 H
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00053' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00067 MASAKI MIYAZAKI
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00067' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00075 Rikiya
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00075' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00107 けい
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00107' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00111 たいし
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00111' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00112 たいち
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00112' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00116 ないとう なっちゃん
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00116' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00122 もと
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00122' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00127 り
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00127' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00133 ビヨンドスタッフ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00133' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00136 下司弘樹
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00136' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00138 中村　敦
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00138' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00141 佐々木優太
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00141' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00143 吉田
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00143' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00163 株式会社KMS
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00163' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00164 ㍿NGA
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00164' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00184 overlap
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00184' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00187 西田　翼
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00187' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00188 大嶋雅人
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00188' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00190 シンソク
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00190' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00191 ヨシヤス
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00191' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00192 徳武俊太郎
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00192' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00198 とも
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00198' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00199 oyama
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00199' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00200 やまちゃん
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00200' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00201 kyosuke
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00201' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00202 大知
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00202' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00203 株式会社AXISグリーン
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00203' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00205 中山友貴
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00205' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00207 ゆうき
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00207' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00209 渡邉史弥(仕事用)
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00209' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00210 ryuya
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00210' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00211 Shintaro
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00211' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00214 竹内スタッフ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00214' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00215 なかひら
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00215' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00217 SIG
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00217' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00220 吉田翔
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00220' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00222 つきじ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00222' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00223 むらお
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00223' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00224 ガク
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00224' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00226 貴大
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00226' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00227 たくぞ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00227' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00228 小菅圭輔
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00228' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00229 加地-スタッフアカウント
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00229' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00230 ヒロト
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00230' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00231 りょう
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00231' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00233 Yuki
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00233' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00234 RAITO
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00234' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00237 ぱ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00237' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00238 たいき
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00238' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00239 まー
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00239' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00241 Ryum.
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00241' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00248 竹内
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00248' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00249 keny
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00249' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00250 YORO（株）スタッフ2
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00250' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00251 佐藤
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00251' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00252 takuya
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00252' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00261 旭野
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00261' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00262 河合潤也
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00262' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00263 のりゆき
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00263' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00265 齊藤大輔
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00265' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00270 三海
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00270' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00271 yuyaさいとう
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00271' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00272 Ryu
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00272' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00273 鈴木
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00273' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00274 屋比久大
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00274' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00277 Mie
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00277' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00278 kaishi
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00278' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00286 やまざきけんと
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00286' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00287 Nexus
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00287' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00290 Ren
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00290' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00292 Fukiko♡
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00292' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00294 Takahiro.Y
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00294' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00295 村上 宝聡
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00295' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00300 Taisei
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00300' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00303 かおり
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00303' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00307 Hironobu Yasukawa
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00307' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00308 小菅圭輔 こすがけいすけ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00308' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00316 鈴木 章裕
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00316' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00317 Mie (*´ω`*)
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00317' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25954 Yuki Sato
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-25954' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25955 Ryum. a
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-25955' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25956 佐藤 亮
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-25956' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25957 一場誠
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-25957' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25971 Y Mitamura
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-25971' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26012 東 智志
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-26012' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26015 伊藤裕輝
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-26015' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26016 つかさ
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-26016' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26021 al.japan 株式会社
UPDATE public.suppliers SET
    extraction_price_format = NULL,
    extraction_qty_format = NULL,
    extraction_order_pattern = NULL,
    extraction_default_unit = NULL,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = NULL,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-26021' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00023 株式会社N&U
UPDATE public.suppliers SET
    extraction_order_pattern = $q$price_at_qty$q$,
    extraction_notes = $q$価格@数量 の形式（SIGと逆）。例: 12000@20。シュリなし等の注記が商品名に付く$q$
WHERE supplier_code = 'SP-00023' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00157 斉藤
UPDATE public.suppliers SET
    extraction_order_pattern = $q$qty_unit_at_price$q$,
    extraction_notes = $q$円は通貨記号であり単位ではない。単位はBOX/枚/パック。例: 30BOX@27,300円$q$
WHERE supplier_code = 'SP-00157' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00178 達也
UPDATE public.suppliers SET
    extraction_order_pattern = $q$labeled_lines$q$
WHERE supplier_code = 'SP-00178' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00189 funスタッフ
UPDATE public.suppliers SET
    extraction_order_pattern = $q$qty_unit_at_price$q$
WHERE supplier_code = 'SP-00189' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00194 Gスタッフ
UPDATE public.suppliers SET
    extraction_order_pattern = $q$price_stock_qty$q$
WHERE supplier_code = 'SP-00194' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25952 SIG 原屋敷
UPDATE public.suppliers SET
    extraction_order_pattern = $q$qty_at_price$q$,
    extraction_notes = $q$商品名 数量@価格 の形式。例: ストームエメラルダ 200@11500$q$
WHERE supplier_code = 'SP-25952' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26017 GALLERY営業部
UPDATE public.suppliers SET
    extraction_order_pattern = $q$at_price_slash_stock$q$
WHERE supplier_code = 'SP-26017' AND tenant_id IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'rollback UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;

DELETE FROM public.line_unit_aliases WHERE alias_text = $q$packs$q$ AND lang = 'ja' AND unit_id = (SELECT id FROM public.line_units WHERE canonical = $q$Pack$q$);
GET DIAGNOSTICS c = ROW_COUNT; a := a + c;
DELETE FROM public.line_unit_aliases WHERE alias_text = $q$ctn$q$ AND lang = 'ja' AND unit_id = (SELECT id FROM public.line_units WHERE canonical = $q$Case$q$);
GET DIAGNOSTICS c = ROW_COUNT; a := a + c;

IF n != 112 THEN RAISE EXCEPTION 'rollback suppliers=% expected=112', n; END IF;
IF a != 2 THEN RAISE EXCEPTION 'rollback aliases deleted=% expected=2', a; END IF;
END
$do$;
COMMIT;
