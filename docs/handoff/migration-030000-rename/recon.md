# recon.md — develop 030000 刻印衝突調査

- **日付**: 2026-06-26
- **対象 KGI**: develop→main PR #2540 が CONFLICTING でなくなる
- **参照**: [design.md](./design.md)

---

## R-1: ファイル内容の同一性確認

```
git diff origin/develop:migrations/20260623_030000_add_products_tcg_type_fk.sql \
         origin/main:migrations/20260623_060000_add_products_tcg_type_fk.sql
```

→ **差分ゼロ（完全同一）**。

両ファイルのコメント内に `Migration 20260623_030000:` という記述が残っているが、
main の 060000 側も同じ表記のまま（先行リネーム時に内容未変更）。
動作に影響しない。

---

## R-2: develop 側の衝突ファイル特定

`origin/develop` の `migrations/` に 030000 タイムスタンプが2本存在：

| ファイル | 用途 |
|---|---|
| `migrations/20260623_030000_add_products_tcg_type_fk.sql` | products FK 追加 |
| `migrations/20260623_030000_drop_inventory_offer_key.sql` | 在庫 offer key 削除 |

`origin/main` の同時点スナップショット：

| ファイル | 用途 |
|---|---|
| `migrations/20260623_030000_drop_inventory_offer_key.sql` | 在庫 offer key 削除 |
| `migrations/20260623_060000_add_products_tcg_type_fk.sql` | products FK 追加（リネーム済） |

---

## R-3: run_all_migrations.sh 登録状況

develop `scripts/run_all_migrations.sh:445`:
```
run_sql migrations/20260623_030000_add_products_tcg_type_fk.sql
```

develop `scripts/run_all_migrations.sh:176`（HELD・コメントアウト済み）:
```
# HELD: 旧キー削除は新コードデプロイ後に手動GOで適用。run_all_migrations.sh では自動実行しない。
# run_sql migrations/20260623_030000_drop_inventory_offer_key.sql
```

main `scripts/run_all_migrations.sh:448`:
```
run_sql migrations/20260623_060000_add_products_tcg_type_fk.sql
```

---

## R-4: ファイル名参照の全箇所（`030000_add_products_tcg_type` を含む）

```
git grep -n "030000_add_products_tcg_type" origin/develop -- ':(exclude)migrations/'
```

| ファイル:行 | 内容 | 変更要否 |
|---|---|---|
| `scripts/run_all_migrations.sh:445` | `run_sql migrations/20260623_030000_add_products_tcg_type_fk.sql` | **要変更** |
| `backend/tests/rls_bootstrap.py:27` | ブートストラップリストにファイル名記載 | **要変更** |
| `backend/tests/test_products_tcg_type_fk.py:45` | テスト内の期待ファイル名 | **要変更** |
| `.claude-pipeline/active-work.md:28` | feature ブランチ記録（テキスト） | 変更不要 |
| `docs/ai-agents/evidence-registry.md:934` | エビデンス記録（テキスト）× 2行 | 変更不要 |

---

## R-5: PR #2540 と migration-guard の現状

```
gh pr view 2540 --json state,mergeable,mergeStateStatus
→ {"state":"OPEN","mergeable":"CONFLICTING","mergeStateStatus":"DIRTY"}
```

migration-guard `.github/workflows/migration-guard.yml` チェック5 ロジック（L287-333）:
- PR の `BASE=main`, `HEAD=develop`
- `--diff-filter=A` で PR 新規追加ファイルのみ抽出
- `EXISTING_STAMPS` = main 時点の全刻印集合
- develop の `030000_add_products_tcg_type_fk` が新規追加として検出 → main の `030000_drop_inventory_offer_key` と刻印 `20260623_030000` が衝突 → **BLOCK**

リネーム後（`060000_add_products_tcg_type_fk`）:
- main に `060000_add_products_tcg_type_fk` が既存 → `--diff-filter=A` で新規追加として検出されない
- チェック5 BLOCK 消える

---

## R-6: 根本原因

PR #2538 が develop を経由せず main 直行したため、main 側では `030000→060000` にリネームされたが develop 側に反映されなかった（刻印ドリフト）。
