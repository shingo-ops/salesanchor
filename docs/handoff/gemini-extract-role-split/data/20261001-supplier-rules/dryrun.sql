-- dryrun.sql (apply.sql の最後の COMMIT を ROLLBACK に置換): suppliers extraction rules (105 new + 7 convert) + unit_aliases 2 rows
-- 対象外(keep): SP-00010, SP-00196, SP-00257
-- 除外(new、既存値あり): なし
BEGIN;
DO $do$
DECLARE
  c int; n int := 0; a int := 0;
  expected_updates CONSTANT int := 112;
  expected_aliases CONSTANT int := 2;
BEGIN
-- SP-00004 伊石侑生 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円は付かないことが多い。バラは{数値}円）$q$,
    extraction_qty_format = $q${数値}BOX / {数値}パック / {数値}枚 / {数値}カートン$q$,
    extraction_order_pattern = $q$["price","×","quantity","unit","status"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末に付記（シュリ無し、傷有り、サーチ済み）$q$,
    extraction_ship_format = $q$冒頭「当日16:00までのご注文で当日国内発送」$q$,
    extraction_notes = $q$商品名の行の下に「価格×数量単位」の行が1〜複数（状態違い）続く。◇で始まる行以降は定型文。$q$,
    extraction_example_text = $q$30th CELEBRATION BOX 
27,500×18BOX
26,500×8BOX（傷有り）
25,500×15BOX シュリ無し
$q$
WHERE supplier_code = 'SP-00004' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00005 カンジン (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠の後ろの{数値}円$q$,
    extraction_qty_format = $q${数値}個$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$個$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$冒頭「明日N日発送商品のご案内」「14時までのご注文で当日発送」$q$,
    extraction_notes = $q$【区分】→◆商品名→「N個＠価格円」。「商品名 〆」は完売、「商品名＠N個」は残数の案内。・で始まる行以降は定型文。$q$,
    extraction_example_text = $q$◆30th　CELEBRATION
40個＠27500円

◆30th CELEBRATION FUTURISTIC BOX
1個＠66000円$q$
WHERE supplier_code = 'SP-00005' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00006 貞弘昂平 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["stock_label","quantity","/","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンク無し）$q$,
    extraction_ship_format = $q$【予約商品】は入荷次第順次発送$q$,
    extraction_notes = $q$・商品名 →「在庫N/価格円」。バルク（RR/RRR 被りあり）は1枚あたりの価格。$q$,
    extraction_example_text = $q$・メガドリーム　 
在庫50/13500円

・ストームエメラルダ　 
在庫50/11800円$q$
WHERE supplier_code = 'SP-00006' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00007 倉田 和博 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$単位/¥{数値}$q$,
    extraction_qty_format = $q$残り{数値}（完売は在庫なし）$q$,
    extraction_order_pattern = $q$["unit","/","yen_prefix","price","newline","残り","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$字下げした行（シュリ無し 等）$q$,
    extraction_ship_format = $q$予約は「入荷次第出荷」「N月入荷分」$q$,
    extraction_notes = $q$⚫︎商品名（複数行）→「単位/¥価格」→「残りN」または「完売」。同じ商品の下に状態違いが字下げで続く。「他カートン」の「商品名×N」は価格なし。【重要】以降は定型文。$q$,
    extraction_example_text = $q$　キャンペーンパック
　10パックセット/¥5,000
　完売
$q$
WHERE supplier_code = 'SP-00007' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00011 星野 良介 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}BOX / {数値}Pack$q$,
    extraction_order_pattern = $q$["quantity","unit","：","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$冒頭「17時まで当日発送可能」、行末（届き次第発送）$q$,
    extraction_notes = $q$『商品名』→「数量単位：価格」。$q$,
    extraction_example_text = $q$『30th デッキセット』
15BOX：19,500

『FUTURISTIC BOX』
10BOX：67,000$q$
WHERE supplier_code = 'SP-00011' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00018 SAMURAI-T (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$単価：{数値}$q$,
    extraction_qty_format = $q$数量：{数値}カートン/BOX/セット/個$q$,
    extraction_order_pattern = $q$["数量：","quantity","unit","newline","単価：","price"]$q$,
    extraction_default_unit = $q$カートン$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$商品ごとに「✅発送日①（要相談）」「✅即日発送可」「✅入荷次第発送」$q$,
    extraction_notes = $q$⚫︎商品名 → ✅発送 →「数量：N単位」→「単価：価格」（縦のラベル形式）。1行形式「⚫︎商品名　数量：N単位　単価：価格」もある。【予約品】【在庫品】の区分あり。$q$,
    extraction_example_text = $q$✅発送日①（要相談）
数量：56カートン
単価：290,000

⚫︎神の支配【OP-18】$q$
WHERE supplier_code = 'SP-00018' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00020 矢ヶ嵜裕史 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/カートン/個$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$商品名に（10/2入荷）、※土日祝発送休み$q$,
    extraction_notes = $q$◆商品名 →「数量単位　＠価格円」。「1個　75,000円」のように＠が無い行もある。$q$,
    extraction_example_text = $q$◆ONE PIECE Card Game ANNIVERSARY SET "English Version 3rd Anniversary Set"
1個　69,800円

◆OP-17
10カートン　＠175,000円$q$
WHERE supplier_code = 'SP-00020' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00029 JUN OKUBAYASHI (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円（円が無い行もある）$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["quantity","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$数量の前に付記（シュリあり3@26300円）$q$,
    extraction_ship_format = $q$※発売日前日発送$q$,
    extraction_notes = $q$■/◼︎商品名 →「数量@価格」。目印の無い「数字@数字」は必ず 数量@価格（例：メガブレイブ 108@9800）。$q$,
    extraction_example_text = $q$■30th CELEBRATION BOX
シュリあり4@27400円

◼︎MEGAスタートデッキ100
※買取品の為サーチ済の可能性あり$q$
WHERE supplier_code = 'SP-00029' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00031 Yasu Kishi (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}箱/カートン（単位なしもある）$q$,
    extraction_order_pattern = $q$["price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$箱$q$,
    extraction_state_format = $q$価格行の前の行（※角小潰れ…、シュリンク無し）$q$,
    extraction_ship_format = $q$冒頭「⚠️9/30明日対応です⚠️」、日祝休み$q$,
    extraction_notes = $q$商品名 →「価格×数量単位」。× と x、空白の有無が揺れる。目印の無い「数字×数字」は必ず 価格×数量（例：18000×60）。$q$,
    extraction_example_text = $q$ORIGINAL ART COLLECTION 
7400 x 50箱


30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー$q$
WHERE supplier_code = 'SP-00031' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00033 T (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$¥{数値}/単位$q$,
    extraction_qty_format = $q${数値}BOX/カートン/冊/セット$q$,
    extraction_order_pattern = $q$["quantity","unit","newline","yen_prefix","price","/","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「数量単位」→「¥価格/単位」（縦3行）。価格の桁区切り誤記あり（¥4,0000）。単独の「〆」は直前の投稿の完売。$q$,
    extraction_example_text = $q$OP-07
1カートン
¥200,000/カートン

OP-08$q$
WHERE supplier_code = 'SP-00033' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00034 かあ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円（円が無い行もある）$q$,
    extraction_qty_format = $q${数値}枚（単位なしもある）$q$,
    extraction_order_pattern = $q$["price","yen","×","quantity"]$q$,
    extraction_default_unit = $q$枚$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$1行で「名前価格円×数量」または「名前数量枚価格円」。目印の無い「名前数字×数字」は 価格×数量（例：ストームエメラルダ12000×25）。「残りN枚」は直前の商品の残数。$q$,
    extraction_example_text = $q$AR195円×3000
モンボ5円×1520

国内発送着払い
転送サービス500円$q$
WHERE supplier_code = 'SP-00034' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00036 末吉宏成 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}円 / ¥{数値}$q$,
    extraction_qty_format = $q$在庫{数値}個/パック/冊/BOX$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$個$q$,
    extraction_state_format = $q$商品名に付記（シュリなし ペリなし）$q$,
    extraction_ship_format = $q$行末（12月入荷次第発送）$q$,
    extraction_notes = $q$1投稿の中で並びが揺れる：「@価格円　在庫N」「在庫N　＠価格円」「在庫N（改行）¥価格」「@価格×在庫N冊」「@価格×数量(注記)」。価格には必ず @/¥/円 が付く。目印の無い「@数字×数字」は @価格×数量。$q$,
    extraction_example_text = $q$ ¥72,000

(great ball)アビスアイ　パック　@140円　在庫700パック

※買取品なのでサーチの可能性大
$q$
WHERE supplier_code = 'SP-00036' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00037 株式会社モノウリ ハタナカ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$¥{数値}$q$,
    extraction_qty_format = $q$在庫{数値}個$q$,
    extraction_order_pattern = $q$["yen_prefix","price","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$個$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$冒頭「15時までのご注文で当日発送可能」$q$,
    extraction_notes = $q$1行で「●商品名　¥価格　在庫N個」。$q$,
    extraction_example_text = $q$15時までのご注文で当日発送可能です！

●アビスアイ　¥8,500　在庫38個
●ブラックボルト　¥23,000　在庫19個
●ブラックボルトDX　¥25,000　在庫21個
●ホワイトフレアDX　¥22,000　在庫23個$q$
WHERE supplier_code = 'SP-00037' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00042 平田光希 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名の次の行（シュリンク付き）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →［単位の行（カートン/BOX）］→「価格円 在庫N」。1商品に単位ごとの行が続く。「EB03〆」「デッキ〆」は略称の完売。$q$,
    extraction_example_text = $q$カートン
200,000円 在庫5
BOX
8,000円 在庫100
$q$
WHERE supplier_code = 'SP-00042' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00043 武 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円/ 1単位$q$,
    extraction_qty_format = $q${数値}点$q$,
    extraction_order_pattern = $q$["price","yen","/","1","unit","newline","quantity","点"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（（ラベル跡大）、（問屋品））$q$,
    extraction_ship_format = $q$商品名に（発送日要相談）$q$,
    extraction_notes = $q$◆商品名（仕入経路）→「価格円/ 1ケース」（または 1BOX）→「N点」。「/ 1ケース」は単位あたりの価格で数量ではない。数量は次の行の「N点」。$q$,
    extraction_example_text = $q$◆ホロライブ　ボリュームヴォルテックス（問屋）（発送日要相談）
5000円/ 1BOX
4点

◆ヴァイスシュヴァルツ 勝利の女神:NIKKE Vol.2（問屋）（発送日要相談）$q$
WHERE supplier_code = 'SP-00043' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00044 miki (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円（円なしもある）$q$,
    extraction_qty_format = $q${数値}箱$q$,
    extraction_order_pattern = $q$["quantity","unit","space","price","yen"]$q$,
    extraction_default_unit = $q$箱$q$,
    extraction_state_format = $q$次の行（シュリンクあり/なし）$q$,
    extraction_ship_format = $q$冒頭「今日発送」「明日発送」$q$,
    extraction_notes = $q$商品名 →「数量箱　価格円」。1行形式もある。$q$,
    extraction_example_text = $q$シュリンクあり
38箱　28,000円

遊戯王ARTWORK 80箱　7,900円
$q$
WHERE supplier_code = 'SP-00044' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00053 H (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}（単位なし）/ カートン$q$,
    extraction_order_pattern = $q$["price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名の次の行（段ボール未開封 等）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格×数量[単位]」。「BOX 8,000×12」のように単位が先頭に付く行もある。目印の無い「数字×数字」は必ず 価格×数量（例：18,500×1）。$q$,
    extraction_example_text = $q$スタートデッキ100コロコロコミック
16,000×1

スペシャルデッキセットex
フシギバナ.リザードン.カメックス$q$
WHERE supplier_code = 'SP-00053' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00067 MASAKI MIYAZAKI (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値} / {数値}BOX$q$,
    extraction_order_pattern = $q$["price","yen","/","stock_label","quantity"]$q$,
    extraction_default_unit = $q$カートン$q$,
    extraction_state_format = $q$商品名に付記（(緑テープ)）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名（単位込み）→「価格円/在庫N」。「4BOX@18,500円」（数量@価格）の行が混ざる。$q$,
    extraction_example_text = $q$30th CELEBRATION box
25,300円/在庫53

MEGA 30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー
4BOX@18,500円$q$
WHERE supplier_code = 'SP-00067' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00075 Rikiya (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/カートン/個/冊$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（検品のため一度開封済み）$q$,
    extraction_ship_format = $q$🟠予約🟠$q$,
    extraction_notes = $q$・商品名 →「数量単位@価格円」。$q$,
    extraction_example_text = $q$・ONE PIECE magazine Vol.21（ワンピースマガジン ヒロインズ 021）
200冊@3,500円

🔴ポケモン在庫🔴
・ストームエメラルダ$q$
WHERE supplier_code = 'SP-00075' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00107 けい (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$数量{数値} / 残り{数値}ボックス$q$,
    extraction_order_pattern = $q$["price","yen","space","数量","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク付き、※送り状跡あり）$q$,
    extraction_ship_format = $q$冒頭「17時までの注文で当日発送」、【予約】発売日発送$q$,
    extraction_notes = $q$🔥商品名 →［状態］→「価格円　数量N」または「価格円　残りNボックス」。「カートン　272,000円　数量1」のように単位が先頭の行もある。$q$,
    extraction_example_text = $q$🔥30th FUTURISTIC BOX
64,000円　数量3

🔥30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー
19,200円　数量14$q$
WHERE supplier_code = 'SP-00107' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00111 たいし (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（（シュリンクなし））$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$◆商品名 →「@価格円 在庫N」（1商品に複数行）。「◆ARバルク、50枚セット」の50枚は商品名の一部。$q$,
    extraction_example_text = $q$◆30th CELEBRATION
@26000円 在庫35

◆PRB-02
@272000円 在庫2$q$
WHERE supplier_code = 'SP-00111' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00112 たいち (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q$数量{数値}$q$,
    extraction_order_pattern = $q$["数量","quantity","space","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「17:00までのご注文で当日発送」$q$,
    extraction_notes = $q$商品名 →「数量N @価格」。$q$,
    extraction_example_text = $q$OP-17 世界最強の戦士
数量300 @12,000

・元払い東京発送
・17:00までのご注文で当日発送$q$
WHERE supplier_code = 'SP-00112' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00116 ないとう なっちゃん (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$¥{数値}$q$,
    extraction_qty_format = $q${数値}BOX/個/CTN$q$,
    extraction_order_pattern = $q$["yen_prefix","price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（（シュリンクなし））$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$1行で「・商品名 ¥価格 × 数量単位」。CTN はカートン。$q$,
    extraction_example_text = $q$━ ポケモンカード (BOX) ━
・MEGA拡張パック 30th CELEBRATION（シュリンクなし） ¥19,000 × 2BOX
・MEGA拡張パック 30th CELEBRATION FUTURISTIC BOX（特別セット） ¥49,000 × 6BOX

━ その他 ━$q$
WHERE supplier_code = 'SP-00116' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00122 もと (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（区切り無し）$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（しゅりあり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格在庫N」（例：10600在庫120）。$q$,
    extraction_example_text = $q$ストームしゅりあり
10600在庫120

30th
27900在庫14$q$
WHERE supplier_code = 'SP-00122' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00127 り (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/カートン$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（(シュリ無し)）$q$,
    extraction_ship_format = $q$見出し「※9/30発送分」$q$,
    extraction_notes = $q$☑️商品名 →「数量単位@価格円」。「下記商品　〆」＋一覧は完売。$q$,
    extraction_example_text = $q$☑️ FB-11
1BOX@8,000円
$q$
WHERE supplier_code = 'SP-00127' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00133 ビヨンドスタッフ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["stock_label","quantity","space","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名の次の行（シュリ無し）$q$,
    extraction_ship_format = $q$冒頭「9/18までに発送」、行末【9/17発送】$q$,
    extraction_notes = $q$商品名 →［状態］→「在庫N ＠価格［【発送注記】］」。$q$,
    extraction_example_text = $q$シュリ無し

在庫40  ＠20000

MEGA 30th CELEBRATION カードセット (9種セット)
$q$
WHERE supplier_code = 'SP-00133' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00136 下司弘樹 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/パック$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク無し、※買取品）$q$,
    extraction_ship_format = $q$冒頭「明日9/27発送」$q$,
    extraction_notes = $q$商品名 →［状態］→「数量単位@価格円」（BOX とパックの行が続く）。$q$,
    extraction_example_text = $q$ストームエメラルダ
20BOX@11,500円
シュリンク無し
20BOX@10,000円
※買取品$q$
WHERE supplier_code = 'SP-00136' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00138 中村　敦 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/カートン/冊/個/枚$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（ダメージ有り、検品のため開封済み）$q$,
    extraction_ship_format = $q$冒頭「在庫品は14時までのご注文で当日発送」$q$,
    extraction_notes = $q$商品名 →「数量［ ］単位@価格円」。一覧の中の「完売中」は完売。$q$,
    extraction_example_text = $q$ONE PIECE magazine Vol.21（ワンピースマガジン ヒロインズ 021）
200冊@3,500円

【遊戯王在庫商品】
LIMIT OVER COLLECTION$q$
WHERE supplier_code = 'SP-00138' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00141 佐々木優太 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}（円なし）$q$,
    extraction_qty_format = $q${数値}box/case（単位なしもある）$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$行末「発送日要相談」$q$,
    extraction_notes = $q$■商品名 →「数量[box]@価格」。目印の無い「数字@数字」は必ず 数量@価格（例：24@26,000）。「100@22,000  完売」は完売。価格の誤記あり（8,2500）。$q$,
    extraction_example_text = $q$・カードセット キモリ・アチャモ・ミズゴロウ

518box@3,800

・カードセット サルノリ・ヒバニー・メッソン
$q$
WHERE supplier_code = 'SP-00141' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00143 吉田 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$価格の前（シュリンクあり@…、ダメージ品）$q$,
    extraction_ship_format = $q$「14時半までのご注文により当日出荷」$q$,
    extraction_notes = $q$⚫︎商品名 →「[状態]@価格円 在庫N」。1行形式もある。$q$,
    extraction_example_text = $q$⚫︎30th CELEBRATION Booster BOX
シュリンクあり@28000円在庫30
シュリンク無し@25800円在庫5

⚫︎30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー$q$
WHERE supplier_code = 'SP-00143' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00163 株式会社KMS (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円が付く行もある）$q$,
    extraction_qty_format = $q${数値}box/カートン（単位なしもある）$q$,
    extraction_order_pattern = $q$["price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（(凹みあり)）$q$,
    extraction_ship_format = $q$行末(発送日要相談)$q$,
    extraction_notes = $q$商品名 →「価格×数量単位」。目印の無い「数字×数字」は必ず 価格×数量（例：1600×5）。「vstarユニバース　28,800円/33box」の形もある。$q$,
    extraction_example_text = $q$スターターセット イーブイ
2500円×10

スターターセット メガゲンガー
1600×5$q$
WHERE supplier_code = 'SP-00163' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00164 ㍿NGA (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}box / 在庫数 {数値}$q$,
    extraction_order_pattern = $q$["@","price","space","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$✅商品名 →「@価格 数量box」（または「在庫数 N」）。$q$,
    extraction_example_text = $q$ORIGINAL ARTWORK COLLECTION BOX
@9200 150box


ℹ️記載していない在庫複数あり（未開封品、PSA鑑定品など）$q$
WHERE supplier_code = 'SP-00164' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00184 overlap (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}個$q$,
    extraction_order_pattern = $q$["quantity","unit","space","price","yen"]$q$,
    extraction_default_unit = $q$個$q$,
    extraction_state_format = $q$次の行（美品/難あり/テープカット）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$【商品名】→ 状態 →「数量個 価格円」。「上記〆になります」の前の一覧は完売。$q$,
    extraction_example_text = $q$シュリンク付き美品
8個 28,000円
シュリンク付き難あり
23個 26,800円
$q$
WHERE supplier_code = 'SP-00184' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00187 西田　翼 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}カートン/BOX$q$,
    extraction_order_pattern = $q$["@","price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$カートン$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$行末(10/1〜10/2発送)$q$,
    extraction_notes = $q$●商品名【型番】→「@価格×数量 単位」。目印の無い「@数字×数字」は必ず @価格×数量。$q$,
    extraction_example_text = $q$●Vジャンプ　10月号 麦わらの一味3人の最強セット(ルフィ＆ゾロ＆サンジ)
@1200×1500(シリアル) ※明日応募〆切
@2000×1500(12月入荷次第発送)

●週刊少年ジャンプ プレミアムカードコレクション29周年エディション(通常版4枚+豪華版4枚)(12月入荷予定) $q$
WHERE supplier_code = 'SP-00187' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00188 大嶋雅人 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["quantity","space","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンク有）$q$,
    extraction_ship_format = $q$「9/22日、栃木または山梨からの発送」$q$,
    extraction_notes = $q$1行で「商品名 状態 数量 @価格」。目印の無い「数字 @数字」は必ず 数量 @価格。$q$,
    extraction_example_text = $q$9/22日、栃木または山梨からの発送の在庫です

30th CELEBRATION　BOX シュリンク有 200 @29000$q$
WHERE supplier_code = 'SP-00188' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00190 シンソク (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen","status"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末の[通常品][状態A-][状態B]$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$■種別「商品名」(型番) →「数量BOX@価格円[状態]」。状態ごとに行が続く。$q$,
    extraction_example_text = $q$■拡張パック「30th CELEBRATION」(M6a)
5BOX@28,000円[通常品]
2BOX@27,200円[状態B]

■拡張パック「ストームエメラルダ」(M6)$q$
WHERE supplier_code = 'SP-00190' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00191 ヨシヤス (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（ダメージ有り）$q$,
    extraction_ship_format = $q$「15時までのご注文で当日発送」$q$,
    extraction_notes = $q$商品名 →［状態］→「数量BOX@価格円」。$q$,
    extraction_example_text = $q$ダメージ有り
1BOX@16,000円

ストームエメラルダ
シュリンク無し、ダメージ有り$q$
WHERE supplier_code = 'SP-00191' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00192 徳武俊太郎 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク付き）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →［状態］→「価格円 在庫N」。$q$,
    extraction_example_text = $q$シュリンク付き
28000円 在庫20

30th CELEBRATION FUTURISTIC BOX フューチャリスティック ボックス
59,000円 在庫2$q$
WHERE supplier_code = 'SP-00192' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00198 とも (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}box$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「※即日発送可」$q$,
    extraction_notes = $q$商品名 →「数量box@価格」。$q$,
    extraction_example_text = $q$エーフィ・ブラッキー
100box@25,000
※即日発送可

国内発送元払い$q$
WHERE supplier_code = 'SP-00198' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00199 oyama (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}（円付きもある）$q$,
    extraction_qty_format = $q$在庫数 {数値}箱 / {数値}セット$q$,
    extraction_order_pattern = $q$["@","price","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（(シュリンク無し)）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$✅商品名 →「＠価格　在庫数 N箱」。$q$,
    extraction_example_text = $q$✅30th Celebration BOX　(シュリンク無し)
＠26,000　在庫数 11箱

✅RRR 100枚ランダムバルク  
@12000円　12セット$q$
WHERE supplier_code = 'SP-00199' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00200 やまちゃん (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}枚/セット$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price"]$q$,
    extraction_default_unit = $q$セット$q$,
    extraction_state_format = $q$商品名に付記（被りあり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$▪️商品名 →「数量単位 @価格」（バルク）。$q$,
    extraction_example_text = $q$▪️AR CHR 100枚 50種類以上
50セット @24,500

▪️AR CHR 100枚 被りなし
100セット @25,000$q$
WHERE supplier_code = 'SP-00200' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00201 kyosuke (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}BOX/カートン$q$,
    extraction_order_pattern = $q$["@","price","space","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（ラベル跡あり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$・商品名 →「@価格　数量単位」。$q$,
    extraction_example_text = $q$・30th CELEBRATION
@28,000　　25BOX

・MEGA 30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー
@19,000　　3BOX$q$
WHERE supplier_code = 'SP-00201' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00202 大知 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}BOX/セット$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「数量単位 @価格」。「30th 両方〆」など略称の完売。$q$,
    extraction_example_text = $q$30th セレブレーション BOX
12BOX @26000
30th FUTURISTIC BOX 
3BOX @60000
$q$
WHERE supplier_code = 'SP-00202' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00203 株式会社AXISグリーン (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["price","@","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク無、未サーチパック、ぺりぺり無）$q$,
    extraction_ship_format = $q$冒頭「9／30日国内発送分」$q$,
    extraction_notes = $q$◎商品名 →「価格@数量」。目印の無い「数字@数字」は必ず 価格@数量（例：27,500@27）。$q$,
    extraction_example_text = $q$◎30th CELEBRATION BOX
27,500@27
シュリンク無
25,000@11
未サーチパック$q$
WHERE supplier_code = 'SP-00203' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00205 中山友貴 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@ {数値}$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$商品ごとの「9/16(水)発送」$q$,
    extraction_notes = $q$■商品名 → 発送日 →「数量BOX @ 価格」。$q$,
    extraction_example_text = $q$9/16(水)発送
12BOX @ 70,000

■30th celebration BOX
9/16(水)発送$q$
WHERE supplier_code = 'SP-00205' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00207 ゆうき (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}箱$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「17時までのご注文で当日発送」$q$,
    extraction_notes = $q$・商品名 →「数量箱 @価格円」。$q$,
    extraction_example_text = $q$・世界最強の戦士 BOX
　6箱 @12,500円

・受け継がれる意志 BOX
　3箱 @18,000円$q$
WHERE supplier_code = 'SP-00207' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00209 渡邉史弥(仕事用) (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$×{数値}BOX/pack/冊$q$,
    extraction_order_pattern = $q$["@","price","yen","×","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$予約は見出し（(11/2発送)）$q$,
    extraction_notes = $q$▼商品名 →「@価格円 ×数量単位」。$q$,
    extraction_example_text = $q$▼ ポケモンカード 30th CELEBRATION
　@28,000円 ×80BOX

▼遊戯王 ORIGINAL ARTWORK COLLECTION
　@9,000円 ×200BOX$q$
WHERE supplier_code = 'SP-00209' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00210 ryuya (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$¥{数値}$q$,
    extraction_qty_format = $q${数値}箱$q$,
    extraction_order_pattern = $q$["yen_prefix","price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$箱$q$,
    extraction_state_format = $q$次の行（シュリンク付き）$q$,
    extraction_ship_format = $q$冒頭「9/20（日）国内発送」$q$,
    extraction_notes = $q$商品名 → 状態 →「¥価格×数量箱」。$q$,
    extraction_example_text = $q$シュリンク付き　

¥24,500×7箱

国内送料　着払い
配送業者　ヤマト運輸$q$
WHERE supplier_code = 'SP-00210' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00211 Shintaro (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}$q$,
    extraction_qty_format = $q$在庫数　{数値}$q$,
    extraction_order_pattern = $q$["@","price","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「12時までの注文で当日発送可能」$q$,
    extraction_notes = $q$✅商品名 →「＠価格　在庫数　N」。$q$,
    extraction_example_text = $q$✅スノーハザード　カートン
＠148000　在庫数　1


$q$
WHERE supplier_code = 'SP-00211' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00214 竹内スタッフ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}box/個/パック$q$,
    extraction_order_pattern = $q$["price","yen","/","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンク有り/無し）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名[状態] →「価格円/数量単位」（価格が先）。$q$,
    extraction_example_text = $q$メガブレイブシュリンク有り
9500円/100box
メガブレイブシュリンク無し
8200円/30box
$q$
WHERE supplier_code = 'SP-00214' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00215 なかひら (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/case/冊/個/set$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$【予約商品:発売日当日発送予定】$q$,
    extraction_notes = $q$🌈区分 → 商品名 →「数量単位　＠価格円」。「ﾏｽﾀｰｶｰﾄﾝ（7case入）＠価格」は数量なし。$q$,
    extraction_example_text = $q$ORIGINAL ARTWORK DUEL SET 遊戯編 城之内編 海馬編
 3種セット（BOX)　3set　＠56,000円(/1set)
🌈ONE PIECE （入荷日未定、入荷次第発送）
magazine Vol.21（ワンピースマガジン ヒロインズ 021）
　100冊 　＠3,500円$q$
WHERE supplier_code = 'SP-00215' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00217 SIG (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["quantity","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$1行で「商品名 数量@価格」。目印の無い「数字@数字」は必ず 数量@価格（例：100@17000）。【カートン】が先頭に付く行はカートン単位。$q$,
    extraction_example_text = $q$弊社とのグループLINEが作成済の方はグループまでご連絡いただけますと幸いです🙇‍♂️

30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー 100@17000

30th CELEBRATION FUTURISTIC BOX 20@48000
$q$
WHERE supplier_code = 'SP-00217' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00220 吉田翔 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}box/packs$q$,
    extraction_order_pattern = $q$["quantity","unit","/","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（（未サーチ））$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「数量単位/価格円」（数量が先。竹内スタッフとは逆）。$q$,
    extraction_example_text = $q$op-17
100box/13,000円

【共通事項】
・適格事業者$q$
WHERE supplier_code = 'SP-00220' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00222 つきじ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$セット$q$,
    extraction_state_format = $q$商品名に付記（被り有り）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$☑️商品名 →「価格円　在庫N」。$q$,
    extraction_example_text = $q$☑️AR 100枚セット 被り有り
27,000円　在庫5

☑️AR PSA10 5枚セット(ランダム）
33,000円 在庫1$q$
WHERE supplier_code = 'SP-00222' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00223 むらお (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["unit","space","price","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリ無し）$q$,
    extraction_ship_format = $q$冒頭「9/28出荷のご案内」$q$,
    extraction_notes = $q$商品名[型番] →「[単位 ]価格 在庫N」。「18000 在庫15〆」は完売。$q$,
    extraction_example_text = $q$プレミアムデッキセット エーフィ・ブラッキー
18000 在庫15〆
$q$
WHERE supplier_code = 'SP-00223' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00224 ガク (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@ {数値}$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンクなし）$q$,
    extraction_ship_format = $q$「本日16時迄のご注文は当日発送」$q$,
    extraction_notes = $q$1行で「◆商品名 状態　数量BOX @ 価格」。$q$,
    extraction_example_text = $q$20BOX以上送料無料です。

◆30th CELEBRATION シュリンクなし　43BOX @ 23,200

◆30thプレミアムデッキセット　14BOX@17,900
$q$
WHERE supplier_code = 'SP-00224' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00226 貴大 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}枚$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$枚$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$区分 → 商品名 →「数量枚@価格」（PSA）。$q$,
    extraction_example_text = $q$メガディアンシーMA
50枚@4500
メガユキメノコMA
20枚@4500
メガズルズキンMA$q$
WHERE supplier_code = 'SP-00226' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00227 たくぞ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$¥{数値}/1box$q$,
    extraction_qty_format = $q${数値}（次の行、数字のみ）$q$,
    extraction_order_pattern = $q$["yen_prefix","price","/","1","unit","newline","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク付き）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 → 状態 →「¥価格/1box」→「数量（数字だけの行）」。「/1box」は単位あたりの価格。$q$,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00227' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00228 小菅圭輔 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$Y{数値}/単価 または {数値}円/単価$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","/","単価","newline","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（ダメージあり）$q$,
    extraction_ship_format = $q$見出し「9/17発送分」$q$,
    extraction_notes = $q$商品名 →「価格/単価」→「在庫N」（縦）。Y は ¥。$q$,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00228' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00229 加地-スタッフアカウント (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["price","yen","/","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$【区分】→ 商品名 →「価格円/数量BOX」。$q$,
    extraction_example_text = $q$30th CELEBRATION FUTURISTIC BOX
50,000円/10BOX

＊基本九州から発送。それ以外の場合は案内します。
＊30BOX以上で送料無料にて発送(30BOX未満は一律1,000円)$q$
WHERE supplier_code = 'SP-00229' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00230 ヒロト (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}box$q$,
    extraction_order_pattern = $q$["quantity","unit","space","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（箱潰れあり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →［状態］→「数量box 価格円」。$q$,
    extraction_example_text = $q$30th CELEBRATION BOX
100box 28000円
 40boxシュリなし26500円

MEGA 30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー$q$
WHERE supplier_code = 'SP-00230' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00231 りょう (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["quantity","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$1行で「商品名 数量@価格」。目印の無い「数字@数字」は必ず 数量@価格（例：100@11300）。【カートン】が先頭に付く行はカートン単位。$q$,
    extraction_example_text = $q$弊社とのグループLINEが作成済の方はグループまでご連絡いただけますと幸いです🙇‍♂️

ストームエメラルダ 100@11300
ブラックボルト 50@20800
ホワイトフレア 100@19800
ロケット団の栄光 50@20800$q$
WHERE supplier_code = 'SP-00231' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00233 Yuki (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$数量{数値}$q$,
    extraction_order_pattern = $q$["@","price","yen","space","数量","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（(シュリンクなし)）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「@価格円　数量N」。「18,800円@ 数量20」のように＠が価格の後ろに付く行もある。$q$,
    extraction_example_text = $q$ジャンプ33号　限定付録　肉ルフィ

@1,500円　数量50(雑誌付き)

ストームエメラルダ
$q$
WHERE supplier_code = 'SP-00233' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00234 RAITO (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円 / ¥{数値}$q$,
    extraction_qty_format = $q$在庫{数値} / 残り{数値}$q$,
    extraction_order_pattern = $q$["price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク付き 状態A-、デッキ状態B）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$⭐️商品名 → 状態 →「価格円 在庫N」。「ボックス/¥価格」→「残りN」の形もある。$q$,
    extraction_example_text = $q$シュリンク付き
29,000円 在庫100
シュリンク付き 状態A-
28,000円 在庫80
$q$
WHERE supplier_code = 'SP-00234' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00237 ぱ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["price","×","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$冒頭「当日18:00までのご注文で当日国内発送」$q$,
    extraction_notes = $q$商品名 →「価格×数量BOX」。$q$,
    extraction_example_text = $q$30th CELEBRATION FUTURISTIC BOX
68,000×2BOX

シャイニートレジャーex
15,500×1BOX$q$
WHERE supplier_code = 'SP-00237' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00238 たいき (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫数{数値}カートン/BOX/セット/枚$q$,
    extraction_order_pattern = $q$["@","price","yen","/","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（※未開封）$q$,
    extraction_ship_format = $q$🔴予約商品 ※発送日要相談$q$,
    extraction_notes = $q$● 商品名【型番】→「@価格円/在庫数N単位」（カートンと BOX の行が続く）。$q$,
    extraction_example_text = $q$● ヴァイス ブースターパック anemoi
@43,000円/在庫数10カートン

🔴在庫商品
$q$
WHERE supplier_code = 'SP-00238' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00239 まー (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["price","@","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（サーチ済、未サーチ）$q$,
    extraction_ship_format = $q$「12時までの注文で当日配送」$q$,
    extraction_notes = $q$✅商品名 →「価格@数量」。目印の無い「数字@数字」は必ず 価格@数量（例：400＠518 は単価400・数量518）。$q$,
    extraction_example_text = $q$✅30th セレブレーション
26000@40
✅ポケモンババ抜き&カルタ
2100@36
$q$
WHERE supplier_code = 'SP-00239' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00241 Ryum. (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["@","price","yen","/","stock_label","quantity"]$q$,
    extraction_default_unit = $q$枚$q$,
    extraction_state_format = $q$商品名に付記（重複アリ）$q$,
    extraction_ship_format = $q$「14時までのご注文で当日出荷」$q$,
    extraction_notes = $q$★商品名 →「@価格円/在庫N」。$q$,
    extraction_example_text = $q$★CHR PSA10 ランダム(重複アリ)※相談可

@4,300円/在庫50

★ MA PSA10 ランダム (重複アリ)
$q$
WHERE supplier_code = 'SP-00241' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00248 竹内 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}万（万円単位）$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","万","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$カートン$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格万　在庫N」（例：24万＝240,000円）。$q$,
    extraction_example_text = $q$遊戯王 ORIGINAL ARTWORK COLLECTION  カートン
24万　在庫20

⚫国内送料 1梱包1000円
100box以上で無料$q$
WHERE supplier_code = 'SP-00248' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00249 keny (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$x{数値}セット$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen","x","quantity","unit"]$q$,
    extraction_default_unit = $q$セット$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$予約（入荷次第発送）$q$,
    extraction_notes = $q$商品名 → 内容 →「34枚1セット@29000円 x2000セット」（1セットあたりの価格 x 販売セット数）。$q$,
    extraction_example_text = $q$ルフィP-099 ナイキニカプロモx4枚

ドン!!カード3種x各10枚

(計34枚セット)
$q$
WHERE supplier_code = 'SP-00249' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00250 YORO（株）スタッフ2 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/セット/枚$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「14時までのご注文で当日出荷」$q$,
    extraction_notes = $q$▪️商品名 →「数量単位@価格円」。$q$,
    extraction_example_text = $q$▪️ストームエメラルダ
50BOX@10,800円

▪️アビスアイ
35BOX@8,500円$q$
WHERE supplier_code = 'SP-00250' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00251 佐藤 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}個$q$,
    extraction_order_pattern = $q$["quantity","unit","space","price","yen"]$q$,
    extraction_default_unit = $q$個$q$,
    extraction_state_format = $q$次の行（美品/難あり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$【商品名】→ 状態 →「数量個 価格円」。$q$,
    extraction_example_text = $q$美品

1個 1,100円

【スノーハザード＆クレイバースト ポケモンセンタージムセット】
$q$
WHERE supplier_code = 'SP-00251' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00252 takuya (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/カートン/パック$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$数量の前（シュリンク付き 13BOX @…）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「[状態 ]数量単位 @価格円」。@ が抜けた行（1BOX 10,000円）もある。$q$,
    extraction_example_text = $q$30th CELEBRATION
シュリンク付き 13BOX @25,000円
シュリンク無し 13BOX @23,500円

30th CELEBRATION FUTURISTIC BOX$q$
WHERE supplier_code = 'SP-00252' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00261 旭野 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$¥{数値}$q$,
    extraction_qty_format = $q$残{数値}$q$,
    extraction_order_pattern = $q$["yen_prefix","price","space","残","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「9/30 仙台より発送」$q$,
    extraction_notes = $q$商品名 →「¥価格 残N」。$q$,
    extraction_example_text = $q$ストームエメラルダ
¥10,400 残42

・インボイス対応事業者です
・9/30 仙台より発送 $q$
WHERE supplier_code = 'SP-00261' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00262 河合潤也 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["status","price","yen","×","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$価格の前（シュリンク有り25500円×100）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$🔲商品名 →「状態価格円×数量」。$q$,
    extraction_example_text = $q$🔲 30th  CELEBRATION BOX 
シュリンク有り25500円×100

-----------------------------------
・買取品$q$
WHERE supplier_code = 'SP-00262' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00263 のりゆき (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["1","unit","space","price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$セット$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「1セット　価格円 在庫N」（1セットは単位あたり）。$q$,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00263' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00265 齊藤大輔 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q$×{数値}箱/パック$q$,
    extraction_order_pattern = $q$["×","quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$箱$q$,
    extraction_state_format = $q$商品名に付記（シュリンク無し、箱潰れ）$q$,
    extraction_ship_format = $q$冒頭「明日15日発送」$q$,
    extraction_notes = $q$1行で「・商品名[ 状態]×数量箱@価格」。$q$,
    extraction_example_text = $q$明日15日発送になります。

・ストームエメラルダ シュリンク無し×31箱@9300
・アビスアイ×35箱@7900
・アビスアイ シュリンク無し×11箱@7000
・インフェルノX×25箱@17000$q$
WHERE supplier_code = 'SP-00265' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00270 三海 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q$数量{数値}（枚）$q$,
    extraction_order_pattern = $q$["@","price","space","数量","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$1行で「・商品名 @価格 数量N」。「最低保証@4,300 被りなし37枚 @4,300」のように価格が2回出る。$q$,
    extraction_example_text = $q$●在庫
・30th CELEBRATION FUTURISTIC BOX @67,000 数量2

・PSA10 AR 最低保証@4,300 被りなし37枚 @4,300
$q$
WHERE supplier_code = 'SP-00270' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00271 yuyaさいとう (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","：","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「16日（発売日発送）」$q$,
    extraction_notes = $q$『商品名』→ 発送日 →「数量BOX：価格」。$q$,
    extraction_example_text = $q$16日（発売日発送）
40BOX：23,000

・適格請求書発行事業者です。
・弊社買取品$q$
WHERE supplier_code = 'SP-00271' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00272 Ryu (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンクあり/なし）$q$,
    extraction_ship_format = $q$「当日15:00までのご注文・お支払い確認で当日発送」$q$,
    extraction_notes = $q$■商品名（型番）→ 状態 →「数量BOX@価格円」。「■商品名 価格円」「価格変更いたしました」は価格の案内、「SOLD」は完売。$q$,
    extraction_example_text = $q$シュリンクあり

2BOX@28,000円

シュリンクなし
$q$
WHERE supplier_code = 'SP-00272' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00273 鈴木 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}ケース/カートン$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$カートン$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$行頭「・9/16発送」$q$,
    extraction_notes = $q$■商品名 →「・発送日　@価格円　在庫Nケース」。$q$,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00273' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00274 屋比久大 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@ {数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["unit","space","@","price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$■ 商品名 →「[単位 ]@ 価格円 在庫N」。$q$,
    extraction_example_text = $q$■ 30th  CELEBRATION BOX
BOX @ 28,400円 在庫8

■ 30th  CELEBRATION FUTURISTIC 
@ 78,000円 在庫1$q$
WHERE supplier_code = 'SP-00274' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00277 Mie (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX（残り{数値}BOX）$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンクなし）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「残りN BOX@価格円」または「N BOX@価格円」。$q$,
    extraction_example_text = $q$30th CELEBRATION シュリンクなし

残り11BOX@15500円

30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー
$q$
WHERE supplier_code = 'SP-00277' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00278 kaishi (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}BOX$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク有り）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「@価格円　在庫NBOX」。「残り2箱」「残り6です！」は直前の商品の残数。$q$,
    extraction_example_text = $q$ストームエメラルダ
@11,400円　在庫36BOX

30th CELEBRATION BOX 
シュリンク有り$q$
WHERE supplier_code = 'SP-00278' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00286 やまざきけんと (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","yen","space","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク付き/シュリ無し）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 → 状態 →「価格円　在庫N」。「残り14」は直前の商品の残数。$q$,
    extraction_example_text = $q$シュリンク付き
28000円　在庫32

シュリンクなし
26500円　在庫５$q$
WHERE supplier_code = 'SP-00286' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00287 Nexus (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX/SET$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（(シュリンクあり)）$q$,
    extraction_ship_format = $q$冒頭「以下本日発送のご提案」$q$,
    extraction_notes = $q$商品名(状態) →「数量BOX@価格円」。$q$,
    extraction_example_text = $q$30th CELEBRATION BOX(シュリンクあり)
15BOX@25,500円

30th CELEBRATION プレミアムデッキセット　エーフィ・ブラッキー
4BOX@18,000円$q$
WHERE supplier_code = 'SP-00287' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00290 Ren (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen","status"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$行末（（シュリンク有り））$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$▫︎種別「商品名」（型番）→「数量BOX@価格円（状態）」。パックは「数量：お問い合わせください」→「1PACK@130円」で数量なし。$q$,
    extraction_example_text = $q$▫︎拡張パック「フュージョンアーツ」（S8）
8BOX@50,000円（シュリンク有り）

▫︎拡張パック「蒼空ストリーム」（S7R）
4BOX@233,000円（シュリンク有り）$q$
WHERE supplier_code = 'SP-00290' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00292 Fukiko♡ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}パック$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$パック$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「16時までのご注文で当日発送」$q$,
    extraction_notes = $q$■商品名 →「@価格円　在庫N単位」。$q$,
    extraction_example_text = $q$■最強ジャンプ 2026年5月号 応募者全員大サービス 頂上の強者パック
@2800円　在庫500パック

◇適格請求書発行業者
◇国内送料/着払い$q$
WHERE supplier_code = 'SP-00292' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00294 Takahiro.Y (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円 / 単価：{数値}円$q$,
    extraction_qty_format = $q${数値}box / 数量：{数値}パック$q$,
    extraction_order_pattern = $q$["price","yen","space","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンク無）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格円 数量box」。ラベル形式（数量：…／単価：…）も混ざる。$q$,
    extraction_example_text = $q$ムニキスゼロ シュリンク無 
7200円 6box

【ワンピース】
$q$
WHERE supplier_code = 'SP-00294' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00295 村上 宝聡 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}個 1セット$q$,
    extraction_order_pattern = $q$["quantity","unit","space","1","セット","space","price","yen"]$q$,
    extraction_default_unit = $q$セット$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$行末(10月入荷次第発送)$q$,
    extraction_notes = $q$「30個 1セット 510,000円(1個辺り17,000円)」＝30個入りセットの価格。$q$,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-00295' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00300 Taisei (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円付きもある）$q$,
    extraction_qty_format = $q${数値}box$q$,
    extraction_order_pattern = $q$["quantity","unit","space","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「14時まで注文で当日出荷対応可能」$q$,
    extraction_notes = $q$商品名 →「数量box 価格」。一覧の中の「〆切」は完売。$q$,
    extraction_example_text = $q$アビスアイ
28box 8,300円

ムニキスゼロ
1box 8,400$q$
WHERE supplier_code = 'SP-00300' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00303 かおり (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}$q$,
    extraction_qty_format = $q${数値}セット/枚$q$,
    extraction_order_pattern = $q$["quantity","unit","space","@","price"]$q$,
    extraction_default_unit = $q$枚$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$▪️商品名 →「数量単位　@価格」。$q$,
    extraction_example_text = $q$▪️AR CHR 100枚 セットスリーブ入り
5セット @27,500

▪️PSA10 AR
67枚　@4,300$q$
WHERE supplier_code = 'SP-00303' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00307 Hironobu Yasukawa (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}BOX$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンク有）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$■商品名 状態 →「@価格円　在庫NBOX」。「残り6Box」は直前の商品の残数。$q$,
    extraction_example_text = $q$■30th CELEBRATION FUTURISTIC BOX
@70,000円　在庫1BOX

■MEGAドリーム シュリンク有
@12,700円　在庫3BOX$q$
WHERE supplier_code = 'SP-00307' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00308 小菅圭輔 こすがけいすけ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円/単価$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","yen","/","単価","newline","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（ダメージあり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格円/単価」→「在庫N」（縦）。SP-00228 と同じ会社（Al.japan）。$q$,
    extraction_example_text = $q$30th celebration プレミアムデッキセット エーフィ・ブラッキー
18,500円/単価
在庫36
ダメージあり
16,000円/単価$q$
WHERE supplier_code = 'SP-00308' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00316 鈴木 章裕 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}カートン$q$,
    extraction_order_pattern = $q$["@","price","yen","space","stock_label","quantity","unit"]$q$,
    extraction_default_unit = $q$カートン$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$「15:00までのご注文で本日国内発送可能」$q$,
    extraction_notes = $q$■商品名 →「・@価格円　在庫Nカートン」。SP-00273 と同じ会社（Playfirst）。$q$,
    extraction_example_text = $q$■30th CELEBRATION 
・@320,000円　在庫3カートン

-----------------------------
・適格請求書発行事業者$q$
WHERE supplier_code = 'SP-00316' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00317 Mie (*´ω`*) (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX（残り{数値}BOX）$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$商品名に付記（シュリンクなし）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「残りN BOX@価格円」または「N BOX@価格円」。SP-00277 と同じ投稿。$q$,
    extraction_example_text = $q$30th CELEBRATION シュリンクなし
残り11BOX@15500円

30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー
12 BOX@16300円$q$
WHERE supplier_code = 'SP-00317' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25954 Yuki Sato (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q${数値}BOX$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（(シュリンクあり)）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →（状態）→「数量BOX@価格円」。$q$,
    extraction_example_text = $q$(シュリンクあり)
40BOX@25,800円

ストームエメラルダ
(シュリンクあり)$q$
WHERE supplier_code = 'SP-25954' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25955 Ryum. a (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$@{数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["@","price","yen","/","stock_label","quantity"]$q$,
    extraction_default_unit = $q$枚$q$,
    extraction_state_format = $q$商品名に付記（重複アリ、シュリ付き）$q$,
    extraction_ship_format = $q$「15時までのご注文で当日出荷可能」$q$,
    extraction_notes = $q$★商品名 →「@価格[円]/在庫N」。「②重複OK@220円/在庫3,000」のように番号付きの子項目もある。$q$,
    extraction_example_text = $q$①🚀被り無し100枚100種🚀
@24,000/在庫 25

②重複OK@220円/在庫3,000
$q$
WHERE supplier_code = 'SP-25955' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25956 佐藤 亮 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q${数値}個$q$,
    extraction_order_pattern = $q$["quantity","unit","space","price","yen"]$q$,
    extraction_default_unit = $q$個$q$,
    extraction_state_format = $q$次の行（美品/難あり）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$【商品名】→ 状態 →「数量個 価格円」。SP-00251 と同じ会社（オーバーラップ）。$q$,
    extraction_example_text = $q$美品
1個 1,100円

【スノーハザード＆クレイバースト ポケモンセンタージムセット】
美品$q$
WHERE supplier_code = 'SP-25956' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25957 一場誠 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q$＠{数値}（円付きもある）$q$,
    extraction_qty_format = $q${数値}BOX/パック/冊/個$q$,
    extraction_order_pattern = $q$["quantity","unit","@","price"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = $q$行末(発送日要相談)$q$,
    extraction_notes = $q$≪予約商品≫/≪在庫商品≫ → 商品名 →「数量単位＠価格」。$q$,
    extraction_example_text = $q$ONE PIECE magazine Vol.21（ワンピースマガジン ヒロインズ 021）
300冊@3,500円(発売後3日以内出荷)

ユニオンアリーナ魔法少女まどか☆マギカ MAGIA EXEDRA【EX16BT】
4BOX@7,200 (発送日要相談)$q$
WHERE supplier_code = 'SP-25957' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25971 Y Mitamura (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（区切り無し）$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = $q$次の行（シュリンク付き）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 → 状態 →「価格在庫N」（例：27,500在庫50）。$q$,
    extraction_example_text = $q$シュリンク付き

27,500在庫50

適格請求書発行事業者
$q$
WHERE supplier_code = 'SP-25971' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26012 東 智志 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q${数値}（単位なし）$q$,
    extraction_order_pattern = $q$["price","@","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$1行で「商品名 価格@数量」。目印の無い「数字@数字」は必ず 価格@数量（例：79,000@2）。$q$,
    extraction_example_text = $q$商品のご案内です。

30th CELEBRATION FUTURISTIC BOX 79,000@2
30th CELEBRATION プレミアムデッキセット：エーフィ＆ブラッキー 19,000@1
ナイトワンダラー 12,000@1
ステラミラクル 12,000@1$q$
WHERE supplier_code = 'SP-26012' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26015 伊藤裕輝 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$（数量の記載なし。1点もの）$q$,
    extraction_order_pattern = $q$["price","yen"]$q$,
    extraction_default_unit = $q$セット$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$数量が書かれないことがある。定型文は SP-00190 シンソクと同じ。$q$,
    extraction_example_text = NULL
WHERE supplier_code = 'SP-26015' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26016 つかさ (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}円$q$,
    extraction_qty_format = $q$在庫{数値}$q$,
    extraction_order_pattern = $q$["price","yen","newline","stock_label","quantity"]$q$,
    extraction_default_unit = $q$BOX$q$,
    extraction_state_format = NULL,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格円」→「在庫N」（縦3行）。$q$,
    extraction_example_text = $q$30th CELEBRATION
26500円
在庫13

◯買取、店舗、スニダン、グループ仕入れ$q$
WHERE supplier_code = 'SP-26016' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26021 al.japan 株式会社 (new)
UPDATE public.suppliers SET
    extraction_price_format = $q${数値}（円なし）$q$,
    extraction_qty_format = $q$@{数値}$q$,
    extraction_order_pattern = $q$["price","space","@","quantity"]$q$,
    extraction_default_unit = $q$枚$q$,
    extraction_state_format = $q$商品名に付記（PSA10）$q$,
    extraction_ship_format = NULL,
    extraction_notes = $q$商品名 →「価格 @数量」（＠の後ろが数量。例：4500000 @1）。$q$,
    extraction_example_text = $q$シャンクス(CS25-26/illust:Shishizaru)【SR】{OP09-004}PSA10

4500000 @1

・自社鑑定品です。
$q$
WHERE supplier_code = 'SP-26021' AND tenant_id IS NULL AND extraction_price_format IS NULL AND extraction_qty_format IS NULL AND extraction_order_pattern IS NULL AND extraction_state_format IS NULL AND extraction_ship_format IS NULL AND extraction_notes IS NULL AND extraction_example_text IS NULL;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00023 株式会社N&U (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["price","@","quantity"]$q$,
    extraction_notes = extraction_notes || E'\n' || $q$目印の無い「数字@数字」は必ず 価格@数量。$q$
WHERE supplier_code = 'SP-00023' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$price_at_qty$q$ AND extraction_notes IS NOT DISTINCT FROM $q$価格@数量 の形式（SIGと逆）。例: 12000@20。シュリなし等の注記が商品名に付く$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00157 斉藤 (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$,
    extraction_notes = extraction_notes || E'\n' || $q$「パック@価格円」は数量なし（パック単価）。一覧の中の「完売」は完売。$q$
WHERE supplier_code = 'SP-00157' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$qty_unit_at_price$q$ AND extraction_notes IS NOT DISTINCT FROM $q$円は通貨記号であり単位ではない。単位はBOX/枚/パック。例: 30BOX@27,300円$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00178 達也 (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["■単価（税込）：","yen_prefix","price","newline","■在庫数：","quantity"]$q$
WHERE supplier_code = 'SP-00178' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$labeled_lines$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00189 funスタッフ (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["quantity","unit","@","price","yen"]$q$
WHERE supplier_code = 'SP-00189' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$qty_unit_at_price$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-00194 Gスタッフ (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["price","yen","space","stock_label","quantity"]$q$
WHERE supplier_code = 'SP-00194' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$price_stock_qty$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-25952 SIG 原屋敷 (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["quantity","@","price"]$q$,
    extraction_notes = extraction_notes || E'\n' || $q$目印の無い「数字@数字」は必ず 数量@価格。$q$
WHERE supplier_code = 'SP-25952' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$qty_at_price$q$ AND extraction_notes IS NOT DISTINCT FROM $q$商品名 数量@価格 の形式。例: ストームエメラルダ 200@11500$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;
-- SP-26017 GALLERY営業部 (convert)
UPDATE public.suppliers SET
    extraction_order_pattern = $q$["@","price","yen","/","stock_label","quantity"]$q$
WHERE supplier_code = 'SP-26017' AND tenant_id IS NULL AND extraction_order_pattern IS NOT DISTINCT FROM $q$at_price_slash_stock$q$;
GET DIAGNOSTICS c = ROW_COUNT;
IF c != 1 THEN RAISE EXCEPTION 'UPDATE row_count=% (expected 1)', c; END IF;
n := n + c;

-- unit_aliases (public.unit_aliases は line_unit_aliases の view。基表へ INSERT)
INSERT INTO public.line_unit_aliases (unit_id, alias_text, lang)
SELECT id, $q$packs$q$, 'ja' FROM public.line_units WHERE canonical = $q$Pack$q$
  AND NOT EXISTS (SELECT 1 FROM public.line_unit_aliases x WHERE x.alias_text = $q$packs$q$ AND x.lang = 'ja');
GET DIAGNOSTICS c = ROW_COUNT; a := a + c;
INSERT INTO public.line_unit_aliases (unit_id, alias_text, lang)
SELECT id, $q$ctn$q$, 'ja' FROM public.line_units WHERE canonical = $q$Case$q$
  AND NOT EXISTS (SELECT 1 FROM public.line_unit_aliases x WHERE x.alias_text = $q$ctn$q$ AND x.lang = 'ja');
GET DIAGNOSTICS c = ROW_COUNT; a := a + c;

IF n != expected_updates THEN RAISE EXCEPTION 'suppliers updated=% expected=%', n, expected_updates; END IF;
IF a != expected_aliases THEN RAISE EXCEPTION 'unit_aliases inserted=% expected=%', a, expected_aliases; END IF;
END
$do$;
ROLLBACK;
