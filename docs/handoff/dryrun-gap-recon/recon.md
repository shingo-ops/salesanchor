# Recon: CI ドライランが 013×103 衝突を検出できなかった原因と再発防止策

**調査日**: 2026-06-13  
**調査者**: Hikky-dev  
**関連**: `docs/handoff/migration-013-fix/recon.md`（障害の直接原因は別 recon に記録済み）  
**PO決定待ち**: §4 提案 B の実装許可

---

## 調査3問

① なぜ CI ドライランが 013×103 衝突を検出できなかったか  
② 検出できる方式の提案  
③ 同種リスクの横展開スキャン（全 migrations のスキャン）

---

## 1. CI ドライランの実際の仕組み（実文確認）

### 1-1. 実行対象は「変更ファイルのみ」

`.github/workflows/migration-test.yml:428-438`:

```bash
if ! ALL_CHANGED=$(git diff --name-only "$BASE" "$HEAD"); then
    ...
fi
```

**CI は PR の差分ファイルのみを実行する。変更のない既存 migration は対象外。**

### 1-2. SQL ファイルのフィルタ

`.github/workflows/migration-test.yml:459-461`:

```bash
CHANGED_SQL=$(echo "$ALL_CHANGED" \
  | grep '^migrations/[0-9][0-9][0-9].*\.sql$' \
  | xargs -r grep -L '{schema}' 2>/dev/null | sort || true)
```

- `[0-9][0-9][0-9].*\.sql$` — 3桁以上の数字で始まる `.sql` を対象（`013_*.sql` も `20260613_*.sql` も両方マッチ）
- `grep -L '{schema}'` — `{schema}` リテラルを含むファイルは除外

### 1-3. ベーススキーマに `source` 列が存在しない

`.github/workflows/migration-test.yml:196-202`:

```sql
CREATE TABLE IF NOT EXISTS tenant_001.leads (
    id         SERIAL PRIMARY KEY,
    tenant_id  INTEGER NOT NULL,
    full_name  VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**`source` 列はベーススキーマに存在しない。** 本番では migration 003（`migrations/003_add_phase1_tenant_tables.sql:83`）で `source VARCHAR(50)` が追加されているが、CI テストのベーススキーマには未反映。

### 1-4. 全 migration が毎デプロイで再実行される

`scripts/run_all_migrations.sh` — 冪等設計に依存した「全実行型」ランナー。  
`scripts/run_all_migrations.sh:74` に migration 013 が登録されており、デプロイごとに実行される。

---

## 2. 衝突が検出されなかった理由（確定事実）

### PR #1（funnel）が migration 103 を追加したとき

| 検査項目 | 結果 | 理由 |
|---|---|---|
| migration 103 が CI テスト対象か | ✅ 対象 | diff に含まれる、`{schema}` なし |
| CI ベーススキーマに `source` があるか | ❌ なし | `.github/workflows/migration-test.yml:196-202` 参照 |
| `DROP COLUMN IF EXISTS source` の挙動 | ✅ no-op | 列が存在しなければ何もしない |
| **CI の判定** | **PASS** | エラーなし・冪等性チェックも通過 |

### migration 013 はなぜ検査されなかったか

PR #1 は migration 013 を**変更していない**。  
CI は `.github/workflows/migration-test.yml:428-438` の `git diff` で変更ファイルのみを抽出するため、013 はテスト対象外。

### 本番で衝突が発生したメカニズム

```
デプロイ #N（PR #1 マージ後初回）:
  [2/145]  013 実行 → source 列が存在 → PASS
  [143/145] 103 実行 → source を DROP → PASS

デプロイ #N+1（次回デプロイ）:
  [2/145]  013 実行 → source 列が存在しない → ERROR: column "source" does not exist → 停止
  [3/145] 以降 実行されず（set -e による即時停止: scripts/run_all_migrations.sh 先頭）
```

---

## 3. まとめ：ドライランのギャップ

ドライランには **2 つのギャップ** が重なった。

| # | ギャップ | 根拠 |
|---|---|---|
| G1 | CI は変更ファイルのみを実行する（既存 migration はスキャンしない） | `migration-test.yml:428-438` |
| G2 | ベーススキーマが本番の「適用済み状態」を反映していない（`source` 列なし） | `migration-test.yml:196-202` vs `migrations/003_add_phase1_tenant_tables.sql:83` |

**G1 のみでも十分**。013 は変更されなかったので、G2 が解消されても今回は検出できない。  
**G2 単独でも不十分**。ベーススキーマを完璧に保つには毎 migration 追加ごとに手動更新が必要で運用コストが高い。

→ 両ギャップを同時に塞ぐ仕組みが必要（§4 参照）。

---

## 4. 検出できる方式の提案（実装は PO 承認後）

### 提案 A: 静的解析 — DROP 時に前方参照をスキャン

**仕組み**: 新規 migration に `DROP COLUMN <列名>` が含まれる場合、 `run_all_migrations.sh` で **より前に実行される** 既存 migration を対象に、その列名のリテラル参照を grep する。

```bash
# 疑似コード（CI チェックスクリプトとして実装）
for col in $(grep -oE 'DROP COLUMN IF EXISTS (\w+)' "$new_migration" | awk '{print $5}'); do
    # run_all_migrations.sh での実行順より前の migration ファイルのみ対象
    earlier_migrations=$(get_migrations_before "$new_migration" scripts/run_all_migrations.sh)
    if echo "$earlier_migrations" | xargs grep -l "\b${col}\b" 2>/dev/null; then
        echo "WARNING: 列 ${col} を参照している earlier migration が存在します"
    fi
done
```

**長所**: VPS アクセス不要、静的解析のみ、即実装可能  
**短所**: 列名の偽陽性あり（コメント・別テーブルの同名列）。精度向上には `テーブル名.列名` での検索が必要

**コスト**: `.github/workflows/migration-guard.yml` に追加（現在 276行 → +50行程度）

### 提案 B: ベーススキーマ自動同期（推奨）

**仕組み**: `migration-test.yml` のベーススキーマを「全 migration を順に適用した結果の `pg_dump --schema-only`」から自動生成するスクリプトを週次 CI で実行し、差分が出たら PR を自動起票。

**長所**: G1・G2 両方を解消する。本番スキーマとの乖離がゼロに近くなる  
**短所**: 週次実行のラグあり（即日反映ではない）。スクリプト作成コスト中程度

**実装の前提**: `migration-guard.yml:チェック2` で全 migration の `run_all_migrations.sh` 登録が強制済みのため、「全 migration を順に適用する」操作は再現可能。

### 今回の最小対処（既実装）

migration 013 を `source` 列の有無で分岐する防御コード（PR #2084、`migrations/013_add_meta_webhook_idempotency.sql:65-103`）により、同一衝突の再発は防止済み。上記 A/B は**将来の類似衝突**への対応。

---

## 5. 横展開スキャン：同種リスクの全件確認

### スキャン方法

対象: `migrations/` 以下の全ファイル  
目的: 「後の migration が DROP した列/テーブルを、先行 migration がまだ参照している」ケースを特定

### スキャン結果

#### DROP COLUMN の実行件数（コメント行除外、非コメントのみ）

| ファイル | DROP 対象 | コメント？ |
|---|---|---|
| `migrations/033_drop_companies_is_individual.sql:37` | `companies.is_individual` | 非コメント（実行） |
| `migrations/035_drop_customer_id_from_downstream.sql:160,168,176,184` | `deals/orders/quotes/invoices.customer_id` | 非コメント（実行） |
| `migrations/036_drop_customer_migration_map.sql:62` | `_customer_migration_map` テーブル | 非コメント（実行） |
| `migrations/053_add_users_locale_down.sql:3` | `users.locale` | 非コメント ※ rollback |
| `migrations/055_add_granted_scopes_down.sql:3` | `granted_scopes` | 非コメント ※ rollback |
| `migrations/067_add_inbound_review_version_and_permissions_down.sql:5` | `discord_inbound_messages.version` | 非コメント ※ rollback |
| `migrations/069_create_tenant_profile_down.sql:8` | `tenant_profile` テーブル | 非コメント ※ rollback |
| `migrations/070_add_spreadsheet_phase_down.sql:13` | `tenant_settings` テーブル | 非コメント ※ rollback |

`*_down.sql` は rollback 専用ファイル。`scripts/run_all_migrations.sh` に登録されていないことを確認済み（`grep "down" scripts/run_all_migrations.sh` → 0件）。本番デプロイには影響しない。

| ファイル | DROP 対象 | コメント？ |
|---|---|---|
| `migrations/20260601_140000_drop_customers_tables.sql:70-86` | `customers` 関連6テーブル | 非コメント（実行） |
| `migrations/20260613_030000_funnel_leads_initiative_channel.sql` (PR1) | `leads.source` | 非コメント（実行）← **今回の衝突**（PR1 未マージの main では未登録） |

#### 先行 migration からの参照チェック

| 衝突候補 | 先行 migration の参照 | 安全か |
|---|---|---|
| 013 × 103（`leads.source`）| `migrations/013_add_meta_webhook_idempotency.sql:54-63` で `SELECT source FROM leads` | ✅ **PR #2084 で修正済み**（IF EXISTS ガード追加） |
| 026 × 20260601（`customers`）| `migrations/026_create_customer_contact_channels.sql:39-44` — `IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'customers') THEN CONTINUE` | ✅ 安全：存在チェックで skip |
| 027 × 20260601（`customers`）| `migrations/027_backfill_customer_contact_channels.sql:26-31` — `IF NOT EXISTS customers OR NOT EXISTS customer_contact_channels THEN CONTINUE`。`customer_discord` も `:59-62` で `IF EXISTS` ガード済み | ✅ 安全確認済み（2026-06-13） |
| 033（`companies.is_individual` DROP）× 以前 | 033 より前の migration に `is_individual` 参照なし（grep確認済み） | ✅ 安全 |
| 035（`customer_id` DROP）× 以前 | 035 より前の migration に `customer_id` CREATE → 035 が DROP → それ以降は参照なし | ✅ 安全（035 以降に customer_id 参照なし） |

#### migration 027 の確認結果（2026-06-13 完了）

`migrations/027_backfill_customer_contact_channels.sql:26-33` に `customers` / `customer_contact_channels` の存在確認ガードがあり、どちらかが存在しないテナントは `CONTINUE` でスキップされる。`customer_discord` 参照は `:59-62` の `IF EXISTS` ブロック内のみ。

`20260601` DROP後の再実行時：
- `027:26-28` で `customers` NOT EXISTS を検知 → `CONTINUE`
- INSERT処理（`:36-49`・`:63-72`）に到達しない → エラーなし

**安全確認済み。SQL修正不要。**

---

### まとめ：確定した衝突ケース

| 衝突 | 状態 |
|---|---|
| **migration 013 × 103**（`leads.source`）| ✅ PR #2084 で修正済み |
| migration 027 × 20260601（`customers`）| ✅ 安全確認済み（`027:26-33` ガード、SQL修正不要） |
| その他 | ✅ 安全（存在チェックあり、または rollback専用） |

---

## 6. 次のアクション

| # | アクション | 担当 | 優先度 |
|---|---|---|---|
| A1 | migration 027 に `customers` 存在チェックがあるか確認 | ✅ 完了（2026-06-13）| — |
| B1 | 提案 A（静的 DROP→参照スキャン）の実装承認 → `migration-guard.yml` チェック5追加 | PO 判断後 | 中 |
| B2 | 提案 B（ベーススキーマ自動同期）の設計・実装 | PO 判断後 | 低（中長期） |
