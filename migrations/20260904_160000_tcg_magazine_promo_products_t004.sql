-- ONE PIECE magazine 付録プロモ 5商品の整備（tenant_004 のみ）
-- 目的: Vol.21 の MULTI 11行と ST21-014 の NONE 1行を解決する
-- 承認: Shingo 2026-09-04
-- バックアップ: tenant_004.tcg_products_bak_20260904 (268)
--               tenant_004.product_search_keywords_bak_20260904 (593)
--               tenant_004.product_exclude_keywords_bak_20260904 (128)

DO $$
DECLARE
  v_div_tcg     uuid;
  v_work_op     uuid;
  v_mfr_bandai  uuid;
  v_cat_single  uuid;
  v_pm0190      uuid;
  v_pm0267      uuid;
  v_pm0269      uuid;
  v_pm0270      uuid;
  v_pm0271      uuid;
  v_count       integer;
BEGIN
  SELECT id INTO v_div_tcg    FROM tenant_004.tcg_major_categories  WHERE code = 'DIV01';
  SELECT id INTO v_work_op    FROM tenant_004.tcg_series             WHERE code = 'IP002';
  SELECT id INTO v_mfr_bandai FROM tenant_004.tcg_manufacturers      WHERE code = 'MK002';
  SELECT id INTO v_cat_single FROM tenant_004.tcg_product_categories WHERE code = 'PC_SINGLE';

  IF v_div_tcg IS NULL OR v_work_op IS NULL OR v_mfr_bandai IS NULL OR v_cat_single IS NULL THEN
    RAISE EXCEPTION '参照マスタが見つかりません';
  END IF;

  -- 1. PM0190 を Vol.20 として確定
  UPDATE tenant_004.tcg_products
     SET japanese_title = 'ONE PIECE magazine Vol.20 付録プロモ',
         english_title  = 'One Piece Magazine Vol.20',
         mark           = 'ST21-014',
         release_date   = DATE '2025-10-03'
   WHERE code = 'PM0190';

  -- 2. PM0267 のスタブを Vol.21 として埋める
  UPDATE tenant_004.tcg_products
     SET japanese_title      = 'ONE PIECE magazine Vol.21 特集ヒロインズ 021 付録プロモ',
         english_title       = 'One Piece Magazine Vol.21 Special Feature: Heroines',
         category_class      = 'Single',
         product_category_id = v_cat_single
   WHERE code = 'PM0267';

  -- 3. 新規3商品
  INSERT INTO tenant_004.tcg_products
    (code, japanese_title, english_title, mark, release_date, category_class,
     division_id, work_id, manufacturer_id, product_category_id, is_active)
  VALUES
    ('PM0269', 'ONE PIECE magazine Vol.16 付録プロモ', 'One Piece Magazine Vol.16',
     'P-028', DATE '2023-03-02', 'Single',
     v_div_tcg, v_work_op, v_mfr_bandai, v_cat_single, TRUE),
    ('PM0270', 'ONE PIECE magazine Vol.17 付録プロモ', 'One Piece Magazine Vol.17',
     'P-046', DATE '2023-09-04', 'Single',
     v_div_tcg, v_work_op, v_mfr_bandai, v_cat_single, TRUE),
    ('PM0271', 'ONE PIECE magazine 別冊 Focus on ONE PIECE FAN LETTER 付録プロモ', NULL,
     'P-096', DATE '2025-06-04', 'Single',
     v_div_tcg, v_work_op, v_mfr_bandai, v_cat_single, TRUE)
  ON CONFLICT (code) DO NOTHING;

  SELECT id INTO v_pm0190 FROM tenant_004.tcg_products WHERE code = 'PM0190';
  SELECT id INTO v_pm0267 FROM tenant_004.tcg_products WHERE code = 'PM0267';
  SELECT id INTO v_pm0269 FROM tenant_004.tcg_products WHERE code = 'PM0269';
  SELECT id INTO v_pm0270 FROM tenant_004.tcg_products WHERE code = 'PM0270';
  SELECT id INTO v_pm0271 FROM tenant_004.tcg_products WHERE code = 'PM0271';

  -- 4. 検索キーワードの追加（既存は消さない）
  INSERT INTO tenant_004.product_search_keywords (product_id, keyword, position)
  VALUES
    (v_pm0190, 'ST21-014',        4),
    (v_pm0269, 'P-028',           1),
    (v_pm0269, 'magazine Vol.16', 2),
    (v_pm0270, 'P-046',           1),
    (v_pm0270, 'magazine Vol.17', 2),
    (v_pm0271, 'P-096',           1),
    (v_pm0271, 'FAN LETTER',      2)
  ON CONFLICT (product_id, keyword) DO NOTHING;

  -- 5. 除外キーワードの追加（PM0190 が Vol.21 を拾わないようにする）
  INSERT INTO tenant_004.product_exclude_keywords (product_id, keyword)
  VALUES
    (v_pm0190, 'ヒロインズ')
  ON CONFLICT DO NOTHING;

  -- 6. 検証（担当範囲だけを数える）
  SELECT count(*) INTO v_count
    FROM tenant_004.tcg_products
   WHERE code BETWEEN 'PM0269' AND 'PM0271';
  IF v_count <> 3 THEN
    RAISE EXCEPTION '新規商品が3件になっていません: %', v_count;
  END IF;

  SELECT count(*) INTO v_count
    FROM tenant_004.tcg_products p
   WHERE p.code BETWEEN 'PM0269' AND 'PM0271'
     AND NOT EXISTS (
       SELECT 1 FROM tenant_004.product_search_keywords k WHERE k.product_id = p.id
     );
  IF v_count <> 0 THEN
    RAISE EXCEPTION '検索キーワードが空の新規商品があります: %', v_count;
  END IF;

  SELECT count(*) INTO v_count
    FROM tenant_004.tcg_products
   WHERE code IN ('PM0190', 'PM0267')
     AND japanese_title LIKE 'ONE PIECE magazine%';
  IF v_count <> 2 THEN
    RAISE EXCEPTION '既存2商品の更新が反映されていません: %', v_count;
  END IF;
END $$;
