---
mode: handoff
---
# recon — S1 段階②b（仕入先台帳 public.suppliers に RLS）

> この文書は何か：仕入先台帳（public.suppliers）に RLS を付ける前に、本番の中身と、この表へ書き込む経路をすべて調べた記録です。

親: [docs/specs/tenant-rls/README.md](../../specs/tenant-rls/README.md)
生データ（リポジトリ外）: `/tmp/CC報告ファイル/s1-stage2/2b-recon-raw.md`、`/tmp/CC報告ファイル/s1-stage2/2b2-recon-raw.md`、`/tmp/CC報告ファイル/s1-stage2/2b-prod-recent.txt`、`/tmp/CC報告ファイル/s1-stage2/2b-schemas.txt`。file:line は worktree 基準の相対パス。読取のみで調べた。

## §1 本番データ

- 【事実】本番 `public.suppliers` は 288 行。全行が共通行（tenant_id が空）。根拠: design.md:15、`/tmp/CC報告ファイル/s1-stage2/2b-prod-recent.txt`（直近 updated_at 順の一覧で tenant_id 列が空）。
- 【事実】各社スキーマに suppliers 表は無い（public のみ）。根拠: design.md:16、`/tmp/CC報告ファイル/s1-stage2/2b-schemas.txt`。
- 【事実】会社画面 `/suppliers` は `tenant_id = 自社` で絞って読む（backend/app/routers/suppliers.py:152）ため、表示件数は 0 件のまま変わらない。
- 【事実】直近 14 日にも作成・更新がある。最新 created/updated は 2026-10-15 13:11:10Z（`/tmp/CC報告ファイル/s1-stage2/2b-recon-raw.md` Q3）。

## §2 書込経路の全列挙

すべて「tenant_id / is_operator を張らない」状態で書いている（set_operator_context の実呼出は routers/fx_rate_admin.py:135 のみ。backend/app/auth/dependencies.py:489-503）。

### HTTP（会社画面）backend/app/routers/suppliers.py（main.py:406、全て Depends(get_current_tenant) あり）
- :266 INSERT（tenant_id=自社）／:274 UPDATE supplier_code（直前 INSERT の id）／:307 UPDATE（id と tenant_id）／:331 論理削除（id と tenant_id）／:443-448 UPDATE・:470-480 INSERT（tenant_id=自社）・:485-493 UPDATE supplier_code（import/commit）。
- NULL 行（共通行）を作るものは無い。

### HTTP（運営画面）backend/app/routers/super_admin_suppliers.py
- :128 INSERT（tenant_id=NULL 固定、ON CONFLICT DO UPDATE）／:152 UPDATE supplier_code／:183 UPDATE（WHERE id のみ）／:211 論理削除（WHERE id のみ）／:462・:488・:506 import/commit／:757 抽出ルール更新（tenant_id IS NULL）。:933 付近は存在確認の SELECT のみ。

### HTTP（LINE 取込の確認）backend/app/routers/tcg_line_import.py（resolve_supplier :398）
- :480 UPDATE line_name（tenant_id 条件なし）／:489 INSERT（列リストに tenant_id なし＝NULL）／:502 UPDATE supplier_code。

### HTTP（端末の自動取込）
- `POST /api/v1/tcg/line-devices/import`（backend/app/routers/line_import_devices.py:68-82、main.py:743）。:77 で upload_android_line_export（tcg_line_import.py:714）を関数として直接呼び、import_line_export → backend/app/services/tcg_line_import_svc.py:643（INSERT、tenant_id なし）・:656（UPDATE）に到達する。
- 認証は端末トークン（Bearer）。get_current_tenant も set_operator_context も無い。tcg_line_import.py:690 の `require_super_admin` は直接呼出のため評価されない。

### 発注複製
- backend/app/routers/purchase_orders.py:108 `_resolve_tenant_supplier_id`（create_po :160/:173 から）: INSERT の列リストに tenant_id なし。frontend からの呼出は 0 件（`/tmp/CC報告ファイル/s1-stage2/2b-recon-raw.md` Q2）。

### サービス・CLI・CI
- backend/app/services/line_source_names.py:114（link_pending :81）: UPDATE line_name（WHERE id のみ）。:98 は LOCK TABLE。
- `python -m app.line_import_admin`（backend/app/line_import_admin.py:172。CI は .github/workflows/line-import-operations.yml:54、main のみ :18）: resolve_supplier（:155）・link_pending 経由で上記 UPDATE/INSERT に到達。tenant/operator の SET は grep で 0 件。
- scripts/seed_suppliers_from_line_master.py:147、scripts/seed_suppliers_from_sheet.py:126（手動 CLI、INSERT）。本番での実行実績は【未確認】。

### Celery
- 【事実】backend/app/tasks/ に suppliers 書込は 0 件。tcg_extraction.py:252 は LEFT JOIN、tcg_mirror.py:165,175,195 は SELECT のみ。beat_schedule（backend/app/celery_app.py:61-）に suppliers へ書くタスクは無い。
- 【事実】ORM の `Supplier` クラスは無い（ORM 経由の書込は 0）。

## §3 毎日の自動登録が端末取込であることの突合

【事実】suppliers 26049 は HTTP で作られていた。経路は `POST /api/v1/tcg/line-devices/import`（Celery ではない）。根拠（`/tmp/CC報告ファイル/s1-stage2/2b2-recon-raw.md`）:
- suppliers 26049.created_at = 2026-10-15 13:11:10.682679+00 が import_jobs 376ad277-… の created_at とマイクロ秒まで一致。26048（10-13 08:06:09.260071）・26047（10-12 22:49:10.041225）も、それぞれ別の import_jobs と一致。
- 3 件とも import_jobs.filename=android-talk.txt、uploaded_by=運営管理者、status=ok。
- nginx の 13:11:10 +0000 に `POST /api/v1/tcg/line-devices/import HTTP/1.1 200`（Python-urllib/3.14）1 行。同窓の import_jobs 43 件と nginx の同パス 43 件が一致。
- 26047〜26049 は tenant_id 空・supplier_type=corporate・supplier_code=SP-<id>。tcg_line_import_svc.py:643-656 の書式と一致。
- 【未確認】10-12・10-13 の呼出元（nginx ログは 10-15 01:02:55Z 起動以降のみ。DB 突合のみ）。Termux 側の送信間隔設定。14 日分の呼出ログ。
- 【推測】10-15 の import_jobs が 12:10〜14:41Z に 3〜30 分間隔で並ぶのは端末の定期送信（呼出元の cron 等は未確認）。

## §4 試験と CI

- suppliers を触る既存試験は 31 ファイル（`/tmp/CC報告ファイル/s1-stage2/2b-recon-raw.md` Q6）。RLS 役（salesanchor_app）で suppliers を検証する既存試験は 0 件。
- CI の実 PG は .github/workflows/test.yml:223,225（RLS_TEST_DATABASE_URL=salesanchor_app、RLS_ADMIN_DATABASE_URL=jarvis）。
- 【事実】.github/workflows/migration-test.yml は migrate_inventory_sprint1.py（migrations/056〜062）で public.suppliers を作る（:568 のコメント）。migrations/056_add_suppliers_type_and_promote_public.sql:24 は「tenant_id 列を持たない」とあり、tenant_id 列を足すのは migrations/20260918_030000_supplier_ssot_phase2.sql:52。
- 【事実（実装時の確認）】したがって PR で変更された SQL だけを流す migration-test の経路では、本 migration（ポリシーが tenant_id を参照）の前提の列が無い状態になる。この確認は workflow を読んだ結果で、CI 実行結果は【未確認】。対処（②a と同様に migration-test.yml へ列だけ登録する案）は、実装担当の権限で workflow の変更が拒否されたため未実施。
- 本便の実 PG 試験は使い捨て DB 方式（backend/tests/test_suppliers_rls.py）。

## §5 既存 ADR 検索

- `git grep -il suppliers docs/adr/`: ADR-021、ADR-072、ADR-085、ADR-1018、ADR-147 の 5 件。
  - ADR-1018（本テーマ。:15 の 11 表、:24-25 で段階②を②a/②b に分けた）。
  - ADR-072（:63,:82,:116 suppliers.py に reset_tenant_context を入れる件）。
  - ADR-021（:53,:78 仕入元マスタは共通の suppliers 参照）、ADR-085（運営画面の仕入先プロンプト）、ADR-147（:25 仕入れロールの権限対象）。
- `docs/adr/FEATURE-INDEX.md:18`: 「在庫 / inventory / 商品マスタ / 仕入元 / オファー」→ ADR-099／ADR-093／ADR-014。
- 【事実】ADR-1018 以外に、suppliers の RLS を決めた ADR は無い。ADR 変更は本便では行わない。
