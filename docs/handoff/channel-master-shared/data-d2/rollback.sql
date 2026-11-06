-- D2: 名簿に無い値の後始末（PO 2026-11-06）。設計 docs/handoff/channel-master-shared/design.md §9 D2・§3-2。
-- rollback（001・004 を unknown / meta_messenger に戻す。006 は backup.sh の写し tenant_006 のデータを psql で流し戻す。手順は run.sh の rollback）。
BEGIN;
SET LOCAL app.tenant_id = '1';
UPDATE tenant_001.leads SET channel_type='unknown', updated_at=NOW() WHERE id=6 AND channel_type='discord';
SET LOCAL app.tenant_id = '4';
UPDATE tenant_004.leads SET channel_type='unknown', updated_at=NOW() WHERE channel_type='messenger' AND id IN (35,36,37,38,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,148);
UPDATE tenant_004.conversation_logs SET channel_type='meta_messenger' WHERE channel_type='messenger' AND id IN (1,3,4);
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_001.leads WHERE channel_type='unknown')=1 AND (SELECT count(*) FROM tenant_004.leads WHERE channel_type='unknown')=54 AND (SELECT count(*) FROM tenant_004.conversation_logs WHERE channel_type='meta_messenger')=3 THEN 1 ELSE 0 END) AS restored;
COMMIT;
