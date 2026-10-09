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
