-- NOTE-B2: value-carrying note labels and normalization rules (tenant_004)
-- Design: docs/handoff/tcg-product-master-growth/design-note-master.md B2-3 through B2-7
-- Idempotent: additive columns, deterministic updates, conflict-safe inserts
-- Validation counts only IDs owned by this migration.

DO $body$
DECLARE
    _schema   TEXT := 'tenant_004';
    _note_ids TEXT[] := ARRAY[
        'NJ030','NJ031','NJ032','NJ033','NJ034','NJ051','NJ052','NJ053',
        'NJ061','NJ062','NJ063','NJ064','NJ065','NJ066','NJ067','NJ068',
        'NJ069','NJ070','NJ072','NJ073','NJ074','NJ075','NJ076','NJ077',
        'NJ078'
    ];
    _rule_ids TEXT[] := ARRAY[
        'NR0137','NR0138','NR0139','NR0140','NR0141','NR0142','NR0143',
        'NR0144','NR0145','NR0146','NR0147','NR0148','NR0149'
    ];
    _note_count INTEGER;
    _rule_count INTEGER;
    _updated_count INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260909_130000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format(
        'ALTER TABLE %I.tcg_note_master ADD COLUMN IF NOT EXISTS match_type TEXT NOT NULL DEFAULT ''LITERAL''',
        _schema
    );
    EXECUTE format(
        'ALTER TABLE %I.tcg_note_master ADD COLUMN IF NOT EXISTS search_pattern TEXT',
        _schema
    );
    EXECUTE format(
        'ALTER TABLE %I.tcg_note_master ADD COLUMN IF NOT EXISTS label_template TEXT',
        _schema
    );

    EXECUTE format($q$
        UPDATE %I.tcg_normalization_rules
        SET from_val = '(\d{1,2}\/\d{1,2})[^\d\/前後]*発送'
        WHERE normalization_rule_id = 'NR0126'
    $q$, _schema);

    GET DIAGNOSTICS _updated_count = ROW_COUNT;
    IF _updated_count != 1 THEN
        RAISE EXCEPTION 'NOTE-B2 normalization update: expected 1 row, got %', _updated_count;
    END IF;

    EXECUTE format($q$
        INSERT INTO %I.tcg_normalization_rules
            (normalization_rule_id, field, rule_type, from_val, to_val, enabled, priority, note)
        VALUES
            ('NR0137','NOTE','REGEX_REPLACE','一(日前|日|個|枚|箱|時)','1$1',TRUE,1100,'NOTE-B2 kanji numeral'),
            ('NR0138','NOTE','REGEX_REPLACE','二(日前|日|個|枚|箱|時)','2$1',TRUE,1110,'NOTE-B2 kanji numeral'),
            ('NR0139','NOTE','REGEX_REPLACE','三(日前|日|個|枚|箱|時)','3$1',TRUE,1120,'NOTE-B2 kanji numeral'),
            ('NR0140','NOTE','REGEX_REPLACE','四(日前|日|個|枚|箱|時)','4$1',TRUE,1130,'NOTE-B2 kanji numeral'),
            ('NR0141','NOTE','REGEX_REPLACE','五(日前|日|個|枚|箱|時)','5$1',TRUE,1140,'NOTE-B2 kanji numeral'),
            ('NR0142','NOTE','REGEX_REPLACE','六(日前|日|個|枚|箱|時)','6$1',TRUE,1150,'NOTE-B2 kanji numeral'),
            ('NR0143','NOTE','REGEX_REPLACE','七(日前|日|個|枚|箱|時)','7$1',TRUE,1160,'NOTE-B2 kanji numeral'),
            ('NR0144','NOTE','REGEX_REPLACE','八(日前|日|個|枚|箱|時)','8$1',TRUE,1170,'NOTE-B2 kanji numeral'),
            ('NR0145','NOTE','REGEX_REPLACE','九(日前|日|個|枚|箱|時)','9$1',TRUE,1180,'NOTE-B2 kanji numeral'),
            ('NR0146','NOTE','REGEX_REPLACE','十(カートン|箱|個|枚)','10$1',TRUE,1190,'NOTE-B2 kanji numeral ten'),
            ('NR0147','NOTE','REGEX_REPLACE','[【】『』\[\]]','',TRUE,1200,'NOTE-B2 bracket removal'),
            ('NR0148','NOTE','REGEX_REPLACE','[ℹ⚠✅]','',TRUE,1210,'NOTE-B2 decoration removal'),
            ('NR0149','NOTE','REGEX_REPLACE','[①②③④⑤⑥⑦⑧⑨]','',TRUE,1220,'NOTE-B2 circled numeral removal')
        ON CONFLICT (normalization_rule_id) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords,
             category, priority, match_type, search_pattern, label_template)
        VALUES
            ('NJ031','日付範囲発送','Ships within date range',TRUE,'','完売','発送時期系',1,'REGEX','(\d{1,2})/(\d{1,2})[〜~ー-](\d{1,2})/(\d{1,2}).{0,4}(発送|出荷)','$1/$2〜$3/$4発送'),
            ('NJ051','日付前後発送','Ships around specified date',TRUE,'','完売','発送時期系',1,'REGEX','(\d{1,2})/(\d{1,2})前後(発送|入荷)','$1/$2前後発送'),
            ('NJ053','指定日までに発送','Ships by specified date',TRUE,'','完売','発送時期系',1,'REGEX','(\d{1,2})月(\d{1,2})日?までに(発送|出荷)','$1/$2までに発送'),
            ('NJ052','月内入荷','Arrives within specified month',TRUE,'','完売','発送時期系',1,'REGEX','(\d{1,2})月内(入荷|発送)','$1月内入荷'),
            ('NJ030','指定日発送','Ships on specified date',TRUE,'','完売,前後,までに,〜,~,ー,-','発送時期系',2,'REGEX','(\d{1,2})[/月](\d{1,2})日?.{0,4}?(発送|出荷)','$1/$2発送'),
            ('NJ032','発売日前発送','Ships before release day',TRUE,'','完売','発送時期系',2,'REGEX','発売日\s*(\d{1,2})日前','発売日$1日前発送'),
            ('NJ033','到着後発送','Ships after arrival',TRUE,'','完売','発送時期系',2,'REGEX','到着後\s*(\d{1,2})日以内発送(目安)?','到着後$1日以内発送$2'),
            ('NJ034','日数指定発送','Ships in specified days',TRUE,'','発売日,到着後,以内,完売,前後,までに,〜,~,ー,-','発送時期系',3,'REGEX','(\d{1,2})日(発送|出荷)','$1日発送'),
            ('NJ076','種数セット','Multi-type set',TRUE,'','','荷姿系',3,'REGEX','(\d{1,2})種セット','$1種セット'),
            ('NJ077','入数','Items per pack',TRUE,'','カートン','荷姿系',3,'REGEX','(\d{1,4})(枚|個)入','$1$2入'),
            ('NJ061','シュリンク付き','Shrink-wrapped',TRUE,'シュリンク付,シュリンクあり,シュリンク有,シュリ有,シュリあり','シュリンク無,シュリ無,シュリンクなし,シュリなし','外装系',2,'LITERAL',NULL,NULL),
            ('NJ062','シュリンクなし','No shrink wrap',TRUE,'シュリンク無,シュリ無,シュリンクなし,シュリなし','シュリンク付,シュリ有,シュリあり','外装系',2,'LITERAL',NULL,NULL),
            ('NJ063','予約商品','Pre-order item',TRUE,'予約商品,予約品','在庫品,在庫商品','取引条件系',3,'LITERAL',NULL,NULL),
            ('NJ064','在庫品','In-stock item',TRUE,'在庫品,在庫商品,有在庫','予約商品,予約品','取引条件系',3,'LITERAL',NULL,NULL),
            ('NJ065','未開封','Unopened',TRUE,'未開封','開封済,一度開封','検品系',2,'LITERAL',NULL,NULL),
            ('NJ066','発売日要相談','Release date negotiable',TRUE,'発売日要相談','発送日要相談','発送時期系',2,'LITERAL',NULL,NULL),
            ('NJ067','バラ売り要相談','Individual sale negotiable',TRUE,'バラ売り要相談,バラOK,バラし対応','','取引条件系',3,'LITERAL',NULL,NULL),
            ('NJ068','直接お渡し可','Direct handoff available',TRUE,'直接お渡し','','取引条件系',3,'LITERAL',NULL,NULL),
            ('NJ069','土日祝発送可','Weekend and holiday shipping available',TRUE,'土日祝も発送,土日祝日発送可,土日祝出荷可','出来ません,不可,休業','発送時期系',2,'LITERAL',NULL,NULL),
            ('NJ070','土日祝発送不可','No weekend or holiday shipping',TRUE,'土日祝発送出来ません,土日祝日発送業務休業','','発送時期系',2,'LITERAL',NULL,NULL),
            ('NJ072','カード付','Card included',TRUE,'カード付','プロモ,カードセット','付属品系',2,'LITERAL',NULL,NULL),
            ('NJ073','完売','Sold out',TRUE,'完売','出荷予定,発送予定','取引条件系',2,'LITERAL',NULL,NULL),
            ('NJ074','締め切り','Deadline',TRUE,'〆','','取引条件系',3,'LITERAL',NULL,NULL),
            ('NJ075','要相談','Negotiable',TRUE,'要相談,応相談','発送日要相談,発売日要相談,送料要相談,バラ売り要相談','取引条件系',3,'LITERAL',NULL,NULL),
            ('NJ078','送料要相談','Shipping fee negotiable',TRUE,'送料要相談,送料相談,送料はご相談','','取引条件系',3,'LITERAL',NULL,NULL)
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    EXECUTE format($q$
        UPDATE %I.tcg_note_master
        SET exclude_keywords = '前日,翌日,時まで,注文で,注文確定'
        WHERE id = 'NJ023'
    $q$, _schema);

    GET DIAGNOSTICS _updated_count = ROW_COUNT;
    IF _updated_count != 1 THEN
        RAISE EXCEPTION 'NOTE-B2 NJ023 update: expected 1 row, got %', _updated_count;
    END IF;

    EXECUTE format(
        'SELECT count(*) FROM %I.tcg_note_master WHERE id = ANY($1)',
        _schema
    ) INTO _note_count USING _note_ids;

    IF _note_count != 25 THEN
        RAISE EXCEPTION 'NOTE-B2 note rows: expected 25, got %', _note_count;
    END IF;

    EXECUTE format(
        'SELECT count(*) FROM %I.tcg_normalization_rules WHERE normalization_rule_id = ANY($1)',
        _schema
    ) INTO _rule_count USING _rule_ids;

    IF _rule_count != 13 THEN
        RAISE EXCEPTION 'NOTE-B2 normalization rows: expected 13, got %', _rule_count;
    END IF;

    RAISE NOTICE 'NOTE-B2 verified: % note rows, % normalization rows', _note_count, _rule_count;
END $body$;
