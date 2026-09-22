# Design: fix-phase2c-dynamic-fk

## KGI
Phase 2c (drop_tcg_products_phase2c.sql) が本番環境で FK エラーなく完走する。

## 設計方針
ハードコードした FK 名リストに頼らず、pg_constraint を走査して tenant_* スキーマ内の
tcg_products を参照する全 FK を動的に発見・削除する。

既存の fix_phase2c_fk_drop_only.sql は残置（冪等）。
本マイグレーションはその直後に実行し、取りこぼし分を確実に消す。

## 実行順序（run_all_migrations.sh）
```
run_sql fix_phase2c_fk_drop_only.sql        # ハードコード版（既存）
run_sql drop_all_tcg_products_fks.sql       # 動的全件版（新規）← ここ
run_sql drop_tcg_products_phase2c.sql       # Phase 2c DROP
```

## KPI / 検証方法
| 基準 | 検証方法 |
|---|---|
| migration が ERROR なく完走する | デプロイログに `Dynamic FK cleanup complete: N FK(s) dropped` が出力される |
| Phase 2c DROP が成功する | デプロイログに phase2c の成功メッセージが出る |
| tenant_*.tcg_products が消えている | 本番で `\dt tenant_*.tcg_products` が 0 件 |

## 守り手
- SET LOCAL lock_timeout = '5s' — ロック待ち無限待機を防止
- SET LOCAL statement_timeout = '30s' — 長時間実行を防止
- DROP CONSTRAINT IF EXISTS — FK が既に消えていても冪等

## 影響範囲
- 本番 DB の tenant_* スキーマ（tcg_products を参照する FK のみ）
- アプリコードへの影響なし（tcg_products は既に非参照化済み）

## 戻し方
DROP CONSTRAINT は不可逆（FK の定義は ADR-1002 Phase 1 で migration 済みのため
ロールバック不要）。tcg_products 自体も Phase 2c で削除するため FK の復元は不要。

## 維持の仕組み
- 本マイグレーションは冪等（IF EXISTS）なため再実行しても安全
- Phase 2c 完了後は tcg_products 自体が消えるため FK も存在しない
- 追加メンテナンス不要

## 外部・過去事例の参照と我々への応用
- PostgreSQL 公式ドキュメント: pg_constraint カタログを使った動的 DDL は標準パターン
  （https://www.postgresql.org/docs/current/catalog-pg-constraint.html）
- format() + EXECUTE による動的 ALTER TABLE は PL/pgSQL での推奨手法
- 我々への応用: FK 名を推測せず pg_catalog を信頼するため、将来のマイグレーション由来の
  FK 追加にも自動対応できる
