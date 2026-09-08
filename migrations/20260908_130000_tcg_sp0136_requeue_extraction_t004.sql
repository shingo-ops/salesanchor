-- LMI-SP0136-REQUEUE: SP0136 の有効メッセージ 2336edf3 の抽出ジョブを再実行可能な状態に戻す
--
-- 背景:
--   tenant_004 の supplier_channel SP0136 に有効な source_message が2件並存している。
--   掃除規則（received_at 最新の1件を残す・NULL は最古扱い）では 2336edf3 が残るが、
--   その抽出ジョブ a6c1d827 が 2026-09-04 の 429 で error のまま止まっている。
--   残す1件が未抽出のため掃除が実行できない（docs/handoff/tcg-line-message-integrity/design.md）。
--
-- 本 migration の範囲:
--   ジョブ a6c1d827 の1行のみ。id・status・created_at の3条件で特定する。
--   他の55件の error ジョブには一切触れない。
--   抽出成功後は status が done になるため、再デプロイ時に再度ヒットすることはない（冪等）。
--
-- 対象ADR: ADR-154
-- 対象テナント: tenant_004（本番）

UPDATE tenant_004.extraction_jobs
SET status        = 'pending',
    error_message = NULL
WHERE id         = 'a6c1d827-7fd5-4cfc-a2e0-b0fa63388b43'
  AND status     = 'error'
  AND created_at = '2026-09-04 07:54:11.187158+00';

-- 確認: 対象ジョブの現在の状態（この1行のみを数える）
SELECT id, status, error_message, extracted_at
FROM tenant_004.extraction_jobs
WHERE id = 'a6c1d827-7fd5-4cfc-a2e0-b0fa63388b43';
