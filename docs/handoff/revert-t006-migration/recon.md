# recon — revert-t006-migration

**仕事名**: revert-t006-migration  
**日付**: 2026-09-06  
**対象ADR**: ADR-154  
**担当**: Hikky-dev (QA-03a)

---

## 障害事実

`deploy.yml` の migration ステップ [210/210] が RAISE EXCEPTION で失敗し、
本番デプロイが完全停止した。

```
ERROR:  20260906_100000: テーブル数が 27 ではありません: 95
CONTEXT:  PL/pgSQL function inline_code_block line 629 at RAISE
```

---

## 根本原因（file:line 引用）

| 引用先 `path:line` | 確認内容 |
|---|---|
| `migrations/20260906_100000_create_tcg_tables_t006.sql:629` | `RAISE EXCEPTION` でテーブル数を検証。対象スキーマ全体のテーブル数を数えていた |
| `scripts/run_all_migrations.sh:587` | 当該 migration を呼び出していた行（本PR で削除） |

### tenant_006 の実態

- `tenant_006` は "Sales Anchor App Review"（Meta 審査専用テナント）
- CRM 系テーブルが **68 本**既に存在するテナント
- migration は「TCG テーブル 27 本を作成した後、スキーマ全体が 27 本のはず」と検算していた
- **68（既存）+ 27（新規）= 95 本** → 検算 27 ≠ 95 で RAISE EXCEPTION

### RAISE EXCEPTION の効果

- PostgreSQL の `DO` ブロック内で RAISE EXCEPTION → トランザクション全体がロールバック
- **tenant_006 に TCG テーブルは 1 本も作られていない**（68 本のまま）
- 本番 DB への副作用: なし

---

## QA 環境の正しい設計

- QA 環境は `tenant_001`（STANDARD-WORKFLOW.md に「空テスト」と明記）に作り直す
- tenant_006 は Meta 審査専用のため TCG QA 用途不可
- QA-03 (別 PR) で tenant_001 向け migration として再作成する

---

## 未解決ゼロ確認

全て解消済み
