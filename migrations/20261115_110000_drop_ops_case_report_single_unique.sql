-- ADR-1012 段階4 便2b: 報告の古い一意（incident_id だけ）を消す。名前ではなく中身で探す（作ったときに名前を付けていないため）。冪等。
DO $$
DECLARE
    c TEXT;
BEGIN
    FOR c IN
        SELECT con.conname
        FROM pg_constraint con
        WHERE con.conrelid = 'ops_case.reports'::regclass
          AND con.contype = 'u'
          AND con.conkey = ARRAY[(SELECT a.attnum FROM pg_attribute a
                                  WHERE a.attrelid = 'ops_case.reports'::regclass AND a.attname = 'incident_id')]::int2[]
    LOOP
        EXECUTE format('ALTER TABLE ops_case.reports DROP CONSTRAINT %I', c);
    END LOOP;
END $$;

COMMENT ON TABLE ops_case.reports IS '相談係の報告。1 件につき種類（kind）ごとに 1 通';
