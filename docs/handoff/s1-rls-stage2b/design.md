---
mode: handoff
---
# 設計 — S1 段階②b（仕入先台帳 public.suppliers の RLS）

> この文書は何か：会社ごとの仕入先と、全社共通の仕入先台帳を、データベース自身が「見せる・書かせる」範囲で守るための設計書です。

**日付**: 2026-10-16　**根拠**: [recon.md](recon.md)、ADR-1018 段階②、ADR-145（products の手本）
**状態**: 設計案作成済み → 審査は [review-opus.md](review-opus.md)

## 1. 目的と利用者に見える変化

- 目的: アプリ接続（salesanchor_app）から、運営以外が共通の仕入先台帳（tenant_id が空の行）を書き換えられないようにする。会社ごとの行は自社の文脈でしか見えない・書けないようにする。
- 利用者に見える変化: **なし**（設計どおり全書込経路に運営の文脈を張った場合）。
  - 根拠: 本番 288 行はすべて共通行（tenant_id 空。/tmp/CC報告ファイル/s1-stage2/2b-prod-recent.txt）。会社画面（/suppliers）は `tenant_id = 自社` で絞って読むため、表示件数は変わらない（0 件のまま）。共通行は誰からでも読めるポリシーなので、LINE 解析・在庫などの読取は変わらない。
  - 各社スキーマに suppliers 表は無い（public のみ。2b-schemas.txt）。

## 2. 変更内容

### 2-1. migration（ADR-145 products と同じ 4 ポリシー）

`migrations/20261016_020000_add_suppliers_rls.sql`

- ENABLE / FORCE ROW LEVEL SECURITY
- SELECT: `tenant_id IS NULL OR tenant_id = 自社`
- INSERT / UPDATE / DELETE: 共通行（tenant_id 空）は `app.is_operator = 'true'` のときだけ、会社行は `tenant_id = 自社` のときだけ
- 文言は migrations/20260626_130000_force_rls_public_products.sql:5-37 の `products` を `suppliers` に置き換えたものと同文。ポリシー名は `suppliers_select` / `suppliers_insert` / `suppliers_update` / `suppliers_delete`。`DROP POLICY IF EXISTS` で冪等。
- run_all_migrations.sh 末尾に 1 行登録。

### 2-2. 書込経路に運営の文脈を張る（漏れると INSERT は 42501 で失敗、UPDATE は静かに 0 行）

共通の型: 書込の直前に `await set_operator_context(db)`（backend/app/auth/dependencies.py:489）、関数の `finally` で `await reset_operator_context(db)`（:506）。`set_tenant_context` は is_operator を空に戻す（:337）ので、**必ず tenant 文脈を張った後**に operator を張る。

| # | 経路 | 書込箇所 | 呼ばれ方 | 対処 |
|---|---|---|---|---|
| 1 | LINE 取込の自動登録 | backend/app/services/tcg_line_import_svc.py:643（INSERT）・:656（UPDATE） | 端末からの毎日の取込 POST /api/v1/tcg/line-devices/import（line_import_devices.py:68→tcg_line_import.py:714）と、運営画面の取込 | 4b ブロックの直前で set、import_line_export の finally で reset |
| 2 | 取込レビューの仕入先決定 | backend/app/routers/tcg_line_import.py:480・:489・:502（resolve_supplier :398） | 運営画面 ReviewSection と CLI（line_import_admin） | 関数内の書込前で set、finally で reset |
| 3 | 運営の仕入先マスタ画面 | backend/app/routers/super_admin_suppliers.py:128・:152・:183・:211・:462・:488・:506・:757 | 運営画面（require_super_admin） | 各書込関数で set、finally で reset |
| 4 | 名寄せ CLI | backend/app/services/line_source_names.py:114（link_pending :81） | CI の line-import-operations.yml:54 経由の line_import_admin | 書込前で set、finally で reset |
| 5 | CLI 入口 | backend/app/line_import_admin.py:172 run（:151 の LOCK TABLE は RLS の対象外） | GitHub Actions の手動実行（運営のみ） | **変更しない**。到達する書込は #2・#4 の関数内で張るため。外側でも張ると内側の reset で外側の想定が崩れるので、張る場所は「書込のある関数の中」だけに統一する |
| 6 | 発注の仕入先複製 | backend/app/routers/purchase_orders.py:108 | POST /purchase-orders（画面からの呼出 0 件） | 列リストに `tenant_id` を足し、値は呼出元の自社 ID（コメント「tenant 仕入元」の意図どおり会社行にする）。operator は張らない。注: 直前の照合 SELECT（:94・:99）は共通行も読めるため、元の共通行自身に一致して INSERT に届くことは通常ない。届いた場合に 42501 で落ちないための修正 |
| 7 | 初期投入スクリプト | scripts/seed_suppliers_from_line_master.py:147・seed_suppliers_from_sheet.py:126 | 手動 CLI | 接続直後に `SET app.is_operator = 'true'`（スクリプト専用接続のため後始末は接続終了で消える） |

触らない: 会社画面 backend/app/routers/suppliers.py（全書込が自社文脈・自社 tenant_id。:274・:485 の `WHERE id` 更新は直前に自社で作った行）。Celery タスク（suppliers の書込 0 件・読取のみ）。

### 2-3. 試験（実 PostgreSQL・アプリ接続役。CI の RLS 用 2 接続）

`backend/tests/test_suppliers_rls.py`（会社番号 982/983）
- ① 4 ポリシーと t/t
- ② 文脈なし・会社文脈とも共通行は読める。会社 A は B の行が見えない
- ③ 会社文脈で共通行の UPDATE が 0 行、共通行の INSERT が 42501
- ④ #1 import_line_export を文脈なしのセッションで呼び、未知の仕入先が共通行として登録される（修正を外すと 42501 で落ちる）
- ⑤ #2 resolve_supplier（create と assign）で共通行に書ける（assign は修正を外すと 0 行で落ちる）
- ⑥ #3 運営画面の作成・更新・論理削除・抽出ルール更新・取込 commit が共通行に反映される
- ⑦ #4 link_pending が共通行の line_name を更新する
- ⑧ #6 発注の複製が自社 tenant_id で作られる
- ⑨ 各経路の後で接続の app.is_operator が空に戻っている（漏れ防止）

回帰の効き: 修正を外した複製で ④〜⑧ が失敗することを実測して記録する（②a と同じ手順）。

## 3. 戻し方

```sql
DROP POLICY IF EXISTS suppliers_select ON public.suppliers;
DROP POLICY IF EXISTS suppliers_insert ON public.suppliers;
DROP POLICY IF EXISTS suppliers_update ON public.suppliers;
DROP POLICY IF EXISTS suppliers_delete ON public.suppliers;
ALTER TABLE public.suppliers NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers DISABLE ROW LEVEL SECURITY;
```
アプリ修正は Revert（文脈を張るだけなので RLS が無くても動作は同じ）。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| CI で試験①〜⑨が実走して合格 | pytest-run-internal のログで test_suppliers_rls の passed 件数 |
| 本番で suppliers が t/t・ポリシー 4 本 | pg_class・pg_policies を SELECT |
| 本番 288 行（適用時点の件数）と最大 id が不変 | 適用前後の count・max(id) |
| アプリ接続役で、文脈なし・会社文脈から共通行を UPDATE すると 0 行、運営文脈では 1 行 | permit-danger 付き BEGIN…ROLLBACK |
| 端末からの LINE 取込が反映後も成功し続ける | 反映後の import_jobs（status=ok）件数が増え、失敗が 0。backend ログに 42501 / row-level security が 0 件 |
| 反映後に新しい仕入先の自動登録が 1 件以上起きたら共通行として作られている | suppliers の新規行の tenant_id が空（起きなければ「未観測」と記録） |

## 5. リスクと対処

| リスク | 対処 |
|---|---|
| 書込経路の見落とし → 取込が 42501 で失敗 | recon で HTTP・Celery・CLI・CI を全列挙（2b・2b2）。反映直後に import_jobs と backend ログを確認し、失敗が出たら §3 の SQL で即戻す |
| is_operator が接続に残る | 各経路の finally で reset。get_db の後始末（clear_tenant_context）でも空に戻る（dependencies.py:421-440）。試験⑨ |
| UPDATE が静かに 0 行 | 試験⑤⑥⑦で更新後の値を確認 |

## 6. 外部・過去事例の参照と我々への応用

PostgreSQL 公式 docs/16/ddl-rowsecurity（FORCE で所有者にも適用、ポリシー不一致の UPDATE は 0 行・INSERT は error）。社内前例 ADR-145 products（同じ 4 ポリシーで 2026-06 から稼働）を手本にする。数値の外部事例は不要（社内前例で挙動を実測できるため）。

## 7. 触らない範囲

suppliers.py（会社画面）、Celery タスク、fx_rate_updater の is_operator 残留（別件として記録のみ）、段階③の表。

## 維持の仕組み

- 守り手（新設）: backend/tests/test_suppliers_rls.py（CI の pytest で、共通行は運営文脈でのみ書ける・会社固有行は自社のみ・各書込経路が文脈を張る、を毎回検証）。
- migration は冪等で毎デプロイ再実行されるため、手作業で RLS を外しても次のデプロイで戻る。
