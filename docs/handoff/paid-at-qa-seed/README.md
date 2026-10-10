# paid-at-qa-seed: 入金日動作確認用テストデータ（tenant_001）

## 目的
入金日（paid_at）の動作確認用に、tenant_001 へテストデータを入れる（リード・会社・担当者・発行済み請求書1件）。

## PO 承認
2026-10-10 チャット「y」（本番への適用は別途、設計者が DRY-RUN -> COMMIT で実行）。

## 想定件数
leads +1 / companies +1 / contacts +1 / invoices +1（status=issued）/ invoice_items +1。audit_logs は書かない（人の操作ではないため）。

## 実行順序
1. precheck.sql（読み取りのみ。QA 行が全て 0 件であること）
2. apply.sql（DRY-RUN は末尾 COMMIT を ROLLBACK に置き換えて流す。確認後に COMMIT 版）
3. postcheck.sql（読み取りのみ）
- rollback.sql は PO の新たな判断なしには実行しない。

## コード確認結果（origin/main 基準）
- A. backend/app/routers/contacts.py:480-482 の _replace_emails(:144-157)・_replace_contact_channels(:207-232) は、入力が空リストなら DELETE のみで INSERT しない。_upsert_discord(:160-204) は None なら DELETE のみ。-> 行は生じない（SQL にも入れない）。leads 側 normalize_channel_type_value（backend/app/services/channel_masters.py:27-36）は None と空文字を None にする。-> channel_type は NULL。
- B. create_contact（contacts.py:439-475）は display_name を surname/given_name から組み立てず、入力値をそのまま INSERT する。-> SQL でも surname='QA担当者'、display_name='QA担当者' を明示指定。
- C. create_lead（leads.py:425-466）は lead_code を INSERT で指定せず列既定（lead_code_seq）に任せ、直後に leads.py:463-466 で LD-{id:05d} に UPDATE する。-> SQL も同じ。companies（companies.py:385-438, UPDATE は :436）・contacts（contacts.py:469-473）も仮コード（PEND）から CO-/CT-{id:05d} へ UPDATE する。
- invoices は invoices.py:373-407、invoice_items は :411-424、発行 UPDATE は :501 に準拠。

## 実行記録

### 書き込み前確認（2026-10-10 Opus 実行・読み取りのみ）
```
       t       | count 
---------------+-------
 leads         |     1
 companies     |     0
 contacts      |     0
 invoices      |     0
 invoice_items |     0
(5 rows)

 qa_leads 
----------
        0
(1 row)

       conrelid       |                 conname                 |                                                                                  pg_get_constraintdef                                                                                  
----------------------+-----------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 tenant_001.companies | companies_trust_level_check             | CHECK (((trust_level IS NULL) OR ((trust_level >= 1) AND (trust_level <= 5))))
 tenant_001.companies | companies_monthly_forecast_source_check | CHECK (((monthly_forecast_source IS NULL) OR ((monthly_forecast_source)::text = ANY ((ARRAY['manual'::character varying, 'ai_analysis'::character varying])::text[]))))
 tenant_001.companies | companies_status_check                  | CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying, 'archived'::character varying, 'pending_dedup_review'::character varying])::text[])))
 tenant_001.contacts  | contacts_status_check                   | CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying, 'archived'::character varying, 'pending_dedup_review'::character varying])::text[])))
 tenant_001.leads     | leads_initiative_check                  | CHECK (((initiative IS NULL) OR ((initiative)::text = ANY ((ARRAY['outbound'::character varying, 'inbound'::character varying])::text[]))))
(5 rows)

 rolname | rolsuper | rolbypassrls 
---------+----------+--------------
 jarvis  | t        | t
(1 row)

    relname    | relrowsecurity | relforcerowsecurity 
---------------+----------------+---------------------
 leads         | t              | f
 contacts      | t              | f
 invoice_items | t              | f
 invoices      | t              | f
 companies     | t              | f
(5 rows)

```

### DRY-RUN（2026-10-10 Opus 実行・ROLLBACK で終了）

DRY-RUN で採番が進んだため、本実行の id は DRY-RUN より 1 つずつずれている。
```
SET
BEGIN
DO
DO
 lead_id | lead_code | company_id | company_code | contact_id | contact_code | invoice_id | invoice_number | status | total_amount |           issued_at           | paid_at 
---------+-----------+------------+--------------+------------+--------------+------------+----------------+--------+--------------+-------------------------------+---------
       5 | LD-00005  |          6 | CO-00006     |          2 | CT-00002     |          1 | IN-0001-01     | issued |      1000.00 | 2026-10-09 23:08:51.771428+00 | 
(1 row)

ROLLBACK
```

### 本実行（PO が `!` で実行、2026-10-10 12:24 UTC、PO 発行の permit-danger チケット使用。Opus の実行は分類器に拒否されたため）
```
SET
BEGIN
DO
DO
 lead_id | lead_code | company_id | company_code | contact_id | contact_code | invoice_id | invoice_number | status | total_amount |          issued_at           | paid_at 
---------+-----------+------------+--------------+------------+--------------+------------+----------------+--------+--------------+------------------------------+---------
       6 | LD-00006  |          7 | CO-00007     |          3 | CT-00003     |          2 | IN-0001-01     | issued |      1000.00 | 2026-10-10 12:24:24.43006+00 | 
(1 row)

COMMIT
```

### 書き込み後確認（各表 +1 件で想定どおり）
```
       t       | count 
---------------+-------
 leads         |     2
 companies     |     1
 contacts      |     1
 invoices      |     1
 invoice_items |     1
(5 rows)

 id | invoice_number | status | total_amount | currency |          issued_at           | paid_at | company_code |          name          | contact_code | no_email 
----+----------------+--------+--------------+----------+------------------------------+---------+--------------+------------------------+--------------+----------
  2 | IN-0001-01     | issued |      1000.00 | JPY      | 2026-10-10 12:24:24.43006+00 |         | CO-00007     | QA入金日テスト株式会社 | CT-00003     | t
(1 row)

```

### 次の手順
- PO が tenant_001 の請求書 IN-0001-01 で日付を選び「入金登録」を行う。
- Opus が paid_at を読み取り確認する。
- rollback.sql は PO の新たな判断なしに実行しない。
