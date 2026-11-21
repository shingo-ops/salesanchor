# 5-4 前調査の生の数（2026-11-21、Opus。本番反映の記録を gh で読んだだけ）

## 控えの段と移行の段の組み合わせ（5-3 の起点の後の本番反映83回。数えは gh run view の段の結論）

```
total 83
backup=skipped migrate=skipped : 55
backup=skipped migrate=success : 23
backup=success migrate=success : 5
--- backup ran
44060541002 2026-11-17T09:58:56Z success success success 159.0
44075427374 2026-11-17T11:35:39Z success success success 159.0
44105121489 2026-11-17T14:37:20Z success success success 158.0
44443616566 2026-11-19T02:20:44Z success success success 165.0
44801242967 2026-11-20T19:20:43Z success success success 166.0
--- run conclusions
Counter({'success': 82, 'failure': 1})
```

## 移行の段が動いた28回（列: run・始まり・移行・控えの段の結論・(c) to-run）

```
44060541002 2026-11-17T09:58:56Z mig success 1
44070159876 2026-11-17T11:01:18Z mig skipped 0
44075427374 2026-11-17T11:35:39Z mig success 2
44082630908 2026-11-17T12:23:09Z mig skipped 0
44096043925 2026-11-17T13:46:12Z mig skipped 0
44105121489 2026-11-17T14:37:20Z mig success 0
44131274427 2026-11-17T16:55:35Z mig skipped 0
44203949092 2026-11-17T23:58:35Z mig skipped 0
44213069844 2026-11-18T01:05:23Z mig skipped 0
44343066159 2026-11-18T16:05:08Z mig skipped 0
44366126348 2026-11-18T18:06:58Z mig skipped 0
44435580828 2026-11-19T01:15:58Z mig skipped 0
44438263812 2026-11-19T01:37:12Z mig skipped 0
44443616566 2026-11-19T02:20:44Z mig success 1
44449713400 2026-11-19T03:11:47Z mig skipped 0
44575090157 2026-11-19T17:14:53Z mig skipped 0
44659581474 2026-11-20T02:16:21Z mig skipped 0
44662019670 2026-11-20T02:36:35Z mig skipped 0
44666331493 2026-11-20T03:14:15Z mig skipped 0
44686062335 2026-11-20T06:11:35Z mig skipped 0
44688432900 2026-11-20T06:31:45Z mig skipped 0
44698205369 2026-11-20T07:52:47Z mig skipped 0
44700714717 2026-11-20T08:12:34Z mig skipped 0
44708863117 2026-11-20T09:13:17Z mig skipped 0
44753443381 2026-11-20T14:26:16Z mig skipped 0
44788175148 2026-11-20T17:57:20Z mig skipped 0
44801242967 2026-11-20T19:20:43Z mig success 1
44845351256 2026-11-21T00:40:10Z mig skipped 0
```

## run_py の26本（scripts/run_all_migrations.sh の ^run_py 行の第2欄）

```
   1 scripts/migrate_meta.py
   1 scripts/migrate_meta_page_routing.py
   1 scripts/migrate_meta_messages_page_id.py
   1 scripts/migrate_meta_messages_message_id_to_text.py
   1 scripts/migrate_meta_inbox_phase1d.py
   1 scripts/migrate_meta_inbox_phase1d_sprint4.py
   1 scripts/migrate_inventory_sprint9.py
   1 scripts/migrate_inventory_sprint8.py
   1 scripts/migrate_inventory_sprint5_to_7.py
   1 scripts/migrate_inventory_sprint2.py
   1 scripts/migrate_inventory_sprint1.py
   1 scripts/migrate_adr119_lead_channels_backfill.py
   1 scripts/migrate_adr109_status_codes.py
   1 scripts/migrate_adr041_granted_scopes.py
   1 scripts/migrate_adr021_sprint5_commissions.py
   1 scripts/migrate_adr021_sprint4_purchase.py
   1 scripts/migrate_adr021_sprint3_shipping.py
   1 scripts/migrate_adr021_sprint2_financials.py
   1 scripts/migrate_adr021_remove_confirmed_status.py
   1 scripts/migrate_adr015_lead_foundation.py
   1 scripts/migrate_20260621_020000_backfill_lead_country.py
   1 scripts/migrate_20260620_080000_calendar_category_backfill.py
   1 scripts/migrate_074_rename_english_name_to_nickname.py
   1 scripts/migrate_073_lead_status.py
   1 scripts/migrate_011_phase5_tenant_tables.py
   1 scripts/migrate_009_phase4_tenant_tables.py
```
