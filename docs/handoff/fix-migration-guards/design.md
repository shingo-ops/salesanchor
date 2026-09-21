# design: fix-migration-guards

## 参照
- recon: docs/handoff/fix-migration-guards/recon.md
- 対象ADR: ADR-1002-unify-product-id-and-fix-migration-compat.md

## How（実装方針）

各マイグレーションのスキーマガード直後に、対象テーブルの存在を `information_schema.tables` でチェックし、テーブルが存在しない場合は `RAISE NOTICE` → `RETURN` でスキップする。

```sql
IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = _schema AND table_name = '<table>'
) THEN
    RAISE NOTICE '<migration>: %.<table> does not exist, skipping', _schema;
    RETURN;
END IF;
```

`20260910_180000` のみ `to_regclass` 方式で3テーブルをチェック済み。
部分削除ケース（1〜2テーブル存在）での `RAISE EXCEPTION` を `RETURN` に変更する。

## KPI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| 6マイグレーションがDROP後の再実行でSKIPする | ローカルで tenant_004 スキーマ保持・テーブル削除後にマイグレーション実行 |
| CIが全パス | PR上のCI結果 |
| 既存テストが壊れない | backend/tests/ 全パス |

## 影響範囲

変更: 既存マイグレーション6ファイルにガード追加のみ
触らない: DML本体・ビジネスロジック・テスト・フロントエンド

## 戻し方

各ファイルの `IF NOT EXISTS ... RETURN` ブロックを削除するだけで元に戻る。

## 外部・過去事例の参照と我々への応用

既存コード内に同パターンの先行事例あり:
- `migrations/20260906_230000_redact_extraction_error_keys_t004.sql` では `information_schema.tables` による `extraction_jobs` 存在チェックを実装済み
- `migrations/20260905_120000_register_15_suppliers_t004.sql` では `to_regclass('.supplier_channels')` 存在チェックを実装済み

上記2ファイルのパターンをそのまま残り6ファイルに適用する。新たな設計判断は不要。

## 維持の仕組み

- ガード追加済みの6マイグレーションは今後のデプロイで安全にスキップされる
- 将来、新たに旧マイグレーションが問題を起こす場合も同パターンで対処可能
- ADR-1002 の移行完了後はこれらのマイグレーションは実質no-opとなり、保守コストはゼロ
