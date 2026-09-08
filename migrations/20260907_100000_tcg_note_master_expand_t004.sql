-- MIG NOTE-EXPAND-A: tcg_note_master 固定札26件追加＋既存2行の検索語更新 (tenant_004)
-- 設計: docs/handoff/tcg-product-master-growth/design-note-master.md 4-2
-- 対象ADR: ADR-154
-- 冪等: INSERT ON CONFLICT DO NOTHING / UPDATE は同値の再代入
-- 件数確認は本ファイルが投入する26件の範囲のみを数える（テーブル全体は数えない）

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
    _ids    TEXT[]  := ARRAY[
        'NJ023','NJ024','NJ025','NJ026','NJ027','NJ028','NJ029',
        'NJ035','NJ036','NJ037','NJ038','NJ039','NJ040',
        'NJ041','NJ042','NJ043','NJ044','NJ045',
        'NJ046','NJ047','NJ048','NJ049','NJ050',
        'NJ054','NJ055','NJ056'
    ];
    _count  INTEGER;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260907_100000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES
        ('NJ023','発売日発送','Ships on release day',TRUE,'発売日発送,発売日当日発送,当日発送,発売日出荷','前日,翌日','発送時期系',2),
        ('NJ024','発売日前日発送','Ships day before release',TRUE,'発売日前日,前日発送','','発送時期系',2),
        ('NJ025','発売日翌日発送','Ships day after release',TRUE,'発売日翌日,翌日発送','受注の翌日','発送時期系',2),
        ('NJ026','即日発送可','Same-day shipping',TRUE,'即日発送,即日出荷,当日出荷,受注の翌日','','発送時期系',2),
        ('NJ027','入荷次第発送','Ships upon arrival',TRUE,'入荷次第,届き次第,到着次第,入荷後発送','','発送時期系',2),
        ('NJ028','発送日要相談','Ship date negotiable',TRUE,'発送日要相談,発送日相談,発送日（要相談）,発送日(要相談),発送日要相,発送日確認','','発送時期系',2),
        ('NJ029','国内発送のみ','Domestic shipping only',TRUE,'国内発送のみ,国内のみ,国内限定','','発送時期系',2),
        ('NJ035','買取品','Buyback stock',TRUE,'買取品,買取含,自社買取,買取(当グループ含)','','仕入元系',3),
        ('NJ036','問屋品','Wholesale stock',TRUE,'問屋','','仕入元系',3),
        ('NJ037','店舗品','Retail-sourced',TRUE,'店舗仕入,店舗購入,ポケセン,カドショ','','仕入元系',3),
        ('NJ038','正規流通品','Official distribution',TRUE,'正規流通,正規品','','仕入元系',3),
        ('NJ039','サーチ済の可能性','Possibly searched',TRUE,'サーチ済,サーチの可能性,サーチ痕,サーチ跡','サーチ痕無,サーチ痕なし,サーチ跡無,未サーチ','サーチ系',2),
        ('NJ040','未サーチ','Unsearched',TRUE,'未サーチ,サーチ痕無,サーチ痕なし,サーチ跡無,サーチなし','','サーチ系',2),
        ('NJ041','伝票跡','Shipping label marks',TRUE,'伝票跡,伝票痕,伝票剥がし跡','','跡痕系',1),
        ('NJ042','テープ跡','Tape marks',TRUE,'テープ跡,テープ痕,連結跡,連結痕,テープ連結','テープカット','跡痕系',1),
        ('NJ043','ラベル跡','Label marks',TRUE,'ラベル跡,ラベル痕','','跡痕系',1),
        ('NJ044','シリアル切り取り','Serial cut out',TRUE,'シリアル切り取り,シリアルナンバー切り取り,シリアル切取','シリアルのみ','跡痕系',1),
        ('NJ045','カートン数字記載','Numbers written on carton',TRUE,'数字の記載,数字記載','','跡痕系',1),
        ('NJ046','段ボール傷','Outer carton damage',TRUE,'段ボール傷,段ボールダメージ,段ボール凹','','ダメージ系',1),
        ('NJ047','B品','B-grade',TRUE,'B品,Ｂ品','','ダメージ系',1),
        ('NJ048','上部切り取り','Top panel cut',TRUE,'上部切り取り,切り取り部分','','ダメージ系',1),
        ('NJ049','美品','Mint condition',TRUE,'美品','','外装系',3),
        ('NJ050','カートン発送可','Carton shipping available',TRUE,'カートン可,カートン発送可,マスターカートン発送可,カートン発送可能','','荷姿系',2),
        ('NJ054','大口割引可','Bulk discount available',TRUE,'大口,値引,値下げ,お値段交渉,交渉可','','取引条件系',3),
        ('NJ055','写真掲載可','Photos may be posted',TRUE,'写真掲載可,画像掲載可,写真掲載可能','','取引条件系',3),
        ('NJ056','SNS投稿不可','No social media posting',TRUE,'SNSへの投稿不可,SNS投稿不可','','取引条件系',3)
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- 既存2行の検索語を更新（同値の再代入で冪等）
    EXECUTE format($q$
        UPDATE %I.tcg_note_master
        SET search_keywords = '再販,再版,再販分,再販仕様,再販品,二次再販,第二版,2版,２版'
        WHERE id = 'NJ004'
    $q$, _schema);

    EXECUTE format($q$
        UPDATE %I.tcg_note_master
        SET search_keywords = '箱痛み,箱ダメ,箱潰れ,箱凹み,箱へこみ,傷みあり,傷み有り,傷み,いたみあり,箱いたみ,箱傷み'
        WHERE id = 'NJ014'
    $q$, _schema);

    -- 本ファイルが投入した26件のみを数える
    EXECUTE format('SELECT count(*) FROM %I.tcg_note_master WHERE id = ANY($1)', _schema)
        INTO _count USING _ids;
    IF _count != 26 THEN
        RAISE EXCEPTION 'tcg_note_master expand: 期待26件、実際%件', _count;
    END IF;

    RAISE NOTICE 'tcg_note_master expand: % 件確認 OK', _count;
END $body$;
