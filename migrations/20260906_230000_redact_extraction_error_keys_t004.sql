-- Migration: 20260906_230000_redact_extraction_error_keys_t004
--
-- 目的: tenant_004.extraction_jobs.error_message に残る Gemini API キー付きURLを
--       安全な定型文に置き換える。対象は 2026-09-04 の 24 行。
--
-- 背景:
--   2026-09-04 のバッチで Gemini API が 429 を返した際、例外メッセージに
--   リクエストURL（key= 付き）が含まれたまま error_message へ保存された。
--   この値は super-admin の診断画面に表示される。
--   現行コードは _safe_error_message()（gemini_extraction_svc.py:68-80）により
--   429 を「レート制限超過 (HTTP 429)」へ変換するため、新規の混入は発生しない。
--
-- 設計判断:
--   - UPDATE のみ。DELETE は行わない。extraction_jobs には analysis_runs と
--     extraction_items が ON DELETE CASCADE で紐づくため、行削除は影響範囲が広がる。
--   - バックアップ表を作らない。退避するとキー文字列が別テーブルに残り、
--     本 migration の目的（キー文字列の除去）に反するため。
--     失われるのは 429 エラーの元テキストのみで、id / status / created_at /
--     source_message_id はすべて残る。
--   - 置換後の文言は現行コードが生成する値と同一にする（表示の一貫性）。
--   - 検算は自分の担当範囲のみ。テーブル全体の件数一致チェックは行わない。
--
-- 冪等性: 実行後は key= を含む行が 0 件になるため、2 回目以降は 0 行更新。
--
-- 作成日: 2026-09-06

DO $$
DECLARE
    _schema         TEXT := 'tenant_004';
    _before_count   INTEGER;
    _after_count    INTEGER;
BEGIN

    -- スキーマ存在ガード（CI 環境対応）
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260906_230000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;
    RAISE NOTICE '20260906_230000: schema % confirmed', _schema;

    -- 対象テーブル存在ガード
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = _schema AND table_name = 'extraction_jobs'
    ) THEN
        RAISE NOTICE '20260906_230000: table %.extraction_jobs does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- 実行前の件数（自分の担当範囲のみ）
    EXECUTE format($q$
        SELECT count(*) FROM %I.extraction_jobs WHERE error_message LIKE '%%key=%%'
    $q$, _schema) INTO _before_count;
    RAISE NOTICE '20260906_230000: before = % rows', _before_count;

    -- 置換（現行コード _safe_error_message() と同一の文言）
    EXECUTE format($q$
        UPDATE %I.extraction_jobs
        SET error_message = 'レート制限超過 (HTTP 429)'
        WHERE error_message LIKE '%%key=%%'
    $q$, _schema);

    -- 実行後の件数（自分の担当範囲のみ）
    EXECUTE format($q$
        SELECT count(*) FROM %I.extraction_jobs WHERE error_message LIKE '%%key=%%'
    $q$, _schema) INTO _after_count;
    RAISE NOTICE '20260906_230000: after = % rows', _after_count;

    IF _after_count <> 0 THEN
        RAISE EXCEPTION '20260906_230000: key= を含む行が % 件残っています', _after_count;
    END IF;

    RAISE NOTICE '20260906_230000: done';

END $$;
