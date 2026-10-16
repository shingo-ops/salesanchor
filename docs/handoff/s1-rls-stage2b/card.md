---
mode: handoff
---
# 実装カード — S1 段階②b（public.suppliers の RLS）

> この文書は何か：実装担当が迷わず作れるよう、触る場所と完了条件を並べたカードです。正は [design.md](design.md)。

## 前提

- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2b（origin/main 2bd773fcd 起点）
- PO 承認: KGI「y」（2026-10-15）、2026-10-16 一任（docs/specs/tenant-rls/ideal-state.md）
- 審査: [review-opus.md](review-opus.md) APPROVE

## 作業

1. migration `migrations/20261016_020000_add_suppliers_rls.sql` を design §2-1 のとおり作成（products の 4 ポリシーと同文、名前は suppliers_*）。`scripts/run_all_migrations.sh` 末尾に 1 行登録（②a の行の次）。
2. design §2-2 の #1〜#4・#6・#7 を修正。型は「書込の直前に `await set_operator_context(db)`、その関数の `finally` で `await reset_operator_context(db)`」。tenant 文脈を張る処理（get_current_tenant / set_tenant_context）がある関数では、その**後**に張る。
   - 想定分岐: 書込関数が途中で `db.commit()` する場合も、session 単位の SET なので commit 後も残る（reset は finally）。関数がセッションを受け取るだけで commit しない場合も同じ型でよい。
   - 想定分岐: #6 purchase_orders.py:108 で自社 tenant_id を取れる変数が無い場合は BLOCKED で止める（推測で取らない）。
   - #7 の 2 スクリプトは接続直後に `SET app.is_operator = 'true'` を 1 回（finally 不要）。
3. 試験 `backend/tests/test_suppliers_rls.py`（会社番号 982/983、②a の test_google_config_rls.py と同じ準備の型）で design §2-3 の ①〜⑨。
4. 回帰の効き: 修正（#1〜#4・#6）を外した複製で ④〜⑧ が落ち、修正ありで全件通ることを実測して保存。
5. 関連既存試験（suppliers を含む 31 ファイルのうち実行できるもの）を流す。ruff。
6. CI の migration-test.yml: public.suppliers が検証用 DB に既にあるか確認（migrate_inventory_sprint1.py が作る想定）。無ければ ②a と同じく最小定義を登録し、PR の触るファイルに足す。

## 触らない範囲

backend/app/routers/suppliers.py、backend/app/tasks/ 配下、fx_rate_updater、段階③の表、共通の rls_bootstrap.py。

## 完了条件

| 基準 | 検証方法 |
|---|---|
| 試験①〜⑨合格 | ローカル実 PG（アプリ接続役）で pytest |
| 修正を外すと④〜⑧が落ちる | 複製での実測ログ |
| 既存の関連試験が回帰しない | pytest 結果 |
| ruff 0 件 | ruff |
