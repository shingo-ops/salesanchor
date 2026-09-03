-- MIG PARITY-02 A-3: tcg_note_master (tenant_004)
-- 注記マスタ 22件を新規テーブルへ投入
-- 移植元: investigate2.gs:14994-15134 (_NOTE_MASTER_ROWS_ 定義値)
--         HEADERS_NOTE_MASTER: 00_Constants.gs:38-47
-- 冪等: CREATE IF NOT EXISTS + INSERT ON CONFLICT DO NOTHING

DO $body$
DECLARE
    _schema TEXT    := 'tenant_004';
    _count  INTEGER;
BEGIN
    -- -------------------------------------------------------------------------
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    -- -------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260903_130000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- -------------------------------------------------------------------------
    -- テーブル作成（additive-only / IF NOT EXISTS）
    -- -------------------------------------------------------------------------
    EXECUTE format($ddl$
        CREATE TABLE IF NOT EXISTS %I.tcg_note_master (
            id               TEXT        PRIMARY KEY,
            label_ja         TEXT        NOT NULL,
            label_en         TEXT        NOT NULL,
            enabled          BOOLEAN     NOT NULL DEFAULT TRUE,
            search_keywords  TEXT        NOT NULL DEFAULT '',
            exclude_keywords TEXT        NOT NULL DEFAULT '',
            category         TEXT        NOT NULL DEFAULT '',
            priority         INTEGER     NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $ddl$, _schema);

    -- -------------------------------------------------------------------------
    -- 22件 seed（GAS: investigate2.gs:14994-15134 の確定値）
    -- search_keywords / exclude_keywords はカンマ区切り TEXT
    -- ON CONFLICT DO NOTHING で冪等
    -- -------------------------------------------------------------------------

    -- NJ001: 検品開封済み（検品系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ001', '検品開封済み', 'Inspected (opened)', TRUE,
            '検品のため,確認のため,開封済,検品済,一度開封,裏を開封,袋を開封,段ボール開封済,弊社検品済',
            'テープカット,カートンテープカット',
            '検品系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ002: プロモ付き（プロモ系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ002', 'プロモ付き', 'Promo included', TRUE,
            'プロモ付,プロモ入り,プロモ30p,プロモ30枚,プロモ付き,熱風のアリーナプロモ,争奪戦プロモ,プロモーションカード',
            'プロモ無し,プロモなし,プロモ無,雑誌プロモ,カードセット',
            'プロモ系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ003: プロモなし（プロモ系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ003', 'プロモなし', 'No promo', TRUE,
            'プロモ無し,プロモなし,プロモ無,プロモ別売',
            'プロモ付,プロモ入り',
            'プロモ系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ004: 再販品（版情報系 priority=3）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ004', '再販品', 'Reissue', TRUE,
            '再販,再版,再販分,再販仕様,再販品,二次再販',
            '初版,初回生産',
            '版情報系', 3
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ005: 初版品（版情報系 priority=3）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ005', '初版品', 'First print', TRUE,
            '初版,初回生産,初版仕様,初回生産分',
            '再販,再版',
            '版情報系', 3
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ006: ダメージ（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ006', 'ダメージ', 'Damage noted', TRUE,
            'ダメージ,ダメージ品,難あり,難有り',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ007: スジ（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ007', 'スジ', 'Crease marks', TRUE,
            'スジ,すじ,スジあり',
            'スペースジャグラー',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ008: 凹み（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ008', '凹み', 'Dented', TRUE,
            '凹み,へこみ,ヘコミ',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ009: 潰れ（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ009', '潰れ', 'Crushed', TRUE,
            '潰れ,つぶれ,ツブレ',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ010: 破れ・破損（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ010', '破れ・破損', 'Torn/Damaged', TRUE,
            '破れ,破損,シュリンク破れ',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ011: 反り（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ011', '反り', 'Warped', TRUE,
            '反り,ソリ,そり',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ012: 傷・キズ（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ012', '傷・キズ', 'Scratched', TRUE,
            'キズ,スレ,傷あり,傷有り,キズあり',
            '傷み,箱痛み',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ013: 汚れ（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ013', '汚れ', 'Stained', TRUE,
            '汚れ,汚れあり,汚れ有り',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ014: 箱痛み（ダメージ系 priority=1）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ014', '箱痛み', 'Box damaged', TRUE,
            '箱痛み,箱ダメ,箱潰れ,箱凹み,箱へこみ,傷みあり,傷み有り,傷み,いたみあり,箱いたみ',
            '',
            'ダメージ系', 1
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ015: 被りあり（分布系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ015', '被りあり', 'Duplicates present', TRUE,
            '被りあり,被り有り,かぶり,被り有',
            '被りなし,重複なし',
            '分布系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ016: 被りなし（分布系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ016', '被りなし', 'No duplicates', TRUE,
            '被りなし,被り無し,重複なし',
            '被りあり',
            '分布系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ017: ランダム（分布系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ017', 'ランダム', 'Random assortment', TRUE,
            'ランダム',
            '完全ランダム,被りなし',
            '分布系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ018: 完全ランダム（分布系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ018', '完全ランダム', 'Fully random assortment', TRUE,
            '完全ランダム',
            '',
            '分布系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ019: 白箱（外装系 priority=3）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ019', '白箱', 'White box', TRUE,
            '白箱,白箱未開封',
            '',
            '外装系', 3
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ020: スリーブ入り（バルク系 priority=2）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ020', 'スリーブ入り', 'Card-sleeved', TRUE,
            'スリーブ入り,スリーブ入',
            'スリーブ無し,スリーブなし',
            'バルク系', 2
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ021: 本付き（付属品系 priority=3）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ021', '本付き', 'Book included', TRUE,
            '本付き,本付',
            '',
            '付属品系', 3
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- NJ022: 雑誌付き（付属品系 priority=3）
    EXECUTE format($q$
        INSERT INTO %I.tcg_note_master
            (id, label_ja, label_en, enabled, search_keywords, exclude_keywords, category, priority)
        VALUES (
            'NJ022', '雑誌付き', 'Magazine included', TRUE,
            '雑誌付き,雑誌付,雑誌プロモ付,雑誌プロモ',
            '',
            '付属品系', 3
        )
        ON CONFLICT (id) DO NOTHING
    $q$, _schema);

    -- -------------------------------------------------------------------------
    -- 件数確認（このmigrationが挿入した NJ001〜NJ022 の22件を確認）
    -- BETWEEN で担当範囲を限定することで、後から追加された行に影響されない
    -- -------------------------------------------------------------------------
    EXECUTE format(
        'SELECT count(*) FROM %I.tcg_note_master WHERE id BETWEEN $1 AND $2',
        _schema
    ) INTO _count USING 'NJ001', 'NJ022';
    IF _count != 22 THEN
        RAISE EXCEPTION 'tcg_note_master: 期待22件、実際%件 (NJ001-NJ022)', _count;
    END IF;

    RAISE NOTICE 'tcg_note_master: 22 件確認 OK (NJ001-NJ022)';
END $body$;
