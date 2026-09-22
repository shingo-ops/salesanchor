-- Migration: 20260905_150000_record_manual_supplier_fixes_t004
-- 目的: 2026-09-05 17:25〜17:45 に直接SQL で適用した仕入元マスタ変更4件を
--       migration として記録する（既に本番適用済み・再実行は冪等）
--
-- 変更内容:
--   (1) SP0007 name → '倉田 和博'（#3306/#3309 確認画面誤操作で上書きされた name の復旧）
--   (2) SP0184 name → 'overlap'  （同誤操作で上書きされた name の復旧）
--   (3) SP0203 '株式会社AXISグリーン' 新規登録 + LINE チャンネル行
--       （HTTP 422 で画面登録できなかったため直接 INSERT）
--   (4) SP0204 'Ryuta' 新規登録 + LINE チャンネル行（同上）
--
-- 冪等性:
--   UPDATE は "name <> '期待値'" 条件付き（既に正しければ 0 行変更）
--   INSERT は ON CONFLICT (code) DO NOTHING
--   supplier_channels は NOT EXISTS で重複挿入防止
--
-- 本番では既に適用済みのため、実行しても実質何も変更しない
--
-- 注意: import_jobs の DELETE（c32e7aa2-...）は一時データの削除であり
--       再現する意味がないため migration にしない（recon.md に事実として記録）

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
    r       RECORD;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260905_150000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    IF to_regclass(_schema || '.tcg_suppliers') IS NULL THEN
        RAISE NOTICE '20260905_150000: %s.tcg_suppliers does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- Table guard: supplier_channels was dropped by migration 20260921_050000
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = _schema AND table_name = 'supplier_channels'
    ) THEN
        RAISE NOTICE '20260905_150000: %.supplier_channels does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- =========================================================
    -- 1 & 2: SP0007/SP0184 name 復旧 UPDATE — DEPRECATED per ADR-155
    --   VALUES now managed via app UI. UPDATE removed to prevent overwrite.
    --   Original: SP0007 → '倉田 和博', SP0184 → 'overlap'
    -- =========================================================

    -- =========================================================
    -- 3. SP0203: '株式会社AXISグリーン' 新規登録 + LINE チャンネル
    --    画面の「新規登録」ボタンが HTTP 422 のため直接 INSERT した。
    -- =========================================================
    EXECUTE format($q$
        INSERT INTO %I.tcg_suppliers (code, name, is_active)
        VALUES ('SP0203', '株式会社AXISグリーン', TRUE)
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.supplier_channels (supplier_id, channel, external_id, is_active)
        SELECT s.id, 'line', NULL, TRUE
        FROM   %I.tcg_suppliers s
        WHERE  s.code = 'SP0203'
          AND  NOT EXISTS (
              SELECT 1 FROM %I.supplier_channels sc
              WHERE  sc.supplier_id = s.id
                AND  sc.channel     = 'line'
                AND  sc.external_id IS NULL
          )
    $q$, _schema, _schema, _schema);

    -- =========================================================
    -- 4. SP0204: 'Ryuta' 新規登録 + LINE チャンネル
    --    同上理由で直接 INSERT した。
    -- =========================================================
    EXECUTE format($q$
        INSERT INTO %I.tcg_suppliers (code, name, is_active)
        VALUES ('SP0204', 'Ryuta', TRUE)
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.supplier_channels (supplier_id, channel, external_id, is_active)
        SELECT s.id, 'line', NULL, TRUE
        FROM   %I.tcg_suppliers s
        WHERE  s.code = 'SP0204'
          AND  NOT EXISTS (
              SELECT 1 FROM %I.supplier_channels sc
              WHERE  sc.supplier_id = s.id
                AND  sc.channel     = 'line'
                AND  sc.external_id IS NULL
          )
    $q$, _schema, _schema, _schema);

    -- =========================================================
    -- 5. 検算: 4件の name と channel 数を RAISE NOTICE で出力
    --
    --    期待値（人手で目視確認）:
    --      SP0007 | 倉田 和博            | 1
    --      SP0184 | overlap              | 1
    --      SP0203 | 株式会社AXISグリーン | 1
    --      SP0204 | Ryuta                | 1
    -- =========================================================
    FOR r IN EXECUTE format($q$
        SELECT s.code, s.name, COUNT(sc.id) AS ch
        FROM        %I.tcg_suppliers     s
        LEFT JOIN   %I.supplier_channels sc ON sc.supplier_id = s.id
        WHERE  s.code IN ('SP0007', 'SP0184', 'SP0203', 'SP0204')
        GROUP  BY s.code, s.name
        ORDER  BY s.code
    $q$, _schema, _schema)
    LOOP
        RAISE NOTICE '20260905_150000 verify: % | % | ch=%', r.code, r.name, r.ch;
    END LOOP;

    RAISE NOTICE '20260905_150000: 完了（本番適用済み・冪等確認）';
END $$;
