# recon — S6 一覧の全件取得・CSV 出力（GET）を記録し、閲覧の大量取得を検知する（get-access-audit）

**日付**: 2026-10-17　**基準**: origin/main 449a77166（作業場所 HEAD と一致）　**仕様書**: [docs/specs/get-access-audit/README.md](../../specs/get-access-audit/README.md)
**生出力**: /tmp/CC報告ファイル/s6-get-audit/（original-s6.txt、audit.py.txt、detail/、r1.txt・r2.txt、loki3.txt、item6.txt）

## 指摘の原文（2026-10-15 のセキュリティ監査。会話記録から転記。original-s6.txt）

> ### S6【低〜中】一部GET全件＋GETの大量取得が無監査
> - 顧客一覧は per_page 上限100で保護。ただし一部GETが無制限: order_financials.py:390, duplicates.py:68, 各 /export CSV（いずれも権限必須・同一テナント内）。
> - 監査は書込メソッドのみ記録、大量エクスポート検知も書込のみ（audit.py:121,133,199）。GETでの大量吸い出しは検知されない。

推奨対策の記述は原文に無い。

## 既存 ADR の検索結果

- `git grep -i -E "data_access_events|bulk_export|閲覧記録" origin/main -- docs/adr` → 0 件。data_access_events・大量検知を決めた ADR は無い。
- 近いもの: docs/adr/ADR-128-audit-log-coverage-high.md（record_audit_log＝書込の網羅。GET は扱わない）、ADR-129（書込の補完）。
- docs/adr/FEATURE-INDEX.md に監査・audit の行は無い。
- 既存のコード上の正本: backend/app/middleware/audit.py（data_access_events・auth_events への記録と大量検知）。

## 1. いまの記録の仕組み（origin/main、audit.py.txt）

- 【事実】書込だけを記録する: backend/app/middleware/audit.py:41 `_WRITE_METHODS = {"POST","PATCH","PUT","DELETE"}`、:126 `if is_write_op and status_code < 500:` のときだけ `_record_data_access`。GET は data_access_events に記録されない。
- 【事実】大量検知 `_check_and_record_bulk_export`（:65-93）: Redis（app.cache.get_redis、非同期クライアント。backend/app/cache.py:7,:43）に `bulk_access:{sha256(email)[:16]}:{time//600}` を incr（:83-88）。`count > 500` で True（:47-48、:90）。呼ばれるのは `_record_data_access` の中だけ（:192）＝数えているのは書込だけ。
- 【事実】検知時の出口は logger.warning（:195-200）と event_type=`bulk_export_alert` の行の INSERT（:194、:202-223）だけ。通知・遮断は無い。
- 【事実】email は JWT のペイロードから署名検証なしで読む（:51-62、ログ用途）。email が無い・Redis 不通・例外のときは検知せず通す（:72-73、:80-81、:91-93）。記録の失敗は logger.exception で握りつぶし、応答に影響しない（:224-225）。
- 【事実】モジュールの説明（:9-11）は「全書き込み操作」「大量エクスポート検知」。:15「バックグラウンドタスクで記録する」は実装（call_next の後に await）と合わない。
- 【事実】public.data_access_events: migrations/071_create_data_access_events.sql:7-18。event_type は `VARCHAR(50) NOT NULL` で CHECK・ENUM は無い（:9。detail/）。60 日超は毎日削除（backend/app/tasks/maintenance.py:29、:149-166、backend/app/celery_app.py:89-95）。
- 【事実】data_access_events を読む画面・API・通知は origin/main に無い（item6.txt、detail/）。

## 2. 本番の量（読み取り）

- 【事実】data_access_events は 3,958 行（2026-08-18〜2026-10-16）。すべて data_write（POST 3,832・PATCH 66・DELETE 46・PUT 14）。GET 0、bulk_export_alert 0（r1.txt、r2.txt）。直近の 1 日あたり 54〜198 行。
- 【事実】Loki に残る nginx 記録（2026-10-09〜10-17、/api/health を除く GET /api/）: 1 日 463〜1,884 件。接続元ごとの 10 分あたりの GET 数の最大は 155（上位は 155・55・42・37・30）（loki3.txt）。nginx の記録には利用者が出ないため、接続元単位で数えた（同じ接続元を共有する複数の利用者は合算される＝利用者単位の値はこれ以下）。
- 【事実】7 日間の GET 回数: /api/v1/financials/orders 1、/api/v1/companies/duplicates 0、/export を含むパス 11（loki3.txt）。
- 【事実】本番コンテナの nginx の docker 記録は 10MB×3 で、deploy のたびに作り直されるため数時間分しか残らない（p1.txt。2026-10-17 00:47 は再起動直後で 0 行、nginx-get.txt）。量は Loki で測った。

## 3. 全件を返す GET・ファイルを返す GET（完全なパス。detail/scan.txt）

すべて main.py の `prefix="/api/v1"`（main.py:238-261 の例外を除く）。

- 全件の一覧: GET /api/v1/financials/orders（order_financials.py:386。権限 orders.view、LIMIT 無し :407-424）、GET /api/v1/companies/duplicates（duplicates.py:67。権限 companies.view、LIMIT 無し :79-97。frontend からの呼び出しは無い）。
- `/export` で終わる GET: 16 本（conditions・note-master・product-categories・status-master・suppliers・units、super-admin の aliases・conditions・knowledge・note-master・product-categories・status-master・suppliers・units、tcg/products/export、tcg/review/csv/export）。どれも権限必須、LIMIT 無し。
- `/export` で終わらない CSV: GET /api/v1/shipping/elogi-csv（order_shipping_details.py:390、order_ids 最大 1000）、GET /api/v1/orders/{order_id}/shipping/elogi-csv（:353）、GET /api/v1/reports/{task_id}/download（reports.py:103、text/csv）。
- 大量取得に当たらないもの（対象外）: 添付 1 件の取得（leads.py:1433）、即時通知の stream 3 本（leads.py:2887、meta_inbox.py:1034、realtime_events.py:58）、担当者の顔画像（public_staff_avatars.py:21）。

## 4. 画面の使い方

- 【事実】/financials/orders は frontend/src/pages/sales/SalesPage.tsx:69 と frontend/src/pages/commissions/CommissionsPage.tsx:121 が全件を前提に使う（ページ送り無し）。件数を区切ると画面の作り直しが要る。
- 【事実】/export 系は frontend がボタン押下時に `api.getBlob` で呼ぶ（ConditionsPage.tsx:103、SuppliersPage.tsx:112、ProductMasterPanel.tsx:52 ほか）。

## 5. 試験の現状

- 【事実】backend/tests/test_security_hardening.py:419-476 `TestBulkExportDetection` が検知関数の 5 件（閾値前後・email 無し・Redis 不通・TTL）を確かめる。Redis は `patch("app.cache._redis", AsyncMock())` で差し替え。
- 【事実】AuditMiddleware を通す試験は backend/tests/test_client_ip.py:116-170 の 1 本。`patch("app.middleware.audit.AsyncSessionLocal", ...)` で INSERT の引数を捕まえる。
- 【事実】GET が記録されないこと・書込だけ数えることを確かめる試験は無い。

## 6. 未確認

- 本番の各テナントの orders・companies の行数（読み取りが権限判定で止まったため未取得。本設計は件数制限をしないため判定に使わない）。
