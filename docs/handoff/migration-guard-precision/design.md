# 設計: migration 2本の存在確認ガードの条件漏れ修正

状態: PO 承認済み（チャット「y」2026-10-17）。マージは PO の「GO #番号」が要る（ADR-136）。
事実: docs/handoff/migration-guard-precision/recon.md
関連 ADR: ADR-1005、ADR-1007（決定2）、ADR-155。

## 1. 目的
CI 全件ドライラン2周目の失敗のうち、存在確認の条件漏れが原因の2件（20260920_020000、20260919_030000）を無くす。

## 2. 変更前後（これだけ）
|ファイル:行|変更前|変更後|
|---|---|---|
|migrations/20260920_020000_supplier_line_name_unique.sql:12-13|`table_schema='public' AND column_name='line_name'`|間に `AND table_name = 'suppliers'` を追加|
|migrations/20260919_030000_master_ssot_fk_work_id.sql:24|`n.nspname='public' AND c.relname='tcg_type'||'_master'`|次行に `AND c.relkind IN ('r','p')` を追加|
触らない: 他の行、他の migration、scripts/run_all_migrations.sh、deploy.yml。

## 3. 影響範囲
- scripts/run_all_migrations.sh:697,706 で毎デプロイ再実行される。
- 本番は索引・FK が既存（recon.md §2）のため、修正前後とも何も変えない。変わるのは索引・制約が無い環境で「落ちる」→「何もしない」だけ。
- ADR-1007 決定2（構造のみ）に反する値の操作は加えていない。

## 4. 受入条件
|基準|検証方法|
|---|---|
|K1 CI 全件ドライランの2周目失敗が 23→21。消えるのは 20260920_020000 と 20260919_030000 の2周目分だけ。新規失敗0|CI ログの失敗一覧を前回 opus_fail_r2.txt と diff|
|K2 1周目の失敗一覧は24件のまま不変|同上|
|K3 本番反映後の migration ログで両ファイルがエラー0|deploy ログ|
|K4 本番の索引定義・FK 定義が prod_before.txt と同一|同じ SELECT（prod_before.txt の a, b）|

## 5. 外部・過去事例
不要: 既存ガードの条件漏れ修正のため。過去事例: 196d75616、PR #4419（既存 migration の本文のみの書き換え）。

## 維持の仕組み
- 守り手: 設計担当（Opus）。反映後に deploy ログと本番 SELECT で K3・K4 を確認する。
- 新しい migration の存在確認で同じ漏れが入らないよう、恒久の自動検出は今回の範囲外（未実装）。ADR-1007 決定6（チェックサム）で実行済みファイルの書き換えが止まる前に入れる必要がある。

## 6. 戻し方
この PR の Revert。
