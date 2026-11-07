# R5 の確認 — 会社4 の通知の送り先（読み取りのみ）

- 実行: 2026-11-07T09:12:17Z、ADR-1024 の reader 道（AUDIT sha=9208dc64d368 rows=1 result=ok）
- 目的: 審査 R5。配信失敗の Discord 通知が今まで本当に送られていないかを、送り先の有無で確かめる

```sql
SELECT count(*) FILTER (WHERE is_active) active_all, count(*) FILTER (WHERE is_active AND event_types::text LIKE '%tcg_distribution_error%') active_tcg_err, count(*) total FROM ai_ro.tenant_004__notification_channels
```

結果（標準出力そのまま。タブ区切り）:

```
active_all	active_tcg_err	total
0	0	0
```
