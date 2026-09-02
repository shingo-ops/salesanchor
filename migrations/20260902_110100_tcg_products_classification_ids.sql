-- Migration: 20260902_110100_tcg_products_classification_ids
-- 目的: tcg_products の UUID 4 列に FK 制約を追加し、GAS 実データで全 268 行を埋める
--
-- 前提: 20260902_110000_tcg_classification_masters.sql が適用済みであること
-- 冪等性:
--   - ADD CONSTRAINT IF NOT EXISTS で重複 FK 追加を防ぐ
--   - UPDATE は同じ値への更新になっても副作用なし

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260902_110100: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- 1. tcg_products 4 UUID 列に FK 制約を追加（IF NOT EXISTS）
    -- ----------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_division_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_division_id
                    FOREIGN KEY (division_id)
                    REFERENCES %I.tcg_major_categories (id)
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_work_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_work_id
                    FOREIGN KEY (work_id)
                    REFERENCES %I.tcg_series (id)
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_manufacturer_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_manufacturer_id
                    FOREIGN KEY (manufacturer_id)
                    REFERENCES %I.tcg_manufacturers (id)
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = format('%I.tcg_products', _schema)::regclass
          AND conname = 'fk_tcg_products_product_category_id'
    ) THEN
        EXECUTE format($q$
            ALTER TABLE %I.tcg_products
                ADD CONSTRAINT fk_tcg_products_product_category_id
                    FOREIGN KEY (product_category_id)
                    REFERENCES %I.tcg_product_categories (id)
        $q$, _schema, _schema);
    END IF;

    -- ----------------------------------------------------------------
    -- 2. 全 268 商品の分類 ID を GAS 実データで埋める
    --    (GAS 実測: 2026-09-02 clasp run dumpSheetAsText で確認)
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        UPDATE %I.tcg_products AS p
        SET
            division_id         = mc.id,
            work_id             = s.id,
            manufacturer_id     = mf.id,
            product_category_id = pc.id
        FROM (VALUES
        ('PM0001', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0002', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0003', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0004', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0005', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0006', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0007', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0008', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0009', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0010', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0011', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0012', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0013', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0014', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0015', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0016', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0017', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0018', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0019', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0020', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0021', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0022', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0023', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0024', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0025', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0026', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0027', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0028', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0029', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0030', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0031', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0032', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0033', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0034', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0035', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0036', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0037', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0038', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0039', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0040', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0041', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0042', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0043', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0044', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0045', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0046', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0047', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0048', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0049', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0050', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0051', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0052', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0053', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0054', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0055', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0056', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0057', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0058', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0059', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0060', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0061', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0062', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0063', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0064', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0065', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0066', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0067', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0068', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0069', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0070', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0071', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0072', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0073', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0074', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0075', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0076', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0077', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0078', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0079', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0080', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0081', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0082', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0083', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0084', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0085', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0086', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0087', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0088', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0089', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0090', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0091', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0092', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0093', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0094', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0095', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0096', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0097', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0098', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0099', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0100', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0101', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0102', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0103', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0104', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0105', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0106', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0107', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0108', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0109', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0110', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0111', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0112', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0113', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0114', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0115', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0116', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0117', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0118', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0119', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0120', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0121', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0122', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0123', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0124', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0125', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0126', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0127', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0128', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0129', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0130', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0131', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0132', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0133', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0134', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0135', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0136', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0137', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0138', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0139', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0140', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0141', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0142', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0143', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0144', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0145', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0146', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0147', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0148', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0149', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0150', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0151', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0152', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0153', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0154', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0155', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0156', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0157', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0158', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0159', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0160', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0161', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0162', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0163', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0164', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0165', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0166', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0167', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0168', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0169', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0170', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0171', 'DIV01', 'IP006', 'MK002', 'PC_BOX'),
        ('PM0172', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0173', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0174', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0175', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0176', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0177', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0178', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0179', 'DIV01', 'IP002', 'MK002', 'PC_SINGLE'),
        ('PM0180', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0181', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0182', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0183', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0184', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0185', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0186', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0187', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0188', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0189', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0190', 'DIV01', 'IP002', 'MK002', 'PC_SINGLE'),
        ('PM0191', 'DIV01', 'IP002', 'MK002', 'PC_SINGLE'),
        ('PM0192', 'DIV01', 'IP006', 'MK002', 'PC_BOX'),
        ('PM0193', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0194', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0195', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0196', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0197', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0198', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0199', 'DIV01', 'IP002', 'MK002', 'PC_SINGLE'),
        ('PM0200', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0201', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0202', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0203', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0204', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0205', 'DIV01', 'IP006', 'MK002', 'PC_BOX'),
        ('PM0206', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0207', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0208', 'DIV01', 'IP005', 'MK004', 'PC_BOX'),
        ('PM0209', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0210', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0211', 'DIV01', 'IP005', 'MK004', 'PC_BOX'),
        ('PM0212', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0213', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0214', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0215', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0216', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0217', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0218', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0219', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0220', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0221', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0222', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0223', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0224', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0225', 'DIV01', 'IP005', 'MK004', 'PC_BOX'),
        ('PM0226', 'DIV01', 'IP003', 'MK002', 'PC_BOX'),
        ('PM0227', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0228', 'DIV01', 'IP007', 'MK004', 'PC_BOX'),
        ('PM0229', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0230', 'DIV01', 'IP007', 'MK004', 'PC_SINGLE'),
        ('PM0231', 'DIV01', 'IP001', 'MK001', 'PC_SINGLE'),
        ('PM0232', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0233', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0234', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0235', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0236', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0237', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0238', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0239', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0240', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0241', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0242', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0243', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0244', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0245', 'DIV01', 'IP010', 'MK003', 'PC_BOX'),
        ('PM0246', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0247', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0248', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0249', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0250', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0251', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0252', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0253', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0254', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0255', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0256', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0257', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0258', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0259', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0260', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0261', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0262', 'DIV01', 'IP004', 'MK005', 'PC_BOX'),
        ('PM0263', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0264', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0265', 'DIV01', 'IP001', 'MK001', 'PC_BOX'),
        ('PM0266', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0267', 'DIV01', 'IP002', 'MK002', 'PC_BOX'),
        ('PM0268', 'DIV01', 'IP002', 'MK002', 'PC_SINGLE')
        ) AS m(product_code, div_code, series_code, mfr_code, pc_code)
        JOIN %I.tcg_major_categories    mc ON mc.code = m.div_code
        JOIN %I.tcg_series              s  ON s.code  = m.series_code
        JOIN %I.tcg_manufacturers       mf ON mf.code = m.mfr_code
        JOIN %I.tcg_product_categories  pc ON pc.code = m.pc_code
        WHERE p.code = m.product_code
    $q$, _schema, _schema, _schema, _schema, _schema);

    -- ----------------------------------------------------------------
    -- 3. 検証: 全 268 行が埋まっていることを確認
    -- ----------------------------------------------------------------
    DECLARE
        _null_count INTEGER;
    BEGIN
        EXECUTE format($q$
            SELECT COUNT(*)
            FROM %I.tcg_products
            WHERE division_id IS NULL
               OR work_id IS NULL
               OR manufacturer_id IS NULL
               OR product_category_id IS NULL
        $q$, _schema) INTO _null_count;

        IF _null_count > 0 THEN
            RAISE EXCEPTION '20260902_110100: % rows have NULL classification IDs after update', _null_count;
        END IF;
    END;

    RAISE NOTICE '20260902_110100: FK constraints added and 268 products classified in schema %', _schema;
END $$;
